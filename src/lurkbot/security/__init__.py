"""
Security Audit System

对标 MoltBot src/security/
"""

from .audit import SecurityFinding, apply_fixes, audit_security
from .dm_policy import (
    DMPolicyConfig,
    get_recommended_dm_scope,
    load_dm_policy,
    validate_dm_policy,
)
from .model_check import check_model_safety
from .warnings import (
    format_findings_table,
    format_security_warning,
    generate_fix_command,
    get_severity_count,
    warning_to_console,
)

__all__ = [
    # audit
    "SecurityFinding",
    "audit_security",
    "apply_fixes",
    # dm_policy
    "DMPolicyConfig",
    "load_dm_policy",
    "validate_dm_policy",
    "get_recommended_dm_scope",
    # model_check
    "check_model_safety",
    # warnings
    "format_security_warning",
    "generate_fix_command",
    "warning_to_console",
    "format_findings_table",
    "get_severity_count",
]
