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

        # Mock hello message with proper structure
        mock_websocket.receive_text = AsyncMock(
            return_value=json.dumps({
                "type": "hello",
                "minProtocol": 1,
                "maxProtocol": 1,
                "client": {
                    "id": "test-client-001",
                    "version": "1.0.0",
                    "platform": "test",
                    "mode": "cli",
                },
            })
        )

        # Create connection
        connection = GatewayConnection(mock_websocket, "test-conn")

        # Perform handshake
        await server._handshake(connection)

        # Verify hello_ok was sent
        mock_websocket.send_text.assert_called()
        call_args = mock_websocket.send_text.call_args[0][0]
        response = json.loads(call_args)

        assert response["type"] == "hello-ok"
        assert "server" in response
        assert "features" in response

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_handshake_with_invalid_message(self, mock_websocket: MagicMock):
        """Test handshake with invalid message type."""
        server = GatewayServer()

        # Mock invalid message
        mock_websocket.receive_text = AsyncMock(
            return_value=json.dumps({"type": "invalid", "params": {}})
        )

        connection = GatewayConnection(mock_websocket, "test-conn")

        with pytest.raises(ValueError, match="Expected hello"):
            await server._handshake(connection)


class TestGatewayProtocol:
    """Test Gateway protocol frame handling."""

    @pytest.mark.integration
    def test_connect_params_parsing(self):
        """Test parsing ConnectParams from JSON."""
        from lurkbot.gateway.protocol.frames import ClientInfo

        data = {
            "minProtocol": 1,
            "maxProtocol": 1,
            "client": {
                "id": "test-client-001",
                "version": "1.0.0",
                "platform": "test",
                "mode": "cli",
            },
        }

        params = ConnectParams(**data)
        assert params.client.id == "test-client-001"
        assert params.client.version == "1.0.0"
        assert params.min_protocol == 1

    @pytest.mark.integration
    def test_hello_ok_response(self):
        """Test HelloOk response structure."""
        server_info = ServerInfo(
            version="0.1.0",
            host=None,
            conn_id="test-conn-001",
        )

        features = Features(
            methods=["chat.send", "session.list"],
            events=["agent.*", "session.*"],
        )

        snapshot = Snapshot()

        hello_ok = HelloOk(
            type="hello-ok",
            protocol=1,
            server=server_info,
            features=features,
            snapshot=snapshot,
        )

        data = hello_ok.model_dump(by_alias=True)
        assert data["type"] == "hello-ok"
        assert data["server"]["version"] == "0.1.0"
        assert data["server"]["connId"] == "test-conn-001"
        assert "chat.send" in data["features"]["methods"]

    @pytest.mark.integration
    def test_event_frame_creation(self):
        """Test creating event frames."""
        import time

        event = EventFrame(
            id="evt-001",
            type="event",
            at=int(time.time() * 1000),
            event="message",
            payload={"content": "Hello, world!"},
        )

        data = event.model_dump()
        assert data["type"] == "event"
        assert data["event"] == "message"
        assert data["id"] == "evt-001"
        assert data["at"] > 0
        assert data["payload"]["content"] == "Hello, world!"

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

        # Process single request - note: _handle_request sends response directly
        msg = await connection.receive_json()
        await server._handle_request(connection, msg)

        # Verify error response was sent
        mock_websocket.send_text.assert_called()
        call_args = mock_websocket.send_text.call_args[0][0]
        response = json.loads(call_args)
        assert response.get("error") is not None or "error" in str(response)


class TestGatewayEventBroadcasting:
    """Test Gateway event broadcasting."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_broadcast_to_connections(self, mock_websocket: MagicMock):
        """Test broadcasting events to connected clients via EventBroadcaster."""
        from lurkbot.gateway.events import EventBroadcaster

        broadcaster = EventBroadcaster()
        events_received = []

        # Create async callback
        async def on_event(event: EventFrame):
            events_received.append(event)
            await mock_websocket.send_text(json.dumps(event.model_dump(by_alias=True)))

        # Subscribe to events
        broadcaster.subscribe(on_event)

        # Emit event
        event = await broadcaster.emit(
            event="test_event",
            payload={"message": "Hello"},
        )

        # Verify event was sent
        assert len(events_received) == 1
        assert events_received[0].event == "test_event"
        mock_websocket.send_text.assert_called()
        call_args = mock_websocket.send_text.call_args[0][0]
        sent_data = json.loads(call_args)
        assert sent_data["event"] == "test_event"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_broadcast_to_multiple_connections(self):
        """Test broadcasting to multiple connections via EventBroadcaster."""
        from lurkbot.gateway.events import EventBroadcaster

        broadcaster = EventBroadcaster()

        # Create multiple mock connections with callbacks
        connections = []
        received_events = {0: [], 1: [], 2: []}

        for i in range(3):
            ws = MagicMock()
            ws.send_text = AsyncMock()
            connections.append(ws)

            # Create closure to capture index
            async def make_callback(idx):
                async def callback(event: EventFrame):
                    received_events[idx].append(event)
                    await connections[idx].send_text(json.dumps(event.model_dump(by_alias=True)))
                return callback

            broadcaster.subscribe(await make_callback(i))

        # Emit event
        await broadcaster.emit(
            event="broadcast_test",
            payload={"count": 3},
        )

        # Verify all connections received the event
        for i, ws in enumerate(connections):
            assert len(received_events[i]) == 1
            ws.send_text.assert_called()


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
            channels=[
                {"id": "channel-1", "type": "discord"},
            ],
        )

        data = snapshot.model_dump(by_alias=True)
        assert len(data["sessions"]) == 2
        assert len(data["channels"]) == 1
        assert "cronJobs" in data  # Aliased from cron_jobs

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_send_snapshot_on_connect(self, mock_websocket: MagicMock):
        """Test sending snapshot after successful connection."""
        server = GatewayServer()

        # Mock hello message with proper structure
        mock_websocket.receive_text = AsyncMock(
            return_value=json.dumps({
                "type": "hello",
                "minProtocol": 1,
                "maxProtocol": 1,
                "client": {
                    "id": "test-client-001",
                    "version": "1.0.0",
                    "platform": "test",
                    "mode": "cli",
                },
            })
        )

        connection = GatewayConnection(mock_websocket, "test-conn")

        # Perform handshake
        await server._handshake(connection)

        # Verify snapshot was sent (part of hello-ok response)
        assert mock_websocket.send_text.called
        call_args = mock_websocket.send_text.call_args[0][0]
        response = json.loads(call_args)
        assert response["type"] == "hello-ok"
        assert "snapshot" in response


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
    assert total_tests >= 17, f"Expected at least 17 tests, got {total_tests}"
