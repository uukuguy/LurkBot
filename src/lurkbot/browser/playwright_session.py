"""
Playwright Session - Playwright 会话管理

对标 MoltBot src/browser/playwright_session.ts
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any, AsyncIterator

from loguru import logger

from .config import load_browser_config
from .types import (
    BrowserAction,
    BrowserConfig,
    BrowserError,
    BrowserNotConnectedError,
    BrowserStatus,
    MouseButton,
)

# Playwright 导入（可选依赖）
try:
    from playwright.async_api import (
        Browser,
        BrowserContext,
        Page,
        Playwright,
        async_playwright,
    )
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    Browser = Any
    BrowserContext = Any
    Page = Any
    Playwright = Any


# ============================================================================
# Session State
# ============================================================================

@dataclass
class PlaywrightSessionState:
    """Playwright 会话状态"""
    playwright: Playwright | None = None
    browser: Browser | None = None
    context: BrowserContext | None = None
    pages: list[Page] = field(default_factory=list)
    active_page_index: int = 0


# ============================================================================
# Playwright Session Manager
# ============================================================================

class PlaywrightSession:
    """
    Playwright 会话管理器

    提供高级 API 来管理浏览器实例、上下文和页面。
    支持通过 CDP 连接到已有浏览器或启动新浏览器。
    """

    def __init__(self, config: BrowserConfig | None = None):
        """
        初始化 Playwright 会话

        Args:
            config: 浏览器配置
        """
        if not PLAYWRIGHT_AVAILABLE:
            raise BrowserError(
                "Playwright is not installed. Run: pip install playwright",
                "PLAYWRIGHT_NOT_AVAILABLE",
            )

        self._config = config or load_browser_config()
        self._state = PlaywrightSessionState()
        self._lock = asyncio.Lock()

    @property
    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self._state.browser is not None and self._state.browser.is_connected()

    @property
    def page(self) -> Page | None:
        """获取当前活动页面"""
        if not self._state.pages:
            return None
        idx = min(self._state.active_page_index, len(self._state.pages) - 1)
        return self._state.pages[idx] if idx >= 0 else None

    @property
    def pages(self) -> list[Page]:
        """获取所有页面"""
        return self._state.pages.copy()

    @property
    def browser(self) -> Browser | None:
        """获取浏览器实例"""
        return self._state.browser

    @property
    def context(self) -> BrowserContext | None:
        """获取浏览器上下文"""
        return self._state.context

    async def launch(self) -> None:
        """启动新浏览器"""
        async with self._lock:
            if self.is_connected:
                logger.warning("Browser already connected")
                return

            logger.info(f"Launching {self._config.browser_type} browser")

            self._state.playwright = await async_playwright().start()

            # 选择浏览器类型
            browser_type = getattr(self._state.playwright, self._config.browser_type)

            # 启动选项
            launch_options = {
                "headless": self._config.headless,
                "slow_mo": self._config.slow_mo,
            }

            if self._config.chrome_args:
                launch_options["args"] = self._config.chrome_args

            if self._config.chrome_path:
                launch_options["executable_path"] = self._config.chrome_path

            # 启动浏览器
            self._state.browser = await browser_type.launch(**launch_options)

            # 创建上下文
            await self._create_context()

            logger.info("Browser launched successfully")

    async def connect_cdp(self, endpoint: str | None = None) -> None:
        """
        通过 CDP 连接到已有浏览器

        Args:
            endpoint: CDP WebSocket 端点（默认从配置读取）
        """
        async with self._lock:
            if self.is_connected:
                logger.warning("Browser already connected")
                return

            cdp_endpoint = endpoint or self._config.cdp_endpoint
            if not cdp_endpoint:
                cdp_endpoint = f"http://127.0.0.1:{self._config.cdp_port}"

            logger.info(f"Connecting to CDP: {cdp_endpoint}")

            self._state.playwright = await async_playwright().start()

            # 通过 CDP 连接
            self._state.browser = await self._state.playwright.chromium.connect_over_cdp(
                cdp_endpoint,
                slow_mo=self._config.slow_mo,
            )

            # 获取默认上下文
            contexts = self._state.browser.contexts
            if contexts:
                self._state.context = contexts[0]
                self._state.pages = list(self._state.context.pages)
            else:
                await self._create_context()

            logger.info("Connected to browser via CDP")

    async def close(self) -> None:
        """关闭浏览器"""
        async with self._lock:
            logger.info("Closing browser session")

            self._state.pages.clear()
            self._state.active_page_index = 0

            if self._state.context:
                try:
                    await self._state.context.close()
                except Exception as e:
                    logger.debug(f"Error closing context: {e}")
                self._state.context = None

            if self._state.browser:
                try:
                    await self._state.browser.close()
                except Exception as e:
                    logger.debug(f"Error closing browser: {e}")
                self._state.browser = None

            if self._state.playwright:
                try:
                    await self._state.playwright.stop()
                except Exception as e:
                    logger.debug(f"Error stopping playwright: {e}")
                self._state.playwright = None

            logger.info("Browser session closed")

    async def _create_context(self) -> None:
        """创建浏览器上下文"""
        if not self._state.browser:
            raise BrowserNotConnectedError()

        context_options = {
            "viewport": {
                "width": self._config.viewport_width,
                "height": self._config.viewport_height,
            },
            "device_scale_factor": self._config.device_scale_factor,
        }

        if self._config.user_agent:
            context_options["user_agent"] = self._config.user_agent

        if self._config.locale:
            context_options["locale"] = self._config.locale

        if self._config.timezone:
            context_options["timezone_id"] = self._config.timezone

        if self._config.geolocation:
            context_options["geolocation"] = self._config.geolocation
            context_options["permissions"] = ["geolocation"]

        if self._config.permissions:
            context_options["permissions"] = self._config.permissions

        if self._config.extra_http_headers:
            context_options["extra_http_headers"] = self._config.extra_http_headers

        self._state.context = await self._state.browser.new_context(**context_options)

        # 设置默认超时
        self._state.context.set_default_timeout(self._config.default_timeout)
        self._state.context.set_default_navigation_timeout(self._config.navigation_timeout)

        # 创建初始页面
        page = await self._state.context.new_page()
        self._state.pages.append(page)
        self._state.active_page_index = 0

    async def get_status(self) -> BrowserStatus:
        """获取浏览器状态"""
        if not self.is_connected:
            return BrowserStatus(
                connected=False,
                browser_type=self._config.browser_type,
                headless=self._config.headless,
            )

        current_url = None
        if self.page:
            try:
                current_url = self.page.url
            except Exception:
                pass

        version = None
        if self._state.browser:
            try:
                version = self._state.browser.version
            except Exception:
                pass

        return BrowserStatus(
            connected=True,
            browser_type=self._config.browser_type,
            headless=self._config.headless,
            viewport={
                "width": self._config.viewport_width,
                "height": self._config.viewport_height,
            },
            tabs_count=len(self._state.pages),
            current_url=current_url,
            version=version,
        )

    # ========================================================================
    # Page Management
    # ========================================================================

    async def new_page(self, url: str | None = None) -> Page:
        """
        创建新页面

        Args:
            url: 可选的初始 URL

        Returns:
            新页面
        """
        if not self._state.context:
            raise BrowserNotConnectedError()

        page = await self._state.context.new_page()
        self._state.pages.append(page)
        self._state.active_page_index = len(self._state.pages) - 1

        if url:
            await page.goto(url)

        return page

    async def close_page(self, index: int | None = None) -> None:
        """
        关闭页面

        Args:
            index: 页面索引（None 表示当前页面）
        """
        if not self._state.pages:
            return

        idx = index if index is not None else self._state.active_page_index
        if 0 <= idx < len(self._state.pages):
            page = self._state.pages.pop(idx)
            await page.close()

            # 调整活动页面索引
            if self._state.pages:
                self._state.active_page_index = min(
                    self._state.active_page_index,
                    len(self._state.pages) - 1,
                )
            else:
                self._state.active_page_index = 0

    def switch_to_page(self, index: int) -> Page | None:
        """
        切换到指定页面

        Args:
            index: 页面索引

        Returns:
            目标页面或 None
        """
        if 0 <= index < len(self._state.pages):
            self._state.active_page_index = index
            return self._state.pages[index]
        return None

    # ========================================================================
    # Navigation
    # ========================================================================

    async def navigate(
        self,
        url: str,
        wait_until: str = "load",
        timeout: float | None = None,
    ) -> dict[str, Any]:
        """
        导航到 URL

        Args:
            url: 目标 URL
            wait_until: 等待条件
            timeout: 超时时间

        Returns:
            导航结果
        """
        page = self.page
        if not page:
            raise BrowserNotConnectedError()

        response = await page.goto(
            url,
            wait_until=wait_until,
            timeout=timeout or self._config.navigation_timeout,
        )

        return {
            "url": page.url,
            "title": await page.title(),
            "status": response.status if response else None,
        }

    async def reload(self, wait_until: str = "load") -> None:
        """重新加载页面"""
        page = self.page
        if not page:
            raise BrowserNotConnectedError()

        await page.reload(wait_until=wait_until)

    async def go_back(self) -> None:
        """后退"""
        page = self.page
        if page:
            await page.go_back()

    async def go_forward(self) -> None:
        """前进"""
        page = self.page
        if page:
            await page.go_forward()

    # ========================================================================
    # Actions
    # ========================================================================

    async def click(
        self,
        selector: str,
        button: str = "left",
        click_count: int = 1,
        delay: float = 0,
        position: dict | None = None,
        modifiers: list[str] | None = None,
        force: bool = False,
        timeout: float | None = None,
    ) -> None:
        """点击元素"""
        page = self.page
        if not page:
            raise BrowserNotConnectedError()

        options = {
            "button": button,
            "click_count": click_count,
            "delay": delay,
            "force": force,
        }

        if position:
            options["position"] = position

        if modifiers:
            options["modifiers"] = modifiers

        if timeout:
            options["timeout"] = timeout

        await page.click(selector, **options)

    async def double_click(
        self,
        selector: str,
        **kwargs,
    ) -> None:
        """双击元素"""
        page = self.page
        if not page:
            raise BrowserNotConnectedError()

        await page.dblclick(selector, **kwargs)

    async def type(
        self,
        selector: str,
        text: str,
        delay: float = 0,
        timeout: float | None = None,
    ) -> None:
        """输入文本"""
        page = self.page
        if not page:
            raise BrowserNotConnectedError()

        await page.type(selector, text, delay=delay, timeout=timeout)

    async def fill(
        self,
        selector: str,
        value: str,
        force: bool = False,
        timeout: float | None = None,
    ) -> None:
        """填充表单字段"""
        page = self.page
        if not page:
            raise BrowserNotConnectedError()

        await page.fill(selector, value, force=force, timeout=timeout)

    async def press(
        self,
        selector: str | None,
        key: str,
        delay: float = 0,
        timeout: float | None = None,
    ) -> None:
        """按键"""
        page = self.page
        if not page:
            raise BrowserNotConnectedError()

        if selector:
            await page.press(selector, key, delay=delay, timeout=timeout)
        else:
            await page.keyboard.press(key, delay=delay)

    async def hover(
        self,
        selector: str,
        position: dict | None = None,
        force: bool = False,
        timeout: float | None = None,
    ) -> None:
        """悬停"""
        page = self.page
        if not page:
            raise BrowserNotConnectedError()

        await page.hover(selector, position=position, force=force, timeout=timeout)

    async def select_option(
        self,
        selector: str,
        value: str | list[str] | None = None,
        label: str | list[str] | None = None,
        index: int | list[int] | None = None,
        timeout: float | None = None,
    ) -> list[str]:
        """选择下拉选项"""
        page = self.page
        if not page:
            raise BrowserNotConnectedError()

        options = {}
        if value:
            options["value"] = value
        if label:
            options["label"] = label
        if index is not None:
            options["index"] = index
        if timeout:
            options["timeout"] = timeout

        return await page.select_option(selector, **options)

    async def check(self, selector: str, timeout: float | None = None) -> None:
        """勾选复选框"""
        page = self.page
        if not page:
            raise BrowserNotConnectedError()

        await page.check(selector, timeout=timeout)

    async def uncheck(self, selector: str, timeout: float | None = None) -> None:
        """取消勾选"""
        page = self.page
        if not page:
            raise BrowserNotConnectedError()

        await page.uncheck(selector, timeout=timeout)

    async def drag(
        self,
        source: str,
        target: str,
        source_position: dict | None = None,
        target_position: dict | None = None,
        force: bool = False,
        timeout: float | None = None,
    ) -> None:
        """拖拽"""
        page = self.page
        if not page:
            raise BrowserNotConnectedError()

        await page.drag_and_drop(
            source,
            target,
            source_position=source_position,
            target_position=target_position,
            force=force,
            timeout=timeout,
        )

    async def scroll(
        self,
        selector: str | None = None,
        x: float = 0,
        y: float = 0,
    ) -> None:
        """滚动"""
        page = self.page
        if not page:
            raise BrowserNotConnectedError()

        if selector:
            element = page.locator(selector)
            await element.scroll_into_view_if_needed()
        else:
            await page.mouse.wheel(x, y)

    async def focus(self, selector: str, timeout: float | None = None) -> None:
        """聚焦元素"""
        page = self.page
        if not page:
            raise BrowserNotConnectedError()

        await page.focus(selector, timeout=timeout)

    # ========================================================================
    # Evaluation
    # ========================================================================

    async def evaluate(
        self,
        expression: str,
        arg: Any = None,
    ) -> Any:
        """
        执行 JavaScript

        Args:
            expression: JavaScript 表达式
            arg: 可选参数

        Returns:
            执行结果
        """
        page = self.page
        if not page:
            raise BrowserNotConnectedError()

        return await page.evaluate(expression, arg)

    # ========================================================================
    # Screenshot
    # ========================================================================

    async def screenshot(
        self,
        full_page: bool = False,
        selector: str | None = None,
        format: str = "png",
        quality: int | None = None,
        omit_background: bool = False,
    ) -> bytes:
        """
        截图

        Args:
            full_page: 是否截取整页
            selector: 元素选择器（截取特定元素）
            format: 图片格式
            quality: 图片质量（仅 jpeg）
            omit_background: 是否忽略背景

        Returns:
            图片数据
        """
        page = self.page
        if not page:
            raise BrowserNotConnectedError()

        options = {
            "type": format,
            "omit_background": omit_background,
        }

        if format == "jpeg" and quality:
            options["quality"] = quality

        if selector:
            element = page.locator(selector)
            return await element.screenshot(**options)
        else:
            options["full_page"] = full_page
            return await page.screenshot(**options)

    # ========================================================================
    # Wait
    # ========================================================================

    async def wait_for_selector(
        self,
        selector: str,
        state: str = "visible",
        timeout: float | None = None,
    ) -> Any:
        """等待选择器"""
        page = self.page
        if not page:
            raise BrowserNotConnectedError()

        return await page.wait_for_selector(selector, state=state, timeout=timeout)

    async def wait_for_load_state(
        self,
        state: str = "load",
        timeout: float | None = None,
    ) -> None:
        """等待加载状态"""
        page = self.page
        if not page:
            raise BrowserNotConnectedError()

        await page.wait_for_load_state(state, timeout=timeout)

    async def wait_for_url(
        self,
        url: str,
        timeout: float | None = None,
    ) -> None:
        """等待 URL"""
        page = self.page
        if not page:
            raise BrowserNotConnectedError()

        await page.wait_for_url(url, timeout=timeout)


# ============================================================================
# Context Manager
# ============================================================================

@asynccontextmanager
async def playwright_session(
    config: BrowserConfig | None = None,
    cdp_endpoint: str | None = None,
) -> AsyncIterator[PlaywrightSession]:
    """
    Playwright 会话上下文管理器

    Args:
        config: 浏览器配置
        cdp_endpoint: CDP 端点（如果提供则连接而非启动）

    Yields:
        PlaywrightSession 实例
    """
    session = PlaywrightSession(config)

    try:
        if cdp_endpoint:
            await session.connect_cdp(cdp_endpoint)
        else:
            await session.launch()
        yield session
    finally:
        await session.close()


# ============================================================================
# Global Session (Singleton)
# ============================================================================

_global_session: PlaywrightSession | None = None
_global_lock = asyncio.Lock()


async def get_session(
    config: BrowserConfig | None = None,
) -> PlaywrightSession:
    """
    获取全局 Playwright 会话

    Args:
        config: 浏览器配置（仅首次调用有效）

    Returns:
        PlaywrightSession 实例
    """
    global _global_session

    async with _global_lock:
        if _global_session is None or not _global_session.is_connected:
            _global_session = PlaywrightSession(config)
        return _global_session


async def get_page() -> Page:
    """
    获取当前页面（快捷方式）

    Returns:
        当前活动页面

    Raises:
        BrowserNotConnectedError: 如果未连接
    """
    session = await get_session()
    page = session.page
    if not page:
        raise BrowserNotConnectedError()
    return page


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    "PLAYWRIGHT_AVAILABLE",
    "PlaywrightSession",
    "PlaywrightSessionState",
    "playwright_session",
    "get_session",
    "get_page",
]
