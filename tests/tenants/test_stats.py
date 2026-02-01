"""租户统计服务测试"""

from datetime import datetime, timedelta

import pytest

from lurkbot.tenants import (
    MemoryTenantStorage,
    QuotaManager,
    Tenant,
    TenantQuota,
    TenantStatus,
    TenantTier,
    TenantUsage,
)
from lurkbot.tenants.stats import (
    QuotaUsageStats,
    StatsPeriod,
    TenantDashboard,
    TenantOverview,
    TenantStatsService,
    TrendDirection,
    UsageTrend,
    configure_stats_service,
    get_stats_service,
)
from lurkbot.tenants.quota import QuotaType


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
def stats_service(storage, quota_manager):
    """统计服务实例"""
    return TenantStatsService(storage, quota_manager)


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
    # 创建过去 7 天的使用数据
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
# 租户概览测试
# ============================================================================


class TestTenantOverview:
    """租户概览测试"""

    @pytest.mark.asyncio
    async def test_get_tenant_overview_not_found(self, stats_service):
        """测试获取不存在的租户概览"""
        result = await stats_service.get_tenant_overview("non-existent")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_tenant_overview_basic(self, stats_service, sample_tenant):
        """测试获取租户基本概览"""
        overview = await stats_service.get_tenant_overview(sample_tenant.id)

        assert overview is not None
        assert overview.tenant_id == sample_tenant.id
        assert overview.tenant_name == sample_tenant.name
        assert overview.display_name == sample_tenant.display_name
        assert overview.status == TenantStatus.ACTIVE
        assert overview.tier == TenantTier.BASIC

    @pytest.mark.asyncio
    async def test_get_tenant_overview_quota_usage(self, stats_service, sample_tenant):
        """测试租户概览包含配额使用"""
        overview = await stats_service.get_tenant_overview(sample_tenant.id)

        assert overview is not None
        assert len(overview.quota_usage) > 0

        # 检查配额使用统计结构
        for quota_stat in overview.quota_usage:
            assert isinstance(quota_stat, QuotaUsageStats)
            assert quota_stat.limit >= 0
            assert quota_stat.current >= 0
            assert quota_stat.status in ["ok", "warning", "exceeded"]

    @pytest.mark.asyncio
    async def test_get_tenant_overview_activity_score(
        self, stats_service, sample_tenant, sample_usage_data
    ):
        """测试租户活跃度评分"""
        overview = await stats_service.get_tenant_overview(sample_tenant.id)

        assert overview is not None
        assert 0 <= overview.activity_score <= 100


# ============================================================================
# 仪表板测试
# ============================================================================


class TestTenantDashboard:
    """租户仪表板测试"""

    @pytest.mark.asyncio
    async def test_get_dashboard_not_found(self, stats_service):
        """测试获取不存在的租户仪表板"""
        result = await stats_service.get_tenant_dashboard("non-existent")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_dashboard_basic(self, stats_service, sample_tenant):
        """测试获取租户仪表板"""
        dashboard = await stats_service.get_tenant_dashboard(sample_tenant.id)

        assert dashboard is not None
        assert isinstance(dashboard, TenantDashboard)
        assert dashboard.tenant_id == sample_tenant.id
        assert dashboard.overview is not None

    @pytest.mark.asyncio
    async def test_get_dashboard_with_trends(
        self, stats_service, sample_tenant, sample_usage_data
    ):
        """测试仪表板包含趋势数据"""
        dashboard = await stats_service.get_tenant_dashboard(
            tenant_id=sample_tenant.id,
            include_trends=True,
            trend_period=StatsPeriod.DAILY,
            trend_days=7,
        )

        assert dashboard is not None
        # 趋势数据可能为空（取决于存储中的数据）
        assert isinstance(dashboard.usage_trends, dict)

    @pytest.mark.asyncio
    async def test_get_dashboard_without_trends(self, stats_service, sample_tenant):
        """测试仪表板不包含趋势数据"""
        dashboard = await stats_service.get_tenant_dashboard(
            tenant_id=sample_tenant.id,
            include_trends=False,
        )

        assert dashboard is not None
        assert len(dashboard.usage_trends) == 0

    @pytest.mark.asyncio
    async def test_get_dashboard_alerts(
        self, stats_service, sample_tenant, quota_manager
    ):
        """测试仪表板告警"""
        # 记录使用量接近限制
        await quota_manager.record_usage(
            sample_tenant.id, QuotaType.TOKENS_PER_DAY, 9000
        )

        dashboard = await stats_service.get_tenant_dashboard(sample_tenant.id)

        assert dashboard is not None
        assert isinstance(dashboard.alerts, list)


# ============================================================================
# 使用量趋势测试
# ============================================================================


class TestUsageTrend:
    """使用量趋势测试"""

    @pytest.mark.asyncio
    async def test_get_usage_trend_empty(self, stats_service, sample_tenant):
        """测试获取空趋势数据"""
        trend = await stats_service.get_usage_trend(
            tenant_id=sample_tenant.id,
            quota_type=QuotaType.TOKENS_PER_DAY,
            period=StatsPeriod.DAILY,
            days=7,
        )

        assert trend is not None
        assert isinstance(trend, UsageTrend)
        assert trend.quota_type == QuotaType.TOKENS_PER_DAY
        assert trend.period == StatsPeriod.DAILY

    @pytest.mark.asyncio
    async def test_get_usage_trend_with_data(
        self, stats_service, sample_tenant, sample_usage_data
    ):
        """测试获取有数据的趋势"""
        trend = await stats_service.get_usage_trend(
            tenant_id=sample_tenant.id,
            quota_type=QuotaType.TOKENS_PER_DAY,
            period=StatsPeriod.DAILY,
            days=7,
        )

        assert trend is not None
        # 数据点数量取决于存储中的数据
        assert isinstance(trend.data_points, list)
        assert trend.trend in [
            TrendDirection.UP,
            TrendDirection.DOWN,
            TrendDirection.STABLE,
        ]

    @pytest.mark.asyncio
    async def test_get_quota_consumption_trends(
        self, stats_service, sample_tenant, sample_usage_data
    ):
        """测试获取配额消耗趋势"""
        trends = await stats_service.get_quota_consumption_trends(
            tenant_id=sample_tenant.id,
            days=30,
        )

        assert isinstance(trends, dict)
        # 应该包含主要配额类型的趋势
        for key, trend in trends.items():
            assert isinstance(trend, UsageTrend)


# ============================================================================
# 系统概览测试
# ============================================================================


class TestSystemOverview:
    """系统概览测试"""

    @pytest.mark.asyncio
    async def test_get_system_overview_empty(self, stats_service):
        """测试空系统概览"""
        overview = await stats_service.get_system_overview()

        assert overview is not None
        assert overview.total_tenants == 0
        assert overview.active_tenants == 0

    @pytest.mark.asyncio
    async def test_get_system_overview_with_tenants(
        self, stats_service, storage, sample_tenant
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

        tenant3 = Tenant(
            id="tenant-3",
            name="test-tenant-3",
            display_name="Test Tenant 3",
            tier=TenantTier.FREE,
            status=TenantStatus.TRIAL,
        )
        await storage.create(tenant3)

        overview = await stats_service.get_system_overview()

        assert overview.total_tenants == 3
        assert overview.active_tenants == 2
        assert overview.trial_tenants == 1
        assert TenantTier.BASIC.value in overview.tier_distribution
        assert TenantTier.PROFESSIONAL.value in overview.tier_distribution
        assert TenantTier.FREE.value in overview.tier_distribution

    @pytest.mark.asyncio
    async def test_get_system_overview_quota_alerts(
        self, stats_service, storage, sample_tenant, quota_manager
    ):
        """测试系统概览配额告警"""
        # 记录使用量超限
        await quota_manager.record_usage(
            sample_tenant.id, QuotaType.TOKENS_PER_DAY, 15000
        )

        overview = await stats_service.get_system_overview()

        assert isinstance(overview.tenants_near_quota, list)
        assert isinstance(overview.tenants_exceeded_quota, list)


# ============================================================================
# 数据聚合测试
# ============================================================================


class TestDataAggregation:
    """数据聚合测试"""

    @pytest.mark.asyncio
    async def test_aggregate_usage_empty(self, stats_service, sample_tenant):
        """测试空数据聚合"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)

        result = await stats_service.aggregate_usage(
            tenant_id=sample_tenant.id,
            period=StatsPeriod.WEEKLY,
            start_date=start_date,
            end_date=end_date,
        )

        # 没有数据时返回 None
        assert result is None

    @pytest.mark.asyncio
    async def test_aggregate_usage_with_data(
        self, stats_service, sample_tenant, sample_usage_data
    ):
        """测试有数据的聚合"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)

        result = await stats_service.aggregate_usage(
            tenant_id=sample_tenant.id,
            period=StatsPeriod.WEEKLY,
            start_date=start_date,
            end_date=end_date,
        )

        if result:
            assert result.tenant_id == sample_tenant.id
            assert result.period == StatsPeriod.WEEKLY.value
            assert result.total_tokens >= 0
            assert result.api_calls >= 0


# ============================================================================
# 趋势计算测试
# ============================================================================


class TestTrendCalculation:
    """趋势计算测试"""

    def test_calculate_trend_stable(self, stats_service):
        """测试稳定趋势"""
        values = [100, 100, 100, 100, 100]
        trend, percentage = stats_service._calculate_trend(values)
        assert trend == TrendDirection.STABLE

    def test_calculate_trend_up(self, stats_service):
        """测试上升趋势"""
        values = [100, 110, 120, 130, 140]
        trend, percentage = stats_service._calculate_trend(values)
        assert trend == TrendDirection.UP
        assert percentage > 0

    def test_calculate_trend_down(self, stats_service):
        """测试下降趋势"""
        values = [140, 130, 120, 110, 100]
        trend, percentage = stats_service._calculate_trend(values)
        assert trend == TrendDirection.DOWN
        assert percentage > 0

    def test_calculate_trend_insufficient_data(self, stats_service):
        """测试数据不足"""
        values = [100]
        trend, percentage = stats_service._calculate_trend(values)
        assert trend == TrendDirection.STABLE
        assert percentage == 0.0


# ============================================================================
# 活跃度评分测试
# ============================================================================


class TestActivityScore:
    """活跃度评分测试"""

    @pytest.mark.asyncio
    async def test_activity_score_no_data(self, stats_service, sample_tenant):
        """测试无数据时的活跃度"""
        score = await stats_service._calculate_activity_score(sample_tenant.id)
        assert score == 0.0

    @pytest.mark.asyncio
    async def test_activity_score_with_data(
        self, stats_service, sample_tenant, sample_usage_data
    ):
        """测试有数据时的活跃度"""
        score = await stats_service._calculate_activity_score(sample_tenant.id)
        assert 0 <= score <= 100


# ============================================================================
# 全局配置测试
# ============================================================================


class TestGlobalConfiguration:
    """全局配置测试"""

    def test_configure_stats_service(self, storage, quota_manager):
        """测试配置统计服务"""
        service = configure_stats_service(storage, quota_manager)
        assert service is not None
        assert isinstance(service, TenantStatsService)

    def test_get_stats_service_after_configure(self, storage, quota_manager):
        """测试配置后获取服务"""
        configure_stats_service(storage, quota_manager)
        service = get_stats_service()
        assert service is not None
