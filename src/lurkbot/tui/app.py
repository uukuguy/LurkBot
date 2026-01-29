"""
TUI 主应用

对标 MoltBot src/tui/tui.ts

交互式终端界面主入口
"""

import asyncio
import sys
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Awaitable
from uuid import uuid4

from loguru import logger
from rich.console import Console, Group
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.text import Text

from .types import (
    ActivityStatus,
    ChatMessage,
    MessageRole,
    TuiConfig,
    TuiEvent,
    TuiEventType,
    TuiState,
    TuiTheme,
    DEFAULT_THEME,
)
from .stream_assembler import TuiStreamAssembler
from .formatters import TuiFormatter
from .commands import CommandHandler
from .events import TuiEventHandler, InputHistory
from .gateway_chat import GatewayChat
from .components import (
    ChatLog,
    ChatLogConfig,
    ThinkingIndicator,
    StreamingIndicator,
    InputBox,
    InputBoxConfig,
    CommandCompleter,
)


@dataclass
class TuiAppConfig:
    """TUI 应用配置"""

    gateway_url: str = "ws://localhost:3000"
    gateway_token: str | None = None
    theme: TuiTheme = field(default_factory=lambda: DEFAULT_THEME)
    show_timestamps: bool = False
    show_thinking: bool = False
    auto_connect: bool = True
    refresh_rate: float = 0.1  # 刷新率（秒）


class TuiApp:
    """
    TUI 主应用

    对标 MoltBot TUI 主入口

    功能:
    - 交互式聊天界面
    - 命令处理
    - 流式响应显示
    - Gateway 通信
    """

    def __init__(
        self,
        config: TuiAppConfig | None = None,
    ) -> None:
        self.config = config or TuiAppConfig()

        # 控制台
        self._console = Console()

        # 状态
        self._state = TuiState(
            show_thinking=self.config.show_thinking,
        )

        # 组件
        self._chat_log = ChatLog(
            ChatLogConfig(
                show_timestamps=self.config.show_timestamps,
                show_thinking=self.config.show_thinking,
                theme=self.config.theme,
            )
        )
        self._thinking = ThinkingIndicator()
        self._streaming = StreamingIndicator(self.config.theme)
        self._input_box = InputBox(
            InputBoxConfig(theme=self.config.theme)
        )
        self._completer = CommandCompleter()

        # Gateway
        self._gateway = GatewayChat(
            url=self.config.gateway_url,
            token=self.config.gateway_token,
        )

        # 命令处理器
        self._command_handler = CommandHandler(self._gateway)

        # 事件处理器
        self._event_handler = TuiEventHandler(self._state)

        # 格式化器
        self._formatter = TuiFormatter(self.config.theme)

        # 流式组装器
        self._stream_assembler = TuiStreamAssembler()

        # 运行状态
        self._running = False
        self._exit_requested = False

        # 设置命令补全
        commands = self._command_handler.get_commands()
        self._completer.set_commands([cmd.name for cmd in commands])

        # 注册 Gateway 回调
        self._gateway.on_event(self._on_gateway_event)
        self._gateway.on_stream(self._on_gateway_stream)

    @property
    def state(self) -> TuiState:
        """获取状态"""
        return self._state

    @property
    def is_running(self) -> bool:
        """是否正在运行"""
        return self._running

    async def start(self) -> None:
        """启动 TUI"""
        self._running = True
        self._exit_requested = False

        # 显示欢迎信息
        self._show_welcome()

        # 自动连接
        if self.config.auto_connect:
            await self._connect()

        # 主循环
        await self._run_loop()

    async def stop(self) -> None:
        """停止 TUI"""
        self._exit_requested = True

        # 断开连接
        if self._gateway.connected:
            await self._gateway.disconnect()

        self._running = False

    def _show_welcome(self) -> None:
        """显示欢迎信息"""
        welcome_text = Text()
        welcome_text.append("LurkBot TUI", style="bold blue")
        welcome_text.append(" - Interactive Terminal Interface\n", style="dim")
        welcome_text.append("Type ", style="dim")
        welcome_text.append("/help", style="cyan")
        welcome_text.append(" for available commands\n", style="dim")
        welcome_text.append("Press ", style="dim")
        welcome_text.append("Ctrl+D", style="cyan")
        welcome_text.append(" to exit", style="dim")

        self._console.print(Panel(welcome_text, border_style="blue"))
        self._console.print()

    async def _connect(self) -> None:
        """连接到 Gateway"""
        self._console.print("[dim]Connecting to gateway...[/dim]")

        success = await self._gateway.connect()

        if success:
            self._state.is_connected = True
            self._state.connection_status = "connected"
            self._console.print("[green]✓ Connected to gateway[/green]")
        else:
            self._state.is_connected = False
            self._state.connection_status = "failed"
            self._console.print("[red]✗ Failed to connect to gateway[/red]")
            self._console.print("[dim]Running in offline mode[/dim]")

        self._console.print()

    async def _run_loop(self) -> None:
        """主运行循环"""
        try:
            while self._running and not self._exit_requested:
                # 读取输入
                try:
                    user_input = await self._read_input()
                except EOFError:
                    # Ctrl+D
                    break
                except KeyboardInterrupt:
                    # Ctrl+C
                    if self._state.active_chat_run_id:
                        # 中止当前运行
                        await self._abort_current_run()
                    else:
                        # 确认退出
                        self._console.print("\n[dim]Press Ctrl+D to exit[/dim]")
                    continue

                if user_input is None:
                    continue

                # 处理输入
                await self._handle_input(user_input)

        except Exception as e:
            logger.error(f"TUI loop error: {e}")
            self._console.print(f"[red]Error: {e}[/red]")

        finally:
            await self.stop()

    async def _read_input(self) -> str | None:
        """读取用户输入"""
        # 构建提示符
        if self._state.is_connected:
            prompt = f"[green]●[/green] {self._state.current_agent_id} >>> "
        else:
            prompt = f"[red]○[/red] {self._state.current_agent_id} >>> "

        # 使用 Rich 的 input
        try:
            # 在异步环境中使用同步 input
            # 实际生产中应该使用 prompt_toolkit
            loop = asyncio.get_event_loop()
            user_input = await loop.run_in_executor(
                None,
                lambda: self._console.input(prompt),
            )
            return user_input.strip() if user_input else None
        except EOFError:
            raise

    async def _handle_input(self, user_input: str) -> None:
        """处理用户输入"""
        if not user_input:
            return

        # 检查是否是命令
        if self._command_handler.is_command(user_input):
            await self._handle_command(user_input)
        else:
            await self._send_message(user_input)

    async def _handle_command(self, command: str) -> None:
        """处理命令"""
        result = await self._command_handler.execute(command, self._state)

        # 显示结果
        if result.message:
            if result.success:
                self._console.print(result.message)
            else:
                self._console.print(f"[red]{result.message}[/red]")

        # 处理特殊动作
        if result.data:
            action = result.data.get("action")
            if action == "exit":
                self._exit_requested = True
            elif action == "clear":
                self._console.clear()
                self._chat_log.clear()

        # 如果需要发送给 Agent
        if result.should_send_to_agent and result.agent_message:
            await self._send_message(result.agent_message)

        self._console.print()

    async def _send_message(self, message: str) -> None:
        """发送消息到 Agent"""
        # 显示用户消息
        user_msg = ChatMessage(
            id=str(uuid4()),
            role=MessageRole.USER,
            content=message,
        )
        self._chat_log.add_message(user_msg)
        self._console.print(
            self._formatter.format_message(user_msg)
        )

        # 检查连接
        if not self._gateway.connected:
            self._console.print("[yellow]Not connected to gateway. Message not sent.[/yellow]")
            self._console.print()
            return

        # 更新状态
        self._state.activity_status = ActivityStatus.SENDING

        try:
            # 发送消息
            run_id = await self._gateway.send_message(
                message=message,
                agent_id=self._state.current_agent_id,
                session_key=self._state.current_session_key or None,
                model=self._state.current_model,
                thinking_level=self._state.thinking_level.value if self._state.thinking_level.value != "off" else None,
            )

            self._state.active_chat_run_id = run_id
            self._state.activity_status = ActivityStatus.WAITING

            # 等待响应完成
            await self._wait_for_response(run_id)

        except Exception as e:
            logger.error(f"Send message error: {e}")
            self._console.print(f"[red]Error sending message: {e}[/red]")
            self._state.activity_status = ActivityStatus.IDLE

        self._console.print()

    async def _wait_for_response(self, run_id: str) -> None:
        """等待响应完成"""
        # 使用 Live 显示流式响应
        with Live(
            self._formatter.format_streaming_indicator(),
            console=self._console,
            refresh_per_second=10,
            transient=True,
        ) as live:
            while (
                self._state.active_chat_run_id == run_id
                and self._state.activity_status in (ActivityStatus.WAITING, ActivityStatus.STREAMING)
            ):
                # 更新显示
                if self._stream_assembler.has_run(run_id):
                    content = self._stream_assembler.get_content(run_id)
                    thinking = self._stream_assembler.get_thinking(run_id)

                    display_parts = []

                    # Thinking
                    if self._state.show_thinking and thinking:
                        display_parts.append(
                            self._formatter.format_thinking_indicator(thinking)
                        )

                    # 内容
                    if content:
                        display_parts.append(Text(content))
                    else:
                        display_parts.append(
                            self._formatter.format_streaming_indicator()
                        )

                    live.update(Group(*display_parts) if display_parts else Text(""))

                await asyncio.sleep(self.config.refresh_rate)

        # 显示最终响应
        if self._stream_assembler.has_run(run_id):
            content = self._stream_assembler.finalize(run_id)
            if content:
                assistant_msg = ChatMessage(
                    id=run_id,
                    role=MessageRole.ASSISTANT,
                    content=content,
                )
                self._chat_log.add_message(assistant_msg)
                self._console.print(
                    self._formatter.format_message(
                        assistant_msg,
                        show_thinking=self._state.show_thinking,
                    )
                )

        self._state.activity_status = ActivityStatus.IDLE
        self._state.active_chat_run_id = None

    async def _abort_current_run(self) -> None:
        """中止当前运行"""
        if not self._state.active_chat_run_id:
            return

        run_id = self._state.active_chat_run_id
        self._console.print(f"\n[yellow]Aborting run {run_id[:8]}...[/yellow]")

        try:
            await self._gateway.abort_run(run_id)
        except Exception as e:
            logger.warning(f"Abort error: {e}")

        self._state.activity_status = ActivityStatus.IDLE
        self._state.active_chat_run_id = None
        self._stream_assembler.clear(run_id)

    async def _on_gateway_event(self, event: TuiEvent) -> None:
        """处理 Gateway 事件"""
        await self._event_handler.handle_event(event)

        # 更新状态
        if event.type == TuiEventType.CONNECTED:
            self._state.is_connected = True
            self._state.connection_status = "connected"
        elif event.type == TuiEventType.DISCONNECTED:
            self._state.is_connected = False
            self._state.connection_status = "disconnected"
        elif event.type == TuiEventType.STREAM_END:
            self._state.activity_status = ActivityStatus.IDLE

    async def _on_gateway_stream(self, run_id: str, delta: dict[str, Any]) -> None:
        """处理 Gateway 流式数据"""
        self._state.activity_status = ActivityStatus.STREAMING
        self._stream_assembler.ingest_delta(
            run_id,
            delta,
            self._state.show_thinking,
        )


async def run_tui(
    gateway_url: str = "ws://localhost:3000",
    gateway_token: str | None = None,
    show_thinking: bool = False,
) -> None:
    """
    运行 TUI

    Args:
        gateway_url: Gateway URL
        gateway_token: Gateway token
        show_thinking: 是否显示 thinking
    """
    config = TuiAppConfig(
        gateway_url=gateway_url,
        gateway_token=gateway_token,
        show_thinking=show_thinking,
    )

    app = TuiApp(config)

    try:
        await app.start()
    except KeyboardInterrupt:
        pass
    finally:
        await app.stop()


def main() -> None:
    """TUI 入口"""
    import argparse

    parser = argparse.ArgumentParser(description="LurkBot TUI")
    parser.add_argument(
        "--gateway",
        "-g",
        default="ws://localhost:3000",
        help="Gateway WebSocket URL",
    )
    parser.add_argument(
        "--token",
        "-t",
        default=None,
        help="Gateway authentication token",
    )
    parser.add_argument(
        "--thinking",
        action="store_true",
        help="Show thinking output",
    )

    args = parser.parse_args()

    asyncio.run(
        run_tui(
            gateway_url=args.gateway,
            gateway_token=args.token,
            show_thinking=args.thinking,
        )
    )


if __name__ == "__main__":
    main()
