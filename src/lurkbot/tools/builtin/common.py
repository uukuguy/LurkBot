"""Common tool utilities.

Ported from moltbot/src/agents/tools/common.ts
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, TypeVar

from pydantic import BaseModel


# =============================================================================
# Tool Result Types
# =============================================================================


class ToolResultContentType(str, Enum):
    """Tool result content types."""

    TEXT = "text"
    IMAGE = "image"
    DOCUMENT = "document"


@dataclass
class ToolResultContent:
    """Single content item in a tool result."""

    type: ToolResultContentType
    text: str | None = None
    data: str | None = None  # Base64 encoded for images
    url: str | None = None
    mime_type: str | None = None


@dataclass
class ToolResult:
    """Standard tool result format.

    Matches moltbot AgentToolResult<TDetails>.
    """

    content: list[ToolResultContent] = field(default_factory=list)
    details: Any | None = None

    def to_text(self) -> str:
        """Get the text content of the result."""
        texts = [c.text for c in self.content if c.text]
        return "\n".join(texts)


# =============================================================================
# Result Helper Functions
# =============================================================================


def json_result(payload: Any) -> ToolResult:
    """Create a JSON text result.

    Equivalent to moltbot jsonResult().
    """
    return ToolResult(
        content=[
            ToolResultContent(
                type=ToolResultContentType.TEXT,
                text=json.dumps(payload, indent=2, ensure_ascii=False),
            )
        ],
        details=payload,
    )


def text_result(text: str, details: Any | None = None) -> ToolResult:
    """Create a plain text result."""
    return ToolResult(
        content=[
            ToolResultContent(
                type=ToolResultContentType.TEXT,
                text=text,
            )
        ],
        details=details,
    )


def error_result(message: str, details: dict[str, Any] | None = None) -> ToolResult:
    """Create an error result."""
    payload = {"error": message, **(details or {})}
    return json_result(payload)


def image_result(
    *,
    label: str,
    path: str,
    base64_data: str,
    mime_type: str,
    extra_text: str | None = None,
    details: dict[str, Any] | None = None,
) -> ToolResult:
    """Create an image result.

    Equivalent to moltbot imageResult().
    """
    content: list[ToolResultContent] = [
        ToolResultContent(
            type=ToolResultContentType.TEXT,
            text=extra_text or f"MEDIA:{path}",
        ),
        ToolResultContent(
            type=ToolResultContentType.IMAGE,
            data=base64_data,
            mime_type=mime_type,
        ),
    ]
    return ToolResult(
        content=content,
        details={"path": path, "label": label, **(details or {})},
    )


# =============================================================================
# Parameter Reading Utilities
# =============================================================================


class ParamError(ValueError):
    """Parameter validation error."""

    pass


def read_string_param(
    params: dict[str, Any],
    key: str,
    *,
    required: bool = False,
    trim: bool = True,
    label: str | None = None,
    allow_empty: bool = False,
) -> str | None:
    """Read and validate a string parameter.

    Equivalent to moltbot readStringParam().

    Args:
        params: Parameter dictionary
        key: Parameter key
        required: Whether the parameter is required
        trim: Whether to trim whitespace
        label: Label for error messages (defaults to key)
        allow_empty: Whether to allow empty strings

    Returns:
        The parameter value or None if not present

    Raises:
        ParamError: If required but missing or empty
    """
    label = label or key
    raw = params.get(key)

    if not isinstance(raw, str):
        if required:
            raise ParamError(f"{label} required")
        return None

    value = raw.strip() if trim else raw

    if not value and not allow_empty:
        if required:
            raise ParamError(f"{label} required")
        return None

    return value


def read_string_or_number_param(
    params: dict[str, Any],
    key: str,
    *,
    required: bool = False,
    label: str | None = None,
) -> str | None:
    """Read a parameter that can be string or number, returning as string.

    Equivalent to moltbot readStringOrNumberParam().
    """
    label = label or key
    raw = params.get(key)

    if isinstance(raw, int | float) and not isinstance(raw, bool):
        if not (raw != raw):  # Check for NaN
            return str(raw)

    if isinstance(raw, str):
        value = raw.strip()
        if value:
            return value

    if required:
        raise ParamError(f"{label} required")
    return None


def read_number_param(
    params: dict[str, Any],
    key: str,
    *,
    required: bool = False,
    label: str | None = None,
    integer: bool = False,
) -> int | float | None:
    """Read and validate a number parameter.

    Equivalent to moltbot readNumberParam().
    """
    label = label or key
    raw = params.get(key)
    value: float | None = None

    if isinstance(raw, int | float) and not isinstance(raw, bool):
        if raw == raw:  # Check for NaN
            value = float(raw)
    elif isinstance(raw, str):
        trimmed = raw.strip()
        if trimmed:
            try:
                value = float(trimmed)
            except ValueError:
                pass

    if value is None:
        if required:
            raise ParamError(f"{label} required")
        return None

    if integer:
        return int(value)
    return value


def read_bool_param(
    params: dict[str, Any],
    key: str,
    *,
    default: bool = False,
) -> bool:
    """Read a boolean parameter with default."""
    raw = params.get(key)
    if isinstance(raw, bool):
        return raw
    return default


def read_string_array_param(
    params: dict[str, Any],
    key: str,
    *,
    required: bool = False,
    label: str | None = None,
) -> list[str] | None:
    """Read and validate a string array parameter.

    Equivalent to moltbot readStringArrayParam().
    """
    label = label or key
    raw = params.get(key)

    if isinstance(raw, list):
        values = [
            entry.strip()
            for entry in raw
            if isinstance(entry, str) and entry.strip()
        ]
        if values:
            return values
        if required:
            raise ParamError(f"{label} required")
        return None

    if isinstance(raw, str):
        value = raw.strip()
        if value:
            return [value]
        if required:
            raise ParamError(f"{label} required")
        return None

    if required:
        raise ParamError(f"{label} required")
    return None


def read_dict_param(
    params: dict[str, Any],
    key: str,
    *,
    required: bool = False,
    label: str | None = None,
) -> dict[str, Any] | None:
    """Read and validate a dictionary parameter."""
    label = label or key
    raw = params.get(key)

    if isinstance(raw, dict):
        return raw

    if required:
        raise ParamError(f"{label} required")
    return None


# =============================================================================
# Action Gate (Permission Check)
# =============================================================================

T = TypeVar("T", bound=dict[str, bool | None])

ActionGate = Callable[[str, bool], bool]


def create_action_gate(actions: dict[str, bool | None] | None) -> ActionGate:
    """Create an action gate function for permission checking.

    Equivalent to moltbot createActionGate().

    Args:
        actions: Dictionary mapping action names to enabled status

    Returns:
        A function that checks if an action is allowed
    """

    def gate(key: str, default_value: bool = True) -> bool:
        if actions is None:
            return default_value
        value = actions.get(key)
        if value is None:
            return default_value
        return value is not False

    return gate


# =============================================================================
# Utility Functions
# =============================================================================


def clamp_number(
    value: int | float | None,
    default: int | float,
    min_val: int | float,
    max_val: int | float,
) -> int | float:
    """Clamp a number to a range with default.

    Equivalent to moltbot clampNumber().
    """
    if value is None or not isinstance(value, int | float):
        value = default
    return max(min_val, min(max_val, value))


def truncate_middle(text: str, max_len: int, ellipsis: str = "...") -> str:
    """Truncate text in the middle if too long."""
    if len(text) <= max_len:
        return text
    if max_len <= len(ellipsis):
        return ellipsis[:max_len]

    available = max_len - len(ellipsis)
    left_len = available // 2
    right_len = available - left_len

    return text[:left_len] + ellipsis + text[-right_len:]


def chunk_string(text: str, chunk_size: int) -> list[str]:
    """Split string into chunks of specified size."""
    return [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)]


def coerce_env(env: dict[str, Any] | None) -> dict[str, str]:
    """Coerce environment variable values to strings."""
    if not env:
        return {}
    return {
        k: str(v)
        for k, v in env.items()
        if v is not None and k
    }
