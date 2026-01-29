"""
CDP Operations - Chrome DevTools Protocol 操作

对标 MoltBot src/browser/cdp.ts
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, Callable

import aiohttp
from loguru import logger

from .types import CDPMessage, CDPSession, BrowserError


# ============================================================================
# CDP Client
# ============================================================================

class CDPClient:
    """
    CDP 客户端

    通过 WebSocket 与 Chrome DevTools Protocol 通信。
    """

    def __init__(self, ws_endpoint: str):
        """
        初始化 CDP 客户端

        Args:
            ws_endpoint: WebSocket 端点 URL
        """
        self._ws_endpoint = ws_endpoint
        self._ws: aiohttp.ClientWebSocketResponse | None = None
        self._session: aiohttp.ClientSession | None = None
        self._message_id = 0
        self._pending_requests: dict[int, asyncio.Future] = {}
        self._event_handlers: dict[str, list[Callable]] = {}
        self._receive_task: asyncio.Task | None = None
        self._connected = False

    @property
    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self._connected and self._ws is not None and not self._ws.closed

    async def connect(self) -> None:
        """连接到 CDP"""
        if self.is_connected:
            return

        logger.debug(f"Connecting to CDP: {self._ws_endpoint}")

        try:
            self._session = aiohttp.ClientSession()
            self._ws = await self._session.ws_connect(
                self._ws_endpoint,
                max_msg_size=100 * 1024 * 1024,  # 100MB
            )
            self._connected = True

            # 启动接收任务
            self._receive_task = asyncio.create_task(self._receive_loop())

            logger.info("Connected to CDP")

        except Exception as e:
            await self.disconnect()
            raise BrowserError(f"Failed to connect to CDP: {e}", "CDP_CONNECT_FAILED")

    async def disconnect(self) -> None:
        """断开 CDP 连接"""
        self._connected = False

        # 取消接收任务
        if self._receive_task:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass
            self._receive_task = None

        # 关闭 WebSocket
        if self._ws and not self._ws.closed:
            await self._ws.close()
        self._ws = None

        # 关闭会话
        if self._session and not self._session.closed:
            await self._session.close()
        self._session = None

        # 取消所有待处理请求
        for future in self._pending_requests.values():
            if not future.done():
                future.cancel()
        self._pending_requests.clear()

        logger.info("Disconnected from CDP")

    async def send(
        self,
        method: str,
        params: dict[str, Any] | None = None,
        timeout: float = 30.0,
    ) -> dict[str, Any]:
        """
        发送 CDP 命令

        Args:
            method: CDP 方法名
            params: 方法参数
            timeout: 超时时间（秒）

        Returns:
            响应结果

        Raises:
            BrowserError: 如果发送失败或响应错误
        """
        if not self.is_connected:
            raise BrowserError("Not connected to CDP", "NOT_CONNECTED")

        self._message_id += 1
        message_id = self._message_id

        message = {
            "id": message_id,
            "method": method,
        }
        if params:
            message["params"] = params

        # 创建 Future 等待响应
        future: asyncio.Future = asyncio.get_event_loop().create_future()
        self._pending_requests[message_id] = future

        try:
            # 发送消息
            await self._ws.send_json(message)
            logger.debug(f"CDP send: {method}")

            # 等待响应
            result = await asyncio.wait_for(future, timeout=timeout)

            # 检查错误
            if "error" in result:
                error = result["error"]
                raise BrowserError(
                    f"CDP error: {error.get('message', 'Unknown error')}",
                    f"CDP_{error.get('code', 'ERROR')}",
                )

            return result.get("result", {})

        except asyncio.TimeoutError:
            raise BrowserError(f"CDP request timeout: {method}", "TIMEOUT")
        finally:
            self._pending_requests.pop(message_id, None)

    def on(self, event: str, handler: Callable) -> None:
        """
        注册事件处理器

        Args:
            event: 事件名称（如 "Page.loadEventFired"）
            handler: 处理函数
        """
        if event not in self._event_handlers:
            self._event_handlers[event] = []
        self._event_handlers[event].append(handler)

    def off(self, event: str, handler: Callable | None = None) -> None:
        """
        移除事件处理器

        Args:
            event: 事件名称
            handler: 处理函数（None 则移除所有）
        """
        if event in self._event_handlers:
            if handler is None:
                del self._event_handlers[event]
            else:
                self._event_handlers[event] = [
                    h for h in self._event_handlers[event] if h != handler
                ]

    async def _receive_loop(self) -> None:
        """接收消息循环"""
        try:
            async for msg in self._ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                        await self._handle_message(data)
                    except json.JSONDecodeError:
                        logger.warning(f"Invalid JSON from CDP: {msg.data[:100]}")
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    logger.error(f"CDP WebSocket error: {self._ws.exception()}")
                    break
                elif msg.type in (aiohttp.WSMsgType.CLOSE, aiohttp.WSMsgType.CLOSED):
                    break
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"CDP receive error: {e}")
        finally:
            self._connected = False

    async def _handle_message(self, data: dict[str, Any]) -> None:
        """处理接收的消息"""
        # 响应消息
        if "id" in data:
            message_id = data["id"]
            if message_id in self._pending_requests:
                future = self._pending_requests[message_id]
                if not future.done():
                    future.set_result(data)

        # 事件消息
        elif "method" in data:
            method = data["method"]
            params = data.get("params", {})

            handlers = self._event_handlers.get(method, [])
            for handler in handlers:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(params)
                    else:
                        handler(params)
                except Exception as e:
                    logger.error(f"CDP event handler error ({method}): {e}")


# ============================================================================
# CDP Helper Functions
# ============================================================================

async def create_cdp_session(
    client: CDPClient,
    target_id: str,
) -> CDPSession:
    """
    创建 CDP 会话

    Args:
        client: CDP 客户端
        target_id: 目标 ID

    Returns:
        CDPSession 实例
    """
    result = await client.send("Target.attachToTarget", {
        "targetId": target_id,
        "flatten": True,
    })

    return CDPSession(
        session_id=result["sessionId"],
        target_id=target_id,
        target_type="page",
    )


async def get_targets(client: CDPClient) -> list[dict[str, Any]]:
    """
    获取所有目标

    Args:
        client: CDP 客户端

    Returns:
        目标列表
    """
    result = await client.send("Target.getTargets")
    return result.get("targetInfos", [])


async def get_page_targets(client: CDPClient) -> list[dict[str, Any]]:
    """
    获取所有页面目标

    Args:
        client: CDP 客户端

    Returns:
        页面目标列表
    """
    targets = await get_targets(client)
    return [t for t in targets if t.get("type") == "page"]


async def create_page_target(
    client: CDPClient,
    url: str = "about:blank",
) -> str:
    """
    创建新页面目标

    Args:
        client: CDP 客户端
        url: 初始 URL

    Returns:
        目标 ID
    """
    result = await client.send("Target.createTarget", {"url": url})
    return result["targetId"]


async def close_target(client: CDPClient, target_id: str) -> bool:
    """
    关闭目标

    Args:
        client: CDP 客户端
        target_id: 目标 ID

    Returns:
        是否成功
    """
    result = await client.send("Target.closeTarget", {"targetId": target_id})
    return result.get("success", False)


# ============================================================================
# CDP Domain Helpers
# ============================================================================

class CDPPage:
    """CDP Page Domain 封装"""

    def __init__(self, client: CDPClient):
        self._client = client

    async def enable(self) -> None:
        """启用 Page domain"""
        await self._client.send("Page.enable")

    async def disable(self) -> None:
        """禁用 Page domain"""
        await self._client.send("Page.disable")

    async def navigate(self, url: str, referrer: str | None = None) -> dict[str, Any]:
        """导航到 URL"""
        params = {"url": url}
        if referrer:
            params["referrer"] = referrer
        return await self._client.send("Page.navigate", params)

    async def reload(self, ignore_cache: bool = False) -> None:
        """重新加载页面"""
        await self._client.send("Page.reload", {"ignoreCache": ignore_cache})

    async def stop_loading(self) -> None:
        """停止加载"""
        await self._client.send("Page.stopLoading")

    async def capture_screenshot(
        self,
        format: str = "png",
        quality: int | None = None,
        clip: dict | None = None,
        from_surface: bool = True,
    ) -> str:
        """
        截图

        Returns:
            Base64 编码的图片数据
        """
        params = {
            "format": format,
            "fromSurface": from_surface,
        }
        if quality is not None:
            params["quality"] = quality
        if clip:
            params["clip"] = clip

        result = await self._client.send("Page.captureScreenshot", params)
        return result["data"]

    async def get_layout_metrics(self) -> dict[str, Any]:
        """获取页面布局指标"""
        return await self._client.send("Page.getLayoutMetrics")


class CDPRuntime:
    """CDP Runtime Domain 封装"""

    def __init__(self, client: CDPClient):
        self._client = client

    async def enable(self) -> None:
        """启用 Runtime domain"""
        await self._client.send("Runtime.enable")

    async def disable(self) -> None:
        """禁用 Runtime domain"""
        await self._client.send("Runtime.disable")

    async def evaluate(
        self,
        expression: str,
        return_by_value: bool = True,
        await_promise: bool = True,
        timeout: float | None = None,
    ) -> Any:
        """
        执行 JavaScript 表达式

        Args:
            expression: JavaScript 表达式
            return_by_value: 是否按值返回
            await_promise: 是否等待 Promise
            timeout: 超时时间

        Returns:
            执行结果
        """
        params = {
            "expression": expression,
            "returnByValue": return_by_value,
            "awaitPromise": await_promise,
        }
        if timeout:
            params["timeout"] = timeout

        result = await self._client.send("Runtime.evaluate", params)

        if "exceptionDetails" in result:
            exception = result["exceptionDetails"]
            raise BrowserError(
                f"JavaScript error: {exception.get('text', 'Unknown error')}",
                "JS_ERROR",
            )

        return result.get("result", {}).get("value")


class CDPInput:
    """CDP Input Domain 封装"""

    def __init__(self, client: CDPClient):
        self._client = client

    async def dispatch_mouse_event(
        self,
        type: str,
        x: float,
        y: float,
        button: str = "left",
        click_count: int = 1,
        modifiers: int = 0,
    ) -> None:
        """分发鼠标事件"""
        await self._client.send("Input.dispatchMouseEvent", {
            "type": type,
            "x": x,
            "y": y,
            "button": button,
            "clickCount": click_count,
            "modifiers": modifiers,
        })

    async def dispatch_key_event(
        self,
        type: str,
        key: str | None = None,
        code: str | None = None,
        text: str | None = None,
        modifiers: int = 0,
    ) -> None:
        """分发键盘事件"""
        params = {
            "type": type,
            "modifiers": modifiers,
        }
        if key:
            params["key"] = key
        if code:
            params["code"] = code
        if text:
            params["text"] = text

        await self._client.send("Input.dispatchKeyEvent", params)

    async def insert_text(self, text: str) -> None:
        """插入文本"""
        await self._client.send("Input.insertText", {"text": text})


class CDPNetwork:
    """CDP Network Domain 封装"""

    def __init__(self, client: CDPClient):
        self._client = client

    async def enable(self) -> None:
        """启用 Network domain"""
        await self._client.send("Network.enable")

    async def disable(self) -> None:
        """禁用 Network domain"""
        await self._client.send("Network.disable")

    async def set_extra_http_headers(self, headers: dict[str, str]) -> None:
        """设置额外的 HTTP 头"""
        await self._client.send("Network.setExtraHTTPHeaders", {"headers": headers})

    async def set_user_agent_override(
        self,
        user_agent: str,
        accept_language: str | None = None,
        platform: str | None = None,
    ) -> None:
        """覆盖 User-Agent"""
        params = {"userAgent": user_agent}
        if accept_language:
            params["acceptLanguage"] = accept_language
        if platform:
            params["platform"] = platform

        await self._client.send("Network.setUserAgentOverride", params)


class CDPAccessibility:
    """CDP Accessibility Domain 封装"""

    def __init__(self, client: CDPClient):
        self._client = client

    async def enable(self) -> None:
        """启用 Accessibility domain"""
        await self._client.send("Accessibility.enable")

    async def disable(self) -> None:
        """禁用 Accessibility domain"""
        await self._client.send("Accessibility.disable")

    async def get_full_ax_tree(self) -> dict[str, Any]:
        """获取完整的可访问性树"""
        return await self._client.send("Accessibility.getFullAXTree")

    async def query_ax_tree(
        self,
        node_id: str | None = None,
        backend_node_id: int | None = None,
        object_id: str | None = None,
        accessible_name: str | None = None,
        role: str | None = None,
    ) -> list[dict[str, Any]]:
        """查询可访问性树"""
        params = {}
        if node_id:
            params["nodeId"] = node_id
        if backend_node_id:
            params["backendNodeId"] = backend_node_id
        if object_id:
            params["objectId"] = object_id
        if accessible_name:
            params["accessibleName"] = accessible_name
        if role:
            params["role"] = role

        result = await self._client.send("Accessibility.queryAXTree", params)
        return result.get("nodes", [])


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    "CDPClient",
    "CDPSession",
    "CDPMessage",
    "create_cdp_session",
    "get_targets",
    "get_page_targets",
    "create_page_target",
    "close_target",
    # Domain helpers
    "CDPPage",
    "CDPRuntime",
    "CDPInput",
    "CDPNetwork",
    "CDPAccessibility",
]
