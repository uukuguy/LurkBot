"""插件系统模块

实现 MoltBot 插件系统，包括：
- Manifest 定义和验证
- 插件发现和加载
- 运行时 API 注入
- 命令注册
"""

from .loader import PluginInstance, PluginLoader, PluginState, get_plugin_loader
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
]
