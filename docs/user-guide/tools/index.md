# Tools Overview

Tools are capabilities that LurkBot agents can use to perform actions. They enable the AI to interact with the real world.

## Built-in Tools

LurkBot includes 22 built-in tools across several categories:

### Shell Tools

| Tool | Description |
|------|-------------|
| `bash` | Execute shell commands |

### File Tools

| Tool | Description |
|------|-------------|
| `read` | Read file contents |
| `write` | Write/create files |
| `edit` | Edit existing files |
| `glob` | Find files by pattern |
| `grep` | Search file contents |

### Browser Tools

| Tool | Description |
|------|-------------|
| `browser_navigate` | Navigate to URL |
| `browser_click` | Click elements |
| `browser_type` | Type text |
| `browser_screenshot` | Capture page |
| `browser_scroll` | Scroll page |

### Canvas Tools

| Tool | Description |
|------|-------------|
| `canvas_create` | Create new canvas |
| `canvas_update` | Update canvas content |

### Session Tools

| Tool | Description |
|------|-------------|
| `sessions_list` | List active sessions |
| `sessions_send` | Send message to session |
| `sessions_spawn` | Spawn subagent |

### System Tools

| Tool | Description |
|------|-------------|
| `message` | Send message to user |
| `nodes` | List connected nodes |
| `cron` | Schedule tasks |

## Tool Categories

Tools are organized into categories for policy management:

| Category | Tools | Risk Level |
|----------|-------|------------|
| `shell` | bash | High |
| `file_read` | read, glob, grep | Low |
| `file_write` | write, edit | Medium |
| `browser` | browser_* | Medium |
| `canvas` | canvas_* | Low |
| `session` | sessions_* | Medium |
| `system` | message, nodes, cron | Low |

## Quick Configuration

### Enable/Disable Tools

```bash
# Disable specific tools
LURKBOT_DISABLED_TOOLS=bash,browser_navigate

# Enable only specific tools
LURKBOT_ENABLED_TOOLS=read,write,edit,glob,grep
```

### Tool Timeout

```bash
# Default tool timeout (seconds)
LURKBOT_TOOL_TIMEOUT=30

# Per-tool timeout
LURKBOT_TOOL_BASH_TIMEOUT=60
```

## Next Steps

- [Built-in Tools](builtin-tools.md) - Detailed tool documentation
- [Tool Policies](tool-policies.md) - Security configuration
- [Sandbox](sandbox.md) - Isolated execution
