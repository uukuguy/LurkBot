"""测试插件 CLI 工具

测试所有插件管理命令的功能和输出格式。
"""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from lurkbot.cli.plugin_cli import app
from lurkbot.plugins.loader import PluginState
from lurkbot.plugins.manifest import PluginManifest
from lurkbot.plugins.permissions import Permission, PermissionLevel, PermissionType
from lurkbot.plugins.profiling import PerformanceReport

# Test runner
runner = CliRunner()


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_plugin():
    """创建模拟插件实例"""
    from lurkbot.plugins.manifest import PluginAuthor, PluginDependencies, PluginPermissions

    manifest = PluginManifest(
        name="test-plugin",
        version="1.0.0",
        type="tool",
        description="A test plugin",
        entry="main.py",
        author=PluginAuthor(name="Test Author"),
        tags=["test", "example"],
        dependencies=PluginDependencies(python=["dep1", "dep2"]),
        permissions=PluginPermissions(filesystem=True, network=True),
    )

    plugin = MagicMock()
    plugin.manifest = manifest
    plugin.state = PluginState.ENABLED
    return plugin


@pytest.fixture
def mock_manager(mock_plugin):
    """创建模拟插件管理器"""
    manager = MagicMock()
    manager.list_plugins.return_value = [mock_plugin]
    manager.get_plugin.return_value = mock_plugin
    manager.is_loaded.return_value = True
    manager.is_enabled.return_value = True

    # Mock async methods
    manager.enable_plugin = AsyncMock(return_value=True)
    manager.disable_plugin = AsyncMock(return_value=True)
    manager.unload_plugin = AsyncMock(return_value=True)
    manager.grant_permission = AsyncMock(return_value=True)
    manager.revoke_permission = AsyncMock(return_value=True)
    manager.get_permission_audit_log = AsyncMock(return_value=[])
    manager.switch_plugin_version = AsyncMock(return_value=True)
    manager.rollback_plugin_version = AsyncMock(return_value=True)

    # Mock profiler
    manager.profiler = MagicMock()
    manager.get_performance_report.return_value = PerformanceReport(
        plugin_name="test-plugin",
        total_executions=10,
        successful_executions=9,
        failed_executions=1,
        avg_execution_time=0.5,
        min_execution_time=0.1,
        max_execution_time=1.0,
    )
    manager.get_all_performance_reports.return_value = {
        "test-plugin": PerformanceReport(
            plugin_name="test-plugin",
            total_executions=10,
            successful_executions=9,
            failed_executions=1,
            avg_execution_time=0.5,
            min_execution_time=0.1,
            max_execution_time=1.0,
        )
    }
    manager.get_performance_bottlenecks.return_value = [
        {
            "plugin": "test-plugin",
            "avg_time": 0.5,
            "max_time": 1.0,
        }
    ]

    # Mock permission manager
    manager.permission_manager = MagicMock()
    manager.permission_manager.get_plugin_permissions.return_value = [
        Permission(
            type=PermissionType.FILESYSTEM_READ,
            level=PermissionLevel.ADMIN,
        )
    ]

    # Mock version manager
    manager.version_manager = MagicMock()
    manager.get_plugin_versions.return_value = ["1.0.0", "1.1.0", "2.0.0"]
    manager.get_version_history.return_value = [
        {"version": "1.0.0", "timestamp": "2024-01-01T00:00:00"},
        {"version": "1.1.0", "timestamp": "2024-01-02T00:00:00"},
    ]

    # Mock orchestrator
    manager.orchestrator = MagicMock()
    manager.visualize_dependency_graph.return_value = "test-plugin -> dep1\ntest-plugin -> dep2"

    return manager


# ============================================================================
# 测试插件列表和搜索
# ============================================================================


def test_list_plugins_default(mock_manager):
    """测试默认列出所有插件"""
    with patch("lurkbot.cli.plugin_cli.get_manager", return_value=mock_manager):
        result = runner.invoke(app, ["list"])
        assert result.exit_code == 0
        assert "test-plugin" in result.stdout
        assert "1.0.0" in result.stdout


def test_list_plugins_with_status_filter(mock_manager):
    """测试按状态筛选插件"""
    with patch("lurkbot.cli.plugin_cli.get_manager", return_value=mock_manager):
        result = runner.invoke(app, ["list", "--status", "enabled"])
        assert result.exit_code == 0
        assert "test-plugin" in result.stdout


def test_list_plugins_json_output(mock_manager):
    """测试 JSON 格式输出"""
    with patch("lurkbot.cli.plugin_cli.get_manager", return_value=mock_manager):
        result = runner.invoke(app, ["list", "--json"])
        assert result.exit_code == 0

        # Verify JSON output
        output = json.loads(result.stdout)
        assert isinstance(output, list)
        assert len(output) == 1
        assert output[0]["name"] == "test-plugin"


def test_list_plugins_empty(mock_manager):
    """测试空插件列表"""
    mock_manager.list_plugins.return_value = []

    with patch("lurkbot.cli.plugin_cli.get_manager", return_value=mock_manager):
        result = runner.invoke(app, ["list"])
        assert result.exit_code == 0
        assert "No plugins found" in result.stdout


def test_search_plugins_found(mock_manager):
    """测试搜索插件（找到结果）"""
    with patch("lurkbot.cli.plugin_cli.get_manager", return_value=mock_manager):
        result = runner.invoke(app, ["search", "test"])
        assert result.exit_code == 0
        assert "test-plugin" in result.stdout


def test_search_plugins_not_found(mock_manager):
    """测试搜索插件（未找到）"""
    with patch("lurkbot.cli.plugin_cli.get_manager", return_value=mock_manager):
        result = runner.invoke(app, ["search", "nonexistent"])
        assert result.exit_code == 0
        assert "No plugins found" in result.stdout


def test_search_plugins_json(mock_manager):
    """测试搜索插件 JSON 输出"""
    with patch("lurkbot.cli.plugin_cli.get_manager", return_value=mock_manager):
        result = runner.invoke(app, ["search", "test", "--json"])
        assert result.exit_code == 0

        output = json.loads(result.stdout)
        assert isinstance(output, list)
        assert len(output) == 1


def test_plugin_info(mock_manager):
    """测试显示插件详情"""
    with patch("lurkbot.cli.plugin_cli.get_plugin_manager", return_value=mock_manager):
        result = runner.invoke(app, ["info", "test-plugin"])
        assert result.exit_code == 0
        assert "test-plugin" in result.stdout
        assert "1.0.0" in result.stdout
        assert "A test plugin" in result.stdout


def test_plugin_info_not_found(mock_manager):
    """测试显示不存在的插件详情"""
    mock_manager.get_plugin.return_value = None

    with patch("lurkbot.cli.plugin_cli.get_plugin_manager", return_value=mock_manager):
        result = runner.invoke(app, ["info", "nonexistent"])
        assert result.exit_code == 1
        assert "not found" in result.stdout


def test_plugin_info_json(mock_manager):
    """测试插件详情 JSON 输出"""
    with patch("lurkbot.cli.plugin_cli.get_plugin_manager", return_value=mock_manager):
        result = runner.invoke(app, ["info", "test-plugin", "--json"])
        assert result.exit_code == 0

        output = json.loads(result.stdout)
        assert output["name"] == "test-plugin"
        assert output["version"] == "1.0.0"


# ============================================================================
# 测试插件安装和卸载
# ============================================================================


def test_install_plugin(mock_manager):
    """测试安装插件"""
    with patch("lurkbot.cli.plugin_cli.get_manager", return_value=mock_manager):
        result = runner.invoke(app, ["install", "./test-plugin"])
        assert result.exit_code == 0
        # Currently shows "not yet implemented" message
        assert "not yet implemented" in result.stdout.lower()


def test_uninstall_plugin_with_force(mock_manager):
    """测试强制卸载插件"""
    with patch("lurkbot.cli.plugin_cli.get_manager", return_value=mock_manager):
        result = runner.invoke(app, ["uninstall", "test-plugin", "--force"])
        assert result.exit_code == 0
        assert "uninstalled successfully" in result.stdout.lower()


def test_uninstall_plugin_not_found(mock_manager):
    """测试卸载不存在的插件"""
    mock_manager.get_plugin.return_value = None

    with patch("lurkbot.cli.plugin_cli.get_manager", return_value=mock_manager):
        result = runner.invoke(app, ["uninstall", "nonexistent", "--force"])
        assert result.exit_code == 1
        assert "not found" in result.stdout


# ============================================================================
# 测试插件启用和禁用
# ============================================================================


def test_enable_plugin(mock_manager):
    """测试启用插件"""
    with patch("lurkbot.cli.plugin_cli.get_manager", return_value=mock_manager):
        result = runner.invoke(app, ["enable", "test-plugin"])
        assert result.exit_code == 0
        assert "enabled" in result.stdout.lower()


def test_enable_plugin_failure(mock_manager):
    """测试启用插件失败"""
    mock_manager.enable_plugin = AsyncMock(return_value=False)

    with patch("lurkbot.cli.plugin_cli.get_manager", return_value=mock_manager):
        result = runner.invoke(app, ["enable", "test-plugin"])
        assert result.exit_code == 1
        assert "failed" in result.stdout.lower()


def test_disable_plugin(mock_manager):
    """测试禁用插件"""
    with patch("lurkbot.cli.plugin_cli.get_manager", return_value=mock_manager):
        result = runner.invoke(app, ["disable", "test-plugin"])
        assert result.exit_code == 0
        assert "disabled" in result.stdout.lower()


def test_disable_plugin_failure(mock_manager):
    """测试禁用插件失败"""
    mock_manager.disable_plugin = AsyncMock(return_value=False)

    with patch("lurkbot.cli.plugin_cli.get_manager", return_value=mock_manager):
        result = runner.invoke(app, ["disable", "test-plugin"])
        assert result.exit_code == 1
        assert "failed" in result.stdout.lower()


# ============================================================================
# 测试性能报告
# ============================================================================


def test_perf_single_plugin(mock_manager):
    """测试查看单个插件性能报告"""
    with patch("lurkbot.cli.plugin_cli.get_manager", return_value=mock_manager):
        result = runner.invoke(app, ["perf", "test-plugin"])
        assert result.exit_code == 0
        assert "Performance Report" in result.stdout
        assert "test-plugin" in result.stdout


def test_perf_all_plugins(mock_manager):
    """测试查看所有插件性能报告"""
    with patch("lurkbot.cli.plugin_cli.get_manager", return_value=mock_manager):
        result = runner.invoke(app, ["perf", "--all"])
        assert result.exit_code == 0
        assert "Performance Reports" in result.stdout


def test_perf_bottlenecks(mock_manager):
    """测试查看性能瓶颈"""
    with patch("lurkbot.cli.plugin_cli.get_manager", return_value=mock_manager):
        result = runner.invoke(app, ["perf", "--bottlenecks"])
        assert result.exit_code == 0
        assert "Bottlenecks" in result.stdout


def test_perf_json_output(mock_manager):
    """测试性能报告 JSON 输出"""
    with patch("lurkbot.cli.plugin_cli.get_manager", return_value=mock_manager):
        result = runner.invoke(app, ["perf", "test-plugin", "--json"])
        assert result.exit_code == 0

        output = json.loads(result.stdout)
        assert output["plugin"] == "test-plugin"
        assert "total_executions" in output


def test_perf_no_data(mock_manager):
    """测试无性能数据"""
    mock_manager.get_performance_report.return_value = None

    with patch("lurkbot.cli.plugin_cli.get_manager", return_value=mock_manager):
        result = runner.invoke(app, ["perf", "test-plugin"])
        assert result.exit_code == 1
        assert "No performance data" in result.stdout


def test_perf_profiling_disabled(mock_manager):
    """测试性能分析未启用"""
    mock_manager.profiler = None

    with patch("lurkbot.cli.plugin_cli.get_manager", return_value=mock_manager):
        result = runner.invoke(app, ["perf", "test-plugin"])
        assert result.exit_code == 1
        assert "not enabled" in result.stdout


# ============================================================================
# 测试权限管理
# ============================================================================


def test_show_permissions(mock_manager):
    """测试显示插件权限"""
    with patch("lurkbot.cli.plugin_cli.get_manager", return_value=mock_manager):
        result = runner.invoke(app, ["permissions", "test-plugin"])
        assert result.exit_code == 0
        assert "Permissions" in result.stdout
        assert "filesystem" in result.stdout.lower()


def test_show_permissions_json(mock_manager):
    """测试权限 JSON 输出"""
    with patch("lurkbot.cli.plugin_cli.get_manager", return_value=mock_manager):
        result = runner.invoke(app, ["permissions", "test-plugin", "--json"])
        assert result.exit_code == 0

        output = json.loads(result.stdout)
        assert isinstance(output, list)
        assert len(output) == 1


def test_show_permissions_disabled(mock_manager):
    """测试权限管理未启用"""
    mock_manager.permission_manager = None

    with patch("lurkbot.cli.plugin_cli.get_manager", return_value=mock_manager):
        result = runner.invoke(app, ["permissions", "test-plugin"])
        assert result.exit_code == 1
        assert "not enabled" in result.stdout


def test_grant_permission(mock_manager):
    """测试授予权限"""
    with patch("lurkbot.cli.plugin_cli.get_manager", return_value=mock_manager):
        result = runner.invoke(app, ["grant", "test-plugin", "filesystem.read"])
        assert result.exit_code == 0
        assert "Granted" in result.stdout


def test_grant_permission_invalid_type(mock_manager):
    """测试授予无效权限类型"""
    with patch("lurkbot.cli.plugin_cli.get_manager", return_value=mock_manager):
        result = runner.invoke(app, ["grant", "test-plugin", "invalid_permission"])
        assert result.exit_code == 1
        assert "Invalid permission type" in result.stdout


def test_revoke_permission(mock_manager):
    """测试撤销权限"""
    with patch("lurkbot.cli.plugin_cli.get_manager", return_value=mock_manager):
        result = runner.invoke(app, ["revoke", "test-plugin", "filesystem.read"])
        assert result.exit_code == 0
        assert "Revoked" in result.stdout


def test_audit_log(mock_manager):
    """测试查看审计日志"""
    mock_manager.get_permission_audit_log = AsyncMock(
        return_value=[
            {
                "timestamp": "2024-01-01T00:00:00",
                "plugin_name": "test-plugin",
                "action": "grant",
                "permission_type": "filesystem.read",
            }
        ]
    )

    with patch("lurkbot.cli.plugin_cli.get_manager", return_value=mock_manager):
        result = runner.invoke(app, ["audit-log"])
        assert result.exit_code == 0
        assert "Audit Log" in result.stdout


def test_audit_log_empty(mock_manager):
    """测试空审计日志"""
    with patch("lurkbot.cli.plugin_cli.get_manager", return_value=mock_manager):
        result = runner.invoke(app, ["audit-log"])
        assert result.exit_code == 0
        assert "No audit log entries" in result.stdout


# ============================================================================
# 测试版本管理
# ============================================================================


def test_list_versions(mock_manager):
    """测试列出插件版本"""
    with patch("lurkbot.cli.plugin_cli.get_manager", return_value=mock_manager):
        result = runner.invoke(app, ["versions", "test-plugin"])
        assert result.exit_code == 0
        assert "1.0.0" in result.stdout
        assert "1.1.0" in result.stdout


def test_list_versions_empty(mock_manager):
    """测试空版本列表"""
    mock_manager.get_plugin_versions.return_value = []

    with patch("lurkbot.cli.plugin_cli.get_manager", return_value=mock_manager):
        result = runner.invoke(app, ["versions", "test-plugin"])
        assert result.exit_code == 0
        assert "No versions found" in result.stdout


def test_list_versions_disabled(mock_manager):
    """测试版本管理未启用"""
    mock_manager.version_manager = None

    with patch("lurkbot.cli.plugin_cli.get_manager", return_value=mock_manager):
        result = runner.invoke(app, ["versions", "test-plugin"])
        assert result.exit_code == 1
        assert "not enabled" in result.stdout


def test_switch_version(mock_manager):
    """测试切换版本"""
    with patch("lurkbot.cli.plugin_cli.get_manager", return_value=mock_manager):
        result = runner.invoke(app, ["switch", "test-plugin", "1.1.0"])
        assert result.exit_code == 0
        assert "Switched" in result.stdout


def test_switch_version_failure(mock_manager):
    """测试切换版本失败"""
    mock_manager.switch_plugin_version = AsyncMock(return_value=False)

    with patch("lurkbot.cli.plugin_cli.get_manager", return_value=mock_manager):
        result = runner.invoke(app, ["switch", "test-plugin", "1.1.0"])
        assert result.exit_code == 1
        assert "Failed" in result.stdout


def test_rollback_version(mock_manager):
    """测试回滚版本"""
    with patch("lurkbot.cli.plugin_cli.get_manager", return_value=mock_manager):
        result = runner.invoke(app, ["rollback", "test-plugin"])
        assert result.exit_code == 0
        assert "Rolled back" in result.stdout


def test_version_history(mock_manager):
    """测试查看版本历史"""
    with patch("lurkbot.cli.plugin_cli.get_manager", return_value=mock_manager):
        result = runner.invoke(app, ["history", "test-plugin"])
        assert result.exit_code == 0
        assert "Version History" in result.stdout
        assert "1.0.0" in result.stdout


def test_version_history_empty(mock_manager):
    """测试空版本历史"""
    mock_manager.get_version_history.return_value = []

    with patch("lurkbot.cli.plugin_cli.get_manager", return_value=mock_manager):
        result = runner.invoke(app, ["history", "test-plugin"])
        assert result.exit_code == 0
        assert "No version history" in result.stdout


# ============================================================================
# 测试依赖图可视化
# ============================================================================


def test_show_dependencies(mock_manager):
    """测试显示依赖图"""
    with patch("lurkbot.cli.plugin_cli.get_manager", return_value=mock_manager):
        result = runner.invoke(app, ["deps"])
        assert result.exit_code == 0
        assert "Dependency Graph" in result.stdout


def test_show_dependencies_json(mock_manager):
    """测试依赖图 JSON 输出"""
    mock_manager.visualize_dependency_graph.return_value = '{"test": "data"}'

    with patch("lurkbot.cli.plugin_cli.get_manager", return_value=mock_manager):
        result = runner.invoke(app, ["deps", "--format", "json"])
        assert result.exit_code == 0


def test_show_dependencies_disabled(mock_manager):
    """测试编排未启用"""
    mock_manager.orchestrator = None

    with patch("lurkbot.cli.plugin_cli.get_manager", return_value=mock_manager):
        result = runner.invoke(app, ["deps"])
        assert result.exit_code == 1
        assert "not enabled" in result.stdout
