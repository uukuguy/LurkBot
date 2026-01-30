"""
Auto-Reply Module - 自动回复系统

对标 MoltBot src/auto-reply/
"""

from .tokens import (
    SILENT_REPLY_TOKEN,
    HEARTBEAT_TOKEN,
    is_silent_reply_text,
    is_heartbeat_ok,
    strip_silent_token,
    strip_heartbeat_token,
)

from .directives import (
    ThinkLevel,
    VerboseLevel,
    ReasoningLevel,
    ElevatedLevel,
    DirectiveResult,
    extract_think_directive,
    extract_verbose_directive,
    extract_reasoning_directive,
    extract_elevated_directive,
)

from .queue import (
    QueueMode,
    QueueDropPolicy,
    QueueDirective,
    QueueItem,
    QueueState,
)

__all__ = [
    # Tokens
    "SILENT_REPLY_TOKEN",
    "HEARTBEAT_TOKEN",
    "is_silent_reply_text",
    "is_heartbeat_ok",
    "strip_silent_token",
    "strip_heartbeat_token",
    # Directives
    "ThinkLevel",
    "VerboseLevel",
    "ReasoningLevel",
    "ElevatedLevel",
    "DirectiveResult",
    "extract_think_directive",
    "extract_verbose_directive",
    "extract_reasoning_directive",
    "extract_elevated_directive",
    # Queue
    "QueueMode",
    "QueueDropPolicy",
    "QueueDirective",
    "QueueItem",
    "QueueState",
]
