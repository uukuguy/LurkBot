"""告警 API 集成测试"""

from datetime import datetime

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from lurkbot.tenants.alerts import (
    AlertEngine,
    AlertSeverity,
    AlertStatus,
    AlertType,
    MemoryAlertStorage,
    configure_alert_engine,
    create_alert_router,
)
from lurkbot.tenants.models import Tenant, TenantQuota, TenantTier
from lurkbot.tenants.quota import QuotaManager
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
    """创建并配置告警引擎"""
    engine = configure_alert_engine(
        tenant_storage=tenant_storage,
        quota_manager=quota_manager,
        alert_storage=alert_storage,
    )
    return engine


@pytest.fixture
def app(alert_engine: AlertEngine) -> FastAPI:
    """创建 FastAPI 应用"""
    app = FastAPI()
    router = create_alert_router()
    app.include_router(router)
    return app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """创建测试客户端"""
    return TestClient(app)


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
        ),
    )
    await tenant_storage.create(tenant)
    return tenant


# ============================================================================
# 告警列表 API 测试
# ============================================================================


class TestAlertListAPI:
    """告警列表 API 测试"""

    def test_list_alerts_empty(self, client: TestClient):
        """测试空告警列表"""
        response = client.get("/api/v1/alerts")

        assert response.status_code == 200
        data = response.json()
        assert data["alerts"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_list_alerts_with_data(
        self,
        client: TestClient,
        alert_engine: AlertEngine,
        test_tenant: Tenant,
    ):
        """测试有数据的告警列表"""
        # 创建告警
        await alert_engine.trigger_alert(
            tenant_id=test_tenant.id,
            alert_type=AlertType.QUOTA_WARNING,
            severity=AlertSeverity.WARNING,
            title="测试告警",
            message="测试消息",
        )

        response = client.get("/api/v1/alerts")

        assert response.status_code == 200
        data = response.json()
        assert len(data["alerts"]) == 1
        assert data["total"] == 1

    @pytest.mark.asyncio
    async def test_list_alerts_with_filters(
        self,
        client: TestClient,
        alert_engine: AlertEngine,
        test_tenant: Tenant,
    ):
        """测试带过滤条件的告警列表"""
        # 创建不同级别的告警
        await alert_engine.trigger_alert(
            tenant_id=test_tenant.id,
            alert_type=AlertType.QUOTA_WARNING,
            severity=AlertSeverity.WARNING,
            title="警告",
            message="消息",
        )
        await alert_engine.trigger_alert(
            tenant_id=test_tenant.id,
            alert_type=AlertType.QUOTA_EXCEEDED,
            severity=AlertSeverity.ERROR,
            title="错误",
            message="消息",
        )

        # 按级别过滤
        response = client.get("/api/v1/alerts?severity=warning")
        assert response.status_code == 200
        data = response.json()
        assert len(data["alerts"]) == 1
        assert data["alerts"][0]["severity"] == "warning"

    def test_list_active_alerts(self, client: TestClient):
        """测试活跃告警列表"""
        response = client.get("/api/v1/alerts/active")

        assert response.status_code == 200
        data = response.json()
        assert "alerts" in data


# ============================================================================
# 告警详情 API 测试
# ============================================================================


class TestAlertDetailAPI:
    """告警详情 API 测试"""

    @pytest.mark.asyncio
    async def test_get_alert(
        self,
        client: TestClient,
        alert_engine: AlertEngine,
        test_tenant: Tenant,
    ):
        """测试获取告警详情"""
        alert = await alert_engine.trigger_alert(
            tenant_id=test_tenant.id,
            alert_type=AlertType.QUOTA_WARNING,
            severity=AlertSeverity.WARNING,
            title="测试告警",
            message="测试消息",
        )

        response = client.get(f"/api/v1/alerts/{alert.alert_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["alert"]["alert_id"] == alert.alert_id
        assert data["alert"]["title"] == "测试告警"

    def test_get_alert_not_found(self, client: TestClient):
        """测试获取不存在的告警"""
        response = client.get("/api/v1/alerts/non-existent")

        assert response.status_code == 404


# ============================================================================
# 告警操作 API 测试
# ============================================================================


class TestAlertOperationsAPI:
    """告警操作 API 测试"""

    @pytest.mark.asyncio
    async def test_resolve_alert(
        self,
        client: TestClient,
        alert_engine: AlertEngine,
        test_tenant: Tenant,
    ):
        """测试解决告警"""
        alert = await alert_engine.trigger_alert(
            tenant_id=test_tenant.id,
            alert_type=AlertType.QUOTA_WARNING,
            severity=AlertSeverity.WARNING,
            title="测试告警",
            message="测试消息",
        )

        response = client.post(
            f"/api/v1/alerts/{alert.alert_id}/resolve",
            json={"resolved_by": "admin", "note": "已修复"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["alert"]["status"] == "resolved"
        assert data["alert"]["resolved_by"] == "admin"

    @pytest.mark.asyncio
    async def test_acknowledge_alert(
        self,
        client: TestClient,
        alert_engine: AlertEngine,
        test_tenant: Tenant,
    ):
        """测试确认告警"""
        alert = await alert_engine.trigger_alert(
            tenant_id=test_tenant.id,
            alert_type=AlertType.QUOTA_WARNING,
            severity=AlertSeverity.WARNING,
            title="测试告警",
            message="测试消息",
        )

        response = client.post(
            f"/api/v1/alerts/{alert.alert_id}/acknowledge",
            json={"acknowledged_by": "operator"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["alert"]["status"] == "acknowledged"

    @pytest.mark.asyncio
    async def test_suppress_alert(
        self,
        client: TestClient,
        alert_engine: AlertEngine,
        test_tenant: Tenant,
    ):
        """测试抑制告警"""
        alert = await alert_engine.trigger_alert(
            tenant_id=test_tenant.id,
            alert_type=AlertType.QUOTA_WARNING,
            severity=AlertSeverity.WARNING,
            title="测试告警",
            message="测试消息",
        )

        response = client.post(
            f"/api/v1/alerts/{alert.alert_id}/suppress",
            json={"duration_seconds": 3600},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["alert"]["status"] == "suppressed"
        assert data["alert"]["suppressed_until"] is not None


# ============================================================================
# 租户告警 API 测试
# ============================================================================


class TestTenantAlertAPI:
    """租户告警 API 测试"""

    @pytest.mark.asyncio
    async def test_list_tenant_alerts(
        self,
        client: TestClient,
        alert_engine: AlertEngine,
        test_tenant: Tenant,
    ):
        """测试获取租户告警列表"""
        await alert_engine.trigger_alert(
            tenant_id=test_tenant.id,
            alert_type=AlertType.QUOTA_WARNING,
            severity=AlertSeverity.WARNING,
            title="测试告警",
            message="测试消息",
        )

        response = client.get(f"/api/v1/alerts/tenants/{test_tenant.id}")

        assert response.status_code == 200
        data = response.json()
        assert len(data["alerts"]) == 1

    @pytest.mark.asyncio
    async def test_get_tenant_alert_stats(
        self,
        client: TestClient,
        alert_engine: AlertEngine,
        test_tenant: Tenant,
    ):
        """测试获取租户告警统计"""
        await alert_engine.trigger_alert(
            tenant_id=test_tenant.id,
            alert_type=AlertType.QUOTA_WARNING,
            severity=AlertSeverity.WARNING,
            title="测试告警",
            message="测试消息",
        )

        response = client.get(f"/api/v1/alerts/tenants/{test_tenant.id}/stats")

        assert response.status_code == 200
        data = response.json()
        assert data["stats"]["total_alerts"] == 1

    @pytest.mark.asyncio
    async def test_trigger_tenant_alert(
        self,
        client: TestClient,
        test_tenant: Tenant,
    ):
        """测试手动触发租户告警"""
        response = client.post(
            f"/api/v1/alerts/tenants/{test_tenant.id}/trigger",
            json={
                "alert_type": "system_warning",
                "severity": "warning",
                "title": "手动告警",
                "message": "这是手动触发的告警",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["alert"]["title"] == "手动告警"
        assert data["alert"]["tenant_id"] == test_tenant.id

    @pytest.mark.asyncio
    async def test_check_tenant_alerts(
        self,
        client: TestClient,
        test_tenant: Tenant,
    ):
        """测试检查租户告警"""
        response = client.post(f"/api/v1/alerts/tenants/{test_tenant.id}/check")

        assert response.status_code == 200
        data = response.json()
        assert "alerts" in data


# ============================================================================
# 规则管理 API 测试
# ============================================================================


class TestRuleAPI:
    """规则管理 API 测试"""

    def test_list_rules(self, client: TestClient):
        """测试获取规则列表"""
        response = client.get("/api/v1/alerts/rules")

        assert response.status_code == 200
        data = response.json()
        assert len(data["rules"]) > 0
        assert data["total"] > 0

    def test_list_enabled_rules(self, client: TestClient):
        """测试获取启用的规则列表"""
        response = client.get("/api/v1/alerts/rules?enabled_only=true")

        assert response.status_code == 200
        data = response.json()
        # 所有返回的规则都应该是启用的
        for rule in data["rules"]:
            assert rule["enabled"] is True

    def test_get_rule(self, client: TestClient):
        """测试获取规则详情"""
        # 先获取规则列表
        list_response = client.get("/api/v1/alerts/rules")
        rules = list_response.json()["rules"]
        rule_id = rules[0]["rule_id"]

        response = client.get(f"/api/v1/alerts/rules/{rule_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["rule_id"] == rule_id

    def test_get_rule_not_found(self, client: TestClient):
        """测试获取不存在的规则"""
        response = client.get("/api/v1/alerts/rules/non-existent")

        assert response.status_code == 404

    def test_disable_rule(self, client: TestClient):
        """测试禁用规则"""
        # 先获取规则列表
        list_response = client.get("/api/v1/alerts/rules")
        rules = list_response.json()["rules"]
        rule_id = rules[0]["rule_id"]

        response = client.post(f"/api/v1/alerts/rules/{rule_id}/disable")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # 验证规则已禁用
        rule_response = client.get(f"/api/v1/alerts/rules/{rule_id}")
        assert rule_response.json()["enabled"] is False

    def test_enable_rule(self, client: TestClient):
        """测试启用规则"""
        # 先获取规则列表并禁用一个
        list_response = client.get("/api/v1/alerts/rules")
        rules = list_response.json()["rules"]
        rule_id = rules[0]["rule_id"]

        client.post(f"/api/v1/alerts/rules/{rule_id}/disable")

        # 启用规则
        response = client.post(f"/api/v1/alerts/rules/{rule_id}/enable")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # 验证规则已启用
        rule_response = client.get(f"/api/v1/alerts/rules/{rule_id}")
        assert rule_response.json()["enabled"] is True

    def test_update_rule(self, client: TestClient):
        """测试更新规则"""
        # 先获取规则列表
        list_response = client.get("/api/v1/alerts/rules")
        rules = list_response.json()["rules"]
        rule_id = rules[0]["rule_id"]

        response = client.patch(
            f"/api/v1/alerts/rules/{rule_id}",
            json={"threshold": 0.9},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_get_rules_stats(self, client: TestClient):
        """测试获取规则统计"""
        response = client.get("/api/v1/alerts/rules/stats/summary")

        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "enabled" in data
        assert "disabled" in data


# ============================================================================
# 告警统计 API 测试
# ============================================================================


class TestAlertStatsAPI:
    """告警统计 API 测试"""

    def test_get_stats_empty(self, client: TestClient):
        """测试空统计"""
        response = client.get("/api/v1/alerts/stats")

        assert response.status_code == 200
        data = response.json()
        assert data["stats"]["total_alerts"] == 0

    @pytest.mark.asyncio
    async def test_get_stats_with_data(
        self,
        client: TestClient,
        alert_engine: AlertEngine,
        test_tenant: Tenant,
    ):
        """测试有数据的统计"""
        # 创建告警
        await alert_engine.trigger_alert(
            tenant_id=test_tenant.id,
            alert_type=AlertType.QUOTA_WARNING,
            severity=AlertSeverity.WARNING,
            title="警告",
            message="消息",
        )
        await alert_engine.trigger_alert(
            tenant_id=test_tenant.id,
            alert_type=AlertType.QUOTA_EXCEEDED,
            severity=AlertSeverity.ERROR,
            title="错误",
            message="消息",
        )

        response = client.get("/api/v1/alerts/stats")

        assert response.status_code == 200
        data = response.json()
        assert data["stats"]["total_alerts"] == 2
        assert data["stats"]["active_alerts"] == 2
