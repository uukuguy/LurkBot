"""审计系统单元测试"""

import asyncio
from datetime import datetime, timedelta

import pytest

from lurkbot.tenants.audit.logger import AuditLogger, configure_audit_logger
from lurkbot.tenants.audit.models import (
    AuditEvent,
    AuditEventType,
    AuditQuery,
    AuditResult,
    AuditSeverity,
    ComplianceCheckResult,
    PolicyEvaluation,
    PolicyEvaluationQuery,
    PolicyEvaluationResult,
    ReportFormat,
    ReportStatus,
    ReportType,
    ResourceType,
)
from lurkbot.tenants.audit.policy_tracker import PolicyTracker
from lurkbot.tenants.audit.reports import ReportGenerator
from lurkbot.tenants.audit.storage import MemoryAuditStorage


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def storage():
    """创建内存存储"""
    return MemoryAuditStorage()


@pytest.fixture
def logger(storage):
    """创建审计日志记录器"""
    return AuditLogger(storage=storage, async_mode=False)


@pytest.fixture
def tracker(storage):
    """创建策略追踪器"""
    return PolicyTracker(storage=storage)


@pytest.fixture
def generator(storage):
    """创建报告生成器"""
    return ReportGenerator(storage=storage)


# ============================================================================
# 数据模型测试
# ============================================================================


class TestAuditModels:
    """审计数据模型测试"""

    def test_audit_event_creation(self):
        """测试审计事件创建"""
        event = AuditEvent(
            event_id="test-event-1",
            event_type=AuditEventType.API_CALL,
            action="test_action",
            tenant_id="tenant-1",
            user_id="user-1",
        )

        assert event.event_id == "test-event-1"
        assert event.event_type == AuditEventType.API_CALL
        assert event.action == "test_action"
        assert event.result == AuditResult.SUCCESS
        assert event.severity == AuditSeverity.INFO

    def test_audit_event_is_success(self):
        """测试审计事件成功检查"""
        event = AuditEvent(
            event_id="test-1",
            event_type=AuditEventType.API_CALL,
            action="test",
            result=AuditResult.SUCCESS,
        )
        assert event.is_success() is True

        event.result = AuditResult.FAILURE
        assert event.is_success() is False

    def test_audit_event_is_security_event(self):
        """测试安全事件检查"""
        event = AuditEvent(
            event_id="test-1",
            event_type=AuditEventType.AUTH_FAILURE,
            action="login",
        )
        assert event.is_security_event() is True

        event.event_type = AuditEventType.API_CALL
        assert event.is_security_event() is False

    def test_policy_evaluation_creation(self):
        """测试策略评估记录创建"""
        evaluation = PolicyEvaluation(
            evaluation_id="eval-1",
            tenant_id="tenant-1",
            action="read",
            resource_type="document",
            result=PolicyEvaluationResult.ALLOW,
        )

        assert evaluation.evaluation_id == "eval-1"
        assert evaluation.is_allowed() is True
        assert evaluation.is_denied() is False

    def test_audit_query_defaults(self):
        """测试审计查询默认值"""
        query = AuditQuery()

        assert query.limit == 100
        assert query.offset == 0
        assert query.order_by == "timestamp"
        assert query.order_desc is True


# ============================================================================
# 存储测试
# ============================================================================


class TestMemoryAuditStorage:
    """内存审计存储测试"""

    @pytest.mark.asyncio
    async def test_save_and_get_event(self, storage):
        """测试保存和获取事件"""
        event = AuditEvent(
            event_id="test-event-1",
            event_type=AuditEventType.API_CALL,
            action="test_action",
            tenant_id="tenant-1",
        )

        await storage.save_event(event)
        retrieved = await storage.get_event("test-event-1")

        assert retrieved is not None
        assert retrieved.event_id == "test-event-1"
        assert retrieved.action == "test_action"

    @pytest.mark.asyncio
    async def test_query_events_by_tenant(self, storage):
        """测试按租户查询事件"""
        # 创建多个事件
        for i in range(5):
            event = AuditEvent(
                event_id=f"event-{i}",
                event_type=AuditEventType.API_CALL,
                action=f"action_{i}",
                tenant_id="tenant-1" if i < 3 else "tenant-2",
            )
            await storage.save_event(event)

        # 查询租户 1 的事件
        query = AuditQuery(tenant_ids=["tenant-1"])
        events = await storage.query_events(query)

        assert len(events) == 3

    @pytest.mark.asyncio
    async def test_query_events_by_type(self, storage):
        """测试按类型查询事件"""
        # 创建不同类型的事件
        await storage.save_event(AuditEvent(
            event_id="event-1",
            event_type=AuditEventType.API_CALL,
            action="api_call",
        ))
        await storage.save_event(AuditEvent(
            event_id="event-2",
            event_type=AuditEventType.AUTH_FAILURE,
            action="login",
        ))

        # 查询 API 调用事件
        query = AuditQuery(event_types=[AuditEventType.API_CALL])
        events = await storage.query_events(query)

        assert len(events) == 1
        assert events[0].event_type == AuditEventType.API_CALL

    @pytest.mark.asyncio
    async def test_count_events(self, storage):
        """测试统计事件数量"""
        for i in range(10):
            await storage.save_event(AuditEvent(
                event_id=f"event-{i}",
                event_type=AuditEventType.API_CALL,
                action=f"action_{i}",
            ))

        query = AuditQuery()
        count = await storage.count_events(query)

        assert count == 10

    @pytest.mark.asyncio
    async def test_get_event_stats(self, storage):
        """测试获取事件统计"""
        # 创建不同类型和结果的事件
        await storage.save_event(AuditEvent(
            event_id="event-1",
            event_type=AuditEventType.API_CALL,
            action="api_call",
            result=AuditResult.SUCCESS,
        ))
        await storage.save_event(AuditEvent(
            event_id="event-2",
            event_type=AuditEventType.AUTH_FAILURE,
            action="login",
            result=AuditResult.FAILURE,
        ))

        stats = await storage.get_event_stats()

        assert stats.total_events == 2
        assert stats.success_events == 1
        assert stats.failure_events == 1

    @pytest.mark.asyncio
    async def test_save_and_get_policy_evaluation(self, storage):
        """测试保存和获取策略评估"""
        evaluation = PolicyEvaluation(
            evaluation_id="eval-1",
            tenant_id="tenant-1",
            action="read",
            resource_type="document",
            result=PolicyEvaluationResult.ALLOW,
        )

        await storage.save_policy_evaluation(evaluation)
        retrieved = await storage.get_policy_evaluation("eval-1")

        assert retrieved is not None
        assert retrieved.evaluation_id == "eval-1"
        assert retrieved.result == PolicyEvaluationResult.ALLOW

    @pytest.mark.asyncio
    async def test_query_policy_evaluations(self, storage):
        """测试查询策略评估"""
        for i in range(5):
            await storage.save_policy_evaluation(PolicyEvaluation(
                evaluation_id=f"eval-{i}",
                tenant_id="tenant-1",
                action="read",
                resource_type="document",
                result=PolicyEvaluationResult.ALLOW if i < 3 else PolicyEvaluationResult.DENY,
            ))

        # 查询允许的评估
        query = PolicyEvaluationQuery(results=[PolicyEvaluationResult.ALLOW])
        evaluations = await storage.query_policy_evaluations(query)

        assert len(evaluations) == 3


# ============================================================================
# 记录器测试
# ============================================================================


class TestAuditLogger:
    """审计日志记录器测试"""

    @pytest.mark.asyncio
    async def test_log_event(self, logger):
        """测试记录事件"""
        event = await logger.log_event(
            event_type=AuditEventType.API_CALL,
            action="test_action",
            tenant_id="tenant-1",
            user_id="user-1",
        )

        assert event.event_id is not None
        assert event.event_type == AuditEventType.API_CALL
        assert event.action == "test_action"

    @pytest.mark.asyncio
    async def test_log_api_call(self, logger):
        """测试记录 API 调用"""
        event = await logger.log_api_call(
            action="get_user",
            tenant_id="tenant-1",
            request_method="GET",
            request_path="/api/users/1",
            response_status=200,
            response_time_ms=50.0,
        )

        assert event.event_type == AuditEventType.API_CALL
        assert event.request_method == "GET"
        assert event.response_status == 200

    @pytest.mark.asyncio
    async def test_log_config_change(self, logger):
        """测试记录配置变更"""
        event = await logger.log_config_change(
            action="update_config",
            tenant_id="tenant-1",
            config_type="system",
            old_value={"key": "old"},
            new_value={"key": "new"},
        )

        assert event.event_type == AuditEventType.CONFIG_UPDATE
        assert event.old_value == {"key": "old"}
        assert event.new_value == {"key": "new"}

    @pytest.mark.asyncio
    async def test_log_permission_change(self, logger):
        """测试记录权限变更"""
        event = await logger.log_permission_change(
            action="grant_permission",
            tenant_id="tenant-1",
            user_id="admin-1",
            target_user_id="user-1",
            permission="read",
        )

        assert event.event_type == AuditEventType.PERMISSION_GRANT
        assert event.severity == AuditSeverity.WARNING

    @pytest.mark.asyncio
    async def test_log_security_event(self, logger):
        """测试记录安全事件"""
        event = await logger.log_security_event(
            action="login_failed",
            event_type=AuditEventType.AUTH_FAILURE,
            tenant_id="tenant-1",
            user_id="user-1",
            client_ip="192.168.1.1",
            result=AuditResult.FAILURE,
        )

        assert event.event_type == AuditEventType.AUTH_FAILURE
        assert event.result == AuditResult.FAILURE

    @pytest.mark.asyncio
    async def test_log_policy_evaluation(self, logger):
        """测试记录策略评估"""
        evaluation = await logger.log_policy_evaluation(
            action="read",
            resource_type="document",
            result=PolicyEvaluationResult.ALLOW,
            tenant_id="tenant-1",
            user_id="user-1",
            matched_policies=["policy-1"],
        )

        assert evaluation.evaluation_id is not None
        assert evaluation.result == PolicyEvaluationResult.ALLOW


# ============================================================================
# 策略追踪器测试
# ============================================================================


class TestPolicyTracker:
    """策略追踪器测试"""

    @pytest.mark.asyncio
    async def test_track_evaluation(self, tracker):
        """测试追踪评估"""
        evaluation = PolicyEvaluation(
            evaluation_id="eval-1",
            tenant_id="tenant-1",
            action="read",
            resource_type="document",
            result=PolicyEvaluationResult.ALLOW,
        )

        await tracker.track_evaluation(evaluation)
        retrieved = await tracker.get_evaluation("eval-1")

        assert retrieved is not None
        assert retrieved.evaluation_id == "eval-1"

    @pytest.mark.asyncio
    async def test_get_evaluation_history(self, tracker):
        """测试获取评估历史"""
        for i in range(5):
            await tracker.track_evaluation(PolicyEvaluation(
                evaluation_id=f"eval-{i}",
                tenant_id="tenant-1",
                action="read",
                resource_type="document",
                result=PolicyEvaluationResult.ALLOW,
            ))

        history = await tracker.get_evaluation_history(tenant_id="tenant-1")

        assert len(history) == 5

    @pytest.mark.asyncio
    async def test_get_denial_reasons(self, tracker):
        """测试获取拒绝原因"""
        # 创建一些拒绝的评估
        for i in range(3):
            await tracker.track_evaluation(PolicyEvaluation(
                evaluation_id=f"eval-{i}",
                tenant_id="tenant-1",
                action="write",
                resource_type="document",
                result=PolicyEvaluationResult.DENY,
                denial_code="PERMISSION_DENIED",
            ))

        reasons = await tracker.get_denial_reasons(tenant_id="tenant-1")

        assert "PERMISSION_DENIED" in reasons
        assert reasons["PERMISSION_DENIED"] == 3

    @pytest.mark.asyncio
    async def test_get_policy_hit_stats(self, tracker):
        """测试获取策略命中统计"""
        for i in range(5):
            await tracker.track_evaluation(PolicyEvaluation(
                evaluation_id=f"eval-{i}",
                tenant_id="tenant-1",
                action="read",
                resource_type="document",
                result=PolicyEvaluationResult.ALLOW,
                matched_policies=["policy-1"] if i < 3 else ["policy-2"],
            ))

        stats = await tracker.get_policy_hit_stats(tenant_id="tenant-1")

        assert "policy-1" in stats
        assert stats["policy-1"] == 3

    @pytest.mark.asyncio
    async def test_get_stats(self, tracker):
        """测试获取统计"""
        for i in range(5):
            await tracker.track_evaluation(PolicyEvaluation(
                evaluation_id=f"eval-{i}",
                tenant_id="tenant-1",
                action="read",
                resource_type="document",
                result=PolicyEvaluationResult.ALLOW if i < 3 else PolicyEvaluationResult.DENY,
            ))

        stats = await tracker.get_stats(tenant_id="tenant-1")

        assert stats.total_evaluations == 5
        assert stats.allow_count == 3
        assert stats.deny_count == 2


# ============================================================================
# 报告生成器测试
# ============================================================================


class TestReportGenerator:
    """报告生成器测试"""

    @pytest.mark.asyncio
    async def test_generate_usage_report(self, generator, storage):
        """测试生成使用量报告"""
        # 创建一些事件
        for i in range(10):
            await storage.save_event(AuditEvent(
                event_id=f"event-{i}",
                event_type=AuditEventType.API_CALL,
                action=f"action_{i}",
                result=AuditResult.SUCCESS,
            ))

        report = await generator.generate_usage_report()

        assert report.report_type == ReportType.USAGE
        assert report.status == ReportStatus.COMPLETED
        assert report.content["overview"]["total_events"] == 10

    @pytest.mark.asyncio
    async def test_generate_security_report(self, generator, storage):
        """测试生成安全审计报告"""
        # 创建一些安全事件
        await storage.save_event(AuditEvent(
            event_id="event-1",
            event_type=AuditEventType.AUTH_FAILURE,
            action="login",
            result=AuditResult.FAILURE,
        ))
        await storage.save_event(AuditEvent(
            event_id="event-2",
            event_type=AuditEventType.ACCESS_DENIED,
            action="access",
            result=AuditResult.DENIED,
        ))

        report = await generator.generate_security_audit_report()

        assert report.report_type == ReportType.SECURITY_AUDIT
        assert report.status == ReportStatus.COMPLETED
        assert len(report.compliance_checks) > 0

    @pytest.mark.asyncio
    async def test_generate_compliance_report(self, generator, storage):
        """测试生成合规检查报告"""
        # 创建一些事件
        for i in range(5):
            await storage.save_event(AuditEvent(
                event_id=f"event-{i}",
                event_type=AuditEventType.API_CALL,
                action=f"action_{i}",
                result=AuditResult.SUCCESS,
            ))

        report = await generator.generate_compliance_report()

        assert report.report_type == ReportType.COMPLIANCE
        assert report.status == ReportStatus.COMPLETED
        assert report.passed_checks >= 0

    @pytest.mark.asyncio
    async def test_format_report_json(self, generator, storage):
        """测试 JSON 格式化报告"""
        report = await generator.generate_usage_report()
        content = generator.format_report(report, ReportFormat.JSON)

        assert content is not None
        assert "report_id" in content

    @pytest.mark.asyncio
    async def test_format_report_markdown(self, generator, storage):
        """测试 Markdown 格式化报告"""
        report = await generator.generate_usage_report()
        content = generator.format_report(report, ReportFormat.MARKDOWN)

        assert content is not None
        assert "# 使用量报告" in content
