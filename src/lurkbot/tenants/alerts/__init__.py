"""告警系统模块

提供多租户告警功能，包括：
- 告警规则引擎
- 告警触发和管理
- 多渠道通知
- 告警存储和查询
"""

from .api import create_alert_router
from .engine import (
    AlertEngine,
    configure_alert_engine,
    get_alert_engine,
)
from .models import (
    Alert,
    AlertCondition,
    AlertNotification,
    AlertRule,
    AlertSeverity,
    AlertStats,
    AlertStatus,
    AlertType,
    ConditionOperator,
    NotificationChannel,
    NotificationConfig,
    TenantNotificationSettings,
)
from .notifications import (
    DingTalkChannel,
    DingTalkConfig,
    EmailChannel,
    EmailConfig,
    FeishuChannel,
    FeishuConfig,
    NotificationChannelBase,
    NotificationService,
    SystemEventChannel,
    WebhookChannel,
    WebhookConfig,
    WeWorkChannel,
    WeWorkConfig,
    configure_notification_service,
    get_notification_service,
)
from .rules import (
    RuleEvaluator,
    RuleManager,
    create_default_rules,
)
from .storage import (
    AlertStorage,
    MemoryAlertStorage,
)

__all__ = [
    # API
    "create_alert_router",
    # Engine
    "AlertEngine",
    "configure_alert_engine",
    "get_alert_engine",
    # Models
    "Alert",
    "AlertCondition",
    "AlertNotification",
    "AlertRule",
    "AlertSeverity",
    "AlertStats",
    "AlertStatus",
    "AlertType",
    "ConditionOperator",
    "NotificationChannel",
    "NotificationConfig",
    "TenantNotificationSettings",
    # Notifications
    "DingTalkChannel",
    "DingTalkConfig",
    "EmailChannel",
    "EmailConfig",
    "FeishuChannel",
    "FeishuConfig",
    "NotificationChannelBase",
    "NotificationService",
    "SystemEventChannel",
    "WebhookChannel",
    "WebhookConfig",
    "WeWorkChannel",
    "WeWorkConfig",
    "configure_notification_service",
    "get_notification_service",
    # Rules
    "RuleEvaluator",
    "RuleManager",
    "create_default_rules",
    # Storage
    "AlertStorage",
    "MemoryAlertStorage",
]
