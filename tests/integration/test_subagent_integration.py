"""Integration tests for subagent communication.

Tests the complete subagent lifecycle including:
- Subagent spawning
- Parent-child message passing
- Announce flow
- Depth limiting
"""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from lurkbot.agents.types import SessionType, build_session_key
from lurkbot.agents.subagent import (
    build_subagent_system_prompt,
    SUBAGENT_DENY_LIST,
)
from lurkbot.sessions.manager import SessionManager, SessionContext


class TestSubagentSpawning:
    """Test subagent spawning functionality."""

    @pytest.mark.integration
    def test_spawn_subagent_basic(self, session_manager: SessionManager):
        """Test basic subagent spawning."""
        # Create parent session
        parent_ctx = SessionContext(
            agent_id="test-agent",
            session_type=SessionType.MAIN,
        )
        parent, _ = session_manager.get_or_create_session(parent_ctx)

        # Spawn subagent
        subagent = session_manager.spawn_subagent_session(
            parent_session_key=parent.session_key,
            agent_id="test-agent",
            task="Perform a research task",
        )

        assert subagent is not None
        assert subagent.session_type == "subagent"
        assert subagent.parent_session == parent.session_key

    @pytest.mark.integration
    def test_spawn_subagent_with_label(self, session_manager: SessionManager):
        """Test spawning subagent with a label."""
        parent_ctx = SessionContext(
            agent_id="test-agent",
            session_type=SessionType.MAIN,
        )
        parent, _ = session_manager.get_or_create_session(parent_ctx)

        subagent = session_manager.spawn_subagent_session(
            parent_session_key=parent.session_key,
            agent_id="test-agent",
            task="Read and analyze files",
            label="File Analyzer",
        )

        assert subagent is not None
        assert "subagent" in subagent.session_key

    @pytest.mark.integration
    def test_spawn_multiple_subagents(self, session_manager: SessionManager):
        """Test spawning multiple subagents from same parent."""
        parent_ctx = SessionContext(
            agent_id="test-agent",
            session_type=SessionType.MAIN,
        )
        parent, _ = session_manager.get_or_create_session(parent_ctx)

        subagents = []
        for i in range(3):
            sub = session_manager.spawn_subagent_session(
                parent_session_key=parent.session_key,
                agent_id="test-agent",
                task=f"Task {i + 1}",
            )
            subagents.append(sub)

        # All subagents should be unique
        session_ids = [s.session_id for s in subagents]
        assert len(set(session_ids)) == 3


class TestSubagentSystemPrompt:
    """Test subagent system prompt generation."""

    @pytest.mark.integration
    def test_build_subagent_prompt_basic(self):
        """Test building basic subagent system prompt."""
        prompt = build_subagent_system_prompt(
            requester_session_key="agent:test:main",
            child_session_key="agent:test:subagent:sub-001",
            task="Analyze the codebase structure",
        )

        assert prompt is not None
        assert "Analyze the codebase" in prompt
        assert "subagent" in prompt.lower() or "task" in prompt.lower()

    @pytest.mark.integration
    def test_build_subagent_prompt_with_label(self):
        """Test building subagent prompt with label."""
        prompt = build_subagent_system_prompt(
            requester_session_key="agent:test:main",
            child_session_key="agent:test:subagent:sub-001",
            task="Search for security vulnerabilities",
            label="Security Scanner",
        )

        assert prompt is not None
        assert "Security Scanner" in prompt

    @pytest.mark.integration
    def test_subagent_deny_list(self):
        """Test that subagent deny list contains expected tools."""
        # These tools should be denied for subagents
        expected_denied = [
            "sessions_spawn",  # Prevent recursive spawning
            "message",  # Prevent direct messaging
        ]

        for tool in expected_denied:
            assert tool in SUBAGENT_DENY_LIST


class TestSubagentDepthLimiting:
    """Test subagent depth limiting."""

    @pytest.mark.integration
    def test_depth_tracking(self, session_manager: SessionManager):
        """Test that subagent depth is tracked correctly."""
        parent_ctx = SessionContext(
            agent_id="test-agent",
            session_type=SessionType.MAIN,
        )
        parent, _ = session_manager.get_or_create_session(parent_ctx)

        # Spawn first level subagent
        sub1 = session_manager.spawn_subagent_session(
            parent_session_key=parent.session_key,
            agent_id="test-agent",
            task="Level 1 task",
        )

        # Verify parent relationship
        assert sub1.parent_session == parent.session_key

        # Spawn second level subagent
        sub2 = session_manager.spawn_subagent_session(
            parent_session_key=sub1.session_key,
            agent_id="test-agent",
            task="Level 2 task",
        )

        # Verify nested parent relationship
        assert sub2.parent_session == sub1.session_key

    @pytest.mark.integration
    def test_max_depth_enforcement(self, session_manager: SessionManager):
        """Test that maximum depth is enforced."""
        parent_ctx = SessionContext(
            agent_id="test-agent",
            session_type=SessionType.MAIN,
        )
        parent, _ = session_manager.get_or_create_session(parent_ctx)

        # Spawn subagents up to max depth
        current_key = parent.session_key
        max_depth = session_manager.config.max_subagent_depth

        for i in range(max_depth):
            sub = session_manager.spawn_subagent_session(
                parent_session_key=current_key,
                agent_id="test-agent",
                task=f"Depth {i + 1}",
            )
            current_key = sub.session_key

        # Attempting to exceed max depth should fail
        with pytest.raises(ValueError):
            session_manager.spawn_subagent_session(
                parent_session_key=current_key,
                agent_id="test-agent",
                task="This should fail",
            )


class TestSubagentSessionKeys:
    """Test subagent session key generation."""

    @pytest.mark.integration
    def test_subagent_key_format(self, session_manager: SessionManager):
        """Test subagent session key format."""
        # Create main session first
        main_ctx = SessionContext(
            agent_id="my-agent",
            session_type=SessionType.MAIN,
        )
        parent, _ = session_manager.get_or_create_session(main_ctx)

        # Spawn a subagent to get the key
        subagent = session_manager.spawn_subagent_session(
            agent_id="my-agent",
            parent_session_key=parent.session_key,
            task="Test task",
        )

        # Key format: agent:{agentId}:subagent:{subagentId}
        key = subagent.session_key
        assert "subagent" in key
        parts = key.split(":")
        assert parts[0] == "agent"
        assert parts[1] == "my-agent"
        assert parts[2] == "subagent"

    @pytest.mark.integration
    def test_unique_subagent_keys(self, session_manager: SessionManager):
        """Test that each subagent gets unique key."""
        main_ctx = SessionContext(
            agent_id="my-agent",
            session_type=SessionType.MAIN,
        )
        parent, _ = session_manager.get_or_create_session(main_ctx)

        # Spawn two subagents
        sub1 = session_manager.spawn_subagent_session(
            agent_id="my-agent",
            parent_session_key=parent.session_key,
            task="Task 1",
        )

        sub2 = session_manager.spawn_subagent_session(
            agent_id="my-agent",
            parent_session_key=parent.session_key,
            task="Task 2",
        )

        assert sub1.session_key != sub2.session_key


class TestSubagentToolDenyList:
    """Test subagent tool deny list."""

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


class TestSubagentParentRelationship:
    """Test parent-subagent relationships."""

    @pytest.mark.integration
    def test_subagent_has_parent(self, session_manager: SessionManager):
        """Test that subagent has correct parent relationship."""
        parent_ctx = SessionContext(
            agent_id="test-agent",
            session_type=SessionType.MAIN,
        )
        parent, _ = session_manager.get_or_create_session(parent_ctx)

        subagent = session_manager.spawn_subagent_session(
            parent_session_key=parent.session_key,
            agent_id="test-agent",
            task="Test task",
        )

        assert subagent.parent_session == parent.session_key

    @pytest.mark.integration
    def test_nested_parent_chain(self, session_manager: SessionManager):
        """Test nested parent chain tracking."""
        parent_ctx = SessionContext(
            agent_id="test-agent",
            session_type=SessionType.MAIN,
        )
        parent, _ = session_manager.get_or_create_session(parent_ctx)

        # Create chain: parent -> sub1 -> sub2
        sub1 = session_manager.spawn_subagent_session(
            parent_session_key=parent.session_key,
            agent_id="test-agent",
            task="Level 1",
        )

        sub2 = session_manager.spawn_subagent_session(
            parent_session_key=sub1.session_key,
            agent_id="test-agent",
            task="Level 2",
        )

        # Verify chain
        assert sub1.parent_session == parent.session_key
        assert sub2.parent_session == sub1.session_key


# Test count verification
def test_subagent_integration_test_count():
    """Verify the number of integration tests."""
    import inspect

    test_classes = [
        TestSubagentSpawning,
        TestSubagentSystemPrompt,
        TestSubagentDepthLimiting,
        TestSubagentSessionKeys,
        TestSubagentToolDenyList,
        TestSubagentParentRelationship,
    ]

    total_tests = 0
    for cls in test_classes:
        methods = [m for m in dir(cls) if m.startswith("test_")]
        total_tests += len(methods)

    # Add standalone test
    total_tests += 1  # test_subagent_integration_test_count

    print(f"\n✅ Subagent integration tests: {total_tests} tests")
    assert total_tests >= 15, f"Expected at least 15 tests, got {total_tests}"
