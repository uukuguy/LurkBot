"""权限继承

提供层级化的权限继承管理功能。

支持以下继承链：
- 租户 → 组 → 用户
- 父角色 → 子角色
"""

from __future__ import annotations

import asyncio
from typing import Any

from loguru import logger
from pydantic import BaseModel, Field


# ============================================================================
# 继承节点
# ============================================================================


class InheritanceNode(BaseModel):
    """继承节点"""

    id: str = Field(description="节点标识")
    node_type: str = Field(description="节点类型 (tenant, group, user, role)")
    display_name: str = Field(default="", description="显示名称")
    parent_ids: list[str] = Field(default_factory=list, description="父节点 ID 列表")
    metadata: dict[str, Any] = Field(default_factory=dict, description="元数据")

    # 直接授予的权限
    granted_permissions: set[str] = Field(
        default_factory=set, description="授予的权限"
    )
    denied_permissions: set[str] = Field(
        default_factory=set, description="拒绝的权限"
    )


# ============================================================================
# 继承解析结果
# ============================================================================


class ResolvedPermissions(BaseModel):
    """解析后的权限集合"""

    principal_id: str = Field(description="主体 ID")
    granted: set[str] = Field(default_factory=set, description="有效的授予权限")
    denied: set[str] = Field(default_factory=set, description="有效的拒绝权限")
    inheritance_chain: list[str] = Field(
        default_factory=list, description="继承链路径"
    )

    def has_permission(self, permission: str) -> bool:
        """检查是否拥有权限

        拒绝权限优先于授予权限。

        Args:
            permission: 权限标识

        Returns:
            是否拥有权限
        """
        if permission in self.denied:
            return False
        return permission in self.granted


# ============================================================================
# 继承管理器
# ============================================================================


class InheritanceManager:
    """权限继承管理器

    管理层级化的权限继承关系，支持：
    - 多级继承（租户→组→用户）
    - 权限合并（继承 + 直接授予）
    - 拒绝优先（显式拒绝覆盖继承的授予）
    - 循环检测
    """

    def __init__(self) -> None:
        self._nodes: dict[str, InheritanceNode] = {}
        self._lock = asyncio.Lock()

    # ========================================================================
    # 节点管理
    # ========================================================================

    async def add_node(self, node: InheritanceNode) -> None:
        """添加节点

        Args:
            node: 继承节点
        """
        async with self._lock:
            self._nodes[node.id] = node
            logger.debug(f"添加继承节点: {node.id} ({node.node_type})")

    async def remove_node(self, node_id: str) -> bool:
        """移除节点

        Args:
            node_id: 节点 ID

        Returns:
            是否移除成功
        """
        async with self._lock:
            if node_id in self._nodes:
                del self._nodes[node_id]
                # 清理其他节点中的引用
                for node in self._nodes.values():
                    if node_id in node.parent_ids:
                        node.parent_ids.remove(node_id)
                logger.debug(f"移除继承节点: {node_id}")
                return True
            return False

    async def get_node(self, node_id: str) -> InheritanceNode | None:
        """获取节点

        Args:
            node_id: 节点 ID

        Returns:
            继承节点
        """
        return self._nodes.get(node_id)

    async def set_parents(self, node_id: str, parent_ids: list[str]) -> bool:
        """设置父节点

        Args:
            node_id: 节点 ID
            parent_ids: 父节点 ID 列表

        Returns:
            是否设置成功

        Raises:
            ValueError: 循环继承
        """
        async with self._lock:
            if node_id not in self._nodes:
                return False

            # 循环检测
            for parent_id in parent_ids:
                if self._would_create_cycle(node_id, parent_id):
                    raise ValueError(
                        f"设置继承关系会产生循环: {node_id} -> {parent_id}"
                    )

            self._nodes[node_id].parent_ids = parent_ids
            return True

    # ========================================================================
    # 权限管理
    # ========================================================================

    async def grant_permission(self, node_id: str, permission: str) -> bool:
        """授予权限

        Args:
            node_id: 节点 ID
            permission: 权限标识

        Returns:
            是否成功
        """
        async with self._lock:
            if node_id not in self._nodes:
                return False

            self._nodes[node_id].granted_permissions.add(permission)
            return True

    async def deny_permission(self, node_id: str, permission: str) -> bool:
        """拒绝权限

        Args:
            node_id: 节点 ID
            permission: 权限标识

        Returns:
            是否成功
        """
        async with self._lock:
            if node_id not in self._nodes:
                return False

            self._nodes[node_id].denied_permissions.add(permission)
            return True

    async def revoke_permission(self, node_id: str, permission: str) -> bool:
        """撤销权限（从授予和拒绝中移除）

        Args:
            node_id: 节点 ID
            permission: 权限标识

        Returns:
            是否成功
        """
        async with self._lock:
            if node_id not in self._nodes:
                return False

            self._nodes[node_id].granted_permissions.discard(permission)
            self._nodes[node_id].denied_permissions.discard(permission)
            return True

    # ========================================================================
    # 权限解析
    # ========================================================================

    async def resolve_permissions(self, node_id: str) -> ResolvedPermissions:
        """解析节点的有效权限

        遍历继承链，合并所有权限。

        Args:
            node_id: 节点 ID

        Returns:
            解析后的权限集合
        """
        granted: set[str] = set()
        denied: set[str] = set()
        chain: list[str] = []
        visited: set[str] = set()

        self._collect_permissions(node_id, granted, denied, chain, visited)

        return ResolvedPermissions(
            principal_id=node_id,
            granted=granted - denied,  # 拒绝优先
            denied=denied,
            inheritance_chain=chain,
        )

    async def has_permission(self, node_id: str, permission: str) -> bool:
        """检查节点是否拥有权限

        Args:
            node_id: 节点 ID
            permission: 权限标识

        Returns:
            是否拥有权限
        """
        resolved = await self.resolve_permissions(node_id)
        return resolved.has_permission(permission)

    # ========================================================================
    # 查询
    # ========================================================================

    async def get_children(self, node_id: str) -> list[str]:
        """获取子节点列表

        Args:
            node_id: 节点 ID

        Returns:
            子节点 ID 列表
        """
        return [
            n.id for n in self._nodes.values()
            if node_id in n.parent_ids
        ]

    async def get_ancestors(self, node_id: str) -> list[str]:
        """获取所有祖先节点

        Args:
            node_id: 节点 ID

        Returns:
            祖先节点 ID 列表
        """
        result: list[str] = []
        visited: set[str] = set()
        self._collect_ancestors(node_id, result, visited)
        return result

    async def get_hierarchy(self) -> dict[str, Any]:
        """获取继承层次结构

        Returns:
            层次结构信息
        """
        roots = [
            n.id for n in self._nodes.values()
            if not n.parent_ids
        ]

        def build_tree(node_id: str, visited: set[str]) -> dict[str, Any]:
            if node_id in visited:
                return {"id": node_id, "circular": True}
            visited.add(node_id)

            node = self._nodes.get(node_id)
            if not node:
                return {"id": node_id, "missing": True}

            children_ids = [
                n.id for n in self._nodes.values()
                if node_id in n.parent_ids
            ]

            return {
                "id": node.id,
                "type": node.node_type,
                "display_name": node.display_name,
                "permissions": {
                    "granted": list(node.granted_permissions),
                    "denied": list(node.denied_permissions),
                },
                "children": [
                    build_tree(c, visited.copy()) for c in children_ids
                ],
            }

        return {
            "roots": [build_tree(r, set()) for r in roots],
            "total_nodes": len(self._nodes),
        }

    # ========================================================================
    # 内部方法
    # ========================================================================

    def _collect_permissions(
        self,
        node_id: str,
        granted: set[str],
        denied: set[str],
        chain: list[str],
        visited: set[str],
    ) -> None:
        """收集权限（递归遍历继承链）

        Args:
            node_id: 当前节点 ID
            granted: 授予权限集合
            denied: 拒绝权限集合
            chain: 继承链
            visited: 已访问节点（防止循环）
        """
        if node_id in visited:
            return
        visited.add(node_id)

        node = self._nodes.get(node_id)
        if not node:
            return

        chain.append(node_id)

        # 添加当前节点的权限
        granted.update(node.granted_permissions)
        denied.update(node.denied_permissions)

        # 递归处理父节点
        for parent_id in node.parent_ids:
            self._collect_permissions(parent_id, granted, denied, chain, visited)

    def _collect_ancestors(
        self,
        node_id: str,
        result: list[str],
        visited: set[str],
    ) -> None:
        """收集祖先节点

        Args:
            node_id: 当前节点 ID
            result: 结果列表
            visited: 已访问节点
        """
        if node_id in visited:
            return
        visited.add(node_id)

        node = self._nodes.get(node_id)
        if not node:
            return

        for parent_id in node.parent_ids:
            result.append(parent_id)
            self._collect_ancestors(parent_id, result, visited)

    def _would_create_cycle(self, node_id: str, new_parent_id: str) -> bool:
        """检查是否会产生循环

        Args:
            node_id: 子节点 ID
            new_parent_id: 新父节点 ID

        Returns:
            是否会产生循环
        """
        if node_id == new_parent_id:
            return True

        # 检查 node_id 是否是 new_parent_id 的祖先
        visited: set[str] = set()
        return self._is_ancestor(node_id, new_parent_id, visited)

    def _is_ancestor(
        self,
        target: str,
        current: str,
        visited: set[str],
    ) -> bool:
        """检查 target 是否是 current 的祖先

        Args:
            target: 目标节点 ID
            current: 当前节点 ID
            visited: 已访问节点

        Returns:
            是否是祖先
        """
        if current in visited:
            return False
        visited.add(current)

        node = self._nodes.get(current)
        if not node:
            return False

        for parent_id in node.parent_ids:
            if parent_id == target:
                return True
            if self._is_ancestor(target, parent_id, visited):
                return True

        return False
