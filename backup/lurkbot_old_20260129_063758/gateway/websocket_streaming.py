"""WebSocket real-time streaming for LurkBot.

Provides real-time updates for:
- Streaming chat responses
- Tool execution notifications
- Approval requests and decisions
- Session status updates
"""

import asyncio
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect
from loguru import logger
from pydantic import BaseModel

from lurkbot.agents.runtime import AgentRuntime

# ============================================================================
# Event Types
# ============================================================================


class EventType(str, Enum):
    """WebSocket event types."""

    # Connection events
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"

    # Chat events
    CHAT_START = "chat_start"
    CHAT_CHUNK = "chat_chunk"
    CHAT_END = "chat_end"
    CHAT_ERROR = "chat_error"

    # Tool events
    TOOL_START = "tool_start"
    TOOL_PROGRESS = "tool_progress"
    TOOL_END = "tool_end"
    TOOL_ERROR = "tool_error"

    # Approval events
    APPROVAL_REQUIRED = "approval_required"
    APPROVAL_RESOLVED = "approval_resolved"
    APPROVAL_TIMEOUT = "approval_timeout"

    # Session events
    SESSION_CREATED = "session_created"
    SESSION_UPDATED = "session_updated"
    SESSION_DELETED = "session_deleted"


# ============================================================================
# Event Models
# ============================================================================


class WebSocketEvent(BaseModel):
    """WebSocket event message."""

    type: EventType
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    session_id: str | None = None
    data: dict[str, Any] = field(default_factory=dict)

    model_config = {"use_enum_values": True}

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return self.model_dump_json()


class ChatStartEvent(BaseModel):
    """Chat start event data."""

    session_id: str
    model: str
    message: str


class ChatChunkEvent(BaseModel):
    """Chat chunk event data."""

    session_id: str
    content: str
    index: int


class ChatEndEvent(BaseModel):
    """Chat end event data."""

    session_id: str
    full_response: str
    model: str


class ToolStartEvent(BaseModel):
    """Tool execution start event."""

    session_id: str
    tool_name: str
    tool_input: dict[str, Any]


class ToolEndEvent(BaseModel):
    """Tool execution end event."""

    session_id: str
    tool_name: str
    success: bool
    output: str | None = None
    error: str | None = None


class ApprovalRequiredEvent(BaseModel):
    """Approval required event."""

    approval_id: str
    session_id: str
    tool_name: str
    command: str | None = None
    expires_at: datetime


# ============================================================================
# WebSocket Session Manager
# ============================================================================


@dataclass
class WebSocketSession:
    """Manages a single WebSocket connection."""

    websocket: WebSocket
    client_id: str
    connected_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    subscribed_sessions: set[str] = field(default_factory=set)

    async def send_event(self, event: WebSocketEvent) -> None:
        """Send an event to this WebSocket connection."""
        try:
            await self.websocket.send_text(event.to_json())
        except Exception as e:
            logger.error(f"Failed to send event to {self.client_id}: {e}")


class WebSocketManager:
    """Manages WebSocket connections and event broadcasting."""

    def __init__(self) -> None:
        self._connections: dict[str, WebSocketSession] = {}
        self._session_subscriptions: dict[str, set[str]] = {}  # session_id -> client_ids
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, client_id: str) -> WebSocketSession:
        """Accept a new WebSocket connection.

        Args:
            websocket: WebSocket connection
            client_id: Unique client identifier

        Returns:
            WebSocket session object
        """
        await websocket.accept()

        session = WebSocketSession(websocket=websocket, client_id=client_id)

        async with self._lock:
            self._connections[client_id] = session

        logger.info(f"WebSocket client connected: {client_id}")

        # Send connected event
        await session.send_event(
            WebSocketEvent(
                type=EventType.CONNECTED,
                data={"client_id": client_id},
            )
        )

        return session

    async def disconnect(self, client_id: str) -> None:
        """Disconnect a WebSocket client.

        Args:
            client_id: Client identifier to disconnect
        """
        async with self._lock:
            if client_id in self._connections:
                session = self._connections[client_id]

                # Remove from all session subscriptions
                for session_id in session.subscribed_sessions:
                    if session_id in self._session_subscriptions:
                        self._session_subscriptions[session_id].discard(client_id)

                del self._connections[client_id]
                logger.info(f"WebSocket client disconnected: {client_id}")

    async def subscribe(self, client_id: str, session_id: str) -> bool:
        """Subscribe a client to session events.

        Args:
            client_id: Client identifier
            session_id: Session to subscribe to

        Returns:
            True if subscription was successful
        """
        async with self._lock:
            if client_id not in self._connections:
                return False

            session = self._connections[client_id]
            session.subscribed_sessions.add(session_id)

            if session_id not in self._session_subscriptions:
                self._session_subscriptions[session_id] = set()
            self._session_subscriptions[session_id].add(client_id)

            logger.debug(f"Client {client_id} subscribed to session {session_id}")
            return True

    async def unsubscribe(self, client_id: str, session_id: str) -> bool:
        """Unsubscribe a client from session events.

        Args:
            client_id: Client identifier
            session_id: Session to unsubscribe from

        Returns:
            True if unsubscription was successful
        """
        async with self._lock:
            if client_id not in self._connections:
                return False

            session = self._connections[client_id]
            session.subscribed_sessions.discard(session_id)

            if session_id in self._session_subscriptions:
                self._session_subscriptions[session_id].discard(client_id)

            logger.debug(f"Client {client_id} unsubscribed from session {session_id}")
            return True

    async def broadcast_to_session(self, session_id: str, event: WebSocketEvent) -> int:
        """Broadcast an event to all clients subscribed to a session.

        Args:
            session_id: Session identifier
            event: Event to broadcast

        Returns:
            Number of clients the event was sent to
        """
        async with self._lock:
            if session_id not in self._session_subscriptions:
                return 0

            client_ids = list(self._session_subscriptions[session_id])

        sent_count = 0
        for client_id in client_ids:
            if client_id in self._connections:
                await self._connections[client_id].send_event(event)
                sent_count += 1

        return sent_count

    async def broadcast_all(self, event: WebSocketEvent) -> int:
        """Broadcast an event to all connected clients.

        Args:
            event: Event to broadcast

        Returns:
            Number of clients the event was sent to
        """
        async with self._lock:
            client_ids = list(self._connections.keys())

        sent_count = 0
        for client_id in client_ids:
            if client_id in self._connections:
                await self._connections[client_id].send_event(event)
                sent_count += 1

        return sent_count

    async def send_to_client(self, client_id: str, event: WebSocketEvent) -> bool:
        """Send an event to a specific client.

        Args:
            client_id: Target client
            event: Event to send

        Returns:
            True if event was sent
        """
        if client_id in self._connections:
            await self._connections[client_id].send_event(event)
            return True
        return False

    def get_client_count(self) -> int:
        """Get number of connected clients."""
        return len(self._connections)

    def get_session_subscriber_count(self, session_id: str) -> int:
        """Get number of subscribers to a session."""
        return len(self._session_subscriptions.get(session_id, set()))


# ============================================================================
# Streaming Chat Handler
# ============================================================================


class StreamingChatHandler:
    """Handles streaming chat through WebSocket."""

    def __init__(
        self,
        runtime: AgentRuntime,
        ws_manager: WebSocketManager,
    ) -> None:
        self.runtime = runtime
        self.ws_manager = ws_manager

    async def handle_chat(
        self,
        client_id: str,
        session_id: str,
        message: str,
        model: str | None = None,
        sender_name: str | None = None,
    ) -> str:
        """Handle a streaming chat request.

        Args:
            client_id: WebSocket client ID
            session_id: Chat session ID
            message: User message
            model: Optional model to use
            sender_name: Optional sender display name

        Returns:
            Full response text
        """
        model = model or self.runtime.settings.models.default_model

        # Send start event
        await self.ws_manager.send_to_client(
            client_id,
            WebSocketEvent(
                type=EventType.CHAT_START,
                session_id=session_id,
                data=ChatStartEvent(
                    session_id=session_id,
                    model=model,
                    message=message,
                ).model_dump(),
            ),
        )

        full_response = ""
        chunk_index = 0

        try:
            async for chunk in self.runtime.stream_chat(
                session_id=session_id,
                channel="websocket",
                sender_id=client_id,
                message=message,
                sender_name=sender_name,
                model=model,
            ):
                full_response += chunk
                chunk_index += 1

                # Send chunk event
                await self.ws_manager.send_to_client(
                    client_id,
                    WebSocketEvent(
                        type=EventType.CHAT_CHUNK,
                        session_id=session_id,
                        data=ChatChunkEvent(
                            session_id=session_id,
                            content=chunk,
                            index=chunk_index,
                        ).model_dump(),
                    ),
                )

            # Send end event
            await self.ws_manager.send_to_client(
                client_id,
                WebSocketEvent(
                    type=EventType.CHAT_END,
                    session_id=session_id,
                    data=ChatEndEvent(
                        session_id=session_id,
                        full_response=full_response,
                        model=model,
                    ).model_dump(),
                ),
            )

        except Exception as e:
            logger.exception(f"Streaming chat error: {e}")
            await self.ws_manager.send_to_client(
                client_id,
                WebSocketEvent(
                    type=EventType.CHAT_ERROR,
                    session_id=session_id,
                    data={"error": str(e)},
                ),
            )

        return full_response


# ============================================================================
# WebSocket Message Protocol
# ============================================================================


class WSMessageType(str, Enum):
    """Incoming WebSocket message types."""

    CHAT = "chat"  # Send a chat message
    SUBSCRIBE = "subscribe"  # Subscribe to session events
    UNSUBSCRIBE = "unsubscribe"  # Unsubscribe from session events
    PING = "ping"  # Keep-alive ping


class WSMessage(BaseModel):
    """Incoming WebSocket message."""

    type: WSMessageType
    data: dict[str, Any] = {}


async def handle_ws_message(
    message: WSMessage,
    client_id: str,
    ws_manager: WebSocketManager,
    chat_handler: StreamingChatHandler,
) -> None:
    """Handle an incoming WebSocket message.

    Args:
        message: Parsed WebSocket message
        client_id: Client identifier
        ws_manager: WebSocket manager
        chat_handler: Chat handler
    """
    if message.type == WSMessageType.PING:
        await ws_manager.send_to_client(
            client_id,
            WebSocketEvent(type=EventType.CONNECTED, data={"pong": True}),
        )

    elif message.type == WSMessageType.SUBSCRIBE:
        session_id = message.data.get("session_id")
        if session_id:
            await ws_manager.subscribe(client_id, session_id)
            await ws_manager.send_to_client(
                client_id,
                WebSocketEvent(
                    type=EventType.SESSION_UPDATED,
                    session_id=session_id,
                    data={"subscribed": True},
                ),
            )

    elif message.type == WSMessageType.UNSUBSCRIBE:
        session_id = message.data.get("session_id")
        if session_id:
            await ws_manager.unsubscribe(client_id, session_id)
            await ws_manager.send_to_client(
                client_id,
                WebSocketEvent(
                    type=EventType.SESSION_UPDATED,
                    session_id=session_id,
                    data={"subscribed": False},
                ),
            )

    elif message.type == WSMessageType.CHAT:
        session_id = message.data.get("session_id")
        user_message = message.data.get("message")
        model = message.data.get("model")
        sender_name = message.data.get("sender_name")

        if session_id and user_message:
            # Run chat in background task
            asyncio.create_task(
                chat_handler.handle_chat(
                    client_id=client_id,
                    session_id=session_id,
                    message=user_message,
                    model=model,
                    sender_name=sender_name,
                )
            )


# ============================================================================
# WebSocket Endpoint Handler
# ============================================================================


async def websocket_chat_endpoint(
    websocket: WebSocket,
    client_id: str,
    ws_manager: WebSocketManager,
    chat_handler: StreamingChatHandler,
) -> None:
    """Handle WebSocket chat endpoint.

    Args:
        websocket: WebSocket connection
        client_id: Unique client identifier
        ws_manager: WebSocket manager
        chat_handler: Chat handler
    """
    await ws_manager.connect(websocket, client_id)

    try:
        while True:
            data = await websocket.receive_text()

            try:
                raw_message = json.loads(data)
                message = WSMessage(**raw_message)
                await handle_ws_message(message, client_id, ws_manager, chat_handler)

            except json.JSONDecodeError:
                await ws_manager.send_to_client(
                    client_id,
                    WebSocketEvent(
                        type=EventType.ERROR,
                        data={"error": "Invalid JSON"},
                    ),
                )

            except Exception as e:
                logger.exception(f"Error handling WebSocket message: {e}")
                await ws_manager.send_to_client(
                    client_id,
                    WebSocketEvent(
                        type=EventType.ERROR,
                        data={"error": str(e)},
                    ),
                )

    except WebSocketDisconnect:
        await ws_manager.disconnect(client_id)
