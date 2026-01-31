"""LLM model configuration and registry.

This module provides configuration for various LLM providers including
domestic Chinese providers (DeepSeek, Qwen, Kimi, GLM) and international
providers (OpenAI, Anthropic, Google).

All providers use OpenAI-compatible API interfaces for consistency.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ModelConfig(BaseModel):
    """Configuration for a single LLM model."""

    provider: str = Field(description="Provider name (e.g., openai, deepseek)")
    model_id: str = Field(description="Model identifier")
    display_name: str = Field(description="Human-readable model name")
    base_url: str | None = Field(
        default=None, description="Custom API endpoint (for OpenAI-compatible providers)"
    )
    api_key_env: str = Field(description="Environment variable name for API key")
    supports_vision: bool = Field(default=False, description="Whether model supports image inputs")
    supports_function_calling: bool = Field(
        default=True, description="Whether model supports function calling"
    )
    context_window: int = Field(default=4096, description="Maximum context window size")
    max_output_tokens: int | None = Field(
        default=None, description="Maximum output tokens (None = provider default)"
    )
    description: str = Field(default="", description="Model description")


class ProviderConfig(BaseModel):
    """Configuration for an LLM provider."""

    name: str = Field(description="Provider name")
    display_name: str = Field(description="Human-readable provider name")
    base_url: str | None = Field(default=None, description="Default API endpoint")
    api_key_env: str = Field(description="Default environment variable for API key")
    models: list[ModelConfig] = Field(default_factory=list, description="Available models")
    description: str = Field(default="", description="Provider description")


# ============================================================================
# International Providers
# ============================================================================

OPENAI_PROVIDER = ProviderConfig(
    name="openai",
    display_name="OpenAI",
    api_key_env="OPENAI_API_KEY",
    description="OpenAI GPT models",
    models=[
        ModelConfig(
            provider="openai",
            model_id="gpt-4o",
            display_name="GPT-4o",
            api_key_env="OPENAI_API_KEY",
            supports_vision=True,
            context_window=128000,
            description="Most capable GPT-4 model with vision support",
        ),
        ModelConfig(
            provider="openai",
            model_id="gpt-4o-mini",
            display_name="GPT-4o Mini",
            api_key_env="OPENAI_API_KEY",
            supports_vision=True,
            context_window=128000,
            description="Smaller, faster, cheaper GPT-4 variant",
        ),
        ModelConfig(
            provider="openai",
            model_id="gpt-4-turbo",
            display_name="GPT-4 Turbo",
            api_key_env="OPENAI_API_KEY",
            supports_vision=True,
            context_window=128000,
            description="Previous generation GPT-4 Turbo",
        ),
    ],
)

ANTHROPIC_PROVIDER = ProviderConfig(
    name="anthropic",
    display_name="Anthropic",
    api_key_env="ANTHROPIC_API_KEY",
    description="Anthropic Claude models",
    models=[
        ModelConfig(
            provider="anthropic",
            model_id="claude-sonnet-4-20250514",
            display_name="Claude Sonnet 4",
            api_key_env="ANTHROPIC_API_KEY",
            supports_vision=True,
            context_window=200000,
            description="Latest Claude Sonnet model with vision support",
        ),
        ModelConfig(
            provider="anthropic",
            model_id="claude-opus-4-5-20251101",
            display_name="Claude Opus 4.5",
            api_key_env="ANTHROPIC_API_KEY",
            supports_vision=True,
            context_window=200000,
            description="Most capable Claude model",
        ),
        ModelConfig(
            provider="anthropic",
            model_id="claude-3-5-sonnet-20241022",
            display_name="Claude 3.5 Sonnet",
            api_key_env="ANTHROPIC_API_KEY",
            supports_vision=True,
            context_window=200000,
            description="Previous generation Claude Sonnet",
        ),
        ModelConfig(
            provider="anthropic",
            model_id="claude-3-5-haiku-20241022",
            display_name="Claude 3.5 Haiku",
            api_key_env="ANTHROPIC_API_KEY",
            supports_vision=True,
            context_window=200000,
            description="Fast and efficient Claude model",
        ),
    ],
)

GOOGLE_PROVIDER = ProviderConfig(
    name="google",
    display_name="Google",
    api_key_env="GOOGLE_API_KEY",
    description="Google Gemini models",
    models=[
        ModelConfig(
            provider="google",
            model_id="gemini-2.0-flash",
            display_name="Gemini 2.0 Flash",
            api_key_env="GOOGLE_API_KEY",
            supports_vision=True,
            context_window=1000000,
            description="Latest Gemini model with multimodal support",
        ),
        ModelConfig(
            provider="google",
            model_id="gemini-1.5-pro",
            display_name="Gemini 1.5 Pro",
            api_key_env="GOOGLE_API_KEY",
            supports_vision=True,
            context_window=2000000,
            description="Most capable Gemini model with massive context window",
        ),
        ModelConfig(
            provider="google",
            model_id="gemini-1.5-flash",
            display_name="Gemini 1.5 Flash",
            api_key_env="GOOGLE_API_KEY",
            supports_vision=True,
            context_window=1000000,
            description="Fast and efficient Gemini model",
        ),
    ],
)

# ============================================================================
# Domestic Chinese Providers (国产大模型)
# ============================================================================

DEEPSEEK_PROVIDER = ProviderConfig(
    name="deepseek",
    display_name="DeepSeek (深度求索)",
    base_url="https://api.deepseek.com/v1",
    api_key_env="DEEPSEEK_API_KEY",
    description="DeepSeek - Chinese AI company with strong coding and reasoning capabilities",
    models=[
        ModelConfig(
            provider="deepseek",
            model_id="deepseek-chat",
            display_name="DeepSeek V3",
            base_url="https://api.deepseek.com/v1",
            api_key_env="DEEPSEEK_API_KEY",
            supports_vision=False,
            supports_function_calling=True,
            context_window=64000,
            description="General-purpose DeepSeek model (latest V3)",
        ),
        ModelConfig(
            provider="deepseek",
            model_id="deepseek-reasoner",
            display_name="DeepSeek R1",
            base_url="https://api.deepseek.com/v1",
            api_key_env="DEEPSEEK_API_KEY",
            supports_vision=False,
            supports_function_calling=True,
            context_window=64000,
            description="Reasoning-focused model with step-by-step thinking",
        ),
        ModelConfig(
            provider="deepseek",
            model_id="deepseek-coder",
            display_name="DeepSeek Coder",
            base_url="https://api.deepseek.com/v1",
            api_key_env="DEEPSEEK_API_KEY",
            supports_vision=False,
            supports_function_calling=True,
            context_window=64000,
            description="Specialized model for programming tasks",
        ),
    ],
)

QWEN_PROVIDER = ProviderConfig(
    name="qwen",
    display_name="Qwen (通义千问)",
    base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
    api_key_env="DASHSCOPE_API_KEY",
    description="Qwen - Alibaba Cloud's multilingual large language model",
    models=[
        ModelConfig(
            provider="qwen",
            model_id="qwen3-max-2026-01-23",
            display_name="Qwen3 Max",
            base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
            api_key_env="DASHSCOPE_API_KEY",
            supports_vision=True,
            supports_function_calling=True,
            context_window=128000,
            description="Latest Qwen3 Max model with multimodal capabilities",
        ),
        ModelConfig(
            provider="qwen",
            model_id="qwen-plus",
            display_name="Qwen Plus",
            base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
            api_key_env="DASHSCOPE_API_KEY",
            supports_vision=False,
            supports_function_calling=True,
            context_window=128000,
            description="Enhanced Qwen model for general tasks",
        ),
        ModelConfig(
            provider="qwen",
            model_id="qwen-turbo",
            display_name="Qwen Turbo",
            base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
            api_key_env="DASHSCOPE_API_KEY",
            supports_vision=False,
            supports_function_calling=True,
            context_window=8000,
            description="Fast and efficient Qwen model",
        ),
    ],
)

KIMI_PROVIDER = ProviderConfig(
    name="kimi",
    display_name="Kimi (月之暗面)",
    base_url="https://api.moonshot.cn/v1",
    api_key_env="MOONSHOT_API_KEY",
    description="Kimi - Moonshot AI's long-context language model",
    models=[
        ModelConfig(
            provider="kimi",
            model_id="moonshot-v1-8k",
            display_name="Kimi 8K",
            base_url="https://api.moonshot.cn/v1",
            api_key_env="MOONSHOT_API_KEY",
            supports_vision=False,
            supports_function_calling=True,
            context_window=8000,
            description="Kimi model with 8K context window",
        ),
        ModelConfig(
            provider="kimi",
            model_id="moonshot-v1-32k",
            display_name="Kimi 32K",
            base_url="https://api.moonshot.cn/v1",
            api_key_env="MOONSHOT_API_KEY",
            supports_vision=False,
            supports_function_calling=True,
            context_window=32000,
            description="Kimi model with 32K context window",
        ),
        ModelConfig(
            provider="kimi",
            model_id="moonshot-v1-128k",
            display_name="Kimi 128K",
            base_url="https://api.moonshot.cn/v1",
            api_key_env="MOONSHOT_API_KEY",
            supports_vision=False,
            supports_function_calling=True,
            context_window=128000,
            description="Kimi model with massive 128K context window",
        ),
    ],
)

GLM_PROVIDER = ProviderConfig(
    name="glm",
    display_name="ChatGLM (智谱)",
    base_url="https://open.bigmodel.cn/api/paas/v4",
    api_key_env="ZHIPUAI_API_KEY",
    description="ChatGLM - Zhipu AI's bilingual conversational language model",
    models=[
        ModelConfig(
            provider="glm",
            model_id="glm-4-plus",
            display_name="GLM-4 Plus",
            base_url="https://open.bigmodel.cn/api/paas/v4",
            api_key_env="ZHIPUAI_API_KEY",
            supports_vision=True,
            supports_function_calling=True,
            context_window=128000,
            description="Enhanced GLM-4 model with vision support",
        ),
        ModelConfig(
            provider="glm",
            model_id="glm-4",
            display_name="GLM-4",
            base_url="https://open.bigmodel.cn/api/paas/v4",
            api_key_env="ZHIPUAI_API_KEY",
            supports_vision=False,
            supports_function_calling=True,
            context_window=128000,
            description="Standard GLM-4 model",
        ),
        ModelConfig(
            provider="glm",
            model_id="glm-3-turbo",
            display_name="GLM-3 Turbo",
            base_url="https://open.bigmodel.cn/api/paas/v4",
            api_key_env="ZHIPUAI_API_KEY",
            supports_vision=False,
            supports_function_calling=True,
            context_window=128000,
            description="Fast and efficient GLM-3 model",
        ),
    ],
)

# ============================================================================
# Provider Registry
# ============================================================================

ALL_PROVIDERS = [
    # International providers
    OPENAI_PROVIDER,
    ANTHROPIC_PROVIDER,
    GOOGLE_PROVIDER,
    # Domestic Chinese providers
    DEEPSEEK_PROVIDER,
    QWEN_PROVIDER,
    KIMI_PROVIDER,
    GLM_PROVIDER,
]

# Provider lookup by name
PROVIDER_REGISTRY: dict[str, ProviderConfig] = {p.name: p for p in ALL_PROVIDERS}

# Model lookup by provider:model_id
MODEL_REGISTRY: dict[str, ModelConfig] = {}
for provider in ALL_PROVIDERS:
    for model in provider.models:
        key = f"{provider.name}:{model.model_id}"
        MODEL_REGISTRY[key] = model


def get_provider(provider_name: str) -> ProviderConfig | None:
    """Get provider configuration by name.

    Args:
        provider_name: Provider name (e.g., 'openai', 'deepseek')

    Returns:
        ProviderConfig if found, None otherwise
    """
    return PROVIDER_REGISTRY.get(provider_name.lower())


def get_model(provider: str, model_id: str) -> ModelConfig | None:
    """Get model configuration.

    Args:
        provider: Provider name
        model_id: Model identifier

    Returns:
        ModelConfig if found, None otherwise
    """
    key = f"{provider.lower()}:{model_id}"
    return MODEL_REGISTRY.get(key)


def list_providers(domestic_only: bool = False) -> list[ProviderConfig]:
    """List available providers.

    Args:
        domestic_only: If True, only return Chinese domestic providers

    Returns:
        List of ProviderConfig
    """
    if domestic_only:
        return [DEEPSEEK_PROVIDER, QWEN_PROVIDER, KIMI_PROVIDER, GLM_PROVIDER]
    return ALL_PROVIDERS


def list_models(
    provider: str | None = None, supports_vision: bool | None = None
) -> list[ModelConfig]:
    """List available models with optional filtering.

    Args:
        provider: Filter by provider name
        supports_vision: Filter by vision support

    Returns:
        List of ModelConfig
    """
    models = list(MODEL_REGISTRY.values())

    if provider:
        models = [m for m in models if m.provider.lower() == provider.lower()]

    if supports_vision is not None:
        models = [m for m in models if m.supports_vision == supports_vision]

    return models


def get_client_config(provider: str, model_id: str) -> dict[str, Any]:
    """Get OpenAI client configuration for a provider/model.

    This returns the configuration needed to create an OpenAI-compatible client
    for the specified provider and model.

    Args:
        provider: Provider name
        model_id: Model identifier

    Returns:
        Dictionary with 'base_url', 'api_key_env', and 'model' keys

    Example:
        >>> config = get_client_config('deepseek', 'deepseek-chat')
        >>> # {'base_url': 'https://api.deepseek.com/v1',
        >>> #  'api_key_env': 'DEEPSEEK_API_KEY',
        >>> #  'model': 'deepseek-chat'}
    """
    model = get_model(provider, model_id)
    if not model:
        raise ValueError(f"Unknown model: {provider}:{model_id}")

    provider_config = get_provider(provider)
    if not provider_config:
        raise ValueError(f"Unknown provider: {provider}")

    return {
        "base_url": model.base_url or provider_config.base_url,
        "api_key_env": model.api_key_env,
        "model": model.model_id,
    }
