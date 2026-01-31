"""DingTalk (钉钉) channel adapter implementation."""

from __future__ import annotations

from typing import Any
import asyncio

from dingtalk_stream import AckMessage, ChatbotMessage
import dingtalk_stream
from loguru import logger

from lurkbot.tools.builtin.message_tool import MessageChannel
from .config import DingTalkConfig


class DingTalkChannel(MessageChannel):
    """DingTalk (钉钉) channel adapter.

    Integrates with DingTalk Stream API for sending and receiving messages.

    Example usage:
        config = DingTalkConfig(
            client_id="your_client_id",
            client_secret="your_client_secret"
        )
        channel = DingTalkChannel(config.model_dump())
        result = await channel.send("conversation_id", "Hello from LurkBot!")
    """

    def __init__(self, config: dict[str, Any]) -> None:
        """Initialize DingTalk channel.

        Args:
            config: Channel configuration dict
        """
        super().__init__(config)

        # Validate config
        self._validate_config()

        # Initialize credential
        self.credential = dingtalk_stream.Credential(
            self.config["client_id"],
            self.config["client_secret"]
        )

        # Stream client will be initialized when needed
        self._client: dingtalk_stream.DingTalkStreamClient | None = None
        self._message_api = DingTalkMessageAPI(
            self.config["client_id"],
            self.config["client_secret"]
        )

        logger.info(
            f"Initialized DingTalk channel for client_id={self.config['client_id']}"
        )

    def _validate_config(self) -> None:
        """Validate required configuration fields."""
        required_fields = ["client_id", "client_secret"]
        for field in required_fields:
            if field not in self.config:
                raise ValueError(f"Missing required config field: {field}")

    async def send(
        self,
        channel_id: str,
        content: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Send a text message.

        Args:
            channel_id: Conversation ID or webhook URL
            content: Message content (text)
            **kwargs: Additional parameters
                - msg_type: Message type (default: "text")
                - at_users: List of user IDs to @mention
                - at_mobiles: List of mobile numbers to @mention
                - is_at_all: Whether to @all (default: False)

        Returns:
            Result dict with sent status

        Example:
            result = await channel.send("conv_123", "Hello!", at_users=["user1"])
        """
        try:
            msg_type = kwargs.get("msg_type", "text")
            at_users = kwargs.get("at_users", [])
            at_mobiles = kwargs.get("at_mobiles", [])
            is_at_all = kwargs.get("is_at_all", False)

            # Send via DingTalk API
            response = await self._message_api.send_text(
                conversation_id=channel_id,
                content=content,
                at_users=at_users,
                at_mobiles=at_mobiles,
                is_at_all=is_at_all
            )

            logger.info(f"Sent DingTalk message to {channel_id}: {content[:50]}...")

            return {
                "sent": True,
                "channel": channel_id,
                "content": content,
                "response": response,
            }

        except Exception as e:
            logger.error(f"Failed to send DingTalk message to {channel_id}: {e}")
            return {
                "sent": False,
                "channel": channel_id,
                "error": str(e),
            }

    async def send_markdown(
        self,
        channel_id: str,
        title: str,
        content: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Send a markdown message.

        Args:
            channel_id: Conversation ID
            title: Markdown title
            content: Markdown content

        Returns:
            Result dict with sent status
        """
        try:
            response = await self._message_api.send_markdown(
                conversation_id=channel_id,
                title=title,
                content=content
            )

            logger.info(f"Sent markdown message to {channel_id}")

            return {
                "sent": True,
                "channel": channel_id,
                "title": title,
                "response": response,
            }

        except Exception as e:
            logger.error(f"Failed to send markdown to {channel_id}: {e}")
            return {
                "sent": False,
                "channel": channel_id,
                "error": str(e),
            }

    async def send_card(
        self,
        channel_id: str,
        card_data: dict[str, Any],
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Send an interactive card message.

        Args:
            channel_id: Conversation ID
            card_data: Card template data

        Returns:
            Result dict with sent status
        """
        try:
            response = await self._message_api.send_card(
                conversation_id=channel_id,
                card_data=card_data
            )

            logger.info(f"Sent card message to {channel_id}")

            return {
                "sent": True,
                "channel": channel_id,
                "response": response,
            }

        except Exception as e:
            logger.error(f"Failed to send card to {channel_id}: {e}")
            return {
                "sent": False,
                "channel": channel_id,
                "error": str(e),
            }

    def start_stream_client(self, callback_handler: Any) -> None:
        """Start Stream mode client for receiving messages.

        Args:
            callback_handler: ChatbotHandler subclass for processing messages

        Example:
            class MyHandler(dingtalk_stream.ChatbotHandler):
                async def process(self, callback):
                    msg = ChatbotMessage.from_dict(callback.data)
                    # Process message
                    return AckMessage.STATUS_OK, 'OK'

            channel.start_stream_client(MyHandler())
        """
        if self._client is None:
            self._client = dingtalk_stream.DingTalkStreamClient(self.credential)
            self._client.register_callback_handler(
                ChatbotMessage.TOPIC,
                callback_handler
            )

        logger.info("Starting DingTalk Stream client...")
        self._client.start_forever()

    async def delete(
        self,
        channel_id: str,
        message_id: str,
    ) -> dict[str, Any]:
        """Delete a message (limited support).

        Note: DingTalk only allows robots to recall their own messages
        within a short time window.

        Args:
            channel_id: Conversation ID
            message_id: Message ID

        Returns:
            Result dict
        """
        logger.warning("DingTalk message deletion has limited support")
        return {
            "deleted": False,
            "message_id": message_id,
            "error": "Message deletion has limited support in DingTalk API",
        }

    async def react(
        self,
        channel_id: str,
        message_id: str,
        emoji: str,
    ) -> dict[str, Any]:
        """Add a reaction (not supported by DingTalk).

        Args:
            channel_id: Conversation ID
            message_id: Message ID
            emoji: Emoji

        Returns:
            Result dict indicating not supported
        """
        logger.warning("DingTalk API does not support reactions")
        return {
            "reacted": False,
            "message_id": message_id,
            "emoji": emoji,
            "error": "Reactions not supported by DingTalk API",
        }

    async def pin(
        self,
        channel_id: str,
        message_id: str,
    ) -> dict[str, Any]:
        """Pin a message (not supported by DingTalk robot API).

        Args:
            channel_id: Conversation ID
            message_id: Message ID

        Returns:
            Result dict indicating not supported
        """
        logger.warning("DingTalk robot API does not support message pinning")
        return {
            "pinned": False,
            "message_id": message_id,
            "error": "Message pinning not supported by DingTalk robot API",
        }

    async def unpin(
        self,
        channel_id: str,
        message_id: str,
    ) -> dict[str, Any]:
        """Unpin a message (not supported).

        Args:
            channel_id: Conversation ID
            message_id: Message ID

        Returns:
            Result dict indicating not supported
        """
        logger.warning("DingTalk robot API does not support message unpinning")
        return {
            "unpinned": False,
            "message_id": message_id,
            "error": "Message unpinning not supported by DingTalk robot API",
        }


class DingTalkMessageAPI:
    """Helper class for DingTalk message API calls.

    Uses dingtalk_stream credential to make API calls.
    """

    def __init__(self, client_id: str, client_secret: str):
        """Initialize message API helper.

        Args:
            client_id: DingTalk client ID
            client_secret: DingTalk client secret
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self._access_token: str | None = None

    async def _get_access_token(self) -> str:
        """Get access token from DingTalk.

        Returns:
            Access token string
        """
        # In real implementation, call DingTalk API to get token
        # For now, return a placeholder
        if self._access_token:
            return self._access_token

        # TODO: Implement actual token retrieval
        # This would call: https://oapi.dingtalk.com/gettoken
        self._access_token = "placeholder_token"
        return self._access_token

    async def send_text(
        self,
        conversation_id: str,
        content: str,
        at_users: list[str] | None = None,
        at_mobiles: list[str] | None = None,
        is_at_all: bool = False,
    ) -> dict[str, Any]:
        """Send text message via DingTalk API.

        Args:
            conversation_id: Target conversation
            content: Message content
            at_users: Users to @mention
            at_mobiles: Mobile numbers to @mention
            is_at_all: Whether to @all

        Returns:
            API response dict
        """
        # TODO: Implement actual API call
        # This is a simplified version for MVP
        logger.info(f"[DingTalk API] Sending text to {conversation_id}")
        return {
            "errcode": 0,
            "errmsg": "ok",
            "message_id": f"msg_{conversation_id}_{id(content)}",
        }

    async def send_markdown(
        self,
        conversation_id: str,
        title: str,
        content: str,
    ) -> dict[str, Any]:
        """Send markdown message via DingTalk API.

        Args:
            conversation_id: Target conversation
            title: Markdown title
            content: Markdown content

        Returns:
            API response dict
        """
        # TODO: Implement actual API call
        logger.info(f"[DingTalk API] Sending markdown to {conversation_id}")
        return {
            "errcode": 0,
            "errmsg": "ok",
            "message_id": f"md_msg_{conversation_id}",
        }

    async def send_card(
        self,
        conversation_id: str,
        card_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Send card message via DingTalk API.

        Args:
            conversation_id: Target conversation
            card_data: Card template data

        Returns:
            API response dict
        """
        # TODO: Implement actual API call
        logger.info(f"[DingTalk API] Sending card to {conversation_id}")
        return {
            "errcode": 0,
            "errmsg": "ok",
            "message_id": f"card_msg_{conversation_id}",
        }
