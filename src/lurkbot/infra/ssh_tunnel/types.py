"""SSH Tunnel types.

对标 MoltBot `src/infra/ssh-tunnel.ts`
"""

from dataclasses import dataclass, field


@dataclass
class SshParsedTarget:
    """解析后的 SSH 目标"""

    host: str
    port: int = 22
    user: str | None = None


@dataclass
class SshTunnelConfig:
    """SSH 隧道配置"""

    # 目标
    target: str  # user@host:port 格式

    # 端口设置
    local_port: int = 0  # 0 表示使用临时端口
    remote_port: int = 0

    # 认证
    identity_file: str | None = None

    # 超时设置
    connect_timeout_seconds: int = 30
    keepalive_interval_seconds: int = 60

    # SSH 选项
    strict_host_key_checking: str = "accept-new"
    batch_mode: bool = True
    exit_on_forward_failure: bool = True


@dataclass
class SshTunnel:
    """SSH 隧道实例"""

    # 配置
    parsed_target: SshParsedTarget
    local_port: int
    remote_port: int

    # 进程信息
    pid: int | None = None
    stderr_lines: list[str] = field(default_factory=list)

    # 状态
    is_running: bool = False
