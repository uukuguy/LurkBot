"""Base class for TTS providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class TtsProviderResult:
    """Result from a TTS provider."""

    success: bool
    audio_data: bytes | None = None
    audio_path: str | None = None
    error: str | None = None
    latency_ms: int | None = None
    output_format: str | None = None
    voice_compatible: bool = False


class TtsProviderBase(ABC):
    """Abstract base class for TTS providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name."""
        ...

    @abstractmethod
    async def synthesize(
        self,
        text: str,
        output_path: str | None = None,
        **kwargs,
    ) -> TtsProviderResult:
        """Synthesize text to speech.

        Args:
            text: Text to synthesize
            output_path: Optional path to save audio file
            **kwargs: Provider-specific options

        Returns:
            TtsProviderResult with audio data or path
        """
        ...

    @abstractmethod
    def is_configured(self) -> bool:
        """Check if provider is properly configured."""
        ...
