"""租户统计数据服务

提供租户使用统计的聚合、分析和趋势计算功能。
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from loguru import logger
from pydantic import BaseModel, Field

from .models import (
    Tenant,
    TenantEvent,
    TenantEventType,
    TenantStatus,
    TenantTier,
    TenantUsage,
)
from .quota import QuotaCheckResult, QuotaManager, QuotaType
from .storage import TenantStorage


# ============================================================================
# 统计周期
# ============================================================================


class StatsPeriod(str, Enum):
    """统计周期"""

    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class TrendDirection(str, Enum):
    """趋势方向"""

    UP = "up"
    DOWN = "down"
    STABLE = "stable"


# ============================================================================
# 统计数据模型
# ============================================================================


class QuotaUsageStats(BaseModel):
    """配额使用统计"""

    quota_type: QuotaType = Field(description="配额类型")
    current: float = Field(default=0, description="当前使用量")
    limit: float = Field(default=0, description="配额限制")
    percentage: float = Field(default=0, description="使用百分比")
    status: str = Field(default="ok", description="状态 (ok/warning/exceeded)")
    trend: TrendDirection = Field(default=TrendDirection.STABLE, description="趋势")
    trend_percentage: float = Field(default=0, description="趋势变化百分比")


class TenantOverview(BaseModel):
    """租户概览"""

    tenant_id: str = Field(description="租户 ID")
    tenant_name: str = Field(description="租户名称")
    display_name: str = Field(description="显示名称")
    status: TenantStatus = Field(description="租户状态")
    tier: TenantTier = Field(description="套餐级别")
    created_at: datetime = Field(description="创建时间")

    # 实时统计
    active_sessions: int = Field(default=0, description="活跃会话数")
    concurrent_requests: int = Field(default=0, description="并发请求数")
    api_calls_today: int = Field(default=0, description="今日 API 调用数")
    tokens_today: int = Field(default=0, description="今日 Token 使用量")

    # 配额使用
    quota_usage: list[QuotaUsageStats] = Field(
        default_factory=list, description="配额使用统计"
    )

    # 活跃度
    activity_score: float = Field(default=0, description="活跃度评分 (0-100)")
    last_activity: datetime | None = Field(default=None, description="最后活动时间")


class UsageDataPoint(BaseModel):
    """使用量数据点"""

    timestamp: datetime = Field(description="时间戳")
    value: float = Field(description="值")


class UsageTrend(BaseModel):
    """使用量趋势"""

    quota_type: QuotaType = Field(description="配额类型")
    period: StatsPeriod = Field(description="统计周期")
    data_points: list[UsageDataPoint] = Field(
        default_factory=list, description="数据点"
    )
    average: float = Field(default=0, description="平均值")
    max_value: float = Field(default=0, description="最大值")
    min_value: float = Field(default=0, description="最小值")
    trend: TrendDirection = Field(default=TrendDirection.STABLE, description="趋势")
    trend_percentage: float = Field(default=0, description="趋势变化百分比")


class TenantDashboard(BaseModel):
    """租户仪表板数据"""

    tenant_id: str = Field(description="租户 ID")
    generated_at: datetime = Field(
        default_factory=datetime.now, description="生成时间"
    )

    # 概览
    overview: TenantOverview = Field(description="租户概览")

    # 实时使用量
    realtime_usage: dict[str, QuotaUsageStats] = Field(
        default_factory=dict, description="实时使用量"
    )

    # 历史趋势
    usage_trends: dict[str, UsageTrend] = Field(
        default_factory=dict, description="使用量趋势"
    )

    # 最近事件
    recent_events: list[TenantEvent] = Field(
        default_factory=list, description="最近事件"
    )

    # 告警
    alerts: list[dict[str, Any]] = Field(default_factory=list, description="告警列表")


class SystemOverview(BaseModel):
    """系统概览（管理员视图）"""

    generated_at: datetime = Field(
        default_factory=datetime.now, description="生成时间"
    )

    # 租户统计
    total_tenants: int = Field(default=0, description="总租户数")
    active_tenants: int = Field(default=0, description="活跃租户数")
    trial_tenants: int = Field(default=0, description="试用租户数")
    suspended_tenants: int = Field(default=0, description="暂停租户数")

    # 套餐分布
    tier_distribution: dict[str, int] = Field(
        default_factory=dict, description="套餐分布"
    )

    # 使用统计
    total_api_calls_today: int = Field(default=0, description="今日总 API 调用")
    total_tokens_today: int = Field(default=0, description="今日总 Token 使用")
    total_active_sessions: int = Field(default=0, description="总活跃会话数")

    # 配额告警
    tenants_near_quota: list[str] = Field(
        default_factory=list, description="接近配额限制的租户"
    )
    tenants_exceeded_quota: list[str] = Field(
        default_factory=list, description="超出配额的租户"
    )

    # 活跃度排名
    top_active_tenants: list[TenantOverview] = Field(
        default_factory=list, description="最活跃租户"
    )


# ============================================================================
# 统计服务
# ============================================================================


class TenantStatsService:
    """租户统计服务

    提供租户使用统计的聚合、分析和趋势计算功能。
    """

    # 活跃度权重
    ACTIVITY_WEIGHTS = {
        "api_calls": 0.3,
        "tokens": 0.3,
        "sessions": 0.2,
        "messages": 0.2,
    }

    # 趋势阈值
    TREND_THRESHOLD = 0.05  # 5% 变化视为趋势

    def __init__(
        self,
        storage: TenantStorage,
        quota_manager: QuotaManager,
    ) -> None:
        """初始化统计服务

        Args:
            storage: 租户存储
            quota_manager: 配额管理器
        """
        self._storage = storage
        self._quota_manager = quota_manager
        self._cache: dict[str, Any] = {}
        self._cache_ttl = 60  # 缓存 60 秒
        self._lock = asyncio.Lock()

    # ========================================================================
    # 租户概览
    # ========================================================================

    async def get_tenant_overview(self, tenant_id: str) -> TenantOverview | None:
        """获取租户概览

        Args:
            tenant_id: 租户 ID

        Returns:
            租户概览，不存在返回 None
        """
        tenant = await self._storage.get(tenant_id)
        if not tenant:
            return None

        # 获取实时使用量
        usage_summary = await self._quota_manager.get_usage_summary(tenant)

        # 构建配额使用统计
        quota_usage = []
        for quota_type in QuotaType:
            usage_data = usage_summary.get(quota_type.value, {})
            quota_usage.append(
                QuotaUsageStats(
                    quota_type=quota_type,
                    current=usage_data.get("current", 0),
                    limit=usage_data.get("limit", 0),
                    percentage=usage_data.get("percentage", 0),
                    status=usage_data.get("status", "ok"),
                )
            )

        # 计算活跃度
        activity_score = await self._calculate_activity_score(tenant_id)

        # 获取最后活动时间
        last_activity = await self._get_last_activity(tenant_id)

        # 获取今日统计
        today_stats = await self._get_today_stats(tenant_id)

        return TenantOverview(
            tenant_id=tenant.id,
            tenant_name=tenant.name,
            display_name=tenant.display_name,
            status=tenant.status,
            tier=tenant.tier,
            created_at=tenant.created_at,
            active_sessions=today_stats.get("active_sessions", 0),
            concurrent_requests=await self._quota_manager.get_concurrent_count(
                tenant_id
            ),
            api_calls_today=today_stats.get("api_calls", 0),
            tokens_today=today_stats.get("tokens", 0),
            quota_usage=quota_usage,
            activity_score=activity_score,
            last_activity=last_activity,
        )

    async def get_tenant_dashboard(
        self,
        tenant_id: str,
        include_trends: bool = True,
        trend_period: StatsPeriod = StatsPeriod.DAILY,
        trend_days: int = 7,
    ) -> TenantDashboard | None:
        """获取租户仪表板数据

        Args:
            tenant_id: 租户 ID
            include_trends: 是否包含趋势数据
            trend_period: 趋势周期
            trend_days: 趋势天数

        Returns:
            仪表板数据，不存在返回 None
        """
        overview = await self.get_tenant_overview(tenant_id)
        if not overview:
            return None

        # 获取实时使用量
        realtime_usage = {}
        for quota_stat in overview.quota_usage:
            realtime_usage[quota_stat.quota_type.value] = quota_stat

        # 获取趋势数据
        usage_trends = {}
        if include_trends:
            for quota_type in [
                QuotaType.TOKENS_PER_DAY,
                QuotaType.API_CALLS_PER_DAY,
            ]:
                trend = await self.get_usage_trend(
                    tenant_id=tenant_id,
                    quota_type=quota_type,
                    period=trend_period,
                    days=trend_days,
                )
                if trend:
                    usage_trends[quota_type.value] = trend

        # 获取最近事件
        recent_events = await self._storage.get_events(
            tenant_id=tenant_id,
            offset=0,
            limit=10,
        )

        # 生成告警
        alerts = await self._generate_alerts(tenant_id, overview)

        return TenantDashboard(
            tenant_id=tenant_id,
            overview=overview,
            realtime_usage=realtime_usage,
            usage_trends=usage_trends,
            recent_events=recent_events,
            alerts=alerts,
        )

    # ========================================================================
    # 使用量趋势
    # ========================================================================

    async def get_usage_trend(
        self,
        tenant_id: str,
        quota_type: QuotaType,
        period: StatsPeriod = StatsPeriod.DAILY,
        days: int = 7,
    ) -> UsageTrend | None:
        """获取使用量趋势

        Args:
            tenant_id: 租户 ID
            quota_type: 配额类型
            period: 统计周期
            days: 天数

        Returns:
            使用量趋势
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        # 获取历史使用数据
        usage_records = await self._storage.get_usage(
            tenant_id=tenant_id,
            period=period.value,
            start_date=start_date,
            end_date=end_date,
        )

        if not usage_records:
            return UsageTrend(
                quota_type=quota_type,
                period=period,
            )

        # 提取数据点
        data_points = []
        for record in usage_records:
            value = self._extract_quota_value(record, quota_type)
            data_points.append(
                UsageDataPoint(
                    timestamp=record.period_start,
                    value=value,
                )
            )

        # 计算统计值
        values = [dp.value for dp in data_points]
        average = sum(values) / len(values) if values else 0
        max_value = max(values) if values else 0
        min_value = min(values) if values else 0

        # 计算趋势
        trend, trend_percentage = self._calculate_trend(values)

        return UsageTrend(
            quota_type=quota_type,
            period=period,
            data_points=data_points,
            average=average,
            max_value=max_value,
            min_value=min_value,
            trend=trend,
            trend_percentage=trend_percentage,
        )

    async def get_quota_consumption_trends(
        self,
        tenant_id: str,
        days: int = 30,
    ) -> dict[str, UsageTrend]:
        """获取配额消耗趋势

        Args:
            tenant_id: 租户 ID
            days: 天数

        Returns:
            各配额类型的趋势
        """
        trends = {}
        for quota_type in [
            QuotaType.TOKENS_PER_DAY,
            QuotaType.API_CALLS_PER_DAY,
            QuotaType.STORAGE,
        ]:
            trend = await self.get_usage_trend(
                tenant_id=tenant_id,
                quota_type=quota_type,
                period=StatsPeriod.DAILY,
                days=days,
            )
            if trend:
                trends[quota_type.value] = trend

        return trends

    # ========================================================================
    # 系统概览（管理员）
    # ========================================================================

    async def get_system_overview(self) -> SystemOverview:
        """获取系统概览（管理员视图）

        Returns:
            系统概览
        """
        # 统计租户数量
        total_tenants = await self._storage.count()
        active_tenants = await self._storage.count(status=TenantStatus.ACTIVE)
        trial_tenants = await self._storage.count(status=TenantStatus.TRIAL)
        suspended_tenants = await self._storage.count(status=TenantStatus.SUSPENDED)

        # 套餐分布
        tier_distribution = {}
        for tier in TenantTier:
            count = await self._storage.count(tier=tier)
            tier_distribution[tier.value] = count

        # 获取所有活跃租户
        active_tenant_list = await self._storage.list(status=TenantStatus.ACTIVE)

        # 统计今日使用量
        total_api_calls = 0
        total_tokens = 0
        total_sessions = 0
        tenants_near_quota = []
        tenants_exceeded_quota = []
        tenant_overviews = []

        for tenant in active_tenant_list:
            overview = await self.get_tenant_overview(tenant.id)
            if overview:
                tenant_overviews.append(overview)
                total_api_calls += overview.api_calls_today
                total_tokens += overview.tokens_today
                total_sessions += overview.active_sessions

                # 检查配额状态
                for quota_stat in overview.quota_usage:
                    if quota_stat.status == "exceeded":
                        if tenant.id not in tenants_exceeded_quota:
                            tenants_exceeded_quota.append(tenant.id)
                    elif quota_stat.status == "warning":
                        if (
                            tenant.id not in tenants_near_quota
                            and tenant.id not in tenants_exceeded_quota
                        ):
                            tenants_near_quota.append(tenant.id)

        # 按活跃度排序
        tenant_overviews.sort(key=lambda x: x.activity_score, reverse=True)
        top_active = tenant_overviews[:10]

        return SystemOverview(
            total_tenants=total_tenants,
            active_tenants=active_tenants,
            trial_tenants=trial_tenants,
            suspended_tenants=suspended_tenants,
            tier_distribution=tier_distribution,
            total_api_calls_today=total_api_calls,
            total_tokens_today=total_tokens,
            total_active_sessions=total_sessions,
            tenants_near_quota=tenants_near_quota,
            tenants_exceeded_quota=tenants_exceeded_quota,
            top_active_tenants=top_active,
        )

    # ========================================================================
    # 历史数据聚合
    # ========================================================================

    async def aggregate_usage(
        self,
        tenant_id: str,
        period: StatsPeriod,
        start_date: datetime,
        end_date: datetime,
    ) -> TenantUsage | None:
        """聚合使用数据

        Args:
            tenant_id: 租户 ID
            period: 统计周期
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            聚合后的使用数据
        """
        # 获取原始数据
        records = await self._storage.get_usage(
            tenant_id=tenant_id,
            period="daily",  # 从日数据聚合
            start_date=start_date,
            end_date=end_date,
        )

        if not records:
            return None

        # 聚合数据
        aggregated = TenantUsage(
            tenant_id=tenant_id,
            period=period.value,
            period_start=start_date,
            period_end=end_date,
        )

        for record in records:
            aggregated.input_tokens += record.input_tokens
            aggregated.output_tokens += record.output_tokens
            aggregated.total_tokens += record.total_tokens
            aggregated.api_calls += record.api_calls
            aggregated.successful_calls += record.successful_calls
            aggregated.failed_calls += record.failed_calls
            aggregated.sessions_created += record.sessions_created
            aggregated.messages_sent += record.messages_sent
            aggregated.estimated_cost += record.estimated_cost

        # 活跃会话和存储取最后一条记录的值
        if records:
            last_record = records[-1]
            aggregated.active_sessions = last_record.active_sessions
            aggregated.storage_used_mb = last_record.storage_used_mb

        return aggregated

    # ========================================================================
    # 内部方法
    # ========================================================================

    async def _calculate_activity_score(self, tenant_id: str) -> float:
        """计算活跃度评分

        Args:
            tenant_id: 租户 ID

        Returns:
            活跃度评分 (0-100)
        """
        # 获取最近 7 天的使用数据
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)

        records = await self._storage.get_usage(
            tenant_id=tenant_id,
            period="daily",
            start_date=start_date,
            end_date=end_date,
        )

        if not records:
            return 0.0

        # 计算各维度得分
        total_api_calls = sum(r.api_calls for r in records)
        total_tokens = sum(r.total_tokens for r in records)
        total_sessions = sum(r.sessions_created for r in records)
        total_messages = sum(r.messages_sent for r in records)

        # 归一化（假设每日基准值）
        daily_api_baseline = 100
        daily_token_baseline = 10000
        daily_session_baseline = 10
        daily_message_baseline = 50

        api_score = min(total_api_calls / (daily_api_baseline * 7), 1.0)
        token_score = min(total_tokens / (daily_token_baseline * 7), 1.0)
        session_score = min(total_sessions / (daily_session_baseline * 7), 1.0)
        message_score = min(total_messages / (daily_message_baseline * 7), 1.0)

        # 加权计算
        score = (
            api_score * self.ACTIVITY_WEIGHTS["api_calls"]
            + token_score * self.ACTIVITY_WEIGHTS["tokens"]
            + session_score * self.ACTIVITY_WEIGHTS["sessions"]
            + message_score * self.ACTIVITY_WEIGHTS["messages"]
        )

        return round(score * 100, 2)

    async def _get_last_activity(self, tenant_id: str) -> datetime | None:
        """获取最后活动时间

        Args:
            tenant_id: 租户 ID

        Returns:
            最后活动时间
        """
        events = await self._storage.get_events(
            tenant_id=tenant_id,
            offset=0,
            limit=1,
        )
        if events:
            return events[0].timestamp
        return None

    async def _get_today_stats(self, tenant_id: str) -> dict[str, int]:
        """获取今日统计

        Args:
            tenant_id: 租户 ID

        Returns:
            今日统计
        """
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow = today + timedelta(days=1)

        records = await self._storage.get_usage(
            tenant_id=tenant_id,
            period="daily",
            start_date=today,
            end_date=tomorrow,
        )

        if not records:
            return {
                "api_calls": 0,
                "tokens": 0,
                "active_sessions": 0,
            }

        record = records[0]
        return {
            "api_calls": record.api_calls,
            "tokens": record.total_tokens,
            "active_sessions": record.active_sessions,
        }

    def _extract_quota_value(
        self, record: TenantUsage, quota_type: QuotaType
    ) -> float:
        """从使用记录中提取配额值

        Args:
            record: 使用记录
            quota_type: 配额类型

        Returns:
            配额值
        """
        mapping = {
            QuotaType.TOKENS_PER_DAY: record.total_tokens,
            QuotaType.API_CALLS_PER_DAY: record.api_calls,
            QuotaType.STORAGE: record.storage_used_mb,
            QuotaType.SESSIONS: record.active_sessions,
        }
        return mapping.get(quota_type, 0)

    def _calculate_trend(
        self, values: list[float]
    ) -> tuple[TrendDirection, float]:
        """计算趋势

        Args:
            values: 值列表（按时间顺序）

        Returns:
            (趋势方向, 变化百分比)
        """
        if len(values) < 2:
            return TrendDirection.STABLE, 0.0

        # 比较前半部分和后半部分的平均值
        mid = len(values) // 2
        first_half = values[:mid]
        second_half = values[mid:]

        first_avg = sum(first_half) / len(first_half) if first_half else 0
        second_avg = sum(second_half) / len(second_half) if second_half else 0

        if first_avg == 0:
            if second_avg > 0:
                return TrendDirection.UP, 100.0
            return TrendDirection.STABLE, 0.0

        change = (second_avg - first_avg) / first_avg

        if change > self.TREND_THRESHOLD:
            return TrendDirection.UP, round(change * 100, 2)
        elif change < -self.TREND_THRESHOLD:
            return TrendDirection.DOWN, round(abs(change) * 100, 2)
        else:
            return TrendDirection.STABLE, round(abs(change) * 100, 2)

    async def _generate_alerts(
        self, tenant_id: str, overview: TenantOverview
    ) -> list[dict[str, Any]]:
        """生成告警

        Args:
            tenant_id: 租户 ID
            overview: 租户概览

        Returns:
            告警列表
        """
        alerts = []

        for quota_stat in overview.quota_usage:
            if quota_stat.status == "exceeded":
                alerts.append(
                    {
                        "level": "error",
                        "type": "quota_exceeded",
                        "quota_type": quota_stat.quota_type.value,
                        "message": f"{quota_stat.quota_type.value} 配额已超限",
                        "current": quota_stat.current,
                        "limit": quota_stat.limit,
                        "percentage": quota_stat.percentage,
                    }
                )
            elif quota_stat.status == "warning":
                alerts.append(
                    {
                        "level": "warning",
                        "type": "quota_warning",
                        "quota_type": quota_stat.quota_type.value,
                        "message": f"{quota_stat.quota_type.value} 配额接近限制",
                        "current": quota_stat.current,
                        "limit": quota_stat.limit,
                        "percentage": quota_stat.percentage,
                    }
                )

        return alerts


# ============================================================================
# 全局实例
# ============================================================================

_stats_service: TenantStatsService | None = None


def configure_stats_service(
    storage: TenantStorage,
    quota_manager: QuotaManager,
) -> TenantStatsService:
    """配置统计服务

    Args:
        storage: 租户存储
        quota_manager: 配额管理器

    Returns:
        统计服务实例
    """
    global _stats_service
    _stats_service = TenantStatsService(storage, quota_manager)
    logger.info("租户统计服务已配置")
    return _stats_service


def get_stats_service() -> TenantStatsService | None:
    """获取统计服务

    Returns:
        统计服务实例
    """
    return _stats_service
