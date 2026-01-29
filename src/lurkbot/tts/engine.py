"""TTS Engine - Main synthesis orchestrator.

Ported from moltbot/src/tts/tts.ts

Provides a unified interface for text-to-speech synthesis across multiple providers.
Handles provider selection, text preprocessing, directive parsing, and audio generation.
"""

from __future__ import annotations

import os
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from loguru import logger

from lurkbot.tts.directive_parser import parse_tts_directives
from lurkbot.tts.providers import (
    EdgeTtsProvider,
    ElevenLabsTtsProvider,
    OpenAITtsProvider,
    TtsProviderResult,
)
from lurkbot.tts.types import (
    DEFAULT_TTS_PROVIDER,
    ResolvedEdgeConfig,
    ResolvedElevenLabsConfig,
    ResolvedOpenAIConfig,
    TtsConfig,
    TtsModelOverrideConfig,
    TtsProvider,
)

if TYPE_CHECKING:
    from lurkbot.tts.providers.base import TtsProviderBase


@dataclass
class TtsEngineConfig:
    """Configuration for TTS engine."""

    # Provider configurations
    openai: ResolvedOpenAIConfig | None = None
    elevenlabs: ResolvedElevenLabsConfig | None = None
    edge: ResolvedEdgeConfig | None = None

    # Default provider
    default_provider: TtsProvider = DEFAULT_TTS_PROVIDER

    # Override policy
    override_policy: TtsModelOverrideConfig | None = None

    # Output directory for generated audio
    output_dir: str | None = None

    # Channel type (affects output format)
    channel: str | None = None


@dataclass
class TtsSynthesisResult:
    """Result from TTS synthesis."""

    success: bool
    audio_data: bytes | None = None
    audio_path: str | None = None
    error: str | None = None
    provider: str | None = None
    latency_ms: int | None = None
    output_format: str | None = None
    voice_compatible: bool = False
    warnings: list[str] = field(default_factory=list)


class TtsEngine:
    """Main TTS synthesis engine.

    Orchestrates text-to-speech synthesis across multiple providers.
    """

    def __init__(self, config: TtsEngineConfig | None = None):
        """Initialize TTS engine.

        Args:
            config: Engine configuration
        """
        self._config = config or TtsEngineConfig()
        self._providers: dict[str, TtsProviderBase] = {}
        self._init_providers()

    def _init_providers(self) -> None:
        """Initialize available TTS providers."""
        # OpenAI provider
        openai_provider = OpenAITtsProvider(config=self._config.openai)
        if openai_provider.is_configured():
            self._providers["openai"] = openai_provider
            logger.debug("OpenAI TTS provider initialized")

        # ElevenLabs provider
        elevenlabs_provider = ElevenLabsTtsProvider(config=self._config.elevenlabs)
        if elevenlabs_provider.is_configured():
            self._providers["elevenlabs"] = elevenlabs_provider
            logger.debug("ElevenLabs TTS provider initialized")

        # Edge provider (always available if enabled)
        edge_config = self._config.edge or ResolvedEdgeConfig(enabled=True)
        edge_provider = EdgeTtsProvider(config=edge_config)
        if edge_provider.is_configured():
            self._providers["edge"] = edge_provider
            logger.debug("Edge TTS provider initialized")

    @property
    def available_providers(self) -> list[str]:
        """Get list of available provider names."""
        return list(self._providers.keys())

    def is_provider_available(self, provider: str) -> bool:
        """Check if a provider is available."""
        return provider in self._providers

    def get_default_provider(self) -> str | None:
        """Get the default provider name."""
        # Use configured default if available
        if self._config.default_provider in self._providers:
            return self._config.default_provider

        # Fall back to first available provider
        if self._providers:
            # Prefer openai > elevenlabs > edge
            for p in ["openai", "elevenlabs", "edge"]:
                if p in self._providers:
                    return p
            return next(iter(self._providers.keys()))

        return None

    async def synthesize(
        self,
        text: str,
        provider: TtsProvider | None = None,
        output_path: str | None = None,
        **kwargs,
    ) -> TtsSynthesisResult:
        """Synthesize text to speech.

        Args:
            text: Text to synthesize
            provider: Provider to use (default: auto-select)
            output_path: Path to save audio file
            **kwargs: Provider-specific options

        Returns:
            TtsSynthesisResult with audio data or path
        """
        start_time = time.time()
        warnings: list[str] = []

        # Parse directives from text
        override_policy = self._config.override_policy or TtsModelOverrideConfig(enabled=True)
        parse_result = parse_tts_directives(
            text,
            policy=override_policy,
            custom_openai_endpoint=False,
        )

        # Use cleaned text for synthesis
        synthesis_text = parse_result.tts_text or parse_result.cleaned_text
        warnings.extend(parse_result.warnings)

        if not synthesis_text.strip():
            return TtsSynthesisResult(
                success=False,
                error="No text to synthesize",
                warnings=warnings,
            )

        # Determine provider
        effective_provider = (
            parse_result.overrides.provider
            or provider
            or self.get_default_provider()
        )

        if not effective_provider:
            return TtsSynthesisResult(
                success=False,
                error="No TTS provider available",
                warnings=warnings,
            )

        if effective_provider not in self._providers:
            return TtsSynthesisResult(
                success=False,
                error=f"Provider '{effective_provider}' not available",
                warnings=warnings,
            )

        # Get provider instance
        provider_instance = self._providers[effective_provider]

        # Merge overrides into kwargs
        merged_kwargs = {**kwargs}
        merged_kwargs["channel"] = self._config.channel

        # Apply provider-specific overrides
        if effective_provider == "openai" and parse_result.overrides.openai:
            if parse_result.overrides.openai.voice:
                merged_kwargs["voice"] = parse_result.overrides.openai.voice
            if parse_result.overrides.openai.model:
                merged_kwargs["model"] = parse_result.overrides.openai.model

        elif effective_provider == "elevenlabs" and parse_result.overrides.elevenlabs:
            el_overrides = parse_result.overrides.elevenlabs
            if el_overrides.voice_id:
                merged_kwargs["voice_id"] = el_overrides.voice_id
            if el_overrides.model_id:
                merged_kwargs["model_id"] = el_overrides.model_id
            if el_overrides.voice_settings:
                merged_kwargs["voice_settings"] = el_overrides.voice_settings
            if el_overrides.seed is not None:
                merged_kwargs["seed"] = el_overrides.seed
            if el_overrides.apply_text_normalization:
                merged_kwargs["apply_text_normalization"] = el_overrides.apply_text_normalization
            if el_overrides.language_code:
                merged_kwargs["language_code"] = el_overrides.language_code

        # Generate output path if not provided
        if not output_path and self._config.output_dir:
            output_path = self._generate_output_path(effective_provider)

        # Synthesize
        try:
            result = await provider_instance.synthesize(
                text=synthesis_text,
                output_path=output_path,
                **merged_kwargs,
            )

            return TtsSynthesisResult(
                success=result.success,
                audio_data=result.audio_data,
                audio_path=result.audio_path,
                error=result.error,
                provider=effective_provider,
                latency_ms=result.latency_ms,
                output_format=result.output_format,
                voice_compatible=result.voice_compatible,
                warnings=warnings,
            )

        except Exception as e:
            logger.exception(f"TTS synthesis error with provider {effective_provider}")
            return TtsSynthesisResult(
                success=False,
                error=str(e),
                provider=effective_provider,
                latency_ms=int((time.time() - start_time) * 1000),
                warnings=warnings,
            )

    def _generate_output_path(self, provider: str) -> str:
        """Generate a unique output path for audio file."""
        output_dir = self._config.output_dir or tempfile.gettempdir()
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        timestamp = int(time.time() * 1000)
        extension = ".mp3"  # Default extension

        return str(Path(output_dir) / f"tts_{provider}_{timestamp}{extension}")


# =============================================================================
# Factory Functions
# =============================================================================

def create_tts_engine(config: TtsConfig | None = None) -> TtsEngine:
    """Create a TTS engine from configuration.

    Args:
        config: TTS configuration

    Returns:
        Configured TtsEngine instance
    """
    if config is None:
        # Create default configuration from environment
        engine_config = TtsEngineConfig(
            openai=ResolvedOpenAIConfig(
                api_key=os.environ.get("OPENAI_API_KEY"),
            ),
            elevenlabs=ResolvedElevenLabsConfig(
                api_key=os.environ.get("ELEVENLABS_API_KEY") or os.environ.get("XI_API_KEY"),
            ),
            edge=ResolvedEdgeConfig(enabled=True),
        )
    else:
        engine_config = TtsEngineConfig(
            openai=config.openai,
            elevenlabs=config.elevenlabs,
            edge=config.edge,
            default_provider=config.default_provider or DEFAULT_TTS_PROVIDER,
            override_policy=config.override_policy,
        )

    return TtsEngine(engine_config)


async def synthesize_text(
    text: str,
    provider: TtsProvider | None = None,
    output_path: str | None = None,
    **kwargs,
) -> TtsSynthesisResult:
    """Convenience function to synthesize text to speech.

    Creates a default TTS engine and synthesizes the text.

    Args:
        text: Text to synthesize
        provider: Provider to use
        output_path: Path to save audio file
        **kwargs: Provider-specific options

    Returns:
        TtsSynthesisResult with audio data or path
    """
    engine = create_tts_engine()
    return await engine.synthesize(
        text=text,
        provider=provider,
        output_path=output_path,
        **kwargs,
    )
