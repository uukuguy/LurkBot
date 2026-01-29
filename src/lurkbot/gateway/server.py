"""
Gateway WebSocket 服务器

对标 MoltBot src/gateway/server.ts
"""

import json
import uuid
import asyncio
from typing import Set
from fastapi import WebSocket, WebSocketDisconnect
from loguru import logger

from lurkbot.gateway.protocol.frames import (
    ConnectParams,
    HelloOk,
    ServerInfo,
    Features,
    Snapshot,
    EventFrame,
    RequestFrame,
    ResponseFrame,
    ErrorCode,
    ErrorShape,
)
from lurkbot.gateway.events import get_event_broadcaster
from lurkbot.gateway.methods import get_method_registry


class GatewayConnection:
    """单个 WebSocket 连接"""

    def __init__(self, websocket: WebSocket, conn_id: str):
        self.websocket = websocket
        self.conn_id = conn_id
        self.client_info = None
        self.authenticated = False

    async def send_json(self, data: dict) -> None:
        """发送 JSON 消息"""
        await self.websocket.send_text(json.dumps(data))

    async def receive_json(self) -> dict:
        """接收 JSON 消息"""
        text = await self.websocket.receive_text()
        return json.loads(text)


class GatewayServer:
    """
    Gateway WebSocket 服务器

    对标 MoltBot Gateway Server
    """

    VERSION = "0.1.0"
    PROTOCOL_VERSION = 1

    def __init__(self):
        self._connections: Set[GatewayConnection] = set()
        self._event_broadcaster = get_event_broadcaster()
        self._method_registry = get_method_registry()

    async def handle_connection(self, websocket: WebSocket) -> None:
        """处理 WebSocket 连接"""
        conn_id = str(uuid.uuid4())[:8]
        connection = GatewayConnection(websocket, conn_id)

        await websocket.accept()
        logger.info(f"Gateway connection accepted: {conn_id}")

        try:
            # 握手
            await self._handshake(connection)
            self._connections.add(connection)

            # 订阅事件
            subscriber = self._event_broadcaster.subscribe(
                lambda event: self._send_event(connection, event)
            )

            # 消息循环
            await self._message_loop(connection)

        except WebSocketDisconnect:
            logger.info(f"Gateway connection closed: {conn_id}")
        except Exception as e:
            logger.error(f"Gateway connection error: {e}")
        finally:
            self._connections.discard(connection)
            if subscriber:
                self._event_broadcaster.unsubscribe(subscriber)

    async def _handshake(self, connection: GatewayConnection) -> None:
        """处理握手"""
        hello_msg = await connection.receive_json()

        if hello_msg.get("type") != "hello":
            raise ValueError("Expected hello message")

        # 解析连接参数
        connect_params = ConnectParams(**hello_msg)
        connection.client_info = connect_params.client

        # 发送 hello-ok 响应
        hello_ok = HelloOk(
            protocol=self.PROTOCOL_VERSION,
            server=ServerInfo(
                version=self.VERSION,
                host=None,
                conn_id=connection.conn_id,
            ),
            features=Features(
                methods=self._method_registry.list_methods(),
                events=["agent.*", "session.*", "cron.*", "config.*"],
            ),
            snapshot=Snapshot(),
        )

        await connection.send_json(hello_ok.model_dump(by_alias=True))
        connection.authenticated = True
        logger.info(f"Handshake completed for {connection.conn_id}")

    async def _message_loop(self, connection: GatewayConnection) -> None:
        """消息循环"""
        while True:
            message = await connection.receive_json()
            msg_type = message.get("type")

            if msg_type == "request":
                await self._handle_request(connection, message)
            else:
                logger.warning(f"Unknown message type: {msg_type}")

    async def _handle_request(self, connection: GatewayConnection, message: dict) -> None:
        """处理 RPC 请求"""
        request = RequestFrame(**message)

        try:
            result = await self._method_registry.invoke(
                request.method,
                params=request.params,
                session_key=request.session_key,
            )

            response = ResponseFrame(
                id=request.id,
                result=result,
            )

        except ValueError as e:
            response = ResponseFrame(
                id=request.id,
                error=ErrorShape(
                    code=ErrorCode.METHOD_NOT_FOUND,
                    message=str(e),
                ),
            )
        except Exception as e:
            logger.error(f"RPC method error: {e}")
            response = ResponseFrame(
                id=request.id,
                error=ErrorShape(
                    code=ErrorCode.INTERNAL_ERROR,
                    message=str(e),
                ),
            )

        await connection.send_json(response.model_dump(by_alias=True))

    async def _send_event(self, connection: GatewayConnection, event: EventFrame) -> None:
        """发送事件到客户端"""
        try:
            await connection.send_json(event.model_dump(by_alias=True))
        except Exception as e:
            logger.error(f"Failed to send event: {e}")


# 全局 Gateway 服务器实例
_gateway_server = GatewayServer()


def get_gateway_server() -> GatewayServer:
    """获取全局 Gateway 服务器"""
    return _gateway_server

