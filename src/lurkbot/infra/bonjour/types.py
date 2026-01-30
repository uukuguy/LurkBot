"""Bonjour/mDNS types.

对标 MoltBot `src/infra/bonjour.ts`
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal


@dataclass
class BonjourService:
    """Bonjour 服务信息"""

    # 基本信息
    name: str
    type: str
    domain: str = "local"

    # 网络信息
    host: str | None = None
    port: int | None = None
    addresses: list[str] = field(default_factory=list)

    # TXT 记录
    txt: dict[str, str] = field(default_factory=dict)

    # 状态
    interface_index: int = 0
    flags: int = 0

    # 时间戳
    discovered_at: datetime = field(default_factory=datetime.now)
    last_seen: datetime = field(default_factory=datetime.now)


@dataclass
class BonjourBrowseResult:
    """Bonjour 浏览结果"""

    service: BonjourService
    event: Literal["added", "removed", "updated"]


@dataclass
class BonjourConfig:
    """Bonjour 配置"""

    # 服务类型
    service_type: str = "_lurkbot._tcp"

    # 服务名称（默认使用主机名）
    service_name: str | None = None

    # 端口
    port: int = 0

    # TXT 记录
    txt_record: dict[str, str] = field(default_factory=dict)

    # 超时设置
    browse_timeout_seconds: int = 10
    resolve_timeout_seconds: int = 5

    # 自动注册
    auto_register: bool = False
