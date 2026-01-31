"""插件管理器

实现插件生命周期管理、状态跟踪、事件分发和并发控制。
"""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any

from loguru import logger

from .loader import PluginInstance, PluginLoader, PluginState, get_plugin_loader
from .manifest import PluginManifest
from .models import (
    PluginConfig,
    PluginEvent,
    PluginEventType,
    PluginExecutionContext,
    PluginExecutionResult,
)
from .registry import PluginRegistry, get_plugin_registry
from .sandbox import PluginSandbox
from .schema_validator import discover_all_plugins


# ============================================================================
# 插件管理器
# ============================================================================


class PluginManager:
    """插件管理器

    负责插件的生命周期管理、状态跟踪和事件分发。
    """

    def __init__(
        self,
        loader: PluginLoader | None = None,
        registry: PluginRegistry | None = None,
    ):
        """初始化管理器

        Args:
            loader: 插件加载器（默认使用全局单例）
            registry: 插件注册表（默认使用全局单例）
        """
        self.loader = loader or get_plugin_loader()
        self.registry = registry or get_plugin_registry()
        self._configs: dict[str, PluginConfig] = {}
        self._sandboxes: dict[str, PluginSandbox] = {}
        self._events: list[PluginEvent] = []
        self._event_handlers: list[callable] = []

    async def discover_and_load_all(
        self, workspace_root: Path | str | None = None
    ) -> int:
        """发现并加载所有插件

        Args:
            workspace_root: 工作区根目录

        Returns:
            加载的插件数量
        """
        logger.info("开始发现和加载插件...")

        # 发现插件
        plugins = discover_all_plugins(workspace_root)
        logger.info(f"发现 {len(plugins)} 个插件")

        # 加载插件
        loaded_count = 0
        for plugin_dir, manifest in plugins:
            try:
                await self.load_plugin(plugin_dir, manifest)
                loaded_count += 1
            except Exception as e:
                logger.error(f"加载插件 {manifest.name} 失败: {e}")

        logger.info(f"成功加载 {loaded_count}/{len(plugins)} 个插件")
        return loaded_count

    async def load_plugin(
        self, plugin_dir: Path, manifest: PluginManifest
    ) -> PluginInstance:
        """加载插件

        Args:
            plugin_dir: 插件目录
            manifest: 插件清单

        Returns:
            插件实例
        """
        name = manifest.name
        logger.info(f"加载插件: {name}")

        try:
            # 使用 loader 加载插件
            plugin = self.loader.load(plugin_dir, manifest)

            # 注册到注册表
            self.registry.register(plugin)

            # 创建配置和沙箱
            config = PluginConfig(
                enabled=manifest.enabled,
                allow_filesystem=manifest.permissions.filesystem,
                allow_network=manifest.permissions.network,
                allow_exec=manifest.permissions.exec,
                allowed_channels=manifest.permissions.channels,
            )
            self._configs[name] = config
            self._sandboxes[name] = PluginSandbox(config)

            # 发布加载事件
            await self._emit_event(
                PluginEvent(
                    plugin_name=name,
                    event_type=PluginEventType.LOAD,
                    success=True,
                    message=f"插件 {name} 加载成功",
                )
            )

            # 如果配置为自动启用，则启用插件
            if config.enabled and config.auto_load:
                await self.enable_plugin(name)

            return plugin

        except Exception as e:
            logger.error(f"加载插件 {name} 失败: {e}")

            # 发布错误事件
            await self._emit_event(
                PluginEvent(
                    plugin_name=name,
                    event_type=PluginEventType.ERROR,
                    success=False,
                    error=str(e),
                )
            )
            raise

    async def unload_plugin(self, name: str) -> bool:
        """卸载插件

        Args:
            name: 插件名称

        Returns:
            是否成功卸载
        """
        logger.info(f"卸载插件: {name}")

        try:
            # 先禁用插件
            if self.is_enabled(name):
                await self.disable_plugin(name)

            # 使用 loader 卸载插件
            success = self.loader.unload(name)

            if success:
                # 从注册表移除
                self.registry.unregister(name)

                # 清理配置和沙箱
                self._configs.pop(name, None)
                self._sandboxes.pop(name, None)

                # 发布卸载事件
                await self._emit_event(
                    PluginEvent(
                        plugin_name=name,
                        event_type=PluginEventType.UNLOAD,
                        success=True,
                        message=f"插件 {name} 卸载成功",
                    )
                )

            return success

        except Exception as e:
            logger.error(f"卸载插件 {name} 失败: {e}")
            await self._emit_event(
                PluginEvent(
                    plugin_name=name,
                    event_type=PluginEventType.ERROR,
                    success=False,
                    error=str(e),
                )
            )
            return False

    async def enable_plugin(self, name: str) -> bool:
        """启用插件

        Args:
            name: 插件名称

        Returns:
            是否成功启用
        """
        logger.info(f"启用插件: {name}")

        try:
            success = self.loader.enable(name)

            if success:
                # 发布启用事件
                await self._emit_event(
                    PluginEvent(
                        plugin_name=name,
                        event_type=PluginEventType.ENABLE,
                        success=True,
                        message=f"插件 {name} 启用成功",
                    )
                )

            return success

        except Exception as e:
            logger.error(f"启用插件 {name} 失败: {e}")
            await self._emit_event(
                PluginEvent(
                    plugin_name=name,
                    event_type=PluginEventType.ERROR,
                    success=False,
                    error=str(e),
                )
            )
            return False

    async def disable_plugin(self, name: str) -> bool:
        """禁用插件

        Args:
            name: 插件名称

        Returns:
            是否成功禁用
        """
        logger.info(f"禁用插件: {name}")

        try:
            success = self.loader.disable(name)

            if success:
                # 发布禁用事件
                await self._emit_event(
                    PluginEvent(
                        plugin_name=name,
                        event_type=PluginEventType.DISABLE,
                        success=True,
                        message=f"插件 {name} 禁用成功",
                    )
                )

            return success

        except Exception as e:
            logger.error(f"禁用插件 {name} 失败: {e}")
            await self._emit_event(
                PluginEvent(
                    plugin_name=name,
                    event_type=PluginEventType.ERROR,
                    success=False,
                    error=str(e),
                )
            )
            return False

    async def execute_plugin(
        self, name: str, context: PluginExecutionContext
    ) -> PluginExecutionResult:
        """执行插件

        Args:
            name: 插件名称
            context: 执行上下文

        Returns:
            执行结果
        """
        logger.debug(f"执行插件: {name}")

        # 检查插件是否存在
        plugin = self.registry.get(name)
        if plugin is None:
            error_msg = f"插件 {name} 不存在"
            logger.error(error_msg)
            return PluginExecutionResult(
                success=False, result=None, error=error_msg, execution_time=0.0
            )

        # 检查插件是否启用
        if plugin.state != PluginState.ENABLED:
            error_msg = f"插件 {name} 未启用（当前状态: {plugin.state}）"
            logger.error(error_msg)
            return PluginExecutionResult(
                success=False, result=None, error=error_msg, execution_time=0.0
            )

        # 获取沙箱
        sandbox = self._sandboxes.get(name)
        if sandbox is None:
            error_msg = f"插件 {name} 沙箱未初始化"
            logger.error(error_msg)
            return PluginExecutionResult(
                success=False, result=None, error=error_msg, execution_time=0.0
            )

        try:
            # 在沙箱中执行插件
            if plugin.instance and hasattr(plugin.instance, "execute"):
                result = await sandbox.execute(plugin.instance.execute, context)
            elif plugin.module and hasattr(plugin.module, "execute"):
                result = await sandbox.execute(plugin.module.execute, context)
            else:
                error_msg = f"插件 {name} 没有 execute 方法"
                logger.error(error_msg)
                return PluginExecutionResult(
                    success=False, result=None, error=error_msg, execution_time=0.0
                )

            # 发布执行事件
            await self._emit_event(
                PluginEvent(
                    plugin_name=name,
                    event_type=PluginEventType.EXECUTE,
                    success=result.success,
                    message=f"插件 {name} 执行完成",
                    error=result.error,
                    metadata={"execution_time": result.execution_time},
                )
            )

            return result

        except Exception as e:
            error_msg = f"执行插件 {name} 时发生异常: {e}"
            logger.error(error_msg)

            await self._emit_event(
                PluginEvent(
                    plugin_name=name,
                    event_type=PluginEventType.ERROR,
                    success=False,
                    error=error_msg,
                )
            )

            return PluginExecutionResult(
                success=False, result=None, error=error_msg, execution_time=0.0
            )

    async def execute_plugins(
        self, context: PluginExecutionContext, plugin_names: list[str] | None = None
    ) -> dict[str, PluginExecutionResult]:
        """并发执行多个插件

        Args:
            context: 执行上下文
            plugin_names: 插件名称列表（None 表示执行所有已启用的插件）

        Returns:
            执行结果字典 {plugin_name: result}
        """
        # 确定要执行的插件
        if plugin_names is None:
            plugins = self.registry.list_by_state(PluginState.ENABLED)
            plugin_names = [p.name for p in plugins]

        logger.info(f"并发执行 {len(plugin_names)} 个插件")

        # 并发执行
        tasks = [self.execute_plugin(name, context) for name in plugin_names]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 构造结果字典
        result_dict = {}
        for name, result in zip(plugin_names, results):
            if isinstance(result, Exception):
                result_dict[name] = PluginExecutionResult(
                    success=False,
                    result=None,
                    error=str(result),
                    execution_time=0.0,
                )
            else:
                result_dict[name] = result

        return result_dict

    def is_loaded(self, name: str) -> bool:
        """检查插件是否已加载"""
        return self.registry.has(name)

    def is_enabled(self, name: str) -> bool:
        """检查插件是否已启用"""
        plugin = self.registry.get(name)
        return plugin is not None and plugin.state == PluginState.ENABLED

    def get_plugin(self, name: str) -> PluginInstance | None:
        """获取插件实例"""
        return self.registry.get(name)

    def list_plugins(self) -> list[PluginInstance]:
        """列出所有插件"""
        return self.registry.list_all()

    def list_enabled_plugins(self) -> list[PluginInstance]:
        """列出已启用的插件"""
        return self.registry.list_by_state(PluginState.ENABLED)

    def get_config(self, name: str) -> PluginConfig | None:
        """获取插件配置"""
        return self._configs.get(name)

    def update_config(self, name: str, config: PluginConfig) -> bool:
        """更新插件配置"""
        if name not in self._configs:
            return False

        self._configs[name] = config
        self._sandboxes[name] = PluginSandbox(config)
        logger.info(f"更新插件 {name} 的配置")
        return True

    def get_events(self, plugin_name: str | None = None) -> list[PluginEvent]:
        """获取事件列表

        Args:
            plugin_name: 插件名称（None 表示获取所有事件）

        Returns:
            事件列表
        """
        if plugin_name is None:
            return self._events.copy()
        else:
            return [e for e in self._events if e.plugin_name == plugin_name]

    def add_event_handler(self, handler: callable) -> None:
        """添加事件处理器

        Args:
            handler: 事件处理函数（接收 PluginEvent 参数）
        """
        self._event_handlers.append(handler)
        logger.debug(f"添加事件处理器: {handler.__name__}")

    async def _emit_event(self, event: PluginEvent) -> None:
        """发布事件

        Args:
            event: 插件事件
        """
        # 记录事件
        self._events.append(event)

        # 调用事件处理器
        for handler in self._event_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                logger.error(f"事件处理器执行失败: {e}")


# ============================================================================
# 全局单例
# ============================================================================

_global_plugin_manager: PluginManager | None = None


def get_plugin_manager() -> PluginManager:
    """获取全局插件管理器单例

    Returns:
        PluginManager 实例
    """
    global _global_plugin_manager
    if _global_plugin_manager is None:
        _global_plugin_manager = PluginManager()
    return _global_plugin_manager
