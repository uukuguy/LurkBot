"""Bootstrap file system for LurkBot agents.

This module handles loading and filtering workspace bootstrap files,
following MoltBot's bootstrap system implementation.

Bootstrap files define the agent's personality, capabilities, and context:
- SOUL.md: Core personality and values (not for subagents)
- IDENTITY.md: Agent name, emoji, appearance (not for subagents)
- USER.md: User preferences and context (not for subagents)
- AGENTS.md: Workspace guidelines and rules
- TOOLS.md: Tool descriptions and configuration
- HEARTBEAT.md: Periodic check tasks (main session only)
- MEMORY.md: Long-term memory (main session only)
- BOOTSTRAP.md: First-run setup (deleted after completion)
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from lurkbot.logging import get_logger

logger = get_logger("bootstrap")

# Bootstrap file names (constants from MoltBot workspace.ts)
AGENTS_FILENAME = "AGENTS.md"
SOUL_FILENAME = "SOUL.md"
TOOLS_FILENAME = "TOOLS.md"
IDENTITY_FILENAME = "IDENTITY.md"
USER_FILENAME = "USER.md"
HEARTBEAT_FILENAME = "HEARTBEAT.md"
BOOTSTRAP_FILENAME = "BOOTSTRAP.md"
MEMORY_FILENAME = "MEMORY.md"
MEMORY_ALT_FILENAME = "memory.md"  # Alternative lowercase

# Bootstrap file type
BootstrapFileName = Literal[
    "AGENTS.md",
    "SOUL.md",
    "TOOLS.md",
    "IDENTITY.md",
    "USER.md",
    "HEARTBEAT.md",
    "BOOTSTRAP.md",
    "MEMORY.md",
    "memory.md",
]

# Files allowed for subagent sessions (from MoltBot workspace.ts:280)
SUBAGENT_BOOTSTRAP_ALLOWLIST: set[str] = {AGENTS_FILENAME, TOOLS_FILENAME}

# Default maximum characters for bootstrap file content
DEFAULT_BOOTSTRAP_MAX_CHARS = 20_000

# Truncation ratios (from MoltBot bootstrap.ts:73-74)
BOOTSTRAP_HEAD_RATIO = 0.7
BOOTSTRAP_TAIL_RATIO = 0.2


@dataclass
class BootstrapFile:
    """A workspace bootstrap file.

    Matches MoltBot's WorkspaceBootstrapFile type.
    """

    name: BootstrapFileName
    path: str
    content: str | None = None
    missing: bool = False


@dataclass
class ContextFile:
    """A context file to inject into the system prompt.

    Matches MoltBot's EmbeddedContextFile type.
    """

    path: str
    content: str


@dataclass
class TrimResult:
    """Result of trimming bootstrap content."""

    content: str
    truncated: bool
    max_chars: int
    original_length: int


def get_default_workspace_dir() -> str:
    """Get the default agent workspace directory.

    Returns ~/clawd by default, or ~/clawd-{profile} if LURKBOT_PROFILE is set.
    Matches MoltBot's resolveDefaultAgentWorkspaceDir.
    """
    profile = os.environ.get("LURKBOT_PROFILE", "").strip()
    home = Path.home()

    if profile and profile.lower() != "default":
        return str(home / f"clawd-{profile}")

    return str(home / "clawd")


def resolve_user_path(path_str: str) -> str:
    """Resolve a path with ~ expansion."""
    return str(Path(path_str).expanduser().resolve())


def is_subagent_session_key(session_key: str | None) -> bool:
    """Check if a session key indicates a subagent session.

    Subagent session keys contain ':subagent:' in their format.
    """
    if not session_key:
        return False
    return ":subagent:" in session_key or session_key.endswith(":subagent")


async def load_workspace_bootstrap_files(workspace_dir: str) -> list[BootstrapFile]:
    """Load all bootstrap files from a workspace directory.

    Matches MoltBot's loadWorkspaceBootstrapFiles function.

    Args:
        workspace_dir: Path to the workspace directory

    Returns:
        List of BootstrapFile objects (some may be missing)
    """
    import aiofiles

    resolved_dir = resolve_user_path(workspace_dir)

    # Define the standard bootstrap files
    entries: list[tuple[BootstrapFileName, str]] = [
        (AGENTS_FILENAME, os.path.join(resolved_dir, AGENTS_FILENAME)),
        (SOUL_FILENAME, os.path.join(resolved_dir, SOUL_FILENAME)),
        (TOOLS_FILENAME, os.path.join(resolved_dir, TOOLS_FILENAME)),
        (IDENTITY_FILENAME, os.path.join(resolved_dir, IDENTITY_FILENAME)),
        (USER_FILENAME, os.path.join(resolved_dir, USER_FILENAME)),
        (HEARTBEAT_FILENAME, os.path.join(resolved_dir, HEARTBEAT_FILENAME)),
        (BOOTSTRAP_FILENAME, os.path.join(resolved_dir, BOOTSTRAP_FILENAME)),
    ]

    # Add memory file entries (check both MEMORY.md and memory.md)
    memory_entries = await _resolve_memory_bootstrap_entries(resolved_dir)
    entries.extend(memory_entries)

    # Load each file
    result: list[BootstrapFile] = []
    for name, file_path in entries:
        try:
            async with aiofiles.open(file_path, encoding="utf-8") as f:
                content = await f.read()
            result.append(BootstrapFile(name=name, path=file_path, content=content, missing=False))
        except FileNotFoundError:
            result.append(BootstrapFile(name=name, path=file_path, missing=True))
        except Exception as e:
            logger.warning(f"Error reading bootstrap file {file_path}: {e}")
            result.append(BootstrapFile(name=name, path=file_path, missing=True))

    return result


async def _resolve_memory_bootstrap_entries(
    resolved_dir: str,
) -> list[tuple[BootstrapFileName, str]]:
    """Resolve memory bootstrap file entries, handling both MEMORY.md and memory.md.

    Deduplicates if both point to the same file (symlink).
    """
    candidates: list[BootstrapFileName] = [MEMORY_FILENAME, MEMORY_ALT_FILENAME]
    entries: list[tuple[BootstrapFileName, str]] = []

    for name in candidates:
        file_path = os.path.join(resolved_dir, name)
        if os.path.exists(file_path):
            entries.append((name, file_path))

    # Deduplicate by real path (in case of symlinks)
    if len(entries) <= 1:
        return entries

    seen: set[str] = set()
    deduped: list[tuple[BootstrapFileName, str]] = []
    for name, file_path in entries:
        try:
            real_path = os.path.realpath(file_path)
        except Exception:
            real_path = file_path

        if real_path not in seen:
            seen.add(real_path)
            deduped.append((name, file_path))

    return deduped


def filter_bootstrap_files_for_session(
    files: list[BootstrapFile],
    session_key: str | None = None,
) -> list[BootstrapFile]:
    """Filter bootstrap files based on session type.

    Subagent sessions only get AGENTS.md and TOOLS.md.
    Matches MoltBot's filterBootstrapFilesForSession.

    Args:
        files: List of bootstrap files to filter
        session_key: Session key to check for subagent

    Returns:
        Filtered list of bootstrap files
    """
    if not session_key or not is_subagent_session_key(session_key):
        return files

    return [f for f in files if f.name in SUBAGENT_BOOTSTRAP_ALLOWLIST]


def trim_bootstrap_content(
    content: str,
    file_name: str,
    max_chars: int = DEFAULT_BOOTSTRAP_MAX_CHARS,
) -> TrimResult:
    """Trim bootstrap content if it exceeds the maximum length.

    Uses head (70%) + tail (20%) strategy with truncation marker.
    Matches MoltBot's trimBootstrapContent function.

    Args:
        content: The file content to trim
        file_name: Name of the file (for truncation marker)
        max_chars: Maximum characters allowed

    Returns:
        TrimResult with possibly truncated content
    """
    trimmed = content.rstrip()

    if len(trimmed) <= max_chars:
        return TrimResult(
            content=trimmed,
            truncated=False,
            max_chars=max_chars,
            original_length=len(trimmed),
        )

    # Calculate head and tail sizes
    head_chars = int(max_chars * BOOTSTRAP_HEAD_RATIO)
    tail_chars = int(max_chars * BOOTSTRAP_TAIL_RATIO)

    head = trimmed[:head_chars]
    tail = trimmed[-tail_chars:]

    # Create truncation marker
    marker = "\n".join(
        [
            "",
            f"[...truncated, read {file_name} for full content...]",
            f"…(truncated {file_name}: kept {head_chars}+{tail_chars} chars of {len(trimmed)})…",
            "",
        ]
    )

    content_with_marker = "\n".join([head, marker, tail])

    return TrimResult(
        content=content_with_marker,
        truncated=True,
        max_chars=max_chars,
        original_length=len(trimmed),
    )


def build_bootstrap_context_files(
    files: list[BootstrapFile],
    max_chars: int = DEFAULT_BOOTSTRAP_MAX_CHARS,
    warn: bool = True,
) -> list[ContextFile]:
    """Build context files from bootstrap files for system prompt injection.

    Matches MoltBot's buildBootstrapContextFiles function.

    Args:
        files: List of bootstrap files
        max_chars: Maximum characters per file
        warn: Whether to log warnings for truncation

    Returns:
        List of context files ready for prompt injection
    """
    result: list[ContextFile] = []

    for file in files:
        if file.missing:
            result.append(
                ContextFile(
                    path=file.name,
                    content=f"[MISSING] Expected at: {file.path}",
                )
            )
            continue

        if not file.content:
            continue

        trimmed = trim_bootstrap_content(file.content, file.name, max_chars)

        if not trimmed.content:
            continue

        if trimmed.truncated and warn:
            logger.warning(
                f"Bootstrap file {file.name} is {trimmed.original_length} chars "
                f"(limit {trimmed.max_chars}); truncating in injected context"
            )

        result.append(ContextFile(path=file.name, content=trimmed.content))

    return result


async def resolve_bootstrap_files_for_run(
    workspace_dir: str,
    session_key: str | None = None,
) -> list[BootstrapFile]:
    """Resolve and filter bootstrap files for an agent run.

    Combines loading and filtering into a single operation.

    Args:
        workspace_dir: Path to the workspace directory
        session_key: Session key for filtering

    Returns:
        Filtered list of bootstrap files
    """
    files = await load_workspace_bootstrap_files(workspace_dir)
    return filter_bootstrap_files_for_session(files, session_key)


async def resolve_bootstrap_context_for_run(
    workspace_dir: str,
    session_key: str | None = None,
    max_chars: int = DEFAULT_BOOTSTRAP_MAX_CHARS,
) -> tuple[list[BootstrapFile], list[ContextFile]]:
    """Resolve bootstrap files and build context files for an agent run.

    This is the main entry point for the bootstrap system.
    Matches MoltBot's resolveBootstrapContextForRun.

    Args:
        workspace_dir: Path to the workspace directory
        session_key: Session key for filtering
        max_chars: Maximum characters per file

    Returns:
        Tuple of (bootstrap_files, context_files)
    """
    bootstrap_files = await resolve_bootstrap_files_for_run(workspace_dir, session_key)
    context_files = build_bootstrap_context_files(bootstrap_files, max_chars)
    return bootstrap_files, context_files


async def ensure_agent_workspace(
    workspace_dir: str | None = None,
    ensure_bootstrap_files: bool = False,
) -> dict[str, str | None]:
    """Ensure the agent workspace directory exists.

    Optionally creates default bootstrap files from templates.
    Matches MoltBot's ensureAgentWorkspace.

    Args:
        workspace_dir: Optional workspace directory path
        ensure_bootstrap_files: Whether to create missing bootstrap files

    Returns:
        Dictionary with workspace paths
    """
    dir_path = resolve_user_path(workspace_dir or get_default_workspace_dir())

    # Create directory if needed
    os.makedirs(dir_path, exist_ok=True)

    result: dict[str, str | None] = {"dir": dir_path}

    if not ensure_bootstrap_files:
        return result

    # Define paths for bootstrap files
    result["agents_path"] = os.path.join(dir_path, AGENTS_FILENAME)
    result["soul_path"] = os.path.join(dir_path, SOUL_FILENAME)
    result["tools_path"] = os.path.join(dir_path, TOOLS_FILENAME)
    result["identity_path"] = os.path.join(dir_path, IDENTITY_FILENAME)
    result["user_path"] = os.path.join(dir_path, USER_FILENAME)
    result["heartbeat_path"] = os.path.join(dir_path, HEARTBEAT_FILENAME)
    result["bootstrap_path"] = os.path.join(dir_path, BOOTSTRAP_FILENAME)

    # TODO: Implement template loading and file creation
    # For now, just return the paths

    return result
