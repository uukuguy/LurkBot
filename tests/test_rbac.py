"""Tests for RBAC system."""

import pytest

from lurkbot.security.rbac import (
    Permission,
    RBACManager,
    Role,
    User,
    get_rbac_manager,
    require_permission,
    require_role,
)


class TestUser:
    """Test User model."""

    def test_create_user(self):
        """Test creating a user."""
        user = User(user_id="user1", role=Role.USER)
        assert user.user_id == "user1"
        assert user.role == Role.USER
        assert user.custom_permissions == []
        assert user.denied_permissions == []

    def test_get_permissions_from_role(self):
        """Test getting permissions from role."""
        user = User(user_id="user1", role=Role.USER)
        permissions = user.get_permissions()

        assert Permission.TOOL_EXECUTE in permissions
        assert Permission.SESSION_CREATE in permissions
        assert Permission.ADMIN_USERS not in permissions  # Admin only

    def test_get_permissions_admin(self):
        """Test admin has all permissions."""
        user = User(user_id="admin1", role=Role.ADMIN)
        permissions = user.get_permissions()

        # Admin should have all permissions
        assert len(permissions) >= 10
        assert Permission.ADMIN_USERS in permissions
        assert Permission.SECURITY_KEY_ROTATE in permissions

    def test_get_permissions_readonly(self):
        """Test readonly has limited permissions."""
        user = User(user_id="readonly1", role=Role.READONLY)
        permissions = user.get_permissions()

        assert Permission.SESSION_READ in permissions
        assert Permission.CONFIG_READ in permissions
        assert Permission.SESSION_UPDATE not in permissions
        assert Permission.TOOL_EXECUTE not in permissions

    def test_custom_permissions(self):
        """Test custom permissions."""
        user = User(
            user_id="user1",
            role=Role.READONLY,
            custom_permissions=[Permission.TOOL_EXECUTE],
        )

        permissions = user.get_permissions()
        assert Permission.SESSION_READ in permissions  # From role
        assert Permission.TOOL_EXECUTE in permissions  # Custom

    def test_denied_permissions(self):
        """Test denied permissions."""
        user = User(
            user_id="user1",
            role=Role.USER,
            denied_permissions=[Permission.SESSION_DELETE],
        )

        permissions = user.get_permissions()
        assert Permission.SESSION_CREATE in permissions
        assert Permission.SESSION_DELETE not in permissions  # Denied

    def test_has_permission(self):
        """Test checking individual permission."""
        user = User(user_id="user1", role=Role.USER)

        assert user.has_permission(Permission.TOOL_EXECUTE) is True
        assert user.has_permission(Permission.ADMIN_USERS) is False


class TestRBACManager:
    """Test RBAC manager."""

    def test_create_manager(self):
        """Test creating RBAC manager."""
        manager = RBACManager()
        assert manager is not None
        assert len(manager.users) == 0

    def test_add_user(self):
        """Test adding a user."""
        manager = RBACManager()
        user = User(user_id="user1", role=Role.USER)

        manager.add_user(user)
        assert "user1" in manager.users

    def test_get_user(self):
        """Test getting a user."""
        manager = RBACManager()
        user = User(user_id="user1", role=Role.USER)
        manager.add_user(user)

        retrieved = manager.get_user("user1")
        assert retrieved is not None
        assert retrieved.user_id == "user1"

    def test_get_user_not_found(self):
        """Test getting non-existent user."""
        manager = RBACManager()
        assert manager.get_user("nonexistent") is None

    def test_remove_user(self):
        """Test removing a user."""
        manager = RBACManager()
        user = User(user_id="user1", role=Role.USER)
        manager.add_user(user)

        removed = manager.remove_user("user1")
        assert removed is True
        assert manager.get_user("user1") is None

    def test_remove_user_not_found(self):
        """Test removing non-existent user."""
        manager = RBACManager()
        removed = manager.remove_user("nonexistent")
        assert removed is False

    def test_check_permission_allowed(self):
        """Test checking allowed permission."""
        manager = RBACManager()
        user = User(user_id="user1", role=Role.USER)
        manager.add_user(user)

        has_perm = manager.check_permission("user1", Permission.TOOL_EXECUTE)
        assert has_perm is True

    def test_check_permission_denied(self):
        """Test checking denied permission."""
        manager = RBACManager()
        user = User(user_id="user1", role=Role.READONLY)
        manager.add_user(user)

        has_perm = manager.check_permission("user1", Permission.TOOL_EXECUTE)
        assert has_perm is False

    def test_check_permission_unknown_user(self):
        """Test checking permission for unknown user."""
        manager = RBACManager()
        has_perm = manager.check_permission("unknown", Permission.TOOL_EXECUTE)
        assert has_perm is False

    def test_grant_permission(self):
        """Test granting a permission."""
        manager = RBACManager()
        user = User(user_id="user1", role=Role.READONLY)
        manager.add_user(user)

        # Initially denied
        assert not manager.check_permission("user1", Permission.TOOL_EXECUTE)

        # Grant permission
        granted = manager.grant_permission("user1", Permission.TOOL_EXECUTE)
        assert granted is True

        # Now allowed
        assert manager.check_permission("user1", Permission.TOOL_EXECUTE)

    def test_revoke_permission(self):
        """Test revoking a permission."""
        manager = RBACManager()
        user = User(user_id="user1", role=Role.USER)
        manager.add_user(user)

        # Initially allowed
        assert manager.check_permission("user1", Permission.SESSION_DELETE)

        # Revoke permission
        revoked = manager.revoke_permission("user1", Permission.SESSION_DELETE)
        assert revoked is True

        # Now denied
        assert not manager.check_permission("user1", Permission.SESSION_DELETE)

    def test_list_users(self):
        """Test listing all users."""
        manager = RBACManager()
        user1 = User(user_id="user1", role=Role.USER)
        user2 = User(user_id="user2", role=Role.ADMIN)
        manager.add_user(user1)
        manager.add_user(user2)

        users = manager.list_users()
        assert len(users) == 2

    def test_list_users_by_role(self):
        """Test listing users filtered by role."""
        manager = RBACManager()
        user1 = User(user_id="user1", role=Role.USER)
        user2 = User(user_id="user2", role=Role.ADMIN)
        user3 = User(user_id="user3", role=Role.USER)
        manager.add_user(user1)
        manager.add_user(user2)
        manager.add_user(user3)

        users = manager.list_users(role=Role.USER)
        assert len(users) == 2

        admins = manager.list_users(role=Role.ADMIN)
        assert len(admins) == 1


class TestDecorators:
    """Test permission decorators."""

    def test_require_permission_allowed(self):
        """Test require_permission decorator allows access."""
        manager = get_rbac_manager()
        user = User(user_id="user1", role=Role.USER)
        manager.add_user(user)

        @require_permission(Permission.TOOL_EXECUTE)
        def test_func(user_id: str):
            return "success"

        result = test_func(user_id="user1")
        assert result == "success"

    def test_require_permission_denied(self):
        """Test require_permission decorator denies access."""
        manager = get_rbac_manager()
        user = User(user_id="user1", role=Role.READONLY)
        manager.add_user(user)

        @require_permission(Permission.TOOL_EXECUTE)
        def test_func(user_id: str):
            return "success"

        with pytest.raises(PermissionError, match="does not have permission"):
            test_func(user_id="user1")

    def test_require_permission_no_user_id(self):
        """Test require_permission raises error without user_id."""

        @require_permission(Permission.TOOL_EXECUTE)
        def test_func():
            return "success"

        with pytest.raises(PermissionError, match="No user_id provided"):
            test_func()

    def test_require_role_allowed(self):
        """Test require_role decorator allows access."""
        manager = get_rbac_manager()
        user = User(user_id="admin1", role=Role.ADMIN)
        manager.add_user(user)

        @require_role(Role.ADMIN)
        def test_func(user_id: str):
            return "admin_success"

        result = test_func(user_id="admin1")
        assert result == "admin_success"

    def test_require_role_denied(self):
        """Test require_role decorator denies access."""
        manager = get_rbac_manager()
        user = User(user_id="user1", role=Role.USER)
        manager.add_user(user)

        @require_role(Role.ADMIN)
        def test_func(user_id: str):
            return "success"

        with pytest.raises(PermissionError, match="does not have role"):
            test_func(user_id="user1")


class TestGlobalRBACManager:
    """Test global RBAC manager."""

    def test_get_rbac_manager(self):
        """Test getting global RBAC manager."""
        manager = get_rbac_manager()
        assert manager is not None
        assert isinstance(manager, RBACManager)

    def test_global_manager_singleton(self):
        """Test global manager is singleton."""
        manager1 = get_rbac_manager()
        manager2 = get_rbac_manager()
        assert manager1 is manager2


class TestRoleDefinitions:
    """Test predefined role definitions."""

    def test_admin_role(self):
        """Test admin role has all permissions."""
        user = User(user_id="admin", role=Role.ADMIN)
        permissions = user.get_permissions()

        # Check some key admin permissions
        assert Permission.ADMIN_USERS in permissions
        assert Permission.ADMIN_GATEWAY in permissions
        assert Permission.SECURITY_KEY_ROTATE in permissions

    def test_user_role(self):
        """Test user role has standard permissions."""
        user = User(user_id="user", role=Role.USER)
        permissions = user.get_permissions()

        assert Permission.TOOL_EXECUTE in permissions
        assert Permission.SESSION_CREATE in permissions
        assert Permission.ADMIN_USERS not in permissions

    def test_readonly_role(self):
        """Test readonly role has read-only permissions."""
        user = User(user_id="readonly", role=Role.READONLY)
        permissions = user.get_permissions()

        assert Permission.SESSION_READ in permissions
        assert Permission.CONFIG_READ in permissions
        assert Permission.SESSION_UPDATE not in permissions
        assert Permission.TOOL_EXECUTE not in permissions

    def test_guest_role(self):
        """Test guest role has minimal permissions."""
        user = User(user_id="guest", role=Role.GUEST)
        permissions = user.get_permissions()

        assert Permission.SESSION_READ in permissions
        assert len(permissions) == 1  # Only session read
