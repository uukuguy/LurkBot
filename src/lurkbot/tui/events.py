"""
TUI 事件处理器

对标 MoltBot src/tui/tui-event-handlers.ts

处理 TUI 事件如连接、消息、流式响应等
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Awaitable
from uuid import uuid4

from loguru import logger

from .types import (
    ActivityStatus,
    ChatMessage,
    MessageRole,
    TuiEvent,
    TuiEventType,
    TuiState,
)
from .stream_assembler import TuiStreamAssembler


# 事件处理器类型
EventListener = Callable[[TuiEvent], Awaitable[None]]
MessageListener = Callable[[ChatMessage], Awaitable[None]]
StreamListener = Callable[[str, str], Awaitable[None]]  # (run_id, display_text)


@dataclass
class EventHandlerConfig:
    """事件处理器配置"""

    max_message_history: int = 1000
    auto_scroll: bool = True
    show_timestamps: bool = False


class TuiEventHandler:
    """
    TUI 事件处理器

    对标 MoltBot tui-event-handlers.ts

    功能:
    - 连接事件处理
    - 消息事件处理
    - 流式响应处理
    - 工具调用处理
    """

    def __init__(
        self,
        state: TuiState,
        config: EventHandlerConfig | None = None,
    ) -> None:
        self.state = state
        self.config = config or EventHandlerConfig()

        # 消息历史
        self._messages: list[ChatMessage] = []

        # 流式组装器
        self._stream_assembler = TuiStreamAssembler()

        # 监听器
        self._event_listeners: list[EventListener] = []
        self._message_listeners: list[MessageListener] = []
        self._stream_listeners: list[StreamListener] = []

    @property
    def messages(self) -> list[ChatMessage]:
        """获取消息历史"""
        return self._messages.copy()

    def add_event_listener(self, listener: EventListener) -> None:
        """添加事件监听器"""
        self._event_listeners.append(listener)

    def add_message_listener(self, listener: MessageListener) -> None:
        """添加消息监听器"""
        self._message_listeners.append(listener)

    def add_stream_listener(self, listener: StreamListener) -> None:
        """添加流式监听器"""
        self._stream_listeners.append(listener)

    def remove_event_listener(self, listener: EventListener) -> None:
        """移除事件监听器"""
        if listener in self._event_listeners:
            self._event_listeners.remove(listener)

    async def handle_event(self, event: TuiEvent) -> None:
        """
        处理事件

        Args:
            event: TUI 事件
        """
        # 根据事件类型处理
        handler_map = {
            TuiEventType.CONNECTED: self._handle_connected,
            TuiEventType.DISCONNECTED: self._handle_disconnected,
            TuiEventType.CONNECTION_ERROR: self._handle_connection_error,
            TuiEventType.MESSAGE_RECEIVED: self._handle_message_received,
            TuiEventType.MESSAGE_SENT: self._handle_message_sent,
            TuiEventType.STREAM_START: self._handle_stream_start,
            TuiEventType.STREAM_CHUNK: self._handle_stream_chunk,
            TuiEventType.STREAM_END: self._handle_stream_end,
            TuiEventType.TOOL_CALL_START: self._handle_tool_call_start,
            TuiEventType.TOOL_CALL_END: self._handle_tool_call_end,
        }

        handler = handler_map.get(event.type)
        if handler:
            await handler(event)

        # 通知监听器
        for listener in self._event_listeners:
            try:
                await listener(event)
            except Exception as e:
                logger.error(f"Event listener error: {e}")

    async def handle_stream_delta(
        self,
        run_id: str,
        delta: dict[str, Any],
    ) -> None:
        """
        处理流式增量

        Args:
            run_id: 运行 ID
            delta: 增量数据
        """
        # 更新状态
        self.state.activity_status = ActivityStatus.STREAMING
        self.state.active_chat_run_id = run_id

        # 组装显示文本
        display_text = self._stream_assembler.ingest_delta(
            run_id,
            delta,
            self.state.show_thinking,
        )

        # 通知流式监听器
        for listener in self._stream_listeners:
            try:
                await listener(run_id, display_text)
            except Exception as e:
                logger.error(f"Stream listener error: {e}")

    async def finalize_stream(self, run_id: str) -> ChatMessage:
        """
        完成流式响应

        Args:
            run_id: 运行 ID

        Returns:
            最终消息
        """
        # 获取最终内容
        content = self._stream_assembler.finalize(run_id)
        thinking = self._stream_assembler.get_thinking(run_id)
        tool_calls = self._stream_assembler.get_tool_calls(run_id)

        # 创建消息
        message = ChatMessage(
            id=run_id,
            role=MessageRole.ASSISTANT,
            content=content,
            thinking=thinking if thinking else None,
            tool_calls=tool_calls,
            is_streaming=False,
        )

        # 添加到历史
        self._add_message(message)

        # 更新状态
        self.state.activity_status = ActivityStatus.IDLE
        self.state.active_chat_run_id = None

        return message

    def add_user_message(self, content: str) -> ChatMessage:
        """
        添加用户消息

        Args:
            content: 消息内容

        Returns:
            消息对象
        """
        message = ChatMessage(
            id=str(uuid4()),
            role=MessageRole.USER,
            content=content,
        )
        self._add_message(message)
        return message

    def add_system_message(self, content: str) -> ChatMessage:
        """
        添加系统消息

        Args:
            content: 消息内容

        Returns:
            消息对象
        """
        message = ChatMessage(
            id=str(uuid4()),
            role=MessageRole.SYSTEM,
            content=content,
        )
        self._add_message(message)
        return message

    def clear_messages(self) -> None:
        """清除所有消息"""
        self._messages.clear()
        self._stream_assembler.clear()

    def _add_message(self, message: ChatMessage) -> None:
        """添加消息到历史"""
        self._messages.append(message)

        # 限制历史大小
        if len(self._messages) > self.config.max_message_history:
            self._messages = self._messages[-self.config.max_message_history :]

        # 通知监听器
        for listener in self._message_listeners:
            asyncio.create_task(self._notify_message_listener(listener, message))

    async def _notify_message_listener(
        self,
        listener: MessageListener,
        message: ChatMessage,
    ) -> None:
        """通知消息监听器"""
        try:
            await listener(message)
        except Exception as e:
            logger.error(f"Message listener error: {e}")

    # ============ 事件处理器 ============

    async def _handle_connected(self, event: TuiEvent) -> None:
        """处理连接事件"""
        self.state.is_connected = True
        self.state.connection_status = "connected"
        self.add_system_message("Connected to gateway")

    async def _handle_disconnected(self, event: TuiEvent) -> None:
        """处理断开事件"""
        self.state.is_connected = False
        self.state.connection_status = "disconnected"
        self.state.activity_status = ActivityStatus.IDLE
        self.add_system_message("Disconnected from gateway")

    async def _handle_connection_error(self, event: TuiEvent) -> None:
        """处理连接错误"""
        self.state.is_connected = False
        self.state.connection_status = f"error: {event.data}"
        error_msg = event.data if isinstance(event.data, str) else str(event.data)
        self.add_system_message(f"Connection error: {error_msg}")

    async def _handle_message_received(self, event: TuiEvent) -> None:
        """处理接收消息事件"""
        data = event.data or {}
        message = ChatMessage(
            id=data.get("id", str(uuid4())),
            role=MessageRole(data.get("role", "assistant")),
            content=data.get("content", ""),
            thinking=data.get("thinking"),
            tool_calls=data.get("tool_calls", []),
        )
        self._add_message(message)

    async def _handle_message_sent(self, event: TuiEvent) -> None:
        """处理发送消息事件"""
        data = event.data or {}
        message = data.get("message", "")
        run_id = data.get("run_id", "")

        # 更新状态
        self.state.activity_status = ActivityStatus.SENDING
        self.state.active_chat_run_id = run_id

        # 添加用户消息
        self.add_user_message(message)

    async def _handle_stream_start(self, event: TuiEvent) -> None:
        """处理流式开始事件"""
        data = event.data or {}
        run_id = data.get("run_id", "")

        self.state.activity_status = ActivityStatus.STREAMING
        self.state.active_chat_run_id = run_id

    async def _handle_stream_chunk(self, event: TuiEvent) -> None:
        """处理流式块事件"""
        data = event.data or {}
        run_id = data.get("run_id", "")
        delta = data.get("delta", {})

        await self.handle_stream_delta(run_id, delta)

    async def _handle_stream_end(self, event: TuiEvent) -> None:
        """处理流式结束事件"""
        data = event.data or {}
        run_id = data.get("run_id", "")

        if run_id:
            await self.finalize_stream(run_id)

    async def _handle_tool_call_start(self, event: TuiEvent) -> None:
        """处理工具调用开始事件"""
        # 可以在这里更新 UI 显示工具正在执行
        pass

    async def _handle_tool_call_end(self, event: TuiEvent) -> None:
        """处理工具调用结束事件"""
        # 可以在这里更新 UI 显示工具执行结果
        pass


class InputHistory:
    """
    输入历史管理

    管理用户输入历史，支持上下键导航
    """

    def __init__(self, max_size: int = 100) -> None:
        self._history: list[str] = []
        self._max_size = max_size
        self._index = 0
        self._current_input = ""

    def add(self, text: str) -> None:
        """添加到历史"""
        text = text.strip()
        if not text:
            return

        # 避免重复
        if self._history and self._history[-1] == text:
            return

        self._history.append(text)

        # 限制大小
        if len(self._history) > self._max_size:
            self._history = self._history[-self._max_size :]

        # 重置索引
        self._index = len(self._history)
        self._current_input = ""

    def prev(self, current: str = "") -> str | None:
        """获取上一条历史"""
        if not self._history:
            return None

        # 保存当前输入
        if self._index == len(self._history):
            self._current_input = current

        if self._index > 0:
            self._index -= 1
            return self._history[self._index]

        return None

    def next(self) -> str | None:
        """获取下一条历史"""
        if not self._history:
            return None

        if self._index < len(self._history) - 1:
            self._index += 1
            return self._history[self._index]
        elif self._index == len(self._history) - 1:
            self._index = len(self._history)
            return self._current_input

        return None

    def reset(self) -> None:
        """重置索引"""
        self._index = len(self._history)
        self._current_input = ""

    @property
    def items(self) -> list[str]:
        """获取所有历史项"""
        return self._history.copy()
