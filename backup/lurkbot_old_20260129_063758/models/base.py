"""Abstract base class for model adapters."""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Any

from lurkbot.models.types import (
    ModelConfig,
    ModelResponse,
    StreamChunk,
    ToolResult,
)


class ModelAdapter(ABC):
    """Abstract base class for model adapters.

    Each adapter implements the interface for a specific model provider
    (Anthropic, OpenAI, Ollama, etc.) while presenting a unified API.
    """

    def __init__(
        self,
        config: ModelConfig,
        api_key: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize the adapter.

        Args:
            config: Model configuration
            api_key: API key for the provider (if required)
            **kwargs: Additional provider-specific options
        """
        self.config = config
        self.api_key = api_key
        self._client: Any = None
        self._extra_options = kwargs

    @property
    @abstractmethod
    def client(self) -> Any:
        """Lazy-load and return the provider client.

        Subclasses must implement this to create the appropriate client.
        """
        ...

    @abstractmethod
    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        tool_results: list[ToolResult] | None = None,
        **kwargs: Any,
    ) -> ModelResponse:
        """Send a chat completion request.

        Args:
            messages: Conversation messages in provider-agnostic format
            tools: Available tools in Anthropic format (name, description, input_schema)
            tool_results: Results from previous tool executions
            **kwargs: Additional provider-specific parameters

        Returns:
            Unified model response
        """
        ...

    @abstractmethod
    async def stream_chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        tool_results: list[ToolResult] | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[StreamChunk]:
        """Stream a chat completion response.

        Args:
            messages: Conversation messages in provider-agnostic format
            tools: Available tools in Anthropic format
            tool_results: Results from previous tool executions
            **kwargs: Additional provider-specific parameters

        Yields:
            Stream chunks containing text or tool use deltas
        """
        ...

    def _get_max_tokens(self, **kwargs: Any) -> int:
        """Get max tokens from kwargs or config default."""
        return kwargs.get("max_tokens", self.config.max_tokens)
