"""Phase 21: TTS (Text-to-Speech) System Tests.

Tests for the TTS module including:
- Type definitions
- Provider implementations
- TTS engine
- Text summarizer
- User preferences
- Directive parser
- TTS tool
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# =============================================================================
# Type Tests
# =============================================================================


class TestTtsTypes:
    """Tests for TTS type definitions."""

    def test_tts_provider_values(self):
        """Test TtsProvider literal values."""
        from lurkbot.tts.types import TtsProvider, TTS_PROVIDERS

        # Check TTS_PROVIDERS list
        assert "openai" in TTS_PROVIDERS
        assert "elevenlabs" in TTS_PROVIDERS
        assert "edge" in TTS_PROVIDERS
        assert len(TTS_PROVIDERS) == 3

    def test_tts_auto_mode_values(self):
        """Test TtsAutoMode literal values."""
        from lurkbot.tts.types import TtsAutoMode, TTS_AUTO_MODES

        assert "off" in TTS_AUTO_MODES
        assert "always" in TTS_AUTO_MODES
        assert "inbound" in TTS_AUTO_MODES
        assert "tagged" in TTS_AUTO_MODES
        assert len(TTS_AUTO_MODES) == 4

    def test_default_constants(self):
        """Test default constant values."""
        from lurkbot.tts.types import (
            DEFAULT_TTS_PROVIDER,
            DEFAULT_OPENAI_MODEL,
            DEFAULT_OPENAI_VOICE,
            DEFAULT_ELEVENLABS_MODEL_ID,
            DEFAULT_ELEVENLABS_VOICE_ID,
        )

        assert DEFAULT_TTS_PROVIDER == "edge"
        assert DEFAULT_OPENAI_MODEL == "gpt-4o-mini-tts"
        assert DEFAULT_OPENAI_VOICE == "alloy"
        assert DEFAULT_ELEVENLABS_MODEL_ID == "eleven_multilingual_v2"
        assert DEFAULT_ELEVENLABS_VOICE_ID == "pMsXgVXv3BLzUgSXRplE"

    def test_openai_tts_models_and_voices(self):
        """Test OpenAI TTS models and voices lists."""
        from lurkbot.tts.types import OPENAI_TTS_MODELS, OPENAI_TTS_VOICES

        assert "tts-1" in OPENAI_TTS_MODELS
        assert "tts-1-hd" in OPENAI_TTS_MODELS
        assert "gpt-4o-mini-tts" in OPENAI_TTS_MODELS

        assert "alloy" in OPENAI_TTS_VOICES
        assert "nova" in OPENAI_TTS_VOICES
        assert "echo" in OPENAI_TTS_VOICES

    def test_tts_result_dataclass(self):
        """Test TtsResult dataclass."""
        from lurkbot.tts.types import TtsResult

        result = TtsResult(
            success=True,
            audio_path="/tmp/audio.mp3",
            provider="openai",
            latency_ms=150,
        )
        assert result.success is True
        assert result.audio_path == "/tmp/audio.mp3"
        assert result.provider == "openai"
        assert result.latency_ms == 150

    def test_tts_result_failure(self):
        """Test TtsResult for failed synthesis."""
        from lurkbot.tts.types import TtsResult

        result = TtsResult(success=False, error="API key invalid")
        assert result.success is False
        assert result.error == "API key invalid"
        assert result.audio_path is None

    def test_resolved_openai_config(self):
        """Test ResolvedOpenAIConfig dataclass."""
        from lurkbot.tts.types import ResolvedOpenAIConfig

        config = ResolvedOpenAIConfig(api_key="sk-test")
        assert config.api_key == "sk-test"
        assert config.model == "gpt-4o-mini-tts"  # Default
        assert config.voice == "alloy"  # Default

    def test_resolved_elevenlabs_config(self):
        """Test ResolvedElevenLabsConfig dataclass."""
        from lurkbot.tts.types import ResolvedElevenLabsConfig

        config = ResolvedElevenLabsConfig(api_key="xi-test")
        assert config.api_key == "xi-test"
        assert config.voice_id == "pMsXgVXv3BLzUgSXRplE"  # Default
        assert config.model_id == "eleven_multilingual_v2"  # Default

    def test_resolved_edge_config(self):
        """Test ResolvedEdgeConfig dataclass."""
        from lurkbot.tts.types import ResolvedEdgeConfig

        config = ResolvedEdgeConfig(enabled=True)
        assert config.enabled is True
        assert config.voice == "en-US-MichelleNeural"  # Default

    def test_tts_user_prefs_data(self):
        """Test TtsUserPrefsData dataclass."""
        from lurkbot.tts.types import TtsUserPrefsData

        prefs = TtsUserPrefsData(
            auto="always",
            provider="openai",
            max_length=2000,
            summarize=True,
        )
        assert prefs.auto == "always"
        assert prefs.provider == "openai"
        assert prefs.max_length == 2000
        assert prefs.summarize is True


# =============================================================================
# Provider Tests
# =============================================================================


class TestOpenAIProvider:
    """Tests for OpenAI TTS provider."""

    def test_provider_creation(self):
        """Test OpenAI provider creation."""
        from lurkbot.tts.providers.openai import OpenAITtsProvider
        from lurkbot.tts.types import ResolvedOpenAIConfig

        config = ResolvedOpenAIConfig(api_key="sk-test")
        provider = OpenAITtsProvider(config)
        assert provider.name == "openai"
        assert provider.is_configured() is True

    def test_provider_not_configured_without_key(self):
        """Test provider not configured without API key."""
        from lurkbot.tts.providers.openai import OpenAITtsProvider
        from lurkbot.tts.types import ResolvedOpenAIConfig

        config = ResolvedOpenAIConfig(api_key=None)
        provider = OpenAITtsProvider(config)
        assert provider.is_configured() is False


class TestElevenLabsProvider:
    """Tests for ElevenLabs TTS provider."""

    def test_provider_creation(self):
        """Test ElevenLabs provider creation."""
        from lurkbot.tts.providers.elevenlabs import ElevenLabsTtsProvider
        from lurkbot.tts.types import ResolvedElevenLabsConfig

        config = ResolvedElevenLabsConfig(api_key="xi-test")
        provider = ElevenLabsTtsProvider(config)
        assert provider.name == "elevenlabs"
        assert provider.is_configured() is True

    def test_provider_not_configured_without_key(self):
        """Test provider not configured without API key."""
        from lurkbot.tts.providers.elevenlabs import ElevenLabsTtsProvider
        from lurkbot.tts.types import ResolvedElevenLabsConfig

        config = ResolvedElevenLabsConfig(api_key=None)
        provider = ElevenLabsTtsProvider(config)
        assert provider.is_configured() is False


class TestEdgeProvider:
    """Tests for Edge TTS provider."""

    def test_provider_creation(self):
        """Test Edge provider creation."""
        from lurkbot.tts.providers.edge import EdgeTtsProvider
        from lurkbot.tts.types import ResolvedEdgeConfig

        config = ResolvedEdgeConfig(enabled=True)
        provider = EdgeTtsProvider(config)
        assert provider.name == "edge"
        assert provider.is_configured() is True

    def test_provider_disabled(self):
        """Test Edge provider when disabled."""
        from lurkbot.tts.providers.edge import EdgeTtsProvider
        from lurkbot.tts.types import ResolvedEdgeConfig

        config = ResolvedEdgeConfig(enabled=False)
        provider = EdgeTtsProvider(config)
        assert provider.is_configured() is False


# =============================================================================
# Engine Tests
# =============================================================================


class TestTtsEngine:
    """Tests for TTS engine."""

    def test_engine_creation(self):
        """Test TTS engine creation."""
        from lurkbot.tts.engine import TtsEngine, TtsEngineConfig
        from lurkbot.tts.types import ResolvedEdgeConfig

        config = TtsEngineConfig(
            edge=ResolvedEdgeConfig(enabled=True),
            default_provider="edge",
        )
        engine = TtsEngine(config)
        assert engine is not None

    def test_available_providers_with_edge(self):
        """Test getting available providers."""
        from lurkbot.tts.engine import TtsEngine, TtsEngineConfig
        from lurkbot.tts.types import ResolvedEdgeConfig

        config = TtsEngineConfig(
            edge=ResolvedEdgeConfig(enabled=True),
            default_provider="edge",
        )
        engine = TtsEngine(config)
        providers = engine.available_providers
        assert "edge" in providers

    def test_available_providers_with_openai(self):
        """Test available providers with OpenAI configured."""
        from lurkbot.tts.engine import TtsEngine, TtsEngineConfig
        from lurkbot.tts.types import ResolvedOpenAIConfig, ResolvedEdgeConfig

        config = TtsEngineConfig(
            openai=ResolvedOpenAIConfig(api_key="sk-test"),
            edge=ResolvedEdgeConfig(enabled=True),
            default_provider="openai",
        )
        engine = TtsEngine(config)
        providers = engine.available_providers
        assert "openai" in providers
        assert "edge" in providers

    def test_engine_without_providers(self):
        """Test engine with no available providers (edge disabled)."""
        from lurkbot.tts.engine import TtsEngine, TtsEngineConfig
        from lurkbot.tts.types import ResolvedEdgeConfig

        # Edge must be explicitly disabled since it requires no API key
        config = TtsEngineConfig(
            edge=ResolvedEdgeConfig(enabled=False),
            default_provider="openai",  # OpenAI not configured, so unavailable
        )
        engine = TtsEngine(config)
        assert len(engine.available_providers) == 0

    def test_get_default_provider(self):
        """Test getting default provider."""
        from lurkbot.tts.engine import TtsEngine, TtsEngineConfig
        from lurkbot.tts.types import ResolvedEdgeConfig

        config = TtsEngineConfig(
            edge=ResolvedEdgeConfig(enabled=True),
            default_provider="edge",
        )
        engine = TtsEngine(config)
        default = engine.get_default_provider()
        assert default == "edge"

    @pytest.mark.asyncio
    async def test_synthesize_no_provider_available(self):
        """Test synthesis fails gracefully when no provider available."""
        from lurkbot.tts.engine import TtsEngine, TtsEngineConfig
        from lurkbot.tts.types import ResolvedEdgeConfig

        # Edge must be explicitly disabled
        config = TtsEngineConfig(
            edge=ResolvedEdgeConfig(enabled=False),
            default_provider="openai",
        )
        engine = TtsEngine(config)

        result = await engine.synthesize("Hello world")
        assert result.success is False
        assert "No TTS provider available" in (result.error or "")

    @pytest.mark.asyncio
    async def test_synthesize_empty_text(self):
        """Test synthesis fails with empty text."""
        from lurkbot.tts.engine import TtsEngine, TtsEngineConfig
        from lurkbot.tts.types import ResolvedEdgeConfig

        config = TtsEngineConfig(
            edge=ResolvedEdgeConfig(enabled=True),
            default_provider="edge",
        )
        engine = TtsEngine(config)

        result = await engine.synthesize("")
        assert result.success is False
        assert "No text to synthesize" in (result.error or "")


# =============================================================================
# Summarizer Tests
# =============================================================================


class TestTtsSummarizer:
    """Tests for TTS text summarizer."""

    def test_summarizer_creation(self):
        """Test summarizer creation."""
        from lurkbot.tts.summarizer import TtsSummarizer

        summarizer = TtsSummarizer()
        assert summarizer is not None

    def test_short_text_unchanged(self):
        """Test short text passes through unchanged."""
        from lurkbot.tts.summarizer import TtsSummarizer, SummarizerConfig

        config = SummarizerConfig(max_chars=100)
        summarizer = TtsSummarizer(config)
        text = "Hello world"
        result = summarizer.summarize(text)
        assert result.text == text
        assert result.was_summarized is False

    def test_long_text_truncated(self):
        """Test long text is truncated."""
        from lurkbot.tts.summarizer import TtsSummarizer, SummarizerConfig

        config = SummarizerConfig(max_chars=50, strategy="truncate")
        summarizer = TtsSummarizer(config)
        text = "A" * 100
        result = summarizer.summarize(text)
        assert len(result.text) <= 50
        assert result.was_summarized is True

    def test_smart_truncate_at_sentence(self):
        """Test smart truncation at sentence boundary."""
        from lurkbot.tts.summarizer import TtsSummarizer, SummarizerConfig

        config = SummarizerConfig(max_chars=60, strategy="smart_truncate")
        summarizer = TtsSummarizer(config)
        text = "This is a test. This is another sentence. And more text here."
        result = summarizer.summarize(text)
        assert result.was_summarized is True
        # Should end with ellipsis
        assert result.text.endswith("...")

    def test_needs_summarization(self):
        """Test needs_summarization check."""
        from lurkbot.tts.summarizer import TtsSummarizer, SummarizerConfig

        config = SummarizerConfig(max_chars=50)
        summarizer = TtsSummarizer(config)

        short_text = "Hello"
        long_text = "A" * 100

        assert summarizer.needs_summarization(short_text) is False
        assert summarizer.needs_summarization(long_text) is True

    def test_estimate_duration(self):
        """Test duration estimation."""
        from lurkbot.tts.summarizer import TtsSummarizer, estimate_tts_duration

        # ~15 chars per second
        text = "A" * 150
        duration = estimate_tts_duration(text)
        assert 9 <= duration <= 11  # ~10 seconds

    def test_split_text(self):
        """Test splitting text into chunks."""
        from lurkbot.tts.summarizer import split_for_tts

        text = "First sentence. " * 50
        chunks = split_for_tts(text, chunk_size=100)
        assert len(chunks) > 1
        for chunk in chunks:
            assert len(chunk) <= 100


# =============================================================================
# Preferences Tests
# =============================================================================


class TestTtsPreferences:
    """Tests for TTS user preferences."""

    def test_resolve_prefs_path_default(self):
        """Test default preferences path."""
        from lurkbot.tts.prefs import resolve_tts_prefs_path

        path = resolve_tts_prefs_path(None)
        assert "tts.json" in path
        assert ".clawdbot" in path

    def test_resolve_prefs_path_explicit(self):
        """Test explicit preferences path."""
        from lurkbot.tts.prefs import resolve_tts_prefs_path

        explicit_path = "/tmp/custom_tts.json"
        path = resolve_tts_prefs_path(explicit_path)
        assert path == explicit_path

    def test_read_prefs_nonexistent(self):
        """Test reading from nonexistent file."""
        from lurkbot.tts.prefs import read_prefs

        prefs = read_prefs("/nonexistent/path/tts.json")
        assert prefs.tts is None

    def test_read_write_prefs(self):
        """Test writing and reading preferences."""
        from lurkbot.tts.prefs import (
            read_prefs,
            set_tts_enabled,
            set_tts_provider,
            set_tts_max_length,
            get_tts_max_length,
            is_tts_enabled,
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            prefs_path = f.name

        try:
            # Set preferences
            set_tts_enabled(prefs_path, True)
            set_tts_provider(prefs_path, "openai")
            set_tts_max_length(prefs_path, 2000)

            # Read back
            max_length = get_tts_max_length(prefs_path)
            assert max_length == 2000

            # Note: is_tts_enabled needs config_auto parameter
            assert is_tts_enabled("off", prefs_path) is True
        finally:
            os.unlink(prefs_path)

    def test_summarization_enabled(self):
        """Test summarization preference."""
        from lurkbot.tts.prefs import (
            is_summarization_enabled,
            set_summarization_enabled,
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            prefs_path = f.name

        try:
            # Default should be True
            assert is_summarization_enabled(prefs_path) is True

            # Set to False
            set_summarization_enabled(prefs_path, False)
            assert is_summarization_enabled(prefs_path) is False

            # Set back to True
            set_summarization_enabled(prefs_path, True)
            assert is_summarization_enabled(prefs_path) is True
        finally:
            os.unlink(prefs_path)


# =============================================================================
# Directive Parser Tests
# =============================================================================


class TestDirectiveParser:
    """Tests for TTS directive parser."""

    def test_parse_no_directive(self):
        """Test parsing text without directive."""
        from lurkbot.tts.directive_parser import parse_tts_directives

        text = "Hello world"
        result = parse_tts_directives(text)
        assert result.has_directive is False
        assert result.cleaned_text == "Hello world"

    def test_parse_simple_directive(self):
        """Test parsing simple inline directive."""
        from lurkbot.tts.directive_parser import parse_tts_directives

        text = "[[tts:provider=openai]] Hello world"
        result = parse_tts_directives(text)
        assert result.has_directive is True
        assert result.overrides.provider == "openai"
        assert "Hello world" in result.cleaned_text

    def test_parse_block_directive(self):
        """Test parsing block directive."""
        from lurkbot.tts.directive_parser import parse_tts_directives

        text = "[[tts:text]]This is custom TTS text[[/tts:text]] Normal text"
        result = parse_tts_directives(text)
        assert result.has_directive is True
        assert result.tts_text == "This is custom TTS text"

    def test_parse_voice_directive(self):
        """Test parsing voice directive."""
        from lurkbot.tts.directive_parser import parse_tts_directives

        text = "[[tts:voice=nova]] Hello"
        result = parse_tts_directives(text)
        assert result.has_directive is True
        assert result.overrides.openai is not None
        assert result.overrides.openai.voice == "nova"

    def test_parse_multiple_params(self):
        """Test parsing multiple parameters."""
        from lurkbot.tts.directive_parser import parse_tts_directives

        text = "[[tts:provider=openai voice=nova model=tts-1]] Hello"
        result = parse_tts_directives(text)
        assert result.has_directive is True
        assert result.overrides.provider == "openai"
        assert result.overrides.openai is not None
        assert result.overrides.openai.voice == "nova"
        assert result.overrides.openai.model == "tts-1"

    def test_parse_elevenlabs_params(self):
        """Test parsing ElevenLabs parameters."""
        from lurkbot.tts.directive_parser import parse_tts_directives

        text = "[[tts:provider=elevenlabs stability=0.7 speed=1.2]] Hello"
        result = parse_tts_directives(text)
        assert result.has_directive is True
        assert result.overrides.provider == "elevenlabs"
        assert result.overrides.elevenlabs is not None
        assert result.overrides.elevenlabs.voice_settings is not None
        assert result.overrides.elevenlabs.voice_settings["stability"] == 0.7
        assert result.overrides.elevenlabs.voice_settings["speed"] == 1.2

    def test_parse_invalid_provider(self):
        """Test parsing invalid provider gives warning."""
        from lurkbot.tts.directive_parser import parse_tts_directives

        text = "[[tts:provider=invalid]] Hello"
        result = parse_tts_directives(text)
        assert result.has_directive is True
        assert result.overrides.provider is None
        assert len(result.warnings) > 0

    def test_policy_disabled(self):
        """Test directives ignored when policy disabled."""
        from lurkbot.tts.directive_parser import parse_tts_directives
        from lurkbot.tts.types import TtsModelOverrideConfig

        policy = TtsModelOverrideConfig(enabled=False)
        text = "[[tts:provider=openai]] Hello"
        result = parse_tts_directives(text, policy=policy)
        assert result.has_directive is False


# =============================================================================
# TTS Tool Tests
# =============================================================================


class TestTtsTool:
    """Tests for TTS tool."""

    def test_tool_creation(self):
        """Test TTS tool creation."""
        from lurkbot.tools.tts_tool import TtsTool, TtsToolConfig

        config = TtsToolConfig()
        tool = TtsTool(config)
        assert tool.name == "tts"
        assert tool.description is not None

    def test_tool_definition(self):
        """Test tool definition schema."""
        from lurkbot.tools.tts_tool import TtsTool

        tool = TtsTool()
        definition = tool.get_tool_definition()
        assert definition["name"] == "tts"
        assert "input_schema" in definition
        assert "text" in definition["input_schema"]["properties"]
        assert "text" in definition["input_schema"]["required"]

    def test_create_tts_tool_factory(self):
        """Test TTS tool factory function."""
        from lurkbot.tools.tts_tool import create_tts_tool

        tool = create_tts_tool(default_provider="edge")
        assert tool is not None
        assert tool.name == "tts"

    @pytest.mark.asyncio
    async def test_execute_without_text(self):
        """Test execute fails without text."""
        from lurkbot.tools.tts_tool import TtsTool

        tool = TtsTool()
        result = await tool.execute()
        assert result["success"] is False
        assert "No text provided" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_with_empty_text(self):
        """Test execute fails with empty text."""
        from lurkbot.tools.tts_tool import TtsTool

        tool = TtsTool()
        result = await tool.execute(text="")
        assert result["success"] is False


# =============================================================================
# Integration Tests
# =============================================================================


class TestTtsIntegration:
    """Integration tests for TTS system."""

    def test_module_exports(self):
        """Test all expected exports are available."""
        from lurkbot.tts import (
            # Types
            TtsProvider,
            TtsConfig,
            TtsModelOverrideConfig,
            ElevenLabsVoiceSettings,
            ResolvedOpenAIConfig,
            ResolvedElevenLabsConfig,
            ResolvedEdgeConfig,
            TtsResult,
            DEFAULT_TTS_PROVIDER,
            # Directive Parser
            TtsDirectiveOverrides,
            TtsDirectiveParseResult,
            parse_tts_directives,
            # Preferences
            read_prefs,
            resolve_tts_prefs_path,
            # Summarizer
            TtsSummarizer,
            SummarizationResult,
            SummarizerConfig,
            # Providers
            TtsProviderBase,
            TtsProviderResult,
            OpenAITtsProvider,
            ElevenLabsTtsProvider,
            EdgeTtsProvider,
            # Engine
            TtsEngine,
            TtsEngineConfig,
            TtsSynthesisResult,
            create_tts_engine,
        )

        # Verify all imports succeeded
        assert TtsProvider is not None
        assert TtsEngine is not None
        assert TtsSummarizer is not None

    def test_full_pipeline_setup(self):
        """Test setting up full TTS pipeline."""
        from lurkbot.tts import (
            TtsEngine,
            TtsEngineConfig,
            TtsSummarizer,
            SummarizerConfig,
            parse_tts_directives,
            ResolvedEdgeConfig,
        )

        # Create components
        config = TtsEngineConfig(
            edge=ResolvedEdgeConfig(enabled=True),
            default_provider="edge",
        )
        engine = TtsEngine(config)
        summarizer = TtsSummarizer(SummarizerConfig(max_chars=500))

        # Verify pipeline components
        assert engine is not None
        assert summarizer is not None

        # Test pipeline flow
        text = "[[tts:provider=edge]] This is a test message for TTS synthesis."
        directive_result = parse_tts_directives(text)
        assert directive_result.has_directive is True

        summary_result = summarizer.summarize(directive_result.cleaned_text.strip())
        assert len(summary_result.text) <= 500


# =============================================================================
# Edge Cases and Error Handling
# =============================================================================


class TestTtsEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_text_summarizer(self):
        """Test summarizer handles empty text."""
        from lurkbot.tts.summarizer import TtsSummarizer

        summarizer = TtsSummarizer()
        result = summarizer.summarize("")
        assert result.text == ""
        assert result.was_summarized is False

    def test_unicode_text(self):
        """Test handling unicode text."""
        from lurkbot.tts.summarizer import TtsSummarizer

        summarizer = TtsSummarizer()
        text = "Hello 世界 🌍 مرحبا"
        result = summarizer.summarize(text)
        assert "世界" in result.text or len(result.text) > 0

    def test_very_long_text(self):
        """Test handling very long text."""
        from lurkbot.tts.summarizer import TtsSummarizer, SummarizerConfig

        config = SummarizerConfig(max_chars=100, strategy="truncate")
        summarizer = TtsSummarizer(config)
        text = "Word " * 1000
        result = summarizer.summarize(text)
        assert len(result.text) <= 100

    def test_directive_case_insensitive(self):
        """Test directive parsing is case insensitive."""
        from lurkbot.tts.directive_parser import parse_tts_directives

        text = "[[TTS:PROVIDER=openai]] Hello"
        result = parse_tts_directives(text)
        assert result.has_directive is True
        assert result.overrides.provider == "openai"

    def test_provider_order(self):
        """Test provider order resolution."""
        from lurkbot.tts.prefs import resolve_tts_provider_order

        order = resolve_tts_provider_order("elevenlabs")
        assert order[0] == "elevenlabs"
        assert "openai" in order
        assert "edge" in order


# =============================================================================
# Performance Tests
# =============================================================================


class TestTtsPerformance:
    """Performance-related tests."""

    def test_summarizer_performance(self):
        """Test summarizer handles large text efficiently."""
        import time
        from lurkbot.tts.summarizer import TtsSummarizer, SummarizerConfig

        config = SummarizerConfig(max_chars=500, strategy="smart_truncate")
        summarizer = TtsSummarizer(config)
        text = "Word " * 10000  # 50000 characters

        start = time.time()
        result = summarizer.summarize(text)
        elapsed = time.time() - start

        assert elapsed < 1.0  # Should complete in under 1 second
        assert len(result.text) <= 500

    def test_directive_parser_performance(self):
        """Test directive parser handles many parses efficiently."""
        import time
        from lurkbot.tts.directive_parser import parse_tts_directives

        texts = [f"[[tts:voice=nova]] Message {i}" for i in range(100)]

        start = time.time()
        for text in texts:
            parse_tts_directives(text)
        elapsed = time.time() - start

        assert elapsed < 1.0  # Should complete in under 1 second
