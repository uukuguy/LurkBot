"""Browser automation tool using Playwright."""

from pathlib import Path
from typing import Any

from loguru import logger
from playwright.async_api import async_playwright

from lurkbot.tools.base import SessionType, Tool, ToolPolicy, ToolResult


class BrowserTool(Tool):
    """Browser automation tool for web navigation and scraping."""

    def __init__(self) -> None:
        """Initialize browser tool."""
        policy = ToolPolicy(
            allowed_session_types={SessionType.MAIN, SessionType.DM},
            requires_approval=False,
            max_execution_time=60,  # Browser operations may take longer
        )
        super().__init__(
            name="browser",
            description=(
                "Automate browser interactions. Navigate to URLs, take screenshots, "
                "and extract text content from web pages."
            ),
            policy=policy,
        )

    async def execute(
        self,
        arguments: dict[str, Any],
        workspace: str,
        session_type: SessionType,
    ) -> ToolResult:
        """Execute browser action.

        Args:
            arguments: Tool parameters (action, url, selector, etc.)
            workspace: Working directory (for screenshot paths)
            session_type: Session type (for policy checking)

        Returns:
            Tool execution result
        """
        action = arguments.get("action")
        if not action:
            return ToolResult(success=False, error="Missing required parameter: action")

        try:
            if action == "navigate":
                return await self._navigate(arguments, workspace)
            elif action == "screenshot":
                return await self._screenshot(arguments, workspace)
            elif action == "extract_text":
                return await self._extract_text(arguments)
            elif action == "get_html":
                return await self._get_html(arguments)
            else:
                return ToolResult(success=False, error=f"Unknown action: {action}")
        except Exception as e:
            logger.exception("Browser tool error")
            return ToolResult(success=False, error=f"Browser error: {str(e)}")

    async def _navigate(self, arguments: dict[str, Any], workspace: str) -> ToolResult:
        """Navigate to URL."""
        url = arguments.get("url")
        if not url:
            return ToolResult(success=False, error="Missing required parameter: url")

        timeout = arguments.get("timeout", 30000)

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            try:
                page = await browser.new_page()
                await page.goto(url, timeout=timeout)

                title = await page.title()
                logger.info(f"Navigated to {url} (title: {title})")

                return ToolResult(success=True, output=f"Navigated to {url}\nTitle: {title}")
            finally:
                await browser.close()

    async def _screenshot(self, arguments: dict[str, Any], workspace: str) -> ToolResult:
        """Take screenshot."""
        url = arguments.get("url")
        if not url:
            return ToolResult(success=False, error="Missing required parameter: url")

        selector = arguments.get("selector")
        screenshot_path = arguments.get("screenshot_path")
        full_page = arguments.get("full_page", True)
        timeout = arguments.get("timeout", 30000)

        # Default screenshot path in workspace
        if not screenshot_path:
            screenshot_path = str(Path(workspace) / f"screenshot_{id(self)}.png")

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            try:
                page = await browser.new_page()
                await page.goto(url, timeout=timeout)

                if selector:
                    # Screenshot specific element
                    element = page.locator(selector)
                    await element.screenshot(path=screenshot_path)
                    logger.info(f"Took screenshot of element {selector} at {screenshot_path}")
                    return ToolResult(
                        success=True,
                        output=f"Screenshot saved to {screenshot_path} (element: {selector})",
                    )
                else:
                    # Screenshot full page or viewport
                    await page.screenshot(path=screenshot_path, full_page=full_page)
                    logger.info(
                        f"Took {'full page' if full_page else 'viewport'} screenshot at {screenshot_path}"
                    )
                    return ToolResult(
                        success=True,
                        output=f"Screenshot saved to {screenshot_path} (full_page: {full_page})",
                    )
            finally:
                await browser.close()

    async def _extract_text(self, arguments: dict[str, Any]) -> ToolResult:
        """Extract text from page."""
        url = arguments.get("url")
        if not url:
            return ToolResult(success=False, error="Missing required parameter: url")

        selector = arguments.get("selector")
        timeout = arguments.get("timeout", 30000)

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            try:
                page = await browser.new_page()
                await page.goto(url, timeout=timeout)

                if selector:
                    # Extract text from specific element
                    text = await page.text_content(selector)
                    if text:
                        logger.info(f"Extracted text from {selector}: {len(text)} chars")
                        return ToolResult(success=True, output=text)
                    else:
                        return ToolResult(success=False, error=f"Element not found: {selector}")
                else:
                    # Extract all text from body
                    text = await page.text_content("body") or ""
                    logger.info(f"Extracted text from body: {len(text)} chars")
                    return ToolResult(success=True, output=text)
            finally:
                await browser.close()

    async def _get_html(self, arguments: dict[str, Any]) -> ToolResult:
        """Get HTML content."""
        url = arguments.get("url")
        if not url:
            return ToolResult(success=False, error="Missing required parameter: url")

        selector = arguments.get("selector")
        timeout = arguments.get("timeout", 30000)

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            try:
                page = await browser.new_page()
                await page.goto(url, timeout=timeout)

                if selector:
                    # Get HTML of specific element
                    html = await page.inner_html(selector)
                    logger.info(f"Got HTML from {selector}: {len(html)} chars")
                    return ToolResult(success=True, output=html)
                else:
                    # Get full page HTML
                    html = await page.content()
                    logger.info(f"Got page HTML: {len(html)} chars")
                    return ToolResult(success=True, output=html)
            finally:
                await browser.close()

    def get_schema(self) -> dict[str, Any]:
        """Get tool schema for AI models.

        Returns:
            JSON schema describing the tool's parameters
        """
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["navigate", "screenshot", "extract_text", "get_html"],
                        "description": "Action to perform",
                    },
                    "url": {
                        "type": "string",
                        "description": "URL to navigate to (required for all actions)",
                    },
                    "selector": {
                        "type": "string",
                        "description": "CSS selector for element (optional, for extract_text and screenshot)",
                    },
                    "screenshot_path": {
                        "type": "string",
                        "description": "Path to save screenshot (optional, defaults to workspace)",
                    },
                    "full_page": {
                        "type": "boolean",
                        "description": "Take full page screenshot (default: true)",
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Navigation timeout in milliseconds (default: 30000)",
                    },
                },
                "required": ["action"],
            },
        }
