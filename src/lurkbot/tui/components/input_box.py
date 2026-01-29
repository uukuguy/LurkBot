"""
TUI 输入框组件

对标 MoltBot TUI 中的输入处理

提供命令行输入功能
"""

from dataclasses import dataclass, field
from typing import Callable, Awaitable, Any

from rich.console import RenderableType
from rich.panel import Panel
from rich.text import Text

from ..types import TuiTheme, DEFAULT_THEME, ActivityStatus
from ..events import InputHistory


@dataclass
class InputBoxConfig:
    """输入框配置"""

    prompt: str = ">>> "
    placeholder: str = "Type a message..."
    max_length: int = 10000
    history_size: int = 100
    multiline: bool = False
    theme: TuiTheme = field(default_factory=lambda: DEFAULT_THEME)


class InputBox:
    """
    输入框组件

    功能:
    - 文本输入
    - 历史导航
    - 命令补全
    """

    def __init__(
        self,
        config: InputBoxConfig | None = None,
    ) -> None:
        self.config = config or InputBoxConfig()
        self._content = ""
        self._cursor_pos = 0
        self._history = InputHistory(max_size=self.config.history_size)
        self._is_focused = True
        self._activity_status = ActivityStatus.IDLE

    @property
    def content(self) -> str:
        """获取输入内容"""
        return self._content

    @property
    def is_empty(self) -> bool:
        """是否为空"""
        return not self._content.strip()

    @property
    def is_focused(self) -> bool:
        """是否获得焦点"""
        return self._is_focused

    def set_content(self, content: str) -> None:
        """
        设置内容

        Args:
            content: 输入内容
        """
        self._content = content[:self.config.max_length]
        self._cursor_pos = len(self._content)

    def clear(self) -> None:
        """清除内容"""
        self._content = ""
        self._cursor_pos = 0
        self._history.reset()

    def insert(self, text: str) -> None:
        """
        插入文本

        Args:
            text: 要插入的文本
        """
        if len(self._content) + len(text) > self.config.max_length:
            return

        before = self._content[:self._cursor_pos]
        after = self._content[self._cursor_pos:]
        self._content = before + text + after
        self._cursor_pos += len(text)

    def delete_char(self) -> None:
        """删除光标前的字符"""
        if self._cursor_pos > 0:
            before = self._content[:self._cursor_pos - 1]
            after = self._content[self._cursor_pos:]
            self._content = before + after
            self._cursor_pos -= 1

    def delete_forward(self) -> None:
        """删除光标后的字符"""
        if self._cursor_pos < len(self._content):
            before = self._content[:self._cursor_pos]
            after = self._content[self._cursor_pos + 1:]
            self._content = before + after

    def move_cursor_left(self) -> None:
        """光标左移"""
        self._cursor_pos = max(0, self._cursor_pos - 1)

    def move_cursor_right(self) -> None:
        """光标右移"""
        self._cursor_pos = min(len(self._content), self._cursor_pos + 1)

    def move_cursor_home(self) -> None:
        """光标移到开头"""
        self._cursor_pos = 0

    def move_cursor_end(self) -> None:
        """光标移到末尾"""
        self._cursor_pos = len(self._content)

    def submit(self) -> str:
        """
        提交输入

        Returns:
            输入内容
        """
        content = self._content.strip()

        if content:
            # 添加到历史
            self._history.add(content)

        # 清除输入
        self.clear()

        return content

    def history_prev(self) -> None:
        """上一条历史"""
        prev = self._history.prev(self._content)
        if prev is not None:
            self.set_content(prev)

    def history_next(self) -> None:
        """下一条历史"""
        next_item = self._history.next()
        if next_item is not None:
            self.set_content(next_item)

    def focus(self) -> None:
        """获得焦点"""
        self._is_focused = True

    def blur(self) -> None:
        """失去焦点"""
        self._is_focused = False

    def set_activity_status(self, status: ActivityStatus) -> None:
        """设置活动状态"""
        self._activity_status = status

    def render(self) -> RenderableType:
        """
        渲染输入框

        Returns:
            Rich 渲染对象
        """
        text = Text()

        # 提示符
        prompt_style = "bold green" if self._is_focused else "dim"
        text.append(self.config.prompt, style=prompt_style)

        # 内容或占位符
        if self._content:
            # 渲染内容，在光标位置显示光标
            before_cursor = self._content[:self._cursor_pos]
            after_cursor = self._content[self._cursor_pos:]

            text.append(before_cursor)

            # 光标
            if self._is_focused:
                if after_cursor:
                    # 光标在字符上
                    text.append(after_cursor[0], style="reverse")
                    text.append(after_cursor[1:])
                else:
                    # 光标在末尾
                    text.append(" ", style="reverse")
            else:
                text.append(after_cursor)
        else:
            # 占位符
            text.append(self.config.placeholder, style="dim italic")
            if self._is_focused:
                text.append(" ", style="reverse")

        # 活动状态指示
        if self._activity_status != ActivityStatus.IDLE:
            status_text = {
                ActivityStatus.SENDING: " [sending...]",
                ActivityStatus.WAITING: " [waiting...]",
                ActivityStatus.STREAMING: " [streaming...]",
            }.get(self._activity_status, "")
            text.append(status_text, style="dim cyan")

        return text

    def render_panel(self) -> RenderableType:
        """
        渲染为 Panel

        Returns:
            Rich Panel
        """
        border_style = (
            self.config.theme.border_focused
            if self._is_focused
            else self.config.theme.border
        )

        return Panel(
            self.render(),
            border_style=border_style,
            padding=(0, 1),
        )


class CommandCompleter:
    """
    命令补全器

    提供命令自动补全功能
    """

    def __init__(self, commands: list[str] | None = None) -> None:
        self._commands = commands or []
        self._completions: list[str] = []
        self._completion_index = 0

    def set_commands(self, commands: list[str]) -> None:
        """设置可用命令"""
        self._commands = sorted(commands)

    def get_completions(self, prefix: str) -> list[str]:
        """
        获取补全列表

        Args:
            prefix: 输入前缀

        Returns:
            匹配的命令列表
        """
        if not prefix.startswith("/"):
            return []

        return [cmd for cmd in self._commands if cmd.startswith(prefix)]

    def complete(self, text: str) -> str | None:
        """
        执行补全

        Args:
            text: 当前输入

        Returns:
            补全后的文本，或 None
        """
        # 只补全开头的命令
        if " " in text:
            return None

        completions = self.get_completions(text)
        if not completions:
            return None

        if len(completions) == 1:
            return completions[0]

        # 多个匹配，找公共前缀
        common = completions[0]
        for comp in completions[1:]:
            while not comp.startswith(common):
                common = common[:-1]
            if not common:
                break

        if common and common != text:
            return common

        # 循环补全
        if not self._completions or self._completions != completions:
            self._completions = completions
            self._completion_index = 0
        else:
            self._completion_index = (self._completion_index + 1) % len(completions)

        return self._completions[self._completion_index]

    def reset(self) -> None:
        """重置补全状态"""
        self._completions = []
        self._completion_index = 0
