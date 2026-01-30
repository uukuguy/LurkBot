# Config File

LurkBot can be configured using JSON configuration files.

## File Locations

Configuration files are loaded in order:

1. **System config**: `~/.lurkbot/config.json`
2. **Workspace config**: `.lurkbot/config.json` (in current directory)

Later files override earlier ones.

## Basic Structure

```json
{
  "gateway": {
    "host": "127.0.0.1",
    "port": 18789
  },
  "agent": {
    "model": "claude-sonnet-4-20250514",
    "max_tokens": 4096,
    "temperature": 0.7
  },
  "channels": {
    "telegram": {
      "enabled": true,
      "allowlist": ["123456789"]
    }
  },
  "tools": {
    "disabled": ["bash"],
    "timeout": 30
  }
}
```

## Complete Reference

### Gateway Section

```json
{
  "gateway": {
    "host": "127.0.0.1",
    "port": 18789,
    "daemon": false,
    "log_level": "info",
    "log_file": "~/.lurkbot/logs/gateway.log"
  }
}
```

### Agent Section

```json
{
  "agent": {
    "model": "claude-sonnet-4-20250514",
    "fallback_models": ["gpt-4o", "claude-haiku-3-5-20241022"],
    "max_tokens": 4096,
    "max_context_tokens": 128000,
    "temperature": 0.7,
    "system_prompt": "You are a helpful assistant...",
    "system_prompt_file": "~/.lurkbot/system-prompt.txt"
  }
}
```

### Channels Section

```json
{
  "channels": {
    "telegram": {
      "enabled": true,
      "bot_token": "${TELEGRAM_BOT_TOKEN}",
      "allowlist": ["123456789", "987654321"],
      "allowed_groups": ["-1001234567890"],
      "mention_gating": false,
      "group_sandbox": true,
      "parse_mode": "Markdown",
      "typing_indicator": true
    },
    "discord": {
      "enabled": true,
      "bot_token": "${DISCORD_BOT_TOKEN}",
      "allowlist": ["123456789012345678"],
      "allowed_guilds": ["123456789012345678"],
      "mention_gating": true,
      "dm_enabled": true
    },
    "slack": {
      "enabled": true,
      "bot_token": "${SLACK_BOT_TOKEN}",
      "app_token": "${SLACK_APP_TOKEN}",
      "allowlist": ["U0123456789"],
      "mention_gating": true,
      "thread_replies": true
    }
  }
}
```

### Sessions Section

```json
{
  "sessions": {
    "timeout": 3600,
    "max_messages": 100,
    "persistence": true,
    "directory": "~/.lurkbot/sessions",
    "context_strategy": "sliding",
    "compact_after": 100
  }
}
```

### Tools Section

```json
{
  "tools": {
    "timeout": 30,
    "disabled": ["bash", "browser_navigate"],
    "enabled": null,
    "policy": {
      "default": "allow",
      "ask": ["bash", "write", "edit"],
      "deny": []
    },
    "audit": {
      "enabled": true,
      "file": "~/.lurkbot/logs/tool-audit.log"
    }
  }
}
```

### Sandbox Section

```json
{
  "sandbox": {
    "enabled": true,
    "session_types": {
      "main": false,
      "dm": true,
      "group": true
    },
    "resources": {
      "memory": "512m",
      "cpu": 1,
      "disk": "1g",
      "timeout": 60
    },
    "network": {
      "enabled": false,
      "allowed_hosts": ["api.example.com"]
    },
    "docker": {
      "image": "ubuntu:22.04",
      "reuse": true
    }
  }
}
```

### Subagents Section

```json
{
  "subagents": {
    "enabled": true,
    "types": ["coder", "browser", "researcher"],
    "max_concurrent": 3,
    "timeout": 300,
    "max_iterations": 10,
    "model": "claude-haiku-3-5-20241022",
    "sandbox": true
  }
}
```

### Logging Section

```json
{
  "logging": {
    "level": "info",
    "format": "text",
    "directory": "~/.lurkbot/logs"
  }
}
```

### Paths Section

```json
{
  "paths": {
    "config": "~/.lurkbot",
    "data": "~/.lurkbot/data",
    "cache": "~/.lurkbot/cache",
    "skills": "~/.lurkbot/skills"
  }
}
```

## Environment Variable Substitution

Use `${VAR_NAME}` to reference environment variables:

```json
{
  "channels": {
    "telegram": {
      "bot_token": "${TELEGRAM_BOT_TOKEN}"
    }
  }
}
```

## Workspace Configuration

Create `.lurkbot/config.json` in your project:

```json
{
  "agent": {
    "system_prompt": "You are a coding assistant for this project..."
  },
  "tools": {
    "policy": {
      "default": "allow"
    }
  }
}
```

This overrides system config for this workspace only.

## Validation

Validate your configuration:

```bash
lurkbot config validate
```

Output:

```
✅ Configuration valid

Loaded from:
  - ~/.lurkbot/config.json
  - .lurkbot/config.json

Active settings:
  - Model: claude-sonnet-4-20250514
  - Channels: telegram, discord
  - Tools: 22 enabled, 0 disabled
```

## Example Configurations

### Minimal

```json
{
  "agent": {
    "model": "claude-sonnet-4-20250514"
  }
}
```

### Development

```json
{
  "gateway": {
    "log_level": "debug"
  },
  "agent": {
    "model": "claude-sonnet-4-20250514"
  },
  "tools": {
    "policy": {
      "default": "allow"
    }
  },
  "sandbox": {
    "enabled": false
  }
}
```

### Production

```json
{
  "gateway": {
    "daemon": true,
    "log_level": "warning"
  },
  "agent": {
    "model": "claude-sonnet-4-20250514",
    "fallback_models": ["gpt-4o"]
  },
  "tools": {
    "policy": {
      "default": "deny",
      "ask": ["read", "glob", "grep"]
    },
    "audit": {
      "enabled": true
    }
  },
  "sandbox": {
    "enabled": true
  }
}
```

---

## See Also

- [Environment Variables](environment.md) - All environment variables
- [Auth Profiles](auth-profiles.md) - Multiple configurations
- [Configuration Overview](index.md) - Configuration hierarchy
