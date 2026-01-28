"""Tests for tool approval system."""

import asyncio
import time

import pytest

from lurkbot.tools.approval import (
    ApprovalDecision,
    ApprovalManager,
    ApprovalRecord,
    ApprovalRequest,
)


@pytest.fixture
def approval_manager():
    """Create approval manager instance."""
    return ApprovalManager()


@pytest.fixture
def sample_request():
    """Create sample approval request."""
    return ApprovalRequest(
        tool_name="bash",
        command="rm -rf /tmp/test",
        session_key="telegram_123_456",
        agent_id="agent_001",
        security_context="GROUP",
        reason="User requested file deletion",
    )


class TestApprovalRequest:
    """Tests for ApprovalRequest model."""

    def test_create_basic_request(self):
        """Test creating basic approval request."""
        request = ApprovalRequest(
            tool_name="bash", session_key="test_session"
        )
        assert request.tool_name == "bash"
        assert request.session_key == "test_session"
        assert request.command is None
        assert request.args == {}

    def test_create_full_request(self, sample_request):
        """Test creating request with all fields."""
        assert sample_request.tool_name == "bash"
        assert sample_request.command == "rm -rf /tmp/test"
        assert sample_request.session_key == "telegram_123_456"
        assert sample_request.agent_id == "agent_001"
        assert sample_request.security_context == "GROUP"
        assert sample_request.reason == "User requested file deletion"


class TestApprovalRecord:
    """Tests for ApprovalRecord model."""

    def test_create_record(self, approval_manager, sample_request):
        """Test creating approval record."""
        record = approval_manager.create(sample_request, timeout_ms=5000)

        assert record.id is not None
        assert len(record.id) > 0
        assert record.request == sample_request
        assert record.created_at_ms > 0
        assert record.expires_at_ms == record.created_at_ms + 5000
        assert record.resolved_at_ms is None
        assert record.decision is None
        assert record.resolved_by is None

    def test_custom_approval_id(self, approval_manager, sample_request):
        """Test creating record with custom ID."""
        custom_id = "custom_approval_123"
        record = approval_manager.create(
            sample_request, approval_id=custom_id
        )
        assert record.id == custom_id

    def test_is_expired(self, approval_manager, sample_request):
        """Test expiry check."""
        # Create already-expired record
        record = approval_manager.create(sample_request, timeout_ms=-1000)
        assert record.is_expired

        # Create valid record
        record = approval_manager.create(sample_request, timeout_ms=5000)
        assert not record.is_expired

    def test_is_resolved(self, approval_manager, sample_request):
        """Test resolution check."""
        record = approval_manager.create(sample_request)
        assert not record.is_resolved

        record.decision = ApprovalDecision.APPROVE
        assert record.is_resolved


class TestApprovalManager:
    """Tests for ApprovalManager."""

    @pytest.mark.asyncio
    async def test_approve_immediately(self, approval_manager, sample_request):
        """Test approving before timeout."""
        record = approval_manager.create(sample_request, timeout_ms=5000)

        # Start waiting in background
        wait_task = asyncio.create_task(
            approval_manager.wait_for_decision(record)
        )

        # Give it time to start waiting
        await asyncio.sleep(0.05)

        # Resolve while waiting
        resolved = approval_manager.resolve(
            record.id, ApprovalDecision.APPROVE, "user_123"
        )
        assert resolved

        # Wait for decision
        decision = await wait_task
        assert decision == ApprovalDecision.APPROVE
        assert record.decision == ApprovalDecision.APPROVE
        assert record.resolved_by == "user_123"
        assert record.resolved_at_ms is not None

    @pytest.mark.asyncio
    async def test_deny_immediately(self, approval_manager, sample_request):
        """Test denying before timeout."""
        record = approval_manager.create(sample_request, timeout_ms=5000)

        # Start waiting in background
        wait_task = asyncio.create_task(
            approval_manager.wait_for_decision(record)
        )

        # Give it time to start waiting
        await asyncio.sleep(0.05)

        # Resolve while waiting
        approval_manager.resolve(
            record.id, ApprovalDecision.DENY, "user_456"
        )

        # Wait for decision
        decision = await wait_task
        assert decision == ApprovalDecision.DENY
        assert record.decision == ApprovalDecision.DENY
        assert record.resolved_by == "user_456"

    @pytest.mark.asyncio
    async def test_timeout(self, approval_manager, sample_request):
        """Test approval timeout."""
        record = approval_manager.create(sample_request, timeout_ms=100)

        # Wait for timeout (no resolve)
        decision = await approval_manager.wait_for_decision(record)
        assert decision == ApprovalDecision.TIMEOUT
        assert record.decision == ApprovalDecision.TIMEOUT
        assert record.resolved_at_ms is not None

    @pytest.mark.asyncio
    async def test_resolve_during_wait(self, approval_manager, sample_request):
        """Test resolving while waiting for decision."""
        record = approval_manager.create(sample_request, timeout_ms=5000)

        # Start waiting in background
        wait_task = asyncio.create_task(
            approval_manager.wait_for_decision(record)
        )

        # Give it time to start
        await asyncio.sleep(0.1)

        # Resolve while waiting
        approval_manager.resolve(
            record.id, ApprovalDecision.APPROVE, "user_789"
        )

        # Should resolve immediately
        decision = await wait_task
        assert decision == ApprovalDecision.APPROVE

    @pytest.mark.asyncio
    async def test_resolve_nonexistent(self, approval_manager):
        """Test resolving non-existent approval."""
        resolved = approval_manager.resolve(
            "nonexistent_id", ApprovalDecision.APPROVE
        )
        assert not resolved

    @pytest.mark.asyncio
    async def test_resolve_twice(self, approval_manager, sample_request):
        """Test resolving the same approval twice."""
        record = approval_manager.create(sample_request, timeout_ms=5000)

        # Start waiting in background
        wait_task = asyncio.create_task(
            approval_manager.wait_for_decision(record)
        )

        # Give it time to start waiting
        await asyncio.sleep(0.05)

        # First resolve
        approval_manager.resolve(record.id, ApprovalDecision.APPROVE)
        decision1 = await wait_task
        assert decision1 == ApprovalDecision.APPROVE

        # Second resolve should fail (already resolved)
        resolved = approval_manager.resolve(record.id, ApprovalDecision.DENY)
        assert not resolved

    def test_get_snapshot(self, approval_manager, sample_request):
        """Test getting approval snapshot."""
        record = approval_manager.create(sample_request)

        snapshot = approval_manager.get_snapshot(record.id)
        assert snapshot is not None
        assert snapshot.id == record.id
        assert snapshot.request == sample_request

    def test_get_snapshot_nonexistent(self, approval_manager):
        """Test getting snapshot of non-existent approval."""
        snapshot = approval_manager.get_snapshot("nonexistent_id")
        assert snapshot is None

    @pytest.mark.asyncio
    async def test_get_all_pending(self, approval_manager, sample_request):
        """Test getting all pending approvals."""
        # Create multiple approvals
        record1 = approval_manager.create(sample_request)
        record2 = approval_manager.create(
            ApprovalRequest(tool_name="file_read", session_key="test_2")
        )

        # Start waiting for both (makes them "pending")
        wait_task1 = asyncio.create_task(
            approval_manager.wait_for_decision(record1)
        )
        wait_task2 = asyncio.create_task(
            approval_manager.wait_for_decision(record2)
        )

        # Give them time to start
        await asyncio.sleep(0.05)

        # Both should be pending
        pending = approval_manager.get_all_pending()
        assert len(pending) >= 2
        ids = {r.id for r in pending}
        assert record1.id in ids
        assert record2.id in ids

        # Cleanup: resolve both
        approval_manager.resolve(record1.id, ApprovalDecision.APPROVE)
        approval_manager.resolve(record2.id, ApprovalDecision.APPROVE)
        await asyncio.gather(wait_task1, wait_task2)

    @pytest.mark.asyncio
    async def test_wait_already_expired(self, approval_manager, sample_request):
        """Test waiting for already-expired approval."""
        record = approval_manager.create(sample_request, timeout_ms=-1000)

        decision = await approval_manager.wait_for_decision(record)
        assert decision == ApprovalDecision.TIMEOUT

    @pytest.mark.asyncio
    async def test_multiple_approvals_concurrent(self, approval_manager):
        """Test handling multiple approvals concurrently."""
        requests = [
            ApprovalRequest(tool_name=f"tool_{i}", session_key=f"session_{i}")
            for i in range(5)
        ]
        records = [
            approval_manager.create(req, timeout_ms=2000) for req in requests
        ]

        # Start waiting for all
        wait_tasks = [
            asyncio.create_task(approval_manager.wait_for_decision(record))
            for record in records
        ]

        # Resolve some, let others timeout
        await asyncio.sleep(0.1)
        approval_manager.resolve(records[0].id, ApprovalDecision.APPROVE)
        approval_manager.resolve(records[2].id, ApprovalDecision.DENY)

        # Wait for all
        decisions = await asyncio.gather(*wait_tasks)

        # Check decisions
        assert decisions[0] == ApprovalDecision.APPROVE
        assert decisions[2] == ApprovalDecision.DENY
        # Others should timeout (after 2 seconds)


class TestApprovalDecision:
    """Tests for ApprovalDecision enum."""

    def test_all_decisions(self):
        """Test all decision types exist."""
        assert ApprovalDecision.APPROVE == "approve"
        assert ApprovalDecision.DENY == "deny"
        assert ApprovalDecision.TIMEOUT == "timeout"

    def test_decision_comparison(self):
        """Test decision comparison."""
        assert ApprovalDecision.APPROVE != ApprovalDecision.DENY
        assert ApprovalDecision.APPROVE == ApprovalDecision.APPROVE
