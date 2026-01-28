"""Integration tests for approval workflow.

Tests the complete flow:
1. Agent Runtime requests tool approval
2. Approval notification sent via Channel
3. User responds with /approve or /deny
4. Tool executes only if approved
"""

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from lurkbot.agents.base import AgentContext
from lurkbot.agents.runtime import AgentRuntime, ModelAgent
from lurkbot.channels.telegram import TelegramChannel
from lurkbot.config import Settings
from lurkbot.config.settings import TelegramSettings
from lurkbot.models.types import ModelResponse, ToolCall
from lurkbot.tools import SessionType
from lurkbot.tools.approval import ApprovalDecision, ApprovalManager, ApprovalRequest
from lurkbot.tools.base import Tool, ToolPolicy, ToolResult


class MockDangerousTool(Tool):
    """Mock tool that requires approval."""

    def __init__(self) -> None:
        super().__init__(
            name="dangerous_tool",
            description="A dangerous tool requiring approval",
            policy=ToolPolicy(
                allowed_session_types={SessionType.MAIN, SessionType.GROUP},
                requires_approval=True,
            ),
        )
        self.executed = False
        self.execution_args: dict | None = None

    async def execute(
        self,
        arguments: dict,
        workspace: str,  # noqa: ARG002
        session_type: SessionType,  # noqa: ARG002
    ) -> ToolResult:
        self.executed = True
        self.execution_args = arguments
        return ToolResult(success=True, output="Dangerous operation completed")

    def get_schema(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": {
                    "operation": {"type": "string", "description": "Operation to perform"}
                },
                "required": ["operation"],
            },
        }


@pytest.fixture
def approval_manager() -> ApprovalManager:
    """Create approval manager."""
    return ApprovalManager()


@pytest.fixture
def telegram_channel(approval_manager: ApprovalManager) -> TelegramChannel:
    """Create mock Telegram channel."""
    settings = TelegramSettings(bot_token="test_token", enabled=True)
    channel = TelegramChannel(settings, approval_manager)
    # Mock the bot app
    channel._app = MagicMock()
    channel._app.bot = AsyncMock()
    channel._running = True
    return channel


@pytest.fixture
def settings() -> Settings:
    """Create test settings."""
    return Settings(
        anthropic_api_key="test_key",
        agent={"model": "anthropic/claude-sonnet-4-20250514"},
    )


@pytest.fixture
def agent_runtime(
    settings: Settings, telegram_channel: TelegramChannel, approval_manager: ApprovalManager
) -> AgentRuntime:
    """Create agent runtime with approval support."""
    runtime = AgentRuntime(settings, channel=telegram_channel)
    # Replace approval manager with test instance
    runtime.approval_manager = approval_manager
    return runtime


def create_tool_use_response(tool_name: str, tool_id: str, tool_input: dict) -> ModelResponse:
    """Create a ModelResponse with a tool call."""
    return ModelResponse(
        text=None,
        tool_calls=[
            ToolCall(
                id=tool_id,
                name=tool_name,
                arguments=tool_input,
            )
        ],
        stop_reason="tool_use",
    )


def create_text_response(text: str) -> ModelResponse:
    """Create a ModelResponse with text."""
    return ModelResponse(
        text=text,
        tool_calls=[],
        stop_reason="end_turn",
    )


class TestApprovalIntegration:
    """Integration tests for approval workflow."""

    @pytest.mark.asyncio
    async def test_approval_required_tool_approved(
        self, agent_runtime: AgentRuntime, telegram_channel: TelegramChannel
    ) -> None:
        """Test tool execution after approval."""
        # Register dangerous tool
        dangerous_tool = MockDangerousTool()
        agent_runtime.tool_registry.register(dangerous_tool)

        # Create mock agent with mocked adapter
        agent = agent_runtime.get_agent()
        assert isinstance(agent, ModelAgent)

        # Mock adapter responses
        mock_response_1 = create_tool_use_response(
            "dangerous_tool", "tool_123", {"operation": "delete_database"}
        )
        mock_response_2 = create_text_response("Operation completed")

        mock_adapter = MagicMock()
        mock_adapter.chat = AsyncMock(side_effect=[mock_response_1, mock_response_2])
        agent._adapter = mock_adapter

        # Create agent context
        context = AgentContext(
            session_id="test_session",
            channel="telegram",
            sender_id="12345",
            sender_name="Test User",
            workspace="/tmp/test",
            session_type=SessionType.MAIN,
        )

        # Start chat in background
        chat_task = asyncio.create_task(agent.chat(context, "Execute dangerous operation"))

        # Wait for approval notification to be sent
        await asyncio.sleep(0.1)

        # Verify notification was sent
        assert telegram_channel._app.bot.send_message.called
        call_args = telegram_channel._app.bot.send_message.call_args
        assert "Tool Approval Required" in call_args.kwargs["text"]
        assert "dangerous_tool" in call_args.kwargs["text"]

        # Get approval ID from notification
        notification = call_args.kwargs["text"]
        # Extract approval ID from "/approve {id}" line
        approval_id = notification.split("/approve ")[1].split(" or")[0]

        # Approve the tool
        agent_runtime.approval_manager.resolve(approval_id, ApprovalDecision.APPROVE, "12345")

        # Wait for chat to complete
        response = await chat_task

        # Verify tool was executed
        assert dangerous_tool.executed
        assert dangerous_tool.execution_args == {"operation": "delete_database"}
        assert "Operation completed" in response

    @pytest.mark.asyncio
    async def test_approval_required_tool_denied(
        self, agent_runtime: AgentRuntime, telegram_channel: TelegramChannel
    ) -> None:
        """Test tool execution denied."""
        # Register dangerous tool
        dangerous_tool = MockDangerousTool()
        agent_runtime.tool_registry.register(dangerous_tool)

        agent = agent_runtime.get_agent()
        assert isinstance(agent, ModelAgent)

        # Mock adapter responses
        mock_response_1 = create_tool_use_response(
            "dangerous_tool", "tool_123", {"operation": "delete_database"}
        )
        mock_response_2 = create_text_response("Operation was denied")

        mock_adapter = MagicMock()
        mock_adapter.chat = AsyncMock(side_effect=[mock_response_1, mock_response_2])
        agent._adapter = mock_adapter

        context = AgentContext(
            session_id="test_session",
            channel="telegram",
            sender_id="12345",
            sender_name="Test User",
            workspace="/tmp/test",
            session_type=SessionType.MAIN,
        )

        # Start chat in background
        chat_task = asyncio.create_task(agent.chat(context, "Execute dangerous operation"))

        # Wait for approval notification
        await asyncio.sleep(0.1)

        # Get approval ID
        call_args = telegram_channel._app.bot.send_message.call_args
        notification = call_args.kwargs["text"]
        approval_id = notification.split("/approve ")[1].split(" or")[0]

        # Deny the tool
        agent_runtime.approval_manager.resolve(approval_id, ApprovalDecision.DENY, "12345")

        # Wait for chat to complete
        response = await chat_task

        # Verify tool was NOT executed
        assert not dangerous_tool.executed
        assert "Operation was denied" in response

    @pytest.mark.asyncio
    async def test_approval_timeout(
        self,
        agent_runtime: AgentRuntime,
        telegram_channel: TelegramChannel,  # noqa: ARG002
    ) -> None:
        """Test approval timeout."""
        dangerous_tool = MockDangerousTool()
        agent_runtime.tool_registry.register(dangerous_tool)

        agent = agent_runtime.get_agent()
        assert isinstance(agent, ModelAgent)

        # Mock adapter responses
        mock_response_1 = create_tool_use_response(
            "dangerous_tool", "tool_123", {"operation": "delete_database"}
        )
        mock_response_2 = create_text_response("Operation timed out")

        mock_adapter = MagicMock()
        mock_adapter.chat = AsyncMock(side_effect=[mock_response_1, mock_response_2])
        agent._adapter = mock_adapter

        # Override approval manager to use short timeout
        original_create = agent_runtime.approval_manager.create

        def create_with_timeout(
            request: ApprovalRequest, **kwargs: Any  # noqa: ARG001
        ) -> Any:  # type: ignore
            # Use 100ms timeout for testing
            return original_create(request, timeout_ms=100)

        with patch.object(
            agent_runtime.approval_manager, "create", side_effect=create_with_timeout
        ):
            context = AgentContext(
                session_id="test_session",
                channel="telegram",
                sender_id="12345",
                sender_name="Test User",
                workspace="/tmp/test",
                session_type=SessionType.MAIN,
            )

            # Execute chat (will timeout)
            response = await agent.chat(context, "Execute dangerous operation")

            # Verify tool was NOT executed due to timeout
            assert not dangerous_tool.executed
            assert "Operation timed out" in response

    @pytest.mark.asyncio
    async def test_multiple_sequential_approvals(
        self,
        agent_runtime: AgentRuntime,
        telegram_channel: TelegramChannel,  # noqa: ARG002
    ) -> None:
        """Test multiple tools requiring approval sequentially."""
        # Register two dangerous tools
        tool1 = MockDangerousTool()
        tool1.name = "dangerous_tool_1"

        tool2 = MockDangerousTool()
        tool2.name = "dangerous_tool_2"

        agent_runtime.tool_registry.register(tool1)
        agent_runtime.tool_registry.register(tool2)

        agent = agent_runtime.get_agent()

        # Mock adapter responses for two sequential tool uses
        mock_response_1 = create_tool_use_response(
            "dangerous_tool_1", "tool_1", {"operation": "op1"}
        )
        mock_response_2 = create_tool_use_response(
            "dangerous_tool_2", "tool_2", {"operation": "op2"}
        )
        mock_response_3 = create_text_response("Both operations completed")

        mock_adapter = MagicMock()
        mock_adapter.chat = AsyncMock(
            side_effect=[mock_response_1, mock_response_2, mock_response_3]
        )
        agent._adapter = mock_adapter

        context = AgentContext(
            session_id="test_session",
            channel="telegram",
            sender_id="12345",
            sender_name="Test User",
            workspace="/tmp/test",
            session_type=SessionType.MAIN,
        )

        # Start chat in background
        async def execute_with_approvals() -> str:
            # Execute chat, approving tools as they come
            task = asyncio.create_task(agent.chat(context, "Execute two operations"))

            # Wait for first approval
            await asyncio.sleep(0.1)
            pending = agent_runtime.approval_manager.get_all_pending()
            assert len(pending) == 1
            agent_runtime.approval_manager.resolve(pending[0].id, ApprovalDecision.APPROVE, "12345")

            # Wait for second approval
            await asyncio.sleep(0.1)
            pending = agent_runtime.approval_manager.get_all_pending()
            assert len(pending) == 1
            agent_runtime.approval_manager.resolve(pending[0].id, ApprovalDecision.DENY, "12345")

            return await task

        response = await execute_with_approvals()

        # Verify: tool1 executed, tool2 not executed
        assert tool1.executed
        assert not tool2.executed
        assert "Both operations completed" in response
