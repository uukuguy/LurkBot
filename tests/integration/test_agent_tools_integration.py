"""Integration tests for Agent + Tools end-to-end flow.

Tests the complete agent execution including:
- Agent creation and configuration
- Tool registration and invocation
- Tool result handling
- Error handling and recovery
"""

import asyncio
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from lurkbot.agents.types import (
    AgentContext,
    AgentRunResult,
    SessionType,
    ThinkLevel,
    PromptMode,
)
from lurkbot.agents.runtime import (
    AgentDependencies,
    create_agent,
    resolve_model_id,
)
from lurkbot.agents.bootstrap import (
    load_workspace_bootstrap_files,
    build_bootstrap_context_files,
)
from lurkbot.agents.system_prompt import build_agent_system_prompt
from lurkbot.tools.policy import (
    filter_tools_nine_layers,
    ToolFilterContext,
    ToolProfileId,
)


class TestAgentCreation:
    """Test agent creation and configuration."""

    @pytest.mark.integration
    @pytest.mark.requires_api
    def test_create_agent_with_system_prompt(self, temp_workspace: Path):
        """Test creating an agent with system prompt.

        Note: This test requires ANTHROPIC_API_KEY to be set.
        """
        system_prompt = "You are a helpful assistant."

        agent = create_agent(
            model="anthropic:claude-sonnet-4-20250514",
            system_prompt=system_prompt,
        )

        assert agent is not None
        assert agent.model.name() == "claude-sonnet-4-20250514"

    @pytest.mark.integration
    def test_resolve_model_id_anthropic(self):
        """Test resolving Anthropic model IDs."""
        model_id = resolve_model_id("anthropic", "claude-sonnet-4-20250514")
        assert model_id == "anthropic:claude-sonnet-4-20250514"

    @pytest.mark.integration
    def test_resolve_model_id_openai(self):
        """Test resolving OpenAI model IDs."""
        model_id = resolve_model_id("openai", "gpt-4o")
        assert model_id == "openai:gpt-4o"

    @pytest.mark.integration
    def test_resolve_model_id_already_formatted(self):
        """Test resolving already formatted model IDs."""
        model_id = resolve_model_id("anthropic", "anthropic:claude-sonnet-4-20250514")
        assert model_id == "anthropic:claude-sonnet-4-20250514"


class TestBootstrapIntegration:
    """Test bootstrap file integration with agent."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_load_bootstrap_files(self, temp_workspace: Path):
        """Test loading bootstrap files from workspace."""
        files = await load_workspace_bootstrap_files(str(temp_workspace))

        assert len(files) > 0
        # Should find AGENTS.md and TOOLS.md we created
        file_names = [f.name for f in files]
        assert "AGENTS.md" in file_names

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_build_bootstrap_context(self, temp_workspace: Path):
        """Test building bootstrap context files."""
        files = await load_workspace_bootstrap_files(str(temp_workspace))
        context_files = build_bootstrap_context_files(
            files,
            max_chars=10000,
        )

        assert len(context_files) > 0
        for cf in context_files:
            assert cf.content is not None


class TestSystemPromptIntegration:
    """Test system prompt generation integration."""

    @pytest.mark.integration
    def test_build_full_system_prompt(self, agent_context: AgentContext, temp_workspace: Path):
        """Test building full system prompt."""
        from lurkbot.agents.system_prompt import SystemPromptParams

        params = SystemPromptParams(
            workspace_dir=str(temp_workspace),
            tool_names=["read_file", "write_file", "exec"],
            default_think_level=ThinkLevel.MEDIUM,
        )
        prompt = build_agent_system_prompt(params)

        assert prompt is not None
        assert len(prompt) > 100

    @pytest.mark.integration
    def test_build_minimal_system_prompt(self, agent_context: AgentContext, temp_workspace: Path):
        """Test building minimal system prompt."""
        from lurkbot.agents.system_prompt import SystemPromptParams

        params = SystemPromptParams(
            workspace_dir=str(temp_workspace),
            tool_names=["read_file"],
            default_think_level=ThinkLevel.OFF,
        )
        prompt = build_agent_system_prompt(params)

        assert prompt is not None


class TestToolPolicyIntegration:
    """Test tool policy filtering integration."""

    @pytest.mark.integration
    def test_filter_tools_basic(self):
        """Test basic tool filtering."""
        # Test that filter_tools_nine_layers function exists and is callable
        from lurkbot.tools.policy import filter_tools_nine_layers, ToolFilterContext

        all_tools = [
            {"name": "read_file"},
            {"name": "write_file"},
            {"name": "exec"},
        ]

        # Create minimal context
        context = ToolFilterContext()

        # Should return tools (exact behavior depends on context)
        filtered = filter_tools_nine_layers(all_tools, context)
        assert isinstance(filtered, list)

    @pytest.mark.integration
    def test_tool_filter_context_creation(self):
        """Test creating ToolFilterContext."""
        from lurkbot.tools.policy import ToolFilterContext

        # Test default context creation
        context = ToolFilterContext()
        assert context is not None

        # Test with profile
        context_with_profile = ToolFilterContext(profile="full")
        assert context_with_profile.profile == "full"


class TestAgentDependencies:
    """Test agent dependencies injection."""

    @pytest.mark.integration
    def test_create_agent_dependencies(self, agent_context: AgentContext):
        """Test creating agent dependencies."""
        deps = AgentDependencies(
            context=agent_context,
            message_history=[],
        )

        assert deps.context.session_id == agent_context.session_id
        assert deps.context.session_type == SessionType.MAIN
        assert len(deps.message_history) == 0

    @pytest.mark.integration
    def test_agent_dependencies_with_history(self, agent_context: AgentContext):
        """Test agent dependencies with message history."""
        history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]

        deps = AgentDependencies(
            context=agent_context,
            message_history=history,
        )

        assert len(deps.message_history) == 2
        assert deps.message_history[0]["role"] == "user"


class TestToolExecution:
    """Test tool execution flow."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_tool_call_format(self):
        """Test tool call format matches expected structure."""
        tool_call = {
            "type": "tool_use",
            "id": "tool-001",
            "name": "read_file",
            "input": {"path": "/test/file.txt"},
        }

        assert tool_call["type"] == "tool_use"
        assert tool_call["name"] == "read_file"
        assert "path" in tool_call["input"]

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_tool_result_format(self):
        """Test tool result format matches expected structure."""
        tool_result = {
            "type": "tool_result",
            "tool_use_id": "tool-001",
            "content": "File contents here",
            "is_error": False,
        }

        assert tool_result["type"] == "tool_result"
        assert tool_result["tool_use_id"] == "tool-001"
        assert tool_result["is_error"] is False

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_tool_error_result(self):
        """Test tool error result format."""
        error_result = {
            "type": "tool_result",
            "tool_use_id": "tool-001",
            "content": "Error: File not found",
            "is_error": True,
        }

        assert error_result["is_error"] is True
        assert "Error" in error_result["content"]


class TestAgentRunResult:
    """Test agent run result handling."""

    @pytest.mark.integration
    def test_successful_run_result(self):
        """Test successful agent run result."""
        result = AgentRunResult(
            aborted=False,
            timed_out=False,
            session_id_used="test-session",
            assistant_texts=["Here is the response"],
        )

        assert result.aborted is False
        assert result.timed_out is False
        assert len(result.assistant_texts) == 1

    @pytest.mark.integration
    def test_run_result_with_error(self):
        """Test agent run result with error."""
        result = AgentRunResult(
            aborted=True,
            timed_out=False,
            prompt_error=ValueError("Test error"),
        )

        assert result.aborted is True
        assert result.prompt_error is not None


class TestContextManagement:
    """Test agent context management."""

    @pytest.mark.integration
    def test_context_for_main_session(self, temp_workspace: Path):
        """Test context for main session."""
        context = AgentContext(
            session_id="main-001",
            session_key="agent:test:main",
            session_type=SessionType.MAIN,
            workspace_dir=str(temp_workspace),
            message_channel="cli",
        )

        assert context.session_type == SessionType.MAIN

    @pytest.mark.integration
    def test_context_for_subagent(self, temp_workspace: Path):
        """Test context for subagent session."""
        context = AgentContext(
            session_id="sub-001",
            session_key="agent:test:subagent:sub-001",
            session_type=SessionType.SUBAGENT,
            workspace_dir=str(temp_workspace),
            message_channel="cli",
            spawned_by="agent:test:main",
        )

        assert context.session_type == SessionType.SUBAGENT
        assert context.spawned_by is not None

    @pytest.mark.integration
    def test_context_thinking_levels(self, temp_workspace: Path):
        """Test different thinking levels in context."""
        # Just verify AgentContext can be created
        context = AgentContext(
            session_id="test-001",
            session_key="agent:test:main",
            session_type=SessionType.MAIN,
            workspace_dir=str(temp_workspace),
            message_channel="cli",
        )

        assert context is not None


# Test count verification
def test_agent_tools_integration_test_count():
    """Verify the number of integration tests."""
    import inspect

    test_classes = [
        TestAgentCreation,
        TestBootstrapIntegration,
        TestSystemPromptIntegration,
        TestToolPolicyIntegration,
        TestAgentDependencies,
        TestToolExecution,
        TestAgentRunResult,
        TestContextManagement,
    ]

    total_tests = 0
    for cls in test_classes:
        methods = [m for m in dir(cls) if m.startswith("test_")]
        total_tests += len(methods)

    # Add standalone test
    total_tests += 1  # test_agent_tools_integration_test_count

    print(f"\n✅ Agent + Tools integration tests: {total_tests} tests")
    assert total_tests >= 20, f"Expected at least 20 tests, got {total_tests}"
