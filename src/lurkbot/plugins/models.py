"""插件系统数据模型

定义插件配置、状态和事件的数据模型。
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ============================================================================
# 插件状态枚举
# ============================================================================


class PluginStatus(str, Enum):
    """插件状态"""

    UNLOADED = "unloaded"  # 未加载
    LOADED = "loaded"  # 已加载
    ENABLED = "enabled"  # 已启用
    DISABLED = "disabled"  # 已禁用
    ERROR = "error"  # 错误状态


class PluginEventType(str, Enum):
    """插件事件类型"""

    LOAD = "load"  # 加载事件
    UNLOAD = "unload"  # 卸载事件
    ENABLE = "enable"  # 启用事件
    DISABLE = "disable"  # 禁用事件
    EXECUTE = "execute"  # 执行事件
    ERROR = "error"  # 错误事件


# ============================================================================
# 插件配置模型
# ============================================================================


class PluginConfig(BaseModel):
    """插件配置

    用于存储插件的运行时配置。
    """

    # 基本配置
    enabled: bool = Field(True, description="是否启用插件")
    auto_load: bool = Field(True, description="是否自动加载")
    priority: int = Field(100, description="加载优先级（数字越小优先级越高）")

    # 资源限制
    max_execution_time: float = Field(30.0, description="最大执行时间（秒）")
    max_memory_mb: int = Field(512, description="最大内存使用（MB）")
    max_cpu_percent: float = Field(80.0, description="最大 CPU 使用率（%）")

    # 权限配置
    allow_filesystem: bool = Field(False, description="允许文件系统访问")
    allow_network: bool = Field(False, description="允许网络访问")
    allow_exec: bool = Field(False, description="允许命令执行")
    allowed_channels: list[str] = Field(default_factory=list, description="允许访问的频道列表")

    # 自定义配置
    custom: dict[str, Any] = Field(default_factory=dict, description="自定义配置项")

    class Config:
        json_schema_extra = {
            "example": {
                "enabled": True,
                "auto_load": True,
                "priority": 100,
                "max_execution_time": 30.0,
                "max_memory_mb": 512,
                "max_cpu_percent": 80.0,
                "allow_filesystem": False,
                "allow_network": True,
                "allow_exec": False,
                "allowed_channels": ["discord", "slack"],
                "custom": {"api_key": "xxx", "endpoint": "https://api.example.com"},
            }
        }


# ============================================================================
# 插件事件模型
# ============================================================================


class PluginEvent(BaseModel):
    """插件事件

    记录插件生命周期中的重要事件。
    """

    plugin_name: str = Field(..., description="插件名称")
    event_type: PluginEventType = Field(..., description="事件类型")
    timestamp: datetime = Field(default_factory=datetime.now, description="事件时间")
    success: bool = Field(True, description="是否成功")
    message: str | None = Field(None, description="事件消息")
    error: str | None = Field(None, description="错误信息")
    metadata: dict[str, Any] = Field(default_factory=dict, description="事件元数据")

    class Config:
        json_schema_extra = {
            "example": {
                "plugin_name": "weather-plugin",
                "event_type": "execute",
                "timestamp": "2026-01-31T12:00:00",
                "success": True,
                "message": "Plugin executed successfully",
                "error": None,
                "metadata": {"execution_time": 0.5, "result": "sunny"},
            }
        }


# ============================================================================
# 插件执行上下文
# ============================================================================


class PluginExecutionContext(BaseModel):
    """插件执行上下文

    传递给插件执行方法的上下文信息。
    """

    # 请求信息
    user_id: str | None = Field(None, description="用户 ID")
    channel_id: str | None = Field(None, description="频道 ID")
    session_id: str | None = Field(None, description="会话 ID")

    # 输入数据
    input_data: dict[str, Any] = Field(default_factory=dict, description="输入数据")
    parameters: dict[str, Any] = Field(default_factory=dict, description="执行参数")

    # 环境信息
    environment: dict[str, Any] = Field(default_factory=dict, description="环境变量")
    config: dict[str, Any] = Field(default_factory=dict, description="插件配置")

    # 元数据
    metadata: dict[str, Any] = Field(default_factory=dict, description="额外元数据")

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user123",
                "channel_id": "discord-general",
                "session_id": "session456",
                "input_data": {"city": "Beijing"},
                "parameters": {"units": "metric"},
                "environment": {"API_KEY": "xxx"},
                "config": {"timeout": 10},
                "metadata": {"request_id": "req789"},
            }
        }


# ============================================================================
# 插件执行结果
# ============================================================================


class PluginExecutionResult(BaseModel):
    """插件执行结果

    插件执行后返回的结果。
    """

    success: bool = Field(..., description="是否成功")
    result: Any = Field(None, description="执行结果")
    error: str | None = Field(None, description="错误信息")
    execution_time: float = Field(..., description="执行时间（秒）")
    metadata: dict[str, Any] = Field(default_factory=dict, description="结果元数据")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "result": {"temperature": 25, "condition": "sunny"},
                "error": None,
                "execution_time": 0.5,
                "metadata": {"cached": False, "api_calls": 1},
            }
        }
