"""TTS Text Summarizer.

Ported from moltbot/src/tts/summarizer.ts

Provides text summarization for TTS to handle long texts that exceed
provider limits or would result in excessively long audio.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from loguru import logger


# =============================================================================
# Constants
# =============================================================================

# Default character limits for different providers
DEFAULT_CHAR_LIMITS = {
    "openai": 4096,
    "elevenlabs": 5000,
    "edge": 5000,
}

# Maximum recommended audio duration in seconds
MAX_AUDIO_DURATION_SECONDS = 60

# Approximate characters per second of speech
CHARS_PER_SECOND = 15


# =============================================================================
# Types
# =============================================================================

SummarizationStrategy = Literal["truncate", "smart_truncate", "summarize", "split"]


@dataclass
class SummarizationResult:
    """Result from text summarization."""

    text: str
    was_summarized: bool
    original_length: int
    final_length: int
    strategy_used: SummarizationStrategy | None = None
    chunks: list[str] | None = None  # For split strategy


@dataclass
class SummarizerConfig:
    """Configuration for text summarizer."""

    # Maximum characters for output
    max_chars: int = 4096

    # Maximum audio duration in seconds
    max_duration_seconds: int = MAX_AUDIO_DURATION_SECONDS

    # Strategy to use when text exceeds limits
    strategy: SummarizationStrategy = "smart_truncate"

    # Whether to preserve sentence boundaries
    preserve_sentences: bool = True

    # Ellipsis to append when truncating
    ellipsis: str = "..."

    # Provider-specific limits
    provider_limits: dict[str, int] | None = None


# =============================================================================
# Summarizer Class
# =============================================================================

class TtsSummarizer:
    """Text summarizer for TTS.

    Handles text that is too long for TTS providers by:
    - Truncating at character limits
    - Smart truncation at sentence boundaries
    - Splitting into multiple chunks
    """

    def __init__(self, config: SummarizerConfig | None = None):
        """Initialize summarizer.

        Args:
            config: Summarizer configuration
        """
        self._config = config or SummarizerConfig()

    def get_char_limit(self, provider: str | None = None) -> int:
        """Get character limit for a provider.

        Args:
            provider: Provider name

        Returns:
            Character limit
        """
        if provider and self._config.provider_limits:
            if provider in self._config.provider_limits:
                return self._config.provider_limits[provider]

        if provider and provider in DEFAULT_CHAR_LIMITS:
            return DEFAULT_CHAR_LIMITS[provider]

        return self._config.max_chars

    def estimate_duration(self, text: str) -> float:
        """Estimate audio duration for text.

        Args:
            text: Text to estimate

        Returns:
            Estimated duration in seconds
        """
        return len(text) / CHARS_PER_SECOND

    def needs_summarization(
        self,
        text: str,
        provider: str | None = None,
    ) -> bool:
        """Check if text needs summarization.

        Args:
            text: Text to check
            provider: Provider name

        Returns:
            True if text exceeds limits
        """
        char_limit = self.get_char_limit(provider)
        duration_limit = self._config.max_duration_seconds * CHARS_PER_SECOND

        return len(text) > char_limit or len(text) > duration_limit

    def summarize(
        self,
        text: str,
        provider: str | None = None,
        strategy: SummarizationStrategy | None = None,
    ) -> SummarizationResult:
        """Summarize text if needed.

        Args:
            text: Text to summarize
            provider: Provider name for limit lookup
            strategy: Override strategy

        Returns:
            SummarizationResult with processed text
        """
        original_length = len(text)
        effective_strategy = strategy or self._config.strategy

        # Check if summarization is needed
        if not self.needs_summarization(text, provider):
            return SummarizationResult(
                text=text,
                was_summarized=False,
                original_length=original_length,
                final_length=original_length,
            )

        char_limit = self.get_char_limit(provider)
        duration_limit = self._config.max_duration_seconds * CHARS_PER_SECOND
        effective_limit = min(char_limit, int(duration_limit))

        logger.debug(
            f"Summarizing text: {original_length} chars -> {effective_limit} limit "
            f"(strategy: {effective_strategy})"
        )

        if effective_strategy == "truncate":
            result_text = self._truncate(text, effective_limit)
        elif effective_strategy == "smart_truncate":
            result_text = self._smart_truncate(text, effective_limit)
        elif effective_strategy == "split":
            chunks = self._split(text, effective_limit)
            return SummarizationResult(
                text=chunks[0] if chunks else "",
                was_summarized=True,
                original_length=original_length,
                final_length=len(chunks[0]) if chunks else 0,
                strategy_used=effective_strategy,
                chunks=chunks,
            )
        else:
            # Default to smart truncate
            result_text = self._smart_truncate(text, effective_limit)

        return SummarizationResult(
            text=result_text,
            was_summarized=True,
            original_length=original_length,
            final_length=len(result_text),
            strategy_used=effective_strategy,
        )

    def _truncate(self, text: str, limit: int) -> str:
        """Simple truncation at character limit.

        Args:
            text: Text to truncate
            limit: Character limit

        Returns:
            Truncated text
        """
        ellipsis = self._config.ellipsis
        if len(text) <= limit:
            return text

        return text[: limit - len(ellipsis)] + ellipsis

    def _smart_truncate(self, text: str, limit: int) -> str:
        """Smart truncation at sentence boundaries.

        Args:
            text: Text to truncate
            limit: Character limit

        Returns:
            Truncated text at sentence boundary
        """
        ellipsis = self._config.ellipsis
        if len(text) <= limit:
            return text

        # Reserve space for ellipsis
        effective_limit = limit - len(ellipsis)

        # Find sentence boundaries
        sentence_endings = re.finditer(r'[.!?]+\s+', text[:effective_limit + 50])
        last_boundary = 0

        for match in sentence_endings:
            if match.end() <= effective_limit:
                last_boundary = match.end()
            else:
                break

        # If we found a sentence boundary, use it
        if last_boundary > 0 and last_boundary > effective_limit * 0.5:
            return text[:last_boundary].rstrip() + ellipsis

        # Fall back to word boundary
        word_boundary = text.rfind(' ', 0, effective_limit)
        if word_boundary > effective_limit * 0.5:
            return text[:word_boundary].rstrip() + ellipsis

        # Fall back to simple truncation
        return text[:effective_limit] + ellipsis

    def _split(self, text: str, chunk_size: int) -> list[str]:
        """Split text into chunks at sentence boundaries.

        Args:
            text: Text to split
            chunk_size: Maximum size per chunk

        Returns:
            List of text chunks
        """
        chunks: list[str] = []
        remaining = text

        while remaining:
            if len(remaining) <= chunk_size:
                chunks.append(remaining)
                break

            # Find a good split point
            split_point = self._find_split_point(remaining, chunk_size)
            chunks.append(remaining[:split_point].rstrip())
            remaining = remaining[split_point:].lstrip()

        return chunks

    def _find_split_point(self, text: str, max_length: int) -> int:
        """Find optimal split point in text.

        Args:
            text: Text to split
            max_length: Maximum length for first part

        Returns:
            Index to split at
        """
        if len(text) <= max_length:
            return len(text)

        # Try to find paragraph break
        para_break = text.rfind('\n\n', 0, max_length)
        if para_break > max_length * 0.5:
            return para_break + 2

        # Try to find sentence boundary
        sentence_endings = list(re.finditer(r'[.!?]+\s+', text[:max_length]))
        if sentence_endings:
            last_sentence = sentence_endings[-1]
            if last_sentence.end() > max_length * 0.5:
                return last_sentence.end()

        # Try to find word boundary
        word_boundary = text.rfind(' ', 0, max_length)
        if word_boundary > max_length * 0.5:
            return word_boundary + 1

        # Fall back to hard split
        return max_length


# =============================================================================
# Convenience Functions
# =============================================================================

def summarize_for_tts(
    text: str,
    provider: str | None = None,
    max_chars: int | None = None,
    strategy: SummarizationStrategy = "smart_truncate",
) -> SummarizationResult:
    """Convenience function to summarize text for TTS.

    Args:
        text: Text to summarize
        provider: Provider name
        max_chars: Maximum characters
        strategy: Summarization strategy

    Returns:
        SummarizationResult
    """
    config = SummarizerConfig(
        max_chars=max_chars or 4096,
        strategy=strategy,
    )
    summarizer = TtsSummarizer(config)
    return summarizer.summarize(text, provider=provider)


def estimate_tts_duration(text: str) -> float:
    """Estimate TTS audio duration for text.

    Args:
        text: Text to estimate

    Returns:
        Estimated duration in seconds
    """
    return len(text) / CHARS_PER_SECOND


def split_for_tts(
    text: str,
    chunk_size: int = 4096,
) -> list[str]:
    """Split text into TTS-friendly chunks.

    Args:
        text: Text to split
        chunk_size: Maximum size per chunk

    Returns:
        List of text chunks
    """
    config = SummarizerConfig(
        max_chars=chunk_size,
        strategy="split",
    )
    summarizer = TtsSummarizer(config)
    result = summarizer.summarize(text, strategy="split")
    return result.chunks or [result.text]
