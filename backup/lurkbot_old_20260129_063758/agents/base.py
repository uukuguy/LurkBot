"""Base agent definitions."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel

from lurkbot.tools.base import SessionType


class ChatMessage(BaseModel):
    """A chat message in a conversation."""

    role: str  # "user", "assistant", "system"
    content: str
    name: str | None = None
    tool_calls: list[dict[str, Any]] | None = None
    tool_call_id: str | None = None


@dataclass
class AgentContext:
    """Context for agent execution."""

    session_id: str
    channel: str
    sender_id: str
    sender_name: str | None = None
    workspace: str | None = None
    messages: list[ChatMessage] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    session_type: SessionType = SessionType.MAIN  # NEW: Add session type for tool policies


class Agent(ABC):
    """Base class for AI agents."""

    def __init__(self, model: str, **kwargs: Any) -> None:
        self.model = model
        self.config = kwargs

    @abstractmethod
    async def chat(self, context: AgentContext, message: str) -> str:
        """Process a chat message and return a response.

        Args:
            context: The agent execution context
            message: The user's message

        Returns:
            The agent's response
        """
        ...

    @abstractmethod
    async def stream_chat(self, context: AgentContext, message: str) -> "AsyncIterator[str]":  # noqa: F821
        """Process a chat message and stream the response.

        Args:
            context: The agent execution context
            message: The user's message

        Yields:
            Chunks of the agent's response
        """
        ...
