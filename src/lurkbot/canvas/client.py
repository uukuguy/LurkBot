"""
Canvas Client 助手

为 Agent 提供便捷的 A2UI 消息生成 API。

对标 MoltBot src/agents/tools/canvas-tool.ts
"""

from __future__ import annotations

from typing import Any

from lurkbot.canvas.protocol import (
    A2UIMessage,
    ButtonSurface,
    CallbackAction,
    CardSurface,
    ContainerSurface,
    DataModelUpdateMessage,
    DeleteSurfaceMessage,
    ImageSurface,
    InputSurface,
    LinkSurface,
    ListSurface,
    ResetMessage,
    Surface,
    SurfaceUpdateMessage,
    TextSurface,
    to_jsonl,
)


class CanvasClient:
    """
    Canvas Client 助手

    提供 Agent 端的便捷 API，用于生成 A2UI 消息。

    示例:
        >>> client = CanvasClient()
        >>> jsonl = client.text("Hello World").to_jsonl()
        >>> # 发送 jsonl 到 Canvas Host
    """

    def __init__(self):
        self.messages: list[A2UIMessage] = []

    def surface_update(self, surface_id: str, surface: Surface) -> CanvasClient:
        """
        更新 Surface

        Args:
            surface_id: Surface ID
            surface: Surface 组件

        Returns:
            self (链式调用)
        """
        self.messages.append(SurfaceUpdateMessage(surface_id=surface_id, surface=surface))
        return self

    def data_update(self, path: str, value: Any) -> CanvasClient:
        """
        更新数据模型

        Args:
            path: 数据路径 (e.g. "user.name")
            value: 新值

        Returns:
            self (链式调用)
        """
        self.messages.append(DataModelUpdateMessage(path=path, value=value))
        return self

    def delete_surface(self, surface_id: str) -> CanvasClient:
        """
        删除 Surface

        Args:
            surface_id: Surface ID

        Returns:
            self (链式调用)
        """
        self.messages.append(DeleteSurfaceMessage(surface_id=surface_id))
        return self

    def reset(self) -> CanvasClient:
        """
        重置画布

        Returns:
            self (链式调用)
        """
        self.messages.append(ResetMessage())
        return self

    def to_jsonl(self) -> str:
        """
        转换为 JSONL 字符串

        Returns:
            JSONL 字符串
        """
        return to_jsonl(self.messages)

    def to_messages(self) -> list[A2UIMessage]:
        """
        获取消息列表

        Returns:
            A2UI 消息列表
        """
        return self.messages

    # ========================================================================
    # 便捷组件构建方法
    # ========================================================================

    def text(
        self,
        content: str,
        surface_id: str = "main",
        style: dict[str, Any] | None = None,
    ) -> CanvasClient:
        """
        添加文本组件

        Args:
            content: 文本内容
            surface_id: Surface ID
            style: CSS 样式

        Returns:
            self (链式调用)
        """
        surface = TextSurface(content=content, style=style)
        return self.surface_update(surface_id, surface)

    def image(
        self,
        src: str,
        surface_id: str = "main",
        alt: str | None = None,
        width: int | str | None = None,
        height: int | str | None = None,
    ) -> CanvasClient:
        """
        添加图片组件

        Args:
            src: 图片 URL
            surface_id: Surface ID
            alt: 替代文本
            width: 宽度
            height: 高度

        Returns:
            self (链式调用)
        """
        surface = ImageSurface(src=src, alt=alt, width=width, height=height)
        return self.surface_update(surface_id, surface)

    def button(
        self,
        label: str,
        callback_id: str,
        surface_id: str = "main",
        disabled: bool = False,
        style: dict[str, Any] | None = None,
    ) -> CanvasClient:
        """
        添加按钮组件

        Args:
            label: 按钮文本
            callback_id: 回调 ID
            surface_id: Surface ID
            disabled: 是否禁用
            style: CSS 样式

        Returns:
            self (链式调用)
        """
        surface = ButtonSurface(
            label=label,
            action=CallbackAction(id=callback_id),
            disabled=disabled,
            style=style,
        )
        return self.surface_update(surface_id, surface)

    def input(
        self,
        surface_id: str = "main",
        placeholder: str | None = None,
        value: str = "",
        input_type: str = "text",
        disabled: bool = False,
    ) -> CanvasClient:
        """
        添加输入框组件

        Args:
            surface_id: Surface ID
            placeholder: 占位符
            value: 初始值
            input_type: 输入类型 (text/password/email/number)
            disabled: 是否禁用

        Returns:
            self (链式调用)
        """
        surface = InputSurface(
            placeholder=placeholder,
            value=value,
            input_type=input_type,  # type: ignore
            disabled=disabled,
        )
        return self.surface_update(surface_id, surface)

    def link(
        self,
        href: str,
        text: str,
        surface_id: str = "main",
        target: str = "_blank",
    ) -> CanvasClient:
        """
        添加链接组件

        Args:
            href: 链接 URL
            text: 链接文本
            surface_id: Surface ID
            target: 目标窗口

        Returns:
            self (链式调用)
        """
        surface = LinkSurface(href=href, text=text, target=target)  # type: ignore
        return self.surface_update(surface_id, surface)

    def container(
        self,
        children: list[Surface],
        surface_id: str = "main",
        direction: str = "column",
        gap: int | None = None,
        style: dict[str, Any] | None = None,
    ) -> CanvasClient:
        """
        添加容器组件

        Args:
            children: 子组件列表
            surface_id: Surface ID
            direction: 排列方向 (row/column)
            gap: 子元素间距
            style: CSS 样式

        Returns:
            self (链式调用)
        """
        surface = ContainerSurface(
            children=children,
            direction=direction,  # type: ignore
            gap=gap,
            style=style,
        )
        return self.surface_update(surface_id, surface)

    def card(
        self,
        children: list[Surface],
        surface_id: str = "main",
        title: str | None = None,
        elevation: int = 1,
    ) -> CanvasClient:
        """
        添加卡片组件

        Args:
            children: 子组件列表
            surface_id: Surface ID
            title: 卡片标题
            elevation: 阴影层级 (1-5)

        Returns:
            self (链式调用)
        """
        surface = CardSurface(
            title=title,
            children=children,
            elevation=elevation,
        )
        return self.surface_update(surface_id, surface)

    def list_view(
        self,
        items: list[Surface],
        surface_id: str = "main",
        ordered: bool = False,
    ) -> CanvasClient:
        """
        添加列表组件

        Args:
            items: 列表项
            surface_id: Surface ID
            ordered: 是否有序列表

        Returns:
            self (链式调用)
        """
        surface = ListSurface(items=items, ordered=ordered)
        return self.surface_update(surface_id, surface)


# ============================================================================
# 便捷函数
# ============================================================================


def create_text_surface(content: str, style: dict[str, Any] | None = None) -> TextSurface:
    """创建文本 Surface"""
    return TextSurface(content=content, style=style)


def create_button_surface(
    label: str, callback_id: str, disabled: bool = False, style: dict[str, Any] | None = None
) -> ButtonSurface:
    """创建按钮 Surface"""
    return ButtonSurface(
        label=label,
        action=CallbackAction(id=callback_id),
        disabled=disabled,
        style=style,
    )


def create_image_surface(
    src: str,
    alt: str | None = None,
    width: int | str | None = None,
    height: int | str | None = None,
) -> ImageSurface:
    """创建图片 Surface"""
    return ImageSurface(src=src, alt=alt, width=width, height=height)


def create_container_surface(
    children: list[Surface],
    direction: str = "column",
    gap: int | None = None,
    style: dict[str, Any] | None = None,
) -> ContainerSurface:
    """创建容器 Surface"""
    return ContainerSurface(
        children=children,
        direction=direction,  # type: ignore
        gap=gap,
        style=style,
    )
