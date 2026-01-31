"""Tests for LLM model configuration."""

import pytest

from lurkbot.config.models import (
    DEEPSEEK_PROVIDER,
    GLM_PROVIDER,
    KIMI_PROVIDER,
    QWEN_PROVIDER,
    get_client_config,
    get_model,
    get_provider,
    list_models,
    list_providers,
)


class TestProviderRegistry:
    """Test provider registry functionality."""

    def test_get_provider_openai(self):
        """Test getting OpenAI provider."""
        provider = get_provider("openai")
        assert provider is not None
        assert provider.name == "openai"
        assert provider.display_name == "OpenAI"

    def test_get_provider_deepseek(self):
        """Test getting DeepSeek provider."""
        provider = get_provider("deepseek")
        assert provider is not None
        assert provider.name == "deepseek"
        assert provider.display_name == "DeepSeek (深度求索)"
        assert provider.base_url == "https://api.deepseek.com/v1"

    def test_get_provider_qwen(self):
        """Test getting Qwen provider."""
        provider = get_provider("qwen")
        assert provider is not None
        assert provider.name == "qwen"
        assert provider.base_url == "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"

    def test_get_provider_case_insensitive(self):
        """Test provider lookup is case-insensitive."""
        assert get_provider("DeepSeek") == get_provider("deepseek")
        assert get_provider("QWEN") == get_provider("qwen")

    def test_get_provider_unknown(self):
        """Test getting unknown provider returns None."""
        assert get_provider("unknown_provider") is None


class TestModelRegistry:
    """Test model registry functionality."""

    def test_get_model_deepseek_chat(self):
        """Test getting DeepSeek Chat model."""
        model = get_model("deepseek", "deepseek-chat")
        assert model is not None
        assert model.provider == "deepseek"
        assert model.model_id == "deepseek-chat"
        assert model.display_name == "DeepSeek V3"
        assert model.base_url == "https://api.deepseek.com/v1"
        assert model.api_key_env == "DEEPSEEK_API_KEY"

    def test_get_model_qwen_plus(self):
        """Test getting Qwen Plus model."""
        model = get_model("qwen", "qwen-plus")
        assert model is not None
        assert model.provider == "qwen"
        assert model.model_id == "qwen-plus"
        assert model.supports_function_calling is True

    def test_get_model_kimi_128k(self):
        """Test getting Kimi 128K model."""
        model = get_model("kimi", "moonshot-v1-128k")
        assert model is not None
        assert model.context_window == 128000
        assert model.api_key_env == "MOONSHOT_API_KEY"

    def test_get_model_glm_4_plus(self):
        """Test getting GLM-4 Plus model."""
        model = get_model("glm", "glm-4-plus")
        assert model is not None
        assert model.supports_vision is True

    def test_get_model_case_insensitive(self):
        """Test model lookup is case-insensitive."""
        assert get_model("DeepSeek", "deepseek-chat") == get_model("deepseek", "deepseek-chat")

    def test_get_model_unknown(self):
        """Test getting unknown model returns None."""
        assert get_model("deepseek", "unknown-model") is None


class TestListProviders:
    """Test provider listing functionality."""

    def test_list_all_providers(self):
        """Test listing all providers."""
        providers = list_providers()
        assert len(providers) >= 7  # At least 7 providers
        provider_names = [p.name for p in providers]
        assert "openai" in provider_names
        assert "anthropic" in provider_names
        assert "deepseek" in provider_names
        assert "qwen" in provider_names

    def test_list_domestic_providers_only(self):
        """Test listing domestic providers only."""
        providers = list_providers(domestic_only=True)
        assert len(providers) == 4
        provider_names = [p.name for p in providers]
        assert "deepseek" in provider_names
        assert "qwen" in provider_names
        assert "kimi" in provider_names
        assert "glm" in provider_names
        # International providers should not be included
        assert "openai" not in provider_names
        assert "anthropic" not in provider_names


class TestListModels:
    """Test model listing functionality."""

    def test_list_all_models(self):
        """Test listing all models."""
        models = list_models()
        assert len(models) > 0
        model_ids = [f"{m.provider}:{m.model_id}" for m in models]
        assert "deepseek:deepseek-chat" in model_ids
        assert "qwen:qwen-plus" in model_ids

    def test_list_models_by_provider(self):
        """Test listing models for specific provider."""
        deepseek_models = list_models(provider="deepseek")
        assert len(deepseek_models) == 3
        assert all(m.provider == "deepseek" for m in deepseek_models)

    def test_list_models_with_vision(self):
        """Test listing models with vision support."""
        vision_models = list_models(supports_vision=True)
        assert len(vision_models) > 0
        assert all(m.supports_vision for m in vision_models)
        model_ids = [m.model_id for m in vision_models]
        assert "qwen3-max-2026-01-23" in model_ids
        assert "glm-4-plus" in model_ids

    def test_list_models_without_vision(self):
        """Test listing models without vision support."""
        no_vision_models = list_models(supports_vision=False)
        assert len(no_vision_models) > 0
        assert all(not m.supports_vision for m in no_vision_models)


class TestClientConfig:
    """Test client configuration generation."""

    def test_get_client_config_deepseek(self):
        """Test getting DeepSeek client config."""
        config = get_client_config("deepseek", "deepseek-chat")
        assert config["base_url"] == "https://api.deepseek.com/v1"
        assert config["api_key_env"] == "DEEPSEEK_API_KEY"
        assert config["model"] == "deepseek-chat"

    def test_get_client_config_qwen(self):
        """Test getting Qwen client config."""
        config = get_client_config("qwen", "qwen-plus")
        assert config["base_url"] == "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
        assert config["api_key_env"] == "DASHSCOPE_API_KEY"
        assert config["model"] == "qwen-plus"

    def test_get_client_config_kimi(self):
        """Test getting Kimi client config."""
        config = get_client_config("kimi", "moonshot-v1-32k")
        assert config["base_url"] == "https://api.moonshot.cn/v1"
        assert config["api_key_env"] == "MOONSHOT_API_KEY"

    def test_get_client_config_glm(self):
        """Test getting ChatGLM client config."""
        config = get_client_config("glm", "glm-4")
        assert config["base_url"] == "https://open.bigmodel.cn/api/paas/v4"
        assert config["api_key_env"] == "ZHIPUAI_API_KEY"

    def test_get_client_config_unknown_model(self):
        """Test getting config for unknown model raises error."""
        with pytest.raises(ValueError, match="Unknown model"):
            get_client_config("deepseek", "unknown-model")

    def test_get_client_config_unknown_provider(self):
        """Test getting config for unknown provider raises error."""
        with pytest.raises(ValueError, match="Unknown model"):
            get_client_config("unknown", "model")


class TestModelCapabilities:
    """Test model capability flags."""

    def test_deepseek_capabilities(self):
        """Test DeepSeek model capabilities."""
        model = get_model("deepseek", "deepseek-chat")
        assert model.supports_function_calling is True
        assert model.supports_vision is False  # DeepSeek V3 doesn't support vision

    def test_qwen_max_capabilities(self):
        """Test Qwen3 Max capabilities."""
        model = get_model("qwen", "qwen3-max-2026-01-23")
        assert model.supports_function_calling is True
        assert model.supports_vision is True

    def test_glm_plus_capabilities(self):
        """Test GLM-4 Plus capabilities."""
        model = get_model("glm", "glm-4-plus")
        assert model.supports_function_calling is True
        assert model.supports_vision is True

    def test_kimi_capabilities(self):
        """Test Kimi capabilities."""
        model = get_model("kimi", "moonshot-v1-128k")
        assert model.supports_function_calling is True
        assert model.supports_vision is False


class TestContextWindows:
    """Test context window sizes."""

    def test_deepseek_context(self):
        """Test DeepSeek context window."""
        model = get_model("deepseek", "deepseek-chat")
        assert model.context_window == 64000

    def test_qwen_context(self):
        """Test Qwen context windows."""
        qwen_plus = get_model("qwen", "qwen-plus")
        assert qwen_plus.context_window == 128000

        qwen_turbo = get_model("qwen", "qwen-turbo")
        assert qwen_turbo.context_window == 8000

    def test_kimi_context_windows(self):
        """Test Kimi various context windows."""
        kimi_8k = get_model("kimi", "moonshot-v1-8k")
        assert kimi_8k.context_window == 8000

        kimi_32k = get_model("kimi", "moonshot-v1-32k")
        assert kimi_32k.context_window == 32000

        kimi_128k = get_model("kimi", "moonshot-v1-128k")
        assert kimi_128k.context_window == 128000
