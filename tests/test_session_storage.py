"""Tests for session storage."""

import pytest

from lurkbot.storage.jsonl import SessionMessage, SessionMetadata, SessionStore


class TestSessionStore:
    """Test SessionStore class."""

    @pytest.fixture
    async def store(self, tmp_path):
        """Create a session store in a temp directory."""
        store = SessionStore(tmp_path / "sessions")
        await store.initialize()
        return store

    @pytest.fixture
    async def session_id(self):
        """Sample session ID."""
        return "telegram_123_456"

    async def test_initialize_creates_directory(self, tmp_path):
        """Test that initialize creates the sessions directory."""
        sessions_dir = tmp_path / "sessions"
        assert not sessions_dir.exists()

        store = SessionStore(sessions_dir)
        await store.initialize()

        assert sessions_dir.exists()
        assert sessions_dir.is_dir()

    async def test_generate_session_id(self):
        """Test session ID generation."""
        session_id = SessionStore.generate_session_id("telegram", "123", "456")
        assert session_id == "telegram_123_456"

        session_id = SessionStore.generate_session_id("discord", "guild123", "user789")
        assert session_id == "discord_guild123_user789"

    async def test_create_session(self, store, session_id):
        """Test session creation."""
        meta = await store.create_session(
            session_id=session_id,
            channel="telegram",
            chat_id="123",
            user_id="456",
        )

        assert meta.session_id == session_id
        assert meta.channel == "telegram"
        assert meta.chat_id == "123"
        assert meta.user_id == "456"
        assert meta.session_type == "main"

    async def test_create_session_with_metadata(self, store, session_id):
        """Test session creation with custom metadata."""
        meta = await store.create_session(
            session_id=session_id,
            channel="telegram",
            chat_id="123",
            user_id="456",
            session_type="group",
            metadata={"custom_key": "custom_value"},
        )

        assert meta.session_type == "group"
        assert meta.metadata["custom_key"] == "custom_value"

    async def test_create_session_duplicate_raises_error(self, store, session_id):
        """Test that creating a duplicate session raises an error."""
        await store.create_session(
            session_id=session_id,
            channel="telegram",
            chat_id="123",
            user_id="456",
        )

        with pytest.raises(FileExistsError):
            await store.create_session(
                session_id=session_id,
                channel="telegram",
                chat_id="123",
                user_id="456",
            )

    async def test_session_exists(self, store, session_id):
        """Test session existence check."""
        assert not await store.session_exists(session_id)

        await store.create_session(
            session_id=session_id,
            channel="telegram",
            chat_id="123",
            user_id="456",
        )

        assert await store.session_exists(session_id)

    async def test_get_or_create_session_new(self, store, session_id):
        """Test get_or_create_session creates new session."""
        assert not await store.session_exists(session_id)

        meta = await store.get_or_create_session(
            session_id=session_id,
            channel="telegram",
            chat_id="123",
            user_id="456",
        )

        assert meta.session_id == session_id
        assert await store.session_exists(session_id)

    async def test_get_or_create_session_existing(self, store, session_id):
        """Test get_or_create_session returns existing session."""
        # Create first
        await store.create_session(
            session_id=session_id,
            channel="telegram",
            chat_id="123",
            user_id="456",
            metadata={"original": True},
        )

        # Get existing
        meta = await store.get_or_create_session(
            session_id=session_id,
            channel="telegram",
            chat_id="123",
            user_id="456",
            metadata={"new": True},  # Should be ignored
        )

        assert meta.metadata.get("original") is True
        assert "new" not in meta.metadata

    async def test_load_metadata(self, store, session_id):
        """Test loading session metadata."""
        await store.create_session(
            session_id=session_id,
            channel="telegram",
            chat_id="123",
            user_id="456",
            session_type="dm",
        )

        meta = await store.load_metadata(session_id)
        assert meta.session_id == session_id
        assert meta.session_type == "dm"

    async def test_load_metadata_not_found(self, store):
        """Test loading metadata for non-existent session."""
        with pytest.raises(FileNotFoundError):
            await store.load_metadata("nonexistent")

    async def test_append_message(self, store, session_id):
        """Test appending a message to a session."""
        await store.create_session(
            session_id=session_id,
            channel="telegram",
            chat_id="123",
            user_id="456",
        )

        msg = SessionMessage(role="user", content="Hello!")
        await store.append_message(session_id, msg)

        messages = await store.load_messages(session_id)
        assert len(messages) == 1
        assert messages[0].role == "user"
        assert messages[0].content == "Hello!"

    async def test_append_messages_batch(self, store, session_id):
        """Test appending multiple messages in batch."""
        await store.create_session(
            session_id=session_id,
            channel="telegram",
            chat_id="123",
            user_id="456",
        )

        messages = [
            SessionMessage(role="user", content="Hello!"),
            SessionMessage(role="assistant", content="Hi there!"),
            SessionMessage(role="user", content="How are you?"),
        ]
        await store.append_messages(session_id, messages)

        loaded = await store.load_messages(session_id)
        assert len(loaded) == 3
        assert loaded[0].content == "Hello!"
        assert loaded[1].content == "Hi there!"
        assert loaded[2].content == "How are you?"

    async def test_load_messages_with_limit(self, store, session_id):
        """Test loading messages with a limit."""
        await store.create_session(
            session_id=session_id,
            channel="telegram",
            chat_id="123",
            user_id="456",
        )

        # Add 5 messages
        for i in range(5):
            msg = SessionMessage(role="user", content=f"Message {i}")
            await store.append_message(session_id, msg)

        # Load only first 3
        messages = await store.load_messages(session_id, limit=3)
        assert len(messages) == 3
        assert messages[0].content == "Message 0"
        assert messages[2].content == "Message 2"

    async def test_load_messages_with_offset(self, store, session_id):
        """Test loading messages with an offset."""
        await store.create_session(
            session_id=session_id,
            channel="telegram",
            chat_id="123",
            user_id="456",
        )

        # Add 5 messages
        for i in range(5):
            msg = SessionMessage(role="user", content=f"Message {i}")
            await store.append_message(session_id, msg)

        # Skip first 2
        messages = await store.load_messages(session_id, offset=2)
        assert len(messages) == 3
        assert messages[0].content == "Message 2"
        assert messages[2].content == "Message 4"

    async def test_load_messages_empty_session(self, store, session_id):
        """Test loading messages from empty session."""
        await store.create_session(
            session_id=session_id,
            channel="telegram",
            chat_id="123",
            user_id="456",
        )

        messages = await store.load_messages(session_id)
        assert len(messages) == 0

    async def test_load_messages_nonexistent_session(self, store):
        """Test loading messages from non-existent session returns empty list."""
        messages = await store.load_messages("nonexistent")
        assert len(messages) == 0

    async def test_append_message_nonexistent_session(self, store):
        """Test appending to non-existent session raises error."""
        msg = SessionMessage(role="user", content="Hello!")
        with pytest.raises(FileNotFoundError):
            await store.append_message("nonexistent", msg)

    async def test_update_metadata(self, store, session_id):
        """Test updating session metadata."""
        await store.create_session(
            session_id=session_id,
            channel="telegram",
            chat_id="123",
            user_id="456",
            session_type="main",
        )

        # Add a message first
        msg = SessionMessage(role="user", content="Hello!")
        await store.append_message(session_id, msg)

        # Update metadata
        updated = await store.update_metadata(session_id, session_type="group")
        assert updated.session_type == "group"

        # Verify message is preserved
        messages = await store.load_messages(session_id)
        assert len(messages) == 1
        assert messages[0].content == "Hello!"

    async def test_delete_session(self, store, session_id):
        """Test deleting a session."""
        await store.create_session(
            session_id=session_id,
            channel="telegram",
            chat_id="123",
            user_id="456",
        )

        assert await store.session_exists(session_id)

        result = await store.delete_session(session_id)
        assert result is True
        assert not await store.session_exists(session_id)

    async def test_delete_nonexistent_session(self, store):
        """Test deleting a non-existent session returns False."""
        result = await store.delete_session("nonexistent")
        assert result is False

    async def test_list_sessions(self, store):
        """Test listing all sessions."""
        # Create multiple sessions
        for i in range(3):
            await store.create_session(
                session_id=f"session_{i}",
                channel="telegram",
                chat_id=str(i),
                user_id="456",
            )

        sessions = await store.list_sessions()
        assert len(sessions) == 3
        assert "session_0" in sessions
        assert "session_1" in sessions
        assert "session_2" in sessions

    async def test_get_message_count(self, store, session_id):
        """Test getting message count."""
        await store.create_session(
            session_id=session_id,
            channel="telegram",
            chat_id="123",
            user_id="456",
        )

        assert await store.get_message_count(session_id) == 0

        # Add messages
        for i in range(5):
            msg = SessionMessage(role="user", content=f"Message {i}")
            await store.append_message(session_id, msg)

        assert await store.get_message_count(session_id) == 5

    async def test_clear_messages(self, store, session_id):
        """Test clearing all messages from a session."""
        await store.create_session(
            session_id=session_id,
            channel="telegram",
            chat_id="123",
            user_id="456",
        )

        # Add messages
        for i in range(5):
            msg = SessionMessage(role="user", content=f"Message {i}")
            await store.append_message(session_id, msg)

        assert await store.get_message_count(session_id) == 5

        # Clear messages
        await store.clear_messages(session_id)

        assert await store.get_message_count(session_id) == 0

        # Session still exists
        assert await store.session_exists(session_id)

        # Metadata preserved
        meta = await store.load_metadata(session_id)
        assert meta.session_id == session_id

    async def test_path_traversal_protection(self, store):
        """Test that path traversal attacks are prevented."""
        # These should be sanitized
        dangerous_ids = [
            "../../../etc/passwd",
            "/etc/passwd",
            "..\\..\\Windows\\System32",
        ]

        for session_id in dangerous_ids:
            path = store._get_session_path(session_id)
            # Path should be inside sessions_dir
            assert str(path).startswith(str(store.sessions_dir))
            # No .. components
            assert ".." not in str(path)


class TestSessionMessage:
    """Test SessionMessage model."""

    def test_create_basic_message(self):
        """Test creating a basic message."""
        msg = SessionMessage(role="user", content="Hello!")
        assert msg.role == "user"
        assert msg.content == "Hello!"
        assert msg.timestamp is not None
        assert msg.name is None
        assert msg.tool_calls is None

    def test_create_message_with_all_fields(self):
        """Test creating a message with all fields."""
        tool_calls = [{"id": "1", "type": "function", "function": {"name": "test"}}]
        msg = SessionMessage(
            role="assistant",
            content="Using tool...",
            name="Claude",
            tool_calls=tool_calls,
            tool_call_id="call_123",
            metadata={"key": "value"},
        )

        assert msg.role == "assistant"
        assert msg.tool_calls == tool_calls
        assert msg.tool_call_id == "call_123"
        assert msg.metadata["key"] == "value"

    def test_message_serialization(self):
        """Test message JSON serialization."""
        msg = SessionMessage(role="user", content="Hello!")
        json_str = msg.model_dump_json()

        # Should be valid JSON
        import json

        data = json.loads(json_str)
        assert data["role"] == "user"
        assert data["content"] == "Hello!"

    def test_message_deserialization(self):
        """Test message deserialization."""
        json_str = '{"role": "user", "content": "Hello!", "timestamp": "2025-01-29T00:00:00"}'
        msg = SessionMessage.model_validate_json(json_str)
        assert msg.role == "user"
        assert msg.content == "Hello!"


class TestSessionMetadata:
    """Test SessionMetadata model."""

    def test_create_metadata(self):
        """Test creating session metadata."""
        meta = SessionMetadata(
            session_id="test_session",
            channel="telegram",
            chat_id="123",
            user_id="456",
        )

        assert meta.session_id == "test_session"
        assert meta.channel == "telegram"
        assert meta.chat_id == "123"
        assert meta.user_id == "456"
        assert meta.session_type == "main"
        assert meta.created_at is not None
        assert meta.updated_at is not None

    def test_metadata_serialization(self):
        """Test metadata JSON serialization."""
        meta = SessionMetadata(
            session_id="test_session",
            channel="telegram",
            chat_id="123",
            user_id="456",
        )
        json_str = meta.model_dump_json()

        import json

        data = json.loads(json_str)
        assert data["session_id"] == "test_session"
        assert data["channel"] == "telegram"
