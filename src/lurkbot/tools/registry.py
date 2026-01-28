"""Tool registry and policy management."""

from typing import Any

from loguru import logger

from lurkbot.tools.base import SessionType, Tool


class ToolRegistry:
    """Registry for tools with policy enforcement.

    The registry manages tool registration, discovery, and policy enforcement
    based on session types. It provides a centralized way to control which
    tools are available to different types of sessions.
    """

    def __init__(self) -> None:
        """Initialize the tool registry."""
        self._tools: dict[str, Tool] = {}
        logger.debug("Initialized tool registry")

    def register(self, tool: Tool) -> None:
        """Register a tool in the registry.

        Args:
            tool: Tool instance to register
        """
        self._tools[tool.name] = tool
        logger.info(
            f"Registered tool: {tool.name} "
            f"(allowed sessions: {[st.value for st in tool.policy.allowed_session_types]})"
        )

    def get(self, name: str) -> Tool | None:
        """Get a tool by name.

        Args:
            name: Name of the tool to retrieve

        Returns:
            Tool instance if found, None otherwise
        """
        return self._tools.get(name)

    def list_tools(self, session_type: SessionType | None = None) -> list[Tool]:
        """List all tools, optionally filtered by session type.

        Args:
            session_type: If provided, only return tools allowed for this session type

        Returns:
            List of tool instances
        """
        if session_type is None:
            return list(self._tools.values())

        return [
            tool
            for tool in self._tools.values()
            if session_type in tool.policy.allowed_session_types
        ]

    def check_policy(self, tool: Tool, session_type: SessionType) -> bool:
        """Check if tool execution is allowed for the given session type.

        Args:
            tool: Tool to check
            session_type: Session type to check against

        Returns:
            True if tool execution is allowed, False otherwise
        """
        allowed = session_type in tool.policy.allowed_session_types
        if not allowed:
            logger.warning(
                f"Tool {tool.name} not allowed for session type {session_type.value}"
            )
        return allowed

    def get_tool_schemas(self, session_type: SessionType) -> list[dict[str, Any]]:
        """Get schemas for all tools available to the given session type.

        This method returns tool schemas in the format expected by AI models
        (Claude, GPT) for tool use functionality.

        Args:
            session_type: Session type to get schemas for

        Returns:
            List of tool schemas (dictionaries with name, description, input_schema)
        """
        tools = self.list_tools(session_type)
        schemas = [tool.get_schema() for tool in tools]
        logger.debug(
            f"Generated {len(schemas)} tool schemas for session type {session_type.value}"
        )
        return schemas

    def __len__(self) -> int:
        """Return the number of registered tools.

        Returns:
            Number of tools in the registry
        """
        return len(self._tools)

    def __contains__(self, name: str) -> bool:
        """Check if a tool with the given name is registered.

        Args:
            name: Tool name to check

        Returns:
            True if tool is registered, False otherwise
        """
        return name in self._tools
