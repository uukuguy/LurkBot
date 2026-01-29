"""Unit tests for Phase 7: Heartbeat + Cron autonomous running systems.

Tests cover:
1. HeartbeatConfig - Configuration management
2. HeartbeatRunner - Heartbeat execution flow
3. CronService - Job management and scheduling
4. CronSchedule types - at, every, cron
5. CronPayload types - systemEvent, agentTurn
"""

import asyncio
import tempfile
import time
from datetime import datetime
from pathlib import Path

import pytest

from lurkbot.autonomous import (
    HEARTBEAT_OK_TOKEN,
    ActiveHours,
    AgentTurnPayload,
    CronJob,
    CronJobState,
    CronRunResult,
    CronScheduleAt,
    CronScheduleCron,
    CronScheduleEvery,
    CronService,
    CronServiceStatus,
    HeartbeatConfig,
    HeartbeatEventPayload,
    HeartbeatRunner,
    SystemEventPayload,
)


# =============================================================================
# Heartbeat Tests
# =============================================================================


class TestHeartbeatConfig:
    """Tests for HeartbeatConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = HeartbeatConfig()
        assert config.enabled is True
        assert config.every == "5m"
        assert config.target == "last"
        assert config.ack_max_chars == 100
        assert config.prompt is None
        assert config.model is None
        assert config.active_hours is None

    def test_custom_config(self):
        """Test custom configuration values."""
        config = HeartbeatConfig(
            enabled=False,
            every="30s",
            target="main",
            prompt="Custom prompt",
            model="anthropic:claude-sonnet-4-20250514",
        )
        assert config.enabled is False
        assert config.every == "30s"
        assert config.target == "main"
        assert config.prompt == "Custom prompt"

    def test_active_hours(self):
        """Test active hours configuration."""
        hours = ActiveHours(start="09:00", end="18:00", timezone="local")
        config = HeartbeatConfig(active_hours=hours)
        assert config.active_hours is not None
        assert config.active_hours.start == "09:00"
        assert config.active_hours.end == "18:00"


class TestHeartbeatRunner:
    """Tests for HeartbeatRunner."""

    @pytest.fixture
    def workspace(self, tmp_path):
        """Create a temporary workspace directory."""
        return tmp_path

    @pytest.fixture
    def runner(self, workspace):
        """Create a HeartbeatRunner instance."""
        return HeartbeatRunner(
            workspace_dir=workspace,
            agent_id="test_agent",
            config=HeartbeatConfig(enabled=True),
        )

    def test_runner_initialization(self, runner):
        """Test runner initialization."""
        assert runner.agent_id == "test_agent"
        assert runner.config.enabled is True
        assert runner._running is False

    def test_parse_interval_seconds(self, runner):
        """Test parsing interval strings."""
        assert runner._parse_interval("30s") == 30.0
        assert runner._parse_interval("5m") == 300.0
        assert runner._parse_interval("1h") == 3600.0
        assert runner._parse_interval("invalid") == 300.0  # Default

    def test_is_effectively_empty(self, runner):
        """Test empty content detection."""
        # Empty content
        assert runner._is_effectively_empty("") is True
        assert runner._is_effectively_empty("   ") is True
        assert runner._is_effectively_empty("\n\n") is True

        # Comment-only content
        assert runner._is_effectively_empty("# Comment") is True
        assert runner._is_effectively_empty("# Line 1\n# Line 2") is True

        # Non-empty content
        assert runner._is_effectively_empty("Task to do") is False
        assert runner._is_effectively_empty("# Comment\nTask") is False

    def test_strip_heartbeat_token(self, runner):
        """Test HEARTBEAT_OK token extraction."""
        # With token
        result = runner._strip_heartbeat_token("HEARTBEAT_OK")
        assert result["is_heartbeat_ok"] is True
        assert result["text"] == ""

        result = runner._strip_heartbeat_token("All good. HEARTBEAT_OK")
        assert result["is_heartbeat_ok"] is True
        assert result["text"] == "All good."

        # Without token
        result = runner._strip_heartbeat_token("Need to check something")
        assert result["is_heartbeat_ok"] is False
        assert result["text"] == "Need to check something"

    def test_is_within_active_hours_no_config(self, runner):
        """Test active hours check without configuration."""
        runner.config.active_hours = None
        assert runner._is_within_active_hours() is True

    def test_hash_message(self, runner):
        """Test message hashing for deduplication."""
        hash1 = runner._hash_message("Test message")
        hash2 = runner._hash_message("Test message")
        hash3 = runner._hash_message("Different message")

        assert hash1 == hash2
        assert hash1 != hash3

    def test_duplicate_detection(self, runner):
        """Test duplicate message detection."""
        message = "Test notification"

        # First time - not duplicate
        assert runner._is_duplicate_within_24h(message) is False

        # Add to recent messages
        runner._add_recent_message(message)

        # Second time - is duplicate
        assert runner._is_duplicate_within_24h(message) is True

    @pytest.mark.asyncio
    async def test_run_once_disabled(self, workspace):
        """Test heartbeat skipped when disabled."""
        runner = HeartbeatRunner(
            workspace_dir=workspace,
            agent_id="test",
            config=HeartbeatConfig(enabled=False),
        )

        result = await runner.run_once()
        assert result.status == "skipped"
        assert result.reason == "disabled"

    @pytest.mark.asyncio
    async def test_run_once_no_heartbeat_file(self, workspace):
        """Test heartbeat skipped when no HEARTBEAT.md file."""
        runner = HeartbeatRunner(
            workspace_dir=workspace,
            agent_id="test",
            config=HeartbeatConfig(enabled=True),
        )

        result = await runner.run_once()
        assert result.status == "skipped"
        assert result.reason == "no-heartbeat-file"

    @pytest.mark.asyncio
    async def test_run_once_empty_file(self, workspace):
        """Test heartbeat ok-empty when file is empty."""
        # Create empty heartbeat file
        heartbeat_file = workspace / "HEARTBEAT.md"
        heartbeat_file.write_text("# Only comments\n")

        runner = HeartbeatRunner(
            workspace_dir=workspace,
            agent_id="test",
            config=HeartbeatConfig(enabled=True),
        )

        result = await runner.run_once()
        assert result.status == "ok-empty"

    def test_event_listener(self, runner):
        """Test event listener registration and unsubscription."""
        events = []

        def listener(event):
            events.append(event)

        unsubscribe = runner.on_event(listener)
        assert listener in runner._event_listeners

        # Emit event
        event = HeartbeatEventPayload(ts=123, status="ok-token")
        runner._emit_event(event)
        assert len(events) == 1
        assert events[0].status == "ok-token"

        # Unsubscribe
        unsubscribe()
        assert listener not in runner._event_listeners


# =============================================================================
# Cron Tests
# =============================================================================


class TestCronSchedules:
    """Tests for CronSchedule types."""

    def test_schedule_at(self):
        """Test at (one-time) schedule."""
        schedule = CronScheduleAt(at_ms=1704067200000)  # 2024-01-01 00:00:00 UTC
        assert schedule.kind == "at"
        assert schedule.at_ms == 1704067200000

    def test_schedule_every(self):
        """Test every (periodic) schedule."""
        schedule = CronScheduleEvery(every_ms=3600000)  # 1 hour
        assert schedule.kind == "every"
        assert schedule.every_ms == 3600000
        assert schedule.anchor_ms is None

    def test_schedule_cron(self):
        """Test cron expression schedule."""
        schedule = CronScheduleCron(expr="0 */6 * * *", tz="UTC")
        assert schedule.kind == "cron"
        assert schedule.expr == "0 */6 * * *"
        assert schedule.tz == "UTC"


class TestCronPayloads:
    """Tests for CronPayload types."""

    def test_system_event_payload(self):
        """Test systemEvent payload."""
        payload = SystemEventPayload(text="Time to check tasks")
        assert payload.kind == "systemEvent"
        assert payload.text == "Time to check tasks"

    def test_agent_turn_payload(self):
        """Test agentTurn payload."""
        payload = AgentTurnPayload(
            message="Run daily report",
            model="anthropic:claude-sonnet-4-20250514",
            timeout_seconds=1800,
            deliver=True,
            channel="last",
        )
        assert payload.kind == "agentTurn"
        assert payload.message == "Run daily report"
        assert payload.timeout_seconds == 1800


class TestCronService:
    """Tests for CronService."""

    @pytest.fixture
    def storage_path(self, tmp_path):
        """Create temporary storage path."""
        return tmp_path / "cron_jobs.jsonl"

    @pytest.fixture
    def service(self, storage_path):
        """Create CronService instance."""
        return CronService(
            storage_path=storage_path,
            agent_id="test_agent",
        )

    def test_service_initialization(self, service):
        """Test service initialization."""
        assert service.agent_id == "test_agent"
        assert service._running is False
        assert len(service.jobs) == 0

    def test_add_job_system_event(self, service):
        """Test adding a systemEvent job."""
        job = service.add(
            {
                "name": "Test Job",
                "description": "Test description",
                "schedule": {"kind": "every", "every_ms": 3600000},
                "payload": {"kind": "systemEvent", "text": "Test message"},
                "session_target": "main",
            }
        )

        assert job.id.startswith("cron_")
        assert job.name == "Test Job"
        assert job.enabled is True
        assert isinstance(job.schedule, CronScheduleEvery)
        assert isinstance(job.payload, SystemEventPayload)
        assert job.session_target == "main"

    def test_add_job_agent_turn(self, service):
        """Test adding an agentTurn job."""
        job = service.add(
            {
                "name": "Agent Task",
                "schedule": {"kind": "every", "every_ms": 86400000},
                "payload": {
                    "kind": "agentTurn",
                    "message": "Generate daily report",
                    "timeout_seconds": 3600,
                },
                "session_target": "isolated",
            }
        )

        assert isinstance(job.payload, AgentTurnPayload)
        assert job.payload.message == "Generate daily report"
        assert job.session_target == "isolated"

    def test_add_job_validation_error(self, service):
        """Test validation error for invalid job configuration."""
        # main session with agentTurn payload should fail
        with pytest.raises(ValueError, match="main session must use systemEvent"):
            service.add(
                {
                    "name": "Invalid Job",
                    "schedule": {"kind": "every", "every_ms": 3600000},
                    "payload": {"kind": "agentTurn", "message": "Test"},
                    "session_target": "main",
                }
            )

    def test_list_jobs(self, service):
        """Test listing jobs."""
        service.add(
            {
                "name": "Job 1",
                "schedule": {"kind": "every", "every_ms": 3600000},
                "payload": {"kind": "systemEvent", "text": "Test 1"},
            }
        )
        service.add(
            {
                "name": "Job 2",
                "schedule": {"kind": "every", "every_ms": 7200000},
                "payload": {"kind": "systemEvent", "text": "Test 2"},
            }
        )

        jobs = service.list()
        assert len(jobs) == 2

    def test_get_job(self, service):
        """Test getting a job by ID."""
        job = service.add(
            {
                "name": "Test Job",
                "schedule": {"kind": "every", "every_ms": 3600000},
                "payload": {"kind": "systemEvent", "text": "Test"},
            }
        )

        retrieved = service.get(job.id)
        assert retrieved is not None
        assert retrieved.id == job.id
        assert retrieved.name == "Test Job"

        # Non-existent job
        assert service.get("non_existent") is None

    def test_update_job(self, service):
        """Test updating a job."""
        job = service.add(
            {
                "name": "Original Name",
                "schedule": {"kind": "every", "every_ms": 3600000},
                "payload": {"kind": "systemEvent", "text": "Original"},
            }
        )

        updated = service.update(
            job.id,
            {
                "name": "Updated Name",
                "enabled": False,
            },
        )

        assert updated.name == "Updated Name"
        assert updated.enabled is False
        assert updated.updated_at_ms >= job.created_at_ms

    def test_update_nonexistent_job(self, service):
        """Test updating a non-existent job."""
        with pytest.raises(ValueError, match="Job not found"):
            service.update("non_existent", {"name": "New Name"})

    def test_remove_job(self, service):
        """Test removing a job."""
        job = service.add(
            {
                "name": "To Remove",
                "schedule": {"kind": "every", "every_ms": 3600000},
                "payload": {"kind": "systemEvent", "text": "Test"},
            }
        )

        assert service.remove(job.id) is True
        assert service.get(job.id) is None
        assert service.remove(job.id) is False  # Already removed

    def test_status(self, service):
        """Test service status."""
        status = service.status()
        assert isinstance(status, CronServiceStatus)
        assert status.running is False
        assert status.job_count == 0

        # Add a job
        service.add(
            {
                "name": "Test",
                "schedule": {"kind": "every", "every_ms": 3600000},
                "payload": {"kind": "systemEvent", "text": "Test"},
            }
        )

        status = service.status()
        assert status.job_count == 1
        assert status.next_job_id is not None

    def test_calculate_next_run_at(self, service):
        """Test next run calculation for 'at' schedule."""
        now_ms = int(time.time() * 1000)
        future_ms = now_ms + 3600000  # 1 hour from now

        schedule = CronScheduleAt(at_ms=future_ms)
        next_run = service._calculate_next_run(schedule, now_ms)
        assert next_run == future_ms

        # Past time returns None
        past_ms = now_ms - 3600000
        schedule = CronScheduleAt(at_ms=past_ms)
        next_run = service._calculate_next_run(schedule, now_ms)
        assert next_run is None

    def test_calculate_next_run_every(self, service):
        """Test next run calculation for 'every' schedule."""
        now_ms = 1000000
        schedule = CronScheduleEvery(every_ms=3600000)  # 1 hour

        next_run = service._calculate_next_run(schedule, now_ms)
        assert next_run is not None
        assert next_run > now_ms
        assert (next_run - now_ms) <= 3600000

    def test_is_due(self, service):
        """Test job due checking."""
        job = service.add(
            {
                "name": "Test",
                "schedule": {"kind": "every", "every_ms": 1000},
                "payload": {"kind": "systemEvent", "text": "Test"},
            }
        )

        # Set next_run_at_ms to past
        job.state.next_run_at_ms = int(time.time() * 1000) - 1000
        assert service._is_due(job) is True

        # Set next_run_at_ms to future
        job.state.next_run_at_ms = int(time.time() * 1000) + 10000
        assert service._is_due(job) is False

        # Job already running
        job.state.next_run_at_ms = int(time.time() * 1000) - 1000
        job.state.running_at_ms = int(time.time() * 1000)
        assert service._is_due(job) is False

    @pytest.mark.asyncio
    async def test_run_job_force(self, service):
        """Test force running a job."""
        events = []

        def on_inject(session_key, text):
            events.append({"session_key": session_key, "text": text})

        service._on_inject_system_event = on_inject

        job = service.add(
            {
                "name": "Test",
                "schedule": {"kind": "every", "every_ms": 3600000},
                "payload": {"kind": "systemEvent", "text": "Test message"},
            }
        )

        result = await service.run(job.id, mode="force")

        assert isinstance(result, CronRunResult)
        assert result.status == "ok"
        assert result.job_id == job.id
        assert len(events) == 1
        assert events[0]["text"] == "Test message"

    @pytest.mark.asyncio
    async def test_run_job_not_due(self, service):
        """Test running a job that's not due."""
        job = service.add(
            {
                "name": "Test",
                "schedule": {"kind": "every", "every_ms": 3600000},
                "payload": {"kind": "systemEvent", "text": "Test"},
            }
        )

        # Set next run to far future
        job.state.next_run_at_ms = int(time.time() * 1000) + 3600000

        result = await service.run(job.id, mode="due")
        assert result.status == "skipped"
        assert result.error == "not due"

    def test_persistence(self, storage_path):
        """Test job persistence across service restarts."""
        # Create service and add job
        service1 = CronService(storage_path=storage_path, agent_id="test")
        job = service1.add(
            {
                "name": "Persistent Job",
                "schedule": {"kind": "every", "every_ms": 3600000},
                "payload": {"kind": "systemEvent", "text": "Test"},
            }
        )
        job_id = job.id

        # Create new service instance (simulating restart)
        service2 = CronService(storage_path=storage_path, agent_id="test")

        # Job should be loaded
        loaded_job = service2.get(job_id)
        assert loaded_job is not None
        assert loaded_job.name == "Persistent Job"

    def test_delete_after_run(self, service):
        """Test delete_after_run flag."""
        events = []
        service._on_inject_system_event = lambda s, t: events.append(t)

        job = service.add(
            {
                "name": "One-time Job",
                "schedule": {"kind": "every", "every_ms": 3600000},
                "payload": {"kind": "systemEvent", "text": "Test"},
                "delete_after_run": True,
            }
        )
        job_id = job.id

        # Run job
        asyncio.get_event_loop().run_until_complete(service.run(job_id, mode="force"))

        # Job should be deleted
        assert service.get(job_id) is None


class TestCronJobState:
    """Tests for CronJobState."""

    def test_default_state(self):
        """Test default job state."""
        state = CronJobState()
        assert state.next_run_at_ms is None
        assert state.running_at_ms is None
        assert state.last_run_at_ms is None
        assert state.last_status is None

    def test_state_with_values(self):
        """Test job state with values."""
        now_ms = int(time.time() * 1000)
        state = CronJobState(
            next_run_at_ms=now_ms + 3600000,
            last_run_at_ms=now_ms - 3600000,
            last_status="ok",
            last_duration_ms=1500,
        )
        assert state.next_run_at_ms is not None
        assert state.last_status == "ok"
        assert state.last_duration_ms == 1500


# =============================================================================
# Integration Tests
# =============================================================================


class TestAutonomousIntegration:
    """Integration tests for autonomous systems."""

    @pytest.mark.asyncio
    async def test_heartbeat_with_callbacks(self, tmp_path):
        """Test heartbeat with callback functions."""
        # Setup
        workspace = tmp_path
        heartbeat_file = workspace / "HEARTBEAT.md"
        heartbeat_file.write_text("- Check system status\n- Review logs")

        replies = []
        deliveries = []

        async def mock_get_reply(prompt, model):
            replies.append(prompt)
            return "All systems normal. HEARTBEAT_OK"

        async def mock_deliver(text, target):
            deliveries.append({"text": text, "target": target})

        runner = HeartbeatRunner(
            workspace_dir=workspace,
            agent_id="test",
            config=HeartbeatConfig(enabled=True),
            on_get_reply=mock_get_reply,
            on_deliver_message=mock_deliver,
        )

        # Run
        result = await runner.run_once()

        # Verify
        assert result.status == "ok-token"
        assert len(replies) == 1
        assert "Check system status" in replies[0]
        assert len(deliveries) == 0  # No delivery for HEARTBEAT_OK

    @pytest.mark.asyncio
    async def test_cron_service_lifecycle(self, tmp_path):
        """Test cron service start/stop lifecycle."""
        storage_path = tmp_path / "cron.jsonl"
        service = CronService(
            storage_path=storage_path,
            agent_id="test",
            tick_interval_seconds=0.1,
        )

        # Add a job
        service.add(
            {
                "name": "Test",
                "schedule": {"kind": "every", "every_ms": 100},
                "payload": {"kind": "systemEvent", "text": "Tick"},
            }
        )

        # Start and verify running
        service.start()
        assert service._running is True
        assert service.status().running is True

        # Wait briefly
        await asyncio.sleep(0.05)

        # Stop
        service.stop()
        assert service._running is False
