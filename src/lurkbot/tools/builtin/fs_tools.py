"""File system tools - read, write, edit.

Ported from moltbot's file system tools.

These are core P0 tools that provide:
- read: Read file contents with line range support
- write: Write content to files
- edit: Edit files with search/replace operations
- apply_patch: Apply unified diff patches
"""

from __future__ import annotations

import difflib
import os
import re
import stat
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from lurkbot.tools.builtin.common import (
    ParamError,
    ToolResult,
    ToolResultContent,
    ToolResultContentType,
    error_result,
    json_result,
    read_bool_param,
    read_number_param,
    read_string_param,
    text_result,
)
from lurkbot.tools.builtin.fs_safe import (
    SafeOpenError,
    SafeOpenErrorCode,
    is_path_within_root,
    open_file_within_root_sync,
    resolve_safe_path,
)


# =============================================================================
# Constants
# =============================================================================

DEFAULT_MAX_READ_LINES = 2000
DEFAULT_MAX_LINE_LENGTH = 2000
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB


# =============================================================================
# Read Tool
# =============================================================================


class ReadParams(BaseModel):
    """Parameters for read tool."""

    path: str = Field(description="File path to read")
    from_line: int | None = Field(
        default=None, alias="from", description="Starting line number (1-indexed)"
    )
    lines: int | None = Field(default=None, description="Number of lines to read")
    encoding: str | None = Field(default=None, description="File encoding (default: utf-8)")

    model_config = {"populate_by_name": True}


async def read_tool(
    params: dict[str, Any],
    root_dir: str | None = None,
) -> ToolResult:
    """Read file contents.

    Supports reading entire files or specific line ranges.
    Output format matches cat -n (line numbers).

    Args:
        params: Tool parameters
        root_dir: Optional root directory for path validation

    Returns:
        ToolResult with file contents
    """
    path = read_string_param(params, "path", required=True)
    if not path:
        return error_result("path required")

    from_line = read_number_param(params, "from", integer=True)
    num_lines = read_number_param(params, "lines", integer=True)
    encoding = read_string_param(params, "encoding") or "utf-8"

    # Resolve path
    if root_dir:
        resolved = resolve_safe_path(root_dir, path)
        if not resolved:
            return error_result("path escapes root directory")
        file_path = resolved
    else:
        file_path = os.path.expanduser(path)

    # Check file exists
    if not os.path.exists(file_path):
        return error_result(f"file not found: {path}")

    if not os.path.isfile(file_path):
        return error_result(f"not a file: {path}")

    # Check file size
    try:
        file_stat = os.stat(file_path)
        if file_stat.st_size > MAX_FILE_SIZE_BYTES:
            return error_result(
                f"file too large: {file_stat.st_size} bytes (max {MAX_FILE_SIZE_BYTES})"
            )
    except OSError as e:
        return error_result(f"cannot stat file: {e}")

    # Read file
    try:
        with open(file_path, encoding=encoding, errors="replace") as f:
            all_lines = f.readlines()
    except OSError as e:
        return error_result(f"cannot read file: {e}")
    except UnicodeDecodeError as e:
        return error_result(f"encoding error: {e}")

    total_lines = len(all_lines)

    # Handle line range
    start_idx = 0
    end_idx = total_lines

    if from_line is not None:
        start_idx = max(0, from_line - 1)  # Convert to 0-indexed

    if num_lines is not None:
        end_idx = min(total_lines, start_idx + num_lines)
    else:
        # Default max lines
        end_idx = min(total_lines, start_idx + DEFAULT_MAX_READ_LINES)

    # Extract lines
    selected_lines = all_lines[start_idx:end_idx]

    # Format with line numbers (cat -n format)
    formatted_lines: list[str] = []
    for i, line in enumerate(selected_lines):
        line_num = start_idx + i + 1
        # Truncate long lines
        line_content = line.rstrip("\n\r")
        if len(line_content) > DEFAULT_MAX_LINE_LENGTH:
            line_content = line_content[:DEFAULT_MAX_LINE_LENGTH] + "..."
        formatted_lines.append(f"{line_num:6d}\t{line_content}")

    content = "\n".join(formatted_lines)

    # Build result
    result_data = {
        "path": path,
        "totalLines": total_lines,
        "fromLine": start_idx + 1,
        "toLine": end_idx,
        "truncated": end_idx < total_lines,
    }

    if content:
        return ToolResult(
            content=[
                ToolResultContent(
                    type=ToolResultContentType.TEXT,
                    text=content,
                )
            ],
            details=result_data,
        )
    else:
        return json_result({**result_data, "content": "(empty)"})


# =============================================================================
# Write Tool
# =============================================================================


class WriteParams(BaseModel):
    """Parameters for write tool."""

    path: str = Field(description="File path to write")
    content: str = Field(description="Content to write")
    create_dirs: bool | None = Field(
        default=None,
        alias="createDirs",
        description="Create parent directories if missing",
    )
    append: bool | None = Field(default=None, description="Append to file instead of overwrite")
    encoding: str | None = Field(default=None, description="File encoding (default: utf-8)")

    model_config = {"populate_by_name": True}


async def write_tool(
    params: dict[str, Any],
    root_dir: str | None = None,
) -> ToolResult:
    """Write content to a file.

    Args:
        params: Tool parameters
        root_dir: Optional root directory for path validation

    Returns:
        ToolResult with write status
    """
    path = read_string_param(params, "path", required=True)
    if not path:
        return error_result("path required")

    # Don't trim content - preserve exact content including whitespace/newlines
    content = read_string_param(params, "content", required=True, allow_empty=True, trim=False)
    if content is None:
        return error_result("content required")

    create_dirs = read_bool_param(params, "createDirs", default=False)
    append = read_bool_param(params, "append", default=False)
    encoding = read_string_param(params, "encoding") or "utf-8"

    # Resolve path
    if root_dir:
        resolved = resolve_safe_path(root_dir, path)
        if not resolved:
            return error_result("path escapes root directory")
        file_path = resolved
    else:
        file_path = os.path.expanduser(path)

    # Create parent directories if requested
    parent_dir = os.path.dirname(file_path)
    if parent_dir and not os.path.exists(parent_dir):
        if create_dirs:
            try:
                os.makedirs(parent_dir, exist_ok=True)
            except OSError as e:
                return error_result(f"cannot create directories: {e}")
        else:
            return error_result(f"parent directory does not exist: {parent_dir}")

    # Check if path is a directory
    if os.path.exists(file_path) and os.path.isdir(file_path):
        return error_result(f"path is a directory: {path}")

    # Write file
    mode = "a" if append else "w"
    try:
        with open(file_path, mode, encoding=encoding) as f:
            f.write(content)
    except OSError as e:
        return error_result(f"cannot write file: {e}")

    # Get file info
    try:
        file_stat = os.stat(file_path)
        size = file_stat.st_size
    except OSError:
        size = len(content.encode(encoding))

    return json_result({
        "path": path,
        "written": True,
        "bytes": size,
        "appended": append,
    })


# =============================================================================
# Edit Tool
# =============================================================================


class EditParams(BaseModel):
    """Parameters for edit tool."""

    path: str = Field(description="File path to edit")
    old: str = Field(description="Text to find and replace")
    new: str = Field(description="Replacement text")
    all_occurrences: bool | None = Field(
        default=None,
        alias="all",
        description="Replace all occurrences (default: first only)",
    )
    encoding: str | None = Field(default=None, description="File encoding (default: utf-8)")

    model_config = {"populate_by_name": True}


async def edit_tool(
    params: dict[str, Any],
    root_dir: str | None = None,
) -> ToolResult:
    """Edit a file with search and replace.

    Args:
        params: Tool parameters
        root_dir: Optional root directory for path validation

    Returns:
        ToolResult with edit status
    """
    path = read_string_param(params, "path", required=True)
    if not path:
        return error_result("path required")

    old_text = read_string_param(params, "old", required=True, allow_empty=True)
    if old_text is None:
        return error_result("old text required")

    new_text = read_string_param(params, "new", required=True, allow_empty=True)
    if new_text is None:
        return error_result("new text required")

    all_occurrences = read_bool_param(params, "all", default=False)
    encoding = read_string_param(params, "encoding") or "utf-8"

    # Resolve path
    if root_dir:
        resolved = resolve_safe_path(root_dir, path)
        if not resolved:
            return error_result("path escapes root directory")
        file_path = resolved
    else:
        file_path = os.path.expanduser(path)

    # Check file exists
    if not os.path.exists(file_path):
        return error_result(f"file not found: {path}")

    if not os.path.isfile(file_path):
        return error_result(f"not a file: {path}")

    # Read current content
    try:
        with open(file_path, encoding=encoding, errors="replace") as f:
            content = f.read()
    except OSError as e:
        return error_result(f"cannot read file: {e}")

    # Check if old text exists
    if old_text not in content:
        return error_result(f"text not found in file: {repr(old_text[:100])}")

    # Count occurrences
    count = content.count(old_text)

    # Perform replacement
    if all_occurrences:
        new_content = content.replace(old_text, new_text)
        replaced = count
    else:
        new_content = content.replace(old_text, new_text, 1)
        replaced = 1

    # Write back
    try:
        with open(file_path, "w", encoding=encoding) as f:
            f.write(new_content)
    except OSError as e:
        return error_result(f"cannot write file: {e}")

    return json_result({
        "path": path,
        "edited": True,
        "occurrences": count,
        "replaced": replaced,
    })


# =============================================================================
# Apply Patch Tool
# =============================================================================


class ApplyPatchParams(BaseModel):
    """Parameters for apply_patch tool."""

    path: str = Field(description="File path to patch")
    patch: str = Field(description="Unified diff patch content")
    encoding: str | None = Field(default=None, description="File encoding (default: utf-8)")

    model_config = {"populate_by_name": True}


def _parse_unified_diff(patch: str) -> list[dict[str, Any]]:
    """Parse a unified diff into hunks.

    Args:
        patch: Unified diff content

    Returns:
        List of hunks with line info and changes
    """
    hunks: list[dict[str, Any]] = []
    lines = patch.split("\n")
    i = 0

    # Skip header lines (---, +++)
    while i < len(lines) and not lines[i].startswith("@@"):
        i += 1

    while i < len(lines):
        line = lines[i]

        # Parse hunk header
        if line.startswith("@@"):
            match = re.match(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", line)
            if not match:
                i += 1
                continue

            old_start = int(match.group(1))
            old_count = int(match.group(2)) if match.group(2) else 1
            new_start = int(match.group(3))
            new_count = int(match.group(4)) if match.group(4) else 1

            hunk = {
                "old_start": old_start,
                "old_count": old_count,
                "new_start": new_start,
                "new_count": new_count,
                "changes": [],
            }

            i += 1

            # Parse hunk content
            while i < len(lines) and not lines[i].startswith("@@"):
                hunk_line = lines[i]
                if not hunk_line:
                    i += 1
                    continue

                if hunk_line.startswith("-"):
                    hunk["changes"].append({"type": "remove", "content": hunk_line[1:]})
                elif hunk_line.startswith("+"):
                    hunk["changes"].append({"type": "add", "content": hunk_line[1:]})
                elif hunk_line.startswith(" "):
                    hunk["changes"].append({"type": "context", "content": hunk_line[1:]})
                elif hunk_line.startswith("\\"):
                    # No newline at end of file marker
                    pass
                else:
                    # Might be end of hunk
                    break

                i += 1

            hunks.append(hunk)
        else:
            i += 1

    return hunks


async def apply_patch_tool(
    params: dict[str, Any],
    root_dir: str | None = None,
) -> ToolResult:
    """Apply a unified diff patch to a file.

    Args:
        params: Tool parameters
        root_dir: Optional root directory for path validation

    Returns:
        ToolResult with patch status
    """
    path = read_string_param(params, "path", required=True)
    if not path:
        return error_result("path required")

    patch = read_string_param(params, "patch", required=True)
    if not patch:
        return error_result("patch required")

    encoding = read_string_param(params, "encoding") or "utf-8"

    # Resolve path
    if root_dir:
        resolved = resolve_safe_path(root_dir, path)
        if not resolved:
            return error_result("path escapes root directory")
        file_path = resolved
    else:
        file_path = os.path.expanduser(path)

    # Check file exists
    if not os.path.exists(file_path):
        return error_result(f"file not found: {path}")

    if not os.path.isfile(file_path):
        return error_result(f"not a file: {path}")

    # Read current content
    try:
        with open(file_path, encoding=encoding, errors="replace") as f:
            original_lines = f.readlines()
    except OSError as e:
        return error_result(f"cannot read file: {e}")

    # Parse patch
    hunks = _parse_unified_diff(patch)
    if not hunks:
        return error_result("no valid hunks found in patch")

    # Apply hunks (from bottom to top to preserve line numbers)
    result_lines = [line.rstrip("\n\r") for line in original_lines]
    hunks_applied = 0
    errors: list[str] = []

    # Sort hunks by old_start descending
    sorted_hunks = sorted(hunks, key=lambda h: h["old_start"], reverse=True)

    for hunk in sorted_hunks:
        old_start = hunk["old_start"] - 1  # Convert to 0-indexed

        # Extract expected old lines and new lines
        old_lines: list[str] = []
        new_lines: list[str] = []

        for change in hunk["changes"]:
            if change["type"] == "remove":
                old_lines.append(change["content"])
            elif change["type"] == "add":
                new_lines.append(change["content"])
            elif change["type"] == "context":
                old_lines.append(change["content"])
                new_lines.append(change["content"])

        # Verify context matches
        end_idx = old_start + len(old_lines)
        if end_idx > len(result_lines):
            errors.append(f"hunk at line {hunk['old_start']}: extends beyond file")
            continue

        actual_old = result_lines[old_start:end_idx]

        # Fuzzy match (allow whitespace differences)
        match = True
        for expected, actual in zip(old_lines, actual_old):
            if expected.strip() != actual.strip():
                match = False
                break

        if not match:
            errors.append(f"hunk at line {hunk['old_start']}: context mismatch")
            continue

        # Apply hunk
        result_lines = result_lines[:old_start] + new_lines + result_lines[end_idx:]
        hunks_applied += 1

    if hunks_applied == 0:
        return error_result(f"no hunks applied: {'; '.join(errors)}")

    # Write patched content
    try:
        with open(file_path, "w", encoding=encoding) as f:
            f.write("\n".join(result_lines))
            if result_lines:
                f.write("\n")  # Trailing newline
    except OSError as e:
        return error_result(f"cannot write file: {e}")

    result_data = {
        "path": path,
        "patched": True,
        "hunksTotal": len(hunks),
        "hunksApplied": hunks_applied,
    }

    if errors:
        result_data["errors"] = errors

    return json_result(result_data)


# =============================================================================
# Tool Registration Helpers
# =============================================================================


def create_read_tool() -> dict[str, Any]:
    """Create read tool definition for PydanticAI."""
    return {
        "name": "read",
        "label": "Read File",
        "description": (
            "Read file contents. "
            "Supports line ranges (from, lines). "
            "Output includes line numbers (cat -n format). "
            "Max 2000 lines per read, long lines truncated."
        ),
        "parameters": ReadParams.model_json_schema(),
    }


def create_write_tool() -> dict[str, Any]:
    """Create write tool definition for PydanticAI."""
    return {
        "name": "write",
        "label": "Write File",
        "description": (
            "Write content to a file. "
            "Can create parent directories (createDirs). "
            "Can append to existing files (append)."
        ),
        "parameters": WriteParams.model_json_schema(),
    }


def create_edit_tool() -> dict[str, Any]:
    """Create edit tool definition for PydanticAI."""
    return {
        "name": "edit",
        "label": "Edit File",
        "description": (
            "Edit a file with search and replace. "
            "Find 'old' text and replace with 'new'. "
            "Use 'all' to replace all occurrences."
        ),
        "parameters": EditParams.model_json_schema(),
    }


def create_apply_patch_tool() -> dict[str, Any]:
    """Create apply_patch tool definition for PydanticAI."""
    return {
        "name": "apply_patch",
        "label": "Apply Patch",
        "description": (
            "Apply a unified diff patch to a file. "
            "Patch format: unified diff (diff -u). "
            "Hunks are applied from bottom to preserve line numbers."
        ),
        "parameters": ApplyPatchParams.model_json_schema(),
    }
