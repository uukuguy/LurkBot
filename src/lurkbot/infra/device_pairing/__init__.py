"""Device Pairing Management.

管理设备注册和认证令牌。

对标 MoltBot `src/infra/device-pairing.ts`
"""

import asyncio
import json
import os
import secrets
import time
from pathlib import Path
from typing import Any

from .types import (
    DeviceAuthToken,
    DevicePairingData,
    DevicePairingPendingRequest,
    PairedDevice,
    TokenVerifyParams,
    TokenVerifyResult,
)

__all__ = [
    "DevicePairingPendingRequest",
    "DeviceAuthToken",
    "PairedDevice",
    "DevicePairingData",
    "TokenVerifyParams",
    "TokenVerifyResult",
    "DevicePairingManager",
    "device_pairing_manager",
    "list_device_pairing",
    "get_paired_device",
    "request_device_pairing",
    "approve_device_pairing",
    "reject_device_pairing",
    "verify_device_token",
]

# 默认目录
DEFAULT_DEVICES_DIR = Path.home() / ".lurkbot" / "devices"

# 待处理请求 TTL（5 分钟）
PENDING_REQUEST_TTL_MS = 5 * 60 * 1000


def _get_ms_timestamp() -> int:
    """获取毫秒时间戳。"""
    return int(time.time() * 1000)


def _generate_token() -> str:
    """生成 32 字符 hex 令牌。"""
    return secrets.token_hex(16)


def _generate_request_id() -> str:
    """生成请求 ID。"""
    return secrets.token_hex(8)


class DevicePairingManager:
    """
    设备配对管理器。

    管理设备配对请求、已配对设备和认证令牌。

    对标 MoltBot device-pairing.ts
    """

    def __init__(self, devices_dir: Path | None = None) -> None:
        self._devices_dir = devices_dir or DEFAULT_DEVICES_DIR
        self._lock = asyncio.Lock()
        self._data: DevicePairingData | None = None

    @property
    def pending_file(self) -> Path:
        """待处理请求文件路径。"""
        return self._devices_dir / "pending.json"

    @property
    def paired_file(self) -> Path:
        """已配对设备文件路径。"""
        return self._devices_dir / "paired.json"

    async def _ensure_dir(self) -> None:
        """确保目录存在。"""
        self._devices_dir.mkdir(parents=True, exist_ok=True)

    async def _load(self) -> DevicePairingData:
        """加载配对数据。"""
        if self._data is not None:
            return self._data

        await self._ensure_dir()

        pending: dict[str, DevicePairingPendingRequest] = {}
        paired: dict[str, PairedDevice] = {}

        # 加载待处理请求
        if self.pending_file.exists():
            try:
                raw = json.loads(self.pending_file.read_text())
                for req_id, req_data in raw.items():
                    pending[req_id] = DevicePairingPendingRequest(
                        request_id=req_data.get("requestId", req_id),
                        device_id=req_data.get("deviceId", ""),
                        public_key=req_data.get("publicKey", ""),
                        display_name=req_data.get("displayName"),
                        platform=req_data.get("platform"),
                        client_id=req_data.get("clientId"),
                        client_mode=req_data.get("clientMode"),
                        role=req_data.get("role"),
                        roles=req_data.get("roles", []),
                        scopes=req_data.get("scopes", []),
                        remote_ip=req_data.get("remoteIp"),
                        silent=req_data.get("silent", False),
                        is_repair=req_data.get("isRepair", False),
                        ts=req_data.get("ts", 0),
                    )
            except (json.JSONDecodeError, KeyError):
                pass

        # 加载已配对设备
        if self.paired_file.exists():
            try:
                raw = json.loads(self.paired_file.read_text())
                for device_id, device_data in raw.items():
                    # 解析令牌
                    tokens: dict[str, DeviceAuthToken] = {}
                    for token_id, token_data in device_data.get("tokens", {}).items():
                        tokens[token_id] = DeviceAuthToken(
                            token=token_data.get("token", ""),
                            role=token_data.get("role", ""),
                            scopes=token_data.get("scopes", []),
                            created_at_ms=token_data.get("createdAtMs", 0),
                            rotated_at_ms=token_data.get("rotatedAtMs"),
                            revoked_at_ms=token_data.get("revokedAtMs"),
                            last_used_at_ms=token_data.get("lastUsedAtMs"),
                        )

                    paired[device_id] = PairedDevice(
                        device_id=device_data.get("deviceId", device_id),
                        public_key=device_data.get("publicKey", ""),
                        display_name=device_data.get("displayName"),
                        platform=device_data.get("platform"),
                        client_id=device_data.get("clientId"),
                        client_mode=device_data.get("clientMode"),
                        role=device_data.get("role"),
                        roles=device_data.get("roles", []),
                        scopes=device_data.get("scopes", []),
                        remote_ip=device_data.get("remoteIp"),
                        tokens=tokens,
                        created_at_ms=device_data.get("createdAtMs", 0),
                        approved_at_ms=device_data.get("approvedAtMs", 0),
                    )
            except (json.JSONDecodeError, KeyError):
                pass

        self._data = DevicePairingData(pending=pending, paired=paired)
        return self._data

    async def _save_pending(self) -> None:
        """保存待处理请求。"""
        if not self._data:
            return

        await self._ensure_dir()

        # 转换为 JSON 格式
        raw: dict[str, Any] = {}
        for req_id, req in self._data.pending.items():
            raw[req_id] = {
                "requestId": req.request_id,
                "deviceId": req.device_id,
                "publicKey": req.public_key,
                "displayName": req.display_name,
                "platform": req.platform,
                "clientId": req.client_id,
                "clientMode": req.client_mode,
                "role": req.role,
                "roles": req.roles,
                "scopes": req.scopes,
                "remoteIp": req.remote_ip,
                "silent": req.silent,
                "isRepair": req.is_repair,
                "ts": req.ts,
            }

        # 原子写入
        temp_file = self.pending_file.with_suffix(".tmp")
        temp_file.write_text(json.dumps(raw, indent=2))
        os.chmod(temp_file, 0o600)
        temp_file.rename(self.pending_file)

    async def _save_paired(self) -> None:
        """保存已配对设备。"""
        if not self._data:
            return

        await self._ensure_dir()

        # 转换为 JSON 格式
        raw: dict[str, Any] = {}
        for device_id, device in self._data.paired.items():
            tokens_raw: dict[str, Any] = {}
            for token_id, token in device.tokens.items():
                tokens_raw[token_id] = {
                    "token": token.token,
                    "role": token.role,
                    "scopes": token.scopes,
                    "createdAtMs": token.created_at_ms,
                    "rotatedAtMs": token.rotated_at_ms,
                    "revokedAtMs": token.revoked_at_ms,
                    "lastUsedAtMs": token.last_used_at_ms,
                }

            raw[device_id] = {
                "deviceId": device.device_id,
                "publicKey": device.public_key,
                "displayName": device.display_name,
                "platform": device.platform,
                "clientId": device.client_id,
                "clientMode": device.client_mode,
                "role": device.role,
                "roles": device.roles,
                "scopes": device.scopes,
                "remoteIp": device.remote_ip,
                "tokens": tokens_raw,
                "createdAtMs": device.created_at_ms,
                "approvedAtMs": device.approved_at_ms,
            }

        # 原子写入
        temp_file = self.paired_file.with_suffix(".tmp")
        temp_file.write_text(json.dumps(raw, indent=2))
        os.chmod(temp_file, 0o600)
        temp_file.rename(self.paired_file)

    async def list_pairing(self) -> tuple[list[DevicePairingPendingRequest], list[PairedDevice]]:
        """
        列出所有待处理请求和已配对设备。

        Returns:
            (待处理请求列表, 已配对设备列表)
        """
        async with self._lock:
            data = await self._load()

            # 清理过期的待处理请求
            now = _get_ms_timestamp()
            expired = [
                req_id
                for req_id, req in data.pending.items()
                if now - req.ts > PENDING_REQUEST_TTL_MS
            ]
            for req_id in expired:
                del data.pending[req_id]

            if expired:
                await self._save_pending()

            # 排序
            pending = sorted(data.pending.values(), key=lambda x: x.ts, reverse=True)
            paired = sorted(data.paired.values(), key=lambda x: x.approved_at_ms, reverse=True)

            return pending, paired

    async def get_paired_device(self, device_id: str) -> PairedDevice | None:
        """
        获取已配对设备。

        Args:
            device_id: 设备 ID

        Returns:
            已配对设备或 None
        """
        async with self._lock:
            data = await self._load()
            return data.paired.get(device_id)

    async def request_pairing(
        self,
        device_id: str,
        public_key: str,
        *,
        display_name: str | None = None,
        platform: str | None = None,
        client_id: str | None = None,
        client_mode: str | None = None,
        role: str | None = None,
        roles: list[str] | None = None,
        scopes: list[str] | None = None,
        remote_ip: str | None = None,
        silent: bool = False,
        is_repair: bool = False,
    ) -> DevicePairingPendingRequest:
        """
        创建配对请求。

        Args:
            device_id: 设备 ID
            public_key: 公钥
            display_name: 显示名称
            platform: 平台
            client_id: 客户端 ID
            client_mode: 客户端模式
            role: 角色
            roles: 角色列表
            scopes: 作用域列表
            remote_ip: 远程 IP
            silent: 是否静默
            is_repair: 是否修复

        Returns:
            配对请求
        """
        async with self._lock:
            data = await self._load()

            request_id = _generate_request_id()
            request = DevicePairingPendingRequest(
                request_id=request_id,
                device_id=device_id,
                public_key=public_key,
                display_name=display_name,
                platform=platform,
                client_id=client_id,
                client_mode=client_mode,
                role=role,
                roles=roles or [],
                scopes=scopes or [],
                remote_ip=remote_ip,
                silent=silent,
                is_repair=is_repair,
                ts=_get_ms_timestamp(),
            )

            data.pending[request_id] = request
            await self._save_pending()

            return request

    async def approve_pairing(self, request_id: str) -> PairedDevice | None:
        """
        批准配对请求。

        Args:
            request_id: 请求 ID

        Returns:
            已配对设备或 None
        """
        async with self._lock:
            data = await self._load()

            request = data.pending.pop(request_id, None)
            if not request:
                return None

            now = _get_ms_timestamp()

            # 创建令牌
            token = _generate_token()
            token_info = DeviceAuthToken(
                token=token,
                role=request.role or "user",
                scopes=request.scopes,
                created_at_ms=now,
            )

            # 创建已配对设备
            device = PairedDevice(
                device_id=request.device_id,
                public_key=request.public_key,
                display_name=request.display_name,
                platform=request.platform,
                client_id=request.client_id,
                client_mode=request.client_mode,
                role=request.role,
                roles=request.roles,
                scopes=request.scopes,
                remote_ip=request.remote_ip,
                tokens={"default": token_info},
                created_at_ms=now,
                approved_at_ms=now,
            )

            data.paired[request.device_id] = device
            await self._save_pending()
            await self._save_paired()

            return device

    async def reject_pairing(self, request_id: str) -> bool:
        """
        拒绝配对请求。

        Args:
            request_id: 请求 ID

        Returns:
            是否成功
        """
        async with self._lock:
            data = await self._load()

            if request_id not in data.pending:
                return False

            del data.pending[request_id]
            await self._save_pending()

            return True

    async def verify_token(self, params: TokenVerifyParams) -> TokenVerifyResult:
        """
        验证设备令牌。

        Args:
            params: 验证参数

        Returns:
            验证结果
        """
        async with self._lock:
            data = await self._load()

            device = data.paired.get(params.device_id)
            if not device:
                return TokenVerifyResult(valid=False, error="Device not found")

            # 查找令牌
            token_info: DeviceAuthToken | None = None
            for ti in device.tokens.values():
                if ti.token == params.token:
                    token_info = ti
                    break

            if not token_info:
                return TokenVerifyResult(valid=False, error="Token not found")

            # 检查是否已撤销
            if token_info.revoked_at_ms:
                return TokenVerifyResult(valid=False, error="Token revoked")

            # 检查作用域
            if params.required_scopes:
                allowed_scopes = set(token_info.scopes)
                for scope in params.required_scopes:
                    if scope not in allowed_scopes:
                        return TokenVerifyResult(
                            valid=False,
                            error=f"Missing scope: {scope}",
                        )

            # 更新最后使用时间
            token_info.last_used_at_ms = _get_ms_timestamp()
            await self._save_paired()

            return TokenVerifyResult(
                valid=True,
                device=device,
                token_info=token_info,
            )

    async def rotate_token(
        self,
        device_id: str,
        token_id: str = "default",
    ) -> DeviceAuthToken | None:
        """
        轮换设备令牌。

        Args:
            device_id: 设备 ID
            token_id: 令牌 ID

        Returns:
            新令牌或 None
        """
        async with self._lock:
            data = await self._load()

            device = data.paired.get(device_id)
            if not device:
                return None

            old_token = device.tokens.get(token_id)
            if not old_token:
                return None

            now = _get_ms_timestamp()

            # 创建新令牌
            new_token = DeviceAuthToken(
                token=_generate_token(),
                role=old_token.role,
                scopes=old_token.scopes,
                created_at_ms=now,
                rotated_at_ms=now,
            )

            device.tokens[token_id] = new_token
            await self._save_paired()

            return new_token

    async def revoke_token(self, device_id: str, token_id: str = "default") -> bool:
        """
        撤销设备令牌。

        Args:
            device_id: 设备 ID
            token_id: 令牌 ID

        Returns:
            是否成功
        """
        async with self._lock:
            data = await self._load()

            device = data.paired.get(device_id)
            if not device:
                return False

            token = device.tokens.get(token_id)
            if not token:
                return False

            token.revoked_at_ms = _get_ms_timestamp()
            await self._save_paired()

            return True


# 全局实例
device_pairing_manager = DevicePairingManager()


# 便捷函数
async def list_device_pairing() -> tuple[list[DevicePairingPendingRequest], list[PairedDevice]]:
    """列出所有待处理请求和已配对设备。"""
    return await device_pairing_manager.list_pairing()


async def get_paired_device(device_id: str) -> PairedDevice | None:
    """获取已配对设备。"""
    return await device_pairing_manager.get_paired_device(device_id)


async def request_device_pairing(
    device_id: str,
    public_key: str,
    **kwargs,
) -> DevicePairingPendingRequest:
    """创建配对请求。"""
    return await device_pairing_manager.request_pairing(device_id, public_key, **kwargs)


async def approve_device_pairing(request_id: str) -> PairedDevice | None:
    """批准配对请求。"""
    return await device_pairing_manager.approve_pairing(request_id)


async def reject_device_pairing(request_id: str) -> bool:
    """拒绝配对请求。"""
    return await device_pairing_manager.reject_pairing(request_id)


async def verify_device_token(
    device_id: str,
    token: str,
    required_scopes: list[str] | None = None,
) -> TokenVerifyResult:
    """验证设备令牌。"""
    params = TokenVerifyParams(
        device_id=device_id,
        token=token,
        required_scopes=required_scopes or [],
    )
    return await device_pairing_manager.verify_token(params)
