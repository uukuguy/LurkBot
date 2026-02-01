"""租户隔离测试"""

import pytest

from lurkbot.tenants import (
    Tenant,
    TenantTier,
)
from lurkbot.tenants.isolation import (
    TenantContext,
    TenantIsolation,
    get_current_tenant,
    get_current_tenant_id,
    inject_tenant_id,
    require_tenant_context,
    set_current_tenant,
)


# ============================================================================
# 测试夹具
# ============================================================================


@pytest.fixture
def isolation():
    """隔离管理器实例"""
    return TenantIsolation()


@pytest.fixture
def sample_tenant():
    """示例租户"""
    return Tenant(
        id="tenant-1",
        name="test-tenant",
        display_name="Test Tenant",
        tier=TenantTier.BASIC,
    )


@pytest.fixture
def sample_tenant_2():
    """第二个示例租户"""
    return Tenant(
        id="tenant-2",
        name="test-tenant-2",
        display_name="Test Tenant 2",
        tier=TenantTier.FREE,
    )


# ============================================================================
# TenantContext 测试
# ============================================================================


class TestTenantContext:
    """租户上下文测试"""

    def test_from_tenant(self, sample_tenant):
        """测试从租户创建上下文"""
        ctx = TenantContext.from_tenant(sample_tenant)
        assert ctx.tenant_id == sample_tenant.id
        assert ctx.tenant_name == sample_tenant.name
        assert ctx.tier == sample_tenant.tier.value

    def test_context_metadata(self, sample_tenant):
        """测试上下文元数据"""
        sample_tenant.metadata = {"key": "value"}
        ctx = TenantContext.from_tenant(sample_tenant)
        assert ctx.metadata == {"key": "value"}
        # 确保是副本
        ctx.metadata["new_key"] = "new_value"
        assert "new_key" not in sample_tenant.metadata


# ============================================================================
# 上下文变量测试
# ============================================================================


class TestContextVariables:
    """上下文变量测试"""

    def test_get_current_tenant_none(self):
        """测试获取当前租户（未设置）"""
        set_current_tenant(None)
        assert get_current_tenant() is None
        assert get_current_tenant_id() is None

    def test_set_and_get_current_tenant(self, sample_tenant):
        """测试设置和获取当前租户"""
        ctx = TenantContext.from_tenant(sample_tenant)
        set_current_tenant(ctx)
        try:
            assert get_current_tenant() == ctx
            assert get_current_tenant_id() == sample_tenant.id
        finally:
            set_current_tenant(None)


# ============================================================================
# TenantIsolation 测试
# ============================================================================


class TestTenantIsolation:
    """租户隔离管理器测试"""

    # ------------------------------------------------------------------------
    # 上下文管理测试
    # ------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_enter_tenant_context(self, isolation, sample_tenant):
        """测试进入租户上下文"""
        try:
            ctx = await isolation.enter_tenant_context(sample_tenant)
            assert ctx.tenant_id == sample_tenant.id
            assert get_current_tenant() == ctx
        finally:
            await isolation.exit_tenant_context()

    @pytest.mark.asyncio
    async def test_exit_tenant_context(self, isolation, sample_tenant):
        """测试退出租户上下文"""
        await isolation.enter_tenant_context(sample_tenant)
        await isolation.exit_tenant_context()
        assert get_current_tenant() is None

    @pytest.mark.asyncio
    async def test_tenant_context_manager(self, isolation, sample_tenant):
        """测试上下文管理器"""
        async with isolation.tenant_context(sample_tenant) as ctx:
            assert ctx.tenant_id == sample_tenant.id
            assert get_current_tenant() == ctx

        # 退出后应该为 None
        assert get_current_tenant() is None

    @pytest.mark.asyncio
    async def test_nested_context(self, isolation, sample_tenant, sample_tenant_2):
        """测试嵌套上下文"""
        async with isolation.tenant_context(sample_tenant) as ctx1:
            assert get_current_tenant_id() == sample_tenant.id

            async with isolation.tenant_context(sample_tenant_2) as ctx2:
                assert get_current_tenant_id() == sample_tenant_2.id

            # 恢复到外层上下文
            assert get_current_tenant_id() == sample_tenant.id

        assert get_current_tenant() is None

    # ------------------------------------------------------------------------
    # 资源隔离测试
    # ------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_register_resource(self, isolation, sample_tenant):
        """测试注册资源"""
        await isolation.register_resource(
            "tenant-1", "agent", "agent-1", {"name": "Test Agent"}
        )
        resource = await isolation.get_resource("tenant-1", "agent", "agent-1")
        assert resource == {"name": "Test Agent"}

    @pytest.mark.asyncio
    async def test_get_resource_nonexistent(self, isolation):
        """测试获取不存在的资源"""
        resource = await isolation.get_resource("tenant-1", "agent", "nonexistent")
        assert resource is None

    @pytest.mark.asyncio
    async def test_remove_resource(self, isolation):
        """测试移除资源"""
        await isolation.register_resource("tenant-1", "agent", "agent-1", {})
        result = await isolation.remove_resource("tenant-1", "agent", "agent-1")
        assert result is True
        assert await isolation.get_resource("tenant-1", "agent", "agent-1") is None

    @pytest.mark.asyncio
    async def test_remove_nonexistent_resource(self, isolation):
        """测试移除不存在的资源"""
        result = await isolation.remove_resource("tenant-1", "agent", "nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_list_resources(self, isolation):
        """测试列出资源"""
        await isolation.register_resource("tenant-1", "agent", "agent-1", {"id": 1})
        await isolation.register_resource("tenant-1", "agent", "agent-2", {"id": 2})
        await isolation.register_resource("tenant-1", "session", "session-1", {"id": 3})

        # 列出所有资源
        all_resources = await isolation.list_resources("tenant-1")
        assert len(all_resources) == 3

        # 按类型过滤
        agents = await isolation.list_resources("tenant-1", "agent")
        assert len(agents) == 2

        sessions = await isolation.list_resources("tenant-1", "session")
        assert len(sessions) == 1

    @pytest.mark.asyncio
    async def test_clear_tenant_resources(self, isolation):
        """测试清除租户资源"""
        await isolation.register_resource("tenant-1", "agent", "agent-1", {})
        await isolation.register_resource("tenant-1", "agent", "agent-2", {})
        await isolation.register_resource("tenant-2", "agent", "agent-1", {})

        count = await isolation.clear_tenant_resources("tenant-1")
        assert count == 2

        # tenant-1 资源应该被清除
        assert await isolation.get_resource("tenant-1", "agent", "agent-1") is None

        # tenant-2 资源应该保留
        assert await isolation.get_resource("tenant-2", "agent", "agent-1") is not None

    # ------------------------------------------------------------------------
    # 访问控制测试
    # ------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_check_resource_access_no_context(self, isolation):
        """测试无上下文时访问检查"""
        set_current_tenant(None)
        result = await isolation.check_resource_access("tenant-1", "agent", "agent-1")
        assert result is False

    @pytest.mark.asyncio
    async def test_check_resource_access_same_tenant(self, isolation, sample_tenant):
        """测试同一租户访问检查"""
        async with isolation.tenant_context(sample_tenant):
            result = await isolation.check_resource_access("tenant-1", "agent", "agent-1")
            assert result is True

    @pytest.mark.asyncio
    async def test_check_resource_access_different_tenant(self, isolation, sample_tenant):
        """测试不同租户访问检查"""
        async with isolation.tenant_context(sample_tenant):
            result = await isolation.check_resource_access("tenant-2", "agent", "agent-1")
            assert result is False

    @pytest.mark.asyncio
    async def test_ensure_tenant_access_success(self, isolation, sample_tenant):
        """测试确保访问权限成功"""
        async with isolation.tenant_context(sample_tenant):
            # 不应该抛出异常
            await isolation.ensure_tenant_access("tenant-1")

    @pytest.mark.asyncio
    async def test_ensure_tenant_access_failure(self, isolation, sample_tenant):
        """测试确保访问权限失败"""
        async with isolation.tenant_context(sample_tenant):
            with pytest.raises(PermissionError):
                await isolation.ensure_tenant_access("tenant-2")

    # ------------------------------------------------------------------------
    # 租户锁测试
    # ------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_get_tenant_lock(self, isolation):
        """测试获取租户锁"""
        lock1 = await isolation.get_tenant_lock("tenant-1")
        lock2 = await isolation.get_tenant_lock("tenant-1")
        # 应该返回相同的锁
        assert lock1 is lock2

        # 不同租户应该返回不同的锁
        lock3 = await isolation.get_tenant_lock("tenant-2")
        assert lock1 is not lock3

    @pytest.mark.asyncio
    async def test_with_tenant_lock(self, isolation):
        """测试在租户锁保护下执行"""
        counter = {"value": 0}

        async def increment():
            counter["value"] += 1
            return counter["value"]

        result = await isolation.with_tenant_lock("tenant-1", increment)
        assert result == 1
        assert counter["value"] == 1

    # ------------------------------------------------------------------------
    # 统计信息测试
    # ------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_get_isolation_stats(self, isolation):
        """测试获取隔离统计信息"""
        await isolation.register_resource("tenant-1", "agent", "agent-1", {})
        await isolation.register_resource("tenant-1", "agent", "agent-2", {})
        await isolation.register_resource("tenant-1", "session", "session-1", {})
        await isolation.register_resource("tenant-2", "agent", "agent-1", {})

        stats = await isolation.get_isolation_stats()

        assert stats["total_tenants"] == 2
        assert stats["total_resources"] == 4
        assert stats["tenants"]["tenant-1"]["resource_count"] == 3
        assert stats["tenants"]["tenant-1"]["by_type"]["agent"] == 2
        assert stats["tenants"]["tenant-1"]["by_type"]["session"] == 1
        assert stats["tenants"]["tenant-2"]["resource_count"] == 1


# ============================================================================
# 装饰器测试
# ============================================================================


class TestDecorators:
    """装饰器测试"""

    @pytest.mark.asyncio
    async def test_require_tenant_context_success(self, sample_tenant):
        """测试要求租户上下文（成功）"""
        @require_tenant_context
        async def my_func():
            return "success"

        ctx = TenantContext.from_tenant(sample_tenant)
        set_current_tenant(ctx)
        try:
            result = await my_func()
            assert result == "success"
        finally:
            set_current_tenant(None)

    @pytest.mark.asyncio
    async def test_require_tenant_context_failure(self):
        """测试要求租户上下文（失败）"""
        @require_tenant_context
        async def my_func():
            return "success"

        set_current_tenant(None)
        with pytest.raises(RuntimeError, match="需要租户上下文"):
            await my_func()

    @pytest.mark.asyncio
    async def test_inject_tenant_id(self, sample_tenant):
        """测试注入租户 ID"""
        @inject_tenant_id
        async def my_func(tenant_id=None):
            return tenant_id

        ctx = TenantContext.from_tenant(sample_tenant)
        set_current_tenant(ctx)
        try:
            result = await my_func()
            assert result == sample_tenant.id
        finally:
            set_current_tenant(None)

    @pytest.mark.asyncio
    async def test_inject_tenant_id_no_context(self):
        """测试注入租户 ID（无上下文）"""
        @inject_tenant_id
        async def my_func(tenant_id=None):
            return tenant_id

        set_current_tenant(None)
        result = await my_func()
        assert result is None

    @pytest.mark.asyncio
    async def test_inject_tenant_id_explicit(self, sample_tenant):
        """测试注入租户 ID（显式指定）"""
        @inject_tenant_id
        async def my_func(tenant_id=None):
            return tenant_id

        ctx = TenantContext.from_tenant(sample_tenant)
        set_current_tenant(ctx)
        try:
            # 显式指定应该覆盖注入
            result = await my_func(tenant_id="explicit-id")
            assert result == "explicit-id"
        finally:
            set_current_tenant(None)
