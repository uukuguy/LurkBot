"""
Hooks tool - Manage and trigger internal hooks

Provides a tool interface for managing the hooks system.
"""

from typing import Optional
from pydantic import BaseModel, Field

from lurkbot.hooks import (
    InternalHookEvent,
    trigger_internal_hook,
    get_global_registry,
    discover_hooks,
    register_internal_hook,
)
from lurkbot.tools.builtin.common import ToolResult, text_result, json_result


class HooksParams(BaseModel):
    """Parameters for hooks tool"""

    action: str = Field(description="Action to perform: list, trigger, discover, info")
    event_type: Optional[str] = Field(
        default=None, description="Event type for trigger action: command, session, agent, gateway"
    )
    event_action: Optional[str] = Field(
        default=None, description="Event action name for trigger action"
    )
    session_key: Optional[str] = Field(
        default=None, description="Session key for trigger action"
    )
    context: Optional[dict] = Field(
        default=None, description="Event context data for trigger action"
    )
    workspace_dir: Optional[str] = Field(
        default=None, description="Workspace directory for discover action"
    )
    event_pattern: Optional[str] = Field(
        default=None, description="Event pattern filter for list action"
    )


async def hooks_tool(params: dict) -> ToolResult:
    """
    Manage and trigger internal hooks

    Actions:
    - list: List registered hooks
    - trigger: Trigger a hook event
    - discover: Discover hooks from directories
    - info: Show hook information

    Args:
        params: Tool parameters

    Returns:
        Tool result with hooks information
    """
    try:
        p = HooksParams.model_validate(params)
        registry = get_global_registry()

        # List registered hooks
        if p.action == "list":
            packages = registry.list_hooks(p.event_pattern)

            if not packages:
                return text_result("No hooks registered")

            lines = ["📋 Registered Hooks:\n"]
            for pkg in packages:
                enabled = "✅" if pkg.metadata.enabled else "❌"
                lines.append(
                    f"{enabled} {pkg.metadata.emoji} {pkg.metadata.name} "
                    f"(priority={pkg.metadata.priority})"
                )
                lines.append(f"   Events: {', '.join(pkg.metadata.events)}")
                if pkg.metadata.description:
                    lines.append(f"   Description: {pkg.metadata.description}")
                lines.append(f"   Source: {pkg.source_path}\n")

            return text_result("\n".join(lines))

        # Trigger a hook event
        elif p.action == "trigger":
            if not p.event_type or not p.event_action or not p.session_key:
                return text_result(
                    "❌ Missing required parameters: event_type, event_action, session_key"
                )

            event = InternalHookEvent(
                type=p.event_type,  # type: ignore
                action=p.event_action,
                session_key=p.session_key,
                context=p.context or {},
            )

            await trigger_internal_hook(event)

            lines = [
                f"✅ Triggered hook event: {p.event_type}:{p.event_action}",
                f"Session: {p.session_key}",
            ]

            if event.messages:
                lines.append("\nMessages:")
                for msg in event.messages:
                    lines.append(f"  {msg}")

            return text_result("\n".join(lines))

        # Discover hooks from directories
        elif p.action == "discover":
            packages = discover_hooks(workspace_dir=p.workspace_dir)

            if not packages:
                return text_result("No hooks discovered")

            lines = [f"🔍 Discovered {len(packages)} hook(s):\n"]
            for pkg in packages:
                lines.append(f"{pkg.metadata.emoji} {pkg.metadata.name}")
                lines.append(f"   Source: {pkg.source_path}")
                lines.append(f"   Events: {', '.join(pkg.metadata.events)}\n")

                # Register discovered hooks
                for event_pattern in pkg.metadata.events:
                    register_internal_hook(event_pattern, pkg)

            lines.append("\n✅ All discovered hooks registered")
            return text_result("\n".join(lines))

        # Show hook information
        elif p.action == "info":
            return json_result(
                {
                    "total_hooks": len(registry.list_hooks()),
                    "hook_types": ["command", "session", "agent", "gateway"],
                    "discovery_paths": [
                        "<workspace>/hooks/",
                        "~/.lurkbot/hooks/",
                        "<lurkbot>/hooks/bundled/",
                    ],
                    "example": {
                        "HOOK.md": "YAML frontmatter + documentation",
                        "handler.py": "Async handler function",
                    },
                }
            )

        else:
            return text_result(
                f"❌ Unknown action: {p.action}\n"
                f"Available actions: list, trigger, discover, info"
            )

    except Exception as e:
        return text_result(f"❌ Error: {e}")


def create_hooks_tool():
    """Create hooks tool for PydanticAI"""
    from pydantic_ai import Tool

    return Tool(hooks_tool, takes_ctx=False, description="Manage and trigger internal hooks")
