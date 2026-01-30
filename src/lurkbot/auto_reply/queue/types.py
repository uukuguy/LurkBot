"""
Auto-Reply Queue Types - 队列类型定义

对标 MoltBot src/auto-reply/queue/types.ts
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal


# 队列模式
QueueMode = Literal[
    "steer",           # 引导模式：等待用户确认
    "followup",        # 跟进模式：主 Agent 后自动执行
    "collect",         # 收集模式：批处理多条消息
    "steer-backlog",   # 引导+积压管理
    "interrupt",       # 中断当前执行
    "queue",           # 标准 FIFO
]

# 丢弃策略
QueueDropPolicy = Literal[
    "old",        # 丢弃最旧
    "new",        # 丢弃最新
    "summarize",  # 总结超出的消息
]


@dataclass
class QueueDirective:
    """
    队列指令

    对标 MoltBot QueueDirective
    """
    cleaned: str
    queue_mode: QueueMode | None = None
    queue_reset: bool = False
    debounce_ms: int | None = None
    cap: int | None = None
    drop_policy: QueueDropPolicy | None = None


@dataclass
class QueueItem:
    """
    队列项

    对标 MoltBot QueueItem
    """
    id: str
    session_key: str
    content: str
    priority: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    metadata: dict = field(default_factory=dict)


@dataclass
class QueueState:
    """
    队列状态

    对标 MoltBot QueueState
    """
    items: list[QueueItem] = field(default_factory=list)
    processing: bool = False
    last_drain_at: datetime | None = None
    total_processed: int = 0
    total_dropped: int = 0
