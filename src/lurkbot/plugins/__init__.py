"""插件系统模块

实现 LurkBot 插件系统，包括：
- Manifest 定义和验证
- 插件发现和加载
- 插件生命周期管理
- 插件沙箱执行
- 插件注册表和索引
"""

from .loader import PluginInstance, PluginLoader, PluginState, get_plugin_loader
from .manager import PluginManager, get_plugin_manager
from .manifest import (
    PluginAuthor,
    PluginDependencies,
    PluginLanguage,
    PluginManifest,
    PluginPermissions,
    PluginRepository,
    PluginType,
    validate_plugin_name,
    validate_semantic_version,
)
from .models import (
    PluginConfig,
    PluginEvent,
    PluginEventType,
    PluginExecutionContext,
    PluginExecutionResult,
    PluginStatus,
)
from .registry import PluginRegistry, get_plugin_registry
from .sandbox import PluginSandbox, check_permission, execute_with_timeout, sandboxed
from .schema_validator import (
    ManifestValidator,
    deduplicate_plugins,
    discover_all_plugins,
    discover_plugins_in_dir,
)

__all__ = [
    # Manifest
    "PluginManifest",
    "PluginType",
    "PluginLanguage",
    "PluginAuthor",
    "PluginRepository",
    "PluginDependencies",
    "PluginPermissions",
    "validate_plugin_name",
    "validate_semantic_version",
    # Validator
    "ManifestValidator",
    "discover_plugins_in_dir",
    "discover_all_plugins",
    "deduplicate_plugins",
    # Loader
    "PluginLoader",
    "PluginInstance",
    "PluginState",
    "get_plugin_loader",
    # Manager
    "PluginManager",
    "get_plugin_manager",
    # Registry
    "PluginRegistry",
    "get_plugin_registry",
    # Sandbox
    "PluginSandbox",
    "sandboxed",
    "execute_with_timeout",
    "check_permission",
    # Models
    "PluginConfig",
    "PluginStatus",
    "PluginEvent",
    "PluginEventType",
    "PluginExecutionContext",
    "PluginExecutionResult",
]
