# LurkBot

A multi-channel AI assistant platform - Python rewrite of [moltbot](https://github.com/moltbot/moltbot).

## Features

- **Multi-Channel Support**: Telegram, Discord, Slack, WhatsApp, and more
- **AI Model Integration**: Claude, GPT, Gemini, and local models via Ollama
- **WebSocket Gateway**: Centralized control plane for all channels
- **Tool System**: Extensible tools for browser automation, file operations, etc.
- **Session Management**: Isolated sessions with context persistence

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager

## Quick Start

```bash
# Install dependencies
make dev

# Run the gateway server
make gateway

# Or use CLI directly
make cli ARGS="--help"
```

## Project Structure

```
src/lurkbot/
├── gateway/     # WebSocket gateway server
├── agents/      # AI agent runtime
├── channels/    # Channel adapters (Telegram, Discord, etc.)
├── cli/         # Command-line interface
├── config/      # Configuration management
├── tools/       # Built-in tools
└── utils/       # Shared utilities
```

## Development

```bash
# Run tests
make test

# Run linter
make lint

# Format code
make format

# Type check
make typecheck

# Run all checks
make check
```

## License

MIT
