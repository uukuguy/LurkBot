"""插件编排系统

支持插件依赖管理、执行顺序控制和条件执行。

核心功能：
1. 依赖图构建 - 解析插件依赖关系
2. 拓扑排序执行 - 按依赖顺序执行插件
3. 循环依赖检测 - 检测并报告循环依赖
4. 条件执行 - 支持基于条件的插件执行
"""

from collections import defaultdict, deque
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable

from loguru import logger
from pydantic import BaseModel, Field

from lurkbot.plugins.models import PluginExecutionContext, PluginExecutionResult


# ============================================================================
# 数据模型
# ============================================================================


class ExecutionConditionType(str, Enum):
    """执行条件类型"""

    ALWAYS = "always"  # 总是执行
    ON_SUCCESS = "on_success"  # 前置插件成功时执行
    ON_FAILURE = "on_failure"  # 前置插件失败时执行
    CUSTOM = "custom"  # 自定义条件


class ExecutionCondition(BaseModel):
    """执行条件"""

    type: ExecutionConditionType = Field(
        ExecutionConditionType.ALWAYS, description="条件类型"
    )
    depends_on: list[str] = Field(default_factory=list, description="依赖的插件名称列表")
    custom_check: Callable[[dict[str, PluginExecutionResult]], bool] | None = Field(
        None, description="自定义条件检查函数"
    )

    class Config:
        arbitrary_types_allowed = True


class PluginNode(BaseModel):
    """插件节点"""

    name: str = Field(..., description="插件名称")
    dependencies: list[str] = Field(default_factory=list, description="依赖的插件列表")
    condition: ExecutionCondition = Field(
        default_factory=ExecutionCondition, description="执行条件"
    )
    priority: int = Field(100, description="优先级（数字越小优先级越高）")

    class Config:
        arbitrary_types_allowed = True


@dataclass
class ExecutionPlan:
    """执行计划"""

    stages: list[list[str]]  # 执行阶段，每个阶段包含可并发执行的插件
    total_plugins: int  # 总插件数
    has_cycles: bool  # 是否存在循环依赖
    cycle_info: list[list[str]] | None = None  # 循环依赖信息


# ============================================================================
# 插件编排器
# ============================================================================


class PluginOrchestrator:
    """插件编排器

    负责管理插件依赖关系、执行顺序和条件执行。
    """

    def __init__(self):
        """初始化编排器"""
        self._nodes: dict[str, PluginNode] = {}
        self._execution_results: dict[str, PluginExecutionResult] = {}

    def register_plugin(
        self,
        name: str,
        dependencies: list[str] | None = None,
        condition: ExecutionCondition | None = None,
        priority: int = 100,
    ) -> None:
        """注册插件节点

        Args:
            name: 插件名称
            dependencies: 依赖的插件列表
            condition: 执行条件
            priority: 优先级
        """
        node = PluginNode(
            name=name,
            dependencies=dependencies or [],
            condition=condition or ExecutionCondition(),
            priority=priority,
        )
        self._nodes[name] = node
        logger.debug(f"注册插件节点: {name}, 依赖: {dependencies}")

    def unregister_plugin(self, name: str) -> bool:
        """注销插件节点

        Args:
            name: 插件名称

        Returns:
            是否成功注销
        """
        if name in self._nodes:
            del self._nodes[name]
            logger.debug(f"注销插件节点: {name}")
            return True
        return False

    def build_dependency_graph(self) -> dict[str, list[str]]:
        """构建依赖图

        Returns:
            依赖图字典 {plugin_name: [dependent_plugins]}
        """
        graph: dict[str, list[str]] = defaultdict(list)

        for node in self._nodes.values():
            # 确保所有节点都在图中
            if node.name not in graph:
                graph[node.name] = []

            # 添加依赖关系
            for dep in node.dependencies:
                if dep not in self._nodes:
                    logger.warning(f"插件 {node.name} 依赖的插件 {dep} 不存在")
                    continue
                graph[dep].append(node.name)

        return dict(graph)

    def detect_cycles(self) -> tuple[bool, list[list[str]] | None]:
        """检测循环依赖

        Returns:
            (是否存在循环, 循环路径列表)
        """
        # 构建邻接表（反向图，用于检测循环）
        adj: dict[str, list[str]] = defaultdict(list)
        for node in self._nodes.values():
            for dep in node.dependencies:
                if dep in self._nodes:
                    adj[node.name].append(dep)

        # DFS 检测循环
        visited: set[str] = set()
        rec_stack: set[str] = set()
        cycles: list[list[str]] = []

        def dfs(node: str, path: list[str]) -> bool:
            """DFS 遍历检测循环"""
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in adj.get(node, []):
                if neighbor not in visited:
                    if dfs(neighbor, path.copy()):
                        return True
                elif neighbor in rec_stack:
                    # 找到循环
                    cycle_start = path.index(neighbor)
                    cycle = path[cycle_start:] + [neighbor]
                    cycles.append(cycle)
                    return True

            rec_stack.remove(node)
            return False

        for node_name in self._nodes:
            if node_name not in visited:
                dfs(node_name, [])

        has_cycles = len(cycles) > 0
        if has_cycles:
            logger.error(f"检测到循环依赖: {cycles}")

        return has_cycles, cycles if has_cycles else None

    def topological_sort(self) -> list[list[str]]:
        """拓扑排序

        Returns:
            执行阶段列表，每个阶段包含可并发执行的插件
        """
        # 计算入度
        in_degree: dict[str, int] = {name: 0 for name in self._nodes}
        adj: dict[str, list[str]] = defaultdict(list)

        for node in self._nodes.values():
            for dep in node.dependencies:
                if dep in self._nodes:
                    adj[dep].append(node.name)
                    in_degree[node.name] += 1

        # 按优先级排序入度为 0 的节点
        queue = deque(
            sorted(
                [name for name, degree in in_degree.items() if degree == 0],
                key=lambda x: self._nodes[x].priority,
            )
        )

        stages: list[list[str]] = []
        processed = 0

        while queue:
            # 当前阶段可并发执行的插件
            current_stage = list(queue)
            stages.append(current_stage)
            queue.clear()

            # 处理当前阶段的所有节点
            for node_name in current_stage:
                processed += 1
                # 更新依赖此节点的其他节点的入度
                for neighbor in adj[node_name]:
                    in_degree[neighbor] -= 1
                    if in_degree[neighbor] == 0:
                        queue.append(neighbor)

            # 按优先级排序下一阶段的节点
            queue = deque(sorted(queue, key=lambda x: self._nodes[x].priority))

        # 检查是否所有节点都被处理（如果没有，说明存在循环）
        if processed != len(self._nodes):
            logger.error("拓扑排序失败：存在循环依赖")
            return []

        return stages

    def create_execution_plan(self) -> ExecutionPlan:
        """创建执行计划

        Returns:
            执行计划
        """
        # 检测循环依赖
        has_cycles, cycle_info = self.detect_cycles()

        if has_cycles:
            return ExecutionPlan(
                stages=[],
                total_plugins=len(self._nodes),
                has_cycles=True,
                cycle_info=cycle_info,
            )

        # 拓扑排序
        stages = self.topological_sort()

        return ExecutionPlan(
            stages=stages,
            total_plugins=len(self._nodes),
            has_cycles=False,
            cycle_info=None,
        )

    def check_execution_condition(
        self, plugin_name: str, results: dict[str, PluginExecutionResult]
    ) -> bool:
        """检查插件执行条件

        Args:
            plugin_name: 插件名称
            results: 已执行插件的结果

        Returns:
            是否满足执行条件
        """
        if plugin_name not in self._nodes:
            return False

        node = self._nodes[plugin_name]
        condition = node.condition

        # ALWAYS 条件
        if condition.type == ExecutionConditionType.ALWAYS:
            return True

        # 检查依赖的插件是否都已执行
        for dep in condition.depends_on:
            if dep not in results:
                logger.debug(f"插件 {plugin_name} 的依赖 {dep} 尚未执行")
                return False

        # ON_SUCCESS 条件
        if condition.type == ExecutionConditionType.ON_SUCCESS:
            return all(results[dep].success for dep in condition.depends_on)

        # ON_FAILURE 条件
        if condition.type == ExecutionConditionType.ON_FAILURE:
            return any(not results[dep].success for dep in condition.depends_on)

        # CUSTOM 条件
        if condition.type == ExecutionConditionType.CUSTOM and condition.custom_check:
            try:
                return condition.custom_check(results)
            except Exception as e:
                logger.error(f"自定义条件检查失败: {e}")
                return False

        return True

    def get_execution_order(self) -> list[str]:
        """获取执行顺序（扁平化）

        Returns:
            插件名称列表（按执行顺序）
        """
        plan = self.create_execution_plan()
        if plan.has_cycles:
            return []

        return [plugin for stage in plan.stages for plugin in stage]

    def get_plugin_dependencies(self, plugin_name: str) -> list[str]:
        """获取插件的依赖列表

        Args:
            plugin_name: 插件名称

        Returns:
            依赖的插件名称列表
        """
        if plugin_name not in self._nodes:
            return []
        return self._nodes[plugin_name].dependencies.copy()

    def get_plugin_dependents(self, plugin_name: str) -> list[str]:
        """获取依赖此插件的其他插件

        Args:
            plugin_name: 插件名称

        Returns:
            依赖此插件的插件名称列表
        """
        dependents = []
        for node in self._nodes.values():
            if plugin_name in node.dependencies:
                dependents.append(node.name)
        return dependents

    def clear(self) -> None:
        """清空所有节点"""
        self._nodes.clear()
        self._execution_results.clear()
        logger.debug("清空编排器")


# ============================================================================
# 全局单例
# ============================================================================

_orchestrator: PluginOrchestrator | None = None


def get_orchestrator() -> PluginOrchestrator:
    """获取全局编排器实例

    Returns:
        PluginOrchestrator 实例
    """
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = PluginOrchestrator()
    return _orchestrator


def reset_orchestrator() -> None:
    """重置全局编排器（主要用于测试）"""
    global _orchestrator
    _orchestrator = None
