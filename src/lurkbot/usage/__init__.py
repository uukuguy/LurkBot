"""Provider Usage 监控系统

实时追踪 AI 提供商使用量和成本

对标 MoltBot src/infra/provider-usage*

## 功能

1. **实时配额监控** - 追踪 API 使用量和限制
2. **成本估算** - 基于 token 使用量估算成本
3. **多提供商支持** - Anthropic, OpenAI, Google 等
4. **会话成本追踪** - 每会话和每日成本汇总

## 使用示例

```python
from lurkbot.usage import (
    load_provider_usage_summary,
    format_usage_summary_line,
    load_cost_usage_summary,
)

# 1. 获取实时使用量
summary = await load_provider_usage_summary()
print(format_usage_summary_line(summary))
# 输出: 📊 Usage: Claude 75% left (Week ⏱2h 30m) · Copilot 40% left (5h)

# 2. 加载成本汇总
cost_summary = await load_cost_usage_summary(
    sessions_dir=Path("~/.lurkbot/sessions"),
    days=30,
)
print(f"Total cost: {cost_summary.totals.total_cost:.2f} USD")
```

## 模块结构

- `types` - 数据类型定义
- `tracker` - 实时使用量跟踪
- `store` - 成本数据存储和加载
- `formatter` - 格式化输出
"""

from .formatter import (
    estimate_usage_cost,
    format_cost_usage_summary,
    format_provider_usage,
    format_reset_remaining,
    format_session_cost_summary,
    format_token_count,
    format_usage_report_lines,
    format_usage_summary_line,
    format_usd,
    format_window_usage,
)
from .store import (
    load_cost_usage_summary,
    load_session_cost_summary,
)
from .tracker import (
    fetch_anthropic_usage,
    get_credentials_from_env,
    load_provider_usage_summary,
)
from .types import (
    PROVIDER_LABELS,
    CostUsageDailyEntry,
    CostUsageSummary,
    CostUsageTotals,
    ModelCostConfig,
    NormalizedUsage,
    ProviderUsageSnapshot,
    SessionCostSummary,
    UsageProviderId,
    UsageSummary,
    UsageWindow,
    clamp_percent,
    normalize_usage,
)

__all__ = [
    # Types
    "UsageWindow",
    "ProviderUsageSnapshot",
    "UsageSummary",
    "UsageProviderId",
    "ModelCostConfig",
    "NormalizedUsage",
    "CostUsageTotals",
    "CostUsageDailyEntry",
    "CostUsageSummary",
    "SessionCostSummary",
    "PROVIDER_LABELS",
    # Tracker
    "load_provider_usage_summary",
    "fetch_anthropic_usage",
    "get_credentials_from_env",
    # Store
    "load_cost_usage_summary",
    "load_session_cost_summary",
    # Formatter
    "estimate_usage_cost",
    "format_usd",
    "format_token_count",
    "format_reset_remaining",
    "format_window_usage",
    "format_provider_usage",
    "format_usage_summary_line",
    "format_usage_report_lines",
    "format_cost_usage_summary",
    "format_session_cost_summary",
    # Utils
    "normalize_usage",
    "clamp_percent",
]
