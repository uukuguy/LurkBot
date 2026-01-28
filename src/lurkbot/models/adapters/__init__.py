"""Model adapters for different providers."""

from lurkbot.models.adapters.anthropic import AnthropicAdapter
from lurkbot.models.adapters.ollama import OllamaAdapter
from lurkbot.models.adapters.openai import OpenAIAdapter

__all__ = [
    "AnthropicAdapter",
    "OpenAIAdapter",
    "OllamaAdapter",
]
