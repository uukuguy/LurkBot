"""
Browser Module - 浏览器自动化模块

对标 MoltBot src/browser/

提供完整的浏览器自动化能力，支持 Playwright 和 CDP。

功能:
- Playwright 会话管理
- CDP (Chrome DevTools Protocol) 支持
- 页面导航和操作
- 截图和角色快照
- 浏览器扩展中继
- HTTP API 服务器

使用示例:

    from lurkbot.browser import PlaywrightSession, playwright_session

    # 使用上下文管理器
    async with playwright_session() as session:
        await session.navigate("https://example.com")
        data = await session.screenshot()

    # 或手动管理
    session = PlaywrightSession()
    await session.launch()
    try:
        await session.navigate("https://example.com")
    finally:
        await session.close()

HTTP 服务器:

    from lurkbot.browser import start_browser_server
    start_browser_server(host="127.0.0.1", port=9333)
"""

from .types import (
    # Enums
    BrowserAction,
    MouseButton,
    KeyModifier,
    # Request Models
    ActRequest,
    NavigateRequest,
    ScreenshotRequest,
    RoleSnapshotRequest,
    EvaluateRequest,
    TabRequest,
    WaitForRequest,
    # Response Models
    BrowserStatus,
    ActResponse,
    NavigateResponse,
    ScreenshotResponse,
    TabInfo,
    TabsResponse,
    EvaluateResponse,
    RoleNode,
    RoleSnapshotResponse,
    # CDP Types
    CDPSession,
    CDPMessage,
    # Extension Types
    ExtensionMessage,
    ExtensionResponse,
    # Config Types
    BrowserConfig,
    ServerConfig,
    # Error Types
    BrowserError,
    BrowserNotConnectedError,
    BrowserTimeoutError,
    BrowserNavigationError,
    BrowserActionError,
    BrowserSelectorError,
)

from .config import (
    load_browser_config,
    load_server_config,
    validate_browser_config,
    detect_chrome_path,
    get_default_user_data_dir,
)

from .chrome import (
    ChromeLaunchOptions,
    ChromeManager,
    get_chrome_version,
    is_chrome_installed,
)

from .cdp import (
    CDPClient,
    create_cdp_session,
    get_targets,
    get_page_targets,
    create_page_target,
    close_target,
    CDPPage,
    CDPRuntime,
    CDPInput,
    CDPNetwork,
    CDPAccessibility,
)

from .playwright_session import (
    PLAYWRIGHT_AVAILABLE,
    PlaywrightSession,
    PlaywrightSessionState,
    playwright_session,
    get_session,
    get_page,
)

from .role_snapshot import (
    RoleSnapshotGenerator,
    get_role_snapshot,
    format_role_tree,
    find_nodes_by_role,
    find_node_by_ref,
    get_interactive_elements,
    summarize_snapshot,
    get_aria_snapshot,
)

from .screenshot import (
    PIL_AVAILABLE,
    ScreenshotOptions,
    capture_screenshot,
    capture_screenshot_base64,
    capture_screenshot_response,
    save_screenshot,
    resize_image,
    crop_image,
    add_highlight_box,
    add_annotation,
    image_to_data_url,
    data_url_to_image,
    get_image_info,
    compare_screenshots,
)

from .extension_relay import (
    ExtensionRelay,
    WebSocketExtensionRelay,
    CDPExtensionRelay,
)

from .server import (
    app,
    create_browser_app,
    run_browser_server,
    start_browser_server,
)


__all__ = [
    # ========== Types ==========
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
    # ========== Config ==========
    "load_browser_config",
    "load_server_config",
    "validate_browser_config",
    "detect_chrome_path",
    "get_default_user_data_dir",
    # ========== Chrome ==========
    "ChromeLaunchOptions",
    "ChromeManager",
    "get_chrome_version",
    "is_chrome_installed",
    # ========== CDP ==========
    "CDPClient",
    "create_cdp_session",
    "get_targets",
    "get_page_targets",
    "create_page_target",
    "close_target",
    "CDPPage",
    "CDPRuntime",
    "CDPInput",
    "CDPNetwork",
    "CDPAccessibility",
    # ========== Playwright ==========
    "PLAYWRIGHT_AVAILABLE",
    "PlaywrightSession",
    "PlaywrightSessionState",
    "playwright_session",
    "get_session",
    "get_page",
    # ========== Role Snapshot ==========
    "RoleSnapshotGenerator",
    "get_role_snapshot",
    "format_role_tree",
    "find_nodes_by_role",
    "find_node_by_ref",
    "get_interactive_elements",
    "summarize_snapshot",
    "get_aria_snapshot",
    # ========== Screenshot ==========
    "PIL_AVAILABLE",
    "ScreenshotOptions",
    "capture_screenshot",
    "capture_screenshot_base64",
    "capture_screenshot_response",
    "save_screenshot",
    "resize_image",
    "crop_image",
    "add_highlight_box",
    "add_annotation",
    "image_to_data_url",
    "data_url_to_image",
    "get_image_info",
    "compare_screenshots",
    # ========== Extension Relay ==========
    "ExtensionRelay",
    "WebSocketExtensionRelay",
    "CDPExtensionRelay",
    # ========== Server ==========
    "app",
    "create_browser_app",
    "run_browser_server",
    "start_browser_server",
]
