"""Tailscale Integration.

Tailscale VPN 集成，用于安全的跨网络通信。

对标 MoltBot `src/infra/tailscale.ts`
"""

import asyncio
import json
import shutil
import subprocess
from datetime import datetime
from typing import Any

from .types import TailscaleConfig, TailscaleNode, TailscaleStatus

__all__ = [
    "TailscaleNode",
    "TailscaleStatus",
    "TailscaleConfig",
    "TailscaleClient",
    "tailscale_client",
    "get_tailscale_status",
    "get_tailscale_ip",
    "is_tailscale_available",
    "list_tailscale_peers",
]


def _parse_datetime(value: str | None) -> datetime | None:
    """解析 ISO 格式的日期时间字符串。"""
    if not value:
        return None
    try:
        # 处理 Go 风格的时间格式
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        return datetime.fromisoformat(value)
    except (ValueError, TypeError):
        return None


def _parse_node(data: dict[str, Any]) -> TailscaleNode:
    """从 JSON 数据解析节点信息。"""
    # 获取 IP 地址
    tailscale_ips = data.get("TailscaleIPs", [])
    ip = None
    ipv6 = None
    for addr in tailscale_ips:
        if ":" in addr:
            ipv6 = addr
        else:
            ip = addr

    return TailscaleNode(
        id=data.get("ID", ""),
        name=data.get("DNSName", "").split(".")[0] or data.get("HostName", ""),
        hostname=data.get("HostName", ""),
        ip=ip,
        ipv6=ipv6,
        dns_name=data.get("DNSName"),
        online=data.get("Online", False),
        active=data.get("Active", False),
        exit_node=data.get("ExitNode", False),
        exit_node_option=data.get("ExitNodeOption", False),
        os=data.get("OS"),
        user_id=str(data.get("UserID")) if data.get("UserID") else None,
        tags=data.get("Tags", []),
        created=_parse_datetime(data.get("Created")),
        last_seen=_parse_datetime(data.get("LastSeen")),
        expires=_parse_datetime(data.get("KeyExpiry")),
    )


class TailscaleClient:
    """
    Tailscale 客户端。

    通过 CLI 与 Tailscale 交互，提供状态查询、节点列表等功能。

    对标 MoltBot tailscale.ts
    """

    def __init__(self, config: TailscaleConfig | None = None) -> None:
        self._config = config or TailscaleConfig()
        self._cli_path: str | None = None
        self._last_status: TailscaleStatus | None = None

    @property
    def cli_path(self) -> str | None:
        """获取 Tailscale CLI 路径。"""
        if self._cli_path is None:
            self._cli_path = shutil.which("tailscale")
        return self._cli_path

    def is_available(self) -> bool:
        """检查 Tailscale 是否可用。"""
        return self.cli_path is not None

    def _run_command(
        self,
        args: list[str],
        *,
        timeout: int | None = None,
    ) -> tuple[bool, str, str]:
        """
        运行 Tailscale CLI 命令。

        使用 subprocess.run 的 execFile 风格调用，避免 shell 注入。

        Args:
            args: 命令参数
            timeout: 超时时间（秒）

        Returns:
            (成功, stdout, stderr)
        """
        if not self.cli_path:
            return False, "", "Tailscale CLI not found"

        timeout = timeout or self._config.timeout_seconds

        try:
            # 使用列表形式调用，避免 shell 注入
            result = subprocess.run(
                [self.cli_path, *args],
                capture_output=True,
                text=True,
                timeout=timeout,
                shell=False,  # 明确禁用 shell
            )
            return result.returncode == 0, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return False, "", "Command timed out"
        except Exception as e:
            return False, "", str(e)

    async def _run_command_async(
        self,
        args: list[str],
        *,
        timeout: int | None = None,
    ) -> tuple[bool, str, str]:
        """
        异步运行 Tailscale CLI 命令。

        使用 asyncio.create_subprocess_exec，避免 shell 注入。

        Args:
            args: 命令参数
            timeout: 超时时间（秒）

        Returns:
            (成功, stdout, stderr)
        """
        if not self.cli_path:
            return False, "", "Tailscale CLI not found"

        timeout = timeout or self._config.timeout_seconds

        try:
            # 使用 exec 风格调用，避免 shell 注入
            proc = await asyncio.create_subprocess_exec(
                self.cli_path,
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=timeout,
            )
            return (
                proc.returncode == 0,
                stdout.decode() if stdout else "",
                stderr.decode() if stderr else "",
            )
        except asyncio.TimeoutError:
            return False, "", "Command timed out"
        except Exception as e:
            return False, "", str(e)

    def get_status(self, *, use_cache: bool = False) -> TailscaleStatus | None:
        """
        获取 Tailscale 状态。

        Args:
            use_cache: 是否使用缓存

        Returns:
            Tailscale 状态
        """
        if use_cache and self._last_status:
            return self._last_status

        success, stdout, _ = self._run_command(["status", "--json"])
        if not success:
            return None

        try:
            data = json.loads(stdout)
            return self._parse_status(data)
        except json.JSONDecodeError:
            return None

    async def get_status_async(
        self,
        *,
        use_cache: bool = False,
    ) -> TailscaleStatus | None:
        """
        异步获取 Tailscale 状态。

        Args:
            use_cache: 是否使用缓存

        Returns:
            Tailscale 状态
        """
        if use_cache and self._last_status:
            return self._last_status

        success, stdout, _ = await self._run_command_async(["status", "--json"])
        if not success:
            return None

        try:
            data = json.loads(stdout)
            return self._parse_status(data)
        except json.JSONDecodeError:
            return None

    def _parse_status(self, data: dict[str, Any]) -> TailscaleStatus:
        """解析状态 JSON。"""
        # 解析自身节点
        self_data = data.get("Self")
        self_node = _parse_node(self_data) if self_data else None

        # 解析对等节点
        peers: dict[str, TailscaleNode] = {}
        peer_data = data.get("Peer", {})
        for peer_id, peer_info in peer_data.items():
            peers[peer_id] = _parse_node(peer_info)

        status = TailscaleStatus(
            backend_state=data.get("BackendState", "Unknown"),
            self_node=self_node,
            tailnet_name=data.get("CurrentTailnet", {}).get("Name"),
            magic_dns_suffix=data.get("MagicDNSSuffix"),
            cert_domains=data.get("CertDomains", []),
            peers=peers,
            health=data.get("Health", []),
            raw=data,
        )

        self._last_status = status
        return status

    def get_ip(self) -> str | None:
        """
        获取当前节点的 Tailscale IP。

        Returns:
            Tailscale IP 地址
        """
        success, stdout, _ = self._run_command(["ip", "-4"])
        if success and stdout.strip():
            return stdout.strip().split("\n")[0]
        return None

    async def get_ip_async(self) -> str | None:
        """
        异步获取当前节点的 Tailscale IP。

        Returns:
            Tailscale IP 地址
        """
        success, stdout, _ = await self._run_command_async(["ip", "-4"])
        if success and stdout.strip():
            return stdout.strip().split("\n")[0]
        return None

    def list_peers(self, *, online_only: bool = False) -> list[TailscaleNode]:
        """
        列出所有对等节点。

        Args:
            online_only: 是否只返回在线节点

        Returns:
            节点列表
        """
        status = self.get_status()
        if not status:
            return []

        peers = list(status.peers.values())
        if online_only:
            peers = [p for p in peers if p.online]

        return peers

    async def list_peers_async(
        self,
        *,
        online_only: bool = False,
    ) -> list[TailscaleNode]:
        """
        异步列出所有对等节点。

        Args:
            online_only: 是否只返回在线节点

        Returns:
            节点列表
        """
        status = await self.get_status_async()
        if not status:
            return []

        peers = list(status.peers.values())
        if online_only:
            peers = [p for p in peers if p.online]

        return peers

    def ping(self, target: str, *, count: int = 1) -> bool:
        """
        Ping 目标节点。

        Args:
            target: 目标节点名称或 IP
            count: ping 次数

        Returns:
            是否成功
        """
        success, _, _ = self._run_command(["ping", "-c", str(count), target])
        return success

    async def ping_async(self, target: str, *, count: int = 1) -> bool:
        """
        异步 Ping 目标节点。

        Args:
            target: 目标节点名称或 IP
            count: ping 次数

        Returns:
            是否成功
        """
        success, _, _ = await self._run_command_async(
            ["ping", "-c", str(count), target]
        )
        return success

    def up(self) -> bool:
        """
        启动 Tailscale。

        Returns:
            是否成功
        """
        args = ["up"]

        if self._config.auth_key:
            args.extend(["--authkey", self._config.auth_key])
        if self._config.control_url:
            args.extend(["--login-server", self._config.control_url])
        if self._config.accept_routes:
            args.append("--accept-routes")
        if self._config.accept_dns:
            args.append("--accept-dns")
        if self._config.shields_up:
            args.append("--shields-up")
        if self._config.exit_node:
            args.extend(["--exit-node", self._config.exit_node])
        if self._config.exit_node_allow_lan_access:
            args.append("--exit-node-allow-lan-access")
        if self._config.advertise_tags:
            args.extend(["--advertise-tags", ",".join(self._config.advertise_tags)])

        success, _, _ = self._run_command(args)
        return success

    def down(self) -> bool:
        """
        停止 Tailscale。

        Returns:
            是否成功
        """
        success, _, _ = self._run_command(["down"])
        return success


# 全局实例
tailscale_client = TailscaleClient()


# 便捷函数
def get_tailscale_status(*, use_cache: bool = False) -> TailscaleStatus | None:
    """
    获取 Tailscale 状态。

    Args:
        use_cache: 是否使用缓存

    Returns:
        Tailscale 状态
    """
    return tailscale_client.get_status(use_cache=use_cache)


def get_tailscale_ip() -> str | None:
    """
    获取当前节点的 Tailscale IP。

    Returns:
        Tailscale IP 地址
    """
    return tailscale_client.get_ip()


def is_tailscale_available() -> bool:
    """
    检查 Tailscale 是否可用。

    Returns:
        是否可用
    """
    return tailscale_client.is_available()


def list_tailscale_peers(*, online_only: bool = False) -> list[TailscaleNode]:
    """
    列出所有对等节点。

    Args:
        online_only: 是否只返回在线节点

    Returns:
        节点列表
    """
    return tailscale_client.list_peers(online_only=online_only)
