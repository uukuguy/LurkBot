"""Model types and data classes for multi-model support."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ApiType(str, Enum):
    """Supported API types for model providers."""

    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    OLLAMA = "ollama"
    LITELLM = "litellm"  # Extension for additional providers


class ModelCost(BaseModel):
    """Model pricing (USD per million tokens)."""

    input: float = 0.0
    output: float = 0.0
    cache_read: float = 0.0
    cache_write: float = 0.0


class ModelCapabilities(BaseModel):
    """Model capability configuration."""

    supports_tools: bool = True
    supports_vision: bool = False
    supports_streaming: bool = True
    supports_thinking: bool = False  # Extended thinking (Anthropic-specific)
    max_output_tokens: int | None = None


class ModelConfig(BaseModel):
    """Model configuration."""

    id: str  # e.g., "anthropic/claude-sonnet-4-20250514"
    name: str  # e.g., "Claude Sonnet 4"
    api_type: ApiType
    provider: str  # e.g., "anthropic", "openai", "ollama"
    model_id: str  # API model identifier
    context_window: int = 128000
    max_tokens: int = 4096
    cost: ModelCost = Field(default_factory=ModelCost)
    capabilities: ModelCapabilities = Field(default_factory=ModelCapabilities)


@dataclass
class ToolCall:
    """A tool call request from the model."""

    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class ModelResponse:
    """Unified model response."""

    text: str | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)
    stop_reason: str | None = None
    usage: dict[str, int] = field(default_factory=dict)
    raw: Any = None


@dataclass
class StreamChunk:
    """Streaming response chunk."""

    text: str | None = None
    tool_use_id: str | None = None
    tool_name: str | None = None
    tool_input_delta: str | None = None
    finish_reason: str | None = None


@dataclass
class ToolResult:
    """Result of a tool execution for sending back to the model."""

    tool_use_id: str
    content: str
    is_error: bool = False
