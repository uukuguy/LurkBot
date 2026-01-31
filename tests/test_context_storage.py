"""Tests for context storage functionality."""

import tempfile
import time
from pathlib import Path

import pytest

from lurkbot.agents.context.models import ContextRecord
from lurkbot.agents.context.storage import ContextStorage


@pytest.fixture
def temp_storage_dir():
    """Create a temporary directory for ChromaDB."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def storage(temp_storage_dir):
    """Create a ContextStorage instance with temporary directory."""
    return ContextStorage(persist_directory=temp_storage_dir)


def test_storage_initialization(storage):
    """Test storage initialization."""
    stats = storage.get_collection_stats()
    assert stats["count"] == 0
    assert stats["collection_name"] == "contexts"


def test_save_single_context(storage):
    """Test saving a single context."""
    context_id = "test_ctx_001"
    text = "This is a test message"
    metadata = {
        "context_id": context_id,
        "session_id": "session_1",
        "user_id": "user_1",
        "timestamp": time.time(),
        "context_type": "user_message",
        "message_role": "user",
    }

    storage.save_context(context_id=context_id, text=text, metadata=metadata)

    stats = storage.get_collection_stats()
    assert stats["count"] == 1


def test_save_contexts_batch(storage):
    """Test batch saving contexts."""
    contexts = [
        {
            "context_id": f"ctx_{i}",
            "text": f"Message {i}",
            "metadata": {
                "context_id": f"ctx_{i}",
                "session_id": "session_1",
                "user_id": "user_1",
                "timestamp": time.time() + i,
                "context_type": "user_message",
                "message_role": "user",
            },
        }
        for i in range(5)
    ]

    storage.save_contexts_batch(contexts)

    stats = storage.get_collection_stats()
    assert stats["count"] == 5


def test_delete_context(storage):
    """Test deleting a specific context."""
    # Save two contexts
    for i in range(2):
        storage.save_context(
            context_id=f"ctx_{i}",
            text=f"Message {i}",
            metadata={
                "context_id": f"ctx_{i}",
                "session_id": "session_1",
                "user_id": "user_1",
                "timestamp": time.time(),
                "context_type": "user_message",
                "message_role": "user",
            },
        )

    # Delete one
    storage.delete_context("ctx_0")

    stats = storage.get_collection_stats()
    assert stats["count"] == 1


def test_delete_session_contexts(storage):
    """Test deleting all contexts for a session."""
    # Save contexts for two sessions
    for session_idx in range(2):
        for msg_idx in range(3):
            storage.save_context(
                context_id=f"session_{session_idx}_msg_{msg_idx}",
                text=f"Message {msg_idx}",
                metadata={
                    "context_id": f"session_{session_idx}_msg_{msg_idx}",
                    "session_id": f"session_{session_idx}",
                    "user_id": "user_1",
                    "timestamp": time.time(),
                    "context_type": "user_message",
                    "message_role": "user",
                },
            )

    assert storage.get_collection_stats()["count"] == 6

    # Delete session_0
    storage.delete_session_contexts("session_0")

    assert storage.get_collection_stats()["count"] == 3


def test_delete_user_contexts(storage):
    """Test deleting all contexts for a user."""
    # Save contexts for two users
    for user_idx in range(2):
        for msg_idx in range(3):
            storage.save_context(
                context_id=f"user_{user_idx}_msg_{msg_idx}",
                text=f"Message {msg_idx}",
                metadata={
                    "context_id": f"user_{user_idx}_msg_{msg_idx}",
                    "session_id": "session_1",
                    "user_id": f"user_{user_idx}",
                    "timestamp": time.time(),
                    "context_type": "user_message",
                    "message_role": "user",
                },
            )

    assert storage.get_collection_stats()["count"] == 6

    # Delete user_0
    storage.delete_user_contexts("user_0")

    assert storage.get_collection_stats()["count"] == 3


def test_query_raw(storage):
    """Test raw query interface."""
    # Save some contexts
    contexts = [
        {
            "context_id": "ctx_1",
            "text": "I want to learn about machine learning",
            "metadata": {
                "context_id": "ctx_1",
                "session_id": "session_1",
                "user_id": "user_1",
                "timestamp": time.time(),
                "context_type": "user_message",
                "message_role": "user",
            },
        },
        {
            "context_id": "ctx_2",
            "text": "Tell me about deep learning",
            "metadata": {
                "context_id": "ctx_2",
                "session_id": "session_1",
                "user_id": "user_1",
                "timestamp": time.time(),
                "context_type": "user_message",
                "message_role": "user",
            },
        },
    ]
    storage.save_contexts_batch(contexts)

    # Query
    results = storage.query_raw(query_texts=["machine learning tutorials"], n_results=2)

    assert len(results["documents"][0]) == 2
    assert len(results["metadatas"][0]) == 2
    assert len(results["distances"][0]) == 2


def test_persistence(temp_storage_dir):
    """Test that data persists across storage instances."""
    # Create storage and save data
    storage1 = ContextStorage(persist_directory=temp_storage_dir)
    storage1.save_context(
        context_id="ctx_1",
        text="Persistent message",
        metadata={
            "context_id": "ctx_1",
            "session_id": "session_1",
            "user_id": "user_1",
            "timestamp": time.time(),
            "context_type": "user_message",
            "message_role": "user",
        },
    )

    # Create new storage instance pointing to same directory
    storage2 = ContextStorage(persist_directory=temp_storage_dir)
    stats = storage2.get_collection_stats()

    # Data should persist
    assert stats["count"] == 1
