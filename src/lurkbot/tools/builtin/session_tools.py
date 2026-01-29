"""Session management tools.

This module provides tools for managing agent sessions:
- sessions_spawn: Create new subagent sessions
- sessions_send: Send messages to other sessions
- sessions_list: List available sessions
- sessions_history: Get session conversation history
- session_status: Get session status
- agents_list: List available agents
"""

from __future__ import annotations

from typing import Any, Callable, Literal

from loguru import logger
from pydantic import BaseModel, Field

from lurkbot.agents.subagent import (
    SpawnParams,
    SpawnResult,
    get_active_run,
    list_active_runs,
    spawn_subagent,
)
from lurkbot.agents.types import AgentContext, SessionType
from lurkbot.sessions import (
    SessionEntry,
    SessionListItem,
    SessionManager,
    SessionState,
    get_session_manager,
)
from lurkbot.tools.builtin.common import (
    ToolResult,
    error_result,
    json_result,
    read_bool_param,
    read_number_param,
    read_string_param,
    text_result,
)


# =============================================================================
# Parameter schemas
# =============================================================================


class SessionsSpawnParams(BaseModel):
    """Parameters for sessions_spawn tool."""

    task: str = Field(..., description="Task description for the subagent")
    agent_id: str | None = Field(None, description="Target agent ID (defaults to current)")
    model: str | None = Field(None, description="Model override")
    thinking: Literal["off", "low", "medium", "high"] = Field(
        "medium", description="Thinking level"
    )
    run_timeout_seconds: int = Field(3600, description="Timeout in seconds")
    cleanup: Literal["delete", "keep"] = Field(
        "keep", description="Whether to delete session after completion"
    )
    label: str | None = Field(None, description="User-visible label for the task")


class SessionsSendParams(BaseModel):
    """Parameters for sessions_send tool."""

    session_key: str = Field(..., description="Target session key")
    message: str = Field(..., description="Message to send")
    deliver: bool = Field(True, description="Whether to deliver to user")


class SessionsListParams(BaseModel):
    """Parameters for sessions_list tool."""

    session_type: str | None = Field(None, description="Filter by session type")
    state: str | None = Field(None, description="Filter by state (active, completed, etc.)")
    limit: int = Field(20, description="Maximum number of results")
    include_message_count: bool = Field(False, description="Include message counts")


class SessionsHistoryParams(BaseModel):
    """Parameters for sessions_history tool."""

    session_key: str = Field(..., description="Session key to get history for")
    limit: int | None = Field(50, description="Maximum messages to return")
    offset: int = Field(0, description="Number of messages to skip")


class SessionStatusParams(BaseModel):
    """Parameters for session_status tool."""

    session_key: str | None = Field(None, description="Session key (defaults to current)")


class AgentsListParams(BaseModel):
    """Parameters for agents_list tool."""

    include_inactive: bool = Field(False, description="Include inactive agents")


# =============================================================================
# Tool implementations
# =============================================================================


async def sessions_spawn_tool(
    params: dict[str, Any],
    context: AgentContext,
) -> ToolResult:
    """Spawn a new subagent session.

    Creates a subagent to handle a specific task asynchronously.
    The subagent will report results back when complete.

    Args:
        params: Tool parameters
        context: Agent context

    Returns:
        ToolResult with session info
    """
    try:
        task = read_string_param(params, "task", required=True)
    except Exception as e:
        return error_result(str(e))

    spawn_params = SpawnParams(
        task=task,
        agent_id=read_string_param(params, "agent_id"),
        model=read_string_param(params, "model"),
        thinking=params.get("thinking", "medium"),
        run_timeout_seconds=int(read_number_param(params, "run_timeout_seconds") or 3600),
        cleanup=params.get("cleanup", "keep"),
        label=read_string_param(params, "label"),
    )

    result = await spawn_subagent(spawn_params, context)

    if not result.success:
        return error_result(result.error or "Failed to spawn subagent")

    return json_result({
        "success": True,
        "session_key": result.session_key,
        "run_id": result.run_id,
        "message": f"Subagent spawned for task: {task[:50]}...",
    })


async def sessions_send_tool(
    params: dict[str, Any],
    context: AgentContext,
    gateway_call: Callable[..., Any] | None = None,
) -> ToolResult:
    """Send a message to another session.

    Args:
        params: Tool parameters
        context: Agent context
        gateway_call: Gateway communication function

    Returns:
        ToolResult
    """
    try:
        session_key = read_string_param(params, "session_key", required=True)
        message = read_string_param(params, "message", required=True)
    except Exception as e:
        return error_result(str(e))

    deliver = read_bool_param(params, "deliver", default=True)

    if gateway_call:
        try:
            await gateway_call({
                "method": "agent",
                "params": {
                    "sessionKey": session_key,
                    "message": message,
                    "deliver": deliver,
                },
            })
            return text_result(f"Message sent to session: {session_key}")
        except Exception as e:
            return error_result(f"Failed to send message: {e}")
    else:
        return error_result("Gateway not available for cross-session messaging")


async def sessions_list_tool(
    params: dict[str, Any],
    context: AgentContext,
) -> ToolResult:
    """List available sessions.

    Args:
        params: Tool parameters
        context: Agent context

    Returns:
        ToolResult with session list
    """
    session_type_str = read_string_param(params, "session_type")
    state_str = read_string_param(params, "state")
    limit = read_number_param(params, "limit") or 20
    include_message_count = read_bool_param(params, "include_message_count", default=False)

    # Parse session type
    session_type = None
    if session_type_str:
        try:
            session_type = SessionType(session_type_str)
        except ValueError:
            pass

    # Parse state
    state = None
    if state_str:
        try:
            state = SessionState(state_str)
        except ValueError:
            pass

    # Get agent ID from context
    agent_id = "default"
    if context.session_key:
        parts = context.session_key.split(":")
        if len(parts) >= 2:
            agent_id = parts[1]

    manager = get_session_manager()
    sessions = manager.list_sessions(
        agent_id=agent_id,
        session_type=session_type,
        state=state,
        limit=int(limit),
        include_message_count=include_message_count,
    )

    # Also include active subagent runs
    active_runs = list_active_runs(context.session_key)

    return json_result({
        "sessions": [
            {
                "session_id": s.session_id,
                "session_key": s.session_key,
                "session_type": s.session_type,
                "state": s.state.value,
                "label": s.label,
                "created_at": s.created_at,
                "updated_at": s.updated_at,
                "message_count": s.message_count,
                "total_tokens": s.total_tokens,
            }
            for s in sessions
        ],
        "active_subagents": [
            {
                "run_id": r.run_id,
                "session_key": r.session_key,
                "task": r.task[:50] + "..." if len(r.task) > 50 else r.task,
                "label": r.label,
                "started_at": r.started_at.isoformat(),
            }
            for r in active_runs
        ],
        "total": len(sessions),
    })


async def sessions_history_tool(
    params: dict[str, Any],
    context: AgentContext,
) -> ToolResult:
    """Get conversation history for a session.

    Args:
        params: Tool parameters
        context: Agent context

    Returns:
        ToolResult with message history
    """
    try:
        session_key = read_string_param(params, "session_key", required=True)
    except Exception as e:
        return error_result(str(e))

    limit = read_number_param(params, "limit") or 50
    offset = read_number_param(params, "offset") or 0

    # Get agent ID from session key
    parts = session_key.split(":")
    if len(parts) < 2:
        return error_result(f"Invalid session key format: {session_key}")
    agent_id = parts[1]

    manager = get_session_manager()

    # Get session to find session_id
    session = manager.get_session(agent_id, session_key)
    if not session:
        return error_result(f"Session not found: {session_key}")

    messages = manager.get_history(
        agent_id=agent_id,
        session_id=session.session_id,
        limit=int(limit) if limit else None,
        offset=int(offset),
    )

    return json_result({
        "session_key": session_key,
        "session_id": session.session_id,
        "messages": [
            {
                "message_id": m.message_id,
                "role": m.role,
                "content": m.content if isinstance(m.content, str) else "[complex content]",
                "timestamp": m.timestamp,
                "name": m.name,
            }
            for m in messages
        ],
        "total": len(messages),
        "has_more": len(messages) == limit,
    })


async def session_status_tool(
    params: dict[str, Any],
    context: AgentContext,
) -> ToolResult:
    """Get status of a session.

    Args:
        params: Tool parameters
        context: Agent context

    Returns:
        ToolResult with session status
    """
    session_key = read_string_param(params, "session_key") or context.session_key

    if not session_key:
        return error_result("No session key provided and no current session")

    # Get agent ID from session key
    parts = session_key.split(":")
    if len(parts) < 2:
        return error_result(f"Invalid session key format: {session_key}")
    agent_id = parts[1]

    manager = get_session_manager()
    session = manager.get_session(agent_id, session_key)

    if not session:
        return error_result(f"Session not found: {session_key}")

    # Check if this is an active subagent run
    active_run = None
    for run in list_active_runs():
        if run.session_key == session_key:
            active_run = run
            break

    return json_result({
        "session_id": session.session_id,
        "session_key": session.session_key,
        "session_type": session.session_type,
        "state": session.state.value,
        "created_at": session.created_at,
        "updated_at": session.updated_at,
        "channel": session.channel,
        "model": session.model,
        "model_provider": session.model_provider,
        "input_tokens": session.input_tokens,
        "output_tokens": session.output_tokens,
        "total_tokens": session.total_tokens,
        "parent_session": session.parent_session,
        "label": session.label,
        "is_running": active_run is not None,
        "run_id": active_run.run_id if active_run else None,
    })


async def agents_list_tool(
    params: dict[str, Any],
    context: AgentContext,
) -> ToolResult:
    """List available agents.

    Args:
        params: Tool parameters
        context: Agent context

    Returns:
        ToolResult with agent list
    """
    include_inactive = read_bool_param(params, "include_inactive", default=False)

    manager = get_session_manager()
    base_dir = manager.base_dir

    agents = []
    if base_dir.exists():
        for agent_dir in base_dir.iterdir():
            if agent_dir.is_dir():
                agent_id = agent_dir.name

                # Count sessions
                sessions = manager.list_sessions(
                    agent_id=agent_id,
                    state=None if include_inactive else SessionState.ACTIVE,
                    limit=1000,
                )

                active_count = sum(1 for s in sessions if s.state == SessionState.ACTIVE)

                if active_count > 0 or include_inactive:
                    agents.append({
                        "agent_id": agent_id,
                        "session_count": len(sessions),
                        "active_sessions": active_count,
                        "path": str(agent_dir),
                    })

    return json_result({
        "agents": agents,
        "total": len(agents),
    })


# =============================================================================
# Tool factory functions
# =============================================================================


def create_sessions_spawn_tool(context: AgentContext) -> Callable[..., ToolResult]:
    """Create a bound sessions_spawn tool."""

    async def tool(params: dict[str, Any]) -> ToolResult:
        return await sessions_spawn_tool(params, context)

    return tool


def create_sessions_send_tool(
    context: AgentContext,
    gateway_call: Callable[..., Any] | None = None,
) -> Callable[..., ToolResult]:
    """Create a bound sessions_send tool."""

    async def tool(params: dict[str, Any]) -> ToolResult:
        return await sessions_send_tool(params, context, gateway_call)

    return tool


def create_sessions_list_tool(context: AgentContext) -> Callable[..., ToolResult]:
    """Create a bound sessions_list tool."""

    async def tool(params: dict[str, Any]) -> ToolResult:
        return await sessions_list_tool(params, context)

    return tool


def create_sessions_history_tool(context: AgentContext) -> Callable[..., ToolResult]:
    """Create a bound sessions_history tool."""

    async def tool(params: dict[str, Any]) -> ToolResult:
        return await sessions_history_tool(params, context)

    return tool


def create_session_status_tool(context: AgentContext) -> Callable[..., ToolResult]:
    """Create a bound session_status tool."""

    async def tool(params: dict[str, Any]) -> ToolResult:
        return await session_status_tool(params, context)

    return tool


def create_agents_list_tool(context: AgentContext) -> Callable[..., ToolResult]:
    """Create a bound agents_list tool."""

    async def tool(params: dict[str, Any]) -> ToolResult:
        return await agents_list_tool(params, context)

    return tool
