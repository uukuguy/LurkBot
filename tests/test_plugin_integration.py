"""插件系统集成测试

测试插件系统与 Agent Runtime 的集成，以及端到端的工作流程。
"""

import tempfile
from pathlib import Path

import pytest

from lurkbot.plugins.loader import get_plugin_loader
from lurkbot.plugins.manager import PluginManager
from lurkbot.plugins.models import PluginExecutionContext
from lurkbot.plugins.registry import PluginRegistry


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def temp_plugin_dir():
    """创建临时插件目录"""
    with tempfile.TemporaryDirectory() as tmpdir:
        plugin_dir = Path(tmpdir) / "integration-test-plugin"
        plugin_dir.mkdir()

        # 创建 plugin.json
        manifest_content = """{
    "name": "integration-test-plugin",
    "version": "1.0.0",
    "description": "Integration test plugin",
    "author": "Test Author",
    "entry": "plugin.py",
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
    # 模拟插件处理
    user_input = context.get("input_data", {}).get("query", "")
    return {
        "plugin_response": f"Processed: {user_input}",
        "metadata": {"processed_by": "integration-test-plugin"}
    }
"""
        (plugin_dir / "plugin.py").write_text(plugin_code)

        yield Path(tmpdir)


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
# 端到端集成测试
# ============================================================================


@pytest.mark.asyncio
async def test_end_to_end_plugin_workflow(plugin_manager, temp_plugin_dir):
    """测试完整的插件工作流程"""
    # Step 1: 发现并加载插件
    loaded_count = await plugin_manager.discover_and_load_all(temp_plugin_dir)
    assert loaded_count == 1

    # Step 2: 验证插件已加载并启用
    assert plugin_manager.is_loaded("integration-test-plugin")
    assert plugin_manager.is_enabled("integration-test-plugin")

    # Step 3: 创建执行上下文
    context = PluginExecutionContext(
        user_id="test-user",
        channel_id="test-channel",
        session_id="test-session",
        input_data={"query": "What is the weather?"},
        parameters={},
    )

    # Step 4: 执行插件
    result = await plugin_manager.execute_plugin("integration-test-plugin", context)

    # Step 5: 验证执行结果
    assert result.success is True
    assert result.error is None
    assert result.result is not None
    assert "plugin_response" in result.result
    assert "Processed: What is the weather?" in result.result["plugin_response"]

    # Step 6: 检查事件记录
    events = plugin_manager.get_events("integration-test-plugin")
    assert len(events) >= 2  # LOAD, ENABLE, EXECUTE


@pytest.mark.asyncio
async def test_plugin_error_handling_integration(plugin_manager, temp_plugin_dir):
    """测试插件错误处理的集成"""
    # 创建会抛出异常的插件
    error_plugin_dir = temp_plugin_dir / "error-plugin"
    error_plugin_dir.mkdir()

    manifest_content = """{
    "name": "error-plugin",
    "version": "1.0.0",
    "description": "Error test plugin",
    "author": "Test Author",
    "entry": "plugin.py",
    "enabled": true,
    "permissions": {
        "filesystem": false,
        "network": false,
        "exec": false,
        "channels": []
    }
}"""
    (error_plugin_dir / "plugin.json").write_text(manifest_content)

    plugin_code = """
async def execute(context):
    raise ValueError("Intentional error for testing")
"""
    (error_plugin_dir / "plugin.py").write_text(plugin_code)

    # 加载插件
    await plugin_manager.discover_and_load_all(temp_plugin_dir)

    # 执行插件
    context = PluginExecutionContext(input_data={"test": "data"})
    result = await plugin_manager.execute_plugin("error-plugin", context)

    # 验证错误被正确处理
    assert result.success is False
    assert result.error is not None
    assert "ValueError" in result.error
    assert "Intentional error" in result.error


@pytest.mark.asyncio
async def test_plugin_timeout_integration(plugin_manager, temp_plugin_dir):
    """测试插件超时的集成"""
    # 创建慢速插件
    slow_plugin_dir = temp_plugin_dir / "slow-plugin"
    slow_plugin_dir.mkdir()

    manifest_content = """{
    "name": "slow-plugin",
    "version": "1.0.0",
    "description": "Slow test plugin",
    "author": "Test Author",
    "entry": "plugin.py",
    "enabled": true,
    "permissions": {
        "filesystem": false,
        "network": false,
        "exec": false,
        "channels": []
    }
}"""
    (slow_plugin_dir / "plugin.json").write_text(manifest_content)

    plugin_code = """
import asyncio

async def execute(context):
    await asyncio.sleep(60)  # 超过默认超时时间
    return {"result": "success"}
"""
    (slow_plugin_dir / "plugin.py").write_text(plugin_code)

    # 加载插件
    await plugin_manager.discover_and_load_all(temp_plugin_dir)

    # 执行插件
    context = PluginExecutionContext(input_data={"test": "data"})
    result = await plugin_manager.execute_plugin("slow-plugin", context)

    # 验证超时被正确处理
    assert result.success is False
    assert result.error is not None
    assert "超时" in result.error


@pytest.mark.asyncio
async def test_multiple_plugins_integration(plugin_manager, temp_plugin_dir):
    """测试多插件集成"""
    # 创建第二个插件
    plugin2_dir = temp_plugin_dir / "plugin2"
    plugin2_dir.mkdir()

    manifest_content = """{
    "name": "plugin2",
    "version": "1.0.0",
    "description": "Second test plugin",
    "author": "Test Author",
    "entry": "plugin.py",
    "enabled": true,
    "permissions": {
        "filesystem": false,
        "network": false,
        "exec": false,
        "channels": []
    }
}"""
    (plugin2_dir / "plugin.json").write_text(manifest_content)

    plugin_code = """
async def execute(context):
    return {"plugin": "plugin2", "status": "success"}
"""
    (plugin2_dir / "plugin.py").write_text(plugin_code)

    # 加载所有插件
    loaded_count = await plugin_manager.discover_and_load_all(temp_plugin_dir)
    assert loaded_count == 2

    # 并发执行所有插件
    context = PluginExecutionContext(input_data={"test": "data"})
    results = await plugin_manager.execute_plugins(context)

    # 验证所有插件都执行成功
    assert len(results) == 2
    assert all(r.success for r in results.values())


@pytest.mark.asyncio
async def test_plugin_config_update_integration(plugin_manager, temp_plugin_dir):
    """测试插件配置更新的集成"""
    # 加载插件
    await plugin_manager.discover_and_load_all(temp_plugin_dir)

    # 获取原始配置
    original_config = plugin_manager.get_config("integration-test-plugin")
    assert original_config is not None
    assert original_config.max_execution_time == 30.0

    # 更新配置
    from lurkbot.plugins.models import PluginConfig

    new_config = PluginConfig(
        enabled=True,
        max_execution_time=60.0,
        allow_network=True,
    )
    success = plugin_manager.update_config("integration-test-plugin", new_config)
    assert success is True

    # 验证配置已更新
    updated_config = plugin_manager.get_config("integration-test-plugin")
    assert updated_config.max_execution_time == 60.0
    assert updated_config.allow_network is True


@pytest.mark.asyncio
async def test_plugin_event_system_integration(plugin_manager, temp_plugin_dir):
    """测试插件事件系统的集成"""
    # 设置事件处理器
    received_events = []

    def event_handler(event):
        received_events.append(event)

    plugin_manager.add_event_handler(event_handler)

    # 加载插件（会触发 LOAD 和 ENABLE 事件）
    await plugin_manager.discover_and_load_all(temp_plugin_dir)

    # 执行插件（会触发 EXECUTE 事件）
    context = PluginExecutionContext(input_data={"test": "data"})
    await plugin_manager.execute_plugin("integration-test-plugin", context)

    # 禁用插件（会触发 DISABLE 事件）
    await plugin_manager.disable_plugin("integration-test-plugin")

    # 验证事件被正确触发
    assert len(received_events) >= 4  # LOAD, ENABLE, EXECUTE, DISABLE

    from lurkbot.plugins.models import PluginEventType

    event_types = [e.event_type for e in received_events]
    assert PluginEventType.LOAD in event_types
    assert PluginEventType.ENABLE in event_types
    assert PluginEventType.EXECUTE in event_types
    assert PluginEventType.DISABLE in event_types


@pytest.mark.asyncio
async def test_plugin_registry_persistence_integration(plugin_manager, temp_plugin_dir):
    """测试插件注册表持久化的集成"""
    # 加载插件
    await plugin_manager.discover_and_load_all(temp_plugin_dir)

    # 验证插件在注册表中
    assert plugin_manager.registry.has("integration-test-plugin")

    # 获取注册表文件路径
    registry_file = plugin_manager.registry._registry_file

    # 验证注册表文件存在
    assert registry_file.exists()

    # 创建新的管理器实例（应该能加载持久化的数据）
    new_registry = PluginRegistry(registry_file=registry_file)

    # 验证数据已持久化
    assert new_registry.has("integration-test-plugin")


# ============================================================================
# Agent Runtime 集成测试（模拟）
# ============================================================================


@pytest.mark.asyncio
async def test_plugin_with_agent_runtime_simulation(plugin_manager, temp_plugin_dir):
    """测试插件与 Agent Runtime 的集成（模拟）"""
    # 加载插件
    await plugin_manager.discover_and_load_all(temp_plugin_dir)

    # 模拟 Agent Runtime 的工作流程
    async def simulated_agent_runtime(user_input: str, enable_plugins: bool = True):
        """模拟 Agent Runtime"""
        if enable_plugins:
            # Step 1: 执行插件
            context = PluginExecutionContext(
                input_data={"query": user_input},
                parameters={},
            )
            plugin_results = await plugin_manager.execute_plugins(context)

            # Step 2: 将插件结果注入到上下文
            plugin_context = []
            for name, result in plugin_results.items():
                if result.success:
                    plugin_context.append(
                        f"Plugin {name}: {result.result}"
                    )

            # Step 3: 模拟 LLM 调用（这里只是返回插件结果）
            return {
                "response": f"Processed with plugins: {plugin_context}",
                "plugin_results": plugin_results,
            }
        else:
            # 不使用插件，直接处理
            return {"response": f"Processed without plugins: {user_input}"}

    # 测试启用插件的情况
    result_with_plugins = await simulated_agent_runtime(
        "What is the weather?", enable_plugins=True
    )
    assert "plugin_results" in result_with_plugins
    assert len(result_with_plugins["plugin_results"]) >= 1

    # 测试禁用插件的情况
    result_without_plugins = await simulated_agent_runtime(
        "What is the weather?", enable_plugins=False
    )
    assert "plugin_results" not in result_without_plugins
