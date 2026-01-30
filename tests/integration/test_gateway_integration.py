"""Integration tests for Gateway WebSocket server.

Tests the complete Gateway lifecycle including:
- WebSocket connection and handshake
- Protocol frame handling
- Event broadcasting
- Method invocation
"""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from lurkbot.gateway.server import GatewayServer, GatewayConnection
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
)


class TestGatewayHandshake:
    """Test Gateway WebSocket handshake."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_successful_handshake(self, mock_websocket: MagicMock):
        """Test successful WebSocket handshake."""
        server = GatewayServer()

        # Mock hello message
        mock_websocket.receive_json = AsyncMock(
            return_value={
                "type": "hello",
                "params": {
                    "client": {
                        "name": "test-client",
                        "version": "1.0.0",
                    }
                },
            }
        )

        # Create connection
        connection = GatewayConnection(mock_websocket, "test-conn")

        # Perform handshake
        await server._handshake(connection)

        # Verify hello_ok was sent
        mock_websocket.send_text.assert_called()
        call_args = mock_websocket.send_text.call_args[0][0]
        response = json.loads(call_args)

        assert response["type"] == "hello_ok"
        assert "server" in response
        assert "features" in response

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_handshake_with_invalid_message(self, mock_websocket: MagicMock):
        """Test handshake with invalid message type."""
        server = GatewayServer()

        # Mock invalid message
        mock_websocket.receive_json = AsyncMock(
            return_value={"type": "invalid", "params": {}}
        )

        connection = GatewayConnection(mock_websocket, "test-conn")

        with pytest.raises(ValueError, match="Expected hello"):
            await server._handshake(connection)


class TestGatewayProtocol:
    """Test Gateway protocol frame handling."""

    @pytest.mark.integration
    def test_connect_params_parsing(self):
        """Test parsing ConnectParams from JSON."""
        data = {
            "client": {
                "name": "test-client",
                "version": "1.0.0",
            },
            "auth": {
                "token": "test-token",
            },
        }

        params = ConnectParams(**data)
        assert params.client.name == "test-client"
        assert params.client.version == "1.0.0"

    @pytest.mark.integration
    def test_hello_ok_response(self):
        """Test HelloOk response structure."""
        server_info = ServerInfo(
            name="LurkBot Gateway",
            version="0.1.0",
            protocol_version=1,
        )

        features = Features(
            streaming=True,
            tools=True,
            canvas=True,
        )

        hello_ok = HelloOk(
            type="hello_ok",
            server=server_info,
            features=features,
        )

        data = hello_ok.model_dump()
        assert data["type"] == "hello_ok"
        assert data["server"]["name"] == "LurkBot Gateway"
        assert data["features"]["streaming"] is True

    @pytest.mark.integration
    def test_event_frame_creation(self):
        """Test creating event frames."""
        event = EventFrame(
            type="event",
            event="message",
            data={"content": "Hello, world!"},
        )

        data = event.model_dump()
        assert data["type"] == "event"
        assert data["event"] == "message"
        assert data["data"]["content"] == "Hello, world!"

    @pytest.mark.integration
    def test_request_frame_parsing(self):
        """Test parsing request frames."""
        data = {
            "type": "request",
            "id": "req-001",
            "method": "chat",
            "params": {
                "message": "Hello",
                "session_id": "test-session",
            },
        }

        request = RequestFrame(**data)
        assert request.id == "req-001"
        assert request.method == "chat"
        assert request.params["message"] == "Hello"

    @pytest.mark.integration
    def test_response_frame_creation(self):
        """Test creating response frames."""
        response = ResponseFrame(
            type="response",
            id="req-001",
            result={"status": "ok", "message": "Success"},
        )

        data = response.model_dump()
        assert data["type"] == "response"
        assert data["id"] == "req-001"
        assert data["result"]["status"] == "ok"


class TestGatewayMessageLoop:
    """Test Gateway message loop handling."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_handle_request(self, mock_websocket: MagicMock):
        """Test handling a request message."""
        server = GatewayServer()

        # Setup mock to return request then disconnect
        messages = [
            json.dumps({
                "type": "request",
                "id": "req-001",
                "method": "ping",
                "params": {},
            }),
        ]
        mock_websocket.receive_text = AsyncMock(side_effect=messages + [Exception("disconnect")])

        connection = GatewayConnection(mock_websocket, "test-conn")
        connection.authenticated = True

        # Handle single message
        try:
            await server._message_loop(connection)
        except Exception:
            pass  # Expected disconnect

        # Verify response was sent
        assert mock_websocket.send_text.called

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_handle_unknown_method(self, mock_websocket: MagicMock):
        """Test handling unknown method."""
        server = GatewayServer()

        # Mock request with unknown method
        mock_websocket.receive_text = AsyncMock(
            return_value=json.dumps({
                "type": "request",
                "id": "req-001",
                "method": "unknown_method",
                "params": {},
            })
        )

        connection = GatewayConnection(mock_websocket, "test-conn")
        connection.authenticated = True

        # Process single request
        msg = await connection.receive_json()
        response = await server._handle_request(connection, msg)

        # Should return error response
        assert response.get("error") is not None or "error" in str(response)


class TestGatewayEventBroadcasting:
    """Test Gateway event broadcasting."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_broadcast_to_connections(self, mock_websocket: MagicMock):
        """Test broadcasting events to connected clients."""
        server = GatewayServer()

        # Add mock connection
        connection = GatewayConnection(mock_websocket, "test-conn")
        connection.authenticated = True
        server._connections.add(connection)

        # Broadcast event
        event = EventFrame(
            type="event",
            event="test_event",
            data={"message": "Hello"},
        )

        await server.broadcast(event)

        # Verify event was sent
        mock_websocket.send_text.assert_called()
        call_args = mock_websocket.send_text.call_args[0][0]
        sent_data = json.loads(call_args)
        assert sent_data["event"] == "test_event"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_broadcast_to_multiple_connections(self):
        """Test broadcasting to multiple connections."""
        server = GatewayServer()

        # Create multiple mock connections
        connections = []
        for i in range(3):
            ws = MagicMock()
            ws.send_text = AsyncMock()
            conn = GatewayConnection(ws, f"conn-{i}")
            conn.authenticated = True
            connections.append(conn)
            server._connections.add(conn)

        # Broadcast event
        event = EventFrame(
            type="event",
            event="broadcast_test",
            data={"count": 3},
        )

        await server.broadcast(event)

        # Verify all connections received the event
        for conn in connections:
            conn.websocket.send_text.assert_called()


class TestGatewayConnectionManagement:
    """Test Gateway connection management."""

    @pytest.mark.integration
    def test_connection_creation(self, mock_websocket: MagicMock):
        """Test creating a gateway connection."""
        connection = GatewayConnection(mock_websocket, "test-conn")

        assert connection.conn_id == "test-conn"
        assert connection.authenticated is False
        assert connection.client_info is None

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_connection_send_json(self, mock_websocket: MagicMock):
        """Test sending JSON through connection."""
        connection = GatewayConnection(mock_websocket, "test-conn")

        await connection.send_json({"type": "test", "data": "hello"})

        mock_websocket.send_text.assert_called_once()
        call_args = mock_websocket.send_text.call_args[0][0]
        assert json.loads(call_args) == {"type": "test", "data": "hello"}

    @pytest.mark.integration
    def test_connection_tracking(self):
        """Test connection tracking in server."""
        server = GatewayServer()

        # Initially no connections
        assert len(server._connections) == 0

        # Add connections
        ws1 = MagicMock()
        ws2 = MagicMock()
        conn1 = GatewayConnection(ws1, "conn-1")
        conn2 = GatewayConnection(ws2, "conn-2")

        server._connections.add(conn1)
        server._connections.add(conn2)

        assert len(server._connections) == 2

        # Remove connection
        server._connections.discard(conn1)
        assert len(server._connections) == 1


class TestGatewaySnapshot:
    """Test Gateway snapshot functionality."""

    @pytest.mark.integration
    def test_snapshot_creation(self):
        """Test creating a snapshot."""
        snapshot = Snapshot(
            sessions=[
                {"id": "session-1", "type": "main"},
                {"id": "session-2", "type": "group"},
            ],
            agents=[
                {"id": "agent-1", "name": "Test Agent"},
            ],
        )

        data = snapshot.model_dump()
        assert len(data["sessions"]) == 2
        assert len(data["agents"]) == 1

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_send_snapshot_on_connect(self, mock_websocket: MagicMock):
        """Test sending snapshot after successful connection."""
        server = GatewayServer()

        # Mock hello message
        mock_websocket.receive_json = AsyncMock(
            return_value={
                "type": "hello",
                "params": {
                    "client": {"name": "test", "version": "1.0"},
                },
            }
        )

        connection = GatewayConnection(mock_websocket, "test-conn")

        # Perform handshake
        await server._handshake(connection)

        # Verify snapshot was sent (part of hello_ok or separate)
        assert mock_websocket.send_text.called


# Test count verification
def test_gateway_integration_test_count():
    """Verify the number of integration tests."""
    import inspect

    test_classes = [
        TestGatewayHandshake,
        TestGatewayProtocol,
        TestGatewayMessageLoop,
        TestGatewayEventBroadcasting,
        TestGatewayConnectionManagement,
        TestGatewaySnapshot,
    ]

    total_tests = 0
    for cls in test_classes:
        methods = [m for m in dir(cls) if m.startswith("test_")]
        total_tests += len(methods)

    # Add standalone test
    total_tests += 1  # test_gateway_integration_test_count

    print(f"\n✅ Gateway integration tests: {total_tests} tests")
    assert total_tests >= 18, f"Expected at least 18 tests, got {total_tests}"
