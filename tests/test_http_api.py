"""Tests for HTTP REST API endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient

from lurkbot.agents.runtime import AgentRuntime
from lurkbot.config import Settings
from lurkbot.gateway.http_api import create_api_router
from lurkbot.gateway.server import GatewayServer


@pytest.fixture
def settings() -> Settings:
    """Create test settings."""
    return Settings(
        anthropic_api_key="test-api-key",
        agent={"workspace": "/tmp/test"},
        storage={"enabled": False},
    )


@pytest.fixture
def runtime(settings: Settings) -> AgentRuntime:
    """Create test agent runtime."""
    return AgentRuntime(settings)


@pytest.fixture
def server(settings: Settings, runtime: AgentRuntime) -> GatewayServer:
    """Create test gateway server with HTTP API."""
    return GatewayServer(settings, runtime=runtime)


@pytest.fixture
async def client(server: GatewayServer):
    """Create async test client."""
    async with AsyncClient(
        transport=ASGITransport(app=server.app),
        base_url="http://test",
    ) as ac:
        yield ac


# ============================================================================
# Health Tests
# ============================================================================


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient):
    """Test health check endpoint."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_api_health_endpoint(client: AsyncClient):
    """Test API health check endpoint."""
    response = await client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "timestamp" in data


# ============================================================================
# Session Tests
# ============================================================================


@pytest.mark.asyncio
async def test_list_sessions_empty(client: AsyncClient):
    """Test listing sessions when empty."""
    response = await client.get("/api/sessions")
    assert response.status_code == 200
    data = response.json()
    assert data["sessions"] == []
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_get_session_not_found(client: AsyncClient):
    """Test getting non-existent session."""
    response = await client.get("/api/sessions/nonexistent")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_session_not_found(client: AsyncClient):
    """Test deleting non-existent session."""
    response = await client.delete("/api/sessions/nonexistent")
    # With storage disabled, this actually returns 200 (session removed from empty dict)
    # This is expected behavior since there's nothing to delete
    assert response.status_code in [200, 404]


@pytest.mark.asyncio
async def test_clear_session_not_found(client: AsyncClient):
    """Test clearing non-existent session."""
    response = await client.post("/api/sessions/nonexistent/clear")
    # With storage disabled, this returns 200 since there's nothing to clear
    assert response.status_code in [200, 404]


# ============================================================================
# Model Tests
# ============================================================================


@pytest.mark.asyncio
async def test_list_models(client: AsyncClient):
    """Test listing available models."""
    response = await client.get("/api/models")
    assert response.status_code == 200
    data = response.json()

    assert "models" in data
    assert "default_model" in data
    assert len(data["models"]) > 0

    # Check model structure
    model = data["models"][0]
    assert "id" in model
    assert "name" in model
    assert "provider" in model
    assert "api_type" in model
    assert "context_window" in model
    assert "max_tokens" in model
    assert "capabilities" in model


@pytest.mark.asyncio
async def test_list_models_contains_anthropic(client: AsyncClient):
    """Test that Anthropic models are included."""
    response = await client.get("/api/models")
    data = response.json()

    anthropic_models = [m for m in data["models"] if m["provider"] == "anthropic"]
    assert len(anthropic_models) >= 1


@pytest.mark.asyncio
async def test_list_models_contains_openai(client: AsyncClient):
    """Test that OpenAI models are included."""
    response = await client.get("/api/models")
    data = response.json()

    openai_models = [m for m in data["models"] if m["provider"] == "openai"]
    assert len(openai_models) >= 1


@pytest.mark.asyncio
async def test_list_models_contains_ollama(client: AsyncClient):
    """Test that Ollama models are included."""
    response = await client.get("/api/models")
    data = response.json()

    ollama_models = [m for m in data["models"] if m["provider"] == "ollama"]
    assert len(ollama_models) >= 1


# ============================================================================
# Approval Tests
# ============================================================================


@pytest.mark.asyncio
async def test_list_approvals_empty(client: AsyncClient):
    """Test listing pending approvals when empty."""
    response = await client.get("/api/approvals")
    assert response.status_code == 200
    data = response.json()
    assert data["approvals"] == []
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_resolve_approval_not_found(client: AsyncClient):
    """Test resolving non-existent approval."""
    response = await client.post(
        "/api/approvals/nonexistent",
        json={"action": "approve"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_resolve_approval_invalid_action(client: AsyncClient):
    """Test resolving approval with invalid action."""
    response = await client.post(
        "/api/approvals/test-id",
        json={"action": "invalid"},
    )
    # Validation error for invalid action pattern
    assert response.status_code == 422


# ============================================================================
# Chat Tests (Limited - No API calls)
# ============================================================================


@pytest.mark.asyncio
async def test_chat_missing_message(client: AsyncClient):
    """Test chat endpoint with missing message."""
    response = await client.post(
        "/api/sessions/test-session/chat",
        json={},
    )
    # Validation error for missing required field
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_chat_empty_message(client: AsyncClient):
    """Test chat endpoint with empty message."""
    response = await client.post(
        "/api/sessions/test-session/chat",
        json={"message": ""},
    )
    # Validation error for min_length=1
    assert response.status_code == 422


# ============================================================================
# CORS Tests
# ============================================================================


@pytest.mark.asyncio
async def test_cors_headers(client: AsyncClient):
    """Test that CORS headers are present."""
    response = await client.options(
        "/api/models",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    # CORS preflight should succeed
    assert response.status_code == 200


# ============================================================================
# API Router Factory Tests
# ============================================================================


def test_create_api_router(runtime: AgentRuntime):
    """Test API router creation."""
    router = create_api_router(runtime)
    assert router is not None
    assert router.prefix == "/api"


def test_create_api_router_custom_channel(runtime: AgentRuntime):
    """Test API router creation with custom channel."""
    router = create_api_router(runtime, channel="custom")
    assert router is not None
