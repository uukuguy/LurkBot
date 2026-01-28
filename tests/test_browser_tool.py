"""Tests for browser tool."""

from pathlib import Path

import pytest

from lurkbot.agents.base import SessionType
from lurkbot.tools.builtin.browser import BrowserTool


class TestBrowserTool:
    """Test browser tool."""

    def test_browser_tool_schema(self):
        """Test browser tool schema."""
        tool = BrowserTool()
        schema = tool.get_schema()

        assert schema["name"] == "browser"
        assert "action" in schema["input_schema"]["properties"]
        assert "url" in schema["input_schema"]["properties"]
        assert schema["input_schema"]["required"] == ["action"]

    def test_browser_tool_policy(self):
        """Test browser tool policy."""
        tool = BrowserTool()
        assert SessionType.MAIN in tool.policy.allowed_session_types
        assert SessionType.DM in tool.policy.allowed_session_types
        assert SessionType.GROUP not in tool.policy.allowed_session_types
        assert tool.policy.requires_approval is False

    async def test_missing_action(self):
        """Test missing action parameter."""
        tool = BrowserTool()
        result = await tool.execute(arguments={}, workspace="/tmp", session_type=SessionType.MAIN)

        assert result.success is False
        assert "action" in result.error.lower()

    async def test_unknown_action(self):
        """Test unknown action."""
        tool = BrowserTool()
        result = await tool.execute(
            arguments={"action": "unknown"}, workspace="/tmp", session_type=SessionType.MAIN
        )

        assert result.success is False
        assert "unknown action" in result.error.lower()

    async def test_navigate_missing_url(self):
        """Test navigate without URL."""
        tool = BrowserTool()
        result = await tool.execute(
            arguments={"action": "navigate"}, workspace="/tmp", session_type=SessionType.MAIN
        )

        assert result.success is False
        assert "url" in result.error.lower()

    @pytest.mark.browser
    async def test_navigate_success(self, request):
        """Test successful navigation."""
        if not request.config.getoption("--browser", default=False):
            pytest.skip("Browser tests require --browser flag and playwright installation")

        tool = BrowserTool()
        result = await tool.execute(
            arguments={"action": "navigate", "url": "https://example.com"},
            workspace="/tmp",
            session_type=SessionType.MAIN,
        )

        assert result.success is True
        assert "example.com" in result.output.lower()

    @pytest.mark.browser
    async def test_screenshot_success(self, request, tmp_path):
        """Test successful screenshot."""
        if not request.config.getoption("--browser", default=False):
            pytest.skip("Browser tests require --browser flag and playwright installation")

        screenshot_path = str(tmp_path / "screenshot.png")

        tool = BrowserTool()
        result = await tool.execute(
            arguments={
                "action": "screenshot",
                "url": "https://example.com",
                "screenshot_path": screenshot_path,
                "full_page": True,
            },
            workspace=str(tmp_path),
            session_type=SessionType.MAIN,
        )

        assert result.success is True
        assert Path(screenshot_path).exists()
        assert Path(screenshot_path).stat().st_size > 0

    @pytest.mark.browser
    async def test_extract_text_success(self, request):
        """Test successful text extraction."""
        if not request.config.getoption("--browser", default=False):
            pytest.skip("Browser tests require --browser flag and playwright installation")

        tool = BrowserTool()
        result = await tool.execute(
            arguments={"action": "extract_text", "url": "https://example.com"},
            workspace="/tmp",
            session_type=SessionType.MAIN,
        )

        assert result.success is True
        assert len(result.output) > 0
        assert "example" in result.output.lower()

    @pytest.mark.browser
    async def test_get_html_success(self, request):
        """Test successful HTML retrieval."""
        if not request.config.getoption("--browser", default=False):
            pytest.skip("Browser tests require --browser flag and playwright installation")

        tool = BrowserTool()
        result = await tool.execute(
            arguments={"action": "get_html", "url": "https://example.com"},
            workspace="/tmp",
            session_type=SessionType.MAIN,
        )

        assert result.success is True
        assert len(result.output) > 0
        assert "<html" in result.output.lower()
        assert "</html>" in result.output.lower()
