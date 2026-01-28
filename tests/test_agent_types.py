"""Tests for agent types and runtime."""

import pytest

from lurkbot.agents import (
    AgentContext,
    AgentDependencies,
    AgentRunResult,
    PromptMode,
    SessionType,
    ThinkLevel,
    build_session_key,
    parse_session_key,
    resolve_model_id,
)


class TestSessionKey:
    """Tests for session key building and parsing."""

    def test_build_main_session_key(self):
        """Test building a main session key."""
        key = build_session_key("test-agent", SessionType.MAIN)
        assert key == "agent:test-agent:main"

    def test_build_group_session_key(self):
        """Test building a group session key."""
        key = build_session_key(
            "test-agent",
            SessionType.GROUP,
            channel="discord",
            group_id="123456",
        )
        assert key == "agent:test-agent:group:discord:123456"

    def test_build_topic_session_key(self):
        """Test building a topic session key."""
        key = build_session_key(
            "test-agent",
            SessionType.TOPIC,
            channel="discord",
            group_id="123456",
            thread_id="789",
        )
        assert key == "agent:test-agent:topic:discord:123456:789"

    def test_build_dm_session_key(self):
        """Test building a DM session key."""
        key = build_session_key(
            "test-agent",
            SessionType.DM,
            channel="telegram",
            dm_partner="user123",
        )
        assert key == "agent:test-agent:dm:telegram:user123"

    def test_build_group_session_key_missing_params(self):
        """Test that building a group session key without params raises error."""
        with pytest.raises(ValueError):
            build_session_key("test-agent", SessionType.GROUP)

    def test_parse_main_session_key(self):
        """Test parsing a main session key."""
        result = parse_session_key("agent:test-agent:main")
        assert result["agent_id"] == "test-agent"
        assert result["session_type"] == SessionType.MAIN

    def test_parse_group_session_key(self):
        """Test parsing a group session key."""
        result = parse_session_key("agent:test-agent:group:discord:123456")
        assert result["agent_id"] == "test-agent"
        assert result["session_type"] == SessionType.GROUP
        assert result["channel"] == "discord"
        assert result["group_id"] == "123456"

    def test_parse_invalid_session_key(self):
        """Test that parsing an invalid session key raises error."""
        with pytest.raises(ValueError):
            parse_session_key("invalid-key")


class TestModelIdResolution:
    """Tests for model ID resolution."""

    def test_resolve_anthropic_model(self):
        """Test resolving Anthropic model ID."""
        result = resolve_model_id("anthropic", "claude-sonnet-4-20250514")
        assert result == "anthropic:claude-sonnet-4-20250514"

    def test_resolve_openai_model(self):
        """Test resolving OpenAI model ID."""
        result = resolve_model_id("openai", "gpt-4o")
        assert result == "openai:gpt-4o"

    def test_resolve_google_model(self):
        """Test resolving Google model ID."""
        result = resolve_model_id("google", "gemini-2.0-flash")
        assert result == "google-gla:gemini-2.0-flash"

    def test_resolve_already_formatted(self):
        """Test resolving already formatted model ID."""
        result = resolve_model_id("anthropic", "anthropic:claude-3-opus")
        assert result == "anthropic:claude-3-opus"

    def test_resolve_unknown_model(self):
        """Test resolving unknown model falls back to default format."""
        result = resolve_model_id("custom", "my-model")
        assert result == "custom:my-model"


class TestAgentContext:
    """Tests for AgentContext."""

    def test_default_values(self):
        """Test AgentContext default values."""
        ctx = AgentContext(session_id="test-session")

        assert ctx.session_id == "test-session"
        assert ctx.session_type == SessionType.MAIN
        assert ctx.provider == "anthropic"
        assert ctx.model_id == "claude-sonnet-4-20250514"
        assert ctx.think_level == ThinkLevel.MEDIUM
        assert ctx.prompt_mode == PromptMode.FULL
        assert ctx.timeout_ms == 120_000
        assert ctx.sandbox_enabled is False
        assert ctx.is_subagent is False

    def test_custom_values(self):
        """Test AgentContext with custom values."""
        ctx = AgentContext(
            session_id="custom-session",
            session_type=SessionType.GROUP,
            provider="openai",
            model_id="gpt-4o",
            think_level=ThinkLevel.HIGH,
            prompt_mode=PromptMode.MINIMAL,
            sandbox_enabled=True,
        )

        assert ctx.session_id == "custom-session"
        assert ctx.session_type == SessionType.GROUP
        assert ctx.provider == "openai"
        assert ctx.model_id == "gpt-4o"
        assert ctx.think_level == ThinkLevel.HIGH
        assert ctx.prompt_mode == PromptMode.MINIMAL
        assert ctx.sandbox_enabled is True


class TestAgentRunResult:
    """Tests for AgentRunResult."""

    def test_default_values(self):
        """Test AgentRunResult default values."""
        result = AgentRunResult()

        assert result.aborted is False
        assert result.timed_out is False
        assert result.prompt_error is None
        assert result.assistant_texts == []
        assert result.has_deferred_requests is False

    def test_has_deferred_requests(self):
        """Test has_deferred_requests property."""
        result = AgentRunResult()
        assert result.has_deferred_requests is False

        result.deferred_requests = "mock"  # type: ignore
        assert result.has_deferred_requests is True


class TestAgentDependencies:
    """Tests for AgentDependencies."""

    def test_create_dependencies(self):
        """Test creating AgentDependencies."""
        ctx = AgentContext(session_id="test")
        deps = AgentDependencies(context=ctx)

        assert deps.context.session_id == "test"
        assert deps.message_history == []

    def test_with_message_history(self):
        """Test AgentDependencies with message history."""
        ctx = AgentContext(session_id="test")
        history = [{"role": "user", "content": "Hello"}]
        deps = AgentDependencies(context=ctx, message_history=history)

        assert len(deps.message_history) == 1
        assert deps.message_history[0]["content"] == "Hello"


class TestChatAPI:
    """Tests for Chat API models."""

    def test_chat_request_defaults(self):
        """Test ChatRequest default values."""
        from lurkbot.agents import ChatRequest

        req = ChatRequest(message="Hello")

        assert req.message == "Hello"
        assert req.session_id is None
        assert req.session_type == "main"
        assert req.provider == "anthropic"
        assert req.model == "claude-sonnet-4-20250514"
        assert req.think_level == "medium"
        assert req.stream is False

    def test_chat_request_custom(self):
        """Test ChatRequest with custom values."""
        from lurkbot.agents import ChatRequest

        req = ChatRequest(
            message="Hello",
            session_id="test-session",
            session_type="group",
            provider="openai",
            model="gpt-4o",
            stream=True,
        )

        assert req.message == "Hello"
        assert req.session_id == "test-session"
        assert req.session_type == "group"
        assert req.provider == "openai"
        assert req.model == "gpt-4o"
        assert req.stream is True

    def test_chat_response(self):
        """Test ChatResponse model."""
        from lurkbot.agents import ChatResponse

        resp = ChatResponse(
            session_id="test",
            text="Hello!",
            messages=[{"role": "assistant", "content": "Hello!"}],
            has_pending_approvals=False,
        )

        assert resp.session_id == "test"
        assert resp.text == "Hello!"
        assert len(resp.messages) == 1
        assert resp.has_pending_approvals is False
        assert resp.error is None

    def test_create_chat_api(self):
        """Test creating the chat API application."""
        from lurkbot.agents import create_chat_api

        app = create_chat_api()

        # Check that routes are registered
        routes = [r.path for r in app.routes]
        assert "/chat" in routes
        assert "/chat/stream" in routes
        assert "/health" in routes
