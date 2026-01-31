"""Structured audit logging system.

This module provides comprehensive audit logging for security-critical operations
including tool execution, session management, and configuration changes.

Audit logs are written in JSONL format for easy parsing and analysis.
"""

from __future__ import annotations

import json
import time
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from lurkbot.logging import get_logger

logger = get_logger("audit_log")


class AuditAction(str, Enum):
    """Types of auditable actions."""

    # Session actions
    SESSION_CREATE = "session.create"
    SESSION_UPDATE = "session.update"
    SESSION_DELETE = "session.delete"

    # Tool execution
    TOOL_CALL = "tool.call"
    TOOL_SUCCESS = "tool.success"
    TOOL_FAILURE = "tool.failure"

    # Agent actions
    AGENT_START = "agent.start"
    AGENT_COMPLETE = "agent.complete"
    AGENT_ERROR = "agent.error"

    # Security actions
    AUTH_SUCCESS = "auth.success"
    AUTH_FAILURE = "auth.failure"
    PERMISSION_DENIED = "permission.denied"
    ENCRYPTION_KEY_ROTATE = "encryption.key_rotate"

    # Configuration
    CONFIG_UPDATE = "config.update"
    SKILL_INSTALL = "skill.install"
    SKILL_UNINSTALL = "skill.uninstall"

    # Gateway
    GATEWAY_START = "gateway.start"
    GATEWAY_STOP = "gateway.stop"
    CHANNEL_CONNECT = "channel.connect"
    CHANNEL_DISCONNECT = "channel.disconnect"


class AuditSeverity(str, Enum):
    """Severity levels for audit events."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AuditLogEntry(BaseModel):
    """Structured audit log entry."""

    timestamp: float = Field(description="Unix timestamp in milliseconds")
    action: AuditAction = Field(description="Type of action")
    severity: AuditSeverity = Field(default=AuditSeverity.INFO, description="Event severity")
    user: str | None = Field(default=None, description="User ID or identifier")
    session_id: str | None = Field(default=None, description="Session ID if applicable")
    channel: str | None = Field(default=None, description="Channel name if applicable")
    tool_name: str | None = Field(default=None, description="Tool name for tool actions")
    result: str | None = Field(default=None, description="Action result (success/failure/data)")
    error: str | None = Field(default=None, description="Error message if failed")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional context")
    duration_ms: float | None = Field(default=None, description="Operation duration in ms")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return self.model_dump(exclude_none=True)

    @staticmethod
    def from_dict(data: dict[str, Any]) -> AuditLogEntry:
        """Create from dictionary."""
        return AuditLogEntry(**data)

    def format_human_readable(self) -> str:
        """Format for human-readable display."""
        dt = datetime.fromtimestamp(self.timestamp / 1000)
        time_str = dt.strftime("%Y-%m-%d %H:%M:%S")

        parts = [
            f"[{time_str}]",
            f"[{self.severity.upper()}]",
            f"{self.action.value}",  # Use .value to get string representation
        ]

        if self.user:
            parts.append(f"user={self.user}")
        if self.session_id:
            parts.append(f"session={self.session_id[:12]}")
        if self.tool_name:
            parts.append(f"tool={self.tool_name}")
        if self.result:
            parts.append(f"result={self.result}")
        if self.duration_ms:
            parts.append(f"duration={self.duration_ms:.1f}ms")

        return " ".join(parts)


class AuditLogger:
    """Audit logger with JSONL persistence and rotation."""

    def __init__(self, log_dir: str | Path, max_size_mb: int = 100):
        """Initialize audit logger.

        Args:
            log_dir: Directory for audit logs
            max_size_mb: Maximum log file size before rotation (MB)
        """
        self.log_dir = Path(log_dir).expanduser()
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self._ensure_dir()

    def _ensure_dir(self) -> None:
        """Ensure log directory exists."""
        self.log_dir.mkdir(parents=True, exist_ok=True)
        # Set restrictive permissions (owner only)
        self.log_dir.chmod(0o700)

    def _get_log_file(self) -> Path:
        """Get current log file path.

        Format: audit-{date}.jsonl
        """
        today = datetime.now().strftime("%Y-%m-%d")
        return self.log_dir / f"audit-{today}.jsonl"

    def _should_rotate(self, log_file: Path) -> bool:
        """Check if log file should be rotated."""
        if not log_file.exists():
            return False
        return log_file.stat().st_size >= self.max_size_bytes

    def _rotate_log(self, log_file: Path) -> None:
        """Rotate log file.

        Format: audit-{date}.jsonl -> audit-{date}.{timestamp}.jsonl
        """
        timestamp = int(time.time())
        rotated = log_file.with_name(f"{log_file.stem}.{timestamp}.jsonl")
        log_file.rename(rotated)
        logger.info(f"Rotated audit log: {log_file} -> {rotated}")

    def log(self, entry: AuditLogEntry) -> None:
        """Write audit log entry.

        Args:
            entry: Audit log entry to write
        """
        log_file = self._get_log_file()

        # Check rotation
        if self._should_rotate(log_file):
            self._rotate_log(log_file)

        # Write entry
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(entry.model_dump_json() + "\n")
        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")

    def log_action(
        self,
        action: AuditAction,
        severity: AuditSeverity = AuditSeverity.INFO,
        user: str | None = None,
        session_id: str | None = None,
        channel: str | None = None,
        tool_name: str | None = None,
        result: str | None = None,
        error: str | None = None,
        metadata: dict[str, Any] | None = None,
        duration_ms: float | None = None,
    ) -> None:
        """Log an action (convenience method).

        Args:
            action: Type of action
            severity: Event severity
            user: User identifier
            session_id: Session ID
            channel: Channel name
            tool_name: Tool name
            result: Action result
            error: Error message
            metadata: Additional context
            duration_ms: Operation duration
        """
        entry = AuditLogEntry(
            timestamp=int(time.time() * 1000),
            action=action,
            severity=severity,
            user=user,
            session_id=session_id,
            channel=channel,
            tool_name=tool_name,
            result=result,
            error=error,
            metadata=metadata or {},
            duration_ms=duration_ms,
        )
        self.log(entry)

    def query(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
        action: AuditAction | None = None,
        user: str | None = None,
        session_id: str | None = None,
        severity: AuditSeverity | None = None,
        limit: int = 1000,
    ) -> list[AuditLogEntry]:
        """Query audit logs.

        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            action: Filter by action type
            user: Filter by user
            session_id: Filter by session
            severity: Filter by severity
            limit: Maximum results

        Returns:
            List of matching audit log entries
        """
        results: list[AuditLogEntry] = []

        # Determine files to read
        if start_date and end_date:
            # TODO: Implement date range filtering
            files = list(self.log_dir.glob("audit-*.jsonl"))
        else:
            files = list(self.log_dir.glob("audit-*.jsonl"))

        # Read and filter entries
        for log_file in sorted(files, reverse=True):  # Newest first
            try:
                with open(log_file, encoding="utf-8") as f:
                    for line in f:
                        if not line.strip():
                            continue

                        try:
                            data = json.loads(line)
                            entry = AuditLogEntry.from_dict(data)

                            # Apply filters
                            if action and entry.action != action:
                                continue
                            if user and entry.user != user:
                                continue
                            if session_id and entry.session_id != session_id:
                                continue
                            if severity and entry.severity != severity:
                                continue

                            results.append(entry)

                            if len(results) >= limit:
                                return results

                        except json.JSONDecodeError:
                            logger.warning(f"Invalid JSON in audit log: {log_file}")
            except OSError as e:
                logger.error(f"Failed to read audit log {log_file}: {e}")

        return results

    def get_stats(self) -> dict[str, Any]:
        """Get audit log statistics.

        Returns:
            Dictionary with log statistics
        """
        files = list(self.log_dir.glob("audit-*.jsonl"))
        total_size = sum(f.stat().st_size for f in files)
        total_entries = 0

        action_counts: dict[str, int] = {}
        severity_counts: dict[str, int] = {}

        for log_file in files:
            try:
                with open(log_file, encoding="utf-8") as f:
                    for line in f:
                        if not line.strip():
                            continue
                        total_entries += 1

                        try:
                            data = json.loads(line)
                            action = data.get("action")
                            severity = data.get("severity")

                            if action:
                                action_counts[action] = action_counts.get(action, 0) + 1
                            if severity:
                                severity_counts[severity] = severity_counts.get(severity, 0) + 1
                        except json.JSONDecodeError:
                            pass
            except OSError:
                pass

        return {
            "total_files": len(files),
            "total_size_mb": total_size / (1024 * 1024),
            "total_entries": total_entries,
            "action_counts": action_counts,
            "severity_counts": severity_counts,
        }


# Global audit logger instance
_audit_logger: AuditLogger | None = None


def get_audit_logger(log_dir: str | Path | None = None) -> AuditLogger:
    """Get or create global audit logger.

    Args:
        log_dir: Log directory (defaults to ~/.lurkbot/logs)

    Returns:
        AuditLogger instance
    """
    global _audit_logger

    if _audit_logger is None:
        if log_dir is None:
            log_dir = Path.home() / ".lurkbot" / "logs"
        _audit_logger = AuditLogger(log_dir)

    return _audit_logger


def audit_log(
    action: AuditAction,
    severity: AuditSeverity = AuditSeverity.INFO,
    **kwargs: Any,
) -> None:
    """Convenience function for audit logging.

    Args:
        action: Type of action
        severity: Event severity
        **kwargs: Additional fields (user, session_id, tool_name, etc.)
    """
    logger_instance = get_audit_logger()
    logger_instance.log_action(action, severity, **kwargs)
