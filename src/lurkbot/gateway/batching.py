"""
消息批处理模块

实现消息批量发送，提升吞吐量
"""

import asyncio
from typing import Callable, Awaitable
from loguru import logger

from lurkbot.utils import json_utils as json


class MessageBatcher:
    """消息批处理器

    实现消息批量发送，通过以下策略提升性能：
    1. 批量大小触发：达到 batch_size 时立即刷新
    2. 延迟触发：超过 batch_delay 时自动刷新
    3. 手动刷新：支持显式调用 flush()

    Args:
        send_func: 发送函数，接收 JSON 字符串
        batch_size: 批量大小（默认 100）
        batch_delay: 批量延迟（秒，默认 0.01 = 10ms）
        auto_flush: 是否自动刷新（默认 True）
    """

    def __init__(
        self,
        send_func: Callable[[str], Awaitable[None]],
        batch_size: int = 100,
        batch_delay: float = 0.01,
        auto_flush: bool = True,
    ):
        self.send_func = send_func
        self.batch_size = batch_size
        self.batch_delay = batch_delay
        self.auto_flush = auto_flush

        self._buffer: list[dict] = []
        self._flush_task: asyncio.Task | None = None
        self._lock = asyncio.Lock()
        self._closed = False

    async def add(self, message: dict) -> None:
        """添加消息到批处理缓冲区

        Args:
            message: 要发送的消息字典
        """
        if self._closed:
            logger.warning("Batcher is closed, ignoring message")
            return

        async with self._lock:
            self._buffer.append(message)

            # 达到批量大小，立即刷新
            if len(self._buffer) >= self.batch_size:
                await self._flush_unlocked()
            # 启动延迟刷新
            elif self.auto_flush and not self._flush_task:
                self._flush_task = asyncio.create_task(self._delayed_flush())

    async def flush(self) -> None:
        """刷新缓冲区（公共接口）"""
        async with self._lock:
            await self._flush_unlocked()

    async def _flush_unlocked(self) -> None:
        """刷新缓冲区（内部实现，需要持有锁）"""
        if not self._buffer:
            return

        # 取消延迟刷新任务
        if self._flush_task:
            self._flush_task.cancel()
            self._flush_task = None

        # 批量发送
        messages = self._buffer
        self._buffer = []

        try:
            await self._send_batch(messages)
        except Exception as e:
            logger.error(f"Failed to send batch: {e}")

    async def _delayed_flush(self) -> None:
        """延迟刷新"""
        try:
            await asyncio.sleep(self.batch_delay)
            async with self._lock:
                await self._flush_unlocked()
        except asyncio.CancelledError:
            # 任务被取消，正常情况
            pass

    async def _send_batch(self, messages: list[dict]) -> None:
        """批量发送消息

        Args:
            messages: 消息列表
        """
        if not messages:
            return

        # 批量序列化
        batch_data = [json.dumps(msg) for msg in messages]

        # 批量发送
        for data in batch_data:
            await self.send_func(data)

    async def close(self) -> None:
        """关闭批处理器，刷新剩余消息"""
        self._closed = True

        # 取消延迟刷新任务
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass

        # 刷新剩余消息
        await self.flush()
