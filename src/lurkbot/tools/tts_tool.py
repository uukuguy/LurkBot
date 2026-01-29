"""TTS Tool - Text-to-Speech synthesis tool.

Provides a tool interface for TTS synthesis that can be used by agents.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from loguru import logger

from lurkbot.tts import (
    TtsEngine,
    TtsEngineConfig,
    TtsProvider,
    TtsSynthesisResult,
    ResolvedEdgeConfig,
    ResolvedElevenLabsConfig,
    ResolvedOpenAIConfig,
    create_tts_engine,
)


@dataclass
class TtsToolConfig:
    """Configuration for TTS tool."""

    # Default provider
    default_provider: TtsProvider = "edge"

    # Output directory for generated audio
    output_dir: str | None = None

    # Provider configurations
    openai_api_key: str | None = None
    elevenlabs_api_key: str | None = None

    # Enable/disable providers
    enable_openai: bool = True
    enable_elevenlabs: bool = True
    enable_edge: bool = True


class TtsTool:
    """TTS synthesis tool for agents.

    Provides text-to-speech synthesis capabilities.
    """

    name = "tts"
    description = "Synthesize text to speech audio"

    def __init__(self, config: TtsToolConfig | None = None):
        """Initialize TTS tool.

        Args:
            config: Tool configuration
        """
        self._config = config or TtsToolConfig()
        self._engine: TtsEngine | None = None

    def _get_engine(self) -> TtsEngine:
        """Get or create TTS engine."""
        if self._engine is None:
            # Build provider configs
            openai_config = None
            if self._config.enable_openai:
                api_key = self._config.openai_api_key or os.environ.get("OPENAI_API_KEY")
                if api_key:
                    openai_config = ResolvedOpenAIConfig(api_key=api_key)

            elevenlabs_config = None
            if self._config.enable_elevenlabs:
                api_key = (
                    self._config.elevenlabs_api_key
                    or os.environ.get("ELEVENLABS_API_KEY")
                    or os.environ.get("XI_API_KEY")
                )
                if api_key:
                    elevenlabs_config = ResolvedElevenLabsConfig(api_key=api_key)

            edge_config = None
            if self._config.enable_edge:
                edge_config = ResolvedEdgeConfig(enabled=True)

            engine_config = TtsEngineConfig(
                openai=openai_config,
                elevenlabs=elevenlabs_config,
                edge=edge_config,
                default_provider=self._config.default_provider,
                output_dir=self._config.output_dir,
            )

            self._engine = TtsEngine(engine_config)

        return self._engine

    @property
    def available_providers(self) -> list[str]:
        """Get list of available providers."""
        return self._get_engine().available_providers

    async def synthesize(
        self,
        text: str,
        provider: TtsProvider | None = None,
        output_path: str | None = None,
        voice: str | None = None,
        model: str | None = None,
        **kwargs,
    ) -> TtsSynthesisResult:
        """Synthesize text to speech.

        Args:
            text: Text to synthesize
            provider: Provider to use (default: auto-select)
            output_path: Path to save audio file
            voice: Voice to use (provider-specific)
            model: Model to use (provider-specific)
            **kwargs: Additional provider-specific options

        Returns:
            TtsSynthesisResult with audio data or path
        """
        engine = self._get_engine()

        # Build kwargs with voice/model if provided
        synth_kwargs = dict(kwargs)
        if voice:
            synth_kwargs["voice"] = voice
        if model:
            synth_kwargs["model"] = model

        return await engine.synthesize(
            text=text,
            provider=provider,
            output_path=output_path,
            **synth_kwargs,
        )

    def get_tool_definition(self) -> dict[str, Any]:
        """Get tool definition for agent use.

        Returns:
            Tool definition dict
        """
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "Text to synthesize to speech",
                    },
                    "provider": {
                        "type": "string",
                        "enum": ["openai", "elevenlabs", "edge"],
                        "description": "TTS provider to use (default: auto-select)",
                    },
                    "voice": {
                        "type": "string",
                        "description": "Voice to use (provider-specific)",
                    },
                    "model": {
                        "type": "string",
                        "description": "Model to use (provider-specific)",
                    },
                    "output_path": {
                        "type": "string",
                        "description": "Path to save audio file",
                    },
                },
                "required": ["text"],
            },
        }

    async def execute(self, **kwargs) -> dict[str, Any]:
        """Execute tool with given arguments.

        Args:
            **kwargs: Tool arguments

        Returns:
            Tool result dict
        """
        text = kwargs.get("text", "")
        if not text:
            return {
                "success": False,
                "error": "No text provided",
            }

        result = await self.synthesize(
            text=text,
            provider=kwargs.get("provider"),
            output_path=kwargs.get("output_path"),
            voice=kwargs.get("voice"),
            model=kwargs.get("model"),
        )

        return {
            "success": result.success,
            "audio_path": result.audio_path,
            "provider": result.provider,
            "latency_ms": result.latency_ms,
            "output_format": result.output_format,
            "error": result.error,
            "warnings": result.warnings,
        }


# =============================================================================
# Factory Functions
# =============================================================================

def create_tts_tool(
    default_provider: TtsProvider = "edge",
    output_dir: str | None = None,
) -> TtsTool:
    """Create a TTS tool with default configuration.

    Args:
        default_provider: Default TTS provider
        output_dir: Output directory for audio files

    Returns:
        Configured TtsTool instance
    """
    config = TtsToolConfig(
        default_provider=default_provider,
        output_dir=output_dir,
    )
    return TtsTool(config)


# =============================================================================
# Convenience Functions
# =============================================================================

async def tts_synthesize(
    text: str,
    provider: TtsProvider | None = None,
    output_path: str | None = None,
    **kwargs,
) -> TtsSynthesisResult:
    """Convenience function to synthesize text to speech.

    Args:
        text: Text to synthesize
        provider: Provider to use
        output_path: Path to save audio file
        **kwargs: Provider-specific options

    Returns:
        TtsSynthesisResult
    """
    tool = TtsTool()
    return await tool.synthesize(
        text=text,
        provider=provider,
        output_path=output_path,
        **kwargs,
    )
