"""HTTP REST API endpoints for LurkBot web interface.

Provides session management, model listing, and chat functionality
through a REST API.
"""

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from loguru import logger
from pydantic import BaseModel, Field

from lurkbot.agents.runtime import AgentRuntime

# ============================================================================
# Request/Response Models
# ============================================================================


class ChatRequest(BaseModel):
    """Request body for chat endpoint."""

    message: str = Field(..., min_length=1, description="User message to send")
    model: str | None = Field(None, description="Model ID (e.g., 'anthropic/claude-sonnet-4')")
    sender_name: str | None = Field(None, description="Optional sender display name")
    stream: bool = Field(False, description="Enable streaming response")


class ChatResponse(BaseModel):
    """Response from chat endpoint."""

    response: str = Field(..., description="AI assistant response")
    model: str = Field(..., description="Model used for response")
    session_id: str = Field(..., description="Session ID")


class SessionInfo(BaseModel):
    """Session information."""

    session_id: str
    channel: str
    sender_id: str
    sender_name: str | None = None
    message_count: int
    session_type: str
    created_at: datetime | None = None


class SessionListResponse(BaseModel):
    """Response for session list endpoint."""

    sessions: list[SessionInfo]
    total: int


class SessionDetailResponse(BaseModel):
    """Detailed session response with messages."""

    session_id: str
    channel: str
    sender_id: str
    sender_name: str | None = None
    message_count: int
    session_type: str
    messages: list[dict[str, Any]]


class ModelInfo(BaseModel):
    """Model information."""

    id: str
    name: str
    provider: str
    api_type: str
    context_window: int
    max_tokens: int
    capabilities: dict[str, bool]


class ModelListResponse(BaseModel):
    """Response for model list endpoint."""

    models: list[ModelInfo]
    default_model: str


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    timestamp: datetime
    version: str = "0.1.0"


class ApprovalAction(BaseModel):
    """Approval action request."""

    action: str = Field(..., pattern="^(approve|deny)$")


# ============================================================================
# API Router Factory
# ============================================================================


def create_api_router(runtime: AgentRuntime, channel: str = "web") -> APIRouter:
    """Create API router with access to agent runtime.

    Args:
        runtime: Agent runtime instance
        channel: Default channel name for web sessions

    Returns:
        Configured API router
    """
    router = APIRouter(prefix="/api", tags=["api"])

    # ========================================================================
    # Health & Status
    # ========================================================================

    @router.get("/health", response_model=HealthResponse)
    async def health_check() -> HealthResponse:
        """Health check endpoint."""
        return HealthResponse(
            status="ok",
            timestamp=datetime.now(UTC),
        )

    # ========================================================================
    # Sessions
    # ========================================================================

    @router.get("/sessions", response_model=SessionListResponse)
    async def list_sessions() -> SessionListResponse:
        """List all sessions."""
        session_ids = await runtime.list_sessions()
        sessions: list[SessionInfo] = []

        for session_id in session_ids:
            # Get session from memory or storage
            if session_id in runtime.sessions:
                ctx = runtime.sessions[session_id]
                sessions.append(
                    SessionInfo(
                        session_id=session_id,
                        channel=ctx.channel,
                        sender_id=ctx.sender_id,
                        sender_name=ctx.sender_name,
                        message_count=len(ctx.messages),
                        session_type=ctx.session_type.value,
                    )
                )
            elif runtime.session_store:
                # Load metadata from storage
                try:
                    count = await runtime.session_store.get_message_count(session_id)
                    sessions.append(
                        SessionInfo(
                            session_id=session_id,
                            channel="unknown",
                            sender_id="unknown",
                            message_count=count,
                            session_type="main",
                        )
                    )
                except Exception:
                    logger.warning(f"Failed to load session info for {session_id}")

        return SessionListResponse(sessions=sessions, total=len(sessions))

    @router.get("/sessions/{session_id}", response_model=SessionDetailResponse)
    async def get_session(session_id: str) -> SessionDetailResponse:
        """Get session details including messages."""
        # Check if session exists
        if session_id not in runtime.sessions:
            # Try to load from storage
            session_ids = await runtime.list_sessions()
            if session_id not in session_ids:
                raise HTTPException(status_code=404, detail="Session not found")

            # Load the session
            await runtime.get_or_create_session(
                session_id=session_id,
                channel=channel,
                sender_id="web",
            )

        ctx = runtime.sessions[session_id]

        # Convert messages to dict format
        messages = [
            {
                "role": m.role,
                "content": m.content,
                "name": m.name,
            }
            for m in ctx.messages
        ]

        return SessionDetailResponse(
            session_id=session_id,
            channel=ctx.channel,
            sender_id=ctx.sender_id,
            sender_name=ctx.sender_name,
            message_count=len(ctx.messages),
            session_type=ctx.session_type.value,
            messages=messages,
        )

    @router.delete("/sessions/{session_id}")
    async def delete_session(session_id: str) -> dict[str, str]:
        """Delete a session."""
        deleted = await runtime.delete_session(session_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Session not found")
        return {"status": "deleted", "session_id": session_id}

    @router.post("/sessions/{session_id}/clear")
    async def clear_session(session_id: str) -> dict[str, str]:
        """Clear session message history."""
        cleared = await runtime.clear_session(session_id)
        if not cleared:
            raise HTTPException(status_code=404, detail="Session not found")
        return {"status": "cleared", "session_id": session_id}

    # ========================================================================
    # Chat
    # ========================================================================

    @router.post("/sessions/{session_id}/chat", response_model=ChatResponse)
    async def chat(session_id: str, request: ChatRequest) -> ChatResponse | StreamingResponse:
        """Send a chat message to a session.

        If stream=True, returns Server-Sent Events stream.
        """
        if request.stream:
            return StreamingResponse(
                _stream_chat(runtime, session_id, channel, request),
                media_type="text/event-stream",
            )

        model = request.model or runtime.settings.models.default_model

        try:
            response = await runtime.chat(
                session_id=session_id,
                channel=channel,
                sender_id="web",
                message=request.message,
                sender_name=request.sender_name,
                model=model,
            )

            return ChatResponse(
                response=response,
                model=model,
                session_id=session_id,
            )

        except Exception as e:
            logger.exception(f"Chat error: {e}")
            raise HTTPException(status_code=500, detail=str(e)) from e

    # ========================================================================
    # Models
    # ========================================================================

    @router.get("/models", response_model=ModelListResponse)
    async def list_models() -> ModelListResponse:
        """List all available models."""
        models_data = runtime.model_registry.list_models()
        models: list[ModelInfo] = []

        for config in models_data:
            models.append(
                ModelInfo(
                    id=config.id,
                    name=config.name,
                    provider=config.provider,
                    api_type=config.api_type.value,
                    context_window=config.context_window,
                    max_tokens=config.max_tokens,
                    capabilities={
                        "tools": config.capabilities.supports_tools,
                        "vision": config.capabilities.supports_vision,
                        "streaming": config.capabilities.supports_streaming,
                        "thinking": config.capabilities.supports_thinking,
                    },
                )
            )

        return ModelListResponse(
            models=models,
            default_model=runtime.settings.models.default_model,
        )

    @router.get("/models/{model_id}")
    async def get_model(model_id: str) -> ModelInfo:
        """Get details for a specific model."""
        # model_id comes with '/' replaced by '-' in path
        actual_id = model_id.replace("-", "/", 1)  # Only replace first dash

        try:
            config = runtime.model_registry.get_config(actual_id)
        except KeyError as e:
            raise HTTPException(status_code=404, detail=f"Model not found: {actual_id}") from e

        return ModelInfo(
            id=config.id,
            name=config.name,
            provider=config.provider,
            api_type=config.api_type.value,
            context_window=config.context_window,
            max_tokens=config.max_tokens,
            capabilities={
                "tools": config.capabilities.supports_tools,
                "vision": config.capabilities.supports_vision,
                "streaming": config.capabilities.supports_streaming,
                "thinking": config.capabilities.supports_thinking,
            },
        )

    # ========================================================================
    # Approvals (for pending tool approvals)
    # ========================================================================

    @router.get("/approvals")
    async def list_pending_approvals() -> dict[str, Any]:
        """List all pending approval requests."""
        pending = runtime.approval_manager.get_all_pending()
        approvals = []

        for record in pending:
            approvals.append(
                {
                    "id": record.id,
                    "tool_name": record.request.tool_name,
                    "command": record.request.command,
                    "session_key": record.request.session_key,
                    "created_at": record.created_at.isoformat(),
                    "expires_at": record.expires_at.isoformat() if record.expires_at else None,
                }
            )

        return {"approvals": approvals, "total": len(approvals)}

    @router.post("/approvals/{approval_id}")
    async def resolve_approval(approval_id: str, request: ApprovalAction) -> dict[str, str]:
        """Approve or deny a pending tool execution.

        Args:
            approval_id: The approval request ID
            request: Action to take (approve/deny)
        """
        from lurkbot.tools.approval import ApprovalDecision

        decision = (
            ApprovalDecision.APPROVE if request.action == "approve" else ApprovalDecision.DENY
        )

        resolved = runtime.approval_manager.resolve(approval_id, decision, "web-user")
        if not resolved:
            raise HTTPException(status_code=404, detail=f"Approval not found: {approval_id}")

        return {"status": request.action, "approval_id": approval_id}

    return router


# ============================================================================
# Streaming Helper
# ============================================================================


async def _stream_chat(
    runtime: AgentRuntime,
    session_id: str,
    channel: str,
    request: ChatRequest,
) -> Any:
    """Generate Server-Sent Events for streaming chat response.

    Args:
        runtime: Agent runtime
        session_id: Session ID
        channel: Channel name
        request: Chat request

    Yields:
        SSE formatted events
    """
    import json

    model = request.model or runtime.settings.models.default_model

    try:
        # Send start event
        yield f"data: {json.dumps({'event': 'start', 'model': model})}\n\n"

        # Stream response chunks
        async for chunk in runtime.stream_chat(
            session_id=session_id,
            channel=channel,
            sender_id="web",
            message=request.message,
            sender_name=request.sender_name,
            model=model,
        ):
            yield f"data: {json.dumps({'event': 'chunk', 'content': chunk})}\n\n"

        # Send end event
        yield f"data: {json.dumps({'event': 'end'})}\n\n"

    except Exception as e:
        logger.exception(f"Stream error: {e}")
        yield f"data: {json.dumps({'event': 'error', 'message': str(e)})}\n\n"
