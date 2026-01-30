"""JSONL-based session storage for conversation persistence.

This module provides a JSONL (JSON Lines) format storage backend for
persisting conversation history. Each line in a session file represents
a single message or event.

Session ID Format: {channel}_{chat_id}_{user_id}
Storage Location: ~/.lurkbot/sessions/{session_id}.jsonl
"""

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import aiofiles
from loguru import logger
from pydantic import BaseModel, Field


def _utc_now() -> datetime:
    """Get current UTC time (timezone-aware)."""
    return datetime.now(UTC)


class SessionMessage(BaseModel):
    """A message stored in a session file.

    This is the serialized format for JSONL storage.
    """

    role: str  # "user", "assistant", "system"
    content: str
    timestamp: datetime = Field(default_factory=_utc_now)
    name: str | None = None
    tool_calls: list[dict[str, Any]] | None = None
    tool_call_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SessionMetadata(BaseModel):
    """Metadata for a session.

    Stored as the first line of a session file.
    """

    session_id: str
    channel: str
    chat_id: str
    user_id: str
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)
    session_type: str = "main"
    metadata: dict[str, Any] = Field(default_factory=dict)


class SessionStore:
    """JSONL-based session storage.

    Provides persistent storage for conversation history using JSONL format.
    Each session is stored in a separate file with one JSON object per line.

    Features:
    - Append-only writes for performance
    - Lazy loading of session history
    - Automatic session file creation
    - Thread-safe async operations

    Example:
        ```python
        store = SessionStore(Path.home() / ".lurkbot" / "sessions")
        await store.initialize()

        # Save a message
        await store.append_message(
            session_id="telegram_123_456",
            message=SessionMessage(role="user", content="Hello!")
        )

        # Load session history
        messages = await store.load_messages("telegram_123_456")
        ```
    """

    def __init__(self, sessions_dir: Path) -> None:
        """Initialize session store.

        Args:
            sessions_dir: Directory to store session files
        """
        self.sessions_dir = Path(sessions_dir)
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the session store.

        Creates the sessions directory if it doesn't exist.
        """
        if self._initialized:
            return

        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self._initialized = True
        logger.info(f"Session store initialized at {self.sessions_dir}")

    def _get_session_path(self, session_id: str) -> Path:
        """Get the file path for a session.

        Args:
            session_id: Session identifier

        Returns:
            Path to the session JSONL file
        """
        # Sanitize session_id to prevent path traversal
        # Remove any path separators and dangerous patterns
        safe_id = re.sub(r"[/\\]", "_", session_id)  # Replace slashes
        safe_id = re.sub(r"\.{2,}", "_", safe_id)  # Replace .. sequences
        safe_id = safe_id.strip(".")  # Remove leading/trailing dots
        return self.sessions_dir / f"{safe_id}.jsonl"

    @staticmethod
    def generate_session_id(channel: str, chat_id: str, user_id: str) -> str:
        """Generate a session ID from channel, chat, and user IDs.

        Args:
            channel: Channel name (e.g., "telegram", "discord")
            chat_id: Chat/conversation identifier
            user_id: User identifier

        Returns:
            Session ID in format: {channel}_{chat_id}_{user_id}
        """
        return f"{channel}_{chat_id}_{user_id}"

    async def session_exists(self, session_id: str) -> bool:
        """Check if a session file exists.

        Args:
            session_id: Session identifier

        Returns:
            True if session file exists
        """
        await self.initialize()
        return self._get_session_path(session_id).exists()

    async def create_session(
        self,
        session_id: str,
        channel: str,
        chat_id: str,
        user_id: str,
        session_type: str = "main",
        metadata: dict[str, Any] | None = None,
    ) -> SessionMetadata:
        """Create a new session.

        Args:
            session_id: Session identifier
            channel: Channel name
            chat_id: Chat identifier
            user_id: User identifier
            session_type: Session type (main, group, dm, topic)
            metadata: Additional metadata

        Returns:
            Session metadata object

        Raises:
            FileExistsError: If session already exists
        """
        await self.initialize()

        path = self._get_session_path(session_id)
        if path.exists():
            raise FileExistsError(f"Session {session_id} already exists")

        meta = SessionMetadata(
            session_id=session_id,
            channel=channel,
            chat_id=chat_id,
            user_id=user_id,
            session_type=session_type,
            metadata=metadata or {},
        )

        # Write metadata as first line
        async with aiofiles.open(path, mode="w", encoding="utf-8") as f:
            await f.write(meta.model_dump_json() + "\n")

        logger.info(f"Created session: {session_id}")
        return meta

    async def get_or_create_session(
        self,
        session_id: str,
        channel: str,
        chat_id: str,
        user_id: str,
        session_type: str = "main",
        metadata: dict[str, Any] | None = None,
    ) -> SessionMetadata:
        """Get existing session or create a new one.

        Args:
            session_id: Session identifier
            channel: Channel name
            chat_id: Chat identifier
            user_id: User identifier
            session_type: Session type
            metadata: Additional metadata

        Returns:
            Session metadata object
        """
        await self.initialize()

        if await self.session_exists(session_id):
            return await self.load_metadata(session_id)

        return await self.create_session(
            session_id=session_id,
            channel=channel,
            chat_id=chat_id,
            user_id=user_id,
            session_type=session_type,
            metadata=metadata,
        )

    async def load_metadata(self, session_id: str) -> SessionMetadata:
        """Load session metadata.

        Args:
            session_id: Session identifier

        Returns:
            Session metadata object

        Raises:
            FileNotFoundError: If session doesn't exist
        """
        await self.initialize()

        path = self._get_session_path(session_id)
        if not path.exists():
            raise FileNotFoundError(f"Session {session_id} not found")

        async with aiofiles.open(path, encoding="utf-8") as f:
            first_line = await f.readline()
            if not first_line:
                raise ValueError(f"Session file {session_id} is empty")
            return SessionMetadata.model_validate_json(first_line)

    async def load_messages(
        self,
        session_id: str,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[SessionMessage]:
        """Load messages from a session.

        Args:
            session_id: Session identifier
            limit: Maximum number of messages to load (None = all)
            offset: Number of messages to skip from the start

        Returns:
            List of session messages
        """
        await self.initialize()

        path = self._get_session_path(session_id)
        if not path.exists():
            return []

        messages: list[SessionMessage] = []
        line_count = 0

        async with aiofiles.open(path, encoding="utf-8") as f:
            async for line in f:
                line = line.strip()
                if not line:
                    continue

                line_count += 1

                # Skip first line (metadata)
                if line_count == 1:
                    continue

                # Apply offset
                if (
                    line_count - 2 < offset
                ):  # -2 because line_count starts at 1 and first line is metadata
                    continue

                # Parse message
                try:
                    data = json.loads(line)
                    # Check if this is a message (has 'role' field) vs metadata
                    if "role" in data:
                        messages.append(SessionMessage.model_validate(data))
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON line in session {session_id}")
                    continue

                # Apply limit
                if limit and len(messages) >= limit:
                    break

        logger.debug(f"Loaded {len(messages)} messages from session {session_id}")
        return messages

    async def append_message(
        self,
        session_id: str,
        message: SessionMessage,
    ) -> None:
        """Append a message to a session.

        Args:
            session_id: Session identifier
            message: Message to append

        Raises:
            FileNotFoundError: If session doesn't exist
        """
        await self.initialize()

        path = self._get_session_path(session_id)
        if not path.exists():
            raise FileNotFoundError(f"Session {session_id} not found")

        async with aiofiles.open(path, mode="a", encoding="utf-8") as f:
            await f.write(message.model_dump_json() + "\n")

        logger.debug(f"Appended message to session {session_id}: {message.role}")

    async def append_messages(
        self,
        session_id: str,
        messages: list[SessionMessage],
    ) -> None:
        """Append multiple messages to a session.

        More efficient than calling append_message multiple times.

        Args:
            session_id: Session identifier
            messages: Messages to append
        """
        await self.initialize()

        path = self._get_session_path(session_id)
        if not path.exists():
            raise FileNotFoundError(f"Session {session_id} not found")

        async with aiofiles.open(path, mode="a", encoding="utf-8") as f:
            for message in messages:
                await f.write(message.model_dump_json() + "\n")

        logger.debug(f"Appended {len(messages)} messages to session {session_id}")

    async def update_metadata(
        self,
        session_id: str,
        **updates: Any,
    ) -> SessionMetadata:
        """Update session metadata.

        This requires rewriting the entire file (expensive operation).
        Use sparingly - prefer storing metadata separately if frequent updates needed.

        Args:
            session_id: Session identifier
            **updates: Fields to update

        Returns:
            Updated session metadata
        """
        await self.initialize()

        path = self._get_session_path(session_id)
        if not path.exists():
            raise FileNotFoundError(f"Session {session_id} not found")

        # Read all lines
        async with aiofiles.open(path, encoding="utf-8") as f:
            lines = await f.readlines()

        if not lines:
            raise ValueError(f"Session file {session_id} is empty")

        # Update metadata
        meta = SessionMetadata.model_validate_json(lines[0])
        for key, value in updates.items():
            if hasattr(meta, key):
                setattr(meta, key, value)
        meta.updated_at = _utc_now()

        # Write back
        lines[0] = meta.model_dump_json() + "\n"
        async with aiofiles.open(path, mode="w", encoding="utf-8") as f:
            await f.writelines(lines)

        logger.debug(f"Updated metadata for session {session_id}")
        return meta

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session.

        Args:
            session_id: Session identifier

        Returns:
            True if session was deleted, False if it didn't exist
        """
        await self.initialize()

        path = self._get_session_path(session_id)
        if not path.exists():
            return False

        path.unlink()
        logger.info(f"Deleted session: {session_id}")
        return True

    async def list_sessions(self) -> list[str]:
        """List all session IDs.

        Returns:
            List of session IDs
        """
        await self.initialize()

        sessions = []
        for path in self.sessions_dir.glob("*.jsonl"):
            sessions.append(path.stem)
        return sessions

    async def get_message_count(self, session_id: str) -> int:
        """Get the number of messages in a session.

        Args:
            session_id: Session identifier

        Returns:
            Number of messages (excluding metadata line)
        """
        await self.initialize()

        path = self._get_session_path(session_id)
        if not path.exists():
            return 0

        count = 0
        async with aiofiles.open(path, encoding="utf-8") as f:
            async for line in f:
                if line.strip():
                    count += 1

        # Subtract 1 for metadata line
        return max(0, count - 1)

    async def clear_messages(self, session_id: str) -> None:
        """Clear all messages from a session, keeping only metadata.

        Args:
            session_id: Session identifier
        """
        await self.initialize()

        path = self._get_session_path(session_id)
        if not path.exists():
            raise FileNotFoundError(f"Session {session_id} not found")

        # Read metadata
        async with aiofiles.open(path, encoding="utf-8") as f:
            first_line = await f.readline()

        # Write back only metadata
        async with aiofiles.open(path, mode="w", encoding="utf-8") as f:
            await f.write(first_line)

        logger.info(f"Cleared messages from session {session_id}")
