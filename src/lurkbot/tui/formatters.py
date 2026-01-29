"""
TUI 消息格式化器

对标 MoltBot src/tui/tui-formatters.ts

提供消息、工具、状态的富文本格式化
"""

from datetime import datetime
from typing import Any

from rich.console import Console, Group
from rich.markdown import Markdown
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

from .types import (
    ActivityStatus,
    ChatMessage,
    MessageRole,
    ThinkingLevel,
    ToolCallDisplay,
    TuiState,
    TuiTheme,
    DEFAULT_THEME,
)


class TuiFormatter:
    """
    TUI 消息格式化器

    对标 MoltBot tui-formatters.ts
    """

    def __init__(self, theme: TuiTheme | None = None) -> None:
        self.theme = theme or DEFAULT_THEME
        self.console = Console()

    def format_message(
        self,
        message: ChatMessage,
        show_thinking: bool = False,
        show_timestamps: bool = False,
    ) -> Panel:
        """
        格式化聊天消息

        Args:
            message: 聊天消息
            show_thinking: 是否显示 thinking
            show_timestamps: 是否显示时间戳

        Returns:
            Rich Panel
        """
        content_parts: list[Any] = []

        # 时间戳
        if show_timestamps:
            ts = message.timestamp.strftime("%H:%M:%S")
            content_parts.append(Text(f"[{ts}] ", style="dim"))

        # Thinking 部分
        if show_thinking and message.thinking:
            thinking_panel = Panel(
                Text(message.thinking, style=self.theme.thinking),
                title="[dim]Thinking[/dim]",
                border_style="dim",
                padding=(0, 1),
            )
            content_parts.append(thinking_panel)
            content_parts.append(Text("\n"))

        # 工具调用部分
        if message.tool_calls:
            for tc in message.tool_calls:
                tc_display = self.format_tool_call(
                    ToolCallDisplay(
                        id=tc.get("id", ""),
                        name=tc.get("name", ""),
                        arguments=tc.get("arguments", {}),
                        status=tc.get("status", "completed"),
                        result=tc.get("result"),
                    )
                )
                content_parts.append(tc_display)
                content_parts.append(Text("\n"))

        # 消息内容
        if message.content:
            # 尝试渲染为 Markdown
            try:
                md = Markdown(message.content)
                content_parts.append(md)
            except Exception:
                content_parts.append(Text(message.content))

        # 确定样式
        if message.role == MessageRole.USER:
            title = "You"
            border_style = self.theme.user_message
        elif message.role == MessageRole.ASSISTANT:
            title = "Assistant"
            border_style = self.theme.assistant_message
        elif message.role == MessageRole.SYSTEM:
            title = "System"
            border_style = self.theme.system_message
        else:
            title = "Tool"
            border_style = self.theme.tool_name

        # 流式标记
        if message.is_streaming:
            title += " ●"
            border_style = self.theme.streaming

        return Panel(
            Group(*content_parts) if len(content_parts) > 1 else (content_parts[0] if content_parts else Text("")),
            title=f"[bold]{title}[/bold]",
            border_style=border_style,
            padding=(0, 1),
        )

    def format_tool_call(
        self,
        tool_call: ToolCallDisplay,
        expanded: bool = False,
    ) -> Panel:
        """
        格式化工具调用

        Args:
            tool_call: 工具调用显示对象
            expanded: 是否展开详情

        Returns:
            Rich Panel
        """
        parts: list[Any] = []

        # 状态图标
        if tool_call.status == "pending":
            status_icon = "⏳"
            status_style = "yellow"
        elif tool_call.status == "running":
            status_icon = "⚙️"
            status_style = self.theme.tool_running
        elif tool_call.status == "completed":
            status_icon = "✓"
            status_style = self.theme.tool_success
        else:  # failed
            status_icon = "✗"
            status_style = self.theme.tool_error

        # 标题行
        title_text = Text()
        title_text.append(f"{status_icon} ", style=status_style)
        title_text.append(tool_call.name, style=f"bold {self.theme.tool_name}")

        parts.append(title_text)

        # 参数（展开时显示）
        if expanded and tool_call.arguments:
            import json

            args_str = json.dumps(tool_call.arguments, indent=2, ensure_ascii=False)
            args_syntax = Syntax(args_str, "json", theme="monokai", line_numbers=False)
            parts.append(Text("\nArguments:", style="dim"))
            parts.append(args_syntax)

        # 结果（展开时显示）
        if expanded and tool_call.result is not None:
            result_str = str(tool_call.result)
            if len(result_str) > 500:
                result_str = result_str[:500] + "..."
            parts.append(Text("\nResult:", style="dim"))
            parts.append(Text(result_str, style="green"))

        # 错误
        if tool_call.error:
            parts.append(Text(f"\nError: {tool_call.error}", style=self.theme.tool_error))

        return Panel(
            Group(*parts),
            border_style="dim",
            padding=(0, 1),
        )

    def format_status_bar(self, state: TuiState) -> Text:
        """
        格式化状态栏

        Args:
            state: TUI 状态

        Returns:
            Rich Text
        """
        text = Text()

        # 连接状态
        if state.is_connected:
            text.append("● ", style=self.theme.connected)
            text.append("Connected", style=self.theme.connected)
        else:
            text.append("○ ", style=self.theme.disconnected)
            text.append("Disconnected", style=self.theme.disconnected)

        text.append(" | ")

        # Agent
        text.append(f"Agent: ", style="dim")
        text.append(state.current_agent_id, style="bold")

        text.append(" | ")

        # Session
        session_display = state.current_session_key or "none"
        if len(session_display) > 20:
            session_display = session_display[:17] + "..."
        text.append(f"Session: ", style="dim")
        text.append(session_display)

        text.append(" | ")

        # 活动状态
        if state.activity_status == ActivityStatus.IDLE:
            text.append("Idle", style="dim")
        elif state.activity_status == ActivityStatus.SENDING:
            text.append("Sending...", style="yellow")
        elif state.activity_status == ActivityStatus.WAITING:
            text.append("Waiting...", style="cyan")
        elif state.activity_status == ActivityStatus.STREAMING:
            text.append("Streaming...", style=self.theme.streaming)

        # Model
        if state.current_model:
            text.append(" | ")
            text.append(f"Model: ", style="dim")
            text.append(state.current_model, style="magenta")

        # Thinking level
        if state.thinking_level != ThinkingLevel.OFF:
            text.append(" | ")
            text.append(f"Think: ", style="dim")
            text.append(state.thinking_level.value, style="cyan")

        return text

    def format_help(self, commands: list[dict[str, str]]) -> Panel:
        """
        格式化帮助信息

        Args:
            commands: 命令列表 [{"name": "/help", "description": "..."}]

        Returns:
            Rich Panel
        """
        table = Table(show_header=True, header_style="bold", box=None)
        table.add_column("Command", style="cyan")
        table.add_column("Description")

        for cmd in commands:
            table.add_row(cmd["name"], cmd.get("description", ""))

        return Panel(
            table,
            title="[bold]Available Commands[/bold]",
            border_style="blue",
        )

    def format_sessions(self, sessions: list[dict[str, Any]]) -> Panel:
        """
        格式化会话列表

        Args:
            sessions: 会话列表

        Returns:
            Rich Panel
        """
        table = Table(show_header=True, header_style="bold", box=None)
        table.add_column("Key", style="cyan")
        table.add_column("Type")
        table.add_column("Messages", justify="right")
        table.add_column("Last Active")

        for session in sessions:
            key = session.get("key", "")
            if len(key) > 30:
                key = key[:27] + "..."
            table.add_row(
                key,
                session.get("type", "unknown"),
                str(session.get("message_count", 0)),
                session.get("last_active", ""),
            )

        return Panel(
            table,
            title="[bold]Sessions[/bold]",
            border_style="blue",
        )

    def format_error(self, message: str, title: str = "Error") -> Panel:
        """格式化错误消息"""
        return Panel(
            Text(message, style=self.theme.error_message),
            title=f"[bold red]{title}[/bold red]",
            border_style="red",
        )

    def format_success(self, message: str, title: str = "Success") -> Panel:
        """格式化成功消息"""
        return Panel(
            Text(message, style="green"),
            title=f"[bold green]{title}[/bold green]",
            border_style="green",
        )

    def format_info(self, message: str, title: str = "Info") -> Panel:
        """格式化信息消息"""
        return Panel(
            Text(message),
            title=f"[bold blue]{title}[/bold blue]",
            border_style="blue",
        )

    def format_thinking_indicator(self, thinking_text: str = "") -> Text:
        """
        格式化 thinking 指示器

        Args:
            thinking_text: thinking 文本

        Returns:
            Rich Text
        """
        text = Text()
        text.append("🤔 ", style="yellow")
        text.append("Thinking", style=self.theme.thinking)

        if thinking_text:
            # 显示最后一行
            lines = thinking_text.strip().split("\n")
            last_line = lines[-1] if lines else ""
            if len(last_line) > 60:
                last_line = last_line[:57] + "..."
            text.append(f": {last_line}", style="dim")

        return text

    def format_streaming_indicator(self) -> Text:
        """格式化流式指示器"""
        text = Text()
        text.append("● ", style=self.theme.streaming)
        text.append("Streaming response...", style="dim")
        return text
