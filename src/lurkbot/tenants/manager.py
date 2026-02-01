"""租户管理器

提供租户生命周期管理功能。
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from typing import Any, Callable

from loguru import logger

from .isolation import TenantContext, TenantIsolation, get_current_tenant
from .models import (
    Tenant,
    TenantConfig,
    TenantEvent,
    TenantEventType,
    TenantQuota,
    TenantStatus,
    TenantTier,
    TenantUsage,
    get_tier_quota,
)
from .quota import QuotaCheckDetail, QuotaCheckResult, QuotaManager, QuotaType
from .storage import TenantStorage


# ============================================================================
# 租户管理器
# ============================================================================


class TenantManager:
    """租户管理器

    负责租户的完整生命周期管理，包括：
    - 租户 CRUD 操作
    - 配额管理和检查
    - 租户隔离
    - 使用统计
    - 审计日志
    """

    def __init__(
        self,
        storage: TenantStorage,
        quota_manager: QuotaManager | None = None,
        isolation: TenantIsolation | None = None,
    ) -> None:
        """初始化租户管理器

        Args:
            storage: 租户存储
            quota_manager: 配额管理器（可选）
            isolation: 隔离管理器（可选）
        """
        self._storage = storage
        self._quota_manager = quota_manager or QuotaManager()
        self._isolation = isolation or TenantIsolation()
        self._event_handlers: list[Callable[[TenantEvent], Any]] = []
        self._lock = asyncio.Lock()

    # ========================================================================
    # 租户 CRUD
    # ========================================================================

    async def create_tenant(
        self,
        name: str,
        display_name: str,
        tier: TenantTier = TenantTier.FREE,
        description: str = "",
        owner_id: str | None = None,
        contact_email: str | None = None,
        trial_days: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Tenant:
        """创建租户

        Args:
            name: 租户名称（唯一）
            display_name: 显示名称
            tier: 套餐级别
            description: 描述
            owner_id: 所有者 ID
            contact_email: 联系邮箱
            trial_days: 试用天数（设置后状态为 TRIAL）
            metadata: 元数据

        Returns:
            创建的租户

        Raises:
            ValueError: 租户名称已存在
        """
        # 检查名称是否已存在
        existing = await self._storage.get_by_name(name)
        if existing:
            raise ValueError(f"租户名称已存在: {name}")

        # 生成租户 ID
        import uuid
        tenant_id = f"tenant_{uuid.uuid4().hex[:12]}"

        # 确定状态和过期时间
        status = TenantStatus.TRIAL if trial_days else TenantStatus.ACTIVE
        trial_ends_at = None
        if trial_days:
            trial_ends_at = datetime.now() + timedelta(days=trial_days)

        # 获取套餐默认配额
        quota = get_tier_quota(tier)

        # 创建租户
        tenant = Tenant(
            id=tenant_id,
            name=name,
            display_name=display_name,
            description=description,
            status=status,
            tier=tier,
            trial_ends_at=trial_ends_at,
            quota=quota,
            owner_id=owner_id,
            contact_email=contact_email,
            metadata=metadata or {},
        )

        # 保存到存储
        tenant = await self._storage.create(tenant)

        # 记录事件
        await self._emit_event(
            tenant_id=tenant.id,
            event_type=TenantEventType.CREATED,
            message=f"租户创建: {name}",
            new_value={"tier": tier.value, "status": status.value},
        )

        logger.info(f"创建租户: id={tenant.id}, name={name}, tier={tier.value}")
        return tenant

    async def get_tenant(self, tenant_id: str) -> Tenant | None:
        """获取租户

        Args:
            tenant_id: 租户 ID

        Returns:
            租户实体，不存在返回 None
        """
        return await self._storage.get(tenant_id)

    async def get_tenant_by_name(self, name: str) -> Tenant | None:
        """通过名称获取租户

        Args:
            name: 租户名称

        Returns:
            租户实体，不存在返回 None
        """
        return await self._storage.get_by_name(name)

    async def update_tenant(
        self,
        tenant_id: str,
        display_name: str | None = None,
        description: str | None = None,
        contact_email: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Tenant:
        """更新租户信息

        Args:
            tenant_id: 租户 ID
            display_name: 显示名称
            description: 描述
            contact_email: 联系邮箱
            metadata: 元数据（合并更新）

        Returns:
            更新后的租户

        Raises:
            ValueError: 租户不存在
        """
        tenant = await self._storage.get(tenant_id)
        if not tenant:
            raise ValueError(f"租户不存在: {tenant_id}")

        # 记录旧值
        old_values = {
            "display_name": tenant.display_name,
            "description": tenant.description,
            "contact_email": tenant.contact_email,
        }

        # 更新字段
        if display_name is not None:
            tenant.display_name = display_name
        if description is not None:
            tenant.description = description
        if contact_email is not None:
            tenant.contact_email = contact_email
        if metadata is not None:
            tenant.metadata.update(metadata)

        # 保存更新
        tenant = await self._storage.update(tenant)

        # 记录事件
        await self._emit_event(
            tenant_id=tenant.id,
            event_type=TenantEventType.UPDATED,
            message="租户信息更新",
            old_value=old_values,
            new_value={
                "display_name": tenant.display_name,
                "description": tenant.description,
                "contact_email": tenant.contact_email,
            },
        )

        return tenant

    async def delete_tenant(self, tenant_id: str, hard_delete: bool = False) -> bool:
        """删除租户

        Args:
            tenant_id: 租户 ID
            hard_delete: 是否硬删除（物理删除）

        Returns:
            是否删除成功
        """
        tenant = await self._storage.get(tenant_id)
        if not tenant:
            return False

        if hard_delete:
            # 清除租户资源
            await self._isolation.clear_tenant_resources(tenant_id)
            # 物理删除
            result = await self._storage.delete(tenant_id)
        else:
            # 软删除（标记为已删除）
            tenant.status = TenantStatus.DELETED
            await self._storage.update(tenant)
            result = True

        if result:
            await self._emit_event(
                tenant_id=tenant_id,
                event_type=TenantEventType.DELETED,
                message=f"租户删除: hard_delete={hard_delete}",
            )
            logger.info(f"删除租户: id={tenant_id}, hard_delete={hard_delete}")

        return result

    async def list_tenants(
        self,
        status: TenantStatus | None = None,
        tier: TenantTier | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> list[Tenant]:
        """列出租户

        Args:
            status: 状态过滤
            tier: 套餐过滤
            offset: 偏移量
            limit: 限制数量

        Returns:
            租户列表
        """
        return await self._storage.list(status=status, tier=tier, offset=offset, limit=limit)

    async def count_tenants(
        self,
        status: TenantStatus | None = None,
        tier: TenantTier | None = None,
    ) -> int:
        """统计租户数量

        Args:
            status: 状态过滤
            tier: 套餐过滤

        Returns:
            租户数量
        """
        return await self._storage.count(status=status, tier=tier)

    # ========================================================================
    # 状态管理
    # ========================================================================

    async def activate_tenant(self, tenant_id: str) -> Tenant:
        """激活租户

        Args:
            tenant_id: 租户 ID

        Returns:
            更新后的租户

        Raises:
            ValueError: 租户不存在
        """
        tenant = await self._storage.get(tenant_id)
        if not tenant:
            raise ValueError(f"租户不存在: {tenant_id}")

        old_status = tenant.status
        tenant.status = TenantStatus.ACTIVE
        tenant = await self._storage.update(tenant)

        await self._emit_event(
            tenant_id=tenant_id,
            event_type=TenantEventType.ACTIVATED,
            message="租户激活",
            old_value=old_status.value,
            new_value=TenantStatus.ACTIVE.value,
        )

        logger.info(f"激活租户: id={tenant_id}")
        return tenant

    async def suspend_tenant(self, tenant_id: str, reason: str = "") -> Tenant:
        """暂停租户

        Args:
            tenant_id: 租户 ID
            reason: 暂停原因

        Returns:
            更新后的租户

        Raises:
            ValueError: 租户不存在
        """
        tenant = await self._storage.get(tenant_id)
        if not tenant:
            raise ValueError(f"租户不存在: {tenant_id}")

        old_status = tenant.status
        tenant.status = TenantStatus.SUSPENDED
        tenant = await self._storage.update(tenant)

        await self._emit_event(
            tenant_id=tenant_id,
            event_type=TenantEventType.SUSPENDED,
            message=f"租户暂停: {reason}",
            old_value=old_status.value,
            new_value=TenantStatus.SUSPENDED.value,
            metadata={"reason": reason},
        )

        logger.info(f"暂停租户: id={tenant_id}, reason={reason}")
        return tenant

    async def expire_tenant(self, tenant_id: str) -> Tenant:
        """设置租户过期

        Args:
            tenant_id: 租户 ID

        Returns:
            更新后的租户

        Raises:
            ValueError: 租户不存在
        """
        tenant = await self._storage.get(tenant_id)
        if not tenant:
            raise ValueError(f"租户不存在: {tenant_id}")

        old_status = tenant.status
        tenant.status = TenantStatus.EXPIRED
        tenant = await self._storage.update(tenant)

        await self._emit_event(
            tenant_id=tenant_id,
            event_type=TenantEventType.EXPIRED,
            message="租户过期",
            old_value=old_status.value,
            new_value=TenantStatus.EXPIRED.value,
        )

        logger.info(f"租户过期: id={tenant_id}")
        return tenant

    # ========================================================================
    # 套餐管理
    # ========================================================================

    async def upgrade_tier(
        self,
        tenant_id: str,
        new_tier: TenantTier,
        update_quota: bool = True,
    ) -> Tenant:
        """升级套餐

        Args:
            tenant_id: 租户 ID
            new_tier: 新套餐
            update_quota: 是否更新配额为新套餐默认值

        Returns:
            更新后的租户

        Raises:
            ValueError: 租户不存在或套餐无效
        """
        tenant = await self._storage.get(tenant_id)
        if not tenant:
            raise ValueError(f"租户不存在: {tenant_id}")

        old_tier = tenant.tier
        tenant.tier = new_tier

        if update_quota:
            tenant.quota = get_tier_quota(new_tier)

        tenant = await self._storage.update(tenant)

        await self._emit_event(
            tenant_id=tenant_id,
            event_type=TenantEventType.TIER_CHANGED,
            message=f"套餐变更: {old_tier.value} -> {new_tier.value}",
            old_value=old_tier.value,
            new_value=new_tier.value,
        )

        logger.info(f"套餐变更: id={tenant_id}, {old_tier.value} -> {new_tier.value}")
        return tenant

    # ========================================================================
    # 配额管理
    # ========================================================================

    async def get_quota(self, tenant_id: str) -> TenantQuota | None:
        """获取租户配额

        Args:
            tenant_id: 租户 ID

        Returns:
            配额配置
        """
        return await self._storage.get_quota(tenant_id)

    async def update_quota(self, tenant_id: str, quota: TenantQuota) -> bool:
        """更新租户配额

        Args:
            tenant_id: 租户 ID
            quota: 新配额

        Returns:
            是否更新成功
        """
        result = await self._storage.update_quota(tenant_id, quota)
        if result:
            await self._emit_event(
                tenant_id=tenant_id,
                event_type=TenantEventType.CONFIG_UPDATED,
                message="配额更新",
                new_value=quota.model_dump(),
            )
        return result

    async def check_quota(
        self,
        tenant_id: str,
        quota_type: QuotaType,
        requested: int | float = 1,
    ) -> QuotaCheckDetail:
        """检查配额

        Args:
            tenant_id: 租户 ID
            quota_type: 配额类型
            requested: 请求数量

        Returns:
            配额检查详情

        Raises:
            ValueError: 租户不存在
        """
        tenant = await self._storage.get(tenant_id)
        if not tenant:
            raise ValueError(f"租户不存在: {tenant_id}")

        return await self._quota_manager.check_quota(tenant, quota_type, requested)

    async def can_proceed(
        self,
        tenant_id: str,
        quota_type: QuotaType,
        requested: int | float = 1,
    ) -> bool:
        """检查是否可以继续操作

        Args:
            tenant_id: 租户 ID
            quota_type: 配额类型
            requested: 请求数量

        Returns:
            是否可以继续
        """
        tenant = await self._storage.get(tenant_id)
        if not tenant:
            return False

        return await self._quota_manager.can_proceed(tenant, quota_type, requested)

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
        await self._quota_manager.record_usage(tenant_id, quota_type, amount)

        # 检查是否超限
        tenant = await self._storage.get(tenant_id)
        if tenant:
            detail = await self._quota_manager.check_quota(tenant, quota_type)
            if detail.result == QuotaCheckResult.EXCEEDED:
                await self._emit_event(
                    tenant_id=tenant_id,
                    event_type=TenantEventType.QUOTA_EXCEEDED,
                    message=f"配额超限: {quota_type.value}",
                    metadata={
                        "quota_type": quota_type.value,
                        "current": detail.current,
                        "limit": detail.limit,
                    },
                )

    # ========================================================================
    # 配置管理
    # ========================================================================

    async def get_config(self, tenant_id: str) -> TenantConfig | None:
        """获取租户配置

        Args:
            tenant_id: 租户 ID

        Returns:
            配置
        """
        return await self._storage.get_config(tenant_id)

    async def update_config(self, tenant_id: str, config: TenantConfig) -> bool:
        """更新租户配置

        Args:
            tenant_id: 租户 ID
            config: 新配置

        Returns:
            是否更新成功
        """
        result = await self._storage.update_config(tenant_id, config)
        if result:
            await self._emit_event(
                tenant_id=tenant_id,
                event_type=TenantEventType.CONFIG_UPDATED,
                message="配置更新",
            )
        return result

    # ========================================================================
    # 上下文管理
    # ========================================================================

    async def enter_context(self, tenant_id: str) -> TenantContext:
        """进入租户上下文

        Args:
            tenant_id: 租户 ID

        Returns:
            租户上下文

        Raises:
            ValueError: 租户不存在或不可用
        """
        tenant = await self._storage.get(tenant_id)
        if not tenant:
            raise ValueError(f"租户不存在: {tenant_id}")

        if not tenant.is_active():
            raise ValueError(f"租户不可用: {tenant_id}, status={tenant.status.value}")

        return await self._isolation.enter_tenant_context(tenant)

    async def exit_context(self) -> None:
        """退出租户上下文"""
        await self._isolation.exit_tenant_context()

    def context(self, tenant_id: str):
        """获取租户上下文管理器

        Args:
            tenant_id: 租户 ID

        Returns:
            上下文管理器
        """
        return TenantManagerContextManager(self, tenant_id)

    def get_current_tenant(self) -> TenantContext | None:
        """获取当前租户上下文

        Returns:
            当前租户上下文
        """
        return get_current_tenant()

    # ========================================================================
    # 使用统计
    # ========================================================================

    async def record_usage_stats(self, usage: TenantUsage) -> bool:
        """记录使用统计

        Args:
            usage: 使用统计

        Returns:
            是否记录成功
        """
        return await self._storage.record_usage(usage)

    async def get_usage_stats(
        self,
        tenant_id: str,
        period: str = "daily",
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[TenantUsage]:
        """获取使用统计

        Args:
            tenant_id: 租户 ID
            period: 统计周期
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            使用统计列表
        """
        return await self._storage.get_usage(
            tenant_id=tenant_id,
            period=period,
            start_date=start_date,
            end_date=end_date,
        )

    async def get_usage_summary(self, tenant_id: str) -> dict[str, Any]:
        """获取使用量摘要

        Args:
            tenant_id: 租户 ID

        Returns:
            使用量摘要
        """
        tenant = await self._storage.get(tenant_id)
        if not tenant:
            return {}

        return await self._quota_manager.get_usage_summary(tenant)

    # ========================================================================
    # 事件管理
    # ========================================================================

    def on_event(self, handler: Callable[[TenantEvent], Any]) -> None:
        """注册事件处理器

        Args:
            handler: 事件处理函数
        """
        self._event_handlers.append(handler)

    async def get_events(
        self,
        tenant_id: str,
        event_type: TenantEventType | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> list[TenantEvent]:
        """获取租户事件

        Args:
            tenant_id: 租户 ID
            event_type: 事件类型过滤
            offset: 偏移量
            limit: 限制数量

        Returns:
            事件列表
        """
        return await self._storage.get_events(
            tenant_id=tenant_id,
            event_type=event_type,
            offset=offset,
            limit=limit,
        )

    async def _emit_event(
        self,
        tenant_id: str,
        event_type: TenantEventType,
        message: str = "",
        actor_id: str | None = None,
        old_value: Any = None,
        new_value: Any = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """发送事件

        Args:
            tenant_id: 租户 ID
            event_type: 事件类型
            message: 事件消息
            actor_id: 操作者 ID
            old_value: 旧值
            new_value: 新值
            metadata: 元数据
        """
        event = TenantEvent(
            tenant_id=tenant_id,
            event_type=event_type,
            message=message,
            actor_id=actor_id,
            old_value=old_value,
            new_value=new_value,
            metadata=metadata or {},
        )

        # 保存到存储
        await self._storage.record_event(event)

        # 通知处理器
        for handler in self._event_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                logger.error(f"事件处理器错误: {e}")

    # ========================================================================
    # 隔离管理
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
        await self._isolation.register_resource(tenant_id, resource_type, resource_id, resource)

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
            资源对象
        """
        return await self._isolation.get_resource(tenant_id, resource_type, resource_id)

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
            资源列表
        """
        return await self._isolation.list_resources(tenant_id, resource_type)

    async def get_isolation_stats(self) -> dict[str, Any]:
        """获取隔离统计信息

        Returns:
            统计信息
        """
        return await self._isolation.get_isolation_stats()

    # ========================================================================
    # 维护任务
    # ========================================================================

    async def check_expired_tenants(self) -> list[str]:
        """检查过期租户

        Returns:
            过期租户 ID 列表
        """
        expired_ids = []
        tenants = await self._storage.list(status=TenantStatus.ACTIVE)

        for tenant in tenants:
            if tenant.is_expired():
                await self.expire_tenant(tenant.id)
                expired_ids.append(tenant.id)

        tenants = await self._storage.list(status=TenantStatus.TRIAL)
        for tenant in tenants:
            if tenant.is_trial_expired():
                await self.expire_tenant(tenant.id)
                expired_ids.append(tenant.id)

        if expired_ids:
            logger.info(f"检测到 {len(expired_ids)} 个过期租户")

        return expired_ids


# ============================================================================
# 上下文管理器
# ============================================================================


class TenantManagerContextManager:
    """租户管理器上下文管理器"""

    def __init__(self, manager: TenantManager, tenant_id: str) -> None:
        self._manager = manager
        self._tenant_id = tenant_id
        self._context: TenantContext | None = None

    async def __aenter__(self) -> TenantContext:
        self._context = await self._manager.enter_context(self._tenant_id)
        return self._context

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self._manager.exit_context()
