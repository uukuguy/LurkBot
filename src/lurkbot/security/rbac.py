"""Role-Based Access Control (RBAC) system.

This module provides a flexible RBAC system for controlling access to
tools, sessions, and configuration operations.
"""

from __future__ import annotations

from enum import Enum
from functools import wraps
from typing import Any, Callable, TypeVar

from pydantic import BaseModel, Field

from lurkbot.logging import get_logger
from lurkbot.security.audit_log import AuditAction, AuditSeverity, audit_log

logger = get_logger("rbac")

# Type variable for decorated functions
F = TypeVar("F", bound=Callable[..., Any])


class Permission(str, Enum):
    """System permissions."""

    # Tool permissions
    TOOL_EXECUTE = "tool.execute"
    TOOL_EXECUTE_DANGEROUS = "tool.execute.dangerous"

    # Session permissions
    SESSION_CREATE = "session.create"
    SESSION_READ = "session.read"
    SESSION_UPDATE = "session.update"
    SESSION_DELETE = "session.delete"

    # Configuration permissions
    CONFIG_READ = "config.read"
    CONFIG_UPDATE = "config.update"
    SKILLS_INSTALL = "skills.install"
    SKILLS_UNINSTALL = "skills.uninstall"

    # Security permissions
    SECURITY_ENCRYPT = "security.encrypt"
    SECURITY_DECRYPT = "security.decrypt"
    SECURITY_KEY_ROTATE = "security.key_rotate"
    SECURITY_AUDIT_READ = "security.audit.read"

    # Admin permissions
    ADMIN_USERS = "admin.users"
    ADMIN_ROLES = "admin.roles"
    ADMIN_GATEWAY = "admin.gateway"


class Role(str, Enum):
    """Predefined system roles."""

    ADMIN = "admin"
    USER = "user"
    READONLY = "readonly"
    GUEST = "guest"


class RoleDefinition(BaseModel):
    """Role definition with permissions."""

    name: str = Field(description="Role name")
    display_name: str = Field(description="Human-readable role name")
    permissions: list[Permission] = Field(description="List of permissions")
    description: str = Field(default="", description="Role description")


# Predefined role definitions
ROLE_DEFINITIONS: dict[Role, RoleDefinition] = {
    Role.ADMIN: RoleDefinition(
        name="admin",
        display_name="Administrator",
        permissions=[p for p in Permission],  # All permissions
        description="Full system access with all permissions",
    ),
    Role.USER: RoleDefinition(
        name="user",
        display_name="User",
        permissions=[
            Permission.TOOL_EXECUTE,
            Permission.SESSION_CREATE,
            Permission.SESSION_READ,
            Permission.SESSION_UPDATE,
            Permission.SESSION_DELETE,
            Permission.CONFIG_READ,
            Permission.SKILLS_INSTALL,
            Permission.SECURITY_ENCRYPT,
            Permission.SECURITY_DECRYPT,
        ],
        description="Standard user with tool execution and session management",
    ),
    Role.READONLY: RoleDefinition(
        name="readonly",
        display_name="Read-Only",
        permissions=[
            Permission.SESSION_READ,
            Permission.CONFIG_READ,
            Permission.SECURITY_AUDIT_READ,
        ],
        description="Read-only access to sessions and configuration",
    ),
    Role.GUEST: RoleDefinition(
        name="guest",
        display_name="Guest",
        permissions=[
            Permission.SESSION_READ,
        ],
        description="Minimal access for guest users",
    ),
}


class User(BaseModel):
    """User with role and custom permissions."""

    user_id: str = Field(description="Unique user identifier")
    role: Role = Field(description="User's role")
    custom_permissions: list[Permission] = Field(
        default_factory=list, description="Additional permissions"
    )
    denied_permissions: list[Permission] = Field(
        default_factory=list, description="Explicitly denied permissions"
    )
    metadata: dict[str, Any] = Field(default_factory=dict, description="User metadata")

    def get_permissions(self) -> set[Permission]:
        """Get effective permissions for the user.

        Returns:
            Set of permissions (role + custom - denied)
        """
        role_def = ROLE_DEFINITIONS.get(self.role)
        if not role_def:
            logger.warning(f"Unknown role: {self.role}, using guest permissions")
            role_def = ROLE_DEFINITIONS[Role.GUEST]

        # Start with role permissions
        permissions = set(role_def.permissions)

        # Add custom permissions
        permissions.update(self.custom_permissions)

        # Remove denied permissions
        permissions -= set(self.denied_permissions)

        return permissions

    def has_permission(self, permission: Permission) -> bool:
        """Check if user has a specific permission.

        Args:
            permission: Permission to check

        Returns:
            True if user has the permission
        """
        return permission in self.get_permissions()


class RBACManager:
    """Role-Based Access Control manager."""

    def __init__(self):
        """Initialize RBAC manager."""
        self.users: dict[str, User] = {}

    def add_user(self, user: User) -> None:
        """Add or update a user.

        Args:
            user: User to add
        """
        self.users[user.user_id] = user
        logger.info(f"Added user {user.user_id} with role {user.role}")

    def remove_user(self, user_id: str) -> bool:
        """Remove a user.

        Args:
            user_id: User ID to remove

        Returns:
            True if user was removed
        """
        if user_id in self.users:
            del self.users[user_id]
            logger.info(f"Removed user {user_id}")
            return True
        return False

    def get_user(self, user_id: str) -> User | None:
        """Get a user by ID.

        Args:
            user_id: User ID

        Returns:
            User object or None
        """
        return self.users.get(user_id)

    def check_permission(self, user_id: str, permission: Permission) -> bool:
        """Check if a user has a permission.

        Args:
            user_id: User ID
            permission: Permission to check

        Returns:
            True if user has the permission
        """
        user = self.get_user(user_id)
        if not user:
            logger.warning(f"Unknown user: {user_id}, permission denied")
            return False

        has_permission = user.has_permission(permission)

        if not has_permission:
            logger.warning(
                f"Permission denied: {user_id} does not have {permission}"
            )
            # Log to audit
            audit_log(
                action=AuditAction.PERMISSION_DENIED,
                severity=AuditSeverity.WARNING,
                user=user_id,
                metadata={
                    "permission": permission.value,
                    "role": user.role.value,
                },
            )

        return has_permission

    def grant_permission(self, user_id: str, permission: Permission) -> bool:
        """Grant a permission to a user.

        Args:
            user_id: User ID
            permission: Permission to grant

        Returns:
            True if permission was granted
        """
        user = self.get_user(user_id)
        if not user:
            return False

        if permission not in user.custom_permissions:
            user.custom_permissions.append(permission)
            logger.info(f"Granted {permission} to {user_id}")
            return True

        return False

    def revoke_permission(self, user_id: str, permission: Permission) -> bool:
        """Revoke a permission from a user.

        Args:
            user_id: User ID
            permission: Permission to revoke

        Returns:
            True if permission was revoked
        """
        user = self.get_user(user_id)
        if not user:
            return False

        if permission in user.custom_permissions:
            user.custom_permissions.remove(permission)

        if permission not in user.denied_permissions:
            user.denied_permissions.append(permission)
            logger.info(f"Revoked {permission} from {user_id}")
            return True

        return False

    def list_users(self, role: Role | None = None) -> list[User]:
        """List users, optionally filtered by role.

        Args:
            role: Optional role filter

        Returns:
            List of users
        """
        if role:
            return [u for u in self.users.values() if u.role == role]
        return list(self.users.values())


# Global RBAC manager instance
_rbac_manager: RBACManager | None = None


def get_rbac_manager() -> RBACManager:
    """Get or create global RBAC manager.

    Returns:
        RBACManager instance
    """
    global _rbac_manager
    if _rbac_manager is None:
        _rbac_manager = RBACManager()
    return _rbac_manager


def require_permission(permission: Permission) -> Callable[[F], F]:
    """Decorator to require permission for a function.

    Args:
        permission: Required permission

    Returns:
        Decorator function

    Example:
        @require_permission(Permission.TOOL_EXECUTE)
        def execute_tool(user_id: str, tool_name: str):
            ...
    """

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Extract user_id from kwargs or first arg
            user_id = kwargs.get("user_id") or (args[0] if args else None)

            if not user_id:
                raise PermissionError("No user_id provided for permission check")

            rbac = get_rbac_manager()
            if not rbac.check_permission(user_id, permission):
                raise PermissionError(
                    f"User {user_id} does not have permission: {permission}"
                )

            return func(*args, **kwargs)

        return wrapper  # type: ignore

    return decorator


def require_role(role: Role) -> Callable[[F], F]:
    """Decorator to require a specific role.

    Args:
        role: Required role

    Returns:
        Decorator function

    Example:
        @require_role(Role.ADMIN)
        def admin_function(user_id: str):
            ...
    """

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Extract user_id
            user_id = kwargs.get("user_id") or (args[0] if args else None)

            if not user_id:
                raise PermissionError("No user_id provided for role check")

            rbac = get_rbac_manager()
            user = rbac.get_user(user_id)

            if not user or user.role != role:
                raise PermissionError(f"User {user_id} does not have role: {role}")

            return func(*args, **kwargs)

        return wrapper  # type: ignore

    return decorator
