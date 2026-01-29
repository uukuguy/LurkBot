"""
Hooks 扩展系统 - 类型定义

定义钩子事件类型、事件结构、处理器接口等核心类型。
"""

from datetime import datetime
from typing import Literal, Callable, Awaitable
from pydantic import BaseModel, Field, ConfigDict


# 钩子事件类型
InternalHookEventType = Literal["command", "session", "agent", "gateway"]


class InternalHookEvent(BaseModel):
    """钩子事件结构"""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    type: InternalHookEventType
    action: str
    session_key: str
    context: dict[str, object] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)
    messages: list[str] = Field(default_factory=list)


# 钩子处理器类型
HookHandler = Callable[[InternalHookEvent], Awaitable[None]]


class HookRequirements(BaseModel):
    """钩子依赖要求"""

    bins: list[str] = Field(default_factory=list, description="Required binaries")
    env: list[str] = Field(default_factory=list, description="Required env vars")
    python_packages: list[str] = Field(
        default_factory=list, description="Required Python packages"
    )


class HookMetadata(BaseModel):
    """钩子元数据 (从 HOOK.md frontmatter 解析)"""

    name: str
    emoji: str = "🔌"
    events: list[str] = Field(
        default_factory=list, description="Event patterns to listen to"
    )
    description: str = ""
    requires: HookRequirements = Field(default_factory=HookRequirements)
    enabled: bool = True
    priority: int = Field(default=100, description="Lower number = higher priority")


class HookPackage(BaseModel):
    """钩子包 (包含元数据和处理器)"""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    metadata: HookMetadata
    handler: HookHandler
    source_path: str
