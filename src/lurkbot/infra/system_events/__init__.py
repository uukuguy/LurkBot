"""System Events Queue.

轻量级内存事件总线，用于向提示词前缀添加人类可读的系统事件。

对标 MoltBot `src/infra/system-events.ts`
"""

from collections import defaultdict
from datetime import datetime

from .types import SessionQueue, SystemEvent

# 每个会话最多保留 20 条事件
MAX_EVENTS_PER_SESSION = 20

__all__ = [
    "SystemEvent",
    "SessionQueue",
    "MAX_EVENTS_PER_SESSION",
    "SystemEventQueue",
    "system_event_queue",
    "enqueue_system_event",
    "drain_system_event_entries",
    "drain_system_events",
    "peek_system_events",
    "has_system_events",
    "is_system_event_context_changed",
]


class SystemEventQueue:
    """
    系统事件队列管理器。

    为每个会话维护一个事件队列，自动去重连续相同事件，
    保持最多 MAX_EVENTS_PER_SESSION 条事件。

    对标 MoltBot system-events.ts
    """

    def __init__(self) -> None:
        self._queues: dict[str, SessionQueue] = defaultdict(SessionQueue)

    def enqueue(
        self,
        session_key: str,
        text: str,
        *,
        ts: datetime | None = None,
    ) -> None:
        """
        入队事件。

        自动去重连续相同事件，保持最多 MAX_EVENTS_PER_SESSION 条。

        Args:
            session_key: 会话标识符
            text: 事件文本
            ts: 事件时间戳（可选，默认当前时间）
        """
        queue = self._queues[session_key]

        # 去重连续相同事件
        if queue.last_event_text == text:
            return

        queue.last_event_text = text
        event = SystemEvent(text=text, ts=ts or datetime.now())
        queue.events.append(event)

        # 保持最多 MAX_EVENTS_PER_SESSION 条（环形缓冲）
        if len(queue.events) > MAX_EVENTS_PER_SESSION:
            queue.events = queue.events[-MAX_EVENTS_PER_SESSION:]

    def drain(self, session_key: str) -> list[SystemEvent]:
        """
        出队并返回所有事件，清空队列。

        Args:
            session_key: 会话标识符

        Returns:
            所有事件列表
        """
        if session_key not in self._queues:
            return []

        queue = self._queues.pop(session_key)
        return queue.events

    def drain_texts(self, session_key: str) -> list[str]:
        """
        出队并返回所有事件文本，清空队列。

        Args:
            session_key: 会话标识符

        Returns:
            所有事件文本列表
        """
        return [e.text for e in self.drain(session_key)]

    def peek(self, session_key: str) -> list[SystemEvent]:
        """
        只读获取所有事件，不清空队列。

        Args:
            session_key: 会话标识符

        Returns:
            所有事件列表
        """
        return list(self._queues[session_key].events)

    def peek_texts(self, session_key: str) -> list[str]:
        """
        只读获取所有事件文本，不清空队列。

        Args:
            session_key: 会话标识符

        Returns:
            所有事件文本列表
        """
        return [e.text for e in self.peek(session_key)]

    def has_events(self, session_key: str) -> bool:
        """
        检查会话是否有待处理的事件。

        Args:
            session_key: 会话标识符

        Returns:
            是否有事件
        """
        return len(self._queues[session_key].events) > 0

    def is_context_changed(self, session_key: str, context_key: str) -> bool:
        """
        检查上下文是否发生变化。

        Args:
            session_key: 会话标识符
            context_key: 当前上下文键

        Returns:
            上下文是否变化
        """
        queue = self._queues[session_key]
        changed = queue.last_context_key != context_key
        queue.last_context_key = context_key
        return changed

    def clear(self, session_key: str) -> None:
        """
        清空指定会话的事件队列。

        Args:
            session_key: 会话标识符
        """
        if session_key in self._queues:
            del self._queues[session_key]

    def clear_all(self) -> None:
        """清空所有会话的事件队列。"""
        self._queues.clear()

    def get_queue_count(self) -> int:
        """获取活跃队列数量。"""
        return len(self._queues)

    def get_event_count(self, session_key: str) -> int:
        """获取指定会话的事件数量。"""
        return len(self._queues[session_key].events)


# 全局实例
system_event_queue = SystemEventQueue()


# 便捷函数（对标 MoltBot 导出的函数）
def enqueue_system_event(
    text: str,
    *,
    session_key: str | None = None,
    ts: datetime | None = None,
) -> None:
    """
    入队系统事件。

    Args:
        text: 事件文本
        session_key: 会话标识符（默认 "default"）
        ts: 事件时间戳（可选）
    """
    system_event_queue.enqueue(session_key or "default", text, ts=ts)


def drain_system_event_entries(session_key: str | None = None) -> list[SystemEvent]:
    """
    出队并返回所有事件条目。

    Args:
        session_key: 会话标识符（默认 "default"）

    Returns:
        所有事件条目列表
    """
    return system_event_queue.drain(session_key or "default")


def drain_system_events(session_key: str | None = None) -> list[str]:
    """
    出队并返回所有事件文本。

    Args:
        session_key: 会话标识符（默认 "default"）

    Returns:
        所有事件文本列表
    """
    return system_event_queue.drain_texts(session_key or "default")


def peek_system_events(session_key: str | None = None) -> list[str]:
    """
    只读获取所有事件文本。

    Args:
        session_key: 会话标识符（默认 "default"）

    Returns:
        所有事件文本列表
    """
    return system_event_queue.peek_texts(session_key or "default")


def has_system_events(session_key: str | None = None) -> bool:
    """
    检查是否有待处理的事件。

    Args:
        session_key: 会话标识符（默认 "default"）

    Returns:
        是否有事件
    """
    return system_event_queue.has_events(session_key or "default")


def is_system_event_context_changed(
    context_key: str,
    *,
    session_key: str | None = None,
) -> bool:
    """
    检查上下文是否发生变化。

    Args:
        context_key: 当前上下文键
        session_key: 会话标识符（默认 "default"）

    Returns:
        上下文是否变化
    """
    return system_event_queue.is_context_changed(session_key or "default", context_key)
