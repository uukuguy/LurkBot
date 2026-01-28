"""Tests for gateway protocol."""

from lurkbot.gateway.protocol import (
    ChannelMessage,
    ConnectMessage,
    Message,
    MessageType,
    RequestMessage,
    ResponseMessage,
)


def test_message_type_enum() -> None:
    """Test MessageType enum values."""
    assert MessageType.CONNECT == "connect"
    assert MessageType.REQUEST == "req"
    assert MessageType.RESPONSE == "res"


def test_message_creation() -> None:
    """Test basic message creation."""
    msg = Message(type=MessageType.PING)

    assert msg.type == MessageType.PING
    assert msg.payload == {}
    assert msg.timestamp is not None


def test_connect_message() -> None:
    """Test ConnectMessage creation."""
    msg = ConnectMessage(client_id="test-client", auth_token="secret")

    assert msg.type == MessageType.CONNECT
    assert msg.client_id == "test-client"
    assert msg.auth_token == "secret"


def test_request_message() -> None:
    """Test RequestMessage creation."""
    msg = RequestMessage(
        id="req-1",
        method="chat",
        params={"message": "Hello"},
    )

    assert msg.type == MessageType.REQUEST
    assert msg.method == "chat"
    assert msg.params == {"message": "Hello"}


def test_response_message() -> None:
    """Test ResponseMessage creation."""
    msg = ResponseMessage(
        request_id="req-1",
        result={"response": "Hi there"},
    )

    assert msg.type == MessageType.RESPONSE
    assert msg.request_id == "req-1"
    assert msg.result == {"response": "Hi there"}
    assert msg.error is None


def test_channel_message() -> None:
    """Test ChannelMessage creation."""
    msg = ChannelMessage(
        channel="telegram",
        sender_id="123",
        sender_name="Test User",
        content="Hello, bot!",
    )

    assert msg.type == MessageType.CHANNEL_MESSAGE
    assert msg.channel == "telegram"
    assert msg.sender_id == "123"
    assert msg.content == "Hello, bot!"
