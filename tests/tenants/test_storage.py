"""租户存储测试"""

import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from lurkbot.tenants import (
    FileTenantStorage,
    MemoryTenantStorage,
    Tenant,
    TenantConfig,
    TenantEvent,
    TenantEventType,
    TenantQuota,
    TenantStatus,
    TenantTier,
    TenantUsage,
)


# ============================================================================
# 测试夹具
# ============================================================================


@pytest.fixture
def memory_storage():
    """内存存储实例"""
    return MemoryTenantStorage()


@pytest.fixture
def file_storage(tmp_path):
    """文件存储实例"""
    return FileTenantStorage(tmp_path)


@pytest.fixture
def sample_tenant():
    """示例租户"""
    return Tenant(
        id="tenant-1",
        name="test-tenant",
        display_name="Test Tenant",
        description="A test tenant",
        status=TenantStatus.ACTIVE,
        tier=TenantTier.BASIC,
    )


@pytest.fixture
def sample_tenant_2():
    """第二个示例租户"""
    return Tenant(
        id="tenant-2",
        name="test-tenant-2",
        display_name="Test Tenant 2",
        status=TenantStatus.TRIAL,
        tier=TenantTier.FREE,
    )


# ============================================================================
# MemoryTenantStorage 测试
# ============================================================================


class TestMemoryTenantStorage:
    """内存存储测试"""

    # ------------------------------------------------------------------------
    # CRUD 测试
    # ------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_create_tenant(self, memory_storage, sample_tenant):
        """测试创建租户"""
        result = await memory_storage.create(sample_tenant)
        assert result.id == sample_tenant.id
        assert result.name == sample_tenant.name

    @pytest.mark.asyncio
    async def test_create_duplicate_id(self, memory_storage, sample_tenant):
        """测试创建重复 ID 的租户"""
        await memory_storage.create(sample_tenant)
        with pytest.raises(ValueError, match="租户已存在"):
            await memory_storage.create(sample_tenant)

    @pytest.mark.asyncio
    async def test_create_duplicate_name(self, memory_storage, sample_tenant):
        """测试创建重复名称的租户"""
        await memory_storage.create(sample_tenant)
        duplicate = Tenant(
            id="tenant-different",
            name=sample_tenant.name,  # 相同名称
            display_name="Different Tenant",
        )
        with pytest.raises(ValueError, match="租户名称已存在"):
            await memory_storage.create(duplicate)

    @pytest.mark.asyncio
    async def test_get_tenant(self, memory_storage, sample_tenant):
        """测试获取租户"""
        await memory_storage.create(sample_tenant)
        result = await memory_storage.get(sample_tenant.id)
        assert result is not None
        assert result.id == sample_tenant.id

    @pytest.mark.asyncio
    async def test_get_nonexistent_tenant(self, memory_storage):
        """测试获取不存在的租户"""
        result = await memory_storage.get("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_name(self, memory_storage, sample_tenant):
        """测试通过名称获取租户"""
        await memory_storage.create(sample_tenant)
        result = await memory_storage.get_by_name(sample_tenant.name)
        assert result is not None
        assert result.id == sample_tenant.id

    @pytest.mark.asyncio
    async def test_get_by_name_nonexistent(self, memory_storage):
        """测试通过名称获取不存在的租户"""
        result = await memory_storage.get_by_name("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_update_tenant(self, memory_storage, sample_tenant):
        """测试更新租户"""
        await memory_storage.create(sample_tenant)
        sample_tenant.display_name = "Updated Name"
        sample_tenant.tier = TenantTier.PROFESSIONAL
        result = await memory_storage.update(sample_tenant)
        assert result.display_name == "Updated Name"
        assert result.tier == TenantTier.PROFESSIONAL

    @pytest.mark.asyncio
    async def test_update_tenant_name(self, memory_storage, sample_tenant):
        """测试更新租户名称"""
        await memory_storage.create(sample_tenant)
        old_name = sample_tenant.name

        # 创建副本进行更新，避免直接修改存储中的对象
        updated_tenant = sample_tenant.model_copy()
        updated_tenant.name = "new-name"
        await memory_storage.update(updated_tenant)

        # 旧名称应该找不到
        assert await memory_storage.get_by_name(old_name) is None
        # 新名称应该能找到
        assert await memory_storage.get_by_name("new-name") is not None

    @pytest.mark.asyncio
    async def test_update_nonexistent_tenant(self, memory_storage, sample_tenant):
        """测试更新不存在的租户"""
        with pytest.raises(ValueError, match="租户不存在"):
            await memory_storage.update(sample_tenant)

    @pytest.mark.asyncio
    async def test_delete_tenant(self, memory_storage, sample_tenant):
        """测试删除租户"""
        await memory_storage.create(sample_tenant)
        result = await memory_storage.delete(sample_tenant.id)
        assert result is True
        assert await memory_storage.get(sample_tenant.id) is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_tenant(self, memory_storage):
        """测试删除不存在的租户"""
        result = await memory_storage.delete("nonexistent")
        assert result is False

    # ------------------------------------------------------------------------
    # 列表和统计测试
    # ------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_list_tenants(self, memory_storage, sample_tenant, sample_tenant_2):
        """测试列出租户"""
        await memory_storage.create(sample_tenant)
        await memory_storage.create(sample_tenant_2)
        result = await memory_storage.list()
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_list_tenants_by_status(self, memory_storage, sample_tenant, sample_tenant_2):
        """测试按状态过滤租户"""
        await memory_storage.create(sample_tenant)  # ACTIVE
        await memory_storage.create(sample_tenant_2)  # TRIAL
        result = await memory_storage.list(status=TenantStatus.ACTIVE)
        assert len(result) == 1
        assert result[0].id == sample_tenant.id

    @pytest.mark.asyncio
    async def test_list_tenants_by_tier(self, memory_storage, sample_tenant, sample_tenant_2):
        """测试按套餐过滤租户"""
        await memory_storage.create(sample_tenant)  # BASIC
        await memory_storage.create(sample_tenant_2)  # FREE
        result = await memory_storage.list(tier=TenantTier.BASIC)
        assert len(result) == 1
        assert result[0].id == sample_tenant.id

    @pytest.mark.asyncio
    async def test_list_tenants_pagination(self, memory_storage):
        """测试分页"""
        for i in range(5):
            tenant = Tenant(
                id=f"tenant-{i}",
                name=f"test-tenant-{i}",
                display_name=f"Test Tenant {i}",
            )
            await memory_storage.create(tenant)

        result = await memory_storage.list(offset=2, limit=2)
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_count_tenants(self, memory_storage, sample_tenant, sample_tenant_2):
        """测试统计租户数量"""
        await memory_storage.create(sample_tenant)
        await memory_storage.create(sample_tenant_2)
        count = await memory_storage.count()
        assert count == 2

    @pytest.mark.asyncio
    async def test_count_tenants_by_status(self, memory_storage, sample_tenant, sample_tenant_2):
        """测试按状态统计租户数量"""
        await memory_storage.create(sample_tenant)  # ACTIVE
        await memory_storage.create(sample_tenant_2)  # TRIAL
        count = await memory_storage.count(status=TenantStatus.ACTIVE)
        assert count == 1

    # ------------------------------------------------------------------------
    # 配额和配置测试
    # ------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_get_quota(self, memory_storage, sample_tenant):
        """测试获取配额"""
        await memory_storage.create(sample_tenant)
        quota = await memory_storage.get_quota(sample_tenant.id)
        assert quota is not None
        assert quota.max_agents == sample_tenant.quota.max_agents

    @pytest.mark.asyncio
    async def test_get_quota_nonexistent(self, memory_storage):
        """测试获取不存在租户的配额"""
        quota = await memory_storage.get_quota("nonexistent")
        assert quota is None

    @pytest.mark.asyncio
    async def test_update_quota(self, memory_storage, sample_tenant):
        """测试更新配额"""
        await memory_storage.create(sample_tenant)
        new_quota = TenantQuota(max_agents=50, max_sessions=500)
        result = await memory_storage.update_quota(sample_tenant.id, new_quota)
        assert result is True

        quota = await memory_storage.get_quota(sample_tenant.id)
        assert quota.max_agents == 50
        assert quota.max_sessions == 500

    @pytest.mark.asyncio
    async def test_update_quota_nonexistent(self, memory_storage):
        """测试更新不存在租户的配额"""
        new_quota = TenantQuota(max_agents=50)
        result = await memory_storage.update_quota("nonexistent", new_quota)
        assert result is False

    @pytest.mark.asyncio
    async def test_get_config(self, memory_storage, sample_tenant):
        """测试获取配置"""
        await memory_storage.create(sample_tenant)
        config = await memory_storage.get_config(sample_tenant.id)
        assert config is not None

    @pytest.mark.asyncio
    async def test_update_config(self, memory_storage, sample_tenant):
        """测试更新配置"""
        await memory_storage.create(sample_tenant)
        new_config = TenantConfig(default_model="gpt-4")
        result = await memory_storage.update_config(sample_tenant.id, new_config)
        assert result is True

        config = await memory_storage.get_config(sample_tenant.id)
        assert config.default_model == "gpt-4"

    # ------------------------------------------------------------------------
    # 使用统计测试
    # ------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_record_usage(self, memory_storage, sample_tenant):
        """测试记录使用统计"""
        await memory_storage.create(sample_tenant)
        now = datetime.now()
        usage = TenantUsage(
            tenant_id=sample_tenant.id,
            period="daily",
            period_start=now,
            period_end=now + timedelta(days=1),
            total_tokens=1000,
            api_calls=50,
        )
        result = await memory_storage.record_usage(usage)
        assert result is True

    @pytest.mark.asyncio
    async def test_get_usage(self, memory_storage, sample_tenant):
        """测试获取使用统计"""
        await memory_storage.create(sample_tenant)
        now = datetime.now()

        # 记录多条使用统计
        for i in range(3):
            usage = TenantUsage(
                tenant_id=sample_tenant.id,
                period="daily",
                period_start=now + timedelta(days=i),
                period_end=now + timedelta(days=i + 1),
                total_tokens=1000 * (i + 1),
            )
            await memory_storage.record_usage(usage)

        usages = await memory_storage.get_usage(sample_tenant.id, period="daily")
        assert len(usages) == 3

    @pytest.mark.asyncio
    async def test_get_usage_with_date_filter(self, memory_storage, sample_tenant):
        """测试按日期过滤使用统计"""
        await memory_storage.create(sample_tenant)
        now = datetime.now()

        for i in range(5):
            usage = TenantUsage(
                tenant_id=sample_tenant.id,
                period="daily",
                period_start=now + timedelta(days=i),
                period_end=now + timedelta(days=i + 1),
            )
            await memory_storage.record_usage(usage)

        usages = await memory_storage.get_usage(
            sample_tenant.id,
            period="daily",
            start_date=now + timedelta(days=2),
            end_date=now + timedelta(days=4),
        )
        assert len(usages) == 2

    # ------------------------------------------------------------------------
    # 事件测试
    # ------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_record_event(self, memory_storage, sample_tenant):
        """测试记录事件"""
        await memory_storage.create(sample_tenant)
        event = TenantEvent(
            tenant_id=sample_tenant.id,
            event_type=TenantEventType.CREATED,
            message="租户创建成功",
        )
        result = await memory_storage.record_event(event)
        assert result is True

    @pytest.mark.asyncio
    async def test_get_events(self, memory_storage, sample_tenant):
        """测试获取事件"""
        await memory_storage.create(sample_tenant)

        # 记录多个事件
        for event_type in [TenantEventType.CREATED, TenantEventType.UPDATED, TenantEventType.CONFIG_UPDATED]:
            event = TenantEvent(
                tenant_id=sample_tenant.id,
                event_type=event_type,
            )
            await memory_storage.record_event(event)

        events = await memory_storage.get_events(sample_tenant.id)
        assert len(events) == 3

    @pytest.mark.asyncio
    async def test_get_events_by_type(self, memory_storage, sample_tenant):
        """测试按类型过滤事件"""
        await memory_storage.create(sample_tenant)

        for event_type in [TenantEventType.CREATED, TenantEventType.UPDATED, TenantEventType.UPDATED]:
            event = TenantEvent(
                tenant_id=sample_tenant.id,
                event_type=event_type,
            )
            await memory_storage.record_event(event)

        events = await memory_storage.get_events(
            sample_tenant.id,
            event_type=TenantEventType.UPDATED,
        )
        assert len(events) == 2

    @pytest.mark.asyncio
    async def test_get_events_pagination(self, memory_storage, sample_tenant):
        """测试事件分页"""
        await memory_storage.create(sample_tenant)

        for i in range(10):
            event = TenantEvent(
                tenant_id=sample_tenant.id,
                event_type=TenantEventType.UPDATED,
            )
            await memory_storage.record_event(event)

        events = await memory_storage.get_events(sample_tenant.id, offset=3, limit=3)
        assert len(events) == 3


# ============================================================================
# FileTenantStorage 测试
# ============================================================================


class TestFileTenantStorage:
    """文件存储测试"""

    @pytest.mark.asyncio
    async def test_create_and_get_tenant(self, file_storage, sample_tenant):
        """测试创建和获取租户"""
        await file_storage.create(sample_tenant)
        result = await file_storage.get(sample_tenant.id)
        assert result is not None
        assert result.id == sample_tenant.id
        assert result.name == sample_tenant.name

    @pytest.mark.asyncio
    async def test_persistence(self, tmp_path, sample_tenant):
        """测试持久化"""
        # 创建存储并添加租户
        storage1 = FileTenantStorage(tmp_path)
        await storage1.create(sample_tenant)

        # 创建新的存储实例，应该能读取到数据
        storage2 = FileTenantStorage(tmp_path)
        result = await storage2.get(sample_tenant.id)
        assert result is not None
        assert result.id == sample_tenant.id

    @pytest.mark.asyncio
    async def test_update_tenant(self, file_storage, sample_tenant):
        """测试更新租户"""
        await file_storage.create(sample_tenant)
        sample_tenant.display_name = "Updated Name"
        await file_storage.update(sample_tenant)

        result = await file_storage.get(sample_tenant.id)
        assert result.display_name == "Updated Name"

    @pytest.mark.asyncio
    async def test_delete_tenant(self, file_storage, sample_tenant):
        """测试删除租户"""
        await file_storage.create(sample_tenant)
        result = await file_storage.delete(sample_tenant.id)
        assert result is True
        assert await file_storage.get(sample_tenant.id) is None

    @pytest.mark.asyncio
    async def test_list_tenants(self, file_storage, sample_tenant, sample_tenant_2):
        """测试列出租户"""
        await file_storage.create(sample_tenant)
        await file_storage.create(sample_tenant_2)
        result = await file_storage.list()
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_quota_operations(self, file_storage, sample_tenant):
        """测试配额操作"""
        await file_storage.create(sample_tenant)

        # 更新配额
        new_quota = TenantQuota(max_agents=100)
        await file_storage.update_quota(sample_tenant.id, new_quota)

        # 验证更新
        quota = await file_storage.get_quota(sample_tenant.id)
        assert quota.max_agents == 100

    @pytest.mark.asyncio
    async def test_config_operations(self, file_storage, sample_tenant):
        """测试配置操作"""
        await file_storage.create(sample_tenant)

        # 更新配置
        new_config = TenantConfig(default_model="claude-3")
        await file_storage.update_config(sample_tenant.id, new_config)

        # 验证更新
        config = await file_storage.get_config(sample_tenant.id)
        assert config.default_model == "claude-3"

    @pytest.mark.asyncio
    async def test_usage_operations(self, file_storage, sample_tenant):
        """测试使用统计操作"""
        await file_storage.create(sample_tenant)
        now = datetime.now()

        # 记录使用统计
        usage = TenantUsage(
            tenant_id=sample_tenant.id,
            period="daily",
            period_start=now,
            period_end=now + timedelta(days=1),
            total_tokens=5000,
        )
        await file_storage.record_usage(usage)

        # 获取使用统计
        usages = await file_storage.get_usage(sample_tenant.id)
        assert len(usages) == 1
        assert usages[0].total_tokens == 5000

    @pytest.mark.asyncio
    async def test_event_operations(self, file_storage, sample_tenant):
        """测试事件操作"""
        await file_storage.create(sample_tenant)

        # 记录事件
        event = TenantEvent(
            tenant_id=sample_tenant.id,
            event_type=TenantEventType.CREATED,
            message="租户创建",
        )
        await file_storage.record_event(event)

        # 获取事件
        events = await file_storage.get_events(sample_tenant.id)
        assert len(events) == 1
        assert events[0].event_type == TenantEventType.CREATED

    @pytest.mark.asyncio
    async def test_usage_persistence(self, tmp_path, sample_tenant):
        """测试使用统计持久化"""
        now = datetime.now()

        # 创建存储并记录使用统计
        storage1 = FileTenantStorage(tmp_path)
        await storage1.create(sample_tenant)
        usage = TenantUsage(
            tenant_id=sample_tenant.id,
            period="daily",
            period_start=now,
            period_end=now + timedelta(days=1),
            total_tokens=3000,
        )
        await storage1.record_usage(usage)

        # 创建新的存储实例，应该能读取到数据
        storage2 = FileTenantStorage(tmp_path)
        usages = await storage2.get_usage(sample_tenant.id)
        assert len(usages) == 1
        assert usages[0].total_tokens == 3000

    @pytest.mark.asyncio
    async def test_event_persistence(self, tmp_path, sample_tenant):
        """测试事件持久化"""
        # 创建存储并记录事件
        storage1 = FileTenantStorage(tmp_path)
        await storage1.create(sample_tenant)
        event = TenantEvent(
            tenant_id=sample_tenant.id,
            event_type=TenantEventType.TIER_CHANGED,
            old_value="free",
            new_value="basic",
        )
        await storage1.record_event(event)

        # 创建新的存储实例，应该能读取到数据
        storage2 = FileTenantStorage(tmp_path)
        events = await storage2.get_events(sample_tenant.id)
        assert len(events) == 1
        assert events[0].event_type == TenantEventType.TIER_CHANGED
