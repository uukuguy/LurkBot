"""TTS user preferences management.

Ported from moltbot/src/tts/tts.ts (readPrefs, updatePrefs, etc.)

Handles atomic read/write of user TTS preferences stored in a JSON file.
"""

from __future__ import annotations

import json
import os
import random
import time
from pathlib import Path

from loguru import logger

from lurkbot.tts.types import (
    TTS_AUTO_MODES,
    DEFAULT_TTS_MAX_LENGTH,
    DEFAULT_TTS_SUMMARIZE,
    TtsAutoMode,
    TtsProvider,
    TtsUserPrefs,
    TtsUserPrefsData,
)


# =============================================================================
# Normalize Helpers
# =============================================================================

def normalize_tts_auto_mode(value: str | None) -> TtsAutoMode | None:
    """Normalize a string to a valid TtsAutoMode."""
    if not value or not isinstance(value, str):
        return None
    normalized = value.strip().lower()
    if normalized in TTS_AUTO_MODES:
        return normalized  # type: ignore[return-value]
    return None


# =============================================================================
# Prefs Path Resolution
# =============================================================================

def resolve_tts_prefs_path(prefs_path: str | None = None) -> str:
    """Resolve the TTS preferences file path.

    Priority:
    1. Explicit prefs_path
    2. CLAWDBOT_TTS_PREFS env var
    3. Default ~/.clawdbot/settings/tts.json
    """
    if prefs_path and prefs_path.strip():
        return os.path.expanduser(prefs_path.strip())

    env_path = os.environ.get("CLAWDBOT_TTS_PREFS", "").strip()
    if env_path:
        return os.path.expanduser(env_path)

    config_dir = os.path.expanduser("~/.clawdbot")
    return os.path.join(config_dir, "settings", "tts.json")


# =============================================================================
# Read / Write Preferences
# =============================================================================

def read_prefs(prefs_path: str) -> TtsUserPrefs:
    """Read TTS user preferences from a JSON file."""
    try:
        path = Path(prefs_path)
        if not path.exists():
            return TtsUserPrefs()
        data = json.loads(path.read_text("utf-8"))
        tts_data = data.get("tts")
        if not tts_data or not isinstance(tts_data, dict):
            return TtsUserPrefs()
        return TtsUserPrefs(
            tts=TtsUserPrefsData(
                auto=tts_data.get("auto"),
                enabled=tts_data.get("enabled"),
                provider=tts_data.get("provider"),
                max_length=tts_data.get("maxLength"),
                summarize=tts_data.get("summarize"),
            )
        )
    except Exception:
        return TtsUserPrefs()


def _atomic_write_file(file_path: str, content: str) -> None:
    """Atomically write a file using temp file + rename."""
    rand_suffix = random.randint(100000, 999999)
    tmp_path = f"{file_path}.tmp.{int(time.time())}.{rand_suffix}"
    try:
        Path(tmp_path).write_text(content, "utf-8")
        os.replace(tmp_path, file_path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def _write_prefs(prefs_path: str, prefs: TtsUserPrefs) -> None:
    """Write TTS user preferences to a JSON file (atomic)."""
    Path(prefs_path).parent.mkdir(parents=True, exist_ok=True)
    data: dict = {}
    if prefs.tts:
        tts_data: dict = {}
        if prefs.tts.auto is not None:
            tts_data["auto"] = prefs.tts.auto
        if prefs.tts.enabled is not None:
            tts_data["enabled"] = prefs.tts.enabled
        if prefs.tts.provider is not None:
            tts_data["provider"] = prefs.tts.provider
        if prefs.tts.max_length is not None:
            tts_data["maxLength"] = prefs.tts.max_length
        if prefs.tts.summarize is not None:
            tts_data["summarize"] = prefs.tts.summarize
        data["tts"] = tts_data
    _atomic_write_file(prefs_path, json.dumps(data, indent=2))


def _update_prefs(prefs_path: str, updater: callable) -> None:
    """Read, update, and write preferences atomically."""
    prefs = read_prefs(prefs_path)
    updater(prefs)
    _write_prefs(prefs_path, prefs)


# =============================================================================
# Auto Mode
# =============================================================================

def resolve_tts_auto_mode_from_prefs(prefs: TtsUserPrefs) -> TtsAutoMode | None:
    """Resolve TTS auto mode from user preferences."""
    if prefs.tts:
        auto = normalize_tts_auto_mode(prefs.tts.auto)
        if auto:
            return auto
        if isinstance(prefs.tts.enabled, bool):
            return "always" if prefs.tts.enabled else "off"
    return None


def resolve_tts_auto_mode(
    config_auto: TtsAutoMode,
    prefs_path: str,
    session_auto: str | None = None,
) -> TtsAutoMode:
    """Resolve the effective TTS auto mode.

    Priority:
    1. Session-level override
    2. User preferences
    3. Config default
    """
    session = normalize_tts_auto_mode(session_auto)
    if session:
        return session

    prefs_auto = resolve_tts_auto_mode_from_prefs(read_prefs(prefs_path))
    if prefs_auto:
        return prefs_auto

    return config_auto


def is_tts_enabled(
    config_auto: TtsAutoMode,
    prefs_path: str,
    session_auto: str | None = None,
) -> bool:
    """Check if TTS is enabled."""
    return resolve_tts_auto_mode(config_auto, prefs_path, session_auto) != "off"


def set_tts_auto_mode(prefs_path: str, mode: TtsAutoMode) -> None:
    """Set the TTS auto mode in preferences."""
    def updater(prefs: TtsUserPrefs) -> None:
        if not prefs.tts:
            prefs.tts = TtsUserPrefsData()
        prefs.tts.enabled = None  # Remove legacy
        prefs.tts.auto = mode

    _update_prefs(prefs_path, updater)


def set_tts_enabled(prefs_path: str, enabled: bool) -> None:
    """Enable/disable TTS via auto mode."""
    set_tts_auto_mode(prefs_path, "always" if enabled else "off")


# =============================================================================
# Provider
# =============================================================================

def get_tts_provider(
    config_provider: TtsProvider,
    provider_source: str,
    prefs_path: str,
    openai_api_key: str | None = None,
    elevenlabs_api_key: str | None = None,
) -> TtsProvider:
    """Get the effective TTS provider.

    Priority:
    1. User preferences
    2. Config (if explicitly set)
    3. Auto-detect from API keys
    4. Default to "edge"
    """
    prefs = read_prefs(prefs_path)
    if prefs.tts and prefs.tts.provider:
        return prefs.tts.provider

    if provider_source == "config":
        return config_provider

    # Auto-detect
    if openai_api_key:
        return "openai"
    if elevenlabs_api_key:
        return "elevenlabs"
    return "edge"


def set_tts_provider(prefs_path: str, provider: TtsProvider) -> None:
    """Set the TTS provider in preferences."""
    def updater(prefs: TtsUserPrefs) -> None:
        if not prefs.tts:
            prefs.tts = TtsUserPrefsData()
        prefs.tts.provider = provider

    _update_prefs(prefs_path, updater)


# =============================================================================
# Max Length
# =============================================================================

def get_tts_max_length(prefs_path: str) -> int:
    """Get the TTS max text length."""
    prefs = read_prefs(prefs_path)
    if prefs.tts and prefs.tts.max_length is not None:
        return prefs.tts.max_length
    return DEFAULT_TTS_MAX_LENGTH


def set_tts_max_length(prefs_path: str, max_length: int) -> None:
    """Set the TTS max text length."""
    def updater(prefs: TtsUserPrefs) -> None:
        if not prefs.tts:
            prefs.tts = TtsUserPrefsData()
        prefs.tts.max_length = max_length

    _update_prefs(prefs_path, updater)


# =============================================================================
# Summarization
# =============================================================================

def is_summarization_enabled(prefs_path: str) -> bool:
    """Check if TTS auto-summarization is enabled."""
    prefs = read_prefs(prefs_path)
    if prefs.tts and prefs.tts.summarize is not None:
        return prefs.tts.summarize
    return DEFAULT_TTS_SUMMARIZE


def set_summarization_enabled(prefs_path: str, enabled: bool) -> None:
    """Set TTS auto-summarization."""
    def updater(prefs: TtsUserPrefs) -> None:
        if not prefs.tts:
            prefs.tts = TtsUserPrefsData()
        prefs.tts.summarize = enabled

    _update_prefs(prefs_path, updater)


# =============================================================================
# Provider Ordering
# =============================================================================

def resolve_tts_provider_order(primary: TtsProvider) -> list[TtsProvider]:
    """Get provider fallback order starting with the primary."""
    from lurkbot.tts.types import TTS_PROVIDERS
    return [primary] + [p for p in TTS_PROVIDERS if p != primary]


def is_tts_provider_configured(
    provider: TtsProvider,
    edge_enabled: bool = True,
    openai_api_key: str | None = None,
    elevenlabs_api_key: str | None = None,
) -> bool:
    """Check if a TTS provider is configured (has required credentials)."""
    if provider == "edge":
        return edge_enabled
    if provider == "openai":
        return bool(openai_api_key)
    if provider == "elevenlabs":
        return bool(elevenlabs_api_key)
    return False


# =============================================================================
# API Key Resolution
# =============================================================================

def resolve_tts_api_key(
    provider: TtsProvider,
    openai_api_key: str | None = None,
    elevenlabs_api_key: str | None = None,
) -> str | None:
    """Resolve API key for a provider.

    Checks config key first, then environment variables.
    """
    if provider == "openai":
        return openai_api_key or os.environ.get("OPENAI_API_KEY")
    if provider == "elevenlabs":
        return (
            elevenlabs_api_key
            or os.environ.get("ELEVENLABS_API_KEY")
            or os.environ.get("XI_API_KEY")
        )
    return None


# =============================================================================
# Last TTS Attempt Tracking
# =============================================================================

_last_tts_attempt: TtsStatusEntry | None = None


def get_last_tts_attempt():
    """Get the last TTS attempt status."""
    from lurkbot.tts.types import TtsStatusEntry
    global _last_tts_attempt
    return _last_tts_attempt


def set_last_tts_attempt(entry) -> None:
    """Set the last TTS attempt status."""
    global _last_tts_attempt
    _last_tts_attempt = entry
