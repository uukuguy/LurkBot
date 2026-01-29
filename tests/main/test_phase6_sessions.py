"""Tests for the session management system (Phase 6).

This module tests:
- SessionStore: JSONL persistence
- SessionManager: Lifecycle management
- Session tools: sessions_spawn, sessions_list, etc.
- Subagent: Spawn and announce flow
"""

import asyncio
import tempfile
from pathlib import Path

import pytest

from lurkbot.agents.types import AgentContext, SessionType
from lurkbot.sessions import (
    MessageEntry,
    SessionContext,
    SessionEntry,
    SessionManager,
    SessionManagerConfig,
    SessionState,
    SessionStore,
    generate_message_id,
    generate_session_id,
)
from lurkbot.agents.subagent import (
    SpawnParams,
    build_subagent_system_prompt,
    spawn_subagent,
    SUBAGENT_DENY_LIST,
)


class TestSessionStore:
    """Test SessionStore functionality."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def store(self, temp_dir):
        """Create a SessionStore instance."""
        return SessionStore(temp_dir)

    def test_create_session(self, store):
        """Test creating a new session."""
        session = store.create(
            session_key="agent:test:main",
            session_type=SessionType.MAIN,
            channel="cli",
            model="claude-sonnet-4-20250514",
        )

        assert session.session_id.startswith("ses_")
        assert session.session_key == "agent:test:main"
        assert session.session_type == "main"
        assert session.state == SessionState.ACTIVE
        assert session.channel == "cli"

    def test_get_session(self, store):
        """Test retrieving a session by key."""
        created = store.create(
            session_key="agent:test:main",
            session_type=SessionType.MAIN,
        )

        retrieved = store.get("agent:test:main")
        assert retrieved is not None
        assert retrieved.session_id == created.session_id
        assert retrieved.session_key == created.session_key

    def test_get_session_not_found(self, store):
        """Test retrieving a non-existent session."""
        result = store.get("agent:nonexistent:main")
        assert result is None

    def test_update_session(self, store):
        """Test updating a session."""
        store.create(
            session_key="agent:test:main",
            session_type=SessionType.MAIN,
        )

        updated = store.update(
            "agent:test:main",
            label="Updated Label",
            model="claude-opus-4-20250514",
        )

        assert updated is not None
        assert updated.label == "Updated Label"
        assert updated.model == "claude-opus-4-20250514"

    def test_delete_session(self, store):
        """Test deleting a session."""
        store.create(
            session_key="agent:test:main",
            session_type=SessionType.MAIN,
        )

        result = store.delete("agent:test:main")
        assert result is True

        # Verify deletion
        retrieved = store.get("agent:test:main")
        assert retrieved is None

    def test_list_sessions(self, store):
        """Test listing sessions."""
        # Create multiple sessions
        store.create(session_key="agent:test:main", session_type=SessionType.MAIN)
        store.create(session_key="agent:test:group:discord:123", session_type=SessionType.GROUP)
        store.create(session_key="agent:test:dm:telegram:456", session_type=SessionType.DM)

        all_sessions = store.list()
        assert len(all_sessions) == 3

        # Filter by type
        main_sessions = store.list(session_type=SessionType.MAIN)
        assert len(main_sessions) == 1

    def test_append_and_get_history(self, store):
        """Test appending messages and retrieving history."""
        session = store.create(
            session_key="agent:test:main",
            session_type=SessionType.MAIN,
        )

        # Append messages
        msg1 = MessageEntry(
            message_id=generate_message_id(),
            role="user",
            content="Hello",
            timestamp=1000,
        )
        msg2 = MessageEntry(
            message_id=generate_message_id(),
            role="assistant",
            content="Hi there!",
            timestamp=2000,
        )

        store.append_message(session.session_id, msg1)
        store.append_message(session.session_id, msg2)

        # Retrieve history
        history = store.get_history(session.session_id)
        assert len(history) == 2
        assert history[0].role == "user"
        assert history[1].role == "assistant"

    def test_get_latest_assistant_reply(self, store):
        """Test getting the latest assistant reply."""
        session = store.create(
            session_key="agent:test:main",
            session_type=SessionType.MAIN,
        )

        store.append_message(
            session.session_id,
            MessageEntry(
                message_id=generate_message_id(),
                role="user",
                content="Question 1",
                timestamp=1000,
            ),
        )
        store.append_message(
            session.session_id,
            MessageEntry(
                message_id=generate_message_id(),
                role="assistant",
                content="Answer 1",
                timestamp=2000,
            ),
        )
        store.append_message(
            session.session_id,
            MessageEntry(
                message_id=generate_message_id(),
                role="user",
                content="Question 2",
                timestamp=3000,
            ),
        )
        store.append_message(
            session.session_id,
            MessageEntry(
                message_id=generate_message_id(),
                role="assistant",
                content="Answer 2",
                timestamp=4000,
            ),
        )

        latest = store.get_latest_assistant_reply(session.session_id)
        assert latest == "Answer 2"


class TestSessionManager:
    """Test SessionManager functionality."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def manager(self, temp_dir):
        """Create a SessionManager instance."""
        config = SessionManagerConfig(base_dir=temp_dir)
        return SessionManager(config)

    def test_get_or_create_session(self, manager):
        """Test get_or_create_session method."""
        ctx = SessionContext(
            agent_id="test_agent",
            session_type=SessionType.MAIN,
        )

        # First call creates
        session1, created1 = manager.get_or_create_session(ctx)
        assert created1 is True
        assert session1.session_type == "main"

        # Second call retrieves
        session2, created2 = manager.get_or_create_session(ctx)
        assert created2 is False
        assert session2.session_id == session1.session_id

    def test_spawn_subagent_session(self, manager):
        """Test creating a subagent session."""
        # Create parent session first
        parent_ctx = SessionContext(
            agent_id="test_agent",
            session_type=SessionType.MAIN,
        )
        parent, _ = manager.get_or_create_session(parent_ctx)

        # Spawn subagent
        subagent = manager.spawn_subagent_session(
            agent_id="test_agent",
            parent_session_key=parent.session_key,
            task="Research something",
            label="Research Task",
        )

        assert subagent.session_type == "subagent"
        assert subagent.parent_session == parent.session_key
        assert "subagent" in subagent.session_key

    def test_subagent_depth_limit(self, manager):
        """Test that subagent depth is limited."""
        # Reduce max depth for testing
        manager.config.max_subagent_depth = 2

        # Create chain: main -> sub1 -> sub2 -> sub3 (should fail)
        parent_ctx = SessionContext(
            agent_id="test_agent",
            session_type=SessionType.MAIN,
        )
        parent, _ = manager.get_or_create_session(parent_ctx)

        sub1 = manager.spawn_subagent_session(
            agent_id="test_agent",
            parent_session_key=parent.session_key,
            task="Level 1",
        )

        sub2 = manager.spawn_subagent_session(
            agent_id="test_agent",
            parent_session_key=sub1.session_key,
            task="Level 2",
        )

        # This should raise an error (depth exceeded)
        with pytest.raises(ValueError, match="depth"):
            manager.spawn_subagent_session(
                agent_id="test_agent",
                parent_session_key=sub2.session_key,
                task="Level 3",
            )


class TestSubagentSystem:
    """Test subagent system functionality."""

    def test_build_subagent_system_prompt(self):
        """Test subagent system prompt generation."""
        prompt = build_subagent_system_prompt(
            requester_session_key="agent:test:main",
            child_session_key="agent:test:subagent:sub_123",
            task="Research Python best practices",
            label="Research",
        )

        assert "subagent" in prompt.lower()
        assert "Research Python best practices" in prompt
        assert "Research" in prompt
        assert "agent:test:main" in prompt
        assert "agent:test:subagent:sub_123" in prompt
        assert "NO spawning other subagents" in prompt

    def test_subagent_deny_list(self):
        """Test that deny list contains expected tools."""
        expected_denied = [
            "sessions_spawn",
            "sessions_list",
            "sessions_history",
            "sessions_send",
            "cron",
            "message",
        ]

        for tool in expected_denied:
            assert tool in SUBAGENT_DENY_LIST


class TestSessionTools:
    """Test session-related tools."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def context(self):
        """Create a test AgentContext."""
        return AgentContext(
            session_id="ses_test123",
            session_key="agent:test:main",
            session_type=SessionType.MAIN,
        )

    @pytest.mark.asyncio
    async def test_sessions_list_tool(self, temp_dir, context):
        """Test sessions_list tool."""
        from lurkbot.sessions import reset_session_manager, SessionManagerConfig
        from lurkbot.tools.builtin.session_tools import sessions_list_tool

        # Reset manager with test config
        reset_session_manager()
        from lurkbot.sessions.manager import _manager, SessionManager
        import lurkbot.sessions.manager as mgr

        config = SessionManagerConfig(base_dir=temp_dir)
        mgr._manager = SessionManager(config)

        # Create some sessions
        manager = mgr._manager
        ctx = SessionContext(agent_id="test", session_type=SessionType.MAIN)
        manager.get_or_create_session(ctx)

        # Call tool
        result = await sessions_list_tool({}, context)

        # Check result - should have sessions array
        result_text = result.to_text()
        assert "sessions" in result_text
        assert "error" not in result_text.lower() or "error" not in result_text

        # Cleanup
        reset_session_manager()


class TestHelperFunctions:
    """Test helper functions."""

    def test_generate_session_id(self):
        """Test session ID generation."""
        id1 = generate_session_id()
        id2 = generate_session_id()

        assert id1.startswith("ses_")
        assert id2.startswith("ses_")
        assert id1 != id2
        assert len(id1) == 16  # "ses_" + 12 chars

    def test_generate_message_id(self):
        """Test message ID generation."""
        id1 = generate_message_id()
        id2 = generate_message_id()

        assert id1.startswith("msg_")
        assert id2.startswith("msg_")
        assert id1 != id2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
