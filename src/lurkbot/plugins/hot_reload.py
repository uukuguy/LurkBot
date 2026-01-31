"""插件热重载

支持不重启服务更新插件，包括文件监控、增量重载、状态保持和事件通知。
"""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any

from loguru import logger
from watchdog.events import (
    FileModifiedEvent,
    FileSystemEvent,
    FileSystemEventHandler,
)
from watchdog.observers import Observer

from .loader import PluginInstance, PluginState
from .manager import PluginManager
from .manifest import PluginManifest
from .schema_validator import ManifestValidator


# ============================================================================
# 热重载事件处理器
# ============================================================================


class PluginReloadHandler(FileSystemEventHandler):
    """插件热重载事件处理器

    监控插件目录的文件变化，触发插件重载。
    """

    def __init__(self, manager: PluginManager, debounce_seconds: float = 1.0):
        """初始化处理器

        Args:
            manager: 插件管理器
            debounce_seconds: 防抖时间（秒）
        """
        super().__init__()
        self.manager = manager
        self.debounce_seconds = debounce_seconds
        self._pending_reloads: dict[str, float] = {}
        self._reload_lock = asyncio.Lock()

    def on_modified(self, event: FileSystemEvent) -> None:
        """文件修改事件处理

        Args:
            event: 文件系统事件
        """
        if event.is_directory:
            return

        # 只处理 Python 文件和 manifest.json
        path = Path(event.src_path)
        if path.suffix not in [".py", ".json"]:
            return

        # 查找插件目录
        plugin_dir = self._find_plugin_dir(path)
        if not plugin_dir:
            return

        # 记录待重载的插件（防抖）
        plugin_name = plugin_dir.name
        self._pending_reloads[plugin_name] = datetime.now().timestamp()

        logger.debug(f"检测到插件文件变化: {path} (插件: {plugin_name})")

    def _find_plugin_dir(self, file_path: Path) -> Path | None:
        """查找文件所属的插件目录

        Args:
            file_path: 文件路径

        Returns:
            插件目录路径，如果不是插件文件则返回 None
        """
        # 向上查找包含 manifest.json 的目录
        current = file_path.parent
        while current != current.parent:
            if (current / "manifest.json").exists():
                return current
            current = current.parent
        return None

    async def process_pending_reloads(self) -> None:
        """处理待重载的插件（防抖后）"""
        if not self._pending_reloads:
            return

        now = datetime.now().timestamp()
        to_reload = []

        # 检查哪些插件已经超过防抖时间
        for plugin_name, timestamp in list(self._pending_reloads.items()):
            if now - timestamp >= self.debounce_seconds:
                to_reload.append(plugin_name)
                del self._pending_reloads[plugin_name]

        # 重载插件
        for plugin_name in to_reload:
            await self._reload_plugin(plugin_name)

    async def _reload_plugin(self, plugin_name: str) -> None:
        """重载插件

        Args:
            plugin_name: 插件名称
        """
        async with self._reload_lock:
            try:
                logger.info(f"开始热重载插件: {plugin_name}")

                # 获取插件实例
                plugin = self.manager.loader.get(plugin_name)
                if not plugin:
                    logger.warning(f"插件 {plugin_name} 不存在，跳过重载")
                    return

                # 保存插件状态
                old_state = plugin.state
                old_enabled = self.manager.is_enabled(plugin_name)

                # 卸载插件
                await self.manager.unload_plugin(plugin_name)

                # 重新加载插件
                plugin_dir = plugin.plugin_dir
                manifest, errors = ManifestValidator.validate_from_file(
                    plugin_dir / "manifest.json"
                )
                if errors:
                    logger.error(f"插件 {plugin_name} manifest 验证失败: {errors}")
                    return
                await self.manager.load_plugin(plugin_dir, manifest)

                # 恢复插件状态
                if old_enabled:
                    await self.manager.enable_plugin(plugin_name)

                logger.info(f"插件 {plugin_name} 热重载成功")

            except Exception as e:
                logger.error(f"插件 {plugin_name} 热重载失败: {e}")


# ============================================================================
# 热重载管理器
# ============================================================================


class HotReloadManager:
    """热重载管理器

    管理插件目录的文件监控和热重载流程。
    """

    def __init__(
        self,
        manager: PluginManager,
        watch_paths: list[Path] | None = None,
        debounce_seconds: float = 1.0,
    ):
        """初始化管理器

        Args:
            manager: 插件管理器
            watch_paths: 监控的路径列表
            debounce_seconds: 防抖时间（秒）
        """
        self.manager = manager
        self.watch_paths = watch_paths or []
        self.debounce_seconds = debounce_seconds

        self._observer: Observer | None = None
        self._handler: PluginReloadHandler | None = None
        self._process_task: asyncio.Task | None = None
        self._running = False

    def start(self) -> None:
        """启动热重载监控"""
        if self._running:
            logger.warning("热重载管理器已经在运行")
            return

        logger.info("启动插件热重载监控...")

        # 创建事件处理器
        self._handler = PluginReloadHandler(self.manager, self.debounce_seconds)

        # 创建观察者
        self._observer = Observer()
        for path in self.watch_paths:
            if path.exists():
                self._observer.schedule(self._handler, str(path), recursive=True)
                logger.info(f"监控插件目录: {path}")

        # 启动观察者
        self._observer.start()
        self._running = True

        # 启动处理任务
        try:
            loop = asyncio.get_running_loop()
            self._process_task = loop.create_task(self._process_loop())
        except RuntimeError:
            # 没有运行中的事件循环，跳过创建任务
            logger.warning("没有运行中的事件循环，热重载处理任务将不会启动")

        logger.info("插件热重载监控已启动")

    def stop(self) -> None:
        """停止热重载监控"""
        if not self._running:
            return

        logger.info("停止插件热重载监控...")

        # 停止观察者
        if self._observer:
            self._observer.stop()
            self._observer.join()
            self._observer = None

        # 停止处理任务
        if self._process_task:
            self._process_task.cancel()
            self._process_task = None

        self._running = False
        logger.info("插件热重载监控已停止")

    async def _process_loop(self) -> None:
        """处理循环（定期检查待重载的插件）"""
        try:
            while self._running:
                if self._handler:
                    await self._handler.process_pending_reloads()
                await asyncio.sleep(0.5)  # 每 0.5 秒检查一次
        except asyncio.CancelledError:
            logger.debug("热重载处理循环已取消")

    def add_watch_path(self, path: Path) -> None:
        """添加监控路径

        Args:
            path: 要监控的路径
        """
        if path in self.watch_paths:
            return

        self.watch_paths.append(path)

        # 如果已经在运行，动态添加监控
        if self._running and self._observer and path.exists():
            self._observer.schedule(self._handler, str(path), recursive=True)
            logger.info(f"添加监控路径: {path}")

    def remove_watch_path(self, path: Path) -> None:
        """移除监控路径

        Args:
            path: 要移除的路径
        """
        if path not in self.watch_paths:
            return

        self.watch_paths.remove(path)
        logger.info(f"移除监控路径: {path}")

        # 注意: watchdog 不支持动态移除监控路径，需要重启观察者
        if self._running:
            logger.warning("移除监控路径需要重启热重载管理器")


# ============================================================================
# 全局单例
# ============================================================================

_hot_reload_manager: HotReloadManager | None = None


def get_hot_reload_manager(
    manager: PluginManager | None = None,
    watch_paths: list[Path] | None = None,
    debounce_seconds: float = 1.0,
) -> HotReloadManager:
    """获取热重载管理器单例

    Args:
        manager: 插件管理器
        watch_paths: 监控的路径列表
        debounce_seconds: 防抖时间（秒）

    Returns:
        热重载管理器实例
    """
    global _hot_reload_manager
    if _hot_reload_manager is None:
        if manager is None:
            raise ValueError("首次调用必须提供 manager 参数")
        _hot_reload_manager = HotReloadManager(manager, watch_paths, debounce_seconds)
    return _hot_reload_manager
