"""Agent runtime for managing agent sessions."""

from collections.abc import AsyncIterator
from typing import Any

from loguru import logger

from lurkbot.agents.base import Agent, AgentContext, ChatMessage
from lurkbot.config import Settings
from lurkbot.tools import SessionType, ToolRegistry
from lurkbot.tools.builtin.bash import BashTool
from lurkbot.tools.builtin.file_ops import ReadFileTool, WriteFileTool


class ClaudeAgent(Agent):
    """Agent using Anthropic's Claude API."""

    def __init__(
        self,
        model: str,
        api_key: str,
        tool_registry: ToolRegistry | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(model, **kwargs)
        self.api_key = api_key
        self.tool_registry = tool_registry
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
                tool_use_blocks = [
                    block for block in response.content if block.type == "tool_use"
                ]

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
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_id,
                            "content": f"Error: {error_msg}",
                            "is_error": True,
                        })
                        continue

                    # Check policy
                    if not self.tool_registry.check_policy(tool, context.session_type):
                        error_msg = f"Tool '{tool_name}' not allowed for session type {context.session_type.value}"
                        logger.warning(error_msg)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_id,
                            "content": f"Error: {error_msg}",
                            "is_error": True,
                        })
                        continue

                    # Execute tool
                    try:
                        result = await tool.execute(
                            tool_input,
                            context.workspace or ".",
                            context.session_type,
                        )

                        # Format tool result for API
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_id,
                            "content": result.output or result.error or "No output",
                            "is_error": not result.success,
                        })

                        if result.success:
                            logger.info(f"Tool '{tool_name}' executed successfully")
                        else:
                            logger.warning(f"Tool '{tool_name}' failed: {result.error}")

                    except Exception as e:
                        logger.exception(f"Tool execution error: {tool_name}")
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_id,
                            "content": f"Execution error: {e}",
                            "is_error": True,
                        })

                # Add tool results to conversation
                messages.append({"role": "user", "content": tool_results})

                # Continue loop to get Claude's response with tool results

            elif response.stop_reason == "end_turn":
                # Normal completion - extract text response
                text_blocks = [
                    block.text for block in response.content if hasattr(block, "text")
                ]
                assistant_message = "\n".join(text_blocks) if text_blocks else ""

                # Save to context
                context.messages.append(ChatMessage(role="assistant", content=assistant_message))

                return assistant_message

            else:
                # Other stop reasons (max_tokens, stop_sequence, etc.)
                logger.warning(f"Unexpected stop reason: {response.stop_reason}")
                text_blocks = [
                    block.text for block in response.content if hasattr(block, "text")
                ]
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
    """Runtime for managing agent sessions."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.sessions: dict[str, AgentContext] = {}
        self.agents: dict[str, Agent] = {}

        # Initialize tool registry
        self.tool_registry = ToolRegistry()
        self._register_builtin_tools()

    def _register_builtin_tools(self) -> None:
        """Register built-in tools."""
        self.tool_registry.register(BashTool())
        self.tool_registry.register(ReadFileTool())
        self.tool_registry.register(WriteFileTool())
        logger.info("Registered built-in tools")

    def get_or_create_session(
        self,
        session_id: str,
        channel: str,
        sender_id: str,
        sender_name: str | None = None,
        session_type: SessionType = SessionType.MAIN,
    ) -> AgentContext:
        """Get or create an agent session."""
        if session_id not in self.sessions:
            self.sessions[session_id] = AgentContext(
                session_id=session_id,
                channel=channel,
                sender_id=sender_id,
                sender_name=sender_name,
                workspace=str(self.settings.agent.workspace),
                session_type=session_type,
            )
            logger.info(f"Created new session: {session_id} (type: {session_type.value})")
        return self.sessions[session_id]

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
                    tool_registry=self.tool_registry,  # Pass tool registry
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
        """Process a chat message."""
        context = self.get_or_create_session(session_id, channel, sender_id, sender_name)
        agent = self.get_agent(model)
        return await agent.chat(context, message)

    async def stream_chat(
        self,
        session_id: str,
        channel: str,
        sender_id: str,
        message: str,
        sender_name: str | None = None,
        model: str | None = None,
    ) -> AsyncIterator[str]:
        """Stream a chat response."""
        context = self.get_or_create_session(session_id, channel, sender_id, sender_name)
        agent = self.get_agent(model)
        async for chunk in agent.stream_chat(context, message):
            yield chunk
