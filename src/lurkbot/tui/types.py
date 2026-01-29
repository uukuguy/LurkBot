"""
TUI 类型定义

对标 MoltBot src/tui/tui.ts 中的类型
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Awaitable

from pydantic import BaseModel


class ActivityStatus(str, Enum):
    """活动状态"""

    IDLE = "idle"
    SENDING = "sending"
    WAITING = "waiting"
    STREAMING = "streaming"


class MessageRole(str, Enum):
    """消息角色"""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class ThinkingLevel(str, Enum):
    """Thinking 级别"""

    OFF = "off"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class TuiState:
    """
    TUI 状态

    对标 MoltBot TuiStateAccess
    """

    # Agent 相关
    agent_default_id: str = "default"
    current_agent_id: str = "default"

    # Session 相关
    session_main_key: str = ""
    current_session_key: str = ""

    # 运行状态
    active_chat_run_id: str | None = None
    is_connected: bool = False
    connection_status: str = "disconnected"
    activity_status: ActivityStatus = ActivityStatus.IDLE

    # UI 状态
    tools_expanded: bool = False
    show_thinking: bool = False
    thinking_level: ThinkingLevel = ThinkingLevel.OFF

    # 模型配置
    current_model: str | None = None


@dataclass
class ChatMessage:
    """聊天消息"""

    id: str
    role: MessageRole
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    thinking: str | None = None
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    tool_results: list[dict[str, Any]] = field(default_factory=list)
    is_streaming: bool = False


@dataclass
class ToolCallDisplay:
    """工具调用显示"""

    id: str
    name: str
    arguments: dict[str, Any]
    status: str = "pending"  # pending, running, completed, failed
    result: Any = None
    error: str | None = None
    expanded: bool = False


class TuiCommand(BaseModel):
    """TUI 命令"""

    model_config = {"arbitrary_types_allowed": True}

    name: str
    aliases: list[str] = []
    description: str = ""
    usage: str = ""
    args: list[str] = []


@dataclass
class TuiCommandResult:
    """命令执行结果"""

    success: bool
    message: str = ""
    data: Any = None
    should_send_to_agent: bool = False
    agent_message: str = ""


# 命令处理器类型
CommandHandler = Callable[["TuiState", list[str]], Awaitable[TuiCommandResult]]


@dataclass
class StreamChunk:
    """流式响应块"""

    run_id: str
    chunk_type: str  # "thinking", "content", "tool_call", "tool_result"
    content: str = ""
    tool_call: ToolCallDisplay | None = None
    is_final: bool = False


@dataclass
class GatewayConnectionInfo:
    """Gateway 连接信息"""

    url: str
    token: str | None = None
    connected: bool = False
    last_ping: datetime | None = None
    latency_ms: float | None = None


# 事件类型
class TuiEventType(str, Enum):
    """TUI 事件类型"""

    # 连接事件
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    CONNECTION_ERROR = "connection_error"

    # 消息事件
    MESSAGE_RECEIVED = "message_received"
    MESSAGE_SENT = "message_sent"
    STREAM_START = "stream_start"
    STREAM_CHUNK = "stream_chunk"
    STREAM_END = "stream_end"

    # 工具事件
    TOOL_CALL_START = "tool_call_start"
    TOOL_CALL_END = "tool_call_end"

    # 命令事件
    COMMAND_EXECUTED = "command_executed"

    # UI 事件
    AGENT_CHANGED = "agent_changed"
    SESSION_CHANGED = "session_changed"
    MODEL_CHANGED = "model_changed"


@dataclass
class TuiEvent:
    """TUI 事件"""

    type: TuiEventType
    data: Any = None
    timestamp: datetime = field(default_factory=datetime.now)


# 颜色主题
@dataclass
class TuiTheme:
    """TUI 主题配色"""

    # 基础颜色
    primary: str = "blue"
    secondary: str = "cyan"
    accent: str = "magenta"

    # 消息颜色
    user_message: str = "green"
    assistant_message: str = "white"
    system_message: str = "yellow"
    error_message: str = "red"

    # 状态颜色
    connected: str = "green"
    disconnected: str = "red"
    streaming: str = "cyan"
    thinking: str = "dim cyan"

    # 工具颜色
    tool_name: str = "yellow"
    tool_running: str = "cyan"
    tool_success: str = "green"
    tool_error: str = "red"

    # 边框
    border: str = "dim"
    border_focused: str = "blue"


# 默认主题
DEFAULT_THEME = TuiTheme()


@dataclass
class TuiConfig:
    """TUI 配置"""

    # Gateway 配置
    gateway_url: str = "ws://localhost:3000"
    gateway_token: str | None = None

    # UI 配置
    theme: TuiTheme = field(default_factory=TuiTheme)
    show_timestamps: bool = False
    show_tool_details: bool = True
    max_history_display: int = 100

    # 行为配置
    auto_scroll: bool = True
    confirm_exit: bool = True
    sound_notifications: bool = False

    # 默认设置
    default_agent_id: str = "default"
    default_thinking_level: ThinkingLevel = ThinkingLevel.OFF
