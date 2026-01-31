"""Context storage using ChromaDB."""

import time
from typing import Any

import chromadb
from chromadb.config import Settings

from lurkbot.logging import get_logger

from .models import ContextRecord

logger = get_logger("context.storage")


class ContextStorage:
    """Manage context persistence in ChromaDB."""

    def __init__(self, persist_directory: str = "./data/chroma_db"):
        """Initialize persistent ChromaDB client.

        Args:
            persist_directory: Directory for ChromaDB data
        """
        self.persist_directory = persist_directory

        # Create persistent client
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(anonymized_telemetry=False),
        )

        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name="contexts",
            metadata={"description": "LurkBot conversation contexts"},
        )

        logger.info(f"Context storage initialized at {persist_directory}")
        logger.info(f"Current collection size: {self.collection.count()}")

    def save_context(
        self,
        context_id: str,
        text: str,
        metadata: dict[str, Any],
        embedding: list[float] | None = None,
    ) -> None:
        """Save a single context.

        Args:
            context_id: Unique identifier
            text: Context text content
            metadata: Context metadata
            embedding: Optional pre-computed embedding
        """
        try:
            self.collection.add(
                ids=[context_id],
                documents=[text],
                metadatas=[metadata],
                embeddings=[embedding] if embedding else None,
            )
            logger.debug(f"Saved context {context_id}")
        except Exception as e:
            logger.error(f"Failed to save context {context_id}: {e}")
            raise

    def save_contexts_batch(self, contexts: list[dict[str, Any]]) -> None:
        """Save multiple contexts in batch.

        Args:
            contexts: List of context dicts with keys: context_id, text, metadata, embedding (optional)
        """
        if not contexts:
            return

        try:
            ids = [ctx["context_id"] for ctx in contexts]
            documents = [ctx["text"] for ctx in contexts]
            metadatas = [ctx["metadata"] for ctx in contexts]
            embeddings = [ctx.get("embedding") for ctx in contexts]

            # Only pass embeddings if all are provided
            if all(e is not None for e in embeddings):
                self.collection.add(
                    ids=ids, documents=documents, metadatas=metadatas, embeddings=embeddings
                )
            else:
                self.collection.add(ids=ids, documents=documents, metadatas=metadatas)

            logger.info(f"Saved {len(contexts)} contexts in batch")
        except Exception as e:
            logger.error(f"Failed to save contexts batch: {e}")
            raise

    def delete_context(self, context_id: str) -> None:
        """Delete a specific context.

        Args:
            context_id: Context ID to delete
        """
        try:
            self.collection.delete(ids=[context_id])
            logger.debug(f"Deleted context {context_id}")
        except Exception as e:
            logger.error(f"Failed to delete context {context_id}: {e}")
            raise

    def delete_session_contexts(self, session_id: str) -> None:
        """Delete all contexts for a session.

        Args:
            session_id: Session ID
        """
        try:
            self.collection.delete(where={"session_id": session_id})
            logger.info(f"Deleted all contexts for session {session_id}")
        except Exception as e:
            logger.error(f"Failed to delete session contexts: {e}")
            raise

    def delete_user_contexts(self, user_id: str) -> None:
        """Delete all contexts for a user.

        Args:
            user_id: User ID
        """
        try:
            self.collection.delete(where={"user_id": user_id})
            logger.info(f"Deleted all contexts for user {user_id}")
        except Exception as e:
            logger.error(f"Failed to delete user contexts: {e}")
            raise

    def get_collection_stats(self) -> dict[str, Any]:
        """Get collection statistics.

        Returns:
            Dict with stats: count, persist_directory
        """
        return {
            "count": self.collection.count(),
            "persist_directory": self.persist_directory,
            "collection_name": self.collection.name,
        }

    def query_raw(
        self,
        query_texts: list[str] | None = None,
        query_embeddings: list[list[float]] | None = None,
        n_results: int = 5,
        where: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Raw query interface for advanced usage.

        Args:
            query_texts: Query text strings
            query_embeddings: Query embeddings
            n_results: Number of results to return
            where: Metadata filter

        Returns:
            ChromaDB query results
        """
        return self.collection.query(
            query_texts=query_texts,
            query_embeddings=query_embeddings,
            n_results=n_results,
            where=where,
            include=["documents", "metadatas", "distances"],
        )
