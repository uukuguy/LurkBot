"""测试插件数据模型

测试 PluginConfig, PluginEvent, PluginExecutionContext, PluginExecutionResult 等数据模型。
"""

from datetime import datetime

import pytest
from pydantic import ValidationError

from lurkbot.plugins.models import (
    PluginConfig,
    PluginEvent,
    PluginEventType,
    PluginExecutionContext,
    PluginExecutionResult,
    PluginStatus,
)


# ============================================================================
# PluginStatus 和 PluginEventType 枚举测试
# ============================================================================


def test_plugin_status_enum():
    """测试插件状态枚举"""
    assert PluginStatus.UNLOADED == "unloaded"
    assert PluginStatus.LOADED == "loaded"
    assert PluginStatus.ENABLED == "enabled"
    assert PluginStatus.DISABLED == "disabled"
    assert PluginStatus.ERROR == "error"


def test_plugin_event_type_enum():
    """测试插件事件类型枚举"""
    assert PluginEventType.LOAD == "load"
    assert PluginEventType.UNLOAD == "unload"
    assert PluginEventType.ENABLE == "enable"
    assert PluginEventType.DISABLE == "disable"
    assert PluginEventType.EXECUTE == "execute"
    assert PluginEventType.ERROR == "error"


# ============================================================================
# PluginConfig 测试
# ============================================================================


def test_plugin_config_default_values():
    """测试 PluginConfig 默认值"""
    config = PluginConfig()

    assert config.enabled is True
    assert config.auto_load is True
    assert config.priority == 100
    assert config.max_execution_time == 30.0
    assert config.max_memory_mb == 512
    assert config.max_cpu_percent == 80.0
    assert config.allow_filesystem is False
    assert config.allow_network is False
    assert config.allow_exec is False
    assert config.allowed_channels == []
    assert config.custom == {}


def test_plugin_config_custom_values():
    """测试 PluginConfig 自定义值"""
    config = PluginConfig(
        enabled=False,
        auto_load=False,
        priority=50,
        max_execution_time=60.0,
        max_memory_mb=1024,
        max_cpu_percent=90.0,
        allow_filesystem=True,
        allow_network=True,
        allow_exec=True,
        allowed_channels=["discord", "slack"],
        custom={"api_key": "test123", "endpoint": "https://api.test.com"},
    )

    assert config.enabled is False
    assert config.auto_load is False
    assert config.priority == 50
    assert config.max_execution_time == 60.0
    assert config.max_memory_mb == 1024
    assert config.max_cpu_percent == 90.0
    assert config.allow_filesystem is True
    assert config.allow_network is True
    assert config.allow_exec is True
    assert config.allowed_channels == ["discord", "slack"]
    assert config.custom == {"api_key": "test123", "endpoint": "https://api.test.com"}


def test_plugin_config_validation():
    """测试 PluginConfig 数据验证"""
    # 测试无效的优先级类型
    with pytest.raises(ValidationError):
        PluginConfig(priority="invalid")  # type: ignore

    # 测试无效的超时时间类型
    with pytest.raises(ValidationError):
        PluginConfig(max_execution_time="invalid")  # type: ignore


# ============================================================================
# PluginEvent 测试
# ============================================================================


def test_plugin_event_creation():
    """测试 PluginEvent 创建"""
    event = PluginEvent(
        plugin_name="test-plugin",
        event_type=PluginEventType.LOAD,
        success=True,
        message="Plugin loaded successfully",
    )

    assert event.plugin_name == "test-plugin"
    assert event.event_type == PluginEventType.LOAD
    assert event.success is True
    assert event.message == "Plugin loaded successfully"
    assert event.error is None
    assert isinstance(event.timestamp, datetime)
    assert event.metadata == {}


def test_plugin_event_with_error():
    """测试带错误信息的 PluginEvent"""
    event = PluginEvent(
        plugin_name="test-plugin",
        event_type=PluginEventType.ERROR,
        success=False,
        error="Failed to load plugin",
        metadata={"error_code": 500},
    )

    assert event.plugin_name == "test-plugin"
    assert event.event_type == PluginEventType.ERROR
    assert event.success is False
    assert event.error == "Failed to load plugin"
    assert event.metadata == {"error_code": 500}


def test_plugin_event_validation():
    """测试 PluginEvent 数据验证"""
    # 缺少必需字段
    with pytest.raises(ValidationError):
        PluginEvent()  # type: ignore

    # 无效的事件类型
    with pytest.raises(ValidationError):
        PluginEvent(plugin_name="test", event_type="invalid")  # type: ignore


# ============================================================================
# PluginExecutionContext 测试
# ============================================================================


def test_plugin_execution_context_default():
    """测试 PluginExecutionContext 默认值"""
    context = PluginExecutionContext()

    assert context.user_id is None
    assert context.channel_id is None
    assert context.session_id is None
    assert context.input_data == {}
    assert context.parameters == {}
    assert context.environment == {}
    assert context.config == {}
    assert context.metadata == {}


def test_plugin_execution_context_with_data():
    """测试带数据的 PluginExecutionContext"""
    context = PluginExecutionContext(
        user_id="user123",
        channel_id="discord-general",
        session_id="session456",
        input_data={"city": "Beijing"},
        parameters={"units": "metric"},
        environment={"API_KEY": "test123"},
        config={"timeout": 10},
        metadata={"request_id": "req789"},
    )

    assert context.user_id == "user123"
    assert context.channel_id == "discord-general"
    assert context.session_id == "session456"
    assert context.input_data == {"city": "Beijing"}
    assert context.parameters == {"units": "metric"}
    assert context.environment == {"API_KEY": "test123"}
    assert context.config == {"timeout": 10}
    assert context.metadata == {"request_id": "req789"}


# ============================================================================
# PluginExecutionResult 测试
# ============================================================================


def test_plugin_execution_result_success():
    """测试成功的 PluginExecutionResult"""
    result = PluginExecutionResult(
        success=True,
        result={"temperature": 25, "condition": "sunny"},
        execution_time=0.5,
        metadata={"cached": False, "api_calls": 1},
    )

    assert result.success is True
    assert result.result == {"temperature": 25, "condition": "sunny"}
    assert result.error is None
    assert result.execution_time == 0.5
    assert result.metadata == {"cached": False, "api_calls": 1}


def test_plugin_execution_result_failure():
    """测试失败的 PluginExecutionResult"""
    result = PluginExecutionResult(
        success=False,
        error="Network timeout",
        execution_time=30.0,
        metadata={"retry_count": 3},
    )

    assert result.success is False
    assert result.result is None
    assert result.error == "Network timeout"
    assert result.execution_time == 30.0
    assert result.metadata == {"retry_count": 3}


def test_plugin_execution_result_validation():
    """测试 PluginExecutionResult 数据验证"""
    # 缺少必需字段
    with pytest.raises(ValidationError):
        PluginExecutionResult()  # type: ignore

    # 无效的执行时间类型
    with pytest.raises(ValidationError):
        PluginExecutionResult(success=True, execution_time="invalid")  # type: ignore
