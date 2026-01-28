# LurkBot - Python Rewrite of Moltbot

## Project Overview

This is a Python rewrite of [moltbot](https://github.com/moltbot/moltbot), a multi-channel AI assistant platform.

## Key Architecture Decisions

- **Package Manager**: uv (fast, modern Python package manager)
- **Build Entry**: Makefile for all common commands
- **Web Framework**: FastAPI for HTTP/WebSocket server
- **Validation**: Pydantic for schema validation
- **CLI**: Typer for command-line interface
- **Logging**: Loguru for structured logging

## Module Mapping (TypeScript → Python)

| Original (TS)     | Python Module        | Description                    |
|-------------------|----------------------|--------------------------------|
| `src/gateway/`    | `lurkbot.gateway`    | WebSocket gateway server       |
| `src/agents/`     | `lurkbot.agents`     | AI agent runtime               |
| `src/channels/`   | `lurkbot.channels`   | Channel adapters               |
| `src/cli/`        | `lurkbot.cli`        | Command-line interface         |
| `src/config/`     | `lurkbot.config`     | Configuration management       |
| `src/tools/`      | `lurkbot.tools`      | Built-in tools                 |

## Development Commands

All commands are accessed via Makefile:

```bash
make help       # Show all available commands
make dev        # Install dev dependencies
make test       # Run tests
make lint       # Run linter
make format     # Format code
make gateway    # Start gateway server
```

## Reference

- Original project: `github.com/moltbot` (not in git scope)
