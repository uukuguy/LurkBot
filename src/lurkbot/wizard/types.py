"""
Wizard 类型定义

对标 MoltBot wizard/prompts.ts 和 wizard/session.ts
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Literal


# ============================================================================
# 基础枚举类型
# ============================================================================


class WizardSessionStatus(str, Enum):
    """向导会话状态"""

    RUNNING = "running"
    DONE = "done"
    CANCELLED = "cancelled"
    ERROR = "error"


class WizardStepType(str, Enum):
    """向导步骤类型"""

    NOTE = "note"
    SELECT = "select"
    MULTISELECT = "multiselect"
    TEXT = "text"
    CONFIRM = "confirm"
    PROGRESS = "progress"
    ACTION = "action"


class WizardStepExecutor(str, Enum):
    """步骤执行者"""

    GATEWAY = "gateway"
    CLIENT = "client"


# ============================================================================
# Onboarding 相关类型
# ============================================================================

# 配置向导模式
OnboardMode = Literal["local", "remote"]

# 向导流程类型
WizardFlow = Literal["quickstart", "advanced"]

# 重置范围
ResetScope = Literal["config", "config+creds+sessions", "full"]

# Gateway 绑定模式
GatewayBindMode = Literal["loopback", "lan", "auto", "tailnet", "custom"]

# Gateway 认证方式
GatewayAuthChoice = Literal["token", "password"]

# Tailscale 暴露模式
TailscaleMode = Literal["off", "serve", "funnel"]


# ============================================================================
# 选项和步骤类型
# ============================================================================


@dataclass
class WizardSelectOption:
    """向导选择选项"""

    value: Any
    label: str
    hint: str | None = None


@dataclass
class WizardStep:
    """
    向导步骤

    对标 MoltBot WizardStep
    """

    id: str
    type: WizardStepType
    title: str | None = None
    message: str | None = None
    options: list[WizardSelectOption] | None = None
    initial_value: Any = None
    placeholder: str | None = None
    sensitive: bool = False
    executor: WizardStepExecutor = WizardStepExecutor.CLIENT


@dataclass
class WizardNextResult:
    """
    向导下一步结果

    对标 MoltBot WizardNextResult
    """

    done: bool
    step: WizardStep | None = None
    status: WizardSessionStatus = WizardSessionStatus.RUNNING
    error: str | None = None


# ============================================================================
# 配置选项类型
# ============================================================================


@dataclass
class OnboardOptions:
    """
    Onboarding 配置选项

    对标 MoltBot OnboardOptions
    """

    # 模式选项
    mode: OnboardMode | None = None
    flow: WizardFlow | None = None

    # 工作区
    workspace: str | None = None

    # 认证选项
    auth_choice: str | None = None
    token: str | None = None
    token_provider: str | None = None

    # 跳过选项
    accept_risk: bool = False
    skip_channels: bool = False
    skip_providers: bool = False
    skip_skills: bool = False


@dataclass
class QuickstartGatewayDefaults:
    """
    QuickStart 模式下的 Gateway 默认配置

    对标 MoltBot QuickstartGatewayDefaults
    """

    has_existing: bool = False
    port: int = 18789
    bind: GatewayBindMode = "loopback"
    auth_mode: GatewayAuthChoice = "token"
    tailscale_mode: TailscaleMode = "off"
    token: str | None = None
    password: str | None = None
    custom_bind_host: str | None = None
    tailscale_reset_on_exit: bool = False


@dataclass
class GatewaySettings:
    """
    Gateway 配置设置结果

    包含配置向导生成的 Gateway 配置
    """

    port: int = 18789
    bind: GatewayBindMode = "loopback"
    custom_bind_host: str | None = None
    auth_mode: GatewayAuthChoice = "token"
    token: str | None = None
    password: str | None = None
    tailscale_mode: TailscaleMode = "off"
    tailscale_reset_on_exit: bool = False


# ============================================================================
# 验证器
# ============================================================================


def is_valid_ipv4(ip: str) -> bool:
    """
    验证 IPv4 地址格式

    对标 MoltBot isValidIPv4()
    """
    parts = ip.split(".")
    if len(parts) != 4:
        return False

    for part in parts:
        try:
            num = int(part)
            if num < 0 or num > 255:
                return False
            # 检查前导零（可选，更严格的验证）
            if part != str(num):
                return False
        except ValueError:
            return False

    return True


def is_valid_port(port: int) -> bool:
    """验证端口号"""
    return 1 <= port <= 65535


# ============================================================================
# 常量
# ============================================================================

# 默认 Gateway 端口
DEFAULT_GATEWAY_PORT = 18789

# 默认工作区目录
DEFAULT_WORKSPACE = "~/.lurkbot/workspace"

# 安全警告文本
SECURITY_WARNING = """Security warning — please read.

LurkBot is a hobby project and still in beta. Expect sharp edges.
This bot can read files and run actions if tools are enabled.
A bad prompt can trick it into doing unsafe things.

If you're not comfortable with basic security and access control, don't run LurkBot.
Ask someone experienced to help before enabling tools or exposing it to the internet.

Recommended baseline:
- Pairing/allowlists + mention gating.
- Sandbox + least-privilege tools.
- Keep secrets out of the agent's reachable filesystem.
- Use the strongest available model for any bot with tools or untrusted inboxes.

Run regularly:
lurkbot security audit --deep
lurkbot security audit --fix
"""
