# CLI Commands Reference

Complete reference for all LurkBot CLI commands.

## Gateway Commands

### `lurkbot gateway start`

Start the WebSocket gateway server.

```bash
lurkbot gateway start [OPTIONS]
```

**Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `--host` | `127.0.0.1` | Host to bind to |
| `--port` | `18789` | Port to listen on |
| `--daemon` | `false` | Run as background daemon |
| `--log-level` | `info` | Log level (debug/info/warning/error) |

**Examples:**

```bash
# Start on default port
lurkbot gateway start

# Start on custom port
lurkbot gateway start --port 8080

# Start as daemon
lurkbot gateway start --daemon
```

### `lurkbot gateway stop`

Stop the running gateway server.

```bash
lurkbot gateway stop
```

### `lurkbot gateway status`

Check the gateway server status.

```bash
lurkbot gateway status
```

**Output:**

```
Gateway Status: Running
  Address: ws://127.0.0.1:18789
  Uptime: 2h 15m
  Connections: 3
  Channels: telegram, discord
```

---

## Agent Commands

### `lurkbot agent chat`

Start an interactive chat session.

```bash
lurkbot agent chat [OPTIONS]
```

**Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `--model` | (from config) | AI model to use |
| `--session` | `main` | Session ID |
| `--system` | (none) | Custom system prompt |
| `--no-tools` | `false` | Disable tool execution |

**Examples:**

```bash
# Start chat with default model
lurkbot agent chat

# Use specific model
lurkbot agent chat --model claude-sonnet-4-20250514

# Use custom session
lurkbot agent chat --session my-project
```

### `lurkbot agent run`

Run a single prompt and exit.

```bash
lurkbot agent run [OPTIONS] PROMPT
```

**Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `--model` | (from config) | AI model to use |
| `--output` | `text` | Output format (text/json) |
| `--no-stream` | `false` | Disable streaming |

**Examples:**

```bash
# Run a single prompt
lurkbot agent run "What is 2+2?"

# Get JSON output
lurkbot agent run --output json "List 3 colors"
```

---

## Configuration Commands

### `lurkbot config show`

Display current configuration.

```bash
lurkbot config show [OPTIONS]
```

**Options:**

| Option | Description |
|--------|-------------|
| `--section` | Show specific section only |
| `--format` | Output format (yaml/json) |

**Examples:**

```bash
# Show all configuration
lurkbot config show

# Show only channels
lurkbot config show --section channels

# Output as JSON
lurkbot config show --format json
```

### `lurkbot config init`

Initialize configuration interactively.

```bash
lurkbot config init [OPTIONS]
```

**Options:**

| Option | Description |
|--------|-------------|
| `--force` | Overwrite existing config |
| `--minimal` | Create minimal config |

### `lurkbot config validate`

Validate configuration file.

```bash
lurkbot config validate [PATH]
```

---

## Channel Commands

### `lurkbot channels list`

List all configured channels.

```bash
lurkbot channels list
```

**Output:**

```
Configured Channels:
  ✅ telegram  - Enabled (Bot: @my_lurkbot)
  ❌ discord   - Disabled
  ⚠️  slack     - Enabled (Not connected)
```

### `lurkbot channels status`

Check channel connection status.

```bash
lurkbot channels status [CHANNEL]
```

---

## Utility Commands

### `lurkbot doctor`

Run system health checks.

```bash
lurkbot doctor [OPTIONS]
```

**Options:**

| Option | Description |
|--------|-------------|
| `--check` | Run specific check only |
| `--fix` | Attempt to fix issues |

**Checks performed:**

- Python version
- Dependencies installed
- Configuration valid
- API keys configured
- Gateway reachable
- Docker available (optional)

### `lurkbot onboard`

Run the setup wizard.

```bash
lurkbot onboard
```

Interactive wizard that helps you:

1. Configure API keys
2. Set up channels
3. Test connections
4. Create initial configuration

### `lurkbot skills list`

List available skills.

```bash
lurkbot skills list [OPTIONS]
```

**Options:**

| Option | Description |
|--------|-------------|
| `--verbose` | Show skill details |
| `--category` | Filter by category |

---

## Environment Variables

All CLI options can be set via environment variables:

```bash
# Format: LURKBOT_<SECTION>__<OPTION>
export LURKBOT_GATEWAY__PORT=8080
export LURKBOT_AGENT__MODEL=claude-sonnet-4-20250514
```

See [Environment Variables](../configuration/environment.md) for complete list.

---

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error |
| 2 | Configuration error |
| 3 | Connection error |
| 4 | Authentication error |

---

## See Also

- [Interactive Chat](interactive-chat.md) - Chat session features
- [Configuration](../configuration/index.md) - Configuration options
- [CLI Reference](../../reference/cli-reference.md) - Complete reference
