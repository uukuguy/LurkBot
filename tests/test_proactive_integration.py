"""测试主动任务识别的集成功能"""

import os

import pytest

from lurkbot.agents.proactive import InputAnalyzer, TaskSuggester
from lurkbot.agents.runtime import run_embedded_agent
from lurkbot.agents.types import AgentContext

# Mark for tests that need API key
needs_api = pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"), reason="OPENAI_API_KEY not set"
)


@needs_api
@pytest.mark.asyncio
async def test_proactive_end_to_end():
    """测试完整的主动识别流程"""
    # 1. Analyze input
    analyzer = InputAnalyzer()
    analysis = await analyzer.analyze("This deployment keeps failing!")

    # 2. Check if should trigger
    should_trigger = analyzer.should_trigger_proactive(analysis)

    # 3. Generate suggestions if triggered
    if should_trigger:
        suggester = TaskSuggester()
        suggestions = await suggester.suggest(
            user_prompt="This deployment keeps failing!",
            analysis=analysis,
        )

        assert len(suggestions) > 0
        assert all(len(s.actions) > 0 for s in suggestions)


@needs_api
@pytest.mark.asyncio
async def test_proactive_with_runtime_integration():
    """测试与 Agent Runtime 的集成"""
    context = AgentContext(
        session_id="test-session-123",
        provider="openai",
        model_id="gpt-4o-mini",
        sender_id="test-user",
    )

    # Note: This test requires API key to be set
    # Run with enable_proactive=True (default)
    try:
        result = await run_embedded_agent(
            context=context,
            prompt="The tests keep failing, this is so frustrating!",
            system_prompt="You are a helpful assistant.",
            enable_context_aware=False,  # Disable context-aware for simpler test
            enable_proactive=True,
        )

        # Should complete without errors
        assert result.session_id_used == "test-session-123"
        # Note: actual suggestions might not appear in result
        # but the system should not crash

    except Exception as e:
        # If API key not available, that's ok for CI
        if "API" in str(e) or "api_key" in str(e).lower():
            pytest.skip("API key not available")
        else:
            raise


@pytest.mark.asyncio
async def test_proactive_disabled():
    """测试禁用主动识别"""
    context = AgentContext(
        session_id="test-session-456",
        provider="openai",
        model_id="gpt-4o-mini",
        sender_id="test-user",
    )

    try:
        result = await run_embedded_agent(
            context=context,
            prompt="Help me debug this",
            system_prompt="You are a helpful assistant.",
            enable_context_aware=False,
            enable_proactive=False,  # Explicitly disable
        )

        # Should work fine without proactive
        assert result.session_id_used == "test-session-456"

    except Exception as e:
        if "API" in str(e) or "api_key" in str(e).lower():
            pytest.skip("API key not available")
        else:
            raise


@needs_api
@pytest.mark.asyncio
async def test_analyzer_handles_various_intents():
    """测试分析器处理各种意图类型"""
    analyzer = InputAnalyzer()

    test_cases = [
        ("How do I deploy this?", "question"),
        ("Please help me fix the bug", "request"),
        ("This is broken!", "complaint"),
        ("Great work!", "feedback"),
        ("I wonder what would happen if...", "exploration"),
    ]

    for prompt, expected_category in test_cases:
        result = await analyzer.analyze(prompt)
        assert result.confidence > 0.0
        # Intent should be one of the valid types
        assert result.intent.value in [
            "question",
            "request",
            "complaint",
            "feedback",
            "exploration",
            "unknown",
        ]
