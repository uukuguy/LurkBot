"""异步优化工具模块测试"""

import asyncio
import time

import pytest

from lurkbot.utils.async_utils import (
    AsyncIOConfig,
    AsyncIOOptimizer,
    AsyncIOStats,
    ConcurrencyController,
    get_global_optimizer,
    set_global_optimizer,
)


class TestAsyncIOConfig:
    """测试 AsyncIOConfig"""

    def test_default_config(self):
        """测试默认配置"""
        config = AsyncIOConfig()
        assert config.max_concurrent_tasks == 100
        assert config.semaphore_timeout == 30.0
        assert config.batch_size == 50
        assert config.batch_timeout == 0.1
        assert config.max_retries == 3
        assert config.retry_delay == 1.0
        assert config.retry_backoff == 2.0
        assert config.default_timeout == 30.0
        assert config.gather_timeout is None

    def test_custom_config(self):
        """测试自定义配置"""
        config = AsyncIOConfig(
            max_concurrent_tasks=200,
            batch_size=100,
            max_retries=5,
        )
        assert config.max_concurrent_tasks == 200
        assert config.batch_size == 100
        assert config.max_retries == 5


class TestAsyncIOStats:
    """测试 AsyncIOStats"""

    def test_default_stats(self):
        """测试默认统计"""
        stats = AsyncIOStats()
        assert stats.total_tasks == 0
        assert stats.completed_tasks == 0
        assert stats.failed_tasks == 0
        assert stats.total_time == 0.0
        assert stats.avg_task_time == 0.0
        assert stats.max_concurrent == 0

    def test_update_task_time(self):
        """测试更新任务耗时"""
        stats = AsyncIOStats()
        stats.update_task_time(1.0)
        assert stats.completed_tasks == 1
        assert stats.total_time == 1.0
        assert stats.avg_task_time == 1.0
        assert stats.max_task_time == 1.0
        assert stats.min_task_time == 1.0

        stats.update_task_time(2.0)
        assert stats.completed_tasks == 2
        assert stats.total_time == 3.0
        assert stats.avg_task_time == 1.5
        assert stats.max_task_time == 2.0
        assert stats.min_task_time == 1.0

    def test_update_concurrent(self):
        """测试更新并发统计"""
        stats = AsyncIOStats()
        stats.update_concurrent(5)
        assert stats.current_concurrent == 5
        assert stats.max_concurrent == 5

        stats.update_concurrent(10)
        assert stats.current_concurrent == 10
        assert stats.max_concurrent == 10

        stats.update_concurrent(3)
        assert stats.current_concurrent == 3
        assert stats.max_concurrent == 10


class TestAsyncIOOptimizer:
    """测试 AsyncIOOptimizer"""

    @pytest.fixture
    def optimizer(self):
        """创建优化器实例"""
        config = AsyncIOConfig(max_concurrent_tasks=10)
        return AsyncIOOptimizer(config)

    @pytest.mark.asyncio
    async def test_semaphore(self, optimizer):
        """测试信号量"""
        async with optimizer.semaphore():
            assert optimizer.stats.current_concurrent == 1

        assert optimizer.stats.current_concurrent == 0

    @pytest.mark.asyncio
    async def test_gather_with_limit_success(self, optimizer):
        """测试并发执行成功"""

        async def task(value: int) -> int:
            await asyncio.sleep(0.01)
            return value * 2

        tasks = [task(i) for i in range(5)]
        results = await optimizer.gather_with_limit(tasks)

        assert results == [0, 2, 4, 6, 8]
        assert optimizer.stats.total_tasks == 5
        assert optimizer.stats.completed_tasks == 5
        assert optimizer.stats.failed_tasks == 0

    @pytest.mark.asyncio
    async def test_gather_with_limit_empty(self, optimizer):
        """测试空任务列表"""
        results = await optimizer.gather_with_limit([])
        assert results == []

    @pytest.mark.asyncio
    async def test_gather_with_limit_exception(self, optimizer):
        """测试异常处理"""

        async def task_success(value: int) -> int:
            return value * 2

        async def task_fail(value: int) -> int:
            raise ValueError(f"Task {value} failed")

        # 不返回异常，应该抛出
        tasks1 = [
            task_success(1),
            task_fail(2),
            task_success(3),
        ]
        with pytest.raises(ValueError, match="Task 2 failed"):
            await optimizer.gather_with_limit(tasks1, return_exceptions=False)

        # 返回异常（需要重新创建任务）
        optimizer.reset_stats()
        tasks2 = [
            task_success(1),
            task_fail(2),
            task_success(3),
        ]
        results = await optimizer.gather_with_limit(tasks2, return_exceptions=True)
        assert len(results) == 3
        assert results[0] == 2
        assert isinstance(results[1], ValueError)
        assert results[2] == 6

    @pytest.mark.asyncio
    async def test_gather_with_limit_concurrency(self, optimizer):
        """测试并发限制"""
        max_concurrent = 0
        current_concurrent = 0
        lock = asyncio.Lock()

        async def task(value: int) -> int:
            nonlocal max_concurrent, current_concurrent
            async with lock:
                current_concurrent += 1
                max_concurrent = max(max_concurrent, current_concurrent)

            await asyncio.sleep(0.01)

            async with lock:
                current_concurrent -= 1

            return value

        # 创建 20 个任务，但最大并发为 10
        tasks = [task(i) for i in range(20)]
        await optimizer.gather_with_limit(tasks)

        assert max_concurrent <= optimizer.config.max_concurrent_tasks

    @pytest.mark.asyncio
    async def test_batch_process(self, optimizer):
        """测试批处理"""

        async def processor(batch: list[int]) -> list[int]:
            await asyncio.sleep(0.01)
            return [x * 2 for x in batch]

        items = list(range(100))
        results = await optimizer.batch_process(items, processor)

        assert len(results) == 100
        assert results == [x * 2 for x in items]

    @pytest.mark.asyncio
    async def test_batch_process_empty(self, optimizer):
        """测试空批处理"""

        async def processor(batch: list[int]) -> list[int]:
            return [x * 2 for x in batch]

        results = await optimizer.batch_process([], processor)
        assert results == []

    @pytest.mark.asyncio
    async def test_batch_process_exception(self, optimizer):
        """测试批处理异常"""

        async def processor(batch: list[int]) -> list[int]:
            raise ValueError("Batch processing failed")

        items = list(range(10))
        with pytest.raises(ValueError, match="Batch processing failed"):
            await optimizer.batch_process(items, processor)

    @pytest.mark.asyncio
    async def test_retry_with_backoff_success(self, optimizer):
        """测试重试成功"""
        call_count = 0

        async def task() -> int:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary failure")
            return 42

        result = await optimizer.retry_with_backoff(task, retry_delay=0.01)
        assert result == 42
        assert call_count == 3
        assert optimizer.stats.total_retries == 2
        assert optimizer.stats.retry_success == 1

    @pytest.mark.asyncio
    async def test_retry_with_backoff_failure(self, optimizer):
        """测试重试失败"""

        async def task() -> int:
            raise ValueError("Permanent failure")

        with pytest.raises(ValueError, match="Permanent failure"):
            await optimizer.retry_with_backoff(
                task,
                max_retries=2,
                retry_delay=0.01,
            )

        assert optimizer.stats.total_retries == 2
        assert optimizer.stats.retry_success == 0

    @pytest.mark.asyncio
    async def test_retry_with_backoff_immediate_success(self, optimizer):
        """测试立即成功（无需重试）"""

        async def task() -> int:
            return 42

        result = await optimizer.retry_with_backoff(task)
        assert result == 42
        assert optimizer.stats.total_retries == 0
        assert optimizer.stats.retry_success == 0

    def test_get_stats(self, optimizer):
        """测试获取统计信息"""
        stats = optimizer.get_stats()
        assert isinstance(stats, AsyncIOStats)
        assert stats.total_tasks == 0

    def test_reset_stats(self, optimizer):
        """测试重置统计信息"""
        optimizer.stats.total_tasks = 10
        optimizer.stats.completed_tasks = 8
        optimizer.reset_stats()
        assert optimizer.stats.total_tasks == 0
        assert optimizer.stats.completed_tasks == 0


class TestConcurrencyController:
    """测试 ConcurrencyController"""

    @pytest.fixture
    async def controller(self):
        """创建并启动控制器"""
        ctrl = ConcurrencyController(max_workers=5, queue_size=100)
        await ctrl.start()
        yield ctrl
        await ctrl.stop()

    @pytest.mark.asyncio
    async def test_acquire(self, controller):
        """测试获取工作槽位"""
        async with controller.acquire():
            assert controller._stats.current_concurrent == 1

        assert controller._stats.current_concurrent == 0

    @pytest.mark.asyncio
    async def test_submit_success(self, controller):
        """测试提交任务成功"""

        async def task() -> int:
            await asyncio.sleep(0.01)
            return 42

        result = await controller.submit(task)
        assert result == 42

    @pytest.mark.asyncio
    async def test_submit_exception(self, controller):
        """测试提交任务异常"""

        async def task() -> int:
            raise ValueError("Task failed")

        with pytest.raises(ValueError, match="Task failed"):
            await controller.submit(task)

    @pytest.mark.asyncio
    async def test_submit_not_running(self):
        """测试未启动时提交任务"""
        controller = ConcurrencyController()

        async def task() -> int:
            return 42

        with pytest.raises(RuntimeError, match="ConcurrencyController is not running"):
            await controller.submit(task)

    @pytest.mark.asyncio
    async def test_start_stop(self):
        """测试启动和停止"""
        controller = ConcurrencyController(max_workers=3)

        # 启动
        await controller.start()
        assert controller._running is True
        assert len(controller._workers) == 3

        # 停止
        await controller.stop()
        assert controller._running is False
        assert len(controller._workers) == 0

    @pytest.mark.asyncio
    async def test_multiple_start(self, controller):
        """测试多次启动"""
        initial_workers = len(controller._workers)
        await controller.start()
        assert len(controller._workers) == initial_workers

    @pytest.mark.asyncio
    async def test_multiple_stop(self, controller):
        """测试多次停止"""
        await controller.stop()
        assert controller._running is False
        await controller.stop()
        assert controller._running is False

    @pytest.mark.asyncio
    async def test_concurrent_tasks(self, controller):
        """测试并发任务"""
        results = []

        async def task(value: int) -> int:
            await asyncio.sleep(0.01)
            return value * 2

        # 提交多个任务
        tasks = [controller.submit(lambda v=i: task(v)) for i in range(10)]
        results = await asyncio.gather(*tasks)

        assert len(results) == 10
        assert results == [i * 2 for i in range(10)]

    def test_get_stats(self, controller):
        """测试获取统计信息"""
        stats = controller.get_stats()
        assert isinstance(stats, AsyncIOStats)

    def test_reset_stats(self, controller):
        """测试重置统计信息"""
        controller._stats.total_tasks = 10
        controller.reset_stats()
        assert controller._stats.total_tasks == 0


class TestGlobalOptimizer:
    """测试全局优化器"""

    def test_get_global_optimizer(self):
        """测试获取全局优化器"""
        optimizer1 = get_global_optimizer()
        optimizer2 = get_global_optimizer()
        assert optimizer1 is optimizer2

    def test_set_global_optimizer(self):
        """测试设置全局优化器"""
        config = AsyncIOConfig(max_concurrent_tasks=200)
        optimizer = AsyncIOOptimizer(config)
        set_global_optimizer(optimizer)

        global_optimizer = get_global_optimizer()
        assert global_optimizer is optimizer
        assert global_optimizer.config.max_concurrent_tasks == 200
