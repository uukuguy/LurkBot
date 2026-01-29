"""
TUI Thinking 指示器组件

对标 MoltBot TUI 中的思考状态显示

显示 AI 正在思考的状态
"""

from dataclasses import dataclass
from typing import Any

from rich.console import RenderableType
from rich.panel import Panel
from rich.text import Text
from rich.spinner import Spinner
from rich.live import Live

from ..types import TuiTheme, DEFAULT_THEME


@dataclass
class ThinkingConfig:
    """Thinking 配置"""

    show_content: bool = True
    max_preview_length: int = 100
    theme: TuiTheme = None  # type: ignore

    def __post_init__(self) -> None:
        if self.theme is None:
            self.theme = DEFAULT_THEME


class ThinkingIndicator:
    """
    Thinking 指示器组件

    功能:
    - 显示思考状态
    - 显示思考内容预览
    - 支持动画效果
    """

    def __init__(
        self,
        config: ThinkingConfig | None = None,
    ) -> None:
        self.config = config or ThinkingConfig()
        self._is_thinking = False
        self._thinking_content = ""
        self._spinner_frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        self._frame_index = 0

    @property
    def is_thinking(self) -> bool:
        """是否正在思考"""
        return self._is_thinking

    def start(self) -> None:
        """开始思考"""
        self._is_thinking = True
        self._thinking_content = ""
        self._frame_index = 0

    def stop(self) -> None:
        """停止思考"""
        self._is_thinking = False

    def update_content(self, content: str) -> None:
        """
        更新思考内容

        Args:
            content: 思考内容
        """
        self._thinking_content = content

    def append_content(self, delta: str) -> None:
        """
        追加思考内容

        Args:
            delta: 增量内容
        """
        self._thinking_content += delta

    def tick(self) -> None:
        """更新动画帧"""
        self._frame_index = (self._frame_index + 1) % len(self._spinner_frames)

    def render(self) -> RenderableType:
        """
        渲染指示器

        Returns:
            Rich 渲染对象
        """
        if not self._is_thinking:
            return Text("")

        text = Text()

        # Spinner
        spinner_char = self._spinner_frames[self._frame_index]
        text.append(f"{spinner_char} ", style="cyan")

        # 标题
        text.append("Thinking", style=self.config.theme.thinking)

        # 内容预览
        if self.config.show_content and self._thinking_content:
            preview = self._get_preview()
            if preview:
                text.append(": ", style="dim")
                text.append(preview, style="dim italic")

        return text

    def render_panel(self) -> RenderableType:
        """
        渲染为 Panel

        Returns:
            Rich Panel
        """
        if not self._is_thinking:
            return Text("")

        content = Text()

        if self._thinking_content:
            # 显示完整内容（可能截断）
            display_content = self._thinking_content
            if len(display_content) > 500:
                display_content = display_content[-500:]
                content.append("...\n", style="dim")
            content.append(display_content, style=self.config.theme.thinking)
        else:
            content.append("Processing...", style="dim")

        return Panel(
            content,
            title="[dim]🤔 Thinking[/dim]",
            border_style="dim",
            padding=(0, 1),
        )

    def _get_preview(self) -> str:
        """获取内容预览"""
        if not self._thinking_content:
            return ""

        # 获取最后一行
        lines = self._thinking_content.strip().split("\n")
        last_line = lines[-1] if lines else ""

        # 截断
        if len(last_line) > self.config.max_preview_length:
            last_line = last_line[: self.config.max_preview_length - 3] + "..."

        return last_line


class StreamingIndicator:
    """
    流式响应指示器

    显示 AI 正在生成响应
    """

    def __init__(
        self,
        theme: TuiTheme | None = None,
    ) -> None:
        self.theme = theme or DEFAULT_THEME
        self._is_streaming = False
        self._dots_count = 0

    @property
    def is_streaming(self) -> bool:
        """是否正在流式响应"""
        return self._is_streaming

    def start(self) -> None:
        """开始流式"""
        self._is_streaming = True
        self._dots_count = 0

    def stop(self) -> None:
        """停止流式"""
        self._is_streaming = False

    def tick(self) -> None:
        """更新动画"""
        self._dots_count = (self._dots_count + 1) % 4

    def render(self) -> RenderableType:
        """渲染指示器"""
        if not self._is_streaming:
            return Text("")

        text = Text()
        text.append("● ", style=self.theme.streaming)
        text.append("Streaming", style="dim")
        text.append("." * self._dots_count, style="dim")

        return text
