"""告警系统单元测试"""

from datetime import datetime, timedelta

import pytest

from lurkbot.tenants.alerts import (
    Alert,
    AlertCondition,
    AlertEngine,
    AlertRule,
    AlertSeverity,
    AlertStats,
    AlertStatus,
    AlertType,
    ConditionOperator,
    MemoryAlertStorage,
    NotificationChannel,
    NotificationService,
    RuleManager,
    SystemEventChannel,
    create_default_rules,
)
from lurkbot.tenants.models import Tenant, TenantQuota, TenantTier
from lurkbot.tenants.quota import QuotaManager, QuotaType
from lurkbot.tenants.storage import MemoryTenantStorage


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def tenant_storage() -> MemoryTenantStorage:
    """创建租户存储"""
    return MemoryTenantStorage()


@pytest.fixture
def quota_manager() -> QuotaManager:
    """创建配额管理器"""
    return QuotaManager()


@pytest.fixture
def alert_storage() -> MemoryAlertStorage:
    """创建告警存储"""
    return MemoryAlertStorage()


@pytest.fixture
def alert_engine(
    tenant_storage: MemoryTenantStorage,
    quota_manager: QuotaManager,
    alert_storage: MemoryAlertStorage,
) -> AlertEngine:
    """创建告警引擎"""
    return AlertEngine(
        tenant_storage=tenant_storage,
        quota_manager=quota_manager,
        alert_storage=alert_storage,
    )


@pytest.fixture
async def test_tenant(tenant_storage: MemoryTenantStorage) -> Tenant:
    """创建测试租户"""
    tenant = Tenant(
        id="test-tenant-1",
        name="test_tenant",
        display_name="Test Tenant",
        tier=TenantTier.BASIC,
        quota=TenantQuota(
            max_tokens_per_day=1000,
            max_api_calls_per_minute=10,
            max_api_calls_per_day=100,
            max_concurrent_requests=5,
        ),
    )
    await tenant_storage.create(tenant)
    return tenant


# ============================================================================
# 数据模型测试
# ============================================================================


class TestAlertModels:
    """告警数据模型测试"""

    def test_alert_creation(self):
        """测试告警创建"""
        alert = Alert(
            alert_id="alert-1",
            rule_id="rule-1",
            tenant_id="tenant-1",
            alert_type=AlertType.QUOTA_WARNING,
            severity=AlertSeverity.WARNING,
            title="配额警告",
            message="Token 使用量已达到 80%",
        )

        assert alert.alert_id == "alert-1"
        assert alert.status == AlertStatus.ACTIVE
        assert alert.is_active()
        assert not alert.is_suppressed()

    def test_alert_condition(self):
        """测试告警条件"""
        condition = AlertCondition(
            condition_type="threshold",
            metric="quota_percentage",
            quota_type=QuotaType.TOKENS_PER_DAY,
            operator=ConditionOperator.GTE,
            threshold=0.8,
        )

        assert condition.threshold == 0.8
        assert condition.operator == ConditionOperator.GTE

    def test_alert_rule(self):
        """测试告警规则"""
        rule = AlertRule(
            rule_id="test-rule",
            name="测试规则",
            alert_type=AlertType.QUOTA_WARNING,
            severity=AlertSeverity.WARNING,
            condition=AlertCondition(
                condition_type="threshold",
                metric="quota_percentage",
                threshold=0.8,
            ),
            throttle_seconds=300,
        )

        assert rule.enabled
        assert rule.throttle_seconds == 300


# ============================================================================
# 规则管理器测试
# ============================================================================


class TestRuleManager:
    """规则管理器测试"""

    def test_default_rules_loaded(self):
        """测试默认规则加载"""
        manager = RuleManager()
        rules = manager.get_all_rules()

        # 应该有配额警告、配额超限、速率限制等规则
        assert len(rules) > 0

        # 检查配额警告规则
        quota_warning_rules = manager.get_rules_by_type(AlertType.QUOTA_WARNING)
        assert len(quota_warning_rules) > 0

    def test_add_and_remove_rule(self):
        """测试添加和移除规则"""
        manager = RuleManager()
        initial_count = len(manager.get_all_rules())

        # 添加规则
        rule = AlertRule(
            rule_id="custom-rule",
            name="自定义规则",
            alert_type=AlertType.SYSTEM_WARNING,
            severity=AlertSeverity.WARNING,
            condition=AlertCondition(
                condition_type="threshold",
                metric="custom_metric",
                threshold=0.9,
            ),
        )
        manager.add_rule(rule)

        assert len(manager.get_all_rules()) == initial_count + 1
        assert manager.get_rule("custom-rule") is not None

        # 移除规则
        manager.remove_rule("custom-rule")
        assert len(manager.get_all_rules()) == initial_count
        assert manager.get_rule("custom-rule") is None

    def test_enable_disable_rule(self):
        """测试启用/禁用规则"""
        manager = RuleManager()
        rules = manager.get_all_rules()
        rule_id = rules[0].rule_id

        # 禁用规则
        manager.disable_rule(rule_id)
        rule = manager.get_rule(rule_id)
        assert not rule.enabled

        # 启用规则
        manager.enable_rule(rule_id)
        rule = manager.get_rule(rule_id)
        assert rule.enabled

    def test_get_rules_for_tenant(self):
        """测试获取租户适用规则"""
        manager = RuleManager()

        # 添加租户特定规则
        rule = AlertRule(
            rule_id="tenant-specific",
            name="租户特定规则",
            alert_type=AlertType.SYSTEM_WARNING,
            severity=AlertSeverity.WARNING,
            condition=AlertCondition(
                condition_type="threshold",
                metric="custom",
                threshold=0.5,
            ),
            tenant_ids=["tenant-1"],
        )
        manager.add_rule(rule)

        # tenant-1 应该能获取到该规则
        rules_for_tenant1 = manager.get_rules_for_tenant("tenant-1")
        assert any(r.rule_id == "tenant-specific" for r in rules_for_tenant1)

        # tenant-2 不应该获取到该规则
        rules_for_tenant2 = manager.get_rules_for_tenant("tenant-2")
        assert not any(r.rule_id == "tenant-specific" for r in rules_for_tenant2)


# ============================================================================
# 告警存储测试
# ============================================================================


class TestAlertStorage:
    """告警存储测试"""

    @pytest.mark.asyncio
    async def test_save_and_get_alert(self, alert_storage: MemoryAlertStorage):
        """测试保存和获取告警"""
        alert = Alert(
            alert_id="alert-1",
            rule_id="rule-1",
            tenant_id="tenant-1",
            alert_type=AlertType.QUOTA_WARNING,
            severity=AlertSeverity.WARNING,
            title="测试告警",
            message="测试消息",
        )

        await alert_storage.save_alert(alert)
        retrieved = await alert_storage.get_alert("alert-1")

        assert retrieved is not None
        assert retrieved.alert_id == "alert-1"
        assert retrieved.title == "测试告警"

    @pytest.mark.asyncio
    async def test_list_alerts_with_filters(self, alert_storage: MemoryAlertStorage):
        """测试带过滤条件的告警列表"""
        # 创建多个告警
        for i in range(5):
            alert = Alert(
                alert_id=f"alert-{i}",
                rule_id="rule-1",
                tenant_id="tenant-1" if i < 3 else "tenant-2",
                alert_type=AlertType.QUOTA_WARNING,
                severity=AlertSeverity.WARNING if i < 2 else AlertSeverity.ERROR,
                title=f"告警 {i}",
                message=f"消息 {i}",
            )
            await alert_storage.save_alert(alert)

        # 按租户过滤
        tenant1_alerts = await alert_storage.list_alerts(tenant_id="tenant-1")
        assert len(tenant1_alerts) == 3

        # 按级别过滤
        error_alerts = await alert_storage.list_alerts(severity=AlertSeverity.ERROR)
        assert len(error_alerts) == 3

    @pytest.mark.asyncio
    async def test_update_alert(self, alert_storage: MemoryAlertStorage):
        """测试更新告警"""
        alert = Alert(
            alert_id="alert-1",
            rule_id="rule-1",
            tenant_id="tenant-1",
            alert_type=AlertType.QUOTA_WARNING,
            severity=AlertSeverity.WARNING,
            title="测试告警",
            message="测试消息",
        )

        await alert_storage.save_alert(alert)

        # 更新状态
        alert.status = AlertStatus.RESOLVED
        alert.resolved_at = datetime.now()
        await alert_storage.update_alert(alert)

        retrieved = await alert_storage.get_alert("alert-1")
        assert retrieved.status == AlertStatus.RESOLVED
        assert retrieved.resolved_at is not None

    @pytest.mark.asyncio
    async def test_get_active_alerts(self, alert_storage: MemoryAlertStorage):
        """测试获取活跃告警"""
        # 创建活跃和已解决的告警
        active_alert = Alert(
            alert_id="active-1",
            rule_id="rule-1",
            tenant_id="tenant-1",
            alert_type=AlertType.QUOTA_WARNING,
            severity=AlertSeverity.WARNING,
            title="活跃告警",
            message="消息",
            status=AlertStatus.ACTIVE,
        )

        resolved_alert = Alert(
            alert_id="resolved-1",
            rule_id="rule-1",
            tenant_id="tenant-1",
            alert_type=AlertType.QUOTA_WARNING,
            severity=AlertSeverity.WARNING,
            title="已解决告警",
            message="消息",
            status=AlertStatus.RESOLVED,
        )

        await alert_storage.save_alert(active_alert)
        await alert_storage.save_alert(resolved_alert)

        active_alerts = await alert_storage.get_active_alerts()
        assert len(active_alerts) == 1
        assert active_alerts[0].alert_id == "active-1"

    @pytest.mark.asyncio
    async def test_get_stats(self, alert_storage: MemoryAlertStorage):
        """测试获取告警统计"""
        # 创建不同状态和级别的告警
        alerts = [
            Alert(
                alert_id="alert-1",
                rule_id="rule-1",
                tenant_id="tenant-1",
                alert_type=AlertType.QUOTA_WARNING,
                severity=AlertSeverity.WARNING,
                title="警告",
                message="消息",
                status=AlertStatus.ACTIVE,
            ),
            Alert(
                alert_id="alert-2",
                rule_id="rule-1",
                tenant_id="tenant-1",
                alert_type=AlertType.QUOTA_EXCEEDED,
                severity=AlertSeverity.ERROR,
                title="错误",
                message="消息",
                status=AlertStatus.RESOLVED,
                resolved_at=datetime.now(),
            ),
        ]

        for alert in alerts:
            await alert_storage.save_alert(alert)

        stats = await alert_storage.get_stats()

        assert stats.total_alerts == 2
        assert stats.active_alerts == 1
        assert stats.resolved_alerts == 1
        assert stats.by_severity.get("warning", 0) == 1
        assert stats.by_severity.get("error", 0) == 1


# ============================================================================
# 告警引擎测试
# ============================================================================


class TestAlertEngine:
    """告警引擎测试"""

    @pytest.mark.asyncio
    async def test_trigger_alert(
        self,
        alert_engine: AlertEngine,
        test_tenant: Tenant,
    ):
        """测试触发告警"""
        alert = await alert_engine.trigger_alert(
            tenant_id=test_tenant.id,
            alert_type=AlertType.SYSTEM_WARNING,
            severity=AlertSeverity.WARNING,
            title="测试告警",
            message="这是一个测试告警",
        )

        assert alert is not None
        assert alert.tenant_id == test_tenant.id
        assert alert.alert_type == AlertType.SYSTEM_WARNING

        # 验证告警已保存
        saved = await alert_engine.get_alert(alert.alert_id)
        assert saved is not None

    @pytest.mark.asyncio
    async def test_resolve_alert(
        self,
        alert_engine: AlertEngine,
        test_tenant: Tenant,
    ):
        """测试解决告警"""
        # 创建告警
        alert = await alert_engine.trigger_alert(
            tenant_id=test_tenant.id,
            alert_type=AlertType.SYSTEM_WARNING,
            severity=AlertSeverity.WARNING,
            title="测试告警",
            message="消息",
        )

        # 解决告警
        resolved = await alert_engine.resolve_alert(
            alert_id=alert.alert_id,
            resolved_by="admin",
            note="问题已修复",
        )

        assert resolved is not None
        assert resolved.status == AlertStatus.RESOLVED
        assert resolved.resolved_by == "admin"
        assert resolved.resolution_note == "问题已修复"

    @pytest.mark.asyncio
    async def test_suppress_alert(
        self,
        alert_engine: AlertEngine,
        test_tenant: Tenant,
    ):
        """测试抑制告警"""
        # 创建告警
        alert = await alert_engine.trigger_alert(
            tenant_id=test_tenant.id,
            alert_type=AlertType.SYSTEM_WARNING,
            severity=AlertSeverity.WARNING,
            title="测试告警",
            message="消息",
        )

        # 抑制告警
        suppressed = await alert_engine.suppress_alert(
            alert_id=alert.alert_id,
            duration_seconds=3600,
        )

        assert suppressed is not None
        assert suppressed.status == AlertStatus.SUPPRESSED
        assert suppressed.suppressed_until is not None

    @pytest.mark.asyncio
    async def test_check_and_trigger_quota_warning(
        self,
        alert_engine: AlertEngine,
        test_tenant: Tenant,
        quota_manager: QuotaManager,
    ):
        """测试配额警告触发"""
        # 记录使用量达到 85%
        await quota_manager.record_usage(
            test_tenant.id,
            QuotaType.TOKENS_PER_DAY,
            850,  # 85% of 1000
        )

        # 检查并触发告警
        alerts = await alert_engine.check_and_trigger(test_tenant.id)

        # 应该触发配额警告
        quota_warnings = [
            a for a in alerts if a.alert_type == AlertType.QUOTA_WARNING
        ]
        assert len(quota_warnings) > 0

    @pytest.mark.asyncio
    async def test_alert_throttling(
        self,
        alert_engine: AlertEngine,
        test_tenant: Tenant,
        quota_manager: QuotaManager,
    ):
        """测试告警节流"""
        # 记录使用量达到 85%
        await quota_manager.record_usage(
            test_tenant.id,
            QuotaType.TOKENS_PER_DAY,
            850,
        )

        # 第一次检查应该触发告警
        alerts1 = await alert_engine.check_and_trigger(test_tenant.id)
        quota_warnings1 = [
            a for a in alerts1 if a.alert_type == AlertType.QUOTA_WARNING
        ]

        # 第二次检查应该被节流
        alerts2 = await alert_engine.check_and_trigger(test_tenant.id)
        quota_warnings2 = [
            a for a in alerts2 if a.alert_type == AlertType.QUOTA_WARNING
        ]

        # 第二次应该没有新的配额警告（被节流）
        assert len(quota_warnings2) < len(quota_warnings1)


# ============================================================================
# 通知服务测试
# ============================================================================


class TestNotificationService:
    """通知服务测试"""

    def test_system_event_channel(self):
        """测试系统事件渠道"""
        channel = SystemEventChannel()

        assert channel.channel_type == NotificationChannel.SYSTEM_EVENT

    @pytest.mark.asyncio
    async def test_send_system_event(self):
        """测试发送系统事件"""
        channel = SystemEventChannel()

        alert = Alert(
            alert_id="alert-1",
            rule_id="rule-1",
            tenant_id="tenant-1",
            alert_type=AlertType.QUOTA_WARNING,
            severity=AlertSeverity.WARNING,
            title="测试告警",
            message="测试消息",
        )

        success = await channel.send(alert)
        assert success

        # 检查事件已记录
        events = channel.get_events("tenant-1")
        assert len(events) == 1
        assert events[0]["alert_id"] == "alert-1"

    @pytest.mark.asyncio
    async def test_notification_service(self):
        """测试通知服务"""
        service = NotificationService()

        # 默认应该有系统事件渠道
        channels = service.list_channels()
        assert NotificationChannel.SYSTEM_EVENT in channels

        # 发送通知
        alert = Alert(
            alert_id="alert-1",
            rule_id="rule-1",
            tenant_id="tenant-1",
            alert_type=AlertType.QUOTA_WARNING,
            severity=AlertSeverity.WARNING,
            title="测试告警",
            message="测试消息",
        )

        results = await service.send(alert)
        assert results[NotificationChannel.SYSTEM_EVENT] is True


# ============================================================================
# 默认规则测试
# ============================================================================


class TestDefaultRules:
    """默认规则测试"""

    def test_create_default_rules(self):
        """测试创建默认规则"""
        rules = create_default_rules()

        assert len(rules) > 0

        # 检查配额类型规则
        quota_types = [QuotaType.TOKENS_PER_DAY, QuotaType.API_CALLS_PER_DAY]
        for qt in quota_types:
            # 应该有警告规则
            warning_rule = next(
                (r for r in rules if r.rule_id == f"quota_warning_{qt.value}"),
                None,
            )
            assert warning_rule is not None
            assert warning_rule.condition.threshold == 0.8

            # 应该有超限规则
            exceeded_rule = next(
                (r for r in rules if r.rule_id == f"quota_exceeded_{qt.value}"),
                None,
            )
            assert exceeded_rule is not None
            assert exceeded_rule.condition.threshold == 1.0

    def test_rate_limit_rules(self):
        """测试速率限制规则"""
        rules = create_default_rules()

        # 检查速率限制警告规则
        rate_warning = next(
            (r for r in rules if r.rule_id == "rate_limit_warning"),
            None,
        )
        assert rate_warning is not None
        assert rate_warning.alert_type == AlertType.RATE_LIMIT_WARNING

        # 检查速率限制超限规则
        rate_exceeded = next(
            (r for r in rules if r.rule_id == "rate_limit_exceeded"),
            None,
        )
        assert rate_exceeded is not None
        assert rate_exceeded.alert_type == AlertType.RATE_LIMIT_EXCEEDED

    def test_concurrent_rules(self):
        """测试并发请求规则"""
        rules = create_default_rules()

        # 检查并发警告规则
        concurrent_warning = next(
            (r for r in rules if r.rule_id == "concurrent_warning"),
            None,
        )
        assert concurrent_warning is not None
        assert concurrent_warning.alert_type == AlertType.CONCURRENT_WARNING

        # 检查并发超限规则
        concurrent_exceeded = next(
            (r for r in rules if r.rule_id == "concurrent_exceeded"),
            None,
        )
        assert concurrent_exceeded is not None
        assert concurrent_exceeded.alert_type == AlertType.CONCURRENT_EXCEEDED
