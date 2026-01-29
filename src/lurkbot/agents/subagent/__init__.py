"""Subagent system implementation.

This module provides the subagent spawning and result announcement functionality,
closely following MoltBot's subagent protocol.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal

from loguru import logger

from lurkbot.agents.types import AgentContext, SessionType
from lurkbot.sessions import (
    SessionEntry,
    SessionManager,
    SessionState,
    SubagentOutcome,
    SubagentResult,
    get_session_manager,
)


# Tool deny list for subagents (they cannot use these tools)
SUBAGENT_DENY_LIST = [
    "sessions_list",
    "sessions_history",
    "sessions_send",
    "sessions_spawn",
    "gateway",
    "agents_list",
    "session_status",
    "cron",
    "memory_search",
    "memory_get",
    "message",
]


@dataclass
class SpawnParams:
    """Parameters for spawning a subagent."""

    task: str  # Task description
    agent_id: str | None = None  # Target agent ID (defaults to current)
    model: str | None = None  # Model override
    model_provider: str | None = None  # Provider override
    thinking: Literal["off", "low", "medium", "high"] = "medium"
    run_timeout_seconds: int = 3600  # Default 1 hour
    cleanup: Literal["delete", "keep"] = "keep"
    label: str | None = None  # User-visible label


@dataclass
class SpawnResult:
    """Result from spawning a subagent."""

    success: bool
    session_key: str
    run_id: str
    error: str | None = None


@dataclass
class SubagentRun:
    """Tracking information for a running subagent."""

    run_id: str
    session_key: str
    parent_session_key: str
    task: str
    label: str | None
    started_at: datetime
    timeout_ms: int
    cleanup: Literal["delete", "keep"]
    agent_id: str


# Registry of active subagent runs
_active_runs: dict[str, SubagentRun] = {}


def build_subagent_system_prompt(
    requester_session_key: str | None,
    child_session_key: str,
    task: str,
    label: str | None = None,
) -> str:
    """Build the system prompt for a subagent.

    This prompt restricts the subagent's behavior and focuses it on the task.

    Args:
        requester_session_key: Parent session key
        child_session_key: Subagent session key
        task: Task description
        label: Optional label

    Returns:
        System prompt string
    """
    task_text = task or "(no specific task)"
    label_text = label or child_session_key.split(":")[-1]

    return f"""
# Subagent Context

You are a **subagent** spawned by the main agent for a specific task.

## Your Role
- You were created to handle: {task_text}
- Complete this task. That's your entire purpose.
- You are NOT the main agent. Don't try to be.

## Rules
1. **Stay focused** - Do your assigned task, nothing else
2. **Complete the task** - Your final message will be automatically reported
3. **Don't initiate** - No heartbeats, no proactive actions, no side quests
4. **Be ephemeral** - You may be terminated after task completion

## What You DON'T Do
- NO user conversations (that's main agent's job)
- NO external messages unless explicitly tasked
- NO cron jobs or persistent state
- NO pretending to be the main agent
- NO using the `message` tool directly
- NO spawning other subagents

## Session Context
- Label: {label_text}
- Requester session: {requester_session_key or "unknown"}
- Your session: {child_session_key}
"""


def generate_run_id() -> str:
    """Generate a unique run ID."""
    return f"run_{uuid.uuid4().hex[:12]}"


async def spawn_subagent(
    params: SpawnParams,
    parent_context: AgentContext,
) -> SpawnResult:
    """Spawn a new subagent session.

    Creates a subagent session and returns immediately. The subagent
    runs asynchronously and reports results through the announce flow.

    Args:
        params: Spawn parameters
        parent_context: Parent agent context

    Returns:
        SpawnResult with session info
    """
    agent_id = params.agent_id or parent_context.session_key.split(":")[1] if parent_context.session_key else "default"
    parent_session_key = parent_context.session_key or f"agent:{agent_id}:main"

    # Create subagent session
    manager = get_session_manager()
    try:
        session = manager.spawn_subagent_session(
            agent_id=agent_id,
            parent_session_key=parent_session_key,
            task=params.task,
            label=params.label,
            model=params.model,
            model_provider=params.model_provider,
        )
    except ValueError as e:
        return SpawnResult(
            success=False,
            session_key="",
            run_id="",
            error=str(e),
        )

    run_id = generate_run_id()
    now = datetime.now()

    # Track the run
    run = SubagentRun(
        run_id=run_id,
        session_key=session.session_key,
        parent_session_key=parent_session_key,
        task=params.task,
        label=params.label,
        started_at=now,
        timeout_ms=params.run_timeout_seconds * 1000,
        cleanup=params.cleanup,
        agent_id=agent_id,
    )
    _active_runs[run_id] = run

    logger.info(
        f"Spawned subagent {session.session_key} with run_id={run_id} "
        f"for task: {params.task[:50]}..."
    )

    return SpawnResult(
        success=True,
        session_key=session.session_key,
        run_id=run_id,
    )


def get_active_run(run_id: str) -> SubagentRun | None:
    """Get an active subagent run by ID."""
    return _active_runs.get(run_id)


def complete_run(run_id: str, outcome: SubagentOutcome) -> SubagentResult | None:
    """Mark a subagent run as complete.

    Args:
        run_id: Run ID
        outcome: Outcome of the run

    Returns:
        SubagentResult or None if not found
    """
    run = _active_runs.pop(run_id, None)
    if not run:
        return None

    ended_at = datetime.now()
    duration_ms = int((ended_at - run.started_at).total_seconds() * 1000)

    # Get the result from session history
    manager = get_session_manager()
    result_text = manager.get_latest_reply(run.agent_id, run.session_key.split(":")[-1])

    return SubagentResult(
        session_key=run.session_key,
        run_id=run_id,
        outcome=outcome,
        result=result_text,
        duration_ms=duration_ms,
    )


async def run_announce_flow(
    run_id: str,
    outcome: SubagentOutcome,
    gateway_call: Any | None = None,  # Callable for gateway communication
) -> bool:
    """Run the subagent announcement flow.

    This is called when a subagent completes to notify the parent session.

    Args:
        run_id: Run ID
        outcome: Execution outcome
        gateway_call: Optional gateway call function

    Returns:
        True if announcement succeeded
    """
    run = _active_runs.get(run_id)
    if not run:
        logger.warning(f"Cannot announce: run {run_id} not found")
        return False

    result = complete_run(run_id, outcome)
    if not result:
        return False

    # Build stats line
    duration_seconds = result.duration_ms / 1000
    stats_line = f"[Stats: duration={duration_seconds:.1f}s, tokens={result.tokens_used}]"

    # Build status label
    status_labels = {
        "ok": "completed",
        "error": "failed",
        "timeout": "timed out",
        "unknown": "ended",
    }
    status_label = status_labels.get(outcome, "ended")

    # Build task label (truncated)
    task_label = run.task[:50] + "..." if len(run.task) > 50 else run.task

    # Build trigger message
    trigger_message = f"""
A background task "{task_label}" just {status_label}.

Findings:
{result.result or "(no output)"}

{stats_line}

Summarize this naturally for the user. Keep it brief (1-2 sentences).
"""

    # Send to parent session via gateway (if available)
    if gateway_call:
        try:
            await gateway_call({
                "method": "agent",
                "params": {
                    "sessionKey": run.parent_session_key,
                    "message": trigger_message,
                    "deliver": True,
                },
            })
        except Exception as e:
            logger.error(f"Failed to send subagent announcement: {e}")
            return False

    # Cleanup if requested
    if run.cleanup == "delete":
        manager = get_session_manager()
        manager.delete_session(run.agent_id, run.session_key)

    logger.info(f"Subagent {run.session_key} announced with outcome: {outcome}")
    return True


def list_active_runs(parent_session_key: str | None = None) -> list[SubagentRun]:
    """List active subagent runs.

    Args:
        parent_session_key: Optional filter by parent

    Returns:
        List of active SubagentRun
    """
    runs = list(_active_runs.values())
    if parent_session_key:
        runs = [r for r in runs if r.parent_session_key == parent_session_key]
    return runs


def get_subagent_context(
    parent_context: AgentContext,
    session: SessionEntry,
    task: str,
    params: SpawnParams,
) -> AgentContext:
    """Create an AgentContext for a subagent.

    Args:
        parent_context: Parent agent context
        session: Subagent session entry
        task: Task description
        params: Spawn parameters

    Returns:
        AgentContext configured for subagent
    """
    return AgentContext(
        session_id=session.session_id,
        session_key=session.session_key,
        session_type=SessionType.SUBAGENT,
        workspace_dir=parent_context.workspace_dir,
        agent_dir=parent_context.agent_dir,
        spawned_by=parent_context.session_key,
        is_subagent=True,
        provider=params.model_provider or parent_context.provider,
        model_id=params.model or parent_context.model_id,
        sandbox_enabled=True,  # Subagents always sandboxed
        extra_system_prompt=build_subagent_system_prompt(
            requester_session_key=parent_context.session_key,
            child_session_key=session.session_key,
            task=task,
            label=params.label,
        ),
    )
