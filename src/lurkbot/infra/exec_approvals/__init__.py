"""Exec Approvals Management.

命令执行允许列表和审批工作流。

对标 MoltBot `src/infra/exec-approvals.ts`
"""

import asyncio
import json
import os
import re
import secrets
import time
from base64 import urlsafe_b64encode
from pathlib import Path
from typing import Any

from .types import (
    ExecAllowlistEntry,
    ExecApprovalsAgent,
    ExecApprovalsDefaults,
    ExecApprovalsFile,
    ExecApprovalsSocket,
    ExecAsk,
    ExecCheckResult,
    ExecSecurity,
)

__all__ = [
    "ExecSecurity",
    "ExecAsk",
    "ExecApprovalsDefaults",
    "ExecAllowlistEntry",
    "ExecApprovalsAgent",
    "ExecApprovalsSocket",
    "ExecApprovalsFile",
    "ExecCheckResult",
    "ExecApprovalsManager",
    "exec_approvals_manager",
    "load_exec_approvals",
    "save_exec_approvals",
    "check_exec_allowed",
    "add_to_allowlist",
]

# 默认路径
DEFAULT_EXEC_APPROVALS_FILE = Path.home() / ".lurkbot" / "exec-approvals.json"
DEFAULT_EXEC_APPROVALS_SOCKET = Path.home() / ".lurkbot" / "exec-approvals.sock"


def _generate_token() -> str:
    """生成 24 字节 base64url 令牌。"""
    return urlsafe_b64encode(secrets.token_bytes(24)).decode("ascii").rstrip("=")


def _get_ms_timestamp() -> int:
    """获取毫秒时间戳。"""
    return int(time.time() * 1000)


class ExecApprovalsManager:
    """
    执行审批管理器。

    管理命令执行的允许列表和审批工作流。

    对标 MoltBot exec-approvals.ts
    """

    def __init__(
        self,
        file_path: Path | None = None,
        socket_path: Path | None = None,
    ) -> None:
        self._file_path = file_path or DEFAULT_EXEC_APPROVALS_FILE
        self._socket_path = socket_path or DEFAULT_EXEC_APPROVALS_SOCKET
        self._lock = asyncio.Lock()
        self._data: ExecApprovalsFile | None = None

    async def _ensure_dir(self) -> None:
        """确保目录存在。"""
        self._file_path.parent.mkdir(parents=True, exist_ok=True)

    async def load(self, *, force: bool = False) -> ExecApprovalsFile:
        """
        加载配置。

        Args:
            force: 是否强制重新加载

        Returns:
            配置文件
        """
        if not force and self._data is not None:
            return self._data

        async with self._lock:
            if not self._file_path.exists():
                # 创建默认配置
                self._data = self._create_default()
                await self._save_internal()
                return self._data

            try:
                raw = json.loads(self._file_path.read_text())
                self._data = self._parse(raw)
            except (json.JSONDecodeError, KeyError):
                self._data = self._create_default()

            return self._data

    def _create_default(self) -> ExecApprovalsFile:
        """创建默认配置。"""
        return ExecApprovalsFile(
            version=1,
            socket=ExecApprovalsSocket(
                path=str(self._socket_path),
                token=_generate_token(),
            ),
            defaults=ExecApprovalsDefaults(
                security=ExecSecurity.DENY,
                ask=ExecAsk.ON_MISS,
                ask_fallback=ExecSecurity.DENY,
                auto_allow_skills=False,
            ),
            agents={},
        )

    def _parse(self, raw: dict[str, Any]) -> ExecApprovalsFile:
        """解析配置 JSON。"""
        # 解析 socket
        socket_data = raw.get("socket", {})
        socket_config = ExecApprovalsSocket(
            path=socket_data.get("path"),
            token=socket_data.get("token"),
        )

        # 解析 defaults
        defaults_data = raw.get("defaults", {})
        defaults = ExecApprovalsDefaults(
            security=ExecSecurity(defaults_data.get("security", "deny")),
            ask=ExecAsk(defaults_data.get("ask", "on-miss")),
            ask_fallback=ExecSecurity(defaults_data.get("askFallback", "deny")),
            auto_allow_skills=defaults_data.get("autoAllowSkills", False),
        )

        # 解析 agents
        agents: dict[str, ExecApprovalsAgent] = {}
        for agent_id, agent_data in raw.get("agents", {}).items():
            # 解析 allowlist
            allowlist: list[ExecAllowlistEntry] = []
            for entry in agent_data.get("allowlist", []):
                allowlist.append(
                    ExecAllowlistEntry(
                        pattern=entry.get("pattern", ""),
                        id=entry.get("id"),
                        last_used_at=entry.get("lastUsedAt"),
                        last_used_command=entry.get("lastUsedCommand"),
                        last_resolved_path=entry.get("lastResolvedPath"),
                    )
                )

            agents[agent_id] = ExecApprovalsAgent(
                security=ExecSecurity(agent_data["security"]) if "security" in agent_data else None,
                ask=ExecAsk(agent_data["ask"]) if "ask" in agent_data else None,
                ask_fallback=ExecSecurity(agent_data["askFallback"]) if "askFallback" in agent_data else None,
                auto_allow_skills=agent_data.get("autoAllowSkills"),
                allowlist=allowlist,
            )

        return ExecApprovalsFile(
            version=raw.get("version", 1),
            socket=socket_config,
            defaults=defaults,
            agents=agents,
        )

    async def _save_internal(self) -> None:
        """保存配置（内部使用，需要持有锁）。"""
        if not self._data:
            return

        await self._ensure_dir()

        raw: dict[str, Any] = {"version": self._data.version}

        # Socket
        if self._data.socket:
            raw["socket"] = {
                "path": self._data.socket.path,
                "token": self._data.socket.token,
            }

        # Defaults
        if self._data.defaults:
            raw["defaults"] = {
                "security": self._data.defaults.security.value,
                "ask": self._data.defaults.ask.value,
                "askFallback": self._data.defaults.ask_fallback.value,
                "autoAllowSkills": self._data.defaults.auto_allow_skills,
            }

        # Agents
        raw["agents"] = {}
        for agent_id, agent in self._data.agents.items():
            agent_raw: dict[str, Any] = {}
            if agent.security is not None:
                agent_raw["security"] = agent.security.value
            if agent.ask is not None:
                agent_raw["ask"] = agent.ask.value
            if agent.ask_fallback is not None:
                agent_raw["askFallback"] = agent.ask_fallback.value
            if agent.auto_allow_skills is not None:
                agent_raw["autoAllowSkills"] = agent.auto_allow_skills

            agent_raw["allowlist"] = []
            for entry in agent.allowlist:
                entry_raw = {"pattern": entry.pattern}
                if entry.id:
                    entry_raw["id"] = entry.id
                if entry.last_used_at:
                    entry_raw["lastUsedAt"] = entry.last_used_at
                if entry.last_used_command:
                    entry_raw["lastUsedCommand"] = entry.last_used_command
                if entry.last_resolved_path:
                    entry_raw["lastResolvedPath"] = entry.last_resolved_path
                agent_raw["allowlist"].append(entry_raw)

            raw["agents"][agent_id] = agent_raw

        # 原子写入
        temp_file = self._file_path.with_suffix(".tmp")
        temp_file.write_text(json.dumps(raw, indent=2))
        os.chmod(temp_file, 0o600)
        temp_file.rename(self._file_path)

    async def save(self) -> None:
        """保存配置。"""
        async with self._lock:
            await self._save_internal()

    def _get_effective_config(
        self,
        agent_id: str | None,
    ) -> tuple[ExecSecurity, ExecAsk, ExecSecurity, bool]:
        """
        获取有效配置（合并默认和代理配置）。

        Returns:
            (security, ask, ask_fallback, auto_allow_skills)
        """
        defaults = self._data.defaults or ExecApprovalsDefaults()

        security = defaults.security
        ask = defaults.ask
        ask_fallback = defaults.ask_fallback
        auto_allow_skills = defaults.auto_allow_skills

        if agent_id and agent_id in self._data.agents:
            agent = self._data.agents[agent_id]
            if agent.security is not None:
                security = agent.security
            if agent.ask is not None:
                ask = agent.ask
            if agent.ask_fallback is not None:
                ask_fallback = agent.ask_fallback
            if agent.auto_allow_skills is not None:
                auto_allow_skills = agent.auto_allow_skills

        return security, ask, ask_fallback, auto_allow_skills

    async def check(
        self,
        command: str,
        *,
        agent_id: str | None = None,
        is_skill: bool = False,
    ) -> ExecCheckResult:
        """
        检查命令是否允许执行。

        Args:
            command: 要执行的命令
            agent_id: 代理 ID
            is_skill: 是否是技能调用

        Returns:
            检查结果
        """
        await self.load()

        security, ask, ask_fallback, auto_allow_skills = self._get_effective_config(agent_id)

        # 技能自动允许
        if is_skill and auto_allow_skills:
            return ExecCheckResult(allowed=True, reason="skill")

        # 完全允许模式
        if security == ExecSecurity.FULL:
            return ExecCheckResult(allowed=True, reason="full")

        # 拒绝模式
        if security == ExecSecurity.DENY:
            if ask == ExecAsk.OFF:
                return ExecCheckResult(allowed=False, reason="denied")
            return ExecCheckResult(allowed=False, reason="ask")

        # 允许列表模式
        if security == ExecSecurity.ALLOWLIST:
            # 检查允许列表
            allowlist: list[ExecAllowlistEntry] = []
            if agent_id and agent_id in self._data.agents:
                allowlist = self._data.agents[agent_id].allowlist

            for entry in allowlist:
                try:
                    if re.match(entry.pattern, command):
                        # 更新使用记录
                        entry.last_used_at = _get_ms_timestamp()
                        entry.last_used_command = command
                        await self.save()

                        return ExecCheckResult(
                            allowed=True,
                            reason="allowlist",
                            matched_pattern=entry.pattern,
                        )
                except re.error:
                    continue

            # 未匹配
            if ask == ExecAsk.OFF:
                return ExecCheckResult(allowed=False, reason="denied")
            if ask == ExecAsk.ALWAYS:
                return ExecCheckResult(allowed=False, reason="ask")
            if ask == ExecAsk.ON_MISS:
                return ExecCheckResult(allowed=False, reason="ask")

        return ExecCheckResult(allowed=False, reason="denied")

    async def add_to_allowlist(
        self,
        pattern: str,
        *,
        agent_id: str = "default",
    ) -> ExecAllowlistEntry:
        """
        添加模式到允许列表。

        Args:
            pattern: 正则模式
            agent_id: 代理 ID

        Returns:
            新条目
        """
        await self.load()

        async with self._lock:
            if agent_id not in self._data.agents:
                self._data.agents[agent_id] = ExecApprovalsAgent()

            entry = ExecAllowlistEntry(
                pattern=pattern,
                id=secrets.token_hex(4),
            )

            self._data.agents[agent_id].allowlist.append(entry)
            await self._save_internal()

            return entry

    async def remove_from_allowlist(
        self,
        pattern: str,
        *,
        agent_id: str = "default",
    ) -> bool:
        """
        从允许列表移除模式。

        Args:
            pattern: 正则模式
            agent_id: 代理 ID

        Returns:
            是否成功
        """
        await self.load()

        async with self._lock:
            if agent_id not in self._data.agents:
                return False

            agent = self._data.agents[agent_id]
            original_len = len(agent.allowlist)
            agent.allowlist = [e for e in agent.allowlist if e.pattern != pattern]

            if len(agent.allowlist) < original_len:
                await self._save_internal()
                return True

            return False

    async def list_allowlist(
        self,
        *,
        agent_id: str = "default",
    ) -> list[ExecAllowlistEntry]:
        """
        列出允许列表。

        Args:
            agent_id: 代理 ID

        Returns:
            允许列表
        """
        await self.load()

        if agent_id not in self._data.agents:
            return []

        return list(self._data.agents[agent_id].allowlist)


# 全局实例
exec_approvals_manager = ExecApprovalsManager()


# 便捷函数
async def load_exec_approvals(*, force: bool = False) -> ExecApprovalsFile:
    """加载执行审批配置。"""
    return await exec_approvals_manager.load(force=force)


async def save_exec_approvals() -> None:
    """保存执行审批配置。"""
    await exec_approvals_manager.save()


async def check_exec_allowed(
    command: str,
    *,
    agent_id: str | None = None,
    is_skill: bool = False,
) -> ExecCheckResult:
    """检查命令是否允许执行。"""
    return await exec_approvals_manager.check(
        command,
        agent_id=agent_id,
        is_skill=is_skill,
    )


async def add_to_allowlist(
    pattern: str,
    *,
    agent_id: str = "default",
) -> ExecAllowlistEntry:
    """添加模式到允许列表。"""
    return await exec_approvals_manager.add_to_allowlist(pattern, agent_id=agent_id)
