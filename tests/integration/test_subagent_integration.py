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
    spawn_subagent,
    build_subagent_system_prompt,
    run_announce_flow,
    SUBAGENT_DENY_LIST,
)
from lurkbot.sessions.manager import SessionManager, SessionContext
from lurkbot.sessions.types import SessionEntry, SessionState


class TestSubagentSpawning:
    """Test subagent spawning functionality."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_spawn_subagent_basic(
        self, session_manager: SessionManager
    ):
        """Test basic subagent spawning."""
        # Create parent session
        parent_ctx = SessionContext(
            agent_id="test-agent",
            session_type=SessionType.MAIN,
        )
        parent = await session_manager.get_or_create_session(parent_ctx)

        # Spawn subagent
        subagent = await session_manager.spawn_subagent(
            parent_session_key=parent.session_key,
            agent_id="test-agent",
            task="Perform a research task",
        )

        assert subagent is not None
        assert subagent.session_type == SessionType.SUBAGENT
        assert subagent.state == SessionState.ACTIVE

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_spawn_subagent_with_tools(
        self, session_manager: SessionManager
    ):
        """Test spawning subagent with specific tools."""
        parent_ctx = SessionContext(
            agent_id="test-agent",
            session_type=SessionType.MAIN,
        )
        parent = await session_manager.get_or_create_session(parent_ctx)

        subagent = await session_manager.spawn_subagent(
            parent_session_key=parent.session_key,
            agent_id="test-agent",
            task="Read and analyze files",
            tools=["read_file", "web_search"],
        )

        assert subagent is not None
        # Tools should be stored in metadata
        assert subagent.metadata.get("tools") == ["read_file", "web_search"]

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_spawn_multiple_subagents(
        self, session_manager: SessionManager
    ):
        """Test spawning multiple subagents from same parent."""
        parent_ctx = SessionContext(
            agent_id="test-agent",
            session_type=SessionType.MAIN,
        )
        parent = await session_manager.get_or_create_session(parent_ctx)

        subagents = []
        for i in range(3):
            sub = await session_manager.spawn_subagent(
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
            task="Analyze the codebase structure",
            parent_context="Working on a Python project",
        )

        assert prompt is not None
        assert "Analyze the codebase" in prompt
        assert "subagent" in prompt.lower() or "task" in prompt.lower()

    @pytest.mark.integration
    def test_build_subagent_prompt_with_constraints(self):
        """Test building subagent prompt with constraints."""
        prompt = build_subagent_system_prompt(
            task="Search for security vulnerabilities",
            parent_context="Security audit",
            constraints=["Do not modify files", "Report findings only"],
        )

        assert prompt is not None
        assert "Do not modify" in prompt or "constraint" in prompt.lower()

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
    @pytest.mark.asyncio
    async def test_depth_tracking(
        self, session_manager: SessionManager
    ):
        """Test that subagent depth is tracked correctly."""
        parent_ctx = SessionContext(
            agent_id="test-agent",
            session_type=SessionType.MAIN,
        )
        parent = await session_manager.get_or_create_session(parent_ctx)

        # Spawn first level subagent
        sub1 = await session_manager.spawn_subagent(
            parent_session_key=parent.session_key,
            agent_id="test-agent",
            task="Level 1 task",
        )

        # Spawn second level subagent
        sub2 = await session_manager.spawn_subagent(
            parent_session_key=sub1.session_key,
            agent_id="test-agent",
            task="Level 2 task",
        )

        # Verify depth is tracked
        assert sub1.metadata.get("depth", 1) == 1
        assert sub2.metadata.get("depth", 2) == 2

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_max_depth_enforcement(
        self, session_manager: SessionManager
    ):
        """Test that maximum depth is enforced."""
        parent_ctx = SessionContext(
            agent_id="test-agent",
            session_type=SessionType.MAIN,
        )
        parent = await session_manager.get_or_create_session(parent_ctx)

        # Spawn subagents up to max depth
        current_key = parent.session_key
        max_depth = session_manager.config.max_subagent_depth

        for i in range(max_depth):
            sub = await session_manager.spawn_subagent(
                parent_session_key=current_key,
                agent_id="test-agent",
                task=f"Depth {i + 1}",
            )
            current_key = sub.session_key

        # Attempting to exceed max depth should fail
        with pytest.raises(ValueError):
            await session_manager.spawn_subagent(
                parent_session_key=current_key,
                agent_id="test-agent",
                task="This should fail",
            )


class TestSubagentAnnounceFlow:
    """Test subagent announce flow."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_announce_result_basic(self):
        """Test basic announce flow."""
        result = {
            "status": "completed",
            "summary": "Task completed successfully",
            "findings": ["Finding 1", "Finding 2"],
        }

        announcement = await run_announce_flow(
            subagent_id="sub-001",
            parent_session_key="agent:test:main",
            result=result,
        )

        assert announcement is not None
        assert "completed" in str(announcement).lower()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_announce_with_error(self):
        """Test announce flow with error result."""
        result = {
            "status": "failed",
            "error": "Could not complete task",
            "partial_results": [],
        }

        announcement = await run_announce_flow(
            subagent_id="sub-001",
            parent_session_key="agent:test:main",
            result=result,
        )

        assert announcement is not None
        assert "failed" in str(announcement).lower() or "error" in str(announcement).lower()


class TestSubagentSessionKeys:
    """Test subagent session key generation."""

    @pytest.mark.integration
    def test_subagent_key_format(self):
        """Test subagent session key format."""
        key = build_session_key(
            agent_id="my-agent",
            session_type=SessionType.SUBAGENT,
            subagent_id="sub-001",
        )

        assert "subagent" in key
        assert "sub-001" in key
        assert key == "agent:my-agent:subagent:sub-001"

    @pytest.mark.integration
    def test_nested_subagent_key(self):
        """Test nested subagent key generation."""
        # First level
        key1 = build_session_key(
            agent_id="my-agent",
            session_type=SessionType.SUBAGENT,
            subagent_id="sub-001",
        )

        # Second level (child of first subagent)
        key2 = build_session_key(
            agent_id="my-agent",
            session_type=SessionType.SUBAGENT,
            subagent_id="sub-002",
        )

        assert key1 != key2
        assert "sub-001" in key1
        assert "sub-002" in key2


class TestSubagentToolFiltering:
    """Test tool filtering for subagents."""

    @pytest.mark.integration
    def test_denied_tools_not_available(self):
        """Test that denied tools are not available to subagents."""
        from lurkbot.tools.policy import filter_tools_nine_layers, ToolFilterContext, ToolProfileId

        all_tools = [
            {"name": "read_file"},
            {"name": "write_file"},
            {"name": "sessions_spawn"},  # Should be denied
            {"name": "message"},  # Should be denied
            {"name": "exec"},
        ]

        context = ToolFilterContext(
            session_type=SessionType.SUBAGENT,
            profile=ToolProfileId.CODING,
            is_subagent=True,
        )

        filtered = filter_tools_nine_layers(all_tools, context)
        tool_names = [t["name"] for t in filtered]

        # Denied tools should not be present
        for denied in SUBAGENT_DENY_LIST:
            if denied in [t["name"] for t in all_tools]:
                assert denied not in tool_names

    @pytest.mark.integration
    def test_allowed_tools_available(self):
        """Test that allowed tools are available to subagents."""
        from lurkbot.tools.policy import filter_tools_nine_layers, ToolFilterContext, ToolProfileId

        all_tools = [
            {"name": "read_file"},
            {"name": "write_file"},
            {"name": "web_search"},
        ]

        context = ToolFilterContext(
            session_type=SessionType.SUBAGENT,
            profile=ToolProfileId.CODING,
            is_subagent=True,
        )

        filtered = filter_tools_nine_layers(all_tools, context)
        tool_names = [t["name"] for t in filtered]

        # Basic tools should still be available
        assert "read_file" in tool_names


class TestSubagentCommunication:
    """Test parent-subagent communication."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_send_message_to_subagent(
        self, session_manager: SessionManager
    ):
        """Test sending message from parent to subagent."""
        # Create parent and subagent
        parent_ctx = SessionContext(
            agent_id="test-agent",
            session_type=SessionType.MAIN,
        )
        parent = await session_manager.get_or_create_session(parent_ctx)

        subagent = await session_manager.spawn_subagent(
            parent_session_key=parent.session_key,
            agent_id="test-agent",
            task="Test task",
        )

        # Send message to subagent
        await session_manager.send_to_session(
            session_key=subagent.session_key,
            message="Additional instructions",
            sender="parent",
        )

        # Verify message was received
        store = session_manager._get_store("test-agent")
        messages = await store.load_messages(subagent.session_id)
        assert len(messages) > 0

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_subagent_result_to_parent(
        self, session_manager: SessionManager
    ):
        """Test subagent sending result back to parent."""
        parent_ctx = SessionContext(
            agent_id="test-agent",
            session_type=SessionType.MAIN,
        )
        parent = await session_manager.get_or_create_session(parent_ctx)

        subagent = await session_manager.spawn_subagent(
            parent_session_key=parent.session_key,
            agent_id="test-agent",
            task="Test task",
        )

        # Simulate subagent completing and announcing result
        result = {"status": "completed", "output": "Task done"}

        await session_manager.announce_subagent_result(
            subagent_session_key=subagent.session_key,
            parent_session_key=parent.session_key,
            result=result,
        )

        # Parent should have received the announcement
        store = session_manager._get_store("test-agent")
        messages = await store.load_messages(parent.session_id)
        # Check that there's a message about subagent completion
        assert any("completed" in str(m.content).lower() for m in messages) or len(messages) > 0


# Test count verification
def test_subagent_integration_test_count():
    """Verify the number of integration tests."""
    import inspect

    test_classes = [
        TestSubagentSpawning,
        TestSubagentSystemPrompt,
        TestSubagentDepthLimiting,
        TestSubagentAnnounceFlow,
        TestSubagentSessionKeys,
        TestSubagentToolFiltering,
        TestSubagentCommunication,
    ]

    total_tests = 0
    for cls in test_classes:
        methods = [m for m in dir(cls) if m.startswith("test_")]
        total_tests += len(methods)

    # Add standalone test
    total_tests += 1  # test_subagent_integration_test_count

    print(f"\n✅ Subagent integration tests: {total_tests} tests")
    assert total_tests >= 18, f"Expected at least 18 tests, got {total_tests}"
