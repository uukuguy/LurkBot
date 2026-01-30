"""Device Pairing types.

对标 MoltBot `src/infra/device-pairing.ts`
"""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class DevicePairingPendingRequest:
    """设备配对待处理请求"""

    # 基本信息
    request_id: str
    device_id: str
    public_key: str

    # 设备信息
    display_name: str | None = None
    platform: str | None = None
    client_id: str | None = None
    client_mode: str | None = None

    # 权限信息
    role: str | None = None
    roles: list[str] = field(default_factory=list)
    scopes: list[str] = field(default_factory=list)

    # 网络信息
    remote_ip: str | None = None

    # 选项
    silent: bool = False
    is_repair: bool = False

    # 时间戳
    ts: int = 0  # 毫秒时间戳


@dataclass
class DeviceAuthToken:
    """设备认证令牌"""

    token: str
    role: str
    scopes: list[str] = field(default_factory=list)

    # 时间戳（毫秒）
    created_at_ms: int = 0
    rotated_at_ms: int | None = None
    revoked_at_ms: int | None = None
    last_used_at_ms: int | None = None


@dataclass
class PairedDevice:
    """已配对设备"""

    # 基本信息
    device_id: str
    public_key: str

    # 设备信息
    display_name: str | None = None
    platform: str | None = None
    client_id: str | None = None
    client_mode: str | None = None

    # 权限信息
    role: str | None = None
    roles: list[str] = field(default_factory=list)
    scopes: list[str] = field(default_factory=list)

    # 网络信息
    remote_ip: str | None = None

    # 令牌
    tokens: dict[str, DeviceAuthToken] = field(default_factory=dict)

    # 时间戳（毫秒）
    created_at_ms: int = 0
    approved_at_ms: int = 0


@dataclass
class DevicePairingData:
    """设备配对数据"""

    pending: dict[str, DevicePairingPendingRequest] = field(default_factory=dict)
    paired: dict[str, PairedDevice] = field(default_factory=dict)


@dataclass
class TokenVerifyParams:
    """令牌验证参数"""

    device_id: str
    token: str
    required_scopes: list[str] = field(default_factory=list)


@dataclass
class TokenVerifyResult:
    """令牌验证结果"""

    valid: bool
    device: PairedDevice | None = None
    token_info: DeviceAuthToken | None = None
    error: str | None = None
