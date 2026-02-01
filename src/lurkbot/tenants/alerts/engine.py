"""告警引擎

提供告警触发、去重、节流和状态管理功能。
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Any, Callable

from loguru import logger

from ..models import TenantEvent, TenantEventType
from ..quota import QuotaManager, QuotaType
from ..storage import TenantStorage
from .models import (
    Alert,
    AlertNotification,
    AlertSeverity,
    AlertStatus,
    AlertType,
    NotificationChannel,
)
from .rules import RuleEvaluator, RuleManager
from .storage import AlertStorage, MemoryAlertStorage


# ============================================================================
# 告警引擎
# ============================================================================


class AlertEngine:
    """告警引擎

    负责告警的触发、去重、节流和状态管理。
    """

    def __init__(
        self,
        tenant_storage: TenantStorage,
        quota_manager: QuotaManager,
        alert_storage: AlertStorage | None = None,
    ) -> None:
        """初始化告警引擎

        Args:
            tenant_storage: 租户存储
            quota_manager: 配额管理器
            alert_storage: 告警存储（可选，默认使用内存存储）
        """
        self._tenant_storage = tenant_storage
        self._quota_manager = quota_manager
        self._alert_storage = alert_storage or MemoryAlertStorage()

        # 规则管理
        self._rule_manager = RuleManager()
        self._rule_evaluator = RuleEvaluator(tenant_storage, quota_manager)

        # 通知回调
        self._notification_handlers: list[Callable[[Alert], Any]] = []

        # 运行状态
        self._running = False
        self._scan_task: asyncio.Task | None = None
        self._lock = asyncio.Lock()

        logger.info("告警引擎初始化完成")

    # ========================================================================
    # 属性
    # ========================================================================

    @property
    def rule_manager(self) -> RuleManager:
        """获取规则管理器"""
        return self._rule_manager

    @property
    def alert_storage(self) -> AlertStorage:
        """获取告警存储"""
        return self._alert_storage

    # ========================================================================
    # 告警触发
    # ========================================================================

    async def check_and_trigger(
        self,
        tenant_id: str,
        context: dict[str, Any] | None = None,
    ) -> list[Alert]:
        """检查并触发告警

        评估所有适用规则，触发满足条件的告警。

        Args:
            tenant_id: 租户 ID
            context: 评估上下文

        Returns:
            触发的告警列表
        """
        triggered_alerts = []
        rules = self._rule_manager.get_rules_for_tenant(tenant_id)

        for rule in rules:
            try:
                triggered, eval_context = await self._rule_evaluator.evaluate(
                    rule, tenant_id, context
                )

                if triggered:
                    # 检查是否应该抑制
                    if await self._should_suppress(rule.rule_id, tenant_id, rule.throttle_seconds):
                        logger.debug(
                            f"告警被节流: rule={rule.rule_id}, tenant={tenant_id}"
                        )
                        continue

                    # 检查每小时限制
                    if await self._exceeds_hourly_limit(
                        rule.rule_id, tenant_id, rule.max_alerts_per_hour
                    ):
                        logger.debug(
                            f"告警超过每小时限制: rule={rule.rule_id}, tenant={tenant_id}"
                        )
                        continue

                    # 创建告警
                    alert = await self._create_alert(rule, tenant_id, eval_context)
                    triggered_alerts.append(alert)

                    # 发送通知
                    await self._send_notifications(alert, rule.channels)

            except Exception as e:
                logger.error(f"评估规则失败: rule={rule.rule_id}, error={e}")

        return triggered_alerts

    async def trigger_alert(
        self,
        tenant_id: str,
        alert_type: AlertType,
        severity: AlertSeverity,
        title: str,
        message: str,
        context: dict[str, Any] | None = None,
        channels: list[NotificationChannel] | None = None,
    ) -> Alert:
        """直接触发告警

        不经过规则评估，直接创建告警。

        Args:
            tenant_id: 租户 ID
            alert_type: 告警类型
            severity: 告警级别
            title: 告警标题
            message: 告警详情
            context: 告警上下文
            channels: 通知渠道

        Returns:
            创建的告警
        """
        alert = Alert(
            alert_id=str(uuid.uuid4()),
            rule_id="manual",
            tenant_id=tenant_id,
            alert_type=alert_type,
            severity=severity,
            title=title,
            message=message,
            context=context or {},
        )

        await self._alert_storage.save_alert(alert)
        logger.info(f"触发告警: {alert.alert_id}, type={alert_type.value}")

        # 发送通知
        if channels:
            await self._send_notifications(alert, channels)

        return alert

    async def _create_alert(
        self,
        rule: Any,  # AlertRule
        tenant_id: str,
        context: dict[str, Any],
    ) -> Alert:
        """创建告警

        Args:
            rule: 告警规则
            tenant_id: 租户 ID
            context: 评估上下文

        Returns:
            创建的告警
        """
        # 生成告警标题和消息
        title = self._generate_title(rule, context)
        message = self._generate_message(rule, context)

        alert = Alert(
            alert_id=str(uuid.uuid4()),
            rule_id=rule.rule_id,
            tenant_id=tenant_id,
            alert_type=rule.alert_type,
            severity=rule.severity,
            title=title,
            message=message,
            context=context,
        )

        await self._alert_storage.save_alert(alert)
        logger.info(
            f"创建告警: {alert.alert_id}, "
            f"type={rule.alert_type.value}, "
            f"tenant={tenant_id}"
        )

        return alert

    def _generate_title(self, rule: Any, context: dict[str, Any]) -> str:
        """生成告警标题"""
        quota_type = context.get("quota_type", "")
        percentage = context.get("percentage", 0)

        if rule.alert_type == AlertType.QUOTA_WARNING:
            return f"{quota_type} 配额警告 ({percentage:.0%})"
        elif rule.alert_type == AlertType.QUOTA_EXCEEDED:
            return f"{quota_type} 配额超限"
        elif rule.alert_type == AlertType.QUOTA_CRITICAL:
            return f"{quota_type} 配额严重超限"
        elif rule.alert_type == AlertType.RATE_LIMIT_WARNING:
            return f"API 速率限制警告 ({percentage:.0%})"
        elif rule.alert_type == AlertType.RATE_LIMIT_EXCEEDED:
            return "API 速率限制超限"
        elif rule.alert_type == AlertType.CONCURRENT_WARNING:
            return f"并发请求警告 ({percentage:.0%})"
        elif rule.alert_type == AlertType.CONCURRENT_EXCEEDED:
            return "并发请求超限"
        else:
            return rule.name

    def _generate_message(self, rule: Any, context: dict[str, Any]) -> str:
        """生成告警消息"""
        current = context.get("current", 0)
        limit = context.get("limit", 0)
        percentage = context.get("percentage", 0)
        quota_type = context.get("quota_type", "")

        if rule.alert_type in (
            AlertType.QUOTA_WARNING,
            AlertType.QUOTA_EXCEEDED,
            AlertType.QUOTA_CRITICAL,
        ):
            return (
                f"{quota_type} 使用量已达到 {percentage:.1%}。\n"
                f"当前: {current}, 限制: {limit}"
            )
        elif rule.alert_type in (
            AlertType.RATE_LIMIT_WARNING,
            AlertType.RATE_LIMIT_EXCEEDED,
        ):
            return (
                f"API 调用速率已达到 {percentage:.1%}。\n"
                f"当前: {current}/分钟, 限制: {limit}/分钟"
            )
        elif rule.alert_type in (
            AlertType.CONCURRENT_WARNING,
            AlertType.CONCURRENT_EXCEEDED,
        ):
            return (
                f"并发请求数已达到 {percentage:.1%}。\n"
                f"当前: {current}, 限制: {limit}"
            )
        else:
            return rule.description

    # ========================================================================
    # 告警去重和节流
    # ========================================================================

    async def _should_suppress(
        self,
        rule_id: str,
        tenant_id: str,
        throttle_seconds: int,
    ) -> bool:
        """检查是否应该抑制告警

        Args:
            rule_id: 规则 ID
            tenant_id: 租户 ID
            throttle_seconds: 节流时间

        Returns:
            是否应该抑制
        """
        if isinstance(self._alert_storage, MemoryAlertStorage):
            recent = await self._alert_storage.get_recent_alert_by_rule(
                rule_id, tenant_id, throttle_seconds
            )
            return recent is not None
        return False

    async def _exceeds_hourly_limit(
        self,
        rule_id: str,
        tenant_id: str,
        max_per_hour: int,
    ) -> bool:
        """检查是否超过每小时限制

        Args:
            rule_id: 规则 ID
            tenant_id: 租户 ID
            max_per_hour: 每小时最大数量

        Returns:
            是否超过限制
        """
        if isinstance(self._alert_storage, MemoryAlertStorage):
            count = await self._alert_storage.get_alerts_count_in_window(
                rule_id, tenant_id, 3600
            )
            return count >= max_per_hour
        return False

    # ========================================================================
    # 告警状态管理
    # ========================================================================

    async def resolve_alert(
        self,
        alert_id: str,
        resolved_by: str | None = None,
        note: str | None = None,
    ) -> Alert | None:
        """解决告警

        Args:
            alert_id: 告警 ID
            resolved_by: 解决者 ID
            note: 解决备注

        Returns:
            更新后的告警
        """
        alert = await self._alert_storage.get_alert(alert_id)
        if not alert:
            return None

        alert.status = AlertStatus.RESOLVED
        alert.resolved_at = datetime.now()
        alert.resolved_by = resolved_by
        alert.resolution_note = note

        await self._alert_storage.update_alert(alert)
        logger.info(f"解决告警: {alert_id}")

        return alert

    async def acknowledge_alert(
        self,
        alert_id: str,
        acknowledged_by: str | None = None,
    ) -> Alert | None:
        """确认告警

        Args:
            alert_id: 告警 ID
            acknowledged_by: 确认者 ID

        Returns:
            更新后的告警
        """
        alert = await self._alert_storage.get_alert(alert_id)
        if not alert:
            return None

        alert.status = AlertStatus.ACKNOWLEDGED
        alert.acknowledged_at = datetime.now()
        if acknowledged_by:
            alert.metadata["acknowledged_by"] = acknowledged_by

        await self._alert_storage.update_alert(alert)
        logger.info(f"确认告警: {alert_id}")

        return alert

    async def suppress_alert(
        self,
        alert_id: str,
        duration_seconds: int = 3600,
    ) -> Alert | None:
        """抑制告警

        Args:
            alert_id: 告警 ID
            duration_seconds: 抑制时长（秒）

        Returns:
            更新后的告警
        """
        alert = await self._alert_storage.get_alert(alert_id)
        if not alert:
            return None

        alert.status = AlertStatus.SUPPRESSED
        alert.suppressed_until = datetime.now() + timedelta(seconds=duration_seconds)

        await self._alert_storage.update_alert(alert)
        logger.info(f"抑制告警: {alert_id}, duration={duration_seconds}s")

        return alert

    async def auto_resolve_alerts(self, tenant_id: str) -> int:
        """自动解决告警

        检查活跃告警，如果条件不再满足则自动解决。

        Args:
            tenant_id: 租户 ID

        Returns:
            解决的告警数量
        """
        resolved_count = 0
        active_alerts = await self._alert_storage.get_active_alerts(tenant_id)

        for alert in active_alerts:
            rule = self._rule_manager.get_rule(alert.rule_id)
            if not rule:
                continue

            # 重新评估规则
            triggered, _ = await self._rule_evaluator.evaluate(rule, tenant_id)

            if not triggered:
                # 条件不再满足，自动解决
                await self.resolve_alert(
                    alert.alert_id,
                    resolved_by="system",
                    note="条件不再满足，自动解决",
                )
                resolved_count += 1

        if resolved_count > 0:
            logger.info(f"自动解决 {resolved_count} 条告警: tenant={tenant_id}")

        return resolved_count

    # ========================================================================
    # 通知
    # ========================================================================

    def on_notification(self, handler: Callable[[Alert], Any]) -> None:
        """注册通知处理器

        Args:
            handler: 通知处理器
        """
        self._notification_handlers.append(handler)

    async def _send_notifications(
        self,
        alert: Alert,
        channels: list[NotificationChannel],
    ) -> None:
        """发送通知

        Args:
            alert: 告警
            channels: 通知渠道
        """
        for channel in channels:
            try:
                # 创建通知记录
                notification = AlertNotification(
                    notification_id=str(uuid.uuid4()),
                    alert_id=alert.alert_id,
                    tenant_id=alert.tenant_id,
                    channel=channel,
                    title=alert.title,
                    content=alert.message,
                )

                # 调用通知处理器
                for handler in self._notification_handlers:
                    try:
                        result = handler(alert)
                        if asyncio.iscoroutine(result):
                            await result
                    except Exception as e:
                        logger.error(f"通知处理器失败: {e}")
                        notification.success = False
                        notification.error_message = str(e)

                # 记录已发送的渠道
                alert.notifications_sent.append(channel.value)

                # 保存通知记录
                await self._alert_storage.save_notification(notification)

                logger.debug(
                    f"发送通知: alert={alert.alert_id}, channel={channel.value}"
                )

            except Exception as e:
                logger.error(f"发送通知失败: channel={channel.value}, error={e}")

    # ========================================================================
    # 事件处理
    # ========================================================================

    async def handle_tenant_event(self, event: TenantEvent) -> None:
        """处理租户事件

        将租户事件转换为告警。

        Args:
            event: 租户事件
        """
        # 配额超限事件
        if event.event_type == TenantEventType.QUOTA_EXCEEDED:
            quota_type = event.metadata.get("quota_type", "unknown")
            current = event.metadata.get("current", 0)
            limit = event.metadata.get("limit", 0)

            await self.trigger_alert(
                tenant_id=event.tenant_id,
                alert_type=AlertType.QUOTA_EXCEEDED,
                severity=AlertSeverity.ERROR,
                title=f"{quota_type} 配额超限",
                message=f"{quota_type} 使用量已超限。当前: {current}, 限制: {limit}",
                context={
                    "quota_type": quota_type,
                    "current": current,
                    "limit": limit,
                    "event_id": str(event.timestamp),
                },
                channels=[NotificationChannel.SYSTEM_EVENT],
            )

        # 租户暂停事件
        elif event.event_type == TenantEventType.SUSPENDED:
            await self.trigger_alert(
                tenant_id=event.tenant_id,
                alert_type=AlertType.TENANT_SUSPENDED,
                severity=AlertSeverity.WARNING,
                title="租户已暂停",
                message=event.message or "租户已被暂停",
                context={"reason": event.message},
                channels=[NotificationChannel.SYSTEM_EVENT],
            )

        # 租户过期事件
        elif event.event_type == TenantEventType.EXPIRED:
            await self.trigger_alert(
                tenant_id=event.tenant_id,
                alert_type=AlertType.TENANT_EXPIRED,
                severity=AlertSeverity.WARNING,
                title="租户已过期",
                message=event.message or "租户已过期",
                context={},
                channels=[NotificationChannel.SYSTEM_EVENT],
            )

        # 套餐变更事件
        elif event.event_type == TenantEventType.TIER_CHANGED:
            await self.trigger_alert(
                tenant_id=event.tenant_id,
                alert_type=AlertType.TIER_CHANGED,
                severity=AlertSeverity.INFO,
                title="套餐已变更",
                message=f"套餐从 {event.old_value} 变更为 {event.new_value}",
                context={
                    "old_tier": event.old_value,
                    "new_tier": event.new_value,
                },
                channels=[NotificationChannel.SYSTEM_EVENT],
            )

    # ========================================================================
    # 后台扫描
    # ========================================================================

    async def start_periodic_scan(self, interval_seconds: int = 300) -> None:
        """启动定期扫描

        Args:
            interval_seconds: 扫描间隔（秒）
        """
        if self._running:
            return

        self._running = True
        self._scan_task = asyncio.create_task(
            self._periodic_scan_loop(interval_seconds)
        )
        logger.info(f"启动告警定期扫描，间隔 {interval_seconds} 秒")

    async def stop_periodic_scan(self) -> None:
        """停止定期扫描"""
        self._running = False
        if self._scan_task:
            self._scan_task.cancel()
            try:
                await self._scan_task
            except asyncio.CancelledError:
                pass
            self._scan_task = None
        logger.info("停止告警定期扫描")

    async def _periodic_scan_loop(self, interval_seconds: int) -> None:
        """定期扫描循环

        Args:
            interval_seconds: 扫描间隔
        """
        while self._running:
            try:
                await self._scan_all_tenants()
            except Exception as e:
                logger.error(f"定期扫描失败: {e}")

            await asyncio.sleep(interval_seconds)

    async def _scan_all_tenants(self) -> None:
        """扫描所有租户"""
        tenants = await self._tenant_storage.list()

        for tenant in tenants:
            try:
                # 检查并触发告警
                await self.check_and_trigger(tenant.id)

                # 自动解决不再满足条件的告警
                await self.auto_resolve_alerts(tenant.id)

            except Exception as e:
                logger.error(f"扫描租户失败: tenant={tenant.id}, error={e}")

    # ========================================================================
    # 查询接口
    # ========================================================================

    async def get_alert(self, alert_id: str) -> Alert | None:
        """获取告警"""
        return await self._alert_storage.get_alert(alert_id)

    async def list_alerts(
        self,
        tenant_id: str | None = None,
        status: AlertStatus | None = None,
        severity: AlertSeverity | None = None,
        alert_type: AlertType | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Alert]:
        """列出告警"""
        return await self._alert_storage.list_alerts(
            tenant_id=tenant_id,
            status=status,
            severity=severity,
            alert_type=alert_type,
            limit=limit,
            offset=offset,
        )

    async def get_active_alerts(self, tenant_id: str | None = None) -> list[Alert]:
        """获取活跃告警"""
        return await self._alert_storage.get_active_alerts(tenant_id)

    async def get_stats(
        self,
        tenant_id: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ):
        """获取告警统计"""
        return await self._alert_storage.get_stats(
            tenant_id=tenant_id,
            start_time=start_time,
            end_time=end_time,
        )


# ============================================================================
# 全局实例管理
# ============================================================================


_alert_engine: AlertEngine | None = None


def configure_alert_engine(
    tenant_storage: TenantStorage,
    quota_manager: QuotaManager,
    alert_storage: AlertStorage | None = None,
) -> AlertEngine:
    """配置告警引擎

    Args:
        tenant_storage: 租户存储
        quota_manager: 配额管理器
        alert_storage: 告警存储

    Returns:
        告警引擎实例
    """
    global _alert_engine
    _alert_engine = AlertEngine(
        tenant_storage=tenant_storage,
        quota_manager=quota_manager,
        alert_storage=alert_storage,
    )
    return _alert_engine


def get_alert_engine() -> AlertEngine:
    """获取告警引擎

    Returns:
        告警引擎实例

    Raises:
        RuntimeError: 如果未配置
    """
    if _alert_engine is None:
        raise RuntimeError("告警引擎未配置，请先调用 configure_alert_engine()")
    return _alert_engine
