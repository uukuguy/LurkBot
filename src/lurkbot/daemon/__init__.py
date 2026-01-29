"""
Daemon - 守护进程系统

对标: MoltBot src/daemon/

提供跨平台的守护进程服务管理：
- macOS: launchd (LaunchAgent)
- Linux: systemd (user service)
- Windows: schtasks (计划任务)
"""

from .service import (
    GatewayService,
    ServiceRuntime,
    ServiceInstallArgs,
    resolve_gateway_service,
)
from .constants import (
    GATEWAY_LAUNCH_AGENT_LABEL,
    SYSTEMD_SERVICE_NAME,
    SCHTASKS_TASK_NAME,
    DEFAULT_GATEWAY_PORT,
    DEFAULT_BIND_ADDRESS,
)
from .paths import (
    get_lurkbot_home,
    get_logs_dir,
    get_run_dir,
    get_gateway_pid_path,
    get_gateway_log_path,
    get_gateway_err_log_path,
    get_workspace_config_path,
    ensure_directories,
)
from .diagnostics import (
    DiagnosticResult,
    diagnose_service,
    format_diagnostic_report,
)
from .inspect import (
    ServiceInfo,
    inspect_service,
    format_service_info,
)

# 平台特定实现（按需导入）
__all__ = [
    # 服务接口
    "GatewayService",
    "ServiceRuntime",
    "ServiceInstallArgs",
    "resolve_gateway_service",
    # 常量
    "GATEWAY_LAUNCH_AGENT_LABEL",
    "SYSTEMD_SERVICE_NAME",
    "SCHTASKS_TASK_NAME",
    "DEFAULT_GATEWAY_PORT",
    "DEFAULT_BIND_ADDRESS",
    # 路径工具
    "get_lurkbot_home",
    "get_logs_dir",
    "get_run_dir",
    "get_gateway_pid_path",
    "get_gateway_log_path",
    "get_gateway_err_log_path",
    "get_workspace_config_path",
    "ensure_directories",
    # 诊断工具
    "DiagnosticResult",
    "diagnose_service",
    "format_diagnostic_report",
    # 检查工具
    "ServiceInfo",
    "inspect_service",
    "format_service_info",
]
