"""配额管理

提供租户配额检查和使用量追踪功能。
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from loguru import logger
from pydantic import BaseModel, Field

from .models import Tenant, TenantQuota, TenantUsage


# ============================================================================
# 配额检查结果
# ============================================================================


class QuotaCheckResult(str, Enum):
    """配额检查结果"""

    OK = "ok"  # 配额充足
    WARNING = "warning"  # 接近限制
    EXCEEDED = "exceeded"  # 已超限
    BLOCKED = "blocked"  # 已阻止


class QuotaType(str, Enum):
    """配额类型"""

    AGENTS = "agents"
    SESSIONS = "sessions"
    PLUGINS = "plugins"
    CUSTOM_TOOLS = "custom_tools"
    TOKENS_PER_DAY = "tokens_per_day"
    TOKENS_PER_REQUEST = "tokens_per_request"
    API_CALLS_PER_MINUTE = "api_calls_per_minute"
    API_CALLS_PER_DAY = "api_calls_per_day"
    STORAGE = "storage"
    CONCURRENT_REQUESTS = "concurrent_requests"


class QuotaCheckDetail(BaseModel):
    """配额检查详情"""

    quota_type: QuotaType = Field(description="配额类型")
    result: QuotaCheckResult = Field(description="检查结果")
    current: int | float = Field(description="当前使用量")
    limit: int | float = Field(description="配额限制")
    percentage: float = Field(description="使用百分比")
    message: str = Field(default="", description="提示信息")


# ============================================================================
# 配额管理器
# ============================================================================


class QuotaManager:
    """配额管理器

    负责检查和追踪租户配额使用情况。
    """

    # 警告阈值（使用率达到此值时发出警告）
    WARNING_THRESHOLD = 0.8  # 80%

    def __init__(self) -> None:
        # 运行时使用量追踪
        self._usage_cache: dict[str, dict[str, Any]] = {}
        # API 调用计数器（滑动窗口）
        self._api_counters: dict[str, list[datetime]] = {}
        # 并发请求计数
        self._concurrent_requests: dict[str, int] = {}
        self._lock = asyncio.Lock()

    # ========================================================================
    # 配额检查
    # ========================================================================

    async def check_quota(
        self,
        tenant: Tenant,
        quota_type: QuotaType,
        requested: int | float = 1,
    ) -> QuotaCheckDetail:
        """检查单个配额

        Args:
            tenant: 租户
            quota_type: 配额类型
            requested: 请求的数量

        Returns:
            配额检查详情
        """
        quota = tenant.quota
        current = await self._get_current_usage(tenant.id, quota_type)
        limit = self._get_quota_limit(quota, quota_type)

        # 计算使用百分比
        if limit > 0:
            percentage = (current + requested) / limit
        else:
            percentage = 0.0

        # 确定检查结果
        if current + requested > limit:
            result = QuotaCheckResult.EXCEEDED
            message = f"{quota_type.value} 配额已超限: {current + requested}/{limit}"
        elif percentage >= self.WARNING_THRESHOLD:
            result = QuotaCheckResult.WARNING
            message = f"{quota_type.value} 配额接近限制: {percentage:.1%}"
        else:
            result = QuotaCheckResult.OK
            message = ""

        return QuotaCheckDetail(
            quota_type=quota_type,
            result=result,
            current=current,
            limit=limit,
            percentage=min(percentage, 1.0),
            message=message,
        )

    async def check_all_quotas(self, tenant: Tenant) -> list[QuotaCheckDetail]:
        """检查所有配额

        Args:
            tenant: 租户

        Returns:
            所有配额检查详情
        """
        results = []
        for quota_type in QuotaType:
            detail = await self.check_quota(tenant, quota_type)
            results.append(detail)
        return results

    async def can_proceed(
        self,
        tenant: Tenant,
        quota_type: QuotaType,
        requested: int | float = 1,
    ) -> bool:
        """检查是否可以继续操作

        Args:
            tenant: 租户
            quota_type: 配额类型
            requested: 请求的数量

        Returns:
            是否可以继续
        """
        detail = await self.check_quota(tenant, quota_type, requested)
        return detail.result in (QuotaCheckResult.OK, QuotaCheckResult.WARNING)

    # ========================================================================
    # 使用量追踪
    # ========================================================================

    async def record_usage(
        self,
        tenant_id: str,
        quota_type: QuotaType,
        amount: int | float = 1,
    ) -> None:
        """记录使用量

        Args:
            tenant_id: 租户 ID
            quota_type: 配额类型
            amount: 使用量
        """
        async with self._lock:
            if tenant_id not in self._usage_cache:
                self._usage_cache[tenant_id] = {}

            key = quota_type.value
            if key not in self._usage_cache[tenant_id]:
                self._usage_cache[tenant_id][key] = 0

            self._usage_cache[tenant_id][key] += amount
            logger.debug(f"记录使用量: tenant={tenant_id}, type={key}, amount={amount}")

    async def reset_usage(
        self,
        tenant_id: str,
        quota_type: QuotaType | None = None,
    ) -> None:
        """重置使用量

        Args:
            tenant_id: 租户 ID
            quota_type: 配额类型（None 表示重置所有）
        """
        async with self._lock:
            if tenant_id not in self._usage_cache:
                return

            if quota_type is None:
                self._usage_cache[tenant_id] = {}
            else:
                self._usage_cache[tenant_id].pop(quota_type.value, None)

    # ========================================================================
    # API 速率限制
    # ========================================================================

    async def check_rate_limit(
        self,
        tenant: Tenant,
        window_seconds: int = 60,
    ) -> QuotaCheckDetail:
        """检查 API 速率限制

        Args:
            tenant: 租户
            window_seconds: 时间窗口（秒）

        Returns:
            配额检查详情
        """
        async with self._lock:
            now = datetime.now()
            tenant_id = tenant.id

            # 初始化计数器
            if tenant_id not in self._api_counters:
                self._api_counters[tenant_id] = []

            # 清理过期记录
            cutoff = now - timedelta(seconds=window_seconds)
            self._api_counters[tenant_id] = [
                t for t in self._api_counters[tenant_id] if t > cutoff
            ]

            current = len(self._api_counters[tenant_id])
            limit = tenant.quota.max_api_calls_per_minute

            if limit > 0:
                percentage = current / limit
            else:
                percentage = 0.0

            if current >= limit:
                result = QuotaCheckResult.EXCEEDED
                message = f"API 速率限制已达到: {current}/{limit}/分钟"
            elif percentage >= self.WARNING_THRESHOLD:
                result = QuotaCheckResult.WARNING
                message = f"API 速率接近限制: {percentage:.1%}"
            else:
                result = QuotaCheckResult.OK
                message = ""

            return QuotaCheckDetail(
                quota_type=QuotaType.API_CALLS_PER_MINUTE,
                result=result,
                current=current,
                limit=limit,
                percentage=min(percentage, 1.0),
                message=message,
            )

    async def record_api_call(self, tenant_id: str) -> None:
        """记录 API 调用

        Args:
            tenant_id: 租户 ID
        """
        async with self._lock:
            if tenant_id not in self._api_counters:
                self._api_counters[tenant_id] = []

            self._api_counters[tenant_id].append(datetime.now())

    # ========================================================================
    # 并发请求限制
    # ========================================================================

    async def acquire_concurrent_slot(self, tenant: Tenant) -> bool:
        """获取并发请求槽位

        Args:
            tenant: 租户

        Returns:
            是否成功获取
        """
        async with self._lock:
            tenant_id = tenant.id
            current = self._concurrent_requests.get(tenant_id, 0)
            limit = tenant.quota.max_concurrent_requests

            if current >= limit:
                logger.warning(f"并发请求已达上限: tenant={tenant_id}, current={current}, limit={limit}")
                return False

            self._concurrent_requests[tenant_id] = current + 1
            return True

    async def release_concurrent_slot(self, tenant_id: str) -> None:
        """释放并发请求槽位

        Args:
            tenant_id: 租户 ID
        """
        async with self._lock:
            current = self._concurrent_requests.get(tenant_id, 0)
            if current > 0:
                self._concurrent_requests[tenant_id] = current - 1

    async def get_concurrent_count(self, tenant_id: str) -> int:
        """获取当前并发请求数

        Args:
            tenant_id: 租户 ID

        Returns:
            并发请求数
        """
        return self._concurrent_requests.get(tenant_id, 0)

    # ========================================================================
    # 内部方法
    # ========================================================================

    async def _get_current_usage(
        self,
        tenant_id: str,
        quota_type: QuotaType,
    ) -> int | float:
        """获取当前使用量

        Args:
            tenant_id: 租户 ID
            quota_type: 配额类型

        Returns:
            当前使用量
        """
        # 特殊处理并发请求
        if quota_type == QuotaType.CONCURRENT_REQUESTS:
            return self._concurrent_requests.get(tenant_id, 0)

        # 特殊处理 API 速率
        if quota_type == QuotaType.API_CALLS_PER_MINUTE:
            now = datetime.now()
            cutoff = now - timedelta(seconds=60)
            calls = self._api_counters.get(tenant_id, [])
            return len([t for t in calls if t > cutoff])

        # 从缓存获取
        if tenant_id in self._usage_cache:
            return self._usage_cache[tenant_id].get(quota_type.value, 0)

        return 0

    def _get_quota_limit(self, quota: TenantQuota, quota_type: QuotaType) -> int | float:
        """获取配额限制

        Args:
            quota: 配额配置
            quota_type: 配额类型

        Returns:
            配额限制值
        """
        mapping = {
            QuotaType.AGENTS: quota.max_agents,
            QuotaType.SESSIONS: quota.max_sessions,
            QuotaType.PLUGINS: quota.max_plugins,
            QuotaType.CUSTOM_TOOLS: quota.max_custom_tools,
            QuotaType.TOKENS_PER_DAY: quota.max_tokens_per_day,
            QuotaType.TOKENS_PER_REQUEST: quota.max_tokens_per_request,
            QuotaType.API_CALLS_PER_MINUTE: quota.max_api_calls_per_minute,
            QuotaType.API_CALLS_PER_DAY: quota.max_api_calls_per_day,
            QuotaType.STORAGE: quota.storage_quota_mb,
            QuotaType.CONCURRENT_REQUESTS: quota.max_concurrent_requests,
        }
        return mapping.get(quota_type, 0)

    # ========================================================================
    # 统计信息
    # ========================================================================

    async def get_usage_summary(self, tenant: Tenant) -> dict[str, Any]:
        """获取使用量摘要

        Args:
            tenant: 租户

        Returns:
            使用量摘要
        """
        summary = {}
        for quota_type in QuotaType:
            current = await self._get_current_usage(tenant.id, quota_type)
            limit = self._get_quota_limit(tenant.quota, quota_type)
            percentage = current / limit if limit > 0 else 0.0

            summary[quota_type.value] = {
                "current": current,
                "limit": limit,
                "percentage": percentage,
                "status": self._get_status_from_percentage(percentage),
            }

        return summary

    def _get_status_from_percentage(self, percentage: float) -> str:
        """根据百分比获取状态

        Args:
            percentage: 使用百分比

        Returns:
            状态字符串
        """
        if percentage >= 1.0:
            return "exceeded"
        elif percentage >= self.WARNING_THRESHOLD:
            return "warning"
        else:
            return "ok"
