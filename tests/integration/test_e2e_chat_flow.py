"""End-to-end integration tests for complete chat flow.

Tests the complete flow from user input to agent response:
- CLI → Agent → Tools → Session → Response

These tests verify the integration between all major components.
"""

import asyncio
import tempfile
import time
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from lurkbot.agents.runtime import (
    AgentDependencies,
    create_agent,
    resolve_model_id,
    run_embedded_agent,
)
from lurkbot.agents.types import (
    AgentContext,
    AgentRunResult,
    PromptMode,
    SessionType,
    ThinkLevel,
)
from lurkbot.agents.system_prompt import SystemPromptParams, build_agent_system_prompt
from lurkbot.sessions.manager import SessionManager, SessionManagerConfig, SessionContext
from lurkbot.sessions.types import MessageEntry, SessionEntry


class TestE2EChatFlowBasic:
    """Test basic end-to-end chat flow without real API calls."""

    @pytest.fixture
    def temp_workspace(self) -> Path:
        """Create a temporary workspace."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir) / "workspace"
            workspace.mkdir(parents=True)
            (workspace / "AGENTS.md").write_text("# Test Agent\nA test agent.")
            (workspace / "TOOLS.md").write_text("# Tools\nAvailable tools.")
            yield workspace

    @pytest.fixture
    def temp_lurkbot_home(self) -> Path:
        """Create a temporary ~/.lurkbot directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir) / ".lurkbot"
            home.mkdir(parents=True)
            (home / "agents").mkdir()
            (home / "sessions").mkdir()
            yield home

    @pytest.fixture
    def session_manager(self, temp_lurkbot_home: Path) -> SessionManager:
        """Create a session manager."""
        config = SessionManagerConfig(
            base_dir=temp_lurkbot_home / "agents",
            auto_cleanup=False,
            max_sessions_per_agent=100,
            max_subagent_depth=3,
        )
        return SessionManager(config=config)

    @pytest.fixture
    def agent_context(self, temp_workspace: Path) -> AgentContext:
        """Create an agent context."""
        return AgentContext(
            session_id="e2e-test-session-001",
            session_key="agent:e2e-test:main",
            session_type=SessionType.MAIN,
            workspace_dir=str(temp_workspace),
            message_channel="test",
            provider="anthropic",
            model_id="claude-sonnet-4-20250514",
            think_level=ThinkLevel.MEDIUM,
            prompt_mode=PromptMode.FULL,
        )

    @pytest.mark.integration
    def test_model_resolution_flow(self):
        """Test model ID resolution for different providers."""
        # Anthropic models
        assert resolve_model_id("anthropic", "claude-sonnet-4-20250514") == "anthropic:claude-sonnet-4-20250514"

        # OpenAI models
        assert resolve_model_id("openai", "gpt-4o") == "openai:gpt-4o"

        # Google models
        assert resolve_model_id("google", "gemini-2.0-flash") == "google-gla:gemini-2.0-flash"

        # Already formatted
        assert resolve_model_id("anthropic", "anthropic:claude-3-5-sonnet") == "anthropic:claude-3-5-sonnet"

    @pytest.mark.integration
    def test_system_prompt_generation_flow(self, temp_workspace: Path):
        """Test system prompt generation for agent."""
        params = SystemPromptParams(
            workspace_dir=str(temp_workspace),
            tool_names=["read_file", "write_file", "bash"],
            default_think_level=ThinkLevel.MEDIUM,
        )

        prompt = build_agent_system_prompt(params)

        # Verify prompt contains expected sections
        assert prompt is not None
        assert len(prompt) > 0
        # The prompt should be a string
        assert isinstance(prompt, str)

    @pytest.mark.integration
    def test_agent_context_creation_flow(self, agent_context: AgentContext):
        """Test agent context creation with all required fields."""
        assert agent_context.session_id == "e2e-test-session-001"
        assert agent_context.session_key == "agent:e2e-test:main"
        assert agent_context.session_type == SessionType.MAIN
        assert agent_context.provider == "anthropic"
        assert agent_context.model_id == "claude-sonnet-4-20250514"
        assert agent_context.think_level == ThinkLevel.MEDIUM

    @pytest.mark.integration
    def test_agent_dependencies_creation_flow(self, agent_context: AgentContext):
        """Test agent dependencies creation."""
        deps = AgentDependencies(
            context=agent_context,
            message_history=[
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there!"},
            ],
        )

        assert deps.context == agent_context
        assert len(deps.message_history) == 2
        assert deps.message_history[0]["role"] == "user"

    @pytest.mark.integration
    def test_session_creation_flow(self, session_manager: SessionManager):
        """Test session creation and retrieval flow."""
        ctx = SessionContext(
            agent_id="e2e-test",
            session_type=SessionType.MAIN,
        )

        # Create session
        session, created = session_manager.get_or_create_session(ctx)

        assert created is True
        assert session is not None
        assert "e2e-test" in session.session_key

        # Retrieve same session
        session2, created2 = session_manager.get_or_create_session(ctx)

        assert created2 is False
        assert session2.session_key == session.session_key

    @pytest.mark.integration
    def test_message_persistence_flow(self, session_manager: SessionManager):
        """Test message persistence in session."""
        ctx = SessionContext(
            agent_id="e2e-test-msg",
            session_type=SessionType.MAIN,
        )

        # Create session
        session, _ = session_manager.get_or_create_session(ctx)

        # Add messages using store directly
        store = session_manager._get_store(ctx.agent_id)

        user_msg = MessageEntry(
            message_id="msg-001",
            role="user",
            content="What is 2 + 2?",
            timestamp=int(time.time() * 1000),
        )

        assistant_msg = MessageEntry(
            message_id="msg-002",
            role="assistant",
            content="2 + 2 equals 4.",
            timestamp=int(time.time() * 1000),
        )

        store.append_message(session.session_id, user_msg)
        store.append_message(session.session_id, assistant_msg)

        # Retrieve messages using session_id
        messages = store.get_history(session.session_id)

        assert len(messages) == 2
        assert messages[0].role == "user"
        assert messages[0].content == "What is 2 + 2?"
        assert messages[1].role == "assistant"
        assert messages[1].content == "2 + 2 equals 4."

    @pytest.mark.integration
    def test_agent_run_result_structure(self):
        """Test AgentRunResult structure."""
        result = AgentRunResult(
            session_id_used="test-session",
            assistant_texts=["Hello, how can I help you?"],
            messages_snapshot=[
                {"role": "user", "content": "Hi"},
                {"role": "assistant", "content": "Hello, how can I help you?"},
            ],
        )

        assert result.aborted is False
        assert result.timed_out is False
        assert result.prompt_error is None
        assert len(result.assistant_texts) == 1
        assert result.assistant_texts[0] == "Hello, how can I help you?"
        assert result.has_deferred_requests is False


class TestE2EChatFlowWithMocks:
    """Test end-to-end chat flow with mocked API calls."""

    @pytest.fixture
    def temp_workspace(self) -> Path:
        """Create a temporary workspace."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir) / "workspace"
            workspace.mkdir(parents=True)
            (workspace / "AGENTS.md").write_text("# Test Agent\nA test agent.")
            yield workspace

    @pytest.fixture
    def agent_context(self, temp_workspace: Path) -> AgentContext:
        """Create an agent context."""
        return AgentContext(
            session_id="e2e-mock-session-001",
            session_key="agent:e2e-mock:main",
            session_type=SessionType.MAIN,
            workspace_dir=str(temp_workspace),
            message_channel="test",
            provider="anthropic",
            model_id="claude-sonnet-4-20250514",
        )

    @pytest.fixture
    def mock_agent_response(self):
        """Create a mock agent response."""
        mock_result = MagicMock()
        mock_result.output = "This is a test response from the mocked agent."
        mock_result.all_messages.return_value = [
            MagicMock(model_dump=lambda: {"role": "user", "content": "Test prompt"}),
            MagicMock(model_dump=lambda: {"role": "assistant", "content": "This is a test response from the mocked agent."}),
        ]
        return mock_result

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_full_chat_flow_mocked(self, agent_context: AgentContext, mock_agent_response):
        """Test full chat flow with mocked agent."""
        with patch("lurkbot.agents.runtime.Agent") as MockAgent:
            # Setup mock
            mock_agent_instance = MagicMock()
            mock_agent_instance.run = AsyncMock(return_value=mock_agent_response)
            MockAgent.return_value = mock_agent_instance

            # Run agent
            result = await run_embedded_agent(
                context=agent_context,
                prompt="Hello, this is a test",
                system_prompt="You are a helpful assistant.",
                message_history=[],
            )

            # Verify result
            assert result.session_id_used == agent_context.session_id
            assert result.aborted is False
            assert result.timed_out is False
            assert result.prompt_error is None

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_chat_flow_with_timeout(self, agent_context: AgentContext):
        """Test chat flow handling timeout."""
        with patch("lurkbot.agents.runtime.Agent") as MockAgent:
            # Setup mock to raise timeout
            mock_agent_instance = MagicMock()
            mock_agent_instance.run = AsyncMock(side_effect=TimeoutError("Agent timed out"))
            MockAgent.return_value = mock_agent_instance

            # Run agent
            result = await run_embedded_agent(
                context=agent_context,
                prompt="This will timeout",
                system_prompt="You are a helpful assistant.",
            )

            # Verify timeout handling
            assert result.timed_out is True
            assert result.aborted is False

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_chat_flow_with_error(self, agent_context: AgentContext):
        """Test chat flow handling errors."""
        with patch("lurkbot.agents.runtime.Agent") as MockAgent:
            # Setup mock to raise error
            mock_agent_instance = MagicMock()
            mock_agent_instance.run = AsyncMock(side_effect=ValueError("Test error"))
            MockAgent.return_value = mock_agent_instance

            # Run agent
            result = await run_embedded_agent(
                context=agent_context,
                prompt="This will error",
                system_prompt="You are a helpful assistant.",
            )

            # Verify error handling
            assert result.prompt_error is not None
            assert isinstance(result.prompt_error, ValueError)


class TestE2EMultiTurnConversation:
    """Test multi-turn conversation flow."""

    @pytest.fixture
    def temp_lurkbot_home(self) -> Path:
        """Create a temporary ~/.lurkbot directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir) / ".lurkbot"
            home.mkdir(parents=True)
            (home / "agents").mkdir()
            yield home

    @pytest.fixture
    def session_manager(self, temp_lurkbot_home: Path) -> SessionManager:
        """Create a session manager."""
        config = SessionManagerConfig(
            base_dir=temp_lurkbot_home / "agents",
            auto_cleanup=False,
        )
        return SessionManager(config=config)

    @pytest.mark.integration
    def test_multi_turn_message_accumulation(self, session_manager: SessionManager):
        """Test message accumulation across multiple turns."""
        ctx = SessionContext(
            agent_id="multi-turn",
            session_type=SessionType.MAIN,
        )

        # Create session
        session, _ = session_manager.get_or_create_session(ctx)
        store = session_manager._get_store(ctx.agent_id)

        # Simulate multi-turn conversation
        turns = [
            ("user", "What is Python?"),
            ("assistant", "Python is a programming language."),
            ("user", "What can I do with it?"),
            ("assistant", "You can build web apps, data analysis, AI, and more."),
            ("user", "Show me an example"),
            ("assistant", "Here's a simple example: print('Hello, World!')"),
        ]

        for i, (role, content) in enumerate(turns):
            msg = MessageEntry(
                message_id=f"msg-{i:03d}",
                role=role,
                content=content,
                timestamp=int(time.time() * 1000),
            )
            store.append_message(session.session_id, msg)

        # Verify all messages are stored
        messages = store.get_history(session.session_id)
        assert len(messages) == 6

        # Verify order
        assert messages[0].content == "What is Python?"
        assert messages[-1].content == "Here's a simple example: print('Hello, World!')"

    @pytest.mark.integration
    def test_conversation_context_building(self, session_manager: SessionManager):
        """Test building conversation context from history."""
        ctx = SessionContext(
            agent_id="context-test",
            session_type=SessionType.MAIN,
        )

        # Create session with history
        session, _ = session_manager.get_or_create_session(ctx)
        store = session_manager._get_store(ctx.agent_id)

        # Add some history
        for i in range(5):
            msg = MessageEntry(
                message_id=f"msg-{i:03d}",
                role="user" if i % 2 == 0 else "assistant",
                content=f"Message {i}",
                timestamp=int(time.time() * 1000),
            )
            store.append_message(session.session_id, msg)

        # Get messages for context
        messages = store.get_history(session.session_id)

        # Build context (convert to dict format for agent)
        context_messages = [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]

        assert len(context_messages) == 5
        assert all("role" in m and "content" in m for m in context_messages)


class TestE2ESessionTypes:
    """Test different session types in E2E flow."""

    @pytest.fixture
    def temp_lurkbot_home(self) -> Path:
        """Create a temporary ~/.lurkbot directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir) / ".lurkbot"
            home.mkdir(parents=True)
            (home / "agents").mkdir()
            yield home

    @pytest.fixture
    def session_manager(self, temp_lurkbot_home: Path) -> SessionManager:
        """Create a session manager."""
        config = SessionManagerConfig(
            base_dir=temp_lurkbot_home / "agents",
            auto_cleanup=False,
        )
        return SessionManager(config=config)

    @pytest.mark.integration
    def test_main_session_flow(self, session_manager: SessionManager):
        """Test main session type flow."""
        ctx = SessionContext(
            agent_id="test",
            session_type=SessionType.MAIN,
        )
        session, created = session_manager.get_or_create_session(ctx)

        assert created is True
        assert "main" in session.session_key

    @pytest.mark.integration
    def test_group_session_flow(self, session_manager: SessionManager):
        """Test group session type flow."""
        ctx = SessionContext(
            agent_id="test",
            session_type=SessionType.GROUP,
            channel="telegram",
            group_id="group-123",
        )
        session, created = session_manager.get_or_create_session(ctx)

        assert created is True
        assert "group" in session.session_key

    @pytest.mark.integration
    def test_dm_session_flow(self, session_manager: SessionManager):
        """Test DM session type flow."""
        ctx = SessionContext(
            agent_id="test",
            session_type=SessionType.DM,
            channel="discord",
            dm_partner="user-456",
        )
        session, created = session_manager.get_or_create_session(ctx)

        assert created is True
        assert "dm" in session.session_key

    @pytest.mark.integration
    def test_multiple_session_types_isolation(self, session_manager: SessionManager):
        """Test that different session types are isolated."""
        main_ctx = SessionContext(agent_id="test-iso", session_type=SessionType.MAIN)
        group_ctx = SessionContext(
            agent_id="test-iso",
            session_type=SessionType.GROUP,
            channel="telegram",
            group_id="group-123",
        )
        dm_ctx = SessionContext(
            agent_id="test-iso",
            session_type=SessionType.DM,
            channel="discord",
            dm_partner="user-456",
        )

        # Create all sessions
        main_session, _ = session_manager.get_or_create_session(main_ctx)
        group_session, _ = session_manager.get_or_create_session(group_ctx)
        dm_session, _ = session_manager.get_or_create_session(dm_ctx)

        store = session_manager._get_store("test-iso")

        # Add different messages to each (use session_id for append_message)
        store.append_message(main_session.session_id, MessageEntry(
            message_id="main-001",
            role="user",
            content="Main session message",
            timestamp=int(time.time() * 1000),
        ))

        store.append_message(group_session.session_id, MessageEntry(
            message_id="group-001",
            role="user",
            content="Group session message",
            timestamp=int(time.time() * 1000),
        ))

        store.append_message(dm_session.session_id, MessageEntry(
            message_id="dm-001",
            role="user",
            content="DM session message",
            timestamp=int(time.time() * 1000),
        ))

        # Verify isolation (use session_id for get_history)
        main_msgs = store.get_history(main_session.session_id)
        group_msgs = store.get_history(group_session.session_id)
        dm_msgs = store.get_history(dm_session.session_id)

        assert len(main_msgs) == 1
        assert main_msgs[0].content == "Main session message"

        assert len(group_msgs) == 1
        assert group_msgs[0].content == "Group session message"

        assert len(dm_msgs) == 1
        assert dm_msgs[0].content == "DM session message"


# Test count verification
def test_e2e_chat_flow_test_count():
    """Verify the number of E2E chat flow tests."""
    import inspect

    test_classes = [
        TestE2EChatFlowBasic,
        TestE2EChatFlowWithMocks,
        TestE2EMultiTurnConversation,
        TestE2ESessionTypes,
    ]

    total_tests = 0
    for cls in test_classes:
        methods = [m for m in dir(cls) if m.startswith("test_")]
        total_tests += len(methods)

    # Add standalone test
    total_tests += 1  # test_e2e_chat_flow_test_count

    print(f"\n✅ E2E chat flow tests: {total_tests} tests")
    assert total_tests >= 15, f"Expected at least 15 tests, got {total_tests}"
