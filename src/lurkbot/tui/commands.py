"""
TUI 命令处理器

对标 MoltBot src/tui/tui-command-handlers.ts

处理 TUI 命令如 /help, /status, /agent 等
"""

import asyncio
import shlex
from dataclasses import dataclass
from typing import Any, Callable, Awaitable

from loguru import logger

from .types import (
    TuiState,
    TuiCommand,
    TuiCommandResult,
    ThinkingLevel,
)
from .gateway_chat import GatewayChat


@dataclass
class CommandDefinition:
    """命令定义"""

    name: str
    aliases: list[str]
    description: str
    usage: str
    handler: Callable[[TuiState, list[str]], Awaitable[TuiCommandResult]]


class CommandHandler:
    """
    TUI 命令处理器

    对标 MoltBot tui-command-handlers.ts

    支持的命令:
    - /help - 显示帮助
    - /status - 网关状态
    - /agent [id] - 切换 Agent
    - /model [ref] - 设置模型
    - /think <level> - 设置 thinking 级别
    - /sessions - 列出会话
    - /new - 重置会话
    - /abort - 中止运行
    - !command - 执行 bash 命令
    """

    def __init__(self, gateway: GatewayChat | None = None) -> None:
        self.gateway = gateway
        self._commands: dict[str, CommandDefinition] = {}
        self._register_builtin_commands()

    def _register_builtin_commands(self) -> None:
        """注册内置命令"""
        commands = [
            CommandDefinition(
                name="/help",
                aliases=["/h", "/?"],
                description="Display available commands",
                usage="/help [command]",
                handler=self._handle_help,
            ),
            CommandDefinition(
                name="/status",
                aliases=["/stat"],
                description="Show gateway status",
                usage="/status",
                handler=self._handle_status,
            ),
            CommandDefinition(
                name="/agent",
                aliases=["/a"],
                description="Switch or list agents",
                usage="/agent [agent_id]",
                handler=self._handle_agent,
            ),
            CommandDefinition(
                name="/model",
                aliases=["/m"],
                description="Set the model",
                usage="/model [model_ref]",
                handler=self._handle_model,
            ),
            CommandDefinition(
                name="/think",
                aliases=["/t"],
                description="Set thinking level",
                usage="/think <off|low|medium|high>",
                handler=self._handle_think,
            ),
            CommandDefinition(
                name="/sessions",
                aliases=["/sess"],
                description="List sessions",
                usage="/sessions",
                handler=self._handle_sessions,
            ),
            CommandDefinition(
                name="/new",
                aliases=["/reset"],
                description="Start a new session",
                usage="/new",
                handler=self._handle_new,
            ),
            CommandDefinition(
                name="/abort",
                aliases=["/stop"],
                description="Abort current run",
                usage="/abort",
                handler=self._handle_abort,
            ),
            CommandDefinition(
                name="/clear",
                aliases=["/cls"],
                description="Clear chat display",
                usage="/clear",
                handler=self._handle_clear,
            ),
            CommandDefinition(
                name="/tools",
                aliases=[],
                description="Toggle tool details display",
                usage="/tools",
                handler=self._handle_tools,
            ),
            CommandDefinition(
                name="/exit",
                aliases=["/quit", "/q"],
                description="Exit TUI",
                usage="/exit",
                handler=self._handle_exit,
            ),
        ]

        for cmd in commands:
            self._commands[cmd.name] = cmd
            for alias in cmd.aliases:
                self._commands[alias] = cmd

    def is_command(self, text: str) -> bool:
        """检查是否是命令"""
        text = text.strip()
        return text.startswith("/") or text.startswith("!")

    def parse_command(self, text: str) -> tuple[str, list[str]]:
        """
        解析命令

        Args:
            text: 命令文本

        Returns:
            (命令名, 参数列表)
        """
        text = text.strip()

        # Bash 命令
        if text.startswith("!"):
            return "!", [text[1:].strip()]

        # 普通命令
        try:
            parts = shlex.split(text)
        except ValueError:
            parts = text.split()

        if not parts:
            return "", []

        cmd = parts[0].lower()
        args = parts[1:]

        return cmd, args

    async def execute(self, text: str, state: TuiState) -> TuiCommandResult:
        """
        执行命令

        Args:
            text: 命令文本
            state: TUI 状态

        Returns:
            命令结果
        """
        cmd, args = self.parse_command(text)

        if not cmd:
            return TuiCommandResult(success=False, message="Empty command")

        # Bash 命令
        if cmd == "!":
            return await self._handle_bash(state, args)

        # 查找命令
        if cmd not in self._commands:
            return TuiCommandResult(
                success=False,
                message=f"Unknown command: {cmd}\nType /help for available commands",
            )

        # 执行命令
        try:
            definition = self._commands[cmd]
            return await definition.handler(state, args)
        except Exception as e:
            logger.error(f"Command error: {e}")
            return TuiCommandResult(success=False, message=f"Error: {e}")

    def get_commands(self) -> list[TuiCommand]:
        """获取所有命令"""
        seen: set[str] = set()
        result: list[TuiCommand] = []

        for name, definition in self._commands.items():
            if name in seen or not name.startswith("/"):
                continue
            seen.add(name)
            result.append(
                TuiCommand(
                    name=definition.name,
                    aliases=definition.aliases,
                    description=definition.description,
                    usage=definition.usage,
                )
            )

        return sorted(result, key=lambda c: c.name)

    # ============ 命令处理器 ============

    async def _handle_help(
        self,
        state: TuiState,
        args: list[str],
    ) -> TuiCommandResult:
        """处理 /help 命令"""
        if args:
            # 显示特定命令的帮助
            cmd_name = args[0]
            if not cmd_name.startswith("/"):
                cmd_name = "/" + cmd_name

            if cmd_name in self._commands:
                definition = self._commands[cmd_name]
                help_text = (
                    f"Command: {definition.name}\n"
                    f"Aliases: {', '.join(definition.aliases) or 'none'}\n"
                    f"Description: {definition.description}\n"
                    f"Usage: {definition.usage}"
                )
                return TuiCommandResult(success=True, message=help_text)
            else:
                return TuiCommandResult(
                    success=False,
                    message=f"Unknown command: {cmd_name}",
                )

        # 显示所有命令
        commands = self.get_commands()
        lines = ["Available commands:", ""]
        for cmd in commands:
            aliases_str = f" ({', '.join(cmd.aliases)})" if cmd.aliases else ""
            lines.append(f"  {cmd.name}{aliases_str}")
            lines.append(f"    {cmd.description}")
        lines.append("")
        lines.append("Type /help <command> for detailed help")
        lines.append("Use !command to execute bash commands")

        return TuiCommandResult(success=True, message="\n".join(lines))

    async def _handle_status(
        self,
        state: TuiState,
        args: list[str],
    ) -> TuiCommandResult:
        """处理 /status 命令"""
        lines = ["Gateway Status:", ""]

        # 连接状态
        if state.is_connected:
            lines.append("  Connection: ✓ Connected")
        else:
            lines.append("  Connection: ✗ Disconnected")

        lines.append(f"  Status: {state.connection_status}")
        lines.append(f"  Activity: {state.activity_status.value}")
        lines.append("")

        # Agent 和 Session
        lines.append(f"  Agent: {state.current_agent_id}")
        lines.append(f"  Session: {state.current_session_key or 'none'}")

        # 模型
        if state.current_model:
            lines.append(f"  Model: {state.current_model}")

        # Thinking
        lines.append(f"  Thinking: {state.thinking_level.value}")

        # 如果有 Gateway 连接，获取详细状态
        if self.gateway and self.gateway.connected:
            try:
                gateway_status = await self.gateway.get_status()
                if gateway_status:
                    lines.append("")
                    lines.append("Gateway Info:")
                    for key, value in gateway_status.items():
                        lines.append(f"  {key}: {value}")
            except Exception as e:
                lines.append(f"  (Failed to get gateway status: {e})")

        return TuiCommandResult(success=True, message="\n".join(lines))

    async def _handle_agent(
        self,
        state: TuiState,
        args: list[str],
    ) -> TuiCommandResult:
        """处理 /agent 命令"""
        if not args:
            # 显示当前 Agent
            return TuiCommandResult(
                success=True,
                message=f"Current agent: {state.current_agent_id}\n"
                f"Default agent: {state.agent_default_id}\n\n"
                f"Usage: /agent <agent_id> to switch",
            )

        # 切换 Agent
        new_agent_id = args[0]
        old_agent_id = state.current_agent_id
        state.current_agent_id = new_agent_id

        return TuiCommandResult(
            success=True,
            message=f"Switched agent: {old_agent_id} → {new_agent_id}",
        )

    async def _handle_model(
        self,
        state: TuiState,
        args: list[str],
    ) -> TuiCommandResult:
        """处理 /model 命令"""
        if not args:
            current = state.current_model or "default"
            return TuiCommandResult(
                success=True,
                message=f"Current model: {current}\n\n"
                f"Usage: /model <model_ref> to change\n"
                f"Examples:\n"
                f"  /model claude-3-opus\n"
                f"  /model gpt-4\n"
                f"  /model default",
            )

        # 设置模型
        new_model = args[0]
        if new_model.lower() == "default":
            state.current_model = None
            return TuiCommandResult(
                success=True,
                message="Model reset to default",
            )

        old_model = state.current_model or "default"
        state.current_model = new_model

        return TuiCommandResult(
            success=True,
            message=f"Model changed: {old_model} → {new_model}",
        )

    async def _handle_think(
        self,
        state: TuiState,
        args: list[str],
    ) -> TuiCommandResult:
        """处理 /think 命令"""
        valid_levels = ["off", "low", "medium", "high"]

        if not args:
            return TuiCommandResult(
                success=True,
                message=f"Current thinking level: {state.thinking_level.value}\n\n"
                f"Usage: /think <{' | '.join(valid_levels)}>",
            )

        level = args[0].lower()
        if level not in valid_levels:
            return TuiCommandResult(
                success=False,
                message=f"Invalid level: {level}\n"
                f"Valid levels: {', '.join(valid_levels)}",
            )

        old_level = state.thinking_level.value
        state.thinking_level = ThinkingLevel(level)
        state.show_thinking = level != "off"

        return TuiCommandResult(
            success=True,
            message=f"Thinking level: {old_level} → {level}",
        )

    async def _handle_sessions(
        self,
        state: TuiState,
        args: list[str],
    ) -> TuiCommandResult:
        """处理 /sessions 命令"""
        if not self.gateway or not self.gateway.connected:
            return TuiCommandResult(
                success=False,
                message="Not connected to gateway",
            )

        try:
            sessions = await self.gateway.list_sessions(state.current_agent_id)

            if not sessions:
                return TuiCommandResult(
                    success=True,
                    message="No sessions found",
                )

            lines = [f"Sessions for agent '{state.current_agent_id}':", ""]
            for session in sessions:
                key = session.get("key", "unknown")
                session_type = session.get("type", "unknown")
                msg_count = session.get("message_count", 0)
                marker = " ←" if key == state.current_session_key else ""
                lines.append(f"  {key} [{session_type}] ({msg_count} messages){marker}")

            return TuiCommandResult(
                success=True,
                message="\n".join(lines),
                data=sessions,
            )

        except Exception as e:
            return TuiCommandResult(
                success=False,
                message=f"Failed to list sessions: {e}",
            )

    async def _handle_new(
        self,
        state: TuiState,
        args: list[str],
    ) -> TuiCommandResult:
        """处理 /new 命令"""
        from uuid import uuid4

        old_key = state.current_session_key
        new_key = f"tui:{uuid4().hex[:8]}"
        state.current_session_key = new_key

        return TuiCommandResult(
            success=True,
            message=f"New session created: {new_key}\n"
            f"Previous session: {old_key or 'none'}",
        )

    async def _handle_abort(
        self,
        state: TuiState,
        args: list[str],
    ) -> TuiCommandResult:
        """处理 /abort 命令"""
        if not state.active_chat_run_id:
            return TuiCommandResult(
                success=False,
                message="No active run to abort",
            )

        if self.gateway and self.gateway.connected:
            try:
                await self.gateway.abort_run(state.active_chat_run_id)
                run_id = state.active_chat_run_id
                state.active_chat_run_id = None
                return TuiCommandResult(
                    success=True,
                    message=f"Aborted run: {run_id}",
                )
            except Exception as e:
                return TuiCommandResult(
                    success=False,
                    message=f"Failed to abort: {e}",
                )
        else:
            state.active_chat_run_id = None
            return TuiCommandResult(
                success=True,
                message="Run marked as aborted (not connected)",
            )

    async def _handle_clear(
        self,
        state: TuiState,
        args: list[str],
    ) -> TuiCommandResult:
        """处理 /clear 命令"""
        # 返回特殊标记，让 UI 清除显示
        return TuiCommandResult(
            success=True,
            message="",
            data={"action": "clear"},
        )

    async def _handle_tools(
        self,
        state: TuiState,
        args: list[str],
    ) -> TuiCommandResult:
        """处理 /tools 命令"""
        state.tools_expanded = not state.tools_expanded
        status = "expanded" if state.tools_expanded else "collapsed"
        return TuiCommandResult(
            success=True,
            message=f"Tool details: {status}",
        )

    async def _handle_exit(
        self,
        state: TuiState,
        args: list[str],
    ) -> TuiCommandResult:
        """处理 /exit 命令"""
        return TuiCommandResult(
            success=True,
            message="Exiting...",
            data={"action": "exit"},
        )

    async def _handle_bash(
        self,
        state: TuiState,
        args: list[str],
    ) -> TuiCommandResult:
        """处理 ! 命令（执行 bash）"""
        if not args or not args[0]:
            return TuiCommandResult(
                success=False,
                message="Usage: !<command>\nExample: !ls -la",
            )

        command = args[0]

        try:
            # 执行命令
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=30.0,
            )

            output_parts: list[str] = []

            if stdout:
                output_parts.append(stdout.decode("utf-8", errors="replace"))

            if stderr:
                stderr_text = stderr.decode("utf-8", errors="replace")
                output_parts.append(f"[stderr]\n{stderr_text}")

            output = "\n".join(output_parts) if output_parts else "(no output)"

            return TuiCommandResult(
                success=process.returncode == 0,
                message=f"$ {command}\n\n{output}",
                data={"returncode": process.returncode},
            )

        except asyncio.TimeoutError:
            return TuiCommandResult(
                success=False,
                message=f"Command timed out: {command}",
            )
        except Exception as e:
            return TuiCommandResult(
                success=False,
                message=f"Command failed: {e}",
            )
