"""Nacos 配置中心集成

支持阿里云 Nacos 配置中心，提供配置读取、写入和监听功能。
"""

from __future__ import annotations

import asyncio
import hashlib
import json
from datetime import datetime
from typing import Any

import httpx
from loguru import logger
from pydantic import BaseModel, Field

from .base import ConfigItem, ConfigProvider, ProviderConfig


# ============================================================================
# Nacos 配置
# ============================================================================


class NacosConfig(ProviderConfig):
    """Nacos 配置"""

    server_addr: str = Field(description="Nacos 服务器地址")
    namespace: str = Field(default="public", description="命名空间")
    group: str = Field(default="DEFAULT_GROUP", description="配置分组")
    username: str = Field(default="", description="用户名")
    password: str = Field(default="", description="密码")
    access_key: str = Field(default="", description="Access Key (阿里云)")
    secret_key: str = Field(default="", description="Secret Key (阿里云)")


# ============================================================================
# Nacos 配置提供者
# ============================================================================


class NacosProvider(ConfigProvider):
    """Nacos 配置提供者

    支持：
    - 配置读取和写入
    - 配置监听（长轮询）
    - 多命名空间和分组
    - 阿里云 ACM 兼容
    """

    def __init__(self, config: NacosConfig):
        """初始化 Nacos 提供者

        Args:
            config: Nacos 配置
        """
        super().__init__(config)
        self.nacos_config = config
        self._client: httpx.AsyncClient | None = None
        self._access_token: str | None = None
        self._token_expire_time: datetime | None = None
        self._listening_configs: dict[str, str] = {}  # key -> md5

    @property
    def _base_url(self) -> str:
        """基础 URL"""
        addr = self.nacos_config.server_addr
        if not addr.startswith("http"):
            addr = f"http://{addr}"
        return addr.rstrip("/")

    # ========================================================================
    # 连接管理
    # ========================================================================

    async def _connect(self) -> bool:
        """连接到 Nacos"""
        self._client = httpx.AsyncClient(timeout=self.config.timeout)

        # 如果配置了用户名密码，获取 token
        if self.nacos_config.username and self.nacos_config.password:
            return await self._login()

        # 检查服务器是否可用
        return await self._health_check()

    async def _disconnect(self) -> None:
        """断开连接"""
        if self._client:
            await self._client.aclose()
            self._client = None
        self._access_token = None

    async def _login(self) -> bool:
        """登录获取 token"""
        if not self._client:
            return False

        try:
            response = await self._client.post(
                f"{self._base_url}/nacos/v1/auth/login",
                data={
                    "username": self.nacos_config.username,
                    "password": self.nacos_config.password,
                },
            )

            if response.status_code == 200:
                data = response.json()
                self._access_token = data.get("accessToken")
                ttl = data.get("tokenTtl", 18000)
                self._token_expire_time = datetime.now()
                logger.debug(f"Nacos 登录成功, token TTL: {ttl}s")
                return True
            else:
                logger.error(f"Nacos 登录失败: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Nacos 登录异常: {e}")
            return False

    async def _ensure_token(self) -> bool:
        """确保 token 有效"""
        if not self.nacos_config.username:
            return True

        if self._access_token and self._token_expire_time:
            # 检查是否即将过期（提前 5 分钟刷新）
            age = (datetime.now() - self._token_expire_time).total_seconds()
            if age < 17700:  # 18000 - 300
                return True

        return await self._login()

    def _get_headers(self) -> dict[str, str]:
        """获取请求头"""
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        if self._access_token:
            headers["accessToken"] = self._access_token
        return headers

    # ========================================================================
    # 配置操作
    # ========================================================================

    async def _get(self, key: str) -> ConfigItem | None:
        """获取配置"""
        if not self._client:
            return None

        await self._ensure_token()

        try:
            response = await self._client.get(
                f"{self._base_url}/nacos/v1/cs/configs",
                params={
                    "dataId": key,
                    "group": self.nacos_config.group,
                    "tenant": self.nacos_config.namespace,
                },
                headers=self._get_headers(),
            )

            if response.status_code == 200:
                content = response.text

                # 尝试解析 JSON
                try:
                    value = json.loads(content)
                    content_type = "json"
                except json.JSONDecodeError:
                    value = content
                    content_type = "text"

                # 计算 MD5
                md5 = hashlib.md5(content.encode()).hexdigest()

                return ConfigItem(
                    key=key,
                    value=value,
                    version=md5,
                    content_type=content_type,
                )

            elif response.status_code == 404:
                return None
            else:
                logger.error(f"Nacos 获取配置失败: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Nacos 获取配置异常: {e}")
            return None

    async def _set(self, key: str, value: Any, content_type: str = "json") -> bool:
        """设置配置"""
        if not self._client:
            return False

        await self._ensure_token()

        # 序列化值
        if content_type == "json" and not isinstance(value, str):
            content = json.dumps(value, ensure_ascii=False)
        else:
            content = str(value)

        try:
            response = await self._client.post(
                f"{self._base_url}/nacos/v1/cs/configs",
                data={
                    "dataId": key,
                    "group": self.nacos_config.group,
                    "tenant": self.nacos_config.namespace,
                    "content": content,
                    "type": content_type,
                },
                headers=self._get_headers(),
            )

            if response.status_code == 200 and response.text == "true":
                logger.debug(f"Nacos 配置发布成功: {key}")
                return True
            else:
                logger.error(f"Nacos 配置发布失败: {response.status_code}, {response.text}")
                return False

        except Exception as e:
            logger.error(f"Nacos 配置发布异常: {e}")
            return False

    async def _delete(self, key: str) -> bool:
        """删除配置"""
        if not self._client:
            return False

        await self._ensure_token()

        try:
            response = await self._client.delete(
                f"{self._base_url}/nacos/v1/cs/configs",
                params={
                    "dataId": key,
                    "group": self.nacos_config.group,
                    "tenant": self.nacos_config.namespace,
                },
                headers=self._get_headers(),
            )

            if response.status_code == 200 and response.text == "true":
                logger.debug(f"Nacos 配置删除成功: {key}")
                return True
            else:
                logger.error(f"Nacos 配置删除失败: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Nacos 配置删除异常: {e}")
            return False

    async def _list(self, prefix: str = "") -> list[str]:
        """列出配置键"""
        if not self._client:
            return []

        await self._ensure_token()

        try:
            response = await self._client.get(
                f"{self._base_url}/nacos/v1/cs/configs",
                params={
                    "dataId": f"{prefix}*" if prefix else "*",
                    "group": self.nacos_config.group,
                    "tenant": self.nacos_config.namespace,
                    "pageNo": 1,
                    "pageSize": 1000,
                    "search": "blur",
                },
                headers=self._get_headers(),
            )

            if response.status_code == 200:
                data = response.json()
                items = data.get("pageItems", [])
                return [item["dataId"] for item in items]
            else:
                logger.error(f"Nacos 列出配置失败: {response.status_code}")
                return []

        except Exception as e:
            logger.error(f"Nacos 列出配置异常: {e}")
            return []

    async def _health_check(self) -> bool:
        """健康检查"""
        if not self._client:
            return False

        try:
            response = await self._client.get(
                f"{self._base_url}/nacos/v1/console/health/liveness",
            )
            return response.status_code == 200

        except Exception:
            return False

    # ========================================================================
    # 配置监听
    # ========================================================================

    async def _check_updates(self) -> None:
        """检查配置更新（使用长轮询）"""
        if not self._client or not self._listening_configs:
            return

        await self._ensure_token()

        # 构建监听字符串
        listening_str = ""
        for key, md5 in self._listening_configs.items():
            listening_str += f"{key}\x02{self.nacos_config.group}\x02{md5}\x02{self.nacos_config.namespace}\x01"

        try:
            response = await self._client.post(
                f"{self._base_url}/nacos/v1/cs/configs/listener",
                data={"Listening-Configs": listening_str},
                headers={
                    **self._get_headers(),
                    "Long-Pulling-Timeout": str(int(self.config.watch_interval * 1000)),
                },
                timeout=self.config.watch_interval + 5,
            )

            if response.status_code == 200 and response.text:
                # 解析变更的配置
                changed_configs = self._parse_listener_response(response.text)

                for key in changed_configs:
                    # 重新获取配置
                    item = await self._get(key)
                    if item:
                        self._update_cache(key, item)
                        self._listening_configs[key] = item.version
                        logger.info(f"Nacos 配置已更新: {key}")

        except asyncio.TimeoutError:
            # 长轮询超时是正常的
            pass
        except Exception as e:
            logger.error(f"Nacos 监听异常: {e}")

    def _parse_listener_response(self, response: str) -> list[str]:
        """解析监听响应

        Args:
            response: 响应内容

        Returns:
            变更的配置键列表
        """
        changed = []
        if not response:
            return changed

        # 响应格式: dataId%02group%02tenant%01
        items = response.split("\x01")
        for item in items:
            if not item:
                continue
            parts = item.split("\x02")
            if len(parts) >= 1:
                changed.append(parts[0])

        return changed

    async def watch(self, key: str) -> None:
        """监听配置变更

        Args:
            key: 配置键
        """
        # 获取当前配置的 MD5
        item = await self._get(key)
        if item:
            self._listening_configs[key] = item.version
            self._update_cache(key, item)
        else:
            self._listening_configs[key] = ""

        logger.debug(f"开始监听 Nacos 配置: {key}")

    async def unwatch(self, key: str) -> None:
        """取消监听

        Args:
            key: 配置键
        """
        if key in self._listening_configs:
            del self._listening_configs[key]
            logger.debug(f"取消监听 Nacos 配置: {key}")


# ============================================================================
# 工厂函数
# ============================================================================


def create_nacos_provider(
    server_addr: str,
    namespace: str = "public",
    group: str = "DEFAULT_GROUP",
    username: str = "",
    password: str = "",
    **kwargs,
) -> NacosProvider:
    """创建 Nacos 配置提供者

    Args:
        server_addr: Nacos 服务器地址
        namespace: 命名空间
        group: 配置分组
        username: 用户名
        password: 密码
        **kwargs: 其他配置参数

    Returns:
        Nacos 配置提供者实例
    """
    config = NacosConfig(
        name="nacos",
        server_addr=server_addr,
        namespace=namespace,
        group=group,
        username=username,
        password=password,
        **kwargs,
    )
    return NacosProvider(config)
