"""Tests for model registry."""

from unittest.mock import MagicMock, patch

import pytest

from lurkbot.models.registry import BUILTIN_MODELS, ModelRegistry
from lurkbot.models.types import ApiType, ModelCapabilities, ModelConfig, ModelCost


class TestBuiltinModels:
    """Test built-in model definitions."""

    def test_anthropic_models_exist(self) -> None:
        """Test that Anthropic models are defined."""
        anthropic_models = [
            "anthropic/claude-sonnet-4-20250514",
            "anthropic/claude-opus-4-20250514",
            "anthropic/claude-haiku-3-5-20241022",
        ]
        for model_id in anthropic_models:
            assert model_id in BUILTIN_MODELS
            config = BUILTIN_MODELS[model_id]
            assert config.api_type == ApiType.ANTHROPIC
            assert config.provider == "anthropic"

    def test_openai_models_exist(self) -> None:
        """Test that OpenAI models are defined."""
        openai_models = [
            "openai/gpt-4o",
            "openai/gpt-4o-mini",
            "openai/gpt-4-turbo",
        ]
        for model_id in openai_models:
            assert model_id in BUILTIN_MODELS
            config = BUILTIN_MODELS[model_id]
            assert config.api_type == ApiType.OPENAI
            assert config.provider == "openai"

    def test_ollama_models_exist(self) -> None:
        """Test that Ollama models are defined."""
        ollama_models = [
            "ollama/llama3.3",
            "ollama/llama3.2",
            "ollama/qwen2.5",
            "ollama/mistral",
        ]
        for model_id in ollama_models:
            assert model_id in BUILTIN_MODELS
            config = BUILTIN_MODELS[model_id]
            assert config.api_type == ApiType.OLLAMA
            assert config.provider == "ollama"

    def test_model_configs_are_valid(self) -> None:
        """Test that all model configs have required fields."""
        for model_id, config in BUILTIN_MODELS.items():
            assert config.id == model_id
            assert config.name
            assert config.api_type in ApiType
            assert config.provider
            assert config.model_id
            assert config.context_window > 0
            assert config.max_tokens > 0


class TestModelRegistry:
    """Test ModelRegistry class."""

    @pytest.fixture
    def mock_settings(self) -> MagicMock:
        """Create mock settings."""
        settings = MagicMock()
        settings.anthropic_api_key = "test-anthropic-key"
        settings.openai_api_key = "test-openai-key"
        settings.models = MagicMock()
        settings.models.custom_models = {}
        settings.models.ollama_base_url = "http://localhost:11434"
        return settings

    def test_init(self, mock_settings: MagicMock) -> None:
        """Test registry initialization."""
        registry = ModelRegistry(mock_settings)
        assert len(registry._models) >= len(BUILTIN_MODELS)

    def test_get_config(self, mock_settings: MagicMock) -> None:
        """Test getting model config."""
        registry = ModelRegistry(mock_settings)
        config = registry.get_config("anthropic/claude-sonnet-4-20250514")
        assert config is not None
        assert config.id == "anthropic/claude-sonnet-4-20250514"

    def test_get_config_not_found(self, mock_settings: MagicMock) -> None:
        """Test getting non-existent model config."""
        registry = ModelRegistry(mock_settings)
        config = registry.get_config("nonexistent/model")
        assert config is None

    def test_get_adapter_unknown_model(self, mock_settings: MagicMock) -> None:
        """Test getting adapter for unknown model raises error."""
        registry = ModelRegistry(mock_settings)
        with pytest.raises(ValueError, match="Unknown model"):
            registry.get_adapter("nonexistent/model")

    def test_get_adapter_missing_api_key(self, mock_settings: MagicMock) -> None:
        """Test getting adapter without API key raises error."""
        mock_settings.anthropic_api_key = None
        registry = ModelRegistry(mock_settings)
        with pytest.raises(ValueError, match="API_KEY not configured"):
            registry.get_adapter("anthropic/claude-sonnet-4-20250514")

    @patch("lurkbot.models.adapters.anthropic.AnthropicAdapter")
    def test_get_adapter_anthropic(
        self, mock_adapter_class: MagicMock, mock_settings: MagicMock
    ) -> None:
        """Test getting Anthropic adapter."""
        registry = ModelRegistry(mock_settings)
        adapter = registry.get_adapter("anthropic/claude-sonnet-4-20250514")
        mock_adapter_class.assert_called_once()
        assert "anthropic/claude-sonnet-4-20250514" in registry._adapters

    @patch("lurkbot.models.adapters.openai.OpenAIAdapter")
    def test_get_adapter_openai(
        self, mock_adapter_class: MagicMock, mock_settings: MagicMock
    ) -> None:
        """Test getting OpenAI adapter."""
        registry = ModelRegistry(mock_settings)
        adapter = registry.get_adapter("openai/gpt-4o")
        mock_adapter_class.assert_called_once()
        assert "openai/gpt-4o" in registry._adapters

    @patch("lurkbot.models.adapters.ollama.OllamaAdapter")
    def test_get_adapter_ollama(
        self, mock_adapter_class: MagicMock, mock_settings: MagicMock
    ) -> None:
        """Test getting Ollama adapter."""
        registry = ModelRegistry(mock_settings)
        adapter = registry.get_adapter("ollama/llama3.3")
        mock_adapter_class.assert_called_once()
        assert "ollama/llama3.3" in registry._adapters

    @patch("lurkbot.models.adapters.anthropic.AnthropicAdapter")
    def test_adapter_caching(
        self, mock_adapter_class: MagicMock, mock_settings: MagicMock
    ) -> None:
        """Test that adapters are cached."""
        registry = ModelRegistry(mock_settings)
        adapter1 = registry.get_adapter("anthropic/claude-sonnet-4-20250514")
        adapter2 = registry.get_adapter("anthropic/claude-sonnet-4-20250514")
        mock_adapter_class.assert_called_once()  # Only called once due to caching

    def test_list_models(self, mock_settings: MagicMock) -> None:
        """Test listing all models."""
        registry = ModelRegistry(mock_settings)
        models = registry.list_models()
        assert len(models) >= len(BUILTIN_MODELS)
        assert all(isinstance(m, ModelConfig) for m in models)

    def test_list_models_filter_by_provider(self, mock_settings: MagicMock) -> None:
        """Test listing models filtered by provider."""
        registry = ModelRegistry(mock_settings)
        anthropic_models = registry.list_models(provider="anthropic")
        assert all(m.provider == "anthropic" for m in anthropic_models)

    def test_list_models_filter_by_api_type(self, mock_settings: MagicMock) -> None:
        """Test listing models filtered by API type."""
        registry = ModelRegistry(mock_settings)
        openai_models = registry.list_models(api_type=ApiType.OPENAI)
        assert all(m.api_type == ApiType.OPENAI for m in openai_models)

    def test_register_model(self, mock_settings: MagicMock) -> None:
        """Test registering a new model."""
        registry = ModelRegistry(mock_settings)
        new_config = ModelConfig(
            id="custom/test-model",
            name="Custom Test Model",
            api_type=ApiType.OPENAI,
            provider="openai",
            model_id="custom-test",
        )
        registry.register_model(new_config)
        assert registry.get_config("custom/test-model") == new_config

    def test_unregister_model(self, mock_settings: MagicMock) -> None:
        """Test unregistering a model."""
        registry = ModelRegistry(mock_settings)
        new_config = ModelConfig(
            id="custom/temp-model",
            name="Temp Model",
            api_type=ApiType.OPENAI,
            provider="openai",
            model_id="temp",
        )
        registry.register_model(new_config)
        assert registry.get_config("custom/temp-model") is not None

        result = registry.unregister_model("custom/temp-model")
        assert result is True
        assert registry.get_config("custom/temp-model") is None

    def test_unregister_nonexistent_model(self, mock_settings: MagicMock) -> None:
        """Test unregistering a non-existent model."""
        registry = ModelRegistry(mock_settings)
        result = registry.unregister_model("nonexistent/model")
        assert result is False

    @patch("lurkbot.models.adapters.anthropic.AnthropicAdapter")
    def test_clear_adapters(
        self, mock_adapter_class: MagicMock, mock_settings: MagicMock
    ) -> None:
        """Test clearing cached adapters."""
        registry = ModelRegistry(mock_settings)
        registry.get_adapter("anthropic/claude-sonnet-4-20250514")
        assert len(registry._adapters) == 1

        registry.clear_adapters()
        assert len(registry._adapters) == 0

    def test_load_custom_models(self, mock_settings: MagicMock) -> None:
        """Test loading custom models from settings."""
        mock_settings.models.custom_models = {
            "custom/my-model": {
                "name": "My Custom Model",
                "api_type": "openai",
                "provider": "openai",
                "model_id": "my-model-v1",
                "context_window": 32000,
            }
        }
        registry = ModelRegistry(mock_settings)
        config = registry.get_config("custom/my-model")
        assert config is not None
        assert config.name == "My Custom Model"
        assert config.context_window == 32000
