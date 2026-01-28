"""Tests for model adapters."""

import json
from collections.abc import AsyncIterator
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from lurkbot.models.adapters.anthropic import AnthropicAdapter
from lurkbot.models.adapters.ollama import OllamaAdapter
from lurkbot.models.adapters.openai import OpenAIAdapter
from lurkbot.models.types import (
    ApiType,
    ModelCapabilities,
    ModelConfig,
    ModelCost,
    ToolResult,
)


@pytest.fixture
def anthropic_config() -> ModelConfig:
    """Create Anthropic model config."""
    return ModelConfig(
        id="anthropic/claude-sonnet-4",
        name="Claude Sonnet 4",
        api_type=ApiType.ANTHROPIC,
        provider="anthropic",
        model_id="claude-sonnet-4-20250514",
        max_tokens=4096,
    )


@pytest.fixture
def openai_config() -> ModelConfig:
    """Create OpenAI model config."""
    return ModelConfig(
        id="openai/gpt-4o",
        name="GPT-4o",
        api_type=ApiType.OPENAI,
        provider="openai",
        model_id="gpt-4o",
        max_tokens=4096,
    )


@pytest.fixture
def ollama_config() -> ModelConfig:
    """Create Ollama model config."""
    return ModelConfig(
        id="ollama/llama3.3",
        name="Llama 3.3",
        api_type=ApiType.OLLAMA,
        provider="ollama",
        model_id="llama3.3",
        max_tokens=4096,
    )


class TestAnthropicAdapter:
    """Test AnthropicAdapter."""

    def test_init(self, anthropic_config: ModelConfig) -> None:
        """Test adapter initialization."""
        adapter = AnthropicAdapter(anthropic_config, api_key="test-key")
        assert adapter.config == anthropic_config
        assert adapter.api_key == "test-key"
        assert adapter._client is None

    @patch("anthropic.AsyncAnthropic")
    def test_client_lazy_load(
        self, mock_client_class: MagicMock, anthropic_config: ModelConfig
    ) -> None:
        """Test that client is lazily loaded."""
        adapter = AnthropicAdapter(anthropic_config, api_key="test-key")
        assert adapter._client is None

        client = adapter.client
        mock_client_class.assert_called_once_with(api_key="test-key")

        # Second access should not create new client
        client2 = adapter.client
        mock_client_class.assert_called_once()

    @pytest.mark.asyncio
    async def test_chat_simple(self, anthropic_config: ModelConfig) -> None:
        """Test simple chat without tools."""
        adapter = AnthropicAdapter(anthropic_config, api_key="test-key")

        # Mock response
        mock_response = MagicMock()
        mock_response.content = [MagicMock(type="text", text="Hello!")]
        mock_response.stop_reason = "end_turn"
        mock_response.usage = MagicMock(input_tokens=10, output_tokens=5)

        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        adapter._client = mock_client

        messages = [{"role": "user", "content": "Hi"}]
        response = await adapter.chat(messages)

        assert response.text == "Hello!"
        assert response.stop_reason == "end_turn"
        assert response.usage["input_tokens"] == 10

    @pytest.mark.asyncio
    async def test_chat_with_tool_use(self, anthropic_config: ModelConfig) -> None:
        """Test chat response with tool use."""
        adapter = AnthropicAdapter(anthropic_config, api_key="test-key")

        # Mock response with tool use
        tool_block = MagicMock()
        tool_block.type = "tool_use"
        tool_block.id = "call_123"
        tool_block.name = "bash"
        tool_block.input = {"command": "ls"}

        mock_response = MagicMock()
        mock_response.content = [tool_block]
        mock_response.stop_reason = "tool_use"
        mock_response.usage = MagicMock(input_tokens=10, output_tokens=5)

        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        adapter._client = mock_client

        messages = [{"role": "user", "content": "List files"}]
        tools = [{"name": "bash", "description": "Run shell commands", "input_schema": {}}]
        response = await adapter.chat(messages, tools=tools)

        assert len(response.tool_calls) == 1
        assert response.tool_calls[0].name == "bash"
        assert response.tool_calls[0].id == "call_123"
        assert response.stop_reason == "tool_use"


class TestOpenAIAdapter:
    """Test OpenAIAdapter."""

    def test_init(self, openai_config: ModelConfig) -> None:
        """Test adapter initialization."""
        adapter = OpenAIAdapter(openai_config, api_key="test-key")
        assert adapter.config == openai_config
        assert adapter.api_key == "test-key"

    def test_convert_tools(self, openai_config: ModelConfig) -> None:
        """Test tool format conversion."""
        adapter = OpenAIAdapter(openai_config, api_key="test-key")

        # Anthropic format tools
        anthropic_tools = [
            {
                "name": "bash",
                "description": "Run shell commands",
                "input_schema": {
                    "type": "object",
                    "properties": {"command": {"type": "string"}},
                    "required": ["command"],
                },
            }
        ]

        openai_tools = adapter._convert_tools(anthropic_tools)

        assert len(openai_tools) == 1
        assert openai_tools[0]["type"] == "function"
        assert openai_tools[0]["function"]["name"] == "bash"
        assert openai_tools[0]["function"]["description"] == "Run shell commands"
        assert openai_tools[0]["function"]["parameters"] == anthropic_tools[0]["input_schema"]

    def test_convert_messages_simple(self, openai_config: ModelConfig) -> None:
        """Test simple message conversion."""
        adapter = OpenAIAdapter(openai_config, api_key="test-key")

        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]

        converted = adapter._convert_messages(messages)

        assert len(converted) == 2
        assert converted[0] == messages[0]
        assert converted[1] == messages[1]

    def test_convert_messages_with_tool_results(self, openai_config: ModelConfig) -> None:
        """Test converting messages with tool results."""
        adapter = OpenAIAdapter(openai_config, api_key="test-key")

        messages = [
            {"role": "user", "content": "List files"},
        ]

        tool_results = [
            ToolResult(tool_use_id="call_123", content="file1.txt\nfile2.txt"),
        ]

        converted = adapter._convert_messages(messages, tool_results)

        assert len(converted) == 2
        assert converted[1]["role"] == "tool"
        assert converted[1]["tool_call_id"] == "call_123"
        assert converted[1]["content"] == "file1.txt\nfile2.txt"

    @pytest.mark.asyncio
    async def test_chat_simple(self, openai_config: ModelConfig) -> None:
        """Test simple chat without tools."""
        adapter = OpenAIAdapter(openai_config, api_key="test-key")

        # Mock response
        mock_message = MagicMock()
        mock_message.content = "Hello!"
        mock_message.tool_calls = None

        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_choice.finish_reason = "stop"

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.usage = MagicMock(prompt_tokens=10, completion_tokens=5)

        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        adapter._client = mock_client

        messages = [{"role": "user", "content": "Hi"}]
        response = await adapter.chat(messages)

        assert response.text == "Hello!"
        assert response.stop_reason == "stop"

    @pytest.mark.asyncio
    async def test_chat_with_tool_use(self, openai_config: ModelConfig) -> None:
        """Test chat response with tool use."""
        adapter = OpenAIAdapter(openai_config, api_key="test-key")

        # Mock tool call
        mock_function = MagicMock()
        mock_function.name = "bash"
        mock_function.arguments = '{"command": "ls"}'

        mock_tool_call = MagicMock()
        mock_tool_call.id = "call_123"
        mock_tool_call.function = mock_function

        mock_message = MagicMock()
        mock_message.content = None
        mock_message.tool_calls = [mock_tool_call]

        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_choice.finish_reason = "tool_calls"

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.usage = MagicMock(prompt_tokens=10, completion_tokens=5)

        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        adapter._client = mock_client

        messages = [{"role": "user", "content": "List files"}]
        tools = [{"name": "bash", "description": "Run shell commands", "input_schema": {}}]
        response = await adapter.chat(messages, tools=tools)

        assert len(response.tool_calls) == 1
        assert response.tool_calls[0].name == "bash"
        assert response.tool_calls[0].arguments == {"command": "ls"}


class TestOllamaAdapter:
    """Test OllamaAdapter."""

    def test_init(self, ollama_config: ModelConfig) -> None:
        """Test adapter initialization."""
        adapter = OllamaAdapter(ollama_config, base_url="http://localhost:11434")
        assert adapter.config == ollama_config
        assert adapter.base_url == "http://localhost:11434"

    def test_init_strips_trailing_slash(self, ollama_config: ModelConfig) -> None:
        """Test that trailing slash is stripped from base URL."""
        adapter = OllamaAdapter(ollama_config, base_url="http://localhost:11434/")
        assert adapter.base_url == "http://localhost:11434"

    def test_convert_tools(self, ollama_config: ModelConfig) -> None:
        """Test tool format conversion (same as OpenAI)."""
        adapter = OllamaAdapter(ollama_config)

        anthropic_tools = [
            {
                "name": "bash",
                "description": "Run shell commands",
                "input_schema": {"type": "object"},
            }
        ]

        openai_tools = adapter._convert_tools(anthropic_tools)

        assert len(openai_tools) == 1
        assert openai_tools[0]["type"] == "function"
        assert openai_tools[0]["function"]["name"] == "bash"

    @pytest.mark.asyncio
    async def test_chat_simple(self, ollama_config: ModelConfig) -> None:
        """Test simple chat."""
        adapter = OllamaAdapter(ollama_config)

        # Mock response
        mock_response_data = {
            "choices": [
                {
                    "message": {"content": "Hello!", "tool_calls": None},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
        }

        mock_response = MagicMock()
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        adapter._client = mock_client

        messages = [{"role": "user", "content": "Hi"}]
        response = await adapter.chat(messages)

        assert response.text == "Hello!"
        assert response.stop_reason == "stop"

    @pytest.mark.asyncio
    async def test_list_models(self, ollama_config: ModelConfig) -> None:
        """Test listing available models."""
        adapter = OllamaAdapter(ollama_config)

        mock_response_data = {
            "models": [
                {"name": "llama3.3"},
                {"name": "qwen2.5"},
                {"name": "mistral"},
            ]
        }

        mock_response = MagicMock()
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        adapter._client = mock_client

        models = await adapter.list_models()

        assert len(models) == 3
        assert "llama3.3" in models
        assert "qwen2.5" in models
