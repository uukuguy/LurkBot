"""Exec tool - Shell command execution.

Ported from moltbot/src/agents/bash-tools.exec.ts

This is a core P0 tool that provides shell command execution with:
- Multiple execution hosts (sandbox/gateway/node)
- Security policies (deny/allowlist/full)
- Approval workflows
- Background execution
- PTY support
- Timeout management
"""

from __future__ import annotations

import asyncio
import os
import shlex
import signal
import subprocess
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Literal

from pydantic import BaseModel, Field

from lurkbot.tools.builtin.common import (
    ToolResult,
    clamp_number,
    coerce_env,
    error_result,
    json_result,
    read_bool_param,
    read_number_param,
    read_string_param,
)


# =============================================================================
# Constants
# =============================================================================

DEFAULT_MAX_OUTPUT = 200_000
DEFAULT_PENDING_MAX_OUTPUT = 200_000
DEFAULT_PATH = os.environ.get(
    "PATH", "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
)
DEFAULT_NOTIFY_TAIL_CHARS = 400
DEFAULT_APPROVAL_TIMEOUT_MS = 120_000
DEFAULT_APPROVAL_REQUEST_TIMEOUT_MS = 130_000
DEFAULT_APPROVAL_RUNNING_NOTICE_MS = 10_000
DEFAULT_YIELD_MS = 10_000
DEFAULT_TIMEOUT_SEC = 120
APPROVAL_SLUG_LENGTH = 8


# =============================================================================
# Types and Enums
# =============================================================================


class ExecHost(str, Enum):
    """Execution host type."""

    SANDBOX = "sandbox"
    GATEWAY = "gateway"
    NODE = "node"


class ExecSecurity(str, Enum):
    """Execution security mode."""

    DENY = "deny"
    ALLOWLIST = "allowlist"
    FULL = "full"


class ExecAsk(str, Enum):
    """Execution ask mode."""

    OFF = "off"
    ON_MISS = "on-miss"
    ALWAYS = "always"


class ExecStatus(str, Enum):
    """Execution status."""

    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    APPROVAL_PENDING = "approval-pending"


@dataclass
class ExecToolDefaults:
    """Default settings for exec tool."""

    host: ExecHost = ExecHost.GATEWAY
    security: ExecSecurity = ExecSecurity.ALLOWLIST
    ask: ExecAsk = ExecAsk.ON_MISS
    node: str | None = None
    path_prepend: list[str] = field(default_factory=list)
    safe_bins: list[str] = field(default_factory=list)
    agent_id: str | None = None
    background_ms: int = DEFAULT_YIELD_MS
    timeout_sec: int = DEFAULT_TIMEOUT_SEC
    approval_running_notice_ms: int = DEFAULT_APPROVAL_RUNNING_NOTICE_MS
    allow_background: bool = True
    scope_key: str | None = None
    session_key: str | None = None
    message_provider: str | None = None
    notify_on_exit: bool = False
    cwd: str | None = None


class ExecParams(BaseModel):
    """Parameters for exec tool."""

    command: str = Field(description="Shell command to execute")
    workdir: str | None = Field(default=None, description="Working directory (defaults to cwd)")
    env: dict[str, str] | None = Field(default=None, description="Environment variables")
    yield_ms: int | None = Field(
        default=None,
        alias="yieldMs",
        description="Milliseconds to wait before backgrounding (default 10000)",
    )
    background: bool | None = Field(
        default=None, description="Run in background immediately"
    )
    timeout: int | None = Field(
        default=None,
        description="Timeout in seconds (optional, kills process on expiry)",
    )
    pty: bool | None = Field(
        default=None,
        description="Run in a pseudo-terminal (PTY) when available",
    )
    elevated: bool | None = Field(
        default=None,
        description="Run on the host with elevated permissions (if allowed)",
    )
    host: str | None = Field(
        default=None, description="Exec host (sandbox|gateway|node)"
    )
    security: str | None = Field(
        default=None, description="Exec security mode (deny|allowlist|full)"
    )
    ask: str | None = Field(
        default=None, description="Exec ask mode (off|on-miss|always)"
    )
    node: str | None = Field(default=None, description="Node id/name for host=node")

    model_config = {"populate_by_name": True}


@dataclass
class ExecRunningDetails:
    """Details for running execution."""

    status: Literal["running"] = "running"
    session_id: str = ""
    pid: int | None = None
    started_at: float = 0.0
    cwd: str | None = None
    tail: str | None = None


@dataclass
class ExecCompletedDetails:
    """Details for completed execution."""

    status: Literal["completed", "failed"] = "completed"
    exit_code: int | None = None
    duration_ms: float = 0.0
    aggregated: str = ""
    cwd: str | None = None


@dataclass
class ExecApprovalDetails:
    """Details for pending approval."""

    status: Literal["approval-pending"] = "approval-pending"
    approval_id: str = ""
    approval_slug: str = ""
    expires_at_ms: float = 0.0
    host: ExecHost = ExecHost.GATEWAY
    command: str = ""
    cwd: str | None = None
    node_id: str | None = None


ExecToolDetails = ExecRunningDetails | ExecCompletedDetails | ExecApprovalDetails


# =============================================================================
# Process Session Registry
# =============================================================================


@dataclass
class ProcessSession:
    """Represents a running or completed process session."""

    id: str
    command: str
    started_at: float
    cwd: str | None = None
    pid: int | None = None
    exit_code: int | None = None
    exit_signal: int | None = None
    exited_at: float | None = None
    backgrounded: bool = False
    aggregated: str = ""
    tail: str = ""
    max_output: int = DEFAULT_MAX_OUTPUT
    pending_max_output: int = DEFAULT_PENDING_MAX_OUTPUT
    scope_key: str | None = None
    session_key: str | None = None
    notify_on_exit: bool = False
    exit_notified: bool = False
    _process: subprocess.Popen | None = None


# Global session registry
_sessions: dict[str, ProcessSession] = {}


def create_session_slug() -> str:
    """Create a unique session ID."""
    return uuid.uuid4().hex


def add_session(session: ProcessSession) -> None:
    """Add a session to the registry."""
    _sessions[session.id] = session


def get_session(session_id: str) -> ProcessSession | None:
    """Get a session by ID."""
    return _sessions.get(session_id)


def remove_session(session_id: str) -> None:
    """Remove a session from the registry."""
    _sessions.pop(session_id, None)


def append_output(session: ProcessSession, data: str) -> None:
    """Append output to a session."""
    session.aggregated += data
    # Keep tail to reasonable size
    max_tail = DEFAULT_NOTIFY_TAIL_CHARS * 2
    if len(session.tail) + len(data) > max_tail:
        session.tail = (session.tail + data)[-max_tail:]
    else:
        session.tail += data

    # Truncate aggregated if too large
    if len(session.aggregated) > session.max_output:
        session.aggregated = session.aggregated[-session.max_output :]


def mark_backgrounded(session: ProcessSession) -> None:
    """Mark a session as backgrounded."""
    session.backgrounded = True


def mark_exited(
    session: ProcessSession,
    exit_code: int | None,
    exit_signal: int | None = None,
) -> None:
    """Mark a session as exited."""
    session.exit_code = exit_code
    session.exit_signal = exit_signal
    session.exited_at = time.time() * 1000


def tail(text: str, max_chars: int) -> str:
    """Get the tail of a string."""
    if len(text) <= max_chars:
        return text
    return text[-max_chars:]


def kill_session(session: ProcessSession) -> None:
    """Kill a session's process."""
    if session._process is not None:
        try:
            # Try SIGTERM first
            session._process.terminate()
            # Give it a moment
            try:
                session._process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                # Force kill
                session._process.kill()
        except ProcessLookupError:
            pass  # Already dead


# =============================================================================
# Helper Functions
# =============================================================================


def normalize_exec_host(value: str | None) -> ExecHost | None:
    """Normalize exec host value."""
    if not value:
        return None
    normalized = value.strip().lower()
    try:
        return ExecHost(normalized)
    except ValueError:
        return None


def normalize_exec_security(value: str | None) -> ExecSecurity | None:
    """Normalize exec security value."""
    if not value:
        return None
    normalized = value.strip().lower()
    try:
        return ExecSecurity(normalized)
    except ValueError:
        return None


def normalize_exec_ask(value: str | None) -> ExecAsk | None:
    """Normalize exec ask value."""
    if not value:
        return None
    normalized = value.strip().lower()
    try:
        return ExecAsk(normalized)
    except ValueError:
        return None


def render_exec_host_label(host: ExecHost) -> str:
    """Get human-readable label for exec host."""
    return host.value


def normalize_path_prepend(entries: list[str] | None) -> list[str]:
    """Normalize path prepend entries."""
    if not entries:
        return []
    seen: set[str] = set()
    normalized: list[str] = []
    for entry in entries:
        if not isinstance(entry, str):
            continue
        trimmed = entry.strip()
        if not trimmed or trimmed in seen:
            continue
        seen.add(trimmed)
        normalized.append(trimmed)
    return normalized


def merge_path_prepend(existing: str | None, prepend: list[str]) -> str:
    """Merge path prepend entries with existing PATH."""
    if not prepend:
        return existing or ""

    existing_parts = [
        part.strip()
        for part in (existing or "").split(os.pathsep)
        if part.strip()
    ]

    merged: list[str] = []
    seen: set[str] = set()

    for part in [*prepend, *existing_parts]:
        if part in seen:
            continue
        seen.add(part)
        merged.append(part)

    return os.pathsep.join(merged)


def apply_path_prepend(
    env: dict[str, str],
    prepend: list[str],
    *,
    require_existing: bool = False,
) -> None:
    """Apply path prepend to environment."""
    if not prepend:
        return
    if require_existing and "PATH" not in env:
        return
    merged = merge_path_prepend(env.get("PATH"), prepend)
    if merged:
        env["PATH"] = merged


def resolve_workdir(
    specified: str | None,
    default_cwd: str | None,
) -> str:
    """Resolve working directory."""
    if specified:
        return os.path.expanduser(specified)
    if default_cwd:
        return os.path.expanduser(default_cwd)
    return os.getcwd()


# =============================================================================
# Exec Process Runner
# =============================================================================


@dataclass
class ExecProcessOutcome:
    """Outcome of an exec process."""

    status: Literal["completed", "failed"]
    exit_code: int | None
    exit_signal: int | None
    duration_ms: float
    aggregated: str
    timed_out: bool
    reason: str | None = None


@dataclass
class ExecProcessHandle:
    """Handle to a running exec process."""

    session: ProcessSession
    started_at: float
    pid: int | None
    promise: asyncio.Task[ExecProcessOutcome]
    kill: Callable[[], None]


async def run_exec_process(
    *,
    command: str,
    workdir: str,
    env: dict[str, str],
    use_pty: bool,
    warnings: list[str],
    max_output: int,
    pending_max_output: int,
    notify_on_exit: bool,
    scope_key: str | None,
    session_key: str | None,
    timeout_sec: int,
    on_update: Callable[[ToolResult], None] | None = None,
) -> ExecProcessHandle:
    """Run an exec process.

    This is the core execution function that spawns and manages a shell process.
    """
    started_at = time.time() * 1000
    session_id = create_session_slug()

    # Create session
    session = ProcessSession(
        id=session_id,
        command=command,
        started_at=started_at,
        cwd=workdir,
        max_output=max_output,
        pending_max_output=pending_max_output,
        notify_on_exit=notify_on_exit,
        scope_key=scope_key,
        session_key=session_key,
    )
    add_session(session)

    # Prepare shell command
    shell = os.environ.get("SHELL", "/bin/bash")

    # Build environment
    proc_env = {**os.environ, **env}
    if "PATH" not in proc_env:
        proc_env["PATH"] = DEFAULT_PATH

    # Spawn process
    try:
        if use_pty:
            # Try to use PTY if available
            try:
                import pty

                master_fd, slave_fd = pty.openpty()
                process = subprocess.Popen(
                    [shell, "-c", command],
                    stdin=slave_fd,
                    stdout=slave_fd,
                    stderr=slave_fd,
                    cwd=workdir,
                    env=proc_env,
                    start_new_session=True,
                )
                os.close(slave_fd)
                session._process = process
                session.pid = process.pid

                # Read from master fd
                async def read_pty() -> None:
                    loop = asyncio.get_event_loop()
                    while True:
                        try:
                            data = await loop.run_in_executor(
                                None, lambda: os.read(master_fd, 4096)
                            )
                            if not data:
                                break
                            append_output(session, data.decode("utf-8", errors="replace"))
                        except OSError:
                            break

                read_task = asyncio.create_task(read_pty())

            except (ImportError, OSError):
                # PTY not available, fall back to regular subprocess
                use_pty = False
                warnings.append("PTY not available, using regular subprocess")

        if not use_pty:
            process = subprocess.Popen(
                [shell, "-c", command],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                cwd=workdir,
                env=proc_env,
                start_new_session=True,
            )
            session._process = process
            session.pid = process.pid

            # Read output in background
            async def read_stdout() -> None:
                loop = asyncio.get_event_loop()
                while True:
                    try:
                        data = await loop.run_in_executor(
                            None, lambda: process.stdout.read(4096) if process.stdout else b""
                        )
                        if not data:
                            break
                        append_output(session, data.decode("utf-8", errors="replace"))
                    except Exception:
                        break

            read_task = asyncio.create_task(read_stdout())

    except Exception as e:
        remove_session(session_id)
        raise RuntimeError(f"Failed to spawn process: {e}") from e

    # Track timeout
    timed_out = False
    timeout_timer: asyncio.Task | None = None

    if timeout_sec > 0:

        async def timeout_handler() -> None:
            nonlocal timed_out
            await asyncio.sleep(timeout_sec)
            if session.exited_at is None:
                timed_out = True
                kill_session(session)

        timeout_timer = asyncio.create_task(timeout_handler())

    # Wait for process to complete
    async def wait_for_completion() -> ExecProcessOutcome:
        loop = asyncio.get_event_loop()

        # Wait for process
        exit_code = await loop.run_in_executor(None, process.wait)

        # Wait for output reader to finish
        try:
            await asyncio.wait_for(read_task, timeout=1.0)
        except asyncio.TimeoutError:
            pass

        # Cancel timeout timer
        if timeout_timer:
            timeout_timer.cancel()

        duration_ms = (time.time() * 1000) - started_at
        mark_exited(session, exit_code)

        # Close PTY master fd if used
        if use_pty:
            try:
                os.close(master_fd)  # type: ignore
            except Exception:
                pass

        status: Literal["completed", "failed"] = "completed" if exit_code == 0 else "failed"

        return ExecProcessOutcome(
            status=status,
            exit_code=exit_code,
            exit_signal=None,
            duration_ms=duration_ms,
            aggregated=session.aggregated,
            timed_out=timed_out,
            reason="Timeout" if timed_out else None,
        )

    promise = asyncio.create_task(wait_for_completion())

    return ExecProcessHandle(
        session=session,
        started_at=started_at,
        pid=session.pid,
        promise=promise,
        kill=lambda: kill_session(session),
    )


# =============================================================================
# Exec Tool Implementation
# =============================================================================


async def exec_tool(
    params: dict[str, Any],
    defaults: ExecToolDefaults | None = None,
    on_update: Callable[[ToolResult], None] | None = None,
) -> ToolResult:
    """Execute a shell command.

    This is the main entry point for the exec tool.

    Args:
        params: Tool parameters
        defaults: Default settings
        on_update: Callback for progress updates

    Returns:
        ToolResult with execution details
    """
    defaults = defaults or ExecToolDefaults()

    # Parse parameters
    command = read_string_param(params, "command", required=True)
    if not command:
        return error_result("command required")

    workdir_param = read_string_param(params, "workdir")
    env_param = params.get("env")
    yield_ms = read_number_param(params, "yieldMs", integer=True)
    background = read_bool_param(params, "background")
    timeout = read_number_param(params, "timeout", integer=True)
    use_pty = read_bool_param(params, "pty")
    elevated = read_bool_param(params, "elevated")

    # Normalize host/security/ask
    host_param = read_string_param(params, "host")
    security_param = read_string_param(params, "security")
    ask_param = read_string_param(params, "ask")
    node_param = read_string_param(params, "node")

    host = normalize_exec_host(host_param) or defaults.host
    security = normalize_exec_security(security_param) or defaults.security
    ask = normalize_exec_ask(ask_param) or defaults.ask

    # Check security policy
    if security == ExecSecurity.DENY:
        return error_result(f"exec denied: host={host.value} security=deny")

    # Resolve working directory
    workdir = resolve_workdir(workdir_param, defaults.cwd)

    # Build environment
    env = coerce_env(env_param)
    if "PATH" not in env:
        env["PATH"] = DEFAULT_PATH

    # Apply path prepend
    apply_path_prepend(env, defaults.path_prepend)

    # Resolve timeout
    timeout_sec = int(timeout) if timeout else defaults.timeout_sec

    # Resolve yield time
    actual_yield_ms = yield_ms if yield_ms is not None else defaults.background_ms

    # Run process
    warnings: list[str] = []

    try:
        handle = await run_exec_process(
            command=command,
            workdir=workdir,
            env=env,
            use_pty=use_pty,
            warnings=warnings,
            max_output=DEFAULT_MAX_OUTPUT,
            pending_max_output=DEFAULT_PENDING_MAX_OUTPUT,
            notify_on_exit=defaults.notify_on_exit,
            scope_key=defaults.scope_key,
            session_key=defaults.session_key,
            timeout_sec=timeout_sec,
            on_update=on_update,
        )

        # If background requested, return immediately
        if background:
            mark_backgrounded(handle.session)
            return json_result({
                "status": "running",
                "sessionId": handle.session.id,
                "pid": handle.pid,
                "startedAt": handle.started_at,
                "cwd": workdir,
                "backgrounded": True,
            })

        # Wait for completion or yield timeout
        if actual_yield_ms > 0 and defaults.allow_background:
            try:
                outcome = await asyncio.wait_for(
                    handle.promise,
                    timeout=actual_yield_ms / 1000,
                )
            except asyncio.TimeoutError:
                # Yield to background
                mark_backgrounded(handle.session)
                return json_result({
                    "status": "running",
                    "sessionId": handle.session.id,
                    "pid": handle.pid,
                    "startedAt": handle.started_at,
                    "cwd": workdir,
                    "tail": tail(handle.session.aggregated, DEFAULT_NOTIFY_TAIL_CHARS),
                    "backgrounded": True,
                })
        else:
            outcome = await handle.promise

        # Build result
        result_data: dict[str, Any] = {
            "status": outcome.status,
            "exitCode": outcome.exit_code,
            "durationMs": outcome.duration_ms,
            "cwd": workdir,
        }

        if warnings:
            result_data["warnings"] = warnings

        if outcome.timed_out:
            result_data["timedOut"] = True

        # Add output
        if outcome.aggregated:
            result_data["output"] = outcome.aggregated

        return json_result(result_data)

    except Exception as e:
        return error_result(str(e), {"command": command, "workdir": workdir})


# =============================================================================
# Process Tool (Query Background Processes)
# =============================================================================


class ProcessParams(BaseModel):
    """Parameters for process tool."""

    action: str = Field(description="Action: list, status, kill, signal, stdin")
    session_id: str | None = Field(
        default=None, alias="sessionId", description="Session ID for status/kill/signal/stdin"
    )
    signal_name: str | None = Field(
        default=None, alias="signal", description="Signal name for signal action"
    )
    input: str | None = Field(default=None, description="Input for stdin action")

    model_config = {"populate_by_name": True}


async def process_tool(params: dict[str, Any]) -> ToolResult:
    """Manage background processes.

    Actions:
    - list: List all sessions
    - status: Get session status
    - kill: Kill a session
    - signal: Send signal to session
    - stdin: Send input to session

    Args:
        params: Tool parameters

    Returns:
        ToolResult with process information
    """
    action = read_string_param(params, "action", required=True)
    session_id = read_string_param(params, "sessionId")
    signal_name = read_string_param(params, "signal")
    stdin_input = read_string_param(params, "input")

    if action == "list":
        sessions_list = [
            {
                "id": s.id,
                "command": s.command[:100],
                "pid": s.pid,
                "startedAt": s.started_at,
                "exited": s.exited_at is not None,
                "exitCode": s.exit_code,
                "backgrounded": s.backgrounded,
            }
            for s in _sessions.values()
        ]
        return json_result({"sessions": sessions_list})

    if not session_id:
        return error_result("sessionId required for this action")

    session = get_session(session_id)
    if not session:
        # Try prefix match
        matches = [s for s in _sessions.values() if s.id.startswith(session_id)]
        if len(matches) == 1:
            session = matches[0]
        elif len(matches) > 1:
            return error_result(f"Ambiguous session ID: {session_id}")
        else:
            return error_result(f"Session not found: {session_id}")

    if action == "status":
        return json_result({
            "id": session.id,
            "command": session.command,
            "pid": session.pid,
            "startedAt": session.started_at,
            "cwd": session.cwd,
            "exited": session.exited_at is not None,
            "exitCode": session.exit_code,
            "exitSignal": session.exit_signal,
            "exitedAt": session.exited_at,
            "backgrounded": session.backgrounded,
            "output": session.aggregated,
            "tail": tail(session.aggregated, DEFAULT_NOTIFY_TAIL_CHARS),
        })

    if action == "kill":
        kill_session(session)
        return json_result({"killed": True, "sessionId": session.id})

    if action == "signal":
        if not signal_name:
            return error_result("signal name required")
        if session._process is None:
            return error_result("Process not available")
        try:
            sig = getattr(signal, f"SIG{signal_name.upper()}", None)
            if sig is None:
                sig = int(signal_name)
            session._process.send_signal(sig)
            return json_result({"signaled": True, "signal": signal_name, "sessionId": session.id})
        except Exception as e:
            return error_result(f"Failed to send signal: {e}")

    if action == "stdin":
        if not stdin_input:
            return error_result("input required")
        if session._process is None or session._process.stdin is None:
            return error_result("Process stdin not available")
        try:
            session._process.stdin.write(stdin_input.encode())
            session._process.stdin.flush()
            return json_result({"sent": True, "sessionId": session.id})
        except Exception as e:
            return error_result(f"Failed to write to stdin: {e}")

    return error_result(f"Unknown action: {action}")


# =============================================================================
# Tool Registration Helpers
# =============================================================================


def create_exec_tool(defaults: ExecToolDefaults | None = None) -> dict[str, Any]:
    """Create exec tool definition for PydanticAI.

    Returns a dict that can be used with Tool.from_schema().
    """
    return {
        "name": "exec",
        "label": "Execute",
        "description": (
            "Execute a shell command. "
            "Supports background execution, timeouts, and PTY mode. "
            "Use process tool to manage background processes."
        ),
        "parameters": ExecParams.model_json_schema(),
    }


def create_process_tool() -> dict[str, Any]:
    """Create process tool definition for PydanticAI."""
    return {
        "name": "process",
        "label": "Process",
        "description": (
            "Manage background processes. "
            "Actions: list (all sessions), status (session details), "
            "kill (terminate), signal (send signal), stdin (send input)."
        ),
        "parameters": ProcessParams.model_json_schema(),
    }
