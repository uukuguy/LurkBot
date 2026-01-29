"""TTS directive parser.

Ported from moltbot/src/tts/tts.ts (parseTtsDirectives)

Parses [[tts:...]] directives from text to extract TTS configuration overrides.

Directive formats:
- Block directive: [[tts:text]]<expressive text>[[/tts:text]]
- Inline directive: [[tts:provider=openai voice=nova model=tts-1]]

Supported parameters:
- provider: openai, elevenlabs, edge
- voice/voiceId: Voice identifier
- model/modelId: Model identifier
- stability, similarityBoost, style, speed, useSpeakerBoost: Voice settings
- applyTextNormalization: auto|on|off
- languageCode: ISO 639-1 code (e.g., en, de)
- seed: Integer 0-4294967295
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from lurkbot.tts.types import (
    OPENAI_TTS_MODELS,
    OPENAI_TTS_VOICES,
    ElevenLabsOverrides,
    OpenAIOverrides,
    TtsDirectiveOverrides,
    TtsDirectiveParseResult,
    TtsModelOverrideConfig,
    TtsProvider,
)


# =============================================================================
# Validation Helpers
# =============================================================================

def is_valid_voice_id(voice_id: str) -> bool:
    """Check if a string is a valid ElevenLabs voice ID."""
    return bool(re.match(r"^[a-zA-Z0-9]{10,40}$", voice_id))


def is_valid_openai_model(model: str, custom_endpoint: bool = False) -> bool:
    """Check if a string is a valid OpenAI TTS model."""
    if custom_endpoint:
        return True
    return model in OPENAI_TTS_MODELS


def is_valid_openai_voice(voice: str, custom_endpoint: bool = False) -> bool:
    """Check if a string is a valid OpenAI TTS voice."""
    if custom_endpoint:
        return True
    return voice in OPENAI_TTS_VOICES


def normalize_language_code(code: str | None) -> str | None:
    """Normalize and validate a language code."""
    if not code:
        return None
    trimmed = code.strip().lower()
    if not re.match(r"^[a-z]{2}$", trimmed):
        raise ValueError(
            "languageCode must be a 2-letter ISO 639-1 code (e.g. en, de, fr)"
        )
    return trimmed


def normalize_apply_text_normalization(
    mode: str | None,
) -> str | None:
    """Normalize text normalization mode."""
    if not mode:
        return None
    trimmed = mode.strip().lower()
    if trimmed in ("auto", "on", "off"):
        return trimmed
    raise ValueError("applyTextNormalization must be one of: auto, on, off")


def normalize_seed(seed: int | None) -> int | None:
    """Normalize and validate a seed value."""
    if seed is None:
        return None
    if not isinstance(seed, (int, float)):
        return None
    next_seed = int(seed)
    if next_seed < 0 or next_seed > 4_294_967_295:
        raise ValueError("seed must be between 0 and 4294967295")
    return next_seed


def parse_boolean_value(value: str) -> bool | None:
    """Parse a boolean value from string."""
    normalized = value.strip().lower()
    if normalized in ("true", "1", "yes", "on"):
        return True
    if normalized in ("false", "0", "no", "off"):
        return False
    return None


def parse_number_value(value: str) -> float | None:
    """Parse a number value from string."""
    try:
        return float(value)
    except ValueError:
        return None


def require_in_range(value: float, min_val: float, max_val: float, label: str) -> None:
    """Validate that a value is within a range."""
    if not isinstance(value, (int, float)) or value < min_val or value > max_val:
        raise ValueError(f"{label} must be between {min_val} and {max_val}")


# =============================================================================
# Directive Parser
# =============================================================================

def parse_tts_directives(
    text: str,
    policy: TtsModelOverrideConfig | None = None,
    custom_openai_endpoint: bool = False,
) -> TtsDirectiveParseResult:
    """Parse TTS directives from text.

    Args:
        text: Input text containing potential TTS directives
        policy: Override policy controlling which directives are allowed
        custom_openai_endpoint: Whether using a custom OpenAI-compatible endpoint

    Returns:
        TtsDirectiveParseResult with cleaned text and parsed overrides
    """
    if policy is None:
        policy = TtsModelOverrideConfig()

    if not policy.enabled:
        return TtsDirectiveParseResult(
            cleaned_text=text,
            has_directive=False,
            overrides=TtsDirectiveOverrides(),
            warnings=[],
        )

    overrides = TtsDirectiveOverrides()
    warnings: list[str] = []
    cleaned_text = text
    has_directive = False

    # Parse block directives: [[tts:text]]...[[/tts:text]]
    block_regex = re.compile(
        r"\[\[tts:text\]\]([\s\S]*?)\[\[/tts:text\]\]", re.IGNORECASE
    )

    def block_replacer(match: re.Match) -> str:
        nonlocal has_directive, overrides
        has_directive = True
        if policy.allow_text and overrides.tts_text is None:
            overrides.tts_text = match.group(1).strip()
        return ""

    cleaned_text = block_regex.sub(block_replacer, cleaned_text)

    # Parse inline directives: [[tts:key=value key2=value2]]
    directive_regex = re.compile(r"\[\[tts:([^\]]+)\]\]", re.IGNORECASE)

    def directive_replacer(match: re.Match) -> str:
        nonlocal has_directive, overrides, warnings
        has_directive = True
        body = match.group(1)
        tokens = body.split()

        for token in tokens:
            eq_index = token.find("=")
            if eq_index == -1:
                continue

            raw_key = token[:eq_index].strip()
            raw_value = token[eq_index + 1 :].strip()
            if not raw_key or not raw_value:
                continue

            key = raw_key.lower()

            try:
                _process_directive_token(
                    key,
                    raw_value,
                    policy,
                    overrides,
                    warnings,
                    custom_openai_endpoint,
                )
            except ValueError as e:
                warnings.append(str(e))

        return ""

    cleaned_text = directive_regex.sub(directive_replacer, cleaned_text)

    return TtsDirectiveParseResult(
        cleaned_text=cleaned_text,
        tts_text=overrides.tts_text,
        has_directive=has_directive,
        overrides=overrides,
        warnings=warnings,
    )


def _process_directive_token(
    key: str,
    value: str,
    policy: TtsModelOverrideConfig,
    overrides: TtsDirectiveOverrides,
    warnings: list[str],
    custom_openai_endpoint: bool,
) -> None:
    """Process a single directive token."""
    # Provider
    if key == "provider":
        if not policy.allow_provider:
            return
        if value in ("openai", "elevenlabs", "edge"):
            overrides.provider = value  # type: ignore[assignment]
        else:
            warnings.append(f'unsupported provider "{value}"')
        return

    # OpenAI voice
    if key in ("voice", "openai_voice", "openaivoice"):
        if not policy.allow_voice:
            return
        if is_valid_openai_voice(value, custom_openai_endpoint):
            if overrides.openai is None:
                overrides.openai = OpenAIOverrides()
            overrides.openai.voice = value
        else:
            warnings.append(f'invalid OpenAI voice "{value}"')
        return

    # ElevenLabs voice
    if key in ("voiceid", "voice_id", "elevenlabs_voice", "elevenlabsvoice"):
        if not policy.allow_voice:
            return
        if is_valid_voice_id(value):
            if overrides.elevenlabs is None:
                overrides.elevenlabs = ElevenLabsOverrides()
            overrides.elevenlabs.voice_id = value
        else:
            warnings.append(f'invalid ElevenLabs voiceId "{value}"')
        return

    # Model
    if key in (
        "model",
        "modelid",
        "model_id",
        "elevenlabs_model",
        "elevenlabsmodel",
        "openai_model",
        "openaimodel",
    ):
        if not policy.allow_model_id:
            return
        if is_valid_openai_model(value, custom_openai_endpoint):
            if overrides.openai is None:
                overrides.openai = OpenAIOverrides()
            overrides.openai.model = value
        else:
            if overrides.elevenlabs is None:
                overrides.elevenlabs = ElevenLabsOverrides()
            overrides.elevenlabs.model_id = value
        return

    # Voice settings: stability
    if key == "stability":
        if not policy.allow_voice_settings:
            return
        num = parse_number_value(value)
        if num is None:
            warnings.append("invalid stability value")
            return
        require_in_range(num, 0, 1, "stability")
        if overrides.elevenlabs is None:
            overrides.elevenlabs = ElevenLabsOverrides()
        if overrides.elevenlabs.voice_settings is None:
            overrides.elevenlabs.voice_settings = {}
        overrides.elevenlabs.voice_settings["stability"] = num
        return

    # Voice settings: similarityBoost
    if key in ("similarity", "similarityboost", "similarity_boost"):
        if not policy.allow_voice_settings:
            return
        num = parse_number_value(value)
        if num is None:
            warnings.append("invalid similarityBoost value")
            return
        require_in_range(num, 0, 1, "similarityBoost")
        if overrides.elevenlabs is None:
            overrides.elevenlabs = ElevenLabsOverrides()
        if overrides.elevenlabs.voice_settings is None:
            overrides.elevenlabs.voice_settings = {}
        overrides.elevenlabs.voice_settings["similarity_boost"] = num
        return

    # Voice settings: style
    if key == "style":
        if not policy.allow_voice_settings:
            return
        num = parse_number_value(value)
        if num is None:
            warnings.append("invalid style value")
            return
        require_in_range(num, 0, 1, "style")
        if overrides.elevenlabs is None:
            overrides.elevenlabs = ElevenLabsOverrides()
        if overrides.elevenlabs.voice_settings is None:
            overrides.elevenlabs.voice_settings = {}
        overrides.elevenlabs.voice_settings["style"] = num
        return

    # Voice settings: speed
    if key == "speed":
        if not policy.allow_voice_settings:
            return
        num = parse_number_value(value)
        if num is None:
            warnings.append("invalid speed value")
            return
        require_in_range(num, 0.5, 2, "speed")
        if overrides.elevenlabs is None:
            overrides.elevenlabs = ElevenLabsOverrides()
        if overrides.elevenlabs.voice_settings is None:
            overrides.elevenlabs.voice_settings = {}
        overrides.elevenlabs.voice_settings["speed"] = num
        return

    # Voice settings: useSpeakerBoost
    if key in ("speakerboost", "speaker_boost", "usespeakerboost", "use_speaker_boost"):
        if not policy.allow_voice_settings:
            return
        bool_val = parse_boolean_value(value)
        if bool_val is None:
            warnings.append("invalid useSpeakerBoost value")
            return
        if overrides.elevenlabs is None:
            overrides.elevenlabs = ElevenLabsOverrides()
        if overrides.elevenlabs.voice_settings is None:
            overrides.elevenlabs.voice_settings = {}
        overrides.elevenlabs.voice_settings["use_speaker_boost"] = bool_val
        return

    # Text normalization
    if key in ("normalize", "applytextnormalization", "apply_text_normalization"):
        if not policy.allow_normalization:
            return
        if overrides.elevenlabs is None:
            overrides.elevenlabs = ElevenLabsOverrides()
        overrides.elevenlabs.apply_text_normalization = normalize_apply_text_normalization(value)  # type: ignore[assignment]
        return

    # Language code
    if key in ("language", "languagecode", "language_code"):
        if not policy.allow_normalization:
            return
        if overrides.elevenlabs is None:
            overrides.elevenlabs = ElevenLabsOverrides()
        overrides.elevenlabs.language_code = normalize_language_code(value)
        return

    # Seed
    if key == "seed":
        if not policy.allow_seed:
            return
        try:
            seed_val = int(value)
            if overrides.elevenlabs is None:
                overrides.elevenlabs = ElevenLabsOverrides()
            overrides.elevenlabs.seed = normalize_seed(seed_val)
        except ValueError:
            warnings.append("invalid seed value")
        return
