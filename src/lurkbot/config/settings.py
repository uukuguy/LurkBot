"""Application settings and configuration."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class GatewaySettings(BaseSettings):
    """Gateway server settings."""

    host: str = "127.0.0.1"
    port: int = 18789
    mode: Literal["local", "remote"] = "local"
    auth_mode: Literal["none", "token", "password"] = "token"
    auth_token: str | None = None


class AgentSettings(BaseSettings):
    """AI agent settings."""

    model: str = "anthropic/claude-sonnet-4-20250514"
    max_tokens: int = 4096
    temperature: float = 0.7
    workspace: Path = Field(default_factory=lambda: Path.home() / "lurkbot")


class TelegramSettings(BaseSettings):
    """Telegram channel settings."""

    enabled: bool = False
    bot_token: str | None = None
    allowed_users: list[int] = Field(default_factory=list)


class DiscordSettings(BaseSettings):
    """Discord channel settings."""

    enabled: bool = False
    bot_token: str | None = None
    allowed_guilds: list[int] = Field(default_factory=list)


class SlackSettings(BaseSettings):
    """Slack channel settings."""

    enabled: bool = False
    bot_token: str | None = None
    app_token: str | None = None
    allowed_channels: list[str] = Field(default_factory=list)


class Settings(BaseSettings):
    """Main application settings."""

    model_config = SettingsConfigDict(
        env_prefix="LURKBOT_",
        env_nested_delimiter="__",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    debug: bool = False
    log_level: str = "INFO"
    data_dir: Path = Field(default_factory=lambda: Path.home() / ".lurkbot")

    # Components
    gateway: GatewaySettings = Field(default_factory=GatewaySettings)
    agent: AgentSettings = Field(default_factory=AgentSettings)

    # Channels
    telegram: TelegramSettings = Field(default_factory=TelegramSettings)
    discord: DiscordSettings = Field(default_factory=DiscordSettings)
    slack: SlackSettings = Field(default_factory=SlackSettings)

    # AI Provider API Keys
    anthropic_api_key: str | None = None
    openai_api_key: str | None = None


@lru_cache
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()
