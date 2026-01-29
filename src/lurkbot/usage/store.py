"""Usage Store

会话成本数据存储和加载

对标 MoltBot src/infra/session-cost-usage.ts
"""

import json
from datetime import datetime, timedelta
from pathlib import Path

from .formatter import estimate_usage_cost
from .types import (
    CostUsageDailyEntry,
    CostUsageSummary,
    CostUsageTotals,
    ModelCostConfig,
    SessionCostSummary,
    normalize_usage,
)


# ============================================================================
# Cost Aggregation (成本聚合)
# ============================================================================

def empty_totals() -> CostUsageTotals:
    """创建空的成本使用量合计"""
    return CostUsageTotals(
        input=0,
        output=0,
        cache_read=0,
        cache_write=0,
        total_tokens=0,
        total_cost=0.0,
        missing_cost_entries=0,
    )


def apply_usage_totals(totals: CostUsageTotals, usage: dict) -> None:
    """应用使用量到合计

    Args:
        totals: 成本使用量合计
        usage: 使用量数据 (字典格式)
    """
    normalized = normalize_usage(usage)

    if normalized.input:
        totals.input += normalized.input
    if normalized.output:
        totals.output += normalized.output
    if normalized.cache_read:
        totals.cache_read += normalized.cache_read
    if normalized.cache_write:
        totals.cache_write += normalized.cache_write

    # 更新总 token 数
    totals.total_tokens = (
        totals.input +
        totals.output +
        totals.cache_read +
        totals.cache_write
    )


def apply_cost_total(totals: CostUsageTotals, cost: float | None) -> None:
    """应用成本到合计

    Args:
        totals: 成本使用量合计
        cost: 成本 (USD)
    """
    if cost is not None:
        totals.total_cost += cost
    else:
        totals.missing_cost_entries += 1


# ============================================================================
# Session File Scanning (会话文件扫描)
# ============================================================================

async def scan_session_file(
    file_path: Path,
    on_entry: callable,
) -> None:
    """扫描会话文件 (JSONL 格式)

    对标: scanUsageFile() in session-cost-usage.ts

    Args:
        file_path: 会话文件路径
        on_entry: 条目处理回调函数
    """
    if not file_path.exists():
        return

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                try:
                    entry = json.loads(line)

                    # 只处理 assistant 消息
                    message = entry.get("message", {})
                    if message.get("role") != "assistant":
                        continue

                    # 提取使用量和元数据
                    usage = message.get("usage")
                    if not usage:
                        continue

                    # 调用回调
                    on_entry({
                        "usage": usage,
                        "provider": message.get("provider"),
                        "model": message.get("model"),
                        "timestamp": entry.get("timestamp"),
                        "cost_total": message.get("cost_total"),
                    })

                except json.JSONDecodeError:
                    # 忽略解析错误
                    continue
                except Exception:
                    # 忽略处理错误
                    continue

    except Exception:
        # 忽略文件读取错误
        pass


def find_session_files_in_date_range(
    sessions_dir: Path,
    since_time: datetime,
) -> list[Path]:
    """查找日期范围内的会话文件

    Args:
        sessions_dir: 会话目录
        since_time: 开始时间

    Returns:
        会话文件路径列表
    """
    if not sessions_dir.exists():
        return []

    files = []

    # 扫描目录下的所有 JSONL 文件
    for file_path in sessions_dir.glob("**/*.jsonl"):
        # 检查文件修改时间
        try:
            mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
            if mtime >= since_time:
                files.append(file_path)
        except Exception:
            # 忽略无法读取的文件
            continue

    return files


# ============================================================================
# Cost Summary Loading (成本汇总加载)
# ============================================================================

async def load_cost_usage_summary(
    sessions_dir: Path,
    days: int = 30,
    model_costs: dict[str, ModelCostConfig] | None = None,
) -> CostUsageSummary:
    """加载成本使用量汇总

    对标: loadCostUsageSummary() in session-cost-usage.ts

    Args:
        sessions_dir: 会话目录
        days: 汇总天数
        model_costs: 模型成本配置 {provider:model: ModelCostConfig}

    Returns:
        成本使用量汇总
    """
    if model_costs is None:
        model_costs = {}

    # 计算开始时间
    since_time = datetime.now() - timedelta(days=days)

    # 查找会话文件
    files = find_session_files_in_date_range(sessions_dir, since_time)

    # 每日成本映射
    daily_map: dict[str, CostUsageTotals] = {}
    totals = empty_totals()

    # 扫描所有文件
    for file_path in files:
        await scan_session_file(
            file_path,
            on_entry=lambda entry: _process_cost_entry(
                entry,
                daily_map,
                totals,
                model_costs,
            ),
        )

    # 转换为每日条目列表
    daily_entries = []
    for date_str, daily_totals in sorted(daily_map.items()):
        daily_entries.append(CostUsageDailyEntry(
            date=date_str,
            input=daily_totals.input,
            output=daily_totals.output,
            cache_read=daily_totals.cache_read,
            cache_write=daily_totals.cache_write,
            total_tokens=daily_totals.total_tokens,
            total_cost=daily_totals.total_cost,
            missing_cost_entries=daily_totals.missing_cost_entries,
        ))

    return CostUsageSummary(
        updated_at=int(datetime.now().timestamp() * 1000),
        days=days,
        daily=daily_entries,
        totals=totals,
    )


def _process_cost_entry(
    entry: dict,
    daily_map: dict[str, CostUsageTotals],
    totals: CostUsageTotals,
    model_costs: dict[str, ModelCostConfig],
) -> None:
    """处理成本条目

    Args:
        entry: 使用量条目
        daily_map: 每日成本映射
        totals: 总计
        model_costs: 模型成本配置
    """
    usage = entry.get("usage")
    if not usage:
        return

    # 解析时间戳
    timestamp_str = entry.get("timestamp")
    if not timestamp_str:
        return

    try:
        timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
    except Exception:
        return

    # 获取日期 key
    date_key = timestamp.strftime("%Y-%m-%d")

    # 确保日期 bucket 存在
    if date_key not in daily_map:
        daily_map[date_key] = empty_totals()

    daily_totals = daily_map[date_key]

    # 应用使用量
    apply_usage_totals(daily_totals, usage)
    apply_usage_totals(totals, usage)

    # 计算成本
    cost = entry.get("cost_total")

    if cost is None:
        # 尝试从配置中计算
        provider = entry.get("provider")
        model = entry.get("model")

        if provider and model:
            cost_key = f"{provider}:{model}"
            model_cost = model_costs.get(cost_key)

            if model_cost:
                normalized = normalize_usage(usage)
                cost = estimate_usage_cost(normalized, model_cost)

    # 应用成本
    apply_cost_total(daily_totals, cost)
    apply_cost_total(totals, cost)


# ============================================================================
# Session Cost Loading (会话成本加载)
# ============================================================================

async def load_session_cost_summary(
    session_file: Path,
    model_costs: dict[str, ModelCostConfig] | None = None,
) -> SessionCostSummary:
    """加载会话成本汇总

    Args:
        session_file: 会话文件路径
        model_costs: 模型成本配置

    Returns:
        会话成本汇总
    """
    if model_costs is None:
        model_costs = {}

    totals = empty_totals()
    last_activity: int | None = None

    def on_entry(entry: dict) -> None:
        nonlocal last_activity

        _process_cost_entry(entry, {}, totals, model_costs)

        # 更新最后活动时间
        timestamp_str = entry.get("timestamp")
        if timestamp_str:
            try:
                timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                timestamp_ms = int(timestamp.timestamp() * 1000)
                if last_activity is None or timestamp_ms > last_activity:
                    last_activity = timestamp_ms
            except Exception:
                pass

    await scan_session_file(session_file, on_entry)

    # 提取会话 ID
    session_id = session_file.stem  # 文件名作为会话 ID

    return SessionCostSummary(
        session_id=session_id,
        session_file=str(session_file),
        last_activity=last_activity,
        input=totals.input,
        output=totals.output,
        cache_read=totals.cache_read,
        cache_write=totals.cache_write,
        total_tokens=totals.total_tokens,
        total_cost=totals.total_cost,
        missing_cost_entries=totals.missing_cost_entries,
    )
