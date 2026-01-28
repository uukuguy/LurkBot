"""Agent runtime implementation using PydanticAI.

This module provides the core agent execution functionality,
implementing MoltBot's runEmbeddedPiAgent equivalent using PydanticAI.
"""

from typing import Any, AsyncIterator

from pydantic import BaseModel, ConfigDict
from pydantic_ai import Agent, DeferredToolRequests, RunContext
from pydantic_ai.messages import (
    FinalResultEvent,
    FunctionToolCallEvent,
    FunctionToolResultEvent,
    PartDeltaEvent,
    PartStartEvent,
    TextPartDelta,
)

from lurkbot.logging import get_logger

from .types import (
    AgentContext,
    AgentRunResult,
    PromptMode,
    StreamEvent,
    ThinkLevel,
)

logger = get_logger("agent")


class AgentDependencies(BaseModel):
    """Dependencies injected into the agent at runtime.

    This is the PydanticAI deps_type that provides context
    to tools and system prompts.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    context: AgentContext
    message_history: list[dict[str, Any]] = []


# Model ID mapping from provider:model format
MODEL_MAPPING = {
    "anthropic": {
        "claude-sonnet-4-20250514": "anthropic:claude-sonnet-4-20250514",
        "claude-opus-4-5-20251101": "anthropic:claude-opus-4-5-20251101",
        "claude-3-5-sonnet-20241022": "anthropic:claude-3-5-sonnet-20241022",
        "claude-3-5-haiku-20241022": "anthropic:claude-3-5-haiku-20241022",
    },
    "openai": {
        "gpt-4o": "openai:gpt-4o",
        "gpt-4o-mini": "openai:gpt-4o-mini",
        "gpt-4-turbo": "openai:gpt-4-turbo",
    },
    "google": {
        "gemini-2.0-flash": "google-gla:gemini-2.0-flash",
        "gemini-1.5-pro": "google-gla:gemini-1.5-pro",
        "gemini-1.5-flash": "google-gla:gemini-1.5-flash",
    },
}


def resolve_model_id(provider: str, model_id: str) -> str:
    """Resolve a provider/model ID to PydanticAI format.

    Args:
        provider: Provider name (anthropic, openai, google, etc.)
        model_id: Model identifier

    Returns:
        PydanticAI-compatible model string
    """
    provider_lower = provider.lower()

    # Check if already in pydantic-ai format
    if ":" in model_id:
        return model_id

    # Look up in mapping
    if provider_lower in MODEL_MAPPING:
        if model_id in MODEL_MAPPING[provider_lower]:
            return MODEL_MAPPING[provider_lower][model_id]

    # Default format
    return f"{provider_lower}:{model_id}"


def create_agent(
    model: str,
    system_prompt: str,
    deps_type: type = AgentDependencies,
) -> Agent[AgentDependencies, str | DeferredToolRequests]:
    """Create a PydanticAI Agent instance.

    This is a factory function that creates an agent with the given
    configuration. Tools are registered separately after creation.

    Args:
        model: PydanticAI model string (e.g., "anthropic:claude-sonnet-4-20250514")
        system_prompt: The system prompt to use
        deps_type: The dependencies type for the agent

    Returns:
        Configured PydanticAI Agent instance
    """
    agent: Agent[AgentDependencies, str | DeferredToolRequests] = Agent(
        model,
        deps_type=deps_type,
        output_type=[str, DeferredToolRequests],
        system_prompt=system_prompt,
    )

    return agent


async def run_embedded_agent(
    context: AgentContext,
    prompt: str,
    system_prompt: str,
    images: list[str] | None = None,
    message_history: list[dict[str, Any]] | None = None,
) -> AgentRunResult:
    """Run an embedded agent session.

    This is the main entry point for running an agent, equivalent to
    MoltBot's runEmbeddedPiAgent function.

    Args:
        context: The agent execution context
        prompt: The user prompt to process
        system_prompt: The generated system prompt
        images: Optional list of image URLs or base64 data
        message_history: Optional previous message history

    Returns:
        AgentRunResult containing the execution results
    """
    result = AgentRunResult(session_id_used=context.session_id)

    try:
        # Resolve the model ID
        model_id = resolve_model_id(context.provider, context.model_id)
        logger.info(f"Running agent with model: {model_id}")

        # Create the agent
        agent = create_agent(
            model=model_id,
            system_prompt=system_prompt,
        )

        # Prepare dependencies
        deps = AgentDependencies(
            context=context,
            message_history=message_history or [],
        )

        # Run the agent
        run_result = await agent.run(prompt, deps=deps)

        # Check for deferred tool requests (human-in-the-loop)
        if isinstance(run_result.output, DeferredToolRequests):
            result.deferred_requests = run_result.output
            logger.info(f"Agent run has {len(run_result.output.approvals)} pending approvals")
        else:
            result.assistant_texts.append(run_result.output)

        # Capture message history
        result.messages_snapshot = [msg.model_dump() for msg in run_result.all_messages()]

    except TimeoutError:
        result.timed_out = True
        logger.error("Agent run timed out")
    except Exception as e:
        result.prompt_error = e
        logger.error(f"Agent run failed: {e}")

    return result


async def run_embedded_agent_stream(
    context: AgentContext,
    prompt: str,
    system_prompt: str,
    images: list[str] | None = None,
    message_history: list[dict[str, Any]] | None = None,
) -> AsyncIterator[StreamEvent]:
    """Run an embedded agent session with streaming output.

    This provides real-time streaming of agent output, useful for
    interactive UIs and long-running operations.

    Args:
        context: The agent execution context
        prompt: The user prompt to process
        system_prompt: The generated system prompt
        images: Optional list of image URLs or base64 data
        message_history: Optional previous message history

    Yields:
        StreamEvent objects for real-time updates
    """
    # Resolve the model ID
    model_id = resolve_model_id(context.provider, context.model_id)
    logger.info(f"Running streaming agent with model: {model_id}")

    # Create the agent
    agent = create_agent(
        model=model_id,
        system_prompt=system_prompt,
    )

    # Prepare dependencies
    deps = AgentDependencies(
        context=context,
        message_history=message_history or [],
    )

    # Stream the agent run
    async with agent.run_stream(prompt, deps=deps) as run:
        # Emit start event
        yield StreamEvent(event_type="assistant_start", data={})

        # Stream text output
        async for text in run.stream_text():
            yield StreamEvent(
                event_type="partial_reply",
                data={"text": text},
            )


async def run_embedded_agent_events(
    context: AgentContext,
    prompt: str,
    system_prompt: str,
    images: list[str] | None = None,
    message_history: list[dict[str, Any]] | None = None,
) -> AsyncIterator[StreamEvent]:
    """Run an embedded agent session with detailed event streaming.

    This provides granular events including tool calls and results,
    useful for debugging and detailed progress tracking.

    Args:
        context: The agent execution context
        prompt: The user prompt to process
        system_prompt: The generated system prompt
        images: Optional list of image URLs or base64 data
        message_history: Optional previous message history

    Yields:
        StreamEvent objects for each agent event
    """
    # Resolve the model ID
    model_id = resolve_model_id(context.provider, context.model_id)
    logger.info(f"Running event-streaming agent with model: {model_id}")

    # Create the agent
    agent = create_agent(
        model=model_id,
        system_prompt=system_prompt,
    )

    # Prepare dependencies
    deps = AgentDependencies(
        context=context,
        message_history=message_history or [],
    )

    # Use the new iter() API for detailed events
    async with agent.iter(prompt, deps=deps) as run:
        async for node in run:
            if Agent.is_user_prompt_node(node):
                yield StreamEvent(
                    event_type="agent_event",
                    data={"type": "user_prompt", "prompt": node.user_prompt},
                )
            elif Agent.is_model_request_node(node):
                async with node.stream(run.ctx) as request_stream:
                    async for event in request_stream:
                        if isinstance(event, PartStartEvent):
                            yield StreamEvent(
                                event_type="agent_event",
                                data={"type": "part_start", "index": event.index},
                            )
                        elif isinstance(event, PartDeltaEvent):
                            if isinstance(event.delta, TextPartDelta):
                                yield StreamEvent(
                                    event_type="partial_reply",
                                    data={"text": event.delta.content_delta},
                                )
                        elif isinstance(event, FinalResultEvent):
                            yield StreamEvent(
                                event_type="agent_event",
                                data={"type": "final_result", "tool_name": event.tool_name},
                            )
            elif Agent.is_call_tools_node(node):
                async with node.stream(run.ctx) as handle_stream:
                    async for event in handle_stream:
                        if isinstance(event, FunctionToolCallEvent):
                            yield StreamEvent(
                                event_type="tool_result",
                                data={
                                    "type": "tool_call",
                                    "tool_name": event.part.tool_name,
                                    "args": event.part.args,
                                    "tool_call_id": event.part.tool_call_id,
                                },
                            )
                        elif isinstance(event, FunctionToolResultEvent):
                            yield StreamEvent(
                                event_type="tool_result",
                                data={
                                    "type": "tool_result",
                                    "content": str(event.result.content)[:500],  # Truncate
                                },
                            )
