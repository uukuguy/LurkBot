"""Tests for system prompt generator."""

import pytest

from lurkbot.agents.bootstrap import ContextFile
from lurkbot.agents.system_prompt import (
    CHAT_CHANNEL_ORDER,
    CORE_TOOL_SUMMARIES,
    DEFAULT_HEARTBEAT_PROMPT,
    HEARTBEAT_TOKEN,
    INTERNAL_MESSAGE_CHANNEL,
    MARKDOWN_CAPABLE_CHANNELS,
    SILENT_REPLY_TOKEN,
    TOOL_ORDER,
    ReactionGuidance,
    RuntimeInfo,
    SandboxInfo,
    SystemPromptParams,
    build_agent_system_prompt,
    build_runtime_line,
    is_silent_reply_text,
    list_deliverable_message_channels,
)
from lurkbot.agents.types import PromptMode, ThinkLevel


class TestConstants:
    """Tests for system prompt constants."""

    def test_silent_reply_token(self):
        """Test silent reply token value."""
        assert SILENT_REPLY_TOKEN == "NO_REPLY"

    def test_heartbeat_token(self):
        """Test heartbeat token value."""
        assert HEARTBEAT_TOKEN == "HEARTBEAT_OK"

    def test_default_heartbeat_prompt(self):
        """Test default heartbeat prompt content."""
        assert "HEARTBEAT.md" in DEFAULT_HEARTBEAT_PROMPT
        assert "HEARTBEAT_OK" in DEFAULT_HEARTBEAT_PROMPT

    def test_chat_channel_order(self):
        """Test chat channel order includes expected channels."""
        assert "telegram" in CHAT_CHANNEL_ORDER
        assert "discord" in CHAT_CHANNEL_ORDER
        assert "slack" in CHAT_CHANNEL_ORDER
        assert "whatsapp" in CHAT_CHANNEL_ORDER

    def test_internal_message_channel(self):
        """Test internal message channel value."""
        assert INTERNAL_MESSAGE_CHANNEL == "webchat"

    def test_markdown_capable_channels(self):
        """Test markdown capable channels set."""
        assert "slack" in MARKDOWN_CAPABLE_CHANNELS
        assert "telegram" in MARKDOWN_CAPABLE_CHANNELS
        assert "discord" in MARKDOWN_CAPABLE_CHANNELS
        assert INTERNAL_MESSAGE_CHANNEL in MARKDOWN_CAPABLE_CHANNELS

    def test_tool_order_contains_core_tools(self):
        """Test tool order contains all core tools."""
        assert "read" in TOOL_ORDER
        assert "write" in TOOL_ORDER
        assert "edit" in TOOL_ORDER
        assert "exec" in TOOL_ORDER
        assert "cron" in TOOL_ORDER
        assert "message" in TOOL_ORDER

    def test_core_tool_summaries(self):
        """Test core tool summaries are defined."""
        assert "read" in CORE_TOOL_SUMMARIES
        assert "write" in CORE_TOOL_SUMMARIES
        assert CORE_TOOL_SUMMARIES["read"] == "Read file contents"


class TestListDeliverableMessageChannels:
    """Tests for list_deliverable_message_channels function."""

    def test_returns_channel_list(self):
        """Test function returns a list of channels."""
        channels = list_deliverable_message_channels()
        assert isinstance(channels, list)
        assert len(channels) > 0

    def test_contains_core_channels(self):
        """Test returned list contains core channels."""
        channels = list_deliverable_message_channels()
        assert "telegram" in channels
        assert "discord" in channels


class TestIsSilentReplyText:
    """Tests for is_silent_reply_text function."""

    def test_none_text(self):
        """Test None text returns False."""
        assert not is_silent_reply_text(None)

    def test_empty_text(self):
        """Test empty text returns False."""
        assert not is_silent_reply_text("")

    def test_exact_token(self):
        """Test exact token match."""
        assert is_silent_reply_text(SILENT_REPLY_TOKEN)

    def test_token_at_start(self):
        """Test token at start of text."""
        assert is_silent_reply_text(f"{SILENT_REPLY_TOKEN} some explanation")

    def test_token_at_end(self):
        """Test token at end of text."""
        assert is_silent_reply_text(f"Done. {SILENT_REPLY_TOKEN}")

    def test_token_in_middle_returns_false(self):
        """Test token in middle returns False."""
        assert not is_silent_reply_text(f"Hello {SILENT_REPLY_TOKEN} world")

    def test_token_with_whitespace(self):
        """Test token with leading/trailing whitespace."""
        assert is_silent_reply_text(f"  {SILENT_REPLY_TOKEN}")
        assert is_silent_reply_text(f"{SILENT_REPLY_TOKEN}  ")


class TestBuildRuntimeLine:
    """Tests for build_runtime_line function."""

    def test_basic_runtime_line(self):
        """Test basic runtime line generation."""
        info = RuntimeInfo(agent_id="main", host="test-host")
        line = build_runtime_line(info, None, [], ThinkLevel.MEDIUM)

        assert "Runtime:" in line
        assert "agent=main" in line
        assert "host=test-host" in line
        assert "thinking=medium" in line

    def test_runtime_line_with_channel(self):
        """Test runtime line with channel info."""
        info = RuntimeInfo(agent_id="main")
        line = build_runtime_line(info, "telegram", ["inlineButtons"], ThinkLevel.HIGH)

        assert "channel=telegram" in line
        assert "capabilities=inlineButtons" in line
        assert "thinking=high" in line

    def test_runtime_line_with_os(self):
        """Test runtime line with OS info."""
        info = RuntimeInfo(os="Linux", arch="x86_64")
        line = build_runtime_line(info, None, [], ThinkLevel.OFF)

        assert "os=Linux (x86_64)" in line

    def test_runtime_line_empty_capabilities(self):
        """Test runtime line with empty capabilities."""
        info = RuntimeInfo(agent_id="main")
        line = build_runtime_line(info, "discord", [], ThinkLevel.LOW)

        assert "capabilities=none" in line


class TestSystemPromptParams:
    """Tests for SystemPromptParams dataclass."""

    def test_default_values(self):
        """Test default parameter values."""
        params = SystemPromptParams(workspace_dir="/test")

        assert params.workspace_dir == "/test"
        assert params.default_think_level == ThinkLevel.MEDIUM
        assert params.reasoning_level == "off"
        assert params.prompt_mode == PromptMode.FULL
        assert params.tool_names == []
        assert params.context_files == []

    def test_custom_values(self):
        """Test custom parameter values."""
        params = SystemPromptParams(
            workspace_dir="/custom",
            default_think_level=ThinkLevel.HIGH,
            prompt_mode=PromptMode.MINIMAL,
            tool_names=["read", "write"],
        )

        assert params.workspace_dir == "/custom"
        assert params.default_think_level == ThinkLevel.HIGH
        assert params.prompt_mode == PromptMode.MINIMAL
        assert params.tool_names == ["read", "write"]


class TestBuildAgentSystemPromptBasic:
    """Tests for build_agent_system_prompt basic functionality."""

    def test_none_mode_returns_minimal(self):
        """Test 'none' mode returns minimal prompt."""
        params = SystemPromptParams(
            workspace_dir="/test",
            prompt_mode=PromptMode.NONE,
        )

        prompt = build_agent_system_prompt(params)

        assert prompt == "You are a personal assistant running inside LurkBot."

    def test_full_mode_includes_identity(self):
        """Test full mode includes identity line."""
        params = SystemPromptParams(workspace_dir="/test")

        prompt = build_agent_system_prompt(params)

        assert "You are a personal assistant running inside LurkBot." in prompt

    def test_includes_workspace_dir(self):
        """Test prompt includes workspace directory."""
        params = SystemPromptParams(workspace_dir="/my/workspace")

        prompt = build_agent_system_prompt(params)

        assert "/my/workspace" in prompt
        assert "Your working directory is:" in prompt

    def test_includes_runtime_section(self):
        """Test prompt includes runtime section."""
        params = SystemPromptParams(workspace_dir="/test")

        prompt = build_agent_system_prompt(params)

        assert "## Runtime" in prompt
        assert "thinking=" in prompt


class TestBuildAgentSystemPromptTools:
    """Tests for tool-related system prompt sections."""

    def test_tooling_section_included(self):
        """Test tooling section is included."""
        params = SystemPromptParams(
            workspace_dir="/test",
            tool_names=["read", "write", "exec"],
        )

        prompt = build_agent_system_prompt(params)

        assert "## Tooling" in prompt
        assert "Tool availability" in prompt

    def test_tool_names_in_prompt(self):
        """Test tool names appear in prompt."""
        params = SystemPromptParams(
            workspace_dir="/test",
            tool_names=["read", "write", "exec"],
        )

        prompt = build_agent_system_prompt(params)

        assert "- read:" in prompt
        assert "- write:" in prompt
        assert "- exec:" in prompt

    def test_tool_summaries_used(self):
        """Test tool summaries are included."""
        params = SystemPromptParams(
            workspace_dir="/test",
            tool_names=["read"],
        )

        prompt = build_agent_system_prompt(params)

        assert "Read file contents" in prompt

    def test_custom_tool_summaries(self):
        """Test custom tool summaries are used."""
        params = SystemPromptParams(
            workspace_dir="/test",
            tool_names=["custom_tool"],
            tool_summaries={"custom_tool": "Does something custom"},
        )

        prompt = build_agent_system_prompt(params)

        assert "- custom_tool: Does something custom" in prompt

    def test_tool_call_style_section(self):
        """Test tool call style section is included."""
        params = SystemPromptParams(workspace_dir="/test")

        prompt = build_agent_system_prompt(params)

        assert "## Tool Call Style" in prompt
        assert "do not narrate routine" in prompt


class TestBuildAgentSystemPromptSkills:
    """Tests for skills-related system prompt sections."""

    def test_skills_section_included(self):
        """Test skills section is included when skills_prompt provided."""
        params = SystemPromptParams(
            workspace_dir="/test",
            skills_prompt="<available_skills>test skill</available_skills>",
        )

        prompt = build_agent_system_prompt(params)

        assert "## Skills (mandatory)" in prompt
        assert "available_skills" in prompt

    def test_skills_section_excluded_in_minimal(self):
        """Test skills section is excluded in minimal mode."""
        params = SystemPromptParams(
            workspace_dir="/test",
            skills_prompt="<available_skills>test</available_skills>",
            prompt_mode=PromptMode.MINIMAL,
        )

        prompt = build_agent_system_prompt(params)

        assert "## Skills (mandatory)" not in prompt


class TestBuildAgentSystemPromptContext:
    """Tests for context-related system prompt sections."""

    def test_context_files_included(self):
        """Test context files are included in prompt."""
        params = SystemPromptParams(
            workspace_dir="/test",
            context_files=[
                ContextFile(path="AGENTS.md", content="Agent content"),
                ContextFile(path="TOOLS.md", content="Tools content"),
            ],
        )

        prompt = build_agent_system_prompt(params)

        assert "# Project Context" in prompt
        assert "## AGENTS.md" in prompt
        assert "Agent content" in prompt
        assert "## TOOLS.md" in prompt
        assert "Tools content" in prompt

    def test_soul_file_persona_hint(self):
        """Test SOUL.md triggers persona embodiment hint."""
        params = SystemPromptParams(
            workspace_dir="/test",
            context_files=[
                ContextFile(path="SOUL.md", content="Be friendly"),
            ],
        )

        prompt = build_agent_system_prompt(params)

        assert "embody its persona and tone" in prompt


class TestBuildAgentSystemPromptMinimalMode:
    """Tests for minimal mode system prompt."""

    def test_minimal_mode_excludes_memory(self):
        """Test minimal mode excludes memory section."""
        params = SystemPromptParams(
            workspace_dir="/test",
            prompt_mode=PromptMode.MINIMAL,
            tool_names=["memory_search", "memory_get"],
        )

        prompt = build_agent_system_prompt(params)

        assert "## Memory Recall" not in prompt

    def test_minimal_mode_excludes_silent_replies(self):
        """Test minimal mode excludes silent replies section."""
        params = SystemPromptParams(
            workspace_dir="/test",
            prompt_mode=PromptMode.MINIMAL,
        )

        prompt = build_agent_system_prompt(params)

        assert "## Silent Replies" not in prompt

    def test_minimal_mode_excludes_heartbeats(self):
        """Test minimal mode excludes heartbeats section."""
        params = SystemPromptParams(
            workspace_dir="/test",
            prompt_mode=PromptMode.MINIMAL,
        )

        prompt = build_agent_system_prompt(params)

        assert "## Heartbeats" not in prompt

    def test_minimal_mode_uses_subagent_context_header(self):
        """Test minimal mode uses 'Subagent Context' header."""
        params = SystemPromptParams(
            workspace_dir="/test",
            prompt_mode=PromptMode.MINIMAL,
            extra_system_prompt="Do this specific task",
        )

        prompt = build_agent_system_prompt(params)

        assert "## Subagent Context" in prompt
        assert "## Group Chat Context" not in prompt


class TestBuildAgentSystemPromptFullMode:
    """Tests for full mode system prompt."""

    def test_full_mode_includes_memory(self):
        """Test full mode includes memory section."""
        params = SystemPromptParams(
            workspace_dir="/test",
            prompt_mode=PromptMode.FULL,
            tool_names=["memory_search"],
        )

        prompt = build_agent_system_prompt(params)

        assert "## Memory Recall" in prompt

    def test_full_mode_includes_silent_replies(self):
        """Test full mode includes silent replies section."""
        params = SystemPromptParams(
            workspace_dir="/test",
            prompt_mode=PromptMode.FULL,
        )

        prompt = build_agent_system_prompt(params)

        assert "## Silent Replies" in prompt
        assert SILENT_REPLY_TOKEN in prompt

    def test_full_mode_includes_heartbeats(self):
        """Test full mode includes heartbeats section."""
        params = SystemPromptParams(
            workspace_dir="/test",
            prompt_mode=PromptMode.FULL,
        )

        prompt = build_agent_system_prompt(params)

        assert "## Heartbeats" in prompt
        assert "HEARTBEAT_OK" in prompt

    def test_full_mode_uses_group_chat_header(self):
        """Test full mode uses 'Group Chat Context' header."""
        params = SystemPromptParams(
            workspace_dir="/test",
            prompt_mode=PromptMode.FULL,
            extra_system_prompt="Group chat rules",
        )

        prompt = build_agent_system_prompt(params)

        assert "## Group Chat Context" in prompt
        assert "## Subagent Context" not in prompt


class TestBuildAgentSystemPromptSandbox:
    """Tests for sandbox-related system prompt sections."""

    def test_sandbox_section_included(self):
        """Test sandbox section is included when enabled."""
        params = SystemPromptParams(
            workspace_dir="/test",
            sandbox_info=SandboxInfo(
                enabled=True,
                workspace_dir="/sandbox/workspace",
            ),
        )

        prompt = build_agent_system_prompt(params)

        assert "## Sandbox" in prompt
        assert "sandboxed runtime" in prompt

    def test_sandbox_section_excluded(self):
        """Test sandbox section is excluded when disabled."""
        params = SystemPromptParams(
            workspace_dir="/test",
            sandbox_info=SandboxInfo(enabled=False),
        )

        prompt = build_agent_system_prompt(params)

        assert "## Sandbox" not in prompt

    def test_sandbox_elevated_info(self):
        """Test sandbox elevated info is included."""
        params = SystemPromptParams(
            workspace_dir="/test",
            sandbox_info=SandboxInfo(
                enabled=True,
                elevated_allowed=True,
                elevated_default_level="ask",
            ),
        )

        prompt = build_agent_system_prompt(params)

        assert "Elevated exec is available" in prompt
        assert "Current elevated level: ask" in prompt


class TestBuildAgentSystemPromptMessaging:
    """Tests for messaging-related system prompt sections."""

    def test_messaging_section_included(self):
        """Test messaging section is included in full mode."""
        params = SystemPromptParams(workspace_dir="/test")

        prompt = build_agent_system_prompt(params)

        assert "## Messaging" in prompt

    def test_message_tool_details(self):
        """Test message tool details when available."""
        params = SystemPromptParams(
            workspace_dir="/test",
            tool_names=["message"],
        )

        prompt = build_agent_system_prompt(params)

        assert "### message tool" in prompt
        assert "action=send" in prompt

    def test_inline_buttons_enabled(self):
        """Test inline buttons info when enabled."""
        params = SystemPromptParams(
            workspace_dir="/test",
            tool_names=["message"],
            runtime_info=RuntimeInfo(
                channel="telegram",
                capabilities=["inlineButtons"],
            ),
        )

        prompt = build_agent_system_prompt(params)

        assert "Inline buttons supported" in prompt


class TestBuildAgentSystemPromptReactions:
    """Tests for reactions-related system prompt sections."""

    def test_minimal_reactions(self):
        """Test minimal reactions guidance."""
        params = SystemPromptParams(
            workspace_dir="/test",
            reaction_guidance=ReactionGuidance(
                level="minimal",
                channel="telegram",
            ),
        )

        prompt = build_agent_system_prompt(params)

        assert "## Reactions" in prompt
        assert "MINIMAL mode" in prompt
        assert "at most 1 reaction per 5-10 exchanges" in prompt

    def test_extensive_reactions(self):
        """Test extensive reactions guidance."""
        params = SystemPromptParams(
            workspace_dir="/test",
            reaction_guidance=ReactionGuidance(
                level="extensive",
                channel="discord",
            ),
        )

        prompt = build_agent_system_prompt(params)

        assert "## Reactions" in prompt
        assert "EXTENSIVE mode" in prompt
        assert "react whenever it feels natural" in prompt


class TestBuildAgentSystemPromptReasoning:
    """Tests for reasoning-related system prompt sections."""

    def test_reasoning_format_included(self):
        """Test reasoning format section when enabled."""
        params = SystemPromptParams(
            workspace_dir="/test",
            reasoning_tag_hint=True,
        )

        prompt = build_agent_system_prompt(params)

        assert "## Reasoning Format" in prompt
        assert "<think>...</think>" in prompt
        assert "<final>...</final>" in prompt

    def test_reasoning_format_excluded(self):
        """Test reasoning format section when disabled."""
        params = SystemPromptParams(
            workspace_dir="/test",
            reasoning_tag_hint=False,
        )

        prompt = build_agent_system_prompt(params)

        assert "## Reasoning Format" not in prompt
