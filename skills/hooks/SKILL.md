---
name: hooks
description: Manage and trigger internal event hooks for system automation and custom behaviors.
metadata: {"lurkbot":{"emoji":"🪝"}}
---

# Hooks Management

Manage the internal hooks system for event-driven automation and custom behaviors.

## Available Tool

- `hooks` - Hook registry and event triggering

## Operations

### 1. List registered hooks

```bash
{
  "action": "list",
  "eventPattern": "command.*"  # optional filter
}
```

### 2. Trigger a hook event

```bash
{
  "action": "trigger",
  "eventType": "command",
  "eventAction": "pre_execute",
  "sessionKey": "channel:default:abc123",
  "context": {
    "command": "test",
    "args": []
  }
}
```

### 3. Discover hooks from directories

```bash
{
  "action": "discover",
  "workspaceDir": "/path/to/workspace/.lurkbot"
}
```

### 4. Show hook information

```bash
{
  "action": "info"
}
```

## Hook System

LurkBot's hooks system allows custom event handlers:

**Event types**:
- `command` - Command lifecycle events
- `session` - Session lifecycle events
- `agent` - Agent execution events
- `gateway` - Gateway communication events

**Hook discovery**:
- Hooks are discovered from `.lurkbot/hooks/` directories
- Each hook is a Python module with specific structure
- Hooks can be enabled/disabled via metadata

## Use Cases

**Command interception**: Modify or validate commands before execution.

**Session monitoring**: Track session lifecycle and state changes.

**Custom automation**: Trigger actions based on specific events.

**Logging and auditing**: Capture events for analysis.

**Workflow customization**: Add custom behavior at key points.

## Hook Structure

Hooks are defined in Python modules:

```python
# .lurkbot/hooks/my_hook.py
"""
---
name: my-hook
events: [command.pre_execute]
enabled: true
priority: 10
---
"""

async def handle(event):
    # Custom logic here
    pass
```

## Tips

- Use specific event patterns to filter hooks
- Higher priority hooks execute first
- Disabled hooks are skipped
- Discovery finds hooks in workspace
- Check hook registry after adding new hooks
- Use trigger for manual testing

## Related Skills

- `sessions` - Hooks can intercept session events
- `automation/cron` - Trigger hooks on schedule
- `automation/gateway` - Gateway events trigger hooks
