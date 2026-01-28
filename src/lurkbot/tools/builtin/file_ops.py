"""File operation tools."""

from pathlib import Path
from typing import Any

import aiofiles
from loguru import logger

from lurkbot.tools.base import SessionType, Tool, ToolPolicy, ToolResult


class ReadFileTool(Tool):
    """Tool for reading file contents.

    This tool reads the contents of a file in the workspace. It includes
    path traversal protection to ensure files outside the workspace cannot
    be accessed.
    """

    def __init__(self) -> None:
        """Initialize the read file tool."""
        policy = ToolPolicy(
            allowed_session_types={SessionType.MAIN, SessionType.DM},
            requires_approval=False,  # Reading is safe, no approval needed
        )
        super().__init__(
            name="read_file",
            description="Read the contents of a file. Use this to examine file contents, configuration files, logs, etc.",
            policy=policy,
        )

    async def execute(
        self,
        arguments: dict[str, Any],
        workspace: str,
        session_type: SessionType,  # noqa: ARG002
    ) -> ToolResult:
        """Read file contents.

        Args:
            arguments: Must contain 'path' key with relative path to file
            workspace: Working directory (base path)
            session_type: Session type (for policy checking)

        Returns:
            ToolResult with file contents or error
        """
        path = arguments.get("path")
        if not path:
            return ToolResult(success=False, error="Missing 'path' argument")

        if not isinstance(path, str):
            return ToolResult(success=False, error=f"Path must be a string, got {type(path)}")

        # Construct full path and resolve it
        workspace_path = Path(workspace).resolve()
        file_path = (workspace_path / path).resolve()

        # Security: Prevent path traversal
        try:
            file_path.relative_to(workspace_path)
        except ValueError:
            error_msg = f"Path '{path}' is outside workspace"
            logger.warning(f"Path traversal attempt blocked: {file_path}")
            return ToolResult(success=False, error=error_msg)

        # Check if file exists
        if not file_path.exists():
            return ToolResult(success=False, error=f"File not found: {path}")

        if not file_path.is_file():
            return ToolResult(success=False, error=f"Path is not a file: {path}")

        try:
            # Read file contents asynchronously
            async with aiofiles.open(file_path, encoding="utf-8") as f:
                content = await f.read()

            logger.info(f"Read file: {file_path} ({len(content)} bytes)")
            return ToolResult(success=True, output=content)

        except UnicodeDecodeError:
            return ToolResult(
                success=False, error=f"File '{path}' is not a text file (binary content)"
            )
        except PermissionError:
            return ToolResult(success=False, error=f"Permission denied: {path}")
        except Exception as e:
            logger.exception(f"Failed to read file: {file_path}")
            return ToolResult(success=False, error=f"Failed to read file: {e}")

    def get_schema(self) -> dict[str, Any]:
        """Get tool schema for AI models.

        Returns:
            JSON schema describing the tool's parameters
        """
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path to the file within the workspace (e.g., 'config.json', 'src/main.py')",
                    }
                },
                "required": ["path"],
            },
        }


class WriteFileTool(Tool):
    """Tool for writing file contents.

    This tool writes content to a file in the workspace. It includes path
    traversal protection and requires user approval for security. Parent
    directories are created automatically if they don't exist.
    """

    def __init__(self) -> None:
        """Initialize the write file tool."""
        policy = ToolPolicy(
            allowed_session_types={SessionType.MAIN},
            requires_approval=True,  # Writing needs approval
        )
        super().__init__(
            name="write_file",
            description="Write content to a file. Use this to create new files or overwrite existing ones.",
            policy=policy,
        )

    async def execute(
        self,
        arguments: dict[str, Any],
        workspace: str,
        session_type: SessionType,  # noqa: ARG002
    ) -> ToolResult:
        """Write content to a file.

        Args:
            arguments: Must contain 'path' and 'content' keys
            workspace: Working directory (base path)
            session_type: Session type (for policy checking)

        Returns:
            ToolResult indicating success or error
        """
        path = arguments.get("path")
        content = arguments.get("content")

        if not path:
            return ToolResult(success=False, error="Missing 'path' argument")
        if content is None:  # Allow empty string
            return ToolResult(success=False, error="Missing 'content' argument")

        if not isinstance(path, str):
            return ToolResult(success=False, error=f"Path must be a string, got {type(path)}")
        if not isinstance(content, str):
            return ToolResult(success=False, error=f"Content must be a string, got {type(content)}")

        # Construct full path and resolve it
        workspace_path = Path(workspace).resolve()
        file_path = (workspace_path / path).resolve()

        # Security: Prevent path traversal
        try:
            file_path.relative_to(workspace_path)
        except ValueError:
            error_msg = f"Path '{path}' is outside workspace"
            logger.warning(f"Path traversal attempt blocked: {file_path}")
            return ToolResult(success=False, error=error_msg)

        try:
            # Create parent directories if they don't exist
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Write file contents asynchronously
            async with aiofiles.open(file_path, "w", encoding="utf-8") as f:
                await f.write(content)

            logger.info(f"Wrote file: {file_path} ({len(content)} bytes)")
            return ToolResult(
                success=True, output=f"Successfully wrote {len(content)} bytes to {path}"
            )

        except PermissionError:
            return ToolResult(success=False, error=f"Permission denied: {path}")
        except Exception as e:
            logger.exception(f"Failed to write file: {file_path}")
            return ToolResult(success=False, error=f"Failed to write file: {e}")

    def get_schema(self) -> dict[str, Any]:
        """Get tool schema for AI models.

        Returns:
            JSON schema describing the tool's parameters
        """
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path to the file within the workspace (e.g., 'output.txt', 'data/results.json')",
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to write to the file",
                    },
                },
                "required": ["path", "content"],
            },
        }
