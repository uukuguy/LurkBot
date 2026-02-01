"""动态配置系统

支持运行时配置更新、配置热加载、多来源配置合并和配置变更通知。
"""

from __future__ import annotations

import asyncio
import copy
import hashlib
import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, TypeVar

from loguru import logger
from pydantic import BaseModel, Field
from watchdog.events import FileModifiedEvent, FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

# ============================================================================
# 配置来源和事件类型
# ============================================================================


class ConfigSource(str, Enum):
    """配置来源类型"""

    FILE = "file"  # 本地文件
    ENV = "env"  # 环境变量
    REMOTE = "remote"  # 远程配置中心
    DATABASE = "database"  # 数据库
    OVERRIDE = "override"  # 运行时覆盖
    DEFAULT = "default"  # 默认值


class ConfigEventType(str, Enum):
    """配置事件类型"""

    LOADED = "loaded"  # 配置加载
    UPDATED = "updated"  # 配置更新
    DELETED = "deleted"  # 配置删除
    ERROR = "error"  # 配置错误
    ROLLBACK = "rollback"  # 配置回滚
    VALIDATED = "validated"  # 配置验证


# ============================================================================
# 配置数据模型
# ============================================================================


class ConfigVersion(BaseModel):
    """配置版本信息"""

    version: str = Field(description="版本号")
    hash: str = Field(description="配置哈希值")
    timestamp: datetime = Field(default_factory=datetime.now, description="版本时间")
    source: ConfigSource = Field(description="配置来源")
    author: str = Field(default="system", description="修改者")
    message: str = Field(default="", description="版本说明")


class ConfigEntry(BaseModel):
    """配置条目"""

    key: str = Field(description="配置键")
    value: Any = Field(description="配置值")
    source: ConfigSource = Field(description="配置来源")
    priority: int = Field(default=0, description="优先级（高覆盖低）")
    timestamp: datetime = Field(default_factory=datetime.now, description="更新时间")
    metadata: dict[str, Any] = Field(default_factory=dict, description="元数据")


class ConfigEvent(BaseModel):
    """配置变更事件"""

    event_type: ConfigEventType = Field(description="事件类型")
    key: str | None = Field(default=None, description="配置键")
    old_value: Any = Field(default=None, description="旧值")
    new_value: Any = Field(default=None, description="新值")
    source: ConfigSource = Field(description="配置来源")
    timestamp: datetime = Field(default_factory=datetime.now, description="事件时间")
    version: str | None = Field(default=None, description="配置版本")
    error: str | None = Field(default=None, description="错误信息")
    metadata: dict[str, Any] = Field(default_factory=dict, description="事件元数据")


class ConfigSnapshot(BaseModel):
    """配置快照"""

    version: str = Field(description="版本号")
    hash: str = Field(description="配置哈希")
    values: dict[str, Any] = Field(description="配置值")
    sources: dict[str, ConfigSource] = Field(description="各配置项来源")
    timestamp: datetime = Field(default_factory=datetime.now, description="快照时间")
    metadata: dict[str, Any] = Field(default_factory=dict, description="元数据")


# ============================================================================
# 配置验证器
# ============================================================================

T = TypeVar("T")
ConfigValidator = Callable[[str, Any], tuple[bool, str | None]]


class ConfigValidatorRegistry:
    """配置验证器注册表"""

    def __init__(self) -> None:
        self._validators: dict[str, list[ConfigValidator]] = {}
        self._global_validators: list[ConfigValidator] = []

    def register(self, key_pattern: str, validator: ConfigValidator) -> None:
        """注册配置验证器

        Args:
            key_pattern: 配置键模式（支持 * 通配符）
            validator: 验证函数，返回 (是否有效, 错误信息)
        """
        if key_pattern not in self._validators:
            self._validators[key_pattern] = []
        self._validators[key_pattern].append(validator)

    def register_global(self, validator: ConfigValidator) -> None:
        """注册全局验证器"""
        self._global_validators.append(validator)

    def validate(self, key: str, value: Any) -> tuple[bool, list[str]]:
        """验证配置值

        Args:
            key: 配置键
            value: 配置值

        Returns:
            (是否有效, 错误信息列表)
        """
        errors = []

        # 运行全局验证器
        for validator in self._global_validators:
            try:
                is_valid, error = validator(key, value)
                if not is_valid and error:
                    errors.append(error)
            except Exception as e:
                errors.append(f"验证器异常: {e}")

        # 运行匹配的验证器
        for pattern, validators in self._validators.items():
            if self._match_pattern(key, pattern):
                for validator in validators:
                    try:
                        is_valid, error = validator(key, value)
                        if not is_valid and error:
                            errors.append(error)
                    except Exception as e:
                        errors.append(f"验证器异常: {e}")

        return len(errors) == 0, errors

    def _match_pattern(self, key: str, pattern: str) -> bool:
        """匹配配置键模式

        Args:
            key: 配置键
            pattern: 模式（支持 * 通配符）

        Returns:
            是否匹配
        """
        if pattern == "*":
            return True
        if "*" not in pattern:
            return key == pattern

        # 简单通配符匹配
        parts = pattern.split("*")
        if len(parts) == 2:
            prefix, suffix = parts
            return key.startswith(prefix) and key.endswith(suffix)

        return False


# ============================================================================
# 配置存储
# ============================================================================


class ConfigStore:
    """配置存储"""

    def __init__(self) -> None:
        self._entries: dict[str, ConfigEntry] = {}
        self._versions: list[ConfigVersion] = []
        self._snapshots: dict[str, ConfigSnapshot] = {}
        self._max_versions = 100
        self._max_snapshots = 20
        self._lock = asyncio.Lock()

    async def get(self, key: str, default: Any = None) -> Any:
        """获取配置值

        Args:
            key: 配置键
            default: 默认值

        Returns:
            配置值
        """
        entry = self._entries.get(key)
        return entry.value if entry else default

    async def set(
        self,
        key: str,
        value: Any,
        source: ConfigSource = ConfigSource.OVERRIDE,
        priority: int = 100,
        metadata: dict[str, Any] | None = None,
    ) -> ConfigEntry:
        """设置配置值

        Args:
            key: 配置键
            value: 配置值
            source: 配置来源
            priority: 优先级
            metadata: 元数据

        Returns:
            配置条目
        """
        async with self._lock:
            entry = ConfigEntry(
                key=key,
                value=value,
                source=source,
                priority=priority,
                metadata=metadata or {},
            )
            self._entries[key] = entry
            return entry

    async def delete(self, key: str) -> bool:
        """删除配置

        Args:
            key: 配置键

        Returns:
            是否删除成功
        """
        async with self._lock:
            if key in self._entries:
                del self._entries[key]
                return True
            return False

    async def get_all(self) -> dict[str, Any]:
        """获取所有配置值

        Returns:
            配置字典
        """
        return {key: entry.value for key, entry in self._entries.items()}

    async def get_entries(self) -> dict[str, ConfigEntry]:
        """获取所有配置条目

        Returns:
            配置条目字典
        """
        return dict(self._entries)

    async def create_snapshot(self, version: str, metadata: dict[str, Any] | None = None) -> ConfigSnapshot:
        """创建配置快照

        Args:
            version: 版本号
            metadata: 元数据

        Returns:
            配置快照
        """
        async with self._lock:
            values = await self.get_all()
            sources = {key: entry.source for key, entry in self._entries.items()}

            # 计算哈希
            config_hash = self._compute_hash(values)

            snapshot = ConfigSnapshot(
                version=version,
                hash=config_hash,
                values=copy.deepcopy(values),
                sources=sources,
                metadata=metadata or {},
            )

            # 保存快照
            self._snapshots[version] = snapshot

            # 清理旧快照
            if len(self._snapshots) > self._max_snapshots:
                oldest = sorted(self._snapshots.keys())[0]
                del self._snapshots[oldest]

            # 记录版本
            version_info = ConfigVersion(
                version=version,
                hash=config_hash,
                source=ConfigSource.OVERRIDE,
            )
            self._versions.append(version_info)

            # 清理旧版本
            if len(self._versions) > self._max_versions:
                self._versions = self._versions[-self._max_versions :]

            return snapshot

    async def restore_snapshot(self, version: str) -> bool:
        """恢复配置快照

        Args:
            version: 版本号

        Returns:
            是否恢复成功
        """
        if version not in self._snapshots:
            return False

        async with self._lock:
            snapshot = self._snapshots[version]

            # 清空当前配置
            self._entries.clear()

            # 恢复快照配置
            for key, value in snapshot.values.items():
                source = snapshot.sources.get(key, ConfigSource.OVERRIDE)
                self._entries[key] = ConfigEntry(
                    key=key,
                    value=value,
                    source=source,
                )

            return True

    async def get_versions(self) -> list[ConfigVersion]:
        """获取版本历史

        Returns:
            版本列表
        """
        return list(self._versions)

    async def get_snapshot(self, version: str) -> ConfigSnapshot | None:
        """获取配置快照

        Args:
            version: 版本号

        Returns:
            配置快照
        """
        return self._snapshots.get(version)

    def _compute_hash(self, values: dict[str, Any]) -> str:
        """计算配置哈希

        Args:
            values: 配置值

        Returns:
            哈希值
        """
        content = json.dumps(values, sort_keys=True, default=str)
        return hashlib.sha256(content.encode()).hexdigest()[:16]


# ============================================================================
# 配置文件监控
# ============================================================================


class ConfigFileHandler(FileSystemEventHandler):
    """配置文件变更处理器"""

    def __init__(
        self,
        on_change: Callable[[Path], None],
        debounce_seconds: float = 1.0,
    ):
        """初始化处理器

        Args:
            on_change: 文件变更回调
            debounce_seconds: 防抖时间（秒）
        """
        super().__init__()
        self.on_change = on_change
        self.debounce_seconds = debounce_seconds
        self._pending_files: dict[str, float] = {}
        self._lock = asyncio.Lock()

    def on_modified(self, event: FileSystemEvent) -> None:
        """文件修改事件

        Args:
            event: 文件系统事件
        """
        if event.is_directory:
            return

        path = Path(event.src_path)
        if path.suffix not in [".json", ".yaml", ".yml", ".toml"]:
            return

        self._pending_files[str(path)] = datetime.now().timestamp()
        logger.debug(f"检测到配置文件变化: {path}")

    async def process_pending(self) -> None:
        """处理待处理的文件变更"""
        if not self._pending_files:
            return

        now = datetime.now().timestamp()
        to_process = []

        async with self._lock:
            for file_path, timestamp in list(self._pending_files.items()):
                if now - timestamp >= self.debounce_seconds:
                    to_process.append(file_path)
                    del self._pending_files[file_path]

        for file_path in to_process:
            try:
                self.on_change(Path(file_path))
            except Exception as e:
                logger.error(f"处理配置文件变更失败: {file_path}, 错误: {e}")


class ConfigWatcher:
    """配置文件监控器"""

    def __init__(self, debounce_seconds: float = 1.0):
        """初始化监控器

        Args:
            debounce_seconds: 防抖时间（秒）
        """
        self.debounce_seconds = debounce_seconds
        self._observer: Observer | None = None
        self._handlers: dict[str, ConfigFileHandler] = {}
        self._callbacks: list[Callable[[Path], None]] = []
        self._running = False
        self._process_task: asyncio.Task | None = None

    def add_callback(self, callback: Callable[[Path], None]) -> None:
        """添加文件变更回调

        Args:
            callback: 回调函数
        """
        self._callbacks.append(callback)

    def watch(self, path: Path) -> None:
        """添加监控路径

        Args:
            path: 监控路径
        """
        if not path.exists():
            logger.warning(f"配置路径不存在: {path}")
            return

        path_str = str(path)
        if path_str in self._handlers:
            return

        def on_change(file_path: Path) -> None:
            for callback in self._callbacks:
                try:
                    callback(file_path)
                except Exception as e:
                    logger.error(f"配置变更回调失败: {e}")

        handler = ConfigFileHandler(on_change, self.debounce_seconds)
        self._handlers[path_str] = handler

        if self._running and self._observer:
            watch_path = str(path) if path.is_dir() else str(path.parent)
            self._observer.schedule(handler, watch_path, recursive=path.is_dir())
            logger.info(f"添加配置监控: {path}")

    def start(self) -> None:
        """启动监控"""
        if self._running:
            return

        logger.info("启动配置文件监控...")

        self._observer = Observer()

        for path_str, handler in self._handlers.items():
            path = Path(path_str)
            watch_path = str(path) if path.is_dir() else str(path.parent)
            self._observer.schedule(handler, watch_path, recursive=path.is_dir())

        self._observer.start()
        self._running = True

        try:
            loop = asyncio.get_running_loop()
            self._process_task = loop.create_task(self._process_loop())
        except RuntimeError:
            logger.warning("没有运行中的事件循环，配置监控处理任务将不会启动")

        logger.info("配置文件监控已启动")

    def stop(self) -> None:
        """停止监控"""
        if not self._running:
            return

        logger.info("停止配置文件监控...")

        if self._observer:
            self._observer.stop()
            self._observer.join()
            self._observer = None

        if self._process_task:
            self._process_task.cancel()
            self._process_task = None

        self._running = False
        logger.info("配置文件监控已停止")

    async def _process_loop(self) -> None:
        """处理循环"""
        try:
            while self._running:
                for handler in self._handlers.values():
                    await handler.process_pending()
                await asyncio.sleep(0.5)
        except asyncio.CancelledError:
            logger.debug("配置监控处理循环已取消")


# ============================================================================
# 动态配置管理器
# ============================================================================


ConfigChangeHandler = Callable[[ConfigEvent], None]


class DynamicConfigManager:
    """动态配置管理器

    支持：
    - 多来源配置合并（文件、环境变量、远程、覆盖）
    - 配置热加载
    - 配置版本控制和回滚
    - 配置验证
    - 配置变更事件通知
    """

    def __init__(self, config_dir: Path | None = None):
        """初始化管理器

        Args:
            config_dir: 配置目录
        """
        self.config_dir = config_dir or Path.cwd() / "config"
        self._store = ConfigStore()
        self._validator_registry = ConfigValidatorRegistry()
        self._watcher = ConfigWatcher()
        self._event_handlers: list[ConfigChangeHandler] = []
        self._version_counter = 0
        self._initialized = False

        # 来源优先级（高覆盖低）
        self._source_priority = {
            ConfigSource.DEFAULT: 0,
            ConfigSource.FILE: 10,
            ConfigSource.ENV: 20,
            ConfigSource.DATABASE: 30,
            ConfigSource.REMOTE: 40,
            ConfigSource.OVERRIDE: 100,
        }

    async def initialize(self) -> None:
        """初始化配置管理器"""
        if self._initialized:
            return

        logger.info(f"初始化动态配置管理器, 配置目录: {self.config_dir}")

        # 加载默认配置
        await self._load_defaults()

        # 加载文件配置
        await self._load_from_files()

        # 加载环境变量配置
        await self._load_from_env()

        # 创建初始快照
        await self._store.create_snapshot(self._next_version(), {"type": "initial"})

        # 设置文件监控
        self._watcher.add_callback(self._on_config_file_changed)
        if self.config_dir.exists():
            self._watcher.watch(self.config_dir)

        self._initialized = True
        logger.info("动态配置管理器初始化完成")

    def start_watching(self) -> None:
        """启动配置监控"""
        self._watcher.start()

    def stop_watching(self) -> None:
        """停止配置监控"""
        self._watcher.stop()

    # ========================================================================
    # 配置读写
    # ========================================================================

    async def get(self, key: str, default: Any = None) -> Any:
        """获取配置值

        Args:
            key: 配置键（支持点号分隔的嵌套键，如 "server.port"）
            default: 默认值

        Returns:
            配置值
        """
        value = await self._store.get(key)
        if value is not None:
            return value

        # 尝试查找嵌套配置
        parts = key.split(".")
        if len(parts) > 1:
            parent = await self._store.get(parts[0])
            if isinstance(parent, dict):
                current = parent
                for part in parts[1:]:
                    if isinstance(current, dict) and part in current:
                        current = current[part]
                    else:
                        return default
                return current

        return default

    async def set(
        self,
        key: str,
        value: Any,
        source: ConfigSource = ConfigSource.OVERRIDE,
        validate: bool = True,
    ) -> bool:
        """设置配置值

        Args:
            key: 配置键
            value: 配置值
            source: 配置来源
            validate: 是否验证

        Returns:
            是否设置成功
        """
        # 验证配置
        if validate:
            is_valid, errors = self._validator_registry.validate(key, value)
            if not is_valid:
                logger.error(f"配置验证失败: {key} = {value}, 错误: {errors}")
                await self._emit_event(
                    ConfigEvent(
                        event_type=ConfigEventType.ERROR,
                        key=key,
                        new_value=value,
                        source=source,
                        error="; ".join(errors),
                    )
                )
                return False

        # 获取旧值
        old_value = await self._store.get(key)

        # 设置新值
        priority = self._source_priority.get(source, 0)
        await self._store.set(key, value, source, priority)

        # 发送变更事件
        await self._emit_event(
            ConfigEvent(
                event_type=ConfigEventType.UPDATED,
                key=key,
                old_value=old_value,
                new_value=value,
                source=source,
            )
        )

        logger.debug(f"配置更新: {key} = {value} (来源: {source.value})")
        return True

    async def delete(self, key: str) -> bool:
        """删除配置

        Args:
            key: 配置键

        Returns:
            是否删除成功
        """
        old_value = await self._store.get(key)
        if old_value is None:
            return False

        await self._store.delete(key)

        await self._emit_event(
            ConfigEvent(
                event_type=ConfigEventType.DELETED,
                key=key,
                old_value=old_value,
                source=ConfigSource.OVERRIDE,
            )
        )

        return True

    async def get_all(self) -> dict[str, Any]:
        """获取所有配置

        Returns:
            配置字典
        """
        return await self._store.get_all()

    # ========================================================================
    # 批量操作
    # ========================================================================

    async def update(
        self,
        values: dict[str, Any],
        source: ConfigSource = ConfigSource.OVERRIDE,
        validate: bool = True,
    ) -> dict[str, bool]:
        """批量更新配置

        Args:
            values: 配置字典
            source: 配置来源
            validate: 是否验证

        Returns:
            各配置键的更新结果
        """
        results = {}
        for key, value in values.items():
            results[key] = await self.set(key, value, source, validate)
        return results

    async def reload(self) -> bool:
        """重新加载配置

        Returns:
            是否重载成功
        """
        logger.info("重新加载配置...")

        # 创建当前快照（用于可能的回滚）
        old_version = self._next_version()
        await self._store.create_snapshot(old_version, {"type": "before_reload"})

        try:
            # 清空当前配置（保留 OVERRIDE 来源）
            entries = await self._store.get_entries()
            for key, entry in entries.items():
                if entry.source != ConfigSource.OVERRIDE:
                    await self._store.delete(key)

            # 重新加载各来源配置
            await self._load_defaults()
            await self._load_from_files()
            await self._load_from_env()

            # 创建新快照
            new_version = self._next_version()
            await self._store.create_snapshot(new_version, {"type": "reload"})

            await self._emit_event(
                ConfigEvent(
                    event_type=ConfigEventType.LOADED,
                    source=ConfigSource.FILE,
                    version=new_version,
                )
            )

            logger.info("配置重新加载完成")
            return True

        except Exception as e:
            logger.error(f"配置重载失败: {e}")

            # 回滚到之前的快照
            await self._store.restore_snapshot(old_version)

            await self._emit_event(
                ConfigEvent(
                    event_type=ConfigEventType.ERROR,
                    source=ConfigSource.FILE,
                    error=str(e),
                )
            )

            return False

    # ========================================================================
    # 版本控制
    # ========================================================================

    async def create_snapshot(self, message: str = "") -> str:
        """创建配置快照

        Args:
            message: 版本说明

        Returns:
            版本号
        """
        version = self._next_version()
        await self._store.create_snapshot(version, {"message": message})
        logger.info(f"创建配置快照: {version}")
        return version

    async def rollback(self, version: str) -> bool:
        """回滚到指定版本

        Args:
            version: 版本号

        Returns:
            是否回滚成功
        """
        snapshot = await self._store.get_snapshot(version)
        if not snapshot:
            logger.error(f"快照不存在: {version}")
            return False

        old_values = await self._store.get_all()
        success = await self._store.restore_snapshot(version)

        if success:
            await self._emit_event(
                ConfigEvent(
                    event_type=ConfigEventType.ROLLBACK,
                    old_value=old_values,
                    new_value=snapshot.values,
                    source=ConfigSource.OVERRIDE,
                    version=version,
                )
            )
            logger.info(f"配置回滚到版本: {version}")

        return success

    async def get_versions(self) -> list[ConfigVersion]:
        """获取版本历史

        Returns:
            版本列表
        """
        return await self._store.get_versions()

    # ========================================================================
    # 验证器
    # ========================================================================

    def register_validator(self, key_pattern: str, validator: ConfigValidator) -> None:
        """注册配置验证器

        Args:
            key_pattern: 配置键模式（支持 * 通配符）
            validator: 验证函数
        """
        self._validator_registry.register(key_pattern, validator)

    def register_global_validator(self, validator: ConfigValidator) -> None:
        """注册全局验证器

        Args:
            validator: 验证函数
        """
        self._validator_registry.register_global(validator)

    async def validate_all(self) -> dict[str, list[str]]:
        """验证所有配置

        Returns:
            错误信息字典
        """
        errors = {}
        entries = await self._store.get_entries()

        for key, entry in entries.items():
            is_valid, error_list = self._validator_registry.validate(key, entry.value)
            if not is_valid:
                errors[key] = error_list

        return errors

    # ========================================================================
    # 事件处理
    # ========================================================================

    def add_event_handler(self, handler: ConfigChangeHandler) -> None:
        """添加配置变更事件处理器

        Args:
            handler: 事件处理函数
        """
        self._event_handlers.append(handler)

    def remove_event_handler(self, handler: ConfigChangeHandler) -> None:
        """移除事件处理器

        Args:
            handler: 事件处理函数
        """
        if handler in self._event_handlers:
            self._event_handlers.remove(handler)

    # ========================================================================
    # 私有方法
    # ========================================================================

    async def _load_defaults(self) -> None:
        """加载默认配置"""
        defaults = {
            "server.host": "0.0.0.0",
            "server.port": 8080,
            "server.debug": False,
            "logging.level": "INFO",
            "logging.format": "json",
        }
        for key, value in defaults.items():
            await self._store.set(key, value, ConfigSource.DEFAULT, priority=0)

    async def _load_from_files(self) -> None:
        """从文件加载配置"""
        if not self.config_dir.exists():
            logger.debug(f"配置目录不存在: {self.config_dir}")
            return

        for config_file in self.config_dir.glob("*.json"):
            try:
                await self._load_json_file(config_file)
            except Exception as e:
                logger.error(f"加载配置文件失败: {config_file}, 错误: {e}")

    async def _load_json_file(self, file_path: Path) -> None:
        """加载 JSON 配置文件

        Args:
            file_path: 文件路径
        """
        with open(file_path) as f:
            data = json.load(f)

        prefix = file_path.stem
        if prefix == "config":
            prefix = ""

        await self._load_dict(data, prefix, ConfigSource.FILE)
        logger.debug(f"加载配置文件: {file_path}")

    async def _load_dict(
        self,
        data: dict[str, Any],
        prefix: str,
        source: ConfigSource,
    ) -> None:
        """递归加载字典配置

        Args:
            data: 配置字典
            prefix: 键前缀
            source: 配置来源
        """
        for key, value in data.items():
            full_key = f"{prefix}.{key}" if prefix else key

            if isinstance(value, dict):
                await self._load_dict(value, full_key, source)
            else:
                priority = self._source_priority.get(source, 0)
                await self._store.set(full_key, value, source, priority)

    async def _load_from_env(self) -> None:
        """从环境变量加载配置

        环境变量格式: LURKBOT_<KEY>
        例如: LURKBOT_SERVER_PORT=8080 -> server.port = 8080
        """
        prefix = "LURKBOT_"

        for key, value in os.environ.items():
            if not key.startswith(prefix):
                continue

            # 转换键名
            config_key = key[len(prefix) :].lower().replace("__", ".")

            # 尝试解析值类型
            parsed_value = self._parse_env_value(value)

            priority = self._source_priority.get(ConfigSource.ENV, 0)
            await self._store.set(config_key, parsed_value, ConfigSource.ENV, priority)
            logger.debug(f"加载环境变量配置: {config_key} = {parsed_value}")

    def _parse_env_value(self, value: str) -> Any:
        """解析环境变量值

        Args:
            value: 字符串值

        Returns:
            解析后的值
        """
        # 布尔值
        if value.lower() in ("true", "yes", "1", "on"):
            return True
        if value.lower() in ("false", "no", "0", "off"):
            return False

        # 数字
        try:
            if "." in value:
                return float(value)
            return int(value)
        except ValueError:
            pass

        # JSON
        if value.startswith("{") or value.startswith("["):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                pass

        return value

    def _on_config_file_changed(self, file_path: Path) -> None:
        """配置文件变更回调

        Args:
            file_path: 变更的文件路径
        """
        logger.info(f"检测到配置文件变更: {file_path}")

        # 异步重新加载
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._reload_file(file_path))
        except RuntimeError:
            logger.warning("没有运行中的事件循环，无法自动重载配置")

    async def _reload_file(self, file_path: Path) -> None:
        """重新加载单个配置文件

        Args:
            file_path: 文件路径
        """
        if file_path.suffix == ".json":
            try:
                await self._load_json_file(file_path)
                logger.info(f"配置文件重载成功: {file_path}")

                await self._emit_event(
                    ConfigEvent(
                        event_type=ConfigEventType.LOADED,
                        source=ConfigSource.FILE,
                        metadata={"file": str(file_path)},
                    )
                )
            except Exception as e:
                logger.error(f"配置文件重载失败: {file_path}, 错误: {e}")

                await self._emit_event(
                    ConfigEvent(
                        event_type=ConfigEventType.ERROR,
                        source=ConfigSource.FILE,
                        error=str(e),
                        metadata={"file": str(file_path)},
                    )
                )

    async def _emit_event(self, event: ConfigEvent) -> None:
        """发送配置变更事件

        Args:
            event: 配置事件
        """
        for handler in self._event_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                logger.error(f"配置事件处理器异常: {e}")

    def _next_version(self) -> str:
        """生成下一个版本号

        Returns:
            版本号
        """
        self._version_counter += 1
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        return f"v{timestamp}.{self._version_counter}"


# ============================================================================
# 全局单例
# ============================================================================

_config_manager: DynamicConfigManager | None = None


def get_config_manager(config_dir: Path | None = None) -> DynamicConfigManager:
    """获取动态配置管理器单例

    Args:
        config_dir: 配置目录

    Returns:
        配置管理器实例
    """
    global _config_manager
    if _config_manager is None:
        _config_manager = DynamicConfigManager(config_dir)
    return _config_manager


async def init_config(config_dir: Path | None = None) -> DynamicConfigManager:
    """初始化配置管理器

    Args:
        config_dir: 配置目录

    Returns:
        配置管理器实例
    """
    manager = get_config_manager(config_dir)
    await manager.initialize()
    return manager
