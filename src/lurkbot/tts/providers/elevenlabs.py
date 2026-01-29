"""ElevenLabs TTS provider.

Ported from moltbot/src/tts/tts.ts (elevenLabsTTS function)

Supports multiple voices and models with fine-grained voice settings.
"""

from __future__ import annotations

import os
import time
from pathlib import Path

import httpx
from loguru import logger

from lurkbot.tts.providers.base import TtsProviderBase, TtsProviderResult
from lurkbot.tts.types import (
    DEFAULT_ELEVENLABS_BASE_URL,
    DEFAULT_ELEVENLABS_MODEL_ID,
    DEFAULT_ELEVENLABS_VOICE_ID,
    DEFAULT_ELEVENLABS_VOICE_SETTINGS,
    DEFAULT_OUTPUT,
    DEFAULT_TIMEOUT_MS,
    TELEGRAM_OUTPUT,
    ResolvedElevenLabsConfig,
)


class ElevenLabsTtsProvider(TtsProviderBase):
    """ElevenLabs TTS provider."""

    def __init__(
        self,
        config: ResolvedElevenLabsConfig | None = None,
        api_key: str | None = None,
    ):
        """Initialize ElevenLabs TTS provider.

        Args:
            config: Resolved ElevenLabs TTS configuration
            api_key: API key (overrides config)
        """
        self._config = config or ResolvedElevenLabsConfig()
        self._api_key = (
            api_key
            or self._config.api_key
            or os.environ.get("ELEVENLABS_API_KEY")
            or os.environ.get("XI_API_KEY")
        )

    @property
    def name(self) -> str:
        return "elevenlabs"

    def is_configured(self) -> bool:
        return bool(self._api_key)

    async def synthesize(
        self,
        text: str,
        output_path: str | None = None,
        voice_id: str | None = None,
        model_id: str | None = None,
        voice_settings: dict | None = None,
        seed: int | None = None,
        apply_text_normalization: str | None = None,
        language_code: str | None = None,
        output_format: str | None = None,
        timeout_ms: int = DEFAULT_TIMEOUT_MS,
        channel: str | None = None,
        **kwargs,
    ) -> TtsProviderResult:
        """Synthesize text to speech using ElevenLabs API.

        Args:
            text: Text to synthesize
            output_path: Path to save audio file
            voice_id: Voice ID to use
            model_id: Model ID to use
            voice_settings: Voice settings (stability, similarity_boost, etc.)
            seed: Random seed for reproducibility
            apply_text_normalization: Text normalization mode (auto, on, off)
            language_code: ISO 639-1 language code
            output_format: Output format
            timeout_ms: Request timeout in milliseconds
            channel: Channel type for format selection

        Returns:
            TtsProviderResult with audio data
        """
        if not self._api_key:
            return TtsProviderResult(
                success=False,
                error="ElevenLabs API key not configured",
            )

        start_time = time.time()

        # Resolve parameters
        effective_voice_id = voice_id or self._config.voice_id or DEFAULT_ELEVENLABS_VOICE_ID
        effective_model_id = model_id or self._config.model_id or DEFAULT_ELEVENLABS_MODEL_ID
        base_url = self._config.base_url or DEFAULT_ELEVENLABS_BASE_URL

        # Merge voice settings
        effective_voice_settings = {**DEFAULT_ELEVENLABS_VOICE_SETTINGS}
        if self._config.voice_settings:
            effective_voice_settings.update({
                "stability": self._config.voice_settings.stability,
                "similarity_boost": self._config.voice_settings.similarity_boost,
                "style": self._config.voice_settings.style,
                "use_speaker_boost": self._config.voice_settings.use_speaker_boost,
                "speed": self._config.voice_settings.speed,
            })
        if voice_settings:
            effective_voice_settings.update(voice_settings)

        # Determine output format based on channel
        output_config = TELEGRAM_OUTPUT if channel == "telegram" else DEFAULT_OUTPUT
        effective_format = output_format or output_config.get("elevenlabs", "mp3_44100_128")
        voice_compatible = output_config.get("voice_compatible", False)

        # Build request body
        body: dict = {
            "text": text,
            "model_id": effective_model_id,
            "voice_settings": effective_voice_settings,
        }

        # Add optional parameters
        effective_seed = seed if seed is not None else self._config.seed
        if effective_seed is not None:
            body["seed"] = effective_seed

        effective_normalization = (
            apply_text_normalization or self._config.apply_text_normalization
        )
        if effective_normalization:
            body["apply_text_normalization"] = effective_normalization

        effective_language = language_code or self._config.language_code
        if effective_language:
            body["language_code"] = effective_language

        try:
            url = f"{base_url}/v1/text-to-speech/{effective_voice_id}"
            if effective_format:
                url += f"?output_format={effective_format}"

            async with httpx.AsyncClient(timeout=timeout_ms / 1000) as client:
                response = await client.post(
                    url,
                    headers={
                        "xi-api-key": self._api_key,
                        "Content-Type": "application/json",
                    },
                    json=body,
                )

                if response.status_code != 200:
                    error_text = response.text
                    logger.error(f"ElevenLabs TTS error: {response.status_code} - {error_text}")
                    return TtsProviderResult(
                        success=False,
                        error=f"ElevenLabs API error: {response.status_code}",
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
                error="ElevenLabs TTS request timed out",
                latency_ms=int((time.time() - start_time) * 1000),
            )
        except Exception as e:
            logger.exception("ElevenLabs TTS error")
            return TtsProviderResult(
                success=False,
                error=str(e),
                latency_ms=int((time.time() - start_time) * 1000),
            )
