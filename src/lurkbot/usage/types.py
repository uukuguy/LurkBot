"""Provider Usage Types

使用量监控的数据类型定义

对标 MoltBot:
- src/infra/provider-usage.types.ts
- src/infra/session-cost-usage.ts
- src/agents/usage.ts
"""

from dataclasses import dataclass
from typing import Literal


# ============================================================================
# Provider Usage Types (实时配额监控)
# ============================================================================

@dataclass
class UsageWindow:
    """使用量窗口

    表示一个时间窗口内的使用量百分比和重置时间。

    对标: UsageWindow in provider-usage.types.ts
    """
    label: str                   # 窗口标签，如 "5h", "Week", "Sonnet", "Opus"
    used_percent: float          # 已使用百分比 (0-100)
    reset_at: int | None = None  # 重置时间 (Unix 时间戳毫秒)


@dataclass
class ProviderUsageSnapshot:
    """提供商使用量快照

    对标: ProviderUsageSnapshot in provider-usage.types.ts
    """
    provider: str                    # 提供商 ID
    display_name: str                # 显示名称
    windows: list[UsageWindow]       # 使用量窗口列表
    plan: str | None = None          # 套餐名称 (如 "Pro", "Plus")
    error: str | None = None         # 错误信息（如果获取失败）


@dataclass
class UsageSummary:
    """使用量汇总

    对标: UsageSummary in provider-usage.types.ts
    """
    updated_at: int                      # 更新时间 (Unix 时间戳毫秒)
    providers: list[ProviderUsageSnapshot]  # 提供商快照列表


# 支持的提供商 ID
UsageProviderId = Literal[
    "anthropic",           # Claude (Anthropic)
    "github-copilot",      # GitHub Copilot
    "google-gemini-cli",   # Google Gemini CLI
    "google-antigravity",  # Google Antigravity
    "minimax",             # MiniMax
    "openai-codex",        # OpenAI Codex
    "zai",                 # z.ai
]


# 提供商显示名称映射
PROVIDER_LABELS: dict[UsageProviderId, str] = {
    "anthropic": "Claude",
    "github-copilot": "Copilot",
    "google-gemini-cli": "Gemini",
    "google-antigravity": "Antigravity",
    "minimax": "MiniMax",
    "openai-codex": "Codex",
    "zai": "z.ai",
}


# ============================================================================
# Cost Tracking Types (成本估算)
# ============================================================================

@dataclass
class ModelCostConfig:
    """模型成本配置

    每百万 token 的成本 (USD)

    对标: ModelCostConfig in usage-format.ts
    """
    input: float        # 输入 token 成本 (per 1M tokens)
    output: float       # 输出 token 成本 (per 1M tokens)
    cache_read: float   # 缓存读取成本 (per 1M tokens)
    cache_write: float  # 缓存写入成本 (per 1M tokens)


@dataclass
class NormalizedUsage:
    """归一化的使用量数据

    对标: NormalizedUsage in agents/usage.ts
    """
    input: int | None = None          # 输入 token 数
    output: int | None = None         # 输出 token 数
    cache_read: int | None = None     # 缓存读取 token 数
    cache_write: int | None = None    # 缓存写入 token 数
    total: int | None = None          # 总 token 数


@dataclass
class CostUsageTotals:
    """成本使用量合计

    对标: CostUsageTotals in session-cost-usage.ts
    """
    input: int = 0                    # 输入 token 总数
    output: int = 0                   # 输出 token 总数
    cache_read: int = 0               # 缓存读取 token 总数
    cache_write: int = 0              # 缓存写入 token 总数
    total_tokens: int = 0             # 总 token 数
    total_cost: float = 0.0           # 总成本 (USD)
    missing_cost_entries: int = 0     # 缺失成本信息的条目数


@dataclass
class CostUsageDailyEntry:
    """每日成本使用量条目

    对标: CostUsageDailyEntry in session-cost-usage.ts
    """
    date: str                         # 日期 (ISO 格式: YYYY-MM-DD)
    input: int = 0
    output: int = 0
    cache_read: int = 0
    cache_write: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0
    missing_cost_entries: int = 0


@dataclass
class CostUsageSummary:
    """成本使用量汇总

    对标: CostUsageSummary in session-cost-usage.ts
    """
    updated_at: int                      # 更新时间 (Unix 时间戳毫秒)
    days: int                            # 汇总天数
    daily: list[CostUsageDailyEntry]     # 每日使用量列表
    totals: CostUsageTotals              # 总计


@dataclass
class SessionCostSummary:
    """会话成本汇总

    对标: SessionCostSummary in session-cost-usage.ts
    """
    session_id: str | None = None
    session_file: str | None = None
    last_activity: int | None = None     # 最后活动时间 (Unix 时间戳毫秒)
    input: int = 0
    output: int = 0
    cache_read: int = 0
    cache_write: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0
    missing_cost_entries: int = 0


# ============================================================================
# Usage Normalization Support (使用量归一化支持)
# ============================================================================

class UsageLike:
    """类似使用量的数据结构

    支持多种 SDK 的命名约定 (OpenAI, Anthropic, Google 等)

    对标: UsageLike in agents/usage.ts
    """
    # 标准命名
    input: int | None = None
    output: int | None = None
    cache_read: int | None = None
    cache_write: int | None = None
    total: int | None = None

    # OpenAI SDK 命名
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None

    # Anthropic SDK 命名 (snake_case)
    input_tokens: int | None = None
    output_tokens: int | None = None
    cache_read_input_tokens: int | None = None
    cache_creation_input_tokens: int | None = None

    # 其他变体
    inputTokens: int | None = None
    outputTokens: int | None = None


def normalize_usage(raw: dict | UsageLike | None) -> NormalizedUsage:
    """归一化使用量数据

    将各种 SDK 的使用量数据归一化为标准格式。

    对标: normalizeUsage() in agents/usage.ts

    Args:
        raw: 原始使用量数据 (支持多种命名约定)

    Returns:
        归一化的使用量数据
    """
    if raw is None:
        return NormalizedUsage()

    if isinstance(raw, dict):
        # 从字典中提取
        input_val = (
            raw.get("input") or
            raw.get("input_tokens") or
            raw.get("inputTokens") or
            raw.get("prompt_tokens") or
            raw.get("promptTokens")
        )

        output_val = (
            raw.get("output") or
            raw.get("output_tokens") or
            raw.get("outputTokens") or
            raw.get("completion_tokens") or
            raw.get("completionTokens")
        )

        cache_read_val = (
            raw.get("cache_read") or
            raw.get("cacheRead") or
            raw.get("cache_read_input_tokens") or
            raw.get("cacheReadInputTokens")
        )

        cache_write_val = (
            raw.get("cache_write") or
            raw.get("cacheWrite") or
            raw.get("cache_creation_input_tokens") or
            raw.get("cacheCreationInputTokens")
        )

        total_val = (
            raw.get("total") or
            raw.get("total_tokens") or
            raw.get("totalTokens")
        )
    else:
        # 从对象属性中提取
        input_val = getattr(raw, "input", None) or getattr(raw, "input_tokens", None) or getattr(raw, "prompt_tokens", None)
        output_val = getattr(raw, "output", None) or getattr(raw, "output_tokens", None) or getattr(raw, "completion_tokens", None)
        cache_read_val = getattr(raw, "cache_read", None) or getattr(raw, "cache_read_input_tokens", None)
        cache_write_val = getattr(raw, "cache_write", None) or getattr(raw, "cache_creation_input_tokens", None)
        total_val = getattr(raw, "total", None) or getattr(raw, "total_tokens", None)

    # 转换为整数 (确保是有限数值)
    def as_int(val) -> int | None:
        if val is None:
            return None
        try:
            num = int(val)
            return num if isinstance(num, int) and num >= 0 else None
        except (ValueError, TypeError):
            return None

    return NormalizedUsage(
        input=as_int(input_val),
        output=as_int(output_val),
        cache_read=as_int(cache_read_val),
        cache_write=as_int(cache_write_val),
        total=as_int(total_val),
    )


def clamp_percent(value: float) -> float:
    """限制百分比值在 0-100 之间

    对标: clampPercent in provider-usage.shared.ts
    """
    if not isinstance(value, (int, float)) or not (0 <= value <= float('inf')):
        return 0.0
    return max(0.0, min(100.0, value))
