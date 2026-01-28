"""Channel registry for unified channel management."""

from typing import TYPE_CHECKING

from loguru import logger

from lurkbot.channels.base import Channel
from lurkbot.config.settings import Settings

if TYPE_CHECKING:
    from lurkbot.tools.approval import ApprovalManager


class ChannelRegistry:
    """Registry for managing multiple channel adapters.

    Features:
    - Dynamic channel loading based on settings
    - Unified start/stop for all channels
    - Channel lookup by name
    - List active channels
    """

    def __init__(
        self,
        settings: Settings,
        approval_manager: "ApprovalManager | None" = None,
    ) -> None:
        """Initialize the channel registry.

        Args:
            settings: Application settings
            approval_manager: Optional approval manager for tool approval commands
        """
        self.settings = settings
        self.approval_manager = approval_manager
        self._channels: dict[str, Channel] = {}
        self._initialized = False

    def _load_channels(self) -> None:
        """Load and initialize enabled channels based on settings."""
        if self._initialized:
            return

        # Load Telegram channel
        if self.settings.telegram.enabled:
            from lurkbot.channels.telegram import TelegramChannel

            telegram = TelegramChannel(
                settings=self.settings.telegram,
                approval_manager=self.approval_manager,
            )
            self._channels["telegram"] = telegram
            logger.info("Telegram channel loaded")

        # Load Discord channel
        if self.settings.discord.enabled:
            from lurkbot.channels.discord import DiscordChannel

            discord = DiscordChannel(
                settings=self.settings.discord,
                approval_manager=self.approval_manager,
            )
            self._channels["discord"] = discord
            logger.info("Discord channel loaded")

        # Load Slack channel
        if self.settings.slack.enabled:
            from lurkbot.channels.slack import SlackChannel

            slack = SlackChannel(
                settings=self.settings.slack,
                approval_manager=self.approval_manager,
            )
            self._channels["slack"] = slack
            logger.info("Slack channel loaded")

        self._initialized = True

    async def start_all(self) -> None:
        """Start all enabled channels."""
        self._load_channels()

        if not self._channels:
            logger.warning("No channels enabled. Enable at least one channel in settings.")
            return

        for name, channel in self._channels.items():
            try:
                await channel.start()
                logger.info(f"Channel '{name}' started successfully")
            except Exception as e:
                logger.error(f"Failed to start channel '{name}': {e}")

    async def stop_all(self) -> None:
        """Stop all running channels."""
        for name, channel in self._channels.items():
            try:
                await channel.stop()
                logger.info(f"Channel '{name}' stopped")
            except Exception as e:
                logger.error(f"Error stopping channel '{name}': {e}")

    def get(self, name: str) -> Channel | None:
        """Get a channel by name.

        Args:
            name: The channel name (e.g., 'telegram', 'discord', 'slack')

        Returns:
            The channel adapter if found, None otherwise
        """
        self._load_channels()
        return self._channels.get(name)

    def list_channels(self) -> list[str]:
        """List all loaded channel names.

        Returns:
            List of channel names
        """
        self._load_channels()
        return list(self._channels.keys())

    def is_enabled(self, name: str) -> bool:
        """Check if a channel is enabled.

        Args:
            name: The channel name

        Returns:
            True if the channel is enabled, False otherwise
        """
        self._load_channels()
        return name in self._channels

    def __len__(self) -> int:
        """Return the number of loaded channels."""
        self._load_channels()
        return len(self._channels)

    def __iter__(self):
        """Iterate over loaded channels."""
        self._load_channels()
        return iter(self._channels.values())

    def items(self):
        """Return channel name-instance pairs."""
        self._load_channels()
        return self._channels.items()
