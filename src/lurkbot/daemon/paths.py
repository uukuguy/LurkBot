"""
Daemon Paths - 守护进程路径解析

对标: MoltBot src/daemon/ 路径相关代码
"""

from pathlib import Path
from .constants import (
    LOG_DIR_NAME,
    RUN_DIR_NAME,
    GATEWAY_PID_FILE,
    GATEWAY_LOG_FILE,
    GATEWAY_ERR_LOG_FILE,
)


def get_lurkbot_home() -> Path:
    """
    获取 LurkBot 主目录

    Returns:
        Path: ~/.lurkbot/
    """
    return Path.home() / ".lurkbot"


def get_logs_dir() -> Path:
    """
    获取日志目录

    Returns:
        Path: ~/.lurkbot/logs/
    """
    return get_lurkbot_home() / LOG_DIR_NAME


def get_run_dir() -> Path:
    """
    获取运行时文件目录

    Returns:
        Path: ~/.lurkbot/run/
    """
    return get_lurkbot_home() / RUN_DIR_NAME


def get_gateway_pid_path() -> Path:
    """
    获取 Gateway PID 文件路径

    Returns:
        Path: ~/.lurkbot/run/gateway.pid
    """
    return get_run_dir() / GATEWAY_PID_FILE


def get_gateway_log_path() -> Path:
    """
    获取 Gateway 日志文件路径

    Returns:
        Path: ~/.lurkbot/logs/gateway.log
    """
    return get_logs_dir() / GATEWAY_LOG_FILE


def get_gateway_err_log_path() -> Path:
    """
    获取 Gateway 错误日志文件路径

    Returns:
        Path: ~/.lurkbot/logs/gateway.err.log
    """
    return get_logs_dir() / GATEWAY_ERR_LOG_FILE


def get_workspace_config_path(workspace: str | Path) -> Path:
    """
    获取工作区配置文件路径

    Args:
        workspace: 工作区路径

    Returns:
        Path: <workspace>/.lurkbot/config.json
    """
    if isinstance(workspace, str):
        workspace = Path(workspace)

    return workspace / ".lurkbot" / "config.json"


def ensure_directories() -> None:
    """
    确保所有必需的目录存在

    创建:
    - ~/.lurkbot/
    - ~/.lurkbot/logs/
    - ~/.lurkbot/run/
    """
    get_lurkbot_home().mkdir(parents=True, exist_ok=True)
    get_logs_dir().mkdir(parents=True, exist_ok=True)
    get_run_dir().mkdir(parents=True, exist_ok=True)


__all__ = [
    "get_lurkbot_home",
    "get_logs_dir",
    "get_run_dir",
    "get_gateway_pid_path",
    "get_gateway_log_path",
    "get_gateway_err_log_path",
    "get_workspace_config_path",
    "ensure_directories",
]
