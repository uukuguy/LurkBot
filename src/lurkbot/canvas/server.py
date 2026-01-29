"""
Canvas Host 服务器

对标 MoltBot src/canvas-host/server.ts

管理 WebSocket 连接和 A2UI 状态。

职责:
- 管理客户端 WebSocket 连接
- 维护会话的 A2UI 状态
- 广播消息到所有订阅的客户端
"""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import WebSocket
from loguru import logger
from pydantic import BaseModel, Field

from lurkbot.canvas.protocol import (
    A2UIMessage,
    DataModelUpdateMessage,
    DeleteSurfaceMessage,
    MessageType,
    ResetMessage,
    Surface,
    SurfaceUpdateMessage,
)


class A2UIState(BaseModel):
    """
    A2UI 会话状态

    对标 MoltBot CanvasHost.state
    """

    surfaces: dict[str, Surface] = Field(default_factory=dict, description="Surface 组件映射")
    data_model: dict[str, Any] = Field(default_factory=dict, description="数据模型")


class CanvasHost:
    """
    Canvas Host 服务

    对标 MoltBot src/canvas-host/server.ts CanvasHost

    职责:
    - 管理 WebSocket 客户端连接
    - 维护 A2UI 状态
    - 广播消息到客户端
    """

    def __init__(self):
        # 客户端连接: session_id -> Set[WebSocket]
        self.clients: dict[str, set[WebSocket]] = {}

        # 会话状态: session_id -> A2UIState
        self.state: dict[str, A2UIState] = {}

        # 锁，用于保护并发访问
        self._lock = asyncio.Lock()

    async def connect(self, session_id: str, websocket: WebSocket):
        """
        注册新的 WebSocket 客户端

        Args:
            session_id: 会话 ID
            websocket: WebSocket 连接
        """
        async with self._lock:
            if session_id not in self.clients:
                self.clients[session_id] = set()
            self.clients[session_id].add(websocket)

        logger.info(f"Canvas client connected (session={session_id}, total={len(self.clients[session_id])})")

    async def disconnect(self, session_id: str, websocket: WebSocket):
        """
        移除 WebSocket 客户端

        Args:
            session_id: 会话 ID
            websocket: WebSocket 连接
        """
        async with self._lock:
            if session_id in self.clients:
                self.clients[session_id].discard(websocket)
                if not self.clients[session_id]:
                    del self.clients[session_id]

        logger.info(f"Canvas client disconnected (session={session_id})")

    async def broadcast(self, session_id: str, messages: list[A2UIMessage]):
        """
        广播 A2UI 消息到所有连接的客户端

        对标 MoltBot CanvasHost.broadcast()

        Args:
            session_id: 会话 ID
            messages: A2UI 消息列表
        """
        async with self._lock:
            clients = self.clients.get(session_id, set()).copy()

        # 处理每条消息
        for message in messages:
            # 更新内部状态（即使没有客户端连接也要更新）
            await self._update_state(session_id, message)

            # 如果有客户端连接，广播消息
            if clients:
                # 序列化消息
                payload = message.model_dump_json(by_alias=True)

                # 广播到所有客户端
                disconnected = []
                for client in clients:
                    try:
                        await client.send_text(payload)
                    except Exception as e:
                        logger.warning(f"Failed to send message to client: {e}")
                        disconnected.append(client)

                # 清理断开的客户端
                if disconnected:
                    async with self._lock:
                        if session_id in self.clients:
                            for client in disconnected:
                                self.clients[session_id].discard(client)

        if clients:
            logger.debug(f"Broadcast {len(messages)} messages to {len(clients)} clients (session={session_id})")
        else:
            logger.debug(f"Updated state for {len(messages)} messages (no clients connected, session={session_id})")

    async def _update_state(self, session_id: str, message: A2UIMessage):
        """
        更新内部状态

        Args:
            session_id: 会话 ID
            message: A2UI 消息
        """
        # 确保状态存在
        if session_id not in self.state:
            self.state[session_id] = A2UIState()

        state = self.state[session_id]

        # 根据消息类型更新状态
        if isinstance(message, SurfaceUpdateMessage):
            state.surfaces[message.surface_id] = message.surface

        elif isinstance(message, DataModelUpdateMessage):
            self._set_nested(state.data_model, message.path, message.value)

        elif isinstance(message, DeleteSurfaceMessage):
            state.surfaces.pop(message.surface_id, None)

        elif isinstance(message, ResetMessage):
            self.state[session_id] = A2UIState()

    def _set_nested(self, data: dict[str, Any], path: str, value: Any):
        """
        设置嵌套数据

        Args:
            data: 数据字典
            path: 点分隔路径 (e.g. "user.name")
            value: 新值
        """
        keys = path.split(".")
        for key in keys[:-1]:
            if key not in data:
                data[key] = {}
            data = data[key]
        data[keys[-1]] = value

    async def reset(self, session_id: str):
        """
        重置会话状态

        Args:
            session_id: 会话 ID
        """
        async with self._lock:
            self.state.pop(session_id, None)

        # 通知客户端重置
        await self.broadcast(session_id, [ResetMessage()])

        logger.info(f"Reset canvas state (session={session_id})")

    def get_state(self, session_id: str) -> A2UIState:
        """
        获取当前状态

        Args:
            session_id: 会话 ID

        Returns:
            A2UI 状态
        """
        return self.state.get(session_id, A2UIState())

    def get_client_count(self, session_id: str) -> int:
        """
        获取客户端连接数

        Args:
            session_id: 会话 ID

        Returns:
            客户端数量
        """
        return len(self.clients.get(session_id, set()))


# ============================================================================
# 全局单例
# ============================================================================

_canvas_host_instance: CanvasHost | None = None


def get_canvas_host() -> CanvasHost:
    """获取全局 CanvasHost 实例"""
    global _canvas_host_instance
    if _canvas_host_instance is None:
        _canvas_host_instance = CanvasHost()
    return _canvas_host_instance
