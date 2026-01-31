"""插件间通信

支持插件之间的数据共享和通信，包括消息总线、共享状态管理和事件订阅机制。
"""

import asyncio
from collections import defaultdict
from datetime import datetime
from typing import Any, Callable

from loguru import logger
from pydantic import BaseModel, Field


# ============================================================================
# 数据模型
# ============================================================================


class Message(BaseModel):
    """消息"""

    id: str = Field(..., description="消息 ID")
    sender: str = Field(..., description="发送者插件名称")
    topic: str = Field(..., description="主题")
    data: dict[str, Any] = Field(default_factory=dict, description="消息数据")
    timestamp: datetime = Field(default_factory=datetime.now, description="时间戳")


# ============================================================================
# 消息总线
# ============================================================================


class MessageBus:
    """消息总线

    实现发布-订阅模式的消息传递机制。
    """

    def __init__(self):
        """初始化消息总线"""
        self._subscribers: dict[str, list[Callable]] = defaultdict(list)
        self._message_queue: asyncio.Queue = asyncio.Queue()
        self._running = False
        self._process_task: asyncio.Task | None = None

    def subscribe(self, topic: str, callback: Callable) -> None:
        """订阅主题

        Args:
            topic: 主题名称
            callback: 回调函数（接收 Message 对象）
        """
        self._subscribers[topic].append(callback)
        logger.debug(f"订阅主题: {topic}")

    def unsubscribe(self, topic: str, callback: Callable) -> None:
        """取消订阅

        Args:
            topic: 主题名称
            callback: 回调函数
        """
        if topic in self._subscribers:
            self._subscribers[topic].remove(callback)
            logger.debug(f"取消订阅主题: {topic}")

    async def publish(self, message: Message) -> None:
        """发布消息

        Args:
            message: 消息对象
        """
        logger.debug(f"发布消息: {message.topic} from {message.sender}")
        await self._message_queue.put(message)

    def start(self) -> None:
        """启动消息总线"""
        if self._running:
            return

        self._running = True
        try:
            loop = asyncio.get_running_loop()
            self._process_task = loop.create_task(self._process_messages())
            logger.info("消息总线已启动")
        except RuntimeError:
            logger.warning("没有运行中的事件循环，消息总线将不会启动")

    def stop(self) -> None:
        """停止消息总线"""
        if not self._running:
            return

        self._running = False
        if self._process_task:
            self._process_task.cancel()
            self._process_task = None
        logger.info("消息总线已停止")

    async def _process_messages(self) -> None:
        """处理消息队列"""
        try:
            while self._running:
                try:
                    message = await asyncio.wait_for(
                        self._message_queue.get(), timeout=1.0
                    )
                    await self._dispatch_message(message)
                except asyncio.TimeoutError:
                    continue
        except asyncio.CancelledError:
            logger.debug("消息处理循环已取消")

    async def _dispatch_message(self, message: Message) -> None:
        """分发消息给订阅者

        Args:
            message: 消息对象
        """
        subscribers = self._subscribers.get(message.topic, [])
        if not subscribers:
            logger.debug(f"主题 {message.topic} 没有订阅者")
            return

        # 并发调用所有订阅者
        tasks = []
        for callback in subscribers:
            if asyncio.iscoroutinefunction(callback):
                tasks.append(callback(message))
            else:
                # 同步回调在线程池中执行
                loop = asyncio.get_event_loop()
                tasks.append(loop.run_in_executor(None, callback, message))

        # 等待所有回调完成
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 记录错误
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"订阅者回调失败: {result}")


# ============================================================================
# 共享状态管理
# ============================================================================


class SharedState:
    """共享状态管理

    提供插件之间的状态共享机制。
    """

    def __init__(self):
        """初始化共享状态"""
        self._state: dict[str, dict[str, Any]] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    async def set(self, namespace: str, key: str, value: Any) -> None:
        """设置状态

        Args:
            namespace: 命名空间（通常是插件名称）
            key: 键
            value: 值
        """
        lock = self._get_lock(namespace)
        async with lock:
            if namespace not in self._state:
                self._state[namespace] = {}
            self._state[namespace][key] = value
            logger.debug(f"设置状态: {namespace}.{key}")

    async def get(self, namespace: str, key: str, default: Any = None) -> Any:
        """获取状态

        Args:
            namespace: 命名空间
            key: 键
            default: 默认值

        Returns:
            状态值
        """
        lock = self._get_lock(namespace)
        async with lock:
            return self._state.get(namespace, {}).get(key, default)

    async def delete(self, namespace: str, key: str) -> None:
        """删除状态

        Args:
            namespace: 命名空间
            key: 键
        """
        lock = self._get_lock(namespace)
        async with lock:
            if namespace in self._state and key in self._state[namespace]:
                del self._state[namespace][key]
                logger.debug(f"删除状态: {namespace}.{key}")

    async def get_all(self, namespace: str) -> dict[str, Any]:
        """获取命名空间下的所有状态

        Args:
            namespace: 命名空间

        Returns:
            状态字典
        """
        lock = self._get_lock(namespace)
        async with lock:
            return self._state.get(namespace, {}).copy()

    async def clear(self, namespace: str) -> None:
        """清空命名空间

        Args:
            namespace: 命名空间
        """
        lock = self._get_lock(namespace)
        async with lock:
            if namespace in self._state:
                self._state[namespace].clear()
                logger.debug(f"清空命名空间: {namespace}")

    def _get_lock(self, namespace: str) -> asyncio.Lock:
        """获取命名空间的锁

        Args:
            namespace: 命名空间

        Returns:
            锁对象
        """
        if namespace not in self._locks:
            self._locks[namespace] = asyncio.Lock()
        return self._locks[namespace]


# ============================================================================
# 插件通信管理器
# ============================================================================


class PluginCommunication:
    """插件通信管理器

    整合消息总线和共享状态管理。
    """

    def __init__(self):
        """初始化通信管理器"""
        self.message_bus = MessageBus()
        self.shared_state = SharedState()

    def start(self) -> None:
        """启动通信管理器"""
        self.message_bus.start()
        logger.info("插件通信管理器已启动")

    def stop(self) -> None:
        """停止通信管理器"""
        self.message_bus.stop()
        logger.info("插件通信管理器已停止")


# ============================================================================
# 全局单例
# ============================================================================

_communication: PluginCommunication | None = None


def get_communication() -> PluginCommunication:
    """获取插件通信管理器单例

    Returns:
        插件通信管理器实例
    """
    global _communication
    if _communication is None:
        _communication = PluginCommunication()
    return _communication
