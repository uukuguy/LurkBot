"""告警存储

提供告警记录的持久化存储功能。
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

from loguru import logger

from .models import (
    Alert,
    AlertNotification,
    AlertSeverity,
    AlertStats,
    AlertStatus,
    AlertType,
)


# ============================================================================
# 告警存储抽象基类
# ============================================================================


class AlertStorage(ABC):
    """告警存储抽象基类"""

    @abstractmethod
    async def save_alert(self, alert: Alert) -> None:
        """保存告警

        Args:
            alert: 告警记录
        """
        pass

    @abstractmethod
    async def get_alert(self, alert_id: str) -> Alert | None:
        """获取告警

        Args:
            alert_id: 告警 ID

        Returns:
            告警记录
        """
        pass

    @abstractmethod
    async def update_alert(self, alert: Alert) -> None:
        """更新告警

        Args:
            alert: 告警记录
        """
        pass

    @abstractmethod
    async def delete_alert(self, alert_id: str) -> bool:
        """删除告警

        Args:
            alert_id: 告警 ID

        Returns:
            是否成功
        """
        pass

    @abstractmethod
    async def list_alerts(
        self,
        tenant_id: str | None = None,
        status: AlertStatus | None = None,
        severity: AlertSeverity | None = None,
        alert_type: AlertType | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Alert]:
        """列出告警

        Args:
            tenant_id: 租户 ID（可选）
            status: 状态过滤
            severity: 级别过滤
            alert_type: 类型过滤
            start_time: 开始时间
            end_time: 结束时间
            limit: 返回数量限制
            offset: 偏移量

        Returns:
            告警列表
        """
        pass

    @abstractmethod
    async def count_alerts(
        self,
        tenant_id: str | None = None,
        status: AlertStatus | None = None,
        severity: AlertSeverity | None = None,
        alert_type: AlertType | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> int:
        """统计告警数量

        Args:
            tenant_id: 租户 ID（可选）
            status: 状态过滤
            severity: 级别过滤
            alert_type: 类型过滤
            start_time: 开始时间
            end_time: 结束时间

        Returns:
            告警数量
        """
        pass

    @abstractmethod
    async def get_active_alerts(
        self,
        tenant_id: str | None = None,
    ) -> list[Alert]:
        """获取活跃告警

        Args:
            tenant_id: 租户 ID（可选）

        Returns:
            活跃告警列表
        """
        pass

    @abstractmethod
    async def save_notification(self, notification: AlertNotification) -> None:
        """保存通知记录

        Args:
            notification: 通知记录
        """
        pass

    @abstractmethod
    async def get_notifications(
        self,
        alert_id: str | None = None,
        tenant_id: str | None = None,
        limit: int = 100,
    ) -> list[AlertNotification]:
        """获取通知记录

        Args:
            alert_id: 告警 ID（可选）
            tenant_id: 租户 ID（可选）
            limit: 返回数量限制

        Returns:
            通知记录列表
        """
        pass

    @abstractmethod
    async def get_stats(
        self,
        tenant_id: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> AlertStats:
        """获取告警统计

        Args:
            tenant_id: 租户 ID（可选）
            start_time: 开始时间
            end_time: 结束时间

        Returns:
            告警统计
        """
        pass


# ============================================================================
# 内存告警存储
# ============================================================================


class MemoryAlertStorage(AlertStorage):
    """内存告警存储

    用于开发和测试的内存存储实现。
    """

    def __init__(self, max_alerts: int = 10000) -> None:
        """初始化内存存储

        Args:
            max_alerts: 最大告警数量
        """
        self._alerts: dict[str, Alert] = {}
        self._notifications: dict[str, AlertNotification] = {}
        self._max_alerts = max_alerts
        self._lock = asyncio.Lock()

    async def save_alert(self, alert: Alert) -> None:
        """保存告警"""
        async with self._lock:
            # 检查容量
            if len(self._alerts) >= self._max_alerts:
                await self._cleanup_old_alerts()

            self._alerts[alert.alert_id] = alert
            logger.debug(f"保存告警: {alert.alert_id}")

    async def get_alert(self, alert_id: str) -> Alert | None:
        """获取告警"""
        return self._alerts.get(alert_id)

    async def update_alert(self, alert: Alert) -> None:
        """更新告警"""
        async with self._lock:
            if alert.alert_id in self._alerts:
                self._alerts[alert.alert_id] = alert
                logger.debug(f"更新告警: {alert.alert_id}")

    async def delete_alert(self, alert_id: str) -> bool:
        """删除告警"""
        async with self._lock:
            if alert_id in self._alerts:
                del self._alerts[alert_id]
                logger.debug(f"删除告警: {alert_id}")
                return True
            return False

    async def list_alerts(
        self,
        tenant_id: str | None = None,
        status: AlertStatus | None = None,
        severity: AlertSeverity | None = None,
        alert_type: AlertType | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Alert]:
        """列出告警"""
        alerts = list(self._alerts.values())

        # 过滤
        if tenant_id:
            alerts = [a for a in alerts if a.tenant_id == tenant_id]
        if status:
            alerts = [a for a in alerts if a.status == status]
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        if alert_type:
            alerts = [a for a in alerts if a.alert_type == alert_type]
        if start_time:
            alerts = [a for a in alerts if a.triggered_at >= start_time]
        if end_time:
            alerts = [a for a in alerts if a.triggered_at <= end_time]

        # 排序（按触发时间倒序）
        alerts.sort(key=lambda a: a.triggered_at, reverse=True)

        # 分页
        return alerts[offset : offset + limit]

    async def count_alerts(
        self,
        tenant_id: str | None = None,
        status: AlertStatus | None = None,
        severity: AlertSeverity | None = None,
        alert_type: AlertType | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> int:
        """统计告警数量"""
        alerts = list(self._alerts.values())

        # 过滤
        if tenant_id:
            alerts = [a for a in alerts if a.tenant_id == tenant_id]
        if status:
            alerts = [a for a in alerts if a.status == status]
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        if alert_type:
            alerts = [a for a in alerts if a.alert_type == alert_type]
        if start_time:
            alerts = [a for a in alerts if a.triggered_at >= start_time]
        if end_time:
            alerts = [a for a in alerts if a.triggered_at <= end_time]

        return len(alerts)

    async def get_active_alerts(
        self,
        tenant_id: str | None = None,
    ) -> list[Alert]:
        """获取活跃告警"""
        return await self.list_alerts(
            tenant_id=tenant_id,
            status=AlertStatus.ACTIVE,
            limit=1000,
        )

    async def save_notification(self, notification: AlertNotification) -> None:
        """保存通知记录"""
        async with self._lock:
            self._notifications[notification.notification_id] = notification
            logger.debug(f"保存通知: {notification.notification_id}")

    async def get_notifications(
        self,
        alert_id: str | None = None,
        tenant_id: str | None = None,
        limit: int = 100,
    ) -> list[AlertNotification]:
        """获取通知记录"""
        notifications = list(self._notifications.values())

        # 过滤
        if alert_id:
            notifications = [n for n in notifications if n.alert_id == alert_id]
        if tenant_id:
            notifications = [n for n in notifications if n.tenant_id == tenant_id]

        # 排序（按发送时间倒序）
        notifications.sort(key=lambda n: n.sent_at, reverse=True)

        return notifications[:limit]

    async def get_stats(
        self,
        tenant_id: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> AlertStats:
        """获取告警统计"""
        now = datetime.now()
        start = start_time or (now - timedelta(days=7))
        end = end_time or now

        # 获取时间范围内的告警
        alerts = await self.list_alerts(
            tenant_id=tenant_id,
            start_time=start,
            end_time=end,
            limit=10000,
        )

        # 统计
        total = len(alerts)
        active = len([a for a in alerts if a.status == AlertStatus.ACTIVE])
        resolved = len([a for a in alerts if a.status == AlertStatus.RESOLVED])
        suppressed = len([a for a in alerts if a.status == AlertStatus.SUPPRESSED])

        # 按级别统计
        by_severity: dict[str, int] = defaultdict(int)
        for alert in alerts:
            by_severity[alert.severity.value] += 1

        # 按类型统计
        by_type: dict[str, int] = defaultdict(int)
        for alert in alerts:
            by_type[alert.alert_type.value] += 1

        # 计算平均解决时间
        resolution_times = []
        for alert in alerts:
            if alert.status == AlertStatus.RESOLVED and alert.resolved_at:
                delta = (alert.resolved_at - alert.triggered_at).total_seconds()
                resolution_times.append(delta)

        avg_resolution = None
        if resolution_times:
            avg_resolution = sum(resolution_times) / len(resolution_times)

        # 通知统计
        notifications = await self.get_notifications(tenant_id=tenant_id, limit=10000)
        notifications_in_range = [
            n for n in notifications if start <= n.sent_at <= end
        ]
        notifications_sent = len(notifications_in_range)
        notifications_failed = len([n for n in notifications_in_range if not n.success])

        return AlertStats(
            tenant_id=tenant_id,
            period_start=start,
            period_end=end,
            total_alerts=total,
            active_alerts=active,
            resolved_alerts=resolved,
            suppressed_alerts=suppressed,
            by_severity=dict(by_severity),
            by_type=dict(by_type),
            avg_resolution_time_seconds=avg_resolution,
            notifications_sent=notifications_sent,
            notifications_failed=notifications_failed,
        )

    async def _cleanup_old_alerts(self) -> None:
        """清理旧告警"""
        # 保留最近的告警，删除最旧的 20%
        if not self._alerts:
            return

        alerts = sorted(
            self._alerts.values(),
            key=lambda a: a.triggered_at,
        )

        # 删除最旧的 20%
        to_delete = len(alerts) // 5
        for alert in alerts[:to_delete]:
            del self._alerts[alert.alert_id]

        logger.info(f"清理了 {to_delete} 条旧告警")

    async def get_recent_alert_by_rule(
        self,
        rule_id: str,
        tenant_id: str,
        within_seconds: int,
    ) -> Alert | None:
        """获取最近的同规则告警

        用于告警去重。

        Args:
            rule_id: 规则 ID
            tenant_id: 租户 ID
            within_seconds: 时间窗口（秒）

        Returns:
            最近的告警（如果存在）
        """
        cutoff = datetime.now() - timedelta(seconds=within_seconds)

        for alert in self._alerts.values():
            if (
                alert.rule_id == rule_id
                and alert.tenant_id == tenant_id
                and alert.triggered_at >= cutoff
            ):
                return alert

        return None

    async def get_alerts_count_in_window(
        self,
        rule_id: str,
        tenant_id: str,
        window_seconds: int,
    ) -> int:
        """获取时间窗口内的告警数量

        用于告警节流。

        Args:
            rule_id: 规则 ID
            tenant_id: 租户 ID
            window_seconds: 时间窗口（秒）

        Returns:
            告警数量
        """
        cutoff = datetime.now() - timedelta(seconds=window_seconds)

        count = 0
        for alert in self._alerts.values():
            if (
                alert.rule_id == rule_id
                and alert.tenant_id == tenant_id
                and alert.triggered_at >= cutoff
            ):
                count += 1

        return count

    def clear(self) -> None:
        """清空所有数据（仅用于测试）"""
        self._alerts.clear()
        self._notifications.clear()
