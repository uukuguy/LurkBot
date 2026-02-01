"""Agent runtime types and data classes.

This module defines the core data structures for the LurkBot agent runtime,
closely following MoltBot's EmbeddedRunAttemptParams and related types.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Literal


class SessionType(str, Enum):
    """Session type enumeration.

    Matches MoltBot session types.
    """

    MAIN = "main"
    GROUP = "group"
    DM = "dm"
    TOPIC = "topic"
    SUBAGENT = "subagent"


class ThinkLevel(str, Enum):
    """Thinking level for extended reasoning.

    Matches MoltBot ThinkLevel.
    """

    OFF = "off"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class VerboseLevel(str, Enum):
    """Verbose output level.

    Matches MoltBot VerboseLevel.
    """

    OFF = "off"
    LOW = "low"
    HIGH = "high"


class PromptMode(str, Enum):
    """System prompt mode.

    Matches MoltBot prompt mode options.
    """

    FULL = "full"
    MINIMAL = "minimal"
    NONE = "none"


class ToolResultFormat(str, Enum):
    """Tool result format for output.

    Matches MoltBot toolResultFormat.
    """

    MARKDOWN = "markdown"
    PLAIN = "plain"


@dataclass
class AgentContext:
    """Agent execution context.

    This is the Python equivalent of MoltBot's EmbeddedRunAttemptParams,
    containing all the context needed for an agent run.
    """

    # Session identification
    session_id: str
    session_key: str | None = None
    session_type: SessionType = SessionType.MAIN

    # Workspace and agent configuration
    workspace_dir: str = "."
    agent_dir: str | None = None
    session_file: str | None = None

    # Channel and messaging context
    message_channel: str | None = None
    message_provider: str | None = None
    agent_account_id: str | None = None
    message_to: str | None = None
    message_thread_id: str | None = None

    # Group context for tool policy resolution
    group_id: str | None = None
    group_channel: str | None = None
    group_space: str | None = None

    # Subagent context
    spawned_by: str | None = None  # Parent session key
    is_subagent: bool = False

    # Sender information
    sender_id: str | None = None
    sender_name: str | None = None
    sender_username: str | None = None

    # Model configuration
    provider: str = "anthropic"
    model_id: str = "claude-sonnet-4-20250514"
    think_level: ThinkLevel = ThinkLevel.MEDIUM
    verbose_level: VerboseLevel = VerboseLevel.OFF
    prompt_mode: PromptMode = PromptMode.FULL

    # Tool configuration
    tool_result_format: ToolResultFormat = ToolResultFormat.MARKDOWN
    disable_tools: bool = False
    sandbox_enabled: bool = False

    # Execution configuration
    timeout_ms: int = 120_000  # 2 minutes default
    run_id: str | None = None

    # Auth profile
    auth_profile_id: str | None = None

    # Owner configuration (for elevated commands)
    owner_numbers: list[str] = field(default_factory=list)

    # Extra system prompt injection
    extra_system_prompt: str | None = None

    # Tenant context (for multi-tenant support)
    tenant_id: str | None = None


@dataclass
class AgentRunResult:
    """Result of an agent run.

    Matches MoltBot's EmbeddedRunAttemptResult structure.
    """

    # Status flags
    aborted: bool = False
    timed_out: bool = False
    prompt_error: Exception | None = None

    # Session info
    session_id_used: str = ""

    # Output
    assistant_texts: list[str] = field(default_factory=list)
    messages_snapshot: list[dict[str, Any]] = field(default_factory=list)

    # Tool usage
    tool_metas: list[dict[str, Any]] = field(default_factory=list)
    last_tool_error: dict[str, Any] | None = None

    # Messaging tool tracking
    did_send_via_messaging_tool: bool = False
    messaging_tool_sent_texts: list[str] = field(default_factory=list)

    # Deferred tool requests (for human-in-the-loop)
    deferred_requests: Any | None = None  # DeferredToolRequests from PydanticAI

    @property
    def has_deferred_requests(self) -> bool:
        """Check if there are pending tool approvals."""
        return self.deferred_requests is not None


@dataclass
class StreamEvent:
    """Event emitted during agent streaming.

    Used for real-time updates to the UI.
    """

    event_type: Literal[
        "partial_reply",
        "assistant_start",
        "block_reply",
        "reasoning_stream",
        "tool_result",
        "agent_event",
    ]
    data: dict[str, Any] = field(default_factory=dict)


# Session key format constants (from MoltBot)
SESSION_KEY_SEPARATOR = ":"


def build_session_key(
    agent_id: str,
    session_type: SessionType,
    channel: str | None = None,
    group_id: str | None = None,
    thread_id: str | None = None,
    dm_partner: str | None = None,
) -> str:
    """Build a session key following MoltBot's format.

    Format patterns:
    - main: agent:{id}:main
    - group: agent:{id}:group:{channel}:{group_id}
    - topic: agent:{id}:topic:{channel}:{group_id}:{thread_id}
    - dm: agent:{id}:dm:{channel}:{partner_id}
    - subagent: agent:{id}:subagent:{parent_session_key}

    Args:
        agent_id: The agent identifier
        session_type: Type of session
        channel: Channel name (e.g., discord, telegram)
        group_id: Group/guild identifier
        thread_id: Thread identifier for topic sessions
        dm_partner: Partner ID for DM sessions

    Returns:
        Formatted session key string
    """
    parts = ["agent", agent_id]

    if session_type == SessionType.MAIN:
        parts.append("main")
    elif session_type == SessionType.GROUP:
        if not channel or not group_id:
            raise ValueError("Group session requires channel and group_id")
        parts.extend(["group", channel, group_id])
    elif session_type == SessionType.TOPIC:
        if not channel or not group_id or not thread_id:
            raise ValueError("Topic session requires channel, group_id, and thread_id")
        parts.extend(["topic", channel, group_id, thread_id])
    elif session_type == SessionType.DM:
        if not channel or not dm_partner:
            raise ValueError("DM session requires channel and dm_partner")
        parts.extend(["dm", channel, dm_partner])
    elif session_type == SessionType.SUBAGENT:
        # Subagent keys are handled differently - they include parent session
        parts.append("subagent")

    return SESSION_KEY_SEPARATOR.join(parts)


def parse_session_key(session_key: str) -> dict[str, Any]:
    """Parse a session key into its components.

    Args:
        session_key: The session key to parse

    Returns:
        Dictionary with parsed components
    """
    parts = session_key.split(SESSION_KEY_SEPARATOR)

    if len(parts) < 3 or parts[0] != "agent":
        raise ValueError(f"Invalid session key format: {session_key}")

    result: dict[str, Any] = {
        "agent_id": parts[1],
        "session_type": parts[2],
    }

    if parts[2] == "main":
        result["session_type"] = SessionType.MAIN
    elif parts[2] == "group" and len(parts) >= 5:
        result["session_type"] = SessionType.GROUP
        result["channel"] = parts[3]
        result["group_id"] = parts[4]
    elif parts[2] == "topic" and len(parts) >= 6:
        result["session_type"] = SessionType.TOPIC
        result["channel"] = parts[3]
        result["group_id"] = parts[4]
        result["thread_id"] = parts[5]
    elif parts[2] == "dm" and len(parts) >= 5:
        result["session_type"] = SessionType.DM
        result["channel"] = parts[3]
        result["dm_partner"] = parts[4]
    elif parts[2] == "subagent":
        result["session_type"] = SessionType.SUBAGENT

    return result
