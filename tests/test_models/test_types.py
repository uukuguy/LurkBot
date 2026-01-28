"""Tests for model types."""


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


class TestApiType:
    """Test ApiType enum."""

    def test_values(self) -> None:
        """Test all expected values exist."""
        assert ApiType.ANTHROPIC.value == "anthropic"
        assert ApiType.OPENAI.value == "openai"
        assert ApiType.OLLAMA.value == "ollama"
        assert ApiType.LITELLM.value == "litellm"

    def test_string_behavior(self) -> None:
        """Test that ApiType behaves as string."""
        assert ApiType.ANTHROPIC == "anthropic"
        assert ApiType.OPENAI.value == "openai"


class TestModelCost:
    """Test ModelCost model."""

    def test_defaults(self) -> None:
        """Test default values."""
        cost = ModelCost()
        assert cost.input == 0.0
        assert cost.output == 0.0
        assert cost.cache_read == 0.0
        assert cost.cache_write == 0.0

    def test_custom_values(self) -> None:
        """Test custom values."""
        cost = ModelCost(input=3.0, output=15.0, cache_read=0.3, cache_write=3.75)
        assert cost.input == 3.0
        assert cost.output == 15.0
        assert cost.cache_read == 0.3
        assert cost.cache_write == 3.75


class TestModelCapabilities:
    """Test ModelCapabilities model."""

    def test_defaults(self) -> None:
        """Test default values."""
        caps = ModelCapabilities()
        assert caps.supports_tools is True
        assert caps.supports_vision is False
        assert caps.supports_streaming is True
        assert caps.supports_thinking is False
        assert caps.max_output_tokens is None

    def test_custom_values(self) -> None:
        """Test custom values."""
        caps = ModelCapabilities(
            supports_tools=False,
            supports_vision=True,
            supports_thinking=True,
            max_output_tokens=8192,
        )
        assert caps.supports_tools is False
        assert caps.supports_vision is True
        assert caps.supports_thinking is True
        assert caps.max_output_tokens == 8192


class TestModelConfig:
    """Test ModelConfig model."""

    def test_minimal_config(self) -> None:
        """Test creating config with minimal required fields."""
        config = ModelConfig(
            id="test/model",
            name="Test Model",
            api_type=ApiType.ANTHROPIC,
            provider="anthropic",
            model_id="test-model-v1",
        )
        assert config.id == "test/model"
        assert config.name == "Test Model"
        assert config.api_type == ApiType.ANTHROPIC
        assert config.provider == "anthropic"
        assert config.model_id == "test-model-v1"
        assert config.context_window == 128000  # default
        assert config.max_tokens == 4096  # default

    def test_full_config(self) -> None:
        """Test creating config with all fields."""
        config = ModelConfig(
            id="anthropic/claude-sonnet-4",
            name="Claude Sonnet 4",
            api_type=ApiType.ANTHROPIC,
            provider="anthropic",
            model_id="claude-sonnet-4-20250514",
            context_window=200000,
            max_tokens=8192,
            cost=ModelCost(input=3.0, output=15.0),
            capabilities=ModelCapabilities(supports_vision=True),
        )
        assert config.context_window == 200000
        assert config.max_tokens == 8192
        assert config.cost.input == 3.0
        assert config.capabilities.supports_vision is True


class TestToolCall:
    """Test ToolCall dataclass."""

    def test_creation(self) -> None:
        """Test creating a ToolCall."""
        tc = ToolCall(
            id="call_123",
            name="bash",
            arguments={"command": "ls -la"},
        )
        assert tc.id == "call_123"
        assert tc.name == "bash"
        assert tc.arguments == {"command": "ls -la"}


class TestModelResponse:
    """Test ModelResponse dataclass."""

    def test_defaults(self) -> None:
        """Test default values."""
        response = ModelResponse()
        assert response.text is None
        assert response.tool_calls == []
        assert response.stop_reason is None
        assert response.usage == {}
        assert response.raw is None

    def test_with_text(self) -> None:
        """Test response with text."""
        response = ModelResponse(
            text="Hello, world!",
            stop_reason="end_turn",
            usage={"input_tokens": 10, "output_tokens": 5},
        )
        assert response.text == "Hello, world!"
        assert response.stop_reason == "end_turn"
        assert response.usage["input_tokens"] == 10

    def test_with_tool_calls(self) -> None:
        """Test response with tool calls."""
        tool_calls = [
            ToolCall(id="1", name="bash", arguments={"command": "ls"}),
            ToolCall(id="2", name="read_file", arguments={"path": "/tmp/test"}),
        ]
        response = ModelResponse(
            tool_calls=tool_calls,
            stop_reason="tool_use",
        )
        assert len(response.tool_calls) == 2
        assert response.tool_calls[0].name == "bash"


class TestStreamChunk:
    """Test StreamChunk dataclass."""

    def test_text_chunk(self) -> None:
        """Test text chunk."""
        chunk = StreamChunk(text="Hello")
        assert chunk.text == "Hello"
        assert chunk.tool_use_id is None

    def test_tool_chunk(self) -> None:
        """Test tool use chunk."""
        chunk = StreamChunk(
            tool_use_id="call_123",
            tool_name="bash",
            tool_input_delta='{"command": "ls"}',
        )
        assert chunk.tool_use_id == "call_123"
        assert chunk.tool_name == "bash"
        assert chunk.tool_input_delta == '{"command": "ls"}'

    def test_finish_chunk(self) -> None:
        """Test finish chunk."""
        chunk = StreamChunk(finish_reason="end_turn")
        assert chunk.finish_reason == "end_turn"


class TestToolResult:
    """Test ToolResult dataclass."""

    def test_success_result(self) -> None:
        """Test successful tool result."""
        result = ToolResult(
            tool_use_id="call_123",
            content="file.txt\ndir/",
        )
        assert result.tool_use_id == "call_123"
        assert result.content == "file.txt\ndir/"
        assert result.is_error is False

    def test_error_result(self) -> None:
        """Test error tool result."""
        result = ToolResult(
            tool_use_id="call_123",
            content="Error: command not found",
            is_error=True,
        )
        assert result.is_error is True
