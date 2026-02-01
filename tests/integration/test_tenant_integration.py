"""租户集成测试

测试租户系统与 Agent Runtime 和 Gateway Server 的集成。
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from lurkbot.tenants import (
    TenantManager,
    MemoryTenantStorage,
    TenantTier,
    TenantStatus,
    QuotaManager,
    QuotaType,
)
from lurkbot.tenants.errors import (
    QuotaExceededError,
    RateLimitedError,
    ConcurrentLimitError,
    PolicyDeniedError,
    TenantNotFoundError,
    TenantInactiveError,
)
from lurkbot.tenants.guards import QuotaGuard, PolicyGuard, configure_guards


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
async def test_tenant(tenant_manager):
    """创建测试租户"""
    tenant = await tenant_manager.create_tenant(
        name="test-tenant",
        display_name="Test Tenant",
        tier=TenantTier.BASIC,
    )
    return tenant


@pytest.fixture
def quota_guard(tenant_manager, quota_manager):
    """创建配额守卫"""
    guard = QuotaGuard(tenant_manager=tenant_manager, quota_manager=quota_manager)
    return guard


@pytest.fixture
def policy_guard():
    """创建策略守卫"""
    return PolicyGuard()


# ============================================================================
# Agent Runtime 集成测试
# ============================================================================


class TestAgentRuntimeIntegration:
    """Agent Runtime 租户集成测试"""

    @pytest.mark.asyncio
    async def test_agent_context_with_tenant_id(self):
        """测试 AgentContext 包含 tenant_id"""
        from lurkbot.agents.types import AgentContext

        context = AgentContext(
            session_id="test-session",
            tenant_id="tenant_123",
        )

        assert context.tenant_id == "tenant_123"
        assert context.session_id == "test-session"

    @pytest.mark.asyncio
    async def test_agent_context_without_tenant_id(self):
        """测试 AgentContext 不包含 tenant_id（向后兼容）"""
        from lurkbot.agents.types import AgentContext

        context = AgentContext(
            session_id="test-session",
        )

        assert context.tenant_id is None

    @pytest.mark.asyncio
    async def test_chat_request_with_tenant_id(self):
        """测试 ChatRequest 包含 tenant_id"""
        from lurkbot.agents.api import ChatRequest

        request = ChatRequest(
            message="Hello",
            tenant_id="tenant_123",
        )

        assert request.tenant_id == "tenant_123"

    @pytest.mark.asyncio
    async def test_chat_request_without_tenant_id(self):
        """测试 ChatRequest 不包含 tenant_id（向后兼容）"""
        from lurkbot.agents.api import ChatRequest

        request = ChatRequest(
            message="Hello",
        )

        assert request.tenant_id is None


# ============================================================================
# Gateway Server 集成测试
# ============================================================================


class TestGatewayServerIntegration:
    """Gateway Server 租户集成测试"""

    @pytest.mark.asyncio
    async def test_gateway_connection_with_tenant_id(self):
        """测试 GatewayConnection 包含 tenant_id"""
        from lurkbot.gateway.server import GatewayConnection

        mock_websocket = MagicMock()
        connection = GatewayConnection(
            websocket=mock_websocket,
            conn_id="test-conn",
        )

        # 初始状态
        assert connection.tenant_id is None

        # 设置 tenant_id
        connection.tenant_id = "tenant_123"
        assert connection.tenant_id == "tenant_123"


# ============================================================================
# 配额检查流程测试
# ============================================================================


class TestQuotaCheckFlow:
    """配额检查流程测试"""

    @pytest.mark.asyncio
    async def test_quota_check_success(self, quota_guard, test_tenant):
        """测试配额检查成功"""
        # 应该不抛出异常
        await quota_guard.check_and_record(
            tenant_id=test_tenant.id,
            quota_type=QuotaType.API_CALLS_PER_DAY,
            amount=1,
        )

    @pytest.mark.asyncio
    async def test_rate_limit_check_success(self, quota_guard, test_tenant):
        """测试速率限制检查成功"""
        # 应该不抛出异常
        await quota_guard.check_rate_limit(test_tenant.id)

    @pytest.mark.asyncio
    async def test_concurrent_slot_acquire_release(self, quota_guard, test_tenant):
        """测试并发槽位获取和释放"""
        # 获取槽位
        result = await quota_guard.acquire_concurrent_slot(test_tenant.id)
        assert result is True

        # 释放槽位
        await quota_guard.release_concurrent_slot(test_tenant.id)

    @pytest.mark.asyncio
    async def test_concurrent_slot_context_manager(self, quota_guard, test_tenant):
        """测试并发槽位上下文管理器"""
        async with quota_guard.concurrent_slot_context(test_tenant.id):
            # 在上下文中
            pass
        # 上下文结束后槽位应该被释放

    @pytest.mark.asyncio
    async def test_rate_limit_context_manager(self, quota_guard, test_tenant):
        """测试速率限制上下文管理器"""
        async with quota_guard.rate_limit_context(test_tenant.id):
            # 在上下文中
            pass

    @pytest.mark.asyncio
    async def test_token_usage_recording(self, quota_guard, test_tenant):
        """测试 Token 使用量记录"""
        await quota_guard.record_token_usage(
            tenant_id=test_tenant.id,
            input_tokens=100,
            output_tokens=200,
        )


# ============================================================================
# 策略评估流程测试
# ============================================================================


class TestPolicyEvaluationFlow:
    """策略评估流程测试"""

    @pytest.mark.asyncio
    async def test_check_permission_without_engine(self, policy_guard):
        """测试无策略引擎时的权限检查（默认允许）"""
        result = await policy_guard.check_permission(
            principal="user:123",
            resource="method:chat",
            action="execute",
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_require_permission_without_engine(self, policy_guard):
        """测试无策略引擎时的权限要求（默认允许）"""
        # 应该不抛出异常
        await policy_guard.require_permission(
            principal="user:123",
            resource="method:chat",
            action="execute",
        )

    @pytest.mark.asyncio
    async def test_evaluate_without_engine(self, policy_guard):
        """测试无策略引擎时的评估"""
        result = await policy_guard.evaluate(
            principal="user:123",
            resource="method:chat",
            action="execute",
        )
        assert result["allowed"] is True
        assert result["matched_policy"] is None

    @pytest.mark.asyncio
    async def test_policy_guard_with_engine(self):
        """测试带策略引擎的策略守卫"""
        from lurkbot.security.policy_engine import PolicyEngine
        from lurkbot.security.policy_dsl import Policy, PolicyEffect

        engine = PolicyEngine()

        # 添加允许策略
        allow_policy = Policy(
            name="allow-chat",
            effect=PolicyEffect.ALLOW,
            principals=["user:*"],
            resources=["method:chat"],
            actions=["execute"],
        )
        await engine.add_policy(allow_policy)

        guard = PolicyGuard(policy_engine=engine)

        result = await guard.check_permission(
            principal="user:123",
            resource="method:chat",
            action="execute",
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_policy_guard_deny(self):
        """测试策略拒绝"""
        from lurkbot.security.policy_engine import PolicyEngine
        from lurkbot.security.policy_dsl import Policy, PolicyEffect

        engine = PolicyEngine()

        # 添加拒绝策略
        deny_policy = Policy(
            name="deny-admin",
            effect=PolicyEffect.DENY,
            principals=["user:*"],
            resources=["method:admin*"],
            actions=["*"],
        )
        await engine.add_policy(deny_policy)

        guard = PolicyGuard(policy_engine=engine)

        with pytest.raises(PolicyDeniedError):
            await guard.require_permission(
                principal="user:123",
                resource="method:admin.delete",
                action="execute",
            )


# ============================================================================
# 错误处理测试
# ============================================================================


class TestErrorHandling:
    """错误处理测试"""

    @pytest.mark.asyncio
    async def test_tenant_not_found_error(self, quota_guard):
        """测试租户不存在错误"""
        with pytest.raises(TenantNotFoundError) as exc_info:
            await quota_guard.check_rate_limit("nonexistent_tenant")

        assert exc_info.value.tenant_id == "nonexistent_tenant"

    @pytest.mark.asyncio
    async def test_tenant_inactive_error(self, tenant_manager, quota_guard):
        """测试租户不可用错误"""
        # 创建并暂停租户
        tenant = await tenant_manager.create_tenant(
            name="inactive-tenant",
            display_name="Inactive Tenant",
        )
        await tenant_manager.suspend_tenant(tenant.id, reason="Test suspension")

        with pytest.raises(TenantInactiveError) as exc_info:
            await quota_guard.check_rate_limit(tenant.id)

        assert exc_info.value.tenant_id == tenant.id

    @pytest.mark.asyncio
    async def test_error_to_dict(self):
        """测试错误转换为字典"""
        error = QuotaExceededError(
            message="配额超限",
            tenant_id="tenant_123",
            quota_type="tokens_per_day",
            current=1000,
            limit=500,
        )

        error_dict = error.to_dict()
        assert error_dict["code"] == "QUOTA_EXCEEDED"
        assert error_dict["tenant_id"] == "tenant_123"
        assert error_dict["details"]["quota_type"] == "tokens_per_day"
        assert error_dict["details"]["current"] == 1000
        assert error_dict["details"]["limit"] == 500


# ============================================================================
# 全局配置测试
# ============================================================================


class TestGlobalConfiguration:
    """全局配置测试"""

    @pytest.mark.asyncio
    async def test_configure_guards(self, tenant_manager):
        """测试配置全局守卫"""
        from lurkbot.security.policy_engine import PolicyEngine

        engine = PolicyEngine()

        configure_guards(
            tenant_manager=tenant_manager,
            policy_engine=engine,
        )

        # 验证配置生效
        from lurkbot.tenants.guards import get_quota_guard, get_policy_guard

        quota_guard = get_quota_guard()
        policy_guard = get_policy_guard()

        assert quota_guard._tenant_manager is tenant_manager
        assert policy_guard._policy_engine is engine
