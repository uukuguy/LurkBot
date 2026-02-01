"""缓存工具模块

提供多层缓存策略，包括：
- 内存缓存（LRU + TTL）
- Redis 缓存
- 多层缓存（L1 + L2）

性能目标：
- 缓存命中率 > 80%
- 性能提升 60%+
"""

import asyncio
import json
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar

from loguru import logger

try:
    import redis.asyncio as aioredis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("redis-py not installed, Redis cache will be disabled")


T = TypeVar("T")


@dataclass
class CacheStats:
    """缓存统计信息"""

    hits: int = 0
    misses: int = 0
    sets: int = 0
    deletes: int = 0
    evictions: int = 0

    @property
    def hit_rate(self) -> float:
        """缓存命中率"""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0

    @property
    def total_operations(self) -> int:
        """总操作数"""
        return self.hits + self.misses + self.sets + self.deletes

    def reset(self) -> None:
        """重置统计"""
        self.hits = 0
        self.misses = 0
        self.sets = 0
        self.deletes = 0
        self.evictions = 0

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "hits": self.hits,
            "misses": self.misses,
            "sets": self.sets,
            "deletes": self.deletes,
            "evictions": self.evictions,
            "hit_rate": self.hit_rate,
            "total_operations": self.total_operations,
        }


@dataclass
class CacheEntry(Generic[T]):
    """缓存条目"""

    value: T
    expire_at: float | None = None

    def is_expired(self) -> bool:
        """检查是否过期"""
        if self.expire_at is None:
            return False
        return time.time() > self.expire_at


class MemoryCache(Generic[T]):
    """内存缓存（LRU + TTL）

    特性：
    - LRU 淘汰策略
    - TTL 过期机制
    - 缓存统计
    - 线程安全

    Args:
        maxsize: 最大缓存条目数
        ttl: 默认过期时间（秒），None 表示永不过期
    """

    def __init__(self, maxsize: int = 1000, ttl: int | None = 300):
        self.maxsize = maxsize
        self.ttl = ttl
        self.cache: OrderedDict[str, CacheEntry[T]] = OrderedDict()
        self.stats = CacheStats()
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> T | None:
        """获取缓存

        Args:
            key: 缓存键

        Returns:
            缓存值，如果不存在或已过期则返回 None
        """
        async with self._lock:
            entry = self.cache.get(key)

            if entry is None:
                self.stats.misses += 1
                return None

            # 检查是否过期
            if entry.is_expired():
                del self.cache[key]
                self.stats.misses += 1
                self.stats.evictions += 1
                return None

            # 移到末尾（LRU）
            self.cache.move_to_end(key)
            self.stats.hits += 1
            return entry.value

    async def set(
        self,
        key: str,
        value: T,
        ttl: int | None = None,
    ) -> None:
        """设置缓存

        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间（秒），None 使用默认 TTL
        """
        async with self._lock:
            # 计算过期时间
            expire_at = None
            if ttl is not None:
                expire_at = time.time() + ttl
            elif self.ttl is not None:
                expire_at = time.time() + self.ttl

            # 创建缓存条目
            entry = CacheEntry(value=value, expire_at=expire_at)

            # 如果已存在，先删除（会移到末尾）
            if key in self.cache:
                del self.cache[key]

            # 添加到末尾
            self.cache[key] = entry
            self.stats.sets += 1

            # 检查是否超过最大容量
            if len(self.cache) > self.maxsize:
                # 删除最旧的条目（第一个）
                self.cache.popitem(last=False)
                self.stats.evictions += 1

    async def delete(self, key: str) -> bool:
        """删除缓存

        Args:
            key: 缓存键

        Returns:
            是否删除成功
        """
        async with self._lock:
            if key in self.cache:
                del self.cache[key]
                self.stats.deletes += 1
                return True
            return False

    async def clear(self) -> None:
        """清空缓存"""
        async with self._lock:
            self.cache.clear()

    async def size(self) -> int:
        """获取缓存大小"""
        async with self._lock:
            return len(self.cache)

    async def get_stats(self) -> CacheStats:
        """获取统计信息"""
        return self.stats

    async def reset_stats(self) -> None:
        """重置统计信息"""
        self.stats.reset()


class RedisCache(Generic[T]):
    """Redis 缓存

    特性：
    - 异步操作
    - 连接池管理
    - 序列化/反序列化
    - 缓存统计

    Args:
        url: Redis 连接 URL
        ttl: 默认过期时间（秒）
        max_connections: 最大连接数
        decode_responses: 是否解码响应
    """

    def __init__(
        self,
        url: str = "redis://localhost:6379",
        ttl: int = 300,
        max_connections: int = 10,
        decode_responses: bool = True,
    ):
        if not REDIS_AVAILABLE:
            raise ImportError("redis-py is not installed")

        self.url = url
        self.ttl = ttl
        self.max_connections = max_connections
        self.decode_responses = decode_responses
        self.stats = CacheStats()

        # 创建连接池
        self.pool = aioredis.ConnectionPool.from_url(
            url,
            max_connections=max_connections,
            decode_responses=decode_responses,
        )
        self.client = aioredis.Redis(connection_pool=self.pool)

    async def get(self, key: str) -> T | None:
        """获取缓存

        Args:
            key: 缓存键

        Returns:
            缓存值，如果不存在则返回 None
        """
        try:
            value = await self.client.get(key)
            if value is not None:
                self.stats.hits += 1
                # 反序列化
                if isinstance(value, str):
                    return json.loads(value)
                return value
            else:
                self.stats.misses += 1
                return None
        except Exception as e:
            logger.error(f"Redis get error: {e}")
            self.stats.misses += 1
            return None

    async def set(
        self,
        key: str,
        value: T,
        ttl: int | None = None,
    ) -> bool:
        """设置缓存

        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间（秒），None 使用默认 TTL

        Returns:
            是否设置成功
        """
        try:
            # 序列化
            if not isinstance(value, (str, bytes, int, float)):
                value = json.dumps(value)

            # 设置缓存
            expire_time = ttl if ttl is not None else self.ttl
            await self.client.setex(key, expire_time, value)
            self.stats.sets += 1
            return True
        except Exception as e:
            logger.error(f"Redis set error: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """删除缓存

        Args:
            key: 缓存键

        Returns:
            是否删除成功
        """
        try:
            result = await self.client.delete(key)
            if result > 0:
                self.stats.deletes += 1
                return True
            return False
        except Exception as e:
            logger.error(f"Redis delete error: {e}")
            return False

    async def clear(self) -> None:
        """清空缓存（危险操作）"""
        try:
            await self.client.flushdb()
        except Exception as e:
            logger.error(f"Redis clear error: {e}")

    async def size(self) -> int:
        """获取缓存大小"""
        try:
            return await self.client.dbsize()
        except Exception as e:
            logger.error(f"Redis size error: {e}")
            return 0

    async def get_stats(self) -> CacheStats:
        """获取统计信息"""
        return self.stats

    async def reset_stats(self) -> None:
        """重置统计信息"""
        self.stats.reset()

    async def close(self) -> None:
        """关闭连接"""
        try:
            await self.client.aclose()
            await self.pool.aclose()
        except Exception as e:
            logger.error(f"Redis close error: {e}")


class MultiLevelCache(Generic[T]):
    """多层缓存（L1 + L2）

    特性：
    - L1: 内存缓存（快速访问）
    - L2: Redis 缓存（持久化）
    - 自动回填 L1
    - 统一的缓存接口

    Args:
        l1_maxsize: L1 最大缓存条目数
        l1_ttl: L1 过期时间（秒）
        l2_url: L2 Redis 连接 URL
        l2_ttl: L2 过期时间（秒）
        l2_enabled: 是否启用 L2
    """

    def __init__(
        self,
        l1_maxsize: int = 1000,
        l1_ttl: int = 60,
        l2_url: str = "redis://localhost:6379",
        l2_ttl: int = 300,
        l2_enabled: bool = True,
    ):
        # L1: 内存缓存
        self.l1 = MemoryCache[T](maxsize=l1_maxsize, ttl=l1_ttl)

        # L2: Redis 缓存
        self.l2: RedisCache[T] | None = None
        if l2_enabled and REDIS_AVAILABLE:
            try:
                self.l2 = RedisCache[T](url=l2_url, ttl=l2_ttl)
            except Exception as e:
                logger.warning(f"Failed to initialize Redis cache: {e}")

        self.stats = CacheStats()

    async def get(self, key: str) -> T | None:
        """获取缓存（L1 -> L2）

        Args:
            key: 缓存键

        Returns:
            缓存值，如果不存在则返回 None
        """
        # 先查 L1
        value = await self.l1.get(key)
        if value is not None:
            self.stats.hits += 1
            return value

        # 再查 L2
        if self.l2 is not None:
            value = await self.l2.get(key)
            if value is not None:
                # 回填 L1
                await self.l1.set(key, value)
                self.stats.hits += 1
                return value

        self.stats.misses += 1
        return None

    async def set(
        self,
        key: str,
        value: T,
        ttl: int | None = None,
    ) -> None:
        """设置缓存（L1 + L2）

        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间（秒），None 使用默认 TTL
        """
        # 设置 L1
        await self.l1.set(key, value, ttl=ttl)

        # 设置 L2
        if self.l2 is not None:
            await self.l2.set(key, value, ttl=ttl)

        self.stats.sets += 1

    async def delete(self, key: str) -> bool:
        """删除缓存（L1 + L2）

        Args:
            key: 缓存键

        Returns:
            是否删除成功
        """
        l1_deleted = await self.l1.delete(key)
        l2_deleted = False
        if self.l2 is not None:
            l2_deleted = await self.l2.delete(key)

        if l1_deleted or l2_deleted:
            self.stats.deletes += 1
            return True
        return False

    async def clear(self) -> None:
        """清空缓存（L1 + L2）"""
        await self.l1.clear()
        if self.l2 is not None:
            await self.l2.clear()

    async def size(self) -> tuple[int, int]:
        """获取缓存大小（L1, L2）"""
        l1_size = await self.l1.size()
        l2_size = 0
        if self.l2 is not None:
            l2_size = await self.l2.size()
        return l1_size, l2_size

    async def get_stats(self) -> dict[str, Any]:
        """获取统计信息"""
        l1_stats = await self.l1.get_stats()
        l2_stats = None
        if self.l2 is not None:
            l2_stats = await self.l2.get_stats()

        return {
            "total": self.stats.to_dict(),
            "l1": l1_stats.to_dict(),
            "l2": l2_stats.to_dict() if l2_stats else None,
        }

    async def reset_stats(self) -> None:
        """重置统计信息"""
        self.stats.reset()
        await self.l1.reset_stats()
        if self.l2 is not None:
            await self.l2.reset_stats()

    async def close(self) -> None:
        """关闭连接"""
        if self.l2 is not None:
            await self.l2.close()


# 便捷函数

async def create_memory_cache(
    maxsize: int = 1000,
    ttl: int | None = 300,
) -> MemoryCache:
    """创建内存缓存

    Args:
        maxsize: 最大缓存条目数
        ttl: 默认过期时间（秒）

    Returns:
        内存缓存实例
    """
    return MemoryCache(maxsize=maxsize, ttl=ttl)


async def create_redis_cache(
    url: str = "redis://localhost:6379",
    ttl: int = 300,
    max_connections: int = 10,
) -> RedisCache:
    """创建 Redis 缓存

    Args:
        url: Redis 连接 URL
        ttl: 默认过期时间（秒）
        max_connections: 最大连接数

    Returns:
        Redis 缓存实例
    """
    return RedisCache(url=url, ttl=ttl, max_connections=max_connections)


async def create_multi_level_cache(
    l1_maxsize: int = 1000,
    l1_ttl: int = 60,
    l2_url: str = "redis://localhost:6379",
    l2_ttl: int = 300,
    l2_enabled: bool = True,
) -> MultiLevelCache:
    """创建多层缓存

    Args:
        l1_maxsize: L1 最大缓存条目数
        l1_ttl: L1 过期时间（秒）
        l2_url: L2 Redis 连接 URL
        l2_ttl: L2 过期时间（秒）
        l2_enabled: 是否启用 L2

    Returns:
        多层缓存实例
    """
    return MultiLevelCache(
        l1_maxsize=l1_maxsize,
        l1_ttl=l1_ttl,
        l2_url=l2_url,
        l2_ttl=l2_ttl,
        l2_enabled=l2_enabled,
    )
