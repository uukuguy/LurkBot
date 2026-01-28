"""Agent runtime for managing agent sessions."""

from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Any

from loguru import logger

from lurkbot.agents.base import Agent, AgentContext, ChatMessage
from lurkbot.config import Settings
from lurkbot.storage.jsonl import SessionMessage, SessionStore
from lurkbot.tools import SessionType, ToolRegistry
from lurkbot.tools.approval import ApprovalDecision, ApprovalManager, ApprovalRequest
from lurkbot.tools.builtin.bash import BashTool
from lurkbot.tools.builtin.file_ops import ReadFileTool, WriteFileTool

if TYPE_CHECKING:
    from lurkbot.channels.base import Channel


class ClaudeAgent(Agent):
    """Agent using Anthropic's Claude API."""

    def __init__(
        self,
        model: str,
        api_key: str,
        tool_registry: ToolRegistry | None = None,
        approval_manager: ApprovalManager | None = None,
        channel: "Channel | None" = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(model, **kwargs)
        self.api_key = api_key
        self.tool_registry = tool_registry
        self.approval_manager = approval_manager
        self.channel = channel
        self._client: Any = None

    @property
    def client(self) -> Any:
        """Lazy-load the Anthropic client."""
        if self._client is None:
            import anthropic

            self._client = anthropic.AsyncAnthropic(api_key=self.api_key)
        return self._client

    async def chat(self, context: AgentContext, message: str) -> str:
        """Process a chat message using Claude with tool support.

        This method supports tool use through an iterative loop:
        1. Send message to Claude with available tools
        2. If Claude wants to use a tool, execute it
        3. Send tool result back and continue conversation
        4. Repeat until Claude provides a text response
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
                logger.debug(f"Providing {len(tools)} tools to Claude")

        # Tool use loop
        max_iterations = 10  # Prevent infinite loops
        for iteration in range(max_iterations):
            logger.debug(f"Tool iteration {iteration + 1}/{max_iterations}")

            # Call Claude API
            response = await self.client.messages.create(
                model=self.model.replace("anthropic/", ""),
                max_tokens=self.config.get("max_tokens", 4096),
                messages=messages,
                tools=tools if tools else None,
            )

            # Check stop reason
            if response.stop_reason == "tool_use":
                # Extract tool use blocks
                tool_use_blocks = [block for block in response.content if block.type == "tool_use"]

                if not tool_use_blocks:
                    logger.warning("Stop reason was tool_use but no tool_use blocks found")
                    break

                logger.info(f"Claude requested {len(tool_use_blocks)} tool(s)")

                # Add assistant's response (including tool_use) to conversation
                messages.append({"role": "assistant", "content": response.content})

                # Execute tools and collect results
                tool_results = []
                for tool_block in tool_use_blocks:
                    tool_name = tool_block.name
                    tool_input = tool_block.input
                    tool_id = tool_block.id

                    logger.info(f"Executing tool: {tool_name}")

                    # Get tool from registry
                    tool = self.tool_registry.get(tool_name) if self.tool_registry else None
                    if not tool:
                        error_msg = f"Tool '{tool_name}' not found in registry"
                        logger.error(error_msg)
                        tool_results.append(
                            {
                                "type": "tool_result",
                                "tool_use_id": tool_id,
                                "content": f"Error: {error_msg}",
                                "is_error": True,
                            }
                        )
                        continue

                    # Check policy
                    if not self.tool_registry.check_policy(tool, context.session_type):
                        error_msg = f"Tool '{tool_name}' not allowed for session type {context.session_type.value}"
                        logger.warning(error_msg)
                        tool_results.append(
                            {
                                "type": "tool_result",
                                "tool_use_id": tool_id,
                                "content": f"Error: {error_msg}",
                                "is_error": True,
                            }
                        )
                        continue

                    # Check if approval required
                    if tool.policy.requires_approval and self.approval_manager:
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
                                notification = self._format_approval_notification(
                                    record, approval_request
                                )

                                # Send to user (use sender_id from context)
                                await self.channel.send(
                                    recipient_id=context.sender_id,
                                    content=notification,
                                )

                                logger.info(
                                    f"Sent approval notification {record.id} to {context.sender_id}"
                                )

                                # Wait for decision
                                decision = await self.approval_manager.wait_for_decision(record)

                                if decision == ApprovalDecision.APPROVE:
                                    logger.info(f"Tool '{tool_name}' approved, executing")
                                else:
                                    # Denied or timeout
                                    error_msg = f"Tool execution {'denied' if decision == ApprovalDecision.DENY else 'timed out'}"
                                    logger.warning(f"Tool '{tool_name}' {error_msg}")
                                    tool_results.append(
                                        {
                                            "type": "tool_result",
                                            "tool_use_id": tool_id,
                                            "content": f"Error: {error_msg}",
                                            "is_error": True,
                                        }
                                    )
                                    continue
                            except Exception as e:
                                logger.exception("Error in approval workflow")
                                tool_results.append(
                                    {
                                        "type": "tool_result",
                                        "tool_use_id": tool_id,
                                        "content": f"Approval error: {e}",
                                        "is_error": True,
                                    }
                                )
                                continue
                        else:
                            # No channel available - deny execution
                            error_msg = "Tool requires approval but no channel available"
                            logger.error(error_msg)
                            tool_results.append(
                                {
                                    "type": "tool_result",
                                    "tool_use_id": tool_id,
                                    "content": f"Error: {error_msg}",
                                    "is_error": True,
                                }
                            )
                            continue

                    # Execute tool
                    try:
                        result = await tool.execute(
                            tool_input,
                            context.workspace or ".",
                            context.session_type,
                        )

                        # Format tool result for API
                        tool_results.append(
                            {
                                "type": "tool_result",
                                "tool_use_id": tool_id,
                                "content": result.output or result.error or "No output",
                                "is_error": not result.success,
                            }
                        )

                        if result.success:
                            logger.info(f"Tool '{tool_name}' executed successfully")
                        else:
                            logger.warning(f"Tool '{tool_name}' failed: {result.error}")

                    except Exception as e:
                        logger.exception(f"Tool execution error: {tool_name}")
                        tool_results.append(
                            {
                                "type": "tool_result",
                                "tool_use_id": tool_id,
                                "content": f"Execution error: {e}",
                                "is_error": True,
                            }
                        )

                # Add tool results to conversation
                messages.append({"role": "user", "content": tool_results})

                # Continue loop to get Claude's response with tool results

            elif response.stop_reason == "end_turn":
                # Normal completion - extract text response
                text_blocks = [block.text for block in response.content if hasattr(block, "text")]
                assistant_message = "\n".join(text_blocks) if text_blocks else ""

                # Save to context
                context.messages.append(ChatMessage(role="assistant", content=assistant_message))

                return assistant_message

            else:
                # Other stop reasons (max_tokens, stop_sequence, etc.)
                logger.warning(f"Unexpected stop reason: {response.stop_reason}")
                text_blocks = [block.text for block in response.content if hasattr(block, "text")]
                assistant_message = "\n".join(text_blocks) if text_blocks else ""
                context.messages.append(ChatMessage(role="assistant", content=assistant_message))
                return assistant_message

        # Max iterations reached
        logger.error(f"Max tool iterations ({max_iterations}) reached")
        return "Error: Maximum tool execution iterations reached. Please try a simpler request."

    def _prepare_messages(self, context: AgentContext) -> list[dict[str, Any]]:
        """Prepare messages for Claude API.

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
            "🔒 Tool Approval Required",
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
        """Stream a chat response using Claude."""
        context.messages.append(ChatMessage(role="user", content=message))

        messages = [{"role": m.role, "content": m.content} for m in context.messages]

        full_response = ""
        async with self.client.messages.stream(
            model=self.model.replace("anthropic/", ""),
            max_tokens=self.config.get("max_tokens", 4096),
            messages=messages,
        ) as stream:
            async for text in stream.text_stream:
                full_response += text
                yield text

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
        """Get or create an agent for the specified model."""
        model = model or self.settings.agent.model

        if model not in self.agents:
            if model.startswith("anthropic/"):
                if not self.settings.anthropic_api_key:
                    raise ValueError("ANTHROPIC_API_KEY not configured")
                self.agents[model] = ClaudeAgent(
                    model=model,
                    api_key=self.settings.anthropic_api_key,
                    tool_registry=self.tool_registry,
                    approval_manager=self.approval_manager,
                    channel=self.channel,
                    max_tokens=self.settings.agent.max_tokens,
                    temperature=self.settings.agent.temperature,
                )
            else:
                raise ValueError(f"Unsupported model: {model}")

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
