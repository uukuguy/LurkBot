"""
Browser Types - 浏览器自动化类型定义

对标 MoltBot src/browser/types.ts
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


# ============================================================================
# Browser Actions
# ============================================================================

class BrowserAction(str, Enum):
    """浏览器动作类型"""
    CLICK = "click"
    DOUBLE_CLICK = "doubleClick"
    TYPE = "type"
    PRESS = "press"
    DRAG = "drag"
    HOVER = "hover"
    FILL = "fill"
    SELECT_OPTION = "selectOption"
    WAIT = "wait"
    SCROLL = "scroll"
    FOCUS = "focus"
    BLUR = "blur"
    CHECK = "check"
    UNCHECK = "uncheck"


class MouseButton(str, Enum):
    """鼠标按键类型"""
    LEFT = "left"
    RIGHT = "right"
    MIDDLE = "middle"


class KeyModifier(str, Enum):
    """键盘修饰键"""
    ALT = "Alt"
    CONTROL = "Control"
    META = "Meta"
    SHIFT = "Shift"


# ============================================================================
# Request Models
# ============================================================================

class ActRequest(BaseModel):
    """执行动作请求"""
    model_config = ConfigDict(populate_by_name=True)

    action: BrowserAction
    selector: str | None = None
    text: str | None = None
    key: str | None = None
    button: MouseButton = MouseButton.LEFT
    modifiers: list[KeyModifier] = Field(default_factory=list)
    position: dict[str, int] | None = None  # {"x": int, "y": int}
    delay: float | None = None
    timeout: float = 30000
    force: bool = False
    no_wait_after: bool = Field(default=False, alias="noWaitAfter")


class NavigateRequest(BaseModel):
    """导航请求"""
    model_config = ConfigDict(populate_by_name=True)

    url: str
    wait_until: Literal["load", "domcontentloaded", "networkidle", "commit"] = Field(
        default="load", alias="waitUntil"
    )
    timeout: float = 30000
    referer: str | None = None


class ScreenshotRequest(BaseModel):
    """截图请求"""
    model_config = ConfigDict(populate_by_name=True)

    full_page: bool = Field(default=False, alias="fullPage")
    selector: str | None = None
    format: Literal["png", "jpeg"] = "png"
    quality: int | None = None  # 0-100, only for jpeg
    omit_background: bool = Field(default=False, alias="omitBackground")
    timeout: float = 30000
    scale: Literal["css", "device"] = "device"


class RoleSnapshotRequest(BaseModel):
    """角色快照请求"""
    model_config = ConfigDict(populate_by_name=True)

    include_hidden: bool = Field(default=False, alias="includeHidden")
    max_depth: int = Field(default=10, alias="maxDepth")
    root_selector: str | None = Field(default=None, alias="rootSelector")


class EvaluateRequest(BaseModel):
    """JavaScript 执行请求"""
    model_config = ConfigDict(populate_by_name=True)

    expression: str
    arg: Any = None
    timeout: float = 30000


class TabRequest(BaseModel):
    """标签页操作请求"""
    model_config = ConfigDict(populate_by_name=True)

    url: str | None = None
    tab_id: int | None = Field(default=None, alias="tabId")


class WaitForRequest(BaseModel):
    """等待请求"""
    model_config = ConfigDict(populate_by_name=True)

    selector: str | None = None
    state: Literal["attached", "detached", "visible", "hidden"] = "visible"
    timeout: float = 30000
    text: str | None = None
    url: str | None = None


# ============================================================================
# Response Models
# ============================================================================

class BrowserStatus(BaseModel):
    """浏览器状态响应"""
    model_config = ConfigDict(populate_by_name=True)

    connected: bool
    browser_type: str = Field(default="chromium", alias="browserType")
    headless: bool = True
    viewport: dict[str, int] | None = None  # {"width": int, "height": int}
    tabs_count: int = Field(default=0, alias="tabsCount")
    current_url: str | None = Field(default=None, alias="currentUrl")
    version: str | None = None


class ActResponse(BaseModel):
    """动作执行响应"""
    model_config = ConfigDict(populate_by_name=True)

    success: bool
    action: str
    selector: str | None = None
    error: str | None = None
    duration_ms: float = Field(default=0, alias="durationMs")


class NavigateResponse(BaseModel):
    """导航响应"""
    model_config = ConfigDict(populate_by_name=True)

    success: bool
    url: str
    title: str | None = None
    status: int | None = None
    error: str | None = None
    duration_ms: float = Field(default=0, alias="durationMs")


class ScreenshotResponse(BaseModel):
    """截图响应"""
    model_config = ConfigDict(populate_by_name=True)

    success: bool
    format: str
    width: int = 0
    height: int = 0
    data: str | None = None  # base64 encoded
    error: str | None = None


class TabInfo(BaseModel):
    """标签页信息"""
    model_config = ConfigDict(populate_by_name=True)

    id: int
    url: str
    title: str
    active: bool = False


class TabsResponse(BaseModel):
    """标签页列表响应"""
    model_config = ConfigDict(populate_by_name=True)

    tabs: list[TabInfo]
    active_tab: int | None = Field(default=None, alias="activeTab")


class EvaluateResponse(BaseModel):
    """JavaScript 执行响应"""
    model_config = ConfigDict(populate_by_name=True)

    success: bool
    result: Any = None
    error: str | None = None
    duration_ms: float = Field(default=0, alias="durationMs")


# ============================================================================
# Role Snapshot Types (Accessibility Tree)
# ============================================================================

class RoleNode(BaseModel):
    """角色节点 - 可访问性树节点"""
    model_config = ConfigDict(populate_by_name=True)

    role: str
    name: str | None = None
    value: str | None = None
    description: str | None = None
    focused: bool = False
    disabled: bool = False
    checked: bool | Literal["mixed"] | None = None
    selected: bool | None = None
    expanded: bool | None = None
    level: int | None = None
    children: list["RoleNode"] = Field(default_factory=list)
    # 额外属性
    ref: str | None = None  # 元素引用，用于后续操作


class RoleSnapshotResponse(BaseModel):
    """角色快照响应"""
    model_config = ConfigDict(populate_by_name=True)

    success: bool
    root: RoleNode | None = None
    error: str | None = None
    total_nodes: int = Field(default=0, alias="totalNodes")


# ============================================================================
# CDP Types
# ============================================================================

class CDPSession(BaseModel):
    """CDP 会话信息"""
    model_config = ConfigDict(populate_by_name=True)

    session_id: str = Field(alias="sessionId")
    target_id: str = Field(alias="targetId")
    target_type: str = Field(default="page", alias="targetType")


class CDPMessage(BaseModel):
    """CDP 消息"""
    model_config = ConfigDict(populate_by_name=True)

    id: int | None = None
    method: str | None = None
    params: dict[str, Any] | None = None
    result: dict[str, Any] | None = None
    error: dict[str, Any] | None = None


# ============================================================================
# Extension Relay Types
# ============================================================================

class ExtensionMessage(BaseModel):
    """扩展消息"""
    model_config = ConfigDict(populate_by_name=True)

    type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    id: str | None = None


class ExtensionResponse(BaseModel):
    """扩展响应"""
    model_config = ConfigDict(populate_by_name=True)

    success: bool
    type: str
    data: Any = None
    error: str | None = None


# ============================================================================
# Configuration Types
# ============================================================================

@dataclass
class BrowserConfig:
    """浏览器配置"""
    browser_type: Literal["chromium", "firefox", "webkit"] = "chromium"
    headless: bool = True
    slow_mo: float = 0
    viewport_width: int = 1280
    viewport_height: int = 720
    device_scale_factor: float = 1.0
    user_agent: str | None = None
    locale: str | None = None
    timezone: str | None = None
    geolocation: dict[str, float] | None = None
    permissions: list[str] = field(default_factory=list)
    extra_http_headers: dict[str, str] = field(default_factory=dict)
    # CDP 配置
    cdp_endpoint: str | None = None
    cdp_port: int = 9222
    # Chrome 启动配置
    chrome_path: str | None = None
    chrome_args: list[str] = field(default_factory=list)
    user_data_dir: str | None = None
    # 扩展配置
    extensions: list[str] = field(default_factory=list)
    # 超时配置
    navigation_timeout: float = 30000
    default_timeout: float = 30000


@dataclass
class ServerConfig:
    """浏览器服务器配置"""
    host: str = "127.0.0.1"
    port: int = 9333
    debug: bool = False
    cors_origins: list[str] = field(default_factory=lambda: ["*"])
    max_concurrent_sessions: int = 5


# ============================================================================
# Error Types
# ============================================================================

class BrowserError(Exception):
    """浏览器错误基类"""
    def __init__(self, message: str, code: str = "BROWSER_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


class BrowserNotConnectedError(BrowserError):
    """浏览器未连接错误"""
    def __init__(self, message: str = "Browser is not connected"):
        super().__init__(message, "NOT_CONNECTED")


class BrowserTimeoutError(BrowserError):
    """浏览器超时错误"""
    def __init__(self, message: str = "Operation timed out"):
        super().__init__(message, "TIMEOUT")


class BrowserNavigationError(BrowserError):
    """导航错误"""
    def __init__(self, message: str, url: str | None = None):
        self.url = url
        super().__init__(message, "NAVIGATION_ERROR")


class BrowserActionError(BrowserError):
    """动作执行错误"""
    def __init__(self, message: str, action: str | None = None):
        self.action = action
        super().__init__(message, "ACTION_ERROR")


class BrowserSelectorError(BrowserError):
    """选择器错误"""
    def __init__(self, message: str, selector: str | None = None):
        self.selector = selector
        super().__init__(message, "SELECTOR_ERROR")


# ============================================================================
# Type Exports
# ============================================================================

__all__ = [
    # Enums
    "BrowserAction",
    "MouseButton",
    "KeyModifier",
    # Request Models
    "ActRequest",
    "NavigateRequest",
    "ScreenshotRequest",
    "RoleSnapshotRequest",
    "EvaluateRequest",
    "TabRequest",
    "WaitForRequest",
    # Response Models
    "BrowserStatus",
    "ActResponse",
    "NavigateResponse",
    "ScreenshotResponse",
    "TabInfo",
    "TabsResponse",
    "EvaluateResponse",
    "RoleNode",
    "RoleSnapshotResponse",
    # CDP Types
    "CDPSession",
    "CDPMessage",
    # Extension Types
    "ExtensionMessage",
    "ExtensionResponse",
    # Config Types
    "BrowserConfig",
    "ServerConfig",
    # Error Types
    "BrowserError",
    "BrowserNotConnectedError",
    "BrowserTimeoutError",
    "BrowserNavigationError",
    "BrowserActionError",
    "BrowserSelectorError",
]
