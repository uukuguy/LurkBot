"""WebSocket Gateway server implementation."""

import asyncio
from collections.abc import Callable
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from loguru import logger

from lurkbot.config import Settings
from lurkbot.gateway.protocol import (
    ConnectMessage,
    Message,
    MessageType,
    RequestMessage,
    ResponseMessage,
)


class ConnectionManager:
    """Manage WebSocket connections."""

    def __init__(self) -> None:
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, client_id: str, websocket: WebSocket) -> None:
        """Accept and register a new connection."""
        await websocket.accept()
        self.active_connections[client_id] = websocket
        logger.info(f"Client connected: {client_id}")

    def disconnect(self, client_id: str) -> None:
        """Remove a connection."""
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            logger.info(f"Client disconnected: {client_id}")

    async def send(self, client_id: str, message: Message) -> None:
        """Send a message to a specific client."""
        if client_id in self.active_connections:
            await self.active_connections[client_id].send_json(message.model_dump(mode="json"))

    async def broadcast(self, message: Message, exclude: str | None = None) -> None:
        """Broadcast a message to all connected clients."""
        for client_id, connection in self.active_connections.items():
            if client_id != exclude:
                await connection.send_json(message.model_dump(mode="json"))


class GatewayServer:
    """WebSocket Gateway server."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.app = FastAPI(title="LurkBot Gateway")
        self.manager = ConnectionManager()
        self.handlers: dict[str, Callable[..., Any]] = {}
        self._setup_routes()

    def _setup_routes(self) -> None:
        """Set up HTTP and WebSocket routes."""

        @self.app.get("/health")
        async def health() -> dict[str, str]:
            return {"status": "ok"}

        @self.app.websocket("/ws/{client_id}")
        async def websocket_endpoint(websocket: WebSocket, client_id: str) -> None:
            await self._handle_connection(websocket, client_id)

    async def _handle_connection(self, websocket: WebSocket, client_id: str) -> None:
        """Handle a WebSocket connection."""
        await self.manager.connect(client_id, websocket)

        try:
            while True:
                data = await websocket.receive_json()
                await self._handle_message(client_id, data)
        except WebSocketDisconnect:
            self.manager.disconnect(client_id)

    async def _handle_message(self, client_id: str, data: dict[str, Any]) -> None:
        """Handle an incoming message."""
        msg_type = data.get("type")

        if msg_type == MessageType.PING:
            await self.manager.send(
                client_id, Message(type=MessageType.PONG, payload=data.get("payload", {}))
            )
        elif msg_type == MessageType.REQUEST:
            await self._handle_request(client_id, RequestMessage(**data))
        elif msg_type == MessageType.CONNECT:
            await self._handle_connect(client_id, ConnectMessage(**data))
        else:
            logger.warning(f"Unknown message type: {msg_type}")

    async def _handle_connect(self, client_id: str, message: ConnectMessage) -> None:
        """Handle connection handshake."""
        # TODO: Implement authentication
        response = Message(
            type=MessageType.EVENT,
            payload={"event": "connected", "client_id": client_id},
        )
        await self.manager.send(client_id, response)

    async def _handle_request(self, client_id: str, message: RequestMessage) -> None:
        """Handle an RPC request."""
        method = message.method
        handler = self.handlers.get(method)

        if handler is None:
            response = ResponseMessage(
                request_id=message.id or "",
                error=f"Unknown method: {method}",
            )
        else:
            try:
                result = await handler(**message.params)
                response = ResponseMessage(
                    request_id=message.id or "",
                    result=result,
                )
            except Exception as e:
                logger.exception(f"Error handling request {method}")
                response = ResponseMessage(
                    request_id=message.id or "",
                    error=str(e),
                )

        await self.manager.send(client_id, response)

    def register_handler(self, method: str, handler: Callable[..., Any]) -> None:
        """Register an RPC method handler."""
        self.handlers[method] = handler

    async def run(self) -> None:
        """Run the gateway server."""
        import uvicorn

        config = uvicorn.Config(
            self.app,
            host=self.settings.gateway.host,
            port=self.settings.gateway.port,
            log_level=self.settings.log_level.lower(),
        )
        server = uvicorn.Server(config)
        await server.serve()
