"""
Daemon Diagnostics - 守护进程诊断工具

对标: MoltBot src/daemon/diagnostics.ts

提供服务状态诊断和常见问题检测。
"""

import asyncio
import socket
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from .service import GatewayService, ServiceRuntime
from .paths import get_gateway_log_path, get_gateway_err_log_path


@dataclass
class DiagnosticResult:
    """诊断结果"""

    level: Literal["ok", "warning", "error"]
    """诊断级别"""

    message: str
    """诊断消息"""

    suggestion: str | None = None
    """修复建议"""


async def diagnose_service(service: GatewayService) -> list[DiagnosticResult]:
    """
    诊断服务状态

    对标: MoltBot diagnoseService()

    Args:
        service: 服务实例

    Returns:
        list[DiagnosticResult]: 诊断结果列表
    """
    results: list[DiagnosticResult] = []

    # 1. 检查服务是否已加载
    is_loaded = await service.is_loaded()
    if not is_loaded:
        results.append(
            DiagnosticResult(
                level="error",
                message="Service is not installed",
                suggestion=f"Run 'lurkbot daemon install' to install the service",
            )
        )
        return results  # 服务未安装，后续检查无意义

    # 2. 检查运行时状态
    runtime = await service.get_runtime()
    if runtime.status == "stopped":
        results.append(
            DiagnosticResult(
                level="warning",
                message="Service is stopped",
                suggestion=f"Run 'lurkbot daemon start' to start the service",
            )
        )
    elif runtime.status == "unknown":
        results.append(
            DiagnosticResult(
                level="warning",
                message="Service status is unknown",
                suggestion="Check system logs for more information",
            )
        )
    else:
        results.append(
            DiagnosticResult(
                level="ok",
                message=f"Service is running (PID: {runtime.pid})",
            )
        )

    # 3. 检查最后退出状态
    if runtime.last_exit_status is not None and runtime.last_exit_status != 0:
        results.append(
            DiagnosticResult(
                level="error",
                message=f"Last exit status: {runtime.last_exit_status}",
                suggestion="Check error logs for crash details",
            )
        )

    # 4. 检查日志文件
    log_results = await _check_log_files()
    results.extend(log_results)

    # 5. 检查端口占用（如果服务正在运行）
    if runtime.status == "running":
        port_results = await _check_port_availability(18789)
        results.extend(port_results)

    return results


async def _check_log_files() -> list[DiagnosticResult]:
    """
    检查日志文件

    Returns:
        list[DiagnosticResult]: 诊断结果
    """
    results: list[DiagnosticResult] = []

    log_path = get_gateway_log_path()
    err_log_path = get_gateway_err_log_path()

    # 检查标准日志
    if log_path.exists():
        size = log_path.stat().st_size
        if size > 10 * 1024 * 1024:  # 10MB
            results.append(
                DiagnosticResult(
                    level="warning",
                    message=f"Log file is large ({size // 1024 // 1024}MB)",
                    suggestion="Consider rotating logs",
                )
            )
    else:
        results.append(
            DiagnosticResult(
                level="warning",
                message="Log file does not exist",
                suggestion="Service may not have started yet",
            )
        )

    # 检查错误日志
    if err_log_path.exists():
        size = err_log_path.stat().st_size
        if size > 0:
            # 读取最后几行
            try:
                with open(err_log_path, "r") as f:
                    lines = f.readlines()
                    last_lines = lines[-5:] if len(lines) > 5 else lines
                    if last_lines:
                        results.append(
                            DiagnosticResult(
                                level="error",
                                message=f"Error log contains {len(lines)} lines",
                                suggestion=f"Recent errors:\n{''.join(last_lines)}",
                            )
                        )
            except Exception:
                pass

    return results


async def _check_port_availability(port: int) -> list[DiagnosticResult]:
    """
    检查端口是否可用

    Args:
        port: 端口号

    Returns:
        list[DiagnosticResult]: 诊断结果
    """
    results: list[DiagnosticResult] = []

    try:
        # 尝试连接端口
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection("127.0.0.1", port), timeout=2.0
        )
        writer.close()
        await writer.wait_closed()

        results.append(
            DiagnosticResult(
                level="ok",
                message=f"Port {port} is accessible",
            )
        )
    except asyncio.TimeoutError:
        results.append(
            DiagnosticResult(
                level="warning",
                message=f"Port {port} connection timeout",
                suggestion="Service may be starting or unresponsive",
            )
        )
    except ConnectionRefusedError:
        results.append(
            DiagnosticResult(
                level="error",
                message=f"Port {port} connection refused",
                suggestion="Service is not listening on this port",
            )
        )
    except Exception as e:
        results.append(
            DiagnosticResult(
                level="error",
                message=f"Port {port} check failed: {e}",
            )
        )

    return results


def format_diagnostic_report(results: list[DiagnosticResult]) -> str:
    """
    格式化诊断报告

    Args:
        results: 诊断结果列表

    Returns:
        str: 格式化的报告
    """
    lines = ["=== Service Diagnostic Report ===\n"]

    for result in results:
        # 级别图标
        icon = {"ok": "✅", "warning": "⚠️", "error": "❌"}[result.level]

        lines.append(f"{icon} {result.message}")

        if result.suggestion:
            lines.append(f"   💡 {result.suggestion}")

        lines.append("")

    return "\n".join(lines)


__all__ = [
    "DiagnosticResult",
    "diagnose_service",
    "format_diagnostic_report",
]
