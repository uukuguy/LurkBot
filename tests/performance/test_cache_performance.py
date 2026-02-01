"""缓存性能测试

测试内容：
- 内存缓存性能
- 多层缓存性能
- 缓存命中率测试
- 并发访问性能
"""

import asyncio
import random
import string

import pytest

from lurkbot.utils.cache import MemoryCache, MultiLevelCache


def generate_random_string(length: int = 10) -> str:
    """生成随机字符串"""
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))


class TestMemoryCachePerformance:
    """测试内存缓存性能"""

    @pytest.mark.benchmark(group="memory_cache_set")
    def test_memory_cache_set_performance(self, benchmark):
        """测试设置性能"""
        cache = MemoryCache[str](maxsize=10000, ttl=300)

        def run_set_values():
            async def set_values():
                for i in range(1000):
                    await cache.set(f"key{i}", f"value{i}")
            asyncio.run(set_values())

        benchmark(run_set_values)

    @pytest.mark.benchmark(group="memory_cache_get")
    def test_memory_cache_get_performance(self, benchmark):
        """测试获取性能"""
        cache = MemoryCache[str](maxsize=10000, ttl=300)

        # 预填充数据
        async def setup():
            for i in range(1000):
                await cache.set(f"key{i}", f"value{i}")

        asyncio.run(setup())

        def run_get_values():
            async def get_values():
                for i in range(1000):
                    await cache.get(f"key{i}")
            asyncio.run(get_values())

        benchmark(run_get_values)

    @pytest.mark.benchmark(group="memory_cache_mixed")
    def test_memory_cache_mixed_performance(self, benchmark):
        """测试混合操作性能"""
        cache = MemoryCache[str](maxsize=10000, ttl=300)

        def run_mixed_operations():
            async def mixed_operations():
                for i in range(500):
                    await cache.set(f"key{i}", f"value{i}")
                    await cache.get(f"key{i}")
            asyncio.run(mixed_operations())

        benchmark(run_mixed_operations)

    @pytest.mark.benchmark(group="memory_cache_concurrent")
    def test_memory_cache_concurrent_performance(self, benchmark):
        """测试并发性能"""
        cache = MemoryCache[str](maxsize=10000, ttl=300)

        def run_concurrent_operations():
            async def concurrent_operations():
                async def worker(worker_id: int):
                    for i in range(100):
                        key = f"key{worker_id}_{i}"
                        await cache.set(key, f"value{i}")
                        await cache.get(key)

                await asyncio.gather(*[worker(i) for i in range(10)])
            asyncio.run(concurrent_operations())

        benchmark(run_concurrent_operations)


class TestMultiLevelCachePerformance:
    """测试多层缓存性能"""

    @pytest.mark.benchmark(group="multi_level_cache_set")
    def test_multi_level_cache_set_performance(self, benchmark):
        """测试设置性能（仅 L1）"""
        cache = MultiLevelCache[str](
            l1_maxsize=10000,
            l1_ttl=60,
            l2_enabled=False,
        )

        def run_set_values():
            async def set_values():
                for i in range(1000):
                    await cache.set(f"key{i}", f"value{i}")
            asyncio.run(set_values())

        benchmark(run_set_values)

    @pytest.mark.benchmark(group="multi_level_cache_get")
    def test_multi_level_cache_get_performance(self, benchmark):
        """测试获取性能（仅 L1）"""
        cache = MultiLevelCache[str](
            l1_maxsize=10000,
            l1_ttl=60,
            l2_enabled=False,
        )

        # 预填充数据
        async def setup():
            for i in range(1000):
                await cache.set(f"key{i}", f"value{i}")

        asyncio.run(setup())

        def run_get_values():
            async def get_values():
                for i in range(1000):
                    await cache.get(f"key{i}")
            asyncio.run(get_values())

        benchmark(run_get_values)

    @pytest.mark.benchmark(group="multi_level_cache_hit_rate")
    def test_multi_level_cache_hit_rate(self, benchmark):
        """测试缓存命中率"""
        cache = MultiLevelCache[str](
            l1_maxsize=100,  # 小容量，测试 LRU
            l1_ttl=60,
            l2_enabled=False,
        )

        def run_test_hit_rate():
            async def test_hit_rate():
                # 预填充 100 个键
                for i in range(100):
                    await cache.set(f"key{i}", f"value{i}")

                # 访问前 80 个键（应该命中）
                for i in range(80):
                    await cache.get(f"key{i}")

                # 访问后 20 个键（应该命中）
                for i in range(80, 100):
                    await cache.get(f"key{i}")

                # 访问不存在的键（应该未命中）
                for i in range(100, 120):
                    await cache.get(f"key{i}")

                # 检查命中率
                stats = await cache.get_stats()
                hit_rate = stats["total"]["hit_rate"]
                assert hit_rate > 0.8, f"Hit rate too low: {hit_rate}"
            asyncio.run(test_hit_rate())

        benchmark(run_test_hit_rate)


class TestCacheHitRateScenarios:
    """测试不同场景下的缓存命中率"""

    @pytest.mark.asyncio
    async def test_sequential_access_hit_rate(self):
        """测试顺序访问命中率"""
        cache = MemoryCache[str](maxsize=1000, ttl=300)

        # 预填充数据
        for i in range(1000):
            await cache.set(f"key{i}", f"value{i}")

        # 重置统计
        await cache.reset_stats()

        # 顺序访问
        for i in range(1000):
            await cache.get(f"key{i}")

        # 检查命中率
        stats = await cache.get_stats()
        assert stats.hit_rate == 1.0, f"Expected 100% hit rate, got {stats.hit_rate}"

    @pytest.mark.asyncio
    async def test_random_access_hit_rate(self):
        """测试随机访问命中率"""
        cache = MemoryCache[str](maxsize=1000, ttl=300)

        # 预填充数据
        for i in range(1000):
            await cache.set(f"key{i}", f"value{i}")

        # 重置统计
        await cache.reset_stats()

        # 随机访问（80% 命中，20% 未命中）
        for _ in range(1000):
            if random.random() < 0.8:
                # 访问存在的键
                key_id = random.randint(0, 999)
                await cache.get(f"key{key_id}")
            else:
                # 访问不存在的键
                await cache.get(f"key_nonexistent_{random.randint(0, 999)}")

        # 检查命中率
        stats = await cache.get_stats()
        assert stats.hit_rate > 0.75, f"Hit rate too low: {stats.hit_rate}"

    @pytest.mark.asyncio
    async def test_hot_key_access_hit_rate(self):
        """测试热点键访问命中率"""
        cache = MemoryCache[str](maxsize=1000, ttl=300)

        # 预填充数据
        for i in range(1000):
            await cache.set(f"key{i}", f"value{i}")

        # 重置统计
        await cache.reset_stats()

        # 热点键访问（80% 访问前 20% 的键）
        for _ in range(1000):
            if random.random() < 0.8:
                # 访问热点键
                key_id = random.randint(0, 199)
                await cache.get(f"key{key_id}")
            else:
                # 访问其他键
                key_id = random.randint(200, 999)
                await cache.get(f"key{key_id}")

        # 检查命中率
        stats = await cache.get_stats()
        assert stats.hit_rate == 1.0, f"Expected 100% hit rate, got {stats.hit_rate}"

    @pytest.mark.asyncio
    async def test_lru_eviction_hit_rate(self):
        """测试 LRU 淘汰后的命中率"""
        cache = MemoryCache[str](maxsize=100, ttl=300)

        # 预填充数据
        for i in range(100):
            await cache.set(f"key{i}", f"value{i}")

        # 重置统计
        await cache.reset_stats()

        # 访问前 50 个键（保持热度）
        for i in range(50):
            await cache.get(f"key{i}")

        # 添加新键，触发 LRU 淘汰
        for i in range(100, 150):
            await cache.set(f"key{i}", f"value{i}")

        # 访问前 50 个键（应该命中）
        for i in range(50):
            await cache.get(f"key{i}")

        # 访问后 50 个键（应该未命中，已被淘汰）
        for i in range(50, 100):
            await cache.get(f"key{i}")

        # 检查命中率
        stats = await cache.get_stats()
        # 前 50 次访问 + 前 50 次访问 = 100 次命中
        # 后 50 次访问 = 50 次未命中
        # 命中率 = 100 / 150 = 0.667
        assert stats.hit_rate > 0.6, f"Hit rate too low: {stats.hit_rate}"


class TestCachePerformanceComparison:
    """测试缓存性能对比"""

    @pytest.mark.asyncio
    async def test_with_vs_without_cache(self):
        """测试有缓存 vs 无缓存的性能对比"""
        cache = MemoryCache[str](maxsize=1000, ttl=300)

        # 模拟慢速数据源
        async def slow_data_source(key: str) -> str:
            await asyncio.sleep(0.001)  # 模拟 1ms 延迟
            return f"value_{key}"

        # 无缓存
        import time

        start = time.perf_counter()
        for i in range(100):
            await slow_data_source(f"key{i}")
        no_cache_time = time.perf_counter() - start

        # 有缓存（第一次访问）
        start = time.perf_counter()
        for i in range(100):
            value = await cache.get(f"key{i}")
            if value is None:
                value = await slow_data_source(f"key{i}")
                await cache.set(f"key{i}", value)
        first_access_time = time.perf_counter() - start

        # 有缓存（第二次访问，全部命中）
        start = time.perf_counter()
        for i in range(100):
            await cache.get(f"key{i}")
        cached_time = time.perf_counter() - start

        # 性能提升
        speedup = no_cache_time / cached_time

        print(f"\n无缓存时间: {no_cache_time:.4f}s")
        print(f"首次访问时间: {first_access_time:.4f}s")
        print(f"缓存命中时间: {cached_time:.4f}s")
        print(f"性能提升: {speedup:.2f}x")

        # 验证性能提升
        assert speedup > 10, f"Performance improvement too low: {speedup}x"

    @pytest.mark.asyncio
    async def test_memory_cache_vs_dict(self):
        """测试 MemoryCache vs 普通字典的性能对比"""
        cache = MemoryCache[str](maxsize=1000, ttl=300)
        plain_dict: dict[str, str] = {}

        # MemoryCache 性能
        import time

        start = time.perf_counter()
        for i in range(1000):
            await cache.set(f"key{i}", f"value{i}")
        for i in range(1000):
            await cache.get(f"key{i}")
        cache_time = time.perf_counter() - start

        # 普通字典性能
        start = time.perf_counter()
        for i in range(1000):
            plain_dict[f"key{i}"] = f"value{i}"
        for i in range(1000):
            _ = plain_dict.get(f"key{i}")
        dict_time = time.perf_counter() - start

        # 性能对比
        overhead = cache_time / dict_time

        print(f"\nMemoryCache 时间: {cache_time:.4f}s")
        print(f"普通字典时间: {dict_time:.4f}s")
        print(f"性能开销: {overhead:.2f}x")

        # 验证性能开销在合理范围内（< 10x）
        assert overhead < 10, f"Performance overhead too high: {overhead}x"
