"""
Security Audit System

对标 MoltBot src/security/
"""

from .audit import SecurityFinding, apply_fixes, audit_security
from .audit_log import (
    AuditAction,
    AuditLogEntry,
    AuditLogger,
    AuditSeverity,
    audit_log,
    get_audit_logger,
)
from .dm_policy import (
    DMPolicyConfig,
    get_recommended_dm_scope,
    load_dm_policy,
    validate_dm_policy,
)
from .encryption import (
    DecryptionError,
    EncryptionError,
    EncryptionManager,
    get_encryption_manager,
    is_encryption_enabled,
)
from .model_check import check_model_safety
from .rbac import (
    Permission,
    RBACManager,
    Role,
    RoleDefinition,
    User,
    get_rbac_manager,
    require_permission,
    require_role,
)
from .warnings import (
    format_findings_table,
    format_security_warning,
    generate_fix_command,
    get_severity_count,
    warning_to_console,
)
from .policy_dsl import (
    AttributeCondition,
    EvaluationContext,
    IPCondition,
    Policy,
    PolicyConditions,
    PolicyDecision,
    PolicyEffect,
    TimeCondition,
)
from .policy_engine import (
    PolicyCache,
    PolicyEngine,
    PolicyStore,
)
from .inheritance import (
    InheritanceManager,
    InheritanceNode,
    ResolvedPermissions,
)

__all__ = [
    # audit (security audit)
    "SecurityFinding",
    "audit_security",
    "apply_fixes",
    # audit_log (audit logging)
    "AuditLogger",
    "AuditLogEntry",
    "AuditAction",
    "AuditSeverity",
    "get_audit_logger",
    "audit_log",
    # dm_policy
    "DMPolicyConfig",
    "load_dm_policy",
    "validate_dm_policy",
    "get_recommended_dm_scope",
    # encryption
    "EncryptionManager",
    "EncryptionError",
    "DecryptionError",
    "get_encryption_manager",
    "is_encryption_enabled",
    # model_check
    "check_model_safety",
    # rbac
    "RBACManager",
    "User",
    "Role",
    "RoleDefinition",
    "Permission",
    "get_rbac_manager",
    "require_permission",
    "require_role",
    # warnings
    "format_security_warning",
    "generate_fix_command",
    "warning_to_console",
    "format_findings_table",
    "get_severity_count",
    # policy_dsl
    "Policy",
    "PolicyEffect",
    "PolicyConditions",
    "TimeCondition",
    "IPCondition",
    "AttributeCondition",
    "EvaluationContext",
    "PolicyDecision",
    # policy_engine
    "PolicyEngine",
    "PolicyStore",
    "PolicyCache",
    # inheritance
    "InheritanceManager",
    "InheritanceNode",
    "ResolvedPermissions",
]
