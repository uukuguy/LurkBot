"""
Rich CLI 提示器

使用 Rich 库实现 WizardPrompter 接口

对标 MoltBot wizard/clack-prompter.ts
"""

import asyncio
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.text import Text

from .prompts import (
    WizardConfirmParams,
    WizardMultiSelectParams,
    WizardProgress,
    WizardPrompter,
    WizardSelectParams,
    WizardTextParams,
    WizardCancelledError,
)


class RichProgress(WizardProgress):
    """Rich 进度实现"""

    def __init__(self, console: Console, label: str) -> None:
        self._console = console
        self._label = label
        self._progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        )
        self._task_id = None
        self._started = False

    def start(self) -> None:
        """启动进度"""
        if not self._started:
            self._progress.start()
            self._task_id = self._progress.add_task(self._label)
            self._started = True

    def update(self, message: str) -> None:
        """更新进度消息"""
        if not self._started:
            self.start()
        if self._task_id is not None:
            self._progress.update(self._task_id, description=message)

    def stop(self, message: str | None = None) -> None:
        """停止进度显示"""
        if self._started:
            self._progress.stop()
            self._started = False
            if message:
                self._console.print(f"✓ {message}")


class RichPrompter:
    """
    Rich CLI 提示器

    使用 Rich 库实现交互式命令行提示

    对标 MoltBot clack-prompter.ts
    """

    def __init__(self, console: Console | None = None) -> None:
        self._console = console or Console()

    async def intro(self, title: str) -> None:
        """显示向导介绍"""
        self._console.print()
        self._console.print(
            Panel(
                Text(title, style="bold cyan"),
                border_style="cyan",
            )
        )
        self._console.print()

    async def outro(self, message: str) -> None:
        """显示向导结束"""
        self._console.print()
        self._console.print(
            Panel(
                Text(message, style="bold green"),
                border_style="green",
            )
        )
        self._console.print()

    async def note(self, message: str, title: str | None = None) -> None:
        """显示提示信息"""
        self._console.print()
        if title:
            self._console.print(
                Panel(
                    message,
                    title=title,
                    border_style="blue",
                )
            )
        else:
            self._console.print(
                Panel(
                    message,
                    border_style="blue",
                )
            )
        self._console.print()

    async def select(self, params: WizardSelectParams) -> Any:
        """单选提示"""
        self._console.print()
        self._console.print(f"[bold]{params.message}[/bold]")
        self._console.print()

        # 显示选项表格
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("Index", style="cyan", width=4)
        table.add_column("Label")
        table.add_column("Hint", style="dim")

        for i, opt in enumerate(params.options, 1):
            hint = opt.get("hint", "")
            table.add_row(f"[{i}]", opt.get("label", ""), hint)

        self._console.print(table)
        self._console.print()

        # 获取用户输入
        while True:
            try:
                choice = Prompt.ask(
                    "Enter number",
                    default="1" if params.initial_value is None else None,
                )
                if choice.lower() in ("q", "quit", "exit"):
                    raise WizardCancelledError("user cancelled")

                idx = int(choice) - 1
                if 0 <= idx < len(params.options):
                    return params.options[idx].get("value")
                self._console.print("[red]Invalid choice. Please try again.[/red]")
            except ValueError:
                self._console.print("[red]Please enter a number.[/red]")
            except KeyboardInterrupt:
                raise WizardCancelledError("user cancelled")

    async def multiselect(self, params: WizardMultiSelectParams) -> list[Any]:
        """多选提示"""
        self._console.print()
        self._console.print(f"[bold]{params.message}[/bold]")
        self._console.print("[dim]Enter numbers separated by commas (e.g., 1,3,5)[/dim]")
        self._console.print()

        # 显示选项表格
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("Index", style="cyan", width=4)
        table.add_column("Label")
        table.add_column("Hint", style="dim")

        for i, opt in enumerate(params.options, 1):
            hint = opt.get("hint", "")
            table.add_row(f"[{i}]", opt.get("label", ""), hint)

        self._console.print(table)
        self._console.print()

        # 获取用户输入
        while True:
            try:
                choice = Prompt.ask(
                    "Enter numbers",
                    default="",
                )
                if choice.lower() in ("q", "quit", "exit"):
                    raise WizardCancelledError("user cancelled")

                if not choice.strip():
                    return []

                indices = [int(x.strip()) - 1 for x in choice.split(",")]
                selected = []
                for idx in indices:
                    if 0 <= idx < len(params.options):
                        selected.append(params.options[idx].get("value"))
                    else:
                        self._console.print(f"[red]Invalid index: {idx + 1}[/red]")
                        break
                else:
                    return selected
            except ValueError:
                self._console.print("[red]Please enter valid numbers.[/red]")
            except KeyboardInterrupt:
                raise WizardCancelledError("user cancelled")

    async def text(self, params: WizardTextParams) -> str:
        """文本输入提示"""
        self._console.print()

        while True:
            try:
                value = Prompt.ask(
                    params.message,
                    default=params.initial_value or "",
                )
                if value.lower() in ("q", "quit", "exit"):
                    raise WizardCancelledError("user cancelled")

                # 验证
                if params.validate:
                    error = params.validate(value)
                    if error:
                        self._console.print(f"[red]{error}[/red]")
                        continue

                return value
            except KeyboardInterrupt:
                raise WizardCancelledError("user cancelled")

    async def confirm(self, params: WizardConfirmParams) -> bool:
        """确认提示"""
        self._console.print()
        try:
            return Confirm.ask(
                params.message,
                default=params.initial_value,
            )
        except KeyboardInterrupt:
            raise WizardCancelledError("user cancelled")

    def progress(self, label: str) -> WizardProgress:
        """显示进度"""
        progress = RichProgress(self._console, label)
        progress.start()
        return progress


def create_rich_prompter(console: Console | None = None) -> RichPrompter:
    """创建 Rich 提示器"""
    return RichPrompter(console)
