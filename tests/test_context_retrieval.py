"""Tests for context retrieval functionality."""

import tempfile
import time

import pytest

from lurkbot.agents.context.retrieval import ContextRetrieval
from lurkbot.agents.context.storage import ContextStorage


@pytest.fixture
def temp_storage_dir():
    """Create a temporary directory for ChromaDB."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def storage(temp_storage_dir):
    """Create a ContextStorage instance."""
    return ContextStorage(persist_directory=temp_storage_dir)


@pytest.fixture
def retrieval(storage):
    """Create a ContextRetrieval instance."""
    return ContextRetrieval(storage)


@pytest.fixture
def sample_contexts(storage):
    """Create sample contexts for testing."""
    base_time = time.time()
    contexts = [
        {
            "context_id": "ctx_1",
            "text": "I need help with Python programming",
            "metadata": {
                "context_id": "ctx_1",
                "session_id": "session_1",
                "user_id": "user_1",
                "timestamp": base_time,
                "context_type": "user_message",
                "message_role": "user",
            },
        },
        {
            "context_id": "ctx_2",
            "text": "Here's how to use Python list comprehensions",
            "metadata": {
                "context_id": "ctx_2",
                "session_id": "session_1",
                "user_id": "user_1",
                "timestamp": base_time + 1,
                "context_type": "assistant_message",
                "message_role": "assistant",
            },
        },
    ]
    storage.save_contexts_batch(contexts)
    return contexts


def test_find_relevant_contexts(retrieval, sample_contexts):
    """Test finding relevant contexts with semantic search."""
    results = retrieval.find_relevant_contexts(query="Python help", user_id="user_1", limit=2)
    assert len(results) <= 2


def test_get_session_history(retrieval, sample_contexts):
    """Test getting session history."""
    history = retrieval.get_session_history(session_id="session_1", limit=10)
    assert all(h.session_id == "session_1" for h in history)


def test_score_relevance(retrieval):
    """Test relevance scoring."""
    score_1 = retrieval.score_relevance(0.1)
    score_2 = retrieval.score_relevance(10.0)
    assert score_1 > score_2
