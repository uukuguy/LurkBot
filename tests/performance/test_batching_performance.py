"""
批处理性能测试

对比启用和禁用批处理的性能差异
"""

import asyncio
import pytest
from lurkbot.gateway.batching import MessageBatcher


class MockWebSocket:
    """模拟 WebSocket"""

    def __init__(self):
        self.sent_messages = []

    async def send_text(self, text: str):
        """模拟发送文本"""
        self.sent_messages.append(text)


@pytest.mark.benchmark(group="batching-send")
def test_send_without_batching(benchmark):
    """测试不使用批处理的发送性能"""
    ws = MockWebSocket()

    def send_messages():
        import json

        async def _send():
            for i in range(100):
                await ws.send_text(json.dumps({"id": i, "data": "test"}))

        asyncio.run(_send())

    benchmark(send_messages)


@pytest.mark.benchmark(group="batching-send")
def test_send_with_batching(benchmark):
    """测试使用批处理的发送性能"""
    ws = MockWebSocket()

    def send_messages():
        async def _send():
            batcher = MessageBatcher(
                send_func=ws.send_text,
                batch_size=100,
                batch_delay=0.01,
                auto_flush=False,
            )

            for i in range(100):
                await batcher.add({"id": i, "data": "test"})

            await batcher.flush()

        asyncio.run(_send())

    benchmark(send_messages)


@pytest.mark.benchmark(group="batching-throughput")
def test_throughput_without_batching(benchmark):
    """测试不使用批处理的吞吐量"""
    ws = MockWebSocket()

    def send_messages():
        import json

        async def _send():
            for i in range(1000):
                await ws.send_text(json.dumps({"id": i}))

        asyncio.run(_send())

    benchmark(send_messages)


@pytest.mark.benchmark(group="batching-throughput")
def test_throughput_with_batching(benchmark):
    """测试使用批处理的吞吐量"""
    ws = MockWebSocket()

    def send_messages():
        async def _send():
            batcher = MessageBatcher(
                send_func=ws.send_text,
                batch_size=100,
                batch_delay=0.01,
                auto_flush=False,
            )

            for i in range(1000):
                await batcher.add({"id": i})

            await batcher.flush()

        asyncio.run(_send())

    benchmark(send_messages)


@pytest.mark.benchmark(group="batching-concurrent")
def test_concurrent_without_batching(benchmark):
    """测试不使用批处理的并发性能"""
    ws = MockWebSocket()

    def send_messages():
        import json

        async def _send():
            tasks = []
            for i in range(100):
                tasks.append(ws.send_text(json.dumps({"id": i})))

            await asyncio.gather(*tasks)

        asyncio.run(_send())

    benchmark(send_messages)


@pytest.mark.benchmark(group="batching-concurrent")
def test_concurrent_with_batching(benchmark):
    """测试使用批处理的并发性能"""
    ws = MockWebSocket()

    def send_messages():
        async def _send():
            batcher = MessageBatcher(
                send_func=ws.send_text,
                batch_size=100,
                batch_delay=0.01,
                auto_flush=False,
            )

            tasks = []
            for i in range(100):
                tasks.append(batcher.add({"id": i}))

            await asyncio.gather(*tasks)
            await batcher.flush()

        asyncio.run(_send())

    benchmark(send_messages)
