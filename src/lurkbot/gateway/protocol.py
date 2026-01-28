"""Gateway protocol definitions."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class MessageType(str, Enum):
    """WebSocket message types."""

    # Connection
    CONNECT = "connect"
    DISCONNECT = "disconnect"
    PING = "ping"
    PONG = "pong"

    # Request/Response
    REQUEST = "req"
    RESPONSE = "res"
    ERROR = "error"

    # Events
    EVENT = "event"

    # Channel messages
    CHANNEL_MESSAGE = "channel_message"
    CHANNEL_TYPING = "channel_typing"


class Message(BaseModel):
    """Base WebSocket message."""

    type: MessageType
    id: str | None = None
    timestamp: datetime = Field(default_factory=datetime.now)
    payload: dict[str, Any] = Field(default_factory=dict)


class ConnectMessage(Message):
    """Connection handshake message."""

    type: MessageType = MessageType.CONNECT
    client_id: str | None = None
    auth_token: str | None = None


class RequestMessage(Message):
    """RPC request message."""

    type: MessageType = MessageType.REQUEST
    method: str
    params: dict[str, Any] = Field(default_factory=dict)


class ResponseMessage(Message):
    """RPC response message."""

    type: MessageType = MessageType.RESPONSE
    request_id: str
    result: Any = None
    error: str | None = None


class ChannelMessage(Message):
    """Message from a channel."""

    type: MessageType = MessageType.CHANNEL_MESSAGE
    channel: str
    sender_id: str
    sender_name: str | None = None
    content: str
    attachments: list[dict[str, Any]] = Field(default_factory=list)
