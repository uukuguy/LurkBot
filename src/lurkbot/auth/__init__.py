"""
Auth module for credential management and rotation.

对标 MoltBot auth/
"""

from lurkbot.auth.profiles import (
    AuthCredential,
    ProfileUsageStats,
    AuthProfileStore,
    calculate_cooldown_ms,
    resolve_auth_profile_order,
    rotate_auth_profile,
    load_auth_profiles,
    save_auth_profiles,
    is_valid_credential,
    match_provider,
    normalize_provider_id,
)

__all__ = [
    "AuthCredential",
    "ProfileUsageStats",
    "AuthProfileStore",
    "calculate_cooldown_ms",
    "resolve_auth_profile_order",
    "rotate_auth_profile",
    "load_auth_profiles",
    "save_auth_profiles",
    "is_valid_credential",
    "match_provider",
    "normalize_provider_id",
]
