"""Bash tool for executing shell commands."""

import asyncio
from typing import TYPE_CHECKING, Any

from loguru import logger

from lurkbot.tools.base import SessionType, Tool, ToolPolicy, ToolResult

if TYPE_CHECKING:
    from lurkbot.sandbox.manager import SandboxManager


class BashTool(Tool):
    """Tool for executing bash commands.

    This tool executes shell commands either:
    - Directly in a subprocess (MAIN sessions)
    - In a Docker sandbox (GROUP/TOPIC sessions)

    Sandbox execution provides resource limits, network isolation, and
    read-only filesystem for security in multi-user contexts.
    """

    def __init__(self, sandbox_manager: "SandboxManager | None" = None) -> None:
        """Initialize the bash tool.

        Args:
            sandbox_manager: Optional sandbox manager for containerized execution
        """
        policy = ToolPolicy(
            allowed_session_types={
                SessionType.MAIN,
                SessionType.GROUP,
                SessionType.TOPIC,
            },
            requires_approval=True,  # Requires user approval
            max_execution_time=30,  # 30 second timeout
        )
        super().__init__(
            name="bash",
            description="Execute bash commands in the workspace. Use this to run shell commands, scripts, and system utilities.",
            policy=policy,
        )
        # Lazy import to avoid circular dependency
        if sandbox_manager is None:
            from lurkbot.sandbox.manager import SandboxManager

            sandbox_manager = SandboxManager()
        self.sandbox_manager = sandbox_manager

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
            session_type: Session type (determines sandbox usage)

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

        # Determine if we should use sandbox
        use_sandbox = session_type in {SessionType.GROUP, SessionType.TOPIC}

        if use_sandbox:
            logger.debug(
                f"Using sandbox for {session_type.value} session: {command[:50]}..."
            )
            return await self._execute_in_sandbox(command, workspace)
        else:
            logger.debug(f"Direct execution for {session_type.value} session")
            return await self._execute_direct(command, workspace)

    async def _execute_in_sandbox(
        self, command: str, workspace: str
    ) -> ToolResult:
        """Execute command in Docker sandbox.

        Args:
            command: Command to execute
            workspace: Working directory

        Returns:
            ToolResult with sandbox execution results
        """
        try:
            # Get sandbox with workspace mount
            from lurkbot.sandbox.types import SandboxConfig

            config = SandboxConfig(
                workspace_path=workspace,
                workspace_readonly=False,
                timeout=self.policy.max_execution_time,
            )

            # Create sandbox instance
            from lurkbot.sandbox.docker import DockerSandbox

            sandbox = DockerSandbox(config)

            # Execute command in workspace
            result = sandbox.execute(f"cd /workspace && {command}")

            success = result.exit_code == 0
            if success:
                logger.info(
                    f"Sandbox command executed successfully (exit code: {result.exit_code})"
                )
            else:
                logger.warning(
                    f"Sandbox command failed (exit code: {result.exit_code})"
                )

            return ToolResult(
                success=success,
                output=result.stdout if result.stdout else None,
                error=result.stderr if result.stderr and not success else None,
                exit_code=result.exit_code,
            )

        except Exception as e:
            logger.exception("Sandbox execution failed with exception")
            return ToolResult(success=False, error=f"Sandbox execution error: {e}")

    async def _execute_direct(self, command: str, workspace: str) -> ToolResult:
        """Execute command directly in subprocess.

        Args:
            command: Command to execute
            workspace: Working directory

        Returns:
            ToolResult with execution results
        """
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
