"""
Auth Profile System - 凭据管理和轮换

对标 MoltBot auth/profiles.ts

功能:
- 凭据存储 (API keys, tokens, OAuth)
- 使用统计和冷却算法
- Profile 优先级排序和轮换
- JSONL 持久化
"""

from dataclasses import dataclass, field, asdict
from typing import Literal
from datetime import datetime
from pathlib import Path
import json
from loguru import logger


@dataclass
class AuthCredential:
    """
    认证凭据

    对标 MoltBot AuthProfileCredential
    """

    type: Literal["api_key", "token", "oauth"]
    key: str | None = None  # for api_key
    token: str | None = None  # for token
    expires: int | None = None  # for token (timestamp in ms)
    access: str | None = None  # for oauth
    refresh: str | None = None  # for oauth


@dataclass
class ProfileUsageStats:
    """
    使用统计

    对标 MoltBot ProfileUsageStats
    """

    last_used: int | None = None  # timestamp in ms
    error_count: int = 0
    cooldown_until: int | None = None  # timestamp in ms
    disabled_until: int | None = None  # timestamp in ms
    disabled_reason: str | None = None
    failure_counts: dict[str, int] = field(default_factory=dict)
    # failure_counts: { "auth": 2, "rate_limit": 1, "timeout": 0, ... }


@dataclass
class AuthProfileStore:
    """
    Profile 存储

    对标 MoltBot AuthProfileStore
    """

    profiles: dict[str, AuthCredential] = field(default_factory=dict)
    usage_stats: dict[str, ProfileUsageStats] = field(default_factory=dict)
    order: dict[str, list[str]] = field(default_factory=dict)
    # order: { "anthropic": ["profile1", "profile2"], "openai": [...] }


# ============================================================================
# Cooldown Algorithm
# ============================================================================


def calculate_cooldown_ms(error_count: int) -> int:
    """
    计算冷却时间

    对标 MoltBot calculateAuthProfileCooldownMs()

    公式: cooldown = min(1 hour, 60 sec × 5^(errorCount-1))
    - errorCount=1 → 60s (60000ms)
    - errorCount=2 → 300s (300000ms, 5m)
    - errorCount=3 → 1500s (1500000ms, 25m)
    - errorCount=4+ → 3600s (3600000ms, 1h) 上限
    """
    base = 60 * 1000  # 60 seconds in ms
    factor = pow(5, max(0, error_count - 1))
    return min(3600 * 1000, int(base * factor))  # max 1 hour


# ============================================================================
# Profile Order Resolution
# ============================================================================


def resolve_auth_profile_order(
    store: AuthProfileStore,
    provider: str,
    preferred_profile: str | None = None,
) -> list[str]:
    """
    解析 Profile 顺序

    对标 MoltBot resolveAuthProfileOrder()

    算法:
    1. 规范化提供商名称
    2. 确定基础顺序
    3. 过滤有效配置文件
    4. 分离：可用 vs 冷却中
    5. 可用的按 lastUsed 排序（最旧优先 = 轮换）
    6. 冷却中的按冷却结束时间排序
    7. 优先指定的 Profile
    """
    normalized_provider = normalize_provider_id(provider)
    now = int(datetime.now().timestamp() * 1000)

    # 确定基础顺序
    base_order = store.order.get(normalized_provider) or [
        p for p in store.profiles.keys() if match_provider(p, normalized_provider)
    ]

    # 过滤有效配置文件
    valid_profiles = [
        p
        for p in base_order
        if p in store.profiles and is_valid_credential(store.profiles[p])
    ]

    # 分离可用和冷却中的
    available: list[str] = []
    in_cooldown: list[str] = []

    for p in valid_profiles:
        stats = store.usage_stats.get(p, ProfileUsageStats())
        # 检查是否在冷却中
        if stats.cooldown_until and stats.cooldown_until > now:
            in_cooldown.append(p)
        # 检查是否被禁用
        elif stats.disabled_until and stats.disabled_until > now:
            continue  # 跳过被禁用的
        else:
            available.append(p)

    # 按 lastUsed 排序（最旧优先 = 轮换）
    available.sort(
        key=lambda p: store.usage_stats.get(p, ProfileUsageStats()).last_used or 0
    )

    # 按冷却结束时间排序
    in_cooldown.sort(
        key=lambda p: store.usage_stats.get(p, ProfileUsageStats()).cooldown_until or 0
    )

    # 合并：可用的在前，冷却的在后
    result = available + in_cooldown

    # 优先指定的 Profile（如果在列表中）
    if preferred_profile and preferred_profile in result:
        result = [preferred_profile] + [p for p in result if p != preferred_profile]

    return result


# ============================================================================
# Profile State Management
# ============================================================================


def mark_profile_failure(
    store: AuthProfileStore,
    profile_id: str,
    reason: str | None = None,
):
    """
    标记 Profile 失败

    对标 MoltBot markAuthProfileFailure()
    """
    if profile_id not in store.usage_stats:
        store.usage_stats[profile_id] = ProfileUsageStats()

    stats = store.usage_stats[profile_id]
    stats.error_count += 1
    stats.cooldown_until = int(datetime.now().timestamp() * 1000) + calculate_cooldown_ms(
        stats.error_count
    )

    if reason:
        stats.failure_counts[reason] = stats.failure_counts.get(reason, 0) + 1

    logger.debug(
        f"Profile {profile_id} failed (count={stats.error_count}, "
        f"cooldown_until={stats.cooldown_until}, reason={reason})"
    )


def mark_profile_success(
    store: AuthProfileStore,
    profile_id: str,
):
    """
    标记 Profile 成功

    重置错误计数和冷却时间
    """
    if profile_id not in store.usage_stats:
        store.usage_stats[profile_id] = ProfileUsageStats()

    stats = store.usage_stats[profile_id]
    stats.last_used = int(datetime.now().timestamp() * 1000)
    stats.error_count = 0
    stats.cooldown_until = None

    logger.debug(f"Profile {profile_id} succeeded (last_used={stats.last_used})")


# ============================================================================
# Rotation Logic
# ============================================================================


def rotate_auth_profile(
    store: AuthProfileStore,
    provider: str,
    current_profile: str | None = None,
) -> str | None:
    """
    轮换到下一个可用的 Profile

    对标 MoltBot rotateAuthProfile()

    返回:
    - 下一个可用的 Profile ID
    - None 如果没有可用的
    """
    order = resolve_auth_profile_order(store, provider)

    if not order:
        logger.warning(f"No profiles available for provider {provider}")
        return None

    # 如果当前 Profile 已知，跳到下一个
    if current_profile and current_profile in order:
        current_idx = order.index(current_profile)
        # 循环到下一个（如果是最后一个，回到第一个）
        next_idx = (current_idx + 1) % len(order)
        next_profile = order[next_idx]
        logger.info(f"Rotating from {current_profile} to {next_profile}")
        return next_profile

    # 否则返回第一个
    first_profile = order[0]
    logger.info(f"Using first profile: {first_profile}")
    return first_profile


# ============================================================================
# Helper Functions
# ============================================================================


def normalize_provider_id(provider: str) -> str:
    """
    规范化提供商 ID

    例如: "anthropic:claude-3-5-sonnet" → "anthropic"
    """
    return provider.lower().split(":")[0].split("/")[0]


def match_provider(profile_id: str, provider: str) -> bool:
    """
    检查 Profile 是否匹配提供商

    例如: match_provider("anthropic-main", "anthropic") → True
    """
    return profile_id.lower().startswith(provider.lower())


def is_valid_credential(cred: AuthCredential) -> bool:
    """
    检查凭据是否有效

    - api_key: 必须有 key
    - token: 必须有 token 且未过期
    - oauth: 必须有 access token
    """
    if cred.type == "api_key":
        return bool(cred.key)
    elif cred.type == "token":
        if not cred.token:
            return False
        # 检查过期时间
        if cred.expires and cred.expires < datetime.now().timestamp() * 1000:
            return False
        return True
    elif cred.type == "oauth":
        return bool(cred.access)
    return False


# ============================================================================
# Persistence (JSONL)
# ============================================================================


def load_auth_profiles(file_path: str | Path) -> AuthProfileStore:
    """
    从 JSONL 文件加载 Auth Profiles

    格式: 每行一个 JSON 对象，包含:
    - profile_id: str
    - credential: AuthCredential
    - stats: ProfileUsageStats (可选)
    """
    path = Path(file_path)
    store = AuthProfileStore()

    if not path.exists():
        logger.debug(f"Auth profiles file not found: {path}")
        return store

    try:
        with path.open("r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue

                try:
                    data = json.loads(line)
                    profile_id = data.get("profile_id")
                    if not profile_id:
                        logger.warning(f"Line {line_num}: missing profile_id")
                        continue

                    # 解析凭据
                    cred_data = data.get("credential")
                    if cred_data:
                        store.profiles[profile_id] = AuthCredential(**cred_data)

                    # 解析统计
                    stats_data = data.get("stats")
                    if stats_data:
                        store.usage_stats[profile_id] = ProfileUsageStats(**stats_data)

                except json.JSONDecodeError as e:
                    logger.warning(f"Line {line_num}: invalid JSON - {e}")
                except Exception as e:
                    logger.warning(f"Line {line_num}: failed to parse - {e}")

        # 解析 order (如果有单独的 order 行)
        # 这里简化：从 profile_id 推断 provider
        for profile_id in store.profiles.keys():
            provider = normalize_provider_id(profile_id)
            if provider not in store.order:
                store.order[provider] = []
            if profile_id not in store.order[provider]:
                store.order[provider].append(profile_id)

        logger.info(f"Loaded {len(store.profiles)} auth profiles from {path}")

    except Exception as e:
        logger.error(f"Failed to load auth profiles from {path}: {e}")

    return store


def save_auth_profiles(store: AuthProfileStore, file_path: str | Path):
    """
    保存 Auth Profiles 到 JSONL 文件

    每行格式:
    {"profile_id": "...", "credential": {...}, "stats": {...}}
    """
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with path.open("w", encoding="utf-8") as f:
            for profile_id, credential in store.profiles.items():
                stats = store.usage_stats.get(profile_id)
                data = {
                    "profile_id": profile_id,
                    "credential": asdict(credential),
                    "stats": asdict(stats) if stats else None,
                }
                f.write(json.dumps(data, ensure_ascii=False) + "\n")

        logger.info(f"Saved {len(store.profiles)} auth profiles to {path}")

    except Exception as e:
        logger.error(f"Failed to save auth profiles to {path}: {e}")
        raise
