# 租户监控系统设计文档

## 概述

本文档描述 LurkBot 租户监控系统的设计和实现，包括租户使用统计仪表板、实时监控和趋势分析功能。

## 系统架构

### 核心组件

```
┌─────────────────────────────────────────────────────────────────┐
│                      租户监控系统                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────┐ │
│  │  TenantStats    │    │  API Router     │    │  Dashboard  │ │
│  │  Service        │◄───│  (FastAPI)      │◄───│  Frontend   │ │
│  └────────┬────────┘    └─────────────────┘    └─────────────┘ │
│           │                                                     │
│           ▼                                                     │
│  ┌─────────────────┐    ┌─────────────────┐                    │
│  │  QuotaManager   │    │  TenantStorage  │                    │
│  │  (实时数据)     │    │  (历史数据)     │                    │
│  └─────────────────┘    └─────────────────┘                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 数据流

1. **实时数据流**：QuotaManager → TenantStatsService → API → 前端
2. **历史数据流**：TenantStorage → TenantStatsService → API → 前端
3. **聚合数据流**：原始数据 → 聚合计算 → 趋势分析 → 可视化

## 数据模型

### 统计周期 (StatsPeriod)

```python
class StatsPeriod(str, Enum):
    HOURLY = "hourly"    # 按小时
    DAILY = "daily"      # 按天
    WEEKLY = "weekly"    # 按周
    MONTHLY = "monthly"  # 按月
```

### 趋势方向 (TrendDirection)

```python
class TrendDirection(str, Enum):
    UP = "up"        # 上升
    DOWN = "down"    # 下降
    STABLE = "stable" # 稳定
```

### 配额使用统计 (QuotaUsageStats)

```python
class QuotaUsageStats(BaseModel):
    quota_type: QuotaType      # 配额类型
    current: float             # 当前使用量
    limit: float               # 配额限制
    percentage: float          # 使用百分比
    status: str                # 状态 (ok/warning/exceeded)
    trend: TrendDirection      # 趋势
    trend_percentage: float    # 趋势变化百分比
```

### 租户概览 (TenantOverview)

```python
class TenantOverview(BaseModel):
    tenant_id: str
    tenant_name: str
    display_name: str
    status: TenantStatus
    tier: TenantTier
    created_at: datetime

    # 实时统计
    active_sessions: int
    concurrent_requests: int
    api_calls_today: int
    tokens_today: int

    # 配额使用
    quota_usage: list[QuotaUsageStats]

    # 活跃度
    activity_score: float      # 0-100
    last_activity: datetime | None
```

### 使用量趋势 (UsageTrend)

```python
class UsageTrend(BaseModel):
    quota_type: QuotaType
    period: StatsPeriod
    data_points: list[UsageDataPoint]
    average: float
    max_value: float
    min_value: float
    trend: TrendDirection
    trend_percentage: float
```

### 租户仪表板 (TenantDashboard)

```python
class TenantDashboard(BaseModel):
    tenant_id: str
    generated_at: datetime
    overview: TenantOverview
    realtime_usage: dict[str, QuotaUsageStats]
    usage_trends: dict[str, UsageTrend]
    recent_events: list[TenantEvent]
    alerts: list[dict[str, Any]]
```

### 系统概览 (SystemOverview)

```python
class SystemOverview(BaseModel):
    generated_at: datetime

    # 租户统计
    total_tenants: int
    active_tenants: int
    trial_tenants: int
    suspended_tenants: int

    # 套餐分布
    tier_distribution: dict[str, int]

    # 使用统计
    total_api_calls_today: int
    total_tokens_today: int
    total_active_sessions: int

    # 配额告警
    tenants_near_quota: list[str]
    tenants_exceeded_quota: list[str]

    # 活跃度排名
    top_active_tenants: list[TenantOverview]
```

## API 端点

### 租户统计端点

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/v1/tenants/{tenant_id}/stats` | GET | 获取租户统计概览 |
| `/api/v1/tenants/{tenant_id}/dashboard` | GET | 获取租户仪表板数据 |
| `/api/v1/tenants/{tenant_id}/usage/realtime` | GET | 获取实时使用量 |
| `/api/v1/tenants/{tenant_id}/usage/history` | GET | 获取历史使用量 |
| `/api/v1/tenants/{tenant_id}/quota/trends` | GET | 获取配额消耗趋势 |
| `/api/v1/tenants/overview` | GET | 获取系统概览（管理员） |

### 请求参数

#### GET /api/v1/tenants/{tenant_id}/dashboard

| 参数 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| include_trends | bool | true | 是否包含趋势数据 |
| trend_period | string | "daily" | 趋势周期 |
| trend_days | int | 7 | 趋势天数 (1-90) |

#### GET /api/v1/tenants/{tenant_id}/usage/history

| 参数 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| period | string | "daily" | 统计周期 |
| days | int | 30 | 天数 (1-365) |

## 核心算法

### 活跃度评分算法

活跃度评分基于过去 7 天的使用数据，采用加权计算：

```python
ACTIVITY_WEIGHTS = {
    "api_calls": 0.3,    # API 调用权重
    "tokens": 0.3,       # Token 使用权重
    "sessions": 0.2,     # 会话创建权重
    "messages": 0.2,     # 消息发送权重
}

# 归一化基准值（每日）
daily_api_baseline = 100
daily_token_baseline = 10000
daily_session_baseline = 10
daily_message_baseline = 50

# 计算各维度得分
api_score = min(total_api_calls / (daily_api_baseline * 7), 1.0)
token_score = min(total_tokens / (daily_token_baseline * 7), 1.0)
session_score = min(total_sessions / (daily_session_baseline * 7), 1.0)
message_score = min(total_messages / (daily_message_baseline * 7), 1.0)

# 加权计算最终得分 (0-100)
score = (
    api_score * 0.3 +
    token_score * 0.3 +
    session_score * 0.2 +
    message_score * 0.2
) * 100
```

### 趋势计算算法

趋势计算比较数据序列的前半部分和后半部分的平均值：

```python
TREND_THRESHOLD = 0.05  # 5% 变化视为趋势

def calculate_trend(values: list[float]) -> tuple[TrendDirection, float]:
    if len(values) < 2:
        return TrendDirection.STABLE, 0.0

    mid = len(values) // 2
    first_avg = sum(values[:mid]) / mid
    second_avg = sum(values[mid:]) / (len(values) - mid)

    if first_avg == 0:
        return TrendDirection.UP if second_avg > 0 else TrendDirection.STABLE, 0.0

    change = (second_avg - first_avg) / first_avg

    if change > TREND_THRESHOLD:
        return TrendDirection.UP, change * 100
    elif change < -TREND_THRESHOLD:
        return TrendDirection.DOWN, abs(change) * 100
    else:
        return TrendDirection.STABLE, abs(change) * 100
```

## 使用示例

### 配置统计服务

```python
from lurkbot.tenants import (
    MemoryTenantStorage,
    QuotaManager,
    configure_stats_service,
)

# 创建依赖
storage = MemoryTenantStorage()
quota_manager = QuotaManager()

# 配置统计服务
stats_service = configure_stats_service(storage, quota_manager)
```

### 集成到 FastAPI 应用

```python
from fastapi import FastAPI
from lurkbot.tenants import create_tenant_stats_router

app = FastAPI()

# 添加租户统计路由
router = create_tenant_stats_router()
app.include_router(router)
```

### 获取租户仪表板

```python
from lurkbot.tenants import get_stats_service

stats_service = get_stats_service()

# 获取仪表板数据
dashboard = await stats_service.get_tenant_dashboard(
    tenant_id="tenant-1",
    include_trends=True,
    trend_period=StatsPeriod.DAILY,
    trend_days=7,
)

# 访问数据
print(f"活跃度评分: {dashboard.overview.activity_score}")
print(f"今日 API 调用: {dashboard.overview.api_calls_today}")
print(f"告警数量: {len(dashboard.alerts)}")
```

### 获取系统概览

```python
# 获取系统概览（管理员视图）
overview = await stats_service.get_system_overview()

print(f"总租户数: {overview.total_tenants}")
print(f"活跃租户数: {overview.active_tenants}")
print(f"接近配额限制的租户: {overview.tenants_near_quota}")
print(f"超出配额的租户: {overview.tenants_exceeded_quota}")
```

## 文件结构

```
src/lurkbot/tenants/
├── stats.py          # 统计服务核心实现
├── api.py            # FastAPI 路由端点
├── models.py         # 数据模型（已有）
├── quota.py          # 配额管理（已有）
├── storage.py        # 存储层（已有）
└── __init__.py       # 模块导出

tests/
├── tenants/
│   └── test_stats.py           # 统计服务单元测试
└── integration/
    └── test_stats_api.py       # API 集成测试
```

## 测试覆盖

### 单元测试 (25 个)

- 租户概览测试 (4 个)
- 仪表板测试 (5 个)
- 使用量趋势测试 (3 个)
- 系统概览测试 (3 个)
- 数据聚合测试 (2 个)
- 趋势计算测试 (4 个)
- 活跃度评分测试 (2 个)
- 全局配置测试 (2 个)

### 集成测试 (14 个)

- 租户统计端点测试 (2 个)
- 仪表板端点测试 (5 个)
- 实时使用量端点测试 (2 个)
- 历史使用量端点测试 (2 个)
- 配额趋势端点测试 (1 个)
- 系统概览端点测试 (2 个)

## 后续优化方向

### Phase 7 Task 2: 告警系统

- 配额即将超限告警
- 异常使用模式检测
- 租户状态变更通知
- 告警通知渠道（邮件、钉钉、飞书）

### Phase 7 Task 3: 审计日志增强

- 详细操作日志
- 策略评估追踪
- 合规报告生成
- 日志导出功能

### 性能优化

- 统计数据缓存
- 异步数据聚合
- 增量更新机制
- 数据压缩存储

---

**文档版本**: 1.0
**创建日期**: 2026-02-01
**最后更新**: 2026-02-01
