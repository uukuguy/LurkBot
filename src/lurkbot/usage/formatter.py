"""Usage Formatter

使用量和成本的格式化输出

对标 MoltBot:
- src/utils/usage-format.ts
- src/infra/provider-usage.format.ts
"""

from datetime import datetime, timedelta

from .types import (
    CostUsageSummary,
    ModelCostConfig,
    NormalizedUsage,
    ProviderUsageSnapshot,
    UsageSummary,
    UsageWindow,
)


# ============================================================================
# Cost Calculation (成本计算)
# ============================================================================

def estimate_usage_cost(
    usage: NormalizedUsage | None,
    cost: ModelCostConfig | None,
) -> float | None:
    """估算使用量成本

    对标: estimateUsageCost() in utils/usage-format.ts

    Args:
        usage: 归一化的使用量数据
        cost: 模型成本配置

    Returns:
        估算成本 (USD)，如果缺少必要信息则返回 None
    """
    if usage is None or cost is None:
        return None

    # 提取各项 token 数量
    input_tokens = usage.input or 0
    output_tokens = usage.output or 0
    cache_read_tokens = usage.cache_read or 0
    cache_write_tokens = usage.cache_write or 0

    # 计算总成本 (per 1M tokens)
    total_cost = (
        input_tokens * cost.input +
        output_tokens * cost.output +
        cache_read_tokens * cost.cache_read +
        cache_write_tokens * cost.cache_write
    )

    # 转换为 USD (除以 1,000,000)
    return total_cost / 1_000_000


def format_usd(value: float | None) -> str | None:
    """格式化 USD 金额

    对标: formatUsd() in utils/usage-format.ts

    Args:
        value: 金额 (USD)

    Returns:
        格式化的字符串，如 "$1.23", "$0.0012"
    """
    if value is None:
        return None

    if value >= 1:
        return f"${value:.2f}"
    elif value >= 0.01:
        return f"${value:.2f}"
    else:
        # 微交易，显示 4 位小数
        return f"${value:.4f}"


def format_token_count(value: int | None) -> str:
    """格式化 token 数量

    对标: formatTokenCount() in utils/usage-format.ts

    Args:
        value: token 数量

    Returns:
        格式化的字符串，如 "1.5m", "250k", "500"
    """
    if value is None:
        return "0"

    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}m"
    elif value >= 1_000:
        return f"{value / 1_000:.1f}k"
    else:
        return str(round(value))


# ============================================================================
# Provider Usage Formatting (提供商使用量格式化)
# ============================================================================

def format_reset_remaining(reset_at_ms: int) -> str:
    """格式化重置剩余时间

    对标: formatResetRemaining() in provider-usage.format.ts

    Args:
        reset_at_ms: 重置时间 (Unix 时间戳毫秒)

    Returns:
        格式化的字符串，如 "2h 30m", "4d 6h", "Jan 29"
    """
    now = datetime.now()
    reset_time = datetime.fromtimestamp(reset_at_ms / 1000)
    delta = reset_time - now

    if delta.total_seconds() < 0:
        return "now"

    # 小于 1 天: 显示小时和分钟
    if delta.total_seconds() < 86400:  # 24 hours
        hours = int(delta.total_seconds() // 3600)
        minutes = int((delta.total_seconds() % 3600) // 60)
        if hours > 0:
            return f"{hours}h {minutes}m" if minutes > 0 else f"{hours}h"
        else:
            return f"{minutes}m"

    # 小于 7 天: 显示天数和小时
    if delta.days < 7:
        hours = int((delta.total_seconds() % 86400) // 3600)
        return f"{delta.days}d {hours}h" if hours > 0 else f"{delta.days}d"

    # 7 天或以上: 显示日期
    return reset_time.strftime("%b %d")


def format_window_usage(window: UsageWindow) -> str:
    """格式化单个使用量窗口

    对标: formatWindowUsage() in provider-usage.format.ts

    Args:
        window: 使用量窗口

    Returns:
        格式化的字符串，如 "5h: 25% left · resets 2h"
    """
    remaining = 100 - window.used_percent
    parts = [f"{window.label}: {remaining:.0f}% left"]

    if window.reset_at:
        reset_str = format_reset_remaining(window.reset_at)
        parts.append(f"resets {reset_str}")

    return " · ".join(parts)


def format_provider_usage(snapshot: ProviderUsageSnapshot) -> str:
    """格式化单个提供商使用量

    对标: formatProviderUsage() in provider-usage.format.ts

    Args:
        snapshot: 提供商使用量快照

    Returns:
        格式化的字符串，如 "Claude (Pro) 75% left (Week)"
    """
    if snapshot.error:
        return f"{snapshot.display_name}: {snapshot.error}"

    if not snapshot.windows:
        return f"{snapshot.display_name}: No usage data"

    # 找到使用率最高的窗口
    max_window = max(snapshot.windows, key=lambda w: w.used_percent)
    remaining = 100 - max_window.used_percent

    # 构建显示名称
    display = snapshot.display_name
    if snapshot.plan:
        display = f"{display} ({snapshot.plan})"

    # 添加重置时间信息
    reset_info = ""
    if max_window.reset_at:
        reset_info = f" ⏱{format_reset_remaining(max_window.reset_at)}"

    return f"{display} {remaining:.0f}% left ({max_window.label}{reset_info})"


def format_usage_summary_line(summary: UsageSummary) -> str | None:
    """格式化使用量汇总为单行

    对标: formatUsageSummaryLine() in provider-usage.format.ts

    Args:
        summary: 使用量汇总

    Returns:
        单行格式化字符串，如 "📊 Usage: Claude 75% left · Copilot 40% left"
    """
    if not summary.providers:
        return None

    # 过滤掉有错误的提供商
    valid_providers = [p for p in summary.providers if not p.error and p.windows]

    if not valid_providers:
        return None

    provider_strs = [format_provider_usage(p) for p in valid_providers]
    return f"📊 Usage: {' · '.join(provider_strs)}"


def format_usage_report_lines(summary: UsageSummary) -> list[str]:
    """格式化使用量汇总为多行报告

    对标: formatUsageReportLines() in provider-usage.format.ts

    Args:
        summary: 使用量汇总

    Returns:
        多行格式化字符串列表
    """
    lines = ["Usage:"]

    for provider in summary.providers:
        # 提供商名称行
        display = provider.display_name
        if provider.plan:
            display = f"{display} ({provider.plan})"
        lines.append(f"  {display}")

        # 错误信息
        if provider.error:
            lines.append(f"    Error: {provider.error}")
            continue

        # 各窗口使用量
        if not provider.windows:
            lines.append("    No usage data")
        else:
            for window in provider.windows:
                lines.append(f"    {format_window_usage(window)}")

    return lines


# ============================================================================
# Cost Usage Formatting (成本使用量格式化)
# ============================================================================

def format_cost_usage_summary(summary: CostUsageSummary) -> list[str]:
    """格式化成本使用量汇总

    Args:
        summary: 成本使用量汇总

    Returns:
        多行格式化字符串列表
    """
    lines = [f"Cost Usage Summary (Last {summary.days} days):"]
    lines.append("")

    # 总计
    totals = summary.totals
    lines.append("Totals:")
    lines.append(f"  Input tokens: {format_token_count(totals.input)}")
    lines.append(f"  Output tokens: {format_token_count(totals.output)}")
    if totals.cache_read > 0:
        lines.append(f"  Cache read: {format_token_count(totals.cache_read)}")
    if totals.cache_write > 0:
        lines.append(f"  Cache write: {format_token_count(totals.cache_write)}")
    lines.append(f"  Total tokens: {format_token_count(totals.total_tokens)}")
    lines.append(f"  Total cost: {format_usd(totals.total_cost) or '$0.00'}")

    if totals.missing_cost_entries > 0:
        lines.append(f"  Missing cost info: {totals.missing_cost_entries} entries")

    # 每日明细 (只显示最近 7 天)
    if summary.daily:
        lines.append("")
        lines.append("Daily breakdown (last 7 days):")
        recent_days = summary.daily[-7:]
        for entry in recent_days:
            cost_str = format_usd(entry.total_cost) or "$0.00"
            tokens_str = format_token_count(entry.total_tokens)
            lines.append(f"  {entry.date}: {tokens_str} tokens, {cost_str}")

    return lines


def format_session_cost_summary(summary) -> list[str]:
    """格式化会话成本汇总

    Args:
        summary: 会话成本汇总 (SessionCostSummary)

    Returns:
        多行格式化字符串列表
    """
    lines = ["Session Cost Summary:"]

    if summary.session_id:
        lines.append(f"  Session ID: {summary.session_id}")
    if summary.session_file:
        lines.append(f"  File: {summary.session_file}")
    if summary.last_activity:
        last_time = datetime.fromtimestamp(summary.last_activity / 1000)
        lines.append(f"  Last activity: {last_time.strftime('%Y-%m-%d %H:%M:%S')}")

    lines.append("")
    lines.append("Usage:")
    lines.append(f"  Input tokens: {format_token_count(summary.input)}")
    lines.append(f"  Output tokens: {format_token_count(summary.output)}")
    if summary.cache_read > 0:
        lines.append(f"  Cache read: {format_token_count(summary.cache_read)}")
    if summary.cache_write > 0:
        lines.append(f"  Cache write: {format_token_count(summary.cache_write)}")
    lines.append(f"  Total tokens: {format_token_count(summary.total_tokens)}")
    lines.append(f"  Total cost: {format_usd(summary.total_cost) or '$0.00'}")

    if summary.missing_cost_entries > 0:
        lines.append(f"  Missing cost info: {summary.missing_cost_entries} entries")

    return lines
