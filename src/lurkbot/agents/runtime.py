"""Agent runtime for managing agent sessions."""

from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Any

from loguru import logger

from lurkbot.agents.base import Agent, AgentContext, ChatMessage
from lurkbot.config import Settings
from lurkbot.models import ModelRegistry, ToolCall, ToolResult
from lurkbot.storage.jsonl import SessionMessage, SessionStore
from lurkbot.tools import SessionType, ToolRegistry
from lurkbot.tools.approval import ApprovalDecision, ApprovalManager, ApprovalRequest
from lurkbot.tools.builtin.bash import BashTool
from lurkbot.tools.builtin.file_ops import ReadFileTool, WriteFileTool

if TYPE_CHECKING:
    from lurkbot.channels.base import Channel


class ModelAgent(Agent):
    """Agent using the multi-model adapter system.

    Supports Anthropic, OpenAI, Ollama, and other providers through
    the unified ModelAdapter interface.
    """

    def __init__(
        self,
        model: str,
        model_registry: ModelRegistry,
        tool_registry: ToolRegistry | None = None,
        approval_manager: ApprovalManager | None = None,
        channel: "Channel | None" = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(model, **kwargs)
        self.model_registry = model_registry
        self.tool_registry = tool_registry
        self.approval_manager = approval_manager
        self.channel = channel

        # Get the model adapter
        self._adapter = model_registry.get_adapter(model)
        logger.info(f"Initialized ModelAgent with {model}")

    async def chat(self, context: AgentContext, message: str) -> str:
        """Process a chat message with tool support.

        This method supports tool use through an iterative loop:
        1. Send message to model with available tools
        2. If model wants to use a tool, execute it
        3. Send tool result back and continue conversation
        4. Repeat until model provides a text response
        """
        # Add user message to context
        context.messages.append(ChatMessage(role="user", content=message))

        # Prepare messages for API (convert to dict format)
        messages = self._prepare_messages(context)

        # Get tool schemas if tool registry is available
        tools = None
        if self.tool_registry:
            tools = self.tool_registry.get_tool_schemas(context.session_type)
            if tools:
                logger.debug(f"Providing {len(tools)} tools to model")

        # Tool use loop
        max_iterations = 10  # Prevent infinite loops
        for iteration in range(max_iterations):
            logger.debug(f"Tool iteration {iteration + 1}/{max_iterations}")

            # Get kwargs from config
            kwargs: dict[str, Any] = {}
            if "max_tokens" in self.config:
                kwargs["max_tokens"] = self.config["max_tokens"]
            if "temperature" in self.config:
                kwargs["temperature"] = self.config["temperature"]

            # Call model API via adapter
            response = await self._adapter.chat(
                messages=messages,
                tools=tools if tools else None,
                **kwargs,
            )

            # Check if model requested tool use
            if response.tool_calls:
                logger.info(f"Model requested {len(response.tool_calls)} tool(s)")

                # Add assistant's response to conversation
                # Convert tool calls to provider format for message history
                assistant_content = self._build_assistant_content(response)
                messages.append({"role": "assistant", "content": assistant_content})

                # Execute tools and collect results
                tool_results = await self._execute_tools(response.tool_calls, context)

                # Add tool results to conversation
                messages.append(
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": r.tool_use_id,
                                "content": r.content,
                                "is_error": r.is_error,
                            }
                            for r in tool_results
                        ],
                    }
                )

                # Continue loop to get model's response with tool results

            elif response.stop_reason in ("end_turn", "stop", None):
                # Normal completion - extract text response
                assistant_message = response.text or ""

                # Save to context
                context.messages.append(ChatMessage(role="assistant", content=assistant_message))

                return assistant_message

            else:
                # Other stop reasons (max_tokens, etc.)
                logger.warning(f"Unexpected stop reason: {response.stop_reason}")
                assistant_message = response.text or ""
                context.messages.append(ChatMessage(role="assistant", content=assistant_message))
                return assistant_message

        # Max iterations reached
        logger.error(f"Max tool iterations ({max_iterations}) reached")
        return "Error: Maximum tool execution iterations reached. Please try a simpler request."

    def _build_assistant_content(self, response: Any) -> list[dict[str, Any]]:
        """Build assistant message content with text and tool use blocks.

        Args:
            response: Model response

        Returns:
            List of content blocks
        """
        content: list[dict[str, Any]] = []

        # Add text if present
        if response.text:
            content.append({"type": "text", "text": response.text})

        # Add tool use blocks
        for tc in response.tool_calls:
            content.append(
                {
                    "type": "tool_use",
                    "id": tc.id,
                    "name": tc.name,
                    "input": tc.arguments,
                }
            )

        return content

    async def _execute_tools(
        self,
        tool_calls: list[ToolCall],
        context: AgentContext,
    ) -> list[ToolResult]:
        """Execute requested tools and return results.

        Args:
            tool_calls: List of tool calls from model
            context: Agent context

        Returns:
            List of tool results
        """
        results: list[ToolResult] = []

        for tc in tool_calls:
            tool_name = tc.name
            tool_input = tc.arguments
            tool_id = tc.id

            logger.info(f"Executing tool: {tool_name}")

            # Get tool from registry
            tool = self.tool_registry.get(tool_name) if self.tool_registry else None
            if not tool:
                error_msg = f"Tool '{tool_name}' not found in registry"
                logger.error(error_msg)
                results.append(
                    ToolResult(
                        tool_use_id=tool_id,
                        content=f"Error: {error_msg}",
                        is_error=True,
                    )
                )
                continue

            # Check policy
            if self.tool_registry and not self.tool_registry.check_policy(
                tool, context.session_type
            ):
                error_msg = (
                    f"Tool '{tool_name}' not allowed for session type {context.session_type.value}"
                )
                logger.warning(error_msg)
                results.append(
                    ToolResult(
                        tool_use_id=tool_id,
                        content=f"Error: {error_msg}",
                        is_error=True,
                    )
                )
                continue

            # Check if approval required
            if tool.policy.requires_approval and self.approval_manager:
                approval_result = await self._handle_approval(
                    tool_name, tool_input, tool_id, context
                )
                if approval_result is not None:
                    results.append(approval_result)
                    continue

            # Execute tool
            try:
                result = await tool.execute(
                    tool_input,
                    context.workspace or ".",
                    context.session_type,
                )

                results.append(
                    ToolResult(
                        tool_use_id=tool_id,
                        content=result.output or result.error or "No output",
                        is_error=not result.success,
                    )
                )

                if result.success:
                    logger.info(f"Tool '{tool_name}' executed successfully")
                else:
                    logger.warning(f"Tool '{tool_name}' failed: {result.error}")

            except Exception as e:
                logger.exception(f"Tool execution error: {tool_name}")
                results.append(
                    ToolResult(
                        tool_use_id=tool_id,
                        content=f"Execution error: {e}",
                        is_error=True,
                    )
                )

        return results

    async def _handle_approval(
        self,
        tool_name: str,
        tool_input: dict[str, Any],
        tool_id: str,
        context: AgentContext,
    ) -> ToolResult | None:
        """Handle tool approval workflow.

        Args:
            tool_name: Name of the tool
            tool_input: Tool input parameters
            tool_id: Tool call ID
            context: Agent context

        Returns:
            ToolResult if approval failed/denied, None if approved
        """
        logger.info(f"Tool '{tool_name}' requires approval")

        # Create approval request
        command = tool_input.get("command") if tool_name == "bash" else None
        approval_request = ApprovalRequest(
            tool_name=tool_name,
            command=command,
            args=tool_input,
            session_key=context.session_id,
            agent_id=self.model,
            security_context=f"Session type: {context.session_type.value}",
            reason=f"Tool {tool_name} requires user approval",
        )

        # Send notification via channel
        if self.channel:
            try:
                # Create approval record
                record = self.approval_manager.create(approval_request)

                # Format notification message
                notification = self._format_approval_notification(record, approval_request)

                # Send to user
                await self.channel.send(
                    recipient_id=context.sender_id,
                    content=notification,
                )

                logger.info(f"Sent approval notification {record.id} to {context.sender_id}")

                # Wait for decision
                decision = await self.approval_manager.wait_for_decision(record)

                if decision == ApprovalDecision.APPROVE:
                    logger.info(f"Tool '{tool_name}' approved, executing")
                    return None  # Approval granted, continue with execution
                else:
                    # Denied or timeout
                    error_msg = f"Tool execution {'denied' if decision == ApprovalDecision.DENY else 'timed out'}"
                    logger.warning(f"Tool '{tool_name}' {error_msg}")
                    return ToolResult(
                        tool_use_id=tool_id,
                        content=f"Error: {error_msg}",
                        is_error=True,
                    )
            except Exception as e:
                logger.exception("Error in approval workflow")
                return ToolResult(
                    tool_use_id=tool_id,
                    content=f"Approval error: {e}",
                    is_error=True,
                )
        else:
            # No channel available - deny execution
            error_msg = "Tool requires approval but no channel available"
            logger.error(error_msg)
            return ToolResult(
                tool_use_id=tool_id,
                content=f"Error: {error_msg}",
                is_error=True,
            )

    def _prepare_messages(self, context: AgentContext) -> list[dict[str, Any]]:
        """Prepare messages for model API.

        Converts ChatMessage objects to the format expected by the API.
        """
        return [{"role": m.role, "content": m.content} for m in context.messages]

    def _format_approval_notification(self, record: Any, request: ApprovalRequest) -> str:
        """Format approval notification message.

        Args:
            record: Approval record with ID and expiry
            request: Approval request details

        Returns:
            Formatted notification message
        """
        lines = [
            "Tool Approval Required",
            "",
            f"Tool: {request.tool_name}",
        ]

        if request.command:
            lines.append(f"Command: {request.command}")

        lines.extend(
            [
                f"Session: {request.session_key}",
                f"Security: {request.security_context or 'Standard'}",
                "",
                f"Reply: /approve {record.id} or /deny {record.id}",
                "Expires in: 5 minutes",
            ]
        )

        return "\n".join(lines)

    async def stream_chat(self, context: AgentContext, message: str) -> AsyncIterator[str]:
        """Stream a chat response.

        Note: Streaming currently does not support tool use.
        """
        context.messages.append(ChatMessage(role="user", content=message))

        messages = [{"role": m.role, "content": m.content} for m in context.messages]

        kwargs: dict[str, Any] = {}
        if "max_tokens" in self.config:
            kwargs["max_tokens"] = self.config["max_tokens"]
        if "temperature" in self.config:
            kwargs["temperature"] = self.config["temperature"]

        full_response = ""
        async for chunk in self._adapter.stream_chat(messages=messages, **kwargs):
            if chunk.text:
                full_response += chunk.text
                yield chunk.text

        context.messages.append(ChatMessage(role="assistant", content=full_response))


class AgentRuntime:
    """Runtime for managing agent sessions.

    Supports optional session persistence using JSONL storage.
    Sessions are automatically loaded from disk on first access
    and saved after each message exchange.
    """

    def __init__(self, settings: Settings, channel: "Channel | None" = None) -> None:
        self.settings = settings
        self.channel = channel
        self.sessions: dict[str, AgentContext] = {}
        self.agents: dict[str, Agent] = {}

        # Initialize model registry
        self.model_registry = ModelRegistry(settings)
        logger.info("Initialized model registry")

        # Initialize tool registry
        self.tool_registry = ToolRegistry()
        self._register_builtin_tools()

        # Initialize approval manager
        self.approval_manager = ApprovalManager()
        logger.info("Initialized approval manager")

        # Initialize session store (if enabled)
        self.session_store: SessionStore | None = None
        if settings.storage.enabled:
            self.session_store = SessionStore(settings.sessions_dir)
            logger.info(f"Session persistence enabled: {settings.sessions_dir}")

    def _register_builtin_tools(self) -> None:
        """Register built-in tools."""
        self.tool_registry.register(BashTool())
        self.tool_registry.register(ReadFileTool())
        self.tool_registry.register(WriteFileTool())
        logger.info("Registered built-in tools")

    async def get_or_create_session(
        self,
        session_id: str,
        channel: str,
        sender_id: str,
        sender_name: str | None = None,
        session_type: SessionType = SessionType.MAIN,
    ) -> AgentContext:
        """Get or create an agent session.

        If persistence is enabled, loads existing session from disk.
        Creates a new session file if one doesn't exist.
        """
        if session_id not in self.sessions:
            # Create new context
            context = AgentContext(
                session_id=session_id,
                channel=channel,
                sender_id=sender_id,
                sender_name=sender_name,
                workspace=str(self.settings.agent.workspace),
                session_type=session_type,
            )

            # Load from storage if enabled
            if self.session_store:
                await self._load_session_from_store(context, channel, sender_id)

            self.sessions[session_id] = context
            logger.info(f"Created new session: {session_id} (type: {session_type.value})")

        return self.sessions[session_id]

    async def _load_session_from_store(
        self,
        context: AgentContext,
        channel: str,
        sender_id: str,
    ) -> None:
        """Load session history from storage.

        Args:
            context: Agent context to populate
            channel: Channel name
            sender_id: User ID
        """
        if not self.session_store:
            return

        try:
            # Get or create session in store
            await self.session_store.get_or_create_session(
                session_id=context.session_id,
                channel=channel,
                chat_id=context.session_id.split("_")[1]
                if "_" in context.session_id
                else context.session_id,
                user_id=sender_id,
                session_type=context.session_type.value,
            )

            # Load existing messages
            stored_messages = await self.session_store.load_messages(
                context.session_id,
                limit=self.settings.storage.max_messages,
            )

            # Convert to ChatMessage format
            for msg in stored_messages:
                context.messages.append(
                    ChatMessage(
                        role=msg.role,
                        content=msg.content,
                        name=msg.name,
                        tool_calls=msg.tool_calls,
                        tool_call_id=msg.tool_call_id,
                    )
                )

            if stored_messages:
                logger.info(
                    f"Loaded {len(stored_messages)} messages from session {context.session_id}"
                )

        except Exception as e:
            logger.exception(f"Error loading session {context.session_id}: {e}")

    async def _save_message_to_store(
        self,
        session_id: str,
        message: ChatMessage,
    ) -> None:
        """Save a message to storage.

        Args:
            session_id: Session identifier
            message: Message to save
        """
        if not self.session_store or not self.settings.storage.auto_save:
            return

        try:
            session_msg = SessionMessage(
                role=message.role,
                content=message.content,
                name=message.name,
                tool_calls=message.tool_calls,
                tool_call_id=message.tool_call_id,
            )
            await self.session_store.append_message(session_id, session_msg)
            logger.debug(f"Saved message to session {session_id}")

        except Exception as e:
            logger.exception(f"Error saving message to session {session_id}: {e}")

    def get_agent(self, model: str | None = None) -> Agent:
        """Get or create an agent for the specified model.

        Args:
            model: Model ID (e.g., "anthropic/claude-sonnet-4-20250514").
                   If None, uses default from settings.

        Returns:
            Agent instance for the model
        """
        model = model or self.settings.models.default_model

        if model not in self.agents:
            self.agents[model] = ModelAgent(
                model=model,
                model_registry=self.model_registry,
                tool_registry=self.tool_registry,
                approval_manager=self.approval_manager,
                channel=self.channel,
                max_tokens=self.settings.agent.max_tokens,
                temperature=self.settings.agent.temperature,
            )

        return self.agents[model]

    async def chat(
        self,
        session_id: str,
        channel: str,
        sender_id: str,
        message: str,
        sender_name: str | None = None,
        model: str | None = None,
    ) -> str:
        """Process a chat message.

        Automatically saves messages to storage if enabled.
        """
        context = await self.get_or_create_session(session_id, channel, sender_id, sender_name)

        # Save user message
        user_msg = ChatMessage(role="user", content=message)
        await self._save_message_to_store(session_id, user_msg)

        agent = self.get_agent(model)
        response = await agent.chat(context, message)

        # Save assistant response
        assistant_msg = ChatMessage(role="assistant", content=response)
        await self._save_message_to_store(session_id, assistant_msg)

        return response

    async def stream_chat(
        self,
        session_id: str,
        channel: str,
        sender_id: str,
        message: str,
        sender_name: str | None = None,
        model: str | None = None,
    ) -> AsyncIterator[str]:
        """Stream a chat response.

        Automatically saves messages to storage if enabled.
        """
        context = await self.get_or_create_session(session_id, channel, sender_id, sender_name)

        # Save user message
        user_msg = ChatMessage(role="user", content=message)
        await self._save_message_to_store(session_id, user_msg)

        agent = self.get_agent(model)
        full_response = ""

        async for chunk in agent.stream_chat(context, message):
            full_response += chunk
            yield chunk

        # Save assistant response after streaming completes
        assistant_msg = ChatMessage(role="assistant", content=full_response)
        await self._save_message_to_store(session_id, assistant_msg)

    async def clear_session(self, session_id: str) -> bool:
        """Clear a session's message history.

        Args:
            session_id: Session identifier

        Returns:
            True if session was cleared
        """
        # Clear in-memory
        if session_id in self.sessions:
            self.sessions[session_id].messages.clear()

        # Clear in storage
        if self.session_store:
            try:
                await self.session_store.clear_messages(session_id)
                logger.info(f"Cleared session: {session_id}")
                return True
            except FileNotFoundError:
                logger.warning(f"Session {session_id} not found in storage")
                return False

        return True

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session completely.

        Args:
            session_id: Session identifier

        Returns:
            True if session was deleted
        """
        # Remove from memory
        if session_id in self.sessions:
            del self.sessions[session_id]

        # Remove from storage
        if self.session_store:
            try:
                deleted = await self.session_store.delete_session(session_id)
                if deleted:
                    logger.info(f"Deleted session: {session_id}")
                return deleted
            except Exception as e:
                logger.exception(f"Error deleting session {session_id}: {e}")
                return False

        return True

    async def list_sessions(self) -> list[str]:
        """List all session IDs.

        Returns:
            List of session IDs from storage
        """
        if self.session_store:
            return await self.session_store.list_sessions()
        return list(self.sessions.keys())

    def list_models(self) -> list[str]:
        """List all available models.

        Returns:
            List of model IDs
        """
        return [m.id for m in self.model_registry.list_models()]
