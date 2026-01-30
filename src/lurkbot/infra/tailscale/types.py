"""Tailscale types.

对标 MoltBot `src/infra/tailscale.ts`
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal


@dataclass
class TailscaleNode:
    """Tailscale 节点信息"""

    # 基本信息
    id: str
    name: str
    hostname: str

    # 网络信息
    ip: str | None = None
    ipv6: str | None = None
    dns_name: str | None = None

    # 状态信息
    online: bool = False
    active: bool = False
    exit_node: bool = False
    exit_node_option: bool = False

    # 设备信息
    os: str | None = None
    user_id: str | None = None
    tags: list[str] = field(default_factory=list)

    # 时间戳
    created: datetime | None = None
    last_seen: datetime | None = None
    expires: datetime | None = None


@dataclass
class TailscaleStatus:
    """Tailscale 状态"""

    # 连接状态
    backend_state: Literal["Running", "Stopped", "NeedsLogin", "NeedsMachineAuth"] | str
    self_node: TailscaleNode | None = None

    # 网络信息
    tailnet_name: str | None = None
    magic_dns_suffix: str | None = None
    cert_domains: list[str] = field(default_factory=list)

    # 节点列表
    peers: dict[str, TailscaleNode] = field(default_factory=dict)

    # 健康状态
    health: list[str] = field(default_factory=list)

    # 原始数据
    raw: dict | None = None


@dataclass
class TailscaleConfig:
    """Tailscale 配置"""

    # 认证
    auth_key: str | None = None
    control_url: str | None = None

    # 网络设置
    accept_routes: bool = True
    accept_dns: bool = True
    shields_up: bool = False

    # 出口节点
    exit_node: str | None = None
    exit_node_allow_lan_access: bool = False

    # 标签
    advertise_tags: list[str] = field(default_factory=list)

    # 超时设置
    timeout_seconds: int = 30
