"""租户错误定义

提供租户相关的错误类型和错误码。
"""

from __future__ import annotations

from enum import Enum
from typing import Any


class TenantErrorCode(str, Enum):
    """租户错误码"""

    # 通用错误
    TENANT_NOT_FOUND = "TENANT_NOT_FOUND"
    TENANT_INACTIVE = "TENANT_INACTIVE"
    TENANT_SUSPENDED = "TENANT_SUSPENDED"
    TENANT_EXPIRED = "TENANT_EXPIRED"

    # 配额错误
    QUOTA_EXCEEDED = "QUOTA_EXCEEDED"
    RATE_LIMITED = "RATE_LIMITED"
    CONCURRENT_LIMIT = "CONCURRENT_LIMIT"
    TOKEN_LIMIT = "TOKEN_LIMIT"

    # 策略错误
    POLICY_DENIED = "POLICY_DENIED"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    RESOURCE_FORBIDDEN = "RESOURCE_FORBIDDEN"

    # 验证错误
    INVALID_TENANT_ID = "INVALID_TENANT_ID"
    AUTHENTICATION_REQUIRED = "AUTHENTICATION_REQUIRED"


class TenantError(Exception):
    """租户错误基类

    所有租户相关错误的基类。
    """

    def __init__(
        self,
        code: TenantErrorCode,
        message: str,
        tenant_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """初始化租户错误

        Args:
            code: 错误码
            message: 错误消息
            tenant_id: 租户 ID
            details: 详细信息
        """
        super().__init__(message)
        self.code = code
        self.message = message
        self.tenant_id = tenant_id
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        """转换为字典

        Returns:
            错误信息字典
        """
        return {
            "code": self.code.value,
            "message": self.message,
            "tenant_id": self.tenant_id,
            "details": self.details,
        }

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(code={self.code.value}, message={self.message!r})"


class QuotaExceededError(TenantError):
    """配额超限错误

    当租户使用量超过配额限制时抛出。
    """

    def __init__(
        self,
        message: str,
        tenant_id: str | None = None,
        quota_type: str | None = None,
        current: int | float = 0,
        limit: int | float = 0,
        details: dict[str, Any] | None = None,
    ) -> None:
        """初始化配额超限错误

        Args:
            message: 错误消息
            tenant_id: 租户 ID
            quota_type: 配额类型
            current: 当前使用量
            limit: 配额限制
            details: 详细信息
        """
        error_details = details or {}
        error_details.update({
            "quota_type": quota_type,
            "current": current,
            "limit": limit,
        })
        super().__init__(
            code=TenantErrorCode.QUOTA_EXCEEDED,
            message=message,
            tenant_id=tenant_id,
            details=error_details,
        )
        self.quota_type = quota_type
        self.current = current
        self.limit = limit


class RateLimitedError(TenantError):
    """速率限制错误

    当租户 API 调用速率超过限制时抛出。
    """

    def __init__(
        self,
        message: str,
        tenant_id: str | None = None,
        retry_after_seconds: int | None = None,
        current_rate: int = 0,
        rate_limit: int = 0,
        details: dict[str, Any] | None = None,
    ) -> None:
        """初始化速率限制错误

        Args:
            message: 错误消息
            tenant_id: 租户 ID
            retry_after_seconds: 建议重试等待时间（秒）
            current_rate: 当前速率
            rate_limit: 速率限制
            details: 详细信息
        """
        error_details = details or {}
        error_details.update({
            "retry_after_seconds": retry_after_seconds,
            "current_rate": current_rate,
            "rate_limit": rate_limit,
        })
        super().__init__(
            code=TenantErrorCode.RATE_LIMITED,
            message=message,
            tenant_id=tenant_id,
            details=error_details,
        )
        self.retry_after_seconds = retry_after_seconds
        self.current_rate = current_rate
        self.rate_limit = rate_limit


class ConcurrentLimitError(TenantError):
    """并发限制错误

    当租户并发请求数超过限制时抛出。
    """

    def __init__(
        self,
        message: str,
        tenant_id: str | None = None,
        current_concurrent: int = 0,
        max_concurrent: int = 0,
        details: dict[str, Any] | None = None,
    ) -> None:
        """初始化并发限制错误

        Args:
            message: 错误消息
            tenant_id: 租户 ID
            current_concurrent: 当前并发数
            max_concurrent: 最大并发数
            details: 详细信息
        """
        error_details = details or {}
        error_details.update({
            "current_concurrent": current_concurrent,
            "max_concurrent": max_concurrent,
        })
        super().__init__(
            code=TenantErrorCode.CONCURRENT_LIMIT,
            message=message,
            tenant_id=tenant_id,
            details=error_details,
        )
        self.current_concurrent = current_concurrent
        self.max_concurrent = max_concurrent


class PolicyDeniedError(TenantError):
    """策略拒绝错误

    当策略评估结果为拒绝时抛出。
    """

    def __init__(
        self,
        message: str,
        tenant_id: str | None = None,
        principal: str | None = None,
        resource: str | None = None,
        action: str | None = None,
        matched_policy: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """初始化策略拒绝错误

        Args:
            message: 错误消息
            tenant_id: 租户 ID
            principal: 主体标识
            resource: 资源标识
            action: 操作标识
            matched_policy: 匹配的策略名称
            details: 详细信息
        """
        error_details = details or {}
        error_details.update({
            "principal": principal,
            "resource": resource,
            "action": action,
            "matched_policy": matched_policy,
        })
        super().__init__(
            code=TenantErrorCode.POLICY_DENIED,
            message=message,
            tenant_id=tenant_id,
            details=error_details,
        )
        self.principal = principal
        self.resource = resource
        self.action = action
        self.matched_policy = matched_policy


class TenantNotFoundError(TenantError):
    """租户不存在错误"""

    def __init__(
        self,
        tenant_id: str,
        message: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """初始化租户不存在错误

        Args:
            tenant_id: 租户 ID
            message: 错误消息
            details: 详细信息
        """
        super().__init__(
            code=TenantErrorCode.TENANT_NOT_FOUND,
            message=message or f"租户不存在: {tenant_id}",
            tenant_id=tenant_id,
            details=details,
        )


class TenantInactiveError(TenantError):
    """租户不可用错误"""

    def __init__(
        self,
        tenant_id: str,
        status: str | None = None,
        message: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """初始化租户不可用错误

        Args:
            tenant_id: 租户 ID
            status: 租户状态
            message: 错误消息
            details: 详细信息
        """
        error_details = details or {}
        if status:
            error_details["status"] = status

        super().__init__(
            code=TenantErrorCode.TENANT_INACTIVE,
            message=message or f"租户不可用: {tenant_id}",
            tenant_id=tenant_id,
            details=error_details,
        )
        self.status = status
