<div align="center">

# 🦎 LurkBot

**The AI That Actually Does Things — In Python**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

[Features](#features) • [Installation](#installation) • [Quick Start](#quick-start) • [Documentation](#documentation) • [Architecture](#architecture)

</div>

---

## Overview

**LurkBot** is a faithful Python reimplementation of [**moltbot**](https://github.com/moltbot/moltbot) — the open-source personal AI assistant that went viral in early 2026. Built for enthusiasts and developers who want to explore AI agents in Python's rich ecosystem, LurkBot maintains moltbot's powerful architecture while leveraging Python's strengths.

### Why LurkBot?

- **Python-Native**: Leverage Python's vast ecosystem (FastAPI, asyncio, Docker SDK)
- **Educational**: Learn AI agent architecture through clean, typed Python code
- **Production-Ready**: Same enterprise-grade design as moltbot, different implementation
- **Community-Driven**: Built for Python developers who prefer PyPI over npm

---

## Features

### Core Capabilities

- **🔌 Multi-Channel Inbox** — WhatsApp, Telegram, Discord, Slack, Signal, iMessage, and more
- **🤖 Multi-Model Support** — Claude, GPT, Gemini, Ollama (local), and any OpenAI-compatible API
- **🌐 WebSocket Gateway** — Local-first control plane for sessions, channels, and tools
- **🛠️ Tool Execution** — Browser automation, file operations, shell commands, and custom tools
- **🔒 Sandbox Isolation** — Docker-based security for untrusted contexts (group chats, public channels)
- **💬 Session Management** — Persistent conversations with context tracking
- **📱 Device Nodes** — Control iOS/macOS/Android devices (camera, screen, location)

### Architectural Highlights

- **Gateway-Centric Design** — Single control plane routes all messages
- **Session Isolation** — Per-user/channel/topic isolation with configurable policies
- **Tool Policies** — Fine-grained control over what each session can execute
- **Skills System** — Extensible plugin architecture for custom capabilities
- **Streaming Responses** — Real-time AI output via WebSocket

---

## Installation

### Prerequisites

- **Python 3.12+**
- **[uv](https://docs.astral.sh/uv/)** (recommended) or pip
- **Docker** (optional, for sandbox isolation)

### Quick Install

```bash
# Clone the repository
git clone https://github.com/yourusername/lurkbot.git
cd lurkbot

# Install dependencies
make dev

# Verify installation
make test
```

### Configuration

Create `~/.lurkbot/.env`:

```bash
# AI Provider (choose one)
LURKBOT_ANTHROPIC_API_KEY=sk-ant-...
LURKBOT_OPENAI_API_KEY=sk-...

# Telegram Bot (optional)
LURKBOT_TELEGRAM__BOT_TOKEN=123456:ABC...
LURKBOT_TELEGRAM__ENABLED=true
```

---

## Quick Start

### Start the Gateway

```bash
make gateway
# Gateway listening on ws://127.0.0.1:18789
```

### Interactive Chat (CLI)

```bash
lurkbot agent chat
# Start chatting with Claude directly
```

### Enable Telegram

1. Create a bot via [@BotFather](https://t.me/botfather)
2. Add token to `.env`: `LURKBOT_TELEGRAM__BOT_TOKEN=...`
3. Restart gateway: `make gateway`

---

## Documentation

### Project Documentation

- **[Architecture Design](docs/design/ARCHITECTURE_DESIGN.md)** — System architecture and design decisions
- **[Moltbot Analysis](docs/design/MOLTBOT_ANALYSIS.md)** — In-depth analysis of the original TypeScript implementation
- **[Next Session Guide](docs/dev/NEXT_SESSION_GUIDE.md)** — Development roadmap and priorities

### External Resources

- **[Moltbot Official Docs](https://docs.molt.bot/)** — Original project documentation
- **[Moltbot GitHub](https://github.com/moltbot/moltbot)** — TypeScript reference implementation

---

## Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────┐
│  Telegram   Discord   Slack   WhatsApp   Signal   iMessage  │
└────────────────────────┬────────────────────────────────────┘
                         │
                    ┌────▼────┐
                    │ Gateway │ (WebSocket Server)
                    └────┬────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
    ┌───▼───┐      ┌────▼────┐      ┌───▼────┐
    │ Agent │      │ Channel │      │  Tool  │
    │Runtime│      │Adapters │      │Registry│
    └───┬───┘      └─────────┘      └───┬────┘
        │                                │
    ┌───▼──────────┐              ┌─────▼─────┐
    │Claude/GPT/   │              │bash/file/ │
    │Gemini/Ollama │              │browser/... │
    └──────────────┘              └───────────┘
```

### Key Design Patterns

- **Gateway Pattern** — Centralized message routing and session management
- **Adapter Pattern** — Unified interface for messaging platforms and AI models
- **Strategy Pattern** — Per-session tool policies and sandbox modes
- **Plugin Pattern** — Extensible skills and custom tools

For detailed architecture, see [ARCHITECTURE_DESIGN.md](docs/design/ARCHITECTURE_DESIGN.md).

---

## Development

### Project Structure

```
lurkbot/
├── src/lurkbot/
│   ├── gateway/          # WebSocket server + RPC protocol
│   ├── agents/           # AI agent runtime + model adapters
│   ├── channels/         # Messaging platform adapters
│   ├── tools/            # Built-in tool implementations
│   ├── config/           # Configuration management
│   ├── cli/              # Command-line interface
│   └── utils/            # Logging, helpers
├── tests/                # pytest test suite
├── docs/                 # Documentation
│   ├── design/           # Architecture docs (EN/ZH)
│   └── dev/              # Development guides
└── Makefile              # Development commands
```

### Commands

```bash
make help       # Show all available commands
make dev        # Install dev dependencies
make test       # Run tests with pytest
make lint       # Run ruff linter
make format     # Format code with ruff
make typecheck  # Run mypy type checker
make check      # Run all checks (lint + typecheck + test)
```

### Contributing

We welcome contributions! LurkBot aims to be a **faithful Python port** of moltbot while embracing Python idioms:

- Follow existing code style (ruff, mypy strict mode)
- Add tests for new features
- Update documentation for API changes
- Reference moltbot's TypeScript implementation when in doubt

---

## Roadmap

### ✅ Phase 1: Foundation (Completed)
- [x] Gateway WebSocket server
- [x] Agent runtime with Claude integration
- [x] Telegram channel adapter
- [x] Configuration system
- [x] CLI interface

### 🚧 Phase 2: Tool System (In Progress)
- [ ] Tool registry and policy engine
- [ ] Built-in tools (bash, file ops, browser)
- [ ] Docker sandbox isolation
- [ ] Tool-calling integration with AI models

### 📋 Phase 3: Channel Expansion
- [ ] Discord adapter
- [ ] Slack adapter
- [ ] WhatsApp adapter (Baileys)
- [ ] Signal adapter

### 📋 Phase 4: Advanced Features
- [ ] Session persistence (JSONL format)
- [ ] Skills system
- [ ] Multi-agent coordination
- [ ] Device nodes (iOS/macOS/Android)

---

## Comparison: Moltbot vs LurkBot

| Feature | Moltbot (TypeScript) | LurkBot (Python) |
|---------|---------------------|------------------|
| **Language** | Node.js 22+ | Python 3.12+ |
| **Package Manager** | pnpm | uv |
| **Web Framework** | Express | FastAPI |
| **Validation** | TypeBox/Zod | Pydantic |
| **CLI** | Commander | Typer |
| **Testing** | Vitest | pytest |
| **Architecture** | Gateway-Centric | Gateway-Centric |
| **Status** | Production | In Development |

---

## License

MIT License - see [LICENSE](LICENSE) file for details.

---

## Acknowledgments

LurkBot is a community-driven Python port of [**moltbot**](https://github.com/moltbot/moltbot) by [Peter Steinberger](https://github.com/steipete). Special thanks to the moltbot community for creating an incredible AI assistant platform.

---

<div align="center">

**Built with Python • Inspired by Moltbot • Powered by Community**

[⭐ Star on GitHub](https://github.com/yourusername/lurkbot) • [📖 Read the Docs](docs/) • [💬 Join Discord](#)

</div>
