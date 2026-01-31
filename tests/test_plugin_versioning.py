"""插件版本管理系统测试"""

import pytest

from lurkbot.plugins.versioning import (
    SemanticVersion,
    VersionManager,
    VersionStatus,
    get_version_manager,
    reset_version_manager,
)


@pytest.fixture
def manager():
    """创建版本管理器实例"""
    reset_version_manager()
    return VersionManager()


@pytest.fixture(autouse=True)
def cleanup():
    """测试后清理"""
    yield
    reset_version_manager()


# ============================================================================
# SemanticVersion 测试
# ============================================================================


def test_semantic_version_parse_simple():
    """测试解析简单版本"""
    version = SemanticVersion.parse("1.2.3")

    assert version.major == 1
    assert version.minor == 2
    assert version.patch == 3
    assert version.prerelease is None
    assert version.build is None


def test_semantic_version_parse_with_prerelease():
    """测试解析带预发布版本"""
    version = SemanticVersion.parse("1.2.3-alpha.1")

    assert version.major == 1
    assert version.minor == 2
    assert version.patch == 3
    assert version.prerelease == "alpha.1"
    assert version.build is None


def test_semantic_version_parse_with_build():
    """测试解析带构建版本"""
    version = SemanticVersion.parse("1.2.3+build.123")

    assert version.major == 1
    assert version.minor == 2
    assert version.patch == 3
    assert version.prerelease is None
    assert version.build == "build.123"


def test_semantic_version_parse_full():
    """测试解析完整版本"""
    version = SemanticVersion.parse("1.2.3-alpha.1+build.123")

    assert version.major == 1
    assert version.minor == 2
    assert version.patch == 3
    assert version.prerelease == "alpha.1"
    assert version.build == "build.123"


def test_semantic_version_parse_invalid():
    """测试解析无效版本"""
    with pytest.raises(ValueError):
        SemanticVersion.parse("invalid")

    with pytest.raises(ValueError):
        SemanticVersion.parse("1.2")

    with pytest.raises(ValueError):
        SemanticVersion.parse("1.2.3.4")


def test_semantic_version_str():
    """测试版本字符串转换"""
    version = SemanticVersion(1, 2, 3, "alpha.1", "build.123")
    assert str(version) == "1.2.3-alpha.1+build.123"


def test_semantic_version_comparison():
    """测试版本比较"""
    v1 = SemanticVersion.parse("1.0.0")
    v2 = SemanticVersion.parse("1.0.1")
    v3 = SemanticVersion.parse("1.1.0")
    v4 = SemanticVersion.parse("2.0.0")

    assert v1 < v2
    assert v2 < v3
    assert v3 < v4

    assert v4 > v3
    assert v3 > v2
    assert v2 > v1


def test_semantic_version_comparison_prerelease():
    """测试预发布版本比较"""
    v1 = SemanticVersion.parse("1.0.0-alpha")
    v2 = SemanticVersion.parse("1.0.0-beta")
    v3 = SemanticVersion.parse("1.0.0")

    assert v1 < v2
    assert v2 < v3  # 预发布版本 < 正式版本


def test_semantic_version_equality():
    """测试版本相等"""
    v1 = SemanticVersion.parse("1.2.3")
    v2 = SemanticVersion.parse("1.2.3")
    v3 = SemanticVersion.parse("1.2.4")

    assert v1 == v2
    assert v1 != v3


# ============================================================================
# VersionManager 基础测试
# ============================================================================


def test_register_version(manager):
    """测试注册版本"""
    success = manager.register_version("test-plugin", "1.0.0")

    assert success
    assert "test-plugin" in manager._versions
    assert "1.0.0" in manager._versions["test-plugin"]


def test_register_version_duplicate(manager):
    """测试注册重复版本"""
    manager.register_version("test-plugin", "1.0.0")
    success = manager.register_version("test-plugin", "1.0.0")

    assert not success


def test_register_version_invalid(manager):
    """测试注册无效版本"""
    success = manager.register_version("test-plugin", "invalid")

    assert not success


def test_unregister_version(manager):
    """测试注销版本"""
    manager.register_version("test-plugin", "1.0.0")
    success = manager.unregister_version("test-plugin", "1.0.0")

    assert success
    assert "1.0.0" not in manager._versions.get("test-plugin", {})


def test_unregister_active_version(manager):
    """测试注销活跃版本（应该失败）"""
    manager.register_version("test-plugin", "1.0.0")
    manager.set_active_version("test-plugin", "1.0.0")

    success = manager.unregister_version("test-plugin", "1.0.0")

    assert not success


# ============================================================================
# 活跃版本管理测试
# ============================================================================


def test_set_active_version(manager):
    """测试设置活跃版本"""
    manager.register_version("test-plugin", "1.0.0")
    success = manager.set_active_version("test-plugin", "1.0.0")

    assert success
    assert manager.get_active_version("test-plugin") == "1.0.0"


def test_set_active_version_nonexistent(manager):
    """测试设置不存在的版本"""
    success = manager.set_active_version("test-plugin", "1.0.0")

    assert not success


def test_set_active_version_updates_status(manager):
    """测试设置活跃版本更新状态"""
    manager.register_version("test-plugin", "1.0.0")
    manager.register_version("test-plugin", "2.0.0")

    manager.set_active_version("test-plugin", "1.0.0")

    v1 = manager.get_version_info("test-plugin", "1.0.0")
    v2 = manager.get_version_info("test-plugin", "2.0.0")

    assert v1.status == VersionStatus.ACTIVE
    assert v2.status == VersionStatus.INACTIVE


def test_get_active_version_none(manager):
    """测试获取不存在的活跃版本"""
    version = manager.get_active_version("nonexistent")

    assert version is None


# ============================================================================
# 版本查询测试
# ============================================================================


def test_get_all_versions(manager):
    """测试获取所有版本"""
    manager.register_version("test-plugin", "1.0.0")
    manager.register_version("test-plugin", "2.0.0")
    manager.register_version("test-plugin", "1.5.0")

    versions = manager.get_all_versions("test-plugin")

    # 应该按版本号排序
    assert versions == ["1.0.0", "1.5.0", "2.0.0"]


def test_get_all_versions_empty(manager):
    """测试获取空版本列表"""
    versions = manager.get_all_versions("nonexistent")

    assert versions == []


def test_get_latest_version(manager):
    """测试获取最新版本"""
    manager.register_version("test-plugin", "1.0.0")
    manager.register_version("test-plugin", "2.0.0")
    manager.register_version("test-plugin", "1.5.0")

    latest = manager.get_latest_version("test-plugin")

    assert latest == "2.0.0"


def test_get_latest_version_none(manager):
    """测试获取不存在的最新版本"""
    latest = manager.get_latest_version("nonexistent")

    assert latest is None


def test_get_version_info(manager):
    """测试获取版本信息"""
    manager.register_version("test-plugin", "1.0.0", metadata={"key": "value"})

    info = manager.get_version_info("test-plugin", "1.0.0")

    assert info is not None
    assert info.plugin_name == "test-plugin"
    assert info.version == "1.0.0"
    assert info.metadata["key"] == "value"


# ============================================================================
# 版本升级和回滚测试
# ============================================================================


def test_upgrade_to_latest(manager):
    """测试升级到最新版本"""
    manager.register_version("test-plugin", "1.0.0")
    manager.register_version("test-plugin", "2.0.0")
    manager.set_active_version("test-plugin", "1.0.0")

    success = manager.upgrade_to_latest("test-plugin")

    assert success
    assert manager.get_active_version("test-plugin") == "2.0.0"


def test_upgrade_to_latest_no_versions(manager):
    """测试升级不存在的插件"""
    success = manager.upgrade_to_latest("nonexistent")

    assert not success


def test_rollback(manager):
    """测试回滚版本"""
    manager.register_version("test-plugin", "1.0.0")
    manager.register_version("test-plugin", "2.0.0")

    manager.set_active_version("test-plugin", "1.0.0")
    manager.set_active_version("test-plugin", "2.0.0")

    success = manager.rollback("test-plugin")

    assert success
    assert manager.get_active_version("test-plugin") == "1.0.0"


def test_rollback_no_history(manager):
    """测试回滚无历史记录"""
    success = manager.rollback("test-plugin")

    assert not success


def test_rollback_version_deleted(manager):
    """测试回滚���已删除的版本"""
    manager.register_version("test-plugin", "1.0.0")
    manager.register_version("test-plugin", "2.0.0")

    manager.set_active_version("test-plugin", "1.0.0")
    manager.set_active_version("test-plugin", "2.0.0")

    # 删除旧版本
    manager.unregister_version("test-plugin", "1.0.0")

    success = manager.rollback("test-plugin")

    assert not success


# ============================================================================
# 版本历史测试
# ============================================================================


def test_get_history(manager):
    """测试获取版本历史"""
    manager.register_version("test-plugin", "1.0.0")
    manager.register_version("test-plugin", "2.0.0")

    manager.set_active_version("test-plugin", "1.0.0")
    manager.set_active_version("test-plugin", "2.0.0")

    history = manager.get_history("test-plugin")

    assert len(history) > 0
    assert history[0].plugin_name == "test-plugin"


def test_get_history_filter_by_plugin(manager):
    """测试按插件过滤历史"""
    manager.register_version("plugin-1", "1.0.0")
    manager.register_version("plugin-2", "1.0.0")

    manager.set_active_version("plugin-1", "1.0.0")
    manager.set_active_version("plugin-2", "1.0.0")

    history = manager.get_history("plugin-1")

    assert all(h.plugin_name == "plugin-1" for h in history)


def test_get_history_limit(manager):
    """测试历史记录数量限制"""
    manager.register_version("test-plugin", "1.0.0")
    manager.register_version("test-plugin", "2.0.0")
    manager.register_version("test-plugin", "3.0.0")

    manager.set_active_version("test-plugin", "1.0.0")
    manager.set_active_version("test-plugin", "2.0.0")
    manager.set_active_version("test-plugin", "3.0.0")

    history = manager.get_history(limit=1)

    assert len(history) == 1


def test_history_action_upgrade(manager):
    """测试历史记录动作（升级）"""
    manager.register_version("test-plugin", "1.0.0")
    manager.register_version("test-plugin", "2.0.0")

    manager.set_active_version("test-plugin", "1.0.0")
    manager.set_active_version("test-plugin", "2.0.0")

    history = manager.get_history("test-plugin")

    assert history[0].action == "upgrade"


def test_history_action_downgrade(manager):
    """测试历史记录动作（降级）"""
    manager.register_version("test-plugin", "1.0.0")
    manager.register_version("test-plugin", "2.0.0")

    manager.set_active_version("test-plugin", "2.0.0")
    manager.set_active_version("test-plugin", "1.0.0")

    history = manager.get_history("test-plugin")

    assert history[0].action == "downgrade"


# ============================================================================
# 清理测试
# ============================================================================


def test_clear(manager):
    """测试清空管理器"""
    manager.register_version("test-plugin", "1.0.0")
    manager.set_active_version("test-plugin", "1.0.0")

    manager.clear()

    assert len(manager._versions) == 0
    assert len(manager._active_versions) == 0
    assert len(manager._history) == 0


# ============================================================================
# 全局单例测试
# ============================================================================


def test_get_version_manager_singleton():
    """测试全局单例"""
    reset_version_manager()

    mgr1 = get_version_manager()
    mgr2 = get_version_manager()

    assert mgr1 is mgr2


def test_reset_version_manager():
    """测试重置全局单例"""
    mgr1 = get_version_manager()

    reset_version_manager()

    mgr2 = get_version_manager()
    assert mgr1 is not mgr2
