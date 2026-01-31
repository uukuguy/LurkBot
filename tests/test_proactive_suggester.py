"""测试 TaskSuggester 模块"""

import os

import pytest

from lurkbot.agents.proactive import (
    InputAnalysis,
    IntentType,
    SentimentType,
    TaskPriority,
    TaskSuggester,
)

# Mark for tests that need API key
needs_api = pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"), reason="OPENAI_API_KEY not set"
)


@needs_api
@pytest.mark.asyncio
async def test_suggester_generates_suggestions():
    """测试生成任务建议"""
    suggester = TaskSuggester()

    analysis = InputAnalysis(
        intent=IntentType.COMPLAINT,
        sentiment=SentimentType.NEGATIVE,
        key_topics=["bug", "crash"],
        implicit_needs=["investigate crash cause", "check logs"],
        confidence=0.85,
    )

    suggestions = await suggester.suggest(
        user_prompt="This app keeps crashing!",
        analysis=analysis,
    )

    assert len(suggestions) > 0
    assert all(s.confidence > 0.0 for s in suggestions)
    assert all(len(s.actions) > 0 for s in suggestions)


@needs_api
@pytest.mark.asyncio
async def test_suggester_with_context_summary():
    """测试带上下文摘要的建议生成"""
    suggester = TaskSuggester()

    analysis = InputAnalysis(
        intent=IntentType.EXPLORATION,
        sentiment=SentimentType.NEUTRAL,
        key_topics=["deployment", "kubernetes"],
        implicit_needs=["learn k8s deployment"],
        confidence=0.75,
    )

    context_summary = "User has been asking about Docker containers repeatedly"

    suggestions = await suggester.suggest(
        user_prompt="How do I deploy to Kubernetes?",
        analysis=analysis,
        context_summary=context_summary,
    )

    assert len(suggestions) > 0


@needs_api
@pytest.mark.asyncio
async def test_suggester_sorts_by_priority():
    """测试建议按优先级排序"""
    suggester = TaskSuggester()

    analysis = InputAnalysis(
        intent=IntentType.REQUEST,
        sentiment=SentimentType.NEUTRAL,
        key_topics=["optimization"],
        implicit_needs=["profile performance"],
        confidence=0.8,
    )

    suggestions = await suggester.suggest(
        user_prompt="The app is slow",
        analysis=analysis,
    )

    # Check that high priority suggestions come first
    if len(suggestions) > 1:
        priorities = [s.priority for s in suggestions]
        # High priority should appear before low priority
        if TaskPriority.HIGH in priorities and TaskPriority.LOW in priorities:
            high_idx = priorities.index(TaskPriority.HIGH)
            low_idx = priorities.index(TaskPriority.LOW)
            assert high_idx < low_idx


@needs_api
@pytest.mark.asyncio
async def test_format_suggestions_for_prompt():
    """测试格式化建议为 prompt 文本"""
    suggester = TaskSuggester()

    analysis = InputAnalysis(
        intent=IntentType.COMPLAINT,
        sentiment=SentimentType.NEGATIVE,
        key_topics=["error"],
        implicit_needs=["debug error"],
        confidence=0.9,
    )

    suggestions = await suggester.suggest(
        user_prompt="I got an error",
        analysis=analysis,
    )

    formatted = suggester.format_suggestions_for_prompt(suggestions)

    assert "💡 主动建议" in formatted
    assert len(formatted) > 0
    # Should include emojis for priorities
    assert any(emoji in formatted for emoji in ["🔴", "🟡", "🟢"])


def test_format_empty_suggestions():
    """测试格式化空建议列表"""
    suggester = TaskSuggester()

    formatted = suggester.format_suggestions_for_prompt([])
    assert formatted == ""
