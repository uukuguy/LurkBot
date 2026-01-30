# Developer Guide

Welcome to the LurkBot Developer Guide. This section covers how to extend, customize, and contribute to LurkBot.

## Overview

| Section | Description |
|---------|-------------|
| [Architecture](architecture.md) | System design and internals |
| [Contributing](contributing.md) | How to contribute |
| [Extending](extending/index.md) | Add custom functionality |
| [API Reference](../api/index.md) | Complete API documentation |

## Quick Links

### Getting Started

- [Development Setup](contributing.md#development-setup) - Set up your environment
- [Architecture Overview](architecture.md) - Understand the system
- [Code Style](contributing.md#code-style) - Coding standards

### Extending LurkBot

- [Custom Channels](extending/custom-channels.md) - Add messaging platforms
- [Custom Tools](extending/custom-tools.md) - Create new tools
- [Custom Skills](extending/custom-skills.md) - Build plugins

### API

- [Gateway API](../api/gateway.md) - WebSocket API
- [Python API](../api/python.md) - Python SDK
- [RPC Methods](../api/rpc.md) - Available RPC calls

## Development Setup

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (recommended)
- Git
- Docker (optional, for sandbox testing)

### Quick Start

```bash
# Clone repository
git clone https://github.com/uukuguy/lurkbot.git
cd lurkbot

# Install development dependencies
make dev

# Install pre-commit hooks
pre-commit install

# Run tests
make test

# Run linting
make lint
```

### Project Structure

```
lurkbot/
├── src/lurkbot/           # Main source code
│   ├── gateway/           # Gateway server
│   ├── channels/          # Channel adapters
│   ├── agents/            # Agent runtime
│   ├── tools/             # Built-in tools
│   ├── sessions/          # Session management
│   └── cli/               # CLI commands
├── tests/                 # Test suite
├── docs/                  # Documentation
├── scripts/               # Utility scripts
└── examples/              # Example code
```

## Next Steps

- [Architecture](architecture.md) - Deep dive into the system
- [Contributing](contributing.md) - Start contributing
- [Extending](extending/index.md) - Build custom components
