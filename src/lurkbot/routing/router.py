"""
Routing Router - 路由决策

对标 MoltBot src/routing/router.ts
"""

from dataclasses import dataclass
from typing import Literal


@dataclass
class RoutingContext:
    """
    路由上下文

    对标 MoltBot RoutingContext
    """
    channel: str
    peer_kind: Literal["dm", "group", "guild", "team"]
    peer_id: str
    account_id: str | None = None
    guild_id: str | None = None   # Discord
    team_id: str | None = None    # Slack


@dataclass
class RoutingBinding:
    """
    路由绑定配置

    对标 MoltBot RoutingBinding
    """
    agent_id: str
    channel: str | None = None
    peer_kind: str | None = None
    peer_id: str | None = None
    guild_id: str | None = None
    team_id: str | None = None
    account_id: str | None = None

    def match_peer(self, kind: str, peer_id: str) -> bool:
        """精确对等匹配"""
        return (
            self.peer_kind == kind
            and self.peer_id == peer_id
        )

    def match_guild(self, guild_id: str) -> bool:
        """Guild 匹配"""
        return self.guild_id == guild_id

    def match_team(self, team_id: str) -> bool:
        """Team 匹配"""
        return self.team_id == team_id

    def match_account(self, account_id: str) -> bool:
        """账户匹配"""
        return self.account_id == account_id

    def match_channel(self, channel: str) -> bool:
        """通道匹配"""
        return self.channel == channel


@dataclass
class AgentConfig:
    """Agent 配置"""
    id: str
    default: bool = False


def resolve_agent_for_message(
    ctx: RoutingContext,
    bindings: list[RoutingBinding],
    agents: list[AgentConfig],
) -> str:
    """
    路由决策流程（6 层）

    对标 MoltBot resolveAgentForMessage()

    层级顺序:
    1. 精确对等匹配 (bindings with peer.kind + peer.id)
    2. Guild 匹配 (Discord guildId)
    3. Team 匹配 (Slack teamId)
    4. 账户匹配 (channel accountId)
    5. 通道匹配 (任何该通道的账户)
    6. 默认 Agent (agents.list[].default 或首个)
    """
    # 1. 精确对等匹配
    for binding in bindings:
        if binding.match_peer(ctx.peer_kind, ctx.peer_id):
            return binding.agent_id

    # 2. Guild 匹配
    if ctx.guild_id:
        for binding in bindings:
            if binding.match_guild(ctx.guild_id):
                return binding.agent_id

    # 3. Team 匹配
    if ctx.team_id:
        for binding in bindings:
            if binding.match_team(ctx.team_id):
                return binding.agent_id

    # 4. 账户匹配
    if ctx.account_id:
        for binding in bindings:
            if binding.match_account(ctx.account_id):
                return binding.agent_id

    # 5. 通道匹配
    for binding in bindings:
        if binding.match_channel(ctx.channel):
            return binding.agent_id

    # 6. 默认 Agent
    for agent in agents:
        if agent.default:
            return agent.id

    return agents[0].id if agents else "main"

