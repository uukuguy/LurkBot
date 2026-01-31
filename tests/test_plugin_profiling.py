"""插件性能分析系统测试"""

import asyncio
import time

import pytest

from lurkbot.plugins.profiling import (
    MetricType,
    PerformanceProfiler,
    get_profiler,
    reset_profiler,
)


@pytest.fixture
def profiler():
    """创建性能分析器实例"""
    reset_profiler()
    return PerformanceProfiler()


@pytest.fixture(autouse=True)
def cleanup():
    """测试后清理"""
    yield
    reset_profiler()


# ============================================================================
# 基础功能测试
# ============================================================================


@pytest.mark.asyncio
async def test_start_profiling(profiler):
    """测试开始性能分析"""
    session_id = await profiler.start_profiling("test-plugin")

    assert session_id.startswith("test-plugin_")
    assert session_id in profiler._active_profiles


@pytest.mark.asyncio
async def test_stop_profiling(profiler):
    """测试停止性能分析"""
    session_id = await profiler.start_profiling("test-plugin")

    # 模拟一些工作
    await asyncio.sleep(0.1)

    profile = await profiler.stop_profiling(session_id, success=True)

    assert profile.plugin_name == "test-plugin"
    assert profile.execution_time > 0
    assert profile.success
    assert session_id not in profiler._active_profiles


@pytest.mark.asyncio
async def test_stop_profiling_with_error(profiler):
    """测试停止性能分析（带错误）"""
    session_id = await profiler.start_profiling("test-plugin")

    profile = await profiler.stop_profiling(
        session_id, success=False, error="Test error"
    )

    assert not profile.success
    assert profile.error == "Test error"


@pytest.mark.asyncio
async def test_stop_profiling_invalid_session(profiler):
    """测试停止无效会话"""
    with pytest.raises(ValueError):
        await profiler.stop_profiling("invalid-session")


# ============================================================================
# 函数执行分析测试
# ============================================================================


@pytest.mark.asyncio
async def test_profile_execution_sync(profiler):
    """测试分析同步函数执行"""

    def sync_func(x, y):
        time.sleep(0.05)
        return x + y

    result, profile = await profiler.profile_execution("test-plugin", sync_func, 1, 2)

    assert result == 3
    assert profile.plugin_name == "test-plugin"
    assert profile.execution_time > 0.05
    assert profile.success


@pytest.mark.asyncio
async def test_profile_execution_async(profiler):
    """测试分析异步函数执行"""

    async def async_func(x, y):
        await asyncio.sleep(0.05)
        return x + y

    result, profile = await profiler.profile_execution("test-plugin", async_func, 1, 2)

    assert result == 3
    assert profile.plugin_name == "test-plugin"
    assert profile.execution_time > 0.05
    assert profile.success


@pytest.mark.asyncio
async def test_profile_execution_with_exception(profiler):
    """测试分析抛出异常的函数"""

    async def failing_func():
        raise ValueError("Test error")

    with pytest.raises(ValueError):
        await profiler.profile_execution("test-plugin", failing_func)

    # 检查是否记录了失败
    profiles = profiler.get_profiles("test-plugin")
    assert len(profiles) == 1
    assert not profiles[0].success
    assert profiles[0].error == "Test error"


# ============================================================================
# 数据查询测试
# ============================================================================


@pytest.mark.asyncio
async def test_get_profiles(profiler):
    """测试获取性能分析记录"""
    session_id = await profiler.start_profiling("test-plugin")
    await profiler.stop_profiling(session_id)

    profiles = profiler.get_profiles("test-plugin")

    assert len(profiles) == 1
    assert profiles[0].plugin_name == "test-plugin"


@pytest.mark.asyncio
async def test_get_profiles_limit(profiler):
    """测试获取性能分析记录（限制数量）"""
    # 创建多个分析记录
    for _ in range(5):
        session_id = await profiler.start_profiling("test-plugin")
        await profiler.stop_profiling(session_id)

    profiles = profiler.get_profiles("test-plugin", limit=3)

    assert len(profiles) == 3


@pytest.mark.asyncio
async def test_get_metrics(profiler):
    """测试获取性能指标"""
    session_id = await profiler.start_profiling("test-plugin")
    await profiler.stop_profiling(session_id)

    metrics = profiler.get_metrics("test-plugin")

    # 应该有 3 个指标：execution_time, cpu_usage, memory_usage
    assert len(metrics) >= 3


@pytest.mark.asyncio
async def test_get_metrics_by_type(profiler):
    """测试按类型获取性能指标"""
    session_id = await profiler.start_profiling("test-plugin")
    await profiler.stop_profiling(session_id)

    metrics = profiler.get_metrics("test-plugin", metric_type=MetricType.EXECUTION_TIME)

    assert len(metrics) == 1
    assert metrics[0].metric_type == MetricType.EXECUTION_TIME


# ============================================================================
# 性能报告测试
# ============================================================================


@pytest.mark.asyncio
async def test_generate_report(profiler):
    """测试生成性能报告"""
    # 创建多个分析记录
    for _ in range(3):
        session_id = await profiler.start_profiling("test-plugin")
        await asyncio.sleep(0.01)
        await profiler.stop_profiling(session_id, success=True)

    report = profiler.generate_report("test-plugin")

    assert report.plugin_name == "test-plugin"
    assert report.total_executions == 3
    assert report.successful_executions == 3
    assert report.failed_executions == 0
    assert report.avg_execution_time > 0


@pytest.mark.asyncio
async def test_generate_report_empty(profiler):
    """测试生成空报告"""
    report = profiler.generate_report("nonexistent")

    assert report.plugin_name == "nonexistent"
    assert report.total_executions == 0


@pytest.mark.asyncio
async def test_generate_report_with_failures(profiler):
    """测试生成包含失败的报告"""
    # 成功执行
    session_id = await profiler.start_profiling("test-plugin")
    await profiler.stop_profiling(session_id, success=True)

    # 失败执行
    session_id = await profiler.start_profiling("test-plugin")
    await profiler.stop_profiling(session_id, success=False, error="Test error")

    report = profiler.generate_report("test-plugin")

    assert report.total_executions == 2
    assert report.successful_executions == 1
    assert report.failed_executions == 1


# ============================================================================
# 瓶颈分析测试
# ============================================================================


@pytest.mark.asyncio
async def test_identify_bottlenecks(profiler):
    """测试识别性能瓶颈"""
    # 创建多个分析记录，其中一些较慢
    for i in range(10):
        session_id = await profiler.start_profiling("test-plugin")
        if i < 2:
            await asyncio.sleep(0.1)  # 慢执行
        else:
            await asyncio.sleep(0.01)  # 正常执行
        await profiler.stop_profiling(session_id)

    bottlenecks = profiler.identify_bottlenecks("test-plugin", threshold_percentile=0.8)

    assert bottlenecks["plugin_name"] == "test-plugin"
    assert len(bottlenecks["bottlenecks"]) > 0


@pytest.mark.asyncio
async def test_identify_bottlenecks_empty(profiler):
    """测试识别空数据的瓶颈"""
    bottlenecks = profiler.identify_bottlenecks("nonexistent")

    assert bottlenecks["plugin_name"] == "nonexistent"
    assert bottlenecks["bottlenecks"] == []


# ============================================================================
# 插件比较测试
# ============================================================================


@pytest.mark.asyncio
async def test_compare_plugins(profiler):
    """测试比较多个插件性能"""
    # 为两个插件创建分析记录
    for plugin in ["plugin-1", "plugin-2"]:
        session_id = await profiler.start_profiling(plugin)
        await profiler.stop_profiling(session_id)

    reports = profiler.compare_plugins(["plugin-1", "plugin-2"])

    assert len(reports) == 2
    assert "plugin-1" in reports
    assert "plugin-2" in reports


# ============================================================================
# 数据清理测试
# ============================================================================


@pytest.mark.asyncio
async def test_clear_data_specific_plugin(profiler):
    """测试清空特定插件数据"""
    session_id = await profiler.start_profiling("test-plugin")
    await profiler.stop_profiling(session_id)

    count = profiler.clear_data("test-plugin")

    assert count == 1
    assert len(profiler.get_profiles("test-plugin")) == 0


@pytest.mark.asyncio
async def test_clear_data_all(profiler):
    """测试清空所有数据"""
    # 为多个插件创建数据
    for plugin in ["plugin-1", "plugin-2"]:
        session_id = await profiler.start_profiling(plugin)
        await profiler.stop_profiling(session_id)

    count = profiler.clear_data()

    assert count == 2
    assert len(profiler._profiles) == 0
    assert len(profiler._metrics) == 0


# ============================================================================
# 全局单例测试
# ============================================================================


def test_get_profiler_singleton():
    """测试全局单例"""
    reset_profiler()

    prof1 = get_profiler()
    prof2 = get_profiler()

    assert prof1 is prof2


def test_reset_profiler():
    """测试重置全局单例"""
    prof1 = get_profiler()

    reset_profiler()

    prof2 = get_profiler()
    assert prof1 is not prof2
