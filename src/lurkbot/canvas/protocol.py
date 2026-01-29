"""
A2UI 协议定义

对标 MoltBot vendor/a2ui/schema/

定义 A2UI v0.8 消息格式和 Surface 组件类型。

参考:
- https://github.com/anthropics/a2ui
- MoltBot src/canvas-host/a2ui.ts
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal, Union

from pydantic import BaseModel, Field


# ============================================================================
# Action 类型
# ============================================================================


class ActionType(str, Enum):
    """Action 类型"""

    CALLBACK = "callback"
    NAVIGATE = "navigate"
    SUBMIT = "submit"


class CallbackAction(BaseModel):
    """回调 Action - 触发 Agent 回调"""

    type: Literal[ActionType.CALLBACK] = ActionType.CALLBACK
    id: str = Field(..., description="回调 ID，由 Agent 处理")


class NavigateAction(BaseModel):
    """导航 Action - 跳转 URL"""

    type: Literal[ActionType.NAVIGATE] = ActionType.NAVIGATE
    url: str = Field(..., description="目标 URL")
    target: Literal["_self", "_blank"] = "_self"


class SubmitAction(BaseModel):
    """提交 Action - 表单提交"""

    type: Literal[ActionType.SUBMIT] = ActionType.SUBMIT
    form_id: str = Field(..., description="表单 ID")


Action = Union[CallbackAction, NavigateAction, SubmitAction]


# ============================================================================
# Surface 组件类型
# ============================================================================


class SurfaceType(str, Enum):
    """Surface 组件类型"""

    TEXT = "text"
    IMAGE = "image"
    BUTTON = "button"
    INPUT = "input"
    LINK = "link"
    CONTAINER = "container"
    CARD = "card"
    LIST = "list"
    FORM = "form"
    SELECT = "select"


class TextSurface(BaseModel):
    """文本组件"""

    type: Literal[SurfaceType.TEXT] = SurfaceType.TEXT
    content: str = Field(..., description="文本内容")
    style: dict[str, Any] | None = Field(
        None, description="CSS 样式 (fontSize, color, etc.)"
    )


class ImageSurface(BaseModel):
    """图片组件"""

    type: Literal[SurfaceType.IMAGE] = SurfaceType.IMAGE
    src: str = Field(..., description="图片 URL")
    alt: str | None = Field(None, description="替代文本")
    width: int | str | None = None
    height: int | str | None = None


class ButtonSurface(BaseModel):
    """按钮组件"""

    type: Literal[SurfaceType.BUTTON] = SurfaceType.BUTTON
    label: str = Field(..., description="按钮文本")
    action: Action = Field(..., description="点击 Action")
    disabled: bool = False
    style: dict[str, Any] | None = None


class InputSurface(BaseModel):
    """输入框组件"""

    type: Literal[SurfaceType.INPUT] = SurfaceType.INPUT
    placeholder: str | None = None
    value: str = ""
    input_type: Literal["text", "password", "email", "number"] = "text"
    disabled: bool = False


class LinkSurface(BaseModel):
    """链接组件"""

    type: Literal[SurfaceType.LINK] = SurfaceType.LINK
    href: str = Field(..., description="链接 URL")
    text: str = Field(..., description="链接文本")
    target: Literal["_self", "_blank"] = "_blank"


class ContainerSurface(BaseModel):
    """容器组件"""

    type: Literal[SurfaceType.CONTAINER] = SurfaceType.CONTAINER
    direction: Literal["row", "column"] = "column"
    children: list["Surface"] = Field(default_factory=list)
    gap: int | None = Field(None, description="子元素间距 (px)")
    style: dict[str, Any] | None = None


class CardSurface(BaseModel):
    """卡片组件"""

    type: Literal[SurfaceType.CARD] = SurfaceType.CARD
    title: str | None = None
    children: list["Surface"] = Field(default_factory=list)
    elevation: int = 1  # 1-5


class ListSurface(BaseModel):
    """列表组件"""

    type: Literal[SurfaceType.LIST] = SurfaceType.LIST
    items: list["Surface"] = Field(default_factory=list)
    ordered: bool = False


class FormSurface(BaseModel):
    """表单组件"""

    type: Literal[SurfaceType.FORM] = SurfaceType.FORM
    form_id: str = Field(..., description="表单唯一 ID")
    fields: list["Surface"] = Field(default_factory=list)
    submit_action: Action | None = None


class SelectSurface(BaseModel):
    """下拉选择组件"""

    type: Literal[SurfaceType.SELECT] = SurfaceType.SELECT
    options: list[dict[str, str]] = Field(
        default_factory=list, description='[{"label": "...", "value": "..."}]'
    )
    value: str | None = None
    placeholder: str | None = None


# Surface 联合类型
Surface = Union[
    TextSurface,
    ImageSurface,
    ButtonSurface,
    InputSurface,
    LinkSurface,
    ContainerSurface,
    CardSurface,
    ListSurface,
    FormSurface,
    SelectSurface,
]

# 更新 ContainerSurface 的 forward ref
ContainerSurface.model_rebuild()
CardSurface.model_rebuild()
ListSurface.model_rebuild()
FormSurface.model_rebuild()


# ============================================================================
# A2UI 消息类型
# ============================================================================


class MessageType(str, Enum):
    """A2UI 消息类型"""

    SURFACE_UPDATE = "surfaceUpdate"
    DATA_MODEL_UPDATE = "dataModelUpdate"
    DELETE_SURFACE = "deleteSurface"
    BEGIN_RENDERING = "beginRendering"
    RESET = "reset"


class SurfaceUpdateMessage(BaseModel):
    """更新 Surface 组件"""

    type: Literal[MessageType.SURFACE_UPDATE] = MessageType.SURFACE_UPDATE
    surface_id: str = Field(..., alias="surfaceId", description="Surface 唯一 ID")
    surface: Surface = Field(..., description="Surface 组件定义")

    class Config:
        populate_by_name = True


class DataModelUpdateMessage(BaseModel):
    """更新数据模型"""

    type: Literal[MessageType.DATA_MODEL_UPDATE] = MessageType.DATA_MODEL_UPDATE
    path: str = Field(..., description="数据路径 (dot notation, e.g. user.name)")
    value: Any = Field(..., description="新值")


class DeleteSurfaceMessage(BaseModel):
    """删除 Surface"""

    type: Literal[MessageType.DELETE_SURFACE] = MessageType.DELETE_SURFACE
    surface_id: str = Field(..., alias="surfaceId", description="要删除的 Surface ID")

    class Config:
        populate_by_name = True


class BeginRenderingMessage(BaseModel):
    """开始渲染标记"""

    type: Literal[MessageType.BEGIN_RENDERING] = MessageType.BEGIN_RENDERING
    session_id: str = Field(..., alias="sessionId", description="会话 ID")

    class Config:
        populate_by_name = True


class ResetMessage(BaseModel):
    """重置画布"""

    type: Literal[MessageType.RESET] = MessageType.RESET


# A2UI 消息联合类型
A2UIMessage = Union[
    SurfaceUpdateMessage,
    DataModelUpdateMessage,
    DeleteSurfaceMessage,
    BeginRenderingMessage,
    ResetMessage,
]


# ============================================================================
# 工具函数
# ============================================================================


def parse_jsonl(jsonl: str) -> list[A2UIMessage]:
    """
    解析 JSONL 格式的 A2UI 消息

    Args:
        jsonl: JSONL 字符串（每行一个 JSON 对象）

    Returns:
        A2UI 消息列表

    Raises:
        ValueError: JSONL 格式错误
    """
    import json

    messages: list[A2UIMessage] = []

    for line_num, line in enumerate(jsonl.strip().split("\n"), 1):
        line = line.strip()
        if not line:
            continue

        try:
            data = json.loads(line)
        except json.JSONDecodeError as e:
            raise ValueError(f"Line {line_num}: Invalid JSON - {e}") from e

        # 根据 type 字段解析
        msg_type = data.get("type")
        try:
            if msg_type == MessageType.SURFACE_UPDATE:
                messages.append(SurfaceUpdateMessage.model_validate(data))
            elif msg_type == MessageType.DATA_MODEL_UPDATE:
                messages.append(DataModelUpdateMessage.model_validate(data))
            elif msg_type == MessageType.DELETE_SURFACE:
                messages.append(DeleteSurfaceMessage.model_validate(data))
            elif msg_type == MessageType.BEGIN_RENDERING:
                messages.append(BeginRenderingMessage.model_validate(data))
            elif msg_type == MessageType.RESET:
                messages.append(ResetMessage.model_validate(data))
            else:
                raise ValueError(f"Unknown message type: {msg_type}")
        except Exception as e:
            raise ValueError(f"Line {line_num}: Validation error - {e}") from e

    return messages


def to_jsonl(messages: list[A2UIMessage]) -> str:
    """
    将 A2UI 消息列表转换为 JSONL 格式

    Args:
        messages: A2UI 消息列表

    Returns:
        JSONL 字符串
    """
    lines = [msg.model_dump_json(by_alias=True) for msg in messages]
    return "\n".join(lines)
