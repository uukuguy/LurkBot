"""
ACP 事件映射器

将 Gateway 事件转换为 ACP Session 通知
对标 MoltBot src/acp/event_mapper.ts
"""

from typing import Callable, Awaitable
from loguru import logger

from lurkbot.acp.types import (
    SessionNotification,
    UserMessageChunk,
    AgentMessageChunk,
    AgentThoughtChunk,
    ToolCallStart,
    ToolCallProgress,
    AgentPlanUpdate,
    CurrentModeUpdate,
    SessionInfoUpdate,
    TextContentBlock,
    ContentBlock,
    PlanEntry,
    ModeInfo,
)
from lurkbot.gateway.protocol.frames import EventFrame


class EventMapper:
    """
    事件映射器

    将 Gateway 事件转换为 ACP 会话通知格式
    """

    def __init__(self):
        self._session_callback: Callable[[SessionNotification], Awaitable[None]] | None = None

    def set_session_callback(
        self, callback: Callable[[SessionNotification], Awaitable[None]]
    ) -> None:
        """设置会话通知回调"""
        self._session_callback = callback

    async def map_gateway_event(self, event: EventFrame, session_id: str) -> SessionNotification | None:
        """
        将 Gateway 事件映射为 ACP 会话通知

        Args:
            event: Gateway 事件帧
            session_id: ACP 会话 ID

        Returns:
            ACP 会话通知，如果事件无法映射则返回 None
        """
        payload = event.payload or {}

        # agent.message.* 事件
        if event.event.startswith("agent.message"):
            return self._map_agent_message_event(event.event, payload, session_id)

        # agent.thinking.* 事件
        if event.event.startswith("agent.thinking"):
            return self._map_agent_thinking_event(event.event, payload, session_id)

        # agent.tool.* 事件
        if event.event.startswith("agent.tool"):
            return self._map_tool_event(event.event, payload, session_id)

        # session.* 事件
        if event.event.startswith("session."):
            return self._map_session_event(event.event, payload, session_id)

        # 未知事件类型
        logger.debug(f"Unmapped Gateway event: {event.event}")
        return None

    def _map_agent_message_event(
        self, event: str, payload: dict, session_id: str
    ) -> SessionNotification | None:
        """映射 agent.message 事件"""
        content = payload.get("content", "")

        # 创建文本内容块
        content_block = TextContentBlock(text=content)

        if "user" in event:
            # 用户消息
            update = UserMessageChunk(content=content_block)
        else:
            # Agent 消息
            update = AgentMessageChunk(content=content_block)

        return SessionNotification(session_id=session_id, update=update)

    def _map_agent_thinking_event(
        self, event: str, payload: dict, session_id: str
    ) -> SessionNotification | None:
        """映射 agent.thinking 事件"""
        thinking_text = payload.get("thinking", payload.get("content", ""))

        content_block = TextContentBlock(text=thinking_text)
        update = AgentThoughtChunk(content=content_block)

        return SessionNotification(session_id=session_id, update=update)

    def _map_tool_event(
        self, event: str, payload: dict, session_id: str
    ) -> SessionNotification | None:
        """映射 agent.tool 事件"""
        tool_call_id = payload.get("toolCallId", payload.get("tool_call_id", ""))
        tool_name = payload.get("toolName", payload.get("tool_name", ""))

        if "start" in event:
            # 工具调用开始
            update = ToolCallStart(
                tool_call_id=tool_call_id,
                tool_name=tool_name,
                tool_input=payload.get("toolInput", payload.get("input")),
            )
        elif "progress" in event or "output" in event:
            # 工具调用进度
            output = payload.get("output", payload.get("content", ""))
            content_block: ContentBlock | None = None
            if output:
                content_block = TextContentBlock(text=str(output))

            update = ToolCallProgress(
                tool_call_id=tool_call_id,
                content=content_block,
            )
        else:
            logger.debug(f"Unmapped tool event: {event}")
            return None

        return SessionNotification(session_id=session_id, update=update)

    def _map_session_event(
        self, event: str, payload: dict, session_id: str
    ) -> SessionNotification | None:
        """映射 session 事件"""
        if "mode" in event:
            # 模式变更
            mode_id = payload.get("modeId", payload.get("mode_id"))
            mode_title = payload.get("modeTitle", payload.get("title", mode_id))

            mode_info = ModeInfo(
                id=mode_id,
                title=mode_title,
            ) if mode_id else None

            update = CurrentModeUpdate(mode=mode_info)
            return SessionNotification(session_id=session_id, update=update)

        if "info" in event:
            # 会话信息更新
            update = SessionInfoUpdate(
                session_id=session_id,
                title=payload.get("title"),
                cwd=payload.get("cwd"),
            )
            return SessionNotification(session_id=session_id, update=update)

        logger.debug(f"Unmapped session event: {event}")
        return None

    async def emit_notification(self, notification: SessionNotification) -> None:
        """发送会话通知"""
        if self._session_callback:
            try:
                await self._session_callback(notification)
            except Exception as e:
                logger.error(f"Error emitting session notification: {e}")


def text_block(text: str) -> TextContentBlock:
    """创建文本内容块的辅助函数"""
    return TextContentBlock(text=text)


def update_agent_message(content: ContentBlock) -> AgentMessageChunk:
    """创建 Agent 消息更新的辅助函数"""
    return AgentMessageChunk(content=content)


def update_user_message(content: ContentBlock) -> UserMessageChunk:
    """创建用户消息更新的辅助函数"""
    return UserMessageChunk(content=content)


def update_agent_thought(content: TextContentBlock) -> AgentThoughtChunk:
    """创建 Agent 思考更新的辅助函数"""
    return AgentThoughtChunk(content=content)


def start_tool_call(
    tool_call_id: str, tool_name: str, tool_input: dict | None = None
) -> ToolCallStart:
    """创建工具调用开始的辅助函数"""
    return ToolCallStart(
        tool_call_id=tool_call_id,
        tool_name=tool_name,
        tool_input=tool_input,
    )


def update_plan(entries: list[PlanEntry]) -> AgentPlanUpdate:
    """创建计划更新的辅助函数"""
    return AgentPlanUpdate(entries=entries)


def plan_entry(
    id: str,
    title: str,
    status: str = "pending",
) -> PlanEntry:
    """创建计划条目的辅助函数"""
    return PlanEntry(id=id, title=title, status=status)


# 全局事件映射器实例
_event_mapper = EventMapper()


def get_event_mapper() -> EventMapper:
    """获取全局事件映射器"""
    return _event_mapper
