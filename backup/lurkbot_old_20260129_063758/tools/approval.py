"""Tool approval system for GROUP/TOPIC sessions.

This module implements approval workflows for dangerous tools that require
user consent before execution. Approvals are requested via Channel notifications
and resolved through user responses.

Architecture:
- ApprovalManager: Manages pending approvals with timeout
- ApprovalRequest: Request data (tool, command, session info)
- ApprovalDecision: User response (approve/deny)
- ApprovalRecord: Complete approval lifecycle record
"""

import asyncio
import time
import uuid
from enum import Enum
from typing import Any

from loguru import logger
from pydantic import BaseModel, Field


class ApprovalDecision(str, Enum):
    """User decision on tool approval."""

    APPROVE = "approve"
    DENY = "deny"
    TIMEOUT = "timeout"  # Automatic decision when timeout expires


class ApprovalRequest(BaseModel):
    """Tool execution approval request.

    Contains all information needed for user to make an informed decision.
    """

    tool_name: str = Field(description="Name of the tool requesting approval")
    command: str | None = Field(None, description="Command to execute (for bash tool)")
    args: dict[str, Any] = Field(default_factory=dict, description="Tool arguments")
    session_key: str = Field(description="Session requesting approval")
    agent_id: str | None = Field(None, description="Agent ID if available")
    security_context: str | None = Field(None, description="Security level or context")
    reason: str | None = Field(None, description="Why this tool needs approval")


class ApprovalRecord(BaseModel):
    """Complete record of an approval lifecycle.

    Tracks the request, decision, timestamps, and resolver identity.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    request: ApprovalRequest
    created_at_ms: int = Field(default_factory=lambda: int(time.time() * 1000))
    expires_at_ms: int
    resolved_at_ms: int | None = None
    decision: ApprovalDecision | None = None
    resolved_by: str | None = None

    @property
    def is_expired(self) -> bool:
        """Check if approval has expired."""
        return int(time.time() * 1000) >= self.expires_at_ms

    @property
    def is_resolved(self) -> bool:
        """Check if approval has been resolved."""
        return self.decision is not None


class ApprovalManager:
    """Manages tool approval lifecycle with timeout handling.

    Provides async interface for requesting approvals and waiting for decisions.
    Supports timeout with automatic DENY on expiry.

    Example:
        manager = ApprovalManager()
        request = ApprovalRequest(
            tool_name="bash",
            command="rm -rf /",
            session_key="telegram_123_456"
        )
        record = manager.create(request, timeout_ms=300000)  # 5 min

        # In another task, resolve the approval
        manager.resolve(record.id, ApprovalDecision.APPROVE, "user_123")

        # Wait for decision (blocks until resolved or timeout)
        decision = await manager.wait_for_decision(record.id)
    """

    def __init__(self) -> None:
        """Initialize approval manager."""
        self._pending: dict[str, _PendingEntry] = {}
        self._records: dict[str, ApprovalRecord] = {}  # All records (waiting or not)

    def create(
        self,
        request: ApprovalRequest,
        timeout_ms: int = 300000,  # 5 minutes default
        approval_id: str | None = None,
    ) -> ApprovalRecord:
        """Create a new approval record.

        Args:
            request: Approval request data
            timeout_ms: Timeout in milliseconds (default: 5 minutes)
            approval_id: Optional custom approval ID

        Returns:
            New approval record with unique ID
        """
        record_id = approval_id.strip() if approval_id else str(uuid.uuid4())
        now_ms = int(time.time() * 1000)

        record = ApprovalRecord(
            id=record_id,
            request=request,
            created_at_ms=now_ms,
            expires_at_ms=now_ms + timeout_ms,
        )

        # Store in records map
        self._records[record.id] = record

        logger.info(
            f"Created approval {record.id} for tool={request.tool_name}, "
            f"session={request.session_key}, expires in {timeout_ms}ms"
        )
        return record

    async def wait_for_decision(self, record: ApprovalRecord) -> ApprovalDecision:
        """Wait for user decision or timeout.

        Args:
            record: Approval record to wait for

        Returns:
            User decision or TIMEOUT

        Note:
            This is a blocking async call that waits until:
            - User approves/denies via resolve()
            - Timeout expires (auto-deny)

            Can be called after resolve() - if already resolved, returns immediately.
        """
        # Check if already resolved (resolve() called before wait)
        if record.is_resolved:
            logger.info(f"Approval {record.id} already resolved with {record.decision}")
            return record.decision  # type: ignore

        # Calculate remaining timeout
        now_ms = int(time.time() * 1000)
        remaining_ms = record.expires_at_ms - now_ms

        if remaining_ms <= 0:
            logger.warning(f"Approval {record.id} already expired")
            record.resolved_at_ms = now_ms
            record.decision = ApprovalDecision.TIMEOUT
            return ApprovalDecision.TIMEOUT

        # Create future for this approval
        future: asyncio.Future[ApprovalDecision] = asyncio.Future()
        timeout_task = asyncio.create_task(
            self._timeout_handler(record.id, remaining_ms / 1000, future)
        )

        # Store in pending map
        entry = _PendingEntry(record=record, future=future, timeout_task=timeout_task)
        self._pending[record.id] = entry

        try:
            # Wait for decision or timeout
            decision = await future
            logger.info(f"Approval {record.id} resolved with {decision}")
            return decision
        finally:
            # Cleanup
            self._pending.pop(record.id, None)
            if not timeout_task.done():
                timeout_task.cancel()

    def resolve(
        self,
        record_id: str,
        decision: ApprovalDecision,
        resolved_by: str | None = None,
    ) -> bool:
        """Resolve a pending approval.

        Args:
            record_id: Approval ID to resolve
            decision: User decision
            resolved_by: User ID who resolved it

        Returns:
            True if approval was resolved, False if not found/already resolved
        """
        entry = self._pending.get(record_id)
        if not entry:
            logger.warning(f"Approval {record_id} not found or already resolved")
            return False

        # Update record
        entry.record.resolved_at_ms = int(time.time() * 1000)
        entry.record.decision = decision
        entry.record.resolved_by = resolved_by

        # Resolve future
        if not entry.future.done():
            entry.future.set_result(decision)

        # Cancel timeout
        if not entry.timeout_task.done():
            entry.timeout_task.cancel()

        logger.info(f"Resolved approval {record_id} with {decision} by {resolved_by}")
        return True

    def get_snapshot(self, record_id: str) -> ApprovalRecord | None:
        """Get current state of an approval.

        Args:
            record_id: Approval ID

        Returns:
            Approval record or None if not found
        """
        # Check pending first (for active waits)
        entry = self._pending.get(record_id)
        if entry:
            return entry.record

        # Check all records
        return self._records.get(record_id)

    def get_all_pending(self) -> list[ApprovalRecord]:
        """Get all pending approvals.

        Returns:
            List of pending approval records
        """
        return [entry.record for entry in self._pending.values()]

    async def _timeout_handler(
        self, record_id: str, timeout_seconds: float, future: asyncio.Future
    ) -> None:
        """Handle approval timeout.

        Args:
            record_id: Approval ID
            timeout_seconds: Timeout duration in seconds
            future: Future to resolve on timeout
        """
        try:
            await asyncio.sleep(timeout_seconds)
            entry = self._pending.get(record_id)
            if entry and not entry.future.done():
                logger.warning(f"Approval {record_id} timed out")
                entry.record.resolved_at_ms = int(time.time() * 1000)
                entry.record.decision = ApprovalDecision.TIMEOUT
                future.set_result(ApprovalDecision.TIMEOUT)
        except asyncio.CancelledError:
            # Timeout was cancelled (approval resolved early)
            pass


class _PendingEntry(BaseModel):
    """Internal entry for tracking pending approvals."""

    model_config = {"arbitrary_types_allowed": True}

    record: ApprovalRecord
    future: Any = Field(exclude=True)  # asyncio.Future
    timeout_task: Any = Field(exclude=True)  # asyncio.Task
