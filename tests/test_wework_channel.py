"""Tests for WeWork channel adapter."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from lurkbot.channels.wework import WeWorkChannel, WeWorkConfig


@pytest.fixture
def wework_config():
    """Create test WeWork configuration."""
    return {
        "corp_id": "test_corp_id",
        "secret": "test_secret",
        "agent_id": "1000001",
        "token": "test_token",
        "encoding_aes_key": "test_aes_key_1234567890123456789012345678901234567890123",
        "enabled": True,
    }


@pytest.fixture
def wework_channel(wework_config):
    """Create test WeWork channel instance."""
    with patch("lurkbot.channels.wework.adapter.WeChatClient"):
        with patch("lurkbot.channels.wework.adapter.WeChatCrypto"):
            return WeWorkChannel(wework_config)


class TestWeWorkConfig:
    """Test WeWork configuration."""

    def test_config_creation(self):
        """Test creating WeWork config."""
        config = WeWorkConfig(
            corp_id="test_corp",
            secret="test_secret",
            agent_id="1000001",
            token="test_token",
            encoding_aes_key="test_key" * 10,
        )

        assert config.corp_id == "test_corp"
        assert config.secret == "test_secret"
        assert config.agent_id == "1000001"
        assert config.enabled is True

    def test_config_validation(self):
        """Test config field validation."""
        with pytest.raises(Exception):
            # Missing required fields should raise error
            WeWorkConfig()  # type: ignore


class TestWeWorkChannel:
    """Test WeWork channel adapter."""

    def test_channel_initialization(self, wework_config):
        """Test channel initialization."""
        with patch("lurkbot.channels.wework.adapter.WeChatClient") as mock_client:
            with patch("lurkbot.channels.wework.adapter.WeChatCrypto") as mock_crypto:
                channel = WeWorkChannel(wework_config)

                # Verify client was initialized with correct params
                mock_client.assert_called_once_with(
                    wework_config["corp_id"],
                    wework_config["secret"]
                )

                # Verify crypto was initialized
                mock_crypto.assert_called_once()

                assert channel.config == wework_config

    def test_missing_config_field(self):
        """Test initialization with missing config field."""
        invalid_config = {
            "corp_id": "test",
            # Missing other required fields
        }

        with pytest.raises(ValueError, match="Missing required config field"):
            WeWorkChannel(invalid_config)

    @pytest.mark.asyncio
    async def test_send_text_message(self, wework_channel):
        """Test sending text message."""
        # Mock the send_text method
        mock_response = {
            "errcode": 0,
            "errmsg": "ok",
            "msgid": "msg_123456",
        }

        wework_channel.client.message.send_text = Mock(return_value=mock_response)

        # Send message
        result = await wework_channel.send("user123", "Hello World!")

        # Verify result
        assert result["sent"] is True
        assert result["channel"] == "user123"
        assert result["content"] == "Hello World!"
        assert result["message_id"] == "msg_123456"

        # Verify API was called correctly
        wework_channel.client.message.send_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_text_message_error(self, wework_channel):
        """Test handling send message error."""
        # Mock API error
        wework_channel.client.message.send_text = Mock(
            side_effect=Exception("API Error")
        )

        # Send message
        result = await wework_channel.send("user123", "Test")

        # Verify error handling
        assert result["sent"] is False
        assert "error" in result
        assert "API Error" in result["error"]

    @pytest.mark.asyncio
    async def test_send_markdown(self, wework_channel):
        """Test sending markdown message."""
        mock_response = {
            "errcode": 0,
            "msgid": "msg_789",
        }

        wework_channel.client.message.send_markdown = Mock(return_value=mock_response)

        # Send markdown
        result = await wework_channel.send_markdown("user123", "# Hello\n**World**")

        # Verify result
        assert result["sent"] is True
        assert result["message_id"] == "msg_789"

    @pytest.mark.asyncio
    async def test_send_image(self, wework_channel):
        """Test sending image message."""
        mock_response = {
            "errcode": 0,
            "msgid": "msg_image_123",
        }

        wework_channel.client.message.send_image = Mock(return_value=mock_response)

        # Send image
        result = await wework_channel.send_image("user123", "media_id_123")

        # Verify result
        assert result["sent"] is True
        assert result["message_id"] == "msg_image_123"

    @pytest.mark.asyncio
    async def test_delete_not_supported(self, wework_channel):
        """Test that delete operation is not supported."""
        result = await wework_channel.delete("user123", "msg_123")

        assert result["deleted"] is False
        assert "not supported" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_react_not_supported(self, wework_channel):
        """Test that react operation is not supported."""
        result = await wework_channel.react("user123", "msg_123", "👍")

        assert result["reacted"] is False
        assert "not supported" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_pin_not_supported(self, wework_channel):
        """Test that pin operation is not supported."""
        result = await wework_channel.pin("user123", "msg_123")

        assert result["pinned"] is False
        assert "not supported" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_unpin_not_supported(self, wework_channel):
        """Test that unpin operation is not supported."""
        result = await wework_channel.unpin("user123", "msg_123")

        assert result["unpinned"] is False
        assert "not supported" in result["error"].lower()

    def test_parse_callback_message(self, wework_channel):
        """Test parsing callback message."""
        # Mock crypto decrypt
        decrypted_xml = """
        <xml>
            <ToUserName><![CDATA[corp_id]]></ToUserName>
            <FromUserName><![CDATA[user123]]></FromUserName>
            <CreateTime>1234567890</CreateTime>
            <MsgType><![CDATA[text]]></MsgType>
            <Content><![CDATA[Hello]]></Content>
            <MsgId>123456789</MsgId>
            <AgentID>1000001</AgentID>
        </xml>
        """

        wework_channel.crypto.decrypt_message = Mock(return_value=decrypted_xml)

        # Parse message
        with patch("lurkbot.channels.wework.adapter.parse_message") as mock_parse:
            mock_msg = Mock()
            mock_msg.type = "text"
            mock_msg.source = "user123"
            mock_parse.return_value = mock_msg

            msg = wework_channel.parse_callback_message(
                "encrypted_xml",
                "signature",
                "timestamp",
                "nonce"
            )

            # Verify decryption was called
            wework_channel.crypto.decrypt_message.assert_called_once_with(
                "encrypted_xml",
                "signature",
                "timestamp",
                "nonce"
            )

            # Verify message was parsed
            assert msg.type == "text"
            assert msg.source == "user123"

    def test_get_user_info(self, wework_channel):
        """Test getting user information."""
        mock_user = {
            "userid": "user123",
            "name": "张三",
            "department": [1, 2],
            "mobile": "13800138000",
        }

        wework_channel.client.user.get = Mock(return_value=mock_user)

        # Get user info
        user = wework_channel.get_user_info("user123")

        # Verify result
        assert user["userid"] == "user123"
        assert user["name"] == "张三"

        wework_channel.client.user.get.assert_called_once_with("user123")

    def test_upload_media(self, wework_channel):
        """Test uploading media."""
        mock_result = {
            "type": "image",
            "media_id": "media_123456",
            "created_at": 1234567890,
        }

        wework_channel.client.media.upload = Mock(return_value=mock_result)

        # Upload media
        result = wework_channel.upload_media("image", "/path/to/image.jpg")

        # Verify result
        assert result["media_id"] == "media_123456"
        assert result["type"] == "image"

        wework_channel.client.media.upload.assert_called_once_with(
            "image",
            "/path/to/image.jpg"
        )

    def test_send_with_additional_params(self, wework_channel):
        """Test sending message with additional parameters."""
        mock_response = {
            "errcode": 0,
            "msgid": "msg_456",
        }

        wework_channel.client.message.send_text = Mock(return_value=mock_response)

        # Send with safe mode and to_party
        import asyncio
        result = asyncio.run(
            wework_channel.send(
                "user123",
                "Secret message",
                safe=1,
                to_party="1|2"
            )
        )

        # Verify send was called
        assert result["sent"] is True
