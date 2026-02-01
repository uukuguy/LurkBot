"""配额管理器测试"""

from datetime import datetime, timedelta

import pytest

from lurkbot.tenants import (
    Tenant,
    TenantQuota,
    TenantTier,
)
from lurkbot.tenants.quota import (
    QuotaCheckResult,
    QuotaManager,
    QuotaType,
)


# ============================================================================
# 测试夹具
# ============================================================================


@pytest.fixture
def quota_manager():
    """配额管理器实例"""
    return QuotaManager()


@pytest.fixture
def sample_tenant():
    """示例租户"""
    return Tenant(
        id="tenant-1",
        name="test-tenant",
        display_name="Test Tenant",
        tier=TenantTier.BASIC,
        quota=TenantQuota(
            max_agents=5,
            max_sessions=50,
            max_plugins=10,
            max_tokens_per_day=10000,
            max_api_calls_per_minute=30,
            max_concurrent_requests=5,
        ),
    )


# ============================================================================
# 配额检查测试
# ============================================================================


class TestQuotaCheck:
    """配额检查测试"""

    @pytest.mark.asyncio
    async def test_check_quota_ok(self, quota_manager, sample_tenant):
        """测试配额充足"""
        result = await quota_manager.check_quota(sample_tenant, QuotaType.AGENTS, 1)
        assert result.result == QuotaCheckResult.OK
        assert result.current == 0
        assert result.limit == 5

    @pytest.mark.asyncio
    async def test_check_quota_warning(self, quota_manager, sample_tenant):
        """测试配额警告"""
        # 记录使用量达到 80%
        await quota_manager.record_usage("tenant-1", QuotaType.AGENTS, 4)
        result = await quota_manager.check_quota(sample_tenant, QuotaType.AGENTS, 0)
        assert result.result == QuotaCheckResult.WARNING
        assert result.percentage == 0.8

    @pytest.mark.asyncio
    async def test_check_quota_exceeded(self, quota_manager, sample_tenant):
        """测试配额超限"""
        # 记录使用量达到上限
        await quota_manager.record_usage("tenant-1", QuotaType.AGENTS, 5)
        result = await quota_manager.check_quota(sample_tenant, QuotaType.AGENTS, 1)
        assert result.result == QuotaCheckResult.EXCEEDED

    @pytest.mark.asyncio
    async def test_check_all_quotas(self, quota_manager, sample_tenant):
        """测试检查所有配额"""
        results = await quota_manager.check_all_quotas(sample_tenant)
        assert len(results) == len(QuotaType)
        assert all(r.result == QuotaCheckResult.OK for r in results)

    @pytest.mark.asyncio
    async def test_can_proceed_true(self, quota_manager, sample_tenant):
        """测试可以继续"""
        result = await quota_manager.can_proceed(sample_tenant, QuotaType.AGENTS, 1)
        assert result is True

    @pytest.mark.asyncio
    async def test_can_proceed_false(self, quota_manager, sample_tenant):
        """测试不能继续"""
        await quota_manager.record_usage("tenant-1", QuotaType.AGENTS, 5)
        result = await quota_manager.can_proceed(sample_tenant, QuotaType.AGENTS, 1)
        assert result is False


# ============================================================================
# 使用量追踪测试
# ============================================================================


class TestUsageTracking:
    """使用量追踪测试"""

    @pytest.mark.asyncio
    async def test_record_usage(self, quota_manager, sample_tenant):
        """测试记录使用量"""
        await quota_manager.record_usage("tenant-1", QuotaType.TOKENS_PER_DAY, 1000)
        result = await quota_manager.check_quota(sample_tenant, QuotaType.TOKENS_PER_DAY)
        assert result.current == 1000

    @pytest.mark.asyncio
    async def test_record_usage_accumulates(self, quota_manager, sample_tenant):
        """测试使用量累加"""
        await quota_manager.record_usage("tenant-1", QuotaType.TOKENS_PER_DAY, 500)
        await quota_manager.record_usage("tenant-1", QuotaType.TOKENS_PER_DAY, 300)
        result = await quota_manager.check_quota(sample_tenant, QuotaType.TOKENS_PER_DAY)
        assert result.current == 800

    @pytest.mark.asyncio
    async def test_reset_usage_single(self, quota_manager, sample_tenant):
        """测试重置单个配额使用量"""
        await quota_manager.record_usage("tenant-1", QuotaType.TOKENS_PER_DAY, 1000)
        await quota_manager.record_usage("tenant-1", QuotaType.AGENTS, 2)
        await quota_manager.reset_usage("tenant-1", QuotaType.TOKENS_PER_DAY)

        # tokens 应该被重置
        result = await quota_manager.check_quota(sample_tenant, QuotaType.TOKENS_PER_DAY)
        assert result.current == 0

        # agents 不应该被重置
        result = await quota_manager.check_quota(sample_tenant, QuotaType.AGENTS)
        assert result.current == 2

    @pytest.mark.asyncio
    async def test_reset_usage_all(self, quota_manager, sample_tenant):
        """测试重置所有使用量"""
        await quota_manager.record_usage("tenant-1", QuotaType.TOKENS_PER_DAY, 1000)
        await quota_manager.record_usage("tenant-1", QuotaType.AGENTS, 2)
        await quota_manager.reset_usage("tenant-1")

        # 所有都应该被重置
        result = await quota_manager.check_quota(sample_tenant, QuotaType.TOKENS_PER_DAY)
        assert result.current == 0
        result = await quota_manager.check_quota(sample_tenant, QuotaType.AGENTS)
        assert result.current == 0


# ============================================================================
# API 速率限制测试
# ============================================================================


class TestRateLimit:
    """API 速率限制测试"""

    @pytest.mark.asyncio
    async def test_check_rate_limit_ok(self, quota_manager, sample_tenant):
        """测试速率限制正常"""
        result = await quota_manager.check_rate_limit(sample_tenant)
        assert result.result == QuotaCheckResult.OK
        assert result.current == 0
        assert result.limit == 30

    @pytest.mark.asyncio
    async def test_record_api_call(self, quota_manager, sample_tenant):
        """测试记录 API 调用"""
        await quota_manager.record_api_call("tenant-1")
        result = await quota_manager.check_rate_limit(sample_tenant)
        assert result.current == 1

    @pytest.mark.asyncio
    async def test_rate_limit_exceeded(self, quota_manager, sample_tenant):
        """测试速率限制超限"""
        for _ in range(30):
            await quota_manager.record_api_call("tenant-1")

        result = await quota_manager.check_rate_limit(sample_tenant)
        assert result.result == QuotaCheckResult.EXCEEDED

    @pytest.mark.asyncio
    async def test_rate_limit_window(self, quota_manager, sample_tenant):
        """测试速率限制时间窗口"""
        # 记录一些调用
        for _ in range(10):
            await quota_manager.record_api_call("tenant-1")

        result = await quota_manager.check_rate_limit(sample_tenant)
        assert result.current == 10


# ============================================================================
# 并发请求限制测试
# ============================================================================


class TestConcurrentRequests:
    """并发请求限制测试"""

    @pytest.mark.asyncio
    async def test_acquire_concurrent_slot(self, quota_manager, sample_tenant):
        """测试获取并发槽位"""
        result = await quota_manager.acquire_concurrent_slot(sample_tenant)
        assert result is True
        count = await quota_manager.get_concurrent_count("tenant-1")
        assert count == 1

    @pytest.mark.asyncio
    async def test_acquire_concurrent_slot_limit(self, quota_manager, sample_tenant):
        """测试并发槽位上限"""
        # 获取所有槽位
        for _ in range(5):
            result = await quota_manager.acquire_concurrent_slot(sample_tenant)
            assert result is True

        # 再获取应该失败
        result = await quota_manager.acquire_concurrent_slot(sample_tenant)
        assert result is False

    @pytest.mark.asyncio
    async def test_release_concurrent_slot(self, quota_manager, sample_tenant):
        """测试释放并发槽位"""
        await quota_manager.acquire_concurrent_slot(sample_tenant)
        await quota_manager.acquire_concurrent_slot(sample_tenant)
        count = await quota_manager.get_concurrent_count("tenant-1")
        assert count == 2

        await quota_manager.release_concurrent_slot("tenant-1")
        count = await quota_manager.get_concurrent_count("tenant-1")
        assert count == 1

    @pytest.mark.asyncio
    async def test_release_empty_slot(self, quota_manager):
        """测试释放空槽位"""
        # 不应该报错
        await quota_manager.release_concurrent_slot("tenant-1")
        count = await quota_manager.get_concurrent_count("tenant-1")
        assert count == 0


# ============================================================================
# 统计信息测试
# ============================================================================


class TestUsageSummary:
    """统计信息测试"""

    @pytest.mark.asyncio
    async def test_get_usage_summary(self, quota_manager, sample_tenant):
        """测试获取使用量摘要"""
        await quota_manager.record_usage("tenant-1", QuotaType.TOKENS_PER_DAY, 5000)
        await quota_manager.record_usage("tenant-1", QuotaType.AGENTS, 2)

        summary = await quota_manager.get_usage_summary(sample_tenant)

        assert "tokens_per_day" in summary
        assert summary["tokens_per_day"]["current"] == 5000
        assert summary["tokens_per_day"]["limit"] == 10000
        assert summary["tokens_per_day"]["percentage"] == 0.5
        assert summary["tokens_per_day"]["status"] == "ok"

        assert "agents" in summary
        assert summary["agents"]["current"] == 2
        assert summary["agents"]["limit"] == 5
        assert summary["agents"]["percentage"] == 0.4
