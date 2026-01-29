"""
LurkBot TUI 终端界面模块

对标 MoltBot src/tui/

提供交互式终端界面功能：
- 实时聊天
- 命令处理
- 流式响应显示
- 多 Agent 支持
"""

from .types import (
    # 状态和配置
    ActivityStatus,
    MessageRole,
    ThinkingLevel,
    TuiState,
    TuiConfig,
    TuiTheme,
    DEFAULT_THEME,
    # 消息
    ChatMessage,
    ToolCallDisplay,
    StreamChunk,
    # 命令
    TuiCommand,
    TuiCommandResult,
    # 事件
    TuiEventType,
    TuiEvent,
    # 连接
    GatewayConnectionInfo,
)

from .stream_assembler import TuiStreamAssembler

from .formatters import TuiFormatter

from .keybindings import (
    KeyAction,
    KeyBinding,
    KeyBindingManager,
    DEFAULT_KEYBINDINGS,
)

from .gateway_chat import GatewayChat

from .commands import CommandHandler

from .events import (
    TuiEventHandler,
    EventHandlerConfig,
    InputHistory,
)

from .components import (
    ChatLog,
    ChatLogConfig,
    ThinkingIndicator,
    ThinkingConfig,
    StreamingIndicator,
    InputBox,
    InputBoxConfig,
    CommandCompleter,
)

from .app import (
    TuiApp,
    TuiAppConfig,
    run_tui,
    main,
)

__all__ = [
    # Types - 状态和配置
    "ActivityStatus",
    "MessageRole",
    "ThinkingLevel",
    "TuiState",
    "TuiConfig",
    "TuiTheme",
    "DEFAULT_THEME",
    # Types - 消息
    "ChatMessage",
    "ToolCallDisplay",
    "StreamChunk",
    # Types - 命令
    "TuiCommand",
    "TuiCommandResult",
    # Types - 事件
    "TuiEventType",
    "TuiEvent",
    # Types - 连接
    "GatewayConnectionInfo",
    # Stream Assembler
    "TuiStreamAssembler",
    # Formatters
    "TuiFormatter",
    # Keybindings
    "KeyAction",
    "KeyBinding",
    "KeyBindingManager",
    "DEFAULT_KEYBINDINGS",
    # Gateway Chat
    "GatewayChat",
    # Commands
    "CommandHandler",
    # Events
    "TuiEventHandler",
    "EventHandlerConfig",
    "InputHistory",
    # Components
    "ChatLog",
    "ChatLogConfig",
    "ThinkingIndicator",
    "ThinkingConfig",
    "StreamingIndicator",
    "InputBox",
    "InputBoxConfig",
    "CommandCompleter",
    # App
    "TuiApp",
    "TuiAppConfig",
    "run_tui",
    "main",
]
