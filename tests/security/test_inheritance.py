"""权限继承测试"""

import pytest

from lurkbot.security.inheritance import (
    InheritanceManager,
    InheritanceNode,
    ResolvedPermissions,
)


# ============================================================================
# InheritanceNode 测试
# ============================================================================


class TestInheritanceNode:
    """继承节点测试"""

    def test_create_node(self):
        """测试创建节点"""
        node = InheritanceNode(
            id="user:alice",
            node_type="user",
            display_name="Alice",
        )
        assert node.id == "user:alice"
        assert node.node_type == "user"
        assert len(node.granted_permissions) == 0

    def test_with_permissions(self):
        """测试带权限的节点"""
        node = InheritanceNode(
            id="role:admin",
            node_type="role",
            granted_permissions={"perm1", "perm2"},
            denied_permissions={"perm3"},
        )
        assert "perm1" in node.granted_permissions
        assert "perm3" in node.denied_permissions


# ============================================================================
# ResolvedPermissions 测试
# ============================================================================


class TestResolvedPermissions:
    """解析权限测试"""

    def test_has_permission(self):
        """测试权限检查"""
        resolved = ResolvedPermissions(
            principal_id="user:alice",
            granted={"read", "write"},
            denied={"delete"},
        )
        assert resolved.has_permission("read") is True
        assert resolved.has_permission("delete") is False
        assert resolved.has_permission("nonexistent") is False

    def test_denied_overrides_granted(self):
        """测试拒绝优先"""
        resolved = ResolvedPermissions(
            principal_id="user:alice",
            granted={"read", "write", "delete"},
            denied={"delete"},
        )
        # delete 被拒绝，即使在 granted 中也不行
        assert resolved.has_permission("delete") is False


# ============================================================================
# InheritanceManager 测试
# ============================================================================


class TestInheritanceManager:
    """继承管理器测试"""

    # ------------------------------------------------------------------------
    # 节点管理测试
    # ------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_add_and_get_node(self):
        """测试添加和获取节点"""
        manager = InheritanceManager()
        node = InheritanceNode(
            id="user:alice",
            node_type="user",
        )
        await manager.add_node(node)

        result = await manager.get_node("user:alice")
        assert result is not None
        assert result.id == "user:alice"

    @pytest.mark.asyncio
    async def test_remove_node(self):
        """测试移除节点"""
        manager = InheritanceManager()
        node = InheritanceNode(id="user:alice", node_type="user")
        await manager.add_node(node)

        result = await manager.remove_node("user:alice")
        assert result is True
        assert await manager.get_node("user:alice") is None

    @pytest.mark.asyncio
    async def test_remove_nonexistent(self):
        """测试移除不存在的节点"""
        manager = InheritanceManager()
        result = await manager.remove_node("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_set_parents(self):
        """测试设置父节点"""
        manager = InheritanceManager()
        await manager.add_node(InheritanceNode(id="user:alice", node_type="user"))
        await manager.add_node(InheritanceNode(id="role:user", node_type="role"))

        result = await manager.set_parents("user:alice", ["role:user"])
        assert result is True

        node = await manager.get_node("user:alice")
        assert "role:user" in node.parent_ids

    @pytest.mark.asyncio
    async def test_cycle_detection(self):
        """测试循环检测"""
        manager = InheritanceManager()
        await manager.add_node(InheritanceNode(id="role:a", node_type="role"))
        await manager.add_node(InheritanceNode(id="role:b", node_type="role"))

        await manager.set_parents("role:a", ["role:b"])

        # 尝试创建循环
        with pytest.raises(ValueError, match="循环"):
            await manager.set_parents("role:b", ["role:a"])

    @pytest.mark.asyncio
    async def test_self_reference_cycle(self):
        """测试自引用循环"""
        manager = InheritanceManager()
        await manager.add_node(InheritanceNode(id="role:a", node_type="role"))

        with pytest.raises(ValueError, match="循环"):
            await manager.set_parents("role:a", ["role:a"])

    # ------------------------------------------------------------------------
    # 权限管理测试
    # ------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_grant_permission(self):
        """测试授予权限"""
        manager = InheritanceManager()
        await manager.add_node(InheritanceNode(id="user:alice", node_type="user"))

        result = await manager.grant_permission("user:alice", "perm1")
        assert result is True

        node = await manager.get_node("user:alice")
        assert "perm1" in node.granted_permissions

    @pytest.mark.asyncio
    async def test_deny_permission(self):
        """测试拒绝权限"""
        manager = InheritanceManager()
        await manager.add_node(InheritanceNode(id="user:alice", node_type="user"))

        result = await manager.deny_permission("user:alice", "perm1")
        assert result is True

        node = await manager.get_node("user:alice")
        assert "perm1" in node.denied_permissions

    @pytest.mark.asyncio
    async def test_revoke_permission(self):
        """测试撤销权限"""
        manager = InheritanceManager()
        await manager.add_node(InheritanceNode(id="user:alice", node_type="user"))
        await manager.grant_permission("user:alice", "perm1")
        await manager.deny_permission("user:alice", "perm2")

        await manager.revoke_permission("user:alice", "perm1")
        await manager.revoke_permission("user:alice", "perm2")

        node = await manager.get_node("user:alice")
        assert "perm1" not in node.granted_permissions
        assert "perm2" not in node.denied_permissions

    # ------------------------------------------------------------------------
    # 权限解析测试
    # ------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_resolve_direct_permissions(self):
        """测试解析直接权限"""
        manager = InheritanceManager()
        await manager.add_node(InheritanceNode(
            id="user:alice",
            node_type="user",
            granted_permissions={"read", "write"},
        ))

        resolved = await manager.resolve_permissions("user:alice")
        assert "read" in resolved.granted
        assert "write" in resolved.granted

    @pytest.mark.asyncio
    async def test_resolve_inherited_permissions(self):
        """测试解析继承权限"""
        manager = InheritanceManager()

        # 创建层次结构: user:alice -> role:developer -> role:user
        await manager.add_node(InheritanceNode(
            id="role:user",
            node_type="role",
            granted_permissions={"read"},
        ))
        await manager.add_node(InheritanceNode(
            id="role:developer",
            node_type="role",
            parent_ids=["role:user"],
            granted_permissions={"write"},
        ))
        await manager.add_node(InheritanceNode(
            id="user:alice",
            node_type="user",
            parent_ids=["role:developer"],
            granted_permissions={"delete"},
        ))

        resolved = await manager.resolve_permissions("user:alice")

        # 应该包含所有层级的权限
        assert "read" in resolved.granted  # from role:user
        assert "write" in resolved.granted  # from role:developer
        assert "delete" in resolved.granted  # from user:alice

    @pytest.mark.asyncio
    async def test_denied_overrides_inherited(self):
        """测试拒绝权限覆盖继承"""
        manager = InheritanceManager()

        await manager.add_node(InheritanceNode(
            id="role:user",
            node_type="role",
            granted_permissions={"read", "write", "delete"},
        ))
        await manager.add_node(InheritanceNode(
            id="user:alice",
            node_type="user",
            parent_ids=["role:user"],
            denied_permissions={"delete"},  # 拒绝删除权限
        ))

        resolved = await manager.resolve_permissions("user:alice")

        assert "read" in resolved.granted
        assert "write" in resolved.granted
        assert "delete" not in resolved.granted  # 被拒绝
        assert "delete" in resolved.denied

    @pytest.mark.asyncio
    async def test_has_permission(self):
        """测试权限检查"""
        manager = InheritanceManager()

        await manager.add_node(InheritanceNode(
            id="role:user",
            node_type="role",
            granted_permissions={"read"},
        ))
        await manager.add_node(InheritanceNode(
            id="user:alice",
            node_type="user",
            parent_ids=["role:user"],
        ))

        assert await manager.has_permission("user:alice", "read") is True
        assert await manager.has_permission("user:alice", "write") is False

    # ------------------------------------------------------------------------
    # 查询测试
    # ------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_get_children(self):
        """测试获取子节点"""
        manager = InheritanceManager()

        await manager.add_node(InheritanceNode(id="role:user", node_type="role"))
        await manager.add_node(InheritanceNode(
            id="user:alice",
            node_type="user",
            parent_ids=["role:user"],
        ))
        await manager.add_node(InheritanceNode(
            id="user:bob",
            node_type="user",
            parent_ids=["role:user"],
        ))

        children = await manager.get_children("role:user")
        assert len(children) == 2
        assert "user:alice" in children
        assert "user:bob" in children

    @pytest.mark.asyncio
    async def test_get_ancestors(self):
        """测试获取祖先节点"""
        manager = InheritanceManager()

        await manager.add_node(InheritanceNode(
            id="role:admin",
            node_type="role",
        ))
        await manager.add_node(InheritanceNode(
            id="role:user",
            node_type="role",
            parent_ids=["role:admin"],
        ))
        await manager.add_node(InheritanceNode(
            id="user:alice",
            node_type="user",
            parent_ids=["role:user"],
        ))

        ancestors = await manager.get_ancestors("user:alice")
        assert "role:user" in ancestors
        assert "role:admin" in ancestors

    @pytest.mark.asyncio
    async def test_get_hierarchy(self):
        """测试获取层次结构"""
        manager = InheritanceManager()

        await manager.add_node(InheritanceNode(id="role:admin", node_type="role"))
        await manager.add_node(InheritanceNode(
            id="role:user",
            node_type="role",
            parent_ids=["role:admin"],
        ))

        hierarchy = await manager.get_hierarchy()
        assert "roots" in hierarchy
        assert hierarchy["total_nodes"] == 2

    # ------------------------------------------------------------------------
    # 复杂场景测试
    # ------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_multiple_parents(self):
        """测试多父节点继承"""
        manager = InheritanceManager()

        await manager.add_node(InheritanceNode(
            id="role:developer",
            node_type="role",
            granted_permissions={"write_code"},
        ))
        await manager.add_node(InheritanceNode(
            id="group:team-a",
            node_type="group",
            granted_permissions={"read_team_data"},
        ))
        await manager.add_node(InheritanceNode(
            id="user:alice",
            node_type="user",
            parent_ids=["role:developer", "group:team-a"],
            granted_permissions={"my_permission"},
        ))

        resolved = await manager.resolve_permissions("user:alice")

        # 应该包含所有父节点和自身的权限
        assert "write_code" in resolved.granted
        assert "read_team_data" in resolved.granted
        assert "my_permission" in resolved.granted

    @pytest.mark.asyncio
    async def test_tenant_group_user_hierarchy(self):
        """测试租户→组→用户层次"""
        manager = InheritanceManager()

        # 租户级别
        await manager.add_node(InheritanceNode(
            id="tenant:company-a",
            node_type="tenant",
            granted_permissions={"access_company_data"},
        ))

        # 组级别
        await manager.add_node(InheritanceNode(
            id="group:engineering",
            node_type="group",
            parent_ids=["tenant:company-a"],
            granted_permissions={"deploy_code"},
        ))

        # 用户级别
        await manager.add_node(InheritanceNode(
            id="user:alice",
            node_type="user",
            parent_ids=["group:engineering"],
            granted_permissions={"edit_profile"},
        ))

        resolved = await manager.resolve_permissions("user:alice")

        assert "access_company_data" in resolved.granted  # 从租户继承
        assert "deploy_code" in resolved.granted  # 从组继承
        assert "edit_profile" in resolved.granted  # 自身权限

        # 检查继承链
        assert len(resolved.inheritance_chain) == 3

    @pytest.mark.asyncio
    async def test_diamond_inheritance(self):
        """测试菱形继承"""
        manager = InheritanceManager()

        # 菱形结构:
        #       A
        #      / \
        #     B   C
        #      \ /
        #       D

        await manager.add_node(InheritanceNode(
            id="role:a",
            node_type="role",
            granted_permissions={"perm_a"},
        ))
        await manager.add_node(InheritanceNode(
            id="role:b",
            node_type="role",
            parent_ids=["role:a"],
            granted_permissions={"perm_b"},
        ))
        await manager.add_node(InheritanceNode(
            id="role:c",
            node_type="role",
            parent_ids=["role:a"],
            granted_permissions={"perm_c"},
        ))
        await manager.add_node(InheritanceNode(
            id="role:d",
            node_type="role",
            parent_ids=["role:b", "role:c"],
            granted_permissions={"perm_d"},
        ))

        resolved = await manager.resolve_permissions("role:d")

        # 应该包含所有权限（perm_a 只出现一次）
        assert "perm_a" in resolved.granted
        assert "perm_b" in resolved.granted
        assert "perm_c" in resolved.granted
        assert "perm_d" in resolved.granted
