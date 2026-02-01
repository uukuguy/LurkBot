"""合规报告生成器

提供使用量报告、安全审计报告和合规检查报告的生成功能。
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta
from typing import Any

from loguru import logger

from .models import (
    AuditEventType,
    AuditQuery,
    AuditResult,
    AuditSeverity,
    AuditStats,
    ComplianceCheck,
    ComplianceCheckResult,
    ComplianceReport,
    PolicyEvaluationQuery,
    PolicyEvaluationResult,
    PolicyEvaluationStats,
    ReportFormat,
    ReportStatus,
    ReportType,
)
from .storage import AuditStorage, MemoryAuditStorage


# ============================================================================
# 合规报告生成器
# ============================================================================


class ReportGenerator:
    """合规报告生成器

    提供各类合规报告的生成功能。
    """

    def __init__(
        self,
        storage: AuditStorage | None = None,
    ) -> None:
        """初始化报告生成器

        Args:
            storage: 审计存储
        """
        self._storage = storage or MemoryAuditStorage()
        logger.info("合规报告生成器初始化完成")

    # =========================================================================
    # 属性
    # =========================================================================

    @property
    def storage(self) -> AuditStorage:
        """获取存储"""
        return self._storage

    # =========================================================================
    # 使用量报告
    # =========================================================================

    async def generate_usage_report(
        self,
        tenant_id: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        report_format: ReportFormat = ReportFormat.JSON,
    ) -> ComplianceReport:
        """生成使用量报告

        Args:
            tenant_id: 租户 ID
            start_time: 开始时间
            end_time: 结束时间
            report_format: 报告格式

        Returns:
            使用量报告
        """
        now = datetime.now()
        start = start_time or (now - timedelta(days=30))
        end = end_time or now

        report = ComplianceReport(
            report_id=str(uuid.uuid4()),
            report_type=ReportType.USAGE,
            report_format=report_format,
            tenant_id=tenant_id,
            period_start=start,
            period_end=end,
            status=ReportStatus.GENERATING,
            title="使用量报告",
        )

        try:
            # 获取审计统计
            audit_stats = await self._storage.get_event_stats(
                tenant_id=tenant_id,
                start_time=start,
                end_time=end,
            )

            # 获取策略评估统计
            policy_stats = await self._storage.get_policy_evaluation_stats(
                tenant_id=tenant_id,
                start_time=start,
                end_time=end,
            )

            # 构建报告内容
            content = {
                "overview": {
                    "total_events": audit_stats.total_events,
                    "success_events": audit_stats.success_events,
                    "failure_events": audit_stats.failure_events,
                    "unique_users": audit_stats.unique_users,
                    "unique_sessions": audit_stats.unique_sessions,
                },
                "api_usage": {
                    "total_calls": audit_stats.by_event_type.get("api_call", 0),
                    "error_calls": audit_stats.by_event_type.get("api_error", 0),
                },
                "policy_evaluations": {
                    "total": policy_stats.total_evaluations,
                    "allowed": policy_stats.allow_count,
                    "denied": policy_stats.deny_count,
                    "avg_time_ms": policy_stats.avg_evaluation_time_ms,
                },
                "by_event_type": audit_stats.by_event_type,
                "by_severity": audit_stats.by_severity,
            }

            # 统计数据
            statistics = {
                "period_days": (end - start).days,
                "events_per_day": audit_stats.total_events / max((end - start).days, 1),
                "success_rate": (
                    audit_stats.success_events / audit_stats.total_events * 100
                    if audit_stats.total_events > 0
                    else 0
                ),
            }

            report.content = content
            report.statistics = statistics
            report.summary = self._generate_usage_summary(audit_stats, policy_stats)
            report.status = ReportStatus.COMPLETED
            report.completed_at = datetime.now()

        except Exception as e:
            logger.error(f"生成使用量报告失败: {e}")
            report.status = ReportStatus.FAILED
            report.error_message = str(e)

        return report

    def _generate_usage_summary(
        self,
        audit_stats: AuditStats,
        policy_stats: PolicyEvaluationStats,
    ) -> str:
        """生成使用量摘要"""
        lines = [
            f"报告周期: {audit_stats.period_start.strftime('%Y-%m-%d')} 至 {audit_stats.period_end.strftime('%Y-%m-%d')}",
            f"总事件数: {audit_stats.total_events}",
            f"成功率: {audit_stats.success_events / audit_stats.total_events * 100:.1f}%" if audit_stats.total_events > 0 else "成功率: N/A",
            f"唯一用户数: {audit_stats.unique_users}",
            f"策略评估总数: {policy_stats.total_evaluations}",
            f"策略拒绝数: {policy_stats.deny_count}",
        ]
        return "\n".join(lines)

    # =========================================================================
    # 安全审计报告
    # =========================================================================

    async def generate_security_audit_report(
        self,
        tenant_id: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        report_format: ReportFormat = ReportFormat.JSON,
    ) -> ComplianceReport:
        """生成安全审计报告

        Args:
            tenant_id: 租户 ID
            start_time: 开始时间
            end_time: 结束时间
            report_format: 报告格式

        Returns:
            安全审计报告
        """
        now = datetime.now()
        start = start_time or (now - timedelta(days=30))
        end = end_time or now

        report = ComplianceReport(
            report_id=str(uuid.uuid4()),
            report_type=ReportType.SECURITY_AUDIT,
            report_format=report_format,
            tenant_id=tenant_id,
            period_start=start,
            period_end=end,
            status=ReportStatus.GENERATING,
            title="安全审计报告",
        )

        try:
            # 获取审计统计
            audit_stats = await self._storage.get_event_stats(
                tenant_id=tenant_id,
                start_time=start,
                end_time=end,
            )

            # 查询安全相关事件
            security_query = AuditQuery(
                tenant_ids=[tenant_id] if tenant_id else None,
                event_types=[
                    AuditEventType.AUTH_SUCCESS,
                    AuditEventType.AUTH_FAILURE,
                    AuditEventType.ACCESS_DENIED,
                    AuditEventType.SUSPICIOUS_ACTIVITY,
                    AuditEventType.PERMISSION_GRANT,
                    AuditEventType.PERMISSION_REVOKE,
                ],
                start_time=start,
                end_time=end,
                limit=1000,
            )
            security_events = await self._storage.query_events(security_query)

            # 分析安全事件
            auth_failures = [e for e in security_events if e.event_type == AuditEventType.AUTH_FAILURE]
            access_denials = [e for e in security_events if e.event_type == AuditEventType.ACCESS_DENIED]
            suspicious = [e for e in security_events if e.event_type == AuditEventType.SUSPICIOUS_ACTIVITY]
            permission_changes = [
                e for e in security_events
                if e.event_type in [AuditEventType.PERMISSION_GRANT, AuditEventType.PERMISSION_REVOKE]
            ]

            # 构建报告内容
            content = {
                "security_overview": {
                    "total_security_events": audit_stats.security_events,
                    "auth_failures": audit_stats.auth_failures,
                    "access_denials": audit_stats.access_denials,
                    "suspicious_activities": len(suspicious),
                    "permission_changes": len(permission_changes),
                },
                "auth_failure_details": self._analyze_auth_failures(auth_failures),
                "access_denial_details": self._analyze_access_denials(access_denials),
                "permission_change_summary": self._summarize_permission_changes(permission_changes),
            }

            # 执行安全检查
            checks = await self._run_security_checks(audit_stats, security_events)
            report.compliance_checks = [c.model_dump() for c in checks]
            report.passed_checks = len([c for c in checks if c.result == ComplianceCheckResult.PASS])
            report.failed_checks = len([c for c in checks if c.result == ComplianceCheckResult.FAIL])
            report.warning_checks = len([c for c in checks if c.result == ComplianceCheckResult.WARNING])

            # 生成建议
            report.recommendations = self._generate_security_recommendations(checks, audit_stats)

            report.content = content
            report.summary = self._generate_security_summary(audit_stats, checks)
            report.status = ReportStatus.COMPLETED
            report.completed_at = datetime.now()

        except Exception as e:
            logger.error(f"生成安全审计报告失败: {e}")
            report.status = ReportStatus.FAILED
            report.error_message = str(e)

        return report

    def _analyze_auth_failures(self, events: list) -> dict[str, Any]:
        """分析认证失败"""
        if not events:
            return {"count": 0, "by_user": {}, "by_ip": {}}

        by_user: dict[str, int] = {}
        by_ip: dict[str, int] = {}

        for event in events:
            if event.user_id:
                by_user[event.user_id] = by_user.get(event.user_id, 0) + 1
            if event.client_ip:
                by_ip[event.client_ip] = by_ip.get(event.client_ip, 0) + 1

        return {
            "count": len(events),
            "by_user": dict(sorted(by_user.items(), key=lambda x: x[1], reverse=True)[:10]),
            "by_ip": dict(sorted(by_ip.items(), key=lambda x: x[1], reverse=True)[:10]),
        }

    def _analyze_access_denials(self, events: list) -> dict[str, Any]:
        """分析访问拒绝"""
        if not events:
            return {"count": 0, "by_action": {}, "by_resource": {}}

        by_action: dict[str, int] = {}
        by_resource: dict[str, int] = {}

        for event in events:
            by_action[event.action] = by_action.get(event.action, 0) + 1
            if event.resource_type:
                by_resource[event.resource_type.value] = by_resource.get(event.resource_type.value, 0) + 1

        return {
            "count": len(events),
            "by_action": dict(sorted(by_action.items(), key=lambda x: x[1], reverse=True)[:10]),
            "by_resource": dict(sorted(by_resource.items(), key=lambda x: x[1], reverse=True)[:10]),
        }

    def _summarize_permission_changes(self, events: list) -> dict[str, Any]:
        """汇总权限变更"""
        grants = [e for e in events if e.event_type == AuditEventType.PERMISSION_GRANT]
        revokes = [e for e in events if e.event_type == AuditEventType.PERMISSION_REVOKE]

        return {
            "total_changes": len(events),
            "grants": len(grants),
            "revokes": len(revokes),
        }

    async def _run_security_checks(
        self,
        stats: AuditStats,
        events: list,
    ) -> list[ComplianceCheck]:
        """执行安全检查"""
        checks = []

        # 检查 1: 认证失败率
        total_auth = stats.by_event_type.get("auth_success", 0) + stats.auth_failures
        if total_auth > 0:
            failure_rate = stats.auth_failures / total_auth * 100
            checks.append(ComplianceCheck(
                check_id="SEC-001",
                check_name="认证失败率检查",
                check_category="认证安全",
                description="检查认证失败率是否在可接受范围内",
                result=ComplianceCheckResult.PASS if failure_rate < 10 else (
                    ComplianceCheckResult.WARNING if failure_rate < 20 else ComplianceCheckResult.FAIL
                ),
                message=f"认证失败率: {failure_rate:.1f}%",
                details={"failure_rate": failure_rate, "threshold": 10},
                severity=AuditSeverity.WARNING if failure_rate >= 10 else AuditSeverity.INFO,
                remediation="检查是否存在暴力破解攻击，考虑启用账户锁定策略" if failure_rate >= 10 else None,
            ))

        # 检查 2: 访问拒绝率
        if stats.total_events > 0:
            denial_rate = stats.access_denials / stats.total_events * 100
            checks.append(ComplianceCheck(
                check_id="SEC-002",
                check_name="访问拒绝率检查",
                check_category="访问控制",
                description="检查访问拒绝率是否异常",
                result=ComplianceCheckResult.PASS if denial_rate < 5 else (
                    ComplianceCheckResult.WARNING if denial_rate < 15 else ComplianceCheckResult.FAIL
                ),
                message=f"访问拒绝率: {denial_rate:.1f}%",
                details={"denial_rate": denial_rate, "threshold": 5},
                severity=AuditSeverity.WARNING if denial_rate >= 5 else AuditSeverity.INFO,
                remediation="检查权限配置是否正确，或是否存在未授权访问尝试" if denial_rate >= 5 else None,
            ))

        # 检查 3: 可疑活动
        suspicious_count = len([e for e in events if e.event_type == AuditEventType.SUSPICIOUS_ACTIVITY])
        checks.append(ComplianceCheck(
            check_id="SEC-003",
            check_name="可疑活动检查",
            check_category="威胁检测",
            description="检查是否存在可疑活动",
            result=ComplianceCheckResult.PASS if suspicious_count == 0 else (
                ComplianceCheckResult.WARNING if suspicious_count < 5 else ComplianceCheckResult.FAIL
            ),
            message=f"可疑活动数: {suspicious_count}",
            details={"suspicious_count": suspicious_count},
            severity=AuditSeverity.ERROR if suspicious_count >= 5 else (
                AuditSeverity.WARNING if suspicious_count > 0 else AuditSeverity.INFO
            ),
            remediation="立即调查可疑活动，检查是否存在安全威胁" if suspicious_count > 0 else None,
        ))

        # 检查 4: 配置变更审计
        config_changes = stats.config_changes
        checks.append(ComplianceCheck(
            check_id="SEC-004",
            check_name="配置变更审计",
            check_category="变更管理",
            description="检查配置变更是否被正确记录",
            result=ComplianceCheckResult.PASS,
            message=f"配置变更数: {config_changes}",
            details={"config_changes": config_changes},
            severity=AuditSeverity.INFO,
        ))

        return checks

    def _generate_security_recommendations(
        self,
        checks: list[ComplianceCheck],
        stats: AuditStats,
    ) -> list[str]:
        """生成安全建议"""
        recommendations = []

        for check in checks:
            if check.result in [ComplianceCheckResult.FAIL, ComplianceCheckResult.WARNING]:
                if check.remediation:
                    recommendations.append(f"[{check.check_id}] {check.remediation}")

        if stats.auth_failures > 100:
            recommendations.append("建议启用多因素认证以增强账户安全")

        if stats.access_denials > 50:
            recommendations.append("建议审查访问控制策略，确保权限配置正确")

        return recommendations

    def _generate_security_summary(
        self,
        stats: AuditStats,
        checks: list[ComplianceCheck],
    ) -> str:
        """生成安全摘要"""
        passed = len([c for c in checks if c.result == ComplianceCheckResult.PASS])
        failed = len([c for c in checks if c.result == ComplianceCheckResult.FAIL])
        warnings = len([c for c in checks if c.result == ComplianceCheckResult.WARNING])

        lines = [
            f"报告周期: {stats.period_start.strftime('%Y-%m-%d')} 至 {stats.period_end.strftime('%Y-%m-%d')}",
            f"安全事件总数: {stats.security_events}",
            f"认证失败: {stats.auth_failures}",
            f"访问拒绝: {stats.access_denials}",
            f"安全检查: 通过 {passed}, 警告 {warnings}, 失败 {failed}",
        ]
        return "\n".join(lines)

    # =========================================================================
    # 合规检查报告
    # =========================================================================

    async def generate_compliance_report(
        self,
        tenant_id: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        report_format: ReportFormat = ReportFormat.JSON,
    ) -> ComplianceReport:
        """生成合规检查报告

        Args:
            tenant_id: 租户 ID
            start_time: 开始时间
            end_time: 结束时间
            report_format: 报告格式

        Returns:
            合规检查报告
        """
        now = datetime.now()
        start = start_time or (now - timedelta(days=30))
        end = end_time or now

        report = ComplianceReport(
            report_id=str(uuid.uuid4()),
            report_type=ReportType.COMPLIANCE,
            report_format=report_format,
            tenant_id=tenant_id,
            period_start=start,
            period_end=end,
            status=ReportStatus.GENERATING,
            title="合规检查报告",
        )

        try:
            # 获取统计数据
            audit_stats = await self._storage.get_event_stats(
                tenant_id=tenant_id,
                start_time=start,
                end_time=end,
            )

            policy_stats = await self._storage.get_policy_evaluation_stats(
                tenant_id=tenant_id,
                start_time=start,
                end_time=end,
            )

            # 执行合规检查
            checks = await self._run_compliance_checks(audit_stats, policy_stats)

            # 构建报告内容
            content = {
                "compliance_overview": {
                    "total_checks": len(checks),
                    "passed": len([c for c in checks if c.result == ComplianceCheckResult.PASS]),
                    "failed": len([c for c in checks if c.result == ComplianceCheckResult.FAIL]),
                    "warnings": len([c for c in checks if c.result == ComplianceCheckResult.WARNING]),
                },
                "audit_coverage": {
                    "total_events": audit_stats.total_events,
                    "event_types_covered": len(audit_stats.by_event_type),
                },
                "policy_enforcement": {
                    "total_evaluations": policy_stats.total_evaluations,
                    "denial_rate": (
                        policy_stats.deny_count / policy_stats.total_evaluations * 100
                        if policy_stats.total_evaluations > 0
                        else 0
                    ),
                },
            }

            report.compliance_checks = [c.model_dump() for c in checks]
            report.passed_checks = len([c for c in checks if c.result == ComplianceCheckResult.PASS])
            report.failed_checks = len([c for c in checks if c.result == ComplianceCheckResult.FAIL])
            report.warning_checks = len([c for c in checks if c.result == ComplianceCheckResult.WARNING])

            # 生成建议
            report.recommendations = self._generate_compliance_recommendations(checks)

            report.content = content
            report.summary = self._generate_compliance_summary(checks)
            report.status = ReportStatus.COMPLETED
            report.completed_at = datetime.now()

        except Exception as e:
            logger.error(f"生成合规检查报告失败: {e}")
            report.status = ReportStatus.FAILED
            report.error_message = str(e)

        return report

    async def _run_compliance_checks(
        self,
        audit_stats: AuditStats,
        policy_stats: PolicyEvaluationStats,
    ) -> list[ComplianceCheck]:
        """执行合规检查"""
        checks = []

        # 检查 1: 审计日志完整性
        checks.append(ComplianceCheck(
            check_id="COMP-001",
            check_name="审计日志完整性",
            check_category="审计",
            description="检查审计日志是否完整记录",
            result=ComplianceCheckResult.PASS if audit_stats.total_events > 0 else ComplianceCheckResult.WARNING,
            message=f"审计事件总数: {audit_stats.total_events}",
            details={"total_events": audit_stats.total_events},
            severity=AuditSeverity.INFO,
        ))

        # 检查 2: 策略执行
        checks.append(ComplianceCheck(
            check_id="COMP-002",
            check_name="策略执行检查",
            check_category="访问控制",
            description="检查策略是否正确执行",
            result=ComplianceCheckResult.PASS if policy_stats.total_evaluations > 0 else ComplianceCheckResult.WARNING,
            message=f"策略评估总数: {policy_stats.total_evaluations}",
            details={
                "total_evaluations": policy_stats.total_evaluations,
                "allow_count": policy_stats.allow_count,
                "deny_count": policy_stats.deny_count,
            },
            severity=AuditSeverity.INFO,
        ))

        # 检查 3: 错误率
        if audit_stats.total_events > 0:
            error_rate = audit_stats.failure_events / audit_stats.total_events * 100
            checks.append(ComplianceCheck(
                check_id="COMP-003",
                check_name="系统错误率检查",
                check_category="可靠性",
                description="检查系统错误率是否在可接受范围内",
                result=ComplianceCheckResult.PASS if error_rate < 5 else (
                    ComplianceCheckResult.WARNING if error_rate < 10 else ComplianceCheckResult.FAIL
                ),
                message=f"错误率: {error_rate:.1f}%",
                details={"error_rate": error_rate, "threshold": 5},
                severity=AuditSeverity.WARNING if error_rate >= 5 else AuditSeverity.INFO,
                remediation="检查系统日志，排查错误原因" if error_rate >= 5 else None,
            ))

        # 检查 4: 数据保护
        data_events = (
            audit_stats.by_event_type.get("data_export", 0) +
            audit_stats.by_event_type.get("data_delete", 0)
        )
        checks.append(ComplianceCheck(
            check_id="COMP-004",
            check_name="数据操作审计",
            check_category="数据保护",
            description="检查数据操作是否被审计",
            result=ComplianceCheckResult.PASS,
            message=f"数据操作事件: {data_events}",
            details={"data_events": data_events},
            severity=AuditSeverity.INFO,
        ))

        # 检查 5: 配置变更控制
        checks.append(ComplianceCheck(
            check_id="COMP-005",
            check_name="配置变更控制",
            check_category="变更管理",
            description="检查配置变更是否受控",
            result=ComplianceCheckResult.PASS,
            message=f"配置变更数: {audit_stats.config_changes}",
            details={"config_changes": audit_stats.config_changes},
            severity=AuditSeverity.INFO,
        ))

        return checks

    def _generate_compliance_recommendations(
        self,
        checks: list[ComplianceCheck],
    ) -> list[str]:
        """生成合规建议"""
        recommendations = []

        for check in checks:
            if check.result in [ComplianceCheckResult.FAIL, ComplianceCheckResult.WARNING]:
                if check.remediation:
                    recommendations.append(f"[{check.check_id}] {check.remediation}")

        if not recommendations:
            recommendations.append("所有合规检查通过，继续保持良好的安全实践")

        return recommendations

    def _generate_compliance_summary(self, checks: list[ComplianceCheck]) -> str:
        """生成合规摘要"""
        passed = len([c for c in checks if c.result == ComplianceCheckResult.PASS])
        failed = len([c for c in checks if c.result == ComplianceCheckResult.FAIL])
        warnings = len([c for c in checks if c.result == ComplianceCheckResult.WARNING])
        total = len(checks)

        compliance_rate = (passed / total * 100) if total > 0 else 0

        lines = [
            f"合规检查总数: {total}",
            f"通过: {passed}, 警告: {warnings}, 失败: {failed}",
            f"合规率: {compliance_rate:.1f}%",
        ]
        return "\n".join(lines)

    # =========================================================================
    # 报告格式化
    # =========================================================================

    def format_report(
        self,
        report: ComplianceReport,
        format_type: ReportFormat | None = None,
    ) -> str:
        """格式化报告

        Args:
            report: 报告对象
            format_type: 格式类型（默认使用报告自身的格式）

        Returns:
            格式化后的报告字符串
        """
        fmt = format_type or report.report_format

        if fmt == ReportFormat.JSON:
            return self._format_json(report)
        elif fmt == ReportFormat.MARKDOWN:
            return self._format_markdown(report)
        else:
            return self._format_json(report)

    def _format_json(self, report: ComplianceReport) -> str:
        """格式化为 JSON"""
        return json.dumps(report.model_dump(), indent=2, default=str, ensure_ascii=False)

    def _format_markdown(self, report: ComplianceReport) -> str:
        """格式化为 Markdown"""
        lines = [
            f"# {report.title}",
            "",
            f"**报告 ID**: {report.report_id}",
            f"**报告类型**: {report.report_type.value}",
            f"**生成时间**: {report.created_at.strftime('%Y-%m-%d %H:%M:%S')}",
            f"**报告周期**: {report.period_start.strftime('%Y-%m-%d')} 至 {report.period_end.strftime('%Y-%m-%d')}",
            "",
            "## 摘要",
            "",
            report.summary,
            "",
        ]

        if report.compliance_checks:
            lines.extend([
                "## 合规检查结果",
                "",
                f"- 通过: {report.passed_checks}",
                f"- 警告: {report.warning_checks}",
                f"- 失败: {report.failed_checks}",
                f"- 合规率: {report.compliance_rate():.1f}%",
                "",
            ])

        if report.recommendations:
            lines.extend([
                "## 建议",
                "",
            ])
            for rec in report.recommendations:
                lines.append(f"- {rec}")
            lines.append("")

        return "\n".join(lines)
