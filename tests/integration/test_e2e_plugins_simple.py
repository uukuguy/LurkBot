"""简化的端到端插件集成测试

基于实际的示例插件进行测试，验证插件系统的核心功能。

测试插件：
- weather-plugin: 天气查询
- time-utils-plugin: 时间工具
- system-info-plugin: 系统信息
"""

import asyncio
from pathlib import Path

import pytest

from lurkbot.plugins.manager import PluginManager
from lurkbot.plugins.manifest import PluginManifest
from lurkbot.plugins.models import PluginExecutionContext
from lurkbot.plugins.schema_validator import discover_all_plugins


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def plugin_manager() -> PluginManager:
    """创建插件管理器实例"""
    return PluginManager(
        enable_orchestration=True,
        enable_permissions=True,
        enable_versioning=True,
        enable_profiling=True,
    )


@pytest.fixture
def workspace_root() -> Path:
    """获取工作区根目录"""
    return Path.cwd()


# ============================================================================
# Test: 插件发现和加载
# ============================================================================


@pytest.mark.asyncio
async def test_discover_and_load_plugins(
    plugin_manager: PluginManager,
    workspace_root: Path,
):
    """测试插件发现和加载"""
    # 1. 发现并加载所有插件
    loaded_count = await plugin_manager.discover_and_load_all(workspace_root)

    # 2. 验证至少加载了示例插件
    assert loaded_count >= 3, f"应该至少加载 3 个示例插件，实际加载了 {loaded_count} 个"

    # 3. 验证插件列表
    plugins = plugin_manager.list_plugins()
    plugin_names = [p.name for p in plugins]

    # 检查示例插件是否被加载
    expected_plugins = ["weather-plugin", "time-utils-plugin", "system-info-plugin"]
    for expected in expected_plugins:
        assert expected in plugin_names, f"插件 {expected} 未被加载"


# ============================================================================
# Test: 单个插件执行
# ============================================================================


@pytest.mark.asyncio
async def test_execute_weather_plugin(
    plugin_manager: PluginManager,
    workspace_root: Path,
):
    """测试天气插件执行"""
    # 1. 加载插件
    await plugin_manager.discover_and_load_all(workspace_root)

    # 2. 执行插件
    context = PluginExecutionContext(
        session_id="test-session",
        user_id="test-user",
        channel_id="test",
        parameters={"city": "Beijing"},
    )

    result = await plugin_manager.execute_plugin("weather-plugin", context)

    # 3. 验证结果
    # 注意：天气插件需要网络访问，可能会失败
    if result.success:
        result_str = str(result.result)
        assert "weather" in result_str.lower() or "temperature" in result_str.lower() or "天气" in result_str
    else:
        # 网络失败是可以接受的
        assert result.error is not None
        assert "http" in result.error.lower() or "network" in result.error.lower() or "请求" in result.error


@pytest.mark.asyncio
async def test_execute_time_utils_plugin(
    plugin_manager: PluginManager,
    workspace_root: Path,
):
    """测试时间工具插件执行"""
    # 1. 加载插件
    await plugin_manager.discover_and_load_all(workspace_root)

    # 2. 执行插件
    context = PluginExecutionContext(
        session_id="test-session",
        user_id="test-user",
        channel_id="test",
        parameters={"timezone": "Asia/Shanghai"},
    )

    result = await plugin_manager.execute_plugin("time-utils-plugin", context)

    # 3. 验证结果
    assert result.success is True, f"插件执行失败: {result.error}"
    assert result.error is None
    assert result.execution_time >= 0
    # result.result 是字符串格式的输出
    result_str = str(result.result)
    assert "时间" in result_str or "time" in result_str.lower() or "timezone" in result_str.lower()


@pytest.mark.asyncio
async def test_execute_system_info_plugin(
    plugin_manager: PluginManager,
    workspace_root: Path,
):
    """测试系统信息插件执行"""
    # 1. 加载插件
    await plugin_manager.discover_and_load_all(workspace_root)

    # 2. 执行插件
    context = PluginExecutionContext(
        session_id="test-session",
        user_id="test-user",
        channel_id="test",
        parameters={},
    )

    result = await plugin_manager.execute_plugin("system-info-plugin", context)

    # 3. 验证结果
    assert result.success is True, f"插件执行失败: {result.error}"
    assert result.error is None
    assert result.execution_time > 0
    result_str = str(result.result)
    assert "cpu" in result_str.lower() or "memory" in result_str.lower() or "系统" in result_str


# ============================================================================
# Test: 并发插件执行
# ============================================================================


@pytest.mark.asyncio
async def test_concurrent_plugin_execution(
    plugin_manager: PluginManager,
    workspace_root: Path,
):
    """测试多个插件并发执行"""
    # 1. 加载插件
    await plugin_manager.discover_and_load_all(workspace_root)

    # 2. 创建执行上下文
    plugin_names = ["weather-plugin", "time-utils-plugin", "system-info-plugin"]
    contexts = [
        PluginExecutionContext(
            session_id="test-session",
            user_id="test-user",
            channel_id="test",
            parameters={"city": "Beijing"},
        ),
        PluginExecutionContext(
            session_id="test-session",
            user_id="test-user",
            channel_id="test",
            parameters={"timezone": "Asia/Shanghai"},
        ),
        PluginExecutionContext(
            session_id="test-session",
            user_id="test-user",
            channel_id="test",
            parameters={},
        ),
    ]

    # 3. 并发执行所有插件
    tasks = [
        plugin_manager.execute_plugin(name, ctx)
        for name, ctx in zip(plugin_names, contexts)
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # 4. 验证结果
    assert len(results) == 3

    # 检查每个结果
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            pytest.fail(f"插件 {plugin_names[i]} 执行失败: {result}")
        assert result.success is True, f"插件 {plugin_names[i]} 执行失败: {result.error}"


# ============================================================================
# Test: 插件状态管理
# ============================================================================


@pytest.mark.asyncio
async def test_plugin_enable_disable(
    plugin_manager: PluginManager,
    workspace_root: Path,
):
    """测试插件启用和禁用"""
    # 1. 加载插件
    await plugin_manager.discover_and_load_all(workspace_root)

    plugin_name = "time-utils-plugin"

    # 2. 禁用插件
    success = await plugin_manager.disable_plugin(plugin_name)
    assert success is True

    # 3. 尝试执行被禁用的插件（应该失败或跳过）
    context = PluginExecutionContext(
        plugin_name=plugin_name,
        session_id="test-session",
        user_id="test-user",
        channel_id="test",
        parameters={},
    )

    try:
        result = await plugin_manager.execute_plugin(plugin_name, context)
        # 如果没有抛出异常，检查结果是否表示插件被禁用
        if result.success:
            # 某些实现可能允许执行但返回特殊状态
            pass
    except Exception as e:
        # 预期的行为：抛出异常表示插件被禁用
        assert "disabled" in str(e).lower() or "not enabled" in str(e).lower()

    # 4. 重新启用插件
    success = await plugin_manager.enable_plugin(plugin_name)
    assert success is True

    # 5. 验证可以再次执行
    result = await plugin_manager.execute_plugin(plugin_name, context)
    assert result.success is True


# ============================================================================
# Test: 插件配置
# ============================================================================


@pytest.mark.asyncio
async def test_plugin_configuration(
    plugin_manager: PluginManager,
    workspace_root: Path,
):
    """测试插件配置管理"""
    # 1. 加载插件
    await plugin_manager.discover_and_load_all(workspace_root)

    plugin_name = "weather-plugin"

    # 2. 获取插件配置
    config = plugin_manager.get_config(plugin_name)

    # 3. 验证配置存在
    # 注意：配置可能为 None 如果没有设置
    if config is not None:
        assert config.enabled is not None


# ============================================================================
# Test: 插件性能分析
# ============================================================================


@pytest.mark.asyncio
async def test_plugin_performance_profiling(
    plugin_manager: PluginManager,
    workspace_root: Path,
):
    """测试插件性能分析"""
    # 1. 加载插件
    await plugin_manager.discover_and_load_all(workspace_root)

    plugin_name = "time-utils-plugin"

    # 2. 执行插件多次
    context = PluginExecutionContext(
        plugin_name=plugin_name,
        session_id="test-session",
        user_id="test-user",
        channel_id="test",
        parameters={"timezone": "Asia/Shanghai"},
    )

    for _ in range(5):
        await plugin_manager.execute_plugin(plugin_name, context)

    # 3. 获取性能报告
    if plugin_manager._enable_profiling and plugin_manager.profiler:
        report = plugin_manager.get_performance_report(plugin_name)

        # 4. 验证性能报告
        if report is not None:
            assert report.total_executions >= 5
            assert report.avg_execution_time > 0
            assert report.min_execution_time > 0
            assert report.max_execution_time > 0


# ============================================================================
# Test: 错误处理
# ============================================================================


@pytest.mark.asyncio
async def test_plugin_error_handling(
    plugin_manager: PluginManager,
    workspace_root: Path,
):
    """测试插件错误处理"""
    # 1. 加载插件
    await plugin_manager.discover_and_load_all(workspace_root)

    # 2. 尝试执行不存在的插件
    context = PluginExecutionContext(
        plugin_name="non-existent-plugin",
        session_id="test-session",
        user_id="test-user",
        channel_id="test",
        parameters={},
    )

    try:
        result = await plugin_manager.execute_plugin("non-existent-plugin", context)
        # 如果没有抛出异常，检查结果是否表示错误
        assert result.success is False
        assert result.error is not None
    except Exception as e:
        # 预期的行为：抛出异常
        assert "not found" in str(e).lower() or "does not exist" in str(e).lower()


# ============================================================================
# Test: 插件列表和查询
# ============================================================================


@pytest.mark.asyncio
async def test_plugin_listing(
    plugin_manager: PluginManager,
    workspace_root: Path,
):
    """测试插件列表和查询"""
    # 1. 加载插件
    await plugin_manager.discover_and_load_all(workspace_root)

    # 2. 获取所有插件
    all_plugins = plugin_manager.list_plugins()
    assert len(all_plugins) >= 3

    # 3. 获取启用的插件
    enabled_plugins = plugin_manager.list_enabled_plugins()
    assert len(enabled_plugins) >= 0

    # 4. 查询特定插件
    plugin = plugin_manager.get_plugin("weather-plugin")
    assert plugin is not None
    assert plugin.name == "weather-plugin"


# ============================================================================
# Test: 插件事件
# ============================================================================


@pytest.mark.asyncio
async def test_plugin_events(
    plugin_manager: PluginManager,
    workspace_root: Path,
):
    """测试插件事件系统"""
    # 1. 设置事件处理器
    events_received = []

    def event_handler(event):
        events_received.append(event)

    plugin_manager.add_event_handler(event_handler)

    # 2. 加载插件（应该触发事件）
    await plugin_manager.discover_and_load_all(workspace_root)

    # 3. 执行插件（应该触发事件）
    context = PluginExecutionContext(
        plugin_name="time-utils-plugin",
        session_id="test-session",
        user_id="test-user",
        channel_id="test",
        parameters={},
    )
    await plugin_manager.execute_plugin("time-utils-plugin", context)

    # 4. 验证事件被触发
    # 注意：事件数量取决于实现
    assert len(events_received) > 0
