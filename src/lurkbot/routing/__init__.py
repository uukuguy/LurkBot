"""
Routing Module - 消息路由系统

对标 MoltBot src/routing/
"""

from .session_key import build_session_key
from .router import (
    RoutingContext,
    RoutingBinding,
    AgentConfig,
    resolve_agent_for_message,
)

__all__ = [
    "build_session_key",
    "RoutingContext",
    "RoutingBinding",
    "AgentConfig",
    "resolve_agent_for_message",
]
