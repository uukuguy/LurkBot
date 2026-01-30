"""
ACP 服务器

实现 ndJSON 双向流通信的 ACP 服务器
对标 MoltBot src/acp/server.ts

基于官方 ACP Python SDK (agent-client-protocol) 的设计
"""

import asyncio
import json
import sys
import platform
from typing import Any
from loguru import logger

from lurkbot.acp.types import (
    PROTOCOL_VERSION,
    ContentBlock,
    Implementation,
    AgentCapabilities,
    PromptCapabilities,
    McpCapabilities,
    ClientCapabilities,
    ModeInfo,
    StopReason,
    SessionNotification,
    JsonRpcRequest,
    JsonRpcResponse,
    JsonRpcNotification,
    InitializeResponse,
    NewSessionResponse,
    LoadSessionResponse,
    PromptResponse,
    SetSessionModeResponse,
    SetSessionModelResponse,
    ReadTextFileResponse,
    WriteTextFileResponse,
    CreateTerminalResponse,
    TerminalOutputResponse,
    WaitForTerminalExitResponse,
    RequestPermissionResponse,
    McpServer,
)
from lurkbot.acp.session import get_session_manager
from lurkbot.acp.translator import get_translator


class ACPServer:
    """
    ACP 服务器

    通过 stdin/stdout 实现 ndJSON 双向流通信
    """

    AGENT_NAME = "LurkBot"
    AGENT_VERSION = "0.1.0"

    def __init__(self):
        self._session_manager = get_session_manager()
        self._translator = get_translator()
        self._request_id_counter = 0
        self._pending_requests: dict[int | str, asyncio.Future] = {}
        self._initialized = False
        self._running = False
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None

    async def run(self) -> None:
        """运行 ACP 服务器（使用 stdin/stdout）"""
        logger.info("Starting ACP Server...")
        self._running = True

        # 设置 stdin/stdout 流
        self._reader, self._writer = await self._setup_stdio()

        try:
            await self._message_loop()
        except asyncio.CancelledError:
            logger.info("ACP Server cancelled")
        except Exception as e:
            logger.error(f"ACP Server error: {e}")
        finally:
            self._running = False
            logger.info("ACP Server stopped")

    async def _setup_stdio(self) -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
        """设置 stdin/stdout 异步流"""
        loop = asyncio.get_running_loop()

        if platform.system() == "Windows":
            return await self._setup_windows_stdio(loop)
        else:
            return await self._setup_posix_stdio(loop)

    async def _setup_posix_stdio(
        self, loop: asyncio.AbstractEventLoop
    ) -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
        """POSIX 系统的 stdio 设置"""
        reader = asyncio.StreamReader()
        reader_protocol = asyncio.StreamReaderProtocol(reader)
        await loop.connect_read_pipe(lambda: reader_protocol, sys.stdin)

        # Writer
        write_transport, write_protocol = await loop.connect_write_pipe(
            asyncio.BaseProtocol, sys.stdout
        )
        writer = asyncio.StreamWriter(write_transport, write_protocol, None, loop)

        return reader, writer

    async def _setup_windows_stdio(
        self, loop: asyncio.AbstractEventLoop
    ) -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
        """Windows 系统的 stdio 设置"""
        import threading

        reader = asyncio.StreamReader()

        # Windows 需要线程来读取 stdin
        def stdin_reader():
            try:
                while self._running:
                    line = sys.stdin.buffer.readline()
                    if not line:
                        break
                    loop.call_soon_threadsafe(reader.feed_data, line)
            finally:
                loop.call_soon_threadsafe(reader.feed_eof)

        threading.Thread(target=stdin_reader, daemon=True).start()

        # 简单的 stdout writer
        class StdoutWriter:
            def write(self, data: bytes) -> None:
                sys.stdout.buffer.write(data)
                sys.stdout.buffer.flush()

            def close(self) -> None:
                pass

            def is_closing(self) -> bool:
                return False

        # 创建一个简化的 writer
        writer = type(
            "SimpleWriter",
            (),
            {
                "write": lambda self, data: sys.stdout.buffer.write(data),
                "drain": lambda self: asyncio.sleep(0),
                "close": lambda self: None,
                "is_closing": lambda self: False,
            },
        )()

        return reader, writer

    async def _message_loop(self) -> None:
        """消息循环"""
        while self._running:
            try:
                line = await self._reader.readline()
                if not line:
                    break

                line_str = line.decode("utf-8").strip()
                if not line_str:
                    continue

                message = json.loads(line_str)
                await self._handle_message(message)

            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON: {e}")
            except Exception as e:
                logger.error(f"Error in message loop: {e}")

    async def _handle_message(self, message: dict) -> None:
        """处理接收到的消息"""
        # 检查是请求还是响应
        if "method" in message:
            if "id" in message:
                # JSON-RPC 请求
                await self._handle_request(message)
            else:
                # JSON-RPC 通知
                await self._handle_notification(message)
        elif "id" in message:
            # JSON-RPC 响应
            await self._handle_response(message)
        else:
            logger.warning(f"Unknown message format: {message}")

    async def _handle_request(self, message: dict) -> None:
        """处理 JSON-RPC 请求"""
        request_id = message.get("id")
        method = message.get("method", "")
        params = message.get("params", {})

        try:
            result = await self._dispatch_method(method, params)
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": result,
            }
        except Exception as e:
            logger.error(f"Method {method} error: {e}")
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32603,
                    "message": str(e),
                },
            }

        await self._write_message(response)

    async def _handle_notification(self, message: dict) -> None:
        """处理 JSON-RPC 通知"""
        method = message.get("method", "")
        params = message.get("params", {})

        try:
            if method == "cancel":
                session_id = params.get("sessionId")
                if session_id:
                    await self._translator.cancel_run(session_id)
            elif method.startswith("_"):
                # 扩展通知
                logger.debug(f"Extension notification: {method}")
            else:
                logger.warning(f"Unknown notification: {method}")
        except Exception as e:
            logger.error(f"Notification {method} error: {e}")

    async def _handle_response(self, message: dict) -> None:
        """处理 JSON-RPC 响应"""
        request_id = message.get("id")
        future = self._pending_requests.pop(request_id, None)

        if future and not future.done():
            if "error" in message:
                error = message["error"]
                future.set_exception(Exception(error.get("message", "Unknown error")))
            else:
                future.set_result(message.get("result"))

    async def _dispatch_method(self, method: str, params: dict) -> dict | None:
        """分发方法调用"""
        handlers = {
            "initialize": self._handle_initialize,
            "session/new": self._handle_new_session,
            "session/load": self._handle_load_session,
            "session/setMode": self._handle_set_mode,
            "session/setModel": self._handle_set_model,
            "prompt": self._handle_prompt,
            # 扩展方法 (以 _ 开头)
        }

        handler = handlers.get(method)
        if handler:
            return await handler(params)

        # 检查是否是扩展方法
        if method.startswith("_"):
            logger.debug(f"Extension method: {method}")
            return {}

        raise ValueError(f"Method not found: {method}")

    async def _handle_initialize(self, params: dict) -> dict:
        """处理初始化请求"""
        protocol_version = params.get("protocolVersion", 1)
        client_info = params.get("clientInfo")

        logger.info(f"ACP Initialize - protocol: {protocol_version}, client: {client_info}")

        self._initialized = True

        response = InitializeResponse(
            protocol_version=PROTOCOL_VERSION,
            agent_info=Implementation(
                name=self.AGENT_NAME,
                title="LurkBot AI Assistant",
                version=self.AGENT_VERSION,
            ),
            agent_capabilities=AgentCapabilities(
                load_session=True,
                prompt_capabilities=PromptCapabilities(
                    image=True,
                    audio=False,
                    embedded_context=True,
                ),
                mcp_capabilities=McpCapabilities(
                    http=False,
                    sse=False,
                    stdio=True,
                ),
            ),
        )

        return response.model_dump(by_alias=True)

    async def _handle_new_session(self, params: dict) -> dict:
        """处理新建会话请求"""
        cwd = params.get("cwd", ".")
        mcp_servers = params.get("mcpServers", [])

        session = self._session_manager.create_session(cwd)

        # 订阅事件
        await self._translator.subscribe_to_events(
            session.session_id,
            self._send_session_notification,
        )

        response = NewSessionResponse(
            session_id=session.session_id,
            modes=[
                ModeInfo(id="default", title="Default"),
                ModeInfo(id="code", title="Code"),
                ModeInfo(id="plan", title="Plan"),
            ],
        )

        return response.model_dump(by_alias=True)

    async def _handle_load_session(self, params: dict) -> dict | None:
        """处理加载会话请求"""
        session_id = params.get("sessionId")
        cwd = params.get("cwd", ".")

        session = self._session_manager.load_session(session_id, cwd)
        if not session:
            return None

        # 订阅事件
        await self._translator.subscribe_to_events(
            session.session_id,
            self._send_session_notification,
        )

        response = LoadSessionResponse(
            modes=[
                ModeInfo(id="default", title="Default"),
                ModeInfo(id="code", title="Code"),
                ModeInfo(id="plan", title="Plan"),
            ],
        )

        return response.model_dump(by_alias=True)

    async def _handle_set_mode(self, params: dict) -> dict | None:
        """处理设置模式请求"""
        session_id = params.get("sessionId")
        mode_id = params.get("modeId")

        if self._session_manager.set_mode(session_id, mode_id):
            return SetSessionModeResponse().model_dump(by_alias=True)
        return None

    async def _handle_set_model(self, params: dict) -> dict | None:
        """处理设置模型请求"""
        session_id = params.get("sessionId")
        model_id = params.get("modelId")

        if self._session_manager.set_model(session_id, model_id):
            return SetSessionModelResponse().model_dump(by_alias=True)
        return None

    async def _handle_prompt(self, params: dict) -> dict:
        """处理 prompt 请求"""
        session_id = params.get("sessionId")
        prompt = params.get("prompt", [])

        response = await self._translator.translate_prompt(session_id, prompt)
        return response.model_dump(by_alias=True)

    async def _send_session_notification(self, notification: SessionNotification) -> None:
        """发送会话通知到客户端"""
        message = {
            "jsonrpc": "2.0",
            "method": "session/update",
            "params": notification.model_dump(by_alias=True),
        }
        await self._write_message(message)

    async def _write_message(self, message: dict) -> None:
        """写入 JSON-RPC 消息"""
        line = json.dumps(message) + "\n"
        if self._writer:
            if hasattr(self._writer, "write"):
                self._writer.write(line.encode("utf-8"))
                if hasattr(self._writer, "drain"):
                    await self._writer.drain()
            else:
                # 简化 writer
                sys.stdout.buffer.write(line.encode("utf-8"))
                sys.stdout.buffer.flush()

    async def send_request(self, method: str, params: dict | None = None) -> Any:
        """发送请求并等待响应"""
        self._request_id_counter += 1
        request_id = self._request_id_counter

        message = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params or {},
        }

        loop = asyncio.get_running_loop()
        future = loop.create_future()
        self._pending_requests[request_id] = future

        await self._write_message(message)

        try:
            return await asyncio.wait_for(future, timeout=30.0)
        except asyncio.TimeoutError:
            self._pending_requests.pop(request_id, None)
            raise

    async def send_notification(self, method: str, params: dict | None = None) -> None:
        """发送通知"""
        message = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
        }
        await self._write_message(message)

    async def close(self) -> None:
        """关闭服务器"""
        self._running = False
        if self._writer:
            self._writer.close()


# 全局 ACP 服务器实例
_acp_server: ACPServer | None = None


def get_acp_server() -> ACPServer:
    """获取全局 ACP 服务器"""
    global _acp_server
    if _acp_server is None:
        _acp_server = ACPServer()
    return _acp_server


async def run_acp_server() -> None:
    """运行 ACP 服务器的便捷函数"""
    server = get_acp_server()
    await server.run()
