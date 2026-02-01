"""审计日志存储

提供审计事件和策略评估记录的持久化存储功能。
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

from loguru import logger

from .models import (
    AuditEvent,
    AuditEventType,
    AuditQuery,
    AuditResult,
    AuditSeverity,
    AuditStats,
    PolicyEvaluation,
    PolicyEvaluationQuery,
    PolicyEvaluationResult,
    PolicyEvaluationStats,
    ResourceType,
)


# ============================================================================
# 审计存储抽象基类
# ============================================================================


class AuditStorage(ABC):
    """审计存储抽象基类"""

    # -------------------------------------------------------------------------
    # 审计事件操作
    # -------------------------------------------------------------------------

    @abstractmethod
    async def save_event(self, event: AuditEvent) -> None:
        """保存审计事件

        Args:
            event: 审计事件
        """
        pass

    @abstractmethod
    async def get_event(self, event_id: str) -> AuditEvent | None:
        """获取审计事件

        Args:
            event_id: 事件 ID

        Returns:
            审计事件
        """
        pass

    @abstractmethod
    async def query_events(self, query: AuditQuery) -> list[AuditEvent]:
        """查询审计事件

        Args:
            query: 查询条件

        Returns:
            审计事件列表
        """
        pass

    @abstractmethod
    async def count_events(self, query: AuditQuery) -> int:
        """统计审计事件数量

        Args:
            query: 查询条件

        Returns:
            事件数量
        """
        pass

    @abstractmethod
    async def delete_events_before(self, before: datetime) -> int:
        """删除指定时间之前的事件

        Args:
            before: 截止时间

        Returns:
            删除的事件数量
        """
        pass

    @abstractmethod
    async def get_event_stats(
        self,
        tenant_id: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> AuditStats:
        """获取审计统计

        Args:
            tenant_id: 租户 ID（可选）
            start_time: 开始时间
            end_time: 结束时间

        Returns:
            审计统计
        """
        pass

    # -------------------------------------------------------------------------
    # 策略评估记录操作
    # -------------------------------------------------------------------------

    @abstractmethod
    async def save_policy_evaluation(self, evaluation: PolicyEvaluation) -> None:
        """保存策略评估记录

        Args:
            evaluation: 策略评估记录
        """
        pass

    @abstractmethod
    async def get_policy_evaluation(self, evaluation_id: str) -> PolicyEvaluation | None:
        """获取策略评估记录

        Args:
            evaluation_id: 评估 ID

        Returns:
            策略评估记录
        """
        pass

    @abstractmethod
    async def query_policy_evaluations(
        self,
        query: PolicyEvaluationQuery,
    ) -> list[PolicyEvaluation]:
        """查询策略评估记录

        Args:
            query: 查询条件

        Returns:
            策略评估记录列表
        """
        pass

    @abstractmethod
    async def count_policy_evaluations(self, query: PolicyEvaluationQuery) -> int:
        """统计策略评估记录数量

        Args:
            query: 查询条件

        Returns:
            记录数量
        """
        pass

    @abstractmethod
    async def get_policy_evaluation_stats(
        self,
        tenant_id: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> PolicyEvaluationStats:
        """获取策略评估统计

        Args:
            tenant_id: 租户 ID（可选）
            start_time: 开始时间
            end_time: 结束时间

        Returns:
            策略评估统计
        """
        pass


# ============================================================================
# 内存审计存储
# ============================================================================


class MemoryAuditStorage(AuditStorage):
    """内存审计存储

    用于开发和测试的内存存储实现。
    """

    def __init__(
        self,
        max_events: int = 100000,
        max_evaluations: int = 50000,
        retention_days: int = 30,
    ) -> None:
        """初始化内存存储

        Args:
            max_events: 最大事件数量
            max_evaluations: 最大评估记录数量
            retention_days: 保留天数
        """
        self._events: dict[str, AuditEvent] = {}
        self._evaluations: dict[str, PolicyEvaluation] = {}
        self._max_events = max_events
        self._max_evaluations = max_evaluations
        self._retention_days = retention_days
        self._lock = asyncio.Lock()

    # -------------------------------------------------------------------------
    # 审计事件操作
    # -------------------------------------------------------------------------

    async def save_event(self, event: AuditEvent) -> None:
        """保存审计事件"""
        async with self._lock:
            # 检查容量
            if len(self._events) >= self._max_events:
                await self._cleanup_old_events()

            self._events[event.event_id] = event
            logger.debug(f"保存审计事件: {event.event_id}")

    async def get_event(self, event_id: str) -> AuditEvent | None:
        """获取审计事件"""
        return self._events.get(event_id)

    async def query_events(self, query: AuditQuery) -> list[AuditEvent]:
        """查询审计事件"""
        events = list(self._events.values())

        # 应用过滤条件
        events = self._filter_events(events, query)

        # 排序
        reverse = query.order_desc
        if query.order_by == "timestamp":
            events.sort(key=lambda e: e.timestamp, reverse=reverse)
        elif query.order_by == "severity":
            severity_order = {
                AuditSeverity.DEBUG: 0,
                AuditSeverity.INFO: 1,
                AuditSeverity.WARNING: 2,
                AuditSeverity.ERROR: 3,
                AuditSeverity.CRITICAL: 4,
            }
            events.sort(key=lambda e: severity_order.get(e.severity, 0), reverse=reverse)

        # 分页
        return events[query.offset : query.offset + query.limit]

    async def count_events(self, query: AuditQuery) -> int:
        """统计审计事件数量"""
        events = list(self._events.values())
        events = self._filter_events(events, query)
        return len(events)

    async def delete_events_before(self, before: datetime) -> int:
        """删除指定时间之前的事件"""
        async with self._lock:
            to_delete = [
                event_id
                for event_id, event in self._events.items()
                if event.timestamp < before
            ]

            for event_id in to_delete:
                del self._events[event_id]

            if to_delete:
                logger.info(f"删除了 {len(to_delete)} 条过期审计事件")

            return len(to_delete)

    async def get_event_stats(
        self,
        tenant_id: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> AuditStats:
        """获取审计统计"""
        now = datetime.now()
        start = start_time or (now - timedelta(days=7))
        end = end_time or now

        # 构建查询 (不使用 limit，因为统计需要所有数据)
        query = AuditQuery(
            tenant_ids=[tenant_id] if tenant_id else None,
            start_time=start,
            end_time=end,
            limit=1000,  # 使用最大允许值，实际过滤不受此限制
        )

        events = list(self._events.values())
        events = self._filter_events(events, query)

        # 统计
        total = len(events)
        success = len([e for e in events if e.result == AuditResult.SUCCESS])
        failure = len([e for e in events if e.result == AuditResult.FAILURE])
        denied = len([e for e in events if e.result == AuditResult.DENIED])

        # 按事件类型统计
        by_event_type: dict[str, int] = defaultdict(int)
        for event in events:
            by_event_type[event.event_type.value] += 1

        # 按严重级别统计
        by_severity: dict[str, int] = defaultdict(int)
        for event in events:
            by_severity[event.severity.value] += 1

        # 按资源类型统计
        by_resource_type: dict[str, int] = defaultdict(int)
        for event in events:
            if event.resource_type:
                by_resource_type[event.resource_type.value] += 1

        # 按结果统计
        by_result: dict[str, int] = defaultdict(int)
        for event in events:
            by_result[event.result.value] += 1

        # 安全统计
        security_types = {
            AuditEventType.AUTH_SUCCESS,
            AuditEventType.AUTH_FAILURE,
            AuditEventType.ACCESS_DENIED,
            AuditEventType.SUSPICIOUS_ACTIVITY,
        }
        security_events = len([e for e in events if e.event_type in security_types])
        auth_failures = len([e for e in events if e.event_type == AuditEventType.AUTH_FAILURE])
        access_denials = len([e for e in events if e.event_type == AuditEventType.ACCESS_DENIED])

        # 配置变更统计
        config_types = {
            AuditEventType.CONFIG_CREATE,
            AuditEventType.CONFIG_UPDATE,
            AuditEventType.CONFIG_DELETE,
        }
        config_changes = len([e for e in events if e.event_type in config_types])

        # 唯一用户和会话
        unique_users = len({e.user_id for e in events if e.user_id})
        unique_sessions = len({e.session_id for e in events if e.session_id})

        return AuditStats(
            tenant_id=tenant_id,
            period_start=start,
            period_end=end,
            total_events=total,
            success_events=success,
            failure_events=failure,
            denied_events=denied,
            by_event_type=dict(by_event_type),
            by_severity=dict(by_severity),
            by_resource_type=dict(by_resource_type),
            by_result=dict(by_result),
            security_events=security_events,
            auth_failures=auth_failures,
            access_denials=access_denials,
            config_changes=config_changes,
            unique_users=unique_users,
            unique_sessions=unique_sessions,
        )

    def _filter_events(self, events: list[AuditEvent], query: AuditQuery) -> list[AuditEvent]:
        """过滤审计事件"""
        # 时间范围
        if query.start_time:
            events = [e for e in events if e.timestamp >= query.start_time]
        if query.end_time:
            events = [e for e in events if e.timestamp <= query.end_time]

        # 租户过滤
        if query.tenant_ids:
            events = [e for e in events if e.tenant_id in query.tenant_ids]

        # 用户过滤
        if query.user_ids:
            events = [e for e in events if e.user_id in query.user_ids]

        # 事件类型过滤
        if query.event_types:
            events = [e for e in events if e.event_type in query.event_types]

        # 严重级别过滤
        if query.severities:
            events = [e for e in events if e.severity in query.severities]

        # 结果过滤
        if query.results:
            events = [e for e in events if e.result in query.results]

        # 资源类型过滤
        if query.resource_types:
            events = [e for e in events if e.resource_type in query.resource_types]

        # 资源 ID 过滤
        if query.resource_ids:
            events = [e for e in events if e.resource_id in query.resource_ids]

        # 操作名称模式匹配
        if query.action_pattern:
            pattern = query.action_pattern.lower()
            events = [e for e in events if pattern in e.action.lower()]

        # 关键词搜索
        if query.keyword:
            keyword = query.keyword.lower()
            events = [
                e
                for e in events
                if keyword in e.action.lower()
                or (e.resource_name and keyword in e.resource_name.lower())
                or (e.error_message and keyword in e.error_message.lower())
            ]

        return events

    async def _cleanup_old_events(self) -> None:
        """清理旧事件"""
        if not self._events:
            return

        # 按时间排序
        events = sorted(
            self._events.values(),
            key=lambda e: e.timestamp,
        )

        # 删除最旧的 20%
        to_delete = len(events) // 5
        for event in events[:to_delete]:
            del self._events[event.event_id]

        logger.info(f"清理了 {to_delete} 条旧审计事件")

    # -------------------------------------------------------------------------
    # 策略评估记录操作
    # -------------------------------------------------------------------------

    async def save_policy_evaluation(self, evaluation: PolicyEvaluation) -> None:
        """保存策略评估记录"""
        async with self._lock:
            # 检查容量
            if len(self._evaluations) >= self._max_evaluations:
                await self._cleanup_old_evaluations()

            self._evaluations[evaluation.evaluation_id] = evaluation
            logger.debug(f"保存策略评估记录: {evaluation.evaluation_id}")

    async def get_policy_evaluation(self, evaluation_id: str) -> PolicyEvaluation | None:
        """获取策略评估记录"""
        return self._evaluations.get(evaluation_id)

    async def query_policy_evaluations(
        self,
        query: PolicyEvaluationQuery,
    ) -> list[PolicyEvaluation]:
        """查询策略评估记录"""
        evaluations = list(self._evaluations.values())

        # 应用过滤条件
        evaluations = self._filter_evaluations(evaluations, query)

        # 排序
        reverse = query.order_desc
        if query.order_by == "timestamp":
            evaluations.sort(key=lambda e: e.timestamp, reverse=reverse)
        elif query.order_by == "evaluation_time_ms":
            evaluations.sort(key=lambda e: e.evaluation_time_ms, reverse=reverse)

        # 分页
        return evaluations[query.offset : query.offset + query.limit]

    async def count_policy_evaluations(self, query: PolicyEvaluationQuery) -> int:
        """统计策略评估记录数量"""
        evaluations = list(self._evaluations.values())
        evaluations = self._filter_evaluations(evaluations, query)
        return len(evaluations)

    async def get_policy_evaluation_stats(
        self,
        tenant_id: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> PolicyEvaluationStats:
        """获取策略评估统计"""
        now = datetime.now()
        start = start_time or (now - timedelta(days=7))
        end = end_time or now

        # 构建查询 (不使用 limit，因为统计需要所有数据)
        query = PolicyEvaluationQuery(
            tenant_ids=[tenant_id] if tenant_id else None,
            start_time=start,
            end_time=end,
            limit=1000,  # 使用最大允许值，实际过滤不受此限制
        )

        evaluations = list(self._evaluations.values())
        evaluations = self._filter_evaluations(evaluations, query)

        # 统计
        total = len(evaluations)
        allow_count = len([e for e in evaluations if e.result == PolicyEvaluationResult.ALLOW])
        deny_count = len([e for e in evaluations if e.result == PolicyEvaluationResult.DENY])
        not_applicable_count = len(
            [e for e in evaluations if e.result == PolicyEvaluationResult.NOT_APPLICABLE]
        )

        # 按策略统计
        by_policy: dict[str, int] = defaultdict(int)
        for evaluation in evaluations:
            for policy_id in evaluation.matched_policies:
                by_policy[policy_id] += 1

        # 按操作统计
        by_action: dict[str, int] = defaultdict(int)
        for evaluation in evaluations:
            by_action[evaluation.action] += 1

        # 按资源类型统计
        by_resource_type: dict[str, int] = defaultdict(int)
        for evaluation in evaluations:
            by_resource_type[evaluation.resource_type] += 1

        # 拒绝原因统计
        denial_reasons: dict[str, int] = defaultdict(int)
        for evaluation in evaluations:
            if evaluation.result == PolicyEvaluationResult.DENY and evaluation.denial_code:
                denial_reasons[evaluation.denial_code] += 1

        # 性能统计
        evaluation_times = [e.evaluation_time_ms for e in evaluations if e.evaluation_time_ms > 0]
        avg_time = sum(evaluation_times) / len(evaluation_times) if evaluation_times else 0.0
        max_time = max(evaluation_times) if evaluation_times else 0.0
        min_time = min(evaluation_times) if evaluation_times else 0.0

        return PolicyEvaluationStats(
            tenant_id=tenant_id,
            period_start=start,
            period_end=end,
            total_evaluations=total,
            allow_count=allow_count,
            deny_count=deny_count,
            not_applicable_count=not_applicable_count,
            by_policy=dict(by_policy),
            by_action=dict(by_action),
            by_resource_type=dict(by_resource_type),
            denial_reasons=dict(denial_reasons),
            avg_evaluation_time_ms=avg_time,
            max_evaluation_time_ms=max_time,
            min_evaluation_time_ms=min_time,
        )

    def _filter_evaluations(
        self,
        evaluations: list[PolicyEvaluation],
        query: PolicyEvaluationQuery,
    ) -> list[PolicyEvaluation]:
        """过滤策略评估记录"""
        # 时间范围
        if query.start_time:
            evaluations = [e for e in evaluations if e.timestamp >= query.start_time]
        if query.end_time:
            evaluations = [e for e in evaluations if e.timestamp <= query.end_time]

        # 租户过滤
        if query.tenant_ids:
            evaluations = [e for e in evaluations if e.tenant_id in query.tenant_ids]

        # 用户过滤
        if query.user_ids:
            evaluations = [e for e in evaluations if e.user_id in query.user_ids]

        # 结果过滤
        if query.results:
            evaluations = [e for e in evaluations if e.result in query.results]

        # 策略 ID 过滤
        if query.policy_ids:
            evaluations = [
                e
                for e in evaluations
                if any(pid in e.matched_policies for pid in query.policy_ids)
            ]

        # 操作过滤
        if query.actions:
            evaluations = [e for e in evaluations if e.action in query.actions]

        # 资源类型过滤
        if query.resource_types:
            evaluations = [e for e in evaluations if e.resource_type in query.resource_types]

        return evaluations

    async def _cleanup_old_evaluations(self) -> None:
        """清理旧评估记录"""
        if not self._evaluations:
            return

        # 按时间排序
        evaluations = sorted(
            self._evaluations.values(),
            key=lambda e: e.timestamp,
        )

        # 删除最旧的 20%
        to_delete = len(evaluations) // 5
        for evaluation in evaluations[:to_delete]:
            del self._evaluations[evaluation.evaluation_id]

        logger.info(f"清理了 {to_delete} 条旧策略评估记录")

    # -------------------------------------------------------------------------
    # 辅助方法
    # -------------------------------------------------------------------------

    async def cleanup_expired(self) -> tuple[int, int]:
        """清理过期数据

        Returns:
            (删除的事件数, 删除的评估记录数)
        """
        cutoff = datetime.now() - timedelta(days=self._retention_days)

        # 清理事件
        events_deleted = await self.delete_events_before(cutoff)

        # 清理评估记录
        async with self._lock:
            to_delete = [
                eval_id
                for eval_id, evaluation in self._evaluations.items()
                if evaluation.timestamp < cutoff
            ]

            for eval_id in to_delete:
                del self._evaluations[eval_id]

        if to_delete:
            logger.info(f"删除了 {len(to_delete)} 条过期策略评估记录")

        return events_deleted, len(to_delete)

    def clear(self) -> None:
        """清空所有数据（仅用于测试）"""
        self._events.clear()
        self._evaluations.clear()

    @property
    def event_count(self) -> int:
        """获取事件数量"""
        return len(self._events)

    @property
    def evaluation_count(self) -> int:
        """获取评估记录数量"""
        return len(self._evaluations)
