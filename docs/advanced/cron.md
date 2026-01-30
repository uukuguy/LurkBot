# Cron Jobs

Schedule recurring tasks with LurkBot's built-in cron system.

## Overview

Cron jobs allow you to:

- Send scheduled messages
- Run periodic tasks
- Automate maintenance
- Create reminders

## Implementation

Source: `src/lurkbot/tools/builtin/cron_tool.py`

LurkBot 的 Cron 系统作为内置 Tool 实现，对标 MoltBot 的 cron-tool。

| 组件 | 描述 |
|------|------|
| `CronJob` | 完整的 cron job 定义 |
| `CronSchedule` | 调度类型：at, every, cron |
| `CronPayload` | 执行负载：systemEvent, agentTurn |
| `CronStore` | 内存存储（占位实现） |

## Schedule Types

Source: `src/lurkbot/tools/builtin/cron_tool.py:47-86`

LurkBot 支持三种调度类型：

### 1. AT - 单次执行

在特定时间执行一次：

```python
class CronScheduleAt(BaseModel):
    """Single execution schedule."""

    kind: Literal["at"] = "at"
    at_ms: int  # 执行时间戳（毫秒）
```

示例：

```json
{
  "kind": "at",
  "atMs": 1706700000000
}
```

### 2. EVERY - 周期执行

按固定间隔周期执行：

```python
class CronScheduleEvery(BaseModel):
    """Periodic execution schedule."""

    kind: Literal["every"] = "every"
    every_ms: int       # 间隔时间（毫秒）
    anchor_ms: int | None  # 锚点时间（可选）
```

示例：

```json
{
  "kind": "every",
  "everyMs": 3600000,     // 每小时
  "anchorMs": 1706700000000
}
```

### 3. CRON - Cron 表达式

使用标准 cron 表达式：

```python
class CronScheduleCron(BaseModel):
    """Cron expression schedule."""

    kind: Literal["cron"] = "cron"
    expr: str           # cron 表达式
    tz: str | None      # 时区（可选）
```

示例：

```json
{
  "kind": "cron",
  "expr": "0 9 * * *",   // 每天 9:00
  "tz": "America/New_York"
}
```

## Payload Types

Source: `src/lurkbot/tools/builtin/cron_tool.py:55-110`

### 1. systemEvent - 系统事件

向主会话注入文本事件：

```python
class SystemEventPayload(BaseModel):
    """System event payload."""

    kind: Literal["systemEvent"] = "systemEvent"
    text: str  # 要注入的文本内容
```

示例：

```json
{
  "kind": "systemEvent",
  "text": "Good morning! Time to check your emails."
}
```

### 2. agentTurn - 代理任务

在独立会话中运行代理任务：

```python
class AgentTurnPayload(BaseModel):
    """Agent turn payload for running tasks."""

    kind: Literal["agentTurn"] = "agentTurn"
    message: str                # 任务消息
    model: str | None           # 模型（可选）
    thinking: str | None        # 思考模式（可选）
    timeout_seconds: int | None # 超时时间（可选）
    deliver: bool | None        # 是否发送结果（可选）
    channel: str | None         # 目标频道（可选）
    to: str | None              # 接收者（可选）
    best_effort_deliver: bool | None  # 尽力交付（可选）
```

示例：

```json
{
  "kind": "agentTurn",
  "message": "Summarize today's conversations and tasks",
  "model": "claude-3-5-sonnet-20241022",
  "timeoutSeconds": 300,
  "deliver": true,
  "channel": "last"
}
```

## CronJob Structure

Source: `src/lurkbot/tools/builtin/cron_tool.py:137-166`

```python
class CronJob(BaseModel):
    """Complete cron job definition."""

    id: str                     # Job ID
    agent_id: str | None        # 关联的 agent ID
    name: str                   # Job 名称
    description: str | None     # 描述
    enabled: bool = True        # 是否启用
    delete_after_run: bool | None  # 运行后删除
    created_at_ms: int          # 创建时间戳
    updated_at_ms: int          # 更新时间戳

    schedule: dict[str, Any]    # 调度配置
    session_target: Literal["main", "isolated"] = "main"  # 会话目标
    wake_mode: Literal["next-heartbeat", "now"] = "next-heartbeat"
    payload: dict[str, Any]     # 执行负载

    isolation: CronJobIsolation | None  # 隔离设置
    state: CronJobState         # 运行状态
```

## Cron Tool Operations

Source: `src/lurkbot/tools/builtin/cron_tool.py:625-731`

Cron tool 支持以下操作：

| Operation | Description | Required Params |
|-----------|-------------|-----------------|
| `status` | 获取 cron 服务状态 | - |
| `list` | 列出所有 cron jobs | - |
| `add` | 创建新 job | `name`, `schedule`, `payload` |
| `update` | 修改现有 job | `id` |
| `remove` | 删除 job | `id` |
| `run` | 手动触发 job | `id` |
| `runs` | 获取 job 运行历史 | `id` |
| `wake` | 唤醒调度器 | - |

## Using Cron Tool

### Via Agent Tool Call

```python
# Get cron service status
result = await cron_tool({"op": "status"})

# List all jobs
result = await cron_tool({"op": "list"})

# Add a new job
result = await cron_tool({
    "op": "add",
    "name": "daily-reminder",
    "schedule": {
        "kind": "cron",
        "expr": "0 9 * * *",
        "tz": "America/New_York"
    },
    "payload": {
        "kind": "systemEvent",
        "text": "Good morning! Time to start the day."
    },
    "sessionTarget": "main"
})

# Run a job manually
result = await cron_tool({
    "op": "run",
    "id": "job-id",
    "mode": "force"  # or "due"
})

# Get job run history
result = await cron_tool({
    "op": "runs",
    "id": "job-id",
    "limit": 10
})

# Update a job
result = await cron_tool({
    "op": "update",
    "id": "job-id",
    "enabled": False
})

# Remove a job
result = await cron_tool({
    "op": "remove",
    "id": "job-id"
})
```

### Via Chat

```
User: Create a daily reminder at 9am to check emails

Agent: I'll create a cron job for that.

[cron tool call: add job with cron schedule "0 9 * * *"]

Done! I've created a daily reminder that will trigger at 9:00 AM.
```

## Managing Cron Jobs

### List Jobs

```bash
lurkbot cron list
```

Output:

```
Cron Jobs:
  daily-reminder    cron: 0 9 * * *     Next: 2026-01-31 09:00
  weekly-backup     every: 604800000ms  Next: 2026-02-02 02:00
  health-check      every: 300000ms     Next: 2026-01-30 12:35
```

### Enable/Disable

```bash
# Disable a job
lurkbot cron disable daily-reminder

# Enable a job
lurkbot cron enable daily-reminder
```

### Run Manually

```bash
# Run a job immediately
lurkbot cron run daily-reminder
```

### Delete Job

```bash
lurkbot cron delete daily-reminder
```

## Job State

Source: `src/lurkbot/tools/builtin/cron_tool.py:112-123`

```python
class CronJobState(BaseModel):
    """Cron job runtime state."""

    next_run_at_ms: int | None      # 下次执行时间
    running_at_ms: int | None       # 正在执行的开始时间
    last_run_at_ms: int | None      # 上次执行时间
    last_status: Literal["ok", "error", "skipped"] | None
    last_error: str | None          # 上次执行错误
    last_duration_ms: int | None    # 上次执行耗时
```

## Service Status

Source: `src/lurkbot/tools/builtin/cron_tool.py:168-175`

```python
class CronServiceStatus(BaseModel):
    """Cron service status."""

    running: bool                   # 服务是否运行中
    job_count: int                  # job 总数
    next_job_id: str | None         # 下一个要执行的 job ID
    next_job_at_ms: int | None      # 下一个执行时间
```

## Examples

### Daily Reminder (systemEvent)

```python
await cron_tool({
    "op": "add",
    "name": "morning-reminder",
    "description": "Daily morning check-in",
    "schedule": {
        "kind": "cron",
        "expr": "0 9 * * 1-5",  # Weekdays at 9 AM
        "tz": "America/New_York"
    },
    "payload": {
        "kind": "systemEvent",
        "text": "🌅 Good morning! Time for daily standup."
    },
    "sessionTarget": "main"
})
```

### Hourly Health Check (every)

```python
await cron_tool({
    "op": "add",
    "name": "health-check",
    "schedule": {
        "kind": "every",
        "everyMs": 3600000  # Every hour
    },
    "payload": {
        "kind": "systemEvent",
        "text": "⏰ Hourly health check"
    }
})
```

### Weekly Report (agentTurn)

```python
await cron_tool({
    "op": "add",
    "name": "weekly-report",
    "description": "Generate weekly summary",
    "schedule": {
        "kind": "cron",
        "expr": "0 17 * * 5",  # Fridays at 5 PM
    },
    "payload": {
        "kind": "agentTurn",
        "message": """Generate a weekly summary report including:
- Conversations this week
- Tasks completed
- Issues encountered
""",
        "model": "claude-3-5-sonnet-20241022",
        "timeoutSeconds": 600,
        "deliver": True,
        "channel": "last"
    },
    "sessionTarget": "isolated"
})
```

### One-Time Reminder (at)

```python
import time

# Remind in 1 hour
remind_time = int((time.time() + 3600) * 1000)

await cron_tool({
    "op": "add",
    "name": "meeting-reminder",
    "schedule": {
        "kind": "at",
        "atMs": remind_time
    },
    "payload": {
        "kind": "systemEvent",
        "text": "📅 Meeting starts in 10 minutes!"
    },
    "deleteAfterRun": True  # 运行后自动删除
})
```

## Timezone Support

Cron 表达式调度支持时区配置：

```python
await cron_tool({
    "op": "add",
    "name": "tokyo-reminder",
    "schedule": {
        "kind": "cron",
        "expr": "0 9 * * *",
        "tz": "Asia/Tokyo"  # 东京时间 9:00
    },
    "payload": {
        "kind": "systemEvent",
        "text": "おはようございます！"
    }
})
```

## Session Isolation

Source: `src/lurkbot/tools/builtin/cron_tool.py:125-135`

Job 可以运行在主会话或隔离会话：

```python
class CronJobIsolation(BaseModel):
    """Isolation settings for cron job."""

    post_to_main_prefix: str | None   # 发送到主会话的前缀
    post_to_main_mode: Literal["summary", "full"] | None
    post_to_main_max_chars: int | None
```

示例：

```python
await cron_tool({
    "op": "add",
    "name": "background-task",
    "schedule": {"kind": "every", "everyMs": 3600000},
    "payload": {
        "kind": "agentTurn",
        "message": "Analyze system logs"
    },
    "sessionTarget": "isolated",
    "isolation": {
        "postToMainPrefix": "📊 Log Analysis Result:\n",
        "postToMainMode": "summary",
        "postToMainMaxChars": 500
    }
})
```

## Implementation Notes

Source: `src/lurkbot/tools/builtin/cron_tool.py:595-618`

### Payload Execution

当前实现包含占位符，完整实现需要：

```python
async def _execute_cron_payload(payload: dict[str, Any]) -> None:
    """Execute a cron job payload."""
    kind = payload.get("kind")

    if kind == "systemEvent":
        # TODO: Inject system event into main session
        text = payload.get("text", "")
        # This would call into the session system
        pass

    elif kind == "agentTurn":
        # TODO: Spawn isolated session and run agent task
        message = payload.get("message", "")
        # This would spawn a subagent to handle the task
        pass
```

### Storage

当前使用内存存储（`CronStore`），生产环境应使用持久化存储：

```python
@dataclass
class CronStore:
    """In-memory cron job storage.

    Note: Full implementation should use persistent storage via Gateway.
    This is a placeholder for local development and testing.
    """

    jobs: dict[str, CronJob] = field(default_factory=dict)
    runs: dict[str, list[CronRunResult]] = field(default_factory=dict)
    _running: bool = False
```

---

## See Also

- [Hooks](hooks.md) - Event-driven automation
- [Gateway](gateway.md) - Gateway architecture
- [Daemon Mode](daemon.md) - Background operation
