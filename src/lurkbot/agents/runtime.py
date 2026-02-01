"""Agent runtime implementation using PydanticAI.

This module provides the core agent execution functionality,
implementing MoltBot's runEmbeddedPiAgent equivalent using PydanticAI.
"""

import os
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
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from lurkbot.config.models import get_client_config, get_model
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
    relevant_contexts: list[dict[str, Any]] = []  # Retrieved historical contexts


# Model ID mapping from provider:model format for native PydanticAI providers
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

# Providers that use OpenAI-compatible API with custom endpoints
OPENAI_COMPATIBLE_PROVIDERS = {"deepseek", "qwen", "kimi", "glm"}


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
    provider: str,
    model_id: str,
    system_prompt: str,
    deps_type: type = AgentDependencies,
) -> Agent[AgentDependencies, str | DeferredToolRequests]:
    """Create a PydanticAI Agent instance.

    This is a factory function that creates an agent with the given
    configuration. Tools are registered separately after creation.

    For OpenAI-compatible providers (DeepSeek, Qwen, Kimi, GLM), this function
    creates an OpenAIChatModel with custom base_url. For native providers
    (Anthropic, OpenAI, Google), it uses the standard model string format.

    Args:
        provider: Provider name (e.g., "anthropic", "deepseek", "qwen")
        model_id: Model identifier (e.g., "claude-sonnet-4-20250514", "deepseek-chat")
        system_prompt: The system prompt to use
        deps_type: The dependencies type for the agent

    Returns:
        Configured PydanticAI Agent instance
    """
    provider_lower = provider.lower()

    # Check if this is an OpenAI-compatible provider that needs custom endpoint
    if provider_lower in OPENAI_COMPATIBLE_PROVIDERS:
        # Get model configuration
        model_config = get_model(provider_lower, model_id)
        if not model_config:
            logger.warning(
                f"Unknown model {provider_lower}:{model_id}, attempting with defaults"
            )
            # Fallback: use get_client_config which may raise if truly unknown
            config = get_client_config(provider_lower, model_id)
        else:
            config = {
                "base_url": model_config.base_url,
                "api_key_env": model_config.api_key_env,
                "model": model_config.model_id,
            }

        # Get API key from environment
        api_key = os.getenv(config["api_key_env"])
        if not api_key:
            raise ValueError(
                f"Missing API key: please set {config['api_key_env']} environment variable"
            )

        # Create OpenAI-compatible model
        openai_model = OpenAIChatModel(
            config["model"],
            provider=OpenAIProvider(
                base_url=config["base_url"],
                api_key=api_key,
            ),
        )

        agent: Agent[AgentDependencies, str | DeferredToolRequests] = Agent(
            openai_model,
            deps_type=deps_type,
            output_type=[str, DeferredToolRequests],
            system_prompt=system_prompt,
        )

        logger.info(
            f"Created agent with OpenAI-compatible provider: {provider_lower} "
            f"at {config['base_url']}"
        )

    else:
        # Use native PydanticAI provider format
        model_string = resolve_model_id(provider_lower, model_id)

        agent: Agent[AgentDependencies, str | DeferredToolRequests] = Agent(
            model_string,
            deps_type=deps_type,
            output_type=[str, DeferredToolRequests],
            system_prompt=system_prompt,
        )

        logger.info(f"Created agent with native provider: {model_string}")

    return agent


async def run_embedded_agent(
    context: AgentContext,
    prompt: str,
    system_prompt: str,
    images: list[str] | None = None,
    message_history: list[dict[str, Any]] | None = None,
    enable_context_aware: bool = True,  # Enable context-aware by default
    enable_proactive: bool = True,  # Enable proactive task identification by default
    enable_plugins: bool = True,  # Enable plugin execution by default
) -> AgentRunResult:
    """Run an embedded agent session with context-aware and proactive capabilities.

    This is the main entry point for running an agent, equivalent to
    MoltBot's runEmbeddedPiAgent function. Now with context-aware and
    proactive task identification capabilities.

    Args:
        context: The agent execution context
        prompt: The user prompt to process
        system_prompt: The generated system prompt
        images: Optional list of image URLs or base64 data
        message_history: Optional previous message history
        enable_context_aware: Enable context-aware retrieval (default: True)
        enable_proactive: Enable proactive task identification (default: True)
        enable_plugins: Enable plugin execution (default: True)

    Returns:
        AgentRunResult containing the execution results
    """
    result = AgentRunResult(session_id_used=context.session_id)

    # Step 0: Tenant validation and quota check (if tenant_id provided)
    quota_guard = None
    if context.tenant_id:
        try:
            from lurkbot.tenants.guards import get_quota_guard
            from lurkbot.tenants.quota import QuotaType

            quota_guard = get_quota_guard()

            # Check rate limit
            await quota_guard.check_rate_limit(context.tenant_id)

            # Acquire concurrent slot
            await quota_guard.acquire_concurrent_slot(context.tenant_id)

            logger.debug(f"Tenant quota check passed: {context.tenant_id}")

        except Exception as e:
            logger.error(f"Tenant quota check failed: {e}")
            result.prompt_error = e
            return result

    try:
        logger.info(f"Running agent with provider={context.provider} model={context.model_id}")

        # Step 0.5: Execute plugins (if enabled)
        plugin_results_text = ""
        if enable_plugins:
            try:
                from lurkbot.plugins import get_plugin_manager
                from lurkbot.plugins.models import PluginExecutionContext

                plugin_manager = get_plugin_manager()

                # Create plugin execution context
                plugin_context = PluginExecutionContext(
                    user_id=context.sender_id or context.session_id,
                    channel_id=context.channel_id,
                    session_id=context.session_id,
                    input_data={"query": prompt},
                    parameters={},
                    environment={},
                    config={},
                    metadata={"provider": context.provider, "model": context.model_id},
                )

                # Execute all enabled plugins
                plugin_results = await plugin_manager.execute_plugins(plugin_context)

                # Format plugin results for injection into system prompt
                if plugin_results:
                    successful_results = [
                        (name, result)
                        for name, result in plugin_results.items()
                        if result.success
                    ]

                    if successful_results:
                        plugin_results_text = "\n\n## Plugin Results\n\n"
                        plugin_results_text += (
                            "The following plugins have been executed to assist with your query:\n\n"
                        )

                        for name, result in successful_results:
                            plugin_results_text += f"### Plugin: {name}\n"
                            plugin_results_text += f"- Execution time: {result.execution_time:.2f}s\n"
                            plugin_results_text += f"- Result: {result.result}\n\n"

                        logger.info(
                            f"Executed {len(successful_results)} plugins successfully"
                        )

            except Exception as e:
                logger.warning(f"Plugin execution failed (continuing without plugins): {e}")

        # Inject plugin results into system prompt
        if plugin_results_text:
            system_prompt = system_prompt + plugin_results_text

        # Step 1: Load relevant contexts (if enabled)
        relevant_contexts = []
        if enable_context_aware:
            try:
                from .context.manager import get_context_manager

                # Use sender_id as user_id, fallback to session_id if not available
                user_id = context.sender_id or context.session_id

                context_manager = get_context_manager()
                retrieved = await context_manager.load_context_for_prompt(
                    prompt=prompt,
                    user_id=user_id,
                    session_id=context.session_id,
                    include_session_history=True,
                )

                # Format contexts and append to system prompt
                if retrieved:
                    context_text = context_manager.format_contexts_for_prompt(retrieved)
                    system_prompt = f"{system_prompt}\n\n## Relevant Context\n{context_text}"
                    logger.info(f"Loaded {len(retrieved)} contexts for context-aware mode")

                relevant_contexts = [rc.context.model_dump() for rc in retrieved]
            except Exception as e:
                logger.warning(f"Context-aware loading failed, continuing without: {e}")

        # Step 1.5: Proactive task identification (if enabled)
        if enable_proactive:
            try:
                from .proactive import InputAnalyzer, TaskSuggester

                # Analyze user input
                analyzer = InputAnalyzer(model=f"{context.provider}:{context.model_id}")
                analysis = await analyzer.analyze(
                    prompt=prompt,
                    context_history=message_history,
                )

                logger.debug(
                    f"Input analysis: intent={analysis.intent.value}, "
                    f"sentiment={analysis.sentiment.value}, "
                    f"confidence={analysis.confidence:.2f}"
                )

                # Check if we should generate suggestions
                if analyzer.should_trigger_proactive(analysis):
                    suggester = TaskSuggester(model=f"{context.provider}:{context.model_id}")

                    # Create context summary from relevant contexts
                    context_summary = None
                    if relevant_contexts:
                        # Simple summary: take last 2 contexts
                        recent = relevant_contexts[-2:]
                        context_summary = "\n".join(
                            [f"- {ctx.get('content', '')[:100]}" for ctx in recent]
                        )

                    suggestions = await suggester.suggest(
                        user_prompt=prompt,
                        analysis=analysis,
                        context_summary=context_summary,
                    )

                    if suggestions:
                        # Format and append suggestions to system prompt
                        suggestions_text = suggester.format_suggestions_for_prompt(suggestions)
                        system_prompt = f"{system_prompt}\n\n{suggestions_text}"
                        logger.info(f"Generated {len(suggestions)} proactive task suggestions")

            except Exception as e:
                logger.warning(f"Proactive task identification failed, continuing without: {e}")

        # Step 2: Create the agent (now supports both native and OpenAI-compatible providers)
        agent = create_agent(
            provider=context.provider,
            model_id=context.model_id,
            system_prompt=system_prompt,
        )

        # Step 3: Prepare dependencies
        deps = AgentDependencies(
            context=context,
            message_history=message_history or [],
            relevant_contexts=relevant_contexts,
        )

        # Step 4: Run the agent
        run_result = await agent.run(prompt, deps=deps)

        # Step 5: Check for deferred tool requests (human-in-the-loop)
        if isinstance(run_result.output, DeferredToolRequests):
            result.deferred_requests = run_result.output
            logger.info(f"Agent run has {len(run_result.output.approvals)} pending approvals")
        else:
            result.assistant_texts.append(run_result.output)

        # Capture message history
        result.messages_snapshot = [msg.model_dump() for msg in run_result.all_messages()]

        # Step 6: Save interaction (if context-aware enabled and not deferred)
        if enable_context_aware and not isinstance(run_result.output, DeferredToolRequests):
            try:
                from .context.manager import get_context_manager

                # Use sender_id as user_id, fallback to session_id if not available
                user_id = context.sender_id or context.session_id

                context_manager = get_context_manager()
                await context_manager.save_interaction(
                    session_id=context.session_id,
                    user_id=user_id,
                    user_message=prompt,
                    assistant_message=run_result.output,
                    tool_calls=None,  # TODO: Extract tool call info from messages
                )
                logger.debug("Saved interaction to context storage")
            except Exception as e:
                logger.warning(f"Failed to save interaction: {e}")

        # Step 7: Record token usage (if tenant_id provided)
        if context.tenant_id and quota_guard:
            try:
                # Extract token usage from run_result if available
                # PydanticAI provides usage info in the result
                input_tokens = 0
                output_tokens = 0

                # Try to get usage from the result
                if hasattr(run_result, "usage") and run_result.usage:
                    input_tokens = getattr(run_result.usage, "request_tokens", 0) or 0
                    output_tokens = getattr(run_result.usage, "response_tokens", 0) or 0

                if input_tokens > 0 or output_tokens > 0:
                    await quota_guard.record_token_usage(
                        context.tenant_id,
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                    )
            except Exception as e:
                logger.warning(f"Failed to record token usage: {e}")

    except TimeoutError:
        result.timed_out = True
        logger.error("Agent run timed out")
    except Exception as e:
        result.prompt_error = e
        logger.error(f"Agent run failed: {e}")
    finally:
        # Release concurrent slot (if tenant_id provided)
        if context.tenant_id and quota_guard:
            try:
                await quota_guard.release_concurrent_slot(context.tenant_id)
            except Exception as e:
                logger.warning(f"Failed to release concurrent slot: {e}")

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
    logger.info(
        f"Running streaming agent with provider={context.provider} model={context.model_id}"
    )

    # Create the agent
    agent = create_agent(
        provider=context.provider,
        model_id=context.model_id,
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
    logger.info(
        f"Running event-streaming agent with provider={context.provider} model={context.model_id}"
    )

    # Create the agent
    agent = create_agent(
        provider=context.provider,
        model_id=context.model_id,
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
