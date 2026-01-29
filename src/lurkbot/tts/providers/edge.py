"""Edge TTS provider.

Ported from moltbot/src/tts/tts.ts (edgeTTS function)

Free TTS using Microsoft Edge's online TTS service.
No API key required.
"""

from __future__ import annotations

import asyncio
import time
from pathlib import Path

from loguru import logger

from lurkbot.tts.providers.base import TtsProviderBase, TtsProviderResult
from lurkbot.tts.types import (
    DEFAULT_EDGE_LANG,
    DEFAULT_EDGE_OUTPUT_FORMAT,
    DEFAULT_EDGE_VOICE,
    DEFAULT_TIMEOUT_MS,
    ResolvedEdgeConfig,
)


class EdgeTtsProvider(TtsProviderBase):
    """Edge TTS provider using Microsoft Edge's online TTS service."""

    def __init__(
        self,
        config: ResolvedEdgeConfig | None = None,
    ):
        """Initialize Edge TTS provider.

        Args:
            config: Resolved Edge TTS configuration
        """
        self._config = config or ResolvedEdgeConfig()

    @property
    def name(self) -> str:
        return "edge"

    def is_configured(self) -> bool:
        return self._config.enabled

    async def synthesize(
        self,
        text: str,
        output_path: str | None = None,
        voice: str | None = None,
        lang: str | None = None,
        output_format: str | None = None,
        pitch: str | None = None,
        rate: str | None = None,
        volume: str | None = None,
        timeout_ms: int = DEFAULT_TIMEOUT_MS,
        **kwargs,
    ) -> TtsProviderResult:
        """Synthesize text to speech using Edge TTS.

        Args:
            text: Text to synthesize
            output_path: Path to save audio file
            voice: Voice to use (e.g., "en-US-MichelleNeural")
            lang: Language code
            output_format: Output format
            pitch: Pitch adjustment (e.g., "+0Hz", "-10Hz")
            rate: Rate adjustment (e.g., "+0%", "-10%")
            volume: Volume adjustment (e.g., "+0%", "-10%")
            timeout_ms: Request timeout in milliseconds

        Returns:
            TtsProviderResult with audio data
        """
        if not self._config.enabled:
            return TtsProviderResult(
                success=False,
                error="Edge TTS is disabled",
            )

        start_time = time.time()

        # Resolve parameters
        effective_voice = voice or self._config.voice or DEFAULT_EDGE_VOICE
        effective_pitch = pitch or self._config.pitch
        effective_rate = rate or self._config.rate
        effective_volume = volume or self._config.volume
        effective_timeout = timeout_ms or self._config.timeout_ms or DEFAULT_TIMEOUT_MS

        try:
            # Import edge_tts lazily to avoid import errors if not installed
            try:
                import edge_tts
            except ImportError:
                return TtsProviderResult(
                    success=False,
                    error="edge-tts package not installed. Install with: pip install edge-tts",
                )

            # Create communicate instance
            communicate = edge_tts.Communicate(
                text=text,
                voice=effective_voice,
                pitch=effective_pitch,
                rate=effective_rate,
                volume=effective_volume,
                proxy=self._config.proxy,
            )

            # Collect audio data
            audio_chunks: list[bytes] = []

            async def collect_audio():
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        audio_chunks.append(chunk["data"])

            # Run with timeout
            try:
                await asyncio.wait_for(
                    collect_audio(),
                    timeout=effective_timeout / 1000,
                )
            except asyncio.TimeoutError:
                return TtsProviderResult(
                    success=False,
                    error="Edge TTS request timed out",
                    latency_ms=int((time.time() - start_time) * 1000),
                )

            if not audio_chunks:
                return TtsProviderResult(
                    success=False,
                    error="No audio data received from Edge TTS",
                    latency_ms=int((time.time() - start_time) * 1000),
                )

            audio_data = b"".join(audio_chunks)
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
                output_format="mp3",
                voice_compatible=False,
            )

        except Exception as e:
            logger.exception("Edge TTS error")
            return TtsProviderResult(
                success=False,
                error=str(e),
                latency_ms=int((time.time() - start_time) * 1000),
            )


async def list_edge_voices(language: str | None = None) -> list[dict]:
    """List available Edge TTS voices.

    Args:
        language: Optional language filter (e.g., "en", "zh")

    Returns:
        List of voice dictionaries with Name, ShortName, Gender, Locale
    """
    try:
        import edge_tts
        voices = await edge_tts.list_voices()

        if language:
            lang_lower = language.lower()
            voices = [
                v for v in voices
                if v.get("Locale", "").lower().startswith(lang_lower)
            ]

        return voices
    except ImportError:
        logger.error("edge-tts package not installed")
        return []
    except Exception as e:
        logger.exception("Failed to list Edge TTS voices")
        return []
