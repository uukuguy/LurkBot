"""Integration test fixtures and configuration.

This module provides shared fixtures for integration tests,
including mock API clients, test databases, and helper utilities.
"""

import asyncio
import tempfile
from pathlib import Path
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic_ai import Agent

from lurkbot.agents.types import AgentContext, SessionType
from lurkbot.sessions.manager import SessionManager, SessionManagerConfig
from lurkbot.sessions.store import SessionStore


# ============================================================================
# Fixtures: Temporary directories
# ============================================================================


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for test data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def temp_workspace(temp_dir: Path) -> Path:
    """Create a temporary workspace directory with bootstrap files."""
    workspace = temp_dir / "workspace"
    workspace.mkdir(parents=True)

    # Create minimal bootstrap files
    (workspace / "AGENTS.md").write_text("# Test Agent\nA test agent for integration tests.")
    (workspace / "TOOLS.md").write_text("# Tools\nAvailable tools for testing.")

    return workspace


@pytest.fixture
def temp_lurkbot_home(temp_dir: Path) -> Path:
    """Create a temporary ~/.lurkbot directory structure."""
    home = temp_dir / ".lurkbot"
    home.mkdir(parents=True)

    # Create subdirectories
    (home / "agents").mkdir()
    (home / "sessions").mkdir()
    (home / "logs").mkdir()
    (home / "run").mkdir()

    return home


# ============================================================================
# Fixtures: Session management
# ============================================================================


@pytest.fixture
def session_manager_config(temp_lurkbot_home: Path) -> SessionManagerConfig:
    """Create session manager configuration for tests."""
    return SessionManagerConfig(
        base_dir=temp_lurkbot_home / "agents",
        auto_cleanup=False,
        max_sessions_per_agent=100,
        max_subagent_depth=3,
    )


@pytest.fixture
def session_manager(session_manager_config: SessionManagerConfig) -> SessionManager:
    """Create a session manager for tests."""
    return SessionManager(config=session_manager_config)


@pytest.fixture
def session_store(temp_lurkbot_home: Path) -> SessionStore:
    """Create a session store for tests."""
    store_dir = temp_lurkbot_home / "agents" / "test-agent"
    store_dir.mkdir(parents=True)
    return SessionStore(store_dir)


# ============================================================================
# Fixtures: Agent context
# ============================================================================


@pytest.fixture
def agent_context(temp_workspace: Path) -> AgentContext:
    """Create a basic agent context for tests."""
    return AgentContext(
        session_id="test-session-001",
        session_key="agent:test-agent:main",
        session_type=SessionType.MAIN,
        workspace_dir=str(temp_workspace),
        message_channel="test",
    )


@pytest.fixture
def subagent_context(temp_workspace: Path) -> AgentContext:
    """Create a subagent context for tests."""
    return AgentContext(
        session_id="test-subagent-001",
        session_key="agent:test-agent:subagent:sub-001",
        session_type=SessionType.SUBAGENT,
        workspace_dir=str(temp_workspace),
        message_channel="test",
        spawned_by="agent:test-agent:main",
    )


@pytest.fixture
def group_context(temp_workspace: Path) -> AgentContext:
    """Create a group session context for tests."""
    return AgentContext(
        session_id="test-group-001",
        session_key="agent:test-agent:group:telegram:group-123",
        session_type=SessionType.GROUP,
        workspace_dir=str(temp_workspace),
        message_channel="telegram",
        group_id="group-123",
    )


# ============================================================================
# Fixtures: Mock API clients
# ============================================================================


@pytest.fixture
def mock_anthropic_client() -> MagicMock:
    """Create a mock Anthropic API client."""
    client = MagicMock()

    # Mock message creation
    mock_response = MagicMock()
    mock_response.content = [MagicMock(type="text", text="Test response")]
    mock_response.stop_reason = "end_turn"
    mock_response.usage = MagicMock(input_tokens=100, output_tokens=50)

    client.messages.create = AsyncMock(return_value=mock_response)

    return client


@pytest.fixture
def mock_tool_response() -> dict:
    """Create a mock tool use response."""
    return {
        "content": [
            {
                "type": "tool_use",
                "id": "tool-001",
                "name": "read_file",
                "input": {"path": "/test/file.txt"},
            }
        ],
        "stop_reason": "tool_use",
    }


@pytest.fixture
def mock_text_response() -> dict:
    """Create a mock text response."""
    return {
        "content": [{"type": "text", "text": "This is a test response."}],
        "stop_reason": "end_turn",
    }


# ============================================================================
# Fixtures: Gateway testing
# ============================================================================


@pytest.fixture
def mock_websocket() -> MagicMock:
    """Create a mock WebSocket connection."""
    ws = MagicMock()
    ws.accept = AsyncMock()
    ws.send_text = AsyncMock()
    ws.send_json = AsyncMock()
    ws.receive_text = AsyncMock(return_value='{"type": "hello", "params": {}}')
    ws.receive_json = AsyncMock(return_value={"type": "hello", "params": {}})
    ws.close = AsyncMock()
    return ws


# ============================================================================
# Fixtures: Event loop
# ============================================================================


@pytest.fixture
def event_loop():
    """Create an event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# Helper functions
# ============================================================================


def create_test_message(role: str, content: str) -> dict:
    """Create a test message in the standard format."""
    return {
        "role": role,
        "content": content,
        "timestamp": "2026-01-30T00:00:00Z",
    }


def create_tool_call(name: str, arguments: dict, tool_id: str = "tool-001") -> dict:
    """Create a test tool call."""
    return {
        "type": "tool_use",
        "id": tool_id,
        "name": name,
        "input": arguments,
    }


def create_tool_result(tool_id: str, result: str, is_error: bool = False) -> dict:
    """Create a test tool result."""
    return {
        "type": "tool_result",
        "tool_use_id": tool_id,
        "content": result,
        "is_error": is_error,
    }


# ============================================================================
# Markers
# ============================================================================


def pytest_configure(config):
    """Configure pytest markers for integration tests."""
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "requires_api: mark test as requiring real API access (ANTHROPIC_API_KEY, etc.)"
    )


def pytest_collection_modifyitems(config, items):
    """Skip tests that require API keys if not available."""
    import os

    # Check if API keys are available
    has_anthropic_key = bool(os.environ.get("ANTHROPIC_API_KEY"))
    has_openai_key = bool(os.environ.get("OPENAI_API_KEY"))

    skip_api = pytest.mark.skip(reason="requires API key (ANTHROPIC_API_KEY or OPENAI_API_KEY)")

    for item in items:
        if "requires_api" in item.keywords:
            if not (has_anthropic_key or has_openai_key):
                item.add_marker(skip_api)
