"""
ACP 协议翻译器

将 ACP 协议消息翻译为 Gateway 协议
对标 MoltBot src/acp/translator.ts
"""

import asyncio
import uuid
from typing import Any
from loguru import logger

from lurkbot.acp.types import (
    ContentBlock,
    TextContentBlock,
    ImageContentBlock,
    StopReason,
    SessionNotification,
    PromptResponse,
)
from lurkbot.acp.session import ACPSession, get_session_manager
from lurkbot.acp.event_mapper import get_event_mapper
from lurkbot.gateway.events import get_event_broadcaster, EventSubscriber
from lurkbot.gateway.methods import get_method_registry, MethodContext
from lurkbot.gateway.protocol.frames import EventFrame


class ACPGatewayTranslator:
    """
    ACP Gateway 翻译器

    负责在 ACP 协议和 Gateway 协议之间进行翻译
    """

    def __init__(self):
        self._session_manager = get_session_manager()
        self._event_broadcaster = get_event_broadcaster()
        self._method_registry = get_method_registry()
        self._event_mapper = get_event_mapper()
        self._active_subscriptions: dict[str, EventSubscriber] = {}

    async def translate_prompt(
        self,
        session_id: str,
        prompt: list[ContentBlock],
    ) -> PromptResponse:
        """
        翻译 ACP prompt 请求到 Gateway

        Args:
            session_id: ACP 会话 ID
            prompt: ACP prompt 内容块列表

        Returns:
            ACP PromptResponse
        """
        session = self._session_manager.get_session(session_id)
        if not session:
            logger.error(f"Session not found: {session_id}")
            return PromptResponse(stop_reason=StopReason.ERROR)

        # 生成运行 ID
        run_id = uuid.uuid4().hex[:16]
        self._session_manager.set_active_run(session_id, run_id)

        try:
            # 转换 prompt 为文本
            prompt_text = self._extract_prompt_text(prompt)

            # 调用 Gateway 方法
            result = await self._method_registry.invoke(
                "agent.prompt",
                params={
                    "prompt": prompt_text,
                    "runId": run_id,
                },
                session_key=session_id,
            )

            # 解析结果
            stop_reason = StopReason.END_TURN
            if result:
                reason = result.get("stopReason", "end_turn")
                if reason in [r.value for r in StopReason]:
                    stop_reason = StopReason(reason)

            return PromptResponse(stop_reason=stop_reason)

        except asyncio.CancelledError:
            return PromptResponse(stop_reason=StopReason.CANCELLED)
        except Exception as e:
            logger.error(f"Error translating prompt: {e}")
            return PromptResponse(stop_reason=StopReason.ERROR)
        finally:
            self._session_manager.set_active_run(session_id, None)

    def _extract_prompt_text(self, prompt: list[ContentBlock]) -> str:
        """从内容块列表中提取文本"""
        texts = []
        for block in prompt:
            if isinstance(block, TextContentBlock):
                texts.append(block.text)
            elif isinstance(block, dict):
                # 处理字典形式的内容块
                if block.get("type") == "text":
                    texts.append(block.get("text", ""))
        return "\n".join(texts)

    async def subscribe_to_events(
        self,
        session_id: str,
        callback,
    ) -> None:
        """
        订阅 Gateway 事件并转换为 ACP 通知

        Args:
            session_id: ACP 会话 ID
            callback: 接收 SessionNotification 的回调函数
        """
        if session_id in self._active_subscriptions:
            # 已经订阅，先取消
            await self.unsubscribe_from_events(session_id)

        async def event_handler(event: EventFrame) -> None:
            """处理 Gateway 事件"""
            notification = await self._event_mapper.map_gateway_event(event, session_id)
            if notification:
                try:
                    await callback(notification)
                except Exception as e:
                    logger.error(f"Error in event callback: {e}")

        # 订阅事件
        subscriber = self._event_broadcaster.subscribe(
            callback=event_handler,
            session_key=session_id,
        )
        self._active_subscriptions[session_id] = subscriber
        logger.debug(f"Subscribed to events for session: {session_id}")

    async def unsubscribe_from_events(self, session_id: str) -> None:
        """取消事件订阅"""
        subscriber = self._active_subscriptions.pop(session_id, None)
        if subscriber:
            self._event_broadcaster.unsubscribe(subscriber)
            logger.debug(f"Unsubscribed from events for session: {session_id}")

    async def cancel_run(self, session_id: str) -> bool:
        """
        取消正在运行的 prompt

        Args:
            session_id: ACP 会话 ID

        Returns:
            是否成功取消
        """
        session = self._session_manager.get_session(session_id)
        if not session or not session.active_run_id:
            return False

        try:
            # 调用 Gateway 取消方法
            await self._method_registry.invoke(
                "agent.cancel",
                params={"runId": session.active_run_id},
                session_key=session_id,
            )
            self._session_manager.cancel_session(session_id)
            return True
        except Exception as e:
            logger.error(f"Error cancelling run: {e}")
            return False

    async def read_file(self, session_id: str, path: str, line: int | None = None, limit: int | None = None) -> dict:
        """
        通过 Gateway 读取文件

        Args:
            session_id: ACP 会话 ID
            path: 文件路径
            line: 起始行号
            limit: 读取行数限制

        Returns:
            包含 content 和 truncated 的字典
        """
        try:
            result = await self._method_registry.invoke(
                "fs.read",
                params={
                    "path": path,
                    "line": line,
                    "limit": limit,
                },
                session_key=session_id,
            )
            return result or {"content": "", "truncated": False}
        except Exception as e:
            logger.error(f"Error reading file: {e}")
            raise

    async def write_file(self, session_id: str, path: str, content: str) -> bool:
        """
        通过 Gateway 写入文件

        Args:
            session_id: ACP 会话 ID
            path: 文件路径
            content: 文件内容

        Returns:
            是否成功
        """
        try:
            await self._method_registry.invoke(
                "fs.write",
                params={
                    "path": path,
                    "content": content,
                },
                session_key=session_id,
            )
            return True
        except Exception as e:
            logger.error(f"Error writing file: {e}")
            return False

    async def create_terminal(
        self,
        session_id: str,
        command: str,
        args: list[str] | None = None,
        cwd: str | None = None,
        env: dict[str, str] | None = None,
    ) -> str | None:
        """
        通过 Gateway 创建终端

        Args:
            session_id: ACP 会话 ID
            command: 命令
            args: 参数列表
            cwd: 工作目录
            env: 环境变量

        Returns:
            终端 ID 或 None
        """
        try:
            result = await self._method_registry.invoke(
                "terminal.create",
                params={
                    "command": command,
                    "args": args or [],
                    "cwd": cwd,
                    "env": env or {},
                },
                session_key=session_id,
            )
            return result.get("terminalId") if result else None
        except Exception as e:
            logger.error(f"Error creating terminal: {e}")
            return None


# 全局翻译器实例
_translator = ACPGatewayTranslator()


def get_translator() -> ACPGatewayTranslator:
    """获取全局翻译器"""
    return _translator
