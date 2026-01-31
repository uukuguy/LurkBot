"""测试插件注册表

测试 PluginRegistry 的注册、查询和持久化功能。
"""

import tempfile
from pathlib import Path

import pytest

from lurkbot.plugins.loader import PluginInstance, PluginState
from lurkbot.plugins.manifest import (
    PluginAuthor,
    PluginManifest,
    PluginPermissions,
    PluginType,
)
from lurkbot.plugins.registry import PluginRegistry


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def temp_registry_file():
    """创建临时注册表文件"""
    with tempfile.TemporaryDirectory() as tmpdir:
        registry_file = Path(tmpdir) / "registry.json"
        yield registry_file


@pytest.fixture
def plugin_manifest():
    """创建测试插件清单"""
    return PluginManifest(
        name="test-plugin",
        version="1.0.0",
        description="Test plugin",
        author=PluginAuthor(name="Test Author"),
        entry="test_plugin.py",
        enabled=True,
        type=PluginType.TOOL,
        tags=["test", "example"],
        permissions=PluginPermissions(
            filesystem=False,
            network=False,
            exec=False,
            channels=[],
        ),
    )


@pytest.fixture
def plugin_instance(plugin_manifest, temp_registry_file):
    """创建测试插件实例"""
    return PluginInstance(
        name="test-plugin",
        manifest=plugin_manifest,
        plugin_dir=temp_registry_file.parent / "test-plugin",
        state=PluginState.LOADED,
        module=None,
        instance=None,
    )


@pytest.fixture
def registry(temp_registry_file):
    """创建插件注册表实例"""
    return PluginRegistry(registry_file=temp_registry_file)


# ============================================================================
# 基础功能测试
# ============================================================================


def test_registry_initialization(temp_registry_file):
    """测试注册表初始化"""
    registry = PluginRegistry(registry_file=temp_registry_file)

    assert registry._plugins == {}
    assert registry._registry_file == temp_registry_file
    assert temp_registry_file.parent.exists()


def test_register_plugin(registry, plugin_instance):
    """测试注册插件"""
    registry.register(plugin_instance)

    assert registry.has("test-plugin")
    assert registry.get("test-plugin") == plugin_instance


def test_register_duplicate_plugin(registry, plugin_instance):
    """测试注册重复插件"""
    registry.register(plugin_instance)
    registry.register(plugin_instance)  # 应该覆盖

    assert registry.has("test-plugin")
    plugins = registry.list_all()
    assert len(plugins) == 1


def test_unregister_plugin(registry, plugin_instance):
    """测试注销插件"""
    registry.register(plugin_instance)
    assert registry.has("test-plugin")

    success = registry.unregister("test-plugin")
    assert success is True
    assert not registry.has("test-plugin")


def test_unregister_nonexistent_plugin(registry):
    """测试注销不存在的插件"""
    success = registry.unregister("nonexistent")
    assert success is False


def test_get_plugin(registry, plugin_instance):
    """测试获取插件"""
    registry.register(plugin_instance)

    plugin = registry.get("test-plugin")
    assert plugin is not None
    assert plugin.name == "test-plugin"


def test_get_nonexistent_plugin(registry):
    """测试获取不存在的插件"""
    plugin = registry.get("nonexistent")
    assert plugin is None


def test_has_plugin(registry, plugin_instance):
    """测试检查插件是否存在"""
    assert not registry.has("test-plugin")

    registry.register(plugin_instance)
    assert registry.has("test-plugin")


# ============================================================================
# 查询功能测试
# ============================================================================


def test_list_all_plugins(registry, plugin_manifest, temp_registry_file):
    """测试列出所有插件"""
    # 注册多个插件
    for i in range(3):
        manifest = plugin_manifest.model_copy()
        manifest.name = f"plugin-{i}"
        instance = PluginInstance(
            name=f"plugin-{i}",
            manifest=manifest,
            plugin_dir=temp_registry_file.parent / f"plugin-{i}",
            state=PluginState.LOADED,
            module=None,
            instance=None,
        )
        registry.register(instance)

    plugins = registry.list_all()
    assert len(plugins) == 3
    assert all(p.name.startswith("plugin-") for p in plugins)


def test_list_by_state(registry, plugin_manifest, temp_registry_file):
    """测试按状态列出插件"""
    # 注册不同状态的插件
    states = [PluginState.LOADED, PluginState.ENABLED, PluginState.DISABLED]
    for i, state in enumerate(states):
        manifest = plugin_manifest.model_copy()
        manifest.name = f"plugin-{i}"
        instance = PluginInstance(
            name=f"plugin-{i}",
            manifest=manifest,
            plugin_dir=temp_registry_file.parent / f"plugin-{i}",
            state=state,
            module=None,
            instance=None,
        )
        registry.register(instance)

    # 查询已启用的插件
    enabled_plugins = registry.list_by_state(PluginState.ENABLED)
    assert len(enabled_plugins) == 1
    assert enabled_plugins[0].state == PluginState.ENABLED

    # 查询已加载的插件
    loaded_plugins = registry.list_by_state(PluginState.LOADED)
    assert len(loaded_plugins) == 1
    assert loaded_plugins[0].state == PluginState.LOADED


def test_list_by_type(registry, plugin_manifest, temp_registry_file):
    """测试按类型列出插件"""
    # 注册不同类型的插件
    types = [PluginType.TOOL, PluginType.CHANNEL, PluginType.MIDDLEWARE]
    for i, plugin_type in enumerate(types):
        manifest = plugin_manifest.model_copy()
        manifest.name = f"plugin-{i}"
        manifest.type = plugin_type
        instance = PluginInstance(
            name=f"plugin-{i}",
            manifest=manifest,
            plugin_dir=temp_registry_file.parent / f"plugin-{i}",
            state=PluginState.LOADED,
            module=None,
            instance=None,
        )
        registry.register(instance)

    # 查询工具类型插件
    tool_plugins = registry.list_by_type(PluginType.TOOL)
    assert len(tool_plugins) == 1
    assert tool_plugins[0].manifest.type == PluginType.TOOL

    # 查询频道类型插件
    channel_plugins = registry.list_by_type(PluginType.CHANNEL)
    assert len(channel_plugins) == 1
    assert channel_plugins[0].manifest.type == PluginType.CHANNEL


def test_find_by_tag(registry, plugin_manifest, temp_registry_file):
    """测试按标签查找插件"""
    # 注册带不同标签的插件
    plugin1_manifest = plugin_manifest.model_copy()
    plugin1_manifest.name = "plugin-1"
    plugin1_manifest.tags = ["test", "example"]
    instance1 = PluginInstance(
        name="plugin-1",
        manifest=plugin1_manifest,
        plugin_dir=temp_registry_file.parent / "plugin-1",
        state=PluginState.LOADED,
        module=None,
        instance=None,
    )

    plugin2_manifest = plugin_manifest.model_copy()
    plugin2_manifest.name = "plugin-2"
    plugin2_manifest.tags = ["production", "stable"]
    instance2 = PluginInstance(
        name="plugin-2",
        manifest=plugin2_manifest,
        plugin_dir=temp_registry_file.parent / "plugin-2",
        state=PluginState.LOADED,
        module=None,
        instance=None,
    )

    registry.register(instance1)
    registry.register(instance2)

    # 查找带 "test" 标签的插件
    test_plugins = registry.find_by_tag("test")
    assert len(test_plugins) == 1
    assert test_plugins[0].name == "plugin-1"

    # 查找带 "production" 标签的插件
    prod_plugins = registry.find_by_tag("production")
    assert len(prod_plugins) == 1
    assert prod_plugins[0].name == "plugin-2"


def test_find_by_keyword(registry, plugin_manifest, temp_registry_file):
    """测试按关键词查找插件"""
    # 注册带不同描述的插件
    plugin1_manifest = plugin_manifest.model_copy()
    plugin1_manifest.name = "weather-plugin"
    plugin1_manifest.description = "Get weather information"
    instance1 = PluginInstance(
        name="weather-plugin",
        manifest=plugin1_manifest,
        plugin_dir=temp_registry_file.parent / "weather-plugin",
        state=PluginState.LOADED,
        module=None,
        instance=None,
    )

    plugin2_manifest = plugin_manifest.model_copy()
    plugin2_manifest.name = "translator-plugin"
    plugin2_manifest.description = "Translate text between languages"
    instance2 = PluginInstance(
        name="translator-plugin",
        manifest=plugin2_manifest,
        plugin_dir=temp_registry_file.parent / "translator-plugin",
        state=PluginState.LOADED,
        module=None,
        instance=None,
    )

    registry.register(instance1)
    registry.register(instance2)

    # 按名称关键词查找
    weather_plugins = registry.find_by_keyword("weather")
    assert len(weather_plugins) == 1
    assert weather_plugins[0].name == "weather-plugin"

    # 按描述关键词查找
    translate_plugins = registry.find_by_keyword("translate")
    assert len(translate_plugins) == 1
    assert translate_plugins[0].name == "translator-plugin"


# ============================================================================
# 持久化测试
# ============================================================================


def test_registry_persistence_file_creation(temp_registry_file, plugin_instance):
    """测试注册表文件创建"""
    # 创建注册表并注册插件
    registry = PluginRegistry(registry_file=temp_registry_file)
    registry.register(plugin_instance)

    # 验证文件已创建
    assert temp_registry_file.exists()

    # 验证文件内容
    import json

    with open(temp_registry_file) as f:
        data = json.load(f)

    assert "plugins" in data
    assert "test-plugin" in data["plugins"]
    assert data["plugins"]["test-plugin"]["name"] == "test-plugin"


def test_registry_persistence_after_unregister(temp_registry_file, plugin_instance):
    """测试注销后的持久化"""
    # 创建注册表并注册插件
    registry = PluginRegistry(registry_file=temp_registry_file)
    registry.register(plugin_instance)

    # 验证文件存在且包含插件
    assert temp_registry_file.exists()
    import json

    with open(temp_registry_file) as f:
        data = json.load(f)
    assert "test-plugin" in data["plugins"]

    # 注销插件
    registry.unregister("test-plugin")

    # 验证文件已更新
    with open(temp_registry_file) as f:
        data = json.load(f)
    assert "test-plugin" not in data["plugins"]
