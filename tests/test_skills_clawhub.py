"""Tests for ClawHub integration."""

import pytest
from httpx import AsyncClient

from lurkbot.skills.clawhub import ClawHubClient, ClawHubSkill


@pytest.mark.asyncio
async def test_clawhub_client_initialization():
    """Test ClawHub client initialization."""
    client = ClawHubClient()
    assert client.api_url == "https://api.clawhub.ai/v1"
    await client.close()


@pytest.mark.asyncio
async def test_clawhub_context_manager():
    """Test ClawHub client as context manager."""
    async with ClawHubClient() as client:
        assert isinstance(client.client, AsyncClient)
    # Client should be closed after context exit


@pytest.mark.asyncio
async def test_clawhub_search_validation():
    """Test search parameter validation (does not call API)."""
    async with ClawHubClient() as client:
        # This test just validates the method signature
        # Actual API calls should be mocked in integration tests
        assert hasattr(client, "search")
        assert hasattr(client, "info")
        assert hasattr(client, "download")


@pytest.mark.asyncio
async def test_clawhub_skill_model():
    """Test ClawHub skill data model."""
    skill_data = {
        "slug": "openclaw/test-skill",
        "name": "Test Skill",
        "description": "A test skill",
        "version": "1.0.0",
        "author": "test-author",
        "tags": ["test", "example"],
        "downloads": 100,
        "rating": 4.5,
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
    }

    skill = ClawHubSkill(**skill_data)
    assert skill.slug == "openclaw/test-skill"
    assert skill.name == "Test Skill"
    assert skill.version == "1.0.0"
    assert len(skill.tags) == 2


# Note: Real API integration tests should be run separately with
# @pytest.mark.integration and mocked responses or live API calls
# These are just unit tests for the client structure
