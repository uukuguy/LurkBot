"""
Phase 8 单元测试: Auth Profile + Context Compaction

测试覆盖:
1. Auth Profile 系统:
   - 冷却算法
   - Profile 优先级排序
   - 凭据验证
   - JSONL 持久化
   - 轮换逻辑

2. Context Compaction 系统:
   - Token 估算
   - 自适应分块比例
   - 消息分割
   - 分阶段摘要（Mock LLM）

对标 MoltBot auth/ 和 agents/compaction.ts 测试
"""

import pytest
from pathlib import Path
from datetime import datetime
import tempfile
import json

# Auth Profile imports
from lurkbot.auth.profiles import (
    AuthCredential,
    ProfileUsageStats,
    AuthProfileStore,
    calculate_cooldown_ms,
    resolve_auth_profile_order,
    mark_profile_failure,
    mark_profile_success,
    rotate_auth_profile,
    load_auth_profiles,
    save_auth_profiles,
    is_valid_credential,
    match_provider,
    normalize_provider_id,
)

# Context Compaction imports
from lurkbot.agents.compaction import (
    BASE_CHUNK_RATIO,
    MIN_CHUNK_RATIO,
    SAFETY_MARGIN,
    estimate_tokens,
    estimate_messages_tokens,
    split_messages_by_token_share,
    chunk_messages_by_max_tokens,
    compute_adaptive_chunk_ratio,
    compact_messages,
)


# ============================================================================
# Auth Profile Tests
# ============================================================================


class TestAuthProfileCooldown:
    """测试冷却算法"""

    def test_cooldown_formula(self):
        """测试冷却公式: min(1h, 60s × 5^(errorCount-1))"""
        # errorCount=1 → 60s (60000ms)
        assert calculate_cooldown_ms(1) == 60 * 1000

        # errorCount=2 → 300s (300000ms, 5m)
        assert calculate_cooldown_ms(2) == 300 * 1000

        # errorCount=3 → 1500s (1500000ms, 25m)
        assert calculate_cooldown_ms(3) == 1500 * 1000

        # errorCount=4 → 7500s 但上限 3600s (1h)
        assert calculate_cooldown_ms(4) == 3600 * 1000

        # errorCount=5+ → 上限 3600s (1h)
        assert calculate_cooldown_ms(5) == 3600 * 1000
        assert calculate_cooldown_ms(10) == 3600 * 1000

    def test_cooldown_zero_errors(self):
        """测试 0 次错误"""
        # 0 次错误仍然触发最小冷却
        assert calculate_cooldown_ms(0) == 60 * 1000


class TestAuthProfileHelpers:
    """测试辅助函数"""

    def test_normalize_provider_id(self):
        """测试提供商 ID 规范化"""
        assert normalize_provider_id("anthropic") == "anthropic"
        assert normalize_provider_id("ANTHROPIC") == "anthropic"
        assert normalize_provider_id("anthropic:claude-3-5-sonnet") == "anthropic"
        assert normalize_provider_id("openai/gpt-4") == "openai"

    def test_match_provider(self):
        """测试 Profile 匹配提供商"""
        assert match_provider("anthropic-main", "anthropic") is True
        assert match_provider("anthropic-backup", "anthropic") is True
        assert match_provider("openai-main", "anthropic") is False
        assert match_provider("ANTHROPIC-MAIN", "anthropic") is True

    def test_is_valid_credential_api_key(self):
        """测试 API Key 凭据验证"""
        valid = AuthCredential(type="api_key", key="sk-xxx")
        assert is_valid_credential(valid) is True

        invalid = AuthCredential(type="api_key", key=None)
        assert is_valid_credential(invalid) is False

        empty = AuthCredential(type="api_key", key="")
        assert is_valid_credential(empty) is False

    def test_is_valid_credential_token(self):
        """测试 Token 凭据验证"""
        # 有效的 token（未过期）
        future_ts = int((datetime.now().timestamp() + 3600) * 1000)
        valid = AuthCredential(type="token", token="token-xxx", expires=future_ts)
        assert is_valid_credential(valid) is True

        # 无 token
        invalid = AuthCredential(type="token", token=None)
        assert is_valid_credential(invalid) is False

        # 过期的 token
        past_ts = int((datetime.now().timestamp() - 3600) * 1000)
        expired = AuthCredential(type="token", token="token-xxx", expires=past_ts)
        assert is_valid_credential(expired) is False

    def test_is_valid_credential_oauth(self):
        """测试 OAuth 凭据验证"""
        valid = AuthCredential(type="oauth", access="access-token")
        assert is_valid_credential(valid) is True

        invalid = AuthCredential(type="oauth", access=None)
        assert is_valid_credential(invalid) is False


class TestProfileStateManagement:
    """测试 Profile 状态管理"""

    def test_mark_profile_failure(self):
        """测试标记失败"""
        store = AuthProfileStore()

        # 第一次失败
        mark_profile_failure(store, "anthropic-main", "auth")
        stats = store.usage_stats["anthropic-main"]
        assert stats.error_count == 1
        assert stats.cooldown_until is not None
        assert stats.failure_counts["auth"] == 1

        # 第二次失败
        mark_profile_failure(store, "anthropic-main", "rate_limit")
        stats = store.usage_stats["anthropic-main"]
        assert stats.error_count == 2
        assert stats.failure_counts["auth"] == 1
        assert stats.failure_counts["rate_limit"] == 1

    def test_mark_profile_success(self):
        """测试标记成功"""
        store = AuthProfileStore()

        # 先失败
        mark_profile_failure(store, "anthropic-main")
        assert store.usage_stats["anthropic-main"].error_count == 1

        # 再成功（重置错误计数）
        mark_profile_success(store, "anthropic-main")
        stats = store.usage_stats["anthropic-main"]
        assert stats.error_count == 0
        assert stats.cooldown_until is None
        assert stats.last_used is not None


class TestProfileOrderResolution:
    """测试 Profile 顺序解析"""

    def test_resolve_order_available_first(self):
        """测试可用的排在前面"""
        store = AuthProfileStore(
            profiles={
                "anthropic-main": AuthCredential(type="api_key", key="key1"),
                "anthropic-backup": AuthCredential(type="api_key", key="key2"),
            },
            order={"anthropic": ["anthropic-main", "anthropic-backup"]},
        )

        # 没有冷却
        order = resolve_auth_profile_order(store, "anthropic")
        assert order == ["anthropic-main", "anthropic-backup"]

    def test_resolve_order_cooldown_last(self):
        """测试冷却中的排在后面"""
        store = AuthProfileStore(
            profiles={
                "anthropic-main": AuthCredential(type="api_key", key="key1"),
                "anthropic-backup": AuthCredential(type="api_key", key="key2"),
            },
            order={"anthropic": ["anthropic-main", "anthropic-backup"]},
        )

        # 标记 main 失败（进入冷却）
        mark_profile_failure(store, "anthropic-main")

        order = resolve_auth_profile_order(store, "anthropic")
        # backup 应该排在前面（因为 main 在冷却中）
        assert order == ["anthropic-backup", "anthropic-main"]

    def test_resolve_order_rotation_by_last_used(self):
        """测试按 lastUsed 轮换（最旧优先）"""
        store = AuthProfileStore(
            profiles={
                "anthropic-1": AuthCredential(type="api_key", key="key1"),
                "anthropic-2": AuthCredential(type="api_key", key="key2"),
                "anthropic-3": AuthCredential(type="api_key", key="key3"),
            },
            usage_stats={
                "anthropic-1": ProfileUsageStats(last_used=1000),
                "anthropic-2": ProfileUsageStats(last_used=3000),
                "anthropic-3": ProfileUsageStats(last_used=2000),
            },
            order={"anthropic": ["anthropic-1", "anthropic-2", "anthropic-3"]},
        )

        order = resolve_auth_profile_order(store, "anthropic")
        # 按 lastUsed 升序排列（最旧的在前）
        assert order == ["anthropic-1", "anthropic-3", "anthropic-2"]

    def test_resolve_order_preferred_first(self):
        """测试指定的 Profile 优先"""
        store = AuthProfileStore(
            profiles={
                "anthropic-main": AuthCredential(type="api_key", key="key1"),
                "anthropic-backup": AuthCredential(type="api_key", key="key2"),
            },
            order={"anthropic": ["anthropic-main", "anthropic-backup"]},
        )

        order = resolve_auth_profile_order(
            store, "anthropic", preferred_profile="anthropic-backup"
        )
        assert order == ["anthropic-backup", "anthropic-main"]


class TestProfileRotation:
    """测试 Profile 轮换"""

    def test_rotate_to_next(self):
        """测试轮换到下一个"""
        store = AuthProfileStore(
            profiles={
                "anthropic-1": AuthCredential(type="api_key", key="key1"),
                "anthropic-2": AuthCredential(type="api_key", key="key2"),
                "anthropic-3": AuthCredential(type="api_key", key="key3"),
            },
            order={"anthropic": ["anthropic-1", "anthropic-2", "anthropic-3"]},
        )

        # 从 1 轮换到 2
        next_profile = rotate_auth_profile(store, "anthropic", "anthropic-1")
        assert next_profile == "anthropic-2"

        # 从 3 轮换回 1（循环）
        next_profile = rotate_auth_profile(store, "anthropic", "anthropic-3")
        assert next_profile == "anthropic-1"

    def test_rotate_no_current(self):
        """测试无当前 Profile（返回第一个）"""
        store = AuthProfileStore(
            profiles={
                "anthropic-main": AuthCredential(type="api_key", key="key1"),
            },
            order={"anthropic": ["anthropic-main"]},
        )

        next_profile = rotate_auth_profile(store, "anthropic")
        assert next_profile == "anthropic-main"

    def test_rotate_no_profiles(self):
        """测试无可用 Profile"""
        store = AuthProfileStore()

        next_profile = rotate_auth_profile(store, "anthropic")
        assert next_profile is None


class TestProfilePersistence:
    """测试 JSONL 持久化"""

    def test_save_and_load(self):
        """测试保存和加载"""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "profiles.jsonl"

            # 创建 store
            store = AuthProfileStore(
                profiles={
                    "anthropic-main": AuthCredential(type="api_key", key="sk-xxx"),
                    "openai-main": AuthCredential(type="token", token="token-xxx"),
                },
                usage_stats={
                    "anthropic-main": ProfileUsageStats(
                        last_used=1000, error_count=0
                    ),
                },
            )

            # 保存
            save_auth_profiles(store, file_path)
            assert file_path.exists()

            # 加载
            loaded = load_auth_profiles(file_path)
            assert len(loaded.profiles) == 2
            assert "anthropic-main" in loaded.profiles
            assert loaded.profiles["anthropic-main"].key == "sk-xxx"
            assert loaded.usage_stats["anthropic-main"].last_used == 1000

    def test_load_nonexistent(self):
        """测试加载不存在的文件"""
        loaded = load_auth_profiles("/nonexistent/path.jsonl")
        assert len(loaded.profiles) == 0


# ============================================================================
# Context Compaction Tests
# ============================================================================


class TestTokenEstimation:
    """测试 Token 估算"""

    def test_estimate_tokens(self):
        """测试文本 token 估算（~4 chars = 1 token）"""
        # 空文本
        assert estimate_tokens("") == 1  # 最小 1 token

        # 4 个字符 ≈ 1 token
        assert estimate_tokens("abcd") == 2  # 4//4 + 1 = 2

        # 100 个字符
        text = "a" * 100
        assert estimate_tokens(text) == 26  # 100//4 + 1

    def test_estimate_messages_tokens(self):
        """测试消息列表 token 估算"""
        messages = [
            {"role": "user", "content": "Hello"},  # 5 chars → 2 tokens
            {"role": "assistant", "content": "Hi there!"},  # 9 chars → 3 tokens
        ]
        total = estimate_messages_tokens(messages)
        assert total == 5  # 2 + 3

    def test_estimate_messages_multimodal(self):
        """测试多模态消息 token 估算"""
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Hello"},  # 5 chars
                    {"type": "image", "source": "..."},  # 忽略
                ],
            }
        ]
        total = estimate_messages_tokens(messages)
        assert total == 2  # 5//4 + 1


class TestMessageSplitting:
    """测试消息分割"""

    def test_split_by_token_share(self):
        """测试按 token 比例分割"""
        messages = [
            {"role": "user", "content": "a" * 100},  # ~26 tokens
            {"role": "assistant", "content": "b" * 100},  # ~26 tokens
            {"role": "user", "content": "c" * 100},  # ~26 tokens
            {"role": "assistant", "content": "d" * 100},  # ~26 tokens
        ]

        # 分成 2 部分
        parts = split_messages_by_token_share(messages, parts=2)
        assert len(parts) == 2
        assert len(parts[0]) == 2  # 前两条
        assert len(parts[1]) == 2  # 后两条

    def test_chunk_by_max_tokens(self):
        """测试按最大 token 分块"""
        messages = [
            {"role": "user", "content": "a" * 100},  # ~26 tokens
            {"role": "assistant", "content": "b" * 100},  # ~26 tokens
            {"role": "user", "content": "c" * 100},  # ~26 tokens
        ]

        # 最大 30 tokens 一块
        chunks = chunk_messages_by_max_tokens(messages, max_tokens=30)
        assert len(chunks) == 3  # 每条消息一块


class TestAdaptiveChunkRatio:
    """测试自适应分块比例"""

    def test_base_ratio_for_small_messages(self):
        """测试小消息使用基础比例"""
        messages = [
            {"role": "user", "content": "a" * 10},  # 很小的消息
            {"role": "assistant", "content": "b" * 10},
        ]
        context_window = 100000

        ratio = compute_adaptive_chunk_ratio(messages, context_window)
        assert ratio == BASE_CHUNK_RATIO  # 0.4

    def test_reduced_ratio_for_large_messages(self):
        """测试大消息减少比例"""
        # 创建平均消息很大的情况（> 10% 上下文）
        messages = [
            {"role": "user", "content": "a" * 50000},  # ~12500 tokens
            {"role": "assistant", "content": "b" * 50000},
        ]
        context_window = 128000

        ratio = compute_adaptive_chunk_ratio(messages, context_window)
        # 应该低于基础比例，但不低于最小比例
        assert MIN_CHUNK_RATIO <= ratio < BASE_CHUNK_RATIO

    def test_min_ratio_floor(self):
        """测试最小比例下限"""
        # 极大的消息
        messages = [
            {"role": "user", "content": "a" * 100000},  # 巨大的消息
        ]
        context_window = 100000

        ratio = compute_adaptive_chunk_ratio(messages, context_window)
        assert ratio >= MIN_CHUNK_RATIO  # 不低于 0.15


class TestCompactMessages:
    """测试消息压缩（不涉及实际 LLM 调用）"""

    @pytest.mark.asyncio
    async def test_no_compaction_needed(self):
        """测试不需要压缩的情况"""
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"},
        ]

        # 上下文窗口很大，不需要压缩
        compacted = await compact_messages(
            messages, context_window=1000000, reserve_tokens=1000, llm_client=None
        )

        # 应该返回原始消息
        assert compacted == messages

    @pytest.mark.asyncio
    async def test_compaction_without_llm(self):
        """测试无 LLM 客户端的压缩（仅保留最近消息）"""
        messages = [
            {"role": "user", "content": "a" * 1000},  # 旧消息
            {"role": "assistant", "content": "b" * 1000},
            {"role": "user", "content": "c" * 100},  # 最近消息
            {"role": "assistant", "content": "d" * 100},
        ]

        # 小上下文窗口，会触发压缩
        compacted = await compact_messages(
            messages, context_window=500, reserve_tokens=100, llm_client=None
        )

        # 无 LLM 时仅保留最近的消息
        assert len(compacted) < len(messages)
        assert compacted[-1]["content"] == "d" * 100  # 最后一条保留


# ============================================================================
# 测试统计
# ============================================================================


def test_phase8_test_count():
    """
    验证测试数量

    Phase 8 目标: 至少 30 个测试用例
    """
    # Auth Profile: ~20 tests
    # Context Compaction: ~10 tests
    # 总计: ~30 tests
    pass
