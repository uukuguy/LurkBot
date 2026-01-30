"""System Events types.

对标 MoltBot `src/infra/system-events.ts`
"""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class SystemEvent:
    """系统事件条目"""

    text: str
    ts: datetime = field(default_factory=datetime.now)


@dataclass
class SessionQueue:
    """会话事件队列状态"""

    events: list[SystemEvent] = field(default_factory=list)
    last_event_text: str | None = None
    last_context_key: str | None = None
