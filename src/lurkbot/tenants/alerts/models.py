"""告警系统数据模型

定义告警相关的数据结构，包括告警规则、告警记录、通知配置等。
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from ..quota import QuotaType


# ============================================================================
# 告警枚举类型
# ============================================================================


class AlertSeverity(str, Enum):
    """告警严重级别"""

    INFO = "info"  # 信息
    WARNING = "warning"  # 警告
    ERROR = "error"  # 错误
    CRITICAL = "critical"  # 严重


class AlertStatus(str, Enum):
    """告警状态"""

    ACTIVE = "active"  # 活跃
    RESOLVED = "resolved"  # 已解决
    SUPPRESSED = "suppressed"  # 已抑制
    ACKNOWLEDGED = "acknowledged"  # 已确认


class AlertType(str, Enum):
    """告警类型"""

    # 配额相关
    QUOTA_WARNING = "quota_warning"  # 配额警告（接近限制）
    QUOTA_EXCEEDED = "quota_exceeded"  # 配额超限
    QUOTA_CRITICAL = "quota_critical"  # 配额严重超限

    # 速率限制
    RATE_LIMIT_WARNING = "rate_limit_warning"  # 速率限制警告
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"  # 速率限制超限

    # 并发请求
    CONCURRENT_WARNING = "concurrent_warning"  # 并发警告
    CONCURRENT_EXCEEDED = "concurrent_exceeded"  # 并发超限

    # 异常检测
    ANOMALY_USAGE = "anomaly_usage"  # 异常使用模式
    ANOMALY_SPIKE = "anomaly_spike"  # 突发流量
    ANOMALY_DROP = "anomaly_drop"  # 流量骤降

    # 状态变更
    TENANT_SUSPENDED = "tenant_suspended"  # 租户暂停
    TENANT_EXPIRED = "tenant_expired"  # 租户过期
    TIER_CHANGED = "tier_changed"  # 套餐变更

    # 系统告警
    SYSTEM_ERROR = "system_error"  # 系统错误
    SYSTEM_WARNING = "system_warning"  # 系统警告


class NotificationChannel(str, Enum):
    """通知渠道"""

    SYSTEM_EVENT = "system_event"  # 系统事件队列
    EMAIL = "email"  # 邮件
    DINGTALK = "dingtalk"  # 钉钉
    FEISHU = "feishu"  # 飞书
    WEWORK = "wework"  # 企业微信
    WEBHOOK = "webhook"  # 自定义 Webhook


class ConditionOperator(str, Enum):
    """条件运算符"""

    GT = "gt"  # 大于
    GTE = "gte"  # 大于等于
    LT = "lt"  # 小于
    LTE = "lte"  # 小于等于
    EQ = "eq"  # 等于
    NEQ = "neq"  # 不等于
    CHANGE_RATE = "change_rate"  # 变化率


# ============================================================================
# 告警条件
# ============================================================================


class AlertCondition(BaseModel):
    """告警条件

    定义触发告警的条件。
    """

    # 条件类型
    condition_type: str = Field(
        default="threshold",
        description="条件类型: threshold/trend/anomaly",
    )

    # 指标
    metric: str = Field(description="监控指标")
    quota_type: QuotaType | None = Field(default=None, description="配额类型（如适用）")

    # 比较
    operator: ConditionOperator = Field(
        default=ConditionOperator.GTE,
        description="比较运算符",
    )
    threshold: float = Field(description="阈值")

    # 持续时间（可选）
    duration_seconds: int = Field(
        default=0,
        description="持续时间（秒），0 表示立即触发",
    )

    # 额外参数
    params: dict[str, Any] = Field(
        default_factory=dict,
        description="额外参数",
    )


# ============================================================================
# 告警规则
# ============================================================================


class AlertRule(BaseModel):
    """告警规则

    定义告警触发规则。
    """

    # 规则标识
    rule_id: str = Field(description="规则 ID")
    name: str = Field(description="规则名称")
    description: str = Field(default="", description="规则描述")

    # 告警类型和级别
    alert_type: AlertType = Field(description="告警类型")
    severity: AlertSeverity = Field(
        default=AlertSeverity.WARNING,
        description="告警级别",
    )

    # 触发条件
    condition: AlertCondition = Field(description="触发条件")

    # 通知配置
    channels: list[NotificationChannel] = Field(
        default_factory=lambda: [NotificationChannel.SYSTEM_EVENT],
        description="通知渠道",
    )

    # 节流配置
    throttle_seconds: int = Field(
        default=300,
        description="节流时间（秒），同一告警在此时间内不重复触发",
    )
    max_alerts_per_hour: int = Field(
        default=10,
        description="每小时最大告警数",
    )

    # 启用状态
    enabled: bool = Field(default=True, description="是否启用")

    # 适用范围
    tenant_ids: list[str] | None = Field(
        default=None,
        description="适用的租户 ID 列表，None 表示所有租户",
    )

    # 元数据
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="规则元数据",
    )
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="创建时间",
    )
    updated_at: datetime = Field(
        default_factory=datetime.now,
        description="更新时间",
    )


# ============================================================================
# 告警记录
# ============================================================================


class Alert(BaseModel):
    """告警记录

    代表一条告警。
    """

    # 告警标识
    alert_id: str = Field(description="告警 ID")
    rule_id: str = Field(description="触发规则 ID")
    tenant_id: str = Field(description="租户 ID")

    # 告警信息
    alert_type: AlertType = Field(description="告警类型")
    severity: AlertSeverity = Field(description="告警级别")
    title: str = Field(description="告警标题")
    message: str = Field(description="告警详情")

    # 状态
    status: AlertStatus = Field(
        default=AlertStatus.ACTIVE,
        description="告警状态",
    )

    # 时间戳
    triggered_at: datetime = Field(
        default_factory=datetime.now,
        description="触发时间",
    )
    resolved_at: datetime | None = Field(
        default=None,
        description="解决时间",
    )
    acknowledged_at: datetime | None = Field(
        default=None,
        description="确认时间",
    )
    suppressed_until: datetime | None = Field(
        default=None,
        description="抑制截止时间",
    )

    # 触发上下文
    context: dict[str, Any] = Field(
        default_factory=dict,
        description="触发上下文（指标值、阈值等）",
    )

    # 通知记录
    notifications_sent: list[str] = Field(
        default_factory=list,
        description="已发送的通知渠道",
    )

    # 处理信息
    resolved_by: str | None = Field(
        default=None,
        description="解决者 ID",
    )
    resolution_note: str | None = Field(
        default=None,
        description="解决备注",
    )

    # 元数据
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="告警元数据",
    )

    def is_active(self) -> bool:
        """检查告警是否活跃"""
        return self.status == AlertStatus.ACTIVE

    def is_suppressed(self) -> bool:
        """检查告警是否被抑制"""
        if self.status != AlertStatus.SUPPRESSED:
            return False
        if self.suppressed_until and datetime.now() > self.suppressed_until:
            return False
        return True

    def can_notify(self) -> bool:
        """检查是否可以发送通知"""
        return self.status == AlertStatus.ACTIVE and not self.is_suppressed()


# ============================================================================
# 通知记录
# ============================================================================


class AlertNotification(BaseModel):
    """告警通知记录"""

    # 通知标识
    notification_id: str = Field(description="通知 ID")
    alert_id: str = Field(description="关联告警 ID")
    tenant_id: str = Field(description="租户 ID")

    # 通知渠道
    channel: NotificationChannel = Field(description="通知渠道")

    # 通知内容
    title: str = Field(description="通知标题")
    content: str = Field(description="通知内容")

    # 发送状态
    sent_at: datetime = Field(
        default_factory=datetime.now,
        description="发送时间",
    )
    success: bool = Field(default=True, description="是否成功")
    error_message: str | None = Field(
        default=None,
        description="错误信息（如失败）",
    )

    # 接收者
    recipients: list[str] = Field(
        default_factory=list,
        description="接收者列表",
    )

    # 元数据
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="通知元数据",
    )


# ============================================================================
# 通知配置
# ============================================================================


class NotificationConfig(BaseModel):
    """通知渠道配置"""

    # 渠道类型
    channel: NotificationChannel = Field(description="通知渠道")
    enabled: bool = Field(default=True, description="是否启用")

    # 渠道配置
    config: dict[str, Any] = Field(
        default_factory=dict,
        description="渠道配置",
    )

    # 接收者
    recipients: list[str] = Field(
        default_factory=list,
        description="默认接收者",
    )

    # 过滤条件
    min_severity: AlertSeverity = Field(
        default=AlertSeverity.WARNING,
        description="最低告警级别",
    )
    alert_types: list[AlertType] | None = Field(
        default=None,
        description="告警类型过滤，None 表示所有",
    )


class TenantNotificationSettings(BaseModel):
    """租户通知设置"""

    tenant_id: str = Field(description="租户 ID")

    # 通知渠道配置
    channels: list[NotificationConfig] = Field(
        default_factory=list,
        description="通知渠道配置",
    )

    # 全局设置
    enabled: bool = Field(default=True, description="是否启用通知")
    quiet_hours_start: int | None = Field(
        default=None,
        description="静默时段开始（小时，0-23）",
    )
    quiet_hours_end: int | None = Field(
        default=None,
        description="静默时段结束（小时，0-23）",
    )

    # 聚合设置
    aggregate_alerts: bool = Field(
        default=True,
        description="是否聚合告警",
    )
    aggregate_window_minutes: int = Field(
        default=5,
        description="聚合窗口（分钟）",
    )


# ============================================================================
# 告警统计
# ============================================================================


class AlertStats(BaseModel):
    """告警统计"""

    tenant_id: str | None = Field(
        default=None,
        description="租户 ID，None 表示全局统计",
    )
    period_start: datetime = Field(description="统计周期开始")
    period_end: datetime = Field(description="统计周期结束")

    # 告警计数
    total_alerts: int = Field(default=0, description="总告警数")
    active_alerts: int = Field(default=0, description="活跃告警数")
    resolved_alerts: int = Field(default=0, description="已解决告警数")
    suppressed_alerts: int = Field(default=0, description="已抑制告警数")

    # 按级别统计
    by_severity: dict[str, int] = Field(
        default_factory=dict,
        description="按级别统计",
    )

    # 按类型统计
    by_type: dict[str, int] = Field(
        default_factory=dict,
        description="按类型统计",
    )

    # 平均解决时间
    avg_resolution_time_seconds: float | None = Field(
        default=None,
        description="平均解决时间（秒）",
    )

    # 通知统计
    notifications_sent: int = Field(default=0, description="发送通知数")
    notifications_failed: int = Field(default=0, description="失败通知数")
