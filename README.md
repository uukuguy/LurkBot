<div align="center">

# 🦎 LurkBot

**Your Personal AI Assistant That Actually Gets Things Done**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Status: Beta](https://img.shields.io/badge/status-beta%20(97%25)-brightgreen.svg)](#roadmap)

[Features](#features) • [Quick Start](#quick-start) • [Documentation](docs/index.md) • [Architecture](#architecture) • [Roadmap](#roadmap) • [中文文档](README.zh.md)

</div>

---

## Why LurkBot?

**LurkBot** is a Python reimplementation of [**Moltbot**](https://github.com/moltbot/moltbot) — the open-source personal AI assistant that took the developer community by storm in early 2026. While Moltbot runs on Node.js, LurkBot brings the same powerful architecture to Python developers who want:

- **A personal AI that lives where you do** — WhatsApp, Telegram, Discord, Slack, and more
- **Real tool execution** — Browse the web, run commands, manage files, automate tasks
- **Local-first control** — Your data, your devices, your rules
- **Always-on availability** — Daemon mode keeps your assistant ready 24/7

> *"If you want a personal, single-user assistant that feels local, fast, and always-on, this is it."*

### What Makes It Different?

Unlike cloud-only AI assistants, LurkBot runs on **your** devices. It connects to **your** messaging apps. It executes tools with **your** permissions. The Gateway is just the control plane — the product is the assistant that actually does things for you.

---

## Features

### Core Capabilities (97% Complete)

| Feature | Description |
|---------|-------------|
| **Multi-Channel Inbox** | Telegram (fully implemented), extensible to WhatsApp, Discord, Slack, Signal |
| **Multi-Model Support** | Claude, GPT, Gemini, Ollama (local) via PydanticAI integration |
| **WebSocket Gateway** | Full-featured control plane for sessions, channels, and tools |
| **22 Native Tools** | exec, read, write, edit, web_search, browser, memory, sessions, cron... |
| **Nine-Layer Policy Engine** | Profile/Provider/Global/Agent/Channel/Sandbox/Subagent filtering |
| **Bootstrap Files** | 8 Markdown files define agent personality and context |
| **Sandbox Isolation** | Docker container protection for untrusted execution |

### Architectural Highlights

- **Gateway-Centric Design** — Single control plane routes all messages
- **Session Isolation** — Per-user/channel/topic isolation with configurable policies
- **Skills System** — Extensible plugin architecture for custom capabilities
- **Hooks System** — Event-driven automation with pre/post tool hooks
- **Daemon System** — Cross-platform background service management
- **Auto-Reply & Routing** — Intelligent message routing and auto-response
- **Infra System** — 8 infrastructure subsystems for production deployment
- **ACP Protocol** — Agent Communication Protocol for multi-agent coordination

---

## Quick Start

### Prerequisites

- **Python 3.12+**
- **[uv](https://docs.astral.sh/uv/)** (recommended) or pip
- **Docker** (optional, for sandbox isolation)

### Installation

```bash
# Clone the repository
git clone https://github.com/uukuguy/lurkbot.git
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

### Run

```bash
# Start the Gateway
lurkbot gateway start
# Gateway listening on ws://127.0.0.1:18789

# Start chatting (CLI mode)
lurkbot agent chat
```

---

## Documentation

📚 **[Full Documentation](docs/index.md)** — Start here for comprehensive guides

### Quick Links

| Section | Description |
|---------|-------------|
| [Getting Started](docs/getting-started/index.md) | Installation, quick start, first bot |
| [User Guide](docs/user-guide/index.md) | CLI, channels, agents, tools, configuration |
| [Advanced Features](docs/advanced/index.md) | Gateway, hooks, skills, daemon, cron |
| [Developer Guide](docs/developer/index.md) | Architecture, contributing, extending |
| [API Reference](docs/api/index.md) | CLI reference, RPC methods |
| [Troubleshooting](docs/troubleshooting/index.md) | FAQ, common issues |

### Design Documents

- [Architecture Design](docs/design/ARCHITECTURE_DESIGN.md) — System architecture and design decisions
- [Moltbot Analysis](docs/design/MOLTBOT_ANALYSIS.md) — In-depth analysis of the original TypeScript implementation

---

## Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────┐
│  Telegram   Discord   Slack   WhatsApp   Signal   CLI       │
└────────────────────────┬────────────────────────────────────┘
                         │
                    ┌────▼────┐
                    │ Gateway │  FastAPI + WebSocket
                    │ :18789  │  ws://127.0.0.1:18789
                    └────┬────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
    ┌───▼───┐      ┌────▼────┐      ┌───▼────┐
    │Agent  │      │ Channel │      │22 Tools│
    │Runtime│      │Adapters │      │+ Policy│
    └───┬───┘      └─────────┘      └───┬────┘
        │                                │
    ┌───▼──────────┐              ┌─────▼─────┐
    │Claude/GPT/   │              │exec/read/ │
    │Gemini/Ollama │              │write/web..│
    └──────────────┘              └───────────┘

Bootstrap File System:
~/.lurkbot/
├── SOUL.md      (Core personality & values)
├── IDENTITY.md  (Name & appearance)
├── USER.md      (User preferences)
├── AGENTS.md    (Workspace guidelines)
├── TOOLS.md     (Tool configuration)
├── MEMORY.md    (Long-term memory)
├── HEARTBEAT.md (Periodic checks)
└── BOOTSTRAP.md (First-run setup)
```

### Key Design Patterns

- **Gateway Pattern** — Centralized message routing and session management
- **Adapter Pattern** — Unified interface for messaging platforms and AI models
- **Strategy Pattern** — Per-session tool policies and sandbox modes
- **Plugin Pattern** — Extensible skills and custom tools

---

## Development

### Project Structure

```
lurkbot/
├── src/lurkbot/
│   ├── gateway/          # WebSocket server + RPC protocol
│   ├── agents/           # AI agent runtime + PydanticAI integration
│   ├── sessions/         # Session management + JSONL persistence
│   ├── tools/            # 22 built-in tools + 9-layer policy engine
│   ├── skills/           # Extensible skills system
│   ├── hooks/            # Event-driven hook system
│   ├── daemon/           # Cross-platform daemon management
│   ├── routing/          # Message routing system
│   ├── auto_reply/       # Auto-reply system
│   ├── infra/            # Infrastructure (8 subsystems)
│   ├── plugins/          # Plugin system
│   ├── security/         # Security + sandbox isolation
│   ├── media/            # Media processing
│   ├── memory/           # Vector search + knowledge persistence
│   ├── browser/          # Playwright browser automation
│   ├── canvas/           # Canvas rendering
│   ├── tui/              # Terminal UI
│   ├── tts/              # Text-to-speech
│   ├── usage/            # Usage tracking
│   ├── wizard/           # Configuration wizard
│   ├── auth/             # Authentication
│   ├── autonomous/       # Autonomous operation mode
│   ├── acp/              # Agent Communication Protocol
│   ├── config/           # Configuration management
│   ├── cli/              # Command-line interface
│   └── logging/          # Structured logging
├── tests/                # pytest test suite
├── docs/                 # Documentation
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

We welcome contributions! LurkBot aims to be a **faithful Python port** of Moltbot while embracing Python idioms:

- Follow existing code style (ruff, mypy strict mode)
- Add tests for new features
- Update documentation for API changes
- Reference Moltbot's TypeScript implementation when in doubt

---

## Roadmap

### ✅ Phase 1: Core Infrastructure (Completed)
- [x] Gateway WebSocket server
- [x] Agent runtime with PydanticAI integration
- [x] Configuration system
- [x] Logging system

### ✅ Phase 2: Tool & Session System (Completed)
- [x] Tool registry with 9-layer policy engine
- [x] 22 built-in tools (bash, file ops, browser, etc.)
- [x] Session management with JSONL persistence
- [x] Skills system
- [x] Hooks system

### ✅ Phase 3: Advanced Features (Completed)
- [x] Daemon system (cross-platform)
- [x] Auto-reply & routing system
- [x] Security system with sandbox isolation
- [x] Memory system (vector search)
- [x] Media processing
- [x] Browser automation (Playwright)
- [x] Canvas & TUI
- [x] TTS system
- [x] Plugin system
- [x] Infra system (8 subsystems)
- [x] ACP (Agent Communication Protocol)
- [x] Autonomous operation mode
- [x] Authentication system
- [x] Configuration wizard
- [x] Usage tracking

### 🚧 Phase 4: Polish & Production (In Progress)
- [ ] Complete CLI command set (currently ~30%)
- [ ] Additional channel adapters (Discord, Slack, WhatsApp)
- [ ] Improve test coverage
- [ ] Production deployment documentation

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
| **Status** | Production | Beta (97% Complete) |

---

## Technology Stack

| Component | Technology |
|-----------|------------|
| Agent Framework | **PydanticAI** — Modern Python Agent framework |
| Web Framework | **FastAPI** — Async ASGI server |
| CLI | **Typer** — Command-line interface |
| Data Validation | **Pydantic** — Type safety |
| Logging | **Loguru** — Structured logging |
| Package Manager | **uv** — Fast Python package manager |

---

## License

MIT License — see [LICENSE](LICENSE) file for details.

---

## Acknowledgments

LurkBot is a community-driven Python port of [**Moltbot**](https://github.com/moltbot/moltbot) by [Peter Steinberger](https://github.com/steipete). Special thanks to the Moltbot community for creating an incredible AI assistant platform.

---

<div align="center">

**Built with Python • Inspired by Moltbot • Powered by PydanticAI**

[⭐ Star on GitHub](https://github.com/uukuguy/lurkbot) • [📖 Documentation](docs/index.md) • [💬 Join Discord](#)

</div>
