"""租户隔离

提供租户级别的数据和资源隔离功能。
"""

from __future__ import annotations

import asyncio
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, TypeVar

from loguru import logger

from .models import Tenant, TenantConfig, TenantQuota


# ============================================================================
# 租户上下文
# ============================================================================


@dataclass
class TenantContext:
    """租户上下文

    存储当前请求的租户信息。
    """

    tenant_id: str
    tenant_name: str
    tier: str
    quota: TenantQuota
    config: TenantConfig
    metadata: dict[str, Any] = field(default_factory=dict)
    entered_at: datetime = field(default_factory=datetime.now)

    @classmethod
    def from_tenant(cls, tenant: Tenant) -> "TenantContext":
        """从租户实体创建上下文

        Args:
            tenant: 租户实体

        Returns:
            租户上下文
        """
        return cls(
            tenant_id=tenant.id,
            tenant_name=tenant.name,
            tier=tenant.tier.value,
            quota=tenant.quota,
            config=tenant.config,
            metadata=tenant.metadata.copy(),
        )


# 当前租户上下文变量
_current_tenant: ContextVar[TenantContext | None] = ContextVar(
    "current_tenant", default=None
)


def get_current_tenant() -> TenantContext | None:
    """获取当前租户上下文

    Returns:
        当前租户上下文，如果未设置则返回 None
    """
    return _current_tenant.get()


def get_current_tenant_id() -> str | None:
    """获取当前租户 ID

    Returns:
        当前租户 ID，如果未设置则返回 None
    """
    ctx = _current_tenant.get()
    return ctx.tenant_id if ctx else None


def set_current_tenant(context: TenantContext | None) -> None:
    """设置当前租户上下文

    Args:
        context: 租户上下文
    """
    _current_tenant.set(context)


# ============================================================================
# 租户隔离管理器
# ============================================================================


class TenantIsolation:
    """租户隔离管理器

    提供租户级别的资源隔离和访问控制。
    """

    def __init__(self) -> None:
        # 租户资源注册表
        self._resources: dict[str, dict[str, Any]] = {}
        # 租户锁
        self._locks: dict[str, asyncio.Lock] = {}
        # 全局锁
        self._global_lock = asyncio.Lock()

    # ========================================================================
    # 上下文管理
    # ========================================================================

    async def enter_tenant_context(self, tenant: Tenant) -> TenantContext:
        """进入租户上下文

        Args:
            tenant: 租户实体

        Returns:
            租户上下文
        """
        context = TenantContext.from_tenant(tenant)
        set_current_tenant(context)
        logger.debug(f"进入租户上下文: {tenant.id}")
        return context

    async def exit_tenant_context(self) -> None:
        """退出租户上下文"""
        ctx = get_current_tenant()
        if ctx:
            logger.debug(f"退出租户上下文: {ctx.tenant_id}")
        set_current_tenant(None)

    def tenant_context(self, tenant: Tenant):
        """租户上下文管理器

        Args:
            tenant: 租户实体

        Returns:
            异步上下文管理器
        """
        return TenantContextManager(self, tenant)

    # ========================================================================
    # 资源隔离
    # ========================================================================

    async def register_resource(
        self,
        tenant_id: str,
        resource_type: str,
        resource_id: str,
        resource: Any,
    ) -> None:
        """注册租户资源

        Args:
            tenant_id: 租户 ID
            resource_type: 资源类型
            resource_id: 资源 ID
            resource: 资源对象
        """
        async with self._global_lock:
            if tenant_id not in self._resources:
                self._resources[tenant_id] = {}

            key = f"{resource_type}:{resource_id}"
            self._resources[tenant_id][key] = resource
            logger.debug(f"注册资源: tenant={tenant_id}, key={key}")

    async def get_resource(
        self,
        tenant_id: str,
        resource_type: str,
        resource_id: str,
    ) -> Any | None:
        """获取租户资源

        Args:
            tenant_id: 租户 ID
            resource_type: 资源类型
            resource_id: 资源 ID

        Returns:
            资源对象，不存在返回 None
        """
        if tenant_id not in self._resources:
            return None

        key = f"{resource_type}:{resource_id}"
        return self._resources[tenant_id].get(key)

    async def remove_resource(
        self,
        tenant_id: str,
        resource_type: str,
        resource_id: str,
    ) -> bool:
        """移除租户资源

        Args:
            tenant_id: 租户 ID
            resource_type: 资源类型
            resource_id: 资源 ID

        Returns:
            是否移除成功
        """
        async with self._global_lock:
            if tenant_id not in self._resources:
                return False

            key = f"{resource_type}:{resource_id}"
            if key in self._resources[tenant_id]:
                del self._resources[tenant_id][key]
                logger.debug(f"移除资源: tenant={tenant_id}, key={key}")
                return True
            return False

    async def list_resources(
        self,
        tenant_id: str,
        resource_type: str | None = None,
    ) -> list[tuple[str, Any]]:
        """列出租户资源

        Args:
            tenant_id: 租户 ID
            resource_type: 资源类型过滤

        Returns:
            资源列表 [(resource_id, resource), ...]
        """
        if tenant_id not in self._resources:
            return []

        results = []
        for key, resource in self._resources[tenant_id].items():
            rtype, rid = key.split(":", 1)
            if resource_type is None or rtype == resource_type:
                results.append((rid, resource))

        return results

    async def clear_tenant_resources(self, tenant_id: str) -> int:
        """清除租户所有资源

        Args:
            tenant_id: 租户 ID

        Returns:
            清除的资源数量
        """
        async with self._global_lock:
            if tenant_id not in self._resources:
                return 0

            count = len(self._resources[tenant_id])
            del self._resources[tenant_id]
            logger.info(f"清除租户资源: tenant={tenant_id}, count={count}")
            return count

    # ========================================================================
    # 访问控制
    # ========================================================================

    async def check_resource_access(
        self,
        tenant_id: str,
        resource_type: str,
        resource_id: str,
    ) -> bool:
        """检查资源访问权限

        Args:
            tenant_id: 租户 ID
            resource_type: 资源类型
            resource_id: 资源 ID

        Returns:
            是否有访问权限
        """
        # 检查当前上下文
        ctx = get_current_tenant()
        if ctx is None:
            logger.warning("未设置租户上下文，拒绝访问")
            return False

        # 检查租户匹配
        if ctx.tenant_id != tenant_id:
            logger.warning(f"租户不匹配: current={ctx.tenant_id}, requested={tenant_id}")
            return False

        return True

    async def ensure_tenant_access(
        self,
        tenant_id: str,
        resource_type: str = "",
        resource_id: str = "",
    ) -> None:
        """确保租户访问权限

        Args:
            tenant_id: 租户 ID
            resource_type: 资源类型
            resource_id: 资源 ID

        Raises:
            PermissionError: 无访问权限
        """
        if not await self.check_resource_access(tenant_id, resource_type, resource_id):
            raise PermissionError(f"无权访问租户资源: {tenant_id}/{resource_type}/{resource_id}")

    # ========================================================================
    # 租户锁
    # ========================================================================

    async def get_tenant_lock(self, tenant_id: str) -> asyncio.Lock:
        """获取租户锁

        Args:
            tenant_id: 租户 ID

        Returns:
            租户锁
        """
        async with self._global_lock:
            if tenant_id not in self._locks:
                self._locks[tenant_id] = asyncio.Lock()
            return self._locks[tenant_id]

    async def with_tenant_lock(
        self,
        tenant_id: str,
        func: Callable[[], Any],
    ) -> Any:
        """在租户锁保护下执行函数

        Args:
            tenant_id: 租户 ID
            func: 要执行的函数

        Returns:
            函数返回值
        """
        lock = await self.get_tenant_lock(tenant_id)
        async with lock:
            if asyncio.iscoroutinefunction(func):
                return await func()
            return func()

    # ========================================================================
    # 统计信息
    # ========================================================================

    async def get_isolation_stats(self) -> dict[str, Any]:
        """获取隔离统计信息

        Returns:
            统计信息
        """
        stats = {
            "total_tenants": len(self._resources),
            "total_resources": sum(len(r) for r in self._resources.values()),
            "tenants": {},
        }

        for tenant_id, resources in self._resources.items():
            # 按类型统计
            type_counts: dict[str, int] = {}
            for key in resources:
                rtype = key.split(":")[0]
                type_counts[rtype] = type_counts.get(rtype, 0) + 1

            stats["tenants"][tenant_id] = {
                "resource_count": len(resources),
                "by_type": type_counts,
            }

        return stats


# ============================================================================
# 上下文管理器
# ============================================================================


class TenantContextManager:
    """租户上下文管理器

    用于 async with 语法。
    """

    def __init__(self, isolation: TenantIsolation, tenant: Tenant) -> None:
        self._isolation = isolation
        self._tenant = tenant
        self._context: TenantContext | None = None
        self._previous_context: TenantContext | None = None

    async def __aenter__(self) -> TenantContext:
        # 保存之前的上下文
        self._previous_context = get_current_tenant()
        # 进入新上下文
        self._context = await self._isolation.enter_tenant_context(self._tenant)
        return self._context

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        # 恢复之前的上下文
        set_current_tenant(self._previous_context)


# ============================================================================
# 装饰器
# ============================================================================


T = TypeVar("T")


def require_tenant_context(func: Callable[..., T]) -> Callable[..., T]:
    """要求租户上下文的装饰器

    确保函数在租户上下文中执行。

    Args:
        func: 被装饰的函数

    Returns:
        装饰后的函数
    """
    import functools

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        ctx = get_current_tenant()
        if ctx is None:
            raise RuntimeError("需要租户上下文")
        return await func(*args, **kwargs)

    return wrapper


def inject_tenant_id(func: Callable[..., T]) -> Callable[..., T]:
    """注入租户 ID 的装饰器

    自动将当前租户 ID 注入到函数参数中。

    Args:
        func: 被装饰的函数

    Returns:
        装饰后的函数
    """
    import functools

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        ctx = get_current_tenant()
        if ctx is not None and "tenant_id" not in kwargs:
            kwargs["tenant_id"] = ctx.tenant_id
        return await func(*args, **kwargs)

    return wrapper
