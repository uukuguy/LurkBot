"""
TUI Gateway 通信适配器

对标 MoltBot src/tui/gateway-chat.ts

提供与 Gateway 服务器的 WebSocket 通信
"""

import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Awaitable
from uuid import uuid4

from loguru import logger

from .types import (
    ActivityStatus,
    GatewayConnectionInfo,
    TuiEvent,
    TuiEventType,
)


@dataclass
class PendingRequest:
    """待处理请求"""

    id: str
    method: str
    future: asyncio.Future[Any]
    timestamp: datetime = field(default_factory=datetime.now)


class GatewayChat:
    """
    Gateway 通信适配器

    对标 MoltBot gateway-chat.ts

    功能:
    - WebSocket 连接管理
    - 消息发送和接收
    - 流式响应处理
    - 心跳保活
    """

    def __init__(
        self,
        url: str = "ws://localhost:3000",
        token: str | None = None,
    ) -> None:
        self.url = url
        self.token = token
        self._ws: Any = None  # websockets.WebSocketClientProtocol
        self._connected = False
        self._connection_info = GatewayConnectionInfo(url=url, token=token)

        # 回调
        self._event_handlers: list[Callable[[TuiEvent], Awaitable[None]]] = []
        self._stream_handlers: list[Callable[[str, dict[str, Any]], Awaitable[None]]] = []

        # 请求追踪
        self._pending_requests: dict[str, PendingRequest] = {}

        # 任务
        self._receive_task: asyncio.Task[None] | None = None
        self._heartbeat_task: asyncio.Task[None] | None = None

    @property
    def connected(self) -> bool:
        """是否已连接"""
        return self._connected

    @property
    def connection_info(self) -> GatewayConnectionInfo:
        """连接信息"""
        return self._connection_info

    async def connect(self) -> bool:
        """
        连接到 Gateway

        Returns:
            是否连接成功
        """
        try:
            import websockets

            # 构建 URL
            url = self.url
            if self.token:
                separator = "&" if "?" in url else "?"
                url = f"{url}{separator}token={self.token}"

            # 连接
            self._ws = await websockets.connect(url)
            self._connected = True
            self._connection_info.connected = True
            self._connection_info.last_ping = datetime.now()

            # 启动接收任务
            self._receive_task = asyncio.create_task(self._receive_loop())

            # 启动心跳任务
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

            # 触发连接事件
            await self._emit_event(TuiEvent(type=TuiEventType.CONNECTED))

            logger.info(f"Connected to Gateway: {self.url}")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to Gateway: {e}")
            self._connected = False
            self._connection_info.connected = False
            await self._emit_event(
                TuiEvent(type=TuiEventType.CONNECTION_ERROR, data=str(e))
            )
            return False

    async def disconnect(self) -> None:
        """断开连接"""
        self._connected = False
        self._connection_info.connected = False

        # 取消任务
        if self._receive_task:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass

        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass

        # 关闭 WebSocket
        if self._ws:
            await self._ws.close()
            self._ws = None

        # 取消所有待处理请求
        for req in self._pending_requests.values():
            if not req.future.done():
                req.future.cancel()
        self._pending_requests.clear()

        # 触发断开事件
        await self._emit_event(TuiEvent(type=TuiEventType.DISCONNECTED))

        logger.info("Disconnected from Gateway")

    async def send_message(
        self,
        message: str,
        agent_id: str = "default",
        session_key: str | None = None,
        model: str | None = None,
        thinking_level: str | None = None,
    ) -> str:
        """
        发送消息

        Args:
            message: 消息内容
            agent_id: Agent ID
            session_key: 会话 Key
            model: 模型
            thinking_level: Thinking 级别

        Returns:
            运行 ID
        """
        run_id = str(uuid4())

        payload = {
            "jsonrpc": "2.0",
            "method": "agent.prompt",
            "id": run_id,
            "params": {
                "agentId": agent_id,
                "message": message,
            },
        }

        if session_key:
            payload["params"]["sessionKey"] = session_key
        if model:
            payload["params"]["model"] = model
        if thinking_level:
            payload["params"]["thinkingLevel"] = thinking_level

        await self._send(payload)

        # 触发发送事件
        await self._emit_event(
            TuiEvent(type=TuiEventType.MESSAGE_SENT, data={"run_id": run_id, "message": message})
        )

        return run_id

    async def abort_run(self, run_id: str) -> bool:
        """
        中止运行

        Args:
            run_id: 运行 ID

        Returns:
            是否成功
        """
        payload = {
            "jsonrpc": "2.0",
            "method": "agent.abort",
            "id": str(uuid4()),
            "params": {"runId": run_id},
        }

        await self._send(payload)
        return True

    async def list_sessions(self, agent_id: str = "default") -> list[dict[str, Any]]:
        """
        列出会话

        Args:
            agent_id: Agent ID

        Returns:
            会话列表
        """
        request_id = str(uuid4())
        payload = {
            "jsonrpc": "2.0",
            "method": "sessions.list",
            "id": request_id,
            "params": {"agentId": agent_id},
        }

        future: asyncio.Future[Any] = asyncio.get_event_loop().create_future()
        self._pending_requests[request_id] = PendingRequest(
            id=request_id,
            method="sessions.list",
            future=future,
        )

        await self._send(payload)

        try:
            result = await asyncio.wait_for(future, timeout=10.0)
            return result.get("sessions", [])
        except asyncio.TimeoutError:
            logger.warning("sessions.list timeout")
            return []
        finally:
            self._pending_requests.pop(request_id, None)

    async def get_status(self) -> dict[str, Any]:
        """
        获取 Gateway 状态

        Returns:
            状态信息
        """
        request_id = str(uuid4())
        payload = {
            "jsonrpc": "2.0",
            "method": "gateway.status",
            "id": request_id,
            "params": {},
        }

        future: asyncio.Future[Any] = asyncio.get_event_loop().create_future()
        self._pending_requests[request_id] = PendingRequest(
            id=request_id,
            method="gateway.status",
            future=future,
        )

        await self._send(payload)

        try:
            result = await asyncio.wait_for(future, timeout=5.0)
            return result
        except asyncio.TimeoutError:
            logger.warning("gateway.status timeout")
            return {}
        finally:
            self._pending_requests.pop(request_id, None)

    def on_event(self, handler: Callable[[TuiEvent], Awaitable[None]]) -> None:
        """注册事件处理器"""
        self._event_handlers.append(handler)

    def on_stream(self, handler: Callable[[str, dict[str, Any]], Awaitable[None]]) -> None:
        """注册流式处理器"""
        self._stream_handlers.append(handler)

    async def _send(self, payload: dict[str, Any]) -> None:
        """发送消息"""
        if not self._ws or not self._connected:
            raise RuntimeError("Not connected to Gateway")

        data = json.dumps(payload)
        await self._ws.send(data)

    async def _receive_loop(self) -> None:
        """接收消息循环"""
        try:
            async for message in self._ws:
                try:
                    data = json.loads(message)
                    await self._handle_message(data)
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON: {message}")
                except Exception as e:
                    logger.error(f"Error handling message: {e}")

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Receive loop error: {e}")
            self._connected = False
            self._connection_info.connected = False
            await self._emit_event(
                TuiEvent(type=TuiEventType.CONNECTION_ERROR, data=str(e))
            )

    async def _handle_message(self, data: dict[str, Any]) -> None:
        """处理接收的消息"""
        # JSON-RPC 响应
        if "id" in data and "result" in data:
            request_id = data["id"]
            if request_id in self._pending_requests:
                req = self._pending_requests[request_id]
                if not req.future.done():
                    req.future.set_result(data["result"])
            return

        # JSON-RPC 错误
        if "id" in data and "error" in data:
            request_id = data["id"]
            if request_id in self._pending_requests:
                req = self._pending_requests[request_id]
                if not req.future.done():
                    req.future.set_exception(Exception(data["error"].get("message", "Unknown error")))
            return

        # 通知/流式消息
        method = data.get("method", "")

        if method == "agent.delta":
            # 流式响应
            params = data.get("params", {})
            run_id = params.get("runId", "")
            for handler in self._stream_handlers:
                await handler(run_id, params)

        elif method == "agent.complete":
            # 完成
            params = data.get("params", {})
            run_id = params.get("runId", "")
            await self._emit_event(
                TuiEvent(type=TuiEventType.STREAM_END, data={"run_id": run_id})
            )

        elif method == "agent.error":
            # 错误
            params = data.get("params", {})
            await self._emit_event(
                TuiEvent(type=TuiEventType.CONNECTION_ERROR, data=params)
            )

    async def _heartbeat_loop(self) -> None:
        """心跳循环"""
        try:
            while self._connected:
                await asyncio.sleep(30)  # 30 秒心跳

                if not self._connected:
                    break

                # 发送 ping
                try:
                    start = datetime.now()
                    pong = await self._ws.ping()
                    await asyncio.wait_for(pong, timeout=10)
                    latency = (datetime.now() - start).total_seconds() * 1000
                    self._connection_info.latency_ms = latency
                    self._connection_info.last_ping = datetime.now()
                except Exception as e:
                    logger.warning(f"Heartbeat failed: {e}")
                    # 尝试重连
                    self._connected = False
                    await self._emit_event(
                        TuiEvent(type=TuiEventType.DISCONNECTED, data="Heartbeat failed")
                    )

        except asyncio.CancelledError:
            pass

    async def _emit_event(self, event: TuiEvent) -> None:
        """触发事件"""
        for handler in self._event_handlers:
            try:
                await handler(event)
            except Exception as e:
                logger.error(f"Event handler error: {e}")
