"""异步优化工具模块

提供异步 I/O 优化和并发控制功能，用于提升系统性能。

主要功能：
- AsyncIOOptimizer: 异步 I/O 优化器
- ConcurrencyController: 并发控制器
- 异步任务批处理
- 异步资源池管理

性能目标：
- 异步 I/O 操作性能提升 20-30%
- 并发任务处理能力提升 30-40%
- 资源利用率提升 15-20%
"""

import asyncio
import time
from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any, TypeVar

from loguru import logger

T = TypeVar("T")


@dataclass
class AsyncIOConfig:
    """异步 I/O 配置"""

    # 并发控制
    max_concurrent_tasks: int = 100  # 最大并发任务数
    semaphore_timeout: float = 30.0  # 信号量超时时间（秒）

    # 批处理配置
    batch_size: int = 50  # 批处理大小
    batch_timeout: float = 0.1  # 批处理超时时间（秒）

    # 重试配置
    max_retries: int = 3  # 最大重试次数
    retry_delay: float = 1.0  # 重试延迟（秒）
    retry_backoff: float = 2.0  # 重试退避因子

    # 超时配置
    default_timeout: float = 30.0  # 默认超时时间（秒）
    gather_timeout: float | None = None  # gather 超时时间（None 表示无限制）


@dataclass
class AsyncIOStats:
    """异步 I/O 统计信息"""

    # 任务统计
    total_tasks: int = 0  # 总任务数
    completed_tasks: int = 0  # 完成任务数
    failed_tasks: int = 0  # 失败任务数
    cancelled_tasks: int = 0  # 取消任务数

    # 性能统计
    total_time: float = 0.0  # 总耗时（秒）
    avg_task_time: float = 0.0  # 平均任务耗时（秒）
    max_task_time: float = 0.0  # 最大任务耗时（秒）
    min_task_time: float = float("inf")  # 最小任务耗时（秒）

    # 并发统计
    max_concurrent: int = 0  # 最大并发数
    current_concurrent: int = 0  # 当前并发数

    # 重试统计
    total_retries: int = 0  # 总重试次数
    retry_success: int = 0  # 重试成功次数

    def update_task_time(self, task_time: float) -> None:
        """更新任务耗时统计"""
        self.total_time += task_time
        self.completed_tasks += 1
        self.avg_task_time = self.total_time / self.completed_tasks
        self.max_task_time = max(self.max_task_time, task_time)
        self.min_task_time = min(self.min_task_time, task_time)

    def update_concurrent(self, current: int) -> None:
        """更新并发统计"""
        self.current_concurrent = current
        self.max_concurrent = max(self.max_concurrent, current)


class AsyncIOOptimizer:
    """异步 I/O 优化器

    提供异步任务的批处理、并发控制、重试机制等功能。

    示例：
        >>> optimizer = AsyncIOOptimizer()
        >>> results = await optimizer.gather_with_limit([task1(), task2(), task3()])
        >>> async with optimizer.semaphore():
        ...     result = await some_async_operation()
    """

    def __init__(self, config: AsyncIOConfig | None = None):
        """初始化异步 I/O 优化器

        Args:
            config: 异步 I/O 配置，默认使用 AsyncIOConfig()
        """
        self.config = config or AsyncIOConfig()
        self.stats = AsyncIOStats()
        self._semaphore = asyncio.Semaphore(self.config.max_concurrent_tasks)
        self._lock = asyncio.Lock()

    @asynccontextmanager
    async def semaphore(self):
        """获取信号量上下文管理器

        用于限制并发任务数量。

        示例：
            >>> async with optimizer.semaphore():
            ...     result = await some_async_operation()
        """
        async with self._lock:
            self.stats.update_concurrent(self.stats.current_concurrent + 1)

        try:
            async with asyncio.timeout(self.config.semaphore_timeout):
                async with self._semaphore:
                    yield
        finally:
            async with self._lock:
                self.stats.update_concurrent(self.stats.current_concurrent - 1)

    async def gather_with_limit(
        self,
        tasks: list[Awaitable[T]],
        return_exceptions: bool = False,
    ) -> list[T | BaseException]:
        """并发执行任务列表，限制并发数量

        Args:
            tasks: 任务列表
            return_exceptions: 是否返回异常（默认 False）

        Returns:
            任务结果列表

        示例:
            >>> results = await optimizer.gather_with_limit([task1(), task2()])
        """
        if not tasks:
            return []

        async def _run_with_semaphore(task: Awaitable[T]) -> T | BaseException:
            """在信号量保护下运行任务"""
            start_time = time.perf_counter()
            try:
                async with self.semaphore():
                    result = await task
                    task_time = time.perf_counter() - start_time
                    async with self._lock:
                        self.stats.update_task_time(task_time)
                        self.stats.total_tasks += 1
                    return result
            except Exception as e:
                async with self._lock:
                    self.stats.failed_tasks += 1
                    self.stats.total_tasks += 1
                if return_exceptions:
                    return e
                raise

        # 使用 gather 并发执行所有任务
        try:
            if self.config.gather_timeout:
                async with asyncio.timeout(self.config.gather_timeout):
                    return await asyncio.gather(
                        *[_run_with_semaphore(task) for task in tasks],
                        return_exceptions=return_exceptions,
                    )
            else:
                return await asyncio.gather(
                    *[_run_with_semaphore(task) for task in tasks],
                    return_exceptions=return_exceptions,
                )
        except asyncio.TimeoutError:
            logger.warning(f"gather_with_limit timeout after {self.config.gather_timeout}s")
            raise

    async def batch_process(
        self,
        items: list[T],
        processor: Callable[[list[T]], Awaitable[list[Any]]],
    ) -> list[Any]:
        """批处理任务

        将大量任务分批处理，提升性能。

        Args:
            items: 待处理项列表
            processor: 批处理函数，接收一批项，返回处理结果

        Returns:
            所有批次的处理结果

        示例:
            >>> async def process_batch(batch):
            ...     return [item * 2 for item in batch]
            >>> results = await optimizer.batch_process([1, 2, 3, 4, 5], process_batch)
        """
        if not items:
            return []

        results = []
        batch_size = self.config.batch_size

        # 分批处理
        for i in range(0, len(items), batch_size):
            batch = items[i : i + batch_size]
            try:
                batch_results = await processor(batch)
                results.extend(batch_results)
            except Exception as e:
                logger.error(f"Batch processing failed: {e}")
                async with self._lock:
                    self.stats.failed_tasks += len(batch)
                raise

        return results

    async def retry_with_backoff(
        self,
        coro: Callable[[], Awaitable[T]],
        max_retries: int | None = None,
        retry_delay: float | None = None,
        retry_backoff: float | None = None,
    ) -> T:
        """带退避的重试机制

        Args:
            coro: 协程函数
            max_retries: 最大重试次数（默认使用配置值）
            retry_delay: 重试延迟（默认使用配置值）
            retry_backoff: 重试退避因子（默认使用配置值）

        Returns:
            协程执行结果

        Raises:
            最后一次重试的异常

        示例:
            >>> result = await optimizer.retry_with_backoff(lambda: some_async_operation())
        """
        max_retries = max_retries or self.config.max_retries
        retry_delay = retry_delay or self.config.retry_delay
        retry_backoff = retry_backoff or self.config.retry_backoff

        last_exception = None
        current_delay = retry_delay

        for attempt in range(max_retries + 1):
            try:
                result = await coro()
                if attempt > 0:
                    async with self._lock:
                        self.stats.retry_success += 1
                return result
            except Exception as e:
                last_exception = e

                if attempt < max_retries:
                    # 准备重试，增加重试计数
                    async with self._lock:
                        self.stats.total_retries += 1
                    logger.warning(
                        f"Retry attempt {attempt + 1}/{max_retries} after {current_delay}s: {e}"
                    )
                    await asyncio.sleep(current_delay)
                    current_delay *= retry_backoff
                else:
                    logger.error(f"All {max_retries} retries failed: {e}")

        raise last_exception  # type: ignore

    def get_stats(self) -> AsyncIOStats:
        """获取统计信息

        Returns:
            异步 I/O 统计信息
        """
        return self.stats

    def reset_stats(self) -> None:
        """重置统计信息"""
        self.stats = AsyncIOStats()


class ConcurrencyController:
    """并发控制器

    提供更细粒度的并发控制功能。

    示例:
        >>> controller = ConcurrencyController(max_workers=10)
        >>> async with controller.acquire():
        ...     result = await some_async_operation()
    """

    def __init__(
        self,
        max_workers: int = 100,
        queue_size: int = 1000,
    ):
        """初始化并发控制器

        Args:
            max_workers: 最大工作线程数
            queue_size: 任务队列大小
        """
        self.max_workers = max_workers
        self.queue_size = queue_size
        self._semaphore = asyncio.Semaphore(max_workers)
        self._queue: asyncio.Queue[Callable[[], Awaitable[Any]]] = asyncio.Queue(
            maxsize=queue_size
        )
        self._workers: list[asyncio.Task] = []
        self._running = False
        self._stats = AsyncIOStats()

    @asynccontextmanager
    async def acquire(self):
        """获取工作槽位

        示例:
            >>> async with controller.acquire():
            ...     result = await some_async_operation()
        """
        async with self._semaphore:
            self._stats.update_concurrent(self._stats.current_concurrent + 1)
            try:
                yield
            finally:
                self._stats.update_concurrent(self._stats.current_concurrent - 1)

    async def submit(self, coro: Callable[[], Awaitable[T]]) -> T:
        """提交任务到队列

        Args:
            coro: 协程函数

        Returns:
            任务结果

        示例:
            >>> result = await controller.submit(lambda: some_async_operation())
        """
        if not self._running:
            raise RuntimeError("ConcurrencyController is not running")

        future: asyncio.Future[T] = asyncio.Future()

        async def _wrapper():
            try:
                result = await coro()
                future.set_result(result)
            except Exception as e:
                future.set_exception(e)

        await self._queue.put(_wrapper)
        return await future

    async def start(self) -> None:
        """启动并发控制器"""
        if self._running:
            return

        self._running = True
        self._workers = [
            asyncio.create_task(self._worker(i)) for i in range(self.max_workers)
        ]
        logger.info(f"ConcurrencyController started with {self.max_workers} workers")

    async def stop(self) -> None:
        """停止并发控制器"""
        if not self._running:
            return

        self._running = False

        # 等待队列清空
        await self._queue.join()

        # 取消所有工作线程
        for worker in self._workers:
            worker.cancel()

        # 等待所有工作线程结束
        await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers.clear()

        logger.info("ConcurrencyController stopped")

    async def _worker(self, worker_id: int) -> None:
        """工作线程

        Args:
            worker_id: 工作线程 ID
        """
        logger.debug(f"Worker {worker_id} started")

        while self._running:
            try:
                # 获取任务
                coro = await asyncio.wait_for(self._queue.get(), timeout=1.0)

                # 执行任务
                start_time = time.perf_counter()
                try:
                    async with self.acquire():
                        await coro()
                    task_time = time.perf_counter() - start_time
                    self._stats.update_task_time(task_time)
                    self._stats.total_tasks += 1
                except Exception as e:
                    logger.error(f"Worker {worker_id} task failed: {e}")
                    self._stats.failed_tasks += 1
                finally:
                    self._queue.task_done()

            except asyncio.TimeoutError:
                # 队列为空，继续等待
                continue
            except asyncio.CancelledError:
                # 工作线程被取消
                break
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}")

        logger.debug(f"Worker {worker_id} stopped")

    def get_stats(self) -> AsyncIOStats:
        """获取统计信息

        Returns:
            异步 I/O 统计信息
        """
        return self._stats

    def reset_stats(self) -> None:
        """重置统计信息"""
        self._stats = AsyncIOStats()


# 全局优化器实例
_global_optimizer: AsyncIOOptimizer | None = None


def get_global_optimizer() -> AsyncIOOptimizer:
    """获取全局异步 I/O 优化器

    Returns:
        全局异步 I/O 优化器实例

    示例:
        >>> optimizer = get_global_optimizer()
        >>> results = await optimizer.gather_with_limit([task1(), task2()])
    """
    global _global_optimizer
    if _global_optimizer is None:
        _global_optimizer = AsyncIOOptimizer()
    return _global_optimizer


def set_global_optimizer(optimizer: AsyncIOOptimizer) -> None:
    """设置全局异步 I/O 优化器

    Args:
        optimizer: 异步 I/O 优化器实例

    示例:
        >>> config = AsyncIOConfig(max_concurrent_tasks=200)
        >>> optimizer = AsyncIOOptimizer(config)
        >>> set_global_optimizer(optimizer)
    """
    global _global_optimizer
    _global_optimizer = optimizer
