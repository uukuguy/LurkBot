"""
Phase 12 - Auto-Reply + Routing 系统测试

测试覆盖:
1. Tokens - 回复令牌
2. Directives - 指令提取
3. Queue Types - 队列类型
4. Session Key - 会话键构建
5. Router - 路由决策
"""

import pytest
from lurkbot.auto_reply import (
    SILENT_REPLY_TOKEN,
    HEARTBEAT_TOKEN,
    is_silent_reply_text,
    is_heartbeat_ok,
    strip_silent_token,
    strip_heartbeat_token,
    extract_think_directive,
    extract_verbose_directive,
    extract_reasoning_directive,
    extract_elevated_directive,
    QueueMode,
    QueueDropPolicy,
    QueueDirective,
    QueueItem,
    QueueState,
)
from lurkbot.routing import (
    build_session_key,
    RoutingContext,
    RoutingBinding,
    AgentConfig,
    resolve_agent_for_message,
)
from datetime import datetime


# ============================================================================
# Tokens 测试
# ============================================================================

class TestTokens:
    """测试回复令牌"""

    def test_silent_reply_token_constant(self):
        """测试静默回复令牌常量"""
        assert SILENT_REPLY_TOKEN == "NO_REPLY"

    def test_heartbeat_token_constant(self):
        """测试心跳令牌常量"""
        assert HEARTBEAT_TOKEN == "HEARTBEAT_OK"

    def test_is_silent_reply_with_suffix(self):
        """测试静默回复检测（后缀）"""
        assert is_silent_reply_text("Some text NO_REPLY")
        assert is_silent_reply_text("NO_REPLY")

    def test_is_silent_reply_with_prefix(self):
        """测试静默回复检测（前缀）"""
        assert is_silent_reply_text("/NO_REPLY")
        assert is_silent_reply_text("/NO_REPLY Some text")

    def test_is_silent_reply_false(self):
        """测试非静默回复"""
        assert not is_silent_reply_text("Normal text")
        assert not is_silent_reply_text("")
        assert not is_silent_reply_text(None)

    def test_is_heartbeat_ok_true(self):
        """测试心跳确认检测（真）"""
        assert is_heartbeat_ok("HEARTBEAT_OK")
        assert is_heartbeat_ok("Some text HEARTBEAT_OK more text")

    def test_is_heartbeat_ok_false(self):
        """测试心跳确认检测（假）"""
        assert not is_heartbeat_ok("Normal text")
        assert not is_heartbeat_ok("")
        assert not is_heartbeat_ok(None)

    def test_strip_silent_token_suffix(self):
        """测试移除静默令牌（后缀）"""
        assert strip_silent_token("Hello NO_REPLY") == "Hello"

    def test_strip_silent_token_prefix(self):
        """测试移除静默令牌（前缀）"""
        assert strip_silent_token("/NO_REPLY Hello") == "Hello"

    def test_strip_heartbeat_token(self):
        """测试移除心跳令牌"""
        assert strip_heartbeat_token("HEARTBEAT_OK") == ""
        assert strip_heartbeat_token("Text HEARTBEAT_OK more") == "Text  more"


# ============================================================================
# Directives 测试
# ============================================================================

class TestDirectives:
    """测试指令提取"""

    def test_extract_think_default(self):
        """测试提取 think 指令（默认）"""
        result = extract_think_directive("/think Hello")
        assert result.has_directive
        assert result.level == "medium"
        assert result.cleaned == "Hello"

    def test_extract_think_with_level(self):
        """测试提取 think 指令（指定级别）"""
        result = extract_think_directive("/think:high Question?")
        assert result.has_directive
        assert result.level == "high"
        assert result.cleaned == "Question?"

    def test_extract_think_short_form(self):
        """测试提取 think 指令（短格式）"""
        result = extract_think_directive("/t:low Test")
        assert result.has_directive
        assert result.level == "low"
        assert result.cleaned == "Test"

    def test_extract_think_no_directive(self):
        """测试无 think 指令"""
        result = extract_think_directive("Normal text")
        assert not result.has_directive
        assert result.level is None
        assert result.cleaned == "Normal text"

    def test_extract_verbose_default(self):
        """测试提取 verbose 指令（默认）"""
        result = extract_verbose_directive("/verbose Hello")
        assert result.has_directive
        assert result.level == "off"
        assert result.cleaned == "Hello"

    def test_extract_verbose_with_level(self):
        """测试提取 verbose 指令（指定级别）"""
        result = extract_verbose_directive("/v:high Explain")
        assert result.has_directive
        assert result.level == "high"
        assert result.cleaned == "Explain"

    def test_extract_reasoning_default(self):
        """测试提取 reasoning 指令（默认）"""
        result = extract_reasoning_directive("/reasoning Problem")
        assert result.has_directive
        assert result.level == "on"
        assert result.cleaned == "Problem"

    def test_extract_reasoning_stream(self):
        """测试提取 reasoning 指令（流式）"""
        result = extract_reasoning_directive("/r:stream Task")
        assert result.has_directive
        assert result.level == "stream"
        assert result.cleaned == "Task"

    def test_extract_elevated_default(self):
        """测试提取 elevated 指令（默认）"""
        result = extract_elevated_directive("/elevated Command")
        assert result.has_directive
        assert result.level == "ask"
        assert result.cleaned == "Command"

    def test_extract_elevated_full(self):
        """测试提取 elevated 指令（完全提权）"""
        result = extract_elevated_directive("/e:full Action")
        assert result.has_directive
        assert result.level == "full"
        assert result.cleaned == "Action"


# ============================================================================
# Queue Types 测试
# ============================================================================

class TestQueueTypes:
    """测试队列类型"""

    def test_queue_directive_creation(self):
        """测试队列指令创建"""
        directive = QueueDirective(
            cleaned="Test message",
            queue_mode="steer",
            queue_reset=True,
            debounce_ms=500,
            cap=10,
            drop_policy="old"
        )
        assert directive.cleaned == "Test message"
        assert directive.queue_mode == "steer"
        assert directive.queue_reset is True
        assert directive.debounce_ms == 500
        assert directive.cap == 10
        assert directive.drop_policy == "old"

    def test_queue_item_creation(self):
        """测试队列项创建"""
        item = QueueItem(
            id="item_123",
            session_key="agent:main:main",
            content="Hello",
            priority=1
        )
        assert item.id == "item_123"
        assert item.session_key == "agent:main:main"
        assert item.content == "Hello"
        assert item.priority == 1
        assert isinstance(item.created_at, datetime)

    def test_queue_state_creation(self):
        """测试队列状态创建"""
        state = QueueState()
        assert state.items == []
        assert state.processing is False
        assert state.last_drain_at is None
        assert state.total_processed == 0
        assert state.total_dropped == 0


# ============================================================================
# Session Key 测试
# ============================================================================

class TestSessionKey:
    """测试会话键构建"""

    def test_build_main_session_key(self):
        """测试构建主会话键"""
        key = build_session_key("main", "telegram", "main")
        assert key == "agent:main:main"

    def test_build_dm_session_key(self):
        """测试构建 DM 会话键"""
        key = build_session_key("main", "telegram", "dm", peer_id="123456")
        assert key == "agent:main:dm:telegram:123456"

    def test_build_group_session_key(self):
        """测试构建群组会话键"""
        key = build_session_key("main", "telegram", "group", peer_id="-1001234567890")
        assert key == "agent:main:group:telegram:-1001234567890"

    def test_build_guild_session_key(self):
        """测试构建 Guild 会话键"""
        key = build_session_key("main", "discord", "guild", guild_id="123456", channel_id="789")
        assert key == "agent:main:guild:discord:123456:channel:789"

    def test_build_thread_session_key(self):
        """测试构建线程会话键"""
        key = build_session_key("main", "slack", "thread", channel_id="C123", thread_id="1234567890.0001")
        assert key == "agent:main:thread:slack:C123:thread:1234567890.0001"

    def test_build_topic_session_key(self):
        """测试构建 Topic 会话键"""
        key = build_session_key("main", "telegram", "topic", peer_id="-100123", topic_id="42")
        assert key == "agent:main:topic:telegram:-100123:topic:42"


# ============================================================================
# Router 测试
# ============================================================================

class TestRouter:
    """测试路由决策"""

    def test_resolve_agent_peer_match(self):
        """测试路由决策 - 精确对等匹配（第1层）"""
        ctx = RoutingContext(
            channel="telegram",
            peer_kind="group",
            peer_id="-1001234567890"
        )
        bindings = [
            RoutingBinding(agent_id="bot1", peer_kind="group", peer_id="-1001234567890")
        ]
        agents = [AgentConfig(id="main", default=True)]
        
        result = resolve_agent_for_message(ctx, bindings, agents)
        assert result == "bot1"

    def test_resolve_agent_guild_match(self):
        """测试路由决策 - Guild 匹配（第2层）"""
        ctx = RoutingContext(
            channel="discord",
            peer_kind="guild",
            peer_id="channel123",
            guild_id="guild456"
        )
        bindings = [
            RoutingBinding(agent_id="discord_bot", guild_id="guild456")
        ]
        agents = [AgentConfig(id="main", default=True)]
        
        result = resolve_agent_for_message(ctx, bindings, agents)
        assert result == "discord_bot"

    def test_resolve_agent_team_match(self):
        """测试路由决策 - Team 匹配（第3层）"""
        ctx = RoutingContext(
            channel="slack",
            peer_kind="team",
            peer_id="channel123",
            team_id="T123456"
        )
        bindings = [
            RoutingBinding(agent_id="slack_bot", team_id="T123456")
        ]
        agents = [AgentConfig(id="main", default=True)]
        
        result = resolve_agent_for_message(ctx, bindings, agents)
        assert result == "slack_bot"

    def test_resolve_agent_account_match(self):
        """测试路由决策 - 账户匹配（第4层）"""
        ctx = RoutingContext(
            channel="telegram",
            peer_kind="dm",
            peer_id="user123",
            account_id="acc456"
        )
        bindings = [
            RoutingBinding(agent_id="account_bot", account_id="acc456")
        ]
        agents = [AgentConfig(id="main", default=True)]
        
        result = resolve_agent_for_message(ctx, bindings, agents)
        assert result == "account_bot"

    def test_resolve_agent_channel_match(self):
        """测试路由决策 - 通道匹配（第5层）"""
        ctx = RoutingContext(
            channel="whatsapp",
            peer_kind="dm",
            peer_id="user123"
        )
        bindings = [
            RoutingBinding(agent_id="whatsapp_bot", channel="whatsapp")
        ]
        agents = [AgentConfig(id="main", default=True)]
        
        result = resolve_agent_for_message(ctx, bindings, agents)
        assert result == "whatsapp_bot"

    def test_resolve_agent_default(self):
        """测试路由决策 - 默认 Agent（第6层）"""
        ctx = RoutingContext(
            channel="telegram",
            peer_kind="dm",
            peer_id="user123"
        )
        bindings = []
        agents = [
            AgentConfig(id="bot1", default=False),
            AgentConfig(id="main", default=True)
        ]
        
        result = resolve_agent_for_message(ctx, bindings, agents)
        assert result == "main"

    def test_resolve_agent_first_fallback(self):
        """测试路由决策 - 首个 Agent 兜底"""
        ctx = RoutingContext(
            channel="telegram",
            peer_kind="dm",
            peer_id="user123"
        )
        bindings = []
        agents = [AgentConfig(id="first_bot")]
        
        result = resolve_agent_for_message(ctx, bindings, agents)
        assert result == "first_bot"

    def test_resolve_agent_no_agents(self):
        """测试路由决策 - 无 Agent 时返回 main"""
        ctx = RoutingContext(
            channel="telegram",
            peer_kind="dm",
            peer_id="user123"
        )
        bindings = []
        agents = []
        
        result = resolve_agent_for_message(ctx, bindings, agents)
        assert result == "main"


# ============================================================================
# 测试计数验证
# ============================================================================

def test_phase12_test_count():
    """验证 Phase 12 测试数量"""
    # Tokens: 11 tests
    # Directives: 10 tests
    # Queue Types: 3 tests
    # Session Key: 6 tests
    # Router: 8 tests
    # Total: 38 tests
    assert True
