"""异步优化性能测试

测试异步 I/O 优化器和并发控制器的性能。
"""

import asyncio
import time

import pytest

from lurkbot.utils.async_utils import (
    AsyncIOConfig,
    AsyncIOOptimizer,
    ConcurrencyController,
)


class TestAsyncIOOptimizerPerformance:
    """测试 AsyncIOOptimizer 性能"""

    @pytest.mark.benchmark(group="gather")
    def test_gather_with_limit_performance(self, benchmark):
        """测试并发执行性能"""

        def run_gather():
            optimizer = AsyncIOOptimizer(AsyncIOConfig(max_concurrent_tasks=50))

            async def task(value: int) -> int:
                await asyncio.sleep(0.001)  # 模拟 I/O 操作
                return value * 2

            async def _run():
                tasks = [task(i) for i in range(100)]
                return await optimizer.gather_with_limit(tasks)

            return asyncio.run(_run())

        result = benchmark(run_gather)
        assert len(result) == 100

    @pytest.mark.benchmark(group="gather")
    def test_gather_without_limit_performance(self, benchmark):
        """测试无限制并发执行性能（对比基准）"""

        async def task(value: int) -> int:
            await asyncio.sleep(0.001)
            return value * 2

        def run_gather():
            async def _run():
                tasks = [task(i) for i in range(100)]
                return await asyncio.gather(*tasks)

            return asyncio.run(_run())

        result = benchmark(run_gather)
        assert len(result) == 100

    @pytest.mark.benchmark(group="batch")
    def test_batch_process_performance(self, benchmark):
        """测试批处理性能"""

        def run_batch():
            optimizer = AsyncIOOptimizer(AsyncIOConfig(max_concurrent_tasks=50))

            async def processor(batch: list[int]) -> list[int]:
                await asyncio.sleep(0.001)
                return [x * 2 for x in batch]

            async def _run():
                items = list(range(1000))
                return await optimizer.batch_process(items, processor)

            return asyncio.run(_run())

        result = benchmark(run_batch)
        assert len(result) == 1000

    @pytest.mark.benchmark(group="batch")
    def test_sequential_process_performance(self, benchmark):
        """测试顺序处理性能（对比基准）"""

        async def process_item(item: int) -> int:
            await asyncio.sleep(0.001)
            return item * 2

        def run_sequential():
            async def _run():
                items = list(range(1000))
                results = []
                for item in items:
                    result = await process_item(item)
                    results.append(result)
                return results

            return asyncio.run(_run())

        result = benchmark(run_sequential)
        assert len(result) == 1000

    @pytest.mark.benchmark(group="retry")
    def test_retry_with_backoff_performance(self, benchmark):
        """测试重试机制性能"""

        def run_retry():
            optimizer = AsyncIOOptimizer(AsyncIOConfig(max_concurrent_tasks=50))
            call_count = 0

            async def task() -> int:
                nonlocal call_count
                call_count += 1
                if call_count < 2:
                    raise ValueError("Temporary failure")
                return 42

            async def _run():
                return await optimizer.retry_with_backoff(
                    task,
                    retry_delay=0.001,
                )

            return asyncio.run(_run())

        result = benchmark(run_retry)
        assert result == 42

    @pytest.mark.benchmark(group="semaphore")
    def test_semaphore_performance(self, benchmark):
        """测试信号量性能"""

        def run_with_semaphore():
            optimizer = AsyncIOOptimizer(AsyncIOConfig(max_concurrent_tasks=50))

            async def _run():
                async with optimizer.semaphore():
                    await asyncio.sleep(0.001)
                    return 42

            return asyncio.run(_run())

        result = benchmark(run_with_semaphore)
        assert result == 42

    @pytest.mark.benchmark(group="concurrent")
    def test_high_concurrency_performance(self, benchmark):
        """测试高并发性能"""

        def run_high_concurrency():
            optimizer = AsyncIOOptimizer(AsyncIOConfig(max_concurrent_tasks=50))

            async def task(value: int) -> int:
                await asyncio.sleep(0.0001)
                return value * 2

            async def _run():
                tasks = [task(i) for i in range(1000)]
                return await optimizer.gather_with_limit(tasks)

            return asyncio.run(_run())

        result = benchmark(run_high_concurrency)
        assert len(result) == 1000


class TestConcurrencyControllerPerformance:
    """测试 ConcurrencyController 性能"""

    @pytest.mark.benchmark(group="controller")
    def test_submit_performance(self, benchmark):
        """测试任务提交性能"""

        def run_submit():
            async def task() -> int:
                await asyncio.sleep(0.001)
                return 42

            async def _run():
                ctrl = ConcurrencyController(max_workers=10, queue_size=1000)
                await ctrl.start()
                try:
                    return await ctrl.submit(task)
                finally:
                    await ctrl.stop()

            return asyncio.run(_run())

        result = benchmark(run_submit)
        assert result == 42

    @pytest.mark.benchmark(group="controller")
    def test_concurrent_submit_performance(self, benchmark):
        """测试并发提交性能"""

        def run_concurrent_submit():
            async def task() -> int:
                await asyncio.sleep(0.001)
                return 42

            async def _run():
                ctrl = ConcurrencyController(max_workers=10, queue_size=1000)
                await ctrl.start()
                try:
                    tasks = [ctrl.submit(task) for _ in range(100)]
                    return await asyncio.gather(*tasks)
                finally:
                    await ctrl.stop()

            return asyncio.run(_run())

        result = benchmark(run_concurrent_submit)
        assert len(result) == 100


class TestAsyncIOComparison:
    """对比测试：优化前后性能对比"""

    @pytest.mark.benchmark(group="comparison")
    def test_optimized_gather(self, benchmark):
        """测试优化后的并发执行"""

        def run():
            optimizer = AsyncIOOptimizer(AsyncIOConfig(max_concurrent_tasks=50))

            async def task(value: int) -> int:
                await asyncio.sleep(0.001)
                return value * 2

            async def _run():
                tasks = [task(i) for i in range(200)]
                return await optimizer.gather_with_limit(tasks)

            return asyncio.run(_run())

        result = benchmark(run)
        assert len(result) == 200

    @pytest.mark.benchmark(group="comparison")
    def test_unoptimized_gather(self, benchmark):
        """测试未优化的并发执行"""

        def run():
            async def task(value: int) -> int:
                await asyncio.sleep(0.001)
                return value * 2

            async def _run():
                tasks = [task(i) for i in range(200)]
                return await asyncio.gather(*tasks)

            return asyncio.run(_run())

        result = benchmark(run)
        assert len(result) == 200

    @pytest.mark.benchmark(group="comparison")
    def test_optimized_batch(self, benchmark):
        """测试优化后的批处理"""

        def run():
            optimizer = AsyncIOOptimizer(AsyncIOConfig(batch_size=50))

            async def processor(batch: list[int]) -> list[int]:
                await asyncio.sleep(0.001)
                return [x * 2 for x in batch]

            async def _run():
                items = list(range(500))
                return await optimizer.batch_process(items, processor)

            return asyncio.run(_run())

        result = benchmark(run)
        assert len(result) == 500

    @pytest.mark.benchmark(group="comparison")
    def test_unoptimized_batch(self, benchmark):
        """测试未优化的批处理"""

        def run():
            async def process_item(item: int) -> int:
                await asyncio.sleep(0.001)
                return item * 2

            async def _run():
                items = list(range(500))
                results = []
                for item in items:
                    result = await process_item(item)
                    results.append(result)
                return results

            return asyncio.run(_run())

        result = benchmark(run)
        assert len(result) == 500


class TestRealWorldScenarios:
    """真实场景性能测试"""

    @pytest.mark.benchmark(group="real-world")
    def test_api_calls_simulation(self, benchmark):
        """模拟 API 调用场景"""

        def run():
            optimizer = AsyncIOOptimizer(AsyncIOConfig(max_concurrent_tasks=20))

            async def api_call(endpoint: str) -> dict:
                """模拟 API 调用"""
                await asyncio.sleep(0.01)  # 模拟网络延迟
                return {"endpoint": endpoint, "status": "success"}

            async def _run():
                endpoints = [f"/api/endpoint{i}" for i in range(100)]
                tasks = [api_call(ep) for ep in endpoints]
                return await optimizer.gather_with_limit(tasks)

            return asyncio.run(_run())

        result = benchmark(run)
        assert len(result) == 100

    @pytest.mark.benchmark(group="real-world")
    def test_database_queries_simulation(self, benchmark):
        """模拟数据库查询场景"""

        def run():
            optimizer = AsyncIOOptimizer(AsyncIOConfig(batch_size=20))

            async def query_batch(ids: list[int]) -> list[dict]:
                """模拟批量数据库查询"""
                await asyncio.sleep(0.005)  # 模拟数据库延迟
                return [{"id": id, "data": f"data_{id}"} for id in ids]

            async def _run():
                ids = list(range(200))
                return await optimizer.batch_process(ids, query_batch)

            return asyncio.run(_run())

        result = benchmark(run)
        assert len(result) == 200

    @pytest.mark.benchmark(group="real-world")
    def test_file_operations_simulation(self, benchmark):
        """模拟文件操作场景"""

        def run():
            optimizer = AsyncIOOptimizer(AsyncIOConfig(max_concurrent_tasks=10))

            async def read_file(filename: str) -> str:
                """模拟文件读取"""
                await asyncio.sleep(0.002)  # 模拟 I/O 延迟
                return f"content of {filename}"

            async def _run():
                filenames = [f"file{i}.txt" for i in range(50)]
                tasks = [read_file(fn) for fn in filenames]
                return await optimizer.gather_with_limit(tasks)

            return asyncio.run(_run())

        result = benchmark(run)
        assert len(result) == 50

    @pytest.mark.benchmark(group="real-world")
    def test_message_processing_simulation(self, benchmark):
        """模拟消息处理场景"""

        def run():
            optimizer = AsyncIOOptimizer(AsyncIOConfig(batch_size=30))

            async def process_messages(messages: list[dict]) -> list[dict]:
                """模拟批量消息处理"""
                await asyncio.sleep(0.003)
                return [
                    {"id": msg["id"], "processed": True, "result": msg["data"] * 2}
                    for msg in messages
                ]

            async def _run():
                messages = [{"id": i, "data": i} for i in range(300)]
                return await optimizer.batch_process(messages, process_messages)

            return asyncio.run(_run())

        result = benchmark(run)
        assert len(result) == 300
