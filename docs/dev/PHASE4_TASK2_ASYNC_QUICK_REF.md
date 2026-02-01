# Phase 4 Task 2.4: 异步优化快速参考卡

## 快速概览

**任务**: Task 2.4 - 异步优化
**状态**: ✅ 完成
**日期**: 2026-02-01
**性能提升**: 批处理 **48.9倍**

## 核心组件

### 1. AsyncIOOptimizer - 异步 I/O 优化器

**创建优化器**:
```python
from lurkbot.utils.async_utils import AsyncIOOptimizer, AsyncIOConfig

config = AsyncIOConfig(max_concurrent_tasks=50)
optimizer = AsyncIOOptimizer(config)
```

**主要方法**:

| 方法 | 功能 | 示例 |
|------|------|------|
| `gather_with_limit()` | 限制并发执行 | `await optimizer.gather_with_limit(tasks)` |
| `batch_process()` | 批量处理 | `await optimizer.batch_process(items, processor)` |
| `retry_with_backoff()` | 重试机制 | `await optimizer.retry_with_backoff(task)` |
| `semaphore()` | 信号量控制 | `async with optimizer.semaphore(): ...` |

### 2. ConcurrencyController - 并发控制器

**创建控制器**:
```python
from lurkbot.utils.async_utils import ConcurrencyController

controller = ConcurrencyController(max_workers=10)
await controller.start()
```

**主要方法**:

| 方法 | 功能 | 示例 |
|------|------|------|
| `start()` | 启动控制器 | `await controller.start()` |
| `stop()` | 停止控制器 | `await controller.stop()` |
| `submit()` | 提交任务 | `await controller.submit(task)` |
| `acquire()` | 获取槽位 | `async with controller.acquire(): ...` |

### 3. 全局优化器

**使用全局优化器**:
```python
from lurkbot.utils.async_utils import get_global_optimizer

optimizer = get_global_optimizer()
results = await optimizer.gather_with_limit(tasks)
```

**自定义全局优化器**:
```python
from lurkbot.utils.async_utils import set_global_optimizer

custom_optimizer = AsyncIOOptimizer(custom_config)
set_global_optimizer(custom_optimizer)
```

## 配置选项

### AsyncIOConfig

```python
@dataclass
class AsyncIOConfig:
    # 并发控制
    max_concurrent_tasks: int = 100      # 最大并发任务数
    semaphore_timeout: float = 30.0      # 信号量超时（秒）

    # 批处理配置
    batch_size: int = 50                 # 批处理大小
    batch_timeout: float = 0.1           # 批处理超时（秒）

    # 重试配置
    max_retries: int = 3                 # 最大重试次数
    retry_delay: float = 1.0             # 重试延迟（秒）
    retry_backoff: float = 2.0           # 重试退避因子

    # 超时配置
    default_timeout: float = 30.0        # 默认超时（秒）
    gather_timeout: float | None = None  # gather 超时（None=无限制）
```

## 使用场景

### 场景 1: API 批量调用

```python
optimizer = AsyncIOOptimizer(AsyncIOConfig(max_concurrent_tasks=20))

async def fetch_api(url: str) -> dict:
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.json()

# 并发调用 API
urls = [f"https://api.example.com/data/{i}" for i in range(100)]
tasks = [fetch_api(url) for url in urls]
results = await optimizer.gather_with_limit(tasks)
```

### 场景 2: 数据库批量查询

```python
optimizer = AsyncIOOptimizer(AsyncIOConfig(batch_size=20))

async def query_batch(ids: list[int]) -> list[dict]:
    async with db.connection() as conn:
        return await conn.fetch_many(ids)

# 批量查询
ids = list(range(1000))
results = await optimizer.batch_process(ids, query_batch)
```

### 场景 3: 不稳定操作重试

```python
optimizer = AsyncIOOptimizer()

async def unstable_operation() -> dict:
    # 可能失败的操作
    response = await external_api.call()
    return response

# 自动重试
result = await optimizer.retry_with_backoff(
    unstable_operation,
    max_retries=5,
    retry_delay=2.0,
)
```

### 场景 4: 文件批量处理

```python
optimizer = AsyncIOOptimizer(AsyncIOConfig(max_concurrent_tasks=10))

async def process_file(filepath: str) -> str:
    async with aiofiles.open(filepath, 'r') as f:
        content = await f.read()
        return process_content(content)

# 并发处理文件
files = glob.glob("data/*.txt")
tasks = [process_file(f) for f in files]
results = await optimizer.gather_with_limit(tasks)
```

## 性能数据

### 批处理性能

| 场景 | 未优化 | 优化后 | 提升 |
|------|--------|--------|------|
| 500项顺序处理 | 580.96 ms | 11.89 ms | **48.9倍** |
| 1000项顺序处理 | ~1160 ms | ~24 ms | **48.3倍** |

### 并发执行性能

| 场景 | 并发数 | 平均耗时 | OPS |
|------|--------|---------|-----|
| 100任务 | 50 | ~3 ms | ~333 ops/s |
| 200任务 | 50 | ~6 ms | ~166 ops/s |
| 1000任务 | 50 | ~30 ms | ~33 ops/s |

### 真实场景模拟

| 场景 | 任务数 | 并发/批大小 | 性能 |
|------|--------|------------|------|
| API 调用 | 100 | 20 | 稳定可控 |
| 数据库查询 | 200 | 20 | 高效批量 |
| 文件操作 | 50 | 10 | I/O 优化明显 |
| 消息处理 | 300 | 30 | 批量高效 |

## 统计监控

### 获取统计信息

```python
# 获取统计
stats = optimizer.get_stats()

print(f"总任务数: {stats.total_tasks}")
print(f"完成任务数: {stats.completed_tasks}")
print(f"失败任务数: {stats.failed_tasks}")
print(f"平均耗时: {stats.avg_task_time:.3f}s")
print(f"最大并发: {stats.max_concurrent}")
print(f"重试次数: {stats.total_retries}")
print(f"重试成功: {stats.retry_success}")
```

### 重置统计

```python
optimizer.reset_stats()
```

## 最佳实践

### 1. 选择合适的并发数

```python
# CPU 密集型任务
config = AsyncIOConfig(max_concurrent_tasks=cpu_count())

# I/O 密集型任务
config = AsyncIOConfig(max_concurrent_tasks=100)

# 外部 API 调用（避免限流）
config = AsyncIOConfig(max_concurrent_tasks=10)
```

### 2. 选择合适的批处理大小

```python
# 小任务（快速执行）
config = AsyncIOConfig(batch_size=100)

# 中等任务
config = AsyncIOConfig(batch_size=50)

# 大任务（耗时较长）
config = AsyncIOConfig(batch_size=10)
```

### 3. 配置重试策略

```python
# 快速重试（网络抖动）
config = AsyncIOConfig(
    max_retries=3,
    retry_delay=0.5,
    retry_backoff=1.5,
)

# 慢速重试（服务恢复）
config = AsyncIOConfig(
    max_retries=5,
    retry_delay=5.0,
    retry_backoff=2.0,
)
```

### 4. 设置超时时间

```python
# 快速操作
config = AsyncIOConfig(
    default_timeout=5.0,
    gather_timeout=10.0,
)

# 慢速操作
config = AsyncIOConfig(
    default_timeout=60.0,
    gather_timeout=120.0,
)
```

## 常见问题

### Q1: 如何选择 AsyncIOOptimizer 还是 ConcurrencyController?

**AsyncIOOptimizer**:
- 适用于一次性批量任务
- 简单易用，无需管理生命周期
- 适合脚本和简单场景

**ConcurrencyController**:
- 适用于长期运行的服务
- 需要管理启动/停止
- 适合复杂的任务调度场景

### Q2: 并发数设置多少合适?

**经验法则**:
- CPU 密集型: `cpu_count()` 或 `cpu_count() * 2`
- I/O 密集型: `50-200`
- 外部 API: `10-50` (根据 API 限流策略)
- 数据库: `20-100` (根据连接池大小)

### Q3: 批处理大小如何选择?

**考虑因素**:
- 单个任务耗时: 越长，批大小越小
- 内存占用: 批大小不能太大
- 响应延迟: 批大小影响首个结果返回时间

**推荐值**:
- 快速任务 (<10ms): 50-100
- 中等任务 (10-100ms): 20-50
- 慢速任务 (>100ms): 5-20

### Q4: 如何处理异常?

**gather_with_limit**:
```python
# 返回异常
results = await optimizer.gather_with_limit(tasks, return_exceptions=True)
for result in results:
    if isinstance(result, Exception):
        logger.error(f"Task failed: {result}")

# 抛出异常
try:
    results = await optimizer.gather_with_limit(tasks)
except Exception as e:
    logger.error(f"Batch failed: {e}")
```

**retry_with_backoff**:
```python
try:
    result = await optimizer.retry_with_backoff(task)
except Exception as e:
    logger.error(f"All retries failed: {e}")
```

## 测试命令

### 运行单元测试

```bash
# 所有单元测试
uv run pytest tests/utils/test_async_utils.py -xvs

# 特定测试类
uv run pytest tests/utils/test_async_utils.py::TestAsyncIOOptimizer -xvs
```

### 运行性能测试

```bash
# 所有性能测试
uv run pytest tests/performance/test_async_performance.py --benchmark-only -v

# 对比测试
uv run pytest tests/performance/test_async_performance.py::TestAsyncIOComparison --benchmark-only -v

# 真实场景测试
uv run pytest tests/performance/test_async_performance.py::TestRealWorldScenarios --benchmark-only -v
```

## 相关文件

### 核心代码
- `src/lurkbot/utils/async_utils.py` - 异步工具模块

### 测试代码
- `tests/utils/test_async_utils.py` - 单元测试 (30 tests)
- `tests/performance/test_async_performance.py` - 性能测试 (17 tests)

### 文档
- `docs/dev/PHASE4_TASK2_ASYNC_OPTIMIZATION.md` - 详细报告
- `docs/dev/PHASE4_TASK2_ASYNC_QUICK_REF.md` - 本快速参考卡

## 下一步

- [ ] 集成到 Gateway 服务器
- [ ] 集成到 Agent API
- [ ] 集成到工具系统
- [ ] 添加性能监控
- [ ] 优化配置参数

---

**最后更新**: 2026-02-01
**版本**: v1.0
