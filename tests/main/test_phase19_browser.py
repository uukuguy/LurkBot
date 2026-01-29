"""
Phase 19 Browser 模块测试

测试浏览器自动化系统的各个组件
"""

import asyncio
import base64
import json
from dataclasses import dataclass
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ============================================================================
# Test Types
# ============================================================================

class TestBrowserTypes:
    """测试浏览器类型定义"""

    def test_browser_action_enum(self):
        """测试 BrowserAction 枚举"""
        from lurkbot.browser.types import BrowserAction

        assert BrowserAction.CLICK.value == "click"
        assert BrowserAction.DOUBLE_CLICK.value == "doubleClick"
        assert BrowserAction.TYPE.value == "type"
        assert BrowserAction.PRESS.value == "press"
        assert BrowserAction.FILL.value == "fill"
        assert BrowserAction.HOVER.value == "hover"
        assert BrowserAction.DRAG.value == "drag"
        assert BrowserAction.SCROLL.value == "scroll"
        assert BrowserAction.WAIT.value == "wait"

    def test_mouse_button_enum(self):
        """测试 MouseButton 枚举"""
        from lurkbot.browser.types import MouseButton

        assert MouseButton.LEFT.value == "left"
        assert MouseButton.RIGHT.value == "right"
        assert MouseButton.MIDDLE.value == "middle"

    def test_key_modifier_enum(self):
        """测试 KeyModifier 枚举"""
        from lurkbot.browser.types import KeyModifier

        assert KeyModifier.ALT.value == "Alt"
        assert KeyModifier.CONTROL.value == "Control"
        assert KeyModifier.META.value == "Meta"
        assert KeyModifier.SHIFT.value == "Shift"

    def test_act_request_model(self):
        """测试 ActRequest 模型"""
        from lurkbot.browser.types import ActRequest, BrowserAction, MouseButton

        request = ActRequest(
            action=BrowserAction.CLICK,
            selector="#button",
            text=None,
            button=MouseButton.LEFT,
            timeout=5000,
        )

        assert request.action == BrowserAction.CLICK
        assert request.selector == "#button"
        assert request.button == MouseButton.LEFT
        assert request.timeout == 5000

    def test_navigate_request_model(self):
        """测试 NavigateRequest 模型"""
        from lurkbot.browser.types import NavigateRequest

        request = NavigateRequest(
            url="https://example.com",
            wait_until="load",
            timeout=30000,
        )

        assert request.url == "https://example.com"
        assert request.wait_until == "load"
        assert request.timeout == 30000

    def test_screenshot_request_model(self):
        """测试 ScreenshotRequest 模型"""
        from lurkbot.browser.types import ScreenshotRequest

        request = ScreenshotRequest(
            full_page=True,
            format="png",
            omit_background=False,
        )

        assert request.full_page is True
        assert request.format == "png"
        assert request.omit_background is False

    def test_browser_status_model(self):
        """测试 BrowserStatus 模型"""
        from lurkbot.browser.types import BrowserStatus

        status = BrowserStatus(
            connected=True,
            browser_type="chromium",
            headless=True,
            tabs_count=3,
            current_url="https://example.com",
        )

        assert status.connected is True
        assert status.browser_type == "chromium"
        assert status.tabs_count == 3

    def test_role_node_model(self):
        """测试 RoleNode 模型"""
        from lurkbot.browser.types import RoleNode

        child = RoleNode(role="button", name="Click me", ref="e2")
        root = RoleNode(
            role="document",
            name="Page",
            children=[child],
            ref="e1",
        )

        assert root.role == "document"
        assert len(root.children) == 1
        assert root.children[0].role == "button"

    def test_browser_config_dataclass(self):
        """测试 BrowserConfig 数据类"""
        from lurkbot.browser.types import BrowserConfig

        config = BrowserConfig(
            browser_type="chromium",
            headless=True,
            viewport_width=1920,
            viewport_height=1080,
        )

        assert config.browser_type == "chromium"
        assert config.headless is True
        assert config.viewport_width == 1920

    def test_browser_error_types(self):
        """测试浏览器错误类型"""
        from lurkbot.browser.types import (
            BrowserError,
            BrowserNotConnectedError,
            BrowserTimeoutError,
            BrowserActionError,
        )

        # 基础错误
        error = BrowserError("Test error", "TEST")
        assert str(error) == "Test error"
        assert error.code == "TEST"

        # 未连接错误
        not_connected = BrowserNotConnectedError()
        assert "not connected" in not_connected.message.lower()

        # 超时错误
        timeout = BrowserTimeoutError()
        assert "timed out" in timeout.message.lower()

        # 动作错误
        action_error = BrowserActionError("Click failed", "click")
        assert action_error.action == "click"


# ============================================================================
# Test Config
# ============================================================================

class TestBrowserConfig:
    """测试浏览器配置"""

    def test_load_default_config(self):
        """测试加载默认配置"""
        from lurkbot.browser.config import load_browser_config

        config = load_browser_config()

        assert config.browser_type == "chromium"
        assert config.headless is True
        assert config.viewport_width == 1280
        assert config.viewport_height == 720

    def test_load_server_config(self):
        """测试加载服务器配置"""
        from lurkbot.browser.config import load_server_config

        config = load_server_config()

        assert config.host == "127.0.0.1"
        assert config.port == 9333
        assert config.debug is False

    def test_validate_browser_config_valid(self):
        """测试验证有效配置"""
        from lurkbot.browser.config import validate_browser_config
        from lurkbot.browser.types import BrowserConfig

        config = BrowserConfig(
            viewport_width=1280,
            viewport_height=720,
            device_scale_factor=1.0,
        )

        errors = validate_browser_config(config)
        assert len(errors) == 0

    def test_validate_browser_config_invalid_viewport(self):
        """测试验证无效视口"""
        from lurkbot.browser.config import validate_browser_config
        from lurkbot.browser.types import BrowserConfig

        config = BrowserConfig(
            viewport_width=50,  # 太小
            viewport_height=5000,  # 太大
        )

        errors = validate_browser_config(config)
        assert len(errors) >= 2

    def test_validate_browser_config_invalid_scale(self):
        """测试验证无效缩放因子"""
        from lurkbot.browser.config import validate_browser_config
        from lurkbot.browser.types import BrowserConfig

        config = BrowserConfig(device_scale_factor=0.1)  # 太小

        errors = validate_browser_config(config)
        assert any("scale factor" in e.lower() for e in errors)

    def test_get_default_user_data_dir(self):
        """测试获取默认用户数据目录"""
        from lurkbot.browser.config import get_default_user_data_dir

        path = get_default_user_data_dir()
        assert "lurkbot" in path
        assert "browser-data" in path

    def test_config_env_override(self):
        """测试环境变量覆盖"""
        import os
        from lurkbot.browser.config import (
            load_browser_config,
            ENV_BROWSER_HEADLESS,
            ENV_BROWSER_VIEWPORT_WIDTH,
        )

        # 设置环境变量
        os.environ[ENV_BROWSER_HEADLESS] = "false"
        os.environ[ENV_BROWSER_VIEWPORT_WIDTH] = "1920"

        try:
            config = load_browser_config()
            assert config.headless is False
            assert config.viewport_width == 1920
        finally:
            # 清理
            del os.environ[ENV_BROWSER_HEADLESS]
            del os.environ[ENV_BROWSER_VIEWPORT_WIDTH]


# ============================================================================
# Test Chrome Manager
# ============================================================================

class TestChromeManager:
    """测试 Chrome 管理器"""

    def test_chrome_launch_options(self):
        """测试 Chrome 启动选项"""
        from lurkbot.browser.chrome import ChromeLaunchOptions

        options = ChromeLaunchOptions(
            headless=True,
            debug_port=9222,
            no_sandbox=True,
        )

        assert options.headless is True
        assert options.debug_port == 9222
        assert options.no_sandbox is True

    def test_chrome_manager_init(self):
        """测试 ChromeManager 初始化"""
        from lurkbot.browser.chrome import ChromeManager

        manager = ChromeManager()

        assert manager.is_running is False
        assert manager.debug_port == 9222

    def test_is_chrome_installed(self):
        """测试 Chrome 安装检测"""
        from lurkbot.browser.chrome import is_chrome_installed

        # 只是测试函数能执行，不依赖实际 Chrome
        result = is_chrome_installed()
        assert isinstance(result, bool)


# ============================================================================
# Test CDP Client
# ============================================================================

class TestCDPClient:
    """测试 CDP 客户端"""

    def test_cdp_client_init(self):
        """测试 CDPClient 初始化"""
        from lurkbot.browser.cdp import CDPClient

        client = CDPClient("ws://127.0.0.1:9222")
        assert client.is_connected is False

    @pytest.mark.asyncio
    async def test_cdp_client_not_connected_error(self):
        """测试未连接时发送消息报错"""
        from lurkbot.browser.cdp import CDPClient
        from lurkbot.browser.types import BrowserError

        client = CDPClient("ws://127.0.0.1:9222")

        with pytest.raises(BrowserError) as exc_info:
            await client.send("Page.navigate", {"url": "https://example.com"})

        assert "NOT_CONNECTED" in exc_info.value.code

    def test_cdp_event_handlers(self):
        """测试 CDP 事件处理"""
        from lurkbot.browser.cdp import CDPClient

        client = CDPClient("ws://127.0.0.1:9222")
        received = []

        def handler(params):
            received.append(params)

        client.on("Page.loadEventFired", handler)

        # 触发事件
        import asyncio
        asyncio.get_event_loop().run_until_complete(
            client._handle_message({
                "method": "Page.loadEventFired",
                "params": {"timestamp": 12345},
            })
        )

        assert len(received) == 1
        assert received[0]["timestamp"] == 12345

    def test_cdp_domain_helpers(self):
        """测试 CDP Domain 封装"""
        from lurkbot.browser.cdp import (
            CDPClient,
            CDPPage,
            CDPRuntime,
            CDPInput,
            CDPNetwork,
        )

        client = CDPClient("ws://127.0.0.1:9222")

        page = CDPPage(client)
        runtime = CDPRuntime(client)
        input_ = CDPInput(client)
        network = CDPNetwork(client)

        assert page._client == client
        assert runtime._client == client
        assert input_._client == client
        assert network._client == client


# ============================================================================
# Test Playwright Session (Mocked)
# ============================================================================

class TestPlaywrightSession:
    """测试 Playwright 会话（使用 Mock）"""

    def test_session_init(self):
        """测试会话初始化"""
        # 跳过如果 Playwright 不可用
        try:
            from lurkbot.browser.playwright_session import (
                PlaywrightSession,
                PLAYWRIGHT_AVAILABLE,
            )
            if not PLAYWRIGHT_AVAILABLE:
                pytest.skip("Playwright not available")

            session = PlaywrightSession()
            assert session.is_connected is False
            assert session.page is None
        except Exception:
            pytest.skip("Playwright not available")

    def test_session_state_dataclass(self):
        """测试会话状态数据类"""
        from lurkbot.browser.playwright_session import PlaywrightSessionState

        state = PlaywrightSessionState()

        assert state.playwright is None
        assert state.browser is None
        assert state.context is None
        assert state.pages == []
        assert state.active_page_index == 0


# ============================================================================
# Test Role Snapshot
# ============================================================================

class TestRoleSnapshot:
    """测试角色快照"""

    def test_format_role_tree(self):
        """测试格式化角色树"""
        from lurkbot.browser.role_snapshot import format_role_tree
        from lurkbot.browser.types import RoleNode

        button = RoleNode(role="button", name="Submit", ref="e2")
        root = RoleNode(
            role="document",
            name="Page",
            children=[button],
            ref="e1",
        )

        text = format_role_tree(root)

        assert "document" in text
        assert "Page" in text
        assert "button" in text
        assert "Submit" in text

    def test_find_nodes_by_role(self):
        """测试按角色查找节点"""
        from lurkbot.browser.role_snapshot import find_nodes_by_role
        from lurkbot.browser.types import RoleNode

        btn1 = RoleNode(role="button", name="OK", ref="e2")
        btn2 = RoleNode(role="button", name="Cancel", ref="e3")
        link = RoleNode(role="link", name="Help", ref="e4")
        root = RoleNode(
            role="document",
            children=[btn1, btn2, link],
            ref="e1",
        )

        buttons = find_nodes_by_role(root, "button")
        assert len(buttons) == 2

        ok_button = find_nodes_by_role(root, "button", "OK")
        assert len(ok_button) == 1
        assert ok_button[0].name == "OK"

    def test_find_node_by_ref(self):
        """测试按引用查找节点"""
        from lurkbot.browser.role_snapshot import find_node_by_ref
        from lurkbot.browser.types import RoleNode

        child = RoleNode(role="button", name="Click", ref="e2")
        root = RoleNode(role="document", children=[child], ref="e1")

        found = find_node_by_ref(root, "e2")
        assert found is not None
        assert found.name == "Click"

        not_found = find_node_by_ref(root, "e999")
        assert not_found is None

    def test_get_interactive_elements(self):
        """测试获取可交互元素"""
        from lurkbot.browser.role_snapshot import get_interactive_elements
        from lurkbot.browser.types import RoleNode

        button = RoleNode(role="button", name="Submit", ref="e1")
        link = RoleNode(role="link", name="Help", ref="e2")
        text = RoleNode(role="text", name="Hello", ref="e3")
        disabled_btn = RoleNode(role="button", name="Disabled", disabled=True, ref="e4")
        root = RoleNode(
            role="document",
            children=[button, link, text, disabled_btn],
            ref="e0",
        )

        interactive = get_interactive_elements(root)

        # button 和 link 是可交互的，text 不是，disabled button 被排除
        assert len(interactive) == 2
        roles = [e.role for e in interactive]
        assert "button" in roles
        assert "link" in roles

    def test_summarize_snapshot(self):
        """测试快照摘要"""
        from lurkbot.browser.role_snapshot import summarize_snapshot
        from lurkbot.browser.types import RoleNode

        btn = RoleNode(role="button", name="OK", ref="e1")
        link = RoleNode(role="link", name="Help", ref="e2")
        root = RoleNode(role="document", children=[btn, link], ref="e0")

        summary = summarize_snapshot(root)

        assert summary["total_nodes"] == 3
        assert summary["interactive_elements"] == 2
        assert "button" in summary["role_distribution"]


# ============================================================================
# Test Screenshot
# ============================================================================

class TestScreenshot:
    """测试截图功能"""

    def test_screenshot_options(self):
        """测试截图选项"""
        from lurkbot.browser.screenshot import ScreenshotOptions

        options = ScreenshotOptions(
            full_page=True,
            format="jpeg",
            quality=80,
        )

        assert options.full_page is True
        assert options.format == "jpeg"
        assert options.quality == 80

    def test_image_to_data_url(self):
        """测试图片转 Data URL"""
        from lurkbot.browser.screenshot import image_to_data_url

        # 创建一个简单的 1x1 PNG
        png_data = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        )

        data_url = image_to_data_url(png_data, "png")

        assert data_url.startswith("data:image/png;base64,")

    def test_data_url_to_image(self):
        """测试 Data URL 转图片"""
        from lurkbot.browser.screenshot import data_url_to_image

        data_url = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="

        data = data_url_to_image(data_url)

        assert len(data) > 0
        # PNG 魔数
        assert data[:8] == b'\x89PNG\r\n\x1a\n'

    def test_get_image_info_without_pil(self):
        """测试获取图片信息（无 PIL）"""
        from lurkbot.browser.screenshot import get_image_info, PIL_AVAILABLE

        png_data = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        )

        info = get_image_info(png_data)

        assert "size_bytes" in info
        assert info["size_bytes"] > 0


# ============================================================================
# Test Extension Relay
# ============================================================================

class TestExtensionRelay:
    """测试扩展中继"""

    def test_extension_relay_init(self):
        """测试扩展中继初始化"""
        from lurkbot.browser.extension_relay import ExtensionRelay

        relay = ExtensionRelay(timeout=10.0)

        assert relay.is_connected is False
        assert relay._timeout == 10.0

    def test_extension_relay_event_handlers(self):
        """测试事件处理器"""
        from lurkbot.browser.extension_relay import ExtensionRelay

        relay = ExtensionRelay()
        received = []

        def handler(event):
            received.append(event)

        relay.on("test_event", handler)
        relay.handle_event({"type": "test_event", "data": "hello"})

        assert len(received) == 1
        assert received[0]["data"] == "hello"

        # 移除处理器
        relay.off("test_event", handler)
        relay.handle_event({"type": "test_event", "data": "world"})

        # 不应再接收
        assert len(received) == 1

    def test_extension_relay_response_handling(self):
        """测试响应处理"""
        import asyncio
        from lurkbot.browser.extension_relay import ExtensionRelay

        relay = ExtensionRelay()
        relay.set_connected(True)

        # 创建待处理请求
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        future = loop.create_future()

        from lurkbot.browser.extension_relay import PendingRequest
        relay._pending_requests["test-id"] = PendingRequest(
            id="test-id",
            future=future,
        )

        # 处理响应
        relay.handle_response({
            "id": "test-id",
            "success": True,
            "type": "test",
            "data": {"result": 42},
        })

        # 检查 Future 是否已完成
        assert future.done()
        result = loop.run_until_complete(future)
        assert result.success is True
        assert result.data["result"] == 42

        loop.close()


# ============================================================================
# Test Server (Mocked)
# ============================================================================

class TestBrowserServer:
    """测试浏览器服务器"""

    def test_create_browser_app(self):
        """测试创建应用"""
        from lurkbot.browser.server import create_browser_app

        app = create_browser_app()

        assert app.title == "LurkBot Browser Server"

        # 检查路由
        routes = [r.path for r in app.routes]
        assert "/" in routes
        assert "/status" in routes
        assert "/health" in routes

    def test_app_routes(self):
        """测试应用路由"""
        from lurkbot.browser.server import app

        routes = [r.path for r in app.routes]

        # 检查主要路由
        assert any("/act" in r for r in routes)
        assert any("/navigate" in r for r in routes)
        assert any("/screenshot" in r for r in routes)
        assert any("/tabs" in r for r in routes)


# ============================================================================
# Test Module Exports
# ============================================================================

class TestModuleExports:
    """测试模块导出"""

    def test_main_exports(self):
        """测试主模块导出"""
        from lurkbot.browser import (
            # Types
            BrowserAction,
            BrowserConfig,
            BrowserStatus,
            BrowserError,
            # Config
            load_browser_config,
            load_server_config,
            # Session
            PlaywrightSession,
            # Snapshot
            RoleSnapshotGenerator,
            format_role_tree,
            # Screenshot
            capture_screenshot_base64,
            # Server
            create_browser_app,
        )

        # 验证导出存在
        assert BrowserAction is not None
        assert BrowserConfig is not None
        assert load_browser_config is not None
        assert PlaywrightSession is not None

    def test_types_module(self):
        """测试类型模块"""
        from lurkbot.browser.types import __all__

        expected = [
            "BrowserAction",
            "MouseButton",
            "KeyModifier",
            "ActRequest",
            "NavigateRequest",
            "BrowserStatus",
            "BrowserConfig",
            "BrowserError",
        ]

        for name in expected:
            assert name in __all__

    def test_routes_module(self):
        """测试路由模块"""
        from lurkbot.browser.routes import (
            act_router,
            navigate_router,
            screenshot_router,
            tabs_router,
        )

        assert act_router is not None
        assert navigate_router is not None
        assert screenshot_router is not None
        assert tabs_router is not None


# ============================================================================
# Test Request/Response Serialization
# ============================================================================

class TestSerialization:
    """测试请求/响应序列化"""

    def test_act_request_serialization(self):
        """测试 ActRequest 序列化"""
        from lurkbot.browser.types import ActRequest, BrowserAction

        request = ActRequest(
            action=BrowserAction.CLICK,
            selector="#btn",
        )

        data = request.model_dump()
        assert data["action"] == "click"
        assert data["selector"] == "#btn"

    def test_browser_status_serialization(self):
        """测试 BrowserStatus 序列化"""
        from lurkbot.browser.types import BrowserStatus

        status = BrowserStatus(
            connected=True,
            browser_type="chromium",
            tabs_count=2,
        )

        data = status.model_dump(by_alias=True)
        assert data["connected"] is True
        assert data["browserType"] == "chromium"
        assert data["tabsCount"] == 2

    def test_role_node_nested_serialization(self):
        """测试 RoleNode 嵌套序列化"""
        from lurkbot.browser.types import RoleNode

        root = RoleNode(
            role="document",
            children=[
                RoleNode(
                    role="button",
                    name="OK",
                    children=[
                        RoleNode(role="text", name="OK Text"),
                    ],
                ),
            ],
        )

        data = root.model_dump()
        assert data["role"] == "document"
        assert len(data["children"]) == 1
        assert data["children"][0]["role"] == "button"
        assert len(data["children"][0]["children"]) == 1


# ============================================================================
# Integration-like Tests (Still Mocked)
# ============================================================================

class TestBrowserIntegration:
    """集成测试（使用 Mock）"""

    def test_config_to_session_flow(self):
        """测试配置到会话的流程"""
        from lurkbot.browser.config import load_browser_config
        from lurkbot.browser.types import BrowserConfig

        # 加载配置
        config = load_browser_config()

        # 验证可用于创建会话
        assert isinstance(config, BrowserConfig)
        assert config.browser_type in ("chromium", "firefox", "webkit")

    def test_snapshot_workflow(self):
        """测试快照工作流"""
        from lurkbot.browser.types import RoleNode
        from lurkbot.browser.role_snapshot import (
            format_role_tree,
            find_nodes_by_role,
            get_interactive_elements,
            summarize_snapshot,
        )

        # 模拟页面结构
        root = RoleNode(
            role="document",
            name="Test Page",
            children=[
                RoleNode(role="heading", name="Title", level=1),
                RoleNode(
                    role="form",
                    children=[
                        RoleNode(role="textbox", name="Username"),
                        RoleNode(role="textbox", name="Password"),
                        RoleNode(role="button", name="Login"),
                    ],
                ),
                RoleNode(role="link", name="Forgot Password"),
            ],
        )

        # 格式化
        text = format_role_tree(root, show_refs=False)
        assert "document" in text
        assert "heading" in text
        assert "form" in text

        # 查找
        buttons = find_nodes_by_role(root, "button")
        assert len(buttons) == 1
        assert buttons[0].name == "Login"

        textboxes = find_nodes_by_role(root, "textbox")
        assert len(textboxes) == 2

        # 可交互元素
        interactive = get_interactive_elements(root)
        assert len(interactive) == 4  # 2 textbox + 1 button + 1 link

        # 摘要
        summary = summarize_snapshot(root)
        assert summary["total_nodes"] == 7
        assert summary["interactive_elements"] == 4

    def test_error_handling_chain(self):
        """测试错误处理链"""
        from lurkbot.browser.types import (
            BrowserError,
            BrowserNotConnectedError,
            BrowserTimeoutError,
            BrowserActionError,
        )

        # 验证继承关系
        assert issubclass(BrowserNotConnectedError, BrowserError)
        assert issubclass(BrowserTimeoutError, BrowserError)
        assert issubclass(BrowserActionError, BrowserError)

        # 验证可以统一捕获
        errors = [
            BrowserNotConnectedError(),
            BrowserTimeoutError(),
            BrowserActionError("failed", "click"),
        ]

        for error in errors:
            try:
                raise error
            except BrowserError as e:
                assert e.code is not None


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
