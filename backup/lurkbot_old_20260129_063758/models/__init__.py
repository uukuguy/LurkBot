"""Multi-model support for LurkBot.

This module provides a unified interface for multiple LLM providers:
- Anthropic Claude (native SDK)
- OpenAI GPT (native SDK)
- Ollama (local models via HTTP API)
"""

from lurkbot.models.base import ModelAdapter
from lurkbot.models.registry import BUILTIN_MODELS, ModelRegistry, get_model_registry
from lurkbot.models.types import (
    ApiType,
    ModelCapabilities,
    ModelConfig,
    ModelCost,
    ModelResponse,
    StreamChunk,
    ToolCall,
    ToolResult,
)

__all__ = [
    # Types
    "ApiType",
    "ModelCapabilities",
    "ModelConfig",
    "ModelCost",
    "ModelResponse",
    "StreamChunk",
    "ToolCall",
    "ToolResult",
    # Base class
    "ModelAdapter",
    # Registry
    "ModelRegistry",
    "BUILTIN_MODELS",
    "get_model_registry",
]
