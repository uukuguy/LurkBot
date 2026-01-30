"""End-to-end integration tests for Subagent spawning flow.

Tests the complete Subagent spawning flow:
- Subagent session creation
- Spawn parameter handling
- Subagent system prompt generation
- Run tracking and management
- Subagent context creation
"""

import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from lurkbot.agents.types import AgentContext, SessionType
from lurkbot.agents.subagent import (
    # Types
    SpawnParams,
    SpawnResult,
    SubagentRun,
    # Constants
    SUBAGENT_DENY_LIST,
    # Functions
    build_subagent_system_prompt,
    generate_run_id,
    get_active_run,
    list_active_runs,
    get_subagent_context,
)
from lurkbot.sessions.manager import SessionManager, SessionManagerConfig, SessionContext
from lurkbot.sessions.types import (
    SessionEntry,
    SessionState,
    SubagentOutcome,
    SubagentResult,
)


class TestE2ESubagentTypes:
    """Test Subagent type definitions."""

    @pytest.mark.integration
    def test_spawn_params_defaults(self):
        """Test SpawnParams default values."""
        params = SpawnParams(task="Test task")

        assert params.task == "Test task"
        assert params.agent_id is None
        assert params.model is None
        assert params.thinking == "medium"
        assert params.run_timeout_seconds == 3600
        assert params.cleanup == "keep"
        assert params.label is None

    @pytest.mark.integration
    def test_spawn_params_custom(self):
        """Test SpawnParams with custom values."""
        params = SpawnParams(
            task="Custom task",
            agent_id="custom-agent",
            model="claude-3-sonnet",
            thinking="high",
            run_timeout_seconds=1800,
            cleanup="delete",
            label="My subagent",
        )

        assert params.task == "Custom task"
        assert params.agent_id == "custom-agent"
        assert params.model == "claude-3-sonnet"
        assert params.thinking == "high"
        assert params.run_timeout_seconds == 1800
        assert params.cleanup == "delete"
        assert params.label == "My subagent"

    @pytest.mark.integration
    def test_spawn_result_success(self):
        """Test successful SpawnResult."""
        result = SpawnResult(
            success=True,
            session_key="agent:test:subagent:sub-001",
            run_id="run_abc123",
        )

        assert result.success is True
        assert result.session_key == "agent:test:subagent:sub-001"
        assert result.run_id == "run_abc123"
        assert result.error is None

    @pytest.mark.integration
    def test_spawn_result_failure(self):
        """Test failed SpawnResult."""
        result = SpawnResult(
            success=False,
            session_key="",
            run_id="",
            error="Maximum subagent depth exceeded",
        )

        assert result.success is False
        assert result.error == "Maximum subagent depth exceeded"

    @pytest.mark.integration
    def test_subagent_run_tracking(self):
        """Test SubagentRun tracking structure."""
        run = SubagentRun(
            run_id="run_test123",
            session_key="agent:test:subagent:sub-001",
            parent_session_key="agent:test:main",
            task="Process data",
            label="Data processor",
            started_at=datetime.now(),
            timeout_ms=3600000,
            cleanup="keep",
            agent_id="test",
        )

        assert run.run_id == "run_test123"
        assert run.session_key == "agent:test:subagent:sub-001"
        assert run.parent_session_key == "agent:test:main"
        assert run.task == "Process data"
        assert run.label == "Data processor"
        assert run.timeout_ms == 3600000


class TestE2ESubagentDenyList:
    """Test Subagent tool deny list."""

    @pytest.mark.integration
    def test_deny_list_contains_sessions_tools(self):
        """Test deny list contains session management tools."""
        assert "sessions_list" in SUBAGENT_DENY_LIST
        assert "sessions_history" in SUBAGENT_DENY_LIST
        assert "sessions_send" in SUBAGENT_DENY_LIST
        assert "sessions_spawn" in SUBAGENT_DENY_LIST

    @pytest.mark.integration
    def test_deny_list_contains_dangerous_tools(self):
        """Test deny list contains dangerous tools."""
        assert "gateway" in SUBAGENT_DENY_LIST
        assert "cron" in SUBAGENT_DENY_LIST
        assert "message" in SUBAGENT_DENY_LIST

    @pytest.mark.integration
    def test_deny_list_contains_memory_tools(self):
        """Test deny list contains memory tools."""
        assert "memory_search" in SUBAGENT_DENY_LIST
        assert "memory_get" in SUBAGENT_DENY_LIST


class TestE2ESubagentSystemPrompt:
    """Test Subagent system prompt generation."""

    @pytest.mark.integration
    def test_build_system_prompt_basic(self):
        """Test basic system prompt generation."""
        prompt = build_subagent_system_prompt(
            requester_session_key="agent:test:main",
            child_session_key="agent:test:subagent:sub-001",
            task="Process the data file",
        )

        assert "subagent" in prompt.lower()
        assert "Process the data file" in prompt
        assert "agent:test:main" in prompt
        assert "agent:test:subagent:sub-001" in prompt

    @pytest.mark.integration
    def test_build_system_prompt_with_label(self):
        """Test system prompt with label."""
        prompt = build_subagent_system_prompt(
            requester_session_key="agent:test:main",
            child_session_key="agent:test:subagent:sub-001",
            task="Analyze data",
            label="Data Analyzer",
        )

        assert "Data Analyzer" in prompt

    @pytest.mark.integration
    def test_build_system_prompt_contains_rules(self):
        """Test system prompt contains behavioral rules."""
        prompt = build_subagent_system_prompt(
            requester_session_key="agent:test:main",
            child_session_key="agent:test:subagent:sub-001",
            task="Test task",
        )

        # Check for key rules
        assert "focused" in prompt.lower() or "focus" in prompt.lower()
        assert "complete" in prompt.lower() or "task" in prompt.lower()

    @pytest.mark.integration
    def test_build_system_prompt_restrictions(self):
        """Test system prompt contains restrictions."""
        prompt = build_subagent_system_prompt(
            requester_session_key="agent:test:main",
            child_session_key="agent:test:subagent:sub-001",
            task="Test task",
        )

        # Check for restrictions
        assert "don't" in prompt.lower() or "no " in prompt.lower()


class TestE2ESubagentIdGeneration:
    """Test Subagent ID generation."""

    @pytest.mark.integration
    def test_generate_run_id_format(self):
        """Test run ID format."""
        run_id = generate_run_id()

        assert run_id.startswith("run_")
        assert len(run_id) == 16  # "run_" + 12 hex chars

    @pytest.mark.integration
    def test_generate_run_id_uniqueness(self):
        """Test run ID uniqueness."""
        ids = set()
        for _ in range(100):
            run_id = generate_run_id()
            assert run_id not in ids
            ids.add(run_id)


class TestE2ESubagentRunTracking:
    """Test Subagent run tracking."""

    @pytest.mark.integration
    def test_get_active_run_not_found(self):
        """Test getting non-existent run."""
        run = get_active_run("run_nonexistent")
        assert run is None

    @pytest.mark.integration
    def test_list_active_runs_empty(self):
        """Test listing active runs when empty."""
        # List with filter that won't match
        runs = list_active_runs("agent:nonexistent:main")
        assert runs == []


class TestE2ESubagentContext:
    """Test Subagent context creation."""

    @pytest.fixture
    def parent_context(self) -> AgentContext:
        """Create a parent agent context."""
        return AgentContext(
            session_id="ses_parent001",
            session_key="agent:test-agent:main",
            session_type=SessionType.MAIN,
            workspace_dir="/tmp/workspace",
            agent_dir="/tmp/.lurkbot/agents/test-agent",
            provider="anthropic",
            model_id="claude-3-sonnet",
        )

    @pytest.fixture
    def subagent_session(self) -> SessionEntry:
        """Create a subagent session entry."""
        return SessionEntry(
            session_id="ses_sub001",
            session_key="agent:test-agent:subagent:sub-001",
            session_type="subagent",
            state=SessionState.ACTIVE,
            created_at=int(time.time() * 1000),
            updated_at=int(time.time() * 1000),
            parent_session="agent:test-agent:main",
        )

    @pytest.mark.integration
    def test_get_subagent_context(self, parent_context: AgentContext, subagent_session: SessionEntry):
        """Test creating subagent context."""
        params = SpawnParams(task="Test task", label="Test label")

        ctx = get_subagent_context(
            parent_context=parent_context,
            session=subagent_session,
            task="Test task",
            params=params,
        )

        assert ctx.session_id == "ses_sub001"
        assert ctx.session_key == "agent:test-agent:subagent:sub-001"
        assert ctx.session_type == SessionType.SUBAGENT
        assert ctx.is_subagent is True
        assert ctx.spawned_by == "agent:test-agent:main"
        assert ctx.sandbox_enabled is True

    @pytest.mark.integration
    def test_get_subagent_context_inherits_workspace(
        self, parent_context: AgentContext, subagent_session: SessionEntry
    ):
        """Test subagent context inherits workspace from parent."""
        params = SpawnParams(task="Test task")

        ctx = get_subagent_context(
            parent_context=parent_context,
            session=subagent_session,
            task="Test task",
            params=params,
        )

        assert ctx.workspace_dir == parent_context.workspace_dir
        assert ctx.agent_dir == parent_context.agent_dir

    @pytest.mark.integration
    def test_get_subagent_context_model_override(
        self, parent_context: AgentContext, subagent_session: SessionEntry
    ):
        """Test subagent context with model override."""
        params = SpawnParams(
            task="Test task",
            model="claude-3-opus",
            model_provider="anthropic",
        )

        ctx = get_subagent_context(
            parent_context=parent_context,
            session=subagent_session,
            task="Test task",
            params=params,
        )

        assert ctx.model_id == "claude-3-opus"
        assert ctx.provider == "anthropic"

    @pytest.mark.integration
    def test_get_subagent_context_has_system_prompt(
        self, parent_context: AgentContext, subagent_session: SessionEntry
    ):
        """Test subagent context includes system prompt."""
        params = SpawnParams(task="Process data", label="Data processor")

        ctx = get_subagent_context(
            parent_context=parent_context,
            session=subagent_session,
            task="Process data",
            params=params,
        )

        assert ctx.extra_system_prompt is not None
        assert "Process data" in ctx.extra_system_prompt
        assert "Data processor" in ctx.extra_system_prompt


class TestE2ESubagentOutcome:
    """Test Subagent outcome handling."""

    @pytest.mark.integration
    def test_subagent_result_ok(self):
        """Test successful subagent result."""
        result = SubagentResult(
            session_key="agent:test:subagent:sub-001",
            run_id="run_abc123",
            outcome="ok",
            result="Task completed successfully",
            duration_ms=5000,
            tokens_used=150,
        )

        assert result.outcome == "ok"
        assert result.result == "Task completed successfully"
        assert result.duration_ms == 5000

    @pytest.mark.integration
    def test_subagent_result_error(self):
        """Test error subagent result."""
        result = SubagentResult(
            session_key="agent:test:subagent:sub-001",
            run_id="run_abc123",
            outcome="error",
            error="Failed to process data",
            duration_ms=2000,
        )

        assert result.outcome == "error"
        assert result.error == "Failed to process data"

    @pytest.mark.integration
    def test_subagent_result_timeout(self):
        """Test timeout subagent result."""
        result = SubagentResult(
            session_key="agent:test:subagent:sub-001",
            run_id="run_abc123",
            outcome="timeout",
            duration_ms=3600000,
        )

        assert result.outcome == "timeout"
        assert result.duration_ms == 3600000


class TestE2ESubagentSessionIntegration:
    """Test Subagent session integration with SessionManager."""

    @pytest.fixture
    def temp_base_dir(self) -> Path:
        """Create a temporary base directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir) / "agents"

    @pytest.fixture
    def session_manager(self, temp_base_dir: Path) -> SessionManager:
        """Create a session manager instance."""
        config = SessionManagerConfig(
            base_dir=temp_base_dir,
            auto_cleanup=False,
            max_sessions_per_agent=100,
            max_subagent_depth=3,
        )
        return SessionManager(config=config)

    @pytest.mark.integration
    def test_session_manager_spawn_subagent(self, session_manager: SessionManager):
        """Test spawning subagent session via SessionManager."""
        # First create main session
        main_ctx = SessionContext(
            agent_id="test-agent",
            session_type=SessionType.MAIN,
        )
        main_session, _ = session_manager.get_or_create_session(main_ctx)

        # Spawn subagent session
        subagent_session = session_manager.spawn_subagent_session(
            agent_id="test-agent",
            parent_session_key=main_session.session_key,
            task="Test subagent task",
            label="Test subagent",
        )

        assert subagent_session is not None
        assert "subagent" in subagent_session.session_key
        assert subagent_session.session_type == "subagent"
        assert subagent_session.parent_session == main_session.session_key

    @pytest.mark.integration
    def test_subagent_session_key_format(self, session_manager: SessionManager):
        """Test subagent session key format."""
        # First create main session
        main_ctx = SessionContext(
            agent_id="test-agent",
            session_type=SessionType.MAIN,
        )
        main_session, _ = session_manager.get_or_create_session(main_ctx)

        # Spawn subagent
        subagent = session_manager.spawn_subagent_session(
            agent_id="test-agent",
            parent_session_key=main_session.session_key,
            task="Test task",
        )

        # Key format: agent:{agentId}:subagent:{subagentId}
        parts = subagent.session_key.split(":")
        assert parts[0] == "agent"
        assert parts[1] == "test-agent"
        assert parts[2] == "subagent"


# Test count verification
def test_e2e_subagent_spawning_test_count():
    """Verify the number of E2E Subagent spawning tests."""
    import inspect

    test_classes = [
        TestE2ESubagentTypes,
        TestE2ESubagentDenyList,
        TestE2ESubagentSystemPrompt,
        TestE2ESubagentIdGeneration,
        TestE2ESubagentRunTracking,
        TestE2ESubagentContext,
        TestE2ESubagentOutcome,
        TestE2ESubagentSessionIntegration,
    ]

    total_tests = 0
    for cls in test_classes:
        methods = [m for m in dir(cls) if m.startswith("test_")]
        total_tests += len(methods)

    # Add standalone test
    total_tests += 1  # test_e2e_subagent_spawning_test_count

    print(f"\n✅ E2E Subagent Spawning tests: {total_tests} tests")
    assert total_tests >= 25, f"Expected at least 25 tests, got {total_tests}"
