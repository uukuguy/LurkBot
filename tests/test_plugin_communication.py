"""插件通信测试"""

import asyncio
from datetime import datetime

import pytest

from lurkbot.plugins.communication import (
    Message,
    MessageBus,
    PluginCommunication,
    SharedState,
    get_communication,
)


# ============================================================================
# Message 测试
# ============================================================================


def test_message_creation():
    """测试消息创建"""
    msg = Message(
        id="msg-1",
        sender="plugin-a",
        topic="test-topic",
        data={"key": "value"},
    )
    assert msg.id == "msg-1"
    assert msg.sender == "plugin-a"
    assert msg.topic == "test-topic"
    assert msg.data == {"key": "value"}
    assert isinstance(msg.timestamp, datetime)


# ============================================================================
# MessageBus 测试
# ============================================================================


@pytest.mark.asyncio
async def test_message_bus_subscribe():
    """测试订阅"""
    bus = MessageBus()
    received_messages = []

    async def callback(message: Message):
        received_messages.append(message)

    bus.subscribe("test-topic", callback)
    assert "test-topic" in bus._subscribers
    assert callback in bus._subscribers["test-topic"]


@pytest.mark.asyncio
async def test_message_bus_unsubscribe():
    """测试取消订阅"""
    bus = MessageBus()

    async def callback(message: Message):
        pass

    bus.subscribe("test-topic", callback)
    bus.unsubscribe("test-topic", callback)
    assert callback not in bus._subscribers["test-topic"]


@pytest.mark.asyncio
async def test_message_bus_publish():
    """测试发布消息"""
    bus = MessageBus()
    received_messages = []

    async def callback(message: Message):
        received_messages.append(message)

    bus.subscribe("test-topic", callback)
    bus.start()

    try:
        msg = Message(
            id="msg-1",
            sender="plugin-a",
            topic="test-topic",
            data={"key": "value"},
        )
        await bus.publish(msg)

        # 等待消息处理
        await asyncio.sleep(0.1)

        assert len(received_messages) == 1
        assert received_messages[0].id == "msg-1"
    finally:
        bus.stop()


@pytest.mark.asyncio
async def test_message_bus_multiple_subscribers():
    """测试多个订阅者"""
    bus = MessageBus()
    received_a = []
    received_b = []

    async def callback_a(message: Message):
        received_a.append(message)

    async def callback_b(message: Message):
        received_b.append(message)

    bus.subscribe("test-topic", callback_a)
    bus.subscribe("test-topic", callback_b)
    bus.start()

    try:
        msg = Message(
            id="msg-1",
            sender="plugin-a",
            topic="test-topic",
            data={"key": "value"},
        )
        await bus.publish(msg)

        # 等待消息处理
        await asyncio.sleep(0.1)

        assert len(received_a) == 1
        assert len(received_b) == 1
    finally:
        bus.stop()


# ============================================================================
# SharedState 测试
# ============================================================================


@pytest.mark.asyncio
async def test_shared_state_set_get():
    """测试设置和获取状态"""
    state = SharedState()

    await state.set("plugin-a", "key1", "value1")
    value = await state.get("plugin-a", "key1")

    assert value == "value1"


@pytest.mark.asyncio
async def test_shared_state_get_default():
    """测试获取不存在的状态"""
    state = SharedState()

    value = await state.get("plugin-a", "nonexistent", default="default-value")
    assert value == "default-value"


@pytest.mark.asyncio
async def test_shared_state_delete():
    """测试删除状态"""
    state = SharedState()

    await state.set("plugin-a", "key1", "value1")
    await state.delete("plugin-a", "key1")
    value = await state.get("plugin-a", "key1")

    assert value is None


@pytest.mark.asyncio
async def test_shared_state_get_all():
    """测试获取所有状态"""
    state = SharedState()

    await state.set("plugin-a", "key1", "value1")
    await state.set("plugin-a", "key2", "value2")
    all_state = await state.get_all("plugin-a")

    assert all_state == {"key1": "value1", "key2": "value2"}


@pytest.mark.asyncio
async def test_shared_state_clear():
    """测试清空命名空间"""
    state = SharedState()

    await state.set("plugin-a", "key1", "value1")
    await state.set("plugin-a", "key2", "value2")
    await state.clear("plugin-a")
    all_state = await state.get_all("plugin-a")

    assert all_state == {}


@pytest.mark.asyncio
async def test_shared_state_isolation():
    """测试命名空间隔离"""
    state = SharedState()

    await state.set("plugin-a", "key1", "value-a")
    await state.set("plugin-b", "key1", "value-b")

    value_a = await state.get("plugin-a", "key1")
    value_b = await state.get("plugin-b", "key1")

    assert value_a == "value-a"
    assert value_b == "value-b"


# ============================================================================
# PluginCommunication 测试
# ============================================================================


def test_plugin_communication_init():
    """测试通信管理器初始化"""
    comm = PluginCommunication()
    assert comm.message_bus is not None
    assert comm.shared_state is not None


@pytest.mark.asyncio
async def test_plugin_communication_integration():
    """测试通信管理器集成"""
    comm = PluginCommunication()
    received_messages = []

    async def callback(message: Message):
        received_messages.append(message)

    comm.message_bus.subscribe("test-topic", callback)
    comm.start()

    try:
        # 发布消息
        msg = Message(
            id="msg-1",
            sender="plugin-a",
            topic="test-topic",
            data={"key": "value"},
        )
        await comm.message_bus.publish(msg)

        # 设置共享状态
        await comm.shared_state.set("plugin-a", "key1", "value1")

        # 等待消息处理
        await asyncio.sleep(0.1)

        # 验证消息
        assert len(received_messages) == 1

        # 验证状态
        value = await comm.shared_state.get("plugin-a", "key1")
        assert value == "value1"
    finally:
        comm.stop()


# ============================================================================
# 全局单例测试
# ============================================================================


def test_get_communication_singleton():
    """测试全局单例"""
    # 清除全局单例
    import lurkbot.plugins.communication as comm_module

    comm_module._communication = None

    # 获取单例
    comm1 = get_communication()
    assert comm1 is not None

    # 第二次调用返回同一个实例
    comm2 = get_communication()
    assert comm1 is comm2

    # 清理
    comm_module._communication = None
