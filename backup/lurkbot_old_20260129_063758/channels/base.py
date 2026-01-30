"""Base channel definitions."""

from abc import ABC, abstractmethod
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class ChannelMessage:
    """A message from a channel."""

    channel: str
    message_id: str
    sender_id: str
    sender_name: str | None
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    reply_to: str | None = None
    attachments: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


MessageHandler = Callable[[ChannelMessage], Coroutine[Any, Any, None]]


class Channel(ABC):
    """Base class for channel adapters."""

    def __init__(self, name: str) -> None:
        self.name = name
        self._handlers: list[MessageHandler] = []

    def on_message(self, handler: MessageHandler) -> MessageHandler:
        """Register a message handler."""
        self._handlers.append(handler)
        return handler

    async def _dispatch(self, message: ChannelMessage) -> None:
        """Dispatch a message to all handlers."""
        for handler in self._handlers:
            await handler(message)

    @abstractmethod
    async def start(self) -> None:
        """Start the channel adapter."""
        ...

    @abstractmethod
    async def stop(self) -> None:
        """Stop the channel adapter."""
        ...

    @abstractmethod
    async def send(
        self,
        recipient_id: str,
        content: str,
        reply_to: str | None = None,
    ) -> str:
        """Send a message to a recipient.

        Args:
            recipient_id: The recipient's ID (user or chat)
            content: The message content
            reply_to: Optional message ID to reply to

        Returns:
            The sent message ID
        """
        ...

    @abstractmethod
    async def send_typing(self, recipient_id: str) -> None:
        """Send a typing indicator."""
        ...
