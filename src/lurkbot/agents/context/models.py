"""Data models for context-aware system."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ContextRecord(BaseModel):
    """Single context record stored in the database."""

    context_id: str = Field(..., description="Unique identifier")
    session_id: str = Field(..., description="Session ID")
    user_id: str = Field(..., description="User ID")
    text: str = Field(..., description="Context text content")
    context_type: str = Field(
        ..., description="user_message | assistant_message | tool_result"
    )
    message_role: str = Field(..., description="user | assistant | system")
    timestamp: float = Field(..., description="Unix timestamp")
    has_tool_call: bool = Field(default=False, description="Whether contains tool calls")
    tool_names: list[str] = Field(default_factory=list, description="Tool names if any")

    @property
    def created_at(self) -> datetime:
        """Get creation datetime."""
        return datetime.fromtimestamp(self.timestamp)

    def to_metadata(self) -> dict[str, Any]:
        """Convert to ChromaDB metadata format.

        Note: ChromaDB only supports str, int, float, bool, or None in metadata.
        Lists are converted to comma-separated strings.
        """
        return {
            "context_id": self.context_id,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "context_type": self.context_type,
            "message_role": self.message_role,
            "timestamp": self.timestamp,
            "has_tool_call": self.has_tool_call,
            "tool_names": ",".join(self.tool_names) if self.tool_names else "",
        }

    @classmethod
    def from_metadata(cls, text: str, metadata: dict[str, Any]) -> "ContextRecord":
        """Create from ChromaDB metadata."""
        # Parse tool_names from comma-separated string
        tool_names_str = metadata.get("tool_names", "")
        tool_names = [name.strip() for name in tool_names_str.split(",") if name.strip()]

        return cls(
            context_id=metadata["context_id"],
            session_id=metadata["session_id"],
            user_id=metadata["user_id"],
            text=text,
            context_type=metadata["context_type"],
            message_role=metadata["message_role"],
            timestamp=metadata["timestamp"],
            has_tool_call=metadata.get("has_tool_call", False),
            tool_names=tool_names,
        )


class RetrievedContext(BaseModel):
    """Retrieved context with relevance score."""

    context: ContextRecord
    distance: float = Field(..., description="Vector distance (smaller is more similar)")
    relevance_score: float = Field(..., description="Relevance score (0-1, higher is better)")

    @classmethod
    def from_chroma_result(cls, doc: str, metadata: dict, distance: float) -> "RetrievedContext":
        """Create from ChromaDB query result."""
        # Convert distance to relevance score (distance越小，score越高)
        relevance_score = 1.0 / (1.0 + distance)

        context = ContextRecord.from_metadata(text=doc, metadata=metadata)

        return cls(context=context, distance=distance, relevance_score=relevance_score)


class ContextConfig(BaseModel):
    """Configuration for context-aware system."""

    persist_dir: str = Field(
        default="./data/chroma_db", description="ChromaDB persistence directory"
    )
    enable_auto_save: bool = Field(default=True, description="Auto-save contexts after interactions")
    max_context_length: int = Field(default=5, description="Maximum number of contexts to load")
    retrieval_limit: int = Field(default=5, description="Limit for retrieval results")
    include_session_history: bool = Field(
        default=True, description="Include current session history"
    )
    time_range_days: int = Field(default=30, description="Time range for context retrieval (days)")
