"""Discord channel adapter."""

from datetime import datetime
from typing import TYPE_CHECKING, Any

from loguru import logger

from lurkbot.channels.base import Channel, ChannelMessage
from lurkbot.config.settings import DiscordSettings

if TYPE_CHECKING:
    from lurkbot.tools.approval import ApprovalManager


class DiscordChannel(Channel):
    """Discord bot channel adapter.

    Features:
    - Mention-based activation: Bot responds only when @mentioned
    - Guild allowlist: Restrict bot to specific servers
    - Approval commands: /approve and /deny for tool approval workflow
    """

    def __init__(
        self,
        settings: DiscordSettings,
        approval_manager: "ApprovalManager | None" = None,
    ) -> None:
        super().__init__("discord")
        self.settings = settings
        self.approval_manager = approval_manager
        self._client: Any = None
        self._running = False

    async def start(self) -> None:
        """Start the Discord bot."""
        if not self.settings.bot_token:
            raise ValueError("Discord bot token not configured")

        import discord
        from discord.ext import commands

        # Set up intents
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.members = True

        # Create bot with command prefix (for /approve, /deny)
        bot = commands.Bot(command_prefix="!", intents=intents)
        self._client = bot

        @bot.event
        async def on_ready() -> None:
            logger.info(f"Discord bot logged in as {bot.user} (ID: {bot.user.id})")
            logger.info(f"Connected to {len(bot.guilds)} guilds")

        @bot.event
        async def on_message(message: discord.Message) -> None:
            # Ignore messages from the bot itself
            if message.author == bot.user:
                return

            # Ignore messages from other bots
            if message.author.bot:
                return

            # Check guild allowlist
            if (
                message.guild
                and self.settings.allowed_guilds
                and message.guild.id not in self.settings.allowed_guilds
            ):
                logger.debug(f"Ignoring message from non-allowed guild: {message.guild.id}")
                return

            # Check if bot is mentioned (mention gating)
            if bot.user not in message.mentions:
                # Process commands even without mention
                await bot.process_commands(message)
                return

            # Remove the bot mention from content
            content = message.content
            for mention in message.mentions:
                if mention == bot.user:
                    content = content.replace(f"<@{bot.user.id}>", "").replace(
                        f"<@!{bot.user.id}>", ""
                    )
            content = content.strip()

            if not content:
                return

            # Build channel message
            channel_message = ChannelMessage(
                channel="discord",
                message_id=str(message.id),
                sender_id=str(message.author.id),
                sender_name=message.author.display_name,
                content=content,
                timestamp=message.created_at or datetime.now(),
                reply_to=str(message.reference.message_id) if message.reference else None,
                metadata={
                    "guild_id": message.guild.id if message.guild else None,
                    "channel_id": message.channel.id,
                },
            )
            await self._dispatch(channel_message)

            # Process commands after handling message
            await bot.process_commands(message)

        @bot.command(name="approve")
        async def approve_cmd(ctx: commands.Context, approval_id: str) -> None:
            """Handle !approve command."""
            # Check guild allowlist
            if (
                ctx.guild
                and self.settings.allowed_guilds
                and ctx.guild.id not in self.settings.allowed_guilds
            ):
                return

            if self.approval_manager:
                from lurkbot.tools.approval import ApprovalDecision

                success = self.approval_manager.resolve(
                    approval_id, ApprovalDecision.APPROVE, str(ctx.author.id)
                )
                if success:
                    await ctx.send(f"✅ Approved tool execution: {approval_id}")
                    logger.info(f"User {ctx.author.id} approved {approval_id}")
                else:
                    await ctx.send(f"❌ Approval not found or already resolved: {approval_id}")
            else:
                await ctx.send("❌ Approval system not configured")

        @bot.command(name="deny")
        async def deny_cmd(ctx: commands.Context, approval_id: str) -> None:
            """Handle !deny command."""
            # Check guild allowlist
            if (
                ctx.guild
                and self.settings.allowed_guilds
                and ctx.guild.id not in self.settings.allowed_guilds
            ):
                return

            if self.approval_manager:
                from lurkbot.tools.approval import ApprovalDecision

                success = self.approval_manager.resolve(
                    approval_id, ApprovalDecision.DENY, str(ctx.author.id)
                )
                if success:
                    await ctx.send(f"🚫 Denied tool execution: {approval_id}")
                    logger.info(f"User {ctx.author.id} denied {approval_id}")
                else:
                    await ctx.send(f"❌ Approval not found or already resolved: {approval_id}")
            else:
                await ctx.send("❌ Approval system not configured")

        self._running = True
        logger.info("Starting Discord bot")

        # Run the bot (non-blocking)
        import asyncio

        asyncio.create_task(bot.start(self.settings.bot_token))

    async def stop(self) -> None:
        """Stop the Discord bot."""
        if self._client and self._running:
            logger.info("Stopping Discord bot")
            await self._client.close()
            self._running = False

    async def send(
        self,
        recipient_id: str,
        content: str,
        reply_to: str | None = None,
    ) -> str:
        """Send a message to a Discord channel.

        Args:
            recipient_id: The channel ID to send to
            content: The message content
            reply_to: Optional message ID to reply to

        Returns:
            The sent message ID
        """
        if not self._client:
            raise RuntimeError("Discord bot not started")

        channel = self._client.get_channel(int(recipient_id))
        if channel is None:
            channel = await self._client.fetch_channel(int(recipient_id))

        # Build reference for reply
        reference = None
        if reply_to:
            import discord

            reference = discord.MessageReference(
                message_id=int(reply_to), channel_id=int(recipient_id)
            )

        message = await channel.send(content, reference=reference)
        return str(message.id)

    async def send_typing(self, recipient_id: str) -> None:
        """Send a typing indicator to a Discord channel."""
        if not self._client:
            raise RuntimeError("Discord bot not started")

        channel = self._client.get_channel(int(recipient_id))
        if channel is None:
            channel = await self._client.fetch_channel(int(recipient_id))

        await channel.typing()
