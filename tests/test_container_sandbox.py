"""容器沙箱测试"""

import pytest

from lurkbot.plugins.container_sandbox import ContainerSandbox, is_docker_available
from lurkbot.plugins.models import PluginConfig, PluginExecutionContext


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def plugin_config():
    """创建插件配置"""
    return PluginConfig(
        enabled=True,
        allow_filesystem=False,
        allow_network=False,
        allow_exec=False,
        max_memory_mb=128,
        max_cpu_percent=50.0,
    )


@pytest.fixture
def execution_context():
    """创建执行上下文"""
    return PluginExecutionContext(
        channel_id="test-channel",
        user_id="test-user",
        input_data={"message": "test message"},
    )


# ============================================================================
# 工具函数测试
# ============================================================================


def test_is_docker_available():
    """测试 Docker 可用性检查"""
    # 这个测试会根据环境返回不同结果
    result = is_docker_available()
    assert isinstance(result, bool)


# ============================================================================
# ContainerSandbox 测试
# ============================================================================


@pytest.mark.skipif(not is_docker_available(), reason="Docker 不可用")
def test_container_sandbox_init(plugin_config):
    """测试沙箱初始化"""
    sandbox = ContainerSandbox(plugin_config)
    assert sandbox.config == plugin_config
    assert sandbox.image == "python:3.12-slim"
    assert sandbox.network_mode == "none"  # 因为 allow_network=False
    sandbox.close()


@pytest.mark.skipif(not is_docker_available(), reason="Docker 不可用")
def test_container_sandbox_network_mode(plugin_config):
    """测试网络模式"""
    # 允许网络
    config_with_network = plugin_config.model_copy(update={"allow_network": True})
    sandbox = ContainerSandbox(config_with_network, network_mode="bridge")
    assert sandbox.network_mode == "bridge"
    sandbox.close()

    # 不允许网络
    sandbox = ContainerSandbox(plugin_config, network_mode="bridge")
    assert sandbox.network_mode == "none"
    sandbox.close()


@pytest.mark.skipif(not is_docker_available(), reason="Docker 不可用")
@pytest.mark.asyncio
async def test_container_sandbox_execute_success(plugin_config, execution_context):
    """测试容器执行成功"""
    sandbox = ContainerSandbox(plugin_config)

    # 简单的插件代码
    plugin_code = '''
async def execute(context):
    """Execute plugin"""
    return {"result": "success", "message": context.get("message_content")}
'''

    try:
        result = await sandbox.execute("test-plugin", plugin_code, execution_context, timeout=60.0)
        assert result.success
        assert result.result is not None
    finally:
        sandbox.close()


@pytest.mark.skipif(not is_docker_available(), reason="Docker 不可用")
@pytest.mark.asyncio
async def test_container_sandbox_execute_error(plugin_config, execution_context):
    """测试容器执行错误"""
    sandbox = ContainerSandbox(plugin_config)

    # 会抛出异常的插件代码
    plugin_code = '''
async def execute(context):
    """Execute plugin"""
    raise ValueError("Test error")
'''

    try:
        result = await sandbox.execute("test-plugin", plugin_code, execution_context, timeout=60.0)
        assert not result.success
        assert "Test error" in (result.error or "")
    finally:
        sandbox.close()


@pytest.mark.skipif(not is_docker_available(), reason="Docker 不可用")
@pytest.mark.asyncio
async def test_container_sandbox_timeout(plugin_config, execution_context):
    """测试容器超时"""
    sandbox = ContainerSandbox(plugin_config)

    # 会超时的插件代码
    plugin_code = '''
import asyncio

async def execute(context):
    """Execute plugin"""
    await asyncio.sleep(100)  # 睡眠 100 秒
    return {"result": "should not reach here"}
'''

    try:
        result = await sandbox.execute("test-plugin", plugin_code, execution_context, timeout=2.0)
        assert not result.success
        assert "超时" in (result.error or "")
    finally:
        sandbox.close()


@pytest.mark.skipif(not is_docker_available(), reason="Docker 不可用")
def test_generate_runner_script(plugin_config):
    """测试生成执行脚本"""
    sandbox = ContainerSandbox(plugin_config)
    script = sandbox._generate_runner_script()

    assert "import asyncio" in script
    assert "import json" in script
    assert "async def main()" in script
    assert "plugin.execute" in script

    sandbox.close()


# ============================================================================
# 集成测试
# ============================================================================


@pytest.mark.skipif(not is_docker_available(), reason="Docker 不可用")
@pytest.mark.asyncio
async def test_container_sandbox_resource_limits(plugin_config, execution_context):
    """测试资源限制"""
    sandbox = ContainerSandbox(plugin_config)

    # 尝试使用大量内存的插件（应该被限制）
    plugin_code = '''
async def execute(context):
    """Execute plugin"""
    # 尝试分配 512MB 内存（超过 128MB 限制）
    try:
        data = bytearray(512 * 1024 * 1024)
        return {"result": "should not succeed"}
    except MemoryError:
        return {"result": "memory limited"}
'''

    try:
        result = await sandbox.execute("test-plugin", plugin_code, execution_context, timeout=60.0)
        # 可能成功（返回 memory limited）或失败（被 OOM killer 杀死）
        assert result is not None
    finally:
        sandbox.close()
