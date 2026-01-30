# Sessions

Sessions represent individual conversations in LurkBot. Each session maintains its own context, history, and configuration.

## Session Types

| Type | Description | Trust Level | Sandbox |
|------|-------------|-------------|---------|
| `main` | Direct messages with owner | Full | No |
| `dm` | DMs from other users | Partial | Optional |
| `group` | Group chat conversations | Low | Yes |
| `topic` | Forum topic threads | Low | Yes |

## Session Keys

Each session has a unique key:

```
<channel>:<chat_id>:<session_type>
```

Examples:

- `telegram:123456789:main` - Owner's Telegram DM
- `discord:987654321:group` - Discord group chat
- `slack:C0123456789:topic` - Slack thread

## Session Lifecycle

```
Created → Active → Idle → Compacted → Archived
            ↑         ↓
            └─────────┘
           (new message)
```

### States

| State | Description |
|-------|-------------|
| **Created** | New session, no messages yet |
| **Active** | Currently in use |
| **Idle** | No recent activity |
| **Compacted** | History summarized to save memory |
| **Archived** | Stored for long-term reference |

## Session Configuration

### Per-Session Settings

```bash
# Session-specific model
LURKBOT_SESSION__<KEY>__MODEL=gpt-4o

# Session-specific tools
LURKBOT_SESSION__<KEY>__TOOLS=read,write,bash
```

### Global Session Settings

```bash
# Default session timeout (seconds)
LURKBOT_SESSION_TIMEOUT=3600

# Max messages before compaction
LURKBOT_SESSION_MAX_MESSAGES=100

# Enable session persistence
LURKBOT_SESSION_PERSISTENCE=true
```

## Session Storage

Sessions are stored in `~/.lurkbot/sessions/`:

```
~/.lurkbot/sessions/
├── telegram_123456789_main.json
├── discord_987654321_group.json
└── slack_C0123456789_topic.json
```

### Session File Format

```json
{
  "key": "telegram:123456789:main",
  "type": "main",
  "channel": "telegram",
  "chat_id": "123456789",
  "created_at": "2026-01-30T10:00:00Z",
  "updated_at": "2026-01-30T12:30:00Z",
  "messages": [
    {"role": "user", "content": "Hello"},
    {"role": "assistant", "content": "Hi there!"}
  ],
  "metadata": {
    "model": "claude-sonnet-4-20250514",
    "tools_used": ["bash", "read"]
  }
}
```

## Session Management

### List Sessions

```bash
lurkbot sessions list
```

Output:

```
Active Sessions:
  telegram:123456789:main    - 15 messages, last active 5m ago
  discord:987654321:group    - 42 messages, last active 2h ago

Idle Sessions:
  slack:C0123456789:topic    - 8 messages, last active 1d ago
```

### Clear Session

```bash
# Clear specific session
lurkbot sessions clear telegram:123456789:main

# Clear all sessions
lurkbot sessions clear --all
```

### Export Session

```bash
# Export to JSON
lurkbot sessions export telegram:123456789:main > session.json

# Export to Markdown
lurkbot sessions export --format markdown telegram:123456789:main > session.md
```

## Session Isolation

### Sandbox Mode

Untrusted sessions run in isolated environments:

```bash
# Enable sandbox for all group sessions
LURKBOT_GROUP_SANDBOX=true

# Sandbox configuration
LURKBOT_SANDBOX_MEMORY_LIMIT=512m
LURKBOT_SANDBOX_CPU_LIMIT=1
LURKBOT_SANDBOX_NETWORK=false
```

### Workspace Isolation

Each session can have its own workspace:

```bash
# Session workspace directory
LURKBOT_SESSION_WORKSPACE=~/.lurkbot/workspaces/<session_key>
```

## Context Management

### Context Window

```bash
# Max context tokens
LURKBOT_MAX_CONTEXT_TOKENS=128000

# Context strategy
LURKBOT_CONTEXT_STRATEGY=sliding  # or: summarize, truncate
```

### Compaction

When context grows too large:

```bash
# Auto-compact after N messages
LURKBOT_COMPACT_AFTER=100

# Compaction strategy
LURKBOT_COMPACT_STRATEGY=summarize  # or: truncate, hybrid
```

## Multi-Session Features

### Session Switching

In CLI:

```bash
# Switch session
/session my-project

# List sessions
/sessions
```

### Cross-Session Communication

Sessions can communicate via the `sessions_send` tool:

```
User: Send "Build complete" to the #dev-updates channel
Bot: [Using sessions_send tool]
     Message sent to discord:dev-updates:group
```

## Troubleshooting

### Session not persisting

1. Check persistence is enabled:
   ```bash
   echo $LURKBOT_SESSION_PERSISTENCE
   ```

2. Verify write permissions:
   ```bash
   ls -la ~/.lurkbot/sessions/
   ```

### Context too long

1. Enable compaction:
   ```bash
   LURKBOT_COMPACT_AFTER=50
   ```

2. Clear session history:
   ```bash
   lurkbot sessions clear <session_key>
   ```

### Session conflicts

If multiple instances access the same session:

```bash
# Enable session locking
LURKBOT_SESSION_LOCKING=true
```

---

## See Also

- [AI Models](models.md) - Model configuration
- [Subagents](subagents.md) - Specialized agents
- [Sandbox](../tools/sandbox.md) - Sandbox isolation
