"""
TUI 快捷键定义

对标 MoltBot TUI 的键盘绑定
"""

from dataclasses import dataclass
from enum import Enum
from typing import Callable, Any


class KeyAction(str, Enum):
    """快捷键动作"""

    # 导航
    SCROLL_UP = "scroll_up"
    SCROLL_DOWN = "scroll_down"
    SCROLL_PAGE_UP = "scroll_page_up"
    SCROLL_PAGE_DOWN = "scroll_page_down"
    SCROLL_TO_TOP = "scroll_to_top"
    SCROLL_TO_BOTTOM = "scroll_to_bottom"

    # 编辑
    SUBMIT = "submit"
    CANCEL = "cancel"
    CLEAR_INPUT = "clear_input"
    HISTORY_PREV = "history_prev"
    HISTORY_NEXT = "history_next"

    # 功能
    TOGGLE_THINKING = "toggle_thinking"
    TOGGLE_TOOLS = "toggle_tools"
    ABORT_RUN = "abort_run"
    NEW_SESSION = "new_session"
    SHOW_HELP = "show_help"
    SHOW_STATUS = "show_status"

    # 窗口
    FOCUS_INPUT = "focus_input"
    FOCUS_CHAT = "focus_chat"
    EXIT = "exit"


@dataclass
class KeyBinding:
    """快捷键绑定"""

    key: str  # 按键表示，如 "ctrl+c", "enter", "up"
    action: KeyAction
    description: str = ""
    when: str | None = None  # 条件，如 "input_focused"


# 默认快捷键配置
DEFAULT_KEYBINDINGS: list[KeyBinding] = [
    # 提交和取消
    KeyBinding("enter", KeyAction.SUBMIT, "Send message", "input_focused"),
    KeyBinding("ctrl+c", KeyAction.CANCEL, "Cancel/Exit"),
    KeyBinding("ctrl+d", KeyAction.EXIT, "Exit TUI"),
    KeyBinding("escape", KeyAction.CANCEL, "Cancel current action"),

    # 历史导航
    KeyBinding("up", KeyAction.HISTORY_PREV, "Previous history", "input_focused"),
    KeyBinding("down", KeyAction.HISTORY_NEXT, "Next history", "input_focused"),

    # 滚动
    KeyBinding("ctrl+up", KeyAction.SCROLL_UP, "Scroll up"),
    KeyBinding("ctrl+down", KeyAction.SCROLL_DOWN, "Scroll down"),
    KeyBinding("pageup", KeyAction.SCROLL_PAGE_UP, "Page up"),
    KeyBinding("pagedown", KeyAction.SCROLL_PAGE_DOWN, "Page down"),
    KeyBinding("ctrl+home", KeyAction.SCROLL_TO_TOP, "Scroll to top"),
    KeyBinding("ctrl+end", KeyAction.SCROLL_TO_BOTTOM, "Scroll to bottom"),

    # 功能快捷键
    KeyBinding("ctrl+t", KeyAction.TOGGLE_THINKING, "Toggle thinking display"),
    KeyBinding("ctrl+e", KeyAction.TOGGLE_TOOLS, "Toggle tool details"),
    KeyBinding("ctrl+x", KeyAction.ABORT_RUN, "Abort current run"),
    KeyBinding("ctrl+n", KeyAction.NEW_SESSION, "New session"),
    KeyBinding("ctrl+h", KeyAction.SHOW_HELP, "Show help"),
    KeyBinding("ctrl+s", KeyAction.SHOW_STATUS, "Show status"),

    # 焦点
    KeyBinding("tab", KeyAction.FOCUS_INPUT, "Focus input"),
    KeyBinding("ctrl+l", KeyAction.CLEAR_INPUT, "Clear input"),
]


class KeyBindingManager:
    """
    快捷键管理器

    管理快捷键绑定和动作分发
    """

    def __init__(self, bindings: list[KeyBinding] | None = None) -> None:
        self._bindings = bindings or DEFAULT_KEYBINDINGS.copy()
        self._handlers: dict[KeyAction, Callable[[], Any]] = {}

    def register_handler(
        self,
        action: KeyAction,
        handler: Callable[[], Any],
    ) -> None:
        """注册动作处理器"""
        self._handlers[action] = handler

    def unregister_handler(self, action: KeyAction) -> None:
        """取消注册动作处理器"""
        self._handlers.pop(action, None)

    def get_action(self, key: str, context: str | None = None) -> KeyAction | None:
        """
        获取按键对应的动作

        Args:
            key: 按键表示
            context: 当前上下文

        Returns:
            对应的动作，或 None
        """
        for binding in self._bindings:
            if binding.key == key:
                # 检查条件
                if binding.when is None or binding.when == context:
                    return binding.action
        return None

    def handle_key(self, key: str, context: str | None = None) -> bool:
        """
        处理按键

        Args:
            key: 按键表示
            context: 当前上下文

        Returns:
            是否处理了该按键
        """
        action = self.get_action(key, context)
        if action and action in self._handlers:
            self._handlers[action]()
            return True
        return False

    def get_bindings(self) -> list[KeyBinding]:
        """获取所有绑定"""
        return self._bindings.copy()

    def get_bindings_for_action(self, action: KeyAction) -> list[KeyBinding]:
        """获取指定动作的所有绑定"""
        return [b for b in self._bindings if b.action == action]

    def add_binding(self, binding: KeyBinding) -> None:
        """添加绑定"""
        self._bindings.append(binding)

    def remove_binding(self, key: str) -> None:
        """移除绑定"""
        self._bindings = [b for b in self._bindings if b.key != key]

    def get_help_text(self) -> list[tuple[str, str]]:
        """
        获取帮助文本

        Returns:
            [(快捷键, 描述), ...]
        """
        result: list[tuple[str, str]] = []
        seen: set[str] = set()

        for binding in self._bindings:
            if binding.description and binding.key not in seen:
                result.append((binding.key, binding.description))
                seen.add(binding.key)

        return result
