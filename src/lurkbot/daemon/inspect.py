"""
Daemon Inspect - 守护进程检查工具

对标: MoltBot src/daemon/inspect.ts

提供服务信息查询和状态检查。
"""

from dataclasses import dataclass
from pathlib import Path

from .service import GatewayService, ServiceRuntime


@dataclass
class ServiceInfo:
    """服务信息"""

    label: str
    """服务标签/名称"""

    is_loaded: bool
    """是否已加载"""

    runtime: ServiceRuntime
    """运行时状态"""

    config_path: Path | None = None
    """配置文件路径"""

    log_path: Path | None = None
    """日志文件路径"""

    err_log_path: Path | None = None
    """错误日志文件路径"""


async def inspect_service(service: GatewayService) -> ServiceInfo:
    """
    检查服务信息

    对标: MoltBot inspectService()

    Args:
        service: 服务实例

    Returns:
        ServiceInfo: 服务信息
    """
    from .paths import get_gateway_log_path, get_gateway_err_log_path

    is_loaded = await service.is_loaded()
    runtime = await service.get_runtime()

    # 获取配置文件路径（平台特定）
    config_path = _get_config_path(service)

    return ServiceInfo(
        label=service.label,
        is_loaded=is_loaded,
        runtime=runtime,
        config_path=config_path,
        log_path=get_gateway_log_path(),
        err_log_path=get_gateway_err_log_path(),
    )


def _get_config_path(service: GatewayService) -> Path | None:
    """
    获取服务配置文件路径

    Args:
        service: 服务实例

    Returns:
        Path | None: 配置文件路径
    """
    # 根据服务类型返回配置文件路径
    if hasattr(service, "plist_path"):
        # macOS LaunchdService
        return service.plist_path  # type: ignore
    elif hasattr(service, "unit_path"):
        # Linux SystemdService
        return service.unit_path  # type: ignore
    else:
        # Windows SchtasksService 没有持久化配置文件
        return None


def format_service_info(info: ServiceInfo) -> str:
    """
    格式化服务信息

    Args:
        info: 服务信息

    Returns:
        str: 格式化的信息
    """
    lines = [
        "=== Service Information ===\n",
        f"Label:        {info.label}",
        f"Loaded:       {'Yes' if info.is_loaded else 'No'}",
        f"Status:       {info.runtime.status}",
    ]

    if info.runtime.state:
        lines.append(f"State:        {info.runtime.state}")

    if info.runtime.sub_state:
        lines.append(f"Sub-State:    {info.runtime.sub_state}")

    if info.runtime.pid:
        lines.append(f"PID:          {info.runtime.pid}")

    if info.runtime.last_exit_status is not None:
        lines.append(f"Last Exit:    {info.runtime.last_exit_status}")

    if info.runtime.last_exit_reason:
        lines.append(f"Exit Reason:  {info.runtime.last_exit_reason}")

    lines.append("")

    if info.config_path:
        lines.append(f"Config:       {info.config_path}")
        lines.append(f"              {'(exists)' if info.config_path.exists() else '(missing)'}")

    if info.log_path:
        lines.append(f"Log:          {info.log_path}")
        if info.log_path.exists():
            size = info.log_path.stat().st_size
            lines.append(f"              ({size} bytes)")

    if info.err_log_path:
        lines.append(f"Error Log:    {info.err_log_path}")
        if info.err_log_path.exists():
            size = info.err_log_path.stat().st_size
            lines.append(f"              ({size} bytes)")

    return "\n".join(lines)


__all__ = [
    "ServiceInfo",
    "inspect_service",
    "format_service_info",
]
