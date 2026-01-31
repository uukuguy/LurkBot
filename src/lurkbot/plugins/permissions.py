"""插件权限细化系统

提供细粒度的插件权限控制和审计功能。

核心功能：
1. 权限模型设计 - 定义权限类型和层级
2. 权限检查机制 - 运行时权限验证
3. 权限审计日志 - 记录权限使用情况
4. 权限管理 API - 提供权限管理接口
"""

import asyncio
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from loguru import logger
from pydantic import BaseModel, Field


# ============================================================================
# 权限类型定义
# ============================================================================


class PermissionType(str, Enum):
    """权限类型"""

    # 文件系统权限
    FILESYSTEM_READ = "filesystem.read"  # 读取文件
    FILESYSTEM_WRITE = "filesystem.write"  # 写入文件
    FILESYSTEM_DELETE = "filesystem.delete"  # 删除文件
    FILESYSTEM_EXECUTE = "filesystem.execute"  # 执行文件

    # 网络权限
    NETWORK_HTTP = "network.http"  # HTTP 请求
    NETWORK_HTTPS = "network.https"  # HTTPS 请求
    NETWORK_WEBSOCKET = "network.websocket"  # WebSocket 连接
    NETWORK_SOCKET = "network.socket"  # 原始 Socket

    # 系统权限
    SYSTEM_EXEC = "system.exec"  # 执行系统命令
    SYSTEM_ENV = "system.env"  # 访问环境变量
    SYSTEM_PROCESS = "system.process"  # 进程管理

    # 数据权限
    DATA_READ = "data.read"  # 读取数据
    DATA_WRITE = "data.write"  # 写入数据
    DATA_DELETE = "data.delete"  # 删除数据

    # 频道权限
    CHANNEL_READ = "channel.read"  # 读取频道消息
    CHANNEL_WRITE = "channel.write"  # 发送频道消息
    CHANNEL_MANAGE = "channel.manage"  # 管理频道

    # 插件权限
    PLUGIN_LOAD = "plugin.load"  # 加载插件
    PLUGIN_UNLOAD = "plugin.unload"  # 卸载插件
    PLUGIN_EXECUTE = "plugin.execute"  # 执行插件


class PermissionLevel(str, Enum):
    """权限级别"""

    NONE = "none"  # 无权限
    READ = "read"  # 只读
    WRITE = "write"  # 读写
    ADMIN = "admin"  # 管理员


class AuditAction(str, Enum):
    """审计动作"""

    GRANT = "grant"  # 授予权限
    REVOKE = "revoke"  # 撤销权限
    CHECK = "check"  # 检查权限
    DENY = "deny"  # 拒绝访问
    ALLOW = "allow"  # 允许访问


# ============================================================================
# 权限模型
# ============================================================================


class Permission(BaseModel):
    """权限定义"""

    type: PermissionType = Field(..., description="权限类型")
    resource: str | None = Field(None, description="资源标识（如文件路径、URL）")
    level: PermissionLevel = Field(PermissionLevel.READ, description="权限级别")
    conditions: dict[str, Any] = Field(default_factory=dict, description="权限条件")

    def matches(self, other: "Permission") -> bool:
        """检查权限是否匹配

        Args:
            other: 要检查的权限

        Returns:
            是否匹配
        """
        # 类型必须匹配
        if self.type != other.type:
            return False

        # 如果指定了资源，资源必须匹配
        if self.resource and other.resource:
            # 支持通配符匹配
            if self.resource.endswith("*"):
                prefix = self.resource[:-1]
                if not other.resource.startswith(prefix):
                    return False
            elif self.resource != other.resource:
                return False

        # 权限级别必须足够
        level_order = [
            PermissionLevel.NONE,
            PermissionLevel.READ,
            PermissionLevel.WRITE,
            PermissionLevel.ADMIN,
        ]
        if level_order.index(self.level) < level_order.index(other.level):
            return False

        return True


class PermissionSet(BaseModel):
    """权限集合"""

    plugin_name: str = Field(..., description="插件名称")
    permissions: list[Permission] = Field(default_factory=list, description="权限列表")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")

    def has_permission(self, permission: Permission) -> bool:
        """检查是否拥有指定权限

        Args:
            permission: 要检查的权限

        Returns:
            是否拥有权限
        """
        return any(p.matches(permission) for p in self.permissions)

    def add_permission(self, permission: Permission) -> None:
        """添加权限

        Args:
            permission: 要添加的权限
        """
        if not self.has_permission(permission):
            self.permissions.append(permission)
            self.updated_at = datetime.now()

    def remove_permission(self, permission: Permission) -> bool:
        """移除权限

        Args:
            permission: 要移除的权限

        Returns:
            是否成功移除
        """
        original_len = len(self.permissions)
        self.permissions = [p for p in self.permissions if not p.matches(permission)]
        if len(self.permissions) < original_len:
            self.updated_at = datetime.now()
            return True
        return False


class AuditLog(BaseModel):
    """审计日志"""

    plugin_name: str = Field(..., description="插件名称")
    action: AuditAction = Field(..., description="审计动作")
    permission: Permission = Field(..., description="相关权限")
    timestamp: datetime = Field(default_factory=datetime.now, description="时间戳")
    success: bool = Field(True, description="是否成功")
    reason: str | None = Field(None, description="原因")
    metadata: dict[str, Any] = Field(default_factory=dict, description="额外元数据")


# ============================================================================
# 权限管理器
# ============================================================================


class PermissionManager:
    """权限管理器

    负责管理插件权限、检查权限和记录审计日志。
    """

    def __init__(self):
        """初始化权限管理器"""
        self._permission_sets: dict[str, PermissionSet] = {}
        self._audit_logs: list[AuditLog] = []
        self._lock = asyncio.Lock()

    async def grant_permission(
        self, plugin_name: str, permission: Permission
    ) -> bool:
        """授予权限

        Args:
            plugin_name: 插件名称
            permission: 要授予的权限

        Returns:
            是否成功授予
        """
        async with self._lock:
            if plugin_name not in self._permission_sets:
                self._permission_sets[plugin_name] = PermissionSet(
                    plugin_name=plugin_name
                )

            perm_set = self._permission_sets[plugin_name]
            perm_set.add_permission(permission)

            # 记录审计日志
            await self._log_audit(
                plugin_name=plugin_name,
                action=AuditAction.GRANT,
                permission=permission,
                success=True,
            )

            logger.info(
                f"授予权限: {plugin_name} -> {permission.type} ({permission.resource})"
            )
            return True

    async def revoke_permission(
        self, plugin_name: str, permission: Permission
    ) -> bool:
        """撤销权限

        Args:
            plugin_name: 插件名称
            permission: 要撤销的权限

        Returns:
            是否成功撤销
        """
        async with self._lock:
            if plugin_name not in self._permission_sets:
                return False

            perm_set = self._permission_sets[plugin_name]
            success = perm_set.remove_permission(permission)

            # 记录审计日志
            await self._log_audit(
                plugin_name=plugin_name,
                action=AuditAction.REVOKE,
                permission=permission,
                success=success,
            )

            if success:
                logger.info(
                    f"撤销权限: {plugin_name} -> {permission.type} ({permission.resource})"
                )

            return success

    async def check_permission(
        self, plugin_name: str, permission: Permission
    ) -> bool:
        """检查权限

        Args:
            plugin_name: 插件名称
            permission: 要检查的权限

        Returns:
            是否拥有权限
        """
        async with self._lock:
            if plugin_name not in self._permission_sets:
                await self._log_audit(
                    plugin_name=plugin_name,
                    action=AuditAction.DENY,
                    permission=permission,
                    success=False,
                    reason="插件未注册",
                )
                return False

            perm_set = self._permission_sets[plugin_name]
            has_perm = perm_set.has_permission(permission)

            # 记录审计日志
            await self._log_audit(
                plugin_name=plugin_name,
                action=AuditAction.ALLOW if has_perm else AuditAction.DENY,
                permission=permission,
                success=has_perm,
                reason=None if has_perm else "权限不足",
            )

            return has_perm

    async def get_permissions(self, plugin_name: str) -> list[Permission]:
        """获取插件的所有权限

        Args:
            plugin_name: 插件名称

        Returns:
            权限列表
        """
        async with self._lock:
            if plugin_name not in self._permission_sets:
                return []
            return self._permission_sets[plugin_name].permissions.copy()

    async def revoke_all_permissions(self, plugin_name: str) -> bool:
        """撤销插件的所有权限

        Args:
            plugin_name: 插件名称

        Returns:
            是否成功撤销
        """
        async with self._lock:
            if plugin_name in self._permission_sets:
                del self._permission_sets[plugin_name]
                logger.info(f"撤销所有权限: {plugin_name}")
                return True
            return False

    async def get_audit_logs(
        self,
        plugin_name: str | None = None,
        action: AuditAction | None = None,
        limit: int = 100,
    ) -> list[AuditLog]:
        """获取审计日志

        Args:
            plugin_name: 插件名称（可选）
            action: 审计动作（可选）
            limit: 返回数量限制

        Returns:
            审计日志列表
        """
        async with self._lock:
            logs = self._audit_logs.copy()

            # 过滤
            if plugin_name:
                logs = [log for log in logs if log.plugin_name == plugin_name]
            if action:
                logs = [log for log in logs if log.action == action]

            # 按时间倒序排序
            logs.sort(key=lambda x: x.timestamp, reverse=True)

            return logs[:limit]

    async def clear_audit_logs(self) -> int:
        """清空审计日志

        Returns:
            清空的日志数量
        """
        async with self._lock:
            count = len(self._audit_logs)
            self._audit_logs.clear()
            logger.info(f"清空审计日志: {count} 条")
            return count

    async def _log_audit(
        self,
        plugin_name: str,
        action: AuditAction,
        permission: Permission,
        success: bool,
        reason: str | None = None,
    ) -> None:
        """记录审计日志

        Args:
            plugin_name: 插件名称
            action: 审计动作
            permission: 相关权限
            success: 是否成功
            reason: 原因
        """
        log = AuditLog(
            plugin_name=plugin_name,
            action=action,
            permission=permission,
            success=success,
            reason=reason,
        )
        self._audit_logs.append(log)

    def get_stats(self) -> dict[str, Any]:
        """获取统计信息

        Returns:
            统计信息字典
        """
        return {
            "total_plugins": len(self._permission_sets),
            "total_permissions": sum(
                len(ps.permissions) for ps in self._permission_sets.values()
            ),
            "total_audit_logs": len(self._audit_logs),
        }


# ============================================================================
# 权限检查装饰器
# ============================================================================


def require_permission(permission_type: PermissionType, resource: str | None = None):
    """权限检查装饰器

    Args:
        permission_type: 权限类型
        resource: 资源标识

    Returns:
        装饰器函数
    """

    def decorator(func):
        async def wrapper(self, *args, **kwargs):
            # 获取插件名称
            plugin_name = getattr(self, "name", "unknown")

            # 检查权限
            manager = get_permission_manager()
            permission = Permission(type=permission_type, resource=resource)

            if not await manager.check_permission(plugin_name, permission):
                raise PermissionError(
                    f"插件 {plugin_name} 没有权限: {permission_type} ({resource})"
                )

            return await func(self, *args, **kwargs)

        return wrapper

    return decorator


# ============================================================================
# 全局单例
# ============================================================================

_permission_manager: PermissionManager | None = None


def get_permission_manager() -> PermissionManager:
    """��取全局权限管理器实例

    Returns:
        PermissionManager 实例
    """
    global _permission_manager
    if _permission_manager is None:
        _permission_manager = PermissionManager()
    return _permission_manager


def reset_permission_manager() -> None:
    """重置全局权限管理器（主要用于测试）"""
    global _permission_manager
    _permission_manager = None
