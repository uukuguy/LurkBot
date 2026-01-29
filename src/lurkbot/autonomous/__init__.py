"""Autonomous operation systems.

Ported from moltbot/src/infra/heartbeat-runner.ts and cron-related modules.

This module contains autonomous operation infrastructure:
- heartbeat/: Heartbeat system with events and HEARTBEAT_OK token
- cron/: Cron service with at/every/cron schedules

MoltBot autonomous running capabilities:
1. Heartbeat: Periodic agent wake-up and task checking
2. Cron: Scheduled task execution with two payload types
3. Subagent: Delegated task execution (implemented in agents/subagent/)
"""

from lurkbot.autonomous.heartbeat import (
    ActiveHours,
    HeartbeatConfig,
    HeartbeatEventPayload,
    HeartbeatRunner,
    HEARTBEAT_OK_TOKEN,
    DEFAULT_HEARTBEAT_EVERY,
    DEFAULT_HEARTBEAT_ACK_MAX_CHARS,
    DEFAULT_HEARTBEAT_TARGET,
)
from lurkbot.autonomous.cron import (
    CronSchedule,
    CronScheduleAt,
    CronScheduleEvery,
    CronScheduleCron,
    CronPayload,
    SystemEventPayload,
    AgentTurnPayload,
    CronJobState,
    CronJob,
    CronService,
    CronServiceStatus,
    CronRunResult,
)

__all__ = [
    # Heartbeat
    "ActiveHours",
    "HeartbeatConfig",
    "HeartbeatEventPayload",
    "HeartbeatRunner",
    "HEARTBEAT_OK_TOKEN",
    "DEFAULT_HEARTBEAT_EVERY",
    "DEFAULT_HEARTBEAT_ACK_MAX_CHARS",
    "DEFAULT_HEARTBEAT_TARGET",
    # Cron
    "CronSchedule",
    "CronScheduleAt",
    "CronScheduleEvery",
    "CronScheduleCron",
    "CronPayload",
    "SystemEventPayload",
    "AgentTurnPayload",
    "CronJobState",
    "CronJob",
    "CronService",
    "CronServiceStatus",
    "CronRunResult",
]
