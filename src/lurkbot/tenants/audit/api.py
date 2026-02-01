"""审计日志 API 端点

提供审计日志相关的 REST API。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from .logger import AuditLogger, get_audit_logger
from .models import (
    AuditEvent,
    AuditEventType,
    AuditQuery,
    AuditResult,
    AuditSeverity,
    AuditStats,
    ComplianceReport,
    PolicyEvaluation,
    PolicyEvaluationQuery,
    PolicyEvaluationResult,
    PolicyEvaluationStats,
    ReportFormat,
    ResourceType,
)
from .policy_tracker import PolicyTracker
from .reports import ReportGenerator
from .storage import AuditStorage, MemoryAuditStorage


# ============================================================================
# 请求/响应模型
# ============================================================================


class AuditEventListResponse(BaseModel):
    """审计事件列表响应"""

    events: list[AuditEvent] = Field(description="事件列表")
    total: int = Field(description="总数")
    limit: int = Field(description="返回数量")
    offset: int = Field(description="偏移量")


class AuditEventDetailResponse(BaseModel):
    """审计事件详情响应"""

    event: AuditEvent = Field(description="事件详情")


class AuditStatsResponse(BaseModel):
    """审计统计响应"""

    stats: AuditStats = Field(description="审计统计")


class PolicyEvaluationListResponse(BaseModel):
    """策略评估列表响应"""

    evaluations: list[PolicyEvaluation] = Field(description="评估列表")
    total: int = Field(description="总数")
    limit: int = Field(description="返回数量")
    offset: int = Field(description="偏移量")


class PolicyEvaluationStatsResponse(BaseModel):
    """策略评估统计响应"""

    stats: PolicyEvaluationStats = Field(description="策略评估统计")


class DenialReasonsResponse(BaseModel):
    """拒绝原因响应"""

    reasons: dict[str, int] = Field(description="拒绝原因统计")


class PolicyHitStatsResponse(BaseModel):
    """策略命中统计响应"""

    stats: dict[str, int] = Field(description="策略命中统计")


class ReportResponse(BaseModel):
    """报告响应"""

    report: ComplianceReport = Field(description="报告")


class ReportContentResponse(BaseModel):
    """报告内容响应"""

    content: str = Field(description="格式化后的报告内容")
    format: str = Field(description="报告格式")


class SuccessResponse(BaseModel):
    """成功响应"""

    success: bool = Field(default=True, description="是否成功")
    message: str = Field(default="", description="消息")


# ============================================================================
# 全局实例
# ============================================================================

_audit_storage: AuditStorage | None = None
_policy_tracker: PolicyTracker | None = None
_report_generator: ReportGenerator | None = None


def configure_audit_api(
    storage: AuditStorage | None = None,
) -> None:
    """配置审计 API

    Args:
        storage: 审计存储
    """
    global _audit_storage, _policy_tracker, _report_generator

    _audit_storage = storage or MemoryAuditStorage()
    _policy_tracker = PolicyTracker(storage=_audit_storage)
    _report_generator = ReportGenerator(storage=_audit_storage)


def get_storage() -> AuditStorage:
    """获取审计存储"""
    global _audit_storage
    if _audit_storage is None:
        _audit_storage = MemoryAuditStorage()
    return _audit_storage


def get_tracker() -> PolicyTracker:
    """获取策略追踪器"""
    global _policy_tracker, _audit_storage
    if _policy_tracker is None:
        _policy_tracker = PolicyTracker(storage=get_storage())
    return _policy_tracker


def get_generator() -> ReportGenerator:
    """获取报告生成器"""
    global _report_generator
    if _report_generator is None:
        _report_generator = ReportGenerator(storage=get_storage())
    return _report_generator


# ============================================================================
# API 路由
# ============================================================================


def create_audit_router() -> APIRouter:
    """创建审计 API 路由

    Returns:
        FastAPI 路由
    """
    router = APIRouter(prefix="/api/v1/audit", tags=["audit"])

    # ========================================================================
    # 审计事件查询
    # ========================================================================

    @router.get("/events", response_model=AuditEventListResponse)
    async def list_events(
        tenant_id: str | None = Query(default=None, description="租户 ID"),
        user_id: str | None = Query(default=None, description="用户 ID"),
        event_type: AuditEventType | None = Query(default=None, description="事件类型"),
        severity: AuditSeverity | None = Query(default=None, description="严重级别"),
        result: AuditResult | None = Query(default=None, description="结果"),
        resource_type: ResourceType | None = Query(default=None, description="资源类型"),
        start_time: datetime | None = Query(default=None, description="开始时间"),
        end_time: datetime | None = Query(default=None, description="结束时间"),
        keyword: str | None = Query(default=None, description="关键词搜索"),
        limit: int = Query(default=100, ge=1, le=1000, description="返回数量"),
        offset: int = Query(default=0, ge=0, description="偏移量"),
        storage: AuditStorage = Depends(get_storage),
    ) -> AuditEventListResponse:
        """获取审计事件列表"""
        query = AuditQuery(
            tenant_ids=[tenant_id] if tenant_id else None,
            user_ids=[user_id] if user_id else None,
            event_types=[event_type] if event_type else None,
            severities=[severity] if severity else None,
            results=[result] if result else None,
            resource_types=[resource_type] if resource_type else None,
            start_time=start_time,
            end_time=end_time,
            keyword=keyword,
            limit=limit,
            offset=offset,
        )

        events = await storage.query_events(query)
        total = await storage.count_events(query)

        return AuditEventListResponse(
            events=events,
            total=total,
            limit=limit,
            offset=offset,
        )

    @router.get("/events/{event_id}", response_model=AuditEventDetailResponse)
    async def get_event(
        event_id: str,
        storage: AuditStorage = Depends(get_storage),
    ) -> AuditEventDetailResponse:
        """获取审计事件详情"""
        event = await storage.get_event(event_id)
        if not event:
            raise HTTPException(status_code=404, detail="事件不存在")

        return AuditEventDetailResponse(event=event)

    @router.get("/tenants/{tenant_id}/events", response_model=AuditEventListResponse)
    async def list_tenant_events(
        tenant_id: str,
        event_type: AuditEventType | None = Query(default=None, description="事件类型"),
        severity: AuditSeverity | None = Query(default=None, description="严重级别"),
        start_time: datetime | None = Query(default=None, description="开始时间"),
        end_time: datetime | None = Query(default=None, description="结束时间"),
        limit: int = Query(default=100, ge=1, le=1000, description="返回数量"),
        offset: int = Query(default=0, ge=0, description="偏移量"),
        storage: AuditStorage = Depends(get_storage),
    ) -> AuditEventListResponse:
        """获取租户审计事件"""
        query = AuditQuery(
            tenant_ids=[tenant_id],
            event_types=[event_type] if event_type else None,
            severities=[severity] if severity else None,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
            offset=offset,
        )

        events = await storage.query_events(query)
        total = await storage.count_events(query)

        return AuditEventListResponse(
            events=events,
            total=total,
            limit=limit,
            offset=offset,
        )

    # ========================================================================
    # 审计统计
    # ========================================================================

    @router.get("/stats", response_model=AuditStatsResponse)
    async def get_stats(
        tenant_id: str | None = Query(default=None, description="租户 ID"),
        start_time: datetime | None = Query(default=None, description="开始时间"),
        end_time: datetime | None = Query(default=None, description="结束时间"),
        storage: AuditStorage = Depends(get_storage),
    ) -> AuditStatsResponse:
        """获取审计统计"""
        stats = await storage.get_event_stats(
            tenant_id=tenant_id,
            start_time=start_time,
            end_time=end_time,
        )

        return AuditStatsResponse(stats=stats)

    @router.get("/tenants/{tenant_id}/stats", response_model=AuditStatsResponse)
    async def get_tenant_stats(
        tenant_id: str,
        start_time: datetime | None = Query(default=None, description="开始时间"),
        end_time: datetime | None = Query(default=None, description="结束时间"),
        storage: AuditStorage = Depends(get_storage),
    ) -> AuditStatsResponse:
        """获取租户审计统计"""
        stats = await storage.get_event_stats(
            tenant_id=tenant_id,
            start_time=start_time,
            end_time=end_time,
        )

        return AuditStatsResponse(stats=stats)

    # ========================================================================
    # 策略评估查询
    # ========================================================================

    @router.get("/policy-evaluations", response_model=PolicyEvaluationListResponse)
    async def list_policy_evaluations(
        tenant_id: str | None = Query(default=None, description="租户 ID"),
        user_id: str | None = Query(default=None, description="用户 ID"),
        result: PolicyEvaluationResult | None = Query(default=None, description="评估结果"),
        action: str | None = Query(default=None, description="操作"),
        resource_type: str | None = Query(default=None, description="资源类型"),
        start_time: datetime | None = Query(default=None, description="开始时间"),
        end_time: datetime | None = Query(default=None, description="结束时间"),
        limit: int = Query(default=100, ge=1, le=1000, description="返回数量"),
        offset: int = Query(default=0, ge=0, description="偏移量"),
        tracker: PolicyTracker = Depends(get_tracker),
    ) -> PolicyEvaluationListResponse:
        """获取策略评估列表"""
        evaluations = await tracker.get_evaluation_history(
            tenant_id=tenant_id,
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            result=result,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
            offset=offset,
        )

        # 获取总数
        query = PolicyEvaluationQuery(
            tenant_ids=[tenant_id] if tenant_id else None,
            user_ids=[user_id] if user_id else None,
            results=[result] if result else None,
            actions=[action] if action else None,
            resource_types=[resource_type] if resource_type else None,
            start_time=start_time,
            end_time=end_time,
            limit=1000,
        )
        total = await tracker.storage.count_policy_evaluations(query)

        return PolicyEvaluationListResponse(
            evaluations=evaluations,
            total=total,
            limit=limit,
            offset=offset,
        )

    @router.get("/policy-evaluations/stats", response_model=PolicyEvaluationStatsResponse)
    async def get_policy_evaluation_stats(
        tenant_id: str | None = Query(default=None, description="租户 ID"),
        start_time: datetime | None = Query(default=None, description="开始时间"),
        end_time: datetime | None = Query(default=None, description="结束时间"),
        tracker: PolicyTracker = Depends(get_tracker),
    ) -> PolicyEvaluationStatsResponse:
        """获取策略评估统计"""
        stats = await tracker.get_stats(
            tenant_id=tenant_id,
            start_time=start_time,
            end_time=end_time,
        )

        return PolicyEvaluationStatsResponse(stats=stats)

    @router.get("/policy-evaluations/denial-reasons", response_model=DenialReasonsResponse)
    async def get_denial_reasons(
        tenant_id: str | None = Query(default=None, description="租户 ID"),
        start_time: datetime | None = Query(default=None, description="开始时间"),
        end_time: datetime | None = Query(default=None, description="结束时间"),
        top_n: int = Query(default=10, ge=1, le=100, description="返回前 N 个"),
        tracker: PolicyTracker = Depends(get_tracker),
    ) -> DenialReasonsResponse:
        """获取拒绝原因统计"""
        reasons = await tracker.get_denial_reasons(
            tenant_id=tenant_id,
            start_time=start_time,
            end_time=end_time,
            top_n=top_n,
        )

        return DenialReasonsResponse(reasons=reasons)

    @router.get("/policy-evaluations/policy-hits", response_model=PolicyHitStatsResponse)
    async def get_policy_hits(
        tenant_id: str | None = Query(default=None, description="租户 ID"),
        start_time: datetime | None = Query(default=None, description="开始时间"),
        end_time: datetime | None = Query(default=None, description="结束时间"),
        top_n: int = Query(default=10, ge=1, le=100, description="返回前 N 个"),
        tracker: PolicyTracker = Depends(get_tracker),
    ) -> PolicyHitStatsResponse:
        """获取策略命中统计"""
        stats = await tracker.get_policy_hit_stats(
            tenant_id=tenant_id,
            start_time=start_time,
            end_time=end_time,
            top_n=top_n,
        )

        return PolicyHitStatsResponse(stats=stats)

    # ========================================================================
    # 报告生成
    # ========================================================================

    @router.get("/reports/usage", response_model=ReportResponse)
    async def generate_usage_report(
        tenant_id: str | None = Query(default=None, description="租户 ID"),
        start_time: datetime | None = Query(default=None, description="开始时间"),
        end_time: datetime | None = Query(default=None, description="结束时间"),
        format: ReportFormat = Query(default=ReportFormat.JSON, description="报告格式"),
        generator: ReportGenerator = Depends(get_generator),
    ) -> ReportResponse:
        """生成使用量报告"""
        report = await generator.generate_usage_report(
            tenant_id=tenant_id,
            start_time=start_time,
            end_time=end_time,
            report_format=format,
        )

        return ReportResponse(report=report)

    @router.get("/reports/security", response_model=ReportResponse)
    async def generate_security_report(
        tenant_id: str | None = Query(default=None, description="租户 ID"),
        start_time: datetime | None = Query(default=None, description="开始时间"),
        end_time: datetime | None = Query(default=None, description="结束时间"),
        format: ReportFormat = Query(default=ReportFormat.JSON, description="报告格式"),
        generator: ReportGenerator = Depends(get_generator),
    ) -> ReportResponse:
        """生成安全审计报告"""
        report = await generator.generate_security_audit_report(
            tenant_id=tenant_id,
            start_time=start_time,
            end_time=end_time,
            report_format=format,
        )

        return ReportResponse(report=report)

    @router.get("/reports/compliance", response_model=ReportResponse)
    async def generate_compliance_report(
        tenant_id: str | None = Query(default=None, description="租户 ID"),
        start_time: datetime | None = Query(default=None, description="开始时间"),
        end_time: datetime | None = Query(default=None, description="结束时间"),
        format: ReportFormat = Query(default=ReportFormat.JSON, description="报告格式"),
        generator: ReportGenerator = Depends(get_generator),
    ) -> ReportResponse:
        """生成合规检查报告"""
        report = await generator.generate_compliance_report(
            tenant_id=tenant_id,
            start_time=start_time,
            end_time=end_time,
            report_format=format,
        )

        return ReportResponse(report=report)

    @router.get("/reports/{report_type}/formatted", response_model=ReportContentResponse)
    async def get_formatted_report(
        report_type: str,
        tenant_id: str | None = Query(default=None, description="租户 ID"),
        start_time: datetime | None = Query(default=None, description="开始时间"),
        end_time: datetime | None = Query(default=None, description="结束时间"),
        format: ReportFormat = Query(default=ReportFormat.MARKDOWN, description="报告格式"),
        generator: ReportGenerator = Depends(get_generator),
    ) -> ReportContentResponse:
        """获取格式化报告内容"""
        if report_type == "usage":
            report = await generator.generate_usage_report(
                tenant_id=tenant_id,
                start_time=start_time,
                end_time=end_time,
                report_format=format,
            )
        elif report_type == "security":
            report = await generator.generate_security_audit_report(
                tenant_id=tenant_id,
                start_time=start_time,
                end_time=end_time,
                report_format=format,
            )
        elif report_type == "compliance":
            report = await generator.generate_compliance_report(
                tenant_id=tenant_id,
                start_time=start_time,
                end_time=end_time,
                report_format=format,
            )
        else:
            raise HTTPException(status_code=400, detail=f"不支持的报告类型: {report_type}")

        content = generator.format_report(report, format)

        return ReportContentResponse(content=content, format=format.value)

    return router
