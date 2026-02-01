"""
Gateway WebSocket 服务器

对标 MoltBot src/gateway/server.ts
"""

import uuid
import asyncio
from typing import Set
from fastapi import WebSocket, WebSocketDisconnect
from loguru import logger

from lurkbot.utils import json_utils as json

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
from lurkbot.gateway.batching import MessageBatcher


class GatewayConnection:
    """单个 WebSocket 连接"""

    def __init__(
        self,
        websocket: WebSocket,
        conn_id: str,
        enable_batching: bool = True,
        batch_size: int = 100,
        batch_delay: float = 0.01,
    ):
        self.websocket = websocket
        self.conn_id = conn_id
        self.client_info = None
        self.authenticated = False
        self.tenant_id: str | None = None  # Tenant context for multi-tenant support

        # 批处理配置
        if enable_batching:
            self.batcher = MessageBatcher(
                send_func=self._send_text,
                batch_size=batch_size,
                batch_delay=batch_delay,
            )
        else:
            self.batcher = None

    async def _send_text(self, text: str) -> None:
        """发送文本消息（内部方法）"""
        await self.websocket.send_text(text)

    async def send_json(self, data: dict) -> None:
        """发送 JSON 消息（支持批处理）"""
        if self.batcher:
            await self.batcher.add(data)
        else:
            await self.websocket.send_text(json.dumps(data))

    async def receive_json(self) -> dict:
        """接收 JSON 消息"""
        text = await self.websocket.receive_text()
        return json.loads(text)

    async def close(self) -> None:
        """关闭连接，刷新剩余消息"""
        if self.batcher:
            await self.batcher.close()


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
            # 关闭连接，刷新剩余消息
            await connection.close()
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

        # 提取并验证租户 (if provided)
        tenant_id = connect_params.auth.get("tenant_id") if connect_params.auth else None
        if tenant_id:
            try:
                from lurkbot.tenants import TenantManager
                from lurkbot.tenants.storage import MemoryTenantStorage

                # Get or create tenant manager (in production, use a shared instance)
                tenant_manager = TenantManager(storage=MemoryTenantStorage())
                tenant = await tenant_manager.get_tenant(tenant_id)

                if not tenant:
                    logger.warning(f"Tenant not found: {tenant_id}")
                    raise ValueError(f"Invalid tenant: {tenant_id}")

                if not tenant.is_active():
                    logger.warning(f"Tenant inactive: {tenant_id}, status={tenant.status.value}")
                    raise ValueError(f"Inactive tenant: {tenant_id}")

                connection.tenant_id = tenant_id
                logger.info(f"Tenant validated for connection {connection.conn_id}: {tenant_id}")

            except ImportError:
                # Tenant module not available, skip validation
                logger.debug("Tenant module not available, skipping tenant validation")
            except ValueError:
                raise
            except Exception as e:
                logger.warning(f"Tenant validation failed: {e}")
                # Continue without tenant context for backward compatibility

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
            # 策略评估 (if tenant context available)
            if connection.tenant_id:
                try:
                    from lurkbot.tenants.guards import get_policy_guard

                    policy_guard = get_policy_guard()
                    await policy_guard.require_permission(
                        principal=f"tenant:{connection.tenant_id}",
                        resource=f"method:{request.method}",
                        action="execute",
                        tenant_id=connection.tenant_id,
                    )
                except ImportError:
                    # Policy guard not available, skip evaluation
                    pass
                except Exception as e:
                    from lurkbot.tenants.errors import PolicyDeniedError

                    if isinstance(e, PolicyDeniedError):
                        response = ResponseFrame(
                            id=request.id,
                            error=ErrorShape(
                                code=ErrorCode.UNAVAILABLE,
                                message=f"Policy denied: {e.message}",
                            ),
                        )
                        await connection.send_json(response.model_dump(by_alias=True))
                        return
                    raise

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

