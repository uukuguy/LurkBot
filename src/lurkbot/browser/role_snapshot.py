"""
Role Snapshot - 可访问性角色快照

对标 MoltBot src/browser/role_snapshot.ts

角色快照将页面的可访问性树转换为结构化数据，
便于 AI Agent 理解页面结构并进行交互。
"""

from __future__ import annotations

from typing import Any

from loguru import logger

from .playwright_session import PlaywrightSession, get_session
from .types import BrowserNotConnectedError, RoleNode, RoleSnapshotResponse

# Playwright 导入（可选依赖）
try:
    from playwright.async_api import Page
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    Page = Any


# ============================================================================
# Role Snapshot Generator
# ============================================================================

class RoleSnapshotGenerator:
    """
    角色快照生成器

    从 Playwright 页面的可访问性树生成结构化快照。
    """

    def __init__(
        self,
        include_hidden: bool = False,
        max_depth: int = 10,
    ):
        """
        初始化生成器

        Args:
            include_hidden: 是否包含隐藏元素
            max_depth: 最大遍历深度
        """
        self._include_hidden = include_hidden
        self._max_depth = max_depth
        self._node_count = 0
        self._ref_counter = 0

    async def generate(
        self,
        page: Page,
        root_selector: str | None = None,
    ) -> RoleSnapshotResponse:
        """
        生成角色快照

        Args:
            page: Playwright 页面
            root_selector: 可选的根元素选择器

        Returns:
            RoleSnapshotResponse
        """
        self._node_count = 0
        self._ref_counter = 0

        try:
            # 获取可访问性快照
            if root_selector:
                element = page.locator(root_selector)
                snapshot = await element.evaluate(
                    "element => element.ariaSnapshot ? element.ariaSnapshot() : null"
                )
                if not snapshot:
                    # 回退到整页快照
                    snapshot = await page.accessibility.snapshot(
                        interesting_only=not self._include_hidden
                    )
            else:
                snapshot = await page.accessibility.snapshot(
                    interesting_only=not self._include_hidden
                )

            if not snapshot:
                return RoleSnapshotResponse(
                    success=True,
                    root=RoleNode(role="document", name="Empty page"),
                    total_nodes=0,
                )

            # 转换为 RoleNode 树
            root = self._convert_node(snapshot, depth=0)

            return RoleSnapshotResponse(
                success=True,
                root=root,
                total_nodes=self._node_count,
            )

        except Exception as e:
            logger.error(f"Failed to generate role snapshot: {e}")
            return RoleSnapshotResponse(
                success=False,
                error=str(e),
            )

    def _convert_node(
        self,
        node: dict[str, Any],
        depth: int,
    ) -> RoleNode:
        """
        转换可访问性节点为 RoleNode

        Args:
            node: 原始可访问性节点
            depth: 当前深度

        Returns:
            RoleNode 实例
        """
        self._node_count += 1
        self._ref_counter += 1

        # 基本属性
        role = node.get("role", "generic")
        name = node.get("name")
        value = node.get("value")
        description = node.get("description")

        # 状态属性
        focused = node.get("focused", False)
        disabled = node.get("disabled", False)
        checked = node.get("checked")
        selected = node.get("selected")
        expanded = node.get("expanded")
        level = node.get("level")

        # 生成引用 ID
        ref = f"e{self._ref_counter}"

        # 递归处理子节点
        children = []
        if depth < self._max_depth:
            for child in node.get("children", []):
                children.append(self._convert_node(child, depth + 1))

        return RoleNode(
            role=role,
            name=name,
            value=value,
            description=description,
            focused=focused,
            disabled=disabled,
            checked=checked,
            selected=selected,
            expanded=expanded,
            level=level,
            children=children,
            ref=ref,
        )


# ============================================================================
# Snapshot Functions
# ============================================================================

async def get_role_snapshot(
    session: PlaywrightSession | None = None,
    include_hidden: bool = False,
    max_depth: int = 10,
    root_selector: str | None = None,
) -> RoleSnapshotResponse:
    """
    获取页面角色快照

    Args:
        session: Playwright 会话（None 则使用全局会话）
        include_hidden: 是否包含隐藏元素
        max_depth: 最大深度
        root_selector: 根元素选择器

    Returns:
        RoleSnapshotResponse
    """
    if session is None:
        session = await get_session()

    page = session.page
    if not page:
        raise BrowserNotConnectedError()

    generator = RoleSnapshotGenerator(
        include_hidden=include_hidden,
        max_depth=max_depth,
    )

    return await generator.generate(page, root_selector)


def format_role_tree(
    node: RoleNode,
    indent: int = 0,
    show_refs: bool = True,
) -> str:
    """
    格式化角色树为文本

    Args:
        node: 根节点
        indent: 缩进级别
        show_refs: 是否显示引用 ID

    Returns:
        格式化的文本
    """
    lines = []
    prefix = "  " * indent

    # 构建节点描述
    parts = [node.role]

    if node.name:
        parts.append(f'"{node.name}"')

    if node.value:
        parts.append(f"value={node.value}")

    # 状态标记
    flags = []
    if node.focused:
        flags.append("focused")
    if node.disabled:
        flags.append("disabled")
    if node.checked is True:
        flags.append("checked")
    elif node.checked == "mixed":
        flags.append("mixed")
    if node.selected:
        flags.append("selected")
    if node.expanded is not None:
        flags.append("expanded" if node.expanded else "collapsed")

    if flags:
        parts.append(f"[{', '.join(flags)}]")

    if show_refs and node.ref:
        parts.append(f"(ref={node.ref})")

    lines.append(f"{prefix}- {' '.join(parts)}")

    # 递归处理子节点
    for child in node.children:
        lines.append(format_role_tree(child, indent + 1, show_refs))

    return "\n".join(lines)


def find_nodes_by_role(
    root: RoleNode,
    role: str,
    name: str | None = None,
) -> list[RoleNode]:
    """
    按角色查找节点

    Args:
        root: 根节点
        role: 目标角色
        name: 可选的名称过滤

    Returns:
        匹配的节点列表
    """
    results = []

    def search(node: RoleNode) -> None:
        if node.role == role:
            if name is None or node.name == name:
                results.append(node)
        for child in node.children:
            search(child)

    search(root)
    return results


def find_node_by_ref(
    root: RoleNode,
    ref: str,
) -> RoleNode | None:
    """
    按引用 ID 查找节点

    Args:
        root: 根节点
        ref: 引用 ID

    Returns:
        匹配的节点或 None
    """
    if root.ref == ref:
        return root

    for child in root.children:
        result = find_node_by_ref(child, ref)
        if result:
            return result

    return None


def get_interactive_elements(root: RoleNode) -> list[RoleNode]:
    """
    获取所有可交互元素

    Args:
        root: 根节点

    Returns:
        可交互元素列表
    """
    interactive_roles = {
        "button",
        "link",
        "textbox",
        "checkbox",
        "radio",
        "combobox",
        "listbox",
        "option",
        "menuitem",
        "tab",
        "slider",
        "spinbutton",
        "switch",
        "searchbox",
    }

    results = []

    def search(node: RoleNode) -> None:
        if node.role in interactive_roles and not node.disabled:
            results.append(node)
        for child in node.children:
            search(child)

    search(root)
    return results


def summarize_snapshot(root: RoleNode) -> dict[str, Any]:
    """
    生成快照摘要

    Args:
        root: 根节点

    Returns:
        摘要信息
    """
    role_counts: dict[str, int] = {}
    total_nodes = 0
    interactive_count = 0

    interactive_roles = {
        "button", "link", "textbox", "checkbox", "radio",
        "combobox", "listbox", "menuitem", "tab", "slider",
    }

    def count(node: RoleNode) -> None:
        nonlocal total_nodes, interactive_count

        total_nodes += 1
        role_counts[node.role] = role_counts.get(node.role, 0) + 1

        if node.role in interactive_roles and not node.disabled:
            interactive_count += 1

        for child in node.children:
            count(child)

    count(root)

    return {
        "total_nodes": total_nodes,
        "interactive_elements": interactive_count,
        "role_distribution": role_counts,
        "top_roles": sorted(
            role_counts.items(),
            key=lambda x: x[1],
            reverse=True,
        )[:10],
    }


# ============================================================================
# Aria Snapshot (Alternative Method)
# ============================================================================

async def get_aria_snapshot(
    session: PlaywrightSession | None = None,
    selector: str | None = None,
) -> str:
    """
    获取 ARIA 快照（Playwright 内置方法）

    这是一个更简洁的快照格式，适合直接传递给 AI。

    Args:
        session: Playwright 会话
        selector: 可选的元素选择器

    Returns:
        ARIA 快照文本
    """
    if session is None:
        session = await get_session()

    page = session.page
    if not page:
        raise BrowserNotConnectedError()

    try:
        if selector:
            element = page.locator(selector)
            return await element.aria_snapshot()
        else:
            # 获取整页快照
            return await page.locator("body").aria_snapshot()
    except Exception as e:
        logger.error(f"Failed to get ARIA snapshot: {e}")
        return f"Error: {e}"


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    "RoleSnapshotGenerator",
    "get_role_snapshot",
    "format_role_tree",
    "find_nodes_by_role",
    "find_node_by_ref",
    "get_interactive_elements",
    "summarize_snapshot",
    "get_aria_snapshot",
]
