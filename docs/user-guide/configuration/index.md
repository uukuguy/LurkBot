# Configuration Overview

LurkBot uses a layered configuration system that allows flexible customization at multiple levels.

## Configuration Hierarchy

Configuration is loaded in this order (later overrides earlier):

```
1. Default values (built-in)
   ↓
2. System config (~/.lurkbot/config.json)
   ↓
3. Environment variables (LURKBOT_*)
   ↓
4. Workspace config (.lurkbot/config.json)
   ↓
5. Runtime overrides (CLI flags)
```

## Quick Start

### Minimal Configuration

Create `~/.lurkbot/.env`:

```bash
# Required: At least one AI provider
LURKBOT_ANTHROPIC_API_KEY=sk-ant-api03-...

# Optional: Enable a channel
LURKBOT_TELEGRAM__ENABLED=true
LURKBOT_TELEGRAM__BOT_TOKEN=123456789:ABC...
```

### Full Configuration

See [Config File](config-file.md) for complete options.

## Configuration Methods

| Method | Best For | Example |
|--------|----------|---------|
| [Environment Variables](environment.md) | Secrets, quick setup | `LURKBOT_ANTHROPIC_API_KEY=...` |
| [Config File](config-file.md) | Complex settings | `~/.lurkbot/config.json` |
| [Auth Profiles](auth-profiles.md) | Multiple environments | `--profile production` |
| CLI Flags | One-time overrides | `--port 8080` |

## Common Settings

### AI Provider

```bash
# Anthropic (recommended)
LURKBOT_ANTHROPIC_API_KEY=sk-ant-api03-...
LURKBOT_DEFAULT_MODEL=claude-sonnet-4-20250514

# OpenAI
LURKBOT_OPENAI_API_KEY=sk-...
LURKBOT_DEFAULT_MODEL=gpt-4o

# Google
LURKBOT_GOOGLE_API_KEY=...
LURKBOT_DEFAULT_MODEL=gemini-pro
```

### Gateway

```bash
LURKBOT_GATEWAY__HOST=127.0.0.1
LURKBOT_GATEWAY__PORT=18789
```

### Channels

```bash
# Telegram
LURKBOT_TELEGRAM__ENABLED=true
LURKBOT_TELEGRAM__BOT_TOKEN=...
LURKBOT_TELEGRAM__ALLOWLIST=123456789

# Discord
LURKBOT_DISCORD__ENABLED=true
LURKBOT_DISCORD__BOT_TOKEN=...
```

## Next Steps

- [Config File](config-file.md) - JSON configuration format
- [Environment Variables](environment.md) - All environment variables
- [Auth Profiles](auth-profiles.md) - Multiple configurations
