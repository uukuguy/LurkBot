"""配置提供者基类

定义配置提供者的统一接口，支持多种配置中心集成。
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable

from loguru import logger
from pydantic import BaseModel, Field


# ============================================================================
# 配置提供者状态
# ============================================================================


class ProviderStatus(str, Enum):
    """配置提供者状态"""

    DISCONNECTED = "disconnected"  # 未连接
    CONNECTING = "connecting"  # 连接中
    CONNECTED = "connected"  # 已连接
    ERROR = "error"  # 错误
    DEGRADED = "degraded"  # 降级（使用缓存）


# ============================================================================
# 配置数据模型
# ============================================================================


class ConfigItem(BaseModel):
    """配置项"""

    key: str = Field(description="配置键")
    value: Any = Field(description="配置值")
    version: str = Field(default="", description="版本号")
    content_type: str = Field(default="json", description="内容类型")
    last_modified: datetime = Field(default_factory=datetime.now, description="最后修改时间")
    metadata: dict[str, Any] = Field(default_factory=dict, description="元数据")


class ProviderConfig(BaseModel):
    """配置提供者配置"""

    name: str = Field(description="提供者名称")
    enabled: bool = Field(default=True, description="是否启用")
    priority: int = Field(default=0, description="优先级")
    timeout: float = Field(default=5.0, description="超时时间（秒）")
    retry_count: int = Field(default=3, description="重试次数")
    retry_delay: float = Field(default=1.0, description="重试延迟（秒）")
    cache_enabled: bool = Field(default=True, description="是否启用缓存")
    cache_ttl: int = Field(default=300, description="缓存 TTL（秒）")
    watch_enabled: bool = Field(default=True, description="是否启用监听")
    watch_interval: float = Field(default=30.0, description="监听间隔（秒）")


# ============================================================================
# 配置变更回调
# ============================================================================

ConfigChangeCallback = Callable[[str, Any, Any], None]  # key, old_value, new_value


# ============================================================================
# 配置提供者基类
# ============================================================================


class ConfigProvider(ABC):
    """配置提供者基类

    定义配置提供者的统一接口，支持：
    - 配置读取和写入
    - 配置监听和自动刷新
    - 本地缓存和故障转移
    - 健康检查
    """

    def __init__(self, config: ProviderConfig):
        """初始化配置提供者

        Args:
            config: 提供者配置
        """
        self.config = config
        self._status = ProviderStatus.DISCONNECTED
        self._cache: dict[str, ConfigItem] = {}
        self._cache_timestamps: dict[str, datetime] = {}
        self._callbacks: list[ConfigChangeCallback] = []
        self._watch_task: asyncio.Task | None = None
        self._connected = False

    @property
    def name(self) -> str:
        """提供者名称"""
        return self.config.name

    @property
    def status(self) -> ProviderStatus:
        """提供者状态"""
        return self._status

    @property
    def is_connected(self) -> bool:
        """是否已连接"""
        return self._connected and self._status == ProviderStatus.CONNECTED

    # ========================================================================
    # 抽象方法（子类必须实现）
    # ========================================================================

    @abstractmethod
    async def _connect(self) -> bool:
        """连接到配置中心

        Returns:
            是否连接成功
        """
        pass

    @abstractmethod
    async def _disconnect(self) -> None:
        """断开连接"""
        pass

    @abstractmethod
    async def _get(self, key: str) -> ConfigItem | None:
        """从配置中心获取配置

        Args:
            key: 配置键

        Returns:
            配置项，不存在返回 None
        """
        pass

    @abstractmethod
    async def _set(self, key: str, value: Any, content_type: str = "json") -> bool:
        """设置配置到配置中心

        Args:
            key: 配置键
            value: 配置值
            content_type: 内容类型

        Returns:
            是否设置成功
        """
        pass

    @abstractmethod
    async def _delete(self, key: str) -> bool:
        """从配置中心删除配置

        Args:
            key: 配置键

        Returns:
            是否删除成功
        """
        pass

    @abstractmethod
    async def _list(self, prefix: str = "") -> list[str]:
        """列出配置键

        Args:
            prefix: 键前缀

        Returns:
            配置键列表
        """
        pass

    @abstractmethod
    async def _health_check(self) -> bool:
        """健康检查

        Returns:
            是否健康
        """
        pass

    # ========================================================================
    # 公共方法
    # ========================================================================

    async def connect(self) -> bool:
        """连接到配置中心

        Returns:
            是否连接成功
        """
        if self._connected:
            return True

        self._status = ProviderStatus.CONNECTING
        logger.info(f"正在连接配置中心: {self.name}")

        for attempt in range(self.config.retry_count):
            try:
                success = await asyncio.wait_for(
                    self._connect(),
                    timeout=self.config.timeout,
                )
                if success:
                    self._connected = True
                    self._status = ProviderStatus.CONNECTED
                    logger.info(f"配置中心连接成功: {self.name}")

                    # 启动监听
                    if self.config.watch_enabled:
                        self._start_watch()

                    return True

            except asyncio.TimeoutError:
                logger.warning(f"配置中心连接超时: {self.name} (尝试 {attempt + 1}/{self.config.retry_count})")
            except Exception as e:
                logger.error(f"配置中心连接失败: {self.name}, 错误: {e}")

            if attempt < self.config.retry_count - 1:
                await asyncio.sleep(self.config.retry_delay)

        self._status = ProviderStatus.ERROR
        logger.error(f"配置中心连接失败: {self.name}")
        return False

    async def disconnect(self) -> None:
        """断开连接"""
        if not self._connected:
            return

        logger.info(f"正在断开配置中心连接: {self.name}")

        # 停止监听
        self._stop_watch()

        try:
            await self._disconnect()
        except Exception as e:
            logger.error(f"断开连接时出错: {e}")

        self._connected = False
        self._status = ProviderStatus.DISCONNECTED
        logger.info(f"配置中心已断开: {self.name}")

    async def get(self, key: str, default: Any = None) -> Any:
        """获取配置值

        Args:
            key: 配置键
            default: 默认值

        Returns:
            配置值
        """
        # 尝试从缓存获取
        if self.config.cache_enabled:
            cached = self._get_from_cache(key)
            if cached is not None:
                return cached.value

        # 从配置中心获取
        if self.is_connected:
            try:
                item = await asyncio.wait_for(
                    self._get(key),
                    timeout=self.config.timeout,
                )
                if item:
                    self._update_cache(key, item)
                    return item.value
            except asyncio.TimeoutError:
                logger.warning(f"获取配置超时: {key}")
            except Exception as e:
                logger.error(f"获取配置失败: {key}, 错误: {e}")

        # 降级到缓存
        if self.config.cache_enabled:
            cached = self._get_from_cache(key, ignore_ttl=True)
            if cached is not None:
                self._status = ProviderStatus.DEGRADED
                logger.warning(f"使用缓存配置: {key}")
                return cached.value

        return default

    async def set(self, key: str, value: Any, content_type: str = "json") -> bool:
        """设置配置值

        Args:
            key: 配置键
            value: 配置值
            content_type: 内容类型

        Returns:
            是否设置成功
        """
        if not self.is_connected:
            logger.error(f"配置中心未连接: {self.name}")
            return False

        try:
            success = await asyncio.wait_for(
                self._set(key, value, content_type),
                timeout=self.config.timeout,
            )
            if success:
                # 更新缓存
                item = ConfigItem(
                    key=key,
                    value=value,
                    content_type=content_type,
                )
                self._update_cache(key, item)
                logger.debug(f"配置设置成功: {key}")
            return success

        except asyncio.TimeoutError:
            logger.error(f"设置配置超时: {key}")
            return False
        except Exception as e:
            logger.error(f"设置配置失败: {key}, 错误: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """删除配置

        Args:
            key: 配置键

        Returns:
            是否删除成功
        """
        if not self.is_connected:
            logger.error(f"配置中心未连接: {self.name}")
            return False

        try:
            success = await asyncio.wait_for(
                self._delete(key),
                timeout=self.config.timeout,
            )
            if success:
                # 清除缓存
                self._remove_from_cache(key)
                logger.debug(f"配置删除成功: {key}")
            return success

        except asyncio.TimeoutError:
            logger.error(f"删除配置超时: {key}")
            return False
        except Exception as e:
            logger.error(f"删除配置失败: {key}, 错误: {e}")
            return False

    async def list_keys(self, prefix: str = "") -> list[str]:
        """列出配置键

        Args:
            prefix: 键前缀

        Returns:
            配置键列表
        """
        if not self.is_connected:
            # 从缓存返回
            return [k for k in self._cache.keys() if k.startswith(prefix)]

        try:
            return await asyncio.wait_for(
                self._list(prefix),
                timeout=self.config.timeout,
            )
        except Exception as e:
            logger.error(f"列出配置键失败: {e}")
            return [k for k in self._cache.keys() if k.startswith(prefix)]

    async def health_check(self) -> bool:
        """健康检查

        Returns:
            是否健康
        """
        try:
            return await asyncio.wait_for(
                self._health_check(),
                timeout=self.config.timeout,
            )
        except Exception:
            return False

    # ========================================================================
    # 回调管理
    # ========================================================================

    def add_callback(self, callback: ConfigChangeCallback) -> None:
        """添加配置变更回调

        Args:
            callback: 回调函数
        """
        self._callbacks.append(callback)

    def remove_callback(self, callback: ConfigChangeCallback) -> None:
        """移除配置变更回调

        Args:
            callback: 回调函数
        """
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    def _notify_change(self, key: str, old_value: Any, new_value: Any) -> None:
        """通知配置变更

        Args:
            key: 配置键
            old_value: 旧值
            new_value: 新值
        """
        for callback in self._callbacks:
            try:
                callback(key, old_value, new_value)
            except Exception as e:
                logger.error(f"配置变更回调异常: {e}")

    # ========================================================================
    # 缓存管理
    # ========================================================================

    def _get_from_cache(self, key: str, ignore_ttl: bool = False) -> ConfigItem | None:
        """从缓存获取配置

        Args:
            key: 配置键
            ignore_ttl: 是否忽略 TTL

        Returns:
            配置项
        """
        if key not in self._cache:
            return None

        if not ignore_ttl:
            timestamp = self._cache_timestamps.get(key)
            if timestamp:
                age = (datetime.now() - timestamp).total_seconds()
                if age > self.config.cache_ttl:
                    return None

        return self._cache[key]

    def _update_cache(self, key: str, item: ConfigItem) -> None:
        """更新缓存

        Args:
            key: 配置键
            item: 配置项
        """
        old_item = self._cache.get(key)
        self._cache[key] = item
        self._cache_timestamps[key] = datetime.now()

        # 通知变更
        if old_item and old_item.value != item.value:
            self._notify_change(key, old_item.value, item.value)

    def _remove_from_cache(self, key: str) -> None:
        """从缓存移除

        Args:
            key: 配置键
        """
        if key in self._cache:
            del self._cache[key]
        if key in self._cache_timestamps:
            del self._cache_timestamps[key]

    def clear_cache(self) -> None:
        """清空缓存"""
        self._cache.clear()
        self._cache_timestamps.clear()

    # ========================================================================
    # 监听管理
    # ========================================================================

    def _start_watch(self) -> None:
        """启动配置监听"""
        if self._watch_task is not None:
            return

        try:
            loop = asyncio.get_running_loop()
            self._watch_task = loop.create_task(self._watch_loop())
            logger.debug(f"配置监听已启动: {self.name}")
        except RuntimeError:
            logger.warning("没有运行中的事件循环，配置监听将不会启动")

    def _stop_watch(self) -> None:
        """停止配置监听"""
        if self._watch_task is not None:
            self._watch_task.cancel()
            self._watch_task = None
            logger.debug(f"配置监听已停止: {self.name}")

    async def _watch_loop(self) -> None:
        """监听循环"""
        try:
            while self._connected:
                await self._check_updates()
                await asyncio.sleep(self.config.watch_interval)
        except asyncio.CancelledError:
            logger.debug(f"配置监听循环已取消: {self.name}")

    async def _check_updates(self) -> None:
        """检查配置更新"""
        for key in list(self._cache.keys()):
            try:
                item = await self._get(key)
                if item:
                    cached = self._cache.get(key)
                    if cached and cached.version != item.version:
                        self._update_cache(key, item)
                        logger.info(f"配置已更新: {key}")
            except Exception as e:
                logger.error(f"检查配置更新失败: {key}, 错误: {e}")


# ============================================================================
# 本地文件配置提供者
# ============================================================================


class LocalFileProvider(ConfigProvider):
    """本地文件配置提供者

    从本地文件系统读取配置，支持 JSON 格式。
    """

    def __init__(
        self,
        config: ProviderConfig,
        config_dir: Path,
    ):
        """初始化本地文件提供者

        Args:
            config: 提供者配置
            config_dir: 配置目录
        """
        super().__init__(config)
        self.config_dir = config_dir
        self._file_versions: dict[str, str] = {}

    async def _connect(self) -> bool:
        """连接（检查目录是否存在）"""
        return self.config_dir.exists()

    async def _disconnect(self) -> None:
        """断开连接"""
        pass

    async def _get(self, key: str) -> ConfigItem | None:
        """获取配置"""
        import json

        file_path = self.config_dir / f"{key}.json"
        if not file_path.exists():
            return None

        try:
            with open(file_path) as f:
                data = json.load(f)

            # 计算版本（文件修改时间）
            mtime = file_path.stat().st_mtime
            version = str(mtime)

            return ConfigItem(
                key=key,
                value=data,
                version=version,
                content_type="json",
                last_modified=datetime.fromtimestamp(mtime),
            )
        except Exception as e:
            logger.error(f"读取配置文件失败: {file_path}, 错误: {e}")
            return None

    async def _set(self, key: str, value: Any, content_type: str = "json") -> bool:
        """设置配置"""
        import json

        file_path = self.config_dir / f"{key}.json"

        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            with open(file_path, "w") as f:
                json.dump(value, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"写入配置文件失败: {file_path}, 错误: {e}")
            return False

    async def _delete(self, key: str) -> bool:
        """删除配置"""
        file_path = self.config_dir / f"{key}.json"

        try:
            if file_path.exists():
                file_path.unlink()
            return True
        except Exception as e:
            logger.error(f"删除配置文件失败: {file_path}, 错误: {e}")
            return False

    async def _list(self, prefix: str = "") -> list[str]:
        """列出配置键"""
        if not self.config_dir.exists():
            return []

        keys = []
        for file_path in self.config_dir.glob("*.json"):
            key = file_path.stem
            if key.startswith(prefix):
                keys.append(key)
        return keys

    async def _health_check(self) -> bool:
        """健康检查"""
        return self.config_dir.exists()
