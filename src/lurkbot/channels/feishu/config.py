"""Feishu channel configuration."""

from __future__ import annotations

from pydantic import BaseModel, Field


class FeishuConfig(BaseModel):
    """Feishu channel configuration.

    Configuration for Feishu (飞书/Lark) integration.

    Attributes:
        app_id: Application ID
        app_secret: Application Secret
        webhook_url: Webhook URL for bot (optional, for simple webhook mode)
        enabled: Whether the channel is enabled
    """

    app_id: str | None = Field(
        default=None,
        description="Application ID from Feishu Open Platform"
    )
    app_secret: str | None = Field(
        default=None,
        description="Application Secret from Feishu Open Platform"
    )
    webhook_url: str | None = Field(
        default=None,
        description="Webhook URL for simple bot mode (optional)"
    )
    enabled: bool = Field(
        default=True,
        description="Whether the channel is enabled"
    )

    model_config = {"extra": "allow"}
