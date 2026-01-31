"""插件权限系统测试"""

import pytest

from lurkbot.plugins.permissions import (
    AuditAction,
    Permission,
    PermissionLevel,
    PermissionManager,
    PermissionSet,
    PermissionType,
    get_permission_manager,
    reset_permission_manager,
)


@pytest.fixture
def manager():
    """创建权限管理器实例"""
    reset_permission_manager()
    return PermissionManager()


@pytest.fixture(autouse=True)
def cleanup():
    """测试后清理"""
    yield
    reset_permission_manager()


# ============================================================================
# Permission 模型测试
# ============================================================================


def test_permission_matches_same_type():
    """测试相同类型的权限匹配"""
    perm1 = Permission(type=PermissionType.FILESYSTEM_READ, level=PermissionLevel.READ)
    perm2 = Permission(type=PermissionType.FILESYSTEM_READ, level=PermissionLevel.READ)

    assert perm1.matches(perm2)


def test_permission_matches_different_type():
    """测试不同类型的权限不匹配"""
    perm1 = Permission(type=PermissionType.FILESYSTEM_READ)
    perm2 = Permission(type=PermissionType.FILESYSTEM_WRITE)

    assert not perm1.matches(perm2)


def test_permission_matches_with_resource():
    """测试带资源的权限匹配"""
    perm1 = Permission(
        type=PermissionType.FILESYSTEM_READ, resource="/data/test.txt"
    )
    perm2 = Permission(
        type=PermissionType.FILESYSTEM_READ, resource="/data/test.txt"
    )

    assert perm1.matches(perm2)


def test_permission_matches_with_wildcard():
    """测试通配符权限匹配"""
    perm1 = Permission(type=PermissionType.FILESYSTEM_READ, resource="/data/*")
    perm2 = Permission(
        type=PermissionType.FILESYSTEM_READ, resource="/data/test.txt"
    )

    assert perm1.matches(perm2)


def test_permission_matches_level():
    """测试权限级别匹配"""
    # WRITE 级别可以匹配 READ 级别
    perm1 = Permission(
        type=PermissionType.FILESYSTEM_READ, level=PermissionLevel.WRITE
    )
    perm2 = Permission(
        type=PermissionType.FILESYSTEM_READ, level=PermissionLevel.READ
    )

    assert perm1.matches(perm2)

    # READ 级别不能匹配 WRITE 级别
    perm3 = Permission(
        type=PermissionType.FILESYSTEM_READ, level=PermissionLevel.READ
    )
    perm4 = Permission(
        type=PermissionType.FILESYSTEM_READ, level=PermissionLevel.WRITE
    )

    assert not perm3.matches(perm4)


# ============================================================================
# PermissionSet 测试
# ============================================================================


def test_permission_set_has_permission():
    """测试权限集合检查"""
    perm_set = PermissionSet(plugin_name="test-plugin")
    perm = Permission(type=PermissionType.FILESYSTEM_READ)

    assert not perm_set.has_permission(perm)

    perm_set.add_permission(perm)
    assert perm_set.has_permission(perm)


def test_permission_set_add_permission():
    """测试添加权限"""
    perm_set = PermissionSet(plugin_name="test-plugin")
    perm = Permission(type=PermissionType.FILESYSTEM_READ)

    perm_set.add_permission(perm)
    assert len(perm_set.permissions) == 1

    # 重复添加不会增加
    perm_set.add_permission(perm)
    assert len(perm_set.permissions) == 1


def test_permission_set_remove_permission():
    """测试移除权限"""
    perm_set = PermissionSet(plugin_name="test-plugin")
    perm = Permission(type=PermissionType.FILESYSTEM_READ)

    perm_set.add_permission(perm)
    assert perm_set.remove_permission(perm)
    assert len(perm_set.permissions) == 0

    # 移除不存在的权限返回 False
    assert not perm_set.remove_permission(perm)


# ============================================================================
# PermissionManager 基础测试
# ============================================================================


@pytest.mark.asyncio
async def test_grant_permission(manager):
    """测试授予权限"""
    perm = Permission(type=PermissionType.FILESYSTEM_READ)

    success = await manager.grant_permission("test-plugin", perm)
    assert success

    perms = await manager.get_permissions("test-plugin")
    assert len(perms) == 1
    assert perms[0].type == PermissionType.FILESYSTEM_READ


@pytest.mark.asyncio
async def test_revoke_permission(manager):
    """测试撤销权限"""
    perm = Permission(type=PermissionType.FILESYSTEM_READ)

    await manager.grant_permission("test-plugin", perm)
    success = await manager.revoke_permission("test-plugin", perm)

    assert success

    perms = await manager.get_permissions("test-plugin")
    assert len(perms) == 0


@pytest.mark.asyncio
async def test_revoke_nonexistent_permission(manager):
    """测试撤销不存在的权限"""
    perm = Permission(type=PermissionType.FILESYSTEM_READ)

    success = await manager.revoke_permission("test-plugin", perm)
    assert not success


@pytest.mark.asyncio
async def test_check_permission_granted(manager):
    """测试检查已授予的权限"""
    perm = Permission(type=PermissionType.FILESYSTEM_READ)

    await manager.grant_permission("test-plugin", perm)
    has_perm = await manager.check_permission("test-plugin", perm)

    assert has_perm


@pytest.mark.asyncio
async def test_check_permission_not_granted(manager):
    """测试检查未授予的权限"""
    perm = Permission(type=PermissionType.FILESYSTEM_READ)

    has_perm = await manager.check_permission("test-plugin", perm)
    assert not has_perm


@pytest.mark.asyncio
async def test_get_permissions(manager):
    """测试获取插件权限"""
    perm1 = Permission(type=PermissionType.FILESYSTEM_READ)
    perm2 = Permission(type=PermissionType.NETWORK_HTTP)

    await manager.grant_permission("test-plugin", perm1)
    await manager.grant_permission("test-plugin", perm2)

    perms = await manager.get_permissions("test-plugin")
    assert len(perms) == 2


@pytest.mark.asyncio
async def test_revoke_all_permissions(manager):
    """测试撤销所有权限"""
    perm1 = Permission(type=PermissionType.FILESYSTEM_READ)
    perm2 = Permission(type=PermissionType.NETWORK_HTTP)

    await manager.grant_permission("test-plugin", perm1)
    await manager.grant_permission("test-plugin", perm2)

    success = await manager.revoke_all_permissions("test-plugin")
    assert success

    perms = await manager.get_permissions("test-plugin")
    assert len(perms) == 0


# ============================================================================
# 审计日志测试
# ============================================================================


@pytest.mark.asyncio
async def test_audit_log_grant(manager):
    """测试授予权限的审计日志"""
    perm = Permission(type=PermissionType.FILESYSTEM_READ)

    await manager.grant_permission("test-plugin", perm)

    logs = await manager.get_audit_logs(plugin_name="test-plugin")
    assert len(logs) > 0
    assert logs[0].action == AuditAction.GRANT
    assert logs[0].success


@pytest.mark.asyncio
async def test_audit_log_revoke(manager):
    """测试撤销权限的审计日志"""
    perm = Permission(type=PermissionType.FILESYSTEM_READ)

    await manager.grant_permission("test-plugin", perm)
    await manager.revoke_permission("test-plugin", perm)

    logs = await manager.get_audit_logs(plugin_name="test-plugin")
    revoke_logs = [log for log in logs if log.action == AuditAction.REVOKE]
    assert len(revoke_logs) > 0


@pytest.mark.asyncio
async def test_audit_log_check_allow(manager):
    """测试允许访问的审计日志"""
    perm = Permission(type=PermissionType.FILESYSTEM_READ)

    await manager.grant_permission("test-plugin", perm)
    await manager.check_permission("test-plugin", perm)

    logs = await manager.get_audit_logs(plugin_name="test-plugin")
    allow_logs = [log for log in logs if log.action == AuditAction.ALLOW]
    assert len(allow_logs) > 0


@pytest.mark.asyncio
async def test_audit_log_check_deny(manager):
    """测试拒绝访问的审计日志"""
    perm = Permission(type=PermissionType.FILESYSTEM_READ)

    await manager.check_permission("test-plugin", perm)

    logs = await manager.get_audit_logs(plugin_name="test-plugin")
    deny_logs = [log for log in logs if log.action == AuditAction.DENY]
    assert len(deny_logs) > 0
    assert not deny_logs[0].success


@pytest.mark.asyncio
async def test_get_audit_logs_filter_by_action(manager):
    """测试按动作过滤审计日志"""
    perm = Permission(type=PermissionType.FILESYSTEM_READ)

    await manager.grant_permission("test-plugin", perm)
    await manager.check_permission("test-plugin", perm)

    grant_logs = await manager.get_audit_logs(action=AuditAction.GRANT)
    assert all(log.action == AuditAction.GRANT for log in grant_logs)


@pytest.mark.asyncio
async def test_get_audit_logs_limit(manager):
    """测试审计日志数量限制"""
    perm = Permission(type=PermissionType.FILESYSTEM_READ)

    # 生成多条日志
    for i in range(10):
        await manager.grant_permission(f"plugin-{i}", perm)

    logs = await manager.get_audit_logs(limit=5)
    assert len(logs) == 5


@pytest.mark.asyncio
async def test_clear_audit_logs(manager):
    """测试清空审计日志"""
    perm = Permission(type=PermissionType.FILESYSTEM_READ)

    await manager.grant_permission("test-plugin", perm)

    count = await manager.clear_audit_logs()
    assert count > 0

    logs = await manager.get_audit_logs()
    assert len(logs) == 0


# ============================================================================
# 统计信息测试
# ============================================================================


@pytest.mark.asyncio
async def test_get_stats(manager):
    """测试获取统计信息"""
    perm1 = Permission(type=PermissionType.FILESYSTEM_READ)
    perm2 = Permission(type=PermissionType.NETWORK_HTTP)

    await manager.grant_permission("plugin-1", perm1)
    await manager.grant_permission("plugin-2", perm2)

    stats = manager.get_stats()

    assert stats["total_plugins"] == 2
    assert stats["total_permissions"] == 2
    assert stats["total_audit_logs"] > 0


# ============================================================================
# 并发测试
# ============================================================================


@pytest.mark.asyncio
async def test_concurrent_grant_permission(manager):
    """测试并发授予权限"""
    import asyncio

    perm = Permission(type=PermissionType.FILESYSTEM_READ)

    # 并发授予权限
    tasks = [
        manager.grant_permission(f"plugin-{i}", perm) for i in range(10)
    ]
    results = await asyncio.gather(*tasks)

    assert all(results)
    assert len(manager._permission_sets) == 10


@pytest.mark.asyncio
async def test_concurrent_check_permission(manager):
    """测试并发检查权限"""
    import asyncio

    perm = Permission(type=PermissionType.FILESYSTEM_READ)
    await manager.grant_permission("test-plugin", perm)

    # 并发检查权限
    tasks = [manager.check_permission("test-plugin", perm) for _ in range(10)]
    results = await asyncio.gather(*tasks)

    assert all(results)


# ============================================================================
# 全局单例测试
# ============================================================================


def test_get_permission_manager_singleton():
    """测试全局单例"""
    reset_permission_manager()

    mgr1 = get_permission_manager()
    mgr2 = get_permission_manager()

    assert mgr1 is mgr2


def test_reset_permission_manager():
    """测试重置全局单例"""
    mgr1 = get_permission_manager()

    reset_permission_manager()

    mgr2 = get_permission_manager()
    assert mgr1 is not mgr2
