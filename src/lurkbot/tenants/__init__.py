"""多租户模块

提供多租户支持，包括：
- 租户数据模型
- 租户存储
- 配额管理
- 租户配置
- 租户隔离
- 租户管理器
"""

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
]
