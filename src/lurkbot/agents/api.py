"""FastAPI integration for LurkBot agent runtime.

This module provides HTTP/SSE endpoints for running agents,
using PydanticAI's AG-UI integration for streaming responses.
"""

from http import HTTPStatus
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.requests import Request
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, Field, ValidationError

from lurkbot.logging import get_logger
from lurkbot.utils import json_utils as json

from .runtime import (
    AgentDependencies,
    create_agent,
    resolve_model_id,
    run_embedded_agent,
    run_embedded_agent_events,
    run_embedded_agent_stream,
)
from .types import (
    AgentContext,
    AgentRunResult,
    PromptMode,
    SessionType,
    StreamEvent,
    ThinkLevel,
    VerboseLevel,
)

logger = get_logger("api")

# Content types
SSE_CONTENT_TYPE = "text/event-stream"
JSON_CONTENT_TYPE = "application/json"


class ChatRequest(BaseModel):
    """Request model for chat endpoint.

    This follows a simplified version of MoltBot's OpenResponses protocol.
    """

    # Required
    message: str = Field(..., description="The user message to process")

    # Session context
    session_id: str | None = Field(None, description="Session identifier")
    session_type: str = Field("main", description="Session type (main/group/dm/topic)")

    # Model configuration
    provider: str = Field("anthropic", description="AI provider")
    model: str = Field("claude-sonnet-4-20250514", description="Model ID")
    think_level: str = Field("medium", description="Thinking level (off/low/medium/high)")

    # Optional context
    system_prompt: str | None = Field(None, description="Custom system prompt override")
    extra_system_prompt: str | None = Field(None, description="Additional system prompt")
    message_history: list[dict[str, Any]] | None = Field(None, description="Previous messages")
    images: list[str] | None = Field(None, description="Image URLs or base64 data")

    # Streaming
    stream: bool = Field(False, description="Enable streaming response")

    # Workspace
    workspace_dir: str = Field(".", description="Workspace directory path")

    # Tenant context (for multi-tenant support)
    tenant_id: str | None = Field(None, description="Tenant identifier for multi-tenant mode")


class ChatResponse(BaseModel):
    """Response model for non-streaming chat endpoint."""

    session_id: str
    text: str
    messages: list[dict[str, Any]] = Field(default_factory=list)
    tool_metas: list[dict[str, Any]] = Field(default_factory=list)
    has_pending_approvals: bool = False
    error: str | None = None


def create_chat_api(
    default_system_prompt: str = "You are a helpful assistant.",
) -> FastAPI:
    """Create a FastAPI application for the chat API.

    This creates endpoints that follow MoltBot's OpenResponses pattern
    while using PydanticAI underneath.

    Args:
        default_system_prompt: Default system prompt if none provided

    Returns:
        Configured FastAPI application
    """
    app = FastAPI(
        title="LurkBot Agent API",
        description="HTTP/SSE API for LurkBot agent runtime",
        version="1.0.0",
    )

    @app.post("/chat", response_model=ChatResponse)
    async def chat_endpoint(request: ChatRequest) -> Response:
        """Process a chat message and return the agent response.

        Supports both streaming (SSE) and non-streaming (JSON) modes.
        """
        logger.info(f"Chat request: session={request.session_id}, stream={request.stream}")

        # Build agent context
        context = AgentContext(
            session_id=request.session_id or "default",
            session_type=SessionType(request.session_type),
            workspace_dir=request.workspace_dir,
            provider=request.provider,
            model_id=request.model,
            think_level=ThinkLevel(request.think_level),
            extra_system_prompt=request.extra_system_prompt,
            tenant_id=request.tenant_id,
        )

        # Determine system prompt
        system_prompt = request.system_prompt or default_system_prompt
        if request.extra_system_prompt:
            system_prompt = f"{system_prompt}\n\n{request.extra_system_prompt}"

        if request.stream:
            # Streaming SSE response
            return StreamingResponse(
                _stream_response(
                    context=context,
                    prompt=request.message,
                    system_prompt=system_prompt,
                    images=request.images,
                    message_history=request.message_history,
                ),
                media_type=SSE_CONTENT_TYPE,
            )
        else:
            # Non-streaming JSON response
            result = await run_embedded_agent(
                context=context,
                prompt=request.message,
                system_prompt=system_prompt,
                images=request.images,
                message_history=request.message_history,
            )

            return Response(
                content=ChatResponse(
                    session_id=result.session_id_used,
                    text=result.assistant_texts[0] if result.assistant_texts else "",
                    messages=result.messages_snapshot,
                    tool_metas=result.tool_metas,
                    has_pending_approvals=result.has_deferred_requests,
                    error=str(result.prompt_error) if result.prompt_error else None,
                ).model_dump_json(),
                media_type=JSON_CONTENT_TYPE,
            )

    @app.post("/chat/stream")
    async def chat_stream_endpoint(request: ChatRequest) -> StreamingResponse:
        """Process a chat message with detailed event streaming.

        Returns granular events including tool calls and results.
        """
        logger.info(f"Stream request: session={request.session_id}")

        context = AgentContext(
            session_id=request.session_id or "default",
            session_type=SessionType(request.session_type),
            workspace_dir=request.workspace_dir,
            provider=request.provider,
            model_id=request.model,
            think_level=ThinkLevel(request.think_level),
            extra_system_prompt=request.extra_system_prompt,
            tenant_id=request.tenant_id,
        )

        system_prompt = request.system_prompt or default_system_prompt
        if request.extra_system_prompt:
            system_prompt = f"{system_prompt}\n\n{request.extra_system_prompt}"

        return StreamingResponse(
            _stream_events(
                context=context,
                prompt=request.message,
                system_prompt=system_prompt,
                images=request.images,
                message_history=request.message_history,
            ),
            media_type=SSE_CONTENT_TYPE,
        )

    @app.get("/health")
    async def health_check() -> dict[str, str]:
        """Health check endpoint."""
        return {"status": "ok"}

    return app


async def _stream_response(
    context: AgentContext,
    prompt: str,
    system_prompt: str,
    images: list[str] | None = None,
    message_history: list[dict[str, Any]] | None = None,
) -> Any:
    """Generate SSE events for streaming response.

    Follows the pattern: data: {json}\n\n
    """
    try:
        async for event in run_embedded_agent_stream(
            context=context,
            prompt=prompt,
            system_prompt=system_prompt,
            images=images,
            message_history=message_history,
        ):
            yield _format_sse_event(event)

        # Send done marker
        yield "data: [DONE]\n\n"

    except Exception as e:
        logger.error(f"Streaming error: {e}")
        error_event = StreamEvent(
            event_type="agent_event",
            data={"type": "error", "message": str(e)},
        )
        yield _format_sse_event(error_event)
        yield "data: [DONE]\n\n"


async def _stream_events(
    context: AgentContext,
    prompt: str,
    system_prompt: str,
    images: list[str] | None = None,
    message_history: list[dict[str, Any]] | None = None,
) -> Any:
    """Generate detailed SSE events for event streaming.

    Provides granular events including tool calls and results.
    """
    try:
        async for event in run_embedded_agent_events(
            context=context,
            prompt=prompt,
            system_prompt=system_prompt,
            images=images,
            message_history=message_history,
        ):
            yield _format_sse_event(event)

        yield "data: [DONE]\n\n"

    except Exception as e:
        logger.error(f"Event streaming error: {e}")
        error_event = StreamEvent(
            event_type="agent_event",
            data={"type": "error", "message": str(e)},
        )
        yield _format_sse_event(error_event)
        yield "data: [DONE]\n\n"


def _format_sse_event(event: StreamEvent) -> str:
    """Format a StreamEvent as an SSE data line."""
    data = {
        "event": event.event_type,
        **event.data,
    }
    return f"data: {json.dumps(data)}\n\n"


# Convenience function to create and configure the app
def create_app() -> FastAPI:
    """Create the default LurkBot API application."""
    return create_chat_api()
