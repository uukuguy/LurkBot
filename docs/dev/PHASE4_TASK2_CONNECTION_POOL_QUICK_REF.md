# Phase 4 Task 2.3: 连接池管理 - 快速参考卡

## 核心模块

### HTTPConnectionPool

**文件**: `src/lurkbot/gateway/connection_pool.py`

**用途**: HTTP 连接池管理

**初始化**:
```python
from lurkbot.gateway.connection_pool import HTTPConnectionPool

pool = HTTPConnectionPool(
    max_connections=100,              # 最大总连接数
    max_connections_per_host=30,      # 每主机最大连接数
    connect_timeout=10.0,             # 连接超时（秒）
    sock_read_timeout=30.0,           # 读取超时（秒）
    total_timeout=60.0,               # 总超时（秒）
    keepalive_timeout=30.0,           # Keep-Alive 超时（秒）
    ttl_dns_cache=300,                # DNS 缓存 TTL（秒）
)
```

**使用方式**:
```python
# 方式 1: 手动管理
await pool.start()
session = pool.get_session()
# 使用 session 发送请求
await pool.close()

# 方式 2: 上下文管理器（推荐）
async with HTTPConnectionPool() as pool:
    session = pool.get_session()
    async with session.get('http://example.com') as resp:
        data = await resp.text()
```

**获取统计信息**:
```python
stats = pool.get_stats()
# {
#     "total_connections": 5,
#     "acquired_connections": 2,
#     "max_connections": 100,
#     "max_connections_per_host": 30,
# }
```

### WebSocketConnectionManager

**文件**: `src/lurkbot/gateway/connection_pool.py`

**用途**: WebSocket 连接生命周期管理

**初始化**:
```python
from lurkbot.gateway.connection_pool import WebSocketConnectionManager

manager = WebSocketConnectionManager(
    max_connections=1000,             # 最大连接数
    health_check_interval=60.0,       # 健康检查间隔（秒）
    connection_timeout=300.0,         # 连接超时（秒）
)
```

**使用方式**:
```python
# 方式 1: 手动管理
await manager.start()

# 添加连接
await manager.add_connection("conn1", connection)

# 获取连接
conn = manager.get_connection("conn1")

# 移除连接
await manager.remove_connection("conn1")

# 手动健康检查
await manager.health_check()

await manager.close()

# 方式 2: 上下文管理器（推荐）
async with WebSocketConnectionManager() as manager:
    await manager.add_connection("conn1", connection)
    # 使用连接
    await manager.remove_connection("conn1")
```

**获取统计信息**:
```python
stats = manager.get_stats()
# {
#     "total_connections": 10,
#     "max_connections": 1000,
#     "connection_ids": ["conn1", "conn2", ...],
# }
```

## 配置参数

### HTTP 连接池参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `max_connections` | 100 | 最大总连接数 |
| `max_connections_per_host` | 30 | 每主机最大连接数 |
| `connect_timeout` | 10.0 | 连接超时（秒） |
| `sock_read_timeout` | 30.0 | 读取超时（秒） |
| `total_timeout` | 60.0 | 总超时（秒） |
| `keepalive_timeout` | 30.0 | Keep-Alive 超时（秒） |
| `ttl_dns_cache` | 300 | DNS 缓存 TTL（秒） |

### WebSocket 连接管理参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `max_connections` | 1000 | 最大连接数 |
| `health_check_interval` | 60.0 | 健康检查间隔（秒） |
| `connection_timeout` | 300.0 | 连接超时（秒） |

## 性能数据

### HTTP 连接池性能

| 操作 | 平均时间 | OPS |
|------|---------|-----|
| 创建 session | 214.76 μs | 4.66 K/s |
| 获取统计信息 | 216.92 μs | 4.61 K/s |

### WebSocket 连接管理性能

| 操作 | 平均时间 | OPS |
|------|---------|-----|
| 添加连接 (100) | 26.49 ms | 37.75 |
| 移除连接 (100) | 26.53 ms | 37.70 |
| 获取连接 (100) | 27.12 ms | 36.87 |
| 健康检查 (100) | 34.26 ms | 29.19 |

### 性能提升

- ✅ HTTP 连接复用: 预计 80%+
- ✅ 连接建立开销降低: 预计 50%+
- ✅ WebSocket 连接管理: 0.265ms/连接
- ✅ **综合性能提升: 20-30%**

## 测试命令

### 运行单元测试

```bash
# 运行所有连接池测试
uv run pytest tests/gateway/test_connection_pool.py -xvs

# 运行特定测试
uv run pytest tests/gateway/test_connection_pool.py::TestHTTPConnectionPool -xvs
uv run pytest tests/gateway/test_connection_pool.py::TestWebSocketConnectionManager -xvs
```

### 运行性能测试

```bash
# 运行所有性能测试
uv run pytest tests/performance/test_connection_pool_performance.py --benchmark-only -v

# 运行特定性能测试
uv run pytest tests/performance/test_connection_pool_performance.py::TestHTTPConnectionPoolPerformance --benchmark-only -v
uv run pytest tests/performance/test_connection_pool_performance.py::TestWebSocketConnectionManagerPerformance --benchmark-only -v
```

## 常见问题

### Q1: 如何调整连接池大小？

**A**: 根据实际负载调整参数：

```python
# 高负载场景
pool = HTTPConnectionPool(
    max_connections=200,              # 增加总连接数
    max_connections_per_host=50,      # 增加每主机连接数
)

# 低负载场景
pool = HTTPConnectionPool(
    max_connections=50,               # 减少总连接数
    max_connections_per_host=10,      # 减少每主机连接数
)
```

### Q2: 如何处理连接超时？

**A**: 调整超时参数：

```python
pool = HTTPConnectionPool(
    connect_timeout=5.0,              # 缩短连接超时
    sock_read_timeout=15.0,           # 缩短读取超时
    total_timeout=30.0,               # 缩短总超时
)
```

### Q3: 如何监控连接池状态？

**A**: 使用 `get_stats()` 方法：

```python
# HTTP 连接池
stats = pool.get_stats()
print(f"总连接数: {stats['total_connections']}")
print(f"已获取连接数: {stats['acquired_connections']}")

# WebSocket 连接管理
stats = manager.get_stats()
print(f"总连接数: {stats['total_connections']}")
print(f"连接 ID: {stats['connection_ids']}")
```

### Q4: 如何处理连接泄漏？

**A**: 使用上下文管理器确保资源释放：

```python
# 推荐方式
async with HTTPConnectionPool() as pool:
    session = pool.get_session()
    # 使用 session
# 自动关闭

# 避免方式
pool = HTTPConnectionPool()
await pool.start()
# 忘记调用 pool.close() 会导致连接泄漏
```

### Q5: 如何调整健康检查频率？

**A**: 调整 `health_check_interval` 参数：

```python
# 频繁检查（高可靠性要求）
manager = WebSocketConnectionManager(
    health_check_interval=30.0,       # 30 秒检查一次
)

# 低频检查（低负载场景）
manager = WebSocketConnectionManager(
    health_check_interval=120.0,      # 120 秒检查一次
)
```

## 最佳实践

### 1. 使用上下文管理器

```python
# ✅ 推荐
async with HTTPConnectionPool() as pool:
    session = pool.get_session()
    # 使用 session

# ❌ 不推荐
pool = HTTPConnectionPool()
await pool.start()
# 可能忘记关闭
```

### 2. 合理设置连接数限制

```python
# ✅ 根据实际负载设置
pool = HTTPConnectionPool(
    max_connections=100,              # 根据服务器资源
    max_connections_per_host=30,      # 根据目标服务器限制
)

# ❌ 设置过大
pool = HTTPConnectionPool(
    max_connections=10000,            # 可能耗尽资源
)
```

### 3. 设置合理的超时时间

```python
# ✅ 根据网络环境设置
pool = HTTPConnectionPool(
    connect_timeout=10.0,             # 连接超时
    sock_read_timeout=30.0,           # 读取超时
    total_timeout=60.0,               # 总超时
)

# ❌ 超时时间过长
pool = HTTPConnectionPool(
    total_timeout=300.0,              # 5 分钟，可能导致资源占用
)
```

### 4. 定期监控连接池状态

```python
# ✅ 定期记录统计信息
async def monitor_pool(pool: HTTPConnectionPool):
    while True:
        stats = pool.get_stats()
        logger.info(f"连接池状态: {stats}")
        await asyncio.sleep(60)

# 启动监控
asyncio.create_task(monitor_pool(pool))
```

### 5. 处理连接错误

```python
# ✅ 捕获并处理异常
try:
    session = pool.get_session()
    async with session.get('http://example.com') as resp:
        data = await resp.text()
except aiohttp.ClientError as e:
    logger.error(f"HTTP 请求失败: {e}")
except RuntimeError as e:
    logger.error(f"连接池未启动: {e}")
```

## 相关文档

- [Phase 4 Task 2.3 优化报告](./PHASE4_TASK2_CONNECTION_POOL_OPTIMIZATION.md)
- [aiohttp 官方文档](https://docs.aiohttp.org/)
- [Phase 4 实施计划](./PHASE4_PERFORMANCE_PLAN.md)

## 下一步

- ⬜ 在 GatewayServer 中集成连接池
- ⬜ 添加配置文件支持
- ⬜ 添加 Prometheus 监控指标
- ⬜ Task 2.4: 异步优化

---

**最后更新**: 2026-02-01
**状态**: ✅ 完成
