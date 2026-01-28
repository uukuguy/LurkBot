"""Sandbox manager for lifecycle management."""

from typing import ClassVar

from loguru import logger

from ..agents.base import SessionType
from .docker import DockerSandbox
from .types import SandboxConfig, SandboxResult


class SandboxManager:
    """Manages sandbox instances based on session type."""

    _instance: ClassVar["SandboxManager | None"] = None

    def __init__(self):
        """Initialize sandbox manager."""
        self._sandboxes: dict[str, DockerSandbox] = {}
        logger.debug("SandboxManager initialized")

    @classmethod
    def get_instance(cls) -> "SandboxManager":
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def should_use_sandbox(self, session_type: SessionType) -> bool:
        """Check if session type should use sandbox.

        Args:
            session_type: Type of session

        Returns:
            True if sandbox should be used
        """
        # main session is trusted, no sandbox needed
        # group and topic sessions are untrusted, use sandbox
        return session_type in {SessionType.GROUP, SessionType.TOPIC}

    def get_sandbox(
        self, session_id: str, config: SandboxConfig | None = None
    ) -> DockerSandbox:
        """Get or create sandbox for session.

        Args:
            session_id: Session identifier
            config: Optional custom sandbox configuration

        Returns:
            Docker sandbox instance
        """
        if session_id not in self._sandboxes:
            sandbox_config = config or SandboxConfig()
            self._sandboxes[session_id] = DockerSandbox(sandbox_config)
            logger.info(f"Created sandbox for session {session_id}")

        return self._sandboxes[session_id]

    def execute(
        self,
        session_id: str,
        session_type: SessionType,
        command: str,
        config: SandboxConfig | None = None,
    ) -> SandboxResult:
        """Execute command, using sandbox if needed.

        Args:
            session_id: Session identifier
            session_type: Type of session
            command: Command to execute
            config: Optional custom sandbox configuration

        Returns:
            Execution result
        """
        if self.should_use_sandbox(session_type):
            # Use sandbox for untrusted sessions
            logger.info(f"Executing command in sandbox for {session_type} session {session_id}")
            sandbox = self.get_sandbox(session_id, config)
            return sandbox.execute(command)
        else:
            # For trusted sessions, would execute directly (not implemented here)
            # In a real implementation, you'd use subprocess or similar
            raise NotImplementedError(
                "Direct execution (without sandbox) not implemented. "
                "Use main session with caution or implement trusted execution."
            )

    def cleanup_session(self, session_id: str) -> None:
        """Cleanup sandbox for session.

        Args:
            session_id: Session identifier
        """
        if session_id in self._sandboxes:
            sandbox = self._sandboxes[session_id]
            sandbox.cleanup()
            del self._sandboxes[session_id]
            logger.info(f"Cleaned up sandbox for session {session_id}")

    def cleanup_all(self) -> None:
        """Cleanup all sandbox instances."""
        for session_id in list(self._sandboxes.keys()):
            self.cleanup_session(session_id)
        logger.info("All sandboxes cleaned up")
