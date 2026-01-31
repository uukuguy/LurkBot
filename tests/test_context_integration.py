"""Integration tests for context-aware system."""

import tempfile
import time

import pytest

from lurkbot.agents.context.manager import ContextManager


@pytest.fixture
def temp_storage_dir():
    """Create a temporary directory for ChromaDB."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def manager(temp_storage_dir):
    """Create a ContextManager instance."""
    return ContextManager(
        persist_directory=temp_storage_dir,
        enable_auto_save=True,
        max_context_length=5,
    )


@pytest.mark.asyncio
async def test_save_and_load_interaction(manager):
    """Test saving an interaction and loading it back."""
    # Save interaction
    await manager.save_interaction(
        session_id="session_1",
        user_id="user_1",
        user_message="What is Python?",
        assistant_message="Python is a high-level programming language.",
    )

    # Load context
    contexts = await manager.load_context_for_prompt(
        prompt="Tell me more about Python",
        user_id="user_1",
        session_id="session_1",
    )

    assert len(contexts) > 0
    # Should find the previous interaction
    assert any("Python" in ctx.context.text for ctx in contexts)


@pytest.mark.asyncio
async def test_cross_session_context_retrieval(manager):
    """Test retrieving contexts across different sessions."""
    # Save interactions in different sessions
    await manager.save_interaction(
        session_id="session_1",
        user_id="user_1",
        user_message="I'm learning machine learning",
        assistant_message="Great! Machine learning is fascinating.",
    )

    await manager.save_interaction(
        session_id="session_2",
        user_id="user_1",
        user_message="What about deep learning?",
        assistant_message="Deep learning is a subset of machine learning.",
    )

    # Query from a new session should find contexts from both previous sessions
    contexts = await manager.load_context_for_prompt(
        prompt="Tell me about neural networks",
        user_id="user_1",
        session_id="session_3",
    )

    # Should find relevant contexts
    assert len(contexts) > 0


@pytest.mark.asyncio
async def test_format_contexts_for_prompt(manager):
    """Test formatting contexts for system prompt."""
    # Create some sample contexts
    await manager.save_interaction(
        session_id="session_1",
        user_id="user_1",
        user_message="Hello",
        assistant_message="Hi there!",
    )

    contexts = await manager.load_context_for_prompt(
        prompt="How are you?",
        user_id="user_1",
        session_id="session_1",
    )

    formatted = manager.format_contexts_for_prompt(contexts)

    # Should contain headers and content
    assert "conversation history" in formatted.lower()
    if contexts:
        assert "User" in formatted or "Assistant" in formatted


@pytest.mark.asyncio
async def test_max_context_length_limit(manager):
    """Test that max_context_length is respected."""
    # Save many interactions
    for i in range(10):
        await manager.save_interaction(
            session_id="session_1",
            user_id="user_1",
            user_message=f"Message {i}",
            assistant_message=f"Response {i}",
        )

    contexts = await manager.load_context_for_prompt(
        prompt="test query",
        user_id="user_1",
        session_id="session_1",
    )

    # Should not exceed max_context_length
    assert len(contexts) <= manager.max_context_length


def test_get_stats(manager):
    """Test getting manager statistics."""
    stats = manager.get_stats()

    assert "storage" in stats
    assert "config" in stats
    assert stats["config"]["enable_auto_save"] is True
    assert stats["config"]["max_context_length"] == 5
