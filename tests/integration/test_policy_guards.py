"""策略守卫测试

测试 PolicyGuard 的各种方法和场景。
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from lurkbot.tenants.errors import PolicyDeniedError
from lurkbot.tenants.guards import PolicyGuard


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def policy_guard():
    """创建策略守卫（无引擎）"""
    return PolicyGuard()


@pytest.fixture
def policy_engine():
    """创建策略引擎"""
    from lurkbot.security.policy_engine import PolicyEngine
    return PolicyEngine()


@pytest.fixture
def policy_guard_with_engine(policy_engine):
    """创建带引擎的策略守卫"""
    return PolicyGuard(policy_engine=policy_engine)


# ============================================================================
# 无引擎测试
# ============================================================================


class TestPolicyGuardWithoutEngine:
    """无策略引擎时的测试"""

    @pytest.mark.asyncio
    async def test_check_permission_default_allow(self, policy_guard):
        """测试无引擎时默认允许"""
        result = await policy_guard.check_permission(
            principal="user:123",
            resource="method:chat",
            action="execute",
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_require_permission_default_allow(self, policy_guard):
        """测试无引擎时 require_permission 不抛异常"""
        # 应该不抛出异常
        await policy_guard.require_permission(
            principal="user:123",
            resource="method:chat",
            action="execute",
        )

    @pytest.mark.asyncio
    async def test_evaluate_default_result(self, policy_guard):
        """测试无引擎时的评估结果"""
        result = await policy_guard.evaluate(
            principal="user:123",
            resource="method:chat",
            action="execute",
        )

        assert result["allowed"] is True
        assert result["reason"] == "PolicyEngine not configured"
        assert result["matched_policy"] is None


# ============================================================================
# 有引擎测试 - 允许场景
# ============================================================================


class TestPolicyGuardAllow:
    """策略允许场景测试"""

    @pytest.mark.asyncio
    async def test_allow_policy_match(self, policy_engine):
        """测试允许策略匹配"""
        from lurkbot.security.policy_dsl import Policy, PolicyEffect

        # 添加允许策略
        policy = Policy(
            name="allow-chat",
            effect=PolicyEffect.ALLOW,
            principals=["user:*"],
            resources=["method:chat"],
            actions=["execute"],
        )
        await policy_engine.add_policy(policy)

        guard = PolicyGuard(policy_engine=policy_engine)

        result = await guard.check_permission(
            principal="user:123",
            resource="method:chat",
            action="execute",
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_allow_with_tenant_context(self, policy_engine):
        """测试带租户上下文的允许"""
        from lurkbot.security.policy_dsl import Policy, PolicyEffect

        policy = Policy(
            name="allow-tenant-chat",
            effect=PolicyEffect.ALLOW,
            principals=["tenant:*"],
            resources=["method:chat"],
            actions=["execute"],
        )
        await policy_engine.add_policy(policy)

        guard = PolicyGuard(policy_engine=policy_engine)

        result = await guard.check_permission(
            principal="tenant:tenant_123",
            resource="method:chat",
            action="execute",
            tenant_id="tenant_123",
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_allow_wildcard_action(self, policy_engine):
        """测试通配符操作允许"""
        from lurkbot.security.policy_dsl import Policy, PolicyEffect

        policy = Policy(
            name="allow-all-actions",
            effect=PolicyEffect.ALLOW,
            principals=["admin:*"],
            resources=["method:*"],
            actions=["*"],
        )
        await policy_engine.add_policy(policy)

        guard = PolicyGuard(policy_engine=policy_engine)

        result = await guard.check_permission(
            principal="admin:root",
            resource="method:admin.delete",
            action="execute",
        )
        assert result is True


# ============================================================================
# 有引擎测试 - 拒绝场景
# ============================================================================


class TestPolicyGuardDeny:
    """策略拒绝场景测试"""

    @pytest.mark.asyncio
    async def test_deny_policy_match(self, policy_engine):
        """测试拒绝策略匹配"""
        from lurkbot.security.policy_dsl import Policy, PolicyEffect

        policy = Policy(
            name="deny-admin",
            effect=PolicyEffect.DENY,
            principals=["user:*"],
            resources=["method:admin*"],
            actions=["*"],
        )
        await policy_engine.add_policy(policy)

        guard = PolicyGuard(policy_engine=policy_engine)

        result = await guard.check_permission(
            principal="user:123",
            resource="method:admin.delete",
            action="execute",
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_require_permission_raises_on_deny(self, policy_engine):
        """测试 require_permission 在拒绝时抛出异常"""
        from lurkbot.security.policy_dsl import Policy, PolicyEffect

        policy = Policy(
            name="deny-sensitive",
            effect=PolicyEffect.DENY,
            principals=["user:*"],
            resources=["method:sensitive*"],
            actions=["*"],
        )
        await policy_engine.add_policy(policy)

        guard = PolicyGuard(policy_engine=policy_engine)

        with pytest.raises(PolicyDeniedError) as exc_info:
            await guard.require_permission(
                principal="user:123",
                resource="method:sensitive.data",
                action="read",
                tenant_id="tenant_456",
            )

        error = exc_info.value
        assert error.principal == "user:123"
        assert error.resource == "method:sensitive.data"
        assert error.action == "read"
        assert error.tenant_id == "tenant_456"

    @pytest.mark.asyncio
    async def test_deny_takes_priority(self, policy_engine):
        """测试拒绝策略优先于允许策略"""
        from lurkbot.security.policy_dsl import Policy, PolicyEffect

        # 添加允许策略
        allow_policy = Policy(
            name="allow-all",
            effect=PolicyEffect.ALLOW,
            principals=["user:*"],
            resources=["method:*"],
            actions=["*"],
            priority=1,
        )
        await policy_engine.add_policy(allow_policy)

        # 添加拒绝策略（同优先级）
        deny_policy = Policy(
            name="deny-admin",
            effect=PolicyEffect.DENY,
            principals=["user:*"],
            resources=["method:admin*"],
            actions=["*"],
            priority=1,
        )
        await policy_engine.add_policy(deny_policy)

        guard = PolicyGuard(policy_engine=policy_engine)

        # 普通方法应该允许
        result = await guard.check_permission(
            principal="user:123",
            resource="method:chat",
            action="execute",
        )
        assert result is True

        # 管理方法应该拒绝
        result = await guard.check_permission(
            principal="user:123",
            resource="method:admin.delete",
            action="execute",
        )
        assert result is False


# ============================================================================
# 评估详情测试
# ============================================================================


class TestPolicyEvaluationDetails:
    """策略评估详情测试"""

    @pytest.mark.asyncio
    async def test_evaluate_returns_details(self, policy_engine):
        """测试评估返回详细信息"""
        from lurkbot.security.policy_dsl import Policy, PolicyEffect

        policy = Policy(
            name="test-policy",
            effect=PolicyEffect.ALLOW,
            principals=["user:*"],
            resources=["method:test"],
            actions=["execute"],
        )
        await policy_engine.add_policy(policy)

        guard = PolicyGuard(policy_engine=policy_engine)

        result = await guard.evaluate(
            principal="user:123",
            resource="method:test",
            action="execute",
        )

        assert result["allowed"] is True
        assert result["effect"] == "allow"
        assert result["matched_policy"] == "test-policy"
        assert result["conditions_met"] is True
        assert "evaluation_time_ms" in result

    @pytest.mark.asyncio
    async def test_evaluate_no_match(self, policy_engine):
        """测试无匹配策略时的评估"""
        guard = PolicyGuard(policy_engine=policy_engine)

        result = await guard.evaluate(
            principal="user:123",
            resource="method:unknown",
            action="execute",
        )

        # 无匹配策略时默认拒绝
        assert result["allowed"] is False
        assert result["matched_policy"] is None


# ============================================================================
# 配置测试
# ============================================================================


class TestPolicyGuardConfiguration:
    """PolicyGuard 配置测试"""

    @pytest.mark.asyncio
    async def test_set_policy_engine(self):
        """测试设置策略引擎"""
        from lurkbot.security.policy_engine import PolicyEngine
        from lurkbot.security.policy_dsl import Policy, PolicyEffect

        guard = PolicyGuard()

        # 无引擎时默认允许
        result = await guard.check_permission(
            principal="user:123",
            resource="method:test",
            action="execute",
        )
        assert result is True

        # 设置引擎
        engine = PolicyEngine()
        deny_policy = Policy(
            name="deny-all",
            effect=PolicyEffect.DENY,
            principals=["*"],
            resources=["*"],
            actions=["*"],
        )
        await engine.add_policy(deny_policy)

        guard.set_policy_engine(engine)

        # 设置后应该使用引擎评估
        result = await guard.check_permission(
            principal="user:123",
            resource="method:test",
            action="execute",
        )
        assert result is False


# ============================================================================
# 错误信息测试
# ============================================================================


class TestPolicyDeniedErrorDetails:
    """PolicyDeniedError 详情测试"""

    @pytest.mark.asyncio
    async def test_error_contains_all_details(self, policy_engine):
        """测试错误包含所有详情"""
        from lurkbot.security.policy_dsl import Policy, PolicyEffect

        policy = Policy(
            name="deny-test",
            effect=PolicyEffect.DENY,
            principals=["user:*"],
            resources=["method:test"],
            actions=["execute"],
        )
        await policy_engine.add_policy(policy)

        guard = PolicyGuard(policy_engine=policy_engine)

        with pytest.raises(PolicyDeniedError) as exc_info:
            await guard.require_permission(
                principal="user:test_user",
                resource="method:test",
                action="execute",
                tenant_id="tenant_abc",
            )

        error = exc_info.value
        error_dict = error.to_dict()

        assert error_dict["code"] == "POLICY_DENIED"
        assert error_dict["tenant_id"] == "tenant_abc"
        assert error_dict["details"]["principal"] == "user:test_user"
        assert error_dict["details"]["resource"] == "method:test"
        assert error_dict["details"]["action"] == "execute"
        assert error_dict["details"]["matched_policy"] == "deny-test"
