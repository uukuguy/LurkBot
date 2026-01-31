"""消息处理性能基准测试

测试 Gateway 消息发送/接收性能
"""

import asyncio
from typing import Any

import pytest
from fastapi import WebSocket
from unittest.mock import AsyncMock, MagicMock

from lurkbot.gateway.server import GatewayConnection, GatewayServer
from lurkbot.utils import json_utils as json


class MockWebSocket:
    """模拟 WebSocket 连接"""

    def __init__(self):
        self.sent_messages = []
        self.received_messages = []
        self.closed = False

    async def accept(self):
        """接受连接"""
        pass

    async def send_text(self, data: str):
        """发送文本消息"""
        self.sent_messages.append(data)

    async def receive_text(self) -> str:
        """接收文本消息"""
        if not self.received_messages:
            raise Exception("No messages to receive")
        return self.received_messages.pop(0)

    async def close(self):
        """关闭连接"""
        self.closed = True

    def add_message(self, message: dict):
        """添加待接收的消息"""
        self.received_messages.append(json.dumps(message))


@pytest.fixture
def mock_websocket():
    """创建模拟 WebSocket"""
    return MockWebSocket()


@pytest.fixture
def gateway_connection(mock_websocket):
    """创建 Gateway 连接"""
    return GatewayConnection(mock_websocket, "test-conn-id")


# ============================================================================
# 消息发送性能测试
# ============================================================================


@pytest.mark.benchmark(group="message-send")
def test_send_json_performance(benchmark, gateway_connection):
    """测试 JSON 消息发送性能"""

    async def send_message():
        await gateway_connection.send_json({"type": "test", "data": "hello"})

    benchmark(lambda: asyncio.run(send_message()))


@pytest.mark.benchmark(group="message-send")
def test_send_large_json_performance(benchmark, gateway_connection):
    """测试大型 JSON 消息发送性能"""

    large_data = {"type": "test", "data": "x" * 10000}  # 10KB 数据

    async def send_message():
        await gateway_connection.send_json(large_data)

    benchmark(lambda: asyncio.run(send_message()))


@pytest.mark.benchmark(group="message-send")
def test_send_batch_messages_performance(benchmark, gateway_connection):
    """测试批量消息发送性能"""

    messages = [{"type": "test", "data": f"message-{i}"} for i in range(100)]

    async def send_batch():
        for msg in messages:
            await gateway_connection.send_json(msg)

    benchmark(lambda: asyncio.run(send_batch()))


# ============================================================================
# 消息接收性能测试
# ============================================================================


@pytest.mark.benchmark(group="message-receive")
def test_receive_json_performance(benchmark, gateway_connection, mock_websocket):
    """测试 JSON 消息接收性能"""

    async def receive_message():
        # 每次迭代都添加一条消息
        mock_websocket.add_message({"type": "test", "data": "hello"})
        return await gateway_connection.receive_json()

    benchmark(lambda: asyncio.run(receive_message()))


@pytest.mark.benchmark(group="message-receive")
def test_receive_large_json_performance(benchmark, gateway_connection, mock_websocket):
    """测试大型 JSON 消息接收性能"""

    large_data = {"type": "test", "data": "x" * 10000}  # 10KB 数据

    async def receive_message():
        # 每次迭代都添加一条消息
        mock_websocket.add_message(large_data)
        return await gateway_connection.receive_json()

    benchmark(lambda: asyncio.run(receive_message()))


# ============================================================================
# JSON 序列化/反序列化性能测试
# ============================================================================


@pytest.mark.benchmark(group="json-ops")
def test_json_dumps_performance(benchmark):
    """测试 JSON 序列化性能"""

    data = {"type": "test", "data": "hello", "nested": {"key": "value"}}

    benchmark(json.dumps, data)


@pytest.mark.benchmark(group="json-ops")
def test_json_loads_performance(benchmark):
    """测试 JSON 反序列化性能"""

    json_str = '{"type": "test", "data": "hello", "nested": {"key": "value"}}'

    benchmark(json.loads, json_str)


@pytest.mark.benchmark(group="json-ops")
def test_large_json_dumps_performance(benchmark):
    """测试大型 JSON 序列化性能"""

    data = {
        "type": "test",
        "data": "x" * 10000,
        "array": [{"id": i, "value": f"item-{i}"} for i in range(100)],
    }

    benchmark(json.dumps, data)


@pytest.mark.benchmark(group="json-ops")
def test_large_json_loads_performance(benchmark):
    """测试大型 JSON 反序列化性能"""

    data = {
        "type": "test",
        "data": "x" * 10000,
        "array": [{"id": i, "value": f"item-{i}"} for i in range(100)],
    }
    json_str = json.dumps(data)

    benchmark(json.loads, json_str)


# ============================================================================
# 并发消息处理性能测试
# ============================================================================


@pytest.mark.benchmark(group="concurrent")
def test_concurrent_send_performance(benchmark):
    """测试并发消息发送性能"""

    async def concurrent_send():
        connections = [
            GatewayConnection(MockWebSocket(), f"conn-{i}") for i in range(10)
        ]

        tasks = [
            conn.send_json({"type": "test", "data": f"message-{i}"})
            for i, conn in enumerate(connections)
        ]

        await asyncio.gather(*tasks)

    benchmark(lambda: asyncio.run(concurrent_send()))


@pytest.mark.benchmark(group="concurrent")
def test_concurrent_receive_performance(benchmark):
    """测试并发消息接收性能"""

    async def concurrent_receive():
        connections = []
        for i in range(10):
            ws = MockWebSocket()
            ws.add_message({"type": "test", "data": f"message-{i}"})
            connections.append(GatewayConnection(ws, f"conn-{i}"))

        tasks = [conn.receive_json() for conn in connections]

        await asyncio.gather(*tasks)

    benchmark(lambda: asyncio.run(concurrent_receive()))


# ============================================================================
# 消息吞吐量测试
# ============================================================================


@pytest.mark.benchmark(group="throughput")
def test_message_throughput_small(benchmark):
    """测试小消息吞吐量 (100 条消息)"""

    async def send_messages():
        conn = GatewayConnection(MockWebSocket(), "test-conn")
        for i in range(100):
            await conn.send_json({"type": "test", "id": i})

    benchmark(lambda: asyncio.run(send_messages()))


@pytest.mark.benchmark(group="throughput")
def test_message_throughput_medium(benchmark):
    """测试中等消息吞吐量 (1000 条消息)"""

    async def send_messages():
        conn = GatewayConnection(MockWebSocket(), "test-conn")
        for i in range(1000):
            await conn.send_json({"type": "test", "id": i})

    benchmark(lambda: asyncio.run(send_messages()))


@pytest.mark.benchmark(group="throughput")
def test_message_throughput_large(benchmark):
    """测试大消息吞吐量 (10000 条消息)"""

    async def send_messages():
        conn = GatewayConnection(MockWebSocket(), "test-conn")
        for i in range(10000):
            await conn.send_json({"type": "test", "id": i})

    benchmark(lambda: asyncio.run(send_messages()))
