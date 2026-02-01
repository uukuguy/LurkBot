"""租户数据模型测试"""

from datetime import datetime, timedelta

import pytest

from lurkbot.tenants import (
    QUOTA_BASIC,
    QUOTA_ENTERPRISE,
    QUOTA_FREE,
    QUOTA_PROFESSIONAL,
    TIER_QUOTAS,
    Tenant,
    TenantConfig,
    TenantEvent,
    TenantEventType,
    TenantQuota,
    TenantStatus,
    TenantTier,
    TenantUsage,
    get_tier_quota,
)


# ============================================================================
# TenantStatus 测试
# ============================================================================


class TestTenantStatus:
    """租户状态枚举测试"""

    def test_status_values(self):
        """测试状态值"""
        assert TenantStatus.ACTIVE == "active"
        assert TenantStatus.SUSPENDED == "suspended"
        assert TenantStatus.TRIAL == "trial"
        assert TenantStatus.EXPIRED == "expired"
        assert TenantStatus.DELETED == "deleted"

    def test_status_count(self):
        """测试状态数量"""
        assert len(TenantStatus) == 5


# ============================================================================
# TenantTier 测试
# ============================================================================


class TestTenantTier:
    """租户套餐级别测试"""

    def test_tier_values(self):
        """测试套餐值"""
        assert TenantTier.FREE == "free"
        assert TenantTier.BASIC == "basic"
        assert TenantTier.PROFESSIONAL == "professional"
        assert TenantTier.ENTERPRISE == "enterprise"

    def test_tier_count(self):
        """测试套餐数量"""
        assert len(TenantTier) == 4


# ============================================================================
# TenantQuota 测试
# ============================================================================


class TestTenantQuota:
    """租户配额测试"""

    def test_default_quota(self):
        """测试默认配额"""
        quota = TenantQuota()
        assert quota.max_agents == 5
        assert quota.max_sessions == 100
        assert quota.max_plugins == 10
        assert quota.max_tokens_per_day == 100000

    def test_custom_quota(self):
        """测试自定义配额"""
        quota = TenantQuota(
            max_agents=20,
            max_sessions=500,
            max_tokens_per_day=1000000,
        )
        assert quota.max_agents == 20
        assert quota.max_sessions == 500
        assert quota.max_tokens_per_day == 1000000

    def test_predefined_quotas(self):
        """测试预定义配额"""
        # FREE
        assert QUOTA_FREE.max_agents == 1
        assert QUOTA_FREE.max_tokens_per_day == 10000

        # BASIC
        assert QUOTA_BASIC.max_agents == 3
        assert QUOTA_BASIC.max_tokens_per_day == 50000

        # PROFESSIONAL
        assert QUOTA_PROFESSIONAL.max_agents == 10
        assert QUOTA_PROFESSIONAL.max_tokens_per_day == 500000

        # ENTERPRISE
        assert QUOTA_ENTERPRISE.max_agents == 100
        assert QUOTA_ENTERPRISE.max_tokens_per_day == 5000000

    def test_tier_quotas_mapping(self):
        """测试套餐配额映射"""
        assert TIER_QUOTAS[TenantTier.FREE] == QUOTA_FREE
        assert TIER_QUOTAS[TenantTier.BASIC] == QUOTA_BASIC
        assert TIER_QUOTAS[TenantTier.PROFESSIONAL] == QUOTA_PROFESSIONAL
        assert TIER_QUOTAS[TenantTier.ENTERPRISE] == QUOTA_ENTERPRISE

    def test_get_tier_quota(self):
        """测试获取套餐配额"""
        quota = get_tier_quota(TenantTier.PROFESSIONAL)
        assert quota.max_agents == QUOTA_PROFESSIONAL.max_agents
        # 确保返回的是副本
        quota.max_agents = 999
        assert QUOTA_PROFESSIONAL.max_agents == 10


# ============================================================================
# TenantConfig 测试
# ============================================================================


class TestTenantConfig:
    """租户配置测试"""

    def test_default_config(self):
        """测试默认配置"""
        config = TenantConfig()
        assert "deepseek:deepseek-chat" in config.allowed_models
        assert config.default_model == "deepseek:deepseek-chat"
        assert config.default_temperature == 0.7
        assert "dingtalk" in config.allowed_channels

    def test_feature_flags(self):
        """测试功能开关"""
        config = TenantConfig()
        assert config.feature_flags["enable_plugins"] is True
        assert config.feature_flags["enable_tools"] is True
        assert config.feature_flags["enable_auto_reply"] is False

    def test_security_settings(self):
        """测试安全设置"""
        config = TenantConfig()
        assert config.security_settings["enable_audit_log"] is True
        assert config.security_settings["enable_sensitive_filter"] is True
        assert config.security_settings["max_message_length"] == 10000

    def test_custom_config(self):
        """测试自定义配置"""
        config = TenantConfig(
            allowed_models=["gpt-4", "claude-3"],
            default_model="gpt-4",
            custom_config={"key": "value"},
        )
        assert config.allowed_models == ["gpt-4", "claude-3"]
        assert config.default_model == "gpt-4"
        assert config.custom_config["key"] == "value"


# ============================================================================
# TenantUsage 测试
# ============================================================================


class TestTenantUsage:
    """租户使用统计测试"""

    def test_create_usage(self):
        """测试创建使用统计"""
        now = datetime.now()
        usage = TenantUsage(
            tenant_id="tenant-1",
            period="daily",
            period_start=now,
            period_end=now + timedelta(days=1),
            input_tokens=1000,
            output_tokens=500,
            total_tokens=1500,
            api_calls=100,
        )
        assert usage.tenant_id == "tenant-1"
        assert usage.period == "daily"
        assert usage.total_tokens == 1500
        assert usage.api_calls == 100

    def test_default_values(self):
        """测试默认值"""
        now = datetime.now()
        usage = TenantUsage(
            tenant_id="tenant-1",
            period="daily",
            period_start=now,
            period_end=now + timedelta(days=1),
        )
        assert usage.input_tokens == 0
        assert usage.output_tokens == 0
        assert usage.total_tokens == 0
        assert usage.api_calls == 0
        assert usage.storage_used_mb == 0.0
        assert usage.estimated_cost == 0.0


# ============================================================================
# Tenant 测试
# ============================================================================


class TestTenant:
    """租户实体测试"""

    def test_create_tenant(self):
        """测试创建租户"""
        tenant = Tenant(
            id="tenant-1",
            name="test-tenant",
            display_name="Test Tenant",
        )
        assert tenant.id == "tenant-1"
        assert tenant.name == "test-tenant"
        assert tenant.display_name == "Test Tenant"
        assert tenant.status == TenantStatus.ACTIVE
        assert tenant.tier == TenantTier.FREE

    def test_tenant_with_quota_and_config(self):
        """测试带配额和配置的租户"""
        quota = TenantQuota(max_agents=20)
        config = TenantConfig(default_model="gpt-4")
        tenant = Tenant(
            id="tenant-1",
            name="test-tenant",
            display_name="Test Tenant",
            quota=quota,
            config=config,
        )
        assert tenant.quota.max_agents == 20
        assert tenant.config.default_model == "gpt-4"

    def test_is_active(self):
        """测试活跃状态检查"""
        tenant = Tenant(
            id="tenant-1",
            name="test-tenant",
            display_name="Test Tenant",
            status=TenantStatus.ACTIVE,
        )
        assert tenant.is_active() is True

        tenant.status = TenantStatus.SUSPENDED
        assert tenant.is_active() is False

    def test_is_expired(self):
        """测试过期状态检查"""
        # 状态为 EXPIRED
        tenant = Tenant(
            id="tenant-1",
            name="test-tenant",
            display_name="Test Tenant",
            status=TenantStatus.EXPIRED,
        )
        assert tenant.is_expired() is True

        # 过期时间已过
        tenant = Tenant(
            id="tenant-2",
            name="test-tenant-2",
            display_name="Test Tenant 2",
            status=TenantStatus.ACTIVE,
            expires_at=datetime.now() - timedelta(days=1),
        )
        assert tenant.is_expired() is True

        # 未过期
        tenant = Tenant(
            id="tenant-3",
            name="test-tenant-3",
            display_name="Test Tenant 3",
            status=TenantStatus.ACTIVE,
            expires_at=datetime.now() + timedelta(days=30),
        )
        assert tenant.is_expired() is False

    def test_is_trial(self):
        """测试试用期检查"""
        tenant = Tenant(
            id="tenant-1",
            name="test-tenant",
            display_name="Test Tenant",
            status=TenantStatus.TRIAL,
        )
        assert tenant.is_trial() is True

        tenant.status = TenantStatus.ACTIVE
        assert tenant.is_trial() is False

    def test_is_trial_expired(self):
        """测试试用期过期检查"""
        # 试用期已过
        tenant = Tenant(
            id="tenant-1",
            name="test-tenant",
            display_name="Test Tenant",
            status=TenantStatus.TRIAL,
            trial_ends_at=datetime.now() - timedelta(days=1),
        )
        assert tenant.is_trial_expired() is True

        # 试用期未过
        tenant = Tenant(
            id="tenant-2",
            name="test-tenant-2",
            display_name="Test Tenant 2",
            status=TenantStatus.TRIAL,
            trial_ends_at=datetime.now() + timedelta(days=7),
        )
        assert tenant.is_trial_expired() is False

        # 非试用状态
        tenant = Tenant(
            id="tenant-3",
            name="test-tenant-3",
            display_name="Test Tenant 3",
            status=TenantStatus.ACTIVE,
        )
        assert tenant.is_trial_expired() is False

    def test_can_use_model(self):
        """测试模型使用权限检查"""
        tenant = Tenant(
            id="tenant-1",
            name="test-tenant",
            display_name="Test Tenant",
        )
        assert tenant.can_use_model("deepseek:deepseek-chat") is True
        assert tenant.can_use_model("unknown-model") is False

    def test_can_use_channel(self):
        """测试渠道使用权限检查"""
        tenant = Tenant(
            id="tenant-1",
            name="test-tenant",
            display_name="Test Tenant",
        )
        assert tenant.can_use_channel("dingtalk") is True
        assert tenant.can_use_channel("unknown-channel") is False

    def test_has_feature(self):
        """测试功能开关检查"""
        tenant = Tenant(
            id="tenant-1",
            name="test-tenant",
            display_name="Test Tenant",
        )
        assert tenant.has_feature("enable_plugins") is True
        assert tenant.has_feature("enable_auto_reply") is False
        assert tenant.has_feature("unknown_feature") is False


# ============================================================================
# TenantEvent 测试
# ============================================================================


class TestTenantEvent:
    """租户事件测试"""

    def test_event_types(self):
        """测试事件类型"""
        assert TenantEventType.CREATED == "created"
        assert TenantEventType.UPDATED == "updated"
        assert TenantEventType.DELETED == "deleted"
        assert TenantEventType.SUSPENDED == "suspended"
        assert TenantEventType.TIER_CHANGED == "tier_changed"
        assert TenantEventType.QUOTA_EXCEEDED == "quota_exceeded"

    def test_create_event(self):
        """测试创建事件"""
        event = TenantEvent(
            tenant_id="tenant-1",
            event_type=TenantEventType.CREATED,
            actor_id="user-1",
            message="租户创建成功",
        )
        assert event.tenant_id == "tenant-1"
        assert event.event_type == TenantEventType.CREATED
        assert event.actor_id == "user-1"
        assert event.message == "租户创建成功"

    def test_event_with_values(self):
        """测试带新旧值的事件"""
        event = TenantEvent(
            tenant_id="tenant-1",
            event_type=TenantEventType.TIER_CHANGED,
            old_value=TenantTier.FREE,
            new_value=TenantTier.PROFESSIONAL,
            message="套餐升级",
        )
        assert event.old_value == TenantTier.FREE
        assert event.new_value == TenantTier.PROFESSIONAL

    def test_event_timestamp(self):
        """测试事件时间戳"""
        before = datetime.now()
        event = TenantEvent(
            tenant_id="tenant-1",
            event_type=TenantEventType.CREATED,
        )
        after = datetime.now()
        assert before <= event.timestamp <= after
