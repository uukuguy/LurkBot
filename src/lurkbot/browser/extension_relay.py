"""
Extension Relay - 浏览器扩展中继

对标 MoltBot src/browser/extension_relay.ts

提供与浏览器扩展的双向通信机制。
"""

from __future__ import annotations

import asyncio
import json
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable

from loguru import logger

from .types import ExtensionMessage, ExtensionResponse


# ============================================================================
# Extension Relay
# ============================================================================

@dataclass
class PendingRequest:
    """待处理请求"""
    id: str
    future: asyncio.Future
    timeout_handle: asyncio.TimerHandle | None = None


class ExtensionRelay:
    """
    扩展中继

    管理与浏览器扩展的通信，支持：
    - 发送消息到扩展
    - 接收扩展消息
    - 请求/响应模式
    - 事件订阅
    """

    def __init__(self, timeout: float = 30.0):
        """
        初始化扩展中继

        Args:
            timeout: 默认请求超时时间（秒）
        """
        self._timeout = timeout
        self._pending_requests: dict[str, PendingRequest] = {}
        self._event_handlers: dict[str, list[Callable]] = {}
        self._message_handler: Callable | None = None
        self._connected = False

    @property
    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self._connected

    def set_connected(self, connected: bool) -> None:
        """设置连接状态"""
        self._connected = connected

    def on_message(self, handler: Callable[[ExtensionMessage], None]) -> None:
        """
        设置消息处理器

        Args:
            handler: 消息处理函数
        """
        self._message_handler = handler

    def on(self, event_type: str, handler: Callable[[dict], None]) -> None:
        """
        订阅事件

        Args:
            event_type: 事件类型
            handler: 处理函数
        """
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        self._event_handlers[event_type].append(handler)

    def off(self, event_type: str, handler: Callable | None = None) -> None:
        """
        取消订阅事件

        Args:
            event_type: 事件类型
            handler: 处理函数（None 则移除所有）
        """
        if event_type in self._event_handlers:
            if handler is None:
                del self._event_handlers[event_type]
            else:
                self._event_handlers[event_type] = [
                    h for h in self._event_handlers[event_type] if h != handler
                ]

    async def send(
        self,
        message_type: str,
        payload: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> ExtensionResponse:
        """
        发送消息到扩展并等待响应

        Args:
            message_type: 消息类型
            payload: 消息负载
            timeout: 超时时间

        Returns:
            ExtensionResponse
        """
        if not self._connected:
            return ExtensionResponse(
                success=False,
                type=message_type,
                error="Extension not connected",
            )

        message_id = str(uuid.uuid4())
        message = ExtensionMessage(
            type=message_type,
            payload=payload or {},
            id=message_id,
        )

        # 创建 Future
        loop = asyncio.get_event_loop()
        future: asyncio.Future = loop.create_future()

        # 设置超时
        actual_timeout = timeout or self._timeout

        def on_timeout() -> None:
            if message_id in self._pending_requests:
                req = self._pending_requests.pop(message_id)
                if not req.future.done():
                    req.future.set_result(ExtensionResponse(
                        success=False,
                        type=message_type,
                        error="Request timeout",
                    ))

        timeout_handle = loop.call_later(actual_timeout, on_timeout)

        # 保存请求
        self._pending_requests[message_id] = PendingRequest(
            id=message_id,
            future=future,
            timeout_handle=timeout_handle,
        )

        # 发送消息（需要子类实现）
        try:
            await self._send_to_extension(message)
        except Exception as e:
            # 清理
            if message_id in self._pending_requests:
                req = self._pending_requests.pop(message_id)
                if req.timeout_handle:
                    req.timeout_handle.cancel()
            return ExtensionResponse(
                success=False,
                type=message_type,
                error=str(e),
            )

        # 等待响应
        return await future

    async def _send_to_extension(self, message: ExtensionMessage) -> None:
        """
        发送消息到扩展（需要子类实现）

        Args:
            message: 要发送的消息
        """
        raise NotImplementedError("Subclass must implement _send_to_extension")

    def handle_response(self, response: dict[str, Any]) -> None:
        """
        处理扩展响应

        Args:
            response: 响应数据
        """
        message_id = response.get("id")
        if not message_id:
            return

        if message_id in self._pending_requests:
            req = self._pending_requests.pop(message_id)

            # 取消超时
            if req.timeout_handle:
                req.timeout_handle.cancel()

            # 设置结果
            if not req.future.done():
                req.future.set_result(ExtensionResponse(
                    success=response.get("success", True),
                    type=response.get("type", ""),
                    data=response.get("data"),
                    error=response.get("error"),
                ))

    def handle_event(self, event: dict[str, Any]) -> None:
        """
        处理扩展事件

        Args:
            event: 事件数据
        """
        event_type = event.get("type")
        if not event_type:
            return

        handlers = self._event_handlers.get(event_type, [])
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Extension event handler error ({event_type}): {e}")

    def handle_incoming_message(self, data: dict[str, Any]) -> None:
        """
        处理传入消息

        Args:
            data: 消息数据
        """
        # 检查是否是响应
        if "id" in data and data.get("id") in self._pending_requests:
            self.handle_response(data)
            return

        # 转换为 ExtensionMessage
        message = ExtensionMessage(
            type=data.get("type", ""),
            payload=data.get("payload", {}),
            id=data.get("id"),
        )

        # 调用消息处理器
        if self._message_handler:
            try:
                self._message_handler(message)
            except Exception as e:
                logger.error(f"Extension message handler error: {e}")

        # 触发事件
        self.handle_event(data)

    def close(self) -> None:
        """关闭中继"""
        self._connected = False

        # 取消所有待处理请求
        for req in self._pending_requests.values():
            if req.timeout_handle:
                req.timeout_handle.cancel()
            if not req.future.done():
                req.future.cancel()

        self._pending_requests.clear()
        self._event_handlers.clear()


# ============================================================================
# WebSocket Extension Relay
# ============================================================================

class WebSocketExtensionRelay(ExtensionRelay):
    """
    WebSocket 扩展中继

    通过 WebSocket 与浏览器扩展通信。
    """

    def __init__(
        self,
        ws_url: str = "ws://127.0.0.1:9334/extension",
        timeout: float = 30.0,
    ):
        """
        初始化 WebSocket 扩展中继

        Args:
            ws_url: WebSocket URL
            timeout: 默认超时时间
        """
        super().__init__(timeout)
        self._ws_url = ws_url
        self._ws: Any = None
        self._receive_task: asyncio.Task | None = None

    async def connect(self) -> None:
        """连接到扩展"""
        import aiohttp

        logger.info(f"Connecting to extension: {self._ws_url}")

        session = aiohttp.ClientSession()
        self._ws = await session.ws_connect(self._ws_url)
        self.set_connected(True)

        # 启动接收循环
        self._receive_task = asyncio.create_task(self._receive_loop())

        logger.info("Connected to extension")

    async def disconnect(self) -> None:
        """断开连接"""
        self.set_connected(False)

        if self._receive_task:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass
            self._receive_task = None

        if self._ws and not self._ws.closed:
            await self._ws.close()
        self._ws = None

        self.close()
        logger.info("Disconnected from extension")

    async def _send_to_extension(self, message: ExtensionMessage) -> None:
        """发送消息到扩展"""
        if not self._ws or self._ws.closed:
            raise ConnectionError("WebSocket not connected")

        await self._ws.send_json(message.model_dump())

    async def _receive_loop(self) -> None:
        """接收消息循环"""
        import aiohttp

        try:
            async for msg in self._ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                        self.handle_incoming_message(data)
                    except json.JSONDecodeError:
                        logger.warning(f"Invalid JSON from extension: {msg.data[:100]}")
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    logger.error(f"Extension WebSocket error: {self._ws.exception()}")
                    break
                elif msg.type in (aiohttp.WSMsgType.CLOSE, aiohttp.WSMsgType.CLOSED):
                    break
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Extension receive error: {e}")
        finally:
            self.set_connected(False)


# ============================================================================
# CDP Extension Relay
# ============================================================================

class CDPExtensionRelay(ExtensionRelay):
    """
    CDP 扩展中继

    通过 CDP 与浏览器扩展通信（使用 Runtime.evaluate）。
    """

    def __init__(
        self,
        page: Any,  # Playwright Page
        timeout: float = 30.0,
    ):
        """
        初始化 CDP 扩展中继

        Args:
            page: Playwright 页面
            timeout: 默认超时时间
        """
        super().__init__(timeout)
        self._page = page
        self._listener_installed = False

    async def setup(self) -> None:
        """设置扩展通信"""
        if self._listener_installed:
            return

        # 注入消息监听器
        await self._page.evaluate("""
            () => {
                window.__lurkbot_extension_messages = [];
                window.addEventListener('message', (event) => {
                    if (event.data && event.data.source === 'lurkbot-extension') {
                        window.__lurkbot_extension_messages.push(event.data);
                    }
                });
            }
        """)

        self._listener_installed = True
        self.set_connected(True)
        logger.info("CDP extension relay setup complete")

    async def _send_to_extension(self, message: ExtensionMessage) -> None:
        """发送消息到扩展"""
        await self._page.evaluate(
            """
            (message) => {
                window.postMessage({
                    source: 'lurkbot-agent',
                    ...message
                }, '*');
            }
            """,
            message.model_dump(),
        )

    async def poll_messages(self) -> list[dict[str, Any]]:
        """
        轮询扩展消息

        Returns:
            消息列表
        """
        messages = await self._page.evaluate("""
            () => {
                const messages = window.__lurkbot_extension_messages || [];
                window.__lurkbot_extension_messages = [];
                return messages;
            }
        """)

        # 处理每个消息
        for msg in messages:
            self.handle_incoming_message(msg)

        return messages


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    "ExtensionRelay",
    "WebSocketExtensionRelay",
    "CDPExtensionRelay",
    "PendingRequest",
]
