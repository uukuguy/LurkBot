"""策略引擎

提供权限策略评估、继承和管理功能。
"""

from __future__ import annotations

import asyncio
import time as time_module
from collections import defaultdict
from typing import Any, Callable

from loguru import logger

from .policy_dsl import (
    EvaluationContext,
    Policy,
    PolicyConditions,
    PolicyDecision,
    PolicyEffect,
)


# ============================================================================
# 策略存储
# ============================================================================


class PolicyStore:
    """策略存储

    管理策略的增删改查。
    """

    def __init__(self) -> None:
        self._policies: dict[str, Policy] = {}
        self._lock = asyncio.Lock()

    async def add_policy(self, policy: Policy) -> None:
        """添加策略

        Args:
            policy: 策略定义
        """
        async with self._lock:
            self._policies[policy.name] = policy
            logger.debug(f"添加策略: {policy.name}")

    async def remove_policy(self, name: str) -> bool:
        """移除策略

        Args:
            name: 策略名称

        Returns:
            是否移除成功
        """
        async with self._lock:
            if name in self._policies:
                del self._policies[name]
                logger.debug(f"移除策略: {name}")
                return True
            return False

    async def get_policy(self, name: str) -> Policy | None:
        """获取策略

        Args:
            name: 策略名称

        Returns:
            策略定义
        """
        return self._policies.get(name)

    async def list_policies(
        self,
        enabled_only: bool = True,
        tag: str | None = None,
    ) -> list[Policy]:
        """列出策略

        Args:
            enabled_only: 是否只返回启用的策略
            tag: 标签过滤

        Returns:
            策略列表
        """
        policies = list(self._policies.values())

        if enabled_only:
            policies = [p for p in policies if p.enabled]

        if tag:
            policies = [p for p in policies if tag in p.tags]

        # 按优先级排序（高优先级在前）
        policies.sort(key=lambda p: p.priority, reverse=True)
        return policies

    async def clear(self) -> None:
        """清空所有策略"""
        async with self._lock:
            self._policies.clear()

    def count(self) -> int:
        """获取策略数量"""
        return len(self._policies)


# ============================================================================
# 策略缓存
# ============================================================================


class PolicyCache:
    """策略评估缓存

    缓存策略评估结果以提高性能。
    """

    def __init__(self, max_size: int = 1000, ttl_seconds: int = 300) -> None:
        """初始化缓存

        Args:
            max_size: 最大缓存数量
            ttl_seconds: 缓存过期时间（秒）
        """
        self._cache: dict[str, tuple[PolicyDecision, float]] = {}
        self._max_size = max_size
        self._ttl_seconds = ttl_seconds
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> PolicyDecision | None:
        """获取缓存

        Args:
            key: 缓存键

        Returns:
            缓存的决策结果
        """
        if key in self._cache:
            decision, timestamp = self._cache[key]
            if time_module.time() - timestamp < self._ttl_seconds:
                self._hits += 1
                return decision
            else:
                del self._cache[key]

        self._misses += 1
        return None

    def put(self, key: str, decision: PolicyDecision) -> None:
        """写入缓存

        Args:
            key: 缓存键
            decision: 决策结果
        """
        # 超过最大大小时清理旧条目
        if len(self._cache) >= self._max_size:
            self._evict()

        self._cache[key] = (decision, time_module.time())

    def invalidate(self, key: str | None = None) -> None:
        """使缓存失效

        Args:
            key: 缓存键（None 表示清空全部）
        """
        if key is None:
            self._cache.clear()
        elif key in self._cache:
            del self._cache[key]

    def stats(self) -> dict[str, Any]:
        """获取缓存统计

        Returns:
            统计信息
        """
        total = self._hits + self._misses
        return {
            "size": len(self._cache),
            "max_size": self._max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": self._hits / total if total > 0 else 0.0,
        }

    def _evict(self) -> None:
        """驱逐旧条目"""
        now = time_module.time()

        # 先删除过期条目
        expired = [k for k, (_, t) in self._cache.items() if now - t >= self._ttl_seconds]
        for k in expired:
            del self._cache[k]

        # 如果仍然超过限制，删除最旧的 25%
        if len(self._cache) >= self._max_size:
            sorted_items = sorted(self._cache.items(), key=lambda x: x[1][1])
            to_remove = len(self._cache) // 4
            for k, _ in sorted_items[:to_remove]:
                del self._cache[k]


# ============================================================================
# 策略引擎
# ============================================================================


class PolicyEngine:
    """策略引擎

    评估权限策略，支持：
    - 多策略优先级评估
    - 条件匹配（时间、IP、属性）
    - 权限继承链
    - 评估缓存
    - 审计追踪
    """

    # 默认策略：无匹配时拒绝
    DEFAULT_EFFECT = PolicyEffect.DENY

    def __init__(
        self,
        store: PolicyStore | None = None,
        cache: PolicyCache | None = None,
        enable_cache: bool = True,
    ) -> None:
        """初始化策略引擎

        Args:
            store: 策略存储
            cache: 策略缓存
            enable_cache: 是否启用缓存
        """
        self._store = store or PolicyStore()
        self._cache = (cache or PolicyCache()) if enable_cache else None
        self._audit_handlers: list[Callable[[EvaluationContext, PolicyDecision], Any]] = []

        # 继承链: child -> [parents]
        self._inheritance: dict[str, list[str]] = {}
        self._lock = asyncio.Lock()

    # ========================================================================
    # 策略管理
    # ========================================================================

    async def add_policy(self, policy: Policy) -> None:
        """添加策略

        Args:
            policy: 策略定义
        """
        await self._store.add_policy(policy)
        if self._cache:
            self._cache.invalidate()

    async def remove_policy(self, name: str) -> bool:
        """移除策略

        Args:
            name: 策略名称

        Returns:
            是否移除成功
        """
        result = await self._store.remove_policy(name)
        if result and self._cache:
            self._cache.invalidate()
        return result

    async def get_policy(self, name: str) -> Policy | None:
        """获取策略

        Args:
            name: 策略名称

        Returns:
            策略定义
        """
        return await self._store.get_policy(name)

    async def list_policies(self, **kwargs) -> list[Policy]:
        """列出策略"""
        return await self._store.list_policies(**kwargs)

    # ========================================================================
    # 策略评估
    # ========================================================================

    async def evaluate(self, context: EvaluationContext) -> PolicyDecision:
        """评估策略

        Args:
            context: 评估上下文

        Returns:
            策略决策
        """
        start_time = time_module.time()

        # 检查缓存
        cache_key = self._make_cache_key(context)
        if self._cache:
            cached = self._cache.get(cache_key)
            if cached is not None:
                return cached

        # 获取所有启用的策略
        policies = await self._store.list_policies(enabled_only=True)

        # 收集所有主体标识
        principals = context.get_all_principals()

        # 评估所有匹配的策略
        matched_decisions: list[tuple[Policy, PolicyDecision]] = []

        for policy in policies:
            decision = self._evaluate_single(policy, context, principals)
            if decision is not None:
                matched_decisions.append((policy, decision))

        # 确定最终决策
        final_decision = self._resolve_conflicts(matched_decisions)

        # 计算耗时
        elapsed_ms = (time_module.time() - start_time) * 1000
        final_decision.evaluation_time_ms = elapsed_ms

        # 写入缓存
        if self._cache:
            self._cache.put(cache_key, final_decision)

        # 触发审计
        await self._audit(context, final_decision)

        return final_decision

    async def is_allowed(
        self,
        principal: str,
        resource: str,
        action: str,
        **kwargs,
    ) -> bool:
        """快速检查是否允许

        Args:
            principal: 主体标识
            resource: 资源标识
            action: 操作标识
            **kwargs: 其他上下文参数

        Returns:
            是否允许
        """
        context = EvaluationContext(
            principal=principal,
            resource=resource,
            action=action,
            **kwargs,
        )
        decision = await self.evaluate(context)
        return decision.allowed

    # ========================================================================
    # 继承管理
    # ========================================================================

    async def set_inheritance(self, child: str, parents: list[str]) -> None:
        """设置权限继承关系

        Args:
            child: 子主体
            parents: 父主体列表
        """
        async with self._lock:
            self._inheritance[child] = parents
            if self._cache:
                self._cache.invalidate()

    async def get_inheritance(self, principal: str) -> list[str]:
        """获取继承链

        Args:
            principal: 主体标识

        Returns:
            所有继承的主体列表（包括间接继承）
        """
        result = []
        visited = set()
        self._collect_parents(principal, result, visited)
        return result

    def _collect_parents(
        self,
        principal: str,
        result: list[str],
        visited: set[str],
    ) -> None:
        """收集所有父主体（递归）

        Args:
            principal: 当前主体
            result: 结果列表
            visited: 已访问集合（防止循环）
        """
        if principal in visited:
            return
        visited.add(principal)

        parents = self._inheritance.get(principal, [])
        for parent in parents:
            result.append(parent)
            self._collect_parents(parent, result, visited)

    # ========================================================================
    # 内部方法
    # ========================================================================

    def _evaluate_single(
        self,
        policy: Policy,
        context: EvaluationContext,
        principals: list[str],
    ) -> PolicyDecision | None:
        """评估单个策略

        Args:
            policy: 策略定义
            context: 评估上下文
            principals: 所有主体标识

        Returns:
            决策结果，如果策略不匹配返回 None
        """
        # 检查主体匹配（包括继承链）
        all_principals = list(principals)
        for p in principals:
            inherited = self._inheritance.get(p, [])
            all_principals.extend(inherited)

        principal_matched = any(policy.matches_principal(p) for p in all_principals)
        if not principal_matched:
            return None

        # 检查资源匹配
        if not policy.matches_resource(context.resource):
            return None

        # 检查操作匹配
        if not policy.matches_action(context.action):
            return None

        # 检查条件
        conditions_met = True
        if policy.conditions is not None:
            conditions_met = policy.conditions.evaluate(context)

        if not conditions_met:
            return PolicyDecision(
                effect=PolicyEffect.DENY,
                matched_policy=policy.name,
                reason=f"条件不满足: {policy.name}",
                conditions_met=False,
            )

        return PolicyDecision(
            effect=policy.effect,
            matched_policy=policy.name,
            reason=f"匹配策略: {policy.name}",
            conditions_met=True,
        )

    def _resolve_conflicts(
        self,
        decisions: list[tuple[Policy, PolicyDecision]],
    ) -> PolicyDecision:
        """解决策略冲突

        策略冲突解决规则：
        1. DENY 优先于 ALLOW（同优先级）
        2. 高优先级策略覆盖低优先级
        3. 无匹配策略时使用默认效果

        Args:
            decisions: 匹配的策略和决策列表

        Returns:
            最终决策
        """
        if not decisions:
            return PolicyDecision(
                effect=self.DEFAULT_EFFECT,
                reason="无匹配策略，默认拒绝",
            )

        # 按优先级排序（高优先级在前）
        sorted_decisions = sorted(decisions, key=lambda x: x[0].priority, reverse=True)

        # 获取最高优先级
        highest_priority = sorted_decisions[0][0].priority

        # 在最高优先级中，DENY 优先
        top_decisions = [
            (p, d) for p, d in sorted_decisions if p.priority == highest_priority
        ]

        for policy, decision in top_decisions:
            if decision.effect == PolicyEffect.DENY and decision.conditions_met:
                return decision

        # 如果没有 DENY，返回第一个 ALLOW
        for policy, decision in top_decisions:
            if decision.effect == PolicyEffect.ALLOW and decision.conditions_met:
                return decision

        # 如果所有决策条件都不满足，使用默认效果
        return PolicyDecision(
            effect=self.DEFAULT_EFFECT,
            reason="所有匹配策略条件不满足，默认拒绝",
        )

    def _make_cache_key(self, context: EvaluationContext) -> str:
        """生成缓存键

        Args:
            context: 评估上下文

        Returns:
            缓存键
        """
        parts = [
            context.principal,
            context.resource,
            context.action,
            str(context.tenant_id or ""),
            "|".join(context.principal_roles),
            "|".join(context.principal_groups),
        ]
        return "::".join(parts)

    async def _audit(
        self,
        context: EvaluationContext,
        decision: PolicyDecision,
    ) -> None:
        """触发审计

        Args:
            context: 评估上下文
            decision: 决策结果
        """
        for handler in self._audit_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(context, decision)
                else:
                    handler(context, decision)
            except Exception as e:
                logger.error(f"审计处理器错误: {e}")

    # ========================================================================
    # 审计
    # ========================================================================

    def on_audit(
        self,
        handler: Callable[[EvaluationContext, PolicyDecision], Any],
    ) -> None:
        """注册审计处理器

        Args:
            handler: 审计处理函数
        """
        self._audit_handlers.append(handler)

    # ========================================================================
    # 统计
    # ========================================================================

    async def get_stats(self) -> dict[str, Any]:
        """获取引擎统计

        Returns:
            统计信息
        """
        stats: dict[str, Any] = {
            "policy_count": self._store.count(),
            "inheritance_count": len(self._inheritance),
        }

        if self._cache:
            stats["cache"] = self._cache.stats()

        return stats
