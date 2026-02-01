"""告警规则引擎

提供告警规则定义、评估和管理功能。
"""

from __future__ import annotations

from typing import Any

from loguru import logger

from ..quota import QuotaCheckResult, QuotaManager, QuotaType
from ..storage import TenantStorage
from .models import (
    Alert,
    AlertCondition,
    AlertRule,
    AlertSeverity,
    AlertType,
    ConditionOperator,
    NotificationChannel,
)


# ============================================================================
# 预定义告警规则
# ============================================================================


def create_default_rules() -> list[AlertRule]:
    """创建默认告警规则

    Returns:
        默认告警规则列表
    """
    rules = []

    # ========================================================================
    # 配额告警规则
    # ========================================================================

    # 配额警告（80%）
    for quota_type in QuotaType:
        rules.append(
            AlertRule(
                rule_id=f"quota_warning_{quota_type.value}",
                name=f"{quota_type.value} 配额警告",
                description=f"当 {quota_type.value} 使用率达到 80% 时触发警告",
                alert_type=AlertType.QUOTA_WARNING,
                severity=AlertSeverity.WARNING,
                condition=AlertCondition(
                    condition_type="threshold",
                    metric="quota_percentage",
                    quota_type=quota_type,
                    operator=ConditionOperator.GTE,
                    threshold=0.8,
                ),
                channels=[NotificationChannel.SYSTEM_EVENT],
                throttle_seconds=3600,  # 1 小时内不重复
                max_alerts_per_hour=2,
            )
        )

    # 配额超限（100%）
    for quota_type in QuotaType:
        rules.append(
            AlertRule(
                rule_id=f"quota_exceeded_{quota_type.value}",
                name=f"{quota_type.value} 配额超限",
                description=f"当 {quota_type.value} 使用率达到 100% 时触发告警",
                alert_type=AlertType.QUOTA_EXCEEDED,
                severity=AlertSeverity.ERROR,
                condition=AlertCondition(
                    condition_type="threshold",
                    metric="quota_percentage",
                    quota_type=quota_type,
                    operator=ConditionOperator.GTE,
                    threshold=1.0,
                ),
                channels=[NotificationChannel.SYSTEM_EVENT],
                throttle_seconds=1800,  # 30 分钟内不重复
                max_alerts_per_hour=4,
            )
        )

    # 配额严重超限（120%）
    for quota_type in [
        QuotaType.TOKENS_PER_DAY,
        QuotaType.API_CALLS_PER_DAY,
    ]:
        rules.append(
            AlertRule(
                rule_id=f"quota_critical_{quota_type.value}",
                name=f"{quota_type.value} 配额严重超限",
                description=f"当 {quota_type.value} 使用率达到 120% 时触发严重告警",
                alert_type=AlertType.QUOTA_CRITICAL,
                severity=AlertSeverity.CRITICAL,
                condition=AlertCondition(
                    condition_type="threshold",
                    metric="quota_percentage",
                    quota_type=quota_type,
                    operator=ConditionOperator.GTE,
                    threshold=1.2,
                ),
                channels=[NotificationChannel.SYSTEM_EVENT],
                throttle_seconds=900,  # 15 分钟内不重复
                max_alerts_per_hour=6,
            )
        )

    # ========================================================================
    # 速率限制告警规则
    # ========================================================================

    # API 速率警告（80%）
    rules.append(
        AlertRule(
            rule_id="rate_limit_warning",
            name="API 速率限制警告",
            description="当 API 调用速率达到限制的 80% 时触发警告",
            alert_type=AlertType.RATE_LIMIT_WARNING,
            severity=AlertSeverity.WARNING,
            condition=AlertCondition(
                condition_type="threshold",
                metric="rate_limit_percentage",
                quota_type=QuotaType.API_CALLS_PER_MINUTE,
                operator=ConditionOperator.GTE,
                threshold=0.8,
            ),
            channels=[NotificationChannel.SYSTEM_EVENT],
            throttle_seconds=300,  # 5 分钟内不重复
            max_alerts_per_hour=6,
        )
    )

    # API 速率超限
    rules.append(
        AlertRule(
            rule_id="rate_limit_exceeded",
            name="API 速率限制超限",
            description="当 API 调用速率达到限制时触发告警",
            alert_type=AlertType.RATE_LIMIT_EXCEEDED,
            severity=AlertSeverity.ERROR,
            condition=AlertCondition(
                condition_type="threshold",
                metric="rate_limit_percentage",
                quota_type=QuotaType.API_CALLS_PER_MINUTE,
                operator=ConditionOperator.GTE,
                threshold=1.0,
            ),
            channels=[NotificationChannel.SYSTEM_EVENT],
            throttle_seconds=60,  # 1 分钟内不重复
            max_alerts_per_hour=30,
        )
    )

    # ========================================================================
    # 并发请求告警规则
    # ========================================================================

    # 并发警告（80%）
    rules.append(
        AlertRule(
            rule_id="concurrent_warning",
            name="并发请求警告",
            description="当并发请求数达到限制的 80% 时触发警告",
            alert_type=AlertType.CONCURRENT_WARNING,
            severity=AlertSeverity.WARNING,
            condition=AlertCondition(
                condition_type="threshold",
                metric="concurrent_percentage",
                quota_type=QuotaType.CONCURRENT_REQUESTS,
                operator=ConditionOperator.GTE,
                threshold=0.8,
            ),
            channels=[NotificationChannel.SYSTEM_EVENT],
            throttle_seconds=300,  # 5 分钟内不重复
            max_alerts_per_hour=6,
        )
    )

    # 并发超限
    rules.append(
        AlertRule(
            rule_id="concurrent_exceeded",
            name="并发请求超限",
            description="当并发请求数达到限制时触发告警",
            alert_type=AlertType.CONCURRENT_EXCEEDED,
            severity=AlertSeverity.ERROR,
            condition=AlertCondition(
                condition_type="threshold",
                metric="concurrent_percentage",
                quota_type=QuotaType.CONCURRENT_REQUESTS,
                operator=ConditionOperator.GTE,
                threshold=1.0,
            ),
            channels=[NotificationChannel.SYSTEM_EVENT],
            throttle_seconds=60,  # 1 分钟内不重复
            max_alerts_per_hour=30,
        )
    )

    return rules


# ============================================================================
# 规则评估器
# ============================================================================


class RuleEvaluator:
    """规则评估器

    负责评估告警规则条件。
    """

    def __init__(
        self,
        storage: TenantStorage,
        quota_manager: QuotaManager,
    ) -> None:
        """初始化评估器

        Args:
            storage: 租户存储
            quota_manager: 配额管理器
        """
        self._storage = storage
        self._quota_manager = quota_manager

    async def evaluate(
        self,
        rule: AlertRule,
        tenant_id: str,
        context: dict[str, Any] | None = None,
    ) -> tuple[bool, dict[str, Any]]:
        """评估规则

        Args:
            rule: 告警规则
            tenant_id: 租户 ID
            context: 评估上下文（可选）

        Returns:
            (是否触发, 评估上下文)
        """
        if not rule.enabled:
            return False, {}

        # 检查租户范围
        if rule.tenant_ids is not None and tenant_id not in rule.tenant_ids:
            return False, {}

        condition = rule.condition
        eval_context: dict[str, Any] = context or {}

        # 根据条件类型评估
        if condition.condition_type == "threshold":
            triggered, ctx = await self._evaluate_threshold(
                condition, tenant_id, eval_context
            )
        elif condition.condition_type == "trend":
            triggered, ctx = await self._evaluate_trend(
                condition, tenant_id, eval_context
            )
        elif condition.condition_type == "anomaly":
            triggered, ctx = await self._evaluate_anomaly(
                condition, tenant_id, eval_context
            )
        else:
            logger.warning(f"未知条件类型: {condition.condition_type}")
            return False, {}

        eval_context.update(ctx)
        return triggered, eval_context

    async def _evaluate_threshold(
        self,
        condition: AlertCondition,
        tenant_id: str,
        context: dict[str, Any],
    ) -> tuple[bool, dict[str, Any]]:
        """评估阈值条件

        Args:
            condition: 告警条件
            tenant_id: 租户 ID
            context: 评估上下文

        Returns:
            (是否触发, 评估上下文)
        """
        # 获取租户
        tenant = await self._storage.get(tenant_id)
        if not tenant:
            return False, {}

        # 获取当前值
        current_value: float = 0.0
        limit_value: float = 0.0

        if condition.metric == "quota_percentage" and condition.quota_type:
            detail = await self._quota_manager.check_quota(
                tenant, condition.quota_type
            )
            current_value = detail.percentage
            limit_value = detail.limit
            context["current"] = detail.current
            context["limit"] = limit_value
            context["quota_type"] = condition.quota_type.value

        elif condition.metric == "rate_limit_percentage":
            detail = await self._quota_manager.check_rate_limit(tenant)
            current_value = detail.percentage
            limit_value = detail.limit
            context["current"] = detail.current
            context["limit"] = limit_value

        elif condition.metric == "concurrent_percentage":
            current = await self._quota_manager.get_concurrent_count(tenant_id)
            limit = tenant.quota.max_concurrent_requests
            current_value = current / limit if limit > 0 else 0.0
            limit_value = limit
            context["current"] = current
            context["limit"] = limit

        else:
            # 从上下文获取
            current_value = context.get("value", 0.0)

        context["percentage"] = current_value
        context["threshold"] = condition.threshold

        # 比较
        triggered = self._compare(current_value, condition.operator, condition.threshold)
        return triggered, context

    async def _evaluate_trend(
        self,
        condition: AlertCondition,
        tenant_id: str,
        context: dict[str, Any],
    ) -> tuple[bool, dict[str, Any]]:
        """评估趋势条件

        Args:
            condition: 告警条件
            tenant_id: 租户 ID
            context: 评估上下文

        Returns:
            (是否触发, 评估上下文)
        """
        # 趋势评估需要历史数据，暂时返回 False
        # TODO: 实现趋势评估逻辑
        return False, context

    async def _evaluate_anomaly(
        self,
        condition: AlertCondition,
        tenant_id: str,
        context: dict[str, Any],
    ) -> tuple[bool, dict[str, Any]]:
        """评估异常条件

        Args:
            condition: 告警条件
            tenant_id: 租户 ID
            context: 评估上下文

        Returns:
            (是否触发, 评估上下文)
        """
        # 异常检测需要更复杂的算法，暂时返回 False
        # TODO: 实现异常检测逻辑
        return False, context

    def _compare(
        self,
        value: float,
        operator: ConditionOperator,
        threshold: float,
    ) -> bool:
        """比较值和阈值

        Args:
            value: 当前值
            operator: 运算符
            threshold: 阈值

        Returns:
            比较结果
        """
        if operator == ConditionOperator.GT:
            return value > threshold
        elif operator == ConditionOperator.GTE:
            return value >= threshold
        elif operator == ConditionOperator.LT:
            return value < threshold
        elif operator == ConditionOperator.LTE:
            return value <= threshold
        elif operator == ConditionOperator.EQ:
            return abs(value - threshold) < 1e-9
        elif operator == ConditionOperator.NEQ:
            return abs(value - threshold) >= 1e-9
        elif operator == ConditionOperator.CHANGE_RATE:
            # 变化率比较需要基准值
            return False
        else:
            return False


# ============================================================================
# 规则管理器
# ============================================================================


class RuleManager:
    """规则管理器

    负责管理告警规则。
    """

    def __init__(self) -> None:
        """初始化规则管理器"""
        self._rules: dict[str, AlertRule] = {}
        self._load_default_rules()

    def _load_default_rules(self) -> None:
        """加载默认规则"""
        for rule in create_default_rules():
            self._rules[rule.rule_id] = rule
        logger.info(f"加载了 {len(self._rules)} 条默认告警规则")

    def add_rule(self, rule: AlertRule) -> None:
        """添加规则

        Args:
            rule: 告警规则
        """
        self._rules[rule.rule_id] = rule
        logger.info(f"添加告警规则: {rule.rule_id}")

    def remove_rule(self, rule_id: str) -> bool:
        """移除规则

        Args:
            rule_id: 规则 ID

        Returns:
            是否成功移除
        """
        if rule_id in self._rules:
            del self._rules[rule_id]
            logger.info(f"移除告警规则: {rule_id}")
            return True
        return False

    def get_rule(self, rule_id: str) -> AlertRule | None:
        """获取规则

        Args:
            rule_id: 规则 ID

        Returns:
            告警规则
        """
        return self._rules.get(rule_id)

    def get_all_rules(self) -> list[AlertRule]:
        """获取所有规则

        Returns:
            所有告警规则
        """
        return list(self._rules.values())

    def get_enabled_rules(self) -> list[AlertRule]:
        """获取所有启用的规则

        Returns:
            启用的告警规则
        """
        return [r for r in self._rules.values() if r.enabled]

    def get_rules_by_type(self, alert_type: AlertType) -> list[AlertRule]:
        """按类型获取规则

        Args:
            alert_type: 告警类���

        Returns:
            匹配的告警规则
        """
        return [r for r in self._rules.values() if r.alert_type == alert_type]

    def get_rules_for_tenant(self, tenant_id: str) -> list[AlertRule]:
        """获取适用于租户的规则

        Args:
            tenant_id: 租户 ID

        Returns:
            适用的告警规则
        """
        rules = []
        for rule in self._rules.values():
            if not rule.enabled:
                continue
            if rule.tenant_ids is None or tenant_id in rule.tenant_ids:
                rules.append(rule)
        return rules

    def enable_rule(self, rule_id: str) -> bool:
        """启用规则

        Args:
            rule_id: 规则 ID

        Returns:
            是否成功
        """
        rule = self._rules.get(rule_id)
        if rule:
            rule.enabled = True
            logger.info(f"启用告警规则: {rule_id}")
            return True
        return False

    def disable_rule(self, rule_id: str) -> bool:
        """禁用规则

        Args:
            rule_id: 规则 ID

        Returns:
            是否成功
        """
        rule = self._rules.get(rule_id)
        if rule:
            rule.enabled = False
            logger.info(f"禁用告警规则: {rule_id}")
            return True
        return False

    def update_rule_threshold(
        self,
        rule_id: str,
        threshold: float,
    ) -> bool:
        """更新规则阈值

        Args:
            rule_id: 规则 ID
            threshold: 新阈值

        Returns:
            是否成功
        """
        rule = self._rules.get(rule_id)
        if rule:
            rule.condition.threshold = threshold
            logger.info(f"更新告警规则阈值: {rule_id} -> {threshold}")
            return True
        return False

    def get_rules_count(self) -> dict[str, int]:
        """获取规则统计

        Returns:
            规则统计
        """
        total = len(self._rules)
        enabled = len([r for r in self._rules.values() if r.enabled])
        return {
            "total": total,
            "enabled": enabled,
            "disabled": total - enabled,
        }
