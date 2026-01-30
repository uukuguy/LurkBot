---
name: cron
description: Schedule and manage recurring tasks with support for cron expressions, periodic intervals, and one-time execution.
metadata: {"moltbot":{"emoji":"⏰"}}
---

# Cron Task Scheduler

Create, manage, and monitor scheduled tasks with flexible scheduling options.

## Available Tool

- `cron` - Comprehensive scheduled task management

## Supported Operations

- `status` - Get cron service status
- `list` - List all cron jobs
- `add` - Create a new cron job
- `update` - Modify an existing job
- `remove` - Delete a cron job
- `run` - Manually trigger a job
- `runs` - Get job run history
- `wake` - Wake up the scheduler

## Schedule Types

### 1. At (one-time execution)

Execute once at a specific time:

```bash
{
  "op": "add",
  "label": "Morning report",
  "schedule": {
    "kind": "at",
    "atMs": 1706774400000  # Unix timestamp in milliseconds
  },
  "payload": {
    "kind": "agentTurn",
    "message": "Generate morning report"
  }
}
```

### 2. Every (periodic execution)

Execute at regular intervals:

```bash
{
  "op": "add",
  "label": "Hourly check",
  "schedule": {
    "kind": "every",
    "everyMs": 3600000,  # 1 hour in milliseconds
    "anchorMs": null     # optional: anchor to specific time
  },
  "payload": {
    "kind": "agentTurn",
    "message": "Check API status"
  }
}
```

### 3. Cron (cron expression)

Use standard cron expressions:

```bash
{
  "op": "add",
  "label": "Daily backup",
  "schedule": {
    "kind": "cron",
    "expr": "0 2 * * *",  # Every day at 2 AM
    "tz": "America/New_York"  # optional timezone
  },
  "payload": {
    "kind": "agentTurn",
    "message": "Run database backup"
  }
}
```

## Payload Types

### System Event

Inject a system event:

```bash
{
  "kind": "systemEvent",
  "text": "Scheduled maintenance starting"
}
```

### Agent Turn

Run an agent task:

```bash
{
  "kind": "agentTurn",
  "message": "Check for updates",
  "model": "claude-sonnet-4.5"  # optional model override
}
```

## Quick Examples

### List all jobs

```bash
{"op": "list"}
```

### Get service status

```bash
{"op": "status"}
```

### Manually run a job

```bash
{
  "op": "run",
  "id": "job-123"
}
```

### Remove a job

```bash
{
  "op": "remove",
  "id": "job-123"
}
```

### View run history

```bash
{
  "op": "runs",
  "id": "job-123",
  "limit": 10
}
```

## Cron Expression Examples

```
0 * * * *        # Every hour at minute 0
*/15 * * * *     # Every 15 minutes
0 9 * * 1-5      # Weekdays at 9 AM
0 0 1 * *        # First day of each month at midnight
0 12 * * 0       # Every Sunday at noon
```

## Use Cases

**Periodic monitoring**: Check APIs, services, or resources at regular intervals.

**Scheduled reports**: Generate daily/weekly reports automatically.

**Maintenance tasks**: Run cleanup, backups, or updates on schedule.

**Reminders**: Send notifications at specific times or intervals.

**Data sync**: Periodically fetch or sync data from external sources.

## Tips

- Use meaningful labels for easy identification
- Test jobs with `run` before scheduling
- Check `runs` history for debugging
- Wake scheduler after adding time-sensitive jobs
- Consider timezones for cron expressions
- Use milliseconds for `at` and `every` schedules

## Related Skills

- `sessions` - Spawn subagents from scheduled tasks
- `automation/gateway` - Access cron service via Gateway
- `messaging` - Send scheduled notifications
