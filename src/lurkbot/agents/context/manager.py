"""Context manager - unified interface for context-aware system."""

import time
import uuid
from typing import Any

from lurkbot.logging import get_logger

from .models import ContextConfig, ContextRecord, RetrievedContext
from .retrieval import ContextRetrieval
from .storage import ContextStorage

logger = get_logger("context.manager")


class ContextManager:
    """Unified context management interface."""

    def __init__(
        self,
        persist_directory: str = "./data/chroma_db",
        enable_auto_save: bool = True,
        max_context_length: int = 5,
    ):
        """Initialize context manager."""
        self.storage = ContextStorage(persist_directory)
        self.retrieval = ContextRetrieval(self.storage)
        self.enable_auto_save = enable_auto_save
        self.max_context_length = max_context_length
        logger.info("ContextManager initialized")

    async def load_context_for_prompt(
        self,
        prompt: str,
        user_id: str,
        session_id: str | None = None,
        include_session_history: bool = True,
    ) -> list[RetrievedContext]:
        """Load relevant contexts for a user prompt."""
        try:
            contexts = self.retrieval.find_relevant_contexts(
                query=prompt, user_id=user_id, limit=self.max_context_length
            )

            if include_session_history and session_id:
                history = self.retrieval.get_session_history(session_id, limit=3)
                for record in history:
                    if not any(c.context.context_id == record.context_id for c in contexts):
                        contexts.append(
                            RetrievedContext(
                                context=record, distance=0.0, relevance_score=1.0
                            )
                        )

            contexts.sort(key=lambda c: c.relevance_score, reverse=True)
            logger.info(f"Loaded {len(contexts)} contexts for prompt")
            return contexts[: self.max_context_length]
        except Exception as e:
            logger.error(f"Failed to load context for prompt: {e}")
            return []

    async def save_interaction(
        self,
        session_id: str,
        user_id: str,
        user_message: str,
        assistant_message: str,
        tool_calls: list[dict] | None = None,
    ) -> None:
        """Save a complete interaction."""
        if not self.enable_auto_save:
            return

        try:
            timestamp = time.time()
            contexts = []

            user_context_id = f"{session_id}_{uuid.uuid4().hex[:8]}"
            user_record = ContextRecord(
                context_id=user_context_id,
                session_id=session_id,
                user_id=user_id,
                text=user_message,
                context_type="user_message",
                message_role="user",
                timestamp=timestamp,
            )
            contexts.append(
                {
                    "context_id": user_record.context_id,
                    "text": user_record.text,
                    "metadata": user_record.to_metadata(),
                }
            )

            assistant_context_id = f"{session_id}_{uuid.uuid4().hex[:8]}"
            has_tool_call = bool(tool_calls)
            tool_names = [tc.get("name") for tc in tool_calls] if tool_calls else []

            assistant_record = ContextRecord(
                context_id=assistant_context_id,
                session_id=session_id,
                user_id=user_id,
                text=assistant_message,
                context_type="assistant_message",
                message_role="assistant",
                timestamp=timestamp + 0.001,
                has_tool_call=has_tool_call,
                tool_names=tool_names,
            )
            contexts.append(
                {
                    "context_id": assistant_record.context_id,
                    "text": assistant_record.text,
                    "metadata": assistant_record.to_metadata(),
                }
            )

            self.storage.save_contexts_batch(contexts)
            logger.info(f"Saved interaction for session {session_id}")
        except Exception as e:
            logger.error(f"Failed to save interaction: {e}")

    def format_contexts_for_prompt(self, contexts: list[RetrievedContext]) -> str:
        """Format contexts for inclusion in system prompt."""
        if not contexts:
            return ""

        lines = ["You have access to the following relevant conversation history:"]
        lines.append("")

        for i, ctx in enumerate(contexts, 1):
            record = ctx.context
            role = "User" if record.message_role == "user" else "Assistant"
            timestamp_str = record.created_at.strftime("%Y-%m-%d %H:%M")

            lines.append(f"{i}. [{timestamp_str}] {role}:")
            lines.append(f"   {record.text[:200]}")
            if len(record.text) > 200:
                lines.append("   ...")
            lines.append("")

        return "\n".join(lines)

    def get_stats(self) -> dict[str, Any]:
        """Get context manager statistics."""
        storage_stats = self.storage.get_collection_stats()
        return {
            "storage": storage_stats,
            "config": {
                "enable_auto_save": self.enable_auto_save,
                "max_context_length": self.max_context_length,
            },
        }


_context_manager: ContextManager | None = None


def get_context_manager(
    persist_directory: str = "./data/chroma_db",
    enable_auto_save: bool = True,
    max_context_length: int = 5,
) -> ContextManager:
    """Get or create global ContextManager instance."""
    global _context_manager

    if _context_manager is None:
        _context_manager = ContextManager(
            persist_directory=persist_directory,
            enable_auto_save=enable_auto_save,
            max_context_length=max_context_length,
        )

    return _context_manager
