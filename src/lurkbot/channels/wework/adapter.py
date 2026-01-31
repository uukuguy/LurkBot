"""WeWork (Enterprise WeChat) channel adapter implementation."""

from __future__ import annotations

from typing import Any

from wechatpy.enterprise import WeChatClient
from wechatpy.crypto import WeChatCrypto
from wechatpy import parse_message
from wechatpy.exceptions import InvalidSignatureException, WeChatException
from loguru import logger

from lurkbot.tools.builtin.message_tool import MessageChannel
from .config import WeWorkConfig


class WeWorkChannel(MessageChannel):
    """WeWork (Enterprise WeChat) channel adapter.

    Integrates with Enterprise WeChat (WeWork) API for sending and receiving messages.

    Example usage:
        config = WeWorkConfig(
            corp_id="your_corp_id",
            secret="your_secret",
            agent_id="your_agent_id",
            token="your_token",
            encoding_aes_key="your_aes_key"
        )
        channel = WeWorkChannel(config.model_dump())
        result = await channel.send("user_id", "Hello from LurkBot!")
    """

    def __init__(self, config: dict[str, Any]) -> None:
        """Initialize WeWork channel.

        Args:
            config: Channel configuration dict
        """
        super().__init__(config)

        # Validate and extract config
        self._validate_config()

        # Initialize WeChatClient
        self.client = WeChatClient(
            self.config["corp_id"],
            self.config["secret"]
        )

        # Initialize crypto for message encryption/decryption
        self.crypto = WeChatCrypto(
            self.config["token"],
            self.config["encoding_aes_key"],
            self.config["corp_id"]
        )

        logger.info(
            f"Initialized WeWork channel for corp_id={self.config['corp_id']}, "
            f"agent_id={self.config['agent_id']}"
        )

    def _validate_config(self) -> None:
        """Validate required configuration fields."""
        required_fields = ["corp_id", "secret", "agent_id", "token", "encoding_aes_key"]
        for field in required_fields:
            if field not in self.config:
                raise ValueError(f"Missing required config field: {field}")

    async def send(
        self,
        channel_id: str,
        content: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Send a text message to a user or chat.

        Args:
            channel_id: User ID or chat ID to send message to
            content: Message content (text)
            **kwargs: Additional parameters
                - msg_type: Message type (default: "text")
                - safe: Safe mode (0 or 1, default: 0)
                - to_party: Department IDs (optional)
                - to_tag: Tag IDs (optional)

        Returns:
            Result dict with sent status and message info

        Example:
            result = await channel.send("user123", "Hello!")
            # Returns: {"sent": True, "message_id": "...", ...}
        """
        try:
            msg_type = kwargs.get("msg_type", "text")
            safe = kwargs.get("safe", 0)
            to_party = kwargs.get("to_party")
            to_tag = kwargs.get("to_tag")

            # Determine if sending to user, party (department), or tag
            to_user = channel_id if not to_party and not to_tag else None

            # Send message via wechatpy client
            response = self.client.message.send_text(
                agent_id=int(self.config["agent_id"]),
                user_ids=to_user,
                party_ids=to_party,
                tag_ids=to_tag,
                content=content,
                safe=safe
            )

            logger.info(
                f"Sent message to {channel_id}: {content[:50]}... "
                f"(response: {response})"
            )

            return {
                "sent": True,
                "channel": channel_id,
                "content": content,
                "message_id": response.get("msgid", "unknown"),
                "invalid_user": response.get("invaliduser"),
                "invalid_party": response.get("invalidparty"),
                "invalid_tag": response.get("invalidtag"),
            }

        except Exception as e:
            logger.error(f"Failed to send WeWork message to {channel_id}: {e}")
            return {
                "sent": False,
                "channel": channel_id,
                "error": str(e),
            }

    async def send_markdown(
        self,
        channel_id: str,
        content: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Send a markdown message.

        Args:
            channel_id: User ID or chat ID
            content: Markdown content

        Returns:
            Result dict with sent status
        """
        try:
            response = self.client.message.send_markdown(
                agent_id=int(self.config["agent_id"]),
                user_ids=channel_id,
                content=content
            )

            logger.info(f"Sent markdown message to {channel_id}")

            return {
                "sent": True,
                "channel": channel_id,
                "message_id": response.get("msgid", "unknown"),
            }

        except Exception as e:
            logger.error(f"Failed to send markdown to {channel_id}: {e}")
            return {
                "sent": False,
                "channel": channel_id,
                "error": str(e),
            }

    async def send_image(
        self,
        channel_id: str,
        media_id: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Send an image message.

        Args:
            channel_id: User ID or chat ID
            media_id: Media ID (uploaded via upload_media)

        Returns:
            Result dict with sent status
        """
        try:
            response = self.client.message.send_image(
                agent_id=int(self.config["agent_id"]),
                user_ids=channel_id,
                media_id=media_id
            )

            logger.info(f"Sent image message to {channel_id}")

            return {
                "sent": True,
                "channel": channel_id,
                "message_id": response.get("msgid", "unknown"),
            }

        except Exception as e:
            logger.error(f"Failed to send image to {channel_id}: {e}")
            return {
                "sent": False,
                "channel": channel_id,
                "error": str(e),
            }

    def parse_callback_message(
        self,
        raw_message: str,
        signature: str,
        timestamp: str,
        nonce: str,
    ) -> Any:
        """Parse and decrypt callback message from WeWork.

        Args:
            raw_message: Raw encrypted XML message
            signature: Message signature
            timestamp: Message timestamp
            nonce: Message nonce

        Returns:
            Parsed message object

        Raises:
            InvalidSignatureException: If signature validation fails
            WeChatException: If message parsing or decryption fails

        Example:
            try:
                msg = channel.parse_callback_message(
                    raw_xml, signature, timestamp, nonce
                )
                if msg.type == "text":
                    print(f"Received: {msg.content}")
            except Exception as e:
                print(f"Parse error: {e}")
        """
        try:
            # Decrypt message
            decrypted_xml = self.crypto.decrypt_message(
                raw_message,
                signature,
                timestamp,
                nonce
            )

            # Parse message
            msg = parse_message(decrypted_xml)

            logger.info(
                f"Parsed callback message: type={msg.type}, "
                f"from={getattr(msg, 'source', 'unknown')}"
            )

            return msg

        except (InvalidSignatureException, WeChatException) as e:
            logger.error(f"Failed to parse callback message: {e}")
            raise

    def create_callback_response(
        self,
        content: str,
        message: Any,
    ) -> str:
        """Create encrypted response for callback.

        Args:
            content: Response content (text or XML)
            message: Original message object (for getting msg_id)

        Returns:
            Encrypted XML response string

        Example:
            msg = channel.parse_callback_message(...)
            response_xml = channel.create_callback_response("Got it!", msg)
            # Return response_xml in HTTP response
        """
        try:
            # Create reply XML
            from wechatpy.replies import TextReply

            reply = TextReply(content=content, message=message)
            reply_xml = reply.render()

            # Encrypt reply
            encrypted_xml = self.crypto.encrypt_message(
                reply_xml,
                nonce=message.id,
                timestamp=message.time
            )

            return encrypted_xml

        except Exception as e:
            logger.error(f"Failed to create callback response: {e}")
            raise

    async def delete(
        self,
        channel_id: str,
        message_id: str,
    ) -> dict[str, Any]:
        """Delete a message (not supported by WeWork API).

        WeWork API does not support message deletion.
        This method is a no-op and returns success=False.

        Args:
            channel_id: User ID or chat ID
            message_id: Message ID

        Returns:
            Result dict indicating deletion is not supported
        """
        logger.warning("WeWork API does not support message deletion")
        return {
            "deleted": False,
            "message_id": message_id,
            "error": "Message deletion not supported by WeWork API",
        }

    async def react(
        self,
        channel_id: str,
        message_id: str,
        emoji: str,
    ) -> dict[str, Any]:
        """Add a reaction to a message (not supported by WeWork API).

        WeWork API does not support reactions.

        Args:
            channel_id: User ID or chat ID
            message_id: Message ID
            emoji: Emoji to react with

        Returns:
            Result dict indicating reactions are not supported
        """
        logger.warning("WeWork API does not support reactions")
        return {
            "reacted": False,
            "message_id": message_id,
            "emoji": emoji,
            "error": "Reactions not supported by WeWork API",
        }

    async def pin(
        self,
        channel_id: str,
        message_id: str,
    ) -> dict[str, Any]:
        """Pin a message (not supported by WeWork API).

        Args:
            channel_id: User ID or chat ID
            message_id: Message ID

        Returns:
            Result dict indicating pinning is not supported
        """
        logger.warning("WeWork API does not support message pinning")
        return {
            "pinned": False,
            "message_id": message_id,
            "error": "Message pinning not supported by WeWork API",
        }

    async def unpin(
        self,
        channel_id: str,
        message_id: str,
    ) -> dict[str, Any]:
        """Unpin a message (not supported by WeWork API).

        Args:
            channel_id: User ID or chat ID
            message_id: Message ID

        Returns:
            Result dict indicating unpinning is not supported
        """
        logger.warning("WeWork API does not support message unpinning")
        return {
            "unpinned": False,
            "message_id": message_id,
            "error": "Message unpinning not supported by WeWork API",
        }

    def get_user_info(self, user_id: str) -> dict[str, Any]:
        """Get user information.

        Args:
            user_id: User ID

        Returns:
            User information dict

        Example:
            user = channel.get_user_info("user123")
            print(f"Name: {user['name']}, Department: {user['department']}")
        """
        try:
            user = self.client.user.get(user_id)
            logger.info(f"Retrieved user info for {user_id}")
            return user

        except Exception as e:
            logger.error(f"Failed to get user info for {user_id}: {e}")
            return {"error": str(e)}

    def upload_media(
        self,
        media_type: str,
        media_file: str | bytes,
    ) -> dict[str, Any]:
        """Upload media file.

        Args:
            media_type: Media type (image, voice, video, file)
            media_file: File path or file bytes

        Returns:
            Upload result with media_id

        Example:
            result = channel.upload_media("image", "/path/to/image.jpg")
            media_id = result["media_id"]
            await channel.send_image("user123", media_id)
        """
        try:
            result = self.client.media.upload(media_type, media_file)
            logger.info(f"Uploaded media: type={media_type}, media_id={result['media_id']}")
            return result

        except Exception as e:
            logger.error(f"Failed to upload media: {e}")
            return {"error": str(e)}
