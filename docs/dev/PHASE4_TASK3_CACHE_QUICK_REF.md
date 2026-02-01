# Phase 4 Task 3: 缓存策略快速参考卡

## 快速开始

### 1. 内存缓存（最简单）

```python
from lurkbot.utils.cache import MemoryCache

# 创建缓存
cache = MemoryCache[str](maxsize=1000, ttl=300)

# 使用缓存
await cache.set("key", "value")
value = await cache.get("key")
```

### 2. 多层缓存（推荐）

```python
from lurkbot.utils.cache import MultiLevelCache

# 创建缓存
cache = MultiLevelCache[str](
    l1_maxsize=1000,
    l1_ttl=60,
    l2_enabled=False,  # 暂时禁用 Redis
)

# 使用缓存
await cache.set("key", "value")
value = await cache.get("key")
```

## 核心 API

### MemoryCache

```python
# 创建
cache = MemoryCache[T](maxsize=1000, ttl=300)

# 操作
await cache.set(key, value, ttl=60)  # 设置
value = await cache.get(key)          # 获取
await cache.delete(key)               # 删除
await cache.clear()                   # 清空

# 统计
stats = await cache.get_stats()
print(f"命中率: {stats.hit_rate:.2%}")
```

### RedisCache

```python
# 创建
cache = RedisCache[T](
    url="redis://localhost:6379",
    ttl=300,
    max_connections=10,
)

# 操作（同 MemoryCache）
await cache.set(key, value, ttl=60)
value = await cache.get(key)

# 关闭
await cache.close()
```

### MultiLevelCache

```python
# 创建
cache = MultiLevelCache[T](
    l1_maxsize=1000,
    l1_ttl=60,
    l2_url="redis://localhost:6379",
    l2_ttl=300,
    l2_enabled=True,
)

# 操作（同 MemoryCache）
await cache.set(key, value)
value = await cache.get(key)

# 统计
stats = await cache.get_stats()
print(f"L1 命中率: {stats['l1']['hit_rate']:.2%}")
print(f"L2 命中率: {stats['l2']['hit_rate']:.2%}")
```

## 性能数据

### 基准测试结果

| 操作 | 时间 | 吞吐量 |
|------|------|--------|
| Set (1000 次) | 1.07 ms | 930 ops/s |
| Get (1000 次) | 0.73 ms | 1363 ops/s |
| Mixed (500 次) | 0.97 ms | 1036 ops/s |

### 性能提升

| 指标 | 数值 |
|------|------|
| 缓存命中性能提升 | **1264x** |
| 缓存命中率 | 75-100% |
| 性能开销 | 5.5x |

## 配置选项

### 环境变量

```bash
# L1 配置
export CACHE_L1_MAXSIZE=1000
export CACHE_L1_TTL=60

# L2 配置
export CACHE_L2_URL=redis://localhost:6379
export CACHE_L2_TTL=300
export CACHE_L2_ENABLED=true
export CACHE_L2_MAX_CONNECTIONS=10
```

### 代码配置

```python
from lurkbot.config.cache import CacheConfig

config = CacheConfig(
    l1_maxsize=1000,
    l1_ttl=60,
    l2_url="redis://localhost:6379",
    l2_ttl=300,
    l2_enabled=True,
)
```

## 使用场景

### 1. 用户会话缓存

```python
# 短 TTL，高频访问
cache = MemoryCache[dict](maxsize=10000, ttl=60)

await cache.set(f"session:{session_id}", session_data)
session = await cache.get(f"session:{session_id}")
```

### 2. API 响应缓存

```python
# 中 TTL，减少 API 调用
cache = MemoryCache[dict](maxsize=1000, ttl=300)

key = f"api:{endpoint}:{params_hash}"
response = await cache.get(key)
if response is None:
    response = await call_api(endpoint, params)
    await cache.set(key, response)
```

### 3. 配置缓存

```python
# 长 TTL，静态数据
cache = MemoryCache[dict](maxsize=100, ttl=3600)

config = await cache.get("app:config")
if config is None:
    config = await load_config()
    await cache.set("app:config", config)
```

### 4. 热点数据缓存

```python
# 多层缓存，L1 快速访问，L2 持久化
cache = MultiLevelCache[str](
    l1_maxsize=1000,
    l1_ttl=60,
    l2_ttl=300,
    l2_enabled=True,
)

# 热点数据自动在 L1 中
value = await cache.get("hot:key")
```

## 最佳实践

### 1. 选择合适的缓存类型

```python
# 小数据量，单机 → MemoryCache
cache = MemoryCache[str](maxsize=1000, ttl=300)

# 大数据量，分布式 → RedisCache
cache = RedisCache[str](url="redis://localhost:6379", ttl=300)

# 混合场景 → MultiLevelCache
cache = MultiLevelCache[str](l1_maxsize=1000, l1_ttl=60)
```

### 2. 设置合理的 TTL

```python
# 实时数据：短 TTL
cache = MemoryCache[str](ttl=30)

# 一般数据：中 TTL
cache = MemoryCache[str](ttl=300)

# 静态数据：长 TTL
cache = MemoryCache[str](ttl=3600)
```

### 3. 监控缓存性能

```python
# 定期检查
stats = await cache.get_stats()

if stats.hit_rate < 0.8:
    logger.warning(f"命中率过低: {stats.hit_rate:.2%}")

if stats.evictions > 1000:
    logger.warning(f"淘汰过多: {stats.evictions}")
```

### 4. 处理缓存穿透

```python
# 缓存空值
value = await cache.get(key)
if value is None:
    value = await fetch_from_db(key)
    if value is None:
        await cache.set(key, "NULL", ttl=60)
    else:
        await cache.set(key, value)
```

### 5. 使用随机 TTL 防止雪崩

```python
import random

ttl = 300 + random.randint(0, 60)
await cache.set(key, value, ttl=ttl)
```

## 测试命令

```bash
# 运行单元测试
uv run pytest tests/utils/test_cache.py -xvs

# 运行性能测试
uv run pytest tests/performance/test_cache_performance.py --benchmark-only -v

# 运行命中率测试
uv run pytest tests/performance/test_cache_performance.py::TestCacheHitRateScenarios -xvs

# 运行性能对比测试
uv run pytest tests/performance/test_cache_performance.py::TestCachePerformanceComparison -xvs
```

## 常见问题

### Q1: Redis 连接失败怎么办？

```python
# 禁用 L2，仅使用 L1
cache = MultiLevelCache[str](
    l1_maxsize=1000,
    l1_ttl=60,
    l2_enabled=False,  # 禁用 Redis
)
```

### Q2: 如何清空所有缓存？

```python
# 清空缓存
await cache.clear()

# 重置统计
await cache.reset_stats()
```

### Q3: 如何查看缓存大小？

```python
# MemoryCache
size = await cache.size()

# MultiLevelCache
l1_size, l2_size = await cache.size()
```

### Q4: 如何设置不过期的缓存？

```python
# 设置 ttl=None
cache = MemoryCache[str](maxsize=1000, ttl=None)
await cache.set("key", "value")  # 永不过期
```

### Q5: 如何处理序列化错误？

```python
# Redis 缓存仅支持 JSON 序列化
# 不支持复杂对象，需要转换为字典

# 错误示例
class User:
    pass
await cache.set("user", User())  # 错误！

# 正确示例
user_dict = {"id": 123, "name": "John"}
await cache.set("user", user_dict)  # 正确
```

## 性能优化技巧

### 1. 批量操作

```python
# 使用 asyncio.gather 并发操作
keys = [f"key{i}" for i in range(100)]
values = await asyncio.gather(*[cache.get(key) for key in keys])
```

### 2. 预热缓存

```python
# 启动时预热热点数据
async def warmup():
    hot_keys = await get_hot_keys()
    for key in hot_keys:
        value = await fetch_from_db(key)
        await cache.set(key, value)
```

### 3. 使用合适的 maxsize

```python
# 根据内存大小设置
# 假设每个条目 1KB，可用内存 100MB
maxsize = 100 * 1024 // 1  # 100000 条
cache = MemoryCache[str](maxsize=maxsize)
```

### 4. 监控和调优

```python
# 定期输出统计
async def monitor():
    while True:
        stats = await cache.get_stats()
        logger.info(f"缓存统计: {stats.to_dict()}")
        await asyncio.sleep(60)
```

## 文件位置

| 文件 | 说明 |
|------|------|
| `src/lurkbot/utils/cache.py` | 缓存工具模块 |
| `src/lurkbot/config/cache.py` | 缓存配置模块 |
| `tests/utils/test_cache.py` | 单元测试 |
| `tests/performance/test_cache_performance.py` | 性能测试 |
| `docs/dev/PHASE4_TASK3_CACHE_OPTIMIZATION.md` | 优化报告 |

## 相关文档

- [Phase 4 实施计划](PHASE4_PERFORMANCE_PLAN.md)
- [性能基线报告](PHASE4_TASK1_PERFORMANCE_BASELINE.md)
- [JSON 优化报告](PHASE4_TASK2_JSON_OPTIMIZATION.md)
- [批处理优化报告](PHASE4_TASK2_BATCHING_OPTIMIZATION.md)
- [连接池优化报告](PHASE4_TASK2_CONNECTION_POOL_OPTIMIZATION.md)
- [异步优化报告](PHASE4_TASK2_ASYNC_OPTIMIZATION.md)

---

**最后更新**: 2026-02-01
**版本**: v1.0
