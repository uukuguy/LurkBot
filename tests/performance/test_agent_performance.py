"""Agent 运行性能基准测试

测试 Agent 执行性能和工具调用性能
"""

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from lurkbot.agents.runtime import AgentDependencies, create_agent
from lurkbot.agents.types import AgentContext, PromptMode, ThinkLevel


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def agent_context():
    """创建测试用 Agent 上下文"""
    return AgentContext(
        user_id="test-user",
        session_id="test-session",
        channel_id="test-channel",
        channel_type="discord",
        prompt_mode=PromptMode.FULL,
        think_level=ThinkLevel.NONE,
    )


@pytest.fixture
def agent_dependencies(agent_context):
    """创建测试用 Agent 依赖"""
    return AgentDependencies(context=agent_context)


# ============================================================================
# Agent 创建性能测试
# ============================================================================


@pytest.mark.benchmark(group="agent-creation")
def test_agent_creation_performance(benchmark, agent_context):
    """测试 Agent 创建性能"""

    def create():
        return create_agent(
            context=agent_context,
            system_prompt="You are a helpful assistant.",
            tools=[],
        )

    benchmark(create)


@pytest.mark.benchmark(group="agent-creation")
def test_agent_creation_with_tools_performance(benchmark, agent_context):
    """测试带工具的 Agent 创建性能"""

    # 创建模拟工具
    def mock_tool(x: int) -> int:
        """A mock tool"""
        return x * 2

    def create():
        return create_agent(
            context=agent_context,
            system_prompt="You are a helpful assistant.",
            tools=[mock_tool],
        )

    benchmark(create)


# ============================================================================
# Agent 运行性能测试 (模拟)
# ============================================================================


@pytest.mark.benchmark(group="agent-run")
def test_simple_prompt_performance(benchmark, agent_context):
    """测试简单提示词处理性能 (模拟)"""

    # 注意: 这里我们只测试 Agent 创建和准备，不实际调用 LLM
    # 实际 LLM 调用会在集成测试中进行

    def run():
        agent = create_agent(
            context=agent_context,
            system_prompt="You are a helpful assistant.",
            tools=[],
        )
        # 模拟准备运行
        return agent

    benchmark(run)


# ============================================================================
# 工具调用性能测试
# ============================================================================


@pytest.mark.benchmark(group="tool-call")
def test_simple_tool_call_performance(benchmark):
    """测试简单工具调用性能"""

    def simple_tool(x: int) -> int:
        """A simple tool"""
        return x * 2

    benchmark(simple_tool, 42)


@pytest.mark.benchmark(group="tool-call")
def test_async_tool_call_performance(benchmark):
    """测试异步工具调用性能"""

    async def async_tool(x: int) -> int:
        """An async tool"""
        await asyncio.sleep(0)  # 模拟异步操作
        return x * 2

    benchmark(lambda: asyncio.run(async_tool(42)))


@pytest.mark.benchmark(group="tool-call")
def test_complex_tool_call_performance(benchmark):
    """测试复杂工具调用性能"""

    def complex_tool(data: dict[str, Any]) -> dict[str, Any]:
        """A complex tool"""
        result = {}
        for key, value in data.items():
            if isinstance(value, int):
                result[key] = value * 2
            elif isinstance(value, str):
                result[key] = value.upper()
            else:
                result[key] = value
        return result

    test_data = {
        "int_val": 42,
        "str_val": "hello",
        "list_val": [1, 2, 3],
        "dict_val": {"nested": "value"},
    }

    benchmark(complex_tool, test_data)


# ============================================================================
# 批量工具调用性能测试
# ============================================================================


@pytest.mark.benchmark(group="tool-batch")
def test_batch_tool_calls_performance(benchmark):
    """测试批量工具调用性能"""

    def tool(x: int) -> int:
        return x * 2

    def batch_call():
        return [tool(i) for i in range(100)]

    benchmark(batch_call)


@pytest.mark.benchmark(group="tool-batch")
def test_concurrent_tool_calls_performance(benchmark):
    """测试并发工具调用性能"""

    async def async_tool(x: int) -> int:
        await asyncio.sleep(0)
        return x * 2

    async def concurrent_call():
        tasks = [async_tool(i) for i in range(100)]
        return await asyncio.gather(*tasks)

    benchmark(lambda: asyncio.run(concurrent_call()))


# ============================================================================
# 上下文处理性能测试
# ============================================================================


@pytest.mark.benchmark(group="context")
def test_context_creation_performance(benchmark):
    """测试上下文创建性能"""

    def create():
        return AgentContext(
            user_id="test-user",
            session_id="test-session",
            channel_id="test-channel",
            channel_type="discord",
            prompt_mode=PromptMode.NORMAL,
            think_level=ThinkLevel.NONE,
        )

    benchmark(create)


@pytest.mark.benchmark(group="context")
def test_dependencies_creation_performance(benchmark, agent_context):
    """测试依赖创建性能"""

    def create():
        return AgentDependencies(
            context=agent_context,
            message_history=[],
            relevant_contexts=[],
        )

    benchmark(create)


@pytest.mark.benchmark(group="context")
def test_dependencies_with_history_performance(benchmark, agent_context):
    """测试带历史记录的依赖创建性能"""

    history = [
        {"role": "user", "content": f"Message {i}"} for i in range(100)
    ]

    def create():
        return AgentDependencies(
            context=agent_context,
            message_history=history,
            relevant_contexts=[],
        )

    benchmark(create)


# ============================================================================
# 消息历史处理性能测试
# ============================================================================


@pytest.mark.benchmark(group="history")
def test_small_history_processing(benchmark):
    """测试小历史记录处理性能 (10 条消息)"""

    history = [
        {"role": "user" if i % 2 == 0 else "assistant", "content": f"Message {i}"}
        for i in range(10)
    ]

    def process():
        return [msg for msg in history if msg["role"] == "user"]

    benchmark(process)


@pytest.mark.benchmark(group="history")
def test_medium_history_processing(benchmark):
    """测试中等历史记录处理性能 (100 条消息)"""

    history = [
        {"role": "user" if i % 2 == 0 else "assistant", "content": f"Message {i}"}
        for i in range(100)
    ]

    def process():
        return [msg for msg in history if msg["role"] == "user"]

    benchmark(process)


@pytest.mark.benchmark(group="history")
def test_large_history_processing(benchmark):
    """测试大历史记录处理性能 (1000 条消息)"""

    history = [
        {"role": "user" if i % 2 == 0 else "assistant", "content": f"Message {i}"}
        for i in range(1000)
    ]

    def process():
        return [msg for msg in history if msg["role"] == "user"]

    benchmark(process)
