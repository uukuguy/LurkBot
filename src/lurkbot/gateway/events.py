"""
Gateway 事件广播系统

对标 MoltBot src/gateway/events.ts
"""

import asyncio
import time
from typing import Callable, Awaitable
from dataclasses import dataclass, field
from loguru import logger

from lurkbot.gateway.protocol.frames import EventFrame


@dataclass
class EventSubscriber:
    """事件订阅者"""

    callback: Callable[[EventFrame], Awaitable[None]]
    session_key: str | None = None  # None = 订阅所有事件
    event_filter: str | None = None  # None = 订阅所有事件类型


class EventBroadcaster:
    """
    事件广播器

    对标 MoltBot EventEmitter
    """

    def __init__(self):
        self._subscribers: list[EventSubscriber] = []
        self._event_id_counter = 0
        self._lock = asyncio.Lock()

    def _generate_event_id(self) -> str:
        """生成事件 ID"""
        self._event_id_counter += 1
        return f"evt_{self._event_id_counter:08x}"

    def subscribe(
        self,
        callback: Callable[[EventFrame], Awaitable[None]],
        session_key: str | None = None,
        event_filter: str | None = None,
    ) -> EventSubscriber:
        """订阅事件"""
        subscriber = EventSubscriber(
            callback=callback,
            session_key=session_key,
            event_filter=event_filter,
        )
        self._subscribers.append(subscriber)
        logger.debug(f"Added event subscriber (session={session_key}, filter={event_filter})")
        return subscriber

    def unsubscribe(self, subscriber: EventSubscriber) -> None:
        """取消订阅"""
        if subscriber in self._subscribers:
            self._subscribers.remove(subscriber)
            logger.debug("Removed event subscriber")

    async def emit(
        self,
        event: str,
        payload: dict | None = None,
        session_key: str | None = None,
    ) -> EventFrame:
        """发送事件"""
        event_frame = EventFrame(
            id=self._generate_event_id(),
            at=int(time.time() * 1000),
            event=event,
            payload=payload,
            session_key=session_key,
        )

        await self._broadcast(event_frame)
        return event_frame

    async def _broadcast(self, event_frame: EventFrame) -> None:
        """广播事件到所有订阅者"""
        tasks = []
        for subscriber in self._subscribers:
            if self._should_deliver(subscriber, event_frame):
                tasks.append(self._deliver_event(subscriber, event_frame))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    def _should_deliver(self, subscriber: EventSubscriber, event_frame: EventFrame) -> bool:
        """判断是否应该投递事件"""
        # 检查 session_key 过滤
        if subscriber.session_key and subscriber.session_key != event_frame.session_key:
            return False

        # 检查事件类型过滤
        if subscriber.event_filter and not event_frame.event.startswith(subscriber.event_filter):
            return False

        return True

    async def _deliver_event(self, subscriber: EventSubscriber, event_frame: EventFrame) -> None:
        """投递事件到订阅者"""
        try:
            await subscriber.callback(event_frame)
        except Exception as e:
            logger.error(f"Error delivering event {event_frame.event}: {e}")


# 全局事件广播器实例
_event_broadcaster = EventBroadcaster()


def get_event_broadcaster() -> EventBroadcaster:
    """获取全局事件广播器"""
    return _event_broadcaster

