"""
TUI 聊天日志组件

对标 MoltBot src/tui/components/chat-log.ts

显示聊天消息历史
"""

from dataclasses import dataclass, field
from typing import Any

from rich.console import Console, Group, RenderableType
from rich.live import Live
from rich.panel import Panel
from rich.text import Text

from ..types import ChatMessage, MessageRole, TuiTheme, DEFAULT_THEME
from ..formatters import TuiFormatter


@dataclass
class ChatLogConfig:
    """聊天日志配置"""

    max_visible_messages: int = 50
    show_timestamps: bool = False
    show_thinking: bool = False
    auto_scroll: bool = True
    theme: TuiTheme = field(default_factory=lambda: DEFAULT_THEME)


class ChatLog:
    """
    聊天日志组件

    对标 MoltBot ChatLog 组件

    功能:
    - 显示消息历史
    - 支持滚动
    - 支持流式消息更新
    """

    def __init__(
        self,
        config: ChatLogConfig | None = None,
    ) -> None:
        self.config = config or ChatLogConfig()
        self._messages: list[ChatMessage] = []
        self._formatter = TuiFormatter(self.config.theme)
        self._scroll_offset = 0
        self._streaming_content: dict[str, str] = {}  # run_id -> current content

    @property
    def messages(self) -> list[ChatMessage]:
        """获取消息列表"""
        return self._messages.copy()

    def add_message(self, message: ChatMessage) -> None:
        """
        添加消息

        Args:
            message: 聊天消息
        """
        self._messages.append(message)

        # 如果开启自动滚动，滚动到底部
        if self.config.auto_scroll:
            self._scroll_to_bottom()

    def update_streaming(self, run_id: str, content: str) -> None:
        """
        更新流式内容

        Args:
            run_id: 运行 ID
            content: 当前内容
        """
        self._streaming_content[run_id] = content

    def finalize_streaming(self, run_id: str) -> None:
        """
        完成流式内容

        Args:
            run_id: 运行 ID
        """
        self._streaming_content.pop(run_id, None)

    def clear(self) -> None:
        """清除所有消息"""
        self._messages.clear()
        self._streaming_content.clear()
        self._scroll_offset = 0

    def scroll_up(self, lines: int = 1) -> None:
        """向上滚动"""
        self._scroll_offset = max(0, self._scroll_offset - lines)

    def scroll_down(self, lines: int = 1) -> None:
        """向下滚动"""
        max_offset = max(0, len(self._messages) - self.config.max_visible_messages)
        self._scroll_offset = min(max_offset, self._scroll_offset + lines)

    def scroll_to_top(self) -> None:
        """滚动到顶部"""
        self._scroll_offset = 0

    def _scroll_to_bottom(self) -> None:
        """滚动到底部"""
        max_offset = max(0, len(self._messages) - self.config.max_visible_messages)
        self._scroll_offset = max_offset

    def render(self) -> RenderableType:
        """
        渲染聊天日志

        Returns:
            Rich 渲染对象
        """
        parts: list[RenderableType] = []

        # 获取可见消息
        start_idx = self._scroll_offset
        end_idx = start_idx + self.config.max_visible_messages
        visible_messages = self._messages[start_idx:end_idx]

        # 渲染每条消息
        for message in visible_messages:
            panel = self._formatter.format_message(
                message,
                show_thinking=self.config.show_thinking,
                show_timestamps=self.config.show_timestamps,
            )
            parts.append(panel)

        # 渲染流式消息
        for run_id, content in self._streaming_content.items():
            streaming_message = ChatMessage(
                id=run_id,
                role=MessageRole.ASSISTANT,
                content=content,
                is_streaming=True,
            )
            panel = self._formatter.format_message(
                streaming_message,
                show_thinking=self.config.show_thinking,
                show_timestamps=self.config.show_timestamps,
            )
            parts.append(panel)

        if not parts:
            parts.append(Text("No messages yet. Type a message to start.", style="dim"))

        return Group(*parts)

    def get_scroll_info(self) -> tuple[int, int, int]:
        """
        获取滚动信息

        Returns:
            (当前偏移, 可见数量, 总数量)
        """
        return (
            self._scroll_offset,
            min(self.config.max_visible_messages, len(self._messages)),
            len(self._messages),
        )
