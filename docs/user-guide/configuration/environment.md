# Environment Variables

Complete reference for all LurkBot environment variables.

## Naming Convention

Environment variables follow this pattern:

```
LURKBOT_<SECTION>__<OPTION>
```

Note: Use double underscore (`__`) to separate sections.

## AI Provider Keys

### Anthropic

```bash
# API key (required for Claude)
LURKBOT_ANTHROPIC_API_KEY=sk-ant-api03-...

# Optional: Custom base URL
LURKBOT_ANTHROPIC_BASE_URL=https://api.anthropic.com
```

### OpenAI

```bash
# API key (required for GPT)
LURKBOT_OPENAI_API_KEY=sk-...

# Optional: Organization ID
LURKBOT_OPENAI_ORG_ID=org-...

# Optional: Custom base URL (for Azure, etc.)
LURKBOT_OPENAI_BASE_URL=https://api.openai.com/v1
```

### Google

```bash
# API key (required for Gemini)
LURKBOT_GOOGLE_API_KEY=...
```

### Ollama

```bash
# Ollama server URL
LURKBOT_OLLAMA_BASE_URL=http://localhost:11434
```

## Model Configuration

```bash
# Default AI model
LURKBOT_DEFAULT_MODEL=claude-sonnet-4-20250514

# Fallback models (comma-separated)
LURKBOT_FALLBACK_MODELS=gpt-4o,claude-haiku-3-5-20241022

# Max tokens in response
LURKBOT_MAX_TOKENS=4096

# Max context tokens
LURKBOT_MAX_CONTEXT_TOKENS=128000

# Temperature (0.0-1.0)
LURKBOT_TEMPERATURE=0.7

# Custom system prompt
LURKBOT_SYSTEM_PROMPT="You are a helpful assistant..."

# System prompt from file
LURKBOT_SYSTEM_PROMPT_FILE=~/.lurkbot/system-prompt.txt
```

## Gateway Configuration

```bash
# Host to bind to
LURKBOT_GATEWAY__HOST=127.0.0.1

# Port to listen on
LURKBOT_GATEWAY__PORT=18789

# Enable daemon mode
LURKBOT_GATEWAY__DAEMON=false

# Log level (debug/info/warning/error)
LURKBOT_GATEWAY__LOG_LEVEL=info

# Log file path
LURKBOT_GATEWAY__LOG_FILE=~/.lurkbot/logs/gateway.log
```

## Channel Configuration

### Telegram

```bash
LURKBOT_TELEGRAM__ENABLED=true
LURKBOT_TELEGRAM__BOT_TOKEN=123456789:ABC...
LURKBOT_TELEGRAM__ALLOWLIST=123456789,987654321
LURKBOT_TELEGRAM__ALLOWED_GROUPS=-1001234567890
LURKBOT_TELEGRAM__MENTION_GATING=false
LURKBOT_TELEGRAM__GROUP_SANDBOX=true
LURKBOT_TELEGRAM__PARSE_MODE=Markdown
LURKBOT_TELEGRAM__TYPING_INDICATOR=true
```

### Discord

```bash
LURKBOT_DISCORD__ENABLED=true
LURKBOT_DISCORD__BOT_TOKEN=MTIzNDU2Nzg5...
LURKBOT_DISCORD__ALLOWLIST=123456789012345678
LURKBOT_DISCORD__ALLOWED_GUILDS=123456789012345678
LURKBOT_DISCORD__ALLOWED_CHANNELS=123456789012345678
LURKBOT_DISCORD__MENTION_GATING=true
LURKBOT_DISCORD__DM_ENABLED=true
LURKBOT_DISCORD__THREAD_SUPPORT=true
```

### Slack

```bash
LURKBOT_SLACK__ENABLED=true
LURKBOT_SLACK__BOT_TOKEN=xoxb-...
LURKBOT_SLACK__APP_TOKEN=xapp-...
LURKBOT_SLACK__ALLOWLIST=U0123456789
LURKBOT_SLACK__ALLOWED_CHANNELS=C0123456789
LURKBOT_SLACK__MENTION_GATING=true
LURKBOT_SLACK__DM_ENABLED=true
LURKBOT_SLACK__THREAD_REPLIES=true
```

### WhatsApp

```bash
LURKBOT_WHATSAPP__ENABLED=true
LURKBOT_WHATSAPP__ALLOWLIST=1234567890@s.whatsapp.net
LURKBOT_WHATSAPP__ALLOWED_GROUPS=123456789-1234567890@g.us
LURKBOT_WHATSAPP__MENTION_GATING=true
```

### Signal

```bash
LURKBOT_SIGNAL__ENABLED=true
LURKBOT_SIGNAL__PHONE_NUMBER=+1234567890
LURKBOT_SIGNAL__ALLOWLIST=+1987654321
```

### iMessage

```bash
LURKBOT_IMESSAGE__ENABLED=true
LURKBOT_IMESSAGE__ALLOWLIST=+1234567890,email@example.com
```

## Session Configuration

```bash
# Session timeout (seconds)
LURKBOT_SESSION_TIMEOUT=3600

# Max messages before compaction
LURKBOT_SESSION_MAX_MESSAGES=100

# Enable session persistence
LURKBOT_SESSION_PERSISTENCE=true

# Session storage directory
LURKBOT_SESSION_DIR=~/.lurkbot/sessions

# Context strategy (sliding/summarize/truncate)
LURKBOT_CONTEXT_STRATEGY=sliding

# Auto-compact after N messages
LURKBOT_COMPACT_AFTER=100
```

## Tool Configuration

```bash
# Default tool timeout (seconds)
LURKBOT_TOOL_TIMEOUT=30

# Disabled tools (comma-separated)
LURKBOT_DISABLED_TOOLS=bash,browser_navigate

# Enabled tools (if set, only these are allowed)
LURKBOT_ENABLED_TOOLS=read,write,edit,glob,grep

# Default tool policy
LURKBOT_TOOL_POLICY_DEFAULT=allow

# Tools requiring confirmation
LURKBOT_TOOL_ASK=bash,write,edit

# Enable tool audit logging
LURKBOT_TOOL_AUDIT=true
```

## Sandbox Configuration

```bash
# Enable sandbox
LURKBOT_SANDBOX_ENABLED=true

# Sandbox for specific session types
LURKBOT_SANDBOX_MAIN=false
LURKBOT_SANDBOX_DM=true
LURKBOT_SANDBOX_GROUP=true

# Resource limits
LURKBOT_SANDBOX_MEMORY=512m
LURKBOT_SANDBOX_CPU=1
LURKBOT_SANDBOX_DISK=1g
LURKBOT_SANDBOX_TIMEOUT=60

# Network access
LURKBOT_SANDBOX_NETWORK=false
LURKBOT_SANDBOX_ALLOWED_HOSTS=api.example.com

# Docker image
LURKBOT_SANDBOX_IMAGE=ubuntu:22.04

# Container reuse
LURKBOT_SANDBOX_REUSE=true
```

## Subagent Configuration

```bash
# Enable subagents
LURKBOT_SUBAGENTS_ENABLED=true

# Enabled subagents (comma-separated)
LURKBOT_SUBAGENTS=coder,browser,researcher

# Max concurrent subagents
LURKBOT_MAX_SUBAGENTS=3

# Subagent timeout (seconds)
LURKBOT_SUBAGENT_TIMEOUT=300

# Subagent max iterations
LURKBOT_SUBAGENT_MAX_ITERATIONS=10

# Default subagent model
LURKBOT_SUBAGENT_MODEL=claude-haiku-3-5-20241022
```

## Logging Configuration

```bash
# Log level
LURKBOT_LOG_LEVEL=info

# Log format (text/json)
LURKBOT_LOG_FORMAT=text

# Log directory
LURKBOT_LOG_DIR=~/.lurkbot/logs

# Enable debug mode
LURKBOT_DEBUG=false
```

## Paths Configuration

```bash
# Config directory
LURKBOT_CONFIG_DIR=~/.lurkbot

# Data directory
LURKBOT_DATA_DIR=~/.lurkbot/data

# Cache directory
LURKBOT_CACHE_DIR=~/.lurkbot/cache

# Skills directory
LURKBOT_SKILLS_DIR=~/.lurkbot/skills
```

## Loading Environment Variables

### From .env File

Create `~/.lurkbot/.env`:

```bash
LURKBOT_ANTHROPIC_API_KEY=sk-ant-api03-...
LURKBOT_DEFAULT_MODEL=claude-sonnet-4-20250514
```

### From Shell

```bash
export LURKBOT_ANTHROPIC_API_KEY=sk-ant-api03-...
export LURKBOT_DEFAULT_MODEL=claude-sonnet-4-20250514
```

### From Command Line

```bash
LURKBOT_DEBUG=true lurkbot gateway start
```

---

## See Also

- [Config File](config-file.md) - JSON configuration
- [Auth Profiles](auth-profiles.md) - Multiple configurations
- [Configuration Overview](index.md) - Configuration hierarchy
