"""插件编排系统测试"""

import pytest

from lurkbot.plugins.models import PluginExecutionResult
from lurkbot.plugins.orchestration import (
    ExecutionCondition,
    ExecutionConditionType,
    PluginOrchestrator,
    get_orchestrator,
    reset_orchestrator,
)


@pytest.fixture
def orchestrator():
    """创建编排器实例"""
    reset_orchestrator()
    return PluginOrchestrator()


@pytest.fixture(autouse=True)
def cleanup():
    """测试后清理"""
    yield
    reset_orchestrator()


# ============================================================================
# 基础功能测试
# ============================================================================


def test_register_plugin(orchestrator):
    """测试注册插件"""
    orchestrator.register_plugin("plugin-a")
    assert "plugin-a" in orchestrator._nodes
    assert orchestrator._nodes["plugin-a"].name == "plugin-a"
    assert orchestrator._nodes["plugin-a"].dependencies == []


def test_register_plugin_with_dependencies(orchestrator):
    """测试注册带依赖的插件"""
    orchestrator.register_plugin("plugin-a")
    orchestrator.register_plugin("plugin-b", dependencies=["plugin-a"])

    assert "plugin-b" in orchestrator._nodes
    assert orchestrator._nodes["plugin-b"].dependencies == ["plugin-a"]


def test_unregister_plugin(orchestrator):
    """测试注销插件"""
    orchestrator.register_plugin("plugin-a")
    assert orchestrator.unregister_plugin("plugin-a")
    assert "plugin-a" not in orchestrator._nodes


def test_unregister_nonexistent_plugin(orchestrator):
    """测试注销不存在的插件"""
    assert not orchestrator.unregister_plugin("nonexistent")


# ============================================================================
# 依赖图测试
# ============================================================================


def test_build_dependency_graph_simple(orchestrator):
    """测试构建简单依赖图"""
    orchestrator.register_plugin("plugin-a")
    orchestrator.register_plugin("plugin-b", dependencies=["plugin-a"])

    graph = orchestrator.build_dependency_graph()

    assert "plugin-a" in graph
    assert "plugin-b" in graph
    assert "plugin-b" in graph["plugin-a"]


def test_build_dependency_graph_complex(orchestrator):
    """测试构建复杂依赖图"""
    # A -> B, C
    # B -> D
    # C -> D
    orchestrator.register_plugin("plugin-a")
    orchestrator.register_plugin("plugin-b", dependencies=["plugin-a"])
    orchestrator.register_plugin("plugin-c", dependencies=["plugin-a"])
    orchestrator.register_plugin("plugin-d", dependencies=["plugin-b", "plugin-c"])

    graph = orchestrator.build_dependency_graph()

    assert "plugin-b" in graph["plugin-a"]
    assert "plugin-c" in graph["plugin-a"]
    assert "plugin-d" in graph["plugin-b"]
    assert "plugin-d" in graph["plugin-c"]


# ============================================================================
# 循环依赖检测测试
# ============================================================================


def test_detect_cycles_no_cycle(orchestrator):
    """测试无循环依赖"""
    orchestrator.register_plugin("plugin-a")
    orchestrator.register_plugin("plugin-b", dependencies=["plugin-a"])
    orchestrator.register_plugin("plugin-c", dependencies=["plugin-b"])

    has_cycles, cycle_info = orchestrator.detect_cycles()

    assert not has_cycles
    assert cycle_info is None


def test_detect_cycles_simple_cycle(orchestrator):
    """测试简单循环依赖"""
    orchestrator.register_plugin("plugin-a", dependencies=["plugin-b"])
    orchestrator.register_plugin("plugin-b", dependencies=["plugin-a"])

    has_cycles, cycle_info = orchestrator.detect_cycles()

    assert has_cycles
    assert cycle_info is not None
    assert len(cycle_info) > 0


def test_detect_cycles_complex_cycle(orchestrator):
    """测试复杂循环依赖"""
    # A -> B -> C -> A
    orchestrator.register_plugin("plugin-a", dependencies=["plugin-c"])
    orchestrator.register_plugin("plugin-b", dependencies=["plugin-a"])
    orchestrator.register_plugin("plugin-c", dependencies=["plugin-b"])

    has_cycles, cycle_info = orchestrator.detect_cycles()

    assert has_cycles
    assert cycle_info is not None


# ============================================================================
# 拓扑排序测试
# ============================================================================


def test_topological_sort_simple(orchestrator):
    """测试简单拓扑排序"""
    orchestrator.register_plugin("plugin-a")
    orchestrator.register_plugin("plugin-b", dependencies=["plugin-a"])

    stages = orchestrator.topological_sort()

    assert len(stages) == 2
    assert stages[0] == ["plugin-a"]
    assert stages[1] == ["plugin-b"]


def test_topological_sort_parallel(orchestrator):
    """测试并行执行"""
    # A, B 无依赖，可并行
    # C 依赖 A 和 B
    orchestrator.register_plugin("plugin-a")
    orchestrator.register_plugin("plugin-b")
    orchestrator.register_plugin("plugin-c", dependencies=["plugin-a", "plugin-b"])

    stages = orchestrator.topological_sort()

    assert len(stages) == 2
    assert set(stages[0]) == {"plugin-a", "plugin-b"}
    assert stages[1] == ["plugin-c"]


def test_topological_sort_with_priority(orchestrator):
    """测试优先级排序"""
    orchestrator.register_plugin("plugin-a", priority=200)
    orchestrator.register_plugin("plugin-b", priority=100)
    orchestrator.register_plugin("plugin-c", priority=150)

    stages = orchestrator.topological_sort()

    # 优先级低的数字先执行
    assert len(stages) == 1
    assert stages[0] == ["plugin-b", "plugin-c", "plugin-a"]


def test_topological_sort_complex(orchestrator):
    """测试复杂拓扑排序"""
    # A -> B, C
    # B -> D
    # C -> D
    # E (独立)
    orchestrator.register_plugin("plugin-a")
    orchestrator.register_plugin("plugin-b", dependencies=["plugin-a"])
    orchestrator.register_plugin("plugin-c", dependencies=["plugin-a"])
    orchestrator.register_plugin("plugin-d", dependencies=["plugin-b", "plugin-c"])
    orchestrator.register_plugin("plugin-e")

    stages = orchestrator.topological_sort()

    assert len(stages) == 3
    assert set(stages[0]) == {"plugin-a", "plugin-e"}
    assert set(stages[1]) == {"plugin-b", "plugin-c"}
    assert stages[2] == ["plugin-d"]


# ============================================================================
# 执行计划测试
# ============================================================================


def test_create_execution_plan_success(orchestrator):
    """测试创建执行计划（成功）"""
    orchestrator.register_plugin("plugin-a")
    orchestrator.register_plugin("plugin-b", dependencies=["plugin-a"])

    plan = orchestrator.create_execution_plan()

    assert not plan.has_cycles
    assert plan.total_plugins == 2
    assert len(plan.stages) == 2
    assert plan.cycle_info is None


def test_create_execution_plan_with_cycle(orchestrator):
    """测试创建执行计划（存在循环）"""
    orchestrator.register_plugin("plugin-a", dependencies=["plugin-b"])
    orchestrator.register_plugin("plugin-b", dependencies=["plugin-a"])

    plan = orchestrator.create_execution_plan()

    assert plan.has_cycles
    assert plan.total_plugins == 2
    assert len(plan.stages) == 0
    assert plan.cycle_info is not None


# ============================================================================
# 执行条件测试
# ============================================================================


def test_check_execution_condition_always(orchestrator):
    """测试 ALWAYS 条件"""
    orchestrator.register_plugin("plugin-a")

    # ALWAYS 条件总是返回 True
    assert orchestrator.check_execution_condition("plugin-a", {})


def test_check_execution_condition_on_success(orchestrator):
    """测试 ON_SUCCESS 条件"""
    condition = ExecutionCondition(
        type=ExecutionConditionType.ON_SUCCESS, depends_on=["plugin-a"]
    )
    orchestrator.register_plugin("plugin-a")
    orchestrator.register_plugin("plugin-b", condition=condition)

    # 依赖插件成功
    results = {
        "plugin-a": PluginExecutionResult(
            success=True, result="ok", execution_time=0.1
        )
    }
    assert orchestrator.check_execution_condition("plugin-b", results)

    # 依赖插件失败
    results = {
        "plugin-a": PluginExecutionResult(
            success=False, error="failed", execution_time=0.1
        )
    }
    assert not orchestrator.check_execution_condition("plugin-b", results)


def test_check_execution_condition_on_failure(orchestrator):
    """测试 ON_FAILURE 条件"""
    condition = ExecutionCondition(
        type=ExecutionConditionType.ON_FAILURE, depends_on=["plugin-a"]
    )
    orchestrator.register_plugin("plugin-a")
    orchestrator.register_plugin("plugin-b", condition=condition)

    # 依赖插件失败
    results = {
        "plugin-a": PluginExecutionResult(
            success=False, error="failed", execution_time=0.1
        )
    }
    assert orchestrator.check_execution_condition("plugin-b", results)

    # 依赖插件成功
    results = {
        "plugin-a": PluginExecutionResult(
            success=True, result="ok", execution_time=0.1
        )
    }
    assert not orchestrator.check_execution_condition("plugin-b", results)


def test_check_execution_condition_custom(orchestrator):
    """测试 CUSTOM 条件"""

    def custom_check(results):
        return results["plugin-a"].success and results["plugin-a"].result == "ok"

    condition = ExecutionCondition(
        type=ExecutionConditionType.CUSTOM,
        depends_on=["plugin-a"],
        custom_check=custom_check,
    )
    orchestrator.register_plugin("plugin-a")
    orchestrator.register_plugin("plugin-b", condition=condition)

    # 满足自定义条件
    results = {
        "plugin-a": PluginExecutionResult(
            success=True, result="ok", execution_time=0.1
        )
    }
    assert orchestrator.check_execution_condition("plugin-b", results)

    # 不满足自定义条件
    results = {
        "plugin-a": PluginExecutionResult(
            success=True, result="error", execution_time=0.1
        )
    }
    assert not orchestrator.check_execution_condition("plugin-b", results)


# ============================================================================
# 辅助方法测试
# ============================================================================


def test_get_execution_order(orchestrator):
    """测试获取执行顺序"""
    orchestrator.register_plugin("plugin-a")
    orchestrator.register_plugin("plugin-b", dependencies=["plugin-a"])
    orchestrator.register_plugin("plugin-c", dependencies=["plugin-b"])

    order = orchestrator.get_execution_order()

    assert order == ["plugin-a", "plugin-b", "plugin-c"]


def test_get_execution_order_with_cycle(orchestrator):
    """测试获取执行顺序（存在循环）"""
    orchestrator.register_plugin("plugin-a", dependencies=["plugin-b"])
    orchestrator.register_plugin("plugin-b", dependencies=["plugin-a"])

    order = orchestrator.get_execution_order()

    assert order == []


def test_get_plugin_dependencies(orchestrator):
    """测试获取插件依赖"""
    orchestrator.register_plugin("plugin-a")
    orchestrator.register_plugin("plugin-b", dependencies=["plugin-a"])

    deps = orchestrator.get_plugin_dependencies("plugin-b")

    assert deps == ["plugin-a"]


def test_get_plugin_dependents(orchestrator):
    """测试获取依赖此插件的其他插件"""
    orchestrator.register_plugin("plugin-a")
    orchestrator.register_plugin("plugin-b", dependencies=["plugin-a"])
    orchestrator.register_plugin("plugin-c", dependencies=["plugin-a"])

    dependents = orchestrator.get_plugin_dependents("plugin-a")

    assert set(dependents) == {"plugin-b", "plugin-c"}


def test_clear(orchestrator):
    """测试清空编排器"""
    orchestrator.register_plugin("plugin-a")
    orchestrator.register_plugin("plugin-b")

    orchestrator.clear()

    assert len(orchestrator._nodes) == 0


# ============================================================================
# 全局单例测试
# ============================================================================


def test_get_orchestrator_singleton():
    """测试全局单例"""
    reset_orchestrator()

    orch1 = get_orchestrator()
    orch2 = get_orchestrator()

    assert orch1 is orch2


def test_reset_orchestrator():
    """测试重置全局单例"""
    orch1 = get_orchestrator()
    orch1.register_plugin("plugin-a")

    reset_orchestrator()

    orch2 = get_orchestrator()
    assert orch1 is not orch2
    assert len(orch2._nodes) == 0
