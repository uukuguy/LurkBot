"""
测试媒体理解系统的基本功能
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from pathlib import Path

from lurkbot.media import (
    understand_media,
    MediaConfig,
    ProviderConfig,
    get_default_config,
    OpenAIProvider,
    AnthropicProvider,
    GeminiProvider,
    LocalProvider,
)


class TestMediaConfig:
    """测试媒体配置功能"""

    def test_default_config_creation(self):
        """测试默认配置创建"""
        config = get_default_config()

        assert isinstance(config, MediaConfig)
        assert isinstance(config.max_chars, dict)
        assert config.max_chars["image"] == 500
        assert config.timeout_seconds == 30
        assert len(config.providers) > 0

        # 检查是否包含所有提供商
        provider_names = [p.provider for p in config.providers]
        assert "gemini" in provider_names
        assert "local" in provider_names

    def test_provider_config_validation(self):
        """测试提供商配置验证"""
        # 测试有效配置
        config = ProviderConfig(
            provider="openai",
            model="gpt-4o",
            enabled=True,
            priority=1
        )
        assert config.provider == "openai"
        assert config.enabled is True
        assert config.priority == 1

    def test_media_config_provider_ordering(self):
        """测试提供商优先级排序"""
        config = MediaConfig(
            providers=[
                ProviderConfig(provider="gemini", model="gemini-1.5-pro", priority=2),
                ProviderConfig(provider="openai", model="gpt-4o", priority=1),
                ProviderConfig(provider="local", model="local-tools", priority=3),
            ]
        )

        # 获取排序后的提供商
        sorted_providers = sorted(config.providers, key=lambda p: p.priority)
        names = [p.provider for p in sorted_providers]

        assert names == ["openai", "gemini", "local"]


class TestProviders:
    """测试各个提供商的基本功能"""

    def test_openai_provider_initialization(self):
        """测试 OpenAI 提供商初始化"""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            provider = OpenAIProvider()
            assert provider.api_key == 'test-key'

    def test_openai_provider_supports_types(self):
        """测试 OpenAI 提供商支持的媒体类型"""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            provider = OpenAIProvider()

            assert provider.supports_type("image") is True
            assert provider.supports_type("audio") is True
            assert provider.supports_type("document") is True
            assert provider.supports_type("video") is False

    def test_anthropic_provider_supports_types(self):
        """测试 Anthropic 提供商支持的媒体类型"""
        with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-key'}):
            provider = AnthropicProvider()

            assert provider.supports_type("image") is True
            assert provider.supports_type("document") is True
            assert provider.supports_type("audio") is False
            assert provider.supports_type("video") is False

    def test_gemini_provider_supports_types(self):
        """测试 Gemini 提供商支持的媒体类型"""
        with patch.dict('os.environ', {'GOOGLE_API_KEY': 'test-key'}):
            provider = GeminiProvider()

            assert provider.supports_type("image") is True
            assert provider.supports_type("audio") is True
            assert provider.supports_type("video") is True
            assert provider.supports_type("document") is True

    def test_local_provider_initialization(self):
        """测试本地提供商初始化"""
        provider = LocalProvider()

        # 本地提供商应该能够初始化，即使没有所有工具
        assert hasattr(provider, 'available_tools')
        assert isinstance(provider.available_tools, dict)

    def test_local_provider_dependency_check(self):
        """测试本地提供商依赖检查"""
        provider = LocalProvider()

        # 检查工具可用性检测
        assert 'PIL' in provider.available_tools
        assert 'ffmpeg' in provider.available_tools
        assert 'file' in provider.available_tools


class TestMediaUnderstanding:
    """测试媒体理解主要功能"""

    @pytest.mark.asyncio
    async def test_understand_media_with_mock_provider(self):
        """测试使用模拟提供商的媒体理解"""
        # 创建模拟提供商
        mock_provider = Mock()
        mock_provider.supports_type.return_value = True
        mock_provider.understand = AsyncMock(return_value="这是一张测试图片")

        # 创建配置
        config = MediaConfig(
            providers=[
                ProviderConfig(
                    provider="mock",
                    model="test-model",
                    enabled=True,
                    priority=1
                )
            ]
        )

        # 模拟提供商创建
        with patch('lurkbot.media.understand.get_provider') as mock_create:
            mock_create.return_value = mock_provider

            result = await understand_media(
                media_url="https://example.com/test.jpg",
                media_type="image",
                config=config
            )

            assert result.success is True
            assert result.summary == "这是一张测试图片"
            assert result.provider_used == "mock"

    @pytest.mark.asyncio
    async def test_understand_media_provider_fallback(self):
        """测试提供商降级机制"""
        # 创建两个模拟提供商
        failing_provider = Mock()
        failing_provider.supports_type.return_value = True
        failing_provider.understand = AsyncMock(side_effect=Exception("API 错误"))

        working_provider = Mock()
        working_provider.supports_type.return_value = True
        working_provider.understand = AsyncMock(return_value="降级处理成功")

        # 创建配置
        config = MediaConfig(
            providers=[
                ProviderConfig(provider="failing", model="model1", priority=1),
                ProviderConfig(provider="working", model="model2", priority=2),
            ]
        )

        # 模拟提供商创建
        def mock_get_provider(provider_name):
            if provider_name == "failing":
                return failing_provider
            elif provider_name == "working":
                return working_provider
            return None

        with patch('lurkbot.media.understand.get_provider', side_effect=mock_get_provider):
            result = await understand_media(
                media_url="https://example.com/test.jpg",
                media_type="image",
                config=config
            )

            assert result.success is True
            assert result.summary == "降级处理成功"
            assert result.provider_used == "working"

    @pytest.mark.asyncio
    async def test_understand_media_no_supported_provider(self):
        """测试没有支持的提供商时的处理"""
        # 创建不支持指定媒体类型的提供商
        mock_provider = Mock()
        mock_provider.supports_type.return_value = False

        config = MediaConfig(
            providers=[
                ProviderConfig(provider="local", model="local-model")
            ]
        )

        with patch('lurkbot.media.understand.get_provider') as mock_get:
            mock_get.return_value = mock_provider

            result = await understand_media(
                media_url="https://example.com/test.mp4",
                media_type="video",
                config=config
            )

            assert result.success is False
            assert result.error is not None

