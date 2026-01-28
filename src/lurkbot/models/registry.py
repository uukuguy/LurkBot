"""Model registry with built-in model definitions."""

from typing import TYPE_CHECKING

from loguru import logger

from lurkbot.models.base import ModelAdapter
from lurkbot.models.types import (
    ApiType,
    ModelCapabilities,
    ModelConfig,
    ModelCost,
)

if TYPE_CHECKING:
    from lurkbot.config.settings import Settings


# Built-in model definitions
BUILTIN_MODELS: dict[str, ModelConfig] = {
    # Anthropic Claude models
    "anthropic/claude-sonnet-4-20250514": ModelConfig(
        id="anthropic/claude-sonnet-4-20250514",
        name="Claude Sonnet 4",
        api_type=ApiType.ANTHROPIC,
        provider="anthropic",
        model_id="claude-sonnet-4-20250514",
        context_window=200000,
        max_tokens=8192,
        cost=ModelCost(input=3.0, output=15.0, cache_read=0.3, cache_write=3.75),
        capabilities=ModelCapabilities(
            supports_tools=True,
            supports_vision=True,
            supports_streaming=True,
            supports_thinking=False,
            max_output_tokens=64000,
        ),
    ),
    "anthropic/claude-opus-4-20250514": ModelConfig(
        id="anthropic/claude-opus-4-20250514",
        name="Claude Opus 4",
        api_type=ApiType.ANTHROPIC,
        provider="anthropic",
        model_id="claude-opus-4-20250514",
        context_window=200000,
        max_tokens=8192,
        cost=ModelCost(input=15.0, output=75.0, cache_read=1.5, cache_write=18.75),
        capabilities=ModelCapabilities(
            supports_tools=True,
            supports_vision=True,
            supports_streaming=True,
            supports_thinking=True,
            max_output_tokens=64000,
        ),
    ),
    "anthropic/claude-haiku-3-5-20241022": ModelConfig(
        id="anthropic/claude-haiku-3-5-20241022",
        name="Claude Haiku 3.5",
        api_type=ApiType.ANTHROPIC,
        provider="anthropic",
        model_id="claude-3-5-haiku-20241022",
        context_window=200000,
        max_tokens=4096,
        cost=ModelCost(input=0.8, output=4.0, cache_read=0.08, cache_write=1.0),
        capabilities=ModelCapabilities(
            supports_tools=True,
            supports_vision=True,
            supports_streaming=True,
            supports_thinking=False,
            max_output_tokens=8192,
        ),
    ),
    # OpenAI GPT models
    "openai/gpt-4o": ModelConfig(
        id="openai/gpt-4o",
        name="GPT-4o",
        api_type=ApiType.OPENAI,
        provider="openai",
        model_id="gpt-4o",
        context_window=128000,
        max_tokens=4096,
        cost=ModelCost(input=2.5, output=10.0),
        capabilities=ModelCapabilities(
            supports_tools=True,
            supports_vision=True,
            supports_streaming=True,
            max_output_tokens=16384,
        ),
    ),
    "openai/gpt-4o-mini": ModelConfig(
        id="openai/gpt-4o-mini",
        name="GPT-4o Mini",
        api_type=ApiType.OPENAI,
        provider="openai",
        model_id="gpt-4o-mini",
        context_window=128000,
        max_tokens=4096,
        cost=ModelCost(input=0.15, output=0.6),
        capabilities=ModelCapabilities(
            supports_tools=True,
            supports_vision=True,
            supports_streaming=True,
            max_output_tokens=16384,
        ),
    ),
    "openai/gpt-4-turbo": ModelConfig(
        id="openai/gpt-4-turbo",
        name="GPT-4 Turbo",
        api_type=ApiType.OPENAI,
        provider="openai",
        model_id="gpt-4-turbo",
        context_window=128000,
        max_tokens=4096,
        cost=ModelCost(input=10.0, output=30.0),
        capabilities=ModelCapabilities(
            supports_tools=True,
            supports_vision=True,
            supports_streaming=True,
            max_output_tokens=4096,
        ),
    ),
    "openai/o1-mini": ModelConfig(
        id="openai/o1-mini",
        name="O1 Mini",
        api_type=ApiType.OPENAI,
        provider="openai",
        model_id="o1-mini",
        context_window=128000,
        max_tokens=65536,
        cost=ModelCost(input=1.1, output=4.4),
        capabilities=ModelCapabilities(
            supports_tools=False,  # O1 doesn't support tools yet
            supports_vision=False,
            supports_streaming=True,
            max_output_tokens=65536,
        ),
    ),
    # Ollama local models
    "ollama/llama3.3": ModelConfig(
        id="ollama/llama3.3",
        name="Llama 3.3 70B",
        api_type=ApiType.OLLAMA,
        provider="ollama",
        model_id="llama3.3",
        context_window=128000,
        max_tokens=4096,
        cost=ModelCost(),  # Free (local)
        capabilities=ModelCapabilities(
            supports_tools=True,
            supports_vision=False,
            supports_streaming=True,
        ),
    ),
    "ollama/llama3.2": ModelConfig(
        id="ollama/llama3.2",
        name="Llama 3.2",
        api_type=ApiType.OLLAMA,
        provider="ollama",
        model_id="llama3.2",
        context_window=128000,
        max_tokens=4096,
        cost=ModelCost(),
        capabilities=ModelCapabilities(
            supports_tools=True,
            supports_vision=True,  # Llama 3.2 has vision variants
            supports_streaming=True,
        ),
    ),
    "ollama/qwen2.5": ModelConfig(
        id="ollama/qwen2.5",
        name="Qwen 2.5",
        api_type=ApiType.OLLAMA,
        provider="ollama",
        model_id="qwen2.5",
        context_window=32000,
        max_tokens=4096,
        cost=ModelCost(),
        capabilities=ModelCapabilities(
            supports_tools=True,
            supports_vision=False,
            supports_streaming=True,
        ),
    ),
    "ollama/qwen2.5-coder": ModelConfig(
        id="ollama/qwen2.5-coder",
        name="Qwen 2.5 Coder",
        api_type=ApiType.OLLAMA,
        provider="ollama",
        model_id="qwen2.5-coder",
        context_window=32000,
        max_tokens=4096,
        cost=ModelCost(),
        capabilities=ModelCapabilities(
            supports_tools=True,
            supports_vision=False,
            supports_streaming=True,
        ),
    ),
    "ollama/deepseek-r1": ModelConfig(
        id="ollama/deepseek-r1",
        name="DeepSeek R1",
        api_type=ApiType.OLLAMA,
        provider="ollama",
        model_id="deepseek-r1",
        context_window=64000,
        max_tokens=8192,
        cost=ModelCost(),
        capabilities=ModelCapabilities(
            supports_tools=True,
            supports_vision=False,
            supports_streaming=True,
        ),
    ),
    "ollama/mistral": ModelConfig(
        id="ollama/mistral",
        name="Mistral 7B",
        api_type=ApiType.OLLAMA,
        provider="ollama",
        model_id="mistral",
        context_window=32000,
        max_tokens=4096,
        cost=ModelCost(),
        capabilities=ModelCapabilities(
            supports_tools=True,
            supports_vision=False,
            supports_streaming=True,
        ),
    ),
}


class ModelRegistry:
    """Registry for model configurations and adapters.

    Manages model definitions and lazily creates adapters on demand.
    Supports built-in models and user-defined custom models.
    """

    def __init__(self, settings: "Settings") -> None:
        """Initialize the model registry.

        Args:
            settings: Application settings containing API keys and model config
        """
        self._settings = settings
        self._models: dict[str, ModelConfig] = dict(BUILTIN_MODELS)
        self._adapters: dict[str, ModelAdapter] = {}
        self._load_custom_models()

    def _load_custom_models(self) -> None:
        """Load custom model definitions from settings."""
        custom_models = getattr(self._settings.models, "custom_models", {})
        for model_id, config_dict in custom_models.items():
            try:
                config = ModelConfig(id=model_id, **config_dict)
                self._models[model_id] = config
                logger.info(f"Loaded custom model: {model_id}")
            except Exception as e:
                logger.warning(f"Failed to load custom model {model_id}: {e}")

    def get_config(self, model_id: str) -> ModelConfig | None:
        """Get model configuration by ID.

        Args:
            model_id: Model identifier (e.g., "anthropic/claude-sonnet-4-20250514")

        Returns:
            Model configuration or None if not found
        """
        return self._models.get(model_id)

    def get_adapter(self, model_id: str) -> ModelAdapter:
        """Get or create an adapter for the specified model.

        Args:
            model_id: Model identifier

        Returns:
            Model adapter instance

        Raises:
            ValueError: If model is not found or API key is missing
        """
        if model_id in self._adapters:
            return self._adapters[model_id]

        config = self._models.get(model_id)
        if not config:
            raise ValueError(f"Unknown model: {model_id}")

        adapter = self._create_adapter(config)
        self._adapters[model_id] = adapter
        logger.debug(f"Created adapter for model: {model_id}")
        return adapter

    def _create_adapter(self, config: ModelConfig) -> ModelAdapter:
        """Create an adapter for the given model configuration.

        Args:
            config: Model configuration

        Returns:
            Configured model adapter

        Raises:
            ValueError: If API key is missing or API type is unsupported
        """
        if config.api_type == ApiType.ANTHROPIC:
            from lurkbot.models.adapters.anthropic import AnthropicAdapter

            api_key = self._settings.anthropic_api_key
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY not configured")
            return AnthropicAdapter(config, api_key)

        elif config.api_type == ApiType.OPENAI:
            from lurkbot.models.adapters.openai import OpenAIAdapter

            api_key = self._settings.openai_api_key
            if not api_key:
                raise ValueError("OPENAI_API_KEY not configured")
            return OpenAIAdapter(config, api_key)

        elif config.api_type == ApiType.OLLAMA:
            from lurkbot.models.adapters.ollama import OllamaAdapter

            base_url = getattr(self._settings.models, "ollama_base_url", "http://localhost:11434")
            return OllamaAdapter(config, base_url=base_url)

        elif config.api_type == ApiType.LITELLM:
            raise ValueError("LiteLLM adapter not yet implemented")

        else:
            raise ValueError(f"Unsupported API type: {config.api_type}")

    def list_models(
        self,
        provider: str | None = None,
        api_type: ApiType | None = None,
    ) -> list[ModelConfig]:
        """List available models with optional filtering.

        Args:
            provider: Filter by provider name (e.g., "anthropic")
            api_type: Filter by API type

        Returns:
            List of matching model configurations
        """
        models = list(self._models.values())

        if provider:
            models = [m for m in models if m.provider == provider]

        if api_type:
            models = [m for m in models if m.api_type == api_type]

        return sorted(models, key=lambda m: m.id)

    def register_model(self, config: ModelConfig) -> None:
        """Register a new model configuration.

        Args:
            config: Model configuration to register
        """
        self._models[config.id] = config
        logger.info(f"Registered model: {config.id}")

    def unregister_model(self, model_id: str) -> bool:
        """Unregister a model configuration.

        Args:
            model_id: Model identifier

        Returns:
            True if model was unregistered
        """
        if model_id in self._models:
            del self._models[model_id]
            # Also remove cached adapter if any
            if model_id in self._adapters:
                del self._adapters[model_id]
            logger.info(f"Unregistered model: {model_id}")
            return True
        return False

    def clear_adapters(self) -> None:
        """Clear all cached adapters."""
        self._adapters.clear()
        logger.debug("Cleared all cached adapters")


def get_model_registry(settings: "Settings") -> ModelRegistry:
    """Create a model registry instance.

    Args:
        settings: Application settings

    Returns:
        Configured model registry
    """
    return ModelRegistry(settings)
