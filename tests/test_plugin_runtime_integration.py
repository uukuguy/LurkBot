"""测试 Agent Runtime 与插件系统的集成

验证插件系统是否正确集成到 Agent Runtime 中。
"""

import tempfile
from pathlib import Path

import pytest

from lurkbot.agents.types import AgentContext
from lurkbot.plugins.loader import get_plugin_loader
from lurkbot.plugins.manager import PluginManager
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
    "description": "Test plugin for runtime integration",
    "author": {"name": "Test Author"},
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
    query = context.get("input_data", {}).get("query", "")
    return {
        "plugin_response": f"Plugin processed: {query}",
        "metadata": {"processed_by": "test-plugin"}
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
# Runtime 集成测试
# ============================================================================


@pytest.mark.asyncio
async def test_plugin_manager_integration(plugin_manager, temp_plugin_dir):
    """测试插件管理器基本集成"""
    # 加载插件
    loaded_count = await plugin_manager.discover_and_load_all(temp_plugin_dir)
    assert loaded_count == 1

    # 验证插件已加载
    assert plugin_manager.is_loaded("test-plugin")
    assert plugin_manager.is_enabled("test-plugin")


@pytest.mark.asyncio
async def test_plugin_execution_with_context(plugin_manager, temp_plugin_dir):
    """测试插件执行与上下文传递"""
    from lurkbot.plugins.models import PluginExecutionContext

    # 加载插件
    await plugin_manager.discover_and_load_all(temp_plugin_dir)

    # 创建执行上下文（模拟 Agent Runtime 的上下文）
    context = PluginExecutionContext(
        user_id="test-user",
        channel_id="test-channel",
        session_id="test-session",
        input_data={"query": "What is the weather?"},
        parameters={},
        metadata={"provider": "anthropic", "model": "claude-sonnet-4"},
    )

    # 执行插件
    result = await plugin_manager.execute_plugin("test-plugin", context)

    # 验证结果
    assert result.success is True
    assert result.error is None
    assert "plugin_response" in result.result
    assert "What is the weather?" in result.result["plugin_response"]


@pytest.mark.asyncio
async def test_plugin_results_formatting(plugin_manager, temp_plugin_dir):
    """测试插件结果格式化（用于注入到 system prompt）"""
    from lurkbot.plugins.models import PluginExecutionContext

    # 加载插件
    await plugin_manager.discover_and_load_all(temp_plugin_dir)

    # 执行插件
    context = PluginExecutionContext(
        input_data={"query": "Test query"},
        parameters={},
    )
    plugin_results = await plugin_manager.execute_plugins(context)

    # 格式化结果（模拟 runtime.py 中的逻辑）
    successful_results = [
        (name, result) for name, result in plugin_results.items() if result.success
    ]

    assert len(successful_results) == 1

    # 构造插件结果文本
    plugin_results_text = "\n\n## Plugin Results\n\n"
    plugin_results_text += (
        "The following plugins have been executed to assist with your query:\n\n"
    )

    for name, result in successful_results:
        plugin_results_text += f"### Plugin: {name}\n"
        plugin_results_text += f"- Execution time: {result.execution_time:.2f}s\n"
        plugin_results_text += f"- Result: {result.result}\n\n"

    # 验证格式化结果
    assert "## Plugin Results" in plugin_results_text
    assert "test-plugin" in plugin_results_text
    assert "Execution time:" in plugin_results_text


@pytest.mark.asyncio
async def test_plugin_graceful_degradation(plugin_manager):
    """测试插件失败时的优雅降级"""
    from lurkbot.plugins.models import PluginExecutionContext

    # 尝试执行不存在的插件
    context = PluginExecutionContext(input_data={"query": "test"})
    result = await plugin_manager.execute_plugin("nonexistent-plugin", context)

    # 验证失败被正确处理
    assert result.success is False
    assert result.error is not None
    assert "不存在" in result.error


@pytest.mark.asyncio
async def test_multiple_plugins_execution(plugin_manager, temp_plugin_dir):
    """测试多插件并发执行"""
    from lurkbot.plugins.models import PluginExecutionContext

    # 创建第二个插件
    plugin2_dir = temp_plugin_dir / "plugin2"
    plugin2_dir.mkdir()

    manifest_content = """{
    "name": "plugin2",
    "version": "1.0.0",
    "description": "Second test plugin",
    "author": {"name": "Test Author"},
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
    context = PluginExecutionContext(input_data={"query": "test"})
    results = await plugin_manager.execute_plugins(context)

    # 验证所有插件都执行成功
    assert len(results) == 2
    assert all(r.success for r in results.values())


# ============================================================================
# 模拟 Runtime 集成测试
# ============================================================================


@pytest.mark.asyncio
async def test_simulated_runtime_with_plugins(plugin_manager, temp_plugin_dir):
    """模拟 Agent Runtime 使用插件的完整流程"""
    from lurkbot.plugins.models import PluginExecutionContext

    # Step 1: 加载插件
    await plugin_manager.discover_and_load_all(temp_plugin_dir)

    # Step 2: 模拟用户输入
    user_prompt = "What is the weather in Beijing?"
    system_prompt = "You are a helpful assistant."

    # Step 3: 执行插件
    plugin_context = PluginExecutionContext(
        user_id="user123",
        channel_id="discord-general",
        session_id="session456",
        input_data={"query": user_prompt},
        parameters={},
        metadata={"provider": "anthropic", "model": "claude-sonnet-4"},
    )

    plugin_results = await plugin_manager.execute_plugins(plugin_context)

    # Step 4: 格式化插件结果
    successful_results = [
        (name, result) for name, result in plugin_results.items() if result.success
    ]

    plugin_results_text = ""
    if successful_results:
        plugin_results_text = "\n\n## Plugin Results\n\n"
        for name, result in successful_results:
            plugin_results_text += f"### Plugin: {name}\n"
            plugin_results_text += f"- Result: {result.result}\n\n"

    # Step 5: 注入到 system prompt
    enhanced_system_prompt = system_prompt + plugin_results_text

    # Step 6: 验证增强后的 system prompt
    assert "## Plugin Results" in enhanced_system_prompt
    assert "test-plugin" in enhanced_system_prompt
    assert "Plugin processed: What is the weather in Beijing?" in enhanced_system_prompt

    # Step 7: 模拟 Agent 执行（这里只是验证 prompt 格式）
    # 实际的 Agent 执行会使用 enhanced_system_prompt
    assert len(enhanced_system_prompt) > len(system_prompt)
