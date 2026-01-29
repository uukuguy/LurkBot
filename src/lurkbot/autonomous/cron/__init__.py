"""Cron service for scheduled task execution.

Ported from moltbot/src/gateway/protocol/schema/cron.ts and related modules.

The cron system provides:
1. Three schedule types: at (one-time), every (periodic), cron (expression)
2. Two payload types: systemEvent (inject message), agentTurn (run agent task)
3. Job management: add, update, remove, list
4. Execution: run (due/force), wake
5. Persistent storage (JSONL)

MoltBot cron architecture:
- CronJob: Complete job definition with schedule, payload, and state
- CronService: Job management and scheduling loop
- CronPayload: systemEvent for main session, agentTurn for isolated execution
"""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Literal
from uuid import uuid4

from loguru import logger

# =============================================================================
# Schedule Types
# =============================================================================


@dataclass
class CronScheduleAt:
    """Single execution at a specific time.

    Matches MoltBot CronSchedule { kind: "at", atMs: number }.
    """

    kind: Literal["at"] = "at"
    at_ms: int = 0  # Unix timestamp in milliseconds


@dataclass
class CronScheduleEvery:
    """Periodic execution at fixed intervals.

    Matches MoltBot CronSchedule { kind: "every", everyMs: number, anchorMs?: number }.
    """

    kind: Literal["every"] = "every"
    every_ms: int = 3600000  # Default 1 hour
    anchor_ms: int | None = None  # Optional anchor timestamp


@dataclass
class CronScheduleCron:
    """Cron expression based scheduling.

    Matches MoltBot CronSchedule { kind: "cron", expr: string, tz?: string }.
    """

    kind: Literal["cron"] = "cron"
    expr: str = ""  # Cron expression (e.g., "0 */6 * * *")
    tz: str = "UTC"  # Timezone


# Union type for schedules
CronSchedule = CronScheduleAt | CronScheduleEvery | CronScheduleCron


# =============================================================================
# Payload Types
# =============================================================================


@dataclass
class SystemEventPayload:
    """System event payload for lightweight notifications.

    Injects text into the main session as a system event.
    Matches MoltBot CronPayload { kind: "systemEvent", text: string }.
    """

    kind: Literal["systemEvent"] = "systemEvent"
    text: str = ""


@dataclass
class AgentTurnPayload:
    """Agent turn payload for running agent tasks.

    Spawns an isolated session and runs an agent task.
    Matches MoltBot CronPayload { kind: "agentTurn", ... }.
    """

    kind: Literal["agentTurn"] = "agentTurn"
    message: str = ""
    model: str | None = None
    thinking: str | None = None
    timeout_seconds: int = 3600
    deliver: bool = True
    channel: str | None = None  # "last" or specific channel
    to: str | None = None
    best_effort_deliver: bool = False


# Union type for payloads
CronPayload = SystemEventPayload | AgentTurnPayload


# =============================================================================
# Job State and Definition
# =============================================================================


@dataclass
class CronJobState:
    """Cron job runtime state.

    Matches MoltBot CronJob.state.
    """

    next_run_at_ms: int | None = None
    running_at_ms: int | None = None
    last_run_at_ms: int | None = None
    last_status: Literal["ok", "error", "skipped"] | None = None
    last_error: str | None = None
    last_duration_ms: int | None = None


@dataclass
class CronJobIsolation:
    """Isolation settings for posting results to main session.

    Matches MoltBot CronJob.isolation.
    """

    post_to_main_prefix: str | None = None
    post_to_main_mode: Literal["summary", "full"] = "summary"
    post_to_main_max_chars: int = 2000


@dataclass
class CronJob:
    """Complete cron job definition.

    Matches MoltBot CronJob from gateway/protocol/schema/cron.ts.
    """

    id: str
    name: str
    agent_id: str | None = None
    description: str | None = None
    enabled: bool = True
    delete_after_run: bool = False
    created_at_ms: int = field(default_factory=lambda: int(time.time() * 1000))
    updated_at_ms: int = field(default_factory=lambda: int(time.time() * 1000))

    # Schedule configuration
    schedule: CronSchedule = field(default_factory=lambda: CronScheduleEvery())

    # Execution target
    session_target: Literal["main", "isolated"] = "main"
    wake_mode: Literal["next-heartbeat", "now"] = "next-heartbeat"

    # Payload configuration
    payload: CronPayload = field(default_factory=lambda: SystemEventPayload())

    # Isolation settings (for isolated sessions)
    isolation: CronJobIsolation | None = None

    # Runtime state
    state: CronJobState = field(default_factory=CronJobState)


# =============================================================================
# Service Types
# =============================================================================


@dataclass
class CronServiceStatus:
    """Cron service status.

    Matches MoltBot CronServiceStatus.
    """

    running: bool
    job_count: int
    next_job_id: str | None = None
    next_job_at_ms: int | None = None


@dataclass
class CronRunResult:
    """Result of running a cron job.

    Matches MoltBot CronRunResult.
    """

    job_id: str
    run_id: str
    started_at_ms: int
    ended_at_ms: int | None = None
    status: Literal["ok", "error", "skipped"] = "ok"
    error: str | None = None
    duration_ms: int | None = None
    output: str | None = None


# =============================================================================
# CronService
# =============================================================================


class CronService:
    """Cron service for managing scheduled tasks.

    Matches MoltBot CronService from gateway/protocol/schema/cron.ts.

    Features:
    - Job CRUD operations
    - Scheduling loop with configurable tick interval
    - Support for three schedule types (at, every, cron)
    - Support for two payload types (systemEvent, agentTurn)
    - Persistent storage via JSONL file
    """

    def __init__(
        self,
        storage_path: str | Path,
        agent_id: str,
        tick_interval_seconds: float = 1.0,
        on_inject_system_event: Callable[[str, str], Any] | None = None,
        on_run_agent_turn: Callable[[CronJob], Any] | None = None,
    ):
        """Initialize cron service.

        Args:
            storage_path: Path to JSONL storage file
            agent_id: Agent identifier
            tick_interval_seconds: Scheduler tick interval
            on_inject_system_event: Callback (session_key, text) -> None
            on_run_agent_turn: Callback (job) -> result
        """
        self.storage_path = Path(storage_path)
        self.agent_id = agent_id
        self.tick_interval = tick_interval_seconds

        # Callbacks
        self._on_inject_system_event = on_inject_system_event
        self._on_run_agent_turn = on_run_agent_turn

        # State
        self.jobs: dict[str, CronJob] = {}
        self.runs: dict[str, list[CronRunResult]] = {}
        self._running = False
        self._task: asyncio.Task | None = None

        # Load persisted jobs
        self._load()

    # -------------------------------------------------------------------------
    # Service Lifecycle
    # -------------------------------------------------------------------------

    def start(self) -> None:
        """Start the cron service scheduler loop."""
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(self._scheduler_loop())
        logger.debug(f"Cron service started for agent {self.agent_id}")

    def stop(self) -> None:
        """Stop the cron service."""
        self._running = False
        if self._task:
            self._task.cancel()
            self._task = None
        logger.debug(f"Cron service stopped for agent {self.agent_id}")

    def status(self) -> CronServiceStatus:
        """Get cron service status."""
        next_job, next_at = self._get_next_scheduled_job()

        return CronServiceStatus(
            running=self._running,
            job_count=len(self.jobs),
            next_job_id=next_job.id if next_job else None,
            next_job_at_ms=next_at,
        )

    # -------------------------------------------------------------------------
    # Job Management
    # -------------------------------------------------------------------------

    def list(self, agent_id: str | None = None) -> list[CronJob]:
        """List all cron jobs.

        Args:
            agent_id: Optional filter by agent ID

        Returns:
            List of CronJob objects
        """
        jobs = list(self.jobs.values())
        if agent_id:
            jobs = [j for j in jobs if j.agent_id == agent_id]
        return jobs

    def get(self, job_id: str) -> CronJob | None:
        """Get a cron job by ID."""
        return self.jobs.get(job_id)

    def add(self, job_input: dict[str, Any]) -> CronJob:
        """Add a new cron job.

        Args:
            job_input: Job configuration dict

        Returns:
            Created CronJob

        Raises:
            ValueError: If job configuration is invalid
        """
        job_id = f"cron_{uuid4().hex[:12]}"
        now_ms = int(time.time() * 1000)

        # Parse schedule
        schedule = self._parse_schedule(job_input.get("schedule", {}))

        # Parse payload
        payload = self._parse_payload(job_input.get("payload", {}))

        # Create job
        job = CronJob(
            id=job_id,
            name=job_input.get("name", f"Job {job_id}"),
            agent_id=job_input.get("agent_id") or self.agent_id,
            description=job_input.get("description"),
            enabled=job_input.get("enabled", True),
            delete_after_run=job_input.get("delete_after_run", False),
            created_at_ms=now_ms,
            updated_at_ms=now_ms,
            schedule=schedule,
            session_target=job_input.get("session_target", "main"),
            wake_mode=job_input.get("wake_mode", "next-heartbeat"),
            payload=payload,
            isolation=self._parse_isolation(job_input.get("isolation")),
            state=CronJobState(
                next_run_at_ms=self._calculate_next_run(schedule, now_ms),
            ),
        )

        # Validate
        self._validate_job(job)

        # Store
        self.jobs[job_id] = job
        self.runs[job_id] = []
        self._save()

        logger.debug(f"Created cron job {job_id}: {job.name}")
        return job

    def update(self, job_id: str, patch: dict[str, Any]) -> CronJob:
        """Update an existing cron job.

        Args:
            job_id: Job identifier
            patch: Fields to update

        Returns:
            Updated CronJob

        Raises:
            ValueError: If job not found or update is invalid
        """
        job = self.jobs.get(job_id)
        if not job:
            raise ValueError(f"Job not found: {job_id}")

        now_ms = int(time.time() * 1000)

        # Update fields
        if "name" in patch:
            job.name = patch["name"]
        if "description" in patch:
            job.description = patch["description"]
        if "enabled" in patch:
            job.enabled = patch["enabled"]
        if "delete_after_run" in patch:
            job.delete_after_run = patch["delete_after_run"]
        if "schedule" in patch:
            job.schedule = self._parse_schedule(patch["schedule"])
            job.state.next_run_at_ms = self._calculate_next_run(job.schedule, now_ms)
        if "payload" in patch:
            job.payload = self._parse_payload(patch["payload"])
        if "session_target" in patch:
            job.session_target = patch["session_target"]
        if "wake_mode" in patch:
            job.wake_mode = patch["wake_mode"]
        if "isolation" in patch:
            job.isolation = self._parse_isolation(patch["isolation"])

        job.updated_at_ms = now_ms

        # Validate
        self._validate_job(job)

        self._save()
        logger.debug(f"Updated cron job {job_id}")
        return job

    def remove(self, job_id: str) -> bool:
        """Remove a cron job.

        Args:
            job_id: Job identifier

        Returns:
            True if job was removed, False if not found
        """
        if job_id not in self.jobs:
            return False

        del self.jobs[job_id]
        self.runs.pop(job_id, None)
        self._save()

        logger.debug(f"Removed cron job {job_id}")
        return True

    # -------------------------------------------------------------------------
    # Execution
    # -------------------------------------------------------------------------

    async def run(
        self, job_id: str, mode: Literal["due", "force"] = "force"
    ) -> CronRunResult:
        """Run a cron job.

        Args:
            job_id: Job identifier
            mode: "due" to run only if scheduled, "force" to run immediately

        Returns:
            CronRunResult with execution status

        Raises:
            ValueError: If job not found
        """
        job = self.jobs.get(job_id)
        if not job:
            raise ValueError(f"Job not found: {job_id}")

        now_ms = int(time.time() * 1000)

        # Check if due for "due" mode
        if mode == "due" and not self._is_due(job):
            return CronRunResult(
                job_id=job_id,
                run_id=f"run_{uuid4().hex[:8]}",
                started_at_ms=now_ms,
                ended_at_ms=now_ms,
                status="skipped",
                error="not due",
            )

        return await self._execute_job(job)

    def wake(self, mode: Literal["next-heartbeat", "now"] = "now") -> None:
        """Wake up the scheduler to check for due jobs.

        Args:
            mode: "now" for immediate check, "next-heartbeat" to wait
        """
        # In full implementation, this would signal the scheduler
        logger.debug(f"Cron scheduler wake requested: {mode}")

    def get_runs(self, job_id: str, limit: int = 10) -> list[CronRunResult]:
        """Get run history for a job.

        Args:
            job_id: Job identifier
            limit: Maximum number of runs to return

        Returns:
            List of CronRunResult (most recent first)
        """
        runs = self.runs.get(job_id, [])
        return list(reversed(runs[-limit:]))

    # -------------------------------------------------------------------------
    # Internal Methods
    # -------------------------------------------------------------------------

    async def _scheduler_loop(self) -> None:
        """Main scheduler loop."""
        while self._running:
            try:
                now_ms = int(time.time() * 1000)

                for job in list(self.jobs.values()):
                    if job.enabled and self._is_due(job):
                        await self._execute_job(job)

            except Exception as e:
                logger.error(f"Cron scheduler error: {e}")

            await asyncio.sleep(self.tick_interval)

    def _is_due(self, job: CronJob) -> bool:
        """Check if job is due for execution."""
        if not job.state.next_run_at_ms:
            return False
        if job.state.running_at_ms:
            return False
        now_ms = int(time.time() * 1000)
        return now_ms >= job.state.next_run_at_ms

    async def _execute_job(self, job: CronJob) -> CronRunResult:
        """Execute a cron job."""
        now_ms = int(time.time() * 1000)
        run_id = f"run_{uuid4().hex[:8]}"

        # Mark as running
        job.state.running_at_ms = now_ms

        try:
            # Execute based on payload type
            if isinstance(job.payload, SystemEventPayload):
                output = await self._execute_system_event(job)
            else:
                output = await self._execute_agent_turn(job)

            ended_ms = int(time.time() * 1000)
            duration_ms = ended_ms - now_ms

            result = CronRunResult(
                job_id=job.id,
                run_id=run_id,
                started_at_ms=now_ms,
                ended_at_ms=ended_ms,
                status="ok",
                duration_ms=duration_ms,
                output=output,
            )

            # Update job state
            job.state.last_run_at_ms = now_ms
            job.state.last_status = "ok"
            job.state.last_duration_ms = duration_ms
            job.state.last_error = None

            logger.debug(f"Cron job {job.id} executed successfully in {duration_ms}ms")

        except Exception as e:
            ended_ms = int(time.time() * 1000)
            error_msg = str(e)

            result = CronRunResult(
                job_id=job.id,
                run_id=run_id,
                started_at_ms=now_ms,
                ended_at_ms=ended_ms,
                status="error",
                error=error_msg,
                duration_ms=ended_ms - now_ms,
            )

            job.state.last_run_at_ms = now_ms
            job.state.last_status = "error"
            job.state.last_error = error_msg

            logger.error(f"Cron job {job.id} failed: {error_msg}")

        finally:
            job.state.running_at_ms = None

            # Calculate next run
            job.state.next_run_at_ms = self._calculate_next_run(
                job.schedule, int(time.time() * 1000)
            )

            # Handle delete_after_run
            if job.delete_after_run and result.status == "ok":
                self.remove(job.id)
            else:
                self._save()

        # Store run result
        if job.id in self.runs:
            self.runs[job.id].append(result)
            # Keep only last 100 runs
            self.runs[job.id] = self.runs[job.id][-100:]

        return result

    async def _execute_system_event(self, job: CronJob) -> str:
        """Execute systemEvent payload."""
        if not isinstance(job.payload, SystemEventPayload):
            raise ValueError("Invalid payload type")

        session_key = f"agent:{job.agent_id or self.agent_id}:main"
        text = job.payload.text

        if self._on_inject_system_event:
            result = self._on_inject_system_event(session_key, text)
            if asyncio.iscoroutine(result):
                await result

        return f"Injected system event to {session_key}"

    async def _execute_agent_turn(self, job: CronJob) -> str:
        """Execute agentTurn payload."""
        if not isinstance(job.payload, AgentTurnPayload):
            raise ValueError("Invalid payload type")

        if self._on_run_agent_turn:
            result = self._on_run_agent_turn(job)
            if asyncio.iscoroutine(result):
                return await result
            return str(result)

        # Placeholder - actual implementation needs agent integration
        return "Agent turn executed (placeholder)"

    def _calculate_next_run(self, schedule: CronSchedule, after_ms: int) -> int | None:
        """Calculate next run time for a schedule."""
        if isinstance(schedule, CronScheduleAt):
            # One-time execution
            if schedule.at_ms > after_ms:
                return schedule.at_ms
            return None

        elif isinstance(schedule, CronScheduleEvery):
            # Periodic execution
            anchor = schedule.anchor_ms or after_ms
            interval = schedule.every_ms

            if interval <= 0:
                return None

            # Find next interval
            elapsed = after_ms - anchor
            intervals = (elapsed // interval) + 1
            return anchor + (intervals * interval)

        elif isinstance(schedule, CronScheduleCron):
            # Cron expression
            try:
                from croniter import croniter

                cron = croniter(schedule.expr, datetime.fromtimestamp(after_ms / 1000))
                next_dt = cron.get_next(datetime)
                return int(next_dt.timestamp() * 1000)
            except ImportError:
                # Fallback: 1 hour from now
                logger.warning("croniter not installed, using 1h fallback")
                return after_ms + 3600000
            except Exception as e:
                logger.error(f"Cron expression error: {e}")
                return None

        return None

    def _get_next_scheduled_job(self) -> tuple[CronJob | None, int | None]:
        """Get the next scheduled job and its run time."""
        next_job: CronJob | None = None
        next_at: int | None = None

        for job in self.jobs.values():
            if not job.enabled:
                continue
            job_next = job.state.next_run_at_ms
            if job_next and (next_at is None or job_next < next_at):
                next_at = job_next
                next_job = job

        return next_job, next_at

    def _validate_job(self, job: CronJob) -> None:
        """Validate job configuration."""
        # main session must use systemEvent
        if job.session_target == "main":
            if not isinstance(job.payload, SystemEventPayload):
                raise ValueError("main session must use systemEvent payload")

        # isolated session must use agentTurn
        if job.session_target == "isolated":
            if not isinstance(job.payload, AgentTurnPayload):
                raise ValueError("isolated session must use agentTurn payload")

    def _parse_schedule(self, data: dict[str, Any]) -> CronSchedule:
        """Parse schedule configuration from dict."""
        kind = data.get("kind", "every")

        if kind == "at":
            return CronScheduleAt(
                kind="at",
                at_ms=data.get("at_ms") or data.get("atMs") or 0,
            )
        elif kind == "every":
            return CronScheduleEvery(
                kind="every",
                every_ms=data.get("every_ms") or data.get("everyMs") or 3600000,
                anchor_ms=data.get("anchor_ms") or data.get("anchorMs"),
            )
        elif kind == "cron":
            return CronScheduleCron(
                kind="cron",
                expr=data.get("expr", ""),
                tz=data.get("tz", "UTC"),
            )
        else:
            return CronScheduleEvery()

    def _parse_payload(self, data: dict[str, Any]) -> CronPayload:
        """Parse payload configuration from dict."""
        kind = data.get("kind", "systemEvent")

        if kind == "systemEvent":
            return SystemEventPayload(
                kind="systemEvent",
                text=data.get("text", ""),
            )
        elif kind == "agentTurn":
            return AgentTurnPayload(
                kind="agentTurn",
                message=data.get("message", ""),
                model=data.get("model"),
                thinking=data.get("thinking"),
                timeout_seconds=data.get("timeout_seconds")
                or data.get("timeoutSeconds")
                or 3600,
                deliver=data.get("deliver", True),
                channel=data.get("channel"),
                to=data.get("to"),
                best_effort_deliver=data.get("best_effort_deliver")
                or data.get("bestEffortDeliver")
                or False,
            )
        else:
            return SystemEventPayload()

    def _parse_isolation(self, data: dict[str, Any] | None) -> CronJobIsolation | None:
        """Parse isolation configuration from dict."""
        if not data:
            return None

        return CronJobIsolation(
            post_to_main_prefix=data.get("post_to_main_prefix")
            or data.get("postToMainPrefix"),
            post_to_main_mode=data.get("post_to_main_mode")
            or data.get("postToMainMode")
            or "summary",
            post_to_main_max_chars=data.get("post_to_main_max_chars")
            or data.get("postToMainMaxChars")
            or 2000,
        )

    # -------------------------------------------------------------------------
    # Persistence
    # -------------------------------------------------------------------------

    def _load(self) -> None:
        """Load jobs from storage."""
        if not self.storage_path.exists():
            return

        try:
            with open(self.storage_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    data = json.loads(line)
                    job = self._job_from_dict(data)
                    self.jobs[job.id] = job
                    self.runs[job.id] = []

            logger.debug(f"Loaded {len(self.jobs)} cron jobs from {self.storage_path}")
        except Exception as e:
            logger.error(f"Failed to load cron jobs: {e}")

    def _save(self) -> None:
        """Save jobs to storage."""
        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.storage_path, "w") as f:
                for job in self.jobs.values():
                    data = self._job_to_dict(job)
                    f.write(json.dumps(data) + "\n")
        except Exception as e:
            logger.error(f"Failed to save cron jobs: {e}")

    def _job_to_dict(self, job: CronJob) -> dict[str, Any]:
        """Convert CronJob to dict for serialization."""
        schedule_dict: dict[str, Any] = {"kind": job.schedule.kind}
        if isinstance(job.schedule, CronScheduleAt):
            schedule_dict["at_ms"] = job.schedule.at_ms
        elif isinstance(job.schedule, CronScheduleEvery):
            schedule_dict["every_ms"] = job.schedule.every_ms
            schedule_dict["anchor_ms"] = job.schedule.anchor_ms
        elif isinstance(job.schedule, CronScheduleCron):
            schedule_dict["expr"] = job.schedule.expr
            schedule_dict["tz"] = job.schedule.tz

        payload_dict: dict[str, Any] = {"kind": job.payload.kind}
        if isinstance(job.payload, SystemEventPayload):
            payload_dict["text"] = job.payload.text
        elif isinstance(job.payload, AgentTurnPayload):
            payload_dict["message"] = job.payload.message
            payload_dict["model"] = job.payload.model
            payload_dict["thinking"] = job.payload.thinking
            payload_dict["timeout_seconds"] = job.payload.timeout_seconds
            payload_dict["deliver"] = job.payload.deliver
            payload_dict["channel"] = job.payload.channel
            payload_dict["to"] = job.payload.to
            payload_dict["best_effort_deliver"] = job.payload.best_effort_deliver

        isolation_dict: dict[str, Any] | None = None
        if job.isolation:
            isolation_dict = {
                "post_to_main_prefix": job.isolation.post_to_main_prefix,
                "post_to_main_mode": job.isolation.post_to_main_mode,
                "post_to_main_max_chars": job.isolation.post_to_main_max_chars,
            }

        return {
            "id": job.id,
            "name": job.name,
            "agent_id": job.agent_id,
            "description": job.description,
            "enabled": job.enabled,
            "delete_after_run": job.delete_after_run,
            "created_at_ms": job.created_at_ms,
            "updated_at_ms": job.updated_at_ms,
            "schedule": schedule_dict,
            "session_target": job.session_target,
            "wake_mode": job.wake_mode,
            "payload": payload_dict,
            "isolation": isolation_dict,
            "state": {
                "next_run_at_ms": job.state.next_run_at_ms,
                "running_at_ms": job.state.running_at_ms,
                "last_run_at_ms": job.state.last_run_at_ms,
                "last_status": job.state.last_status,
                "last_error": job.state.last_error,
                "last_duration_ms": job.state.last_duration_ms,
            },
        }

    def _job_from_dict(self, data: dict[str, Any]) -> CronJob:
        """Create CronJob from dict."""
        state_data = data.get("state", {})

        return CronJob(
            id=data["id"],
            name=data["name"],
            agent_id=data.get("agent_id"),
            description=data.get("description"),
            enabled=data.get("enabled", True),
            delete_after_run=data.get("delete_after_run", False),
            created_at_ms=data.get("created_at_ms", int(time.time() * 1000)),
            updated_at_ms=data.get("updated_at_ms", int(time.time() * 1000)),
            schedule=self._parse_schedule(data.get("schedule", {})),
            session_target=data.get("session_target", "main"),
            wake_mode=data.get("wake_mode", "next-heartbeat"),
            payload=self._parse_payload(data.get("payload", {})),
            isolation=self._parse_isolation(data.get("isolation")),
            state=CronJobState(
                next_run_at_ms=state_data.get("next_run_at_ms"),
                running_at_ms=state_data.get("running_at_ms"),
                last_run_at_ms=state_data.get("last_run_at_ms"),
                last_status=state_data.get("last_status"),
                last_error=state_data.get("last_error"),
                last_duration_ms=state_data.get("last_duration_ms"),
            ),
        )


# =============================================================================
# Module Exports
# =============================================================================

__all__ = [
    # Schedule types
    "CronSchedule",
    "CronScheduleAt",
    "CronScheduleEvery",
    "CronScheduleCron",
    # Payload types
    "CronPayload",
    "SystemEventPayload",
    "AgentTurnPayload",
    # Job types
    "CronJobState",
    "CronJobIsolation",
    "CronJob",
    # Service types
    "CronServiceStatus",
    "CronRunResult",
    "CronService",
]
