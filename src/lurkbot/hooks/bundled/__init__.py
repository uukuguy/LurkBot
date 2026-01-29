"""
Hooks 扩展系统 - 预装钩子

提供预装的钩子实现。
"""

from loguru import logger

from ..types import HookMetadata, HookPackage, HookRequirements, InternalHookEvent
from ..registry import register_internal_hook


def register_bundled_hooks() -> None:
    """注册所有预装钩子"""
    hooks = [
        _create_session_memory_hook(),
        _create_command_logger_hook(),
        _create_boot_md_hook(),
    ]

    for hook in hooks:
        for event_pattern in hook.metadata.events:
            register_internal_hook(event_pattern, hook)

    logger.info(f"Registered {len(hooks)} bundled hooks")


def _create_session_memory_hook() -> HookPackage:
    """💾 session-memory: /new 时保存会话快照"""

    async def handler(event: InternalHookEvent) -> None:
        """保存会话快照到内存"""
        session_key = event.session_key
        logger.info(f"💾 Saving session snapshot for {session_key}")

        # TODO: 实际实现需要调用 sessions.store.save_snapshot()
        event.messages.append(f"✨ Session {session_key} saved!")

    metadata = HookMetadata(
        name="session-memory",
        emoji="💾",
        events=["command:new"],
        description="Save session snapshot on /new command",
        requires=HookRequirements(),
        enabled=True,
        priority=100,
    )

    return HookPackage(
        metadata=metadata,
        handler=handler,
        source_path="<bundled>",
    )


def _create_command_logger_hook() -> HookPackage:
    """📝 command-logger: 命令事件日志"""

    async def handler(event: InternalHookEvent) -> None:
        """记录命令事件"""
        logger.info(
            f"📝 Command event: {event.action} "
            f"(session={event.session_key}, context={event.context})"
        )

    metadata = HookMetadata(
        name="command-logger",
        emoji="📝",
        events=["command:*"],
        description="Log all command events",
        requires=HookRequirements(),
        enabled=True,
        priority=200,
    )

    return HookPackage(
        metadata=metadata,
        handler=handler,
        source_path="<bundled>",
    )


def _create_boot_md_hook() -> HookPackage:
    """🚀 boot-md: Gateway 启动后运行 BOOT.md"""

    async def handler(event: InternalHookEvent) -> None:
        """Gateway 启动后执行 BOOT.md"""
        logger.info("🚀 Gateway startup detected")

        workspace_dir = event.context.get("workspace_dir")
        if not workspace_dir:
            logger.warning("No workspace_dir in context, skipping BOOT.md")
            return

        # TODO: 实际实现需要读取和执行 BOOT.md
        logger.info(f"Would execute BOOT.md from {workspace_dir}")
        event.messages.append("🚀 BOOT.md executed!")

    metadata = HookMetadata(
        name="boot-md",
        emoji="🚀",
        events=["gateway:startup"],
        description="Run BOOT.md after Gateway startup",
        requires=HookRequirements(),
        enabled=True,
        priority=50,
    )

    return HookPackage(
        metadata=metadata,
        handler=handler,
        source_path="<bundled>",
    )
