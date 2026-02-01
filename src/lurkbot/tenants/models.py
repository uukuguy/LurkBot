"""多租户数据模型

定义租户相关的数据结构，包括租户实体、配额、配置等。
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ============================================================================
# 租户状态和级别
# ============================================================================


class TenantStatus(str, Enum):
    """租户状态"""

    ACTIVE = "active"  # 正常
    SUSPENDED = "suspended"  # 暂停
    TRIAL = "trial"  # 试用
    EXPIRED = "expired"  # 过期
    DELETED = "deleted"  # 已删除


class TenantTier(str, Enum):
    """租户套餐级别"""

    FREE = "free"  # 免费版
    BASIC = "basic"  # 基础版
    PROFESSIONAL = "professional"  # 专业版
    ENTERPRISE = "enterprise"  # 企业版


# ============================================================================
# 租户配额
# ============================================================================


class TenantQuota(BaseModel):
    """租户配额

    定义租户可使用的资源限制。
    """

    # 代理限制
    max_agents: int = Field(default=5, description="最大代理数")
    max_agents_per_channel: int = Field(default=2, description="每渠道最大代理数")

    # 会话限制
    max_sessions: int = Field(default=100, description="最大并发会话数")
    max_session_history: int = Field(default=1000, description="最大会话历史数")

    # 插件限制
    max_plugins: int = Field(default=10, description="最大插件数")
    max_custom_tools: int = Field(default=20, description="最大自定义工具数")

    # Token 限制
    max_tokens_per_day: int = Field(default=100000, description="每日 token 限制")
    max_tokens_per_request: int = Field(default=4096, description="单次请求最大 token")

    # API 限制
    max_api_calls_per_minute: int = Field(default=60, description="每分钟 API 调用限制")
    max_api_calls_per_day: int = Field(default=10000, description="每日 API 调用限制")

    # 存储限制
    storage_quota_mb: int = Field(default=500, description="存储配额 (MB)")
    max_file_size_mb: int = Field(default=10, description="单文件最大大小 (MB)")

    # 并发限制
    max_concurrent_requests: int = Field(default=5, description="最大并发请求数")


# ============================================================================
# 预定义配额
# ============================================================================


QUOTA_FREE = TenantQuota(
    max_agents=1,
    max_agents_per_channel=1,
    max_sessions=10,
    max_session_history=100,
    max_plugins=3,
    max_custom_tools=5,
    max_tokens_per_day=10000,
    max_tokens_per_request=2048,
    max_api_calls_per_minute=10,
    max_api_calls_per_day=1000,
    storage_quota_mb=100,
    max_file_size_mb=5,
    max_concurrent_requests=2,
)

QUOTA_BASIC = TenantQuota(
    max_agents=3,
    max_agents_per_channel=2,
    max_sessions=50,
    max_session_history=500,
    max_plugins=10,
    max_custom_tools=20,
    max_tokens_per_day=50000,
    max_tokens_per_request=4096,
    max_api_calls_per_minute=30,
    max_api_calls_per_day=5000,
    storage_quota_mb=500,
    max_file_size_mb=10,
    max_concurrent_requests=5,
)

QUOTA_PROFESSIONAL = TenantQuota(
    max_agents=10,
    max_agents_per_channel=5,
    max_sessions=200,
    max_session_history=2000,
    max_plugins=50,
    max_custom_tools=100,
    max_tokens_per_day=500000,
    max_tokens_per_request=8192,
    max_api_calls_per_minute=100,
    max_api_calls_per_day=50000,
    storage_quota_mb=2000,
    max_file_size_mb=50,
    max_concurrent_requests=20,
)

QUOTA_ENTERPRISE = TenantQuota(
    max_agents=100,
    max_agents_per_channel=50,
    max_sessions=1000,
    max_session_history=10000,
    max_plugins=200,
    max_custom_tools=500,
    max_tokens_per_day=5000000,
    max_tokens_per_request=32768,
    max_api_calls_per_minute=1000,
    max_api_calls_per_day=500000,
    storage_quota_mb=10000,
    max_file_size_mb=100,
    max_concurrent_requests=100,
)

# 配额映射
TIER_QUOTAS: dict[TenantTier, TenantQuota] = {
    TenantTier.FREE: QUOTA_FREE,
    TenantTier.BASIC: QUOTA_BASIC,
    TenantTier.PROFESSIONAL: QUOTA_PROFESSIONAL,
    TenantTier.ENTERPRISE: QUOTA_ENTERPRISE,
}


def get_tier_quota(tier: TenantTier) -> TenantQuota:
    """获取套餐默认配额

    Args:
        tier: 套餐级别

    Returns:
        配额配置
    """
    return TIER_QUOTAS.get(tier, QUOTA_FREE).model_copy()


# ============================================================================
# 租户配置
# ============================================================================


class TenantConfig(BaseModel):
    """租户级配置

    定义租户的个性化配置。
    """

    # 模型配置
    allowed_models: list[str] = Field(
        default_factory=lambda: ["deepseek:deepseek-chat", "qwen:qwen-plus"],
        description="允许使用的模型列表",
    )
    default_model: str = Field(default="deepseek:deepseek-chat", description="默认模型")
    default_max_tokens: int = Field(default=4096, description="默认最大 token")
    default_temperature: float = Field(default=0.7, description="默认温度")

    # 渠道配置
    allowed_channels: list[str] = Field(
        default_factory=lambda: ["dingtalk", "feishu", "wework"],
        description="允许的渠道列表",
    )
    default_channel: str = Field(default="dingtalk", description="默认渠道")

    # 系统提示
    default_system_prompt: str = Field(
        default="You are a helpful assistant.",
        description="默认系统提示",
    )
    custom_system_prompts: dict[str, str] = Field(
        default_factory=dict,
        description="自定义系统提示（按场景）",
    )

    # 工具配置
    enabled_tools: list[str] = Field(
        default_factory=list,
        description="启用的工具列表",
    )
    disabled_tools: list[str] = Field(
        default_factory=list,
        description="禁用的工具列表",
    )
    custom_tools: list[str] = Field(
        default_factory=list,
        description="自定义工具列表",
    )

    # 功能开关
    feature_flags: dict[str, bool] = Field(
        default_factory=lambda: {
            "enable_plugins": True,
            "enable_tools": True,
            "enable_memory": True,
            "enable_auto_reply": False,
            "enable_voice": False,
            "enable_image": True,
        },
        description="功能开关",
    )

    # 安全配置
    security_settings: dict[str, Any] = Field(
        default_factory=lambda: {
            "enable_audit_log": True,
            "enable_sensitive_filter": True,
            "max_message_length": 10000,
        },
        description="安全设置",
    )

    # 自定义配置
    custom_config: dict[str, Any] = Field(
        default_factory=dict,
        description="自定义配置",
    )


# ============================================================================
# 租户使用统计
# ============================================================================


class TenantUsage(BaseModel):
    """租户使用统计"""

    tenant_id: str = Field(description="租户 ID")
    period: str = Field(description="统计周期 (daily/weekly/monthly)")
    period_start: datetime = Field(description="周期开始时间")
    period_end: datetime = Field(description="周期结束时间")

    # Token 使用
    input_tokens: int = Field(default=0, description="输入 token 数")
    output_tokens: int = Field(default=0, description="输出 token 数")
    total_tokens: int = Field(default=0, description="总 token 数")

    # API 调用
    api_calls: int = Field(default=0, description="API 调用次数")
    successful_calls: int = Field(default=0, description="成功调用次数")
    failed_calls: int = Field(default=0, description="失败调用次数")

    # 会话统计
    sessions_created: int = Field(default=0, description="创建会话数")
    active_sessions: int = Field(default=0, description="活跃会话数")
    messages_sent: int = Field(default=0, description="发送消息数")

    # 存储使用
    storage_used_mb: float = Field(default=0.0, description="存储使用量 (MB)")

    # 费用估算
    estimated_cost: float = Field(default=0.0, description="预估费用")


# ============================================================================
# 租户实体
# ============================================================================


class Tenant(BaseModel):
    """租户实体

    代表一个租户（组织/团队）。
    """

    # 基本信息
    id: str = Field(description="租户唯一标识")
    name: str = Field(description="租户名称（唯一）")
    display_name: str = Field(description="显示名称")
    description: str = Field(default="", description="租户描述")

    # 状态和级别
    status: TenantStatus = Field(default=TenantStatus.ACTIVE, description="租户状态")
    tier: TenantTier = Field(default=TenantTier.FREE, description="套餐级别")

    # 时间戳
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")
    expires_at: datetime | None = Field(default=None, description="过期时间")
    trial_ends_at: datetime | None = Field(default=None, description="试用结束时间")

    # 配额和配置
    quota: TenantQuota = Field(default_factory=TenantQuota, description="资源配额")
    config: TenantConfig = Field(default_factory=TenantConfig, description="租户配置")

    # 联系信息
    owner_id: str | None = Field(default=None, description="所有者用户 ID")
    admin_ids: list[str] = Field(default_factory=list, description="管理员用户 ID 列表")
    contact_email: str | None = Field(default=None, description="联系邮箱")

    # 元数据
    metadata: dict[str, Any] = Field(default_factory=dict, description="自定义元数据")
    tags: list[str] = Field(default_factory=list, description="标签")

    def is_active(self) -> bool:
        """检查租户是否活跃"""
        return self.status == TenantStatus.ACTIVE

    def is_expired(self) -> bool:
        """检查租户是否过期"""
        if self.status == TenantStatus.EXPIRED:
            return True
        if self.expires_at and datetime.now() > self.expires_at:
            return True
        return False

    def is_trial(self) -> bool:
        """检查是否试用期"""
        return self.status == TenantStatus.TRIAL

    def is_trial_expired(self) -> bool:
        """检查试用期是否过期"""
        if not self.is_trial():
            return False
        if self.trial_ends_at and datetime.now() > self.trial_ends_at:
            return True
        return False

    def can_use_model(self, model: str) -> bool:
        """检查是否可以使用指定模型"""
        return model in self.config.allowed_models

    def can_use_channel(self, channel: str) -> bool:
        """检查是否可以使用指定渠道"""
        return channel in self.config.allowed_channels

    def has_feature(self, feature: str) -> bool:
        """检查是否启用指定功能"""
        return self.config.feature_flags.get(feature, False)


# ============================================================================
# 租户事件
# ============================================================================


class TenantEventType(str, Enum):
    """租户事件类型"""

    CREATED = "created"  # 租户创建
    UPDATED = "updated"  # 租户更新
    DELETED = "deleted"  # 租户删除
    SUSPENDED = "suspended"  # 租户暂停
    ACTIVATED = "activated"  # 租户激活
    EXPIRED = "expired"  # 租户过期
    TIER_CHANGED = "tier_changed"  # 套餐变更
    QUOTA_EXCEEDED = "quota_exceeded"  # 配额超限
    CONFIG_UPDATED = "config_updated"  # 配置更新


class TenantEvent(BaseModel):
    """租户事件"""

    tenant_id: str = Field(description="租户 ID")
    event_type: TenantEventType = Field(description="事件类型")
    timestamp: datetime = Field(default_factory=datetime.now, description="事件时间")
    actor_id: str | None = Field(default=None, description="操作者 ID")
    old_value: Any = Field(default=None, description="旧值")
    new_value: Any = Field(default=None, description="新值")
    message: str = Field(default="", description="事件描述")
    metadata: dict[str, Any] = Field(default_factory=dict, description="事件元数据")
