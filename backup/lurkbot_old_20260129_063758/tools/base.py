"""Base tool definitions for LurkBot."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from pydantic import BaseModel


class SessionType(str, Enum):
    """Session type for tool policy control.

    Attributes:
        MAIN: Direct user DM (fully trusted)
        GROUP: Group chat (requires sandbox)
        DM: Other user DM (partially trusted)
        TOPIC: Forum topic (requires sandbox)
    """

    MAIN = "main"
    GROUP = "group"
    DM = "dm"
    TOPIC = "topic"


class ToolApprovalStatus(str, Enum):
    """Tool execution approval status.

    Attributes:
        APPROVED: Tool execution is approved
        DENIED: Tool execution is denied
        NEEDS_APPROVAL: Tool requires user approval before execution
    """

    APPROVED = "approved"
    DENIED = "denied"
    NEEDS_APPROVAL = "needs_approval"


@dataclass
class ToolPolicy:
    """Tool execution policy.

    Attributes:
        allowed_session_types: Set of session types where this tool is allowed
        requires_approval: Whether user approval is required before execution
        sandbox_required: Whether execution must happen in sandbox
        max_execution_time: Maximum execution time in seconds
    """

    allowed_session_types: set[SessionType] = field(default_factory=lambda: {SessionType.MAIN})
    requires_approval: bool = False
    sandbox_required: bool = False
    max_execution_time: int = 30  # seconds


class ToolInput(BaseModel):
    """Tool execution input.

    Attributes:
        name: Name of the tool to execute
        arguments: Tool-specific arguments
    """

    name: str
    arguments: dict[str, Any]


class ToolResult(BaseModel):
    """Tool execution result.

    Attributes:
        success: Whether the tool execution was successful
        output: Standard output from the tool (if any)
        error: Error message (if failed)
        exit_code: Exit code (for command-line tools)
    """

    success: bool
    output: str | None = None
    error: str | None = None
    exit_code: int | None = None


class Tool(ABC):
    """Abstract base class for tools.

    All tools must inherit from this class and implement the required methods.
    """

    def __init__(self, name: str, description: str, policy: ToolPolicy | None = None):
        """Initialize the tool.

        Args:
            name: Tool name (used for registration and invocation)
            description: Human-readable description of what the tool does
            policy: Tool execution policy (defaults to main-only, no approval)
        """
        self.name = name
        self.description = description
        self.policy = policy or ToolPolicy()

    @abstractmethod
    async def execute(
        self,
        arguments: dict[str, Any],
        workspace: str,
        session_type: SessionType,
    ) -> ToolResult:
        """Execute the tool.

        Args:
            arguments: Tool-specific arguments
            workspace: Working directory path for tool execution
            session_type: Session type for policy enforcement

        Returns:
            Tool execution result containing success status and output/error
        """
        ...

    @abstractmethod
    def get_schema(self) -> dict[str, Any]:
        """Get tool schema for AI model.

        Returns JSON schema describing tool name, description, and parameters
        in the format expected by Claude/GPT tool use APIs.

        Returns:
            Dictionary with 'name', 'description', and 'input_schema' keys
        """
        ...
