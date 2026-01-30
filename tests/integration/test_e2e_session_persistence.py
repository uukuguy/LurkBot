"""End-to-end integration tests for Session persistence flow.

Tests the complete Session persistence flow:
- Session creation and storage
- Message history persistence
- Session retrieval and restoration
- Multi-session management
- Session lifecycle (active -> completed -> cleanup)
"""

import json
import tempfile
import time
from pathlib import Path
from typing import Any

import pytest

from lurkbot.agents.types import SessionType
from lurkbot.sessions.manager import SessionManager, SessionManagerConfig, SessionContext
from lurkbot.sessions.store import SessionStore, generate_session_id, generate_message_id
from lurkbot.sessions.types import (
    MessageEntry,
    SessionEntry,
    SessionState,
    SessionListItem,
)


class TestE2ESessionPersistence:
    """Test Session persistence flow."""

    @pytest.fixture
    def temp_agent_dir(self) -> Path:
        """Create a temporary agent directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir) / "agents" / "test-agent"

    @pytest.fixture
    def session_store(self, temp_agent_dir: Path) -> SessionStore:
        """Create a session store instance."""
        return SessionStore(temp_agent_dir)

    @pytest.mark.integration
    def test_session_store_initialization(self, session_store: SessionStore):
        """Test session store initializes correctly."""
        assert session_store.agent_dir.exists()
        assert session_store.sessions_file.parent.exists()

    @pytest.mark.integration
    def test_session_id_generation(self):
        """Test session ID generation format."""
        session_id = generate_session_id()
        assert session_id.startswith("ses_")
        assert len(session_id) == 16  # "ses_" + 12 chars

    @pytest.mark.integration
    def test_message_id_generation(self):
        """Test message ID generation format."""
        message_id = generate_message_id()
        assert message_id.startswith("msg_")
        assert len(message_id) == 16  # "msg_" + 12 chars

    @pytest.mark.integration
    def test_session_creation(self, session_store: SessionStore):
        """Test creating a new session."""
        session = session_store.create(
            session_key="agent:test-agent:main",
            session_type=SessionType.MAIN,
            channel="cli",
            model="claude-3-sonnet",
            model_provider="anthropic",
        )

        assert session.session_id.startswith("ses_")
        assert session.session_key == "agent:test-agent:main"
        assert session.session_type == "main"
        assert session.state == SessionState.ACTIVE
        assert session.channel == "cli"
        assert session.model == "claude-3-sonnet"

    @pytest.mark.integration
    def test_session_retrieval_by_key(self, session_store: SessionStore):
        """Test retrieving session by key."""
        # Create session
        created = session_store.create(
            session_key="agent:test-agent:main",
            session_type=SessionType.MAIN,
        )

        # Retrieve by key
        retrieved = session_store.get("agent:test-agent:main")

        assert retrieved is not None
        assert retrieved.session_id == created.session_id
        assert retrieved.session_key == created.session_key

    @pytest.mark.integration
    def test_session_retrieval_by_id(self, session_store: SessionStore):
        """Test retrieving session by ID."""
        # Create session
        created = session_store.create(
            session_key="agent:test-agent:main",
            session_type=SessionType.MAIN,
        )

        # Retrieve by ID
        retrieved = session_store.get_by_id(created.session_id)

        assert retrieved is not None
        assert retrieved.session_id == created.session_id

    @pytest.mark.integration
    def test_session_update(self, session_store: SessionStore):
        """Test updating session fields."""
        # Create session
        session_store.create(
            session_key="agent:test-agent:main",
            session_type=SessionType.MAIN,
            channel="cli",
        )

        # Update session
        updated = session_store.update(
            "agent:test-agent:main",
            state=SessionState.PAUSED,
            last_channel="telegram",
            label="My test session",
        )

        assert updated is not None
        assert updated.state == SessionState.PAUSED
        assert updated.last_channel == "telegram"
        assert updated.label == "My test session"

    @pytest.mark.integration
    def test_session_deletion(self, session_store: SessionStore):
        """Test deleting a session."""
        # Create session
        session_store.create(
            session_key="agent:test-agent:main",
            session_type=SessionType.MAIN,
        )

        # Delete session
        result = session_store.delete("agent:test-agent:main")
        assert result is True

        # Verify deletion
        retrieved = session_store.get("agent:test-agent:main")
        assert retrieved is None


class TestE2EMessagePersistence:
    """Test Message history persistence."""

    @pytest.fixture
    def temp_agent_dir(self) -> Path:
        """Create a temporary agent directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir) / "agents" / "test-agent"

    @pytest.fixture
    def session_store(self, temp_agent_dir: Path) -> SessionStore:
        """Create a session store instance."""
        return SessionStore(temp_agent_dir)

    @pytest.mark.integration
    def test_append_message(self, session_store: SessionStore):
        """Test appending message to history."""
        # Create session
        session = session_store.create(
            session_key="agent:test-agent:main",
            session_type=SessionType.MAIN,
        )

        # Append message
        message = MessageEntry(
            message_id="msg_test001",
            role="user",
            content="Hello, world!",
            timestamp=int(time.time() * 1000),
        )
        session_store.append_message(session.session_id, message)

        # Verify history file exists
        history_file = session_store._get_history_file(session.session_id)
        assert history_file.exists()

    @pytest.mark.integration
    def test_get_history(self, session_store: SessionStore):
        """Test retrieving message history."""
        # Create session
        session = session_store.create(
            session_key="agent:test-agent:main",
            session_type=SessionType.MAIN,
        )

        # Append messages
        messages = [
            MessageEntry(
                message_id="msg_001",
                role="user",
                content="Hello",
                timestamp=int(time.time() * 1000),
            ),
            MessageEntry(
                message_id="msg_002",
                role="assistant",
                content="Hi there!",
                timestamp=int(time.time() * 1000) + 1000,
            ),
            MessageEntry(
                message_id="msg_003",
                role="user",
                content="How are you?",
                timestamp=int(time.time() * 1000) + 2000,
            ),
        ]

        for msg in messages:
            session_store.append_message(session.session_id, msg)

        # Retrieve history
        history = session_store.get_history(session.session_id)

        assert len(history) == 3
        assert history[0].message_id == "msg_001"
        assert history[0].content == "Hello"
        assert history[1].message_id == "msg_002"
        assert history[1].content == "Hi there!"
        assert history[2].message_id == "msg_003"

    @pytest.mark.integration
    def test_get_history_with_limit(self, session_store: SessionStore):
        """Test history retrieval with limit."""
        # Create session
        session = session_store.create(
            session_key="agent:test-agent:main",
            session_type=SessionType.MAIN,
        )

        # Append multiple messages
        for i in range(10):
            message = MessageEntry(
                message_id=f"msg_{i:03d}",
                role="user" if i % 2 == 0 else "assistant",
                content=f"Message {i}",
                timestamp=int(time.time() * 1000) + i * 1000,
            )
            session_store.append_message(session.session_id, message)

        # Retrieve with limit
        history = session_store.get_history(session.session_id, limit=5)

        assert len(history) == 5
        assert history[0].message_id == "msg_000"
        assert history[4].message_id == "msg_004"

    @pytest.mark.integration
    def test_get_history_with_offset(self, session_store: SessionStore):
        """Test history retrieval with offset."""
        # Create session
        session = session_store.create(
            session_key="agent:test-agent:main",
            session_type=SessionType.MAIN,
        )

        # Append messages
        for i in range(10):
            message = MessageEntry(
                message_id=f"msg_{i:03d}",
                role="user",
                content=f"Message {i}",
                timestamp=int(time.time() * 1000) + i * 1000,
            )
            session_store.append_message(session.session_id, message)

        # Retrieve with offset
        history = session_store.get_history(session.session_id, offset=3)

        assert len(history) == 7
        assert history[0].message_id == "msg_003"

    @pytest.mark.integration
    def test_get_message_count(self, session_store: SessionStore):
        """Test getting message count."""
        # Create session
        session = session_store.create(
            session_key="agent:test-agent:main",
            session_type=SessionType.MAIN,
        )

        # Append messages
        for i in range(5):
            message = MessageEntry(
                message_id=f"msg_{i:03d}",
                role="user",
                content=f"Message {i}",
                timestamp=int(time.time() * 1000),
            )
            session_store.append_message(session.session_id, message)

        # Get count
        count = session_store.get_message_count(session.session_id)
        assert count == 5

    @pytest.mark.integration
    def test_get_latest_assistant_reply(self, session_store: SessionStore):
        """Test getting latest assistant reply."""
        # Create session
        session = session_store.create(
            session_key="agent:test-agent:main",
            session_type=SessionType.MAIN,
        )

        # Append messages
        messages = [
            MessageEntry(
                message_id="msg_001",
                role="user",
                content="Hello",
                timestamp=int(time.time() * 1000),
            ),
            MessageEntry(
                message_id="msg_002",
                role="assistant",
                content="First reply",
                timestamp=int(time.time() * 1000) + 1000,
            ),
            MessageEntry(
                message_id="msg_003",
                role="user",
                content="Another question",
                timestamp=int(time.time() * 1000) + 2000,
            ),
            MessageEntry(
                message_id="msg_004",
                role="assistant",
                content="Latest reply",
                timestamp=int(time.time() * 1000) + 3000,
            ),
        ]

        for msg in messages:
            session_store.append_message(session.session_id, msg)

        # Get latest reply
        reply = session_store.get_latest_assistant_reply(session.session_id)
        assert reply == "Latest reply"

    @pytest.mark.integration
    def test_clear_history(self, session_store: SessionStore):
        """Test clearing message history."""
        # Create session
        session = session_store.create(
            session_key="agent:test-agent:main",
            session_type=SessionType.MAIN,
        )

        # Append messages
        for i in range(5):
            message = MessageEntry(
                message_id=f"msg_{i:03d}",
                role="user",
                content=f"Message {i}",
                timestamp=int(time.time() * 1000),
                input_tokens=100,
                output_tokens=50,
            )
            session_store.append_message(session.session_id, message)

        # Clear history
        session_store.clear_history(session.session_id)

        # Verify cleared
        history = session_store.get_history(session.session_id)
        assert len(history) == 0

        # Verify token counts reset
        updated_session = session_store.get_by_id(session.session_id)
        assert updated_session is not None
        assert updated_session.input_tokens == 0
        assert updated_session.output_tokens == 0


class TestE2EMultiSessionManagement:
    """Test multi-session management."""

    @pytest.fixture
    def temp_agent_dir(self) -> Path:
        """Create a temporary agent directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir) / "agents" / "test-agent"

    @pytest.fixture
    def session_store(self, temp_agent_dir: Path) -> SessionStore:
        """Create a session store instance."""
        return SessionStore(temp_agent_dir)

    @pytest.mark.integration
    def test_create_multiple_sessions(self, session_store: SessionStore):
        """Test creating multiple sessions."""
        sessions = []
        for i in range(5):
            session = session_store.create(
                session_key=f"agent:test-agent:session-{i}",
                session_type=SessionType.MAIN,
            )
            sessions.append(session)

        # All sessions should have unique IDs
        session_ids = [s.session_id for s in sessions]
        assert len(set(session_ids)) == 5

    @pytest.mark.integration
    def test_list_sessions(self, session_store: SessionStore):
        """Test listing sessions."""
        # Create sessions
        for i in range(5):
            session_store.create(
                session_key=f"agent:test-agent:session-{i}",
                session_type=SessionType.MAIN,
            )

        # List sessions
        sessions = session_store.list()

        assert len(sessions) == 5
        assert all(isinstance(s, SessionListItem) for s in sessions)

    @pytest.mark.integration
    def test_list_sessions_filter_by_type(self, session_store: SessionStore):
        """Test listing sessions with type filter."""
        # Create sessions of different types
        session_store.create(
            session_key="agent:test-agent:main",
            session_type=SessionType.MAIN,
        )
        session_store.create(
            session_key="agent:test-agent:group:123",
            session_type=SessionType.GROUP,
        )
        session_store.create(
            session_key="agent:test-agent:subagent:sub1",
            session_type=SessionType.SUBAGENT,
        )

        # Filter by type
        main_sessions = session_store.list(session_type=SessionType.MAIN)
        group_sessions = session_store.list(session_type=SessionType.GROUP)
        subagent_sessions = session_store.list(session_type=SessionType.SUBAGENT)

        assert len(main_sessions) == 1
        assert len(group_sessions) == 1
        assert len(subagent_sessions) == 1

    @pytest.mark.integration
    def test_list_sessions_filter_by_state(self, session_store: SessionStore):
        """Test listing sessions with state filter."""
        # Create sessions
        session_store.create(
            session_key="agent:test-agent:active",
            session_type=SessionType.MAIN,
        )
        session_store.create(
            session_key="agent:test-agent:paused",
            session_type=SessionType.MAIN,
        )
        session_store.update("agent:test-agent:paused", state=SessionState.PAUSED)

        session_store.create(
            session_key="agent:test-agent:completed",
            session_type=SessionType.MAIN,
        )
        session_store.update("agent:test-agent:completed", state=SessionState.COMPLETED)

        # Filter by state
        active_sessions = session_store.list(state=SessionState.ACTIVE)
        paused_sessions = session_store.list(state=SessionState.PAUSED)
        completed_sessions = session_store.list(state=SessionState.COMPLETED)

        assert len(active_sessions) == 1
        assert len(paused_sessions) == 1
        assert len(completed_sessions) == 1

    @pytest.mark.integration
    def test_get_or_create_existing(self, session_store: SessionStore):
        """Test get_or_create with existing session."""
        # Create session
        original = session_store.create(
            session_key="agent:test-agent:main",
            session_type=SessionType.MAIN,
        )

        # Get or create (should return existing)
        session, created = session_store.get_or_create(
            session_key="agent:test-agent:main",
            session_type=SessionType.MAIN,
        )

        assert created is False
        assert session.session_id == original.session_id

    @pytest.mark.integration
    def test_get_or_create_new(self, session_store: SessionStore):
        """Test get_or_create with new session."""
        session, created = session_store.get_or_create(
            session_key="agent:test-agent:main",
            session_type=SessionType.MAIN,
        )

        assert created is True
        assert session.session_key == "agent:test-agent:main"


class TestE2ESessionLifecycle:
    """Test Session lifecycle management."""

    @pytest.fixture
    def temp_agent_dir(self) -> Path:
        """Create a temporary agent directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir) / "agents" / "test-agent"

    @pytest.fixture
    def session_store(self, temp_agent_dir: Path) -> SessionStore:
        """Create a session store instance."""
        return SessionStore(temp_agent_dir)

    @pytest.mark.integration
    def test_session_state_transitions(self, session_store: SessionStore):
        """Test session state transitions."""
        # Create session (ACTIVE)
        session = session_store.create(
            session_key="agent:test-agent:main",
            session_type=SessionType.MAIN,
        )
        assert session.state == SessionState.ACTIVE

        # Pause session
        session = session_store.update(session.session_key, state=SessionState.PAUSED)
        assert session.state == SessionState.PAUSED

        # Resume session
        session = session_store.update(session.session_key, state=SessionState.ACTIVE)
        assert session.state == SessionState.ACTIVE

        # Complete session
        session = session_store.update(session.session_key, state=SessionState.COMPLETED)
        assert session.state == SessionState.COMPLETED

    @pytest.mark.integration
    def test_token_tracking(self, session_store: SessionStore):
        """Test token usage tracking."""
        # Create session
        session = session_store.create(
            session_key="agent:test-agent:main",
            session_type=SessionType.MAIN,
        )

        # Append messages with token usage
        messages = [
            MessageEntry(
                message_id="msg_001",
                role="user",
                content="Hello",
                timestamp=int(time.time() * 1000),
                input_tokens=100,
                output_tokens=0,
            ),
            MessageEntry(
                message_id="msg_002",
                role="assistant",
                content="Hi!",
                timestamp=int(time.time() * 1000),
                input_tokens=0,
                output_tokens=50,
            ),
            MessageEntry(
                message_id="msg_003",
                role="user",
                content="Question",
                timestamp=int(time.time() * 1000),
                input_tokens=200,
                output_tokens=0,
            ),
            MessageEntry(
                message_id="msg_004",
                role="assistant",
                content="Answer",
                timestamp=int(time.time() * 1000),
                input_tokens=0,
                output_tokens=150,
            ),
        ]

        for msg in messages:
            session_store.append_message(session.session_id, msg)

        # Check token counts
        updated = session_store.get_by_id(session.session_id)
        assert updated.input_tokens == 300  # 100 + 200
        assert updated.output_tokens == 200  # 50 + 150
        assert updated.total_tokens == 500

    @pytest.mark.integration
    def test_session_persistence_across_instances(self, temp_agent_dir: Path):
        """Test session data persists across store instances."""
        # Create session with first store instance
        store1 = SessionStore(temp_agent_dir)
        session = store1.create(
            session_key="agent:test-agent:main",
            session_type=SessionType.MAIN,
            label="Persistent session",
        )

        # Append message
        message = MessageEntry(
            message_id="msg_001",
            role="user",
            content="Test message",
            timestamp=int(time.time() * 1000),
        )
        store1.append_message(session.session_id, message)

        # Create new store instance
        store2 = SessionStore(temp_agent_dir)

        # Verify session persists
        retrieved = store2.get("agent:test-agent:main")
        assert retrieved is not None
        assert retrieved.label == "Persistent session"

        # Verify history persists
        history = store2.get_history(retrieved.session_id)
        assert len(history) == 1
        assert history[0].content == "Test message"


class TestE2ESessionManager:
    """Test SessionManager integration."""

    @pytest.fixture
    def temp_base_dir(self) -> Path:
        """Create a temporary base directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir) / "agents"

    @pytest.fixture
    def session_manager(self, temp_base_dir: Path) -> SessionManager:
        """Create a session manager instance."""
        config = SessionManagerConfig(
            base_dir=temp_base_dir,
            auto_cleanup=False,
            max_sessions_per_agent=100,
            max_subagent_depth=3,
        )
        return SessionManager(config=config)

    @pytest.mark.integration
    def test_session_manager_get_or_create(self, session_manager: SessionManager):
        """Test SessionManager get_or_create."""
        ctx = SessionContext(
            agent_id="test-agent",
            session_type=SessionType.MAIN,
        )

        session, created = session_manager.get_or_create_session(ctx)

        assert created is True
        assert session.session_key.startswith("agent:test-agent:")
        assert session.session_type == "main"

    @pytest.mark.integration
    def test_session_manager_multiple_agents(self, session_manager: SessionManager):
        """Test SessionManager with multiple agents."""
        # Create sessions for different agents
        agents = ["agent-1", "agent-2", "agent-3"]
        sessions = []

        for agent_id in agents:
            ctx = SessionContext(
                agent_id=agent_id,
                session_type=SessionType.MAIN,
            )
            session, created = session_manager.get_or_create_session(ctx)
            sessions.append(session)

        # Verify all sessions are unique
        session_ids = [s.session_id for s in sessions]
        assert len(set(session_ids)) == 3

        # Verify each agent has its own store
        for agent_id in agents:
            store = session_manager._get_store(agent_id)
            assert store is not None
            agent_sessions = store.list()
            assert len(agent_sessions) == 1


# Test count verification
def test_e2e_session_persistence_test_count():
    """Verify the number of E2E Session persistence tests."""
    import inspect

    test_classes = [
        TestE2ESessionPersistence,
        TestE2EMessagePersistence,
        TestE2EMultiSessionManagement,
        TestE2ESessionLifecycle,
        TestE2ESessionManager,
    ]

    total_tests = 0
    for cls in test_classes:
        methods = [m for m in dir(cls) if m.startswith("test_")]
        total_tests += len(methods)

    # Add standalone test
    total_tests += 1  # test_e2e_session_persistence_test_count

    print(f"\n✅ E2E Session Persistence tests: {total_tests} tests")
    assert total_tests >= 25, f"Expected at least 25 tests, got {total_tests}"
