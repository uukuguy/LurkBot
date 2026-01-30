"""
ACP 会话管理

管理 ACP 连接的会话状态
对标 MoltBot src/acp/session.ts
"""

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from typing import Literal
from loguru import logger


@dataclass
class ACPSession:
    """ACP 会话"""

    session_id: str
    cwd: str
    created_at: int  # timestamp ms
    active_run_id: str | None = None
    mode_id: str | None = None
    model_id: str | None = None
    status: Literal["active", "idle", "cancelled"] = "idle"
    metadata: dict = field(default_factory=dict)


@dataclass
class PendingPrompt:
    """等待中的 Prompt"""

    prompt_id: str
    session_id: str
    created_at: int
    future: asyncio.Future


class ACPSessionManager:
    """
    ACP 会话管理器

    管理多个 ACP 会话的生命周期
    """

    def __init__(self):
        self._sessions: dict[str, ACPSession] = {}
        self._pending_prompts: dict[str, PendingPrompt] = {}
        self._lock = asyncio.Lock()

    def create_session(self, cwd: str, session_id: str | None = None) -> ACPSession:
        """创建新会话"""
        if session_id is None:
            session_id = uuid.uuid4().hex[:16]

        session = ACPSession(
            session_id=session_id,
            cwd=cwd,
            created_at=int(time.time() * 1000),
        )

        self._sessions[session_id] = session
        logger.info(f"ACP Session created: {session_id}")
        return session

    def get_session(self, session_id: str) -> ACPSession | None:
        """获取会话"""
        return self._sessions.get(session_id)

    def load_session(self, session_id: str, cwd: str) -> ACPSession | None:
        """加载已存在的会话"""
        session = self._sessions.get(session_id)
        if session:
            session.cwd = cwd
            session.status = "idle"
            logger.info(f"ACP Session loaded: {session_id}")
        return session

    def list_sessions(self) -> list[ACPSession]:
        """列出所有会话"""
        return list(self._sessions.values())

    def delete_session(self, session_id: str) -> bool:
        """删除会话"""
        if session_id in self._sessions:
            del self._sessions[session_id]
            logger.info(f"ACP Session deleted: {session_id}")
            return True
        return False

    def set_active_run(self, session_id: str, run_id: str | None) -> None:
        """设置活跃的运行 ID"""
        session = self._sessions.get(session_id)
        if session:
            session.active_run_id = run_id
            session.status = "active" if run_id else "idle"

    def cancel_session(self, session_id: str) -> bool:
        """取消会话"""
        session = self._sessions.get(session_id)
        if session:
            session.status = "cancelled"
            session.active_run_id = None
            logger.info(f"ACP Session cancelled: {session_id}")
            return True
        return False

    def set_mode(self, session_id: str, mode_id: str) -> bool:
        """设置会话模式"""
        session = self._sessions.get(session_id)
        if session:
            session.mode_id = mode_id
            logger.debug(f"ACP Session {session_id} mode set to: {mode_id}")
            return True
        return False

    def set_model(self, session_id: str, model_id: str) -> bool:
        """设置会话模型"""
        session = self._sessions.get(session_id)
        if session:
            session.model_id = model_id
            logger.debug(f"ACP Session {session_id} model set to: {model_id}")
            return True
        return False

    async def create_pending_prompt(self, session_id: str) -> PendingPrompt:
        """创建待处理的 Prompt"""
        async with self._lock:
            prompt_id = uuid.uuid4().hex[:16]
            loop = asyncio.get_running_loop()
            future = loop.create_future()

            pending = PendingPrompt(
                prompt_id=prompt_id,
                session_id=session_id,
                created_at=int(time.time() * 1000),
                future=future,
            )

            self._pending_prompts[prompt_id] = pending
            return pending

    async def resolve_prompt(self, prompt_id: str, result: dict) -> bool:
        """解决待处理的 Prompt"""
        async with self._lock:
            pending = self._pending_prompts.pop(prompt_id, None)
            if pending and not pending.future.done():
                pending.future.set_result(result)
                return True
            return False

    async def reject_prompt(self, prompt_id: str, error: Exception) -> bool:
        """拒绝待处理的 Prompt"""
        async with self._lock:
            pending = self._pending_prompts.pop(prompt_id, None)
            if pending and not pending.future.done():
                pending.future.set_exception(error)
                return True
            return False

    def get_pending_prompt(self, prompt_id: str) -> PendingPrompt | None:
        """获取待处理的 Prompt"""
        return self._pending_prompts.get(prompt_id)

    def clear_pending_prompts(self, session_id: str) -> int:
        """清除会话的所有待处理 Prompt"""
        cleared = 0
        to_remove = []
        for prompt_id, pending in self._pending_prompts.items():
            if pending.session_id == session_id:
                if not pending.future.done():
                    pending.future.cancel()
                to_remove.append(prompt_id)
                cleared += 1

        for prompt_id in to_remove:
            del self._pending_prompts[prompt_id]

        return cleared


# 全局会话管理器实例
_session_manager = ACPSessionManager()


def get_session_manager() -> ACPSessionManager:
    """获取全局会话管理器"""
    return _session_manager
