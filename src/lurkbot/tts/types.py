"""TTS type definitions.

Ported from moltbot/src/config/types.tts.ts and moltbot/src/tts/tts.ts
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


# =============================================================================
# Core Type Aliases
# =============================================================================

TtsProvider = Literal["openai", "elevenlabs", "edge"]
TtsMode = Literal["final", "all"]
TtsAutoMode = Literal["off", "always", "inbound", "tagged"]

TTS_AUTO_MODES: set[str] = {"off", "always", "inbound", "tagged"}
TTS_PROVIDERS: list[TtsProvider] = ["openai", "elevenlabs", "edge"]


# =============================================================================
# Constants (matching MoltBot defaults)
# =============================================================================

DEFAULT_TTS_PROVIDER: TtsProvider = "edge"
DEFAULT_TIMEOUT_MS = 30_000
DEFAULT_TTS_MAX_LENGTH = 1500
DEFAULT_TTS_SUMMARIZE = True
DEFAULT_MAX_TEXT_LENGTH = 4096
TEMP_FILE_CLEANUP_DELAY_S = 5 * 60  # 5 minutes

DEFAULT_ELEVENLABS_BASE_URL = "https://api.elevenlabs.io"
DEFAULT_ELEVENLABS_VOICE_ID = "pMsXgVXv3BLzUgSXRplE"
DEFAULT_ELEVENLABS_MODEL_ID = "eleven_multilingual_v2"
DEFAULT_OPENAI_MODEL = "gpt-4o-mini-tts"
DEFAULT_OPENAI_VOICE = "alloy"
DEFAULT_EDGE_VOICE = "en-US-MichelleNeural"
DEFAULT_EDGE_LANG = "en-US"
DEFAULT_EDGE_OUTPUT_FORMAT = "audio-24khz-48kbitrate-mono-mp3"

DEFAULT_ELEVENLABS_VOICE_SETTINGS = {
    "stability": 0.5,
    "similarity_boost": 0.75,
    "style": 0.0,
    "use_speaker_boost": True,
    "speed": 1.0,
}

OPENAI_TTS_MODELS: list[str] = ["gpt-4o-mini-tts", "tts-1", "tts-1-hd"]
OPENAI_TTS_VOICES: list[str] = [
    "alloy", "ash", "coral", "echo", "fable", "onyx", "nova", "sage", "shimmer",
]

# Channel-specific output formats
TELEGRAM_OUTPUT = {
    "openai": "opus",
    "elevenlabs": "opus_48000_64",
    "extension": ".opus",
    "voice_compatible": True,
}

DEFAULT_OUTPUT = {
    "openai": "mp3",
    "elevenlabs": "mp3_44100_128",
    "extension": ".mp3",
    "voice_compatible": False,
}

TELEPHONY_OUTPUT = {
    "openai": {"format": "pcm", "sample_rate": 24000},
    "elevenlabs": {"format": "pcm_22050", "sample_rate": 22050},
}


# =============================================================================
# Model Override Policy
# =============================================================================

@dataclass
class TtsModelOverrideConfig:
    """Configuration for model-provided TTS overrides."""

    enabled: bool = True
    allow_text: bool = True
    allow_provider: bool = True
    allow_voice: bool = True
    allow_model_id: bool = True
    allow_voice_settings: bool = True
    allow_normalization: bool = True
    allow_seed: bool = True


# =============================================================================
# ElevenLabs Voice Settings
# =============================================================================

@dataclass
class ElevenLabsVoiceSettings:
    """ElevenLabs voice settings."""

    stability: float = 0.5
    similarity_boost: float = 0.75
    style: float = 0.0
    use_speaker_boost: bool = True
    speed: float = 1.0


# =============================================================================
# Provider Configs (Raw from config file)
# =============================================================================

@dataclass
class ElevenLabsConfig:
    """Raw ElevenLabs configuration from config file."""

    api_key: str | None = None
    base_url: str | None = None
    voice_id: str | None = None
    model_id: str | None = None
    seed: int | None = None
    apply_text_normalization: Literal["auto", "on", "off"] | None = None
    language_code: str | None = None
    voice_settings: dict | None = None


@dataclass
class OpenAITtsConfig:
    """Raw OpenAI TTS configuration from config file."""

    api_key: str | None = None
    model: str | None = None
    voice: str | None = None


@dataclass
class EdgeTtsConfig:
    """Raw Edge TTS configuration from config file."""

    enabled: bool | None = None
    voice: str | None = None
    lang: str | None = None
    output_format: str | None = None
    pitch: str | None = None
    rate: str | None = None
    volume: str | None = None
    save_subtitles: bool = False
    proxy: str | None = None
    timeout_ms: int | None = None


# =============================================================================
# TTS Config (Raw from config file)
# =============================================================================

@dataclass
class TtsConfig:
    """Raw TTS configuration from config file.

    Matches MoltBot TtsConfig type.
    """

    auto: TtsAutoMode | None = None
    enabled: bool | None = None  # Legacy
    mode: TtsMode | None = None
    provider: TtsProvider | None = None
    summary_model: str | None = None
    model_overrides: TtsModelOverrideConfig | None = None
    elevenlabs: ElevenLabsConfig | None = None
    openai: OpenAITtsConfig | None = None
    edge: EdgeTtsConfig | None = None
    prefs_path: str | None = None
    max_text_length: int | None = None
    timeout_ms: int | None = None


# =============================================================================
# Resolved Configs (Fully resolved with defaults)
# =============================================================================

@dataclass
class ResolvedElevenLabsConfig:
    """Fully resolved ElevenLabs configuration."""

    api_key: str | None = None
    base_url: str = DEFAULT_ELEVENLABS_BASE_URL
    voice_id: str = DEFAULT_ELEVENLABS_VOICE_ID
    model_id: str = DEFAULT_ELEVENLABS_MODEL_ID
    seed: int | None = None
    apply_text_normalization: Literal["auto", "on", "off"] | None = None
    language_code: str | None = None
    voice_settings: ElevenLabsVoiceSettings = field(
        default_factory=ElevenLabsVoiceSettings
    )


@dataclass
class ResolvedOpenAIConfig:
    """Fully resolved OpenAI TTS configuration."""

    api_key: str | None = None
    model: str = DEFAULT_OPENAI_MODEL
    voice: str = DEFAULT_OPENAI_VOICE


@dataclass
class ResolvedEdgeConfig:
    """Fully resolved Edge TTS configuration."""

    enabled: bool = True
    voice: str = DEFAULT_EDGE_VOICE
    lang: str = DEFAULT_EDGE_LANG
    output_format: str = DEFAULT_EDGE_OUTPUT_FORMAT
    output_format_configured: bool = False
    pitch: str | None = None
    rate: str | None = None
    volume: str | None = None
    save_subtitles: bool = False
    proxy: str | None = None
    timeout_ms: int | None = None


@dataclass
class ResolvedTtsConfig:
    """Fully resolved TTS configuration with all defaults applied.

    Matches MoltBot ResolvedTtsConfig type.
    """

    auto: TtsAutoMode = "off"
    mode: TtsMode = "final"
    provider: TtsProvider = "edge"
    provider_source: Literal["config", "default"] = "default"
    summary_model: str | None = None
    model_overrides: TtsModelOverrideConfig = field(
        default_factory=TtsModelOverrideConfig
    )
    elevenlabs: ResolvedElevenLabsConfig = field(
        default_factory=ResolvedElevenLabsConfig
    )
    openai: ResolvedOpenAIConfig = field(default_factory=ResolvedOpenAIConfig)
    edge: ResolvedEdgeConfig = field(default_factory=ResolvedEdgeConfig)
    prefs_path: str | None = None
    max_text_length: int = DEFAULT_MAX_TEXT_LENGTH
    timeout_ms: int = DEFAULT_TIMEOUT_MS


# =============================================================================
# Directive Overrides
# =============================================================================

@dataclass
class OpenAIOverrides:
    """OpenAI-specific overrides from directives."""

    voice: str | None = None
    model: str | None = None


@dataclass
class ElevenLabsOverrides:
    """ElevenLabs-specific overrides from directives."""

    voice_id: str | None = None
    model_id: str | None = None
    seed: int | None = None
    apply_text_normalization: Literal["auto", "on", "off"] | None = None
    language_code: str | None = None
    voice_settings: dict | None = None


@dataclass
class TtsDirectiveOverrides:
    """Overrides parsed from [[tts:...]] directives."""

    tts_text: str | None = None
    provider: TtsProvider | None = None
    openai: OpenAIOverrides | None = None
    elevenlabs: ElevenLabsOverrides | None = None


@dataclass
class TtsDirectiveParseResult:
    """Result of parsing TTS directives from text."""

    cleaned_text: str
    tts_text: str | None = None
    has_directive: bool = False
    overrides: TtsDirectiveOverrides = field(default_factory=TtsDirectiveOverrides)
    warnings: list[str] = field(default_factory=list)


# =============================================================================
# TTS Results
# =============================================================================

@dataclass
class TtsResult:
    """Result of TTS conversion."""

    success: bool
    audio_path: str | None = None
    error: str | None = None
    latency_ms: int | None = None
    provider: str | None = None
    output_format: str | None = None
    voice_compatible: bool | None = None


@dataclass
class TtsTelephonyResult:
    """Result of telephony TTS conversion."""

    success: bool
    audio_buffer: bytes | None = None
    error: str | None = None
    latency_ms: int | None = None
    provider: str | None = None
    output_format: str | None = None
    sample_rate: int | None = None


# =============================================================================
# TTS Status Entry (for tracking last attempt)
# =============================================================================

@dataclass
class TtsStatusEntry:
    """Status of the last TTS attempt."""

    timestamp: float
    success: bool
    text_length: int
    summarized: bool
    provider: str | None = None
    latency_ms: int | None = None
    error: str | None = None


# =============================================================================
# User Preferences
# =============================================================================

@dataclass
class TtsUserPrefsData:
    """TTS section of user preferences."""

    auto: TtsAutoMode | None = None
    enabled: bool | None = None  # Legacy
    provider: TtsProvider | None = None
    max_length: int | None = None
    summarize: bool | None = None


@dataclass
class TtsUserPrefs:
    """User preferences file structure."""

    tts: TtsUserPrefsData | None = None


# =============================================================================
# Summarize Result
# =============================================================================

@dataclass
class SummarizeResult:
    """Result of text summarization."""

    summary: str
    latency_ms: int
    input_length: int
    output_length: int
