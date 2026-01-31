"""插件注册表

实现插件索引、元数据存储、查询接口和持久化。
"""

import json
from pathlib import Path

from loguru import logger

from .loader import PluginInstance, PluginState
from .manifest import PluginManifest, PluginType


# ============================================================================
# 插件注册表
# ============================================================================


class PluginRegistry:
    """插件注册表

    维护插件名称到插件实例的映射，提供查询和持久化功能。
    """

    def __init__(self, registry_file: Path | None = None):
        """初始化注册表

        Args:
            registry_file: 注册表文件路径（默认为 data/plugins/registry.json）
        """
        self._plugins: dict[str, PluginInstance] = {}
        self._registry_file = registry_file or Path("data/plugins/registry.json")

        # 确保目录存在
        self._registry_file.parent.mkdir(parents=True, exist_ok=True)

        # 加载已保存的注册表
        self._load_registry()

    def register(self, plugin: PluginInstance) -> None:
        """注册插件

        Args:
            plugin: 插件实例
        """
        name = plugin.name
        if name in self._plugins:
            logger.warning(f"插件 {name} 已注册，将被覆盖")

        self._plugins[name] = plugin
        logger.debug(f"注册插件: {name}")

        # 保存到文件
        self._save_registry()

    def unregister(self, name: str) -> bool:
        """注销插件

        Args:
            name: 插件名称

        Returns:
            是否成功注销
        """
        if name not in self._plugins:
            logger.warning(f"插件 {name} 未注册")
            return False

        del self._plugins[name]
        logger.debug(f"注销插件: {name}")

        # 保存到文件
        self._save_registry()
        return True

    def get(self, name: str) -> PluginInstance | None:
        """获取插件实例

        Args:
            name: 插件名称

        Returns:
            插件实例（如果存在）
        """
        return self._plugins.get(name)

    def has(self, name: str) -> bool:
        """检查插件是否已注册

        Args:
            name: 插件名称

        Returns:
            是否已注册
        """
        return name in self._plugins

    def list_all(self) -> list[PluginInstance]:
        """列出所有插件

        Returns:
            插件列表
        """
        return list(self._plugins.values())

    def list_by_state(self, state: PluginState) -> list[PluginInstance]:
        """按状态列出插件

        Args:
            state: 插件状态

        Returns:
            插件列表
        """
        return [p for p in self._plugins.values() if p.state == state]

    def list_by_type(self, plugin_type: PluginType) -> list[PluginInstance]:
        """按类型列出插件

        Args:
            plugin_type: 插件类型

        Returns:
            插件列表
        """
        return [p for p in self._plugins.values() if p.manifest.type == plugin_type]

    def find_by_tag(self, tag: str) -> list[PluginInstance]:
        """按标签查找插件

        Args:
            tag: 标签

        Returns:
            插件列表
        """
        return [p for p in self._plugins.values() if tag in p.manifest.tags]

    def find_by_keyword(self, keyword: str) -> list[PluginInstance]:
        """按关键词查找插件

        Args:
            keyword: 关键词

        Returns:
            插件列表
        """
        keyword_lower = keyword.lower()
        return [
            p
            for p in self._plugins.values()
            if keyword_lower in p.manifest.name.lower()
            or keyword_lower in p.manifest.description.lower()
            or any(keyword_lower in kw.lower() for kw in p.manifest.keywords)
        ]

    def get_metadata(self, name: str) -> PluginManifest | None:
        """获取插件元数据

        Args:
            name: 插件名称

        Returns:
            插件元数据（如果存在）
        """
        plugin = self.get(name)
        return plugin.manifest if plugin else None

    def get_all_metadata(self) -> dict[str, PluginManifest]:
        """获取所有插件元数据

        Returns:
            插件元数据字典 {name: manifest}
        """
        return {name: plugin.manifest for name, plugin in self._plugins.items()}

    def clear(self) -> None:
        """清空注册表"""
        self._plugins.clear()
        logger.debug("清空插件注册表")
        self._save_registry()

    def _save_registry(self) -> None:
        """保存注册表到文件"""
        try:
            # 构造可序列化的数据
            data = {
                "plugins": {
                    name: {
                        "name": plugin.name,
                        "version": plugin.manifest.version,
                        "description": plugin.manifest.description,
                        "type": plugin.manifest.type.value,
                        "state": plugin.state.value,
                        "plugin_dir": str(plugin.plugin_dir),
                        "enabled": plugin.manifest.enabled,
                        "tags": plugin.manifest.tags,
                        "keywords": plugin.manifest.keywords,
                    }
                    for name, plugin in self._plugins.items()
                }
            }

            # 写入文件
            with open(self._registry_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            logger.debug(f"保存插件注册表到 {self._registry_file}")

        except Exception as e:
            logger.error(f"保存插件注册表失败: {e}")

    def _load_registry(self) -> None:
        """从文件加载注册表"""
        if not self._registry_file.exists():
            logger.debug(f"注册表文件不存在: {self._registry_file}")
            return

        try:
            with open(self._registry_file, encoding="utf-8") as f:
                data = json.load(f)

            # 注意：这里只加载元数据，不加载实际的插件实例
            # 实际的插件加载由 PluginLoader 负责
            logger.debug(f"从 {self._registry_file} 加载插件注册表")
            logger.debug(f"注册表中有 {len(data.get('plugins', {}))} 个插件记录")

        except Exception as e:
            logger.error(f"加载插件注册表失败: {e}")


# ============================================================================
# 全局单例
# ============================================================================

_global_plugin_registry: PluginRegistry | None = None


def get_plugin_registry() -> PluginRegistry:
    """获取全局插件注册表单例

    Returns:
        PluginRegistry 实例
    """
    global _global_plugin_registry
    if _global_plugin_registry is None:
        _global_plugin_registry = PluginRegistry()
    return _global_plugin_registry
