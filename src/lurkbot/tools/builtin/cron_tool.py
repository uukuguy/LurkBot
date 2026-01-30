"""Cron tool for scheduled task management.

Ported from moltbot/src/agents/tools/cron-tool.ts

This tool provides comprehensive scheduled task management with support for:
- Single-run tasks (at a specific time)
- Periodic tasks (every X interval)
- Cron expression schedules

MoltBot cron tool operations:
- status: Get cron service status
- list: List all cron jobs
- add: Create a new cron job
- update: Modify an existing job
- remove: Delete a cron job
- run: Manually trigger a job
- runs: Get job run history
- wake: Wake up the scheduler
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Literal, TypedDict
from uuid import uuid4

from pydantic import BaseModel, Field

from lurkbot.tools.builtin.common import (
    ToolResult,
    error_result,
    json_result,
    read_number_param,
    read_string_param,
    text_result,
)


# =============================================================================
# Type Definitions (from moltbot/src/gateway/protocol/schema/cron.ts)
# =============================================================================


class ScheduleKind(str, Enum):
    """Cron schedule types."""

    AT = "at"  # Single execution at a specific time
    EVERY = "every"  # Periodic execution
    CRON = "cron"  # Cron expression


class PayloadKind(str, Enum):
    """Cron payload types."""

    SYSTEM_EVENT = "systemEvent"  # Inject system event
    AGENT_TURN = "agentTurn"  # Run agent task


class CronScheduleAt(BaseModel):
    """Single execution schedule."""

    kind: Literal["at"] = "at"
    at_ms: int = Field(alias="atMs")


class CronScheduleEvery(BaseModel):
    """Periodic execution schedule."""

    kind: Literal["every"] = "every"
    every_ms: int = Field(alias="everyMs")
    anchor_ms: int | None = Field(default=None, alias="anchorMs")


class CronScheduleCron(BaseModel):
    """Cron expression schedule."""

    kind: Literal["cron"] = "cron"
    expr: str
    tz: str | None = None


CronSchedule = CronScheduleAt | CronScheduleEvery | CronScheduleCron


class SystemEventPayload(BaseModel):
    """System event payload."""

    kind: Literal["systemEvent"] = "systemEvent"
    text: str


class AgentTurnPayload(BaseModel):
    """Agent turn payload for running tasks."""

    kind: Literal["agentTurn"] = "agentTurn"
    message: str
    model: str | None = None
    thinking: str | None = None
    timeout_seconds: int | None = Field(default=None, alias="timeoutSeconds")
    deliver: bool | None = None
    channel: str | None = None  # "last" or specific channel
    to: str | None = None
    best_effort_deliver: bool | None = Field(default=None, alias="bestEffortDeliver")


CronPayload = SystemEventPayload | AgentTurnPayload


class CronJobState(BaseModel):
    """Cron job runtime state."""

    next_run_at_ms: int | None = Field(default=None, alias="nextRunAtMs")
    running_at_ms: int | None = Field(default=None, alias="runningAtMs")
    last_run_at_ms: int | None = Field(default=None, alias="lastRunAtMs")
    last_status: Literal["ok", "error", "skipped"] | None = Field(
        default=None, alias="lastStatus"
    )
    last_error: str | None = Field(default=None, alias="lastError")
    last_duration_ms: int | None = Field(default=None, alias="lastDurationMs")


class CronJobIsolation(BaseModel):
    """Isolation settings for cron job."""

    post_to_main_prefix: str | None = Field(default=None, alias="postToMainPrefix")
    post_to_main_mode: Literal["summary", "full"] | None = Field(
        default=None, alias="postToMainMode"
    )
    post_to_main_max_chars: int | None = Field(
        default=None, alias="postToMainMaxChars"
    )


class CronJob(BaseModel):
    """Complete cron job definition.

    Matches moltbot CronJob type from gateway/protocol/schema/cron.ts.
    """

    id: str
    agent_id: str | None = Field(default=None, alias="agentId")
    name: str
    description: str | None = None
    enabled: bool = True
    delete_after_run: bool | None = Field(default=None, alias="deleteAfterRun")
    created_at_ms: int = Field(alias="createdAtMs")
    updated_at_ms: int = Field(alias="updatedAtMs")

    schedule: dict[str, Any]  # CronSchedule as dict for flexibility
    session_target: Literal["main", "isolated"] = Field(
        default="main", alias="sessionTarget"
    )
    wake_mode: Literal["next-heartbeat", "now"] = Field(
        default="next-heartbeat", alias="wakeMode"
    )
    payload: dict[str, Any]  # CronPayload as dict for flexibility

    isolation: CronJobIsolation | None = None
    state: CronJobState = Field(default_factory=CronJobState)

    class Config:
        populate_by_name = True


class CronServiceStatus(BaseModel):
    """Cron service status."""

    running: bool
    job_count: int = Field(alias="jobCount")
    next_job_id: str | None = Field(default=None, alias="nextJobId")
    next_job_at_ms: int | None = Field(default=None, alias="nextJobAtMs")


class CronRunResult(BaseModel):
    """Result of running a cron job."""

    job_id: str = Field(alias="jobId")
    run_id: str = Field(alias="runId")
    started_at_ms: int = Field(alias="startedAtMs")
    ended_at_ms: int | None = Field(default=None, alias="endedAtMs")
    status: Literal["ok", "error", "skipped"]
    error: str | None = None
    duration_ms: int | None = Field(default=None, alias="durationMs")


# =============================================================================
# Cron Tool Parameters
# =============================================================================


class CronParams(BaseModel):
    """Parameters for cron tool.

    Matches moltbot cron tool schema.
    """

    op: Literal["status", "list", "add", "update", "remove", "run", "runs", "wake"]

    # For add/update operations
    name: str | None = None
    description: str | None = None
    enabled: bool | None = None
    schedule: dict[str, Any] | None = None
    payload: dict[str, Any] | None = None
    session_target: Literal["main", "isolated"] | None = Field(
        default=None, alias="sessionTarget"
    )
    wake_mode: Literal["next-heartbeat", "now"] | None = Field(
        default=None, alias="wakeMode"
    )
    delete_after_run: bool | None = Field(default=None, alias="deleteAfterRun")
    isolation: dict[str, Any] | None = None

    # For update/remove/run operations
    id: str | None = None

    # For run operation
    mode: Literal["due", "force"] | None = None

    # For runs operation (get run history)
    limit: int | None = None

    class Config:
        populate_by_name = True


# =============================================================================
# In-Memory Cron Store (placeholder for full implementation)
# =============================================================================


@dataclass
class CronStore:
    """In-memory cron job storage.

    Note: Full implementation should use persistent storage via Gateway.
    This is a placeholder for local development and testing.
    """

    jobs: dict[str, CronJob] = field(default_factory=dict)
    runs: dict[str, list[CronRunResult]] = field(default_factory=dict)
    _running: bool = False

    def start(self) -> None:
        """Start the cron service."""
        self._running = True

    def stop(self) -> None:
        """Stop the cron service."""
        self._running = False

    def is_running(self) -> bool:
        """Check if service is running."""
        return self._running


# Global cron store instance
_cron_store: CronStore | None = None


def get_cron_store() -> CronStore:
    """Get the global cron store instance."""
    global _cron_store
    if _cron_store is None:
        _cron_store = CronStore()
    return _cron_store


# =============================================================================
# Cron Tool Implementation
# =============================================================================


async def cron_tool(params: dict[str, Any]) -> ToolResult:
    """Execute cron tool operations.

    Args:
        params: Tool parameters containing 'op' and operation-specific fields

    Returns:
        ToolResult with operation result or error
    """
    try:
        cron_params = CronParams.model_validate(params)
    except Exception as e:
        return error_result(f"Invalid parameters: {e}")

    store = get_cron_store()

    match cron_params.op:
        case "status":
            return _cron_status(store)
        case "list":
            return _cron_list(store)
        case "add":
            return _cron_add(store, cron_params)
        case "update":
            return _cron_update(store, cron_params)
        case "remove":
            return _cron_remove(store, cron_params)
        case "run":
            return await _cron_run(store, cron_params)
        case "runs":
            return _cron_runs(store, cron_params)
        case "wake":
            return _cron_wake(store)
        case _:
            return error_result(f"Unknown operation: {cron_params.op}")


def _cron_status(store: CronStore) -> ToolResult:
    """Get cron service status."""
    # Find next scheduled job
    next_job: CronJob | None = None
    next_at: int | None = None

    for job in store.jobs.values():
        if not job.enabled:
            continue
        job_next = job.state.next_run_at_ms
        if job_next and (next_at is None or job_next < next_at):
            next_at = job_next
            next_job = job

    status = CronServiceStatus(
        running=store.is_running(),
        jobCount=len(store.jobs),
        nextJobId=next_job.id if next_job else None,
        nextJobAtMs=next_at,
    )

    return json_result(status.model_dump(by_alias=True, exclude_none=True))


def _cron_list(store: CronStore) -> ToolResult:
    """List all cron jobs."""
    jobs = [job.model_dump(by_alias=True, exclude_none=True) for job in store.jobs.values()]
    return json_result({"jobs": jobs, "count": len(jobs)})


def _cron_add(store: CronStore, params: CronParams) -> ToolResult:
    """Add a new cron job."""
    if not params.name:
        return error_result("Missing required field: name")
    if not params.schedule:
        return error_result("Missing required field: schedule")
    if not params.payload:
        return error_result("Missing required field: payload")

    now_ms = int(time.time() * 1000)
    job_id = str(uuid4())[:8]

    job = CronJob(
        id=job_id,
        name=params.name,
        description=params.description,
        enabled=params.enabled if params.enabled is not None else True,
        deleteAfterRun=params.delete_after_run,
        createdAtMs=now_ms,
        updatedAtMs=now_ms,
        schedule=params.schedule,
        sessionTarget=params.session_target or "main",
        wakeMode=params.wake_mode or "next-heartbeat",
        payload=params.payload,
        isolation=CronJobIsolation.model_validate(params.isolation)
        if params.isolation
        else None,
        state=CronJobState(nextRunAtMs=_calculate_next_run(params.schedule, now_ms)),
    )

    store.jobs[job_id] = job
    store.runs[job_id] = []

    return json_result(
        {
            "success": True,
            "job": job.model_dump(by_alias=True, exclude_none=True),
        }
    )


def _cron_update(store: CronStore, params: CronParams) -> ToolResult:
    """Update an existing cron job."""
    if not params.id:
        return error_result("Missing required field: id")

    job = store.jobs.get(params.id)
    if not job:
        return error_result(f"Job not found: {params.id}")

    now_ms = int(time.time() * 1000)

    # Update fields if provided
    if params.name is not None:
        job.name = params.name
    if params.description is not None:
        job.description = params.description
    if params.enabled is not None:
        job.enabled = params.enabled
    if params.schedule is not None:
        job.schedule = params.schedule
        job.state.next_run_at_ms = _calculate_next_run(params.schedule, now_ms)
    if params.payload is not None:
        job.payload = params.payload
    if params.session_target is not None:
        job.session_target = params.session_target
    if params.wake_mode is not None:
        job.wake_mode = params.wake_mode
    if params.delete_after_run is not None:
        job.delete_after_run = params.delete_after_run
    if params.isolation is not None:
        job.isolation = CronJobIsolation.model_validate(params.isolation)

    job.updated_at_ms = now_ms

    return json_result(
        {
            "success": True,
            "job": job.model_dump(by_alias=True, exclude_none=True),
        }
    )


def _cron_remove(store: CronStore, params: CronParams) -> ToolResult:
    """Remove a cron job."""
    if not params.id:
        return error_result("Missing required field: id")

    job = store.jobs.pop(params.id, None)
    if not job:
        return error_result(f"Job not found: {params.id}")

    # Also remove run history
    store.runs.pop(params.id, None)

    return json_result({"success": True, "removedId": params.id})


async def _cron_run(store: CronStore, params: CronParams) -> ToolResult:
    """Manually trigger a cron job."""
    if not params.id:
        return error_result("Missing required field: id")

    job = store.jobs.get(params.id)
    if not job:
        return error_result(f"Job not found: {params.id}")

    mode = params.mode or "force"
    now_ms = int(time.time() * 1000)

    # Check if due for "due" mode
    if mode == "due":
        if not job.state.next_run_at_ms or job.state.next_run_at_ms > now_ms:
            return json_result(
                {
                    "success": False,
                    "reason": "Job not due yet",
                    "nextRunAtMs": job.state.next_run_at_ms,
                }
            )

    # Mark as running
    job.state.running_at_ms = now_ms

    # Execute the job (placeholder - actual execution depends on payload type)
    run_id = str(uuid4())[:8]
    try:
        # TODO: Implement actual job execution based on payload kind
        # For now, simulate successful execution
        await _execute_cron_payload(job.payload)

        ended_ms = int(time.time() * 1000)
        duration_ms = ended_ms - now_ms

        result = CronRunResult(
            jobId=job.id,
            runId=run_id,
            startedAtMs=now_ms,
            endedAtMs=ended_ms,
            status="ok",
            durationMs=duration_ms,
        )

        # Update job state
        job.state.last_run_at_ms = now_ms
        job.state.last_status = "ok"
        job.state.last_duration_ms = duration_ms
        job.state.running_at_ms = None

        # Calculate next run
        job.state.next_run_at_ms = _calculate_next_run(job.schedule, ended_ms)

        # Handle delete_after_run
        if job.delete_after_run:
            store.jobs.pop(job.id, None)

    except Exception as e:
        ended_ms = int(time.time() * 1000)
        result = CronRunResult(
            jobId=job.id,
            runId=run_id,
            startedAtMs=now_ms,
            endedAtMs=ended_ms,
            status="error",
            error=str(e),
            durationMs=ended_ms - now_ms,
        )

        job.state.last_run_at_ms = now_ms
        job.state.last_status = "error"
        job.state.last_error = str(e)
        job.state.running_at_ms = None

    # Store run result
    if job.id in store.runs:
        store.runs[job.id].append(result)
        # Keep only last 100 runs
        store.runs[job.id] = store.runs[job.id][-100:]

    return json_result(result.model_dump(by_alias=True, exclude_none=True))


def _cron_runs(store: CronStore, params: CronParams) -> ToolResult:
    """Get run history for a cron job."""
    if not params.id:
        return error_result("Missing required field: id")

    runs = store.runs.get(params.id, [])
    limit = params.limit or 10

    # Return most recent runs first
    recent_runs = list(reversed(runs[-limit:]))

    return json_result(
        {
            "jobId": params.id,
            "runs": [r.model_dump(by_alias=True, exclude_none=True) for r in recent_runs],
            "count": len(recent_runs),
        }
    )


def _cron_wake(store: CronStore) -> ToolResult:
    """Wake up the cron scheduler."""
    # In full implementation, this would signal the cron service
    # to check for due jobs immediately
    return json_result({"success": True, "message": "Cron scheduler woken up"})


# =============================================================================
# Helper Functions
# =============================================================================


def _calculate_next_run(schedule: dict[str, Any], after_ms: int) -> int | None:
    """Calculate the next run time for a schedule.

    Args:
        schedule: Schedule configuration dict
        after_ms: Calculate next run after this timestamp

    Returns:
        Next run timestamp in milliseconds, or None if no more runs
    """
    kind = schedule.get("kind")

    if kind == "at":
        at_ms = schedule.get("atMs")
        if at_ms and at_ms > after_ms:
            return at_ms
        return None  # One-time job already passed

    elif kind == "every":
        every_ms = schedule.get("everyMs")
        anchor_ms = schedule.get("anchorMs", after_ms)
        if not every_ms:
            return None

        # Find next interval
        elapsed = after_ms - anchor_ms
        intervals = (elapsed // every_ms) + 1
        return anchor_ms + (intervals * every_ms)

    elif kind == "cron":
        # TODO: Implement cron expression parsing
        # For now, return 1 hour from now as placeholder
        return after_ms + 3600000

    return None


async def _execute_cron_payload(payload: dict[str, Any]) -> None:
    """Execute a cron job payload.

    Args:
        payload: Payload configuration dict

    Note: This is a placeholder. Full implementation should:
    - For systemEvent: Inject text into main session
    - For agentTurn: Spawn isolated session and run agent
    """
    kind = payload.get("kind")

    if kind == "systemEvent":
        # TODO: Inject system event into main session
        text = payload.get("text", "")
        # This would call into the session system
        pass

    elif kind == "agentTurn":
        # TODO: Spawn isolated session and run agent task
        message = payload.get("message", "")
        # This would spawn a subagent to handle the task
        pass


# =============================================================================
# Tool Factory Function
# =============================================================================


def create_cron_tool() -> tuple[str, str, dict[str, Any], Any]:
    """Create the cron tool definition.

    Returns:
        Tuple of (name, description, schema, handler)
    """
    name = "cron"
    description = """Manage scheduled tasks (cron jobs).

Operations:
- status: Get cron service status
- list: List all cron jobs
- add: Create a new cron job
- update: Modify an existing job
- remove: Delete a cron job
- run: Manually trigger a job
- runs: Get job run history
- wake: Wake up the scheduler

Schedule types:
- at: Single execution at a specific time (atMs)
- every: Periodic execution (everyMs, optional anchorMs)
- cron: Cron expression (expr, optional tz)

Payload types:
- systemEvent: Inject text event into main session
- agentTurn: Run agent task in isolated session"""

    schema = {
        "type": "object",
        "properties": {
            "op": {
                "type": "string",
                "enum": ["status", "list", "add", "update", "remove", "run", "runs", "wake"],
                "description": "Operation to perform",
            },
            "id": {
                "type": "string",
                "description": "Job ID (for update/remove/run/runs)",
            },
            "name": {
                "type": "string",
                "description": "Job name (for add/update)",
            },
            "description": {
                "type": "string",
                "description": "Job description (for add/update)",
            },
            "enabled": {
                "type": "boolean",
                "description": "Whether job is enabled (for add/update)",
            },
            "schedule": {
                "type": "object",
                "description": "Schedule configuration",
                "properties": {
                    "kind": {"type": "string", "enum": ["at", "every", "cron"]},
                    "atMs": {"type": "number"},
                    "everyMs": {"type": "number"},
                    "anchorMs": {"type": "number"},
                    "expr": {"type": "string"},
                    "tz": {"type": "string"},
                },
            },
            "payload": {
                "type": "object",
                "description": "Payload configuration",
                "properties": {
                    "kind": {"type": "string", "enum": ["systemEvent", "agentTurn"]},
                    "text": {"type": "string"},
                    "message": {"type": "string"},
                    "model": {"type": "string"},
                    "thinking": {"type": "string"},
                    "timeoutSeconds": {"type": "number"},
                    "deliver": {"type": "boolean"},
                    "channel": {"type": "string"},
                    "to": {"type": "string"},
                },
            },
            "sessionTarget": {
                "type": "string",
                "enum": ["main", "isolated"],
                "description": "Session target for job execution",
            },
            "wakeMode": {
                "type": "string",
                "enum": ["next-heartbeat", "now"],
                "description": "When to wake for job execution",
            },
            "deleteAfterRun": {
                "type": "boolean",
                "description": "Delete job after single run",
            },
            "mode": {
                "type": "string",
                "enum": ["due", "force"],
                "description": "Run mode: due (only if scheduled) or force",
            },
            "limit": {
                "type": "number",
                "description": "Limit for runs history",
            },
        },
        "required": ["op"],
    }

    return name, description, schema, cron_tool
