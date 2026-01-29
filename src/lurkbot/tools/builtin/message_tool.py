"""Message tool - multi-channel messaging.

Ported from moltbot's message tool.

This is a P1 tool that provides:
- message: Send messages to various channels (Discord, Slack, etc.)

Supported actions:
- send: Send a message to a channel
- delete: Delete a message
- react: Add a reaction to a message
- pin: Pin a message
- poll: Create a poll
- thread: Create or reply to a thread
- event: Create calendar event
- media: Send media content
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field

from lurkbot.tools.builtin.common import (
    ToolResult,
    error_result,
    json_result,
    read_string_param,
    read_string_array_param,
    read_dict_param,
    read_bool_param,
)


# =============================================================================
# Constants
# =============================================================================

class MessageAction(str, Enum):
    """Supported message actions."""
    SEND = "send"
    DELETE = "delete"
    REACT = "react"
    PIN = "pin"
    UNPIN = "unpin"
    POLL = "poll"
    THREAD = "thread"
    EVENT = "event"
    MEDIA = "media"


class ChannelType(str, Enum):
    """Supported channel types."""
    DISCORD = "discord"
    SLACK = "slack"
    TELEGRAM = "telegram"
    CLI = "cli"
    WEB = "web"


# =============================================================================
# Configuration
# =============================================================================


@dataclass
class MessageConfig:
    """Configuration for message tool."""

    enabled: bool = True
    default_channel_type: str = "cli"
    # Channel configurations (would be loaded from config file in production)
    channels: dict[str, dict[str, Any]] = field(default_factory=dict)


# =============================================================================
# Channel Registry
# =============================================================================


class MessageChannel:
    """Base class for message channels.

    Subclasses implement specific channel integrations.
    """

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config

    async def send(
        self,
        channel_id: str,
        content: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Send a message to a channel."""
        raise NotImplementedError

    async def delete(
        self,
        channel_id: str,
        message_id: str,
    ) -> dict[str, Any]:
        """Delete a message."""
        raise NotImplementedError

    async def react(
        self,
        channel_id: str,
        message_id: str,
        emoji: str,
    ) -> dict[str, Any]:
        """Add a reaction to a message."""
        raise NotImplementedError

    async def pin(
        self,
        channel_id: str,
        message_id: str,
    ) -> dict[str, Any]:
        """Pin a message."""
        raise NotImplementedError

    async def unpin(
        self,
        channel_id: str,
        message_id: str,
    ) -> dict[str, Any]:
        """Unpin a message."""
        raise NotImplementedError


class CLIChannel(MessageChannel):
    """CLI channel - outputs to console (for development/testing)."""

    async def send(
        self,
        channel_id: str,
        content: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Print message to console."""
        from loguru import logger
        logger.info(f"[CLI Message] {channel_id}: {content}")
        return {
            "sent": True,
            "channel": channel_id,
            "content": content,
            "message_id": f"cli-msg-{id(content)}",
        }

    async def delete(
        self,
        channel_id: str,
        message_id: str,
    ) -> dict[str, Any]:
        """Mark message as deleted (CLI doesn't really delete)."""
        from loguru import logger
        logger.info(f"[CLI Delete] {channel_id}: {message_id}")
        return {"deleted": True, "message_id": message_id}

    async def react(
        self,
        channel_id: str,
        message_id: str,
        emoji: str,
    ) -> dict[str, Any]:
        """Log reaction (CLI doesn't support reactions)."""
        from loguru import logger
        logger.info(f"[CLI React] {channel_id}: {message_id} + {emoji}")
        return {"reacted": True, "message_id": message_id, "emoji": emoji}

    async def pin(
        self,
        channel_id: str,
        message_id: str,
    ) -> dict[str, Any]:
        """Log pin (CLI doesn't support pinning)."""
        from loguru import logger
        logger.info(f"[CLI Pin] {channel_id}: {message_id}")
        return {"pinned": True, "message_id": message_id}

    async def unpin(
        self,
        channel_id: str,
        message_id: str,
    ) -> dict[str, Any]:
        """Log unpin (CLI doesn't support pinning)."""
        from loguru import logger
        logger.info(f"[CLI Unpin] {channel_id}: {message_id}")
        return {"unpinned": True, "message_id": message_id}


# Channel registry
_channel_registry: dict[str, type[MessageChannel]] = {
    "cli": CLIChannel,
}


def register_channel(channel_type: str, channel_class: type[MessageChannel]) -> None:
    """Register a channel type."""
    _channel_registry[channel_type] = channel_class


def get_channel(channel_type: str, config: dict[str, Any]) -> MessageChannel | None:
    """Get a channel instance by type."""
    channel_class = _channel_registry.get(channel_type)
    if channel_class:
        return channel_class(config)
    return None


# =============================================================================
# Message Tool Parameters
# =============================================================================


class MessageParams(BaseModel):
    """Parameters for message tool."""

    action: str = Field(
        description="Action to perform: send, delete, react, pin, unpin, poll, thread, event, media"
    )
    channel: str | None = Field(
        default=None,
        description="Channel ID to send message to"
    )
    channel_type: str | None = Field(
        default=None,
        alias="channelType",
        description="Channel type: discord, slack, telegram, cli"
    )
    content: str | None = Field(
        default=None,
        description="Message content (for send action)"
    )
    message_id: str | None = Field(
        default=None,
        alias="messageId",
        description="Message ID (for delete, react, pin actions)"
    )
    emoji: str | None = Field(
        default=None,
        description="Emoji to react with"
    )
    attachments: list[str] | None = Field(
        default=None,
        description="List of attachment URLs"
    )
    embed: dict[str, Any] | None = Field(
        default=None,
        description="Embed data (for rich messages)"
    )
    reply_to: str | None = Field(
        default=None,
        alias="replyTo",
        description="Message ID to reply to"
    )
    thread_name: str | None = Field(
        default=None,
        alias="threadName",
        description="Thread name (for thread action)"
    )
    poll_options: list[str] | None = Field(
        default=None,
        alias="pollOptions",
        description="Poll options (for poll action)"
    )

    model_config = {"populate_by_name": True}


# =============================================================================
# Message Tool Implementation
# =============================================================================


async def message_tool(
    params: dict[str, Any],
    config: MessageConfig | None = None,
) -> ToolResult:
    """Send messages to channels.

    Multi-channel messaging tool supporting various platforms.

    Args:
        params: Tool parameters
        config: Message configuration

    Returns:
        ToolResult with operation result
    """
    config = config or MessageConfig()

    if not config.enabled:
        return error_result("message tool is disabled")

    # Read action parameter
    action = read_string_param(params, "action", required=True)
    if not action:
        return error_result("action required")

    # Normalize action
    try:
        action_enum = MessageAction(action.lower())
    except ValueError:
        valid_actions = ", ".join(a.value for a in MessageAction)
        return error_result(f"Invalid action '{action}'. Valid actions: {valid_actions}")

    # Get channel info
    channel_id = read_string_param(params, "channel")
    channel_type = read_string_param(params, "channelType") or config.default_channel_type

    if not channel_id:
        return error_result("channel required")

    # Get channel instance
    channel_config = config.channels.get(channel_type, {})
    channel = get_channel(channel_type, channel_config)

    if not channel:
        return error_result(f"Unknown channel type: {channel_type}")

    # Execute action
    try:
        if action_enum == MessageAction.SEND:
            return await _handle_send(params, channel, channel_id)
        elif action_enum == MessageAction.DELETE:
            return await _handle_delete(params, channel, channel_id)
        elif action_enum == MessageAction.REACT:
            return await _handle_react(params, channel, channel_id)
        elif action_enum == MessageAction.PIN:
            return await _handle_pin(params, channel, channel_id)
        elif action_enum == MessageAction.UNPIN:
            return await _handle_unpin(params, channel, channel_id)
        elif action_enum == MessageAction.POLL:
            return await _handle_poll(params, channel, channel_id)
        elif action_enum == MessageAction.THREAD:
            return await _handle_thread(params, channel, channel_id)
        elif action_enum == MessageAction.EVENT:
            return await _handle_event(params, channel, channel_id)
        elif action_enum == MessageAction.MEDIA:
            return await _handle_media(params, channel, channel_id)
        else:
            return error_result(f"Action not implemented: {action}")
    except Exception as e:
        return error_result(f"Message action failed: {e}")


async def _handle_send(
    params: dict[str, Any],
    channel: MessageChannel,
    channel_id: str,
) -> ToolResult:
    """Handle send action."""
    content = read_string_param(params, "content")
    if not content:
        return error_result("content required for send action")

    attachments = read_string_array_param(params, "attachments")
    embed = read_dict_param(params, "embed")
    reply_to = read_string_param(params, "replyTo")

    result = await channel.send(
        channel_id,
        content,
        attachments=attachments,
        embed=embed,
        reply_to=reply_to,
    )

    return json_result({
        "action": "send",
        "channel": channel_id,
        **result,
    })


async def _handle_delete(
    params: dict[str, Any],
    channel: MessageChannel,
    channel_id: str,
) -> ToolResult:
    """Handle delete action."""
    message_id = read_string_param(params, "messageId", required=True)
    if not message_id:
        return error_result("messageId required for delete action")

    result = await channel.delete(channel_id, message_id)

    return json_result({
        "action": "delete",
        "channel": channel_id,
        **result,
    })


async def _handle_react(
    params: dict[str, Any],
    channel: MessageChannel,
    channel_id: str,
) -> ToolResult:
    """Handle react action."""
    message_id = read_string_param(params, "messageId", required=True)
    if not message_id:
        return error_result("messageId required for react action")

    emoji = read_string_param(params, "emoji", required=True)
    if not emoji:
        return error_result("emoji required for react action")

    result = await channel.react(channel_id, message_id, emoji)

    return json_result({
        "action": "react",
        "channel": channel_id,
        **result,
    })


async def _handle_pin(
    params: dict[str, Any],
    channel: MessageChannel,
    channel_id: str,
) -> ToolResult:
    """Handle pin action."""
    message_id = read_string_param(params, "messageId", required=True)
    if not message_id:
        return error_result("messageId required for pin action")

    result = await channel.pin(channel_id, message_id)

    return json_result({
        "action": "pin",
        "channel": channel_id,
        **result,
    })


async def _handle_unpin(
    params: dict[str, Any],
    channel: MessageChannel,
    channel_id: str,
) -> ToolResult:
    """Handle unpin action."""
    message_id = read_string_param(params, "messageId", required=True)
    if not message_id:
        return error_result("messageId required for unpin action")

    result = await channel.unpin(channel_id, message_id)

    return json_result({
        "action": "unpin",
        "channel": channel_id,
        **result,
    })


async def _handle_poll(
    params: dict[str, Any],
    channel: MessageChannel,
    channel_id: str,
) -> ToolResult:
    """Handle poll action."""
    content = read_string_param(params, "content")
    if not content:
        return error_result("content (poll question) required for poll action")

    options = read_string_array_param(params, "pollOptions")
    if not options or len(options) < 2:
        return error_result("pollOptions (at least 2) required for poll action")

    # Poll is typically sent as a special message
    # For CLI channel, we just send a formatted message
    poll_content = f"📊 **Poll**: {content}\n" + "\n".join(
        f"  {i+1}. {opt}" for i, opt in enumerate(options)
    )

    result = await channel.send(channel_id, poll_content, poll_options=options)

    return json_result({
        "action": "poll",
        "channel": channel_id,
        "question": content,
        "options": options,
        **result,
    })


async def _handle_thread(
    params: dict[str, Any],
    channel: MessageChannel,
    channel_id: str,
) -> ToolResult:
    """Handle thread action."""
    content = read_string_param(params, "content")
    thread_name = read_string_param(params, "threadName")
    reply_to = read_string_param(params, "replyTo")

    if not content:
        return error_result("content required for thread action")

    # Thread is typically a reply to a message or creating a new thread
    thread_content = f"🧵 {thread_name or 'Thread'}: {content}"

    result = await channel.send(
        channel_id,
        thread_content,
        thread_name=thread_name,
        reply_to=reply_to,
    )

    return json_result({
        "action": "thread",
        "channel": channel_id,
        "threadName": thread_name,
        **result,
    })


async def _handle_event(
    params: dict[str, Any],
    channel: MessageChannel,
    channel_id: str,
) -> ToolResult:
    """Handle event action (calendar event)."""
    content = read_string_param(params, "content")
    if not content:
        return error_result("content (event description) required for event action")

    # Event is typically sent as a special formatted message
    event_content = f"📅 **Event**: {content}"

    result = await channel.send(channel_id, event_content, is_event=True)

    return json_result({
        "action": "event",
        "channel": channel_id,
        **result,
    })


async def _handle_media(
    params: dict[str, Any],
    channel: MessageChannel,
    channel_id: str,
) -> ToolResult:
    """Handle media action."""
    attachments = read_string_array_param(params, "attachments")
    if not attachments:
        return error_result("attachments required for media action")

    content = read_string_param(params, "content") or ""

    result = await channel.send(
        channel_id,
        content,
        attachments=attachments,
    )

    return json_result({
        "action": "media",
        "channel": channel_id,
        "attachments": attachments,
        **result,
    })


# =============================================================================
# Tool Registration Helpers
# =============================================================================


def create_message_tool() -> dict[str, Any]:
    """Create message tool definition for PydanticAI."""
    return {
        "name": "message",
        "label": "Message",
        "description": (
            "Send messages to channels (Discord, Slack, Telegram, etc.). "
            "Supports actions: send, delete, react, pin, unpin, poll, thread, event, media."
        ),
        "parameters": MessageParams.model_json_schema(),
    }
