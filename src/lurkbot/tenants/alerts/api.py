"""告警 API 端点

提供告警相关的 REST API。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from .engine import AlertEngine, get_alert_engine
from .models import (
    Alert,
    AlertSeverity,
    AlertStats,
    AlertStatus,
    AlertType,
)


# ============================================================================
# 请求/响应模型
# ============================================================================


class AlertListResponse(BaseModel):
    """告警列表响应"""

    alerts: list[Alert] = Field(description="告警列表")
    total: int = Field(description="总数")
    limit: int = Field(description="返回数量")
    offset: int = Field(description="偏移量")


class AlertDetailResponse(BaseModel):
    """告警详情响应"""

    alert: Alert = Field(description="告警详情")


class ResolveAlertRequest(BaseModel):
    """解决告警请求"""

    resolved_by: str | None = Field(default=None, description="解决者 ID")
    note: str | None = Field(default=None, description="解决备注")


class SuppressAlertRequest(BaseModel):
    """抑制告警请求"""

    duration_seconds: int = Field(
        default=3600,
        description="抑制时长（秒）",
        ge=60,
        le=86400,
    )


class AcknowledgeAlertRequest(BaseModel):
    """确认告警请求"""

    acknowledged_by: str | None = Field(default=None, description="确认者 ID")


class TriggerAlertRequest(BaseModel):
    """触发告警请求"""

    alert_type: AlertType = Field(description="告警类型")
    severity: AlertSeverity = Field(
        default=AlertSeverity.WARNING,
        description="告警级别",
    )
    title: str = Field(description="告警标题")
    message: str = Field(description="告警详情")
    context: dict[str, Any] = Field(
        default_factory=dict,
        description="告警上下文",
    )


class AlertStatsResponse(BaseModel):
    """告警统计响应"""

    stats: AlertStats = Field(description="告警统计")


class RuleListResponse(BaseModel):
    """规则列表响应"""

    rules: list[dict[str, Any]] = Field(description="规则列表")
    total: int = Field(description="总数")


class RuleUpdateRequest(BaseModel):
    """规则更新请求"""

    enabled: bool | None = Field(default=None, description="是否启用")
    threshold: float | None = Field(default=None, description="阈值")


class SuccessResponse(BaseModel):
    """成功响应"""

    success: bool = Field(default=True, description="是否成功")
    message: str = Field(default="", description="消息")


# ============================================================================
# 依赖注入
# ============================================================================


def get_engine() -> AlertEngine:
    """获取告警引擎依赖"""
    try:
        return get_alert_engine()
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))


# ============================================================================
# API 路由
# ============================================================================


def create_alert_router() -> APIRouter:
    """创建告警 API 路由

    Returns:
        FastAPI 路由
    """
    router = APIRouter(prefix="/api/v1/alerts", tags=["alerts"])

    # ========================================================================
    # 告警查询
    # ========================================================================

    @router.get("", response_model=AlertListResponse)
    async def list_alerts(
        tenant_id: str | None = Query(default=None, description="租户 ID"),
        status: AlertStatus | None = Query(default=None, description="状态过滤"),
        severity: AlertSeverity | None = Query(default=None, description="级别过滤"),
        alert_type: AlertType | None = Query(default=None, description="类型过滤"),
        limit: int = Query(default=100, ge=1, le=1000, description="返回数量"),
        offset: int = Query(default=0, ge=0, description="偏移量"),
        engine: AlertEngine = Depends(get_engine),
    ) -> AlertListResponse:
        """获取告警列表"""
        alerts = await engine.list_alerts(
            tenant_id=tenant_id,
            status=status,
            severity=severity,
            alert_type=alert_type,
            limit=limit,
            offset=offset,
        )

        total = await engine.alert_storage.count_alerts(
            tenant_id=tenant_id,
            status=status,
            severity=severity,
            alert_type=alert_type,
        )

        return AlertListResponse(
            alerts=alerts,
            total=total,
            limit=limit,
            offset=offset,
        )

    @router.get("/active", response_model=AlertListResponse)
    async def list_active_alerts(
        tenant_id: str | None = Query(default=None, description="租户 ID"),
        engine: AlertEngine = Depends(get_engine),
    ) -> AlertListResponse:
        """获取活跃告警列表"""
        alerts = await engine.get_active_alerts(tenant_id)

        return AlertListResponse(
            alerts=alerts,
            total=len(alerts),
            limit=len(alerts),
            offset=0,
        )

    @router.get("/stats", response_model=AlertStatsResponse)
    async def get_alert_stats(
        tenant_id: str | None = Query(default=None, description="租户 ID"),
        start_time: datetime | None = Query(default=None, description="开始时间"),
        end_time: datetime | None = Query(default=None, description="结束时间"),
        engine: AlertEngine = Depends(get_engine),
    ) -> AlertStatsResponse:
        """获取告警统计"""
        stats = await engine.get_stats(
            tenant_id=tenant_id,
            start_time=start_time,
            end_time=end_time,
        )

        return AlertStatsResponse(stats=stats)

    # ========================================================================
    # 规则管理 (必须在 /{alert_id} 之前定义，避免路由冲突)
    # ========================================================================

    @router.get("/rules", response_model=RuleListResponse)
    async def list_rules(
        enabled_only: bool = Query(default=False, description="仅显示启用的规则"),
        engine: AlertEngine = Depends(get_engine),
    ) -> RuleListResponse:
        """获取告警规则列表"""
        if enabled_only:
            rules = engine.rule_manager.get_enabled_rules()
        else:
            rules = engine.rule_manager.get_all_rules()

        rule_dicts = [rule.model_dump() for rule in rules]

        return RuleListResponse(
            rules=rule_dicts,
            total=len(rule_dicts),
        )

    @router.get("/rules/stats/summary")
    async def get_rules_stats(
        engine: AlertEngine = Depends(get_engine),
    ) -> dict[str, int]:
        """获取规则统计"""
        return engine.rule_manager.get_rules_count()

    @router.get("/rules/{rule_id}")
    async def get_rule(
        rule_id: str,
        engine: AlertEngine = Depends(get_engine),
    ) -> dict[str, Any]:
        """获取告警规则详情"""
        rule = engine.rule_manager.get_rule(rule_id)
        if not rule:
            raise HTTPException(status_code=404, detail="规则不存在")

        return rule.model_dump()

    @router.patch("/rules/{rule_id}", response_model=SuccessResponse)
    async def update_rule(
        rule_id: str,
        request: RuleUpdateRequest,
        engine: AlertEngine = Depends(get_engine),
    ) -> SuccessResponse:
        """更新告警规则"""
        rule = engine.rule_manager.get_rule(rule_id)
        if not rule:
            raise HTTPException(status_code=404, detail="规则不存在")

        if request.enabled is not None:
            if request.enabled:
                engine.rule_manager.enable_rule(rule_id)
            else:
                engine.rule_manager.disable_rule(rule_id)

        if request.threshold is not None:
            engine.rule_manager.update_rule_threshold(rule_id, request.threshold)

        return SuccessResponse(success=True, message="规则已更新")

    @router.post("/rules/{rule_id}/enable", response_model=SuccessResponse)
    async def enable_rule(
        rule_id: str,
        engine: AlertEngine = Depends(get_engine),
    ) -> SuccessResponse:
        """启用告警规则"""
        success = engine.rule_manager.enable_rule(rule_id)
        if not success:
            raise HTTPException(status_code=404, detail="规则不存在")

        return SuccessResponse(success=True, message="规则已启用")

    @router.post("/rules/{rule_id}/disable", response_model=SuccessResponse)
    async def disable_rule(
        rule_id: str,
        engine: AlertEngine = Depends(get_engine),
    ) -> SuccessResponse:
        """禁用告警规则"""
        success = engine.rule_manager.disable_rule(rule_id)
        if not success:
            raise HTTPException(status_code=404, detail="规则不存在")

        return SuccessResponse(success=True, message="规则已禁用")

    # ========================================================================
    # 租户告警 (必须在 /{alert_id} 之前定义，避免路由冲突)
    # ========================================================================

    @router.get("/tenants/{tenant_id}", response_model=AlertListResponse)
    async def list_tenant_alerts(
        tenant_id: str,
        status: AlertStatus | None = Query(default=None, description="状态过滤"),
        severity: AlertSeverity | None = Query(default=None, description="级别过滤"),
        limit: int = Query(default=100, ge=1, le=1000, description="返回数量"),
        offset: int = Query(default=0, ge=0, description="偏移量"),
        engine: AlertEngine = Depends(get_engine),
    ) -> AlertListResponse:
        """获取租户告警列表"""
        alerts = await engine.list_alerts(
            tenant_id=tenant_id,
            status=status,
            severity=severity,
            limit=limit,
            offset=offset,
        )

        total = await engine.alert_storage.count_alerts(
            tenant_id=tenant_id,
            status=status,
            severity=severity,
        )

        return AlertListResponse(
            alerts=alerts,
            total=total,
            limit=limit,
            offset=offset,
        )

    @router.get("/tenants/{tenant_id}/stats", response_model=AlertStatsResponse)
    async def get_tenant_alert_stats(
        tenant_id: str,
        start_time: datetime | None = Query(default=None, description="开始时间"),
        end_time: datetime | None = Query(default=None, description="结束时间"),
        engine: AlertEngine = Depends(get_engine),
    ) -> AlertStatsResponse:
        """获取租户告警统计"""
        stats = await engine.get_stats(
            tenant_id=tenant_id,
            start_time=start_time,
            end_time=end_time,
        )

        return AlertStatsResponse(stats=stats)

    @router.post("/tenants/{tenant_id}/trigger", response_model=AlertDetailResponse)
    async def trigger_tenant_alert(
        tenant_id: str,
        request: TriggerAlertRequest,
        engine: AlertEngine = Depends(get_engine),
    ) -> AlertDetailResponse:
        """手动触发租户告警"""
        alert = await engine.trigger_alert(
            tenant_id=tenant_id,
            alert_type=request.alert_type,
            severity=request.severity,
            title=request.title,
            message=request.message,
            context=request.context,
        )

        return AlertDetailResponse(alert=alert)

    @router.post("/tenants/{tenant_id}/check", response_model=AlertListResponse)
    async def check_tenant_alerts(
        tenant_id: str,
        engine: AlertEngine = Depends(get_engine),
    ) -> AlertListResponse:
        """检查并触发租户告警"""
        alerts = await engine.check_and_trigger(tenant_id)

        return AlertListResponse(
            alerts=alerts,
            total=len(alerts),
            limit=len(alerts),
            offset=0,
        )

    # ========================================================================
    # 告警详情和操作 (动态路由放在最后)
    # ========================================================================

    @router.get("/{alert_id}", response_model=AlertDetailResponse)
    async def get_alert(
        alert_id: str,
        engine: AlertEngine = Depends(get_engine),
    ) -> AlertDetailResponse:
        """获取告警详情"""
        alert = await engine.get_alert(alert_id)
        if not alert:
            raise HTTPException(status_code=404, detail="告警不存在")

        return AlertDetailResponse(alert=alert)

    @router.post("/{alert_id}/resolve", response_model=AlertDetailResponse)
    async def resolve_alert(
        alert_id: str,
        request: ResolveAlertRequest,
        engine: AlertEngine = Depends(get_engine),
    ) -> AlertDetailResponse:
        """解决告警"""
        alert = await engine.resolve_alert(
            alert_id=alert_id,
            resolved_by=request.resolved_by,
            note=request.note,
        )

        if not alert:
            raise HTTPException(status_code=404, detail="告警不存在")

        return AlertDetailResponse(alert=alert)

    @router.post("/{alert_id}/acknowledge", response_model=AlertDetailResponse)
    async def acknowledge_alert(
        alert_id: str,
        request: AcknowledgeAlertRequest,
        engine: AlertEngine = Depends(get_engine),
    ) -> AlertDetailResponse:
        """确认告警"""
        alert = await engine.acknowledge_alert(
            alert_id=alert_id,
            acknowledged_by=request.acknowledged_by,
        )

        if not alert:
            raise HTTPException(status_code=404, detail="告警不存在")

        return AlertDetailResponse(alert=alert)

    @router.post("/{alert_id}/suppress", response_model=AlertDetailResponse)
    async def suppress_alert(
        alert_id: str,
        request: SuppressAlertRequest,
        engine: AlertEngine = Depends(get_engine),
    ) -> AlertDetailResponse:
        """抑制告警"""
        alert = await engine.suppress_alert(
            alert_id=alert_id,
            duration_seconds=request.duration_seconds,
        )

        if not alert:
            raise HTTPException(status_code=404, detail="告警不存在")

        return AlertDetailResponse(alert=alert)

    return router
