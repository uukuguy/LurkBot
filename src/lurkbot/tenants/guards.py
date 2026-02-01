"""租户守卫

提供配额检查和策略评估的守卫类。
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any, AsyncIterator

from loguru import logger

from .errors import (
    ConcurrentLimitError,
    PolicyDeniedError,
    QuotaExceededError,
    RateLimitedError,
    TenantInactiveError,
    TenantNotFoundError,
)
from .quota import QuotaCheckResult, QuotaManager, QuotaType

if TYPE_CHECKING:
    from lurkbot.security.policy_dsl import EvaluationContext
    from lurkbot.security.policy_engine import PolicyEngine

    from .manager import TenantManager
    from .models import Tenant


class QuotaGuard:
    """配额守卫

    提供配额检查的上下文管理器和辅助方法。
    """

    def __init__(
        self,
        tenant_manager: TenantManager | None = None,
        quota_manager: QuotaManager | None = None,
    ) -> None:
        """初始化配额守卫

        Args:
            tenant_manager: 租户管理器
            quota_manager: 配额管理器
        """
        self._tenant_manager = tenant_manager
        self._quota_manager = quota_manager or QuotaManager()

    def set_tenant_manager(self, tenant_manager: TenantManager) -> None:
        """设置租户管理器

        Args:
            tenant_manager: 租户管理器
        """
        self._tenant_manager = tenant_manager

    async def _get_tenant(self, tenant_id: str) -> Tenant:
        """获取租户

        Args:
            tenant_id: 租户 ID

        Returns:
            租户实体

        Raises:
            TenantNotFoundError: 租户不存在
            TenantInactiveError: 租户不可用
        """
        if not self._tenant_manager:
            raise RuntimeError("TenantManager not configured")

        tenant = await self._tenant_manager.get_tenant(tenant_id)
        if not tenant:
            raise TenantNotFoundError(tenant_id)

        if not tenant.is_active():
            raise TenantInactiveError(tenant_id, status=tenant.status.value)

        return tenant

    async def check_and_record(
        self,
        tenant_id: str,
        quota_type: QuotaType,
        amount: int | float = 1,
    ) -> None:
        """检查配额并记录使用量

        Args:
            tenant_id: 租户 ID
            quota_type: 配额类型
            amount: 使用量

        Raises:
            QuotaExceededError: 配额超限
        """
        tenant = await self._get_tenant(tenant_id)

        # 检查配额
        detail = await self._quota_manager.check_quota(tenant, quota_type, amount)

        if detail.result == QuotaCheckResult.EXCEEDED:
            raise QuotaExceededError(
                message=detail.message,
                tenant_id=tenant_id,
                quota_type=quota_type.value,
                current=detail.current,
                limit=detail.limit,
            )

        # 记录使用量
        await self._quota_manager.record_usage(tenant_id, quota_type, amount)

        if detail.result == QuotaCheckResult.WARNING:
            logger.warning(f"配额警告: tenant={tenant_id}, {detail.message}")

    async def check_rate_limit(self, tenant_id: str) -> None:
        """检查 API 速率限制

        Args:
            tenant_id: 租户 ID

        Raises:
            RateLimitedError: 速率超限
        """
        tenant = await self._get_tenant(tenant_id)

        detail = await self._quota_manager.check_rate_limit(tenant)

        if detail.result == QuotaCheckResult.EXCEEDED:
            raise RateLimitedError(
                message=detail.message,
                tenant_id=tenant_id,
                retry_after_seconds=60,  # 建议等待 60 秒
                current_rate=int(detail.current),
                rate_limit=int(detail.limit),
            )

        # 记录 API 调用
        await self._quota_manager.record_api_call(tenant_id)

        if detail.result == QuotaCheckResult.WARNING:
            logger.warning(f"速率警告: tenant={tenant_id}, {detail.message}")

    @asynccontextmanager
    async def rate_limit_context(self, tenant_id: str) -> AsyncIterator[None]:
        """速率限制上下文管理器

        Args:
            tenant_id: 租户 ID

        Yields:
            None

        Raises:
            RateLimitedError: 速率超限
        """
        await self.check_rate_limit(tenant_id)
        yield

    async def acquire_concurrent_slot(self, tenant_id: str) -> bool:
        """获取并发槽位

        Args:
            tenant_id: 租户 ID

        Returns:
            是否成功获取

        Raises:
            ConcurrentLimitError: 并发超限
        """
        tenant = await self._get_tenant(tenant_id)

        acquired = await self._quota_manager.acquire_concurrent_slot(tenant)

        if not acquired:
            current = await self._quota_manager.get_concurrent_count(tenant_id)
            raise ConcurrentLimitError(
                message=f"并发请求已达上限: {current}/{tenant.quota.max_concurrent_requests}",
                tenant_id=tenant_id,
                current_concurrent=current,
                max_concurrent=tenant.quota.max_concurrent_requests,
            )

        return True

    async def release_concurrent_slot(self, tenant_id: str) -> None:
        """释放并发槽位

        Args:
            tenant_id: 租户 ID
        """
        await self._quota_manager.release_concurrent_slot(tenant_id)

    @asynccontextmanager
    async def concurrent_slot_context(self, tenant_id: str) -> AsyncIterator[None]:
        """并发槽位上下文管理器

        自动获取和释放并发槽位。

        Args:
            tenant_id: 租户 ID

        Yields:
            None

        Raises:
            ConcurrentLimitError: 并发超限
        """
        await self.acquire_concurrent_slot(tenant_id)
        try:
            yield
        finally:
            await self.release_concurrent_slot(tenant_id)

    async def record_token_usage(
        self,
        tenant_id: str,
        input_tokens: int,
        output_tokens: int,
    ) -> None:
        """记录 Token 使用量

        Args:
            tenant_id: 租户 ID
            input_tokens: 输入 Token 数
            output_tokens: 输出 Token 数
        """
        total_tokens = input_tokens + output_tokens
        await self._quota_manager.record_usage(
            tenant_id,
            QuotaType.TOKENS_PER_DAY,
            total_tokens,
        )
        logger.debug(
            f"记录 Token 使用: tenant={tenant_id}, "
            f"input={input_tokens}, output={output_tokens}, total={total_tokens}"
        )


class PolicyGuard:
    """策略守卫

    提供策略评估的辅助方法。
    """

    def __init__(
        self,
        policy_engine: PolicyEngine | None = None,
    ) -> None:
        """初始化策略守卫

        Args:
            policy_engine: 策略引擎
        """
        self._policy_engine = policy_engine

    def set_policy_engine(self, policy_engine: PolicyEngine) -> None:
        """设置策略引擎

        Args:
            policy_engine: 策略引擎
        """
        self._policy_engine = policy_engine

    async def check_permission(
        self,
        principal: str,
        resource: str,
        action: str,
        tenant_id: str | None = None,
        **kwargs: Any,
    ) -> bool:
        """检查权限

        Args:
            principal: 主体标识
            resource: 资源标识
            action: 操作标识
            tenant_id: 租户 ID
            **kwargs: 其他上下文参数

        Returns:
            是否允许
        """
        if not self._policy_engine:
            # 无策略引擎时默认允许
            logger.warning("PolicyEngine not configured, allowing by default")
            return True

        return await self._policy_engine.is_allowed(
            principal=principal,
            resource=resource,
            action=action,
            tenant_id=tenant_id,
            **kwargs,
        )

    async def require_permission(
        self,
        principal: str,
        resource: str,
        action: str,
        tenant_id: str | None = None,
        **kwargs: Any,
    ) -> None:
        """要求权限（失败抛异常）

        Args:
            principal: 主体标识
            resource: 资源标识
            action: 操作标识
            tenant_id: 租户 ID
            **kwargs: 其他上下文参数

        Raises:
            PolicyDeniedError: 策略拒绝
        """
        if not self._policy_engine:
            # 无策略引擎时默认允许
            logger.warning("PolicyEngine not configured, allowing by default")
            return

        from lurkbot.security.policy_dsl import EvaluationContext

        context = EvaluationContext(
            principal=principal,
            resource=resource,
            action=action,
            tenant_id=tenant_id,
            **kwargs,
        )

        decision = await self._policy_engine.evaluate(context)

        if not decision.allowed:
            raise PolicyDeniedError(
                message=decision.reason or f"策略拒绝: {principal} -> {resource}:{action}",
                tenant_id=tenant_id,
                principal=principal,
                resource=resource,
                action=action,
                matched_policy=decision.matched_policy,
            )

    async def evaluate(
        self,
        principal: str,
        resource: str,
        action: str,
        tenant_id: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """评估策略并返回详细结果

        Args:
            principal: 主体标识
            resource: 资源标识
            action: 操作标识
            tenant_id: 租户 ID
            **kwargs: 其他上下文参数

        Returns:
            评估结果字典
        """
        if not self._policy_engine:
            return {
                "allowed": True,
                "reason": "PolicyEngine not configured",
                "matched_policy": None,
            }

        from lurkbot.security.policy_dsl import EvaluationContext

        context = EvaluationContext(
            principal=principal,
            resource=resource,
            action=action,
            tenant_id=tenant_id,
            **kwargs,
        )

        decision = await self._policy_engine.evaluate(context)

        return {
            "allowed": decision.allowed,
            "effect": decision.effect.value,
            "reason": decision.reason,
            "matched_policy": decision.matched_policy,
            "conditions_met": decision.conditions_met,
            "evaluation_time_ms": decision.evaluation_time_ms,
        }


# ============================================================================
# 全局实例
# ============================================================================

_quota_guard: QuotaGuard | None = None
_policy_guard: PolicyGuard | None = None


def get_quota_guard() -> QuotaGuard:
    """获取全局配额守卫

    Returns:
        配额守卫实例
    """
    global _quota_guard
    if _quota_guard is None:
        _quota_guard = QuotaGuard()
    return _quota_guard


def get_policy_guard() -> PolicyGuard:
    """获取全局策略守卫

    Returns:
        策略守卫实例
    """
    global _policy_guard
    if _policy_guard is None:
        _policy_guard = PolicyGuard()
    return _policy_guard


def configure_guards(
    tenant_manager: TenantManager | None = None,
    policy_engine: PolicyEngine | None = None,
) -> None:
    """配置全局守卫

    Args:
        tenant_manager: 租户管理器
        policy_engine: 策略引擎
    """
    if tenant_manager:
        get_quota_guard().set_tenant_manager(tenant_manager)
    if policy_engine:
        get_policy_guard().set_policy_engine(policy_engine)
