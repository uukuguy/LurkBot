"""
Daemon Constants - 守护进程常量定义

对标: MoltBot src/daemon/ 常量定义
"""

# ============================================================================
# 服务标签 / Service Labels
# ============================================================================

GATEWAY_LAUNCH_AGENT_LABEL = "bot.lurk.gateway"
"""macOS LaunchAgent 服务标签（Reverse Domain Notation）"""

SYSTEMD_SERVICE_NAME = "lurkbot-gateway"
"""Linux Systemd 服务名称"""

SCHTASKS_TASK_NAME = "lurkbot-gateway"
"""Windows 计划任务名称"""


# ============================================================================
# 默认配置 / Default Configuration
# ============================================================================

DEFAULT_GATEWAY_PORT = 18789
"""Gateway 默认监听端口"""

DEFAULT_BIND_ADDRESS = "loopback"
"""默认绑定地址类型"""


# ============================================================================
# 日志和 PID 文件 / Logs and PID Files
# ============================================================================

LOG_DIR_NAME = "logs"
"""日志目录名称"""

RUN_DIR_NAME = "run"
"""运行时文件目录名称"""

GATEWAY_PID_FILE = "gateway.pid"
"""Gateway PID 文件名"""

GATEWAY_LOG_FILE = "gateway.log"
"""Gateway 日志文件名"""

GATEWAY_ERR_LOG_FILE = "gateway.err.log"
"""Gateway 错误日志文件名"""


__all__ = [
    "GATEWAY_LAUNCH_AGENT_LABEL",
    "SYSTEMD_SERVICE_NAME",
    "SCHTASKS_TASK_NAME",
    "DEFAULT_GATEWAY_PORT",
    "DEFAULT_BIND_ADDRESS",
    "LOG_DIR_NAME",
    "RUN_DIR_NAME",
    "GATEWAY_PID_FILE",
    "GATEWAY_LOG_FILE",
    "GATEWAY_ERR_LOG_FILE",
]
