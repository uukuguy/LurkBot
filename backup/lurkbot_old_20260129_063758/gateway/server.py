"""WebSocket Gateway server implementation."""

from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger

from lurkbot.config import Settings
from lurkbot.gateway.protocol import (
    ConnectMessage,
    Message,
    MessageType,
    RequestMessage,
    ResponseMessage,
)

if TYPE_CHECKING:
    from lurkbot.agents.runtime import AgentRuntime
    from lurkbot.gateway.websocket_streaming import StreamingChatHandler, WebSocketManager


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
    """WebSocket Gateway server with HTTP REST API.

    Provides both WebSocket connections for real-time communication
    and HTTP REST API endpoints for session/model management.
    """

    def __init__(
        self,
        settings: Settings,
        runtime: "AgentRuntime | None" = None,
    ) -> None:
        """Initialize the gateway server.

        Args:
            settings: Application settings
            runtime: Optional agent runtime for HTTP API endpoints
        """
        self.settings = settings
        self.runtime = runtime
        self.app = FastAPI(
            title="LurkBot Gateway",
            description="Multi-channel AI assistant platform",
            version="0.1.0",
        )
        self.manager = ConnectionManager()
        self.handlers: dict[str, Callable[..., Any]] = {}

        # WebSocket streaming components
        self._ws_manager: WebSocketManager | None = None
        self._chat_handler: StreamingChatHandler | None = None

        self._setup_middleware()
        self._setup_routes()

    def _setup_middleware(self) -> None:
        """Set up CORS and other middleware."""
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # Configure appropriately for production
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    def _setup_routes(self) -> None:
        """Set up HTTP and WebSocket routes."""

        @self.app.get("/health")
        async def health() -> dict[str, str]:
            return {"status": "ok"}

        @self.app.websocket("/ws/{client_id}")
        async def websocket_endpoint(websocket: WebSocket, client_id: str) -> None:
            await self._handle_connection(websocket, client_id)

        # Add HTTP REST API routes if runtime is available
        if self.runtime:
            from lurkbot.gateway.http_api import create_api_router

            api_router = create_api_router(self.runtime, channel="web")
            self.app.include_router(api_router)
            logger.info("HTTP REST API routes enabled at /api/*")

            # Set up WebSocket streaming for chat
            from lurkbot.gateway.websocket_streaming import (
                StreamingChatHandler,
                WebSocketManager,
                websocket_chat_endpoint,
            )

            self._ws_manager = WebSocketManager()
            self._chat_handler = StreamingChatHandler(self.runtime, self._ws_manager)

            @self.app.websocket("/ws/chat/{client_id}")
            async def websocket_chat(websocket: WebSocket, client_id: str) -> None:
                """WebSocket endpoint for streaming chat."""
                await websocket_chat_endpoint(
                    websocket, client_id, self._ws_manager, self._chat_handler
                )

            logger.info("WebSocket streaming chat enabled at /ws/chat/{client_id}")

            # Mount static files for web dashboard
            static_dir = Path(__file__).parent.parent / "static"
            if static_dir.exists():
                self.app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

                @self.app.get("/")
                async def serve_dashboard() -> FileResponse:
                    """Serve the web dashboard."""
                    return FileResponse(static_dir / "index.html")

                logger.info("Web dashboard enabled at /")
            else:
                logger.warning(f"Static directory not found: {static_dir}")

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

    async def _handle_connect(self, client_id: str, _message: ConnectMessage) -> None:
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
