"""测试插件沙箱

测试 PluginSandbox 的超时控制、权限检查和异常隔离功能。
"""

import asyncio

import pytest

from lurkbot.plugins.models import PluginConfig, PluginExecutionContext
from lurkbot.plugins.sandbox import (
    PluginSandbox,
    check_permission,
    execute_with_timeout,
    sandboxed,
)


# ============================================================================
# 测试函数
# ============================================================================


async def simple_async_func(context: PluginExecutionContext) -> dict:
    """简单的异步测试函数"""
    return {"result": "success", "input": context.input_data}


async def slow_async_func(context: PluginExecutionContext) -> dict:
    """慢速异步测试函数（用于测试超时）"""
    await asyncio.sleep(5)
    return {"result": "success"}


async def error_async_func(context: PluginExecutionContext) -> dict:
    """会抛出异常的测试函数"""
    raise ValueError("Test error")


def simple_sync_func(context: PluginExecutionContext) -> dict:
    """简单的同步测试函数"""
    return {"result": "success", "input": context.input_data}


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def plugin_config():
    """创建测试插件配置"""
    return PluginConfig(
        enabled=True,
        max_execution_time=2.0,
        max_memory_mb=256,
        allow_filesystem=False,
        allow_network=False,
        allow_exec=False,
        allowed_channels=["test-channel"],
    )


@pytest.fixture
def sandbox(plugin_config):
    """创建沙箱实例"""
    return PluginSandbox(config=plugin_config)


@pytest.fixture
def execution_context():
    """创建执行上下文"""
    return PluginExecutionContext(
        user_id="test-user",
        channel_id="test-channel",
        input_data={"test": "data"},
    )


# ============================================================================
# PluginSandbox 基础测试
# ============================================================================


@pytest.mark.asyncio
async def test_sandbox_initialization():
    """测试沙箱初始化"""
    sandbox = PluginSandbox()

    assert sandbox.config is not None
    assert isinstance(sandbox.config, PluginConfig)


@pytest.mark.asyncio
async def test_sandbox_with_custom_config(plugin_config):
    """测试使用自定义配置初始化沙箱"""
    sandbox = PluginSandbox(config=plugin_config)

    assert sandbox.config == plugin_config
    assert sandbox.config.max_execution_time == 2.0
    assert sandbox.config.allow_network is False


# ============================================================================
# 执行功能测试
# ============================================================================


@pytest.mark.asyncio
async def test_execute_async_function(sandbox, execution_context):
    """测试执行异步函数"""
    result = await sandbox.execute(simple_async_func, execution_context)

    assert result.success is True
    assert result.error is None
    assert result.result == {"result": "success", "input": {"test": "data"}}
    assert result.execution_time >= 0


@pytest.mark.asyncio
async def test_execute_sync_function(sandbox, execution_context):
    """测试执行同步函数"""
    result = await sandbox.execute(simple_sync_func, execution_context)

    assert result.success is True
    assert result.error is None
    assert result.result == {"result": "success", "input": {"test": "data"}}
    assert result.execution_time >= 0


# ============================================================================
# 超时控制测试
# ============================================================================


@pytest.mark.asyncio
async def test_execute_timeout(sandbox, execution_context):
    """测试执行超时"""
    result = await sandbox.execute(slow_async_func, execution_context)

    assert result.success is False
    assert result.error is not None
    assert "超时" in result.error
    assert result.metadata.get("timed_out") is True


@pytest.mark.asyncio
async def test_execute_with_timeout_helper():
    """测试 execute_with_timeout 辅助函数"""
    async def quick_task():
        await asyncio.sleep(0.1)
        return "success"

    result = await execute_with_timeout(quick_task(), timeout=1.0)
    assert result == "success"


@pytest.mark.asyncio
async def test_execute_with_timeout_error():
    """测试 execute_with_timeout 超时错误"""
    async def slow_task():
        await asyncio.sleep(5)
        return "success"

    with pytest.raises(TimeoutError) as exc_info:
        await execute_with_timeout(slow_task(), timeout=0.5)

    assert "超时" in str(exc_info.value)


# ============================================================================
# 异常处理测试
# ============================================================================


@pytest.mark.asyncio
async def test_execute_with_exception(sandbox, execution_context):
    """测试执行时的异常处理"""
    result = await sandbox.execute(error_async_func, execution_context)

    assert result.success is False
    assert result.error is not None
    assert "ValueError" in result.error
    assert "Test error" in result.error
    assert result.metadata.get("exception_type") == "ValueError"


# ============================================================================
# 权限检查测试
# ============================================================================


@pytest.mark.asyncio
async def test_permission_check_allowed_channel(sandbox):
    """测试允许的频道权限检查"""
    context = PluginExecutionContext(channel_id="test-channel")

    # 应该不抛出异常
    result = await sandbox.execute(simple_async_func, context)
    assert result.success is True


@pytest.mark.asyncio
async def test_permission_check_denied_channel(sandbox):
    """测试拒绝的频道权限检查"""
    context = PluginExecutionContext(channel_id="unauthorized-channel")

    result = await sandbox.execute(simple_async_func, context)

    assert result.success is False
    assert result.error is not None
    assert "无权访问频道" in result.error
    assert result.metadata.get("permission_denied") is True


@pytest.mark.asyncio
async def test_permission_check_no_channel_restriction():
    """测试无频道限制的权限检查"""
    config = PluginConfig(allowed_channels=[])  # 空列表表示无限制
    sandbox = PluginSandbox(config=config)
    context = PluginExecutionContext(channel_id="any-channel")

    result = await sandbox.execute(simple_async_func, context)
    # 当 allowed_channels 为空时，_check_permissions 不会检查频道权限
    # 所以应该成功执行
    assert result.success is True


# ============================================================================
# check_permission 辅助函数测试
# ============================================================================


def test_check_permission_filesystem():
    """测试文件系统权限检查"""
    config = PluginConfig(allow_filesystem=True)
    assert check_permission(config, "filesystem") is True

    config = PluginConfig(allow_filesystem=False)
    assert check_permission(config, "filesystem") is False


def test_check_permission_network():
    """测试网络权限检查"""
    config = PluginConfig(allow_network=True)
    assert check_permission(config, "network") is True

    config = PluginConfig(allow_network=False)
    assert check_permission(config, "network") is False


def test_check_permission_exec():
    """测试命令执行权限检查"""
    config = PluginConfig(allow_exec=True)
    assert check_permission(config, "exec") is True

    config = PluginConfig(allow_exec=False)
    assert check_permission(config, "exec") is False


def test_check_permission_channel():
    """测试频道权限检查"""
    config = PluginConfig(allowed_channels=["channel1", "channel2"])

    assert check_permission(config, "channel", "channel1") is True
    assert check_permission(config, "channel", "channel2") is True
    assert check_permission(config, "channel", "channel3") is False
    assert check_permission(config, "channel", None) is True  # None 表示不检查


def test_check_permission_unknown_type():
    """测试未知权限类型"""
    config = PluginConfig()
    assert check_permission(config, "unknown") is False


# ============================================================================
# sandboxed 装饰器测试
# ============================================================================


@pytest.mark.asyncio
async def test_sandboxed_decorator_async():
    """测试 sandboxed 装饰器（异步函数）"""

    @sandboxed(timeout=1.0)
    async def decorated_func(context: PluginExecutionContext):
        await asyncio.sleep(0.1)
        return {"result": "success"}

    context = PluginExecutionContext()
    result = await decorated_func(context)

    assert result == {"result": "success"}


@pytest.mark.asyncio
async def test_sandboxed_decorator_timeout():
    """测试 sandboxed 装饰器超时"""

    @sandboxed(timeout=0.5)
    async def slow_func(context: PluginExecutionContext):
        await asyncio.sleep(2)
        return {"result": "success"}

    context = PluginExecutionContext()

    with pytest.raises(TimeoutError) as exc_info:
        await slow_func(context)

    assert "超时" in str(exc_info.value)


def test_sandboxed_decorator_sync():
    """测试 sandboxed 装饰器（同步函数）"""

    @sandboxed(timeout=1.0)
    def decorated_func(context: PluginExecutionContext):
        return {"result": "success"}

    context = PluginExecutionContext()
    result = decorated_func(context)

    assert result == {"result": "success"}
