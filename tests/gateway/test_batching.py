"""
测试批处理模块
"""

import asyncio
import pytest
from lurkbot.gateway.batching import MessageBatcher


@pytest.mark.asyncio
async def test_batch_size_trigger():
    """测试批量大小触发"""
    sent_messages = []

    async def mock_send(text: str):
        sent_messages.append(text)

    batcher = MessageBatcher(
        send_func=mock_send,
        batch_size=3,
        batch_delay=1.0,  # 长延迟，确保不会被延迟触发
        auto_flush=False,  # 禁用自动刷新
    )

    # 添加 3 条消息，应该立即刷新
    await batcher.add({"id": 1})
    await batcher.add({"id": 2})
    await batcher.add({"id": 3})

    # 等待一小段时间确保消息已发送
    await asyncio.sleep(0.01)

    assert len(sent_messages) == 3


@pytest.mark.asyncio
async def test_delay_trigger():
    """测试延迟触发"""
    sent_messages = []

    async def mock_send(text: str):
        sent_messages.append(text)

    batcher = MessageBatcher(
        send_func=mock_send,
        batch_size=100,  # 大批量，确保不会被批量大小触发
        batch_delay=0.05,  # 50ms 延迟
        auto_flush=True,
    )

    # 添加 2 条消息
    await batcher.add({"id": 1})
    await batcher.add({"id": 2})

    # 立即检查，应该还没发送
    assert len(sent_messages) == 0

    # 等待延迟时间
    await asyncio.sleep(0.1)

    # 现在应该已经发送
    assert len(sent_messages) == 2


@pytest.mark.asyncio
async def test_manual_flush():
    """测试手动刷新"""
    sent_messages = []

    async def mock_send(text: str):
        sent_messages.append(text)

    batcher = MessageBatcher(
        send_func=mock_send,
        batch_size=100,
        batch_delay=1.0,
        auto_flush=False,
    )

    # 添加消息
    await batcher.add({"id": 1})
    await batcher.add({"id": 2})

    # 手动刷新
    await batcher.flush()

    assert len(sent_messages) == 2


@pytest.mark.asyncio
async def test_close():
    """测试关闭时刷新"""
    sent_messages = []

    async def mock_send(text: str):
        sent_messages.append(text)

    batcher = MessageBatcher(
        send_func=mock_send,
        batch_size=100,
        batch_delay=1.0,
        auto_flush=False,
    )

    # 添加消息
    await batcher.add({"id": 1})
    await batcher.add({"id": 2})

    # 关闭，应该刷新剩余消息
    await batcher.close()

    assert len(sent_messages) == 2


@pytest.mark.asyncio
async def test_empty_flush():
    """测试空缓冲区刷新"""
    sent_messages = []

    async def mock_send(text: str):
        sent_messages.append(text)

    batcher = MessageBatcher(
        send_func=mock_send,
        batch_size=100,
        batch_delay=1.0,
    )

    # 刷新空缓冲区
    await batcher.flush()

    assert len(sent_messages) == 0


@pytest.mark.asyncio
async def test_concurrent_add():
    """测试并发添加"""
    sent_messages = []

    async def mock_send(text: str):
        sent_messages.append(text)
        await asyncio.sleep(0.001)  # 模拟发送延迟

    batcher = MessageBatcher(
        send_func=mock_send,
        batch_size=10,
        batch_delay=0.1,
    )

    # 并发添加 20 条消息
    tasks = [batcher.add({"id": i}) for i in range(20)]
    await asyncio.gather(*tasks)

    # 等待所有消息发送
    await asyncio.sleep(0.2)

    assert len(sent_messages) == 20
