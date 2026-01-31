"""Tests for audit logging system."""

import json
import tempfile
import time
from pathlib import Path

import pytest

from lurkbot.security.audit_log import (
    AuditAction,
    AuditLogEntry,
    AuditLogger,
    AuditSeverity,
    audit_log,
    get_audit_logger,
)


class TestAuditLogEntry:
    """Test audit log entry model."""

    def test_create_entry(self):
        """Test creating audit log entry."""
        entry = AuditLogEntry(
            timestamp=1234567890000,
            action=AuditAction.TOOL_CALL,
            severity=AuditSeverity.INFO,
            user="user123",
            session_id="ses_abc",
            tool_name="test_tool",
            result="success",
        )

        assert entry.timestamp == 1234567890000
        assert entry.action == AuditAction.TOOL_CALL
        assert entry.user == "user123"
        assert entry.tool_name == "test_tool"

    def test_to_dict(self):
        """Test converting entry to dictionary."""
        entry = AuditLogEntry(
            timestamp=1234567890000,
            action=AuditAction.SESSION_CREATE,
            severity=AuditSeverity.INFO,
            user="user123",
        )

        data = entry.to_dict()
        assert data["timestamp"] == 1234567890000
        assert data["action"] == "session.create"
        assert data["user"] == "user123"
        # None fields should be excluded
        assert "tool_name" not in data

    def test_from_dict(self):
        """Test creating entry from dictionary."""
        data = {
            "timestamp": 1234567890000,
            "action": "tool.call",
            "severity": "info",
            "user": "user123",
        }

        entry = AuditLogEntry.from_dict(data)
        assert entry.timestamp == 1234567890000
        assert entry.action == AuditAction.TOOL_CALL
        assert entry.user == "user123"

    def test_format_human_readable(self):
        """Test human-readable formatting."""
        entry = AuditLogEntry(
            timestamp=int(time.time() * 1000),
            action=AuditAction.TOOL_SUCCESS,
            severity=AuditSeverity.INFO,
            user="user123",
            session_id="ses_abc123",
            tool_name="test_tool",
            result="ok",
            duration_ms=123.5,
        )

        formatted = entry.format_human_readable()
        assert "INFO" in formatted
        assert "tool.success" in formatted
        assert "user=user123" in formatted
        assert "tool=test_tool" in formatted
        assert "duration=123.5ms" in formatted


class TestAuditLogger:
    """Test audit logger functionality."""

    def test_create_logger(self):
        """Test creating audit logger."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = AuditLogger(tmpdir)
            assert logger.log_dir == Path(tmpdir)
            assert logger.log_dir.exists()

    def test_log_directory_permissions(self):
        """Test log directory has secure permissions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_dir = Path(tmpdir) / "logs"
            logger = AuditLogger(log_dir)

            stat = log_dir.stat()
            mode = stat.st_mode & 0o777
            assert mode == 0o700  # Owner only

    def test_log_entry(self):
        """Test logging an entry."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = AuditLogger(tmpdir)

            entry = AuditLogEntry(
                timestamp=int(time.time() * 1000),
                action=AuditAction.TOOL_CALL,
                severity=AuditSeverity.INFO,
                tool_name="test_tool",
            )

            logger.log(entry)

            # Check log file was created
            log_file = logger._get_log_file()
            assert log_file.exists()

            # Check content
            with open(log_file) as f:
                line = f.readline()
                data = json.loads(line)
                assert data["action"] == "tool.call"
                assert data["tool_name"] == "test_tool"

    def test_log_action_convenience(self):
        """Test log_action convenience method."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = AuditLogger(tmpdir)

            logger.log_action(
                action=AuditAction.SESSION_CREATE,
                severity=AuditSeverity.INFO,
                user="user123",
                session_id="ses_abc",
                metadata={"channel": "telegram"},
            )

            log_file = logger._get_log_file()
            with open(log_file) as f:
                line = f.readline()
                data = json.loads(line)
                assert data["action"] == "session.create"
                assert data["user"] == "user123"
                assert data["metadata"]["channel"] == "telegram"

    def test_log_rotation(self):
        """Test log file rotation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Set small max size to trigger rotation
            logger = AuditLogger(tmpdir, max_size_mb=0.001)  # 1KB

            # Write entries until rotation happens
            for i in range(100):
                logger.log_action(
                    action=AuditAction.TOOL_CALL,
                    tool_name=f"tool_{i}",
                    result="x" * 100,  # Make entry larger
                )

            # Check that rotation occurred
            log_files = list(Path(tmpdir).glob("audit-*.jsonl"))
            assert len(log_files) > 1  # Should have rotated file

    def test_query_logs(self):
        """Test querying audit logs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = AuditLogger(tmpdir)

            # Log different actions
            logger.log_action(
                action=AuditAction.TOOL_CALL, tool_name="tool1", user="user1"
            )
            logger.log_action(
                action=AuditAction.TOOL_SUCCESS, tool_name="tool1", user="user1"
            )
            logger.log_action(
                action=AuditAction.SESSION_CREATE, user="user2", session_id="ses_123"
            )

            # Query all
            results = logger.query()
            assert len(results) == 3

            # Query by action
            tool_calls = logger.query(action=AuditAction.TOOL_CALL)
            assert len(tool_calls) == 1
            assert tool_calls[0].tool_name == "tool1"

            # Query by user
            user1_logs = logger.query(user="user1")
            assert len(user1_logs) == 2

            # Query by session
            session_logs = logger.query(session_id="ses_123")
            assert len(session_logs) == 1

    def test_query_with_limit(self):
        """Test query with limit."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = AuditLogger(tmpdir)

            # Log many entries
            for i in range(50):
                logger.log_action(action=AuditAction.TOOL_CALL, tool_name=f"tool_{i}")

            # Query with limit
            results = logger.query(limit=10)
            assert len(results) == 10

    def test_get_stats(self):
        """Test getting audit log statistics."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = AuditLogger(tmpdir)

            # Log various actions
            logger.log_action(action=AuditAction.TOOL_CALL)
            logger.log_action(action=AuditAction.TOOL_CALL)
            logger.log_action(action=AuditAction.SESSION_CREATE)
            logger.log_action(
                action=AuditAction.TOOL_FAILURE, severity=AuditSeverity.ERROR
            )

            stats = logger.get_stats()

            assert stats["total_entries"] == 4
            assert stats["total_files"] == 1
            assert stats["action_counts"]["tool.call"] == 2
            assert stats["action_counts"]["session.create"] == 1
            assert stats["severity_counts"]["info"] == 3
            assert stats["severity_counts"]["error"] == 1


class TestGlobalAuditLogger:
    """Test global audit logger functionality."""

    def test_get_audit_logger(self):
        """Test getting global audit logger."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = get_audit_logger(log_dir=tmpdir)
            assert logger is not None
            assert isinstance(logger, AuditLogger)


class TestAuditActions:
    """Test audit action types."""

    def test_all_action_types(self):
        """Test that all action types are valid."""
        actions = [
            AuditAction.SESSION_CREATE,
            AuditAction.TOOL_CALL,
            AuditAction.AGENT_START,
            AuditAction.AUTH_SUCCESS,
            AuditAction.CONFIG_UPDATE,
            AuditAction.GATEWAY_START,
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            logger = AuditLogger(tmpdir)

            for action in actions:
                logger.log_action(action=action)

            results = logger.query()
            assert len(results) == len(actions)

    def test_severity_levels(self):
        """Test different severity levels."""
        severities = [
            AuditSeverity.DEBUG,
            AuditSeverity.INFO,
            AuditSeverity.WARNING,
            AuditSeverity.ERROR,
            AuditSeverity.CRITICAL,
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            logger = AuditLogger(tmpdir)

            for severity in severities:
                logger.log_action(action=AuditAction.TOOL_CALL, severity=severity)

            results = logger.query()
            assert len(results) == len(severities)

            # Query by severity
            errors = logger.query(severity=AuditSeverity.ERROR)
            assert len(errors) == 1


class TestAuditLogPerformance:
    """Test audit logging performance."""

    def test_logging_performance(self):
        """Test logging performance."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = AuditLogger(tmpdir)

            start = time.time()
            for i in range(1000):
                logger.log_action(
                    action=AuditAction.TOOL_CALL, tool_name=f"tool_{i}", result="ok"
                )
            elapsed = time.time() - start

            # Should be able to log 1000 entries in < 1 second
            assert elapsed < 1.0, f"Logging too slow: {elapsed:.3f}s for 1000 entries"

    def test_query_performance(self):
        """Test query performance."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = AuditLogger(tmpdir)

            # Create 1000 log entries
            for i in range(1000):
                logger.log_action(action=AuditAction.TOOL_CALL, user=f"user_{i % 10}")

            # Query performance
            start = time.time()
            results = logger.query(user="user_5")
            elapsed = time.time() - start

            # Should be able to query in < 0.1 seconds
            assert elapsed < 0.1, f"Query too slow: {elapsed:.3f}s"
            assert len(results) == 100  # 1000 / 10
