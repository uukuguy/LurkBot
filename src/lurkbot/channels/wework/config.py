"""WeWork channel configuration."""

from __future__ import annotations

from pydantic import BaseModel, Field


class WeWorkConfig(BaseModel):
    """WeWork channel configuration.

    Configuration for Enterprise WeChat (WeWork) integration.

    Attributes:
        corp_id: Enterprise Corp ID (企业 ID)
        secret: Application secret (应用 Secret)
        agent_id: Agent ID (应用 AgentId)
        token: Callback verification token
        encoding_aes_key: Message encryption key
        enabled: Whether the channel is enabled
    """

    corp_id: str = Field(
        description="Enterprise Corp ID (企业 ID)"
    )
    secret: str = Field(
        description="Application secret (应用 Secret)"
    )
    agent_id: str = Field(
        description="Agent ID (应用 AgentId)"
    )
    token: str = Field(
        description="Callback verification token"
    )
    encoding_aes_key: str = Field(
        description="Message encryption key (EncodingAESKey)"
    )
    enabled: bool = Field(
        default=True,
        description="Whether the channel is enabled"
    )

    model_config = {"extra": "allow"}
