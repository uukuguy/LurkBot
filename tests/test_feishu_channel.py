"""Tests for Feishu channel adapter."""

import pytest
from unittest.mock import Mock, patch
from lurkbot.channels.feishu import FeishuChannel, FeishuConfig


@pytest.fixture
def feishu_webhook_config():
    """Create test Feishu webhook configuration."""
    return {
        "webhook_url": "https://open.feishu.cn/open-apis/bot/v2/hook/test_token",
        "enabled": True,
    }


@pytest.fixture
def feishu_openapi_config():
    """Create test Feishu OpenAPI configuration."""
    return {
        "app_id": "cli_test_app",
        "app_secret": "test_secret",
        "enabled": True,
    }


@pytest.fixture
def feishu_webhook_channel(feishu_webhook_config):
    """Create test Feishu channel in webhook mode."""
    with patch("lurkbot.channels.feishu.adapter.LarkWebhook"):
        return FeishuChannel(feishu_webhook_config)


@pytest.fixture
def feishu_openapi_channel(feishu_openapi_config):
    """Create test Feishu channel in OpenAPI mode."""
    return FeishuChannel(feishu_openapi_config)


class TestFeishuConfig:
    """Test Feishu configuration."""

    def test_webhook_config_creation(self):
        """Test creating webhook config."""
        config = FeishuConfig(
            webhook_url="https://open.feishu.cn/open-apis/bot/v2/hook/xxx"
        )

        assert config.webhook_url is not None
        assert config.enabled is True

    def test_openapi_config_creation(self):
        """Test creating OpenAPI config."""
        config = FeishuConfig(
            app_id="cli_xxx",
            app_secret="secret"
        )

        assert config.app_id == "cli_xxx"
        assert config.app_secret == "secret"
        assert config.enabled is True


class TestFeishuChannel:
    """Test Feishu channel adapter."""

    def test_webhook_channel_initialization(self, feishu_webhook_config):
        """Test webhook channel initialization."""
        with patch("lurkbot.channels.feishu.adapter.LarkWebhook") as mock_bot:
            channel = FeishuChannel(feishu_webhook_config)

            # Verify bot was initialized
            mock_bot.assert_called_once_with(feishu_webhook_config["webhook_url"])
            assert channel.mode == "webhook"

    def test_openapi_channel_initialization(self, feishu_openapi_config):
        """Test OpenAPI channel initialization."""
        channel = FeishuChannel(feishu_openapi_config)

        assert channel.mode == "openapi"
        assert channel.app_id == "cli_test_app"

    def test_missing_config(self):
        """Test initialization with missing config."""
        invalid_config = {"enabled": True}  # No webhook or app credentials

        with pytest.raises(ValueError, match="Either webhook_url or"):
            FeishuChannel(invalid_config)

    @pytest.mark.asyncio
    async def test_send_webhook_message(self, feishu_webhook_channel):
        """Test sending message in webhook mode."""
        feishu_webhook_channel.bot.text = Mock()

        result = await feishu_webhook_channel.send("", "Hello Feishu!")

        assert result["sent"] is True
        assert result["channel"] == "webhook"
        assert result["content"] == "Hello Feishu!"

        feishu_webhook_channel.bot.text.assert_called_once_with("Hello Feishu!")

    @pytest.mark.asyncio
    async def test_send_openapi_message(self, feishu_openapi_channel):
        """Test sending message in OpenAPI mode."""
        result = await feishu_openapi_channel.send("ou_123", "Hello user!")

        assert result["sent"] is True
        assert result["channel"] == "ou_123"
        assert result["content"] == "Hello user!"

    @pytest.mark.asyncio
    async def test_send_error(self, feishu_webhook_channel):
        """Test handling send error."""
        feishu_webhook_channel.bot.text = Mock(side_effect=Exception("API Error"))

        result = await feishu_webhook_channel.send("", "Test")

        assert result["sent"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_send_card(self, feishu_webhook_channel):
        """Test sending card message."""
        feishu_webhook_channel.bot.card = Mock()

        result = await feishu_webhook_channel.send_card(
            "",
            "Card Title",
            "Card Content",
            buttons=[{"content": "Link", "url": "https://example.com"}]
        )

        assert result["sent"] is True
        assert result["title"] == "Card Title"

    @pytest.mark.asyncio
    async def test_send_rich_text(self, feishu_webhook_channel):
        """Test sending rich text."""
        feishu_webhook_channel.bot.text = Mock()

        payload = [
            {"tag": "text", "text": "Hello "},
            {"tag": "a", "text": "Link", "href": "https://example.com"}
        ]

        result = await feishu_webhook_channel.send_rich_text("", payload, "Title")

        assert result["sent"] is True
        assert result["title"] == "Title"

    @pytest.mark.asyncio
    async def test_delete_limited_support(self, feishu_webhook_channel):
        """Test that delete has limited support."""
        result = await feishu_webhook_channel.delete("", "msg_123")

        assert result["deleted"] is False
        assert "limited support" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_react_not_supported(self, feishu_webhook_channel):
        """Test that react is not supported in webhook mode."""
        result = await feishu_webhook_channel.react("", "msg_123", "👍")

        assert result["reacted"] is False
        assert "not supported" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_pin_requires_admin(self, feishu_webhook_channel):
        """Test that pin requires admin permissions."""
        result = await feishu_webhook_channel.pin("", "msg_123")

        assert result["pinned"] is False
        assert "admin" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_unpin_requires_admin(self, feishu_webhook_channel):
        """Test that unpin requires admin permissions."""
        result = await feishu_webhook_channel.unpin("", "msg_123")

        assert result["unpinned"] is False
        assert "admin" in result["error"].lower()
