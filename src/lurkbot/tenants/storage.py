"""租户存储

提供租户数据的持久化存储功能。
"""

from __future__ import annotations

import asyncio
import json
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any

from loguru import logger
from pydantic import BaseModel

from .models import (
    Tenant,
    TenantConfig,
    TenantEvent,
    TenantEventType,
    TenantQuota,
    TenantStatus,
    TenantTier,
    TenantUsage,
)


# ============================================================================
# 存储接口
# ============================================================================


class TenantStorage(ABC):
    """租户存储抽象基类

    定义租户数据存储的统一接口。
    """

    # ========================================================================
    # 租户 CRUD
    # ========================================================================

    @abstractmethod
    async def create(self, tenant: Tenant) -> Tenant:
        """创建租户

        Args:
            tenant: 租户实体

        Returns:
            创建的租户

        Raises:
            ValueError: 租户已存在
        """
        pass

    @abstractmethod
    async def get(self, tenant_id: str) -> Tenant | None:
        """获取租户

        Args:
            tenant_id: 租户 ID

        Returns:
            租户实体，不存在返回 None
        """
        pass

    @abstractmethod
    async def get_by_name(self, name: str) -> Tenant | None:
        """通过名称获取租户

        Args:
            name: 租户名称

        Returns:
            租户实体，不存在返回 None
        """
        pass

    @abstractmethod
    async def update(self, tenant: Tenant) -> Tenant:
        """更新租户

        Args:
            tenant: 租户实体

        Returns:
            更新后的租户

        Raises:
            ValueError: 租户不存在
        """
        pass

    @abstractmethod
    async def delete(self, tenant_id: str) -> bool:
        """删除租户

        Args:
            tenant_id: 租户 ID

        Returns:
            是否删除成功
        """
        pass

    @abstractmethod
    async def list(
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
        pass

    @abstractmethod
    async def count(
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
        pass

    # ========================================================================
    # 配额管理
    # ========================================================================

    @abstractmethod
    async def get_quota(self, tenant_id: str) -> TenantQuota | None:
        """获取租户配额

        Args:
            tenant_id: 租户 ID

        Returns:
            配额配置
        """
        pass

    @abstractmethod
    async def update_quota(self, tenant_id: str, quota: TenantQuota) -> bool:
        """更新租户配额

        Args:
            tenant_id: 租户 ID
            quota: 新配额

        Returns:
            是否更新成功
        """
        pass

    # ========================================================================
    # 配置管理
    # ========================================================================

    @abstractmethod
    async def get_config(self, tenant_id: str) -> TenantConfig | None:
        """获取租户配置

        Args:
            tenant_id: 租户 ID

        Returns:
            配置
        """
        pass

    @abstractmethod
    async def update_config(self, tenant_id: str, config: TenantConfig) -> bool:
        """更新租户配置

        Args:
            tenant_id: 租户 ID
            config: 新配置

        Returns:
            是否更新成功
        """
        pass

    # ========================================================================
    # 使用统计
    # ========================================================================

    @abstractmethod
    async def get_usage(
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
        pass

    @abstractmethod
    async def record_usage(self, usage: TenantUsage) -> bool:
        """记录使用统计

        Args:
            usage: 使用统计

        Returns:
            是否记录成功
        """
        pass

    # ========================================================================
    # 事件记录
    # ========================================================================

    @abstractmethod
    async def record_event(self, event: TenantEvent) -> bool:
        """记录租户事件

        Args:
            event: 租户事件

        Returns:
            是否记录成功
        """
        pass

    @abstractmethod
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
        pass


# ============================================================================
# 内存存储实现
# ============================================================================


class MemoryTenantStorage(TenantStorage):
    """内存租户存储

    适用于测试和开发环境。
    """

    def __init__(self) -> None:
        self._tenants: dict[str, Tenant] = {}
        self._tenants_by_name: dict[str, str] = {}  # name -> id
        self._usage: dict[str, list[TenantUsage]] = {}  # tenant_id -> usages
        self._events: dict[str, list[TenantEvent]] = {}  # tenant_id -> events
        self._lock = asyncio.Lock()

    async def create(self, tenant: Tenant) -> Tenant:
        async with self._lock:
            if tenant.id in self._tenants:
                raise ValueError(f"租户已存在: {tenant.id}")
            if tenant.name in self._tenants_by_name:
                raise ValueError(f"租户名称已存在: {tenant.name}")

            self._tenants[tenant.id] = tenant
            self._tenants_by_name[tenant.name] = tenant.id
            self._usage[tenant.id] = []
            self._events[tenant.id] = []

            logger.debug(f"创建租户: {tenant.id}")
            return tenant

    async def get(self, tenant_id: str) -> Tenant | None:
        return self._tenants.get(tenant_id)

    async def get_by_name(self, name: str) -> Tenant | None:
        tenant_id = self._tenants_by_name.get(name)
        if tenant_id:
            return self._tenants.get(tenant_id)
        return None

    async def update(self, tenant: Tenant) -> Tenant:
        async with self._lock:
            if tenant.id not in self._tenants:
                raise ValueError(f"租户不存在: {tenant.id}")

            old_tenant = self._tenants[tenant.id]

            # 如果名称变更，更新名称索引
            if old_tenant.name != tenant.name:
                if tenant.name in self._tenants_by_name:
                    raise ValueError(f"租户名称已存在: {tenant.name}")
                del self._tenants_by_name[old_tenant.name]
                self._tenants_by_name[tenant.name] = tenant.id

            tenant.updated_at = datetime.now()
            self._tenants[tenant.id] = tenant

            logger.debug(f"更新租户: {tenant.id}")
            return tenant

    async def delete(self, tenant_id: str) -> bool:
        async with self._lock:
            if tenant_id not in self._tenants:
                return False

            tenant = self._tenants[tenant_id]
            del self._tenants_by_name[tenant.name]
            del self._tenants[tenant_id]

            if tenant_id in self._usage:
                del self._usage[tenant_id]
            if tenant_id in self._events:
                del self._events[tenant_id]

            logger.debug(f"删除租户: {tenant_id}")
            return True

    async def list(
        self,
        status: TenantStatus | None = None,
        tier: TenantTier | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> list[Tenant]:
        tenants = list(self._tenants.values())

        # 过滤
        if status:
            tenants = [t for t in tenants if t.status == status]
        if tier:
            tenants = [t for t in tenants if t.tier == tier]

        # 排序（按创建时间倒序）
        tenants.sort(key=lambda t: t.created_at, reverse=True)

        # 分页
        return tenants[offset : offset + limit]

    async def count(
        self,
        status: TenantStatus | None = None,
        tier: TenantTier | None = None,
    ) -> int:
        tenants = list(self._tenants.values())

        if status:
            tenants = [t for t in tenants if t.status == status]
        if tier:
            tenants = [t for t in tenants if t.tier == tier]

        return len(tenants)

    async def get_quota(self, tenant_id: str) -> TenantQuota | None:
        tenant = self._tenants.get(tenant_id)
        if tenant:
            return tenant.quota
        return None

    async def update_quota(self, tenant_id: str, quota: TenantQuota) -> bool:
        async with self._lock:
            if tenant_id not in self._tenants:
                return False

            tenant = self._tenants[tenant_id]
            tenant.quota = quota
            tenant.updated_at = datetime.now()
            return True

    async def get_config(self, tenant_id: str) -> TenantConfig | None:
        tenant = self._tenants.get(tenant_id)
        if tenant:
            return tenant.config
        return None

    async def update_config(self, tenant_id: str, config: TenantConfig) -> bool:
        async with self._lock:
            if tenant_id not in self._tenants:
                return False

            tenant = self._tenants[tenant_id]
            tenant.config = config
            tenant.updated_at = datetime.now()
            return True

    async def get_usage(
        self,
        tenant_id: str,
        period: str = "daily",
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[TenantUsage]:
        usages = self._usage.get(tenant_id, [])

        # 过滤
        filtered = [u for u in usages if u.period == period]

        if start_date:
            filtered = [u for u in filtered if u.period_start >= start_date]
        if end_date:
            filtered = [u for u in filtered if u.period_end <= end_date]

        return filtered

    async def record_usage(self, usage: TenantUsage) -> bool:
        if usage.tenant_id not in self._usage:
            self._usage[usage.tenant_id] = []

        self._usage[usage.tenant_id].append(usage)
        return True

    async def record_event(self, event: TenantEvent) -> bool:
        if event.tenant_id not in self._events:
            self._events[event.tenant_id] = []

        self._events[event.tenant_id].append(event)
        return True

    async def get_events(
        self,
        tenant_id: str,
        event_type: TenantEventType | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> list[TenantEvent]:
        events = self._events.get(tenant_id, [])

        # 过滤
        if event_type:
            events = [e for e in events if e.event_type == event_type]

        # 排序（按时间倒序）
        events.sort(key=lambda e: e.timestamp, reverse=True)

        # 分页
        return events[offset : offset + limit]


# ============================================================================
# 文件存储实现
# ============================================================================


class FileTenantStorage(TenantStorage):
    """文件租户存储

    将租户数据持久化到 JSON 文件。
    """

    def __init__(self, data_dir: Path):
        """初始化文件存储

        Args:
            data_dir: 数据目录
        """
        self.data_dir = data_dir
        self._tenants_file = data_dir / "tenants.json"
        self._usage_file = data_dir / "usage.json"
        self._events_file = data_dir / "events.json"
        self._lock = asyncio.Lock()

        # 内存缓存
        self._tenants: dict[str, Tenant] = {}
        self._tenants_by_name: dict[str, str] = {}
        self._usage: dict[str, list[TenantUsage]] = {}
        self._events: dict[str, list[TenantEvent]] = {}
        self._loaded = False

    async def _ensure_loaded(self) -> None:
        """确保数据已加载"""
        if self._loaded:
            return

        async with self._lock:
            if self._loaded:
                return

            self.data_dir.mkdir(parents=True, exist_ok=True)

            # 加载租户数据
            if self._tenants_file.exists():
                with open(self._tenants_file) as f:
                    data = json.load(f)
                    for item in data:
                        tenant = Tenant.model_validate(item)
                        self._tenants[tenant.id] = tenant
                        self._tenants_by_name[tenant.name] = tenant.id

            # 加载使用统计
            if self._usage_file.exists():
                with open(self._usage_file) as f:
                    data = json.load(f)
                    for tenant_id, usages in data.items():
                        self._usage[tenant_id] = [TenantUsage.model_validate(u) for u in usages]

            # 加载事件
            if self._events_file.exists():
                with open(self._events_file) as f:
                    data = json.load(f)
                    for tenant_id, events in data.items():
                        self._events[tenant_id] = [TenantEvent.model_validate(e) for e in events]

            self._loaded = True
            logger.debug(f"加载租户数据: {len(self._tenants)} 个租户")

    async def _save_tenants(self) -> None:
        """保存租户数据"""
        data = [t.model_dump(mode="json") for t in self._tenants.values()]
        with open(self._tenants_file, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)

    async def _save_usage(self) -> None:
        """保存使用统计"""
        data = {
            tid: [u.model_dump(mode="json") for u in usages]
            for tid, usages in self._usage.items()
        }
        with open(self._usage_file, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)

    async def _save_events(self) -> None:
        """保存事件"""
        data = {
            tid: [e.model_dump(mode="json") for e in events]
            for tid, events in self._events.items()
        }
        with open(self._events_file, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)

    async def create(self, tenant: Tenant) -> Tenant:
        await self._ensure_loaded()

        async with self._lock:
            if tenant.id in self._tenants:
                raise ValueError(f"租户已存在: {tenant.id}")
            if tenant.name in self._tenants_by_name:
                raise ValueError(f"租户名称已存在: {tenant.name}")

            self._tenants[tenant.id] = tenant
            self._tenants_by_name[tenant.name] = tenant.id
            self._usage[tenant.id] = []
            self._events[tenant.id] = []

            await self._save_tenants()

            logger.debug(f"创建租户: {tenant.id}")
            return tenant

    async def get(self, tenant_id: str) -> Tenant | None:
        await self._ensure_loaded()
        return self._tenants.get(tenant_id)

    async def get_by_name(self, name: str) -> Tenant | None:
        await self._ensure_loaded()
        tenant_id = self._tenants_by_name.get(name)
        if tenant_id:
            return self._tenants.get(tenant_id)
        return None

    async def update(self, tenant: Tenant) -> Tenant:
        await self._ensure_loaded()

        async with self._lock:
            if tenant.id not in self._tenants:
                raise ValueError(f"租户不存在: {tenant.id}")

            old_tenant = self._tenants[tenant.id]

            if old_tenant.name != tenant.name:
                if tenant.name in self._tenants_by_name:
                    raise ValueError(f"租户名称已存在: {tenant.name}")
                del self._tenants_by_name[old_tenant.name]
                self._tenants_by_name[tenant.name] = tenant.id

            tenant.updated_at = datetime.now()
            self._tenants[tenant.id] = tenant

            await self._save_tenants()

            logger.debug(f"更新租户: {tenant.id}")
            return tenant

    async def delete(self, tenant_id: str) -> bool:
        await self._ensure_loaded()

        async with self._lock:
            if tenant_id not in self._tenants:
                return False

            tenant = self._tenants[tenant_id]
            del self._tenants_by_name[tenant.name]
            del self._tenants[tenant_id]

            if tenant_id in self._usage:
                del self._usage[tenant_id]
            if tenant_id in self._events:
                del self._events[tenant_id]

            await self._save_tenants()
            await self._save_usage()
            await self._save_events()

            logger.debug(f"删除租户: {tenant_id}")
            return True

    async def list(
        self,
        status: TenantStatus | None = None,
        tier: TenantTier | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> list[Tenant]:
        await self._ensure_loaded()

        tenants = list(self._tenants.values())

        if status:
            tenants = [t for t in tenants if t.status == status]
        if tier:
            tenants = [t for t in tenants if t.tier == tier]

        tenants.sort(key=lambda t: t.created_at, reverse=True)
        return tenants[offset : offset + limit]

    async def count(
        self,
        status: TenantStatus | None = None,
        tier: TenantTier | None = None,
    ) -> int:
        await self._ensure_loaded()

        tenants = list(self._tenants.values())

        if status:
            tenants = [t for t in tenants if t.status == status]
        if tier:
            tenants = [t for t in tenants if t.tier == tier]

        return len(tenants)

    async def get_quota(self, tenant_id: str) -> TenantQuota | None:
        await self._ensure_loaded()
        tenant = self._tenants.get(tenant_id)
        if tenant:
            return tenant.quota
        return None

    async def update_quota(self, tenant_id: str, quota: TenantQuota) -> bool:
        await self._ensure_loaded()

        async with self._lock:
            if tenant_id not in self._tenants:
                return False

            tenant = self._tenants[tenant_id]
            tenant.quota = quota
            tenant.updated_at = datetime.now()

            await self._save_tenants()
            return True

    async def get_config(self, tenant_id: str) -> TenantConfig | None:
        await self._ensure_loaded()
        tenant = self._tenants.get(tenant_id)
        if tenant:
            return tenant.config
        return None

    async def update_config(self, tenant_id: str, config: TenantConfig) -> bool:
        await self._ensure_loaded()

        async with self._lock:
            if tenant_id not in self._tenants:
                return False

            tenant = self._tenants[tenant_id]
            tenant.config = config
            tenant.updated_at = datetime.now()

            await self._save_tenants()
            return True

    async def get_usage(
        self,
        tenant_id: str,
        period: str = "daily",
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[TenantUsage]:
        await self._ensure_loaded()

        usages = self._usage.get(tenant_id, [])
        filtered = [u for u in usages if u.period == period]

        if start_date:
            filtered = [u for u in filtered if u.period_start >= start_date]
        if end_date:
            filtered = [u for u in filtered if u.period_end <= end_date]

        return filtered

    async def record_usage(self, usage: TenantUsage) -> bool:
        await self._ensure_loaded()

        async with self._lock:
            if usage.tenant_id not in self._usage:
                self._usage[usage.tenant_id] = []

            self._usage[usage.tenant_id].append(usage)
            await self._save_usage()
            return True

    async def record_event(self, event: TenantEvent) -> bool:
        await self._ensure_loaded()

        async with self._lock:
            if event.tenant_id not in self._events:
                self._events[event.tenant_id] = []

            self._events[event.tenant_id].append(event)
            await self._save_events()
            return True

    async def get_events(
        self,
        tenant_id: str,
        event_type: TenantEventType | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> list[TenantEvent]:
        await self._ensure_loaded()

        events = self._events.get(tenant_id, [])

        if event_type:
            events = [e for e in events if e.event_type == event_type]

        events.sort(key=lambda e: e.timestamp, reverse=True)
        return events[offset : offset + limit]
