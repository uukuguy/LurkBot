# CLI Overview

LurkBot provides a powerful command-line interface for managing your AI assistant.

## Installation

The CLI is automatically installed with LurkBot:

```bash
# Verify installation
lurkbot --version
```

## Command Structure

```bash
lurkbot [OPTIONS] COMMAND [ARGS]
```

### Global Options

| Option | Description |
|--------|-------------|
| `--version` | Show version and exit |
| `--help` | Show help message |
| `--config PATH` | Use custom config file |
| `--verbose` | Enable verbose output |

## Main Commands

### Gateway Commands

```bash
lurkbot gateway start    # Start the gateway server
lurkbot gateway stop     # Stop the gateway server
lurkbot gateway status   # Check gateway status
```

### Agent Commands

```bash
lurkbot agent chat       # Start interactive chat
lurkbot agent run        # Run a single prompt
```

### Configuration Commands

```bash
lurkbot config show      # Show current configuration
lurkbot config init      # Initialize configuration
lurkbot config validate  # Validate configuration
```

### Channel Commands

```bash
lurkbot channels list    # List configured channels
lurkbot channels status  # Check channel status
```

### Utility Commands

```bash
lurkbot doctor           # Run health checks
lurkbot onboard          # Setup wizard
lurkbot skills list      # List available skills
```

## Quick Examples

### Start a Chat Session

```bash
# Interactive chat with Claude
lurkbot agent chat

# Chat with a specific model
lurkbot agent chat --model gpt-4o
```

### Run the Gateway

```bash
# Start gateway in foreground
lurkbot gateway start

# Start gateway as daemon
lurkbot gateway start --daemon
```

### Check System Health

```bash
# Run all health checks
lurkbot doctor

# Check specific component
lurkbot doctor --check gateway
```

## Next Steps

- [Commands Reference](commands.md) - Complete command documentation
- [Interactive Chat](interactive-chat.md) - Chat session features
- [CLI Reference](../../reference/cli-reference.md) - Full CLI reference
