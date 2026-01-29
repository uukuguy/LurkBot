"""
Canvas Host - A2UI 界面系统

对标 MoltBot src/canvas-host/

提供 Agent-to-User Interface (A2UI) 支持，允许 Agent 生成声明式 UI。

主要模块:
- protocol: A2UI 消息类型和 Surface 组件定义
- server: Canvas Host 服务器，管理 WebSocket 连接和状态
- client: Agent 端便捷 API
"""

from lurkbot.canvas.protocol import (
    # 消息类型
    A2UIMessage,
    BeginRenderingMessage,
    CallbackAction,
    DataModelUpdateMessage,
    DeleteSurfaceMessage,
    ResetMessage,
    SurfaceUpdateMessage,
    # Surface 组件
    ButtonSurface,
    ContainerSurface,
    ImageSurface,
    InputSurface,
    Surface,
    TextSurface,
    # 工具函数
    parse_jsonl,
    to_jsonl,
)
from lurkbot.canvas.client import CanvasClient
from lurkbot.canvas.server import A2UIState, CanvasHost, get_canvas_host

__all__ = [
    # 消息类型
    "A2UIMessage",
    "SurfaceUpdateMessage",
    "DataModelUpdateMessage",
    "DeleteSurfaceMessage",
    "BeginRenderingMessage",
    "ResetMessage",
    # Surface 组件
    "Surface",
    "TextSurface",
    "ImageSurface",
    "ButtonSurface",
    "InputSurface",
    "ContainerSurface",
    # Action 类型
    "CallbackAction",
    # 服务器
    "CanvasHost",
    "A2UIState",
    "get_canvas_host",
    # 客户端
    "CanvasClient",
    # 工具函数
    "parse_jsonl",
    "to_jsonl",
]
