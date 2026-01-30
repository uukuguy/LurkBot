"""System Presence.

分布式设备/节点状态跟踪，带 TTL 和 LRU 淘汰。

对标 MoltBot `src/infra/system-presence.ts`
"""

import platform
import re
import socket
from datetime import datetime, timedelta

from cachetools import TTLCache

from .types import SystemPresence, SystemPresenceUpdate

# TTL: 5 分钟
PRESENCE_TTL_SECONDS = 300

# 最大条目: 200（LRU by timestamp）
MAX_PRESENCE_ENTRIES = 200

__all__ = [
    "SystemPresence",
    "SystemPresenceUpdate",
    "PRESENCE_TTL_SECONDS",
    "MAX_PRESENCE_ENTRIES",
    "update_system_presence",
    "upsert_presence",
    "list_system_presence",
    "get_self_presence",
]


# 存在感缓存（TTL + LRU）
_presence_cache: TTLCache[str, SystemPresence] = TTLCache(
    maxsize=MAX_PRESENCE_ENTRIES,
    ttl=PRESENCE_TTL_SECONDS,
)

# 更新回调列表
_update_callbacks: list[callable] = []


def _parse_presence_text(text: str) -> dict[str, str | None]:
    """
    从文本中解析存在感信息。

    支持格式:
    - "host@ip v1.0.0"
    - "hostname (192.168.1.1)"
    - "device v2.0"
    """
    result: dict[str, str | None] = {
        "host": None,
        "ip": None,
        "version": None,
    }

    # 尝试匹配 host@ip 格式
    match = re.match(r"^([^@\s]+)@([\d.]+)", text)
    if match:
        result["host"] = match.group(1)
        result["ip"] = match.group(2)

    # 尝试匹配 host (ip) 格式
    if not result["host"]:
        match = re.match(r"^([^\s(]+)\s*\(([\d.]+)\)", text)
        if match:
            result["host"] = match.group(1)
            result["ip"] = match.group(2)

    # 尝试匹配版本号
    version_match = re.search(r"v([\d.]+)", text)
    if version_match:
        result["version"] = version_match.group(1)

    return result


def _merge_string_lists(existing: list[str], new: list[str]) -> list[str]:
    """合并字符串列表，去重。"""
    seen = set(existing)
    result = list(existing)
    for item in new:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def _compute_changes(
    previous: SystemPresence | None,
    next_presence: SystemPresence,
) -> tuple[dict[str, object], list[str]]:
    """计算两个存在感之间的变化。"""
    changes: dict[str, object] = {}
    changed_keys: list[str] = []

    if previous is None:
        # 全部都是新的
        for key in [
            "host", "ip", "version", "platform", "device_family",
            "model_identifier", "last_input_seconds", "mode", "reason",
            "device_id", "instance_id", "roles", "scopes", "text",
        ]:
            value = getattr(next_presence, key)
            if value is not None and value != [] and value != "":
                changes[key] = value
                changed_keys.append(key)
    else:
        # 比较差异
        for key in [
            "host", "ip", "version", "platform", "device_family",
            "model_identifier", "last_input_seconds", "mode", "reason",
            "device_id", "instance_id", "roles", "scopes", "text",
        ]:
            old_value = getattr(previous, key)
            new_value = getattr(next_presence, key)
            if old_value != new_value:
                changes[key] = new_value
                changed_keys.append(key)

    return changes, changed_keys


def update_system_presence(
    key: str,
    presence: SystemPresence,
    *,
    notify: bool = True,
) -> SystemPresenceUpdate | None:
    """
    更新节点存在感。

    Args:
        key: 节点标识符
        presence: 存在感数据
        notify: 是否触发更新回调

    Returns:
        更新事件（如果有变化）
    """
    previous = _presence_cache.get(key)

    # 如果有文本但没有解析的字段，尝试解析
    if presence.text and not presence.host:
        parsed = _parse_presence_text(presence.text)
        if parsed["host"]:
            presence.host = parsed["host"]
        if parsed["ip"]:
            presence.ip = parsed["ip"]
        if parsed["version"]:
            presence.version = parsed["version"]

    # 更新时间戳
    presence.ts = datetime.now()

    # 计算变化
    changes, changed_keys = _compute_changes(previous, presence)

    # 存入缓存
    _presence_cache[key] = presence

    # 如果有变化，创建更新事件
    if changed_keys:
        update = SystemPresenceUpdate(
            key=key,
            previous=previous,
            next=presence,
            changes=changes,
            changed_keys=changed_keys,
        )

        # 触发回调
        if notify:
            for callback in _update_callbacks:
                try:
                    callback(update)
                except Exception:
                    pass

        return update

    return None


def upsert_presence(key: str, presence: SystemPresence) -> SystemPresenceUpdate | None:
    """
    合并更新节点存在感。

    与 update_system_presence 不同，此函数会合并 roles 和 scopes。

    Args:
        key: 节点标识符
        presence: 存在感数据

    Returns:
        更新事件（如果有变化）
    """
    existing = _presence_cache.get(key)

    if existing:
        # 合并 roles 和 scopes
        if presence.roles:
            presence.roles = _merge_string_lists(existing.roles, presence.roles)
        else:
            presence.roles = existing.roles

        if presence.scopes:
            presence.scopes = _merge_string_lists(existing.scopes, presence.scopes)
        else:
            presence.scopes = existing.scopes

        # 保留现有值（如果新值为空）
        if not presence.host and existing.host:
            presence.host = existing.host
        if not presence.ip and existing.ip:
            presence.ip = existing.ip
        if not presence.version and existing.version:
            presence.version = existing.version
        if not presence.platform and existing.platform:
            presence.platform = existing.platform
        if not presence.device_family and existing.device_family:
            presence.device_family = existing.device_family
        if not presence.model_identifier and existing.model_identifier:
            presence.model_identifier = existing.model_identifier
        if not presence.mode and existing.mode:
            presence.mode = existing.mode
        if not presence.reason and existing.reason:
            presence.reason = existing.reason
        if not presence.device_id and existing.device_id:
            presence.device_id = existing.device_id
        if not presence.instance_id and existing.instance_id:
            presence.instance_id = existing.instance_id

    return update_system_presence(key, presence)


def list_system_presence() -> dict[str, SystemPresence]:
    """
    列出所有在线节点。

    自动清理过期条目（由 TTLCache 处理）。

    Returns:
        节点 ID 到存在感的映射
    """
    # TTLCache 会自动清理过期条目
    return dict(_presence_cache)


def get_self_presence() -> SystemPresence:
    """
    获取当前节点的存在感。

    Returns:
        当前节点的存在感
    """
    hostname = socket.gethostname()
    try:
        ip = socket.gethostbyname(hostname)
    except socket.gaierror:
        ip = "127.0.0.1"

    return SystemPresence(
        host=hostname,
        ip=ip,
        platform=platform.system().lower(),
        device_family=platform.machine(),
        model_identifier=platform.node(),
        reason="self",
        text=f"{hostname}@{ip}",
    )


def register_update_callback(callback: callable) -> callable:
    """
    注册存在感更新回调。

    Args:
        callback: 回调函数，接收 SystemPresenceUpdate 参数

    Returns:
        取消注册的函数
    """
    _update_callbacks.append(callback)

    def unregister():
        if callback in _update_callbacks:
            _update_callbacks.remove(callback)

    return unregister


def clear_presence_cache() -> None:
    """清空存在感缓存（用于测试）。"""
    _presence_cache.clear()


# 初始化自身存在感
def _init_self_presence() -> None:
    """初始化自身存在感。"""
    self_presence = get_self_presence()
    update_system_presence("self", self_presence, notify=False)


# 模块加载时初始化
_init_self_presence()
