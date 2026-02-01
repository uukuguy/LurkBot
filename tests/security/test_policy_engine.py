"""策略引擎测试"""

from datetime import datetime

import pytest

from lurkbot.security.policy_dsl import (
    AttributeCondition,
    EvaluationContext,
    IPCondition,
    Policy,
    PolicyConditions,
    PolicyDecision,
    PolicyEffect,
    TimeCondition,
)
from lurkbot.security.policy_engine import (
    PolicyCache,
    PolicyEngine,
    PolicyStore,
)


# ============================================================================
# TimeCondition 测试
# ============================================================================


class TestTimeCondition:
    """时间条件测试"""

    def test_weekday_match(self):
        """测试星期几匹配"""
        cond = TimeCondition(weekdays=[1, 2, 3, 4, 5])  # 工作日
        monday = datetime(2026, 2, 2, 10, 0)  # 周一
        assert cond.evaluate(monday) is True

        sunday = datetime(2026, 2, 1, 10, 0)  # 周日
        assert cond.evaluate(sunday) is False

    def test_time_range(self):
        """测试时间范围"""
        cond = TimeCondition(after="09:00", before="18:00")
        within = datetime(2026, 2, 2, 12, 0)
        assert cond.evaluate(within) is True

        before = datetime(2026, 2, 2, 8, 0)
        assert cond.evaluate(before) is False

        after = datetime(2026, 2, 2, 19, 0)
        assert cond.evaluate(after) is False

    def test_combined_conditions(self):
        """测试组合条件"""
        cond = TimeCondition(
            after="09:00",
            before="18:00",
            weekdays=[1, 2, 3, 4, 5],
        )
        # 周一 12:00 - 应该通过
        assert cond.evaluate(datetime(2026, 2, 2, 12, 0)) is True
        # 周日 12:00 - 不应该通过
        assert cond.evaluate(datetime(2026, 2, 1, 12, 0)) is False


# ============================================================================
# IPCondition 测试
# ============================================================================


class TestIPCondition:
    """IP 条件测试"""

    def test_allowed_ips(self):
        """测试允许 IP 列表"""
        cond = IPCondition(allowed_ips=["10.0.0.1", "10.0.0.2"])
        assert cond.evaluate("10.0.0.1") is True
        assert cond.evaluate("10.0.0.3") is False

    def test_cidr_match(self):
        """测试 CIDR 匹配"""
        cond = IPCondition(in_cidrs=["10.0.0.0/8"])
        assert cond.evaluate("10.1.2.3") is True
        assert cond.evaluate("192.168.1.1") is False

    def test_not_in_cidr(self):
        """测试 CIDR 排除"""
        cond = IPCondition(not_in_cidrs=["192.168.0.0/16"])
        assert cond.evaluate("10.0.0.1") is True
        assert cond.evaluate("192.168.1.1") is False

    def test_no_ip(self):
        """测试无 IP 时默认通过"""
        cond = IPCondition(allowed_ips=["10.0.0.1"])
        assert cond.evaluate(None) is True


# ============================================================================
# AttributeCondition 测试
# ============================================================================


class TestAttributeCondition:
    """属性条件测试"""

    def test_eq_operator(self):
        """测试相等运算符"""
        cond = AttributeCondition(key="department", operator="eq", value="engineering")
        assert cond.evaluate({"department": "engineering"}) is True
        assert cond.evaluate({"department": "sales"}) is False

    def test_ne_operator(self):
        """测试不等运算符"""
        cond = AttributeCondition(key="status", operator="ne", value="blocked")
        assert cond.evaluate({"status": "active"}) is True
        assert cond.evaluate({"status": "blocked"}) is False

    def test_in_operator(self):
        """测试 in 运算符"""
        cond = AttributeCondition(
            key="role", operator="in", value=["admin", "manager"]
        )
        assert cond.evaluate({"role": "admin"}) is True
        assert cond.evaluate({"role": "user"}) is False

    def test_gt_operator(self):
        """测试大于运算符"""
        cond = AttributeCondition(key="level", operator="gt", value=5)
        assert cond.evaluate({"level": 10}) is True
        assert cond.evaluate({"level": 3}) is False

    def test_contains_operator(self):
        """测试包含运算符"""
        cond = AttributeCondition(key="tags", operator="contains", value="vip")
        assert cond.evaluate({"tags": ["vip", "active"]}) is True
        assert cond.evaluate({"tags": ["normal"]}) is False

    def test_missing_key(self):
        """测试缺失属性"""
        cond = AttributeCondition(key="missing", operator="eq", value="x")
        assert cond.evaluate({}) is False


# ============================================================================
# Policy 测试
# ============================================================================


class TestPolicy:
    """策略定义测试"""

    def test_matches_principal_wildcard(self):
        """测试主体通配符匹配"""
        policy = Policy(
            name="test",
            effect=PolicyEffect.ALLOW,
            principals=["*"],
            resources=["tool:*"],
            actions=["execute"],
        )
        assert policy.matches_principal("user:alice") is True
        assert policy.matches_principal("role:admin") is True

    def test_matches_principal_exact(self):
        """测试主体精确匹配"""
        policy = Policy(
            name="test",
            effect=PolicyEffect.ALLOW,
            principals=["user:alice"],
        )
        assert policy.matches_principal("user:alice") is True
        assert policy.matches_principal("user:bob") is False

    def test_matches_principal_prefix_wildcard(self):
        """测试主体前缀通配符"""
        policy = Policy(
            name="test",
            effect=PolicyEffect.ALLOW,
            principals=["role:*"],
        )
        assert policy.matches_principal("role:admin") is True
        assert policy.matches_principal("user:alice") is False

    def test_matches_resource(self):
        """测试资源匹配"""
        policy = Policy(
            name="test",
            effect=PolicyEffect.ALLOW,
            resources=["tool:search", "tool:calculate"],
        )
        assert policy.matches_resource("tool:search") is True
        assert policy.matches_resource("tool:delete") is False

    def test_matches_action(self):
        """测试操作匹配"""
        policy = Policy(
            name="test",
            effect=PolicyEffect.ALLOW,
            actions=["read", "write"],
        )
        assert policy.matches_action("read") is True
        assert policy.matches_action("delete") is False
        # * 通配符
        policy2 = Policy(name="test2", effect=PolicyEffect.ALLOW, actions=["*"])
        assert policy2.matches_action("anything") is True

    def test_empty_lists_match_all(self):
        """测试空列表匹配所有"""
        policy = Policy(name="test", effect=PolicyEffect.ALLOW)
        assert policy.matches_principal("anyone") is True
        assert policy.matches_resource("anything") is True
        assert policy.matches_action("whatever") is True


# ============================================================================
# PolicyStore 测试
# ============================================================================


class TestPolicyStore:
    """策略存储测试"""

    @pytest.mark.asyncio
    async def test_add_and_get(self):
        """测试添加和获取策略"""
        store = PolicyStore()
        policy = Policy(name="test", effect=PolicyEffect.ALLOW)
        await store.add_policy(policy)

        result = await store.get_policy("test")
        assert result is not None
        assert result.name == "test"

    @pytest.mark.asyncio
    async def test_remove(self):
        """测试移除策略"""
        store = PolicyStore()
        policy = Policy(name="test", effect=PolicyEffect.ALLOW)
        await store.add_policy(policy)

        result = await store.remove_policy("test")
        assert result is True
        assert await store.get_policy("test") is None

    @pytest.mark.asyncio
    async def test_list_enabled_only(self):
        """测试只列出启用的策略"""
        store = PolicyStore()
        await store.add_policy(Policy(name="p1", effect=PolicyEffect.ALLOW, enabled=True))
        await store.add_policy(Policy(name="p2", effect=PolicyEffect.DENY, enabled=False))

        policies = await store.list_policies(enabled_only=True)
        assert len(policies) == 1
        assert policies[0].name == "p1"

    @pytest.mark.asyncio
    async def test_list_sorted_by_priority(self):
        """测试按优先级排序"""
        store = PolicyStore()
        await store.add_policy(Policy(name="low", effect=PolicyEffect.ALLOW, priority=1))
        await store.add_policy(Policy(name="high", effect=PolicyEffect.ALLOW, priority=10))

        policies = await store.list_policies()
        assert policies[0].name == "high"
        assert policies[1].name == "low"


# ============================================================================
# PolicyCache 测试
# ============================================================================


class TestPolicyCache:
    """策略缓存测试"""

    def test_put_and_get(self):
        """测试写入和读取"""
        cache = PolicyCache()
        decision = PolicyDecision(effect=PolicyEffect.ALLOW, reason="test")
        cache.put("key1", decision)

        result = cache.get("key1")
        assert result is not None
        assert result.effect == PolicyEffect.ALLOW

    def test_cache_miss(self):
        """测试缓存未命中"""
        cache = PolicyCache()
        result = cache.get("nonexistent")
        assert result is None

    def test_cache_stats(self):
        """测试缓存统计"""
        cache = PolicyCache()
        decision = PolicyDecision(effect=PolicyEffect.ALLOW, reason="test")
        cache.put("key1", decision)
        cache.get("key1")  # hit
        cache.get("key2")  # miss

        stats = cache.stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["size"] == 1

    def test_invalidate_single(self):
        """测试失效单个条目"""
        cache = PolicyCache()
        decision = PolicyDecision(effect=PolicyEffect.ALLOW, reason="test")
        cache.put("key1", decision)
        cache.put("key2", decision)

        cache.invalidate("key1")
        assert cache.get("key1") is None
        assert cache.get("key2") is not None

    def test_invalidate_all(self):
        """测试失效所有条目"""
        cache = PolicyCache()
        decision = PolicyDecision(effect=PolicyEffect.ALLOW, reason="test")
        cache.put("key1", decision)
        cache.put("key2", decision)

        cache.invalidate()
        assert cache.get("key1") is None
        assert cache.get("key2") is None


# ============================================================================
# PolicyEngine 测试
# ============================================================================


class TestPolicyEngine:
    """策略引擎测试"""

    @pytest.mark.asyncio
    async def test_default_deny(self):
        """测试默认拒绝"""
        engine = PolicyEngine(enable_cache=False)
        context = EvaluationContext(
            principal="user:alice",
            resource="tool:search",
            action="execute",
        )
        decision = await engine.evaluate(context)
        assert decision.denied is True

    @pytest.mark.asyncio
    async def test_allow_policy(self):
        """测试允许策略"""
        engine = PolicyEngine(enable_cache=False)
        await engine.add_policy(Policy(
            name="allow-all",
            effect=PolicyEffect.ALLOW,
            principals=["*"],
            resources=["*"],
            actions=["*"],
        ))

        context = EvaluationContext(
            principal="user:alice",
            resource="tool:search",
            action="execute",
        )
        decision = await engine.evaluate(context)
        assert decision.allowed is True
        assert decision.matched_policy == "allow-all"

    @pytest.mark.asyncio
    async def test_deny_overrides_allow(self):
        """测试拒绝覆盖允许（同优先级）"""
        engine = PolicyEngine(enable_cache=False)
        await engine.add_policy(Policy(
            name="allow-tools",
            effect=PolicyEffect.ALLOW,
            principals=["role:*"],
            resources=["tool:*"],
            actions=["execute"],
            priority=0,
        ))
        await engine.add_policy(Policy(
            name="deny-dangerous",
            effect=PolicyEffect.DENY,
            principals=["role:*"],
            resources=["tool:delete"],
            actions=["execute"],
            priority=0,
        ))

        # 允许的工具
        ctx = EvaluationContext(
            principal="user:alice",
            principal_roles=["developer"],
            resource="tool:search",
            action="execute",
        )
        assert (await engine.evaluate(ctx)).allowed is True

        # 拒绝的工具
        ctx = EvaluationContext(
            principal="user:alice",
            principal_roles=["developer"],
            resource="tool:delete",
            action="execute",
        )
        assert (await engine.evaluate(ctx)).denied is True

    @pytest.mark.asyncio
    async def test_priority_override(self):
        """测试高优先级覆盖"""
        engine = PolicyEngine(enable_cache=False)
        await engine.add_policy(Policy(
            name="deny-all",
            effect=PolicyEffect.DENY,
            principals=["*"],
            resources=["*"],
            actions=["*"],
            priority=0,
        ))
        await engine.add_policy(Policy(
            name="admin-override",
            effect=PolicyEffect.ALLOW,
            principals=["role:admin"],
            resources=["*"],
            actions=["*"],
            priority=10,
        ))

        # 普通用户被拒绝
        ctx = EvaluationContext(
            principal="user:bob",
            resource="tool:search",
            action="execute",
        )
        assert (await engine.evaluate(ctx)).denied is True

        # admin 被允许（高优先级）
        ctx = EvaluationContext(
            principal="user:alice",
            principal_roles=["admin"],
            resource="tool:search",
            action="execute",
        )
        assert (await engine.evaluate(ctx)).allowed is True

    @pytest.mark.asyncio
    async def test_conditions_time(self):
        """测试时间条件"""
        engine = PolicyEngine(enable_cache=False)
        await engine.add_policy(Policy(
            name="work-hours-only",
            effect=PolicyEffect.ALLOW,
            principals=["*"],
            resources=["*"],
            actions=["*"],
            conditions=PolicyConditions(
                time=TimeCondition(after="09:00", before="18:00"),
            ),
        ))

        # 工作时间内
        ctx = EvaluationContext(
            principal="user:alice",
            resource="tool:search",
            action="execute",
            timestamp=datetime(2026, 2, 2, 12, 0),
        )
        decision = await engine.evaluate(ctx)
        assert decision.allowed is True

        # 非工作时间
        ctx = EvaluationContext(
            principal="user:alice",
            resource="tool:search",
            action="execute",
            timestamp=datetime(2026, 2, 2, 22, 0),
        )
        decision = await engine.evaluate(ctx)
        assert decision.denied is True

    @pytest.mark.asyncio
    async def test_conditions_ip(self):
        """测试 IP 条件"""
        engine = PolicyEngine(enable_cache=False)
        await engine.add_policy(Policy(
            name="internal-only",
            effect=PolicyEffect.ALLOW,
            principals=["*"],
            resources=["*"],
            actions=["*"],
            conditions=PolicyConditions(
                ip=IPCondition(in_cidrs=["10.0.0.0/8"]),
            ),
        ))

        # 内网 IP
        ctx = EvaluationContext(
            principal="user:alice",
            resource="tool:search",
            action="execute",
            ip_address="10.1.2.3",
        )
        assert (await engine.evaluate(ctx)).allowed is True

        # 外网 IP
        ctx = EvaluationContext(
            principal="user:alice",
            resource="tool:search",
            action="execute",
            ip_address="8.8.8.8",
        )
        assert (await engine.evaluate(ctx)).denied is True

    @pytest.mark.asyncio
    async def test_is_allowed_shortcut(self):
        """测试快捷检查方法"""
        engine = PolicyEngine(enable_cache=False)
        await engine.add_policy(Policy(
            name="allow-read",
            effect=PolicyEffect.ALLOW,
            principals=["*"],
            resources=["*"],
            actions=["read"],
        ))

        assert await engine.is_allowed("user:alice", "data:users", "read") is True
        assert await engine.is_allowed("user:alice", "data:users", "write") is False

    @pytest.mark.asyncio
    async def test_inheritance(self):
        """测试权限继承"""
        engine = PolicyEngine(enable_cache=False)

        # 设置继承关系: developer 继承 user
        await engine.set_inheritance("role:developer", ["role:user"])

        # 只允许 user 角色
        await engine.add_policy(Policy(
            name="allow-user",
            effect=PolicyEffect.ALLOW,
            principals=["role:user"],
            resources=["tool:*"],
            actions=["execute"],
        ))

        # developer 应该也能访问（通过继承）
        ctx = EvaluationContext(
            principal="user:alice",
            principal_roles=["developer"],
            resource="tool:search",
            action="execute",
        )
        decision = await engine.evaluate(ctx)
        assert decision.allowed is True

    @pytest.mark.asyncio
    async def test_cache_hit(self):
        """测试缓存命中"""
        engine = PolicyEngine(enable_cache=True)
        await engine.add_policy(Policy(
            name="allow-all",
            effect=PolicyEffect.ALLOW,
            principals=["*"],
            resources=["*"],
            actions=["*"],
        ))

        ctx = EvaluationContext(
            principal="user:alice",
            resource="tool:search",
            action="execute",
        )

        # 第一次评估
        d1 = await engine.evaluate(ctx)
        assert d1.allowed is True

        # 第二次应该命中缓存
        d2 = await engine.evaluate(ctx)
        assert d2.allowed is True

    @pytest.mark.asyncio
    async def test_audit_handler(self):
        """测试审计处理器"""
        engine = PolicyEngine(enable_cache=False)
        await engine.add_policy(Policy(
            name="allow-all",
            effect=PolicyEffect.ALLOW,
            principals=["*"],
            resources=["*"],
            actions=["*"],
        ))

        audit_records = []

        def handler(ctx, decision):
            audit_records.append((ctx, decision))

        engine.on_audit(handler)

        ctx = EvaluationContext(
            principal="user:alice",
            resource="tool:search",
            action="execute",
        )
        await engine.evaluate(ctx)

        assert len(audit_records) == 1
        assert audit_records[0][1].allowed is True

    @pytest.mark.asyncio
    async def test_get_stats(self):
        """测试获取统计"""
        engine = PolicyEngine(enable_cache=True)
        await engine.add_policy(Policy(
            name="p1", effect=PolicyEffect.ALLOW,
        ))
        await engine.add_policy(Policy(
            name="p2", effect=PolicyEffect.DENY,
        ))

        stats = await engine.get_stats()
        assert stats["policy_count"] == 2
        assert "cache" in stats

    @pytest.mark.asyncio
    async def test_tenant_principal(self):
        """测试租户主体"""
        engine = PolicyEngine(enable_cache=False)
        await engine.add_policy(Policy(
            name="tenant-policy",
            effect=PolicyEffect.ALLOW,
            principals=["tenant:tenant-1"],
            resources=["*"],
            actions=["*"],
        ))

        ctx = EvaluationContext(
            principal="user:alice",
            tenant_id="tenant-1",
            resource="tool:search",
            action="execute",
        )
        assert (await engine.evaluate(ctx)).allowed is True

        ctx = EvaluationContext(
            principal="user:bob",
            tenant_id="tenant-2",
            resource="tool:search",
            action="execute",
        )
        assert (await engine.evaluate(ctx)).denied is True

    @pytest.mark.asyncio
    async def test_attribute_conditions(self):
        """测试属性条件"""
        engine = PolicyEngine(enable_cache=False)
        await engine.add_policy(Policy(
            name="vip-only",
            effect=PolicyEffect.ALLOW,
            principals=["*"],
            resources=["premium:*"],
            actions=["*"],
            conditions=PolicyConditions(
                attributes=[
                    AttributeCondition(
                        key="level",
                        operator="gte",
                        value=5,
                    ),
                ],
            ),
        ))

        # VIP 用户
        ctx = EvaluationContext(
            principal="user:alice",
            resource="premium:analytics",
            action="read",
            attributes={"level": 10},
        )
        assert (await engine.evaluate(ctx)).allowed is True

        # 普通用户
        ctx = EvaluationContext(
            principal="user:bob",
            resource="premium:analytics",
            action="read",
            attributes={"level": 2},
        )
        assert (await engine.evaluate(ctx)).denied is True
