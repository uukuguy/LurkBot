"""System Presence types.

对标 MoltBot `src/infra/system-presence.ts`
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal


@dataclass
class SystemPresence:
    """系统存在感条目"""

    # 基本信息
    host: str | None = None
    ip: str | None = None
    version: str | None = None
    platform: str | None = None
    device_family: str | None = None
    model_identifier: str | None = None

    # 状态信息
    last_input_seconds: int | None = None
    mode: Literal["gateway", "node"] | None = None
    reason: Literal["self", "discovered", "imported"] | None = None

    # 身份信息
    device_id: str | None = None
    instance_id: str | None = None

    # 权限信息
    roles: list[str] = field(default_factory=list)
    scopes: list[str] = field(default_factory=list)

    # 原始文本和时间戳
    text: str = ""
    ts: datetime = field(default_factory=datetime.now)


@dataclass
class SystemPresenceUpdate:
    """系统存在感更新事件"""

    key: str
    previous: SystemPresence | None
    next: SystemPresence
    changes: dict[str, object]
    changed_keys: list[str]
