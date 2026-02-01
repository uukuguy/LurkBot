<div align="center">

# 🦎 LurkBot

**Enterprise-Grade Multi-Channel AI Assistant Platform**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Tests: 625+](https://img.shields.io/badge/tests-625%2B%20passed-brightgreen.svg)](#testing)
[![Version: v1.0.0-alpha.1](https://img.shields.io/badge/version-v1.0.0--alpha.1-orange.svg)](#roadmap)

[Features](#features) • [Innovations](#key-innovations) • [Quick Start](#quick-start) • [Architecture](#architecture) • [Documentation](docs/index.md) • [中文文档](README.zh.md)

</div>

---

## Why LurkBot?

**LurkBot** is a production-ready Python implementation of a multi-channel AI assistant platform, featuring industry-first innovations like the **Nine-Layer Tool Policy Engine** and **Bootstrap File System**. Built for enterprises and power users who need:

- **Multi-Channel Presence** — Telegram, Discord, Slack, WeWork, DingTalk, Feishu, and more
- **Real Tool Execution** — 22 native tools with Docker sandbox isolation
- **Enterprise Multi-Tenancy** — Quota management, audit logging, compliance reporting
- **Production Deployment** — Docker + Kubernetes with HPA, health checks, and monitoring
- **Local-First Control** — Your data, your devices, your rules

> *"A personal AI assistant that actually gets things done — securely, at scale."*

---

## Key Innovations

### 🏆 Industry-First Features

| Innovation | Description |
|------------|-------------|
| **Nine-Layer Tool Policy Engine** | Hierarchical permission control: Profile → Provider → Global → Agent → Channel → Sandbox → Subagent |
| **Bootstrap File System** | 8 Markdown files define agent personality, memory, and behavior |
| **23-Part System Prompt Generator** | Modular, configurable prompt construction with dynamic sections |
| **Multi-Dimensional Session Isolation** | 5 session types with automatic routing and policy enforcement |
| **Adaptive Context Compaction** | Intelligent chunking with multi-stage summarization |
| **Subagent Communication Protocol** | Hierarchical task delegation with depth limiting (max 3 levels) |

### 🔧 Technical Highlights

```
┌─────────────────────────────────────────────────────────────────┐
│                    Nine-Layer Tool Policy Engine                 │
├─────────────────────────────────────────────────────────────────┤
│  Layer 1: Profile Policy        (minimal/coding/messaging/full) │
│  Layer 2: Provider Profile      (per AI provider settings)      │
│  Layer 3: Global Allow/Deny     (system-wide rules)             │
│  Layer 4: Global Provider       (provider-specific globals)     │
│  Layer 5: Agent Policy          (per-agent configuration)       │
│  Layer 6: Agent Provider        (agent + provider combo)        │
│  Layer 7: Group/Channel         (channel-specific rules)        │
│  Layer 8: Sandbox Policy        (isolation enforcement)         │
│  Layer 9: Subagent Policy       (child agent restrictions)      │
└─────────────────────────────────────────────────────────────────┘
```

---

## Features

### Core Platform (v1.0.0 - 100% Complete)

| Feature | Description |
|---------|-------------|
| **Multi-Channel Support** | Telegram, Discord, Slack, WeWork, DingTalk, Feishu + extensible adapters |
| **Multi-Model AI** | Claude, GPT, Gemini, Ollama, DeepSeek, Qwen, Kimi, ChatGLM (13+ models) |
| **22 Native Tools** | exec, read, write, edit, web_search, browser, memory, sessions, cron, canvas, tts... |
| **WebSocket Gateway** | Full-featured control plane with RPC protocol |
| **Session Management** | 5 session types with JSONL persistence |
| **Subagent System** | Hierarchical task delegation with communication protocol |

### Enterprise Features

| Feature | Description |
|---------|-------------|
| **Multi-Tenant System** | 4 tiers (Free/Basic/Professional/Enterprise) with quota management |
| **Audit Logging** | Complete operation audit with compliance reporting |
| **Alert System** | Quota alerts, anomaly detection, notification channels |
| **Monitoring** | Prometheus metrics, performance dashboards |
| **Security** | Docker sandbox, 9-layer policy, exec approvals |

### Production Deployment

| Feature | Description |
|---------|-------------|
| **Docker** | Multi-stage builds, non-root user, health checks |
| **Kubernetes** | Deployment, HPA, PDB, Ingress, ConfigMap, Secrets |
| **Health Endpoints** | `/health`, `/ready`, `/live` for probes |
| **Observability** | Structured logging, metrics export |

### China Ecosystem Support 🇨🇳

| Feature | Description |
|---------|-------------|
| **Enterprise Messaging** | WeWork (企业微信), DingTalk (钉钉), Feishu (飞书) |
| **Domestic LLMs** | DeepSeek, Qwen, Kimi, ChatGLM + 9 more via OpenAI-compatible API |
| **Vector Database** | sqlite-vec for lightweight semantic search |

---

## Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        User Interface Layer                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │
│  │   TUI    │  │  Web UI  │  │   CLI    │  │  Wizard  │        │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘        │
└───────┼─────────────┼──────────────┼─────────────┼──────────────┘
        │             │              │             │
┌───────┴─────────────┴──────────────┴─────────────┴──────────────┐
│                    Gateway WebSocket Layer                       │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │    Gateway Server (FastAPI + WebSocket + RPC Protocol)     │ │
│  │    - Protocol Handling  - Event Broadcasting  - Sessions   │ │
│  └──────────────────────────┬─────────────────────────────────┘ │
└─────────────────────────────┼───────────────────────────────────┘
                              │
┌─────────────────────────────┴───────────────────────────────────┐
│                       Core Services Layer                        │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │   Agent     │  │   Session    │  │  Auto-Reply  │           │
│  │   Runtime   │  │   Manager    │  │  & Routing   │           │
│  └──────┬──────┘  └──────┬───────┘  └──────┬───────┘           │
│         │                │                  │                   │
│  ┌──────┴────────────────┴──────────────────┴───────┐          │
│  │              Message Processing Center            │          │
│  │  - Message Routing  - Queue Management  - Events │          │
│  └──────┬────────────────────────────────────┬──────┘          │
└─────────┼────────────────────────────────────┼──────────────────┘
          │                                    │
┌─────────┴────────────────────────────────────┴──────────────────┐
│                      Channel Adapter Layer                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │
│  │Telegram  │  │ Discord  │  │  Slack   │  │  WeWork  │        │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                      │
│  │ DingTalk │  │  Feishu  │  │   Mock   │                      │
│  └──────────┘  └──────────┘  └──────────┘                      │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                      Support Services Layer                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Tool System  │  │   Security   │  │    Infra     │          │
│  │ - 22 Tools   │  │ - Audit      │  │ - Tailscale  │          │
│  │ - 9L Policy  │  │ - Sandbox    │  │ - Bonjour    │          │
│  │ - Plugins    │  │ - Approvals  │  │ - SSH Tunnel │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   Skills &   │  │    Hooks     │  │  Multi-      │          │
│  │   Plugins    │  │   System     │  │  Tenant      │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
```

### Bootstrap File System

```
~/.lurkbot/
├── SOUL.md       # Core personality & values (not passed to subagents)
├── IDENTITY.md   # Name & appearance (not passed to subagents)
├── USER.md       # User preferences (not passed to subagents)
├── AGENTS.md     # Workspace guidelines (passed to subagents)
├── TOOLS.md      # Tool configuration (passed to subagents)
├── MEMORY.md     # Long-term memory (main session only)
├── HEARTBEAT.md  # Periodic check tasks (main session only)
└── BOOTSTRAP.md  # First-run setup (deleted after completion)
```

### Module Structure (30+ Modules)

```
src/lurkbot/
├── agents/           # AI agent runtime (bootstrap, system_prompt, compaction)
├── tools/            # 22 built-in tools + 9-layer policy engine
├── sessions/         # Session management + JSONL persistence
├── gateway/          # WebSocket server + RPC protocol + FastAPI app
├── channels/         # Channel adapters (Telegram, Discord, Slack, WeWork...)
├── plugins/          # Plugin system (loader, manager, sandbox)
├── skills/           # Skills system + ClawHub integration
├── hooks/            # Event-driven hook system (10 event types)
├── tenants/          # Multi-tenant system (quota, policy, audit)
├── monitoring/       # Prometheus metrics + performance tracking
├── security/         # Security audit + sandbox isolation
├── infra/            # 8 infrastructure subsystems
├── browser/          # Playwright browser automation
├── memory/           # Vector search + knowledge persistence
├── autonomous/       # Heartbeat + Cron autonomous operation
├── acp/              # Agent Communication Protocol
├── daemon/           # Cross-platform daemon management
├── tui/              # Terminal UI (Rich components)
├── tts/              # Text-to-speech (Edge/ElevenLabs/OpenAI)
├── canvas/           # Canvas rendering system
├── media/            # Media understanding (4 providers)
├── auto_reply/       # Auto-reply queue system
├── routing/          # 6-layer message routing
├── auth/             # Authentication + profile rotation
├── usage/            # Usage tracking + cost calculation
├── wizard/           # Configuration wizard
├── config/           # Configuration management
├── cli/              # Command-line interface (Typer)
└── logging/          # Structured logging (Loguru)
```

---

## Quick Start

### Prerequisites

- **Python 3.12+**
- **[uv](https://docs.astral.sh/uv/)** (recommended) or pip
- **Docker** (optional, for sandbox isolation and deployment)

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
# AI Provider (choose one or more)
LURKBOT_ANTHROPIC_API_KEY=sk-ant-...
LURKBOT_OPENAI_API_KEY=sk-...

# Telegram Bot (optional)
LURKBOT_TELEGRAM__BOT_TOKEN=123456:ABC...
LURKBOT_TELEGRAM__ENABLED=true
```

### Run

```bash
# Start the Gateway
lurkbot gateway --host 0.0.0.0 --port 18789
# Gateway listening on ws://127.0.0.1:18789

# Start chatting (CLI mode)
lurkbot agent chat
```

### Docker Deployment

```bash
# Quick start with Docker Compose
cp .env.example .env
# Edit .env with your API keys
docker compose up -d

# Verify
curl http://localhost:18789/health
```

### Kubernetes Deployment

```bash
# Apply all manifests
kubectl apply -k k8s/

# Verify
kubectl get pods -n lurkbot
kubectl port-forward svc/lurkbot-gateway 18789:18789 -n lurkbot
```

---

## Plugin System

LurkBot features a powerful plugin system for extending capabilities:

### Built-in Example Plugins

| Plugin | Description | Permissions |
|--------|-------------|-------------|
| **weather-plugin** | Real-time weather via wttr.in API | network |
| **time-utils-plugin** | Multi-timezone time conversion | none |
| **system-info-plugin** | CPU, memory, disk monitoring | filesystem |

### Quick Example

```python
# .plugins/hello-plugin/main.py
async def execute(context):
    name = context.input_data.get("name", "World")
    return {"message": f"Hello, {name}!"}
```

```bash
# Use the plugin
lurkbot plugin exec hello-plugin --input '{"name": "Alice"}'
```

See [Plugin Documentation](docs/design/PLUGIN_USER_GUIDE.md) for details.

---

## Testing

### Test Statistics

| Category | Tests | Status |
|----------|-------|--------|
| Integration Tests | 219 | ✅ Passed |
| Phase Tests | 343+ | ✅ Passed |
| Unit Tests | 100+ | ✅ Passed |
| **Total** | **625+** | **✅ 100% Passed** |

### Run Tests

```bash
# Run all tests
make test

# Run with coverage
pytest --cov=src --cov-report=term-missing

# Run specific test
pytest tests/integration/test_e2e_chat_flow.py -xvs
```

---

## Documentation

📚 **[Full Documentation](docs/index.md)**

### Quick Links

| Section | Description |
|---------|-------------|
| [Getting Started](docs/getting-started/index.md) | Installation, quick start, first bot |
| [User Guide](docs/user-guide/index.md) | CLI, channels, agents, tools, configuration |
| [Advanced Features](docs/advanced/index.md) | Gateway, hooks, skills, daemon, cron |
| [Developer Guide](docs/developer/index.md) | Architecture, contributing, extending |
| [API Reference](docs/api/index.md) | CLI reference, RPC methods |
| [Deployment Guide](docs/deploy/DEPLOYMENT_GUIDE.md) | Docker, Kubernetes deployment |

### Design Documents

- [Architecture Design](docs/design/ARCHITECTURE_DESIGN.md)
- [Plugin System Design](docs/design/PLUGIN_SYSTEM_DESIGN.md)
- [China Ecosystem Guide](docs/design/CHINA_ECOSYSTEM_GUIDE.md)

---

## Technology Stack

| Component | Technology |
|-----------|------------|
| **AI Framework** | PydanticAI 1.0+ |
| **Web Framework** | FastAPI + Uvicorn |
| **Data Validation** | Pydantic 2.10+ |
| **CLI** | Typer + Rich |
| **Logging** | Loguru |
| **Package Manager** | uv |
| **Container** | Docker + Kubernetes |
| **Vector DB** | ChromaDB + sqlite-vec |
| **Browser** | Playwright |

---

## Roadmap

### ✅ v1.0.0 (Current Release)

- [x] Core Infrastructure (Gateway, Agent Runtime, Sessions)
- [x] 22 Native Tools + Nine-Layer Policy Engine
- [x] Multi-Channel Support (7 platforms)
- [x] Multi-Model AI (13+ models)
- [x] Plugin System with 3 example plugins
- [x] Multi-Tenant System with quota management
- [x] Monitoring + Audit Logging
- [x] Docker + Kubernetes Deployment
- [x] 625+ Tests (100% passing)

### 🔮 Future Plans

- [ ] CI/CD Pipeline (GitHub Actions + ArgoCD)
- [ ] Enhanced Observability (Grafana dashboards)
- [ ] Additional Channel Adapters
- [ ] Plugin Marketplace

---

## Comparison: Moltbot vs LurkBot

| Feature | Moltbot (TypeScript) | LurkBot (Python) |
|---------|---------------------|------------------|
| **Language** | Node.js 22+ | Python 3.12+ |
| **Code Size** | ~411,783 LOC | ~79,520 LOC |
| **Agent Framework** | Pi SDK | PydanticAI |
| **Multi-Tenant** | ❌ | ✅ |
| **Monitoring** | Basic | Prometheus |
| **K8s Deployment** | ❌ | ✅ |
| **China Ecosystem** | Partial | Complete |
| **Status** | Production | v1.0.0 Production |

---

## License

MIT License — see [LICENSE](LICENSE) file for details.

---

## Acknowledgments

LurkBot is inspired by [**OpenClaw/Moltbot**](https://github.com/openclaw/openclaw). Special thanks to the open-source AI assistant community.

---

<div align="center">

**Built with Python • Powered by PydanticAI • Production Ready**

[⭐ Star on GitHub](https://github.com/uukuguy/lurkbot) • [📖 Documentation](docs/index.md) • [🐛 Issues](https://github.com/uukuguy/lurkbot/issues)

</div>
