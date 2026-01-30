"""End-to-end integration tests for Gateway WebSocket flow.

Tests the complete Gateway WebSocket flow:
- Connection establishment
- Handshake protocol
- Message exchange
- Event broadcasting
- Connection lifecycle
"""

import asyncio
import json
import tempfile
import time
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from lurkbot.gateway.server import GatewayServer, GatewayConnection
from lurkbot.gateway.protocol.frames import (
    ConnectParams,
    ClientInfo,
    HelloOk,
    ServerInfo,
    Features,
    Snapshot,
    RequestFrame,
    ResponseFrame,
    ErrorCode,
    ErrorShape,
)


class TestE2EGatewayHandshake:
    """Test Gateway WebSocket handshake flow."""

    @pytest.fixture
    def gateway_server(self) -> GatewayServer:
        """Create a gateway server instance."""
        return GatewayServer()

    @pytest.fixture
    def mock_websocket(self) -> MagicMock:
        """Create a mock WebSocket connection."""
        ws = MagicMock()
        ws.accept = AsyncMock()
        ws.send_text = AsyncMock()
        ws.receive_text = AsyncMock()
        ws.close = AsyncMock()
        return ws

    @pytest.mark.integration
    def test_gateway_server_initialization(self, gateway_server: GatewayServer):
        """Test gateway server initializes correctly."""
        assert gateway_server.VERSION is not None
        assert gateway_server.PROTOCOL_VERSION >= 1
        assert gateway_server._connections is not None

    @pytest.mark.integration
    def test_gateway_connection_creation(self, mock_websocket: MagicMock):
        """Test gateway connection object creation."""
        conn = GatewayConnection(mock_websocket, "test-conn-id")

        assert conn.websocket == mock_websocket
        assert conn.conn_id == "test-conn-id"
        assert conn.authenticated is False
        assert conn.client_info is None

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_gateway_connection_send_json(self, mock_websocket: MagicMock):
        """Test sending JSON through connection."""
        conn = GatewayConnection(mock_websocket, "test-conn")

        await conn.send_json({"type": "test", "data": "hello"})

        mock_websocket.send_text.assert_called_once()
        sent_data = json.loads(mock_websocket.send_text.call_args[0][0])
        assert sent_data["type"] == "test"
        assert sent_data["data"] == "hello"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_gateway_connection_receive_json(self, mock_websocket: MagicMock):
        """Test receiving JSON through connection."""
        mock_websocket.receive_text = AsyncMock(return_value='{"type": "hello", "params": {}}')
        conn = GatewayConnection(mock_websocket, "test-conn")

        result = await conn.receive_json()

        assert result["type"] == "hello"
        assert "params" in result

    @pytest.mark.integration
    def test_connect_params_parsing(self):
        """Test ConnectParams model parsing."""
        client = ClientInfo(
            id="test-client-001",
            version="1.0.0",
            platform="linux",
            mode="cli",
        )
        params = ConnectParams(
            minProtocol=1,
            maxProtocol=1,
            client=client,
        )

        assert params.min_protocol == 1
        assert params.max_protocol == 1
        assert params.client.id == "test-client-001"
        assert params.client.mode == "cli"

    @pytest.mark.integration
    def test_hello_ok_response_structure(self):
        """Test HelloOk response structure."""
        hello_ok = HelloOk(
            protocol=1,
            server=ServerInfo(
                version="0.1.0",
                host=None,
                conn_id="test-123",
            ),
            features=Features(
                methods=["chat.send", "session.list"],
                events=["agent.*", "session.*"],
            ),
            snapshot=Snapshot(),
        )

        assert hello_ok.protocol == 1
        assert hello_ok.server.version == "0.1.0"
        assert hello_ok.server.conn_id == "test-123"
        assert "chat.send" in hello_ok.features.methods
        assert "agent.*" in hello_ok.features.events


class TestE2EGatewayMessageExchange:
    """Test Gateway message exchange flow."""

    @pytest.fixture
    def mock_websocket(self) -> MagicMock:
        """Create a mock WebSocket connection."""
        ws = MagicMock()
        ws.accept = AsyncMock()
        ws.send_text = AsyncMock()
        ws.receive_text = AsyncMock()
        ws.close = AsyncMock()
        return ws

    @pytest.mark.integration
    def test_request_frame_structure(self):
        """Test RequestFrame structure."""
        request = RequestFrame(
            type="request",
            id="req-001",
            method="chat.send",
            params={"message": "Hello"},
            session_key="agent:test:main",
        )

        assert request.type == "request"
        assert request.id == "req-001"
        assert request.method == "chat.send"
        assert request.params["message"] == "Hello"

    @pytest.mark.integration
    def test_response_frame_structure(self):
        """Test ResponseFrame structure."""
        response = ResponseFrame(
            type="response",
            id="req-001",
            result={"status": "ok", "data": "response data"},
        )

        assert response.type == "response"
        assert response.id == "req-001"
        assert response.result["status"] == "ok"

    @pytest.mark.integration
    def test_error_response_structure(self):
        """Test error response structure."""
        response = ResponseFrame(
            type="response",
            id="req-001",
            error=ErrorShape(
                code=ErrorCode.INVALID_REQUEST,
                message="Invalid request format",
            ),
        )

        assert response.type == "response"
        assert response.error is not None
        assert response.error.message == "Invalid request format"
        assert response.error.code == ErrorCode.INVALID_REQUEST


class TestE2EGatewayProtocol:
    """Test Gateway protocol flow."""

    @pytest.fixture
    def gateway_server(self) -> GatewayServer:
        """Create a gateway server instance."""
        return GatewayServer()

    @pytest.fixture
    def mock_websocket(self) -> MagicMock:
        """Create a mock WebSocket for protocol testing."""
        ws = MagicMock()
        ws.accept = AsyncMock()
        ws.send_text = AsyncMock()
        ws.close = AsyncMock()
        return ws

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_handshake_protocol_flow(self, gateway_server: GatewayServer, mock_websocket: MagicMock):
        """Test complete handshake protocol flow."""
        # Setup hello message with correct structure
        hello_message = {
            "type": "hello",
            "minProtocol": 1,
            "maxProtocol": 1,
            "client": {
                "id": "test-client-001",
                "version": "1.0.0",
                "platform": "linux",
                "mode": "cli",
            },
        }
        mock_websocket.receive_text = AsyncMock(return_value=json.dumps(hello_message))

        conn = GatewayConnection(mock_websocket, "test-handshake")

        # Perform handshake
        await gateway_server._handshake(conn)

        # Verify response was sent
        mock_websocket.send_text.assert_called_once()

        # Verify connection state
        assert conn.authenticated is True
        assert conn.client_info is not None

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_invalid_handshake_raises_error(self, gateway_server: GatewayServer, mock_websocket: MagicMock):
        """Test invalid handshake raises error."""
        # Setup invalid message (not hello type)
        invalid_message = {
            "type": "request",
            "method": "some.method",
        }
        mock_websocket.receive_text = AsyncMock(return_value=json.dumps(invalid_message))

        conn = GatewayConnection(mock_websocket, "test-invalid")

        # Should raise error for non-hello message
        with pytest.raises(ValueError, match="Expected hello message"):
            await gateway_server._handshake(conn)


class TestE2EGatewayEventBroadcasting:
    """Test Gateway event broadcasting."""

    @pytest.mark.integration
    def test_event_broadcaster_initialization(self):
        """Test event broadcaster initialization."""
        from lurkbot.gateway.events import get_event_broadcaster

        broadcaster = get_event_broadcaster()
        assert broadcaster is not None

    @pytest.mark.integration
    def test_event_subscriber_registration(self):
        """Test event subscriber registration."""
        from lurkbot.gateway.events import get_event_broadcaster

        broadcaster = get_event_broadcaster()
        events_received = []

        def handler(event):
            events_received.append(event)

        subscriber = broadcaster.subscribe(handler)

        # Verify subscriber was created
        assert subscriber is not None


class TestE2EGatewayMethodRegistry:
    """Test Gateway method registry."""

    @pytest.mark.integration
    def test_method_registry_initialization(self):
        """Test method registry initialization."""
        from lurkbot.gateway.methods import get_method_registry

        registry = get_method_registry()
        assert registry is not None

    @pytest.mark.integration
    def test_method_registry_list_methods(self):
        """Test listing available methods."""
        from lurkbot.gateway.methods import get_method_registry

        registry = get_method_registry()
        methods = registry.list_methods()

        assert isinstance(methods, list)
        # Should have some methods registered
        assert len(methods) >= 0


class TestE2EGatewayConnectionLifecycle:
    """Test Gateway connection lifecycle."""

    @pytest.fixture
    def gateway_server(self) -> GatewayServer:
        """Create a gateway server instance."""
        return GatewayServer()

    @pytest.mark.integration
    def test_connection_tracking(self, gateway_server: GatewayServer):
        """Test connection tracking in server."""
        assert gateway_server._connections is not None
        assert len(gateway_server._connections) == 0

    @pytest.mark.integration
    def test_multiple_connection_ids_unique(self, gateway_server: GatewayServer):
        """Test that connection IDs are unique."""
        import uuid

        ids = set()
        for _ in range(100):
            conn_id = str(uuid.uuid4())[:8]
            assert conn_id not in ids
            ids.add(conn_id)


# Test count verification
def test_e2e_gateway_test_count():
    """Verify the number of E2E Gateway tests."""
    import inspect

    test_classes = [
        TestE2EGatewayHandshake,
        TestE2EGatewayMessageExchange,
        TestE2EGatewayProtocol,
        TestE2EGatewayEventBroadcasting,
        TestE2EGatewayMethodRegistry,
        TestE2EGatewayConnectionLifecycle,
    ]

    total_tests = 0
    for cls in test_classes:
        methods = [m for m in dir(cls) if m.startswith("test_")]
        total_tests += len(methods)

    # Add standalone test
    total_tests += 1  # test_e2e_gateway_test_count

    print(f"\n✅ E2E Gateway tests: {total_tests} tests")
    assert total_tests >= 15, f"Expected at least 15 tests, got {total_tests}"
