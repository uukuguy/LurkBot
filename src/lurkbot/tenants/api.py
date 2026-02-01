"""租户统计 API 端点

提供租户使用统计仪表板的 REST API。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from .models import TenantStatus, TenantTier
from .stats import (
    QuotaUsageStats,
    StatsPeriod,
    SystemOverview,
    TenantDashboard,
    TenantOverview,
    TenantStatsService,
    TrendDirection,
    UsageTrend,
    get_stats_service,
)


# ============================================================================
# 响应模型
# ============================================================================


class TenantOverviewResponse(BaseModel):
    """租户概览响应"""

    tenant_id: str
    tenant_name: str
    display_name: str
    status: str
    tier: str
    created_at: datetime
    active_sessions: int
    concurrent_requests: int
    api_calls_today: int
    tokens_today: int
    activity_score: float
    last_activity: datetime | None
    quota_usage: list[dict[str, Any]]


class UsageTrendResponse(BaseModel):
    """使用量趋势响应"""

    quota_type: str
    period: str
    data_points: list[dict[str, Any]]
    average: float
    max_value: float
    min_value: float
    trend: str
    trend_percentage: float


class TenantDashboardResponse(BaseModel):
    """租户仪表板响应"""

    tenant_id: str
    generated_at: datetime
    overview: TenantOverviewResponse
    realtime_usage: dict[str, dict[str, Any]]
    usage_trends: dict[str, UsageTrendResponse]
    recent_events: list[dict[str, Any]]
    alerts: list[dict[str, Any]]


class SystemOverviewResponse(BaseModel):
    """系统概览响应"""

    generated_at: datetime
    total_tenants: int
    active_tenants: int
    trial_tenants: int
    suspended_tenants: int
    tier_distribution: dict[str, int]
    total_api_calls_today: int
    total_tokens_today: int
    total_active_sessions: int
    tenants_near_quota: list[str]
    tenants_exceeded_quota: list[str]
    top_active_tenants: list[TenantOverviewResponse]


class RealtimeUsageResponse(BaseModel):
    """实时使用量响应"""

    tenant_id: str
    timestamp: datetime
    usage: dict[str, dict[str, Any]]


class HistoryUsageResponse(BaseModel):
    """历史使用量响应"""

    tenant_id: str
    period: str
    start_date: datetime
    end_date: datetime
    data: list[dict[str, Any]]


class QuotaTrendsResponse(BaseModel):
    """配额趋势响应"""

    tenant_id: str
    trends: dict[str, UsageTrendResponse]


# ============================================================================
# 依赖注入
# ============================================================================


def get_stats_service_dep() -> TenantStatsService:
    """获取统计服务依赖"""
    service = get_stats_service()
    if not service:
        raise HTTPException(
            status_code=503,
            detail="统计服务未配置",
        )
    return service


# ============================================================================
# 辅助函数
# ============================================================================


def _overview_to_response(overview: TenantOverview) -> TenantOverviewResponse:
    """转换概览为响应"""
    return TenantOverviewResponse(
        tenant_id=overview.tenant_id,
        tenant_name=overview.tenant_name,
        display_name=overview.display_name,
        status=overview.status.value,
        tier=overview.tier.value,
        created_at=overview.created_at,
        active_sessions=overview.active_sessions,
        concurrent_requests=overview.concurrent_requests,
        api_calls_today=overview.api_calls_today,
        tokens_today=overview.tokens_today,
        activity_score=overview.activity_score,
        last_activity=overview.last_activity,
        quota_usage=[
            {
                "quota_type": q.quota_type.value,
                "current": q.current,
                "limit": q.limit,
                "percentage": q.percentage,
                "status": q.status,
                "trend": q.trend.value,
                "trend_percentage": q.trend_percentage,
            }
            for q in overview.quota_usage
        ],
    )


def _trend_to_response(trend: UsageTrend) -> UsageTrendResponse:
    """转换趋势为响应"""
    return UsageTrendResponse(
        quota_type=trend.quota_type.value,
        period=trend.period.value,
        data_points=[
            {"timestamp": dp.timestamp.isoformat(), "value": dp.value}
            for dp in trend.data_points
        ],
        average=trend.average,
        max_value=trend.max_value,
        min_value=trend.min_value,
        trend=trend.trend.value,
        trend_percentage=trend.trend_percentage,
    )


# ============================================================================
# API 路由
# ============================================================================


def create_tenant_stats_router() -> APIRouter:
    """创建租户统计 API 路由

    Returns:
        FastAPI 路由
    """
    router = APIRouter(prefix="/api/v1/tenants", tags=["tenant-stats"])

    # ========================================================================
    # 租户统计端点
    # ========================================================================

    @router.get("/{tenant_id}/stats", response_model=TenantOverviewResponse)
    async def get_tenant_stats(
        tenant_id: str,
        stats_service: TenantStatsService = Depends(get_stats_service_dep),
    ):
        """获取租户统计概览

        Args:
            tenant_id: 租户 ID

        Returns:
            租户统计概览
        """
        overview = await stats_service.get_tenant_overview(tenant_id)
        if not overview:
            raise HTTPException(
                status_code=404,
                detail=f"租户不存在: {tenant_id}",
            )
        return _overview_to_response(overview)

    @router.get("/{tenant_id}/dashboard", response_model=TenantDashboardResponse)
    async def get_tenant_dashboard(
        tenant_id: str,
        include_trends: bool = Query(True, description="是否包含趋势数据"),
        trend_period: str = Query("daily", description="趋势周期"),
        trend_days: int = Query(7, ge=1, le=90, description="趋势天数"),
        stats_service: TenantStatsService = Depends(get_stats_service_dep),
    ):
        """获取租户仪表板数据

        Args:
            tenant_id: 租户 ID
            include_trends: 是否包含趋势数据
            trend_period: 趋势周期 (hourly/daily/weekly/monthly)
            trend_days: 趋势天数

        Returns:
            仪表板数据
        """
        try:
            period = StatsPeriod(trend_period)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"无效的趋势周期: {trend_period}",
            )

        dashboard = await stats_service.get_tenant_dashboard(
            tenant_id=tenant_id,
            include_trends=include_trends,
            trend_period=period,
            trend_days=trend_days,
        )

        if not dashboard:
            raise HTTPException(
                status_code=404,
                detail=f"租户不存在: {tenant_id}",
            )

        return TenantDashboardResponse(
            tenant_id=dashboard.tenant_id,
            generated_at=dashboard.generated_at,
            overview=_overview_to_response(dashboard.overview),
            realtime_usage={
                k: {
                    "quota_type": v.quota_type.value,
                    "current": v.current,
                    "limit": v.limit,
                    "percentage": v.percentage,
                    "status": v.status,
                }
                for k, v in dashboard.realtime_usage.items()
            },
            usage_trends={
                k: _trend_to_response(v) for k, v in dashboard.usage_trends.items()
            },
            recent_events=[
                {
                    "event_type": e.event_type.value,
                    "timestamp": e.timestamp.isoformat(),
                    "message": e.message,
                    "metadata": e.metadata,
                }
                for e in dashboard.recent_events
            ],
            alerts=dashboard.alerts,
        )

    @router.get("/{tenant_id}/usage/realtime", response_model=RealtimeUsageResponse)
    async def get_realtime_usage(
        tenant_id: str,
        stats_service: TenantStatsService = Depends(get_stats_service_dep),
    ):
        """获取实时使用量

        Args:
            tenant_id: 租户 ID

        Returns:
            实时使用量
        """
        overview = await stats_service.get_tenant_overview(tenant_id)
        if not overview:
            raise HTTPException(
                status_code=404,
                detail=f"租户不存在: {tenant_id}",
            )

        return RealtimeUsageResponse(
            tenant_id=tenant_id,
            timestamp=datetime.now(),
            usage={
                q.quota_type.value: {
                    "current": q.current,
                    "limit": q.limit,
                    "percentage": q.percentage,
                    "status": q.status,
                }
                for q in overview.quota_usage
            },
        )

    @router.get("/{tenant_id}/usage/history", response_model=HistoryUsageResponse)
    async def get_usage_history(
        tenant_id: str,
        period: str = Query("daily", description="统计周期"),
        days: int = Query(30, ge=1, le=365, description="天数"),
        stats_service: TenantStatsService = Depends(get_stats_service_dep),
    ):
        """获取历史使用量

        Args:
            tenant_id: 租户 ID
            period: 统计周期 (hourly/daily/weekly/monthly)
            days: 天数

        Returns:
            历史使用量
        """
        try:
            stats_period = StatsPeriod(period)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"无效的统计周期: {period}",
            )

        end_date = datetime.now()
        start_date = datetime.now()
        from datetime import timedelta

        start_date = end_date - timedelta(days=days)

        # 获取聚合数据
        aggregated = await stats_service.aggregate_usage(
            tenant_id=tenant_id,
            period=stats_period,
            start_date=start_date,
            end_date=end_date,
        )

        data = []
        if aggregated:
            data.append(
                {
                    "period_start": aggregated.period_start.isoformat(),
                    "period_end": aggregated.period_end.isoformat(),
                    "input_tokens": aggregated.input_tokens,
                    "output_tokens": aggregated.output_tokens,
                    "total_tokens": aggregated.total_tokens,
                    "api_calls": aggregated.api_calls,
                    "successful_calls": aggregated.successful_calls,
                    "failed_calls": aggregated.failed_calls,
                    "sessions_created": aggregated.sessions_created,
                    "messages_sent": aggregated.messages_sent,
                    "storage_used_mb": aggregated.storage_used_mb,
                    "estimated_cost": aggregated.estimated_cost,
                }
            )

        return HistoryUsageResponse(
            tenant_id=tenant_id,
            period=period,
            start_date=start_date,
            end_date=end_date,
            data=data,
        )

    @router.get("/{tenant_id}/quota/trends", response_model=QuotaTrendsResponse)
    async def get_quota_trends(
        tenant_id: str,
        days: int = Query(30, ge=1, le=365, description="天数"),
        stats_service: TenantStatsService = Depends(get_stats_service_dep),
    ):
        """获取配额消耗趋势

        Args:
            tenant_id: 租户 ID
            days: 天数

        Returns:
            配额趋势
        """
        trends = await stats_service.get_quota_consumption_trends(
            tenant_id=tenant_id,
            days=days,
        )

        return QuotaTrendsResponse(
            tenant_id=tenant_id,
            trends={k: _trend_to_response(v) for k, v in trends.items()},
        )

    # ========================================================================
    # 系统概览端点（管理员）
    # ========================================================================

    @router.get("/overview", response_model=SystemOverviewResponse)
    async def get_system_overview(
        stats_service: TenantStatsService = Depends(get_stats_service_dep),
    ):
        """获取系统概览（管理员视图）

        Returns:
            系统概览
        """
        overview = await stats_service.get_system_overview()

        return SystemOverviewResponse(
            generated_at=overview.generated_at,
            total_tenants=overview.total_tenants,
            active_tenants=overview.active_tenants,
            trial_tenants=overview.trial_tenants,
            suspended_tenants=overview.suspended_tenants,
            tier_distribution=overview.tier_distribution,
            total_api_calls_today=overview.total_api_calls_today,
            total_tokens_today=overview.total_tokens_today,
            total_active_sessions=overview.total_active_sessions,
            tenants_near_quota=overview.tenants_near_quota,
            tenants_exceeded_quota=overview.tenants_exceeded_quota,
            top_active_tenants=[
                _overview_to_response(t) for t in overview.top_active_tenants
            ],
        )

    return router
