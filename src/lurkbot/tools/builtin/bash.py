"""Bash tool for executing shell commands."""

import asyncio
from typing import Any

from loguru import logger

from lurkbot.tools.base import SessionType, Tool, ToolPolicy, ToolResult


class BashTool(Tool):
    """Tool for executing bash commands.

    This tool executes shell commands in a subprocess. It supports timeout
    protection and working directory specification. For security, it's only
    allowed in MAIN sessions by default and requires user approval.
    """

    def __init__(self) -> None:
        """Initialize the bash tool."""
        policy = ToolPolicy(
            allowed_session_types={SessionType.MAIN},  # Only main sessions for now
            requires_approval=True,  # Requires user approval
            max_execution_time=30,  # 30 second timeout
        )
        super().__init__(
            name="bash",
            description="Execute bash commands in the workspace. Use this to run shell commands, scripts, and system utilities.",
            policy=policy,
        )

    async def execute(
        self,
        arguments: dict[str, Any],
        workspace: str,
        session_type: SessionType,
    ) -> ToolResult:
        """Execute a bash command.

        Args:
            arguments: Must contain 'command' key with the command to execute
            workspace: Working directory for command execution
            session_type: Session type (for policy checking)

        Returns:
            ToolResult with command output or error
        """
        command = arguments.get("command")
        if not command:
            return ToolResult(success=False, error="Missing 'command' argument")

        if not isinstance(command, str):
            return ToolResult(
                success=False, error=f"Command must be a string, got {type(command)}"
            )

        logger.info(f"Executing bash command: {command[:100]}...")

        try:
            # Create subprocess
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=workspace,
            )

            # Execute with timeout
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=self.policy.max_execution_time,
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()  # Clean up zombie process
                error_msg = (
                    f"Command timed out after {self.policy.max_execution_time} seconds"
                )
                logger.warning(error_msg)
                return ToolResult(success=False, error=error_msg)

            # Decode output
            output_str = stdout.decode("utf-8", errors="replace") if stdout else ""
            error_str = stderr.decode("utf-8", errors="replace") if stderr else ""
            exit_code = process.returncode or 0

            # Determine success
            success = exit_code == 0

            if success:
                logger.info(f"Command executed successfully (exit code: {exit_code})")
            else:
                logger.warning(f"Command failed (exit code: {exit_code})")

            return ToolResult(
                success=success,
                output=output_str if output_str else None,
                error=error_str if error_str and not success else None,
                exit_code=exit_code,
            )

        except Exception as e:
            logger.exception("Bash execution failed with exception")
            return ToolResult(success=False, error=f"Execution error: {e}")

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
                    "command": {
                        "type": "string",
                        "description": "The bash command to execute. Can include pipes, redirects, and other shell features.",
                    }
                },
                "required": ["command"],
            },
        }
