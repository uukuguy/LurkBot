"""策略评估追踪

提供策略评估的追踪和分析功能。
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

from loguru import logger

from .models import (
    PolicyEvaluation,
    PolicyEvaluationQuery,
    PolicyEvaluationResult,
    PolicyEvaluationStats,
)
from .storage import AuditStorage, MemoryAuditStorage


# ============================================================================
# 策略评估追踪器
# ============================================================================


class PolicyTracker:
    """策略评估追踪器

    提供策略评估的追踪、分析和统计功能。
    """

    def __init__(
        self,
        storage: AuditStorage | None = None,
        cache_ttl: int = 300,
    ) -> None:
        """初始化策略追踪器

        Args:
            storage: 审计存储
            cache_ttl: 缓存 TTL（秒）
        """
        self._storage = storage or MemoryAuditStorage()
        self._cache_ttl = cache_ttl

        # 统计缓存
        self._stats_cache: dict[str, tuple[datetime, PolicyEvaluationStats]] = {}
        self._denial_cache: dict[str, tuple[datetime, dict[str, int]]] = {}
        self._policy_hit_cache: dict[str, tuple[datetime, dict[str, int]]] = {}

        self._lock = asyncio.Lock()

        logger.info("策略评估追踪器初始化完成")

    # =========================================================================
    # 属性
    # =========================================================================

    @property
    def storage(self) -> AuditStorage:
        """获取存储"""
        return self._storage

    # =========================================================================
    # 评估追踪
    # =========================================================================

    async def track_evaluation(
        self,
        evaluation: PolicyEvaluation,
    ) -> None:
        """追踪策略评估

        Args:
            evaluation: 策略评估记录
        """
        await self._storage.save_policy_evaluation(evaluation)

        # 清除相关缓存
        await self._invalidate_cache(evaluation.tenant_id)

        logger.debug(
            f"追踪策略评估: evaluation_id={evaluation.evaluation_id}, "
            f"result={evaluation.result.value}"
        )

    async def get_evaluation(self, evaluation_id: str) -> PolicyEvaluation | None:
        """获取策略评估记录

        Args:
            evaluation_id: 评估 ID

        Returns:
            策略评估记录
        """
        return await self._storage.get_policy_evaluation(evaluation_id)

    async def get_evaluation_history(
        self,
        tenant_id: str | None = None,
        user_id: str | None = None,
        action: str | None = None,
        resource_type: str | None = None,
        result: PolicyEvaluationResult | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[PolicyEvaluation]:
        """获取评估历史

        Args:
            tenant_id: 租户 ID
            user_id: 用户 ID
            action: 操作
            resource_type: 资源类型
            result: 评估结果
            start_time: 开始时间
            end_time: 结束时间
            limit: 限制数量
            offset: 偏移量

        Returns:
            评估记录列表
        """
        query = PolicyEvaluationQuery(
            tenant_ids=[tenant_id] if tenant_id else None,
            user_ids=[user_id] if user_id else None,
            actions=[action] if action else None,
            resource_types=[resource_type] if resource_type else None,
            results=[result] if result else None,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
            offset=offset,
        )

        return await self._storage.query_policy_evaluations(query)

    # =========================================================================
    # 拒绝原因分析
    # =========================================================================

    async def get_denial_reasons(
        self,
        tenant_id: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        top_n: int = 10,
    ) -> dict[str, int]:
        """获取拒绝原因统计

        Args:
            tenant_id: 租户 ID
            start_time: 开始时间
            end_time: 结束时间
            top_n: 返回前 N 个

        Returns:
            拒绝原因统计（原因 -> 次数）
        """
        cache_key = f"denial:{tenant_id}:{start_time}:{end_time}"

        # 检查缓存
        if cache_key in self._denial_cache:
            cached_time, cached_data = self._denial_cache[cache_key]
            if datetime.now() - cached_time < timedelta(seconds=self._cache_ttl):
                return dict(sorted(cached_data.items(), key=lambda x: x[1], reverse=True)[:top_n])

        # 查询数据
        query = PolicyEvaluationQuery(
            tenant_ids=[tenant_id] if tenant_id else None,
            results=[PolicyEvaluationResult.DENY],
            start_time=start_time,
            end_time=end_time,
            limit=1000,
        )

        evaluations = await self._storage.query_policy_evaluations(query)

        # 统计拒绝原因
        denial_reasons: dict[str, int] = defaultdict(int)
        for evaluation in evaluations:
            if evaluation.denial_code:
                denial_reasons[evaluation.denial_code] += 1
            elif evaluation.denial_message:
                # 使用消息的前 50 个字符作为键
                key = evaluation.denial_message[:50]
                denial_reasons[key] += 1
            else:
                denial_reasons["unknown"] += 1

        # 缓存结果
        self._denial_cache[cache_key] = (datetime.now(), dict(denial_reasons))

        # 返回 top N
        return dict(sorted(denial_reasons.items(), key=lambda x: x[1], reverse=True)[:top_n])

    async def get_denial_details(
        self,
        denial_code: str,
        tenant_id: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 100,
    ) -> list[PolicyEvaluation]:
        """获取特定拒绝原因的详细记录

        Args:
            denial_code: 拒绝代码
            tenant_id: 租户 ID
            start_time: 开始时间
            end_time: 结束时间
            limit: 限制数量

        Returns:
            评估记录列表
        """
        query = PolicyEvaluationQuery(
            tenant_ids=[tenant_id] if tenant_id else None,
            results=[PolicyEvaluationResult.DENY],
            start_time=start_time,
            end_time=end_time,
            limit=1000,
        )

        evaluations = await self._storage.query_policy_evaluations(query)

        # 过滤特定拒绝代码
        filtered = [e for e in evaluations if e.denial_code == denial_code]

        return filtered[:limit]

    # =========================================================================
    # 策略命中统计
    # =========================================================================

    async def get_policy_hit_stats(
        self,
        tenant_id: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        top_n: int = 10,
    ) -> dict[str, int]:
        """获取策略命中统计

        Args:
            tenant_id: 租户 ID
            start_time: 开始时间
            end_time: 结束时间
            top_n: 返回前 N 个

        Returns:
            策略命中统计（策略 ID -> 命中次数）
        """
        cache_key = f"policy_hit:{tenant_id}:{start_time}:{end_time}"

        # 检查缓存
        if cache_key in self._policy_hit_cache:
            cached_time, cached_data = self._policy_hit_cache[cache_key]
            if datetime.now() - cached_time < timedelta(seconds=self._cache_ttl):
                return dict(sorted(cached_data.items(), key=lambda x: x[1], reverse=True)[:top_n])

        # 查询数据
        query = PolicyEvaluationQuery(
            tenant_ids=[tenant_id] if tenant_id else None,
            start_time=start_time,
            end_time=end_time,
            limit=1000,
        )

        evaluations = await self._storage.query_policy_evaluations(query)

        # 统计策略命中
        policy_hits: dict[str, int] = defaultdict(int)
        for evaluation in evaluations:
            for policy_id in evaluation.matched_policies:
                policy_hits[policy_id] += 1

        # 缓存结果
        self._policy_hit_cache[cache_key] = (datetime.now(), dict(policy_hits))

        # 返回 top N
        return dict(sorted(policy_hits.items(), key=lambda x: x[1], reverse=True)[:top_n])

    async def get_policy_effectiveness(
        self,
        policy_id: str,
        tenant_id: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> dict[str, Any]:
        """获取策略有效性分析

        Args:
            policy_id: 策略 ID
            tenant_id: 租户 ID
            start_time: 开始时间
            end_time: 结束时间

        Returns:
            策略有效性分析结果
        """
        query = PolicyEvaluationQuery(
            tenant_ids=[tenant_id] if tenant_id else None,
            policy_ids=[policy_id],
            start_time=start_time,
            end_time=end_time,
            limit=1000,
        )

        evaluations = await self._storage.query_policy_evaluations(query)

        if not evaluations:
            return {
                "policy_id": policy_id,
                "total_evaluations": 0,
                "allow_count": 0,
                "deny_count": 0,
                "allow_rate": 0.0,
                "deny_rate": 0.0,
                "avg_evaluation_time_ms": 0.0,
                "unique_users": 0,
                "unique_actions": 0,
            }

        # 统计
        total = len(evaluations)
        allow_count = len([e for e in evaluations if e.result == PolicyEvaluationResult.ALLOW])
        deny_count = len([e for e in evaluations if e.result == PolicyEvaluationResult.DENY])

        # 评估时间
        eval_times = [e.evaluation_time_ms for e in evaluations if e.evaluation_time_ms > 0]
        avg_time = sum(eval_times) / len(eval_times) if eval_times else 0.0

        # 唯一用户和操作
        unique_users = len({e.user_id for e in evaluations if e.user_id})
        unique_actions = len({e.action for e in evaluations})

        return {
            "policy_id": policy_id,
            "total_evaluations": total,
            "allow_count": allow_count,
            "deny_count": deny_count,
            "allow_rate": (allow_count / total * 100) if total > 0 else 0.0,
            "deny_rate": (deny_count / total * 100) if total > 0 else 0.0,
            "avg_evaluation_time_ms": avg_time,
            "unique_users": unique_users,
            "unique_actions": unique_actions,
        }

    # =========================================================================
    # 操作分析
    # =========================================================================

    async def get_action_stats(
        self,
        tenant_id: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        top_n: int = 10,
    ) -> dict[str, dict[str, int]]:
        """获取操作统计

        Args:
            tenant_id: 租户 ID
            start_time: 开始时间
            end_time: 结束时间
            top_n: 返回前 N 个

        Returns:
            操作统计（操作 -> {allow: N, deny: N}）
        """
        query = PolicyEvaluationQuery(
            tenant_ids=[tenant_id] if tenant_id else None,
            start_time=start_time,
            end_time=end_time,
            limit=1000,
        )

        evaluations = await self._storage.query_policy_evaluations(query)

        # 统计操作
        action_stats: dict[str, dict[str, int]] = defaultdict(lambda: {"allow": 0, "deny": 0, "total": 0})
        for evaluation in evaluations:
            action_stats[evaluation.action]["total"] += 1
            if evaluation.result == PolicyEvaluationResult.ALLOW:
                action_stats[evaluation.action]["allow"] += 1
            elif evaluation.result == PolicyEvaluationResult.DENY:
                action_stats[evaluation.action]["deny"] += 1

        # 按总数排序并返回 top N
        sorted_actions = sorted(
            action_stats.items(),
            key=lambda x: x[1]["total"],
            reverse=True,
        )[:top_n]

        return dict(sorted_actions)

    async def get_resource_type_stats(
        self,
        tenant_id: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> dict[str, dict[str, int]]:
        """获取资源类型统计

        Args:
            tenant_id: 租户 ID
            start_time: 开始时间
            end_time: 结束时间

        Returns:
            资源类型统计（类型 -> {allow: N, deny: N}）
        """
        query = PolicyEvaluationQuery(
            tenant_ids=[tenant_id] if tenant_id else None,
            start_time=start_time,
            end_time=end_time,
            limit=1000,
        )

        evaluations = await self._storage.query_policy_evaluations(query)

        # 统计资源类型
        resource_stats: dict[str, dict[str, int]] = defaultdict(lambda: {"allow": 0, "deny": 0, "total": 0})
        for evaluation in evaluations:
            resource_stats[evaluation.resource_type]["total"] += 1
            if evaluation.result == PolicyEvaluationResult.ALLOW:
                resource_stats[evaluation.resource_type]["allow"] += 1
            elif evaluation.result == PolicyEvaluationResult.DENY:
                resource_stats[evaluation.resource_type]["deny"] += 1

        return dict(resource_stats)

    # =========================================================================
    # 用户分析
    # =========================================================================

    async def get_user_evaluation_stats(
        self,
        user_id: str,
        tenant_id: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> dict[str, Any]:
        """获取用户评估统计

        Args:
            user_id: 用户 ID
            tenant_id: 租户 ID
            start_time: 开始时间
            end_time: 结束时间

        Returns:
            用户评估统计
        """
        query = PolicyEvaluationQuery(
            tenant_ids=[tenant_id] if tenant_id else None,
            user_ids=[user_id],
            start_time=start_time,
            end_time=end_time,
            limit=1000,
        )

        evaluations = await self._storage.query_policy_evaluations(query)

        if not evaluations:
            return {
                "user_id": user_id,
                "total_evaluations": 0,
                "allow_count": 0,
                "deny_count": 0,
                "allow_rate": 0.0,
                "deny_rate": 0.0,
                "unique_actions": 0,
                "unique_resources": 0,
                "denial_reasons": {},
            }

        # 统计
        total = len(evaluations)
        allow_count = len([e for e in evaluations if e.result == PolicyEvaluationResult.ALLOW])
        deny_count = len([e for e in evaluations if e.result == PolicyEvaluationResult.DENY])

        # 唯一操作和资源
        unique_actions = len({e.action for e in evaluations})
        unique_resources = len({e.resource_id for e in evaluations if e.resource_id})

        # 拒绝原因
        denial_reasons: dict[str, int] = defaultdict(int)
        for evaluation in evaluations:
            if evaluation.result == PolicyEvaluationResult.DENY and evaluation.denial_code:
                denial_reasons[evaluation.denial_code] += 1

        return {
            "user_id": user_id,
            "total_evaluations": total,
            "allow_count": allow_count,
            "deny_count": deny_count,
            "allow_rate": (allow_count / total * 100) if total > 0 else 0.0,
            "deny_rate": (deny_count / total * 100) if total > 0 else 0.0,
            "unique_actions": unique_actions,
            "unique_resources": unique_resources,
            "denial_reasons": dict(denial_reasons),
        }

    # =========================================================================
    # 综合统计
    # =========================================================================

    async def get_stats(
        self,
        tenant_id: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> PolicyEvaluationStats:
        """获取策略评估统计

        Args:
            tenant_id: 租户 ID
            start_time: 开始时间
            end_time: 结束时间

        Returns:
            策略评估统计
        """
        cache_key = f"stats:{tenant_id}:{start_time}:{end_time}"

        # 检查缓存
        if cache_key in self._stats_cache:
            cached_time, cached_data = self._stats_cache[cache_key]
            if datetime.now() - cached_time < timedelta(seconds=self._cache_ttl):
                return cached_data

        # 获取统计
        stats = await self._storage.get_policy_evaluation_stats(
            tenant_id=tenant_id,
            start_time=start_time,
            end_time=end_time,
        )

        # 缓存结果
        self._stats_cache[cache_key] = (datetime.now(), stats)

        return stats

    # =========================================================================
    # 趋势分析
    # =========================================================================

    async def get_evaluation_trend(
        self,
        tenant_id: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        interval: str = "hour",
    ) -> list[dict[str, Any]]:
        """获取评估趋势

        Args:
            tenant_id: 租户 ID
            start_time: 开始时间
            end_time: 结束时间
            interval: 时间间隔（hour/day/week）

        Returns:
            趋势数据列表
        """
        now = datetime.now()
        start = start_time or (now - timedelta(days=7))
        end = end_time or now

        query = PolicyEvaluationQuery(
            tenant_ids=[tenant_id] if tenant_id else None,
            start_time=start,
            end_time=end,
            limit=1000,
        )

        evaluations = await self._storage.query_policy_evaluations(query)

        # 确定时间间隔
        if interval == "hour":
            delta = timedelta(hours=1)
            format_str = "%Y-%m-%d %H:00"
        elif interval == "day":
            delta = timedelta(days=1)
            format_str = "%Y-%m-%d"
        else:  # week
            delta = timedelta(weeks=1)
            format_str = "%Y-W%W"

        # 按时间间隔分组
        buckets: dict[str, dict[str, int]] = defaultdict(lambda: {"allow": 0, "deny": 0, "total": 0})

        for evaluation in evaluations:
            bucket_key = evaluation.timestamp.strftime(format_str)
            buckets[bucket_key]["total"] += 1
            if evaluation.result == PolicyEvaluationResult.ALLOW:
                buckets[bucket_key]["allow"] += 1
            elif evaluation.result == PolicyEvaluationResult.DENY:
                buckets[bucket_key]["deny"] += 1

        # 转换为列表
        trend = [
            {
                "time": key,
                "total": value["total"],
                "allow": value["allow"],
                "deny": value["deny"],
            }
            for key, value in sorted(buckets.items())
        ]

        return trend

    # =========================================================================
    # 内部方法
    # =========================================================================

    async def _invalidate_cache(self, tenant_id: str | None = None) -> None:
        """清除缓存

        Args:
            tenant_id: 租户 ID（如果指定，只清除该租户的缓存）
        """
        async with self._lock:
            if tenant_id:
                # 清除特定租户的缓存
                keys_to_remove = [
                    key for key in self._stats_cache.keys()
                    if tenant_id in key
                ]
                for key in keys_to_remove:
                    del self._stats_cache[key]

                keys_to_remove = [
                    key for key in self._denial_cache.keys()
                    if tenant_id in key
                ]
                for key in keys_to_remove:
                    del self._denial_cache[key]

                keys_to_remove = [
                    key for key in self._policy_hit_cache.keys()
                    if tenant_id in key
                ]
                for key in keys_to_remove:
                    del self._policy_hit_cache[key]
            else:
                # 清除所有缓存
                self._stats_cache.clear()
                self._denial_cache.clear()
                self._policy_hit_cache.clear()

    def clear_cache(self) -> None:
        """清除所有缓存"""
        self._stats_cache.clear()
        self._denial_cache.clear()
        self._policy_hit_cache.clear()
