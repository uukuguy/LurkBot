"""Tests for channel adapters."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from lurkbot.channels.base import Channel, ChannelMessage
from lurkbot.config.settings import DiscordSettings, Settings, SlackSettings, TelegramSettings

# =============================================================================
# Base Channel Tests
# =============================================================================


class TestChannelMessage:
    """Tests for ChannelMessage dataclass."""

    def test_create_minimal_message(self):
        """Test creating message with minimal fields."""
        msg = ChannelMessage(
            channel="test",
            message_id="123",
            sender_id="user1",
            sender_name="Test User",
            content="Hello",
        )
        assert msg.channel == "test"
        assert msg.message_id == "123"
        assert msg.sender_id == "user1"
        assert msg.content == "Hello"
        assert msg.reply_to is None
        assert msg.attachments == []
        assert msg.metadata == {}

    def test_create_full_message(self):
        """Test creating message with all fields."""
        timestamp = datetime.now()
        msg = ChannelMessage(
            channel="discord",
            message_id="456",
            sender_id="user2",
            sender_name="Full User",
            content="Hello World",
            timestamp=timestamp,
            reply_to="123",
            attachments=[{"type": "image", "url": "http://example.com/img.png"}],
            metadata={"guild_id": 789},
        )
        assert msg.channel == "discord"
        assert msg.timestamp == timestamp
        assert msg.reply_to == "123"
        assert len(msg.attachments) == 1
        assert msg.metadata["guild_id"] == 789


class ConcreteChannel(Channel):
    """Concrete implementation for testing."""

    async def start(self):
        pass

    async def stop(self):
        pass

    async def send(
        self,
        recipient_id: str,  # noqa: ARG002
        content: str,  # noqa: ARG002
        reply_to: str | None = None,  # noqa: ARG002
    ) -> str:
        return "sent_123"

    async def send_typing(self, recipient_id: str) -> None:
        pass


class TestChannelBase:
    """Tests for Channel base class."""

    def test_channel_initialization(self):
        """Test channel initialization."""
        channel = ConcreteChannel("test")
        assert channel.name == "test"
        assert channel._handlers == []

    def test_register_handler(self):
        """Test registering message handler."""
        channel = ConcreteChannel("test")

        async def handler(msg: ChannelMessage) -> None:
            pass

        result = channel.on_message(handler)
        assert result == handler
        assert handler in channel._handlers

    async def test_dispatch_to_handlers(self):
        """Test dispatching messages to handlers."""
        channel = ConcreteChannel("test")
        received = []

        async def handler(msg: ChannelMessage) -> None:
            received.append(msg)

        channel.on_message(handler)

        msg = ChannelMessage(
            channel="test",
            message_id="1",
            sender_id="user",
            sender_name="User",
            content="test",
        )
        await channel._dispatch(msg)

        assert len(received) == 1
        assert received[0].content == "test"


# =============================================================================
# Discord Channel Tests
# =============================================================================


class TestDiscordChannel:
    """Tests for Discord channel adapter."""

    @pytest.fixture
    def discord_settings(self):
        """Create Discord settings."""
        return DiscordSettings(
            enabled=True,
            bot_token="test_token",
            allowed_guilds=[123456789],
        )

    def test_discord_channel_initialization(self, discord_settings):
        """Test Discord channel initialization."""
        from lurkbot.channels.discord import DiscordChannel

        channel = DiscordChannel(settings=discord_settings)
        assert channel.name == "discord"
        assert channel.settings == discord_settings
        assert channel._client is None
        assert not channel._running

    async def test_discord_start_without_token(self):
        """Test Discord channel fails without token."""
        from lurkbot.channels.discord import DiscordChannel

        settings = DiscordSettings(enabled=True, bot_token=None)
        channel = DiscordChannel(settings=settings)

        with pytest.raises(ValueError, match="Discord bot token not configured"):
            await channel.start()

    async def test_discord_send_without_start(self, discord_settings):
        """Test send fails if bot not started."""
        from lurkbot.channels.discord import DiscordChannel

        channel = DiscordChannel(settings=discord_settings)

        with pytest.raises(RuntimeError, match="Discord bot not started"):
            await channel.send("123", "Hello")

    async def test_discord_send_typing_without_start(self, discord_settings):
        """Test send_typing fails if bot not started."""
        from lurkbot.channels.discord import DiscordChannel

        channel = DiscordChannel(settings=discord_settings)

        with pytest.raises(RuntimeError, match="Discord bot not started"):
            await channel.send_typing("123")

    async def test_discord_stop_when_not_running(self, discord_settings):
        """Test stop does nothing when not running."""
        from lurkbot.channels.discord import DiscordChannel

        channel = DiscordChannel(settings=discord_settings)
        await channel.stop()  # Should not raise


# =============================================================================
# Slack Channel Tests
# =============================================================================


class TestSlackChannel:
    """Tests for Slack channel adapter."""

    @pytest.fixture
    def slack_settings(self):
        """Create Slack settings."""
        return SlackSettings(
            enabled=True,
            bot_token="xoxb-test-token",
            app_token="xapp-test-token",
            allowed_channels=["C123456"],
        )

    def test_slack_channel_initialization(self, slack_settings):
        """Test Slack channel initialization."""
        from lurkbot.channels.slack import SlackChannel

        channel = SlackChannel(settings=slack_settings)
        assert channel.name == "slack"
        assert channel.settings == slack_settings
        assert channel._socket_client is None
        assert channel._web_client is None
        assert channel._bot_user_id is None
        assert not channel._running

    async def test_slack_start_without_bot_token(self):
        """Test Slack channel fails without bot token."""
        from lurkbot.channels.slack import SlackChannel

        settings = SlackSettings(enabled=True, bot_token=None, app_token="xapp-test")
        channel = SlackChannel(settings=settings)

        with pytest.raises(ValueError, match="Slack bot token not configured"):
            await channel.start()

    async def test_slack_start_without_app_token(self):
        """Test Slack channel fails without app token."""
        from lurkbot.channels.slack import SlackChannel

        settings = SlackSettings(enabled=True, bot_token="xoxb-test", app_token=None)
        channel = SlackChannel(settings=settings)

        with pytest.raises(ValueError, match="Slack app token not configured"):
            await channel.start()

    async def test_slack_send_without_start(self, slack_settings):
        """Test send fails if bot not started."""
        from lurkbot.channels.slack import SlackChannel

        channel = SlackChannel(settings=slack_settings)

        with pytest.raises(RuntimeError, match="Slack bot not started"):
            await channel.send("C123", "Hello")

    def test_slack_is_bot_mentioned(self, slack_settings):
        """Test bot mention detection."""
        from lurkbot.channels.slack import SlackChannel

        channel = SlackChannel(settings=slack_settings)
        channel._bot_user_id = "U12345"

        assert channel._is_bot_mentioned("<@U12345> hello") is True
        assert channel._is_bot_mentioned("hello <@U12345>") is True
        assert channel._is_bot_mentioned("hello world") is False
        assert channel._is_bot_mentioned("<@U99999> hello") is False

    def test_slack_remove_bot_mention(self, slack_settings):
        """Test removing bot mention from text."""
        from lurkbot.channels.slack import SlackChannel

        channel = SlackChannel(settings=slack_settings)
        channel._bot_user_id = "U12345"

        assert channel._remove_bot_mention("<@U12345> hello") == "hello"
        assert channel._remove_bot_mention("hello <@U12345>") == "hello"
        assert channel._remove_bot_mention("<@U12345>  hello  <@U12345>") == "hello"
        assert channel._remove_bot_mention("no mention") == "no mention"

    async def test_slack_send_typing_is_noop(self, slack_settings):
        """Test send_typing is a no-op for Slack."""
        from lurkbot.channels.slack import SlackChannel

        channel = SlackChannel(settings=slack_settings)
        channel._web_client = MagicMock()  # Prevent RuntimeError

        # Should not raise, just log
        await channel.send_typing("C123")

    async def test_slack_stop_when_not_running(self, slack_settings):
        """Test stop does nothing when not running."""
        from lurkbot.channels.slack import SlackChannel

        channel = SlackChannel(settings=slack_settings)
        await channel.stop()  # Should not raise


# =============================================================================
# Channel Registry Tests
# =============================================================================


class TestChannelRegistry:
    """Tests for channel registry."""

    @pytest.fixture
    def settings_no_channels(self):
        """Create settings with no channels enabled."""
        return Settings(
            telegram=TelegramSettings(enabled=False),
            discord=DiscordSettings(enabled=False),
            slack=SlackSettings(enabled=False),
        )

    @pytest.fixture
    def settings_telegram_only(self):
        """Create settings with only Telegram enabled."""
        return Settings(
            telegram=TelegramSettings(enabled=True, bot_token="test_token"),
            discord=DiscordSettings(enabled=False),
            slack=SlackSettings(enabled=False),
        )

    @pytest.fixture
    def settings_all_channels(self):
        """Create settings with all channels enabled."""
        return Settings(
            telegram=TelegramSettings(enabled=True, bot_token="tg_token"),
            discord=DiscordSettings(enabled=True, bot_token="dc_token"),
            slack=SlackSettings(enabled=True, bot_token="slack_bot", app_token="slack_app"),
        )

    def test_registry_initialization(self, settings_no_channels):
        """Test registry initialization."""
        from lurkbot.channels.registry import ChannelRegistry

        registry = ChannelRegistry(settings=settings_no_channels)
        assert registry.settings == settings_no_channels
        assert registry.approval_manager is None
        assert not registry._initialized

    def test_registry_load_no_channels(self, settings_no_channels):
        """Test loading with no channels enabled."""
        from lurkbot.channels.registry import ChannelRegistry

        registry = ChannelRegistry(settings=settings_no_channels)
        channels = registry.list_channels()
        assert channels == []
        assert len(registry) == 0

    def test_registry_load_telegram_only(self, settings_telegram_only):
        """Test loading with only Telegram enabled."""
        from lurkbot.channels.registry import ChannelRegistry

        registry = ChannelRegistry(settings=settings_telegram_only)
        channels = registry.list_channels()
        assert "telegram" in channels
        assert len(registry) == 1

    def test_registry_load_all_channels(self, settings_all_channels):
        """Test loading with all channels enabled."""
        from lurkbot.channels.registry import ChannelRegistry

        registry = ChannelRegistry(settings=settings_all_channels)
        channels = registry.list_channels()
        assert "telegram" in channels
        assert "discord" in channels
        assert "slack" in channels
        assert len(registry) == 3

    def test_registry_get_channel(self, settings_telegram_only):
        """Test getting channel by name."""
        from lurkbot.channels.registry import ChannelRegistry
        from lurkbot.channels.telegram import TelegramChannel

        registry = ChannelRegistry(settings=settings_telegram_only)

        telegram = registry.get("telegram")
        assert telegram is not None
        assert isinstance(telegram, TelegramChannel)

        nonexistent = registry.get("nonexistent")
        assert nonexistent is None

    def test_registry_is_enabled(self, settings_telegram_only):
        """Test checking if channel is enabled."""
        from lurkbot.channels.registry import ChannelRegistry

        registry = ChannelRegistry(settings=settings_telegram_only)

        assert registry.is_enabled("telegram") is True
        assert registry.is_enabled("discord") is False
        assert registry.is_enabled("slack") is False

    def test_registry_iteration(self, settings_all_channels):
        """Test iterating over channels."""
        from lurkbot.channels.registry import ChannelRegistry

        registry = ChannelRegistry(settings=settings_all_channels)

        channel_names = [channel.name for channel in registry]
        assert "telegram" in channel_names
        assert "discord" in channel_names
        assert "slack" in channel_names

    def test_registry_items(self, settings_all_channels):
        """Test getting channel name-instance pairs."""
        from lurkbot.channels.registry import ChannelRegistry

        registry = ChannelRegistry(settings=settings_all_channels)

        items = dict(registry.items())
        assert "telegram" in items
        assert "discord" in items
        assert "slack" in items

    async def test_registry_start_all_no_channels(self, settings_no_channels):
        """Test starting with no channels."""
        from lurkbot.channels.registry import ChannelRegistry

        registry = ChannelRegistry(settings=settings_no_channels)
        await registry.start_all()  # Should log warning but not raise

    @patch("lurkbot.channels.telegram.TelegramChannel.start", new_callable=AsyncMock)
    async def test_registry_start_all(self, mock_start, settings_telegram_only):
        """Test starting all channels."""
        from lurkbot.channels.registry import ChannelRegistry

        registry = ChannelRegistry(settings=settings_telegram_only)
        await registry.start_all()

        mock_start.assert_called_once()

    @patch("lurkbot.channels.telegram.TelegramChannel.start", new_callable=AsyncMock)
    @patch("lurkbot.channels.telegram.TelegramChannel.stop", new_callable=AsyncMock)
    async def test_registry_stop_all(
        self,
        mock_stop,
        mock_start,  # noqa: ARG002
        settings_telegram_only,
    ):
        """Test stopping all channels."""
        from lurkbot.channels.registry import ChannelRegistry

        registry = ChannelRegistry(settings=settings_telegram_only)
        await registry.start_all()
        await registry.stop_all()

        mock_stop.assert_called_once()

    @patch("lurkbot.channels.telegram.TelegramChannel.start", new_callable=AsyncMock)
    async def test_registry_start_handles_errors(self, mock_start, settings_telegram_only):
        """Test that start_all handles errors gracefully."""
        from lurkbot.channels.registry import ChannelRegistry

        mock_start.side_effect = Exception("Connection failed")

        registry = ChannelRegistry(settings=settings_telegram_only)
        await registry.start_all()  # Should not raise, just log error
