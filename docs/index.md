# LurkBot Documentation

<div align="center">

**Python-Based AI Assistant — Action-Oriented Agent Framework**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![PydanticAI](https://img.shields.io/badge/Framework-PydanticAI-009688.svg)](https://ai.pydantic.dev/)

</div>

---

## Welcome to LurkBot

LurkBot is a multi-channel AI assistant system built on the **PydanticAI** framework, supporting Telegram, Discord, Slack, and other messaging platforms. It provides 22 native tools, a nine-layer security policy system, and flexible Bootstrap configuration capabilities—suitable for both daily productivity enhancement and as a reference implementation for AI Agent development.

## Quick Navigation

<table>
<tr>
<td width="50%">

### Getting Started

Start here if you're new

- [Installation](getting-started/installation.md) - Setup and dependencies
- [Quick Start](getting-started/quick-start.md) - 5-minute walkthrough
- [First Bot](getting-started/first-bot.md) - Create a Telegram bot
- [Core Concepts](getting-started/concepts.md) - Architecture overview

</td>
<td width="50%">

### User Guide

Learn how to use LurkBot effectively

- [CLI Commands](user-guide/cli/index.md) - Command-line reference
- [Channels](user-guide/channels/index.md) - Platform integration
- [Agents](user-guide/agents/index.md) - AI models & sessions
- [Built-in Tools](user-guide/tools/index.md) - 22 native tools

</td>
</tr>
<tr>
<td width="50%">

### Advanced Features

Unlock LurkBot's full potential

- [Gateway Service](advanced/gateway.md) - WebSocket RPC interface
- [Skills Extension](advanced/skills.md) - Markdown plugin system
- [Hooks System](advanced/hooks.md) - Event-driven automation
- [Daemon Mode](advanced/daemon.md) - Production deployment

</td>
<td width="50%">

### Developer Resources

Contribute and extend

- [Architecture](developer/architecture.md) - PydanticAI tech stack
- [Contributing](developer/contributing.md) - Development guide
- [API Reference](api/index.md) - RPC methods & protocols
- [Extending](developer/extending/index.md) - Custom tools/channels/skills

</td>
</tr>
</table>

---

## Core Features

| Feature | Description |
|---------|-------------|
| **Multi-Channel** | Telegram, Discord, Slack, CLI (WhatsApp/Signal planned) |
| **Multi-Model** | Claude (Anthropic), GPT (OpenAI), Gemini (Google), Ollama (local) |
| **22 Native Tools** | exec, read, write, edit, web_search, memory, sessions, cron... |
| **Nine-Layer Policy** | Profile/Provider/Global/Agent/Channel/Sandbox/Subagent filtering |
| **Bootstrap Files** | 8 Markdown files define agent personality and context |
| **Sandbox Isolation** | Docker container protection for untrusted execution |

---

## Architecture Overview

```
┌────────────────────────────────────────────────────────────┐
│                   External Platforms                        │
│   Telegram    Discord    Slack    CLI    (WhatsApp...)     │
└──────────────────────┬─────────────────────────────────────┘
                       │
                  ┌────▼─────┐
                  │ Gateway  │  FastAPI + WebSocket
                  │ :18789   │  ws://127.0.0.1:18789
                  └────┬─────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
   ┌────▼────┐   ┌────▼────┐   ┌────▼────┐
   │PydanticAI│   │ Channel │   │ 22 Tools │
   │  Agent   │   │ Adapters│   │ + Policy │
   └────┬─────┘   └─────────┘   └────┬────┘
        │                             │
   ┌────▼────────────┐       ┌───────▼───────┐
   │ Claude/GPT/     │       │ exec/read/    │
   │ Gemini/Ollama   │       │ write/web/... │
   └─────────────────┘       └───────────────┘

Bootstrap File System:
~/clawd/
├── SOUL.md      (Core personality & values)
├── IDENTITY.md  (Name & appearance)
├── USER.md      (User preferences)
├── AGENTS.md    (Workspace guidelines)
├── TOOLS.md     (Tool configuration)
├── MEMORY.md    (Long-term memory)
├── HEARTBEAT.md (Periodic checks)
└── BOOTSTRAP.md (First-run setup)
```

---

## Quick Start

```bash
# Clone repository
git clone https://github.com/uukuguy/lurkbot.git
cd lurkbot

# Install dependencies (using uv or pip)
make dev  # or: pip install -e .[dev]

# Configure API Key (choose one AI provider)
export LURKBOT_ANTHROPIC_API_KEY=sk-ant-...
# or: export LURKBOT_OPENAI_API_KEY=sk-...
# or: export LURKBOT_GOOGLE_API_KEY=...

# Start Gateway
lurkbot gateway start

# Start chatting (CLI mode)
lurkbot agent chat
```

See the [Quick Start Guide](getting-started/quick-start.md) for detailed instructions.

---

## Technology Stack

| Component | Technology |
|-----------|------------|
| Agent Framework | **PydanticAI** - Modern Python Agent framework |
| Web Framework | **FastAPI** - Async ASGI server |
| CLI | **Typer** - Command-line interface |
| Data Validation | **Pydantic** - Type safety |
| Logging | **Loguru** - Structured logging |
| Package Manager | **uv** - Fast Python package manager |

---

## Community & Support

- **GitHub Issues**: [Report bugs or request features](https://github.com/uukuguy/lurkbot/issues)
- **Discussions**: [Ask questions and share ideas](https://github.com/uukuguy/lurkbot/discussions)
- **Project Status**: 23 development phases completed, 562 test cases passing

---

## License

LurkBot is released under the [MIT License](https://opensource.org/licenses/MIT).

---

<div align="center">

**Built with Python • Powered by PydanticAI • Community Driven**

</div>
