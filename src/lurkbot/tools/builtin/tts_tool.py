"""TTS (Text-to-Speech) tool for voice synthesis.

Ported from moltbot/src/agents/tools/tts-tool.ts

This tool provides text-to-speech capabilities:
- Convert text to speech audio
- Multiple provider support (OpenAI, ElevenLabs, Edge TTS)
- Voice selection and customization
- Directive parsing for embedded TTS commands

MoltBot uses [[tts:...]] directives in responses to trigger speech.
"""

from __future__ import annotations

import base64
import io
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from lurkbot.tools.builtin.common import (
    ToolResult,
    ToolResultContent,
    ToolResultContentType,
    error_result,
    json_result,
    text_result,
)


# =============================================================================
# Type Definitions
# =============================================================================


class TTSProvider(str):
    """TTS provider identifiers."""

    OPENAI = "openai"
    ELEVENLABS = "elevenlabs"
    EDGE = "edge"
    LOCAL = "local"


class TTSVoice(BaseModel):
    """Voice configuration for TTS."""

    id: str
    name: str | None = None
    provider: str | None = None
    language: str | None = None
    gender: Literal["male", "female", "neutral"] | None = None


class TTSParams(BaseModel):
    """Parameters for TTS tool.

    Matches moltbot TTS tool schema.
    """

    op: Literal["speak", "voices", "providers", "parse"]

    # For speak operation
    text: str | None = None
    voice: str | None = None
    provider: str | None = None
    speed: float | None = None  # 0.25 to 4.0
    pitch: float | None = None  # -20 to 20 (semitones)
    output_format: Literal["mp3", "wav", "ogg", "opus"] | None = Field(
        default=None, alias="outputFormat"
    )
    output_path: str | None = Field(default=None, alias="outputPath")

    # For parse operation (extract TTS directives from text)
    input_text: str | None = Field(default=None, alias="inputText")

    class Config:
        populate_by_name = True


class TTSResult(BaseModel):
    """Result of TTS operation."""

    success: bool
    audio_base64: str | None = Field(default=None, alias="audioBase64")
    audio_path: str | None = Field(default=None, alias="audioPath")
    format: str | None = None
    duration_ms: int | None = Field(default=None, alias="durationMs")
    bytes: int | None = None
    voice_used: str | None = Field(default=None, alias="voiceUsed")
    provider_used: str | None = Field(default=None, alias="providerUsed")
    error: str | None = None

    class Config:
        populate_by_name = True


class TTSDirective(BaseModel):
    """Parsed TTS directive from text."""

    text: str
    voice: str | None = None
    speed: float | None = None
    pitch: float | None = None
    emotion: str | None = None


# =============================================================================
# TTS Configuration
# =============================================================================


class TTSConfig(BaseModel):
    """Configuration for TTS tool."""

    # Default provider
    default_provider: str = Field(default="openai", alias="defaultProvider")

    # Provider-specific settings
    openai_api_key: str | None = Field(default=None, alias="openaiApiKey")
    openai_model: str = Field(default="tts-1", alias="openaiModel")
    openai_voice: str = Field(default="alloy", alias="openaiVoice")

    elevenlabs_api_key: str | None = Field(default=None, alias="elevenlabsApiKey")
    elevenlabs_voice_id: str | None = Field(default=None, alias="elevenlabsVoiceId")

    # Edge TTS (free, no API key needed)
    edge_voice: str = Field(default="en-US-JennyNeural", alias="edgeVoice")

    # Output settings
    default_format: str = Field(default="mp3", alias="defaultFormat")
    output_dir: str | None = Field(default=None, alias="outputDir")

    class Config:
        populate_by_name = True


_config: TTSConfig | None = None


def get_tts_config() -> TTSConfig:
    """Get the global TTS configuration."""
    global _config
    if _config is None:
        _config = TTSConfig()
    return _config


def configure_tts(config: TTSConfig) -> None:
    """Configure the TTS tool."""
    global _config
    _config = config


# =============================================================================
# Voice Definitions
# =============================================================================

# OpenAI voices
OPENAI_VOICES = [
    TTSVoice(id="alloy", name="Alloy", provider="openai", gender="neutral"),
    TTSVoice(id="echo", name="Echo", provider="openai", gender="male"),
    TTSVoice(id="fable", name="Fable", provider="openai", gender="neutral"),
    TTSVoice(id="onyx", name="Onyx", provider="openai", gender="male"),
    TTSVoice(id="nova", name="Nova", provider="openai", gender="female"),
    TTSVoice(id="shimmer", name="Shimmer", provider="openai", gender="female"),
]

# Edge TTS popular voices
EDGE_VOICES = [
    TTSVoice(
        id="en-US-JennyNeural",
        name="Jenny",
        provider="edge",
        language="en-US",
        gender="female",
    ),
    TTSVoice(
        id="en-US-GuyNeural",
        name="Guy",
        provider="edge",
        language="en-US",
        gender="male",
    ),
    TTSVoice(
        id="en-GB-SoniaNeural",
        name="Sonia",
        provider="edge",
        language="en-GB",
        gender="female",
    ),
    TTSVoice(
        id="zh-CN-XiaoxiaoNeural",
        name="Xiaoxiao",
        provider="edge",
        language="zh-CN",
        gender="female",
    ),
    TTSVoice(
        id="zh-CN-YunxiNeural",
        name="Yunxi",
        provider="edge",
        language="zh-CN",
        gender="male",
    ),
    TTSVoice(
        id="ja-JP-NanamiNeural",
        name="Nanami",
        provider="edge",
        language="ja-JP",
        gender="female",
    ),
]


# =============================================================================
# TTS Tool Implementation
# =============================================================================


async def tts_tool(params: dict[str, Any]) -> ToolResult:
    """Execute TTS tool operations.

    Args:
        params: Tool parameters containing 'op' and operation-specific fields

    Returns:
        ToolResult with operation result or error
    """
    try:
        tts_params = TTSParams.model_validate(params)
    except Exception as e:
        return error_result(f"Invalid parameters: {e}")

    config = get_tts_config()

    match tts_params.op:
        case "speak":
            return await _tts_speak(tts_params, config)
        case "voices":
            return _tts_voices(tts_params, config)
        case "providers":
            return _tts_providers(config)
        case "parse":
            return _tts_parse(tts_params)
        case _:
            return error_result(f"Unknown operation: {tts_params.op}")


async def _tts_speak(params: TTSParams, config: TTSConfig) -> ToolResult:
    """Convert text to speech audio."""
    if not params.text:
        return error_result("Missing required field: text")

    provider = params.provider or config.default_provider
    voice = params.voice
    speed = params.speed or 1.0
    output_format = params.output_format or config.default_format

    try:
        match provider:
            case "openai":
                return await _speak_openai(params, config)
            case "elevenlabs":
                return await _speak_elevenlabs(params, config)
            case "edge":
                return await _speak_edge(params, config)
            case _:
                return error_result(f"Unknown provider: {provider}")
    except Exception as e:
        return json_result(
            TTSResult(
                success=False,
                error=str(e),
            ).model_dump(by_alias=True, exclude_none=True)
        )


async def _speak_openai(params: TTSParams, config: TTSConfig) -> ToolResult:
    """Generate speech using OpenAI TTS API."""
    try:
        from openai import AsyncOpenAI
    except ImportError:
        return error_result("openai package not installed. Install with: pip install openai")

    if not config.openai_api_key:
        return error_result("OpenAI API key not configured")

    client = AsyncOpenAI(api_key=config.openai_api_key)

    voice = params.voice or config.openai_voice
    speed = params.speed or 1.0
    output_format = params.output_format or "mp3"

    # Map format to OpenAI response format
    response_format = output_format
    if response_format == "wav":
        response_format = "wav"
    elif response_format == "ogg":
        response_format = "opus"

    try:
        response = await client.audio.speech.create(
            model=config.openai_model,
            voice=voice,
            input=params.text,
            speed=speed,
            response_format=response_format,
        )

        audio_bytes = response.content

        # Save to file if output_path specified
        audio_path = None
        if params.output_path:
            path = Path(params.output_path)
            path.write_bytes(audio_bytes)
            audio_path = str(path)

        return json_result(
            TTSResult(
                success=True,
                audioBase64=base64.b64encode(audio_bytes).decode("utf-8"),
                audioPath=audio_path,
                format=output_format,
                bytes=len(audio_bytes),
                voiceUsed=voice,
                providerUsed="openai",
            ).model_dump(by_alias=True, exclude_none=True)
        )

    except Exception as e:
        return json_result(
            TTSResult(
                success=False,
                error=str(e),
                providerUsed="openai",
            ).model_dump(by_alias=True, exclude_none=True)
        )


async def _speak_elevenlabs(params: TTSParams, config: TTSConfig) -> ToolResult:
    """Generate speech using ElevenLabs API."""
    # TODO: Implement ElevenLabs integration
    return json_result(
        TTSResult(
            success=False,
            error="ElevenLabs provider not yet implemented",
            providerUsed="elevenlabs",
        ).model_dump(by_alias=True, exclude_none=True)
    )


async def _speak_edge(params: TTSParams, config: TTSConfig) -> ToolResult:
    """Generate speech using Edge TTS (free, no API key).

    Edge TTS uses Microsoft's online TTS service.
    """
    try:
        import edge_tts
    except ImportError:
        return error_result(
            "edge-tts package not installed. Install with: pip install edge-tts"
        )

    voice = params.voice or config.edge_voice
    speed = params.speed or 1.0
    output_format = params.output_format or "mp3"

    # Edge TTS speed is expressed as percentage (+50% = 1.5x)
    rate_str = f"+{int((speed - 1) * 100)}%" if speed >= 1 else f"{int((speed - 1) * 100)}%"

    try:
        communicate = edge_tts.Communicate(
            text=params.text,
            voice=voice,
            rate=rate_str,
        )

        # Collect audio data
        audio_data = io.BytesIO()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data.write(chunk["data"])

        audio_bytes = audio_data.getvalue()

        # Save to file if output_path specified
        audio_path = None
        if params.output_path:
            path = Path(params.output_path)
            path.write_bytes(audio_bytes)
            audio_path = str(path)

        return json_result(
            TTSResult(
                success=True,
                audioBase64=base64.b64encode(audio_bytes).decode("utf-8"),
                audioPath=audio_path,
                format=output_format,
                bytes=len(audio_bytes),
                voiceUsed=voice,
                providerUsed="edge",
            ).model_dump(by_alias=True, exclude_none=True)
        )

    except Exception as e:
        return json_result(
            TTSResult(
                success=False,
                error=str(e),
                providerUsed="edge",
            ).model_dump(by_alias=True, exclude_none=True)
        )


def _tts_voices(params: TTSParams, config: TTSConfig) -> ToolResult:
    """List available voices for a provider."""
    provider = params.provider or config.default_provider

    match provider:
        case "openai":
            voices = OPENAI_VOICES
        case "edge":
            voices = EDGE_VOICES
        case _:
            voices = []

    return json_result(
        {
            "provider": provider,
            "voices": [v.model_dump(exclude_none=True) for v in voices],
            "count": len(voices),
        }
    )


def _tts_providers(config: TTSConfig) -> ToolResult:
    """List available TTS providers."""
    providers = [
        {
            "id": "openai",
            "name": "OpenAI TTS",
            "requiresApiKey": True,
            "configured": config.openai_api_key is not None,
        },
        {
            "id": "elevenlabs",
            "name": "ElevenLabs",
            "requiresApiKey": True,
            "configured": config.elevenlabs_api_key is not None,
        },
        {
            "id": "edge",
            "name": "Edge TTS (Microsoft)",
            "requiresApiKey": False,
            "configured": True,  # Always available
        },
    ]

    return json_result(
        {
            "providers": providers,
            "default": config.default_provider,
        }
    )


def _tts_parse(params: TTSParams) -> ToolResult:
    """Parse TTS directives from text.

    MoltBot uses [[tts:...]] directives in responses, e.g.:
    - [[tts:Hello world]]
    - [[tts:voice=nova|Hello world]]
    - [[tts:speed=1.2|voice=alloy|Hello world]]
    """
    import re

    input_text = params.input_text or params.text
    if not input_text:
        return error_result("Missing required field: inputText or text")

    # Pattern for [[tts:...]] directives
    pattern = r"\[\[tts:([^\]]+)\]\]"

    directives: list[dict[str, Any]] = []
    for match in re.finditer(pattern, input_text):
        content = match.group(1)

        # Parse parameters if present (format: key=value|key=value|text)
        parts = content.split("|")
        directive = TTSDirective(text=parts[-1])  # Last part is always the text

        for part in parts[:-1]:
            if "=" in part:
                key, value = part.split("=", 1)
                key = key.strip().lower()
                value = value.strip()

                if key == "voice":
                    directive.voice = value
                elif key == "speed":
                    try:
                        directive.speed = float(value)
                    except ValueError:
                        pass
                elif key == "pitch":
                    try:
                        directive.pitch = float(value)
                    except ValueError:
                        pass
                elif key == "emotion":
                    directive.emotion = value

        directives.append(directive.model_dump(exclude_none=True))

    # Also return text with directives removed
    clean_text = re.sub(pattern, "", input_text).strip()

    return json_result(
        {
            "directives": directives,
            "count": len(directives),
            "cleanText": clean_text,
        }
    )


# =============================================================================
# Tool Factory Function
# =============================================================================


def create_tts_tool() -> tuple[str, str, dict[str, Any], Any]:
    """Create the TTS tool definition.

    Returns:
        Tuple of (name, description, schema, handler)
    """
    name = "tts"
    description = """Text-to-speech synthesis.

Operations:
- speak: Convert text to speech audio
- voices: List available voices for a provider
- providers: List available TTS providers
- parse: Parse [[tts:...]] directives from text

Providers:
- openai: OpenAI TTS (requires API key)
- elevenlabs: ElevenLabs (requires API key)
- edge: Microsoft Edge TTS (free, no API key)

Examples:
- Generate speech: {"op": "speak", "text": "Hello world", "voice": "alloy"}
- List voices: {"op": "voices", "provider": "openai"}
- Parse directives: {"op": "parse", "inputText": "Here is a message [[tts:Hello!]]"}"""

    schema = {
        "type": "object",
        "properties": {
            "op": {
                "type": "string",
                "enum": ["speak", "voices", "providers", "parse"],
                "description": "Operation to perform",
            },
            "text": {
                "type": "string",
                "description": "Text to convert to speech",
            },
            "voice": {
                "type": "string",
                "description": "Voice ID to use",
            },
            "provider": {
                "type": "string",
                "enum": ["openai", "elevenlabs", "edge"],
                "description": "TTS provider to use",
            },
            "speed": {
                "type": "number",
                "minimum": 0.25,
                "maximum": 4.0,
                "description": "Speech speed (0.25 to 4.0)",
            },
            "pitch": {
                "type": "number",
                "description": "Pitch adjustment in semitones",
            },
            "outputFormat": {
                "type": "string",
                "enum": ["mp3", "wav", "ogg", "opus"],
                "description": "Output audio format",
            },
            "outputPath": {
                "type": "string",
                "description": "Path to save audio file",
            },
            "inputText": {
                "type": "string",
                "description": "Text containing TTS directives to parse",
            },
        },
        "required": ["op"],
    }

    return name, description, schema, tts_tool
