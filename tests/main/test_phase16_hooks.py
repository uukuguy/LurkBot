"""
Phase 16 - Hooks 扩展系统测试
"""

import pytest
from datetime import datetime
from pathlib import Path
import tempfile
import shutil

from lurkbot.hooks import (
    InternalHookEvent,
    HookMetadata,
    HookRequirements,
    HookPackage,
    HookRegistry,
    register_internal_hook,
    trigger_internal_hook,
    get_global_registry,
    discover_hooks,
    load_hook_from_path,
    register_bundled_hooks,
)


# ============================================================================
# 测试: 钩子事件类型
# ============================================================================


def test_hook_event_creation():
    """测试钩子事件创建"""
    event = InternalHookEvent(
        type="command",
        action="new",
        session_key="agent:main:main",
        context={"workspace_dir": "~/clawd"},
    )

    assert event.type == "command"
    assert event.action == "new"
    assert event.session_key == "agent:main:main"
    assert event.context["workspace_dir"] == "~/clawd"
    assert isinstance(event.timestamp, datetime)
    assert event.messages == []


def test_hook_event_with_messages():
    """测试钩子事件消息列表"""
    event = InternalHookEvent(
        type="session",
        action="created",
        session_key="agent:main:main",
    )

    event.messages.append("✨ Session created!")
    event.messages.append("📝 Logged to file")

    assert len(event.messages) == 2
    assert event.messages[0] == "✨ Session created!"


# ============================================================================
# 测试: 钩子元数据
# ============================================================================


def test_hook_metadata_creation():
    """测试钩子元数据创建"""
    metadata = HookMetadata(
        name="test-hook",
        emoji="🧪",
        events=["command:test"],
        description="Test hook",
        requires=HookRequirements(bins=["node"], env=["API_KEY"]),
        enabled=True,
        priority=100,
    )

    assert metadata.name == "test-hook"
    assert metadata.emoji == "🧪"
    assert metadata.events == ["command:test"]
    assert metadata.requires.bins == ["node"]
    assert metadata.requires.env == ["API_KEY"]


def test_hook_metadata_defaults():
    """测试钩子元数据默认值"""
    metadata = HookMetadata(name="minimal-hook")

    assert metadata.emoji == "🔌"
    assert metadata.events == []
    assert metadata.description == ""
    assert metadata.enabled is True
    assert metadata.priority == 100


# ============================================================================
# 测试: 钩子注册表
# ============================================================================


@pytest.fixture
def registry():
    """创建测试用注册表"""
    return HookRegistry()


@pytest.fixture
def sample_hook_package():
    """创建示例钩子包"""

    async def handler(event: InternalHookEvent) -> None:
        event.messages.append(f"Handler executed for {event.action}")

    metadata = HookMetadata(
        name="sample-hook",
        emoji="📦",
        events=["command:test"],
        priority=100,
    )

    return HookPackage(
        metadata=metadata,
        handler=handler,
        source_path="/test/sample-hook",
    )


def test_registry_register(registry, sample_hook_package):
    """测试注册钩子"""
    registry.register("command:test", sample_hook_package)

    hooks = registry.list_hooks("command:test")
    assert len(hooks) == 1
    assert hooks[0].metadata.name == "sample-hook"


def test_registry_register_multiple_priorities(registry):
    """测试按优先级注册多个钩子"""

    async def handler(event: InternalHookEvent) -> None:
        pass

    # 创建三个不同优先级的钩子
    hook1 = HookPackage(
        metadata=HookMetadata(name="hook1", priority=200),
        handler=handler,
        source_path="/test/hook1",
    )
    hook2 = HookPackage(
        metadata=HookMetadata(name="hook2", priority=50),
        handler=handler,
        source_path="/test/hook2",
    )
    hook3 = HookPackage(
        metadata=HookMetadata(name="hook3", priority=100),
        handler=handler,
        source_path="/test/hook3",
    )

    registry.register("command:test", hook1)
    registry.register("command:test", hook2)
    registry.register("command:test", hook3)

    hooks = registry.list_hooks("command:test")
    assert len(hooks) == 3
    # 应该按优先级排序: hook2 (50) < hook3 (100) < hook1 (200)
    assert hooks[0].metadata.name == "hook2"
    assert hooks[1].metadata.name == "hook3"
    assert hooks[2].metadata.name == "hook1"


def test_registry_unregister(registry, sample_hook_package):
    """测试取消注册钩子"""
    registry.register("command:test", sample_hook_package)
    assert len(registry.list_hooks("command:test")) == 1

    success = registry.unregister("command:test", "sample-hook")
    assert success is True
    assert len(registry.list_hooks("command:test")) == 0


def test_registry_unregister_nonexistent(registry):
    """测试取消注册不存在的钩子"""
    success = registry.unregister("command:test", "nonexistent")
    assert success is False


def test_registry_match_event_pattern(registry):
    """测试事件模式匹配"""
    # 精确匹配
    assert registry._match_event_pattern("command:new", "command:new")

    # 通配符匹配
    assert registry._match_event_pattern("command:new", "command:*")
    assert registry._match_event_pattern("command:reset", "command:*")

    # 不匹配
    assert not registry._match_event_pattern("session:created", "command:*")


def test_registry_get_handlers_for_event(registry):
    """测试获取事件的处理器"""

    async def handler(event: InternalHookEvent) -> None:
        pass

    # 注册多个钩子
    hook1 = HookPackage(
        metadata=HookMetadata(name="hook1", events=["command:*"]),
        handler=handler,
        source_path="/test/hook1",
    )
    hook2 = HookPackage(
        metadata=HookMetadata(name="hook2", events=["command:new"]),
        handler=handler,
        source_path="/test/hook2",
    )
    hook3 = HookPackage(
        metadata=HookMetadata(name="hook3", events=["session:*"], enabled=False),
        handler=handler,
        source_path="/test/hook3",
    )

    registry.register("command:*", hook1)
    registry.register("command:new", hook2)
    registry.register("session:*", hook3)

    # 测试 command:new 事件
    event = InternalHookEvent(
        type="command",
        action="new",
        session_key="agent:main:main",
    )

    handlers = registry.get_handlers_for_event(event)
    assert len(handlers) == 2  # hook1 和 hook2 匹配
    assert handlers[0].metadata.name in ["hook1", "hook2"]

    # 测试 session:created 事件 (hook3 被禁用)
    event2 = InternalHookEvent(
        type="session",
        action="created",
        session_key="agent:main:main",
    )

    handlers2 = registry.get_handlers_for_event(event2)
    assert len(handlers2) == 0  # hook3 被禁用


@pytest.mark.asyncio
async def test_registry_trigger(registry):
    """测试触发钩子"""
    executed = []

    async def handler1(event: InternalHookEvent) -> None:
        executed.append("handler1")
        event.messages.append("Handler 1 executed")

    async def handler2(event: InternalHookEvent) -> None:
        executed.append("handler2")
        event.messages.append("Handler 2 executed")

    hook1 = HookPackage(
        metadata=HookMetadata(name="hook1", priority=100),
        handler=handler1,
        source_path="/test/hook1",
    )
    hook2 = HookPackage(
        metadata=HookMetadata(name="hook2", priority=50),
        handler=handler2,
        source_path="/test/hook2",
    )

    registry.register("command:test", hook1)
    registry.register("command:test", hook2)

    event = InternalHookEvent(
        type="command",
        action="test",
        session_key="agent:main:main",
    )

    await registry.trigger(event)

    # 应该按优先级执行: handler2 (50) -> handler1 (100)
    assert executed == ["handler2", "handler1"]
    assert len(event.messages) == 2


@pytest.mark.asyncio
async def test_registry_trigger_with_error(registry):
    """测试触发钩子时的错误处理"""

    async def failing_handler(event: InternalHookEvent) -> None:
        raise ValueError("Handler failed!")

    async def normal_handler(event: InternalHookEvent) -> None:
        event.messages.append("Normal handler executed")

    hook1 = HookPackage(
        metadata=HookMetadata(name="failing-hook", priority=50),
        handler=failing_handler,
        source_path="/test/failing",
    )
    hook2 = HookPackage(
        metadata=HookMetadata(name="normal-hook", priority=100),
        handler=normal_handler,
        source_path="/test/normal",
    )

    registry.register("command:test", hook1)
    registry.register("command:test", hook2)

    event = InternalHookEvent(
        type="command",
        action="test",
        session_key="agent:main:main",
    )

    # 不应该抛出异常
    await registry.trigger(event)

    # 正常的处理器应该仍然执行
    assert "Normal handler executed" in event.messages
    # 失败的处理器应该记录错误消息
    assert any("failed" in msg.lower() for msg in event.messages)


# ============================================================================
# 测试: 全局注册表
# ============================================================================


@pytest.mark.asyncio
async def test_global_registry():
    """测试全局注册表"""
    executed = []

    async def handler(event: InternalHookEvent) -> None:
        executed.append("global_handler")

    hook = HookPackage(
        metadata=HookMetadata(name="global-hook"),
        handler=handler,
        source_path="/test/global",
    )

    register_internal_hook("command:global", hook)

    event = InternalHookEvent(
        type="command",
        action="global",
        session_key="agent:main:main",
    )

    await trigger_internal_hook(event)

    assert "global_handler" in executed


# ============================================================================
# 测试: 钩子发现
# ============================================================================


@pytest.fixture
def temp_hooks_dir():
    """创建临时钩子目录"""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


def test_discover_hooks_empty(temp_hooks_dir):
    """测试发现空目录"""
    packages = discover_hooks(workspace_dir=str(temp_hooks_dir))
    assert len(packages) == 0


def test_load_hook_from_path_missing_files(temp_hooks_dir):
    """测试加载缺少文件的钩子"""
    hook_dir = temp_hooks_dir / "incomplete-hook"
    hook_dir.mkdir()

    # 缺少 HOOK.md 和 handler.py
    package = load_hook_from_path(hook_dir)
    assert package is None


def test_load_hook_from_path_valid(temp_hooks_dir):
    """测试加载有效的钩子"""
    hook_dir = temp_hooks_dir / "valid-hook"
    hook_dir.mkdir()

    # 创建 HOOK.md
    hook_md = hook_dir / "HOOK.md"
    hook_md.write_text(
        """---
name: valid-hook
emoji: ✅
events:
  - command:test
description: A valid test hook
enabled: true
priority: 100
---

# Valid Hook

This is a valid hook for testing.
""",
        encoding="utf-8",
    )

    # 创建 handler.py
    handler_py = hook_dir / "handler.py"
    handler_py.write_text(
        """
async def handler(event):
    event.messages.append("Valid hook executed")
""",
        encoding="utf-8",
    )

    package = load_hook_from_path(hook_dir)
    assert package is not None
    assert package.metadata.name == "valid-hook"
    assert package.metadata.emoji == "✅"
    assert package.metadata.events == ["command:test"]
    assert callable(package.handler)


# ============================================================================
# 测试: 预装钩子
# ============================================================================


def test_register_bundled_hooks():
    """测试注册预装钩子"""
    registry = get_global_registry()
    initial_count = len(registry.list_hooks())

    register_bundled_hooks()

    # 应该注册了至少 3 个预装钩子
    final_count = len(registry.list_hooks())
    assert final_count >= initial_count + 3


@pytest.mark.asyncio
async def test_bundled_session_memory_hook():
    """测试预装的 session-memory 钩子"""
    register_bundled_hooks()

    event = InternalHookEvent(
        type="command",
        action="new",
        session_key="agent:main:main",
    )

    await trigger_internal_hook(event)

    # 应该有消息表示会话已保存
    assert any("saved" in msg.lower() for msg in event.messages)


@pytest.mark.asyncio
async def test_bundled_command_logger_hook():
    """测试预装的 command-logger 钩子"""
    register_bundled_hooks()

    event = InternalHookEvent(
        type="command",
        action="test",
        session_key="agent:main:main",
        context={"test": "data"},
    )

    # 不应该抛出异常
    await trigger_internal_hook(event)


@pytest.mark.asyncio
async def test_bundled_boot_md_hook():
    """测试预装的 boot-md 钩子"""
    register_bundled_hooks()

    event = InternalHookEvent(
        type="gateway",
        action="startup",
        session_key="agent:main:main",
        context={"workspace_dir": "/test/workspace"},
    )

    await trigger_internal_hook(event)

    # 应该有消息表示 BOOT.md 已执行
    assert any("boot" in msg.lower() for msg in event.messages)


# ============================================================================
# 测试: 钩子优先级
# ============================================================================


@pytest.mark.asyncio
async def test_hook_execution_order():
    """测试钩子按优先级执行"""
    registry = HookRegistry()
    execution_order = []

    async def make_handler(name: str):
        async def handler(event: InternalHookEvent) -> None:
            execution_order.append(name)

        return handler

    # 创建不同优先级的钩子
    for name, priority in [("high", 10), ("medium", 50), ("low", 100)]:
        hook = HookPackage(
            metadata=HookMetadata(name=name, priority=priority),
            handler=await make_handler(name),
            source_path=f"/test/{name}",
        )
        registry.register("command:event", hook)

    event = InternalHookEvent(
        type="command",
        action="event",
        session_key="agent:main:main",
    )

    await registry.trigger(event)

    # 应该按优先级执行: high (10) -> medium (50) -> low (100)
    assert execution_order == ["high", "medium", "low"]


# ============================================================================
# 测试: 钩子禁用
# ============================================================================


@pytest.mark.asyncio
async def test_disabled_hook_not_executed():
    """测试禁用的钩子不会执行"""
    registry = HookRegistry()
    executed = []

    async def handler(event: InternalHookEvent) -> None:
        executed.append("executed")

    hook = HookPackage(
        metadata=HookMetadata(name="disabled-hook", enabled=False),
        handler=handler,
        source_path="/test/disabled",
    )

    registry.register("test:event", hook)

    event = InternalHookEvent(
        type="command",
        action="event",
        session_key="agent:main:main",
    )

    await registry.trigger(event)

    # 禁用的钩子不应该执行
    assert len(executed) == 0
