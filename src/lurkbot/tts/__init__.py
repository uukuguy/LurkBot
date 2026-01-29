"""TTS (Text-to-Speech) module for LurkBot.

Provides text-to-speech synthesis capabilities with multiple providers:
- OpenAI TTS (gpt-4o-mini-tts, tts-1, tts-1-hd)
- ElevenLabs TTS
- Edge TTS (free, no API key required)

Ported from MoltBot's TTS implementation.
"""

# Types
from lurkbot.tts.types import (
    DEFAULT_ELEVENLABS_BASE_URL,
    DEFAULT_ELEVENLABS_MODEL_ID,
    DEFAULT_ELEVENLABS_VOICE_ID,
    DEFAULT_ELEVENLABS_VOICE_SETTINGS,
    DEFAULT_OPENAI_MODEL,
    DEFAULT_OPENAI_VOICE,
    DEFAULT_TTS_PROVIDER,
    ElevenLabsVoiceSettings,
    ResolvedEdgeConfig,
    ResolvedElevenLabsConfig,
    ResolvedOpenAIConfig,
    TtsConfig,
    TtsModelOverrideConfig,
    TtsProvider,
    TtsResult,
    TtsUserPrefs,
    TtsUserPrefsData,
)

# Directive Parser
from lurkbot.tts.directive_parser import (
    TtsDirectiveOverrides,
    TtsDirectiveParseResult,
    parse_tts_directives,
)

# User Preferences
from lurkbot.tts.prefs import (
    get_last_tts_attempt,
    get_tts_max_length,
    get_tts_provider,
    is_summarization_enabled,
    is_tts_enabled,
    read_prefs,
    resolve_tts_api_key,
    resolve_tts_auto_mode,
    resolve_tts_prefs_path,
    resolve_tts_provider_order,
    set_last_tts_attempt,
    set_summarization_enabled,
    set_tts_auto_mode,
    set_tts_enabled,
    set_tts_max_length,
    set_tts_provider,
)

# Summarizer
from lurkbot.tts.summarizer import (
    SummarizationResult,
    SummarizerConfig,
    TtsSummarizer,
    estimate_tts_duration,
    split_for_tts,
    summarize_for_tts,
)

# Providers
from lurkbot.tts.providers import (
    EdgeTtsProvider,
    ElevenLabsTtsProvider,
    OpenAITtsProvider,
    TtsProviderBase,
    TtsProviderResult,
)

# Engine
from lurkbot.tts.engine import (
    TtsEngine,
    TtsEngineConfig,
    TtsSynthesisResult,
    create_tts_engine,
    synthesize_text,
)

__all__ = [
    # Types
    "TtsProvider",
    "TtsConfig",
    "TtsModelOverrideConfig",
    "ElevenLabsVoiceSettings",
    "ResolvedOpenAIConfig",
    "ResolvedElevenLabsConfig",
    "ResolvedEdgeConfig",
    "TtsResult",
    "TtsUserPrefs",
    "TtsUserPrefsData",
    "DEFAULT_TTS_PROVIDER",
    "DEFAULT_OPENAI_MODEL",
    "DEFAULT_OPENAI_VOICE",
    "DEFAULT_ELEVENLABS_MODEL_ID",
    "DEFAULT_ELEVENLABS_VOICE_ID",
    "DEFAULT_ELEVENLABS_BASE_URL",
    "DEFAULT_ELEVENLABS_VOICE_SETTINGS",
    # Directive Parser
    "TtsDirectiveOverrides",
    "TtsDirectiveParseResult",
    "parse_tts_directives",
    # User Preferences
    "get_last_tts_attempt",
    "get_tts_max_length",
    "get_tts_provider",
    "is_summarization_enabled",
    "is_tts_enabled",
    "read_prefs",
    "resolve_tts_api_key",
    "resolve_tts_auto_mode",
    "resolve_tts_prefs_path",
    "resolve_tts_provider_order",
    "set_last_tts_attempt",
    "set_summarization_enabled",
    "set_tts_auto_mode",
    "set_tts_enabled",
    "set_tts_max_length",
    "set_tts_provider",
    # Summarizer
    "SummarizationResult",
    "SummarizerConfig",
    "TtsSummarizer",
    "estimate_tts_duration",
    "split_for_tts",
    "summarize_for_tts",
    # Providers
    "TtsProviderBase",
    "TtsProviderResult",
    "OpenAITtsProvider",
    "ElevenLabsTtsProvider",
    "EdgeTtsProvider",
    # Engine
    "TtsEngine",
    "TtsEngineConfig",
    "TtsSynthesisResult",
    "create_tts_engine",
    "synthesize_text",
]