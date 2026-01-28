"""Tests for BashTool sandbox integration."""

import pytest

from lurkbot.sandbox.manager import SandboxManager
from lurkbot.tools.base import SessionType
from lurkbot.tools.builtin.bash import BashTool


@pytest.mark.asyncio
@pytest.mark.docker
async def test_bash_tool_main_session_no_sandbox(tmp_path):
    """Test bash tool in MAIN session uses direct execution."""
    tool = BashTool()
    result = await tool.execute(
        {"command": "echo 'Hello from main'"},
        str(tmp_path),
        SessionType.MAIN,
    )

    assert result.success is True
    assert "Hello from main" in result.output


@pytest.mark.asyncio
@pytest.mark.docker
async def test_bash_tool_group_session_uses_sandbox(tmp_path):
    """Test bash tool in GROUP session uses Docker sandbox."""
    sandbox_manager = SandboxManager()
    tool = BashTool(sandbox_manager=sandbox_manager)

    result = await tool.execute(
        {"command": "echo 'Hello from sandbox'"},
        str(tmp_path),
        SessionType.GROUP,
    )

    assert result.success is True
    assert "Hello from sandbox" in result.output


@pytest.mark.asyncio
@pytest.mark.docker
async def test_bash_tool_topic_session_uses_sandbox(tmp_path):
    """Test bash tool in TOPIC session uses Docker sandbox."""
    sandbox_manager = SandboxManager()
    tool = BashTool(sandbox_manager=sandbox_manager)

    result = await tool.execute(
        {"command": "echo 'Hello from topic'"},
        str(tmp_path),
        SessionType.TOPIC,
    )

    assert result.success is True
    assert "Hello from topic" in result.output


@pytest.mark.asyncio
@pytest.mark.docker
async def test_bash_tool_sandbox_with_workspace(tmp_path):
    """Test bash tool sandbox can access workspace."""
    # Create test file in workspace
    test_file = tmp_path / "test.txt"
    test_file.write_text("test content")

    sandbox_manager = SandboxManager()
    tool = BashTool(sandbox_manager=sandbox_manager)

    result = await tool.execute(
        {"command": "cat test.txt"},
        str(tmp_path),
        SessionType.GROUP,
    )

    assert result.success is True
    assert "test content" in result.output


@pytest.mark.asyncio
@pytest.mark.docker
async def test_bash_tool_sandbox_failure(tmp_path):
    """Test bash tool sandbox handles command failures."""
    sandbox_manager = SandboxManager()
    tool = BashTool(sandbox_manager=sandbox_manager)

    result = await tool.execute(
        {"command": "exit 42"},
        str(tmp_path),
        SessionType.GROUP,
    )

    assert result.success is False
    assert result.exit_code == 42


@pytest.mark.asyncio
@pytest.mark.docker
async def test_bash_tool_sandbox_timeout(tmp_path):
    """Test bash tool sandbox respects timeout."""
    sandbox_manager = SandboxManager()
    tool = BashTool(sandbox_manager=sandbox_manager)
    tool.policy.max_execution_time = 1  # 1 second timeout

    result = await tool.execute(
        {"command": "sleep 10"},
        str(tmp_path),
        SessionType.GROUP,
    )

    assert result.success is False
    assert "timeout" in result.error.lower() or "timed out" in result.error.lower()


@pytest.mark.asyncio
async def test_bash_tool_policy_allows_multiple_session_types():
    """Test bash tool allows MAIN, GROUP, and TOPIC sessions."""
    tool = BashTool()

    assert SessionType.MAIN in tool.policy.allowed_session_types
    assert SessionType.GROUP in tool.policy.allowed_session_types
    assert SessionType.TOPIC in tool.policy.allowed_session_types
    # DM sessions not allowed (for security)
    assert SessionType.DM not in tool.policy.allowed_session_types
