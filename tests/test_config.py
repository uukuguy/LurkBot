"""Tests for LurkBot configuration."""

from lurkbot.config import Settings, get_settings


def test_default_settings() -> None:
    """Test default settings values."""
    settings = Settings()

    assert settings.debug is False
    assert settings.log_level == "INFO"
    assert settings.gateway.port == 18789
    assert settings.gateway.host == "127.0.0.1"


def test_get_settings_cached() -> None:
    """Test that get_settings returns cached instance."""
    settings1 = get_settings()
    settings2 = get_settings()

    assert settings1 is settings2


def test_telegram_settings_defaults() -> None:
    """Test Telegram settings defaults."""
    settings = Settings()

    assert settings.telegram.enabled is False
    assert settings.telegram.bot_token is None
    assert settings.telegram.allowed_users == []
