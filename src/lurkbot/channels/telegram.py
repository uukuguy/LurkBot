"""Telegram channel adapter."""

from datetime import datetime
from typing import TYPE_CHECKING, Any

from loguru import logger

from lurkbot.channels.base import Channel, ChannelMessage
from lurkbot.config.settings import TelegramSettings

if TYPE_CHECKING:
    from lurkbot.tools.approval import ApprovalDecision, ApprovalManager


class TelegramChannel(Channel):
    """Telegram bot channel adapter."""

    def __init__(
        self,
        settings: TelegramSettings,
        approval_manager: "ApprovalManager | None" = None,
    ) -> None:
        super().__init__("telegram")
        self.settings = settings
        self.approval_manager = approval_manager
        self._app: Any = None
        self._running = False

    async def start(self) -> None:
        """Start the Telegram bot."""
        if not self.settings.bot_token:
            raise ValueError("Telegram bot token not configured")

        from telegram import Update
        from telegram.ext import (
            Application,
            CommandHandler,
            MessageHandler,
            filters,
        )

        self._app = Application.builder().token(self.settings.bot_token).build()

        async def handle_message(update: Update, context: Any) -> None:
            if update.message is None or update.message.text is None:
                return

            user = update.message.from_user
            if user is None:
                return

            # Check allowlist
            if self.settings.allowed_users and user.id not in self.settings.allowed_users:
                logger.warning(f"Ignoring message from non-allowed user: {user.id}")
                return

            message = ChannelMessage(
                channel="telegram",
                message_id=str(update.message.message_id),
                sender_id=str(user.id),
                sender_name=user.full_name,
                content=update.message.text,
                timestamp=update.message.date or datetime.now(),
                reply_to=(
                    str(update.message.reply_to_message.message_id)
                    if update.message.reply_to_message
                    else None
                ),
                metadata={"chat_id": update.message.chat_id},
            )
            await self._dispatch(message)

        async def handle_approve(update: Update, context: Any) -> None:
            """Handle /approve command."""
            if update.message is None or not context.args:
                return

            user = update.message.from_user
            if user is None:
                return

            # Check allowlist
            if self.settings.allowed_users and user.id not in self.settings.allowed_users:
                logger.warning(f"Ignoring command from non-allowed user: {user.id}")
                return

            approval_id = context.args[0]
            if self.approval_manager:
                from lurkbot.tools.approval import ApprovalDecision

                success = self.approval_manager.resolve(
                    approval_id, ApprovalDecision.APPROVE, str(user.id)
                )
                if success:
                    await update.message.reply_text(f"✅ Approved tool execution: {approval_id}")
                    logger.info(f"User {user.id} approved {approval_id}")
                else:
                    await update.message.reply_text(f"❌ Approval not found or already resolved: {approval_id}")
            else:
                await update.message.reply_text("❌ Approval system not configured")

        async def handle_deny(update: Update, context: Any) -> None:
            """Handle /deny command."""
            if update.message is None or not context.args:
                return

            user = update.message.from_user
            if user is None:
                return

            # Check allowlist
            if self.settings.allowed_users and user.id not in self.settings.allowed_users:
                logger.warning(f"Ignoring command from non-allowed user: {user.id}")
                return

            approval_id = context.args[0]
            if self.approval_manager:
                from lurkbot.tools.approval import ApprovalDecision

                success = self.approval_manager.resolve(
                    approval_id, ApprovalDecision.DENY, str(user.id)
                )
                if success:
                    await update.message.reply_text(f"🚫 Denied tool execution: {approval_id}")
                    logger.info(f"User {user.id} denied {approval_id}")
                else:
                    await update.message.reply_text(f"❌ Approval not found or already resolved: {approval_id}")
            else:
                await update.message.reply_text("❌ Approval system not configured")

        self._app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        self._app.add_handler(CommandHandler("approve", handle_approve))
        self._app.add_handler(CommandHandler("deny", handle_deny))

        self._running = True
        logger.info("Starting Telegram bot")
        await self._app.initialize()
        await self._app.start()
        await self._app.updater.start_polling()  # type: ignore

    async def stop(self) -> None:
        """Stop the Telegram bot."""
        if self._app and self._running:
            logger.info("Stopping Telegram bot")
            await self._app.updater.stop()  # type: ignore
            await self._app.stop()
            await self._app.shutdown()
            self._running = False

    async def send(
        self,
        recipient_id: str,
        content: str,
        reply_to: str | None = None,
    ) -> str:
        """Send a message to a Telegram chat."""
        if not self._app:
            raise RuntimeError("Telegram bot not started")

        message = await self._app.bot.send_message(
            chat_id=int(recipient_id),
            text=content,
            reply_to_message_id=int(reply_to) if reply_to else None,
        )
        return str(message.message_id)

    async def send_typing(self, recipient_id: str) -> None:
        """Send a typing indicator."""
        if not self._app:
            raise RuntimeError("Telegram bot not started")

        await self._app.bot.send_chat_action(
            chat_id=int(recipient_id),
            action="typing",
        )
