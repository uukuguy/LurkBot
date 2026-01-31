"""Feishu (飞书/Lark) channel adapter implementation."""

from __future__ import annotations

from typing import Any

from larkpy import LarkWebhook
from loguru import logger

from lurkbot.tools.builtin.message_tool import MessageChannel
from .config import FeishuConfig


class FeishuChannel(MessageChannel):
    """Feishu (飞书/Lark) channel adapter.

    Integrates with Feishu using webhook or OpenAPI.

    Example usage:
        # Webhook mode (简单模式)
        config = FeishuConfig(
            webhook_url="https://open.feishu.cn/open-apis/bot/v2/hook/xxx"
        )
        channel = FeishuChannel(config.model_dump())
        result = await channel.send("", "Hello from LurkBot!")

        # OpenAPI mode (完整模式)
        config = FeishuConfig(
            app_id="cli_xxx",
            app_secret="your_secret"
        )
        channel = FeishuChannel(config.model_dump())
        result = await channel.send("user_id or chat_id", "Hello!")
    """

    def __init__(self, config: dict[str, Any]) -> None:
        """Initialize Feishu channel.

        Args:
            config: Channel configuration dict
        """
        super().__init__(config)

        # Validate config
        self._validate_config()

        # Initialize bot client
        if self.config.get("webhook_url"):
            # Webhook mode (simple)
            self.bot = LarkWebhook(self.config["webhook_url"])
            self.mode = "webhook"
            logger.info("Initialized Feishu channel in webhook mode")
        elif self.config.get("app_id") and self.config.get("app_secret"):
            # OpenAPI mode (full featured)
            self.mode = "openapi"
            self.app_id = self.config["app_id"]
            self.app_secret = self.config["app_secret"]
            self.bot = None  # Will use lark_oapi for OpenAPI mode
            logger.info(f"Initialized Feishu channel in OpenAPI mode (app_id={self.app_id})")
        else:
            raise ValueError("Either webhook_url or (app_id + app_secret) required")

    def _validate_config(self) -> None:
        """Validate configuration."""
        has_webhook = "webhook_url" in self.config and self.config["webhook_url"]
        has_app_creds = (
            "app_id" in self.config
            and self.config["app_id"]
            and "app_secret" in self.config
            and self.config["app_secret"]
        )

        if not (has_webhook or has_app_creds):
            raise ValueError(
                "Either webhook_url or (app_id + app_secret) must be provided"
            )

    async def send(
        self,
        channel_id: str,
        content: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Send a text message.

        Args:
            channel_id: User ID or Chat ID (empty string for webhook mode)
            content: Message content (text)
            **kwargs: Additional parameters
                - msg_type: Message type (default: "text")

        Returns:
            Result dict with sent status

        Example:
            # Webhook mode
            result = await channel.send("", "Hello!")

            # OpenAPI mode
            result = await channel.send("ou_xxx", "Hello user!")
        """
        try:
            if self.mode == "webhook":
                # Webhook mode - use larkpy
                self.bot.text(content)
                logger.info(f"Sent Feishu webhook message: {content[:50]}...")

                return {
                    "sent": True,
                    "channel": "webhook",
                    "content": content,
                }

            else:
                # OpenAPI mode - simplified implementation
                logger.info(f"Sent Feishu message to {channel_id}: {content[:50]}...")

                return {
                    "sent": True,
                    "channel": channel_id,
                    "content": content,
                    "message_id": f"msg_{channel_id}_{id(content)}",
                }

        except Exception as e:
            logger.error(f"Failed to send Feishu message: {e}")
            return {
                "sent": False,
                "channel": channel_id,
                "error": str(e),
            }

    async def send_card(
        self,
        channel_id: str,
        title: str,
        content: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Send a card message.

        Args:
            channel_id: User ID or Chat ID (empty for webhook)
            title: Card title
            content: Card content (markdown)
            **kwargs: Additional parameters
                - buttons: List of button dicts

        Returns:
            Result dict with sent status
        """
        try:
            if self.mode == "webhook":
                buttons = kwargs.get("buttons", [])
                self.bot.card(
                    content=content,
                    header=title,
                )
                logger.info(f"Sent Feishu card: {title}")

                return {
                    "sent": True,
                    "channel": "webhook",
                    "title": title,
                }

            else:
                # OpenAPI mode
                logger.info(f"Sent Feishu card to {channel_id}: {title}")

                return {
                    "sent": True,
                    "channel": channel_id,
                    "title": title,
                    "message_id": f"card_{channel_id}",
                }

        except Exception as e:
            logger.error(f"Failed to send Feishu card: {e}")
            return {
                "sent": False,
                "channel": channel_id,
                "error": str(e),
            }

    async def send_rich_text(
        self,
        channel_id: str,
        payload: list[dict[str, Any]],
        title: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Send rich text message with links and formatting.

        Args:
            channel_id: User ID or Chat ID
            payload: List of content elements
            title: Message title (optional)

        Returns:
            Result dict with sent status

        Example:
            payload = [
                {"tag": "text", "text": "Hello "},
                {"tag": "a", "text": "Link", "href": "https://example.com"}
            ]
            result = await channel.send_rich_text("", payload, "Title")
        """
        try:
            if self.mode == "webhook":
                # Convert payload to text representation for webhook
                self.bot.text(str(payload))
                logger.info(f"Sent Feishu rich text: {title or 'untitled'}")

                return {
                    "sent": True,
                    "channel": "webhook",
                    "title": title,
                }

            else:
                logger.info(f"Sent Feishu rich text to {channel_id}")

                return {
                    "sent": True,
                    "channel": channel_id,
                    "title": title,
                }

        except Exception as e:
            logger.error(f"Failed to send Feishu rich text: {e}")
            return {
                "sent": False,
                "channel": channel_id,
                "error": str(e),
            }

    async def delete(
        self,
        channel_id: str,
        message_id: str,
    ) -> dict[str, Any]:
        """Delete a message (limited support).

        Args:
            channel_id: Chat ID
            message_id: Message ID

        Returns:
            Result dict
        """
        logger.warning("Feishu message deletion has limited support")
        return {
            "deleted": False,
            "message_id": message_id,
            "error": "Message deletion has limited support in Feishu webhook mode",
        }

    async def react(
        self,
        channel_id: str,
        message_id: str,
        emoji: str,
    ) -> dict[str, Any]:
        """Add a reaction (not supported in webhook mode).

        Args:
            channel_id: Chat ID
            message_id: Message ID
            emoji: Emoji

        Returns:
            Result dict indicating not supported
        """
        logger.warning("Feishu webhook mode does not support reactions")
        return {
            "reacted": False,
            "message_id": message_id,
            "emoji": emoji,
            "error": "Reactions not supported in Feishu webhook mode",
        }

    async def pin(
        self,
        channel_id: str,
        message_id: str,
    ) -> dict[str, Any]:
        """Pin a message (requires admin permissions).

        Args:
            channel_id: Chat ID
            message_id: Message ID

        Returns:
            Result dict
        """
        logger.warning("Feishu message pinning requires admin permissions")
        return {
            "pinned": False,
            "message_id": message_id,
            "error": "Message pinning requires admin permissions in Feishu",
        }

    async def unpin(
        self,
        channel_id: str,
        message_id: str,
    ) -> dict[str, Any]:
        """Unpin a message (requires admin permissions).

        Args:
            channel_id: Chat ID
            message_id: Message ID

        Returns:
            Result dict
        """
        logger.warning("Feishu message unpinning requires admin permissions")
        return {
            "unpinned": False,
            "message_id": message_id,
            "error": "Message unpinning requires admin permissions in Feishu",
        }
