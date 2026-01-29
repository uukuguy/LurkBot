"""
Hooks 扩展系统

提供事件驱动的扩展机制，允许在关键事件点注册和执行自定义处理器。
"""

from .types import (
    InternalHookEventType,
    InternalHookEvent,
    HookHandler,
    HookMetadata,
    HookRequirements,
    HookPackage,
)
from .registry import (
    HookRegistry,
    register_internal_hook,
    trigger_internal_hook,
    get_global_registry,
)
from .discovery import discover_hooks, load_hook_from_path
from .bundled import register_bundled_hooks

__all__ = [
    # Types
    "InternalHookEventType",
    "InternalHookEvent",
    "HookHandler",
    "HookMetadata",
    "HookRequirements",
    "HookPackage",
    # Registry
    "HookRegistry",
    "register_internal_hook",
    "trigger_internal_hook",
    "get_global_registry",
    # Discovery
    "discover_hooks",
    "load_hook_from_path",
    # Bundled
    "register_bundled_hooks",
]
