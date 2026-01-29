"""OpenAI TTS provider.

Ported from moltbot/src/tts/tts.ts (openaiTTS function)

Supports models: gpt-4o-mini-tts, tts-1, tts-1-hd
Supports voices: alloy, ash, coral, echo, fable, onyx, nova, sage, shimmer
"""

from __future__ import annotations

import os
import time
from pathlib import Path

import httpx
from loguru import logger

from lurkbot.tts.providers.base import TtsProviderBase, TtsProviderResult
from lurkbot.tts.types import (
    DEFAULT_OPENAI_MODEL,
    DEFAULT_OPENAI_VOICE,
    DEFAULT_OUTPUT,
    DEFAULT_TIMEOUT_MS,
    TELEGRAM_OUTPUT,
    ResolvedOpenAIConfig,
)


class OpenAITtsProvider(TtsProviderBase):
    """OpenAI TTS provider."""

    def __init__(
        self,
        config: ResolvedOpenAIConfig | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
    ):
        """Initialize OpenAI TTS provider.

        Args:
            config: Resolved OpenAI TTS configuration
            api_key: API key (overrides config)
            base_url: Base URL for API (for custom endpoints)
        """
        self._config = config or ResolvedOpenAIConfig()
        self._api_key = api_key or self._config.api_key or os.environ.get("OPENAI_API_KEY")
        self._base_url = base_url or "https://api.openai.com/v1"

    @property
    def name(self) -> str:
        return "openai"

    def is_configured(self) -> bool:
        return bool(self._api_key)

    async def synthesize(
        self,
        text: str,
        output_path: str | None = None,
        voice: str | None = None,
        model: str | None = None,
        response_format: str | None = None,
        speed: float = 1.0,
        timeout_ms: int = DEFAULT_TIMEOUT_MS,
        channel: str | None = None,
        **kwargs,
    ) -> TtsProviderResult:
        """Synthesize text to speech using OpenAI API.

        Args:
            text: Text to synthesize
            output_path: Path to save audio file
            voice: Voice to use (default: alloy)
            model: Model to use (default: gpt-4o-mini-tts)
            response_format: Output format (mp3, opus, aac, flac, wav, pcm)
            speed: Speech speed (0.25 to 4.0)
            timeout_ms: Request timeout in milliseconds
            channel: Channel type for format selection (e.g., "telegram")

        Returns:
            TtsProviderResult with audio data
        """
        if not self._api_key:
            return TtsProviderResult(
                success=False,
                error="OpenAI API key not configured",
            )

        start_time = time.time()

        # Resolve parameters
        effective_voice = voice or self._config.voice or DEFAULT_OPENAI_VOICE
        effective_model = model or self._config.model or DEFAULT_OPENAI_MODEL

        # Determine output format based on channel
        output_config = TELEGRAM_OUTPUT if channel == "telegram" else DEFAULT_OUTPUT
        effective_format = response_format or output_config.get("openai", "mp3")
        voice_compatible = output_config.get("voice_compatible", False)
        extension = output_config.get("extension", ".mp3")

        try:
            async with httpx.AsyncClient(timeout=timeout_ms / 1000) as client:
                response = await client.post(
                    f"{self._base_url}/audio/speech",
                    headers={
                        "Authorization": f"Bearer {self._api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": effective_model,
                        "input": text,
                        "voice": effective_voice,
                        "response_format": effective_format,
                        "speed": speed,
                    },
                )

                if response.status_code != 200:
                    error_text = response.text
                    logger.error(f"OpenAI TTS error: {response.status_code} - {error_text}")
                    return TtsProviderResult(
                        success=False,
                        error=f"OpenAI API error: {response.status_code}",
                        latency_ms=int((time.time() - start_time) * 1000),
                    )

                audio_data = response.content
                latency_ms = int((time.time() - start_time) * 1000)

                # Save to file if path provided
                if output_path:
                    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                    Path(output_path).write_bytes(audio_data)

                return TtsProviderResult(
                    success=True,
                    audio_data=audio_data,
                    audio_path=output_path,
                    latency_ms=latency_ms,
                    output_format=effective_format,
                    voice_compatible=voice_compatible,
                )

        except httpx.TimeoutException:
            return TtsProviderResult(
                success=False,
                error="OpenAI TTS request timed out",
                latency_ms=int((time.time() - start_time) * 1000),
            )
        except Exception as e:
            logger.exception("OpenAI TTS error")
            return TtsProviderResult(
                success=False,
                error=str(e),
                latency_ms=int((time.time() - start_time) * 1000),
            )
