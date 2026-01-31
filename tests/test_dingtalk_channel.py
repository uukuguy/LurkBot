"""Tests for DingTalk channel adapter."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from lurkbot.channels.dingtalk import DingTalkChannel, DingTalkConfig


@pytest.fixture
def dingtalk_config():
    """Create test DingTalk configuration."""
    return {
        "client_id": "test_client_id",
        "client_secret": "test_client_secret",
        "robot_code": "test_robot",
        "enabled": True,
    }


@pytest.fixture
def dingtalk_channel(dingtalk_config):
    """Create test DingTalk channel instance."""
    with patch("lurkbot.channels.dingtalk.adapter.dingtalk_stream.Credential"):
        return DingTalkChannel(dingtalk_config)


class TestDingTalkConfig:
    """Test DingTalk configuration."""

    def test_config_creation(self):
        """Test creating DingTalk config."""
        config = DingTalkConfig(
            client_id="test_client",
            client_secret="test_secret",
            robot_code="test_robot",
        )

        assert config.client_id == "test_client"
        assert config.client_secret == "test_secret"
        assert config.robot_code == "test_robot"
        assert config.enabled is True


class TestDingTalkChannel:
    """Test DingTalk channel adapter."""

    def test_channel_initialization(self, dingtalk_config):
        """Test channel initialization."""
        with patch("lurkbot.channels.dingtalk.adapter.dingtalk_stream.Credential") as mock_cred:
            channel = DingTalkChannel(dingtalk_config)

            # Verify credential was created
            mock_cred.assert_called_once_with(
                dingtalk_config["client_id"],
                dingtalk_config["client_secret"]
            )

            assert channel.config == dingtalk_config

    def test_missing_config_field(self):
        """Test initialization with missing config field."""
        invalid_config = {
            "client_id": "test",
            # Missing client_secret
        }

        with pytest.raises(ValueError, match="Missing required config field"):
            DingTalkChannel(invalid_config)

    @pytest.mark.asyncio
    async def test_send_text_message(self, dingtalk_channel):
        """Test sending text message."""
        # Mock the API
        dingtalk_channel._message_api.send_text = AsyncMock(
            return_value={
                "errcode": 0,
                "errmsg": "ok",
                "message_id": "msg_123",
            }
        )

        # Send message
        result = await dingtalk_channel.send("conv_123", "Hello DingTalk!")

        # Verify result
        assert result["sent"] is True
        assert result["channel"] == "conv_123"
        assert result["content"] == "Hello DingTalk!"

        # Verify API was called
        dingtalk_channel._message_api.send_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_text_with_at_users(self, dingtalk_channel):
        """Test sending text with @mentions."""
        dingtalk_channel._message_api.send_text = AsyncMock(
            return_value={"errcode": 0, "message_id": "msg_456"}
        )

        result = await dingtalk_channel.send(
            "conv_123",
            "Hello @user",
            at_users=["user1", "user2"]
        )

        assert result["sent"] is True
        dingtalk_channel._message_api.send_text.assert_called_once_with(
            conversation_id="conv_123",
            content="Hello @user",
            at_users=["user1", "user2"],
            at_mobiles=[],
            is_at_all=False
        )

    @pytest.mark.asyncio
    async def test_send_text_error(self, dingtalk_channel):
        """Test handling send message error."""
        dingtalk_channel._message_api.send_text = AsyncMock(
            side_effect=Exception("API Error")
        )

        result = await dingtalk_channel.send("conv_123", "Test")

        assert result["sent"] is False
        assert "error" in result
        assert "API Error" in result["error"]

    @pytest.mark.asyncio
    async def test_send_markdown(self, dingtalk_channel):
        """Test sending markdown message."""
        dingtalk_channel._message_api.send_markdown = AsyncMock(
            return_value={"errcode": 0, "message_id": "md_789"}
        )

        result = await dingtalk_channel.send_markdown(
            "conv_123",
            "Title",
            "# Markdown Content"
        )

        assert result["sent"] is True
        assert result["title"] == "Title"

    @pytest.mark.asyncio
    async def test_send_card(self, dingtalk_channel):
        """Test sending card message."""
        card_data = {"template_id": "card_123", "content": "data"}

        dingtalk_channel._message_api.send_card = AsyncMock(
            return_value={"errcode": 0, "message_id": "card_999"}
        )

        result = await dingtalk_channel.send_card("conv_123", card_data)

        assert result["sent"] is True

    @pytest.mark.asyncio
    async def test_delete_limited_support(self, dingtalk_channel):
        """Test that delete has limited support."""
        result = await dingtalk_channel.delete("conv_123", "msg_123")

        assert result["deleted"] is False
        assert "limited support" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_react_not_supported(self, dingtalk_channel):
        """Test that react is not supported."""
        result = await dingtalk_channel.react("conv_123", "msg_123", "👍")

        assert result["reacted"] is False
        assert "not supported" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_pin_not_supported(self, dingtalk_channel):
        """Test that pin is not supported."""
        result = await dingtalk_channel.pin("conv_123", "msg_123")

        assert result["pinned"] is False
        assert "not supported" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_unpin_not_supported(self, dingtalk_channel):
        """Test that unpin is not supported."""
        result = await dingtalk_channel.unpin("conv_123", "msg_123")

        assert result["unpinned"] is False
        assert "not supported" in result["error"].lower()
