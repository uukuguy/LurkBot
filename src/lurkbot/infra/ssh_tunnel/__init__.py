"""SSH Tunnel Management.

生成和管理 SSH 端口转发隧道。

对标 MoltBot `src/infra/ssh-tunnel.ts`

安全说明：
- 使用 asyncio.create_subprocess_exec() 而非 shell=True
- 所有参数通过列表传递，避免 shell 注入
- SSH 二进制路径硬编码为 /usr/bin/ssh
"""

import asyncio
import re
import signal
import socket
from typing import Callable

from .types import SshParsedTarget, SshTunnel, SshTunnelConfig

__all__ = [
    "SshParsedTarget",
    "SshTunnel",
    "SshTunnelConfig",
    "SshTunnelManager",
    "parse_ssh_target",
    "start_ssh_port_forward",
    "find_available_port",
]

# SSH 二进制路径（硬编码，避免注入）
SSH_BINARY = "/usr/bin/ssh"


def parse_ssh_target(raw: str) -> SshParsedTarget:
    """
    解析 SSH 目标字符串。

    支持格式:
    - host
    - host:port
    - user@host
    - user@host:port

    Args:
        raw: 原始字符串

    Returns:
        解析后的目标

    Raises:
        ValueError: 如果格式无效
    """
    # 匹配 user@host:port 格式
    match = re.match(r"^(?:([^@]+)@)?([^:]+)(?::(\d+))?$", raw.strip())
    if not match:
        raise ValueError(f"Invalid SSH target format: {raw}")

    user = match.group(1)
    host = match.group(2)
    port_str = match.group(3)

    port = int(port_str) if port_str else 22

    return SshParsedTarget(host=host, port=port, user=user)


def find_available_port(start: int = 49152, end: int = 65535) -> int:
    """
    查找可用的本地端口。

    Args:
        start: 起始端口
        end: 结束端口

    Returns:
        可用端口

    Raises:
        RuntimeError: 如果没有可用端口
    """
    for port in range(start, end):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.bind(("127.0.0.1", port))
                return port
        except OSError:
            continue

    raise RuntimeError("No available port found")


class SshTunnelManager:
    """
    SSH 隧道管理器。

    管理 SSH 端口转发隧道的生命周期。

    对标 MoltBot ssh-tunnel.ts
    """

    def __init__(self) -> None:
        self._tunnels: dict[str, SshTunnel] = {}
        self._processes: dict[str, asyncio.subprocess.Process] = {}

    async def start(
        self,
        config: SshTunnelConfig,
        *,
        tunnel_id: str | None = None,
        on_stderr: Callable[[str], None] | None = None,
    ) -> SshTunnel:
        """
        启动 SSH 端口转发隧道。

        使用 create_subprocess_exec 避免 shell 注入。

        Args:
            config: 隧道配置
            tunnel_id: 隧道 ID（可选，自动生成）
            on_stderr: stderr 回调

        Returns:
            隧道实例

        Raises:
            RuntimeError: 如果启动失败
        """
        # 解析目标
        parsed_target = parse_ssh_target(config.target)

        # 确定本地端口
        local_port = config.local_port
        if local_port == 0:
            local_port = find_available_port()

        # 构建 SSH 命令参数
        args = self._build_ssh_args(config, parsed_target, local_port)

        # 生成隧道 ID
        if tunnel_id is None:
            tunnel_id = f"{parsed_target.host}:{config.remote_port}:{local_port}"

        # 创建隧道实例
        tunnel = SshTunnel(
            parsed_target=parsed_target,
            local_port=local_port,
            remote_port=config.remote_port,
            stderr_lines=[],
            is_running=False,
        )

        # 启动 SSH 进程（使用 exec 风格，避免 shell 注入）
        proc = await asyncio.create_subprocess_exec(
            SSH_BINARY,
            *args,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )

        tunnel.pid = proc.pid
        self._tunnels[tunnel_id] = tunnel
        self._processes[tunnel_id] = proc

        # 启动 stderr 读取任务
        asyncio.create_task(self._read_stderr(tunnel_id, proc, on_stderr))

        # 等待隧道建立
        try:
            await self._wait_for_listener(local_port, timeout=config.connect_timeout_seconds)
            tunnel.is_running = True
        except TimeoutError as e:
            await self.stop(tunnel_id)
            raise RuntimeError(f"SSH tunnel failed to establish: {e}") from e

        return tunnel

    def _build_ssh_args(
        self,
        config: SshTunnelConfig,
        target: SshParsedTarget,
        local_port: int,
    ) -> list[str]:
        """构建 SSH 命令参数（列表形式，避免 shell 注入）。"""
        args = [
            "-N",  # 不执行远程命令
            "-T",  # 禁用伪终端
            "-o", f"StrictHostKeyChecking={config.strict_host_key_checking}",
            "-o", f"ExitOnForwardFailure={'yes' if config.exit_on_forward_failure else 'no'}",
            "-o", f"BatchMode={'yes' if config.batch_mode else 'no'}",
            "-o", f"ServerAliveInterval={config.keepalive_interval_seconds}",
            "-o", f"ConnectTimeout={config.connect_timeout_seconds}",
        ]

        # 身份文件
        if config.identity_file:
            args.extend(["-i", config.identity_file])

        # 端口转发
        args.extend([
            "-L", f"{local_port}:127.0.0.1:{config.remote_port}",
        ])

        # 端口
        if target.port != 22:
            args.extend(["-p", str(target.port)])

        # 目标
        if target.user:
            args.append(f"{target.user}@{target.host}")
        else:
            args.append(target.host)

        return args

    async def _read_stderr(
        self,
        tunnel_id: str,
        proc: asyncio.subprocess.Process,
        on_stderr: Callable[[str], None] | None,
    ) -> None:
        """读取 stderr 输出。"""
        tunnel = self._tunnels.get(tunnel_id)
        if not tunnel or not proc.stderr:
            return

        while True:
            try:
                line = await proc.stderr.readline()
                if not line:
                    break

                line_str = line.decode("utf-8", errors="replace").strip()
                if line_str:
                    tunnel.stderr_lines.append(line_str)
                    if on_stderr:
                        on_stderr(line_str)
            except Exception:
                break

    async def _wait_for_listener(
        self,
        port: int,
        timeout: int = 30,
        poll_interval: float = 0.25,
    ) -> None:
        """等待本地端口监听器就绪。"""
        elapsed = 0.0
        while elapsed < timeout:
            try:
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection("127.0.0.1", port),
                    timeout=1.0,
                )
                writer.close()
                await writer.wait_closed()
                return
            except (ConnectionRefusedError, asyncio.TimeoutError, OSError):
                await asyncio.sleep(poll_interval)
                elapsed += poll_interval

        raise TimeoutError(f"Port {port} did not become available within {timeout}s")

    async def stop(self, tunnel_id: str, *, force: bool = False) -> None:
        """
        停止 SSH 隧道。

        Args:
            tunnel_id: 隧道 ID
            force: 是否强制终止
        """
        proc = self._processes.pop(tunnel_id, None)
        tunnel = self._tunnels.pop(tunnel_id, None)

        if not proc:
            return

        if tunnel:
            tunnel.is_running = False

        # 先尝试 SIGTERM
        try:
            proc.send_signal(signal.SIGTERM)
        except (ProcessLookupError, OSError):
            return

        # 等待进程退出
        try:
            await asyncio.wait_for(proc.wait(), timeout=1.5)
        except asyncio.TimeoutError:
            # 强制终止
            if force:
                try:
                    proc.kill()
                    await proc.wait()
                except (ProcessLookupError, OSError):
                    pass

    async def stop_all(self) -> None:
        """停止所有隧道。"""
        tunnel_ids = list(self._tunnels.keys())
        for tunnel_id in tunnel_ids:
            await self.stop(tunnel_id)

    def get_tunnel(self, tunnel_id: str) -> SshTunnel | None:
        """获取隧道实例。"""
        return self._tunnels.get(tunnel_id)

    def list_tunnels(self) -> list[SshTunnel]:
        """列出所有隧道。"""
        return list(self._tunnels.values())


# 全局实例
_manager = SshTunnelManager()


async def start_ssh_port_forward(
    target: str,
    remote_port: int,
    *,
    local_port: int = 0,
    identity_file: str | None = None,
    timeout_seconds: int = 30,
) -> SshTunnel:
    """
    启动 SSH 端口转发隧道。

    Args:
        target: SSH 目标（user@host:port 格式）
        remote_port: 远程端口
        local_port: 本地端口（0 表示自动选择）
        identity_file: 身份文件路径
        timeout_seconds: 连接超时（秒）

    Returns:
        隧道实例
    """
    config = SshTunnelConfig(
        target=target,
        local_port=local_port,
        remote_port=remote_port,
        identity_file=identity_file,
        connect_timeout_seconds=timeout_seconds,
    )
    return await _manager.start(config)
