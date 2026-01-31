"""DingTalk channel configuration."""

from __future__ import annotations

from pydantic import BaseModel, Field


class DingTalkConfig(BaseModel):
    """DingTalk channel configuration.

    Configuration for DingTalk (钉钉) Stream mode integration.

    Attributes:
        client_id: App Key or Client ID
        client_secret: App Secret or Client Secret
        robot_code: Robot code for group robot (optional)
        enabled: Whether the channel is enabled
    """

    client_id: str = Field(
        description="App Key or Client ID from DingTalk Open Platform"
    )
    client_secret: str = Field(
        description="App Secret or Client Secret from DingTalk Open Platform"
    )
    robot_code: str | None = Field(
        default=None,
        description="Robot code for group robot (optional)"
    )
    enabled: bool = Field(
        default=True,
        description="Whether the channel is enabled"
    )

    model_config = {"extra": "allow"}
