"""Tests for WebSocket streaming functionality."""


import pytest

from lurkbot.agents.runtime import AgentRuntime
from lurkbot.config import Settings
from lurkbot.gateway.websocket_streaming import (
    EventType,
    StreamingChatHandler,
    WebSocketEvent,
    WebSocketManager,
    WSMessage,
    WSMessageType,
    handle_ws_message,
)


@pytest.fixture
def settings() -> Settings:
    """Create test settings."""
    return Settings(
        anthropic_api_key="test-api-key",
        agent={"workspace": "/tmp/test"},
        storage={"enabled": False},
    )


@pytest.fixture
def runtime(settings: Settings) -> AgentRuntime:
    """Create test agent runtime."""
    return AgentRuntime(settings)


@pytest.fixture
def ws_manager() -> WebSocketManager:
    """Create WebSocket manager."""
    return WebSocketManager()


@pytest.fixture
def chat_handler(runtime: AgentRuntime, ws_manager: WebSocketManager) -> StreamingChatHandler:
    """Create chat handler."""
    return StreamingChatHandler(runtime, ws_manager)


# ============================================================================
# WebSocketEvent Tests
# ============================================================================


def test_websocket_event_creation():
    """Test WebSocket event creation."""
    event = WebSocketEvent(
        type=EventType.CONNECTED,
        data={"client_id": "test-client"},
    )
    assert event.type == EventType.CONNECTED
    assert event.data == {"client_id": "test-client"}
    assert event.timestamp is not None


def test_websocket_event_to_json():
    """Test WebSocket event JSON serialization."""
    event = WebSocketEvent(
        type=EventType.CHAT_START,
        session_id="test-session",
        data={"model": "gpt-4o"},
    )
    json_str = event.to_json()
    assert "chat_start" in json_str
    assert "test-session" in json_str
    assert "gpt-4o" in json_str


def test_event_types():
    """Test all event types are defined."""
    # Connection events
    assert EventType.CONNECTED is not None
    assert EventType.DISCONNECTED is not None
    assert EventType.ERROR is not None

    # Chat events
    assert EventType.CHAT_START is not None
    assert EventType.CHAT_CHUNK is not None
    assert EventType.CHAT_END is not None
    assert EventType.CHAT_ERROR is not None

    # Tool events
    assert EventType.TOOL_START is not None
    assert EventType.TOOL_PROGRESS is not None
    assert EventType.TOOL_END is not None
    assert EventType.TOOL_ERROR is not None

    # Approval events
    assert EventType.APPROVAL_REQUIRED is not None
    assert EventType.APPROVAL_RESOLVED is not None
    assert EventType.APPROVAL_TIMEOUT is not None


# ============================================================================
# WSMessage Tests
# ============================================================================


def test_ws_message_chat():
    """Test chat WebSocket message parsing."""
    msg = WSMessage(
        type=WSMessageType.CHAT,
        data={"session_id": "test", "message": "Hello"},
    )
    assert msg.type == WSMessageType.CHAT
    assert msg.data["session_id"] == "test"
    assert msg.data["message"] == "Hello"


def test_ws_message_subscribe():
    """Test subscribe WebSocket message."""
    msg = WSMessage(
        type=WSMessageType.SUBSCRIBE,
        data={"session_id": "test-session"},
    )
    assert msg.type == WSMessageType.SUBSCRIBE


def test_ws_message_ping():
    """Test ping WebSocket message."""
    msg = WSMessage(type=WSMessageType.PING)
    assert msg.type == WSMessageType.PING


# ============================================================================
# WebSocketManager Tests
# ============================================================================


def test_ws_manager_creation(ws_manager: WebSocketManager):
    """Test WebSocket manager creation."""
    assert ws_manager is not None
    assert ws_manager.get_client_count() == 0


def test_ws_manager_get_session_subscriber_count(ws_manager: WebSocketManager):
    """Test getting subscriber count for a session."""
    count = ws_manager.get_session_subscriber_count("nonexistent")
    assert count == 0


# ============================================================================
# StreamingChatHandler Tests
# ============================================================================


def test_chat_handler_creation(chat_handler: StreamingChatHandler):
    """Test chat handler creation."""
    assert chat_handler is not None
    assert chat_handler.runtime is not None
    assert chat_handler.ws_manager is not None


# ============================================================================
# Integration Tests (Mock WebSocket)
# ============================================================================


class MockWebSocket:
    """Mock WebSocket for testing."""

    def __init__(self):
        self.sent_messages: list[str] = []
        self.accepted = False
        self.closed = False

    async def accept(self):
        self.accepted = True

    async def send_text(self, text: str):
        self.sent_messages.append(text)

    async def receive_text(self):
        # Simulate disconnect after first receive
        raise RuntimeError("Mock disconnect")

    async def close(self):
        self.closed = True


@pytest.mark.asyncio
async def test_ws_manager_connect(ws_manager: WebSocketManager):
    """Test WebSocket connection."""
    mock_ws = MockWebSocket()

    session = await ws_manager.connect(mock_ws, "test-client")

    assert session is not None
    assert session.client_id == "test-client"
    assert mock_ws.accepted is True
    assert ws_manager.get_client_count() == 1

    # Should have sent connected event
    assert len(mock_ws.sent_messages) == 1
    assert "connected" in mock_ws.sent_messages[0]


@pytest.mark.asyncio
async def test_ws_manager_disconnect(ws_manager: WebSocketManager):
    """Test WebSocket disconnection."""
    mock_ws = MockWebSocket()

    await ws_manager.connect(mock_ws, "test-client")
    assert ws_manager.get_client_count() == 1

    await ws_manager.disconnect("test-client")
    assert ws_manager.get_client_count() == 0


@pytest.mark.asyncio
async def test_ws_manager_subscribe(ws_manager: WebSocketManager):
    """Test subscribing to a session."""
    mock_ws = MockWebSocket()

    await ws_manager.connect(mock_ws, "test-client")

    result = await ws_manager.subscribe("test-client", "test-session")
    assert result is True
    assert ws_manager.get_session_subscriber_count("test-session") == 1


@pytest.mark.asyncio
async def test_ws_manager_unsubscribe(ws_manager: WebSocketManager):
    """Test unsubscribing from a session."""
    mock_ws = MockWebSocket()

    await ws_manager.connect(mock_ws, "test-client")
    await ws_manager.subscribe("test-client", "test-session")

    result = await ws_manager.unsubscribe("test-client", "test-session")
    assert result is True
    assert ws_manager.get_session_subscriber_count("test-session") == 0


@pytest.mark.asyncio
async def test_ws_manager_subscribe_nonexistent_client(ws_manager: WebSocketManager):
    """Test subscribing with non-existent client."""
    result = await ws_manager.subscribe("nonexistent", "test-session")
    assert result is False


@pytest.mark.asyncio
async def test_ws_manager_send_to_client(ws_manager: WebSocketManager):
    """Test sending event to specific client."""
    mock_ws = MockWebSocket()

    await ws_manager.connect(mock_ws, "test-client")

    event = WebSocketEvent(
        type=EventType.SESSION_UPDATED,
        session_id="test-session",
        data={"updated": True},
    )

    result = await ws_manager.send_to_client("test-client", event)
    assert result is True
    assert len(mock_ws.sent_messages) == 2  # connected + event


@pytest.mark.asyncio
async def test_ws_manager_send_to_nonexistent_client(ws_manager: WebSocketManager):
    """Test sending to non-existent client."""
    event = WebSocketEvent(type=EventType.ERROR, data={"error": "test"})

    result = await ws_manager.send_to_client("nonexistent", event)
    assert result is False


@pytest.mark.asyncio
async def test_ws_manager_broadcast_to_session(ws_manager: WebSocketManager):
    """Test broadcasting to session subscribers."""
    mock_ws1 = MockWebSocket()
    mock_ws2 = MockWebSocket()

    await ws_manager.connect(mock_ws1, "client-1")
    await ws_manager.connect(mock_ws2, "client-2")

    await ws_manager.subscribe("client-1", "test-session")
    await ws_manager.subscribe("client-2", "test-session")

    event = WebSocketEvent(
        type=EventType.CHAT_CHUNK,
        session_id="test-session",
        data={"content": "Hello"},
    )

    sent_count = await ws_manager.broadcast_to_session("test-session", event)
    assert sent_count == 2


@pytest.mark.asyncio
async def test_ws_manager_broadcast_all(ws_manager: WebSocketManager):
    """Test broadcasting to all clients."""
    mock_ws1 = MockWebSocket()
    mock_ws2 = MockWebSocket()

    await ws_manager.connect(mock_ws1, "client-1")
    await ws_manager.connect(mock_ws2, "client-2")

    event = WebSocketEvent(type=EventType.ERROR, data={"error": "test"})

    sent_count = await ws_manager.broadcast_all(event)
    assert sent_count == 2


# ============================================================================
# Message Handler Tests
# ============================================================================


@pytest.mark.asyncio
async def test_handle_ping_message(
    ws_manager: WebSocketManager, chat_handler: StreamingChatHandler
):
    """Test handling ping message."""
    mock_ws = MockWebSocket()
    await ws_manager.connect(mock_ws, "test-client")

    msg = WSMessage(type=WSMessageType.PING)
    await handle_ws_message(msg, "test-client", ws_manager, chat_handler)

    # Should have sent pong response
    assert len(mock_ws.sent_messages) == 2  # connected + pong


@pytest.mark.asyncio
async def test_handle_subscribe_message(
    ws_manager: WebSocketManager, chat_handler: StreamingChatHandler
):
    """Test handling subscribe message."""
    mock_ws = MockWebSocket()
    await ws_manager.connect(mock_ws, "test-client")

    msg = WSMessage(
        type=WSMessageType.SUBSCRIBE,
        data={"session_id": "test-session"},
    )
    await handle_ws_message(msg, "test-client", ws_manager, chat_handler)

    assert ws_manager.get_session_subscriber_count("test-session") == 1


@pytest.mark.asyncio
async def test_handle_unsubscribe_message(
    ws_manager: WebSocketManager, chat_handler: StreamingChatHandler
):
    """Test handling unsubscribe message."""
    mock_ws = MockWebSocket()
    await ws_manager.connect(mock_ws, "test-client")
    await ws_manager.subscribe("test-client", "test-session")

    msg = WSMessage(
        type=WSMessageType.UNSUBSCRIBE,
        data={"session_id": "test-session"},
    )
    await handle_ws_message(msg, "test-client", ws_manager, chat_handler)

    assert ws_manager.get_session_subscriber_count("test-session") == 0
