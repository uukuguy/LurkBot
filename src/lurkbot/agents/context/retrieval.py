"""Context retrieval with semantic search."""

import time
from typing import Any

from lurkbot.logging import get_logger

from .models import ContextRecord, RetrievedContext
from .storage import ContextStorage

logger = get_logger("context.retrieval")


class ContextRetrieval:
    """Retrieve relevant contexts using semantic search."""

    def __init__(self, storage: ContextStorage):
        """Initialize retrieval manager.

        Args:
            storage: ContextStorage instance
        """
        self.storage = storage

    def find_relevant_contexts(
        self,
        query: str,
        user_id: str | None = None,
        session_id: str | None = None,
        limit: int = 5,
        time_range: tuple[float, float] | None = None,
        context_types: list[str] | None = None,
    ) -> list[RetrievedContext]:
        """Find relevant contexts using semantic search.

        Args:
            query: Query text
            user_id: Filter by user ID
            session_id: Filter by session ID
            limit: Maximum results
            time_range: Tuple of (start_timestamp, end_timestamp)
            context_types: Filter by context types

        Returns:
            List of RetrievedContext objects sorted by relevance
        """
        # Build metadata filter
        where = {}
        if user_id:
            where["user_id"] = user_id
        if session_id:
            where["session_id"] = session_id
        if context_types:
            where["context_type"] = {"$in": context_types}

        # TODO: ChromaDB doesn't support timestamp range filtering directly
        # We'll filter after retrieval for now
        try:
            results = self.storage.query_raw(
                query_texts=[query], n_results=limit, where=where if where else None
            )

            if not results["documents"] or not results["documents"][0]:
                logger.debug(f"No contexts found for query: {query[:50]}...")
                return []

            # Parse results
            retrieved = []
            for doc, metadata, distance in zip(
                results["documents"][0], results["metadatas"][0], results["distances"][0]
            ):
                # Apply time range filter
                if time_range:
                    timestamp = metadata.get("timestamp", 0)
                    if not (time_range[0] <= timestamp <= time_range[1]):
                        continue

                retrieved.append(RetrievedContext.from_chroma_result(doc, metadata, distance))

            logger.info(f"Found {len(retrieved)} relevant contexts for query")
            return retrieved

        except Exception as e:
            logger.error(f"Failed to retrieve contexts: {e}")
            return []

    def get_session_history(self, session_id: str, limit: int = 10) -> list[ContextRecord]:
        """Get recent history for a session.

        Args:
            session_id: Session ID
            limit: Maximum number of records

        Returns:
            List of ContextRecord sorted by timestamp (newest first)
        """
        try:
            # Query with session filter
            results = self.storage.query_raw(
                query_texts=[""],  # Empty query to get all
                n_results=limit,
                where={"session_id": session_id},
            )

            if not results["documents"] or not results["documents"][0]:
                return []

            # Convert to ContextRecord
            records = [
                ContextRecord.from_metadata(doc, metadata)
                for doc, metadata in zip(results["documents"][0], results["metadatas"][0])
            ]

            # Sort by timestamp (newest first)
            records.sort(key=lambda r: r.timestamp, reverse=True)

            return records[:limit]

        except Exception as e:
            logger.error(f"Failed to get session history: {e}")
            return []

    def get_user_contexts(
        self,
        user_id: str,
        limit: int = 20,
        time_range: tuple[float, float] | None = None,
    ) -> list[ContextRecord]:
        """Get contexts for a user across all sessions.

        Args:
            user_id: User ID
            limit: Maximum number of records
            time_range: Optional time range filter

        Returns:
            List of ContextRecord sorted by timestamp (newest first)
        """
        try:
            results = self.storage.query_raw(
                query_texts=[""],  # Empty query
                n_results=limit,
                where={"user_id": user_id},
            )

            if not results["documents"] or not results["documents"][0]:
                return []

            records = [
                ContextRecord.from_metadata(doc, metadata)
                for doc, metadata in zip(results["documents"][0], results["metadatas"][0])
            ]

            # Apply time range filter
            if time_range:
                records = [r for r in records if time_range[0] <= r.timestamp <= time_range[1]]

            # Sort by timestamp
            records.sort(key=lambda r: r.timestamp, reverse=True)

            return records[:limit]

        except Exception as e:
            logger.error(f"Failed to get user contexts: {e}")
            return []

    def score_relevance(self, distance: float) -> float:
        """Convert distance to relevance score.

        Args:
            distance: Vector distance from ChromaDB

        Returns:
            Relevance score (0-1, higher is better)
        """
        # Simple inverse distance scoring
        return 1.0 / (1.0 + distance)
