"""测试 InputAnalyzer 模块"""

import os

import pytest

from lurkbot.agents.proactive import (
    InputAnalyzer,
    InputAnalysis,
    IntentType,
    SentimentType,
)

# Mark for tests that need API key
needs_api = pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"), reason="OPENAI_API_KEY not set"
)


@needs_api
@pytest.mark.asyncio
async def test_analyzer_question_intent():
    """测试识别提问意图"""
    analyzer = InputAnalyzer()

    result = await analyzer.analyze("How do I fix this error?")

    assert isinstance(result, InputAnalysis)
    assert result.intent == IntentType.QUESTION
    assert result.confidence > 0.0


@needs_api
@pytest.mark.asyncio
async def test_analyzer_complaint_intent():
    """测试识别抱怨意图"""
    analyzer = InputAnalyzer()

    result = await analyzer.analyze("This bug is so annoying, it keeps crashing!")

    assert isinstance(result, InputAnalysis)
    assert result.intent == IntentType.COMPLAINT
    assert result.sentiment == SentimentType.NEGATIVE


@needs_api
@pytest.mark.asyncio
async def test_analyzer_with_context():
    """测试带历史上下文的分析"""
    analyzer = InputAnalyzer()

    context_history = [
        {"role": "user", "content": "I'm trying to deploy the app"},
        {
            "role": "assistant",
            "content": "Have you checked the deployment logs?",
        },
    ]

    result = await analyzer.analyze("Still not working", context_history=context_history)

    assert isinstance(result, InputAnalysis)
    assert len(result.implicit_needs) > 0  # Should detect implicit debugging need


def test_should_trigger_proactive_negative_complaint():
    """测试消极抱怨是否触发主动建议"""
    analyzer = InputAnalyzer()

    analysis = InputAnalysis(
        intent=IntentType.COMPLAINT,
        sentiment=SentimentType.NEGATIVE,
        key_topics=["bug", "error"],
        implicit_needs=["investigate error"],
        confidence=0.8,
    )

    should_trigger = analyzer.should_trigger_proactive(analysis)
    assert should_trigger is True


def test_should_trigger_proactive_implicit_needs():
    """测试有隐含需求是否触发主动建议"""
    analyzer = InputAnalyzer()

    analysis = InputAnalysis(
        intent=IntentType.QUESTION,
        sentiment=SentimentType.NEUTRAL,
        key_topics=["deployment"],
        implicit_needs=["check logs", "verify config"],
        confidence=0.7,
    )

    should_trigger = analyzer.should_trigger_proactive(analysis)
    assert should_trigger is True


def test_should_not_trigger_low_confidence():
    """测试低置信度不触发主动建议"""
    analyzer = InputAnalyzer()

    analysis = InputAnalysis(
        intent=IntentType.COMPLAINT,
        sentiment=SentimentType.NEGATIVE,
        key_topics=[],
        implicit_needs=[],
        confidence=0.3,  # Low confidence
    )

    should_trigger = analyzer.should_trigger_proactive(analysis)
    assert should_trigger is False


def test_analyzer_initialization():
    """测试分析器初始化（不需要 API key）"""
    analyzer = InputAnalyzer()
    assert analyzer.model == "openai:gpt-4o-mini"
    assert analyzer._agent is not None
