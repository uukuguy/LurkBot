"""Phase 15 - Provider Usage 监控系统测试

对标 MoltBot 的 provider-usage 相关测试
"""

import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from lurkbot.usage import (
    PROVIDER_LABELS,
    CostUsageDailyEntry,
    CostUsageSummary,
    CostUsageTotals,
    ModelCostConfig,
    NormalizedUsage,
    ProviderUsageSnapshot,
    SessionCostSummary,
    UsageSummary,
    UsageWindow,
    clamp_percent,
    estimate_usage_cost,
    format_cost_usage_summary,
    format_provider_usage,
    format_reset_remaining,
    format_token_count,
    format_usage_summary_line,
    format_usd,
    format_window_usage,
    load_cost_usage_summary,
    load_session_cost_summary,
    normalize_usage,
)


# ============================================================================
# Types Tests (类型测试)
# ============================================================================

class TestUsageTypes:
    """使用量类型测试"""

    def test_usage_window(self):
        """测试 UsageWindow 数据类"""
        window = UsageWindow(
            label="5h",
            used_percent=25.5,
            reset_at=1700000000000,
        )

        assert window.label == "5h"
        assert window.used_percent == 25.5
        assert window.reset_at == 1700000000000

    def test_provider_usage_snapshot(self):
        """测试 ProviderUsageSnapshot 数据类"""
        snapshot = ProviderUsageSnapshot(
            provider="anthropic",
            display_name="Claude",
            windows=[
                UsageWindow(label="5h", used_percent=20.0),
                UsageWindow(label="Week", used_percent=50.0),
            ],
            plan="Pro",
        )

        assert snapshot.provider == "anthropic"
        assert snapshot.display_name == "Claude"
        assert len(snapshot.windows) == 2
        assert snapshot.plan == "Pro"
        assert snapshot.error is None

    def test_usage_summary(self):
        """测试 UsageSummary 数据类"""
        summary = UsageSummary(
            updated_at=1700000000000,
            providers=[
                ProviderUsageSnapshot(
                    provider="anthropic",
                    display_name="Claude",
                    windows=[],
                ),
            ],
        )

        assert summary.updated_at == 1700000000000
        assert len(summary.providers) == 1

    def test_provider_labels(self):
        """测试提供商标签映射"""
        assert PROVIDER_LABELS["anthropic"] == "Claude"
        assert PROVIDER_LABELS["github-copilot"] == "Copilot"
        assert PROVIDER_LABELS["google-gemini-cli"] == "Gemini"


# ============================================================================
# Usage Normalization Tests (使用量归一化测试)
# ============================================================================

class TestUsageNormalization:
    """使用量归一化测试"""

    def test_normalize_usage_standard_naming(self):
        """测试标准命名的归一化"""
        raw = {
            "input": 1000,
            "output": 500,
            "cache_read": 200,
            "cache_write": 100,
            "total": 1800,
        }

        normalized = normalize_usage(raw)
        assert normalized.input == 1000
        assert normalized.output == 500
        assert normalized.cache_read == 200
        assert normalized.cache_write == 100
        assert normalized.total == 1800

    def test_normalize_usage_openai_naming(self):
        """测试 OpenAI SDK 命名的归一化"""
        raw = {
            "prompt_tokens": 1000,
            "completion_tokens": 500,
            "total_tokens": 1500,
        }

        normalized = normalize_usage(raw)
        assert normalized.input == 1000
        assert normalized.output == 500
        assert normalized.total == 1500

    def test_normalize_usage_anthropic_naming(self):
        """测试 Anthropic SDK 命名的归一化"""
        raw = {
            "input_tokens": 1000,
            "output_tokens": 500,
            "cache_read_input_tokens": 200,
            "cache_creation_input_tokens": 100,
        }

        normalized = normalize_usage(raw)
        assert normalized.input == 1000
        assert normalized.output == 500
        assert normalized.cache_read == 200
        assert normalized.cache_write == 100

    def test_normalize_usage_none(self):
        """测试 None 值的归一化"""
        normalized = normalize_usage(None)
        assert normalized.input is None
        assert normalized.output is None

    def test_clamp_percent(self):
        """测试百分比限制函数"""
        assert clamp_percent(50.0) == 50.0
        assert clamp_percent(-10.0) == 0.0
        assert clamp_percent(150.0) == 100.0
        assert clamp_percent(0.0) == 0.0
        assert clamp_percent(100.0) == 100.0


# ============================================================================
# Cost Calculation Tests (成本计算测试)
# ============================================================================

class TestCostCalculation:
    """成本计算测试"""

    def test_estimate_usage_cost(self):
        """测试成本估算"""
        usage = NormalizedUsage(
            input=1_000_000,      # 1M tokens
            output=500_000,       # 0.5M tokens
            cache_read=200_000,   # 0.2M tokens
            cache_write=100_000,  # 0.1M tokens
        )

        cost = ModelCostConfig(
            input=3.0,       # $3 per 1M tokens
            output=15.0,     # $15 per 1M tokens
            cache_read=0.3,  # $0.3 per 1M tokens
            cache_write=3.75, # $3.75 per 1M tokens
        )

        total_cost = estimate_usage_cost(usage, cost)

        # Expected: 1 * 3 + 0.5 * 15 + 0.2 * 0.3 + 0.1 * 3.75
        #         = 3 + 7.5 + 0.06 + 0.375
        #         = 10.935
        assert total_cost is not None
        assert abs(total_cost - 10.935) < 0.001

    def test_estimate_usage_cost_none(self):
        """测试缺少数据时的成本估算"""
        assert estimate_usage_cost(None, None) is None

        usage = NormalizedUsage(input=1000)
        assert estimate_usage_cost(usage, None) is None

        cost = ModelCostConfig(input=3.0, output=15.0, cache_read=0.3, cache_write=3.75)
        assert estimate_usage_cost(None, cost) is None


# ============================================================================
# Formatting Tests (格式化测试)
# ============================================================================

class TestFormatting:
    """格式化测试"""

    def test_format_usd(self):
        """测试 USD 格式化"""
        assert format_usd(1.23) == "$1.23"
        assert format_usd(0.05) == "$0.05"
        assert format_usd(0.0012) == "$0.0012"
        assert format_usd(100.5) == "$100.50"
        assert format_usd(None) is None

    def test_format_token_count(self):
        """测试 token 数量格式化"""
        assert format_token_count(1_500_000) == "1.5m"
        assert format_token_count(250_000) == "250.0k"
        assert format_token_count(500) == "500"
        assert format_token_count(None) == "0"

    def test_format_reset_remaining(self):
        """测试重置时间格式化"""
        now_ms = int(datetime.now().timestamp() * 1000)

        # 2 小时后 (允许一些精度误差)
        reset_2h = now_ms + (2 * 3600 * 1000)
        formatted_2h = format_reset_remaining(reset_2h)
        assert "h" in formatted_2h  # 应该包含小时

        # 3 天后
        reset_3d = now_ms + (3 * 86400 * 1000)
        formatted_3d = format_reset_remaining(reset_3d)
        assert "3d" in formatted_3d or "2d" in formatted_3d  # 允许一些精度误差

        # 已过期
        reset_past = now_ms - 1000
        assert format_reset_remaining(reset_past) == "now"

    def test_format_window_usage(self):
        """测试使用量窗口格式化"""
        window = UsageWindow(
            label="5h",
            used_percent=25.0,
            reset_at=None,
        )

        formatted = format_window_usage(window)
        assert "5h" in formatted
        assert "75% left" in formatted

    def test_format_provider_usage(self):
        """测试提供商使用量格式化"""
        snapshot = ProviderUsageSnapshot(
            provider="anthropic",
            display_name="Claude",
            windows=[
                UsageWindow(label="Week", used_percent=30.0),
            ],
            plan="Pro",
        )

        formatted = format_provider_usage(snapshot)
        assert "Claude" in formatted
        assert "Pro" in formatted
        assert "70% left" in formatted

    def test_format_provider_usage_error(self):
        """测试错误情况的提供商使用量格式化"""
        snapshot = ProviderUsageSnapshot(
            provider="anthropic",
            display_name="Claude",
            windows=[],
            error="No API key",
        )

        formatted = format_provider_usage(snapshot)
        assert "Claude" in formatted
        assert "No API key" in formatted

    def test_format_usage_summary_line(self):
        """测试使用量汇总单行格式化"""
        summary = UsageSummary(
            updated_at=int(datetime.now().timestamp() * 1000),
            providers=[
                ProviderUsageSnapshot(
                    provider="anthropic",
                    display_name="Claude",
                    windows=[UsageWindow(label="Week", used_percent=25.0)],
                ),
            ],
        )

        formatted = format_usage_summary_line(summary)
        assert formatted is not None
        assert "📊 Usage:" in formatted
        assert "Claude" in formatted

    def test_format_usage_summary_line_empty(self):
        """测试空使用量汇总的格式化"""
        summary = UsageSummary(
            updated_at=int(datetime.now().timestamp() * 1000),
            providers=[],
        )

        formatted = format_usage_summary_line(summary)
        assert formatted is None


# ============================================================================
# Cost Store Tests (成本存储测试)
# ============================================================================

class TestCostStore:
    """成本存储测试"""

    @pytest.mark.asyncio
    async def test_load_cost_usage_summary_empty_dir(self, tmp_path):
        """测试从空目录加载成本汇总"""
        sessions_dir = tmp_path / "sessions"
        sessions_dir.mkdir()

        summary = await load_cost_usage_summary(sessions_dir, days=30)

        assert isinstance(summary, CostUsageSummary)
        assert summary.days == 30
        assert len(summary.daily) == 0
        assert summary.totals.total_tokens == 0
        assert summary.totals.total_cost == 0.0

    @pytest.mark.asyncio
    async def test_load_cost_usage_summary_with_data(self, tmp_path):
        """测试从包含数据的目录加载成本汇总"""
        sessions_dir = tmp_path / "sessions"
        sessions_dir.mkdir()

        # 创建测试会话文件
        session_file = sessions_dir / "test_session.jsonl"

        # 写入测试数据
        now = datetime.now()
        entries = [
            {
                "message": {
                    "role": "assistant",
                    "usage": {
                        "input_tokens": 1000,
                        "output_tokens": 500,
                    },
                    "provider": "anthropic",
                    "model": "claude-3-5-sonnet-20241022",
                    "cost_total": 0.015,
                },
                "timestamp": now.isoformat(),
            },
            {
                "message": {
                    "role": "assistant",
                    "usage": {
                        "input_tokens": 2000,
                        "output_tokens": 1000,
                    },
                    "provider": "anthropic",
                    "model": "claude-3-5-sonnet-20241022",
                    "cost_total": 0.030,
                },
                "timestamp": now.isoformat(),
            },
        ]

        with open(session_file, "w") as f:
            for entry in entries:
                f.write(json.dumps(entry) + "\n")

        # 加载成本汇总
        summary = await load_cost_usage_summary(sessions_dir, days=1)

        assert summary.totals.input == 3000
        assert summary.totals.output == 1500
        assert summary.totals.total_tokens == 4500
        assert abs(summary.totals.total_cost - 0.045) < 0.001

    @pytest.mark.asyncio
    async def test_load_session_cost_summary(self, tmp_path):
        """测试加载单个会话成本汇总"""
        session_file = tmp_path / "test_session.jsonl"

        # 写入测试数据
        now = datetime.now()
        entries = [
            {
                "message": {
                    "role": "assistant",
                    "usage": {
                        "input_tokens": 1000,
                        "output_tokens": 500,
                    },
                    "cost_total": 0.015,
                },
                "timestamp": now.isoformat(),
            },
        ]

        with open(session_file, "w") as f:
            for entry in entries:
                f.write(json.dumps(entry) + "\n")

        # 加载会话成本
        summary = await load_session_cost_summary(session_file)

        assert summary.session_id == "test_session"
        assert summary.input == 1000
        assert summary.output == 500
        assert summary.total_tokens == 1500
        assert abs(summary.total_cost - 0.015) < 0.001


# ============================================================================
# Integration Tests (集成测试)
# ============================================================================

class TestIntegration:
    """集成测试"""

    def test_full_workflow(self):
        """测试完整工作流"""
        # 1. 创建使用量数据
        usage = NormalizedUsage(
            input=1_000_000,
            output=500_000,
        )

        # 2. 创建成本配置
        cost = ModelCostConfig(
            input=3.0,
            output=15.0,
            cache_read=0.3,
            cache_write=3.75,
        )

        # 3. 估算成本
        total_cost = estimate_usage_cost(usage, cost)
        assert total_cost is not None

        # 4. 格式化输出
        formatted_cost = format_usd(total_cost)
        assert formatted_cost is not None

        formatted_tokens = format_token_count(usage.input)
        assert "1.0m" in formatted_tokens

    def test_cost_usage_summary_format(self):
        """测试成本使用量汇总格式化"""
        summary = CostUsageSummary(
            updated_at=int(datetime.now().timestamp() * 1000),
            days=30,
            daily=[
                CostUsageDailyEntry(
                    date="2025-01-29",
                    input=10000,
                    output=5000,
                    total_tokens=15000,
                    total_cost=0.15,
                ),
            ],
            totals=CostUsageTotals(
                input=10000,
                output=5000,
                total_tokens=15000,
                total_cost=0.15,
            ),
        )

        lines = format_cost_usage_summary(summary)
        assert len(lines) > 0
        assert any("Cost Usage Summary" in line for line in lines)
        assert any("$0.15" in line for line in lines)
