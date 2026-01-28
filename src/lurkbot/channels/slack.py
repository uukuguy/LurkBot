"""Slack channel adapter."""

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from loguru import logger

from lurkbot.channels.base import Channel, ChannelMessage
from lurkbot.config.settings import SlackSettings

if TYPE_CHECKING:
    from lurkbot.tools.approval import ApprovalManager


class SlackChannel(Channel):
    """Slack bot channel adapter using Socket Mode.

    Features:
    - Socket Mode: Real-time events without public HTTP endpoint
    - Channel allowlist: Restrict bot to specific channels
    - Approval commands: @bot approve/deny for tool approval workflow
    - Mention-based activation: Bot responds when mentioned with @bot
    """

    def __init__(
        self,
        settings: SlackSettings,
        approval_manager: "ApprovalManager | None" = None,
    ) -> None:
        super().__init__("slack")
        self.settings = settings
        self.approval_manager = approval_manager
        self._socket_client: Any = None
        self._web_client: Any = None
        self._bot_user_id: str | None = None
        self._running = False

    async def start(self) -> None:
        """Start the Slack bot with Socket Mode."""
        if not self.settings.bot_token:
            raise ValueError("Slack bot token not configured")
        if not self.settings.app_token:
            raise ValueError("Slack app token not configured (required for Socket Mode)")

        from slack_sdk.socket_mode.aiohttp import SocketModeClient
        from slack_sdk.web.async_client import AsyncWebClient

        # Initialize web client
        self._web_client = AsyncWebClient(token=self.settings.bot_token)

        # Get bot user ID for mention detection
        auth_response = await self._web_client.auth_test()
        self._bot_user_id = auth_response["user_id"]
        logger.info(f"Slack bot authenticated as user ID: {self._bot_user_id}")

        # Initialize socket mode client
        self._socket_client = SocketModeClient(
            app_token=self.settings.app_token,
            web_client=self._web_client,
        )

        # Register message handler
        self._socket_client.socket_mode_request_listeners.append(self._handle_socket_request)

        self._running = True
        logger.info("Starting Slack bot (Socket Mode)")

        # Connect to Slack
        await self._socket_client.connect()

    async def _handle_socket_request(self, client: Any, req: Any) -> None:
        """Handle incoming Socket Mode requests."""
        from slack_sdk.socket_mode.response import SocketModeResponse

        # Handle events_api requests (messages, etc.)
        if req.type == "events_api":
            # Acknowledge the request
            response = SocketModeResponse(envelope_id=req.envelope_id)
            await client.send_socket_mode_response(response)

            event = req.payload.get("event", {})
            event_type = event.get("type")

            if event_type == "message" or event_type == "app_mention":
                await self._handle_message_event(event)

    async def _handle_message_event(self, event: dict[str, Any]) -> None:
        """Handle a message event from Slack."""
        # Ignore bot messages and message edits/deletes
        if event.get("subtype") is not None:
            return

        # Ignore messages from bots
        if event.get("bot_id"):
            return

        channel_id = event.get("channel", "")
        user_id = event.get("user", "")
        text = event.get("text", "")
        ts = event.get("ts", "")
        thread_ts = event.get("thread_ts")

        # Check channel allowlist
        if (
            self.settings.allowed_channels
            and channel_id not in self.settings.allowed_channels
        ):
            logger.debug(f"Ignoring message from non-allowed channel: {channel_id}")
            return

        # Check for bot mention
        if not self._is_bot_mentioned(text):
            return

        # Remove bot mention from content
        content = self._remove_bot_mention(text)

        # Handle approval commands
        if content.startswith("approve "):
            await self._handle_approve(channel_id, user_id, content[8:].strip(), ts)
            return
        elif content.startswith("deny "):
            await self._handle_deny(channel_id, user_id, content[5:].strip(), ts)
            return

        if not content:
            return

        # Get user info for display name
        user_info = await self._web_client.users_info(user=user_id)
        user_name = user_info["user"].get("real_name") or user_info["user"].get("name", "Unknown")

        # Build channel message
        message = ChannelMessage(
            channel="slack",
            message_id=ts,
            sender_id=user_id,
            sender_name=user_name,
            content=content,
            timestamp=datetime.fromtimestamp(float(ts), tz=UTC),
            reply_to=thread_ts,
            metadata={
                "channel_id": channel_id,
                "thread_ts": thread_ts,
            },
        )
        await self._dispatch(message)

    def _is_bot_mentioned(self, text: str) -> bool:
        """Check if the bot is mentioned in the text."""
        if not self._bot_user_id:
            return False
        return f"<@{self._bot_user_id}>" in text

    def _remove_bot_mention(self, text: str) -> str:
        """Remove bot mention from text."""
        if not self._bot_user_id:
            return text
        return text.replace(f"<@{self._bot_user_id}>", "").strip()

    async def _handle_approve(
        self, channel_id: str, user_id: str, approval_id: str, ts: str
    ) -> None:
        """Handle approve command."""
        if not approval_id:
            await self._send_reply(channel_id, "❌ Usage: @bot approve <approval_id>", ts)
            return

        if self.approval_manager:
            from lurkbot.tools.approval import ApprovalDecision

            success = self.approval_manager.resolve(
                approval_id, ApprovalDecision.APPROVE, user_id
            )
            if success:
                await self._send_reply(
                    channel_id, f"✅ Approved tool execution: {approval_id}", ts
                )
                logger.info(f"User {user_id} approved {approval_id}")
            else:
                await self._send_reply(
                    channel_id,
                    f"❌ Approval not found or already resolved: {approval_id}",
                    ts,
                )
        else:
            await self._send_reply(channel_id, "❌ Approval system not configured", ts)

    async def _handle_deny(
        self, channel_id: str, user_id: str, approval_id: str, ts: str
    ) -> None:
        """Handle deny command."""
        if not approval_id:
            await self._send_reply(channel_id, "❌ Usage: @bot deny <approval_id>", ts)
            return

        if self.approval_manager:
            from lurkbot.tools.approval import ApprovalDecision

            success = self.approval_manager.resolve(approval_id, ApprovalDecision.DENY, user_id)
            if success:
                await self._send_reply(channel_id, f"🚫 Denied tool execution: {approval_id}", ts)
                logger.info(f"User {user_id} denied {approval_id}")
            else:
                await self._send_reply(
                    channel_id,
                    f"❌ Approval not found or already resolved: {approval_id}",
                    ts,
                )
        else:
            await self._send_reply(channel_id, "❌ Approval system not configured", ts)

    async def _send_reply(self, channel_id: str, text: str, thread_ts: str | None) -> None:
        """Send a reply message to a channel."""
        if self._web_client:
            await self._web_client.chat_postMessage(
                channel=channel_id,
                text=text,
                thread_ts=thread_ts,
            )

    async def stop(self) -> None:
        """Stop the Slack bot."""
        if self._socket_client and self._running:
            logger.info("Stopping Slack bot")
            await self._socket_client.close()
            self._running = False

    async def send(
        self,
        recipient_id: str,
        content: str,
        reply_to: str | None = None,
    ) -> str:
        """Send a message to a Slack channel.

        Args:
            recipient_id: The channel ID to send to
            content: The message content
            reply_to: Optional thread timestamp to reply in

        Returns:
            The sent message timestamp (Slack message ID)
        """
        if not self._web_client:
            raise RuntimeError("Slack bot not started")

        response = await self._web_client.chat_postMessage(
            channel=recipient_id,
            text=content,
            thread_ts=reply_to,
        )
        return response["ts"]

    async def send_typing(self, recipient_id: str) -> None:
        """Send a typing indicator.

        Note: Slack doesn't have a native typing indicator API for bots.
        This method is a no-op for Slack.
        """
        # Slack doesn't support typing indicators for bots via the Web API.
        # The RTM API supports it but requires a different connection type.
        # We'll log a debug message but do nothing.
        logger.debug(f"Typing indicator not supported for Slack channel: {recipient_id}")
