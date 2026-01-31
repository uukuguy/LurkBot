"""插件管理器

实现插件生命周期管理、状态跟踪、事件分发和并发控制。

Phase 7 增强功能：
- 插件编排：依赖管理和拓扑排序执行
- 权限控制：细粒度权限检查和审计
- 版本管理：多版本共存和版本切换
- 性能分析：执行性能监控和报告
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
from .orchestration import ExecutionCondition, PluginOrchestrator
from .permissions import Permission, PermissionLevel, PermissionManager, PermissionType
from .profiling import PerformanceProfiler, PerformanceReport
from .registry import PluginRegistry, get_plugin_registry
from .sandbox import PluginSandbox
from .schema_validator import discover_all_plugins
from .versioning import VersionManager


# ============================================================================
# 插件管理器
# ============================================================================


class PluginManager:
    """插件管理器

    负责插件的生命周期管理、状态跟踪和事件分发。

    Phase 7 增强功能：
    - 插件编排：通过 orchestrator 管理插件依赖和执行顺序
    - 权限控制：通过 permission_manager 进行细粒度权限检查
    - 版本管理：通过 version_manager 支持多版本共存
    - 性能分析：通过 profiler 收集和分析性能数据
    """

    def __init__(
        self,
        loader: PluginLoader | None = None,
        registry: PluginRegistry | None = None,
        enable_orchestration: bool = True,
        enable_permissions: bool = True,
        enable_versioning: bool = True,
        enable_profiling: bool = True,
    ):
        """初始化管理器

        Args:
            loader: 插件加载器（默认使用全局单例）
            registry: 插件注册表（默认使用全局单例）
            enable_orchestration: 是否启用插件编排
            enable_permissions: 是否启用权限控制
            enable_versioning: 是否启用版本管理
            enable_profiling: 是否启用性能分析
        """
        self.loader = loader or get_plugin_loader()
        self.registry = registry or get_plugin_registry()
        self._configs: dict[str, PluginConfig] = {}
        self._sandboxes: dict[str, PluginSandbox] = {}
        self._events: list[PluginEvent] = []
        self._event_handlers: list[callable] = []

        # Phase 7 Task 4: 性能优化 - 添加缓存机制
        self._plugin_cache: dict[str, PluginInstance] = {}  # 插件实例缓存
        self._manifest_cache: dict[str, PluginManifest] = {}  # Manifest 缓存
        self._cache_enabled: bool = True  # 缓存开关

        # Phase 7: 集成新功能模块
        self._enable_orchestration = enable_orchestration
        self._enable_permissions = enable_permissions
        self._enable_versioning = enable_versioning
        self._enable_profiling = enable_profiling

        # 初始化编排器
        self.orchestrator = PluginOrchestrator() if enable_orchestration else None

        # 初始化权限管理器
        self.permission_manager = PermissionManager() if enable_permissions else None

        # 初始化版本管理器
        self.version_manager = VersionManager() if enable_versioning else None

        # 初始化性能分析器
        self.profiler = PerformanceProfiler() if enable_profiling else None

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
        version = manifest.version
        cache_key = f"{name}:{version}"

        # Phase 7 Task 4: 检查缓存
        if self._cache_enabled and cache_key in self._plugin_cache:
            logger.debug(f"从缓存加载插件: {name} v{version}")
            return self._plugin_cache[cache_key]

        logger.info(f"加载插件: {name} v{version}")

        try:
            # Phase 7: 版本管理集成
            if self._enable_versioning and self.version_manager:
                # 检查版本是否已存在
                existing_version = self.version_manager.get_version_info(name, version)
                if existing_version:
                    logger.warning(f"插件 {name} v{version} 已存在，跳过加载")
                    # 从 loader 获取已加载的插件实例
                    existing_plugin = self.loader.get(name)
                    if existing_plugin:
                        return existing_plugin

            # 使用 loader 加载插件
            plugin = self.loader.load(plugin_dir, manifest)

            # 注册到注册表
            self.registry.register(plugin)

            # Phase 7: 版本管理集成 - 注册版本
            if self._enable_versioning and self.version_manager:
                # 将插件信息存储在 metadata 中
                version_metadata = {
                    "plugin_dir": str(plugin_dir),
                    "manifest": manifest.model_dump(),
                }
                self.version_manager.register_version(name, version, version_metadata)
                logger.debug(f"注册插件版本: {name} v{version}")

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

            # Phase 7: 编排系统集成 - 注册插件节点
            if self._enable_orchestration and self.orchestrator:
                # 注意：manifest.dependencies 是包依赖，不是插件依赖
                # 插件间依赖需要在 manifest 中添加新字段或通过其他方式指定
                # 这里暂时使用空列表，后续可以扩展
                plugin_dependencies = []
                if hasattr(manifest, "plugin_dependencies"):
                    plugin_dependencies = manifest.plugin_dependencies

                priority = manifest.priority if hasattr(manifest, "priority") else 100
                self.orchestrator.register_plugin(
                    name=name,
                    dependencies=plugin_dependencies,
                    priority=priority,
                )
                logger.debug(f"注册插件到编排器: {name}, 依赖: {plugin_dependencies}")

            # Phase 7: 权限管理集成 - 授予基础权限
            if self._enable_permissions and self.permission_manager:
                await self._grant_plugin_permissions(name, manifest)

            # 发布加载事件
            await self._emit_event(
                PluginEvent(
                    plugin_name=name,
                    event_type=PluginEventType.LOAD,
                    success=True,
                    message=f"插件 {name} v{version} 加载成功",
                )
            )

            # 如果配置为自动启用，则启用插件
            if config.enabled and config.auto_load:
                await self.enable_plugin(name)

            # Phase 7 Task 4: 添加到缓存
            if self._cache_enabled:
                self._plugin_cache[cache_key] = plugin
                self._manifest_cache[cache_key] = manifest
                logger.debug(f"插件已缓存: {cache_key}")

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

                # Phase 7 Task 4: 清理缓存
                if self._cache_enabled:
                    # 清理所有该插件的版本缓存
                    keys_to_remove = [k for k in self._plugin_cache.keys() if k.startswith(f"{name}:")]
                    for key in keys_to_remove:
                        self._plugin_cache.pop(key, None)
                        self._manifest_cache.pop(key, None)
                    if keys_to_remove:
                        logger.debug(f"清理插件缓存: {keys_to_remove}")

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

        # Phase 7: 权限检查集成
        if self._enable_permissions and self.permission_manager:
            # 检查基本执行权限
            execute_permission = Permission(
                type=PermissionType.PLUGIN_EXECUTE,
                resource=name,
                level=PermissionLevel.WRITE,
            )
            has_permission = await self.permission_manager.check_permission(
                plugin_name=name,
                permission=execute_permission,
            )
            if not has_permission:
                error_msg = f"插件 {name} 没有执行权限"
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

        # Phase 7: 性能分析集成 - 开始分析
        profiling_session_id = None
        if self._enable_profiling and self.profiler:
            profiling_session_id = await self.profiler.start_profiling(name)

        try:
            # 在沙箱中执行插件
            if plugin.instance and hasattr(plugin.instance, "execute"):
                result = await sandbox.execute(plugin.instance.execute, context)
            elif plugin.module and hasattr(plugin.module, "execute"):
                result = await sandbox.execute(plugin.module.execute, context)
            else:
                error_msg = f"插件 {name} 没有 execute 方法"
                logger.error(error_msg)
                result = PluginExecutionResult(
                    success=False, result=None, error=error_msg, execution_time=0.0
                )

            # Phase 7: 性能分析集成 - 结束分析
            if self._enable_profiling and self.profiler and profiling_session_id:
                profile = await self.profiler.stop_profiling(
                    profiling_session_id, success=result.success
                )
                if profile:
                    logger.debug(
                        f"插件 {name} 执行完成: "
                        f"耗时 {profile.execution_time:.3f}s, "
                        f"CPU {profile.cpu_percent:.1f}%, "
                        f"内存 {profile.memory_mb:.1f}MB"
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

            # Phase 7: 性能分析集成 - 记录失败
            if self._enable_profiling and self.profiler and profiling_session_id:
                await self.profiler.stop_profiling(
                    profiling_session_id, success=False, error=str(e)
                )

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

        logger.info(f"执行 {len(plugin_names)} 个插件")

        # Phase 7: 编排系统集成 - 使用拓扑排序执行
        if self._enable_orchestration and self.orchestrator:
            try:
                # 确保所有要执行的插件都已注册到编排器
                for name in plugin_names:
                    if name not in self.orchestrator._nodes:
                        # 如果插件未注册到编排器，先注册
                        self.orchestrator.register_plugin(name, dependencies=[])

                # 生成执行计划
                plan = self.orchestrator.create_execution_plan()

                if plan.has_cycles:
                    logger.error(f"检测到循环依赖: {plan.cycle_info}")
                    # 降级为并发执行
                    return await self._execute_plugins_concurrent(context, plugin_names)

                logger.info(f"使用编排执行，共 {len(plan.stages)} 个阶段")

                # 按阶段执行
                result_dict = {}
                for stage_idx, stage_plugins in enumerate(plan.stages, 1):
                    # 只执行请求的插件
                    stage_plugins_to_execute = [
                        p for p in stage_plugins if p in plugin_names
                    ]
                    if not stage_plugins_to_execute:
                        continue

                    logger.debug(
                        f"执行阶段 {stage_idx}/{len(plan.stages)}: {stage_plugins_to_execute}"
                    )

                    # 并发执行同一阶段的插件
                    stage_results = await self._execute_plugins_concurrent(
                        context, stage_plugins_to_execute
                    )
                    result_dict.update(stage_results)

                    # 更新编排器的执行结果（用于条件判断）
                    if self.orchestrator:
                        self.orchestrator._execution_results.update(stage_results)

                return result_dict

            except Exception as e:
                logger.error(f"编排执行失败: {e}，降级为并发执行")
                return await self._execute_plugins_concurrent(context, plugin_names)
        else:
            # 不使用编排，直接并发执行
            return await self._execute_plugins_concurrent(context, plugin_names)

    async def _execute_plugins_concurrent(
        self, context: PluginExecutionContext, plugin_names: list[str]
    ) -> dict[str, PluginExecutionResult]:
        """并发执行插件（内部方法）

        Args:
            context: 执行上下文
            plugin_names: 插件名称列表

        Returns:
            执行结果字典
        """
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

    # ========================================================================
    # Phase 7: 权限管理方法
    # ========================================================================

    async def _grant_plugin_permissions(
        self, plugin_name: str, manifest: PluginManifest
    ) -> None:
        """授予插件基础权限

        Args:
            plugin_name: 插件名称
            manifest: 插件清单
        """
        if not self.permission_manager:
            return

        # 根据 manifest 中的权限配置授予权限
        if manifest.permissions.filesystem:
            await self.permission_manager.grant_permission(
                plugin_name=plugin_name,
                permission=Permission(
                    type=PermissionType.FILESYSTEM_READ,
                    level=PermissionLevel.READ,
                ),
            )
            await self.permission_manager.grant_permission(
                plugin_name=plugin_name,
                permission=Permission(
                    type=PermissionType.FILESYSTEM_WRITE,
                    level=PermissionLevel.WRITE,
                ),
            )

        if manifest.permissions.network:
            await self.permission_manager.grant_permission(
                plugin_name=plugin_name,
                permission=Permission(
                    type=PermissionType.NETWORK_HTTP,
                    level=PermissionLevel.WRITE,
                ),
            )
            await self.permission_manager.grant_permission(
                plugin_name=plugin_name,
                permission=Permission(
                    type=PermissionType.NETWORK_HTTPS,
                    level=PermissionLevel.WRITE,
                ),
            )

        if manifest.permissions.exec:
            await self.permission_manager.grant_permission(
                plugin_name=plugin_name,
                permission=Permission(
                    type=PermissionType.SYSTEM_EXEC,
                    level=PermissionLevel.WRITE,
                ),
            )

        # 授予基本插件权限
        await self.permission_manager.grant_permission(
            plugin_name=plugin_name,
            permission=Permission(
                type=PermissionType.PLUGIN_EXECUTE,
                resource=plugin_name,
                level=PermissionLevel.WRITE,
            ),
        )

        logger.debug(f"已授予插件 {plugin_name} 基础权限")

    async def grant_permission(
        self,
        plugin_name: str,
        permission_type: PermissionType,
        resource: str | None = None,
        level: PermissionLevel = PermissionLevel.WRITE,
    ) -> bool:
        """授予插件权限

        Args:
            plugin_name: 插件名称
            permission_type: 权限类型
            resource: 资源标识
            level: 权限级别

        Returns:
            是否成功授予
        """
        if not self.permission_manager:
            logger.warning("权限管理未启用")
            return False

        permission = Permission(
            type=permission_type,
            resource=resource,
            level=level,
        )
        await self.permission_manager.grant_permission(
            plugin_name=plugin_name,
            permission=permission,
        )
        logger.info(f"授予插件 {plugin_name} 权限: {permission_type}")
        return True

    async def revoke_permission(
        self,
        plugin_name: str,
        permission_type: PermissionType,
        resource: str | None = None,
    ) -> bool:
        """撤销插件权限

        Args:
            plugin_name: 插件名称
            permission_type: 权限类型
            resource: 资源标识

        Returns:
            是否成功撤销
        """
        if not self.permission_manager:
            logger.warning("权限管理未启用")
            return False

        permission = Permission(
            type=permission_type,
            resource=resource,
        )
        await self.permission_manager.revoke_permission(
            plugin_name=plugin_name,
            permission=permission,
        )
        logger.info(f"撤销插件 {plugin_name} 权限: {permission_type}")
        return True

    async def get_permission_audit_log(self, plugin_name: str | None = None) -> list[Any]:
        """获取权限审计日志

        Args:
            plugin_name: 插件名称（None 表示获取所有日志）

        Returns:
            审计日志列表
        """
        if not self.permission_manager:
            return []

        return await self.permission_manager.get_audit_logs(plugin_name)

    # ========================================================================
    # Phase 7: 版本管理方法
    # ========================================================================

    def get_plugin_versions(self, plugin_name: str) -> list[str]:
        """获取插件的所有版本

        Args:
            plugin_name: 插件名称

        Returns:
            版本列表
        """
        if not self.version_manager:
            return []

        return self.version_manager.get_all_versions(plugin_name)

    async def switch_plugin_version(
        self, plugin_name: str, target_version: str
    ) -> bool:
        """切换插件版本

        Args:
            plugin_name: 插件名称
            target_version: 目标版本

        Returns:
            是否成功切换
        """
        if not self.version_manager:
            logger.warning("版本管理未启用")
            return False

        try:
            success = self.version_manager.set_active_version(plugin_name, target_version)
            if success:
                logger.info(f"插件 {plugin_name} 切换到版本 {target_version}")
                # 注意：版本切换不会自动重新加载插件
                # 需要手动卸载并重新加载插件以应用新版本
            return success
        except Exception as e:
            logger.error(f"切换插件版本失败: {e}")
            return False

    async def rollback_plugin_version(self, plugin_name: str) -> bool:
        """回滚插件到上一个版本

        Args:
            plugin_name: 插件名称

        Returns:
            是否成功回滚
        """
        if not self.version_manager:
            logger.warning("版本管理未启用")
            return False

        try:
            success = self.version_manager.rollback(plugin_name)
            if success:
                # 获取当前活跃版本
                current_version = self.version_manager.get_active_version(plugin_name)
                if current_version:
                    logger.info(f"插件 {plugin_name} 回滚到版本 {current_version}")
                    # 注意：版本回滚不会自动重新加载插件
                    # 需要手动卸载并重新加载插件以应用回滚版本
                return True
            return False
        except Exception as e:
            logger.error(f"回滚插件版本失败: {e}")
            return False

    def get_version_history(self, plugin_name: str) -> list[Any]:
        """获取插件版本历史

        Args:
            plugin_name: 插件名称

        Returns:
            版本历史记录列表
        """
        if not self.version_manager:
            return []

        return self.version_manager.get_history(plugin_name)

    # ========================================================================
    # Phase 7: 性能分析方法
    # ========================================================================

    def get_performance_report(self, plugin_name: str) -> PerformanceReport | None:
        """获取插件性能报告

        Args:
            plugin_name: 插件名称

        Returns:
            性能报告
        """
        if not self.profiler:
            return None

        return self.profiler.generate_report(plugin_name)

    def get_all_performance_reports(self) -> dict[str, PerformanceReport]:
        """获取所有插件的性能报告

        Returns:
            性能报告字典 {plugin_name: report}
        """
        if not self.profiler:
            return {}

        return self.profiler.generate_all_reports()

    def get_performance_bottlenecks(
        self, threshold_percentile: float = 0.9
    ) -> list[str]:
        """识别性能瓶颈插件

        Args:
            threshold_percentile: 阈值百分位（默认 90%）

        Returns:
            瓶颈插件名称列表
        """
        if not self.profiler:
            return []

        return self.profiler.identify_bottlenecks(threshold_percentile)

    def compare_plugin_performance(
        self, plugin_names: list[str]
    ) -> dict[str, PerformanceReport]:
        """比较多个插件的性能

        Args:
            plugin_names: 插件名称列表

        Returns:
            性能报告字典
        """
        if not self.profiler:
            return {}

        return self.profiler.compare_plugins(plugin_names)

    # ========================================================================
    # Phase 7: 编排管理方法
    # ========================================================================

    def visualize_dependency_graph(self, output_format: str = "text") -> str:
        """可视化插件依赖图

        Args:
            output_format: 输出格式（text/dot）

        Returns:
            依赖图的文本表示
        """
        if not self.orchestrator:
            return "编排系统未启用"

        return self.orchestrator.visualize_graph(output_format)

    def get_execution_plan(self, plugin_names: list[str] | None = None) -> Any:
        """获取插件执行计划

        Args:
            plugin_names: 插件名称列表（None 表示所有已注册的插件）

        Returns:
            执行计划
        """
        if not self.orchestrator:
            return None

        # 注意：orchestrator.create_execution_plan() 不接受参数
        # 它会为所有已注册的插件创建执行计划
        return self.orchestrator.create_execution_plan()

    # ========================================================================
    # Phase 7 Task 4: 缓存管理方法
    # ========================================================================

    def clear_cache(self, plugin_name: str | None = None) -> int:
        """清理插件缓存

        Args:
            plugin_name: 插件名称（None 表示清理所有缓存）

        Returns:
            清理的缓存项数量
        """
        if not self._cache_enabled:
            return 0

        if plugin_name is None:
            # 清理所有缓存
            count = len(self._plugin_cache)
            self._plugin_cache.clear()
            self._manifest_cache.clear()
            logger.info(f"已清理所有插件缓存: {count} 项")
            return count
        else:
            # 清理指定插件的缓存
            keys_to_remove = [k for k in self._plugin_cache.keys() if k.startswith(f"{plugin_name}:")]
            for key in keys_to_remove:
                self._plugin_cache.pop(key, None)
                self._manifest_cache.pop(key, None)
            logger.info(f"已清理插件 {plugin_name} 的缓存: {len(keys_to_remove)} 项")
            return len(keys_to_remove)

    def get_cache_stats(self) -> dict[str, Any]:
        """获取缓存统计信息

        Returns:
            缓存统计信息字典
        """
        if not self._cache_enabled:
            return {
                "enabled": False,
                "plugin_count": 0,
                "manifest_count": 0,
                "total_size": 0,
            }

        return {
            "enabled": True,
            "plugin_count": len(self._plugin_cache),
            "manifest_count": len(self._manifest_cache),
            "plugins": list(self._plugin_cache.keys()),
        }

    def enable_cache(self, enabled: bool = True) -> None:
        """启用或禁用缓存

        Args:
            enabled: 是否启用缓存
        """
        self._cache_enabled = enabled
        if not enabled:
            self.clear_cache()
        logger.info(f"插件缓存已{'启用' if enabled else '禁用'}")


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
