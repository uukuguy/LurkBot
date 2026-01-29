"""
Phase 13 Tests - Daemon 守护进程系统

测试覆盖:
- 服务接口基础功能
- 不同平台服务实现
- 服务状态查询和转换
- 路径解析和常量
- 错误处理和诊断
"""

import platform
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from lurkbot.daemon import (
    # 服务接口
    GatewayService,
    ServiceRuntime,
    ServiceInstallArgs,
    resolve_gateway_service,
    # 常量
    GATEWAY_LAUNCH_AGENT_LABEL,
    SYSTEMD_SERVICE_NAME,
    SCHTASKS_TASK_NAME,
    DEFAULT_GATEWAY_PORT,
    DEFAULT_BIND_ADDRESS,
    # 路径工具
    get_lurkbot_home,
    get_logs_dir,
    get_run_dir,
    get_gateway_pid_path,
    get_gateway_log_path,
    get_gateway_err_log_path,
    get_workspace_config_path,
    ensure_directories,
    # 诊断工具
    DiagnosticResult,
    diagnose_service,
    format_diagnostic_report,
    # 检查工具
    ServiceInfo,
    inspect_service,
    format_service_info,
)


# ============================================================================
# 测试计数器
# ============================================================================


def test_phase13_test_count():
    """确保测试数量符合预期（26 个测试）"""
    import sys

    module = sys.modules[__name__]
    test_functions = [
        name for name in dir(module) if name.startswith("test_") and callable(getattr(module, name))
    ]
    count = len(test_functions)
    assert count == 26, f"Expected 26 tests, got {count}"


# ============================================================================
# 1. 服务接口基础功能测试
# ============================================================================


def test_service_runtime_creation():
    """测试 ServiceRuntime 数据类创建"""
    runtime = ServiceRuntime(
        status="running",
        state="active",
        sub_state="running",
        pid=12345,
        last_exit_status=0,
    )

    assert runtime.status == "running"
    assert runtime.state == "active"
    assert runtime.sub_state == "running"
    assert runtime.pid == 12345
    assert runtime.last_exit_status == 0


def test_service_install_args_defaults():
    """测试 ServiceInstallArgs 默认值"""
    args = ServiceInstallArgs()

    assert args.port == 18789
    assert args.bind == "loopback"
    assert args.profile is None
    assert args.workspace is None


def test_service_install_args_custom():
    """测试 ServiceInstallArgs 自定义值"""
    args = ServiceInstallArgs(
        port=8080,
        bind="lan",
        profile="dev",
        workspace="/path/to/workspace",
    )

    assert args.port == 8080
    assert args.bind == "lan"
    assert args.profile == "dev"
    assert args.workspace == "/path/to/workspace"


def test_resolve_gateway_service_returns_correct_type():
    """测试 resolve_gateway_service 返回正确的平台实现"""
    service = resolve_gateway_service()

    assert isinstance(service, GatewayService)

    system = platform.system()
    if system == "Darwin":
        from lurkbot.daemon.launchd import LaunchdService

        assert isinstance(service, LaunchdService)
    elif system == "Linux":
        from lurkbot.daemon.systemd import SystemdService

        assert isinstance(service, SystemdService)
    elif system == "Windows":
        from lurkbot.daemon.schtasks import SchtasksService

        assert isinstance(service, SchtasksService)


def test_resolve_gateway_service_with_profile():
    """测试 resolve_gateway_service 支持 profile 参数"""
    service = resolve_gateway_service(profile="test-profile")

    assert isinstance(service, GatewayService)
    assert "test-profile" in service.label or "test_profile" in service.label


# ============================================================================
# 2. 常量测试
# ============================================================================


def test_constants_defined():
    """测试所有常量已定义"""
    assert GATEWAY_LAUNCH_AGENT_LABEL == "bot.lurk.gateway"
    assert SYSTEMD_SERVICE_NAME == "lurkbot-gateway"
    assert SCHTASKS_TASK_NAME == "lurkbot-gateway"
    assert DEFAULT_GATEWAY_PORT == 18789
    assert DEFAULT_BIND_ADDRESS == "loopback"


# ============================================================================
# 3. 路径工具测试
# ============================================================================


def test_get_lurkbot_home():
    """测试 get_lurkbot_home 返回正确路径"""
    home = get_lurkbot_home()

    assert isinstance(home, Path)
    assert home == Path.home() / ".lurkbot"


def test_get_logs_dir():
    """测试 get_logs_dir 返回正确路径"""
    logs_dir = get_logs_dir()

    assert isinstance(logs_dir, Path)
    assert logs_dir == Path.home() / ".lurkbot" / "logs"


def test_get_run_dir():
    """测试 get_run_dir 返回正确路径"""
    run_dir = get_run_dir()

    assert isinstance(run_dir, Path)
    assert run_dir == Path.home() / ".lurkbot" / "run"


def test_get_gateway_pid_path():
    """测试 get_gateway_pid_path 返回正确路径"""
    pid_path = get_gateway_pid_path()

    assert isinstance(pid_path, Path)
    assert pid_path == Path.home() / ".lurkbot" / "run" / "gateway.pid"


def test_get_gateway_log_path():
    """测试 get_gateway_log_path 返回正确路径"""
    log_path = get_gateway_log_path()

    assert isinstance(log_path, Path)
    assert log_path == Path.home() / ".lurkbot" / "logs" / "gateway.log"


def test_get_gateway_err_log_path():
    """测试 get_gateway_err_log_path 返回正确路径"""
    err_log_path = get_gateway_err_log_path()

    assert isinstance(err_log_path, Path)
    assert err_log_path == Path.home() / ".lurkbot" / "logs" / "gateway.err.log"


def test_get_workspace_config_path():
    """测试 get_workspace_config_path 返回正确路径"""
    workspace = Path("/path/to/workspace")
    config_path = get_workspace_config_path(workspace)

    assert isinstance(config_path, Path)
    assert config_path == workspace / ".lurkbot" / "config.json"


def test_get_workspace_config_path_with_string():
    """测试 get_workspace_config_path 支持字符串参数"""
    workspace = "/path/to/workspace"
    config_path = get_workspace_config_path(workspace)

    assert isinstance(config_path, Path)
    assert config_path == Path(workspace) / ".lurkbot" / "config.json"


def test_ensure_directories_creates_dirs(tmp_path, monkeypatch):
    """测试 ensure_directories 创建必需目录"""
    # 使用临时目录
    fake_home = tmp_path / "fake_home"
    monkeypatch.setattr(Path, "home", lambda: fake_home)

    ensure_directories()

    assert (fake_home / ".lurkbot").exists()
    assert (fake_home / ".lurkbot" / "logs").exists()
    assert (fake_home / ".lurkbot" / "run").exists()


# ============================================================================
# 4. 诊断工具测试
# ============================================================================


def test_diagnostic_result_creation():
    """测试 DiagnosticResult 数据类创建"""
    result = DiagnosticResult(
        level="error",
        message="Service is not running",
        suggestion="Run 'lurkbot daemon start'",
    )

    assert result.level == "error"
    assert result.message == "Service is not running"
    assert result.suggestion == "Run 'lurkbot daemon start'"


@pytest.mark.asyncio
async def test_diagnose_service_not_installed():
    """测试诊断未安装的服务"""
    # 创建 mock 服务
    mock_service = AsyncMock(spec=GatewayService)
    mock_service.is_loaded = AsyncMock(return_value=False)

    results = await diagnose_service(mock_service)

    assert len(results) >= 1
    assert any(r.level == "error" and "not installed" in r.message.lower() for r in results)


@pytest.mark.asyncio
async def test_diagnose_service_stopped():
    """测试诊断已停止的服务"""
    # 创建 mock 服务
    mock_service = AsyncMock(spec=GatewayService)
    mock_service.is_loaded = AsyncMock(return_value=True)
    mock_service.get_runtime = AsyncMock(
        return_value=ServiceRuntime(status="stopped")
    )

    results = await diagnose_service(mock_service)

    assert len(results) >= 1
    assert any(r.level == "warning" and "stopped" in r.message.lower() for r in results)


def test_format_diagnostic_report():
    """测试格式化诊断报告"""
    results = [
        DiagnosticResult(level="ok", message="Service is running"),
        DiagnosticResult(
            level="warning",
            message="Log file is large",
            suggestion="Consider rotating logs",
        ),
        DiagnosticResult(
            level="error",
            message="Port is not accessible",
            suggestion="Check firewall settings",
        ),
    ]

    report = format_diagnostic_report(results)

    assert "Service is running" in report
    assert "Log file is large" in report
    assert "Port is not accessible" in report
    assert "Consider rotating logs" in report
    assert "Check firewall settings" in report


# ============================================================================
# 5. 检查工具测试
# ============================================================================


def test_service_info_creation():
    """测试 ServiceInfo 数据类创建"""
    runtime = ServiceRuntime(status="running", pid=12345)
    info = ServiceInfo(
        label="bot.lurk.gateway",
        is_loaded=True,
        runtime=runtime,
        config_path=Path("/path/to/config"),
        log_path=Path("/path/to/log"),
        err_log_path=Path("/path/to/err.log"),
    )

    assert info.label == "bot.lurk.gateway"
    assert info.is_loaded is True
    assert info.runtime.status == "running"
    assert info.config_path == Path("/path/to/config")


@pytest.mark.asyncio
async def test_inspect_service():
    """测试检查服务信息"""
    # 创建 mock 服务
    mock_service = AsyncMock(spec=GatewayService)
    mock_service.label = "test-service"
    mock_service.is_loaded = AsyncMock(return_value=True)
    mock_service.get_runtime = AsyncMock(
        return_value=ServiceRuntime(status="running", pid=12345)
    )

    info = await inspect_service(mock_service)

    assert info.label == "test-service"
    assert info.is_loaded is True
    assert info.runtime.status == "running"
    assert info.runtime.pid == 12345


def test_format_service_info():
    """测试格式化服务信息"""
    runtime = ServiceRuntime(
        status="running",
        state="active",
        sub_state="running",
        pid=12345,
        last_exit_status=0,
    )
    info = ServiceInfo(
        label="bot.lurk.gateway",
        is_loaded=True,
        runtime=runtime,
        config_path=Path("/path/to/config"),
        log_path=Path("/path/to/log"),
        err_log_path=Path("/path/to/err.log"),
    )

    formatted = format_service_info(info)

    assert "bot.lurk.gateway" in formatted
    assert "running" in formatted
    assert "12345" in formatted
    assert "/path/to/config" in formatted


# ============================================================================
# 6. 平台特定实现测试（当前平台）
# ============================================================================


@pytest.mark.skipif(platform.system() != "Darwin", reason="macOS only")
def test_launchd_service_label():
    """测试 LaunchdService 标签解析"""
    from lurkbot.daemon.launchd import LaunchdService

    service = LaunchdService()
    assert service.label == "bot.lurk.gateway"

    service_with_profile = LaunchdService(profile="dev")
    assert "dev" in service_with_profile.label


@pytest.mark.skipif(platform.system() != "Linux", reason="Linux only")
def test_systemd_service_label():
    """测试 SystemdService 标签解析"""
    from lurkbot.daemon.systemd import SystemdService

    service = SystemdService()
    assert service.label == "lurkbot-gateway"

    service_with_profile = SystemdService(profile="dev")
    assert "dev" in service_with_profile.label


@pytest.mark.skipif(platform.system() != "Windows", reason="Windows only")
def test_schtasks_service_label():
    """测试 SchtasksService 标签解析"""
    from lurkbot.daemon.schtasks import SchtasksService

    service = SchtasksService()
    assert service.label == "lurkbot-gateway"

    service_with_profile = SchtasksService(profile="dev")
    assert "dev" in service_with_profile.label


# ============================================================================
# 总结
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
