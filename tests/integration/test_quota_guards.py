"""配额守卫测试

测试 QuotaGuard 的各种方法和场景。
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from lurkbot.tenants import (
    TenantManager,
    MemoryTenantStorage,
    TenantTier,
    QuotaManager,
    QuotaType,
    TenantQuota,
)
from lurkbot.tenants.errors import (
    QuotaExceededError,
    RateLimitedError,
    ConcurrentLimitError,
    TenantNotFoundError,
    TenantInactiveError,
)
from lurkbot.tenants.guards import QuotaGuard


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def storage():
    """创建内存存储"""
    return MemoryTenantStorage()


@pytest.fixture
def quota_manager():
    """创建配额管理器"""
    return QuotaManager()


@pytest.fixture
def tenant_manager(storage, quota_manager):
    """创建租户管理器"""
    return TenantManager(storage=storage, quota_manager=quota_manager)


@pytest.fixture
def quota_guard(tenant_manager, quota_manager):
    """创建配额守卫"""
    return QuotaGuard(tenant_manager=tenant_manager, quota_manager=quota_manager)


@pytest.fixture
async def basic_tenant(tenant_manager):
    """创建基础套餐租户"""
    tenant = await tenant_manager.create_tenant(
        name="basic-tenant",
        display_name="Basic Tenant",
        tier=TenantTier.BASIC,
    )
    return tenant


@pytest.fixture
async def free_tenant(tenant_manager):
    """创建免费套餐租户"""
    tenant = await tenant_manager.create_tenant(
        name="free-tenant",
        display_name="Free Tenant",
        tier=TenantTier.FREE,
    )
    return tenant


# ============================================================================
# 基本功能测试
# ============================================================================


class TestQuotaGuardBasic:
    """QuotaGuard 基本功能测试"""

    @pytest.mark.asyncio
    async def test_check_and_record_success(self, quota_guard, basic_tenant):
        """测试检查并记录成功"""
        await quota_guard.check_and_record(
            tenant_id=basic_tenant.id,
            quota_type=QuotaType.API_CALLS_PER_DAY,
            amount=1,
        )

    @pytest.mark.asyncio
    async def test_check_rate_limit_success(self, quota_guard, basic_tenant):
        """测试速率限制检查成功"""
        await quota_guard.check_rate_limit(basic_tenant.id)

    @pytest.mark.asyncio
    async def test_acquire_concurrent_slot_success(self, quota_guard, basic_tenant):
        """测试获取并发槽位成功"""
        result = await quota_guard.acquire_concurrent_slot(basic_tenant.id)
        assert result is True

    @pytest.mark.asyncio
    async def test_release_concurrent_slot(self, quota_guard, basic_tenant):
        """测试释放并发槽位"""
        await quota_guard.acquire_concurrent_slot(basic_tenant.id)
        await quota_guard.release_concurrent_slot(basic_tenant.id)

    @pytest.mark.asyncio
    async def test_record_token_usage(self, quota_guard, basic_tenant):
        """测试记录 Token 使用量"""
        await quota_guard.record_token_usage(
            tenant_id=basic_tenant.id,
            input_tokens=100,
            output_tokens=200,
        )


# ============================================================================
# 配额超限测试
# ============================================================================


class TestQuotaExceeded:
    """配额超限场景测试"""

    @pytest.mark.asyncio
    async def test_quota_exceeded_error(self, tenant_manager, quota_manager):
        """测试配额超限错误"""
        # 创建配额很低的租户
        tenant = await tenant_manager.create_tenant(
            name="low-quota-tenant",
            display_name="Low Quota Tenant",
            tier=TenantTier.FREE,
        )

        # 更新配额为很低的值
        low_quota = TenantQuota(
            max_agents=1,
            max_sessions=1,
            max_plugins=0,
            max_custom_tools=0,
            max_tokens_per_day=10,  # 很低的限制
            max_tokens_per_request=5,
            max_api_calls_per_minute=1,
            max_api_calls_per_day=1,  # 很低的限制
            storage_quota_mb=1,
            max_concurrent_requests=1,
        )
        await tenant_manager.update_quota(tenant.id, low_quota)

        guard = QuotaGuard(tenant_manager=tenant_manager, quota_manager=quota_manager)

        # 第一次调用应该成功
        await guard.check_and_record(
            tenant_id=tenant.id,
            quota_type=QuotaType.API_CALLS_PER_DAY,
            amount=1,
        )

        # 第二次调用应该失败
        with pytest.raises(QuotaExceededError) as exc_info:
            await guard.check_and_record(
                tenant_id=tenant.id,
                quota_type=QuotaType.API_CALLS_PER_DAY,
                amount=1,
            )

        assert exc_info.value.tenant_id == tenant.id
        assert exc_info.value.quota_type == "api_calls_per_day"


# ============================================================================
# 速率限制测试
# ============================================================================


class TestRateLimiting:
    """速率限制场景测试"""

    @pytest.mark.asyncio
    async def test_rate_limit_exceeded(self, tenant_manager, quota_manager):
        """测试速率限制超限"""
        # 创建速率限制很低的租户
        tenant = await tenant_manager.create_tenant(
            name="rate-limited-tenant",
            display_name="Rate Limited Tenant",
            tier=TenantTier.FREE,
        )

        # 更新配额为很低的速率限制
        low_quota = TenantQuota(
            max_agents=10,
            max_sessions=10,
            max_plugins=5,
            max_custom_tools=5,
            max_tokens_per_day=100000,
            max_tokens_per_request=10000,
            max_api_calls_per_minute=2,  # 很低的速率限制
            max_api_calls_per_day=1000,
            storage_quota_mb=100,
            max_concurrent_requests=5,
        )
        await tenant_manager.update_quota(tenant.id, low_quota)

        guard = QuotaGuard(tenant_manager=tenant_manager, quota_manager=quota_manager)

        # 快速调用多次
        await guard.check_rate_limit(tenant.id)
        await guard.check_rate_limit(tenant.id)

        # 第三次应该失败
        with pytest.raises(RateLimitedError) as exc_info:
            await guard.check_rate_limit(tenant.id)

        assert exc_info.value.tenant_id == tenant.id
        assert exc_info.value.retry_after_seconds == 60


# ============================================================================
# 并发限制测试
# ============================================================================


class TestConcurrentLimiting:
    """并发限制场景测试"""

    @pytest.mark.asyncio
    async def test_concurrent_limit_exceeded(self, tenant_manager, quota_manager):
        """测试并发限制超限"""
        # 创建并发限制很低的租户
        tenant = await tenant_manager.create_tenant(
            name="concurrent-limited-tenant",
            display_name="Concurrent Limited Tenant",
            tier=TenantTier.FREE,
        )

        # 更新配额为很低的并发限制
        low_quota = TenantQuota(
            max_agents=10,
            max_sessions=10,
            max_plugins=5,
            max_custom_tools=5,
            max_tokens_per_day=100000,
            max_tokens_per_request=10000,
            max_api_calls_per_minute=100,
            max_api_calls_per_day=1000,
            storage_quota_mb=100,
            max_concurrent_requests=1,  # 只允许 1 个并发
        )
        await tenant_manager.update_quota(tenant.id, low_quota)

        guard = QuotaGuard(tenant_manager=tenant_manager, quota_manager=quota_manager)

        # 第一次获取应该成功
        await guard.acquire_concurrent_slot(tenant.id)

        # 第二次获取应该失败
        with pytest.raises(ConcurrentLimitError) as exc_info:
            await guard.acquire_concurrent_slot(tenant.id)

        assert exc_info.value.tenant_id == tenant.id
        assert exc_info.value.current_concurrent == 1
        assert exc_info.value.max_concurrent == 1

    @pytest.mark.asyncio
    async def test_concurrent_slot_release_allows_new(self, tenant_manager, quota_manager):
        """测试释放槽位后可以获取新槽位"""
        tenant = await tenant_manager.create_tenant(
            name="concurrent-test-tenant",
            display_name="Concurrent Test Tenant",
            tier=TenantTier.FREE,
        )

        low_quota = TenantQuota(
            max_agents=10,
            max_sessions=10,
            max_plugins=5,
            max_custom_tools=5,
            max_tokens_per_day=100000,
            max_tokens_per_request=10000,
            max_api_calls_per_minute=100,
            max_api_calls_per_day=1000,
            storage_quota_mb=100,
            max_concurrent_requests=1,
        )
        await tenant_manager.update_quota(tenant.id, low_quota)

        guard = QuotaGuard(tenant_manager=tenant_manager, quota_manager=quota_manager)

        # 获取槽位
        await guard.acquire_concurrent_slot(tenant.id)

        # 释放槽位
        await guard.release_concurrent_slot(tenant.id)

        # 再次获取应该成功
        result = await guard.acquire_concurrent_slot(tenant.id)
        assert result is True


# ============================================================================
# 上下文管理器测试
# ============================================================================


class TestContextManagers:
    """上下文管理器测试"""

    @pytest.mark.asyncio
    async def test_concurrent_slot_context_manager(self, quota_guard, basic_tenant):
        """测试并发槽位上下文管理器"""
        async with quota_guard.concurrent_slot_context(basic_tenant.id):
            # 在上下文中
            pass
        # 上下文结束后槽位应该被释放

    @pytest.mark.asyncio
    async def test_concurrent_slot_context_manager_exception(self, quota_guard, basic_tenant):
        """测试并发槽位上下文管理器异常处理"""
        try:
            async with quota_guard.concurrent_slot_context(basic_tenant.id):
                raise ValueError("Test exception")
        except ValueError:
            pass
        # 即使发生异常，槽位也应该被释放

    @pytest.mark.asyncio
    async def test_rate_limit_context_manager(self, quota_guard, basic_tenant):
        """测试速率限制上下文管理器"""
        async with quota_guard.rate_limit_context(basic_tenant.id):
            # 在上下文中
            pass


# ============================================================================
# 租户验证测试
# ============================================================================


class TestTenantValidation:
    """租户验证测试"""

    @pytest.mark.asyncio
    async def test_nonexistent_tenant(self, quota_guard):
        """测试不存在的租户"""
        with pytest.raises(TenantNotFoundError):
            await quota_guard.check_rate_limit("nonexistent_tenant_id")

    @pytest.mark.asyncio
    async def test_suspended_tenant(self, tenant_manager, quota_manager):
        """测试暂停的租户"""
        tenant = await tenant_manager.create_tenant(
            name="suspended-tenant",
            display_name="Suspended Tenant",
        )
        await tenant_manager.suspend_tenant(tenant.id, reason="Test")

        guard = QuotaGuard(tenant_manager=tenant_manager, quota_manager=quota_manager)

        with pytest.raises(TenantInactiveError):
            await guard.check_rate_limit(tenant.id)

    @pytest.mark.asyncio
    async def test_expired_tenant(self, tenant_manager, quota_manager):
        """测试过期的租户"""
        tenant = await tenant_manager.create_tenant(
            name="expired-tenant",
            display_name="Expired Tenant",
        )
        await tenant_manager.expire_tenant(tenant.id)

        guard = QuotaGuard(tenant_manager=tenant_manager, quota_manager=quota_manager)

        with pytest.raises(TenantInactiveError):
            await guard.check_rate_limit(tenant.id)


# ============================================================================
# 配置测试
# ============================================================================


class TestQuotaGuardConfiguration:
    """QuotaGuard 配置测试"""

    @pytest.mark.asyncio
    async def test_set_tenant_manager(self, quota_manager, tenant_manager):
        """测试设置租户管理器"""
        guard = QuotaGuard(quota_manager=quota_manager)

        # 未设置时应该抛出错误
        with pytest.raises(RuntimeError):
            await guard.check_rate_limit("any_tenant")

        # 设置后应该正常工作
        guard.set_tenant_manager(tenant_manager)

        tenant = await tenant_manager.create_tenant(
            name="config-test-tenant",
            display_name="Config Test Tenant",
        )

        await guard.check_rate_limit(tenant.id)
