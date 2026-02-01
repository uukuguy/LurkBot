"""租户统计 API 集成测试"""

from datetime import datetime, timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from lurkbot.tenants import (
    MemoryTenantStorage,
    QuotaManager,
    Tenant,
    TenantQuota,
    TenantStatus,
    TenantTier,
    TenantUsage,
)
from lurkbot.tenants.api import create_tenant_stats_router
from lurkbot.tenants.stats import configure_stats_service


# ============================================================================
# 测试夹具
# ============================================================================


@pytest.fixture
def storage():
    """内存存储实例"""
    return MemoryTenantStorage()


@pytest.fixture
def quota_manager():
    """配额管理器实例"""
    return QuotaManager()


@pytest.fixture
def app(storage, quota_manager):
    """FastAPI 应用实例"""
    # 配置统计服务
    configure_stats_service(storage, quota_manager)

    # 创建应用
    app = FastAPI()
    router = create_tenant_stats_router()
    app.include_router(router)

    return app


@pytest.fixture
def client(app):
    """测试客户端"""
    return TestClient(app)


@pytest.fixture
async def sample_tenant(storage):
    """示例租户"""
    tenant = Tenant(
        id="tenant-1",
        name="test-tenant",
        display_name="Test Tenant",
        tier=TenantTier.BASIC,
        status=TenantStatus.ACTIVE,
        quota=TenantQuota(
            max_agents=5,
            max_sessions=50,
            max_plugins=10,
            max_tokens_per_day=10000,
            max_api_calls_per_minute=30,
            max_api_calls_per_day=1000,
            max_concurrent_requests=5,
        ),
    )
    await storage.create(tenant)
    return tenant


@pytest.fixture
async def sample_usage_data(storage, sample_tenant):
    """示例使用数据"""
    usage_records = []
    for i in range(7):
        date = datetime.now() - timedelta(days=i)
        usage = TenantUsage(
            tenant_id=sample_tenant.id,
            period="daily",
            period_start=date.replace(hour=0, minute=0, second=0, microsecond=0),
            period_end=date.replace(hour=23, minute=59, second=59, microsecond=999999),
            input_tokens=1000 + i * 100,
            output_tokens=500 + i * 50,
            total_tokens=1500 + i * 150,
            api_calls=100 + i * 10,
            successful_calls=95 + i * 9,
            failed_calls=5 + i,
            sessions_created=10 + i,
            active_sessions=5 + i,
            messages_sent=50 + i * 5,
            storage_used_mb=10.0 + i * 0.5,
            estimated_cost=0.5 + i * 0.05,
        )
        await storage.record_usage(usage)
        usage_records.append(usage)
    return usage_records


# ============================================================================
# 租户统计端点测试
# ============================================================================


class TestTenantStatsEndpoint:
    """租户统计端点测试"""

    @pytest.mark.asyncio
    async def test_get_tenant_stats_not_found(self, client):
        """测试获取不存在的租户统计"""
        response = client.get("/api/v1/tenants/non-existent/stats")
        assert response.status_code == 404
        assert "租户不存在" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_tenant_stats_success(self, client, sample_tenant):
        """测试成功获取租户统计"""
        response = client.get(f"/api/v1/tenants/{sample_tenant.id}/stats")
        assert response.status_code == 200

        data = response.json()
        assert data["tenant_id"] == sample_tenant.id
        assert data["tenant_name"] == sample_tenant.name
        assert data["status"] == "active"
        assert data["tier"] == "basic"
        assert "quota_usage" in data
        assert "activity_score" in data


# ============================================================================
# 仪表板端点测试
# ============================================================================


class TestDashboardEndpoint:
    """仪表板端点测试"""

    @pytest.mark.asyncio
    async def test_get_dashboard_not_found(self, client):
        """测试获取不存在的租户仪表板"""
        response = client.get("/api/v1/tenants/non-existent/dashboard")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_dashboard_success(self, client, sample_tenant):
        """测试成功获取仪表板"""
        response = client.get(f"/api/v1/tenants/{sample_tenant.id}/dashboard")
        assert response.status_code == 200

        data = response.json()
        assert data["tenant_id"] == sample_tenant.id
        assert "overview" in data
        assert "realtime_usage" in data
        assert "usage_trends" in data
        assert "recent_events" in data
        assert "alerts" in data

    @pytest.mark.asyncio
    async def test_get_dashboard_with_trends(self, client, sample_tenant):
        """测试获取包含趋势的仪表板"""
        response = client.get(
            f"/api/v1/tenants/{sample_tenant.id}/dashboard",
            params={"include_trends": True, "trend_period": "daily", "trend_days": 7},
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_dashboard_without_trends(self, client, sample_tenant):
        """测试获取不包含趋势的仪表板"""
        response = client.get(
            f"/api/v1/tenants/{sample_tenant.id}/dashboard",
            params={"include_trends": False},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["usage_trends"]) == 0

    @pytest.mark.asyncio
    async def test_get_dashboard_invalid_period(self, client, sample_tenant):
        """测试无效的趋势周期"""
        response = client.get(
            f"/api/v1/tenants/{sample_tenant.id}/dashboard",
            params={"trend_period": "invalid"},
        )
        assert response.status_code == 400
        assert "无效的趋势周期" in response.json()["detail"]


# ============================================================================
# 实时使用量端点测试
# ============================================================================


class TestRealtimeUsageEndpoint:
    """实时使用量端点测试"""

    @pytest.mark.asyncio
    async def test_get_realtime_usage_not_found(self, client):
        """测试获取不存在的租户实时使用量"""
        response = client.get("/api/v1/tenants/non-existent/usage/realtime")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_realtime_usage_success(self, client, sample_tenant):
        """测试成功获取实时使用量"""
        response = client.get(f"/api/v1/tenants/{sample_tenant.id}/usage/realtime")
        assert response.status_code == 200

        data = response.json()
        assert data["tenant_id"] == sample_tenant.id
        assert "timestamp" in data
        assert "usage" in data


# ============================================================================
# 历史使用量端点测试
# ============================================================================


class TestHistoryUsageEndpoint:
    """历史使用量端点测试"""

    @pytest.mark.asyncio
    async def test_get_history_usage_success(self, client, sample_tenant):
        """测试成功获取历史使用量"""
        response = client.get(
            f"/api/v1/tenants/{sample_tenant.id}/usage/history",
            params={"period": "daily", "days": 30},
        )
        assert response.status_code == 200

        data = response.json()
        assert data["tenant_id"] == sample_tenant.id
        assert data["period"] == "daily"
        assert "data" in data

    @pytest.mark.asyncio
    async def test_get_history_usage_invalid_period(self, client, sample_tenant):
        """测试无效的统计周期"""
        response = client.get(
            f"/api/v1/tenants/{sample_tenant.id}/usage/history",
            params={"period": "invalid"},
        )
        assert response.status_code == 400


# ============================================================================
# 配额趋势端点测试
# ============================================================================


class TestQuotaTrendsEndpoint:
    """配额趋势端点测试"""

    @pytest.mark.asyncio
    async def test_get_quota_trends_success(self, client, sample_tenant):
        """测试成功获取配额趋势"""
        response = client.get(
            f"/api/v1/tenants/{sample_tenant.id}/quota/trends",
            params={"days": 30},
        )
        assert response.status_code == 200

        data = response.json()
        assert data["tenant_id"] == sample_tenant.id
        assert "trends" in data


# ============================================================================
# 系统概览端点测试
# ============================================================================


class TestSystemOverviewEndpoint:
    """系统概览端点测试"""

    @pytest.mark.asyncio
    async def test_get_system_overview_empty(self, client):
        """测试空系统概览"""
        response = client.get("/api/v1/tenants/overview")
        assert response.status_code == 200

        data = response.json()
        assert data["total_tenants"] == 0
        assert data["active_tenants"] == 0

    @pytest.mark.asyncio
    async def test_get_system_overview_with_tenants(
        self, client, storage, sample_tenant
    ):
        """测试有租户的系统概览"""
        # 创建更多租户
        tenant2 = Tenant(
            id="tenant-2",
            name="test-tenant-2",
            display_name="Test Tenant 2",
            tier=TenantTier.PROFESSIONAL,
            status=TenantStatus.ACTIVE,
        )
        await storage.create(tenant2)

        response = client.get("/api/v1/tenants/overview")
        assert response.status_code == 200

        data = response.json()
        assert data["total_tenants"] == 2
        assert data["active_tenants"] == 2
        assert "tier_distribution" in data
        assert "top_active_tenants" in data
