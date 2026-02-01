"""Consul 配置中心集成

支持 HashiCorp Consul KV 存储，提供配置读取、写入和监听功能。
"""

from __future__ import annotations

import asyncio
import base64
import json
from datetime import datetime
from typing import Any

import httpx
from loguru import logger
from pydantic import Field

from .base import ConfigItem, ConfigProvider, ProviderConfig


# ============================================================================
# Consul 配置
# ============================================================================


class ConsulConfig(ProviderConfig):
    """Consul 配置"""

    host: str = Field(default="localhost", description="Consul 服务器地址")
    port: int = Field(default=8500, description="Consul 端口")
    scheme: str = Field(default="http", description="协议 (http/https)")
    token: str = Field(default="", description="ACL Token")
    datacenter: str = Field(default="", description="数据中心")
    prefix: str = Field(default="config/", description="键前缀")
    consistency: str = Field(default="default", description="一致性模式")


# ============================================================================
# Consul 配置提供者
# ============================================================================


class ConsulProvider(ConfigProvider):
    """Consul 配置提供者

    支持：
    - KV 存储读写
    - 配置监听（阻塞查询）
    - ACL Token 认证
    - 多数据中心
    """

    def __init__(self, config: ConsulConfig):
        """初始化 Consul 提供者

        Args:
            config: Consul 配置
        """
        super().__init__(config)
        self.consul_config = config
        self._client: httpx.AsyncClient | None = None
        self._watch_indexes: dict[str, int] = {}  # key -> modify_index

    @property
    def _base_url(self) -> str:
        """基础 URL"""
        return f"{self.consul_config.scheme}://{self.consul_config.host}:{self.consul_config.port}"

    def _get_full_key(self, key: str) -> str:
        """获取完整键名（带前缀）"""
        prefix = self.consul_config.prefix
        if prefix and not key.startswith(prefix):
            return f"{prefix}{key}"
        return key

    def _strip_prefix(self, key: str) -> str:
        """去除键前缀"""
        prefix = self.consul_config.prefix
        if prefix and key.startswith(prefix):
            return key[len(prefix) :]
        return key

    # ========================================================================
    # 连接管理
    # ========================================================================

    async def _connect(self) -> bool:
        """连接到 Consul"""
        headers = {}
        if self.consul_config.token:
            headers["X-Consul-Token"] = self.consul_config.token

        self._client = httpx.AsyncClient(
            timeout=self.config.timeout,
            headers=headers,
        )

        return await self._health_check()

    async def _disconnect(self) -> None:
        """断开连接"""
        if self._client:
            await self._client.aclose()
            self._client = None

    def _get_params(self) -> dict[str, Any]:
        """获取通用请求参数"""
        params = {}
        if self.consul_config.datacenter:
            params["dc"] = self.consul_config.datacenter
        if self.consul_config.consistency != "default":
            params[self.consul_config.consistency] = ""
        return params

    # ========================================================================
    # 配置操作
    # ========================================================================

    async def _get(self, key: str) -> ConfigItem | None:
        """获取配置"""
        if not self._client:
            return None

        full_key = self._get_full_key(key)

        try:
            response = await self._client.get(
                f"{self._base_url}/v1/kv/{full_key}",
                params=self._get_params(),
            )

            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    item = data[0]

                    # 解码 Base64 值
                    value_b64 = item.get("Value", "")
                    if value_b64:
                        value_bytes = base64.b64decode(value_b64)
                        value_str = value_bytes.decode("utf-8")

                        # 尝试解析 JSON
                        try:
                            value = json.loads(value_str)
                            content_type = "json"
                        except json.JSONDecodeError:
                            value = value_str
                            content_type = "text"
                    else:
                        value = ""
                        content_type = "text"

                    # 记录 ModifyIndex 用于监听
                    modify_index = item.get("ModifyIndex", 0)
                    self._watch_indexes[key] = modify_index

                    return ConfigItem(
                        key=key,
                        value=value,
                        version=str(modify_index),
                        content_type=content_type,
                        metadata={
                            "create_index": item.get("CreateIndex"),
                            "modify_index": modify_index,
                            "lock_index": item.get("LockIndex"),
                            "flags": item.get("Flags"),
                        },
                    )

            elif response.status_code == 404:
                return None
            else:
                logger.error(f"Consul 获取配置失败: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Consul 获取配置异常: {e}")
            return None

    async def _set(self, key: str, value: Any, content_type: str = "json") -> bool:
        """设置配置"""
        if not self._client:
            return False

        full_key = self._get_full_key(key)

        # 序列化值
        if content_type == "json" and not isinstance(value, str):
            content = json.dumps(value, ensure_ascii=False)
        else:
            content = str(value)

        try:
            response = await self._client.put(
                f"{self._base_url}/v1/kv/{full_key}",
                params=self._get_params(),
                content=content.encode("utf-8"),
            )

            if response.status_code == 200 and response.text == "true":
                logger.debug(f"Consul 配置设置成功: {key}")
                return True
            else:
                logger.error(f"Consul 配置设置失败: {response.status_code}, {response.text}")
                return False

        except Exception as e:
            logger.error(f"Consul 配置设置异常: {e}")
            return False

    async def _delete(self, key: str) -> bool:
        """删除配置"""
        if not self._client:
            return False

        full_key = self._get_full_key(key)

        try:
            response = await self._client.delete(
                f"{self._base_url}/v1/kv/{full_key}",
                params=self._get_params(),
            )

            if response.status_code == 200 and response.text == "true":
                logger.debug(f"Consul 配置删除成功: {key}")
                if key in self._watch_indexes:
                    del self._watch_indexes[key]
                return True
            else:
                logger.error(f"Consul 配置删除失败: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Consul 配置删除异常: {e}")
            return False

    async def _list(self, prefix: str = "") -> list[str]:
        """列出配置键"""
        if not self._client:
            return []

        full_prefix = self._get_full_key(prefix)

        try:
            params = {**self._get_params(), "keys": ""}
            response = await self._client.get(
                f"{self._base_url}/v1/kv/{full_prefix}",
                params=params,
            )

            if response.status_code == 200:
                keys = response.json()
                return [self._strip_prefix(k) for k in keys]
            elif response.status_code == 404:
                return []
            else:
                logger.error(f"Consul 列出配置失败: {response.status_code}")
                return []

        except Exception as e:
            logger.error(f"Consul 列出配置异常: {e}")
            return []

    async def _health_check(self) -> bool:
        """健康检查"""
        if not self._client:
            return False

        try:
            response = await self._client.get(
                f"{self._base_url}/v1/status/leader",
            )
            return response.status_code == 200 and response.text != '""'

        except Exception:
            return False

    # ========================================================================
    # 配置监听
    # ========================================================================

    async def _check_updates(self) -> None:
        """检查配置更新（使用阻塞查询）"""
        if not self._client or not self._watch_indexes:
            return

        for key, index in list(self._watch_indexes.items()):
            try:
                await self._watch_key(key, index)
            except Exception as e:
                logger.error(f"Consul 监听异常: {key}, 错误: {e}")

    async def _watch_key(self, key: str, index: int) -> None:
        """监听单个配置键

        Args:
            key: 配置键
            index: 当前 ModifyIndex
        """
        if not self._client:
            return

        full_key = self._get_full_key(key)

        try:
            params = {
                **self._get_params(),
                "index": index,
                "wait": f"{int(self.config.watch_interval)}s",
            }

            response = await self._client.get(
                f"{self._base_url}/v1/kv/{full_key}",
                params=params,
                timeout=self.config.watch_interval + 5,
            )

            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    item = data[0]
                    new_index = item.get("ModifyIndex", 0)

                    if new_index > index:
                        # 配置已更新
                        config_item = await self._get(key)
                        if config_item:
                            self._update_cache(key, config_item)
                            logger.info(f"Consul 配置已更新: {key}")

        except asyncio.TimeoutError:
            # 阻塞查询超时是正常的
            pass

    async def watch(self, key: str) -> None:
        """监听配置变更

        Args:
            key: 配置键
        """
        # 获取当前配置的 ModifyIndex
        item = await self._get(key)
        if item:
            self._watch_indexes[key] = int(item.version)
            self._update_cache(key, item)
        else:
            self._watch_indexes[key] = 0

        logger.debug(f"开始监听 Consul 配置: {key}")

    async def unwatch(self, key: str) -> None:
        """取消监听

        Args:
            key: 配置键
        """
        if key in self._watch_indexes:
            del self._watch_indexes[key]
            logger.debug(f"取消监听 Consul 配置: {key}")

    # ========================================================================
    # 事务操作
    # ========================================================================

    async def txn(self, operations: list[dict[str, Any]]) -> bool:
        """执行事务操作

        Args:
            operations: 操作列表，每个操作包含:
                - verb: 操作类型 (set, delete, check-index, etc.)
                - key: 配置键
                - value: 配置值（可选）
                - index: ModifyIndex（可选）

        Returns:
            是否执行成功
        """
        if not self._client:
            return False

        txn_ops = []
        for op in operations:
            verb = op.get("verb", "set")
            key = self._get_full_key(op.get("key", ""))

            txn_op = {"KV": {"Verb": verb, "Key": key}}

            if "value" in op:
                value = op["value"]
                if not isinstance(value, str):
                    value = json.dumps(value, ensure_ascii=False)
                txn_op["KV"]["Value"] = base64.b64encode(value.encode()).decode()

            if "index" in op:
                txn_op["KV"]["Index"] = op["index"]

            txn_ops.append(txn_op)

        try:
            response = await self._client.put(
                f"{self._base_url}/v1/txn",
                params=self._get_params(),
                json=txn_ops,
            )

            if response.status_code == 200:
                logger.debug("Consul 事务执行成功")
                return True
            else:
                logger.error(f"Consul 事务执行失败: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Consul 事务执行异常: {e}")
            return False


# ============================================================================
# 工厂函数
# ============================================================================


def create_consul_provider(
    host: str = "localhost",
    port: int = 8500,
    token: str = "",
    prefix: str = "config/",
    **kwargs,
) -> ConsulProvider:
    """创建 Consul 配置提供者

    Args:
        host: Consul 服务器地址
        port: Consul 端口
        token: ACL Token
        prefix: 键前缀
        **kwargs: 其他配置参数

    Returns:
        Consul 配置提供者实例
    """
    config = ConsulConfig(
        name="consul",
        host=host,
        port=port,
        token=token,
        prefix=prefix,
        **kwargs,
    )
    return ConsulProvider(config)
