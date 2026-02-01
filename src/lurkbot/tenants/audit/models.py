"""审计日志数据模型

定义审计日志相关的数据结构，包括审计事件、策略评估记录、合规报告等。
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ============================================================================
# 审计事件枚举类型
# ============================================================================


class AuditEventType(str, Enum):
    """审计事件类型"""

    # API 调用
    API_CALL = "api_call"  # API 调用
    API_ERROR = "api_error"  # API 错误

    # 配置变更
    CONFIG_CREATE = "config_create"  # 配置创建
    CONFIG_UPDATE = "config_update"  # 配置更新
    CONFIG_DELETE = "config_delete"  # 配置删除

    # 权限变更
    PERMISSION_GRANT = "permission_grant"  # 权限授予
    PERMISSION_REVOKE = "permission_revoke"  # 权限撤销
    ROLE_ASSIGN = "role_assign"  # 角色分配
    ROLE_REMOVE = "role_remove"  # 角色移除

    # 策略评估
    POLICY_EVALUATE = "policy_evaluate"  # 策略评估
    POLICY_ALLOW = "policy_allow"  # 策略允许
    POLICY_DENY = "policy_deny"  # 策略拒绝

    # 租户操作
    TENANT_CREATE = "tenant_create"  # 租户创建
    TENANT_UPDATE = "tenant_update"  # 租户更新
    TENANT_DELETE = "tenant_delete"  # 租户删除
    TENANT_SUSPEND = "tenant_suspend"  # 租户暂停
    TENANT_ACTIVATE = "tenant_activate"  # 租户激活

    # 配额操作
    QUOTA_UPDATE = "quota_update"  # 配额更新
    QUOTA_EXCEEDED = "quota_exceeded"  # 配额超限
    QUOTA_WARNING = "quota_warning"  # 配额警告

    # 安全事件
    AUTH_SUCCESS = "auth_success"  # 认证成功
    AUTH_FAILURE = "auth_failure"  # 认证失败
    ACCESS_DENIED = "access_denied"  # 访问拒绝
    SUSPICIOUS_ACTIVITY = "suspicious_activity"  # 可疑活动

    # 数据操作
    DATA_EXPORT = "data_export"  # 数据导出
    DATA_IMPORT = "data_import"  # 数据导入
    DATA_DELETE = "data_delete"  # 数据删除

    # 系统事件
    SYSTEM_START = "system_start"  # 系统启动
    SYSTEM_STOP = "system_stop"  # 系统停止
    SYSTEM_ERROR = "system_error"  # 系统错误


class AuditSeverity(str, Enum):
    """审计事件严重级别"""

    DEBUG = "debug"  # 调试
    INFO = "info"  # 信息
    WARNING = "warning"  # 警告
    ERROR = "error"  # 错误
    CRITICAL = "critical"  # 严重


class AuditResult(str, Enum):
    """审计事件结果"""

    SUCCESS = "success"  # 成功
    FAILURE = "failure"  # 失败
    PARTIAL = "partial"  # 部分成功
    DENIED = "denied"  # 被拒绝
    ERROR = "error"  # 错误


class ResourceType(str, Enum):
    """资源类型"""

    TENANT = "tenant"  # 租户
    USER = "user"  # 用户
    AGENT = "agent"  # 代理
    SESSION = "session"  # 会话
    PLUGIN = "plugin"  # 插件
    TOOL = "tool"  # 工具
    CONFIG = "config"  # 配置
    QUOTA = "quota"  # 配额
    POLICY = "policy"  # 策略
    PERMISSION = "permission"  # 权限
    API = "api"  # API
    DATA = "data"  # 数据
    SYSTEM = "system"  # 系统


# ============================================================================
# 审计事件
# ============================================================================


class AuditEvent(BaseModel):
    """审计事件

    记录系统中发生的所有可审计操作。
    """

    # 事件标识
    event_id: str = Field(description="事件唯一 ID")
    event_type: AuditEventType = Field(description="事件类型")
    severity: AuditSeverity = Field(
        default=AuditSeverity.INFO,
        description="严重级别",
    )

    # 时间戳
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="事件时间",
    )

    # 主体信息（谁执行的操作）
    tenant_id: str | None = Field(default=None, description="租户 ID")
    user_id: str | None = Field(default=None, description="用户 ID")
    session_id: str | None = Field(default=None, description="会话 ID")
    client_ip: str | None = Field(default=None, description="客户端 IP")
    user_agent: str | None = Field(default=None, description="用户代理")

    # 操作信息
    action: str = Field(description="操作名称")
    resource_type: ResourceType | None = Field(default=None, description="资源类型")
    resource_id: str | None = Field(default=None, description="资源 ID")
    resource_name: str | None = Field(default=None, description="资源名称")

    # 结果信息
    result: AuditResult = Field(
        default=AuditResult.SUCCESS,
        description="操作结果",
    )
    result_code: int | None = Field(default=None, description="结果代码")
    error_message: str | None = Field(default=None, description="错误信息")

    # 变更详情
    old_value: Any = Field(default=None, description="变更前的值")
    new_value: Any = Field(default=None, description="变更后的值")
    changes: dict[str, Any] = Field(
        default_factory=dict,
        description="变更详情",
    )

    # 请求信息
    request_id: str | None = Field(default=None, description="请求 ID")
    request_method: str | None = Field(default=None, description="请求方法")
    request_path: str | None = Field(default=None, description="请求路径")
    request_params: dict[str, Any] = Field(
        default_factory=dict,
        description="请求参数（脱敏后）",
    )

    # 响应信息
    response_status: int | None = Field(default=None, description="响应状态码")
    response_time_ms: float | None = Field(default=None, description="响应时间（毫秒）")

    # 元数据
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="额外元数据",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="标签",
    )

    # 关联信息
    parent_event_id: str | None = Field(default=None, description="父事件 ID")
    correlation_id: str | None = Field(default=None, description="关联 ID")

    def is_success(self) -> bool:
        """检查操作是否成功"""
        return self.result == AuditResult.SUCCESS

    def is_security_event(self) -> bool:
        """检查是否为安全事件"""
        security_types = {
            AuditEventType.AUTH_SUCCESS,
            AuditEventType.AUTH_FAILURE,
            AuditEventType.ACCESS_DENIED,
            AuditEventType.SUSPICIOUS_ACTIVITY,
            AuditEventType.PERMISSION_GRANT,
            AuditEventType.PERMISSION_REVOKE,
        }
        return self.event_type in security_types

    def is_config_change(self) -> bool:
        """检查是否为配置变更"""
        config_types = {
            AuditEventType.CONFIG_CREATE,
            AuditEventType.CONFIG_UPDATE,
            AuditEventType.CONFIG_DELETE,
        }
        return self.event_type in config_types


# ============================================================================
# 策略评估记录
# ============================================================================


class PolicyEvaluationResult(str, Enum):
    """策略评估结果"""

    ALLOW = "allow"  # 允许
    DENY = "deny"  # 拒绝
    NOT_APPLICABLE = "not_applicable"  # 不适用


class PolicyEvaluation(BaseModel):
    """策略评估记录

    记录策略引擎的评估过程和结果。
    """

    # 评估标识
    evaluation_id: str = Field(description="评估 ID")
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="评估时间",
    )

    # 请求上下文
    tenant_id: str = Field(description="租户 ID")
    user_id: str | None = Field(default=None, description="用户 ID")
    session_id: str | None = Field(default=None, description="会话 ID")

    # 评估请求
    action: str = Field(description="请求的操作")
    resource_type: str = Field(description="资源类型")
    resource_id: str | None = Field(default=None, description="资源 ID")
    context: dict[str, Any] = Field(
        default_factory=dict,
        description="评估上下文",
    )

    # 评估结果
    result: PolicyEvaluationResult = Field(description="评估结果")
    decision_reason: str = Field(default="", description="决策原因")

    # 匹配的策略
    matched_policies: list[str] = Field(
        default_factory=list,
        description="匹配的策略 ID 列表",
    )
    matched_rules: list[str] = Field(
        default_factory=list,
        description="匹配的规则 ID 列表",
    )

    # 拒绝详情（如果被拒绝）
    denial_code: str | None = Field(default=None, description="拒绝代码")
    denial_message: str | None = Field(default=None, description="拒绝消息")
    denial_policy_id: str | None = Field(default=None, description="拒绝策略 ID")
    denial_rule_id: str | None = Field(default=None, description="拒绝规则 ID")

    # 评估详情
    evaluation_time_ms: float = Field(default=0.0, description="评估耗时（毫秒）")
    policies_evaluated: int = Field(default=0, description="评估的策略数")
    rules_evaluated: int = Field(default=0, description="评估的规则数")

    # 元数据
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="额外元数据",
    )

    def is_allowed(self) -> bool:
        """检查是否被允许"""
        return self.result == PolicyEvaluationResult.ALLOW

    def is_denied(self) -> bool:
        """检查是否被拒绝"""
        return self.result == PolicyEvaluationResult.DENY


# ============================================================================
# 审计查询
# ============================================================================


class AuditQuery(BaseModel):
    """审计查询条件"""

    # 时间范围
    start_time: datetime | None = Field(default=None, description="开始时间")
    end_time: datetime | None = Field(default=None, description="结束时间")

    # 过滤条件
    tenant_ids: list[str] | None = Field(default=None, description="租户 ID 列表")
    user_ids: list[str] | None = Field(default=None, description="用户 ID 列表")
    event_types: list[AuditEventType] | None = Field(
        default=None,
        description="事件类型列表",
    )
    severities: list[AuditSeverity] | None = Field(
        default=None,
        description="严重级别列表",
    )
    results: list[AuditResult] | None = Field(default=None, description="结果列表")
    resource_types: list[ResourceType] | None = Field(
        default=None,
        description="资源类型列表",
    )
    resource_ids: list[str] | None = Field(default=None, description="资源 ID 列表")

    # 搜索
    action_pattern: str | None = Field(default=None, description="操作名称模式")
    keyword: str | None = Field(default=None, description="关键词搜索")

    # 分页
    offset: int = Field(default=0, ge=0, description="偏移量")
    limit: int = Field(default=100, ge=1, le=1000, description="限制数量")

    # 排序
    order_by: str = Field(default="timestamp", description="排序字段")
    order_desc: bool = Field(default=True, description="是否降序")


class PolicyEvaluationQuery(BaseModel):
    """策略评估查询条件"""

    # 时间范围
    start_time: datetime | None = Field(default=None, description="开始时间")
    end_time: datetime | None = Field(default=None, description="结束时间")

    # 过滤条件
    tenant_ids: list[str] | None = Field(default=None, description="租户 ID 列表")
    user_ids: list[str] | None = Field(default=None, description="用户 ID 列表")
    results: list[PolicyEvaluationResult] | None = Field(
        default=None,
        description="结果列表",
    )
    policy_ids: list[str] | None = Field(default=None, description="策略 ID 列表")
    actions: list[str] | None = Field(default=None, description="操作列表")
    resource_types: list[str] | None = Field(default=None, description="资源类型列表")

    # 分页
    offset: int = Field(default=0, ge=0, description="偏移量")
    limit: int = Field(default=100, ge=1, le=1000, description="限制数量")

    # 排序
    order_by: str = Field(default="timestamp", description="排序字段")
    order_desc: bool = Field(default=True, description="是否降序")


# ============================================================================
# 审计统计
# ============================================================================


class AuditStats(BaseModel):
    """审计统计"""

    # 统计范围
    tenant_id: str | None = Field(
        default=None,
        description="租户 ID，None 表示全局统计",
    )
    period_start: datetime = Field(description="统计周期开始")
    period_end: datetime = Field(description="统计周期结束")

    # 事件计数
    total_events: int = Field(default=0, description="总事件数")
    success_events: int = Field(default=0, description="成功事件数")
    failure_events: int = Field(default=0, description="失败事件数")
    denied_events: int = Field(default=0, description="拒绝事件数")

    # 按类型统计
    by_event_type: dict[str, int] = Field(
        default_factory=dict,
        description="按事件类型统计",
    )

    # 按严重级别统计
    by_severity: dict[str, int] = Field(
        default_factory=dict,
        description="按严重级别统计",
    )

    # 按资源类型统计
    by_resource_type: dict[str, int] = Field(
        default_factory=dict,
        description="按资源类型统计",
    )

    # 按结果统计
    by_result: dict[str, int] = Field(
        default_factory=dict,
        description="按结果统计",
    )

    # 安全统计
    security_events: int = Field(default=0, description="安全事件数")
    auth_failures: int = Field(default=0, description="认证失败数")
    access_denials: int = Field(default=0, description="访问拒绝数")

    # 配置变更统计
    config_changes: int = Field(default=0, description="配置变更数")

    # 活跃用户
    unique_users: int = Field(default=0, description="唯一用户数")
    unique_sessions: int = Field(default=0, description="唯一会话数")


class PolicyEvaluationStats(BaseModel):
    """策略评估统计"""

    # 统计范围
    tenant_id: str | None = Field(
        default=None,
        description="租户 ID，None 表示全局统计",
    )
    period_start: datetime = Field(description="统计周期开始")
    period_end: datetime = Field(description="统计周期结束")

    # 评估计数
    total_evaluations: int = Field(default=0, description="总评估数")
    allow_count: int = Field(default=0, description="允许数")
    deny_count: int = Field(default=0, description="拒绝数")
    not_applicable_count: int = Field(default=0, description="不适用数")

    # 按策略统计
    by_policy: dict[str, int] = Field(
        default_factory=dict,
        description="按策略统计",
    )

    # 按操作统计
    by_action: dict[str, int] = Field(
        default_factory=dict,
        description="按操作统计",
    )

    # 按资源类型统计
    by_resource_type: dict[str, int] = Field(
        default_factory=dict,
        description="按资源类型统计",
    )

    # 拒绝原因统计
    denial_reasons: dict[str, int] = Field(
        default_factory=dict,
        description="拒绝原因统计",
    )

    # 性能统计
    avg_evaluation_time_ms: float = Field(default=0.0, description="平均评估时间（毫秒）")
    max_evaluation_time_ms: float = Field(default=0.0, description="最大评估时间（毫秒）")
    min_evaluation_time_ms: float = Field(default=0.0, description="最小评估时间（毫秒）")


# ============================================================================
# 合规报告
# ============================================================================


class ReportType(str, Enum):
    """报告类型"""

    USAGE = "usage"  # 使用量报告
    SECURITY_AUDIT = "security_audit"  # 安全审计报告
    COMPLIANCE = "compliance"  # 合规检查报告
    POLICY_EVALUATION = "policy_evaluation"  # 策略评估报告
    ACCESS_REVIEW = "access_review"  # 访问审查报告


class ReportFormat(str, Enum):
    """报告格式"""

    JSON = "json"  # JSON 格式
    MARKDOWN = "markdown"  # Markdown 格式
    HTML = "html"  # HTML 格式
    CSV = "csv"  # CSV 格式


class ReportStatus(str, Enum):
    """报告状态"""

    PENDING = "pending"  # 待生成
    GENERATING = "generating"  # 生成中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"  # 失败


class ComplianceReport(BaseModel):
    """合规报告"""

    # 报告标识
    report_id: str = Field(description="报告 ID")
    report_type: ReportType = Field(description="报告类型")
    report_format: ReportFormat = Field(
        default=ReportFormat.JSON,
        description="报告格式",
    )

    # 报告范围
    tenant_id: str | None = Field(default=None, description="租户 ID")
    period_start: datetime = Field(description="报告周期开始")
    period_end: datetime = Field(description="报告周期结束")

    # 报告状态
    status: ReportStatus = Field(
        default=ReportStatus.PENDING,
        description="报告状态",
    )
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="创建时间",
    )
    completed_at: datetime | None = Field(default=None, description="完成时间")
    error_message: str | None = Field(default=None, description="错误信息")

    # 报告内容
    title: str = Field(description="报告标题")
    summary: str = Field(default="", description="报告摘要")
    content: dict[str, Any] = Field(
        default_factory=dict,
        description="报告内容",
    )

    # 统计数据
    statistics: dict[str, Any] = Field(
        default_factory=dict,
        description="统计数据",
    )

    # 合规检查结果
    compliance_checks: list[dict[str, Any]] = Field(
        default_factory=list,
        description="合规检查项",
    )
    passed_checks: int = Field(default=0, description="通过检查数")
    failed_checks: int = Field(default=0, description="失败检查数")
    warning_checks: int = Field(default=0, description="警告检查数")

    # 建议
    recommendations: list[str] = Field(
        default_factory=list,
        description="改进建议",
    )

    # 元数据
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="报告元数据",
    )
    generated_by: str | None = Field(default=None, description="生成者")

    def is_completed(self) -> bool:
        """检查报告是否完成"""
        return self.status == ReportStatus.COMPLETED

    def compliance_rate(self) -> float:
        """计算合规率"""
        total = self.passed_checks + self.failed_checks + self.warning_checks
        if total == 0:
            return 100.0
        return (self.passed_checks / total) * 100


# ============================================================================
# 合规检查项
# ============================================================================


class ComplianceCheckResult(str, Enum):
    """合规检查结果"""

    PASS = "pass"  # 通过
    FAIL = "fail"  # 失败
    WARNING = "warning"  # 警告
    NOT_APPLICABLE = "not_applicable"  # 不适用
    ERROR = "error"  # 错误


class ComplianceCheck(BaseModel):
    """合规检查项"""

    # 检查标识
    check_id: str = Field(description="检查项 ID")
    check_name: str = Field(description="检查项名称")
    check_category: str = Field(description="检查类别")
    description: str = Field(default="", description="检查描述")

    # 检查结果
    result: ComplianceCheckResult = Field(description="检查结果")
    message: str = Field(default="", description="结果消息")
    details: dict[str, Any] = Field(
        default_factory=dict,
        description="详细信息",
    )

    # 严重性
    severity: AuditSeverity = Field(
        default=AuditSeverity.INFO,
        description="严重级别",
    )

    # 修复建议
    remediation: str | None = Field(default=None, description="修复建议")
    reference: str | None = Field(default=None, description="参考链接")

    # 时间戳
    checked_at: datetime = Field(
        default_factory=datetime.now,
        description="检查时间",
    )
