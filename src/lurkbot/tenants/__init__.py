"""多租户模块

提供多租户支持，包括：
- 租户数据模型
- 租户存储
- 配额管理
- 租户配置
- 租户隔离
- 租户管理器
- 错误类型
- 守卫类
- 中间件
- 统计服务
- 告警系统
"""

from .errors import (
    ConcurrentLimitError,
    PolicyDeniedError,
    QuotaExceededError,
    RateLimitedError,
    TenantError,
    TenantErrorCode,
    TenantInactiveError,
    TenantNotFoundError,
)
from .guards import (
    PolicyGuard,
    QuotaGuard,
    configure_guards,
    get_policy_guard,
    get_quota_guard,
)
from .isolation import (
    TenantContext,
    TenantContextManager,
    TenantIsolation,
    get_current_tenant,
    get_current_tenant_id,
    inject_tenant_id,
    require_tenant_context,
    set_current_tenant,
)
from .manager import TenantManager
from .middleware import (
    TenantMiddleware,
    get_tenant_from_request,
    require_tenant,
)
from .models import (
    QUOTA_BASIC,
    QUOTA_ENTERPRISE,
    QUOTA_FREE,
    QUOTA_PROFESSIONAL,
    TIER_QUOTAS,
    Tenant,
    TenantConfig,
    TenantEvent,
    TenantEventType,
    TenantQuota,
    TenantStatus,
    TenantTier,
    TenantUsage,
    get_tier_quota,
)
from .quota import (
    QuotaCheckDetail,
    QuotaCheckResult,
    QuotaManager,
    QuotaType,
)
from .storage import (
    FileTenantStorage,
    MemoryTenantStorage,
    TenantStorage,
)
from .stats import (
    QuotaUsageStats,
    StatsPeriod,
    SystemOverview,
    TenantDashboard,
    TenantOverview,
    TenantStatsService,
    TrendDirection,
    UsageDataPoint,
    UsageTrend,
    configure_stats_service,
    get_stats_service,
)
from .api import (
    create_tenant_stats_router,
)
from .alerts import (
    Alert,
    AlertCondition,
    AlertEngine,
    AlertNotification,
    AlertRule,
    AlertSeverity,
    AlertStats,
    AlertStatus,
    AlertStorage,
    AlertType,
    MemoryAlertStorage,
    NotificationService,
    RuleEvaluator,
    RuleManager,
    configure_alert_engine,
    create_alert_router,
    create_default_rules,
    get_alert_engine,
)

__all__ = [
    # Models
    "Tenant",
    "TenantStatus",
    "TenantTier",
    "TenantQuota",
    "TenantConfig",
    "TenantUsage",
    "TenantEvent",
    "TenantEventType",
    # Quotas
    "QUOTA_FREE",
    "QUOTA_BASIC",
    "QUOTA_PROFESSIONAL",
    "QUOTA_ENTERPRISE",
    "TIER_QUOTAS",
    "get_tier_quota",
    # Storage
    "TenantStorage",
    "MemoryTenantStorage",
    "FileTenantStorage",
    # Quota Manager
    "QuotaManager",
    "QuotaType",
    "QuotaCheckResult",
    "QuotaCheckDetail",
    # Isolation
    "TenantIsolation",
    "TenantContext",
    "TenantContextManager",
    "get_current_tenant",
    "get_current_tenant_id",
    "set_current_tenant",
    "require_tenant_context",
    "inject_tenant_id",
    # Manager
    "TenantManager",
    # Errors
    "TenantError",
    "TenantErrorCode",
    "QuotaExceededError",
    "RateLimitedError",
    "ConcurrentLimitError",
    "PolicyDeniedError",
    "TenantNotFoundError",
    "TenantInactiveError",
    # Guards
    "QuotaGuard",
    "PolicyGuard",
    "get_quota_guard",
    "get_policy_guard",
    "configure_guards",
    # Middleware
    "TenantMiddleware",
    "get_tenant_from_request",
    "require_tenant",
    # Stats
    "TenantStatsService",
    "TenantOverview",
    "TenantDashboard",
    "SystemOverview",
    "QuotaUsageStats",
    "UsageTrend",
    "UsageDataPoint",
    "StatsPeriod",
    "TrendDirection",
    "configure_stats_service",
    "get_stats_service",
    # API
    "create_tenant_stats_router",
    # Alerts
    "Alert",
    "AlertCondition",
    "AlertEngine",
    "AlertNotification",
    "AlertRule",
    "AlertSeverity",
    "AlertStats",
    "AlertStatus",
    "AlertStorage",
    "AlertType",
    "MemoryAlertStorage",
    "NotificationService",
    "RuleEvaluator",
    "RuleManager",
    "configure_alert_engine",
    "create_alert_router",
    "create_default_rules",
    "get_alert_engine",
]
