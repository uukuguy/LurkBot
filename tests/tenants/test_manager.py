"""租户管理器测试"""

from datetime import datetime, timedelta

import pytest

from lurkbot.tenants import (
    MemoryTenantStorage,
    Tenant,
    TenantConfig,
    TenantEventType,
    TenantQuota,
    TenantStatus,
    TenantTier,
    TenantUsage,
)
from lurkbot.tenants.manager import TenantManager
from lurkbot.tenants.quota import QuotaManager, QuotaType


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
def manager(storage, quota_manager):
    """租户管理器实例"""
    return TenantManager(storage=storage, quota_manager=quota_manager)


# ============================================================================
# 租户 CRUD 测试
# ============================================================================


class TestTenantCRUD:
    """租户 CRUD 测试"""

    @pytest.mark.asyncio
    async def test_create_tenant(self, manager):
        """测试创建租户"""
        tenant = await manager.create_tenant(
            name="test-org",
            display_name="Test Organization",
            tier=TenantTier.BASIC,
            description="A test organization",
        )
        assert tenant.name == "test-org"
        assert tenant.display_name == "Test Organization"
        assert tenant.tier == TenantTier.BASIC
        assert tenant.status == TenantStatus.ACTIVE
        assert tenant.id.startswith("tenant_")

    @pytest.mark.asyncio
    async def test_create_tenant_with_trial(self, manager):
        """测试创建试用租户"""
        tenant = await manager.create_tenant(
            name="trial-org",
            display_name="Trial Organization",
            trial_days=14,
        )
        assert tenant.status == TenantStatus.TRIAL
        assert tenant.trial_ends_at is not None

    @pytest.mark.asyncio
    async def test_create_duplicate_name(self, manager):
        """测试创建重复名称的租户"""
        await manager.create_tenant(
            name="test-org",
            display_name="Test Organization",
        )
        with pytest.raises(ValueError, match="租户名称已存在"):
            await manager.create_tenant(
                name="test-org",
                display_name="Another Organization",
            )

    @pytest.mark.asyncio
    async def test_get_tenant(self, manager):
        """测试获取租户"""
        created = await manager.create_tenant(
            name="test-org",
            display_name="Test Organization",
        )
        tenant = await manager.get_tenant(created.id)
        assert tenant is not None
        assert tenant.id == created.id

    @pytest.mark.asyncio
    async def test_get_tenant_by_name(self, manager):
        """测试通过名称获取租户"""
        created = await manager.create_tenant(
            name="test-org",
            display_name="Test Organization",
        )
        tenant = await manager.get_tenant_by_name("test-org")
        assert tenant is not None
        assert tenant.id == created.id

    @pytest.mark.asyncio
    async def test_get_nonexistent_tenant(self, manager):
        """测试获取不存在的租户"""
        tenant = await manager.get_tenant("nonexistent")
        assert tenant is None

    @pytest.mark.asyncio
    async def test_update_tenant(self, manager):
        """测试更新租户"""
        created = await manager.create_tenant(
            name="test-org",
            display_name="Test Organization",
        )
        updated = await manager.update_tenant(
            tenant_id=created.id,
            display_name="Updated Organization",
            description="Updated description",
        )
        assert updated.display_name == "Updated Organization"
        assert updated.description == "Updated description"

    @pytest.mark.asyncio
    async def test_update_nonexistent_tenant(self, manager):
        """测试更新不存在的租户"""
        with pytest.raises(ValueError, match="租户不存在"):
            await manager.update_tenant(
                tenant_id="nonexistent",
                display_name="Updated",
            )

    @pytest.mark.asyncio
    async def test_delete_tenant_soft(self, manager):
        """测试软删除租户"""
        created = await manager.create_tenant(
            name="test-org",
            display_name="Test Organization",
        )
        result = await manager.delete_tenant(created.id)
        assert result is True

        # 软删除后应该还能获取到，但状态为 DELETED
        tenant = await manager.get_tenant(created.id)
        assert tenant is not None
        assert tenant.status == TenantStatus.DELETED

    @pytest.mark.asyncio
    async def test_delete_tenant_hard(self, manager):
        """测试硬删除租户"""
        created = await manager.create_tenant(
            name="test-org",
            display_name="Test Organization",
        )
        result = await manager.delete_tenant(created.id, hard_delete=True)
        assert result is True

        # 硬删除后应该获取不到
        tenant = await manager.get_tenant(created.id)
        assert tenant is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_tenant(self, manager):
        """测试删除不存在的租户"""
        result = await manager.delete_tenant("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_list_tenants(self, manager):
        """测试列出租户"""
        await manager.create_tenant(name="org-1", display_name="Org 1")
        await manager.create_tenant(name="org-2", display_name="Org 2")
        await manager.create_tenant(name="org-3", display_name="Org 3")

        tenants = await manager.list_tenants()
        assert len(tenants) == 3

    @pytest.mark.asyncio
    async def test_list_tenants_filtered(self, manager):
        """测试按条件列出租户"""
        await manager.create_tenant(
            name="org-1", display_name="Org 1", tier=TenantTier.FREE
        )
        await manager.create_tenant(
            name="org-2", display_name="Org 2", tier=TenantTier.BASIC
        )

        free_tenants = await manager.list_tenants(tier=TenantTier.FREE)
        assert len(free_tenants) == 1

    @pytest.mark.asyncio
    async def test_count_tenants(self, manager):
        """测试统计租户数量"""
        await manager.create_tenant(name="org-1", display_name="Org 1")
        await manager.create_tenant(name="org-2", display_name="Org 2")

        count = await manager.count_tenants()
        assert count == 2


# ============================================================================
# 状态管理测试
# ============================================================================


class TestStatusManagement:
    """状态管理测试"""

    @pytest.mark.asyncio
    async def test_activate_tenant(self, manager):
        """测试激活租户"""
        created = await manager.create_tenant(
            name="test-org", display_name="Test Org", trial_days=14
        )
        assert created.status == TenantStatus.TRIAL

        activated = await manager.activate_tenant(created.id)
        assert activated.status == TenantStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_suspend_tenant(self, manager):
        """测试暂停租户"""
        created = await manager.create_tenant(
            name="test-org", display_name="Test Org"
        )
        suspended = await manager.suspend_tenant(created.id, reason="违规操作")
        assert suspended.status == TenantStatus.SUSPENDED

    @pytest.mark.asyncio
    async def test_expire_tenant(self, manager):
        """测试设置过期"""
        created = await manager.create_tenant(
            name="test-org", display_name="Test Org"
        )
        expired = await manager.expire_tenant(created.id)
        assert expired.status == TenantStatus.EXPIRED

    @pytest.mark.asyncio
    async def test_status_change_nonexistent(self, manager):
        """测试对不存在租户的状态变更"""
        with pytest.raises(ValueError, match="租户不存在"):
            await manager.activate_tenant("nonexistent")

        with pytest.raises(ValueError, match="租户不存在"):
            await manager.suspend_tenant("nonexistent")

        with pytest.raises(ValueError, match="租户不存在"):
            await manager.expire_tenant("nonexistent")


# ============================================================================
# 套餐管理测试
# ============================================================================


class TestTierManagement:
    """套餐管理测试"""

    @pytest.mark.asyncio
    async def test_upgrade_tier(self, manager):
        """测试升级套餐"""
        created = await manager.create_tenant(
            name="test-org",
            display_name="Test Org",
            tier=TenantTier.FREE,
        )
        assert created.tier == TenantTier.FREE

        upgraded = await manager.upgrade_tier(created.id, TenantTier.PROFESSIONAL)
        assert upgraded.tier == TenantTier.PROFESSIONAL
        # 配额应该更新为新套餐默认值
        assert upgraded.quota.max_agents == 10

    @pytest.mark.asyncio
    async def test_upgrade_tier_without_quota_update(self, manager):
        """测试升级套餐不更新配额"""
        created = await manager.create_tenant(
            name="test-org",
            display_name="Test Org",
            tier=TenantTier.FREE,
        )
        old_quota = created.quota.max_agents

        upgraded = await manager.upgrade_tier(
            created.id, TenantTier.PROFESSIONAL, update_quota=False
        )
        assert upgraded.tier == TenantTier.PROFESSIONAL
        # 配额不应该更新
        assert upgraded.quota.max_agents == old_quota

    @pytest.mark.asyncio
    async def test_upgrade_tier_nonexistent(self, manager):
        """测试升级不存在租户的套餐"""
        with pytest.raises(ValueError, match="租户不存在"):
            await manager.upgrade_tier("nonexistent", TenantTier.PROFESSIONAL)


# ============================================================================
# 配额管理测试
# ============================================================================


class TestQuotaManagement:
    """配额管理测试"""

    @pytest.mark.asyncio
    async def test_get_quota(self, manager):
        """测试获取配额"""
        created = await manager.create_tenant(
            name="test-org",
            display_name="Test Org",
            tier=TenantTier.BASIC,
        )
        quota = await manager.get_quota(created.id)
        assert quota is not None
        assert quota.max_agents == 3  # BASIC quota

    @pytest.mark.asyncio
    async def test_update_quota(self, manager):
        """测试更新配额"""
        created = await manager.create_tenant(
            name="test-org",
            display_name="Test Org",
        )
        new_quota = TenantQuota(max_agents=50)
        result = await manager.update_quota(created.id, new_quota)
        assert result is True

        quota = await manager.get_quota(created.id)
        assert quota.max_agents == 50

    @pytest.mark.asyncio
    async def test_check_quota(self, manager):
        """测试检查配额"""
        created = await manager.create_tenant(
            name="test-org",
            display_name="Test Org",
        )
        detail = await manager.check_quota(created.id, QuotaType.AGENTS)
        assert detail.current == 0
        assert detail.limit > 0

    @pytest.mark.asyncio
    async def test_can_proceed(self, manager):
        """测试是否可以继续"""
        created = await manager.create_tenant(
            name="test-org",
            display_name="Test Org",
        )
        result = await manager.can_proceed(created.id, QuotaType.AGENTS)
        assert result is True

    @pytest.mark.asyncio
    async def test_can_proceed_nonexistent(self, manager):
        """测试不存在租户的配额检查"""
        result = await manager.can_proceed("nonexistent", QuotaType.AGENTS)
        assert result is False


# ============================================================================
# 配置管理测试
# ============================================================================


class TestConfigManagement:
    """配置管理测试"""

    @pytest.mark.asyncio
    async def test_get_config(self, manager):
        """测试获取配置"""
        created = await manager.create_tenant(
            name="test-org",
            display_name="Test Org",
        )
        config = await manager.get_config(created.id)
        assert config is not None
        assert "deepseek:deepseek-chat" in config.allowed_models

    @pytest.mark.asyncio
    async def test_update_config(self, manager):
        """测试更新配置"""
        created = await manager.create_tenant(
            name="test-org",
            display_name="Test Org",
        )
        new_config = TenantConfig(default_model="claude-3")
        result = await manager.update_config(created.id, new_config)
        assert result is True

        config = await manager.get_config(created.id)
        assert config.default_model == "claude-3"


# ============================================================================
# 上下文管理测试
# ============================================================================


class TestContextManagement:
    """上下文管理测试"""

    @pytest.mark.asyncio
    async def test_enter_context(self, manager):
        """测试进入上下文"""
        created = await manager.create_tenant(
            name="test-org",
            display_name="Test Org",
        )
        ctx = await manager.enter_context(created.id)
        try:
            assert ctx.tenant_id == created.id
            assert manager.get_current_tenant() is not None
        finally:
            await manager.exit_context()

    @pytest.mark.asyncio
    async def test_enter_context_nonexistent(self, manager):
        """测试进入不存在租户的上下文"""
        with pytest.raises(ValueError, match="租户不存在"):
            await manager.enter_context("nonexistent")

    @pytest.mark.asyncio
    async def test_enter_context_inactive(self, manager):
        """测试进入非活跃租户的上下文"""
        created = await manager.create_tenant(
            name="test-org",
            display_name="Test Org",
        )
        await manager.suspend_tenant(created.id)

        with pytest.raises(ValueError, match="租户不可用"):
            await manager.enter_context(created.id)

    @pytest.mark.asyncio
    async def test_context_manager(self, manager):
        """测试上下文管理器"""
        created = await manager.create_tenant(
            name="test-org",
            display_name="Test Org",
        )
        async with manager.context(created.id) as ctx:
            assert ctx.tenant_id == created.id


# ============================================================================
# 事件管理测试
# ============================================================================


class TestEventManagement:
    """事件管理测试"""

    @pytest.mark.asyncio
    async def test_events_recorded_on_create(self, manager):
        """测试创建时记录事件"""
        created = await manager.create_tenant(
            name="test-org",
            display_name="Test Org",
        )
        events = await manager.get_events(created.id)
        assert len(events) >= 1
        assert any(e.event_type == TenantEventType.CREATED for e in events)

    @pytest.mark.asyncio
    async def test_events_recorded_on_status_change(self, manager):
        """测试状态变更时记录事件"""
        created = await manager.create_tenant(
            name="test-org",
            display_name="Test Org",
        )
        await manager.suspend_tenant(created.id, reason="test")

        events = await manager.get_events(created.id)
        assert any(e.event_type == TenantEventType.SUSPENDED for e in events)

    @pytest.mark.asyncio
    async def test_events_recorded_on_tier_change(self, manager):
        """测试套餐变更时记录事件"""
        created = await manager.create_tenant(
            name="test-org",
            display_name="Test Org",
        )
        await manager.upgrade_tier(created.id, TenantTier.PROFESSIONAL)

        events = await manager.get_events(created.id)
        assert any(e.event_type == TenantEventType.TIER_CHANGED for e in events)

    @pytest.mark.asyncio
    async def test_event_handler(self, manager):
        """测试事件处理器"""
        received_events = []

        def handler(event):
            received_events.append(event)

        manager.on_event(handler)

        await manager.create_tenant(
            name="test-org",
            display_name="Test Org",
        )

        assert len(received_events) >= 1
        assert received_events[0].event_type == TenantEventType.CREATED

    @pytest.mark.asyncio
    async def test_async_event_handler(self, manager):
        """测试异步事件处理器"""
        received_events = []

        async def handler(event):
            received_events.append(event)

        manager.on_event(handler)

        await manager.create_tenant(
            name="test-org",
            display_name="Test Org",
        )

        assert len(received_events) >= 1


# ============================================================================
# 维护任务测试
# ============================================================================


class TestMaintenanceTasks:
    """维护任务测试"""

    @pytest.mark.asyncio
    async def test_check_expired_tenants(self, manager):
        """测试检查过期租户"""
        # 创建一个已过期的租户
        created = await manager.create_tenant(
            name="expired-org",
            display_name="Expired Org",
        )
        # 手动设置过期时间为过去
        tenant = await manager.get_tenant(created.id)
        tenant.expires_at = datetime.now() - timedelta(days=1)
        await manager._storage.update(tenant)

        expired_ids = await manager.check_expired_tenants()
        assert created.id in expired_ids

        # 验证状态已更新
        tenant = await manager.get_tenant(created.id)
        assert tenant.status == TenantStatus.EXPIRED

    @pytest.mark.asyncio
    async def test_check_trial_expired_tenants(self, manager):
        """测试检查试用期过期租户"""
        # 创建试用租户
        created = await manager.create_tenant(
            name="trial-org",
            display_name="Trial Org",
            trial_days=1,
        )
        # 手动设置试用结束时间为过去
        tenant = await manager.get_tenant(created.id)
        tenant.trial_ends_at = datetime.now() - timedelta(days=1)
        await manager._storage.update(tenant)

        expired_ids = await manager.check_expired_tenants()
        assert created.id in expired_ids


# ============================================================================
# 使用统计测试
# ============================================================================


class TestUsageStats:
    """使用统计测试"""

    @pytest.mark.asyncio
    async def test_record_and_get_usage(self, manager):
        """测试记录和获取使用统计"""
        created = await manager.create_tenant(
            name="test-org",
            display_name="Test Org",
        )

        now = datetime.now()
        usage = TenantUsage(
            tenant_id=created.id,
            period="daily",
            period_start=now,
            period_end=now + timedelta(days=1),
            total_tokens=5000,
            api_calls=100,
        )
        result = await manager.record_usage_stats(usage)
        assert result is True

        usages = await manager.get_usage_stats(created.id)
        assert len(usages) == 1
        assert usages[0].total_tokens == 5000

    @pytest.mark.asyncio
    async def test_get_usage_summary(self, manager):
        """测试获取使用量摘要"""
        created = await manager.create_tenant(
            name="test-org",
            display_name="Test Org",
        )
        summary = await manager.get_usage_summary(created.id)
        assert len(summary) > 0
