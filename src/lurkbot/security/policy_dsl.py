"""策略 DSL（领域特定语言）

提供权限策略定义和解析功能。
"""

from __future__ import annotations

from datetime import datetime, time
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ============================================================================
# 策略效果
# ============================================================================


class PolicyEffect(str, Enum):
    """策略效果"""

    ALLOW = "allow"  # 允许
    DENY = "deny"  # 拒绝


# ============================================================================
# 条件类型
# ============================================================================


class TimeCondition(BaseModel):
    """时间条件"""

    after: str | None = Field(default=None, description="开始时间 (HH:MM)")
    before: str | None = Field(default=None, description="结束时间 (HH:MM)")
    weekdays: list[int] | None = Field(
        default=None,
        description="允许的星期几 (1=周一, 7=周日)",
    )
    timezone: str = Field(default="UTC", description="时区")

    def evaluate(self, now: datetime | None = None) -> bool:
        """评估时间条件

        Args:
            now: 当前时间（默认为 datetime.now()）

        Returns:
            是否满足条件
        """
        if now is None:
            now = datetime.now()

        # 检查星期几
        if self.weekdays is not None:
            # isoweekday(): Monday=1, Sunday=7
            if now.isoweekday() not in self.weekdays:
                return False

        # 检查时间范围
        current_time = now.time()

        if self.after is not None:
            parts = self.after.split(":")
            after_time = time(int(parts[0]), int(parts[1]))
            if current_time < after_time:
                return False

        if self.before is not None:
            parts = self.before.split(":")
            before_time = time(int(parts[0]), int(parts[1]))
            if current_time > before_time:
                return False

        return True


class IPCondition(BaseModel):
    """IP 条件"""

    in_cidrs: list[str] | None = Field(default=None, description="允许的 CIDR 列表")
    not_in_cidrs: list[str] | None = Field(default=None, description="禁止的 CIDR 列表")
    allowed_ips: list[str] | None = Field(default=None, description="允许的 IP 列表")

    def evaluate(self, ip: str | None) -> bool:
        """评估 IP 条件

        Args:
            ip: 客户端 IP 地址

        Returns:
            是否满足条件
        """
        if ip is None:
            return True  # 无 IP 信息时默认通过

        # 简单 IP 匹配
        if self.allowed_ips is not None:
            if ip not in self.allowed_ips:
                return False

        # CIDR 匹配
        if self.in_cidrs is not None:
            if not any(self._match_cidr(ip, cidr) for cidr in self.in_cidrs):
                return False

        if self.not_in_cidrs is not None:
            if any(self._match_cidr(ip, cidr) for cidr in self.not_in_cidrs):
                return False

        return True

    @staticmethod
    def _match_cidr(ip: str, cidr: str) -> bool:
        """简单 CIDR 匹配

        Args:
            ip: IP 地址
            cidr: CIDR 表示

        Returns:
            是否匹配
        """
        if "/" not in cidr:
            return ip == cidr

        network, prefix_len = cidr.split("/")
        prefix_len = int(prefix_len)

        ip_parts = [int(p) for p in ip.split(".")]
        net_parts = [int(p) for p in network.split(".")]

        if len(ip_parts) != 4 or len(net_parts) != 4:
            return False

        ip_int = (ip_parts[0] << 24) + (ip_parts[1] << 16) + (ip_parts[2] << 8) + ip_parts[3]
        net_int = (net_parts[0] << 24) + (net_parts[1] << 16) + (net_parts[2] << 8) + net_parts[3]
        mask = ((1 << 32) - 1) << (32 - prefix_len)

        return (ip_int & mask) == (net_int & mask)


class AttributeCondition(BaseModel):
    """属性条件"""

    key: str = Field(description="属性键")
    operator: str = Field(
        default="eq",
        description="比较运算符: eq, ne, in, not_in, gt, lt, gte, lte, contains",
    )
    value: Any = Field(description="比较值")

    def evaluate(self, attributes: dict[str, Any]) -> bool:
        """评估属性条件

        Args:
            attributes: 属性字典

        Returns:
            是否满足条件
        """
        actual = attributes.get(self.key)
        if actual is None:
            return self.operator == "ne"

        if self.operator == "eq":
            return actual == self.value
        elif self.operator == "ne":
            return actual != self.value
        elif self.operator == "in":
            return actual in self.value
        elif self.operator == "not_in":
            return actual not in self.value
        elif self.operator == "gt":
            return actual > self.value
        elif self.operator == "lt":
            return actual < self.value
        elif self.operator == "gte":
            return actual >= self.value
        elif self.operator == "lte":
            return actual <= self.value
        elif self.operator == "contains":
            return self.value in actual
        else:
            return False


# ============================================================================
# 策略条件
# ============================================================================


class PolicyConditions(BaseModel):
    """策略条件集合"""

    time: TimeCondition | None = Field(default=None, description="时间条件")
    ip: IPCondition | None = Field(default=None, description="IP 条件")
    attributes: list[AttributeCondition] | None = Field(
        default=None, description="属性条件列表"
    )

    def evaluate(self, context: "EvaluationContext") -> bool:
        """评估所有条件

        Args:
            context: 评估上下文

        Returns:
            是否所有条件都满足
        """
        # 时间条件
        if self.time is not None:
            if not self.time.evaluate(context.timestamp):
                return False

        # IP 条件
        if self.ip is not None:
            if not self.ip.evaluate(context.ip_address):
                return False

        # 属性条件（所有条件必须满足 - AND 逻辑）
        if self.attributes is not None:
            for attr_cond in self.attributes:
                if not attr_cond.evaluate(context.attributes):
                    return False

        return True


# ============================================================================
# 策略定义
# ============================================================================


class Policy(BaseModel):
    """策略定义

    基于 YAML/JSON 友好格式的策略描述。
    """

    name: str = Field(description="策略名称")
    description: str = Field(default="", description="策略描述")
    effect: PolicyEffect = Field(description="策略效果")
    priority: int = Field(default=0, description="优先级（越大越高）")

    # 主体匹配
    principals: list[str] = Field(
        default_factory=list,
        description="主体列表（role:xxx, user:xxx, group:xxx, tenant:xxx）",
    )

    # 资源匹配
    resources: list[str] = Field(
        default_factory=list,
        description="资源列表（tool:xxx, session:xxx, config:xxx, *）",
    )

    # 操作匹配
    actions: list[str] = Field(
        default_factory=list,
        description="操作列表（read, write, execute, delete, manage, *）",
    )

    # 条件
    conditions: PolicyConditions | None = Field(default=None, description="策略条件")

    # 元数据
    enabled: bool = Field(default=True, description="是否启用")
    tags: list[str] = Field(default_factory=list, description="标签")
    metadata: dict[str, Any] = Field(default_factory=dict, description="元数据")

    def matches_principal(self, principal: str) -> bool:
        """检查主体是否匹配

        Args:
            principal: 主体标识符

        Returns:
            是否匹配
        """
        if not self.principals:
            return True  # 空列表表示匹配所有

        for p in self.principals:
            if p == "*" or p == principal:
                return True

            # 通配符匹配
            if p.endswith(":*"):
                prefix = p[:-1]  # "role:" from "role:*"
                if principal.startswith(prefix):
                    return True

        return False

    def matches_resource(self, resource: str) -> bool:
        """检查资源是否匹配

        Args:
            resource: 资源标识符

        Returns:
            是否匹配
        """
        if not self.resources:
            return True

        for r in self.resources:
            if r == "*" or r == resource:
                return True

            # 通配符匹配
            if r.endswith(":*"):
                prefix = r[:-1]
                if resource.startswith(prefix):
                    return True

        return False

    def matches_action(self, action: str) -> bool:
        """检查操作是否匹配

        Args:
            action: 操作标识符

        Returns:
            是否匹配
        """
        if not self.actions:
            return True

        return "*" in self.actions or action in self.actions


# ============================================================================
# 评估上下文
# ============================================================================


class EvaluationContext(BaseModel):
    """策略评估上下文"""

    # 主体信息
    principal: str = Field(description="主体标识符 (如 user:xxx, role:admin)")
    principal_roles: list[str] = Field(
        default_factory=list, description="主体角色列表"
    )
    principal_groups: list[str] = Field(
        default_factory=list, description="主体组列表"
    )
    tenant_id: str | None = Field(default=None, description="租户 ID")

    # 请求信息
    resource: str = Field(description="资源标识符")
    action: str = Field(description="操作标识符")

    # 环境信息
    ip_address: str | None = Field(default=None, description="客户端 IP")
    timestamp: datetime | None = Field(default=None, description="请求时间")

    # 自定义属性
    attributes: dict[str, Any] = Field(default_factory=dict, description="额外属性")

    def get_all_principals(self) -> list[str]:
        """获取所有主体标识

        Returns:
            所有主体标识列表
        """
        principals = [self.principal]

        for role in self.principal_roles:
            principals.append(f"role:{role}")

        for group in self.principal_groups:
            principals.append(f"group:{group}")

        if self.tenant_id:
            principals.append(f"tenant:{self.tenant_id}")

        return principals


# ============================================================================
# 评估结果
# ============================================================================


class PolicyDecision(BaseModel):
    """策略评估结果"""

    effect: PolicyEffect = Field(description="最终效果")
    matched_policy: str | None = Field(default=None, description="匹配的策略名称")
    reason: str = Field(default="", description="原因说明")
    conditions_met: bool = Field(default=True, description="条件是否满足")
    evaluation_time_ms: float = Field(default=0.0, description="评估耗时 (ms)")

    @property
    def allowed(self) -> bool:
        """是否允许"""
        return self.effect == PolicyEffect.ALLOW

    @property
    def denied(self) -> bool:
        """是否拒绝"""
        return self.effect == PolicyEffect.DENY
