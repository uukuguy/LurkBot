"""Exec Approvals types.

对标 MoltBot `src/infra/exec-approvals.ts`
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Literal


class ExecHost(str, Enum):
    """执行主机类型"""

    SANDBOX = "sandbox"
    GATEWAY = "gateway"
    NODE = "node"


class ExecSecurity(str, Enum):
    """执行安全级别"""

    DENY = "deny"
    ALLOWLIST = "allowlist"
    FULL = "full"


class ExecAsk(str, Enum):
    """执行询问模式"""

    OFF = "off"
    ON_MISS = "on-miss"
    ALWAYS = "always"


@dataclass
class ExecApprovalsDefaults:
    """执行审批默认设置"""

    security: ExecSecurity = ExecSecurity.DENY
    ask: ExecAsk = ExecAsk.ON_MISS
    ask_fallback: ExecSecurity = ExecSecurity.DENY
    auto_allow_skills: bool = False


@dataclass
class ExecAllowlistEntry:
    """执行允许列表条目"""

    pattern: str
    id: str | None = None
    last_used_at: int | None = None
    last_used_command: str | None = None
    last_resolved_path: str | None = None


@dataclass
class ExecApprovalsAgent:
    """代理执行审批配置"""

    security: ExecSecurity | None = None
    ask: ExecAsk | None = None
    ask_fallback: ExecSecurity | None = None
    auto_allow_skills: bool | None = None
    allowlist: list[ExecAllowlistEntry] = field(default_factory=list)


@dataclass
class ExecApprovalsSocket:
    """执行审批 Socket 配置"""

    path: str | None = None
    token: str | None = None


@dataclass
class ExecApprovalsFile:
    """执行审批配置文件"""

    version: int = 1
    socket: ExecApprovalsSocket | None = None
    defaults: ExecApprovalsDefaults | None = None
    agents: dict[str, ExecApprovalsAgent] = field(default_factory=dict)


@dataclass
class ExecCheckResult:
    """执行检查结果"""

    allowed: bool
    reason: Literal["allowlist", "denied", "ask", "full"] | str
    matched_pattern: str | None = None
