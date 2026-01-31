# 性能测试文档

## 概述

本目录包含 LurkBot 的性能基准测试套件，用于测试和分析系统的性能表现。

## 测试覆盖

### 1. 消息处理性能 (`test_message_performance.py`)

测试 Gateway 消息发送/接收性能：

- **消息发送**: 单条消息、大型消息、批量消息
- **消息接收**: 单条消息、大型消息
- **JSON 操作**: 序列化/反序列化性能
- **并发处理**: 并发发送/接收
- **吞吐量**: 小/中/大规模消息吞吐量

### 2. Agent 运行性能 (`test_agent_performance.py`)

测试 Agent 执行和工具调用性能：

- **Agent 创建**: 基础 Agent、带工具的 Agent
- **工具调用**: 简单工具、异步工具、复杂工具
- **批量调用**: 批量工具调用、并发工具调用
- **上下文处理**: 上下文创建、依赖创建
- **历史记录**: 小/中/大规模历史记录处理

## 快速开始

### 安装依赖

```bash
# 安装性能测试依赖
uv add pytest-benchmark locust prometheus-client --dev
```

### 运行测试

#### 方式 1: 使用运行脚本 (推荐)

```bash
# 运行所有性能测试并生成报告
python tests/performance/run_tests.py
```

#### 方式 2: 使用 pytest 直接运行

```bash
# 运行所有性能测试
pytest tests/performance/ --benchmark-only -v

# 运行特定测试组
pytest tests/performance/ --benchmark-only --benchmark-group=message-send -v

# 保存结果到 JSON
pytest tests/performance/ --benchmark-only --benchmark-json=results.json -v

# 自动保存结果
pytest tests/performance/ --benchmark-only --benchmark-autosave -v
```

### 查看结果

性能测试结果会保存在 `tests/performance/reports/` 目录：

- `benchmark_results.json` - pytest-benchmark 原始结果
- `performance_report_YYYYMMDD_HHMMSS.json` - 结构化性能报告
- `performance_report_YYYYMMDD_HHMMSS.md` - Markdown 格式报告

## 性能指标

### 核心指标

| 指标 | 说明 | 单位 |
|------|------|------|
| **min_time** | 最小执行时间 | 秒 |
| **max_time** | 最大执行时间 | 秒 |
| **mean_time** | 平均执行时间 | 秒 |
| **median_time** | 中位数执行时间 | 秒 |
| **stddev** | 标准差 | 秒 |
| **ops_per_second** | 每秒操作数 | ops/s |
| **iterations** | 迭代次数 | 次 |

### 性能目标

| 测试组 | 目标 | 当前值 |
|--------|------|--------|
| 消息发送 | < 1ms | TBD |
| 消息接收 | < 1ms | TBD |
| JSON 序列化 | < 0.1ms | TBD |
| Agent 创建 | < 10ms | TBD |
| 工具调用 | < 1ms | TBD |
| 批量处理 (100) | < 100ms | TBD |

## 测试组说明

### message-send

测试消息发送性能：
- `test_send_json_performance` - 单条消息发送
- `test_send_large_json_performance` - 大型消息发送
- `test_send_batch_messages_performance` - 批量消息发送

### message-receive

测试消息接收性能：
- `test_receive_json_performance` - 单条消息接收
- `test_receive_large_json_performance` - 大型消息接收

### json-ops

测试 JSON 操作性能：
- `test_json_dumps_performance` - JSON 序列化
- `test_json_loads_performance` - JSON 反序列化
- `test_large_json_dumps_performance` - 大型 JSON 序列化
- `test_large_json_loads_performance` - 大型 JSON 反序列化

### concurrent

测试并发处理性能：
- `test_concurrent_send_performance` - 并发消息发送
- `test_concurrent_receive_performance` - 并发消息接收

### throughput

测试消息吞吐量：
- `test_message_throughput_small` - 小规模吞吐量 (100 条)
- `test_message_throughput_medium` - 中等规模吞吐量 (1000 条)
- `test_message_throughput_large` - 大规模吞吐量 (10000 条)

### agent-creation

测试 Agent 创建性能：
- `test_agent_creation_performance` - 基础 Agent 创建
- `test_agent_creation_with_tools_performance` - 带工具的 Agent 创建

### tool-call

测试工具调用性能：
- `test_simple_tool_call_performance` - 简单工具调用
- `test_async_tool_call_performance` - 异步工具调用
- `test_complex_tool_call_performance` - 复杂工具调用

### tool-batch

测试批量工具调用性能：
- `test_batch_tool_calls_performance` - 批量工具调用
- `test_concurrent_tool_calls_performance` - 并发工具调用

### context

测试上下文处理性能：
- `test_context_creation_performance` - 上下文创建
- `test_dependencies_creation_performance` - 依赖创建
- `test_dependencies_with_history_performance` - 带历史记录的依赖创建

### history

测试历史记录处理性能：
- `test_small_history_processing` - 小历史记录 (10 条)
- `test_medium_history_processing` - 中等历史记录 (100 条)
- `test_large_history_processing` - 大历史记录 (1000 条)

## 高级用法

### 比较性能

```bash
# 保存基线
pytest tests/performance/ --benchmark-only --benchmark-save=baseline

# 运行新测试并比较
pytest tests/performance/ --benchmark-only --benchmark-compare=baseline
```

### 自定义迭代次数

```bash
# 设置最小迭代次数
pytest tests/performance/ --benchmark-only --benchmark-min-rounds=100
```

### 禁用 GC

```bash
# 禁用垃圾回收以获得更稳定的结果
pytest tests/performance/ --benchmark-only --benchmark-disable-gc
```

### 生成直方图

```bash
# 生成性能直方图
pytest tests/performance/ --benchmark-only --benchmark-histogram
```

## 性能分析工具

### PerformanceTimer

用于手动计时：

```python
from tests.performance import PerformanceTimer

with PerformanceTimer() as timer:
    # 执行代码
    pass

print(f"Elapsed: {timer.elapsed:.4f}s")
```

### PerformanceReporter

用于生成报告：

```python
from tests.performance import PerformanceReporter, PerformanceReport

reporter = PerformanceReporter()
report = PerformanceReport(...)
reporter.save_report(report)
reporter.save_markdown_report(report)
```

## 最佳实践

### 1. 测试隔离

- 每个测试应该独立运行
- 使用 fixtures 准备测试数据
- 避免测试之间的依赖

### 2. 测试数据

- 使用真实的数据规模
- 测试边界情况（空数据、大数据）
- 使用多种数据类型

### 3. 性能目标

- 设定明确的性能目标
- 定期运行性能测试
- 跟踪性能趋势

### 4. 结果分析

- 关注平均值和中位数
- 注意标准差（稳定性）
- 比较不同版本的性能

## 故障排除

### 测试运行缓慢

- 减少迭代次数: `--benchmark-min-rounds=10`
- 只运行特定测试组: `--benchmark-group=message-send`
- 使用更快的机器

### 结果不稳定

- 禁用 GC: `--benchmark-disable-gc`
- 增加迭代次数: `--benchmark-min-rounds=1000`
- 关闭其他程序

### 内存不足

- 减少测试数据规模
- 分批运行测试
- 增加系统内存

## 参考资料

- [pytest-benchmark 文档](https://pytest-benchmark.readthedocs.io/)
- [Locust 文档](https://docs.locust.io/)
- [Python 性能优化指南](https://docs.python.org/3/howto/perf_profiling.html)

## 下一步

1. 运行基准测试建立性能基线
2. 识别性能瓶颈
3. 实施性能优化
4. 验证优化效果
5. 更新性能目标

---

**最后更新**: 2026-02-01
**维护者**: LurkBot Team
