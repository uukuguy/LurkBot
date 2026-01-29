"""Safe file system operations.

Ported from moltbot/src/infra/fs-safe.ts

This module provides secure file operations with protection against:
- Path traversal attacks (escaping root directory)
- Symlink attacks
- Race conditions (TOCTOU)
"""

from __future__ import annotations

import os
import stat
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import BinaryIO


class SafeOpenErrorCode(str, Enum):
    """Error codes for safe file open operations."""

    INVALID_PATH = "invalid-path"
    NOT_FOUND = "not-found"


class SafeOpenError(Exception):
    """Error raised during safe file operations."""

    def __init__(self, code: SafeOpenErrorCode, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass
class SafeOpenResult:
    """Result of a safe file open operation."""

    handle: BinaryIO
    real_path: str
    stat: os.stat_result


# Error codes that indicate file/directory not found
NOT_FOUND_CODES = frozenset(["ENOENT", "ENOTDIR"])


def _ensure_trailing_sep(value: str) -> str:
    """Ensure path ends with separator."""
    if value.endswith(os.sep):
        return value
    return value + os.sep


def _is_not_found_error(err: OSError) -> bool:
    """Check if error indicates file/directory not found."""
    import errno

    return err.errno in (errno.ENOENT, errno.ENOTDIR)


def _is_symlink_open_error(err: OSError) -> bool:
    """Check if error indicates symlink blocking."""
    import errno

    return err.errno in (errno.ELOOP, errno.EINVAL, getattr(errno, "ENOTSUP", 0))


async def open_file_within_root(
    root_dir: str,
    relative_path: str,
) -> SafeOpenResult:
    """Safely open a file within a root directory.

    This function provides multiple layers of protection:
    1. Path validation - ensures resolved path is within root
    2. Symlink protection - prevents symlink attacks via O_NOFOLLOW
    3. Inode verification - guards against TOCTOU race conditions

    Equivalent to moltbot openFileWithinRoot().

    Args:
        root_dir: The root directory (jail)
        relative_path: Path relative to root directory

    Returns:
        SafeOpenResult with file handle, real path, and stat info

    Raises:
        SafeOpenError: If path is invalid or file not found
    """
    # Resolve root directory to real path
    try:
        root_real = os.path.realpath(root_dir)
    except OSError as err:
        if _is_not_found_error(err):
            raise SafeOpenError(SafeOpenErrorCode.NOT_FOUND, "root dir not found") from err
        raise

    # Ensure root exists and is a directory
    if not os.path.isdir(root_real):
        raise SafeOpenError(SafeOpenErrorCode.NOT_FOUND, "root dir not found")

    root_with_sep = _ensure_trailing_sep(root_real)

    # Resolve the target path
    resolved = os.path.normpath(os.path.join(root_with_sep, relative_path))

    # Check if resolved path is within root
    if not resolved.startswith(root_with_sep) and resolved != root_real.rstrip(os.sep):
        raise SafeOpenError(SafeOpenErrorCode.INVALID_PATH, "path escapes root")

    # Check for symlink via lstat before opening
    try:
        lstat_result = os.lstat(resolved)
        if stat.S_ISLNK(lstat_result.st_mode):
            raise SafeOpenError(SafeOpenErrorCode.INVALID_PATH, "symlink not allowed")
    except OSError as err:
        if _is_not_found_error(err):
            raise SafeOpenError(SafeOpenErrorCode.NOT_FOUND, "file not found") from err
        raise

    # Try to open file with O_NOFOLLOW if available (Unix)
    # On Windows, we rely on lstat check above
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW

    try:
        fd = os.open(resolved, flags)
    except OSError as err:
        if _is_not_found_error(err):
            raise SafeOpenError(SafeOpenErrorCode.NOT_FOUND, "file not found") from err
        if _is_symlink_open_error(err):
            raise SafeOpenError(SafeOpenErrorCode.INVALID_PATH, "symlink open blocked") from err
        raise

    handle = None
    try:
        # Wrap fd in file object
        handle = os.fdopen(fd, "rb")

        # Get stat via file handle
        file_stat = os.fstat(handle.fileno())

        # Verify it's a regular file
        if not stat.S_ISREG(file_stat.st_mode):
            raise SafeOpenError(SafeOpenErrorCode.INVALID_PATH, "not a file")

        # Get real path and verify it's within root
        real_path = os.path.realpath(resolved)
        if not real_path.startswith(root_with_sep) and real_path != root_real.rstrip(os.sep):
            raise SafeOpenError(SafeOpenErrorCode.INVALID_PATH, "path escapes root")

        # Verify inode matches (TOCTOU protection)
        real_stat = os.stat(real_path)
        if file_stat.st_ino != real_stat.st_ino or file_stat.st_dev != real_stat.st_dev:
            raise SafeOpenError(SafeOpenErrorCode.INVALID_PATH, "path mismatch")

        return SafeOpenResult(
            handle=handle,
            real_path=real_path,
            stat=file_stat,
        )

    except Exception:
        if handle is not None:
            try:
                handle.close()
            except Exception:
                pass
        raise


def open_file_within_root_sync(
    root_dir: str,
    relative_path: str,
) -> SafeOpenResult:
    """Synchronous version of open_file_within_root.

    Args:
        root_dir: The root directory (jail)
        relative_path: Path relative to root directory

    Returns:
        SafeOpenResult with file handle, real path, and stat info

    Raises:
        SafeOpenError: If path is invalid or file not found
    """
    # Resolve root directory to real path
    try:
        root_real = os.path.realpath(root_dir)
    except OSError as err:
        if _is_not_found_error(err):
            raise SafeOpenError(SafeOpenErrorCode.NOT_FOUND, "root dir not found") from err
        raise

    # Ensure root exists and is a directory
    if not os.path.isdir(root_real):
        raise SafeOpenError(SafeOpenErrorCode.NOT_FOUND, "root dir not found")

    root_with_sep = _ensure_trailing_sep(root_real)

    # Resolve the target path
    resolved = os.path.normpath(os.path.join(root_with_sep, relative_path))

    # Check if resolved path is within root
    if not resolved.startswith(root_with_sep) and resolved != root_real.rstrip(os.sep):
        raise SafeOpenError(SafeOpenErrorCode.INVALID_PATH, "path escapes root")

    # Check for symlink via lstat before opening
    try:
        lstat_result = os.lstat(resolved)
        if stat.S_ISLNK(lstat_result.st_mode):
            raise SafeOpenError(SafeOpenErrorCode.INVALID_PATH, "symlink not allowed")
    except OSError as err:
        if _is_not_found_error(err):
            raise SafeOpenError(SafeOpenErrorCode.NOT_FOUND, "file not found") from err
        raise

    # Try to open file with O_NOFOLLOW if available (Unix)
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW

    try:
        fd = os.open(resolved, flags)
    except OSError as err:
        if _is_not_found_error(err):
            raise SafeOpenError(SafeOpenErrorCode.NOT_FOUND, "file not found") from err
        if _is_symlink_open_error(err):
            raise SafeOpenError(SafeOpenErrorCode.INVALID_PATH, "symlink open blocked") from err
        raise

    handle = None
    try:
        handle = os.fdopen(fd, "rb")
        file_stat = os.fstat(handle.fileno())

        if not stat.S_ISREG(file_stat.st_mode):
            raise SafeOpenError(SafeOpenErrorCode.INVALID_PATH, "not a file")

        real_path = os.path.realpath(resolved)
        if not real_path.startswith(root_with_sep) and real_path != root_real.rstrip(os.sep):
            raise SafeOpenError(SafeOpenErrorCode.INVALID_PATH, "path escapes root")

        real_stat = os.stat(real_path)
        if file_stat.st_ino != real_stat.st_ino or file_stat.st_dev != real_stat.st_dev:
            raise SafeOpenError(SafeOpenErrorCode.INVALID_PATH, "path mismatch")

        return SafeOpenResult(
            handle=handle,
            real_path=real_path,
            stat=file_stat,
        )

    except Exception:
        if handle is not None:
            try:
                handle.close()
            except Exception:
                pass
        raise


def is_path_within_root(root_dir: str, target_path: str) -> bool:
    """Check if a path is within a root directory.

    Does not open the file, just validates the path structure.

    Args:
        root_dir: The root directory
        target_path: Path to check (can be absolute or relative)

    Returns:
        True if target_path is within root_dir
    """
    try:
        root_real = os.path.realpath(root_dir)
        root_with_sep = _ensure_trailing_sep(root_real)

        # If target is relative, join with root
        if not os.path.isabs(target_path):
            resolved = os.path.normpath(os.path.join(root_with_sep, target_path))
        else:
            resolved = os.path.normpath(target_path)

        return resolved.startswith(root_with_sep) or resolved == root_real.rstrip(os.sep)
    except Exception:
        return False


def resolve_safe_path(root_dir: str, relative_path: str) -> str | None:
    """Resolve a relative path within root directory safely.

    Returns the resolved absolute path if valid, None otherwise.

    Args:
        root_dir: The root directory
        relative_path: Path relative to root

    Returns:
        Resolved absolute path or None if invalid
    """
    try:
        root_real = os.path.realpath(root_dir)
        root_with_sep = _ensure_trailing_sep(root_real)

        resolved = os.path.normpath(os.path.join(root_with_sep, relative_path))

        if not resolved.startswith(root_with_sep) and resolved != root_real.rstrip(os.sep):
            return None

        return resolved
    except Exception:
        return None
