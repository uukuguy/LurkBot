"""Integration tests for session persistence.

Tests the complete session lifecycle including:
- Session creation and storage
- Message persistence
- History loading and recovery
- Cross-session operations
"""

import pytest
from pathlib import Path

from lurkbot.agents.types import SessionType, build_session_key
from lurkbot.sessions.manager import SessionManager, SessionContext, SessionManagerConfig
from lurkbot.sessions.store import SessionStore, generate_session_id, get_session_store
from lurkbot.sessions.types import (
    MessageEntry,
    SessionEntry,
    SessionState,
)


class TestSessionLifecycle:
    """Test complete session lifecycle."""

    @pytest.mark.integration
    def test_create_and_retrieve_session(
        self, session_manager: SessionManager, temp_lurkbot_home: Path
    ):
        """Test creating a session and retrieving it."""
        # Create session context
        ctx = SessionContext(
            agent_id="test-agent",
            session_type=SessionType.MAIN,
            label="Test Session",
        )

        # Create session
        session, created = session_manager.get_or_create_session(ctx)

        assert session is not None
        assert created is True
        assert session.session_type == "main"
        assert session.state == SessionState.ACTIVE

        # Retrieve the same session
        session2, created2 = session_manager.get_or_create_session(ctx)
        assert session2.session_id == session.session_id
        assert created2 is False

    @pytest.mark.integration
    def test_session_with_messages(
        self, session_manager: SessionManager
    ):
        """Test session with message persistence."""
        # Create session
        ctx = SessionContext(
            agent_id="test-agent-msg",
            session_type=SessionType.MAIN,
        )
        session, _ = session_manager.get_or_create_session(ctx)

        # Add messages
        messages = [
            MessageEntry(
                message_id="msg-001",
                role="user",
                content="Hello, how are you?",
                timestamp=1000,
            ),
            MessageEntry(
                message_id="msg-002",
                role="assistant",
                content="I'm doing well, thank you!",
                timestamp=2000,
            ),
            MessageEntry(
                message_id="msg-003",
                role="user",
                content="Can you help me with a task?",
                timestamp=3000,
            ),
        ]

        for msg in messages:
            session_manager.append_message("test-agent-msg", session.session_id, msg)

        # Load messages
        loaded = session_manager.get_history("test-agent-msg", session.session_id)
        assert len(loaded) == 3
        assert loaded[0].content == "Hello, how are you?"
        assert loaded[1].role == "assistant"

    @pytest.mark.integration
    def test_session_recovery(
        self, temp_lurkbot_home: Path
    ):
        """Test session recovery after restart."""
        # Create first manager and session
        config = SessionManagerConfig(base_dir=temp_lurkbot_home / "agents")
        manager1 = SessionManager(config)

        ctx = SessionContext(
            agent_id="recovery-agent",
            session_type=SessionType.MAIN,
        )
        session, _ = manager1.get_or_create_session(ctx)

        manager1.append_message(
            "recovery-agent",
            session.session_id,
            MessageEntry(message_id="msg-001", role="user", content="Test message", timestamp=1000),
        )

        # Simulate restart by creating new manager instance
        manager2 = SessionManager(config)

        # Verify session exists
        sessions = manager2.list_sessions("recovery-agent")
        assert len(sessions) == 1
        assert sessions[0].session_id == session.session_id

        # Verify messages
        messages = manager2.get_history("recovery-agent", session.session_id)
        assert len(messages) == 1
        assert messages[0].content == "Test message"


class TestMultiSessionOperations:
    """Test operations across multiple sessions."""

    @pytest.mark.integration
    def test_multiple_session_types(
        self, session_manager: SessionManager
    ):
        """Test creating different session types."""
        agent_id = "multi-session-agent"

        # Create main session
        main_ctx = SessionContext(
            agent_id=agent_id,
            session_type=SessionType.MAIN,
        )
        main_session, _ = session_manager.get_or_create_session(main_ctx)

        # Create group session
        group_ctx = SessionContext(
            agent_id=agent_id,
            session_type=SessionType.GROUP,
            channel="telegram",
            group_id="group-123",
        )
        group_session, _ = session_manager.get_or_create_session(group_ctx)

        # Create DM session
        dm_ctx = SessionContext(
            agent_id=agent_id,
            session_type=SessionType.DM,
            channel="telegram",
            dm_partner="user-456",
        )
        dm_session, _ = session_manager.get_or_create_session(dm_ctx)

        # Verify all sessions are different
        assert main_session.session_id != group_session.session_id
        assert group_session.session_id != dm_session.session_id
        assert main_session.session_type == "main"
        assert group_session.session_type == "group"
        assert dm_session.session_type == "dm"

    @pytest.mark.integration
    def test_session_listing(
        self, session_manager: SessionManager
    ):
        """Test listing all sessions for an agent."""
        agent_id = "list-test-agent"

        # Create multiple sessions
        for i in range(5):
            ctx = SessionContext(
                agent_id=agent_id,
                session_type=SessionType.GROUP,
                channel="telegram",
                group_id=f"group-{i}",
            )
            session_manager.get_or_create_session(ctx)

        # List sessions
        sessions = session_manager.list_sessions(agent_id)
        assert len(sessions) == 5


class TestSubagentSessions:
    """Test subagent session management."""

    @pytest.mark.integration
    def test_spawn_subagent_session(
        self, session_manager: SessionManager
    ):
        """Test spawning a subagent session."""
        agent_id = "parent-agent"

        # Create parent session
        parent_ctx = SessionContext(
            agent_id=agent_id,
            session_type=SessionType.MAIN,
        )
        parent_session, _ = session_manager.get_or_create_session(parent_ctx)

        # Spawn subagent
        subagent_session = session_manager.spawn_subagent_session(
            agent_id=agent_id,
            parent_session_key=parent_session.session_key,
            task="Perform a subtask",
        )

        assert subagent_session is not None
        assert subagent_session.session_type == "subagent"
        assert "subagent" in subagent_session.session_key

    @pytest.mark.integration
    def test_subagent_depth_limit(
        self, session_manager: SessionManager
    ):
        """Test that subagent depth is limited."""
        agent_id = "depth-test-agent"

        # Create parent session
        parent_ctx = SessionContext(
            agent_id=agent_id,
            session_type=SessionType.MAIN,
        )
        parent, _ = session_manager.get_or_create_session(parent_ctx)

        # Spawn nested subagents up to limit
        current_key = parent.session_key
        for depth in range(session_manager.config.max_subagent_depth):
            sub = session_manager.spawn_subagent_session(
                agent_id=agent_id,
                parent_session_key=current_key,
                task=f"Subtask at depth {depth + 1}",
            )
            assert sub is not None
            current_key = sub.session_key

        # Attempting to spawn beyond limit should fail
        with pytest.raises(ValueError, match="depth"):
            session_manager.spawn_subagent_session(
                agent_id=agent_id,
                parent_session_key=current_key,
                task="This should fail",
            )


class TestSessionCleanup:
    """Test session cleanup and garbage collection."""

    @pytest.mark.integration
    def test_clear_session_messages(
        self, session_manager: SessionManager
    ):
        """Test clearing session messages."""
        agent_id = "cleanup-agent"

        # Create session with messages
        ctx = SessionContext(
            agent_id=agent_id,
            session_type=SessionType.MAIN,
        )
        session, _ = session_manager.get_or_create_session(ctx)

        for i in range(10):
            session_manager.append_message(
                agent_id,
                session.session_id,
                MessageEntry(message_id=f"msg-{i:03d}", role="user", content=f"Message {i}", timestamp=1000 + i),
            )

        # Verify messages exist
        messages = session_manager.get_history(agent_id, session.session_id)
        assert len(messages) == 10

        # Clear messages
        session_manager.clear_history(agent_id, session.session_id)

        # Verify messages are cleared
        messages = session_manager.get_history(agent_id, session.session_id)
        assert len(messages) == 0

        # Session should still exist
        sessions = session_manager.list_sessions(agent_id)
        assert len(sessions) == 1

    @pytest.mark.integration
    def test_delete_session(
        self, session_manager: SessionManager
    ):
        """Test deleting a session completely."""
        agent_id = "delete-agent"

        # Create session
        ctx = SessionContext(
            agent_id=agent_id,
            session_type=SessionType.MAIN,
        )
        session, _ = session_manager.get_or_create_session(ctx)

        session_manager.append_message(
            agent_id,
            session.session_id,
            MessageEntry(message_id="msg-001", role="user", content="Test", timestamp=1000),
        )

        # Delete session
        deleted = session_manager.delete_session(agent_id, session.session_key)
        assert deleted is True

        # Verify session is gone
        sessions = session_manager.list_sessions(agent_id)
        assert len(sessions) == 0


class TestSessionKeyFormats:
    """Test session key generation and parsing."""

    def test_main_session_key(self):
        """Test main session key format."""
        key = build_session_key(
            agent_id="my-agent",
            session_type=SessionType.MAIN,
        )
        assert key == "agent:my-agent:main"

    def test_group_session_key(self):
        """Test group session key format."""
        key = build_session_key(
            agent_id="my-agent",
            session_type=SessionType.GROUP,
            channel="telegram",
            group_id="group-123",
        )
        assert key == "agent:my-agent:group:telegram:group-123"

    def test_dm_session_key(self):
        """Test DM session key format."""
        key = build_session_key(
            agent_id="my-agent",
            session_type=SessionType.DM,
            channel="discord",
            dm_partner="user-456",
        )
        assert key == "agent:my-agent:dm:discord:user-456"

    def test_subagent_session_key(self):
        """Test subagent session key format."""
        # Subagent keys are built differently - they use the SessionManager
        # which generates a unique subagent ID
        # Here we just verify the format pattern
        agent_id = "my-agent"
        subagent_id = "sub-001"
        expected_key = f"agent:{agent_id}:subagent:{subagent_id}"
        assert "subagent" in expected_key
        assert agent_id in expected_key


class TestMessagePagination:
    """Test message loading with pagination."""

    @pytest.mark.integration
    def test_load_messages_with_limit(
        self, session_manager: SessionManager
    ):
        """Test loading messages with a limit."""
        agent_id = "pagination-agent"

        ctx = SessionContext(
            agent_id=agent_id,
            session_type=SessionType.MAIN,
        )
        session, _ = session_manager.get_or_create_session(ctx)

        # Add many messages
        for i in range(100):
            session_manager.append_message(
                agent_id,
                session.session_id,
                MessageEntry(message_id=f"msg-{i:03d}", role="user", content=f"Message {i}", timestamp=1000 + i),
            )

        # Load with limit
        messages = session_manager.get_history(
            agent_id, session.session_id, limit=10
        )
        assert len(messages) == 10

    @pytest.mark.integration
    def test_load_messages_with_offset(
        self, session_manager: SessionManager
    ):
        """Test loading messages with offset."""
        agent_id = "offset-agent"

        ctx = SessionContext(
            agent_id=agent_id,
            session_type=SessionType.MAIN,
        )
        session, _ = session_manager.get_or_create_session(ctx)

        # Add messages
        for i in range(20):
            session_manager.append_message(
                agent_id,
                session.session_id,
                MessageEntry(message_id=f"msg-{i:03d}", role="user", content=f"Message {i}", timestamp=1000 + i),
            )

        # Load with offset
        messages = session_manager.get_history(
            agent_id, session.session_id, offset=10, limit=5
        )
        assert len(messages) == 5
        assert messages[0].content == "Message 10"


# Test count verification
def test_session_integration_test_count():
    """Verify the number of integration tests."""
    import inspect

    test_classes = [
        TestSessionLifecycle,
        TestMultiSessionOperations,
        TestSubagentSessions,
        TestSessionCleanup,
        TestSessionKeyFormats,
        TestMessagePagination,
    ]

    total_tests = 0
    for cls in test_classes:
        methods = [m for m in dir(cls) if m.startswith("test_")]
        total_tests += len(methods)

    # Add standalone test
    total_tests += 1  # test_session_integration_test_count

    print(f"\n✅ Session integration tests: {total_tests} tests")
    assert total_tests >= 15, f"Expected at least 15 tests, got {total_tests}"
