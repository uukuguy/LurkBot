"""插件动态加载器

实现插件的动态导入、生命周期管理和沙箱隔离。
参考：MOLTBOT_COMPLETE_ARCHITECTURE.md 第 16.1 节
"""

import importlib
import importlib.util
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from loguru import logger

from .manifest import PluginManifest


# ============================================================================
# 插件生命周期状态
# ============================================================================


class PluginState(str, Enum):
    """插件状态"""

    UNLOADED = "unloaded"  # 未加载
    LOADED = "loaded"  # 已加载
    ENABLED = "enabled"  # 已启用
    DISABLED = "disabled"  # 已禁用
    ERROR = "error"  # 错误状态


# ============================================================================
# 插件实例
# ============================================================================


@dataclass
class PluginInstance:
    """插件实例"""

    name: str  # 插件名称
    manifest: PluginManifest  # 插件清单
    plugin_dir: Path  # 插件目录
    state: PluginState  # 状态
    module: Any | None = None  # Python 模块对象
    instance: Any | None = None  # 插件实例对象
    error: str | None = None  # 错误信息

    def __repr__(self) -> str:
        return f"PluginInstance(name={self.name!r}, state={self.state})"


# ============================================================================
# 插件加载器
# ============================================================================


class PluginLoader:
    """插件加载器

    负责插件的动态导入和生命周期管理。
    """

    def __init__(self):
        self._plugins: dict[str, PluginInstance] = {}

    def load(
        self, plugin_dir: Path, manifest: PluginManifest
    ) -> PluginInstance:
        """加载插件

        Args:
            plugin_dir: 插件目录
            manifest: 插件清单

        Returns:
            插件实例

        Raises:
            ImportError: 导入失败
            ValueError: 参数错误
        """
        name = manifest.name

        # 检查是否已加载
        if name in self._plugins:
            logger.warning(f"插件 {name} 已加载，将重新加载")
            self.unload(name)

        logger.info(f"加载插件: {name} v{manifest.version}")

        # 创建插件实例
        plugin = PluginInstance(
            name=name,
            manifest=manifest,
            plugin_dir=plugin_dir,
            state=PluginState.UNLOADED,
        )

        try:
            # 检查依赖
            self._check_dependencies(manifest)

            # 动态导入插件模块
            module = self._import_plugin_module(plugin_dir, manifest)
            plugin.module = module

            # 实例化插件类
            if manifest.main_class:
                plugin_class = getattr(module, manifest.main_class)
                plugin.instance = plugin_class()
            else:
                # 没有 main_class，使用模块本身
                plugin.instance = module

            plugin.state = PluginState.LOADED
            logger.info(f"插件 {name} 加载成功")

        except Exception as e:
            plugin.state = PluginState.ERROR
            plugin.error = str(e)
            logger.error(f"插件 {name} 加载失败: {e}")
            raise

        self._plugins[name] = plugin
        return plugin

    def unload(self, name: str) -> bool:
        """卸载插件

        Args:
            name: 插件名称

        Returns:
            是否成功卸载
        """
        if name not in self._plugins:
            logger.warning(f"插件 {name} 未加载")
            return False

        plugin = self._plugins[name]

        logger.info(f"卸载插件: {name}")

        # 调用插件的清理方法（如果有）
        if plugin.instance and hasattr(plugin.instance, "on_unload"):
            try:
                plugin.instance.on_unload()
            except Exception as e:
                logger.warning(f"插件 {name} 清理失败: {e}")

        # 从 sys.modules 中移除
        if plugin.module:
            module_name = plugin.module.__name__
            if module_name in sys.modules:
                del sys.modules[module_name]

        # 从缓存中移除
        del self._plugins[name]
        logger.debug(f"插件 {name} 已卸载")

        return True

    def enable(self, name: str) -> bool:
        """启用插件

        Args:
            name: 插件名称

        Returns:
            是否成功启用
        """
        if name not in self._plugins:
            logger.error(f"插件 {name} 未加载")
            return False

        plugin = self._plugins[name]

        if plugin.state == PluginState.ENABLED:
            logger.warning(f"插件 {name} 已启用")
            return True

        logger.info(f"启用插件: {name}")

        # 调用插件的启用方法（如果有）
        if plugin.instance and hasattr(plugin.instance, "on_enable"):
            try:
                plugin.instance.on_enable()
            except Exception as e:
                plugin.state = PluginState.ERROR
                plugin.error = str(e)
                logger.error(f"插件 {name} 启用失败: {e}")
                return False

        plugin.state = PluginState.ENABLED
        logger.info(f"插件 {name} 已启用")
        return True

    def disable(self, name: str) -> bool:
        """禁用插件

        Args:
            name: 插件名称

        Returns:
            是否成功禁用
        """
        if name not in self._plugins:
            logger.error(f"插件 {name} 未加载")
            return False

        plugin = self._plugins[name]

        if plugin.state == PluginState.DISABLED:
            logger.warning(f"插件 {name} 已禁用")
            return True

        logger.info(f"禁用插件: {name}")

        # 调用插件的禁用方法（如果有）
        if plugin.instance and hasattr(plugin.instance, "on_disable"):
            try:
                plugin.instance.on_disable()
            except Exception as e:
                logger.warning(f"插件 {name} 禁用时出错: {e}")

        plugin.state = PluginState.DISABLED
        logger.info(f"插件 {name} 已禁用")
        return True

    def get(self, name: str) -> PluginInstance | None:
        """获取插件实例

        Args:
            name: 插件名称

        Returns:
            插件实例（如果存在）
        """
        return self._plugins.get(name)

    def list_all(self) -> list[PluginInstance]:
        """列出所有插件

        Returns:
            插件列表
        """
        return list(self._plugins.values())

    def list_enabled(self) -> list[PluginInstance]:
        """列出已启用的插件

        Returns:
            已启用的插件列表
        """
        return [p for p in self._plugins.values() if p.state == PluginState.ENABLED]

    def _import_plugin_module(
        self, plugin_dir: Path, manifest: PluginManifest
    ) -> Any:
        """动态导入插件模块

        Args:
            plugin_dir: 插件目录
            manifest: 插件清单

        Returns:
            模块对象

        Raises:
            ImportError: 导入失败
        """
        entry_file = plugin_dir / manifest.entry

        if not entry_file.exists():
            raise ImportError(f"插件入口文件不存在: {entry_file}")

        # 生成模块名（确保唯一性）
        module_name = f"lurkbot.plugins.loaded.{manifest.name}"

        # 使用 importlib 动态导入
        spec = importlib.util.spec_from_file_location(module_name, entry_file)
        if spec is None or spec.loader is None:
            raise ImportError(f"无法创建模块 spec: {entry_file}")

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)

        logger.debug(f"导入模块: {module_name} (from {entry_file})")
        return module

    def _check_dependencies(self, manifest: PluginManifest) -> None:
        """检查插件依赖

        Args:
            manifest: 插件清单

        Raises:
            ImportError: 缺少依赖
        """
        # 检查 Python 包依赖
        missing_packages = []
        for package in manifest.dependencies.python:
            try:
                importlib.import_module(package)
            except ImportError:
                missing_packages.append(package)

        if missing_packages:
            raise ImportError(f"缺少 Python 包依赖: {', '.join(missing_packages)}")

        # 检查环境变量依赖
        import os

        missing_env = [
            env for env in manifest.dependencies.env if env not in os.environ
        ]

        if missing_env:
            raise ValueError(f"缺少环境变量: {', '.join(missing_env)}")

        logger.debug(f"插件 {manifest.name} 依赖检查通过")


# ============================================================================
# 全局单例
# ============================================================================

_global_plugin_loader: PluginLoader | None = None


def get_plugin_loader() -> PluginLoader:
    """获取全局插件加载器单例

    Returns:
        PluginLoader 实例
    """
    global _global_plugin_loader
    if _global_plugin_loader is None:
        _global_plugin_loader = PluginLoader()
    return _global_plugin_loader
