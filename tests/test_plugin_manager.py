"""测试插件管理器

测试 PluginManager 的生命周期管理、事件分发和并发执行功能。
"""

import asyncio
import tempfile
from pathlib import Path

import pytest

from lurkbot.plugins.loader import PluginState, get_plugin_loader
from lurkbot.plugins.manager import PluginManager
from lurkbot.plugins.manifest import PluginAuthor, PluginManifest, PluginPermissions
from lurkbot.plugins.models import (
    PluginConfig,
    PluginEventType,
    PluginExecutionContext,
)
from lurkbot.plugins.registry import PluginRegistry


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def temp_plugin_dir():
    """创建临时插件目录"""
    with tempfile.TemporaryDirectory() as tmpdir:
        plugin_dir = Path(tmpdir) / "test-plugin"
        plugin_dir.mkdir()

        # 创建 plugin.json
        manifest_content = """{
    "name": "test-plugin",
    "version": "1.0.0",
    "description": "Test plugin",
    "author": {"name": "Test Author"},
    "entry": "test_plugin.py",
    "enabled": true,
    "permissions": {
        "filesystem": false,
        "network": false,
        "exec": false,
        "channels": []
    }
}"""
        (plugin_dir / "plugin.json").write_text(manifest_content)

        # 创建插件代码
        plugin_code = """
async def execute(context):
    return {"result": "success", "input": context.input_data}
"""
        (plugin_dir / "test_plugin.py").write_text(plugin_code)

        yield plugin_dir


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
        permissions=PluginPermissions(
            filesystem=False,
            network=False,
            exec=False,
            channels=[],
        ),
    )


@pytest.fixture
async def plugin_manager():
    """创建插件管理器实例"""
    loader = get_plugin_loader()
    registry = PluginRegistry()
    manager = PluginManager(loader=loader, registry=registry)
    yield manager
    # 清理
    for plugin in manager.list_plugins():
        await manager.unload_plugin(plugin.name)


# ============================================================================
# 基础功能测试
# ============================================================================


@pytest.mark.asyncio
async def test_plugin_manager_initialization():
    """测试插件管理器初始化"""
    manager = PluginManager()

    assert manager.loader is not None
    assert manager.registry is not None
    assert isinstance(manager._configs, dict)
    assert isinstance(manager._sandboxes, dict)
    assert isinstance(manager._events, list)


@pytest.mark.asyncio
async def test_load_plugin(plugin_manager, temp_plugin_dir, plugin_manifest):
    """测试加载插件"""
    plugin = await plugin_manager.load_plugin(temp_plugin_dir, plugin_manifest)

    assert plugin is not None
    assert plugin.name == "test-plugin"
    assert plugin.state == PluginState.ENABLED  # auto_load=True
    assert plugin_manager.is_loaded("test-plugin")
    assert plugin_manager.is_enabled("test-plugin")

    # 检查配置和沙箱是否创建
    config = plugin_manager.get_config("test-plugin")
    assert config is not None
    assert config.enabled is True


@pytest.mark.asyncio
async def test_unload_plugin(plugin_manager, temp_plugin_dir, plugin_manifest):
    """测试卸载插件"""
    # 先加载
    await plugin_manager.load_plugin(temp_plugin_dir, plugin_manifest)
    assert plugin_manager.is_loaded("test-plugin")

    # 卸载
    success = await plugin_manager.unload_plugin("test-plugin")
    assert success is True
    assert not plugin_manager.is_loaded("test-plugin")

    # 配置和沙箱应该被清理
    assert plugin_manager.get_config("test-plugin") is None


@pytest.mark.asyncio
async def test_enable_plugin(plugin_manager, temp_plugin_dir, plugin_manifest):
    """测试启用插件"""
    # 加载但不自动启用
    manifest = plugin_manifest.model_copy()
    manifest.enabled = False
    await plugin_manager.load_plugin(temp_plugin_dir, manifest)

    # 手动启用
    success = await plugin_manager.enable_plugin("test-plugin")
    assert success is True
    assert plugin_manager.is_enabled("test-plugin")


@pytest.mark.asyncio
async def test_disable_plugin(plugin_manager, temp_plugin_dir, plugin_manifest):
    """测试禁用插件"""
    # 加载并启用
    await plugin_manager.load_plugin(temp_plugin_dir, plugin_manifest)
    assert plugin_manager.is_enabled("test-plugin")

    # 禁用
    success = await plugin_manager.disable_plugin("test-plugin")
    assert success is True
    assert not plugin_manager.is_enabled("test-plugin")


# ============================================================================
# 插件执行测试
# ============================================================================


@pytest.mark.asyncio
async def test_execute_plugin(plugin_manager, temp_plugin_dir, plugin_manifest):
    """测试执行插件"""
    # 加载插件
    await plugin_manager.load_plugin(temp_plugin_dir, plugin_manifest)

    # 创建执行上下文
    context = PluginExecutionContext(
        input_data={"test": "data"},
        parameters={"param1": "value1"},
    )

    # 执行插件
    result = await plugin_manager.execute_plugin("test-plugin", context)

    assert result.success is True
    assert result.error is None
    assert result.execution_time >= 0
    assert result.result is not None


@pytest.mark.asyncio
async def test_execute_nonexistent_plugin(plugin_manager):
    """测试执行不存在的插件"""
    context = PluginExecutionContext()
    result = await plugin_manager.execute_plugin("nonexistent", context)

    assert result.success is False
    assert result.error is not None
    assert "不存在" in result.error


@pytest.mark.asyncio
async def test_execute_disabled_plugin(plugin_manager, temp_plugin_dir, plugin_manifest):
    """测试执行已禁用的插件"""
    # 加载并禁用
    await plugin_manager.load_plugin(temp_plugin_dir, plugin_manifest)
    await plugin_manager.disable_plugin("test-plugin")

    # 尝试执行
    context = PluginExecutionContext()
    result = await plugin_manager.execute_plugin("test-plugin", context)

    assert result.success is False
    assert result.error is not None
    assert "未启用" in result.error


@pytest.mark.asyncio
async def test_execute_plugins_concurrent(plugin_manager, temp_plugin_dir, plugin_manifest):
    """测试并发执行多个插件"""
    # 加载插件
    await plugin_manager.load_plugin(temp_plugin_dir, plugin_manifest)

    # 创建执行上下文
    context = PluginExecutionContext(input_data={"test": "data"})

    # 并发执行
    results = await plugin_manager.execute_plugins(context, ["test-plugin"])

    assert len(results) == 1
    assert "test-plugin" in results
    assert results["test-plugin"].success is True


# ============================================================================
# 配置管理测试
# ============================================================================


@pytest.mark.asyncio
async def test_get_config(plugin_manager, temp_plugin_dir, plugin_manifest):
    """测试获取插件配置"""
    await plugin_manager.load_plugin(temp_plugin_dir, plugin_manifest)

    config = plugin_manager.get_config("test-plugin")
    assert config is not None
    assert isinstance(config, PluginConfig)
    assert config.enabled is True


@pytest.mark.asyncio
async def test_update_config(plugin_manager, temp_plugin_dir, plugin_manifest):
    """测试更新插件配置"""
    await plugin_manager.load_plugin(temp_plugin_dir, plugin_manifest)

    # 更新配置
    new_config = PluginConfig(
        enabled=False,
        max_execution_time=60.0,
        allow_network=True,
    )
    success = plugin_manager.update_config("test-plugin", new_config)

    assert success is True

    # 验证配置已更新
    config = plugin_manager.get_config("test-plugin")
    assert config.enabled is False
    assert config.max_execution_time == 60.0
    assert config.allow_network is True


# ============================================================================
# 事件系统测试
# ============================================================================


@pytest.mark.asyncio
async def test_event_emission(plugin_manager, temp_plugin_dir, plugin_manifest):
    """测试事件发布"""
    # 加载插件会触发 LOAD 和 ENABLE 事件
    await plugin_manager.load_plugin(temp_plugin_dir, plugin_manifest)

    events = plugin_manager.get_events("test-plugin")
    assert len(events) >= 2

    # 检查 LOAD 事件
    load_events = [e for e in events if e.event_type == PluginEventType.LOAD]
    assert len(load_events) == 1
    assert load_events[0].success is True

    # 检查 ENABLE 事件
    enable_events = [e for e in events if e.event_type == PluginEventType.ENABLE]
    assert len(enable_events) == 1
    assert enable_events[0].success is True


@pytest.mark.asyncio
async def test_event_handler(plugin_manager, temp_plugin_dir, plugin_manifest):
    """测试事件处理器"""
    received_events = []

    def handler(event):
        received_events.append(event)

    plugin_manager.add_event_handler(handler)

    # 加载插件会触发事件
    await plugin_manager.load_plugin(temp_plugin_dir, plugin_manifest)

    # 验证事件处理器被调用
    assert len(received_events) >= 2


# ============================================================================
# 查询功能测试
# ============================================================================


@pytest.mark.asyncio
async def test_list_plugins(plugin_manager, temp_plugin_dir, plugin_manifest):
    """测试列出所有插件"""
    await plugin_manager.load_plugin(temp_plugin_dir, plugin_manifest)

    plugins = plugin_manager.list_plugins()
    assert len(plugins) == 1
    assert plugins[0].name == "test-plugin"


@pytest.mark.asyncio
async def test_list_enabled_plugins(plugin_manager, temp_plugin_dir, plugin_manifest):
    """测试列出已启用的插件"""
    await plugin_manager.load_plugin(temp_plugin_dir, plugin_manifest)

    enabled_plugins = plugin_manager.list_enabled_plugins()
    assert len(enabled_plugins) == 1
    assert enabled_plugins[0].name == "test-plugin"

    # 禁用后再查询
    await plugin_manager.disable_plugin("test-plugin")
    enabled_plugins = plugin_manager.list_enabled_plugins()
    assert len(enabled_plugins) == 0
