"""
DM Policy Configuration and Validation

对标 MoltBot src/security/dm_policy.ts
"""

from dataclasses import dataclass
from typing import Literal


@dataclass
class DMPolicyConfig:
    """
    DM 策略配置

    对标: MoltBot DMPolicyConfig
    """

    dm_scope: Literal["main", "per-channel-peer", "per-sender"]
    """会话隔离范围"""

    is_multi_user: bool
    """是否多用户环境"""


def load_dm_policy() -> DMPolicyConfig:
    """
    加载 DM 策略配置

    Returns:
        DM 策略配置

    对标: MoltBot loadDMPolicy()
    """
    try:
        from ..config import load_config

        config = load_config()

        # 获取 session 配置
        session_config = config.get("session", {})
        dm_scope = session_config.get("dmScope", "main")

        # 检测是否多用户环境
        # 这里简化处理，实际应该检查历史会话中的发件人数量
        channels_config = config.get("channels", {})
        is_multi_user = len(channels_config) > 1

        return DMPolicyConfig(
            dm_scope=dm_scope,
            is_multi_user=is_multi_user,
        )

    except Exception:
        # 默认配置
        return DMPolicyConfig(
            dm_scope="main",
            is_multi_user=False,
        )


def validate_dm_policy(policy: DMPolicyConfig) -> bool:
    """
    验证 DM 策略安全性

    Args:
        policy: DM 策略配置

    Returns:
        是否安全

    对标: MoltBot validateDMPolicy()
    """
    # 多用户环境应该使用隔离策略
    if policy.is_multi_user and policy.dm_scope == "main":
        return False

    return True


def get_recommended_dm_scope(is_multi_user: bool) -> str:
    """
    获取推荐的 DM 隔离范围

    Args:
        is_multi_user: 是否多用户环境

    Returns:
        推荐的 dm_scope 值

    对标: MoltBot getRecommendedDMScope()
    """
    if is_multi_user:
        return "per-channel-peer"
    return "main"
