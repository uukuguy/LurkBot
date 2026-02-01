"""缓存工具模块测试

测试内容：
- MemoryCache 功能测试
- RedisCache 功能测试（需要 Redis）
- MultiLevelCache 功能测试
- 缓存统计测试
- TTL 过期测试
"""

import asyncio
import time

import pytest

from lurkbot.utils.cache import (
    CacheStats,
    MemoryCache,
    MultiLevelCache,
    RedisCache,
    create_memory_cache,
    create_multi_level_cache,
    create_redis_cache,
)


class TestCacheStats:
    """测试缓存统计"""

    def test_cache_stats_init(self):
        """测试初始化"""
        stats = CacheStats()
        assert stats.hits == 0
        assert stats.misses == 0
        assert stats.sets == 0
        assert stats.deletes == 0
        assert stats.evictions == 0

    def test_cache_stats_hit_rate(self):
        """测试命中率计算"""
        stats = CacheStats()
        assert stats.hit_rate == 0.0

        stats.hits = 80
        stats.misses = 20
        assert stats.hit_rate == 0.8

        stats.hits = 100
        stats.misses = 0
        assert stats.hit_rate == 1.0

    def test_cache_stats_total_operations(self):
        """测试总操作数"""
        stats = CacheStats()
        stats.hits = 100
        stats.misses = 50
        stats.sets = 30
        stats.deletes = 10
        assert stats.total_operations == 190

    def test_cache_stats_reset(self):
        """测试重置"""
        stats = CacheStats()
        stats.hits = 100
        stats.misses = 50
        stats.reset()
        assert stats.hits == 0
        assert stats.misses == 0

    def test_cache_stats_to_dict(self):
        """测试转换为字典"""
        stats = CacheStats()
        stats.hits = 80
        stats.misses = 20
        data = stats.to_dict()
        assert data["hits"] == 80
        assert data["misses"] == 20
        assert data["hit_rate"] == 0.8


class TestMemoryCache:
    """测试内存缓存"""

    @pytest.mark.asyncio
    async def test_memory_cache_init(self):
        """测试初始化"""
        cache = MemoryCache[str](maxsize=100, ttl=60)
        assert cache.maxsize == 100
        assert cache.ttl == 60
        assert await cache.size() == 0

    @pytest.mark.asyncio
    async def test_memory_cache_get_set(self):
        """测试 get/set"""
        cache = MemoryCache[str](maxsize=100, ttl=60)

        # 设置缓存
        await cache.set("key1", "value1")
        assert await cache.size() == 1

        # 获取缓存
        value = await cache.get("key1")
        assert value == "value1"

        # 获取不存在的键
        value = await cache.get("key2")
        assert value is None

    @pytest.mark.asyncio
    async def test_memory_cache_delete(self):
        """测试删除"""
        cache = MemoryCache[str](maxsize=100, ttl=60)

        # 设置缓存
        await cache.set("key1", "value1")
        assert await cache.size() == 1

        # 删除缓存
        result = await cache.delete("key1")
        assert result is True
        assert await cache.size() == 0

        # 删除不存在的键
        result = await cache.delete("key2")
        assert result is False

    @pytest.mark.asyncio
    async def test_memory_cache_clear(self):
        """测试清空"""
        cache = MemoryCache[str](maxsize=100, ttl=60)

        # 设置多个缓存
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        assert await cache.size() == 2

        # 清空缓存
        await cache.clear()
        assert await cache.size() == 0

    @pytest.mark.asyncio
    async def test_memory_cache_lru_eviction(self):
        """测试 LRU 淘汰"""
        cache = MemoryCache[str](maxsize=3, ttl=None)

        # 设置 3 个缓存
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        await cache.set("key3", "value3")
        assert await cache.size() == 3

        # 设置第 4 个缓存，应该淘汰 key1
        await cache.set("key4", "value4")
        assert await cache.size() == 3
        assert await cache.get("key1") is None
        assert await cache.get("key4") == "value4"

        # 访问 key2，使其成为最近使用
        await cache.get("key2")

        # 设置第 5 个缓存，应该淘汰 key3
        await cache.set("key5", "value5")
        assert await cache.size() == 3
        assert await cache.get("key3") is None
        assert await cache.get("key2") == "value2"

    @pytest.mark.asyncio
    async def test_memory_cache_ttl_expiration(self):
        """测试 TTL 过期"""
        cache = MemoryCache[str](maxsize=100, ttl=1)

        # 设置缓存
        await cache.set("key1", "value1")
        assert await cache.get("key1") == "value1"

        # 等待过期
        await asyncio.sleep(1.1)

        # 获取缓存，应该已过期
        value = await cache.get("key1")
        assert value is None
        assert await cache.size() == 0

    @pytest.mark.asyncio
    async def test_memory_cache_custom_ttl(self):
        """测试自定义 TTL"""
        cache = MemoryCache[str](maxsize=100, ttl=10)

        # 设置缓存，使用自定义 TTL
        await cache.set("key1", "value1", ttl=1)
        assert await cache.get("key1") == "value1"

        # 等待过期
        await asyncio.sleep(1.1)

        # 获取缓存，应该已过期
        value = await cache.get("key1")
        assert value is None

    @pytest.mark.asyncio
    async def test_memory_cache_stats(self):
        """测试统计"""
        cache = MemoryCache[str](maxsize=100, ttl=60)

        # 设置缓存
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")

        # 获取缓存
        await cache.get("key1")  # hit
        await cache.get("key2")  # hit
        await cache.get("key3")  # miss

        # 删除缓存
        await cache.delete("key1")

        # 检查统计
        stats = await cache.get_stats()
        assert stats.hits == 2
        assert stats.misses == 1
        assert stats.sets == 2
        assert stats.deletes == 1
        assert stats.hit_rate == 2 / 3

        # 重置统计
        await cache.reset_stats()
        stats = await cache.get_stats()
        assert stats.hits == 0
        assert stats.misses == 0

    @pytest.mark.asyncio
    async def test_memory_cache_concurrent_access(self):
        """测试并发访问"""
        cache = MemoryCache[int](maxsize=1000, ttl=60)

        # 并发设置
        async def set_value(i: int):
            await cache.set(f"key{i}", i)

        await asyncio.gather(*[set_value(i) for i in range(100)])
        assert await cache.size() == 100

        # 并发获取
        async def get_value(i: int):
            value = await cache.get(f"key{i}")
            assert value == i

        await asyncio.gather(*[get_value(i) for i in range(100)])


class TestRedisCache:
    """测试 Redis 缓存

    注意：这些测试需要 Redis 服务器运行
    """

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not hasattr(RedisCache, "__init__"),
        reason="Redis not available",
    )
    async def test_redis_cache_init(self):
        """测试初始化"""
        try:
            cache = RedisCache[str](url="redis://localhost:6379", ttl=60)
            await cache.close()
        except Exception:
            pytest.skip("Redis not available")

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not hasattr(RedisCache, "__init__"),
        reason="Redis not available",
    )
    async def test_redis_cache_get_set(self):
        """测试 get/set"""
        try:
            cache = RedisCache[str](url="redis://localhost:6379", ttl=60)

            # 清空数据库
            await cache.clear()

            # 设置缓存
            result = await cache.set("test_key1", "test_value1")
            assert result is True

            # 获取缓存
            value = await cache.get("test_key1")
            assert value == "test_value1"

            # 获取不存在的键
            value = await cache.get("test_key2")
            assert value is None

            await cache.close()
        except Exception:
            pytest.skip("Redis not available")

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not hasattr(RedisCache, "__init__"),
        reason="Redis not available",
    )
    async def test_redis_cache_delete(self):
        """测试删除"""
        try:
            cache = RedisCache[str](url="redis://localhost:6379", ttl=60)

            # 清空数据库
            await cache.clear()

            # 设置缓存
            await cache.set("test_key1", "test_value1")

            # 删除缓存
            result = await cache.delete("test_key1")
            assert result is True

            # 获取缓存，应该不存在
            value = await cache.get("test_key1")
            assert value is None

            # 删除不存在的键
            result = await cache.delete("test_key2")
            assert result is False

            await cache.close()
        except Exception:
            pytest.skip("Redis not available")

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not hasattr(RedisCache, "__init__"),
        reason="Redis not available",
    )
    async def test_redis_cache_ttl_expiration(self):
        """测试 TTL 过期"""
        try:
            cache = RedisCache[str](url="redis://localhost:6379", ttl=1)

            # 清空数据库
            await cache.clear()

            # 设置缓存
            await cache.set("test_key1", "test_value1")
            assert await cache.get("test_key1") == "test_value1"

            # 等待过期
            await asyncio.sleep(1.1)

            # 获取缓存，应该已过期
            value = await cache.get("test_key1")
            assert value is None

            await cache.close()
        except Exception:
            pytest.skip("Redis not available")

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not hasattr(RedisCache, "__init__"),
        reason="Redis not available",
    )
    async def test_redis_cache_stats(self):
        """测试统计"""
        try:
            cache = RedisCache[str](url="redis://localhost:6379", ttl=60)

            # 清空数据库
            await cache.clear()

            # 重置统计
            await cache.reset_stats()

            # 设置缓存
            await cache.set("test_key1", "test_value1")
            await cache.set("test_key2", "test_value2")

            # 获取缓存
            await cache.get("test_key1")  # hit
            await cache.get("test_key2")  # hit
            await cache.get("test_key3")  # miss

            # 删除缓存
            await cache.delete("test_key1")

            # 检查统计
            stats = await cache.get_stats()
            assert stats.hits == 2
            assert stats.misses == 1
            assert stats.sets == 2
            assert stats.deletes == 1

            await cache.close()
        except Exception:
            pytest.skip("Redis not available")


class TestMultiLevelCache:
    """测试多层缓存"""

    @pytest.mark.asyncio
    async def test_multi_level_cache_init(self):
        """测试初始化"""
        cache = MultiLevelCache[str](
            l1_maxsize=100,
            l1_ttl=60,
            l2_enabled=False,
        )
        assert cache.l1 is not None
        assert cache.l2 is None

    @pytest.mark.asyncio
    async def test_multi_level_cache_get_set_l1_only(self):
        """测试 get/set（仅 L1）"""
        cache = MultiLevelCache[str](
            l1_maxsize=100,
            l1_ttl=60,
            l2_enabled=False,
        )

        # 设置缓存
        await cache.set("key1", "value1")

        # 获取缓存
        value = await cache.get("key1")
        assert value == "value1"

        # 获取不存在的键
        value = await cache.get("key2")
        assert value is None

    @pytest.mark.asyncio
    async def test_multi_level_cache_delete_l1_only(self):
        """测试删除（仅 L1）"""
        cache = MultiLevelCache[str](
            l1_maxsize=100,
            l1_ttl=60,
            l2_enabled=False,
        )

        # 设置缓存
        await cache.set("key1", "value1")

        # 删除缓存
        result = await cache.delete("key1")
        assert result is True

        # 获取缓存，应该不存在
        value = await cache.get("key1")
        assert value is None

    @pytest.mark.asyncio
    async def test_multi_level_cache_clear_l1_only(self):
        """测试清空（仅 L1）"""
        cache = MultiLevelCache[str](
            l1_maxsize=100,
            l1_ttl=60,
            l2_enabled=False,
        )

        # 设置多个缓存
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")

        # 清空缓存
        await cache.clear()

        # 获取缓存，应该不存在
        assert await cache.get("key1") is None
        assert await cache.get("key2") is None

    @pytest.mark.asyncio
    async def test_multi_level_cache_size_l1_only(self):
        """测试大小（仅 L1）"""
        cache = MultiLevelCache[str](
            l1_maxsize=100,
            l1_ttl=60,
            l2_enabled=False,
        )

        # 设置多个缓存
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")

        # 获取大小
        l1_size, l2_size = await cache.size()
        assert l1_size == 2
        assert l2_size == 0

    @pytest.mark.asyncio
    async def test_multi_level_cache_stats_l1_only(self):
        """测试统计（仅 L1）"""
        cache = MultiLevelCache[str](
            l1_maxsize=100,
            l1_ttl=60,
            l2_enabled=False,
        )

        # 设置缓存
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")

        # 获取缓存
        await cache.get("key1")  # hit
        await cache.get("key2")  # hit
        await cache.get("key3")  # miss

        # 删除缓存
        await cache.delete("key1")

        # 检查统计
        stats = await cache.get_stats()
        assert stats["total"]["hits"] == 2
        assert stats["total"]["misses"] == 1
        assert stats["total"]["sets"] == 2
        assert stats["total"]["deletes"] == 1
        assert stats["l1"]["hits"] == 2
        assert stats["l1"]["misses"] == 1
        assert stats["l2"] is None


class TestCacheFactories:
    """测试缓存工厂函数"""

    @pytest.mark.asyncio
    async def test_create_memory_cache(self):
        """测试创建内存缓存"""
        cache = await create_memory_cache(maxsize=100, ttl=60)
        assert cache.maxsize == 100
        assert cache.ttl == 60

    @pytest.mark.asyncio
    async def test_create_multi_level_cache(self):
        """测试创建多层缓存"""
        cache = await create_multi_level_cache(
            l1_maxsize=100,
            l1_ttl=60,
            l2_enabled=False,
        )
        assert cache.l1 is not None
        assert cache.l2 is None
