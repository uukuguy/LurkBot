# LurkBot - Enterprise-Grade Multi-Channel AI Assistant Platform

## Project Overview

LurkBot is a production-ready Python implementation of a multi-channel AI assistant platform, featuring industry-first innovations like the **Nine-Layer Tool Policy Engine** and **Bootstrap File System**. Version 1.0.0 with 625+ tests passing.

**Status**: v1.0.0-alpha.1 (Internal Integration Testing)
**Tests**: 625+ (100% passing)
**Code**: ~79,520 lines Python

## Key Architecture Decisions

| Component | Technology | Rationale |
|-----------|------------|-----------|
| **Package Manager** | uv | Fast, modern Python package manager |
| **Build Entry** | Makefile | Unified command interface |
| **Web Framework** | FastAPI | Async ASGI server with WebSocket support |
| **Validation** | Pydantic 2.10+ | Type safety and data validation |
| **CLI** | Typer + Rich | Modern command-line interface |
| **Logging** | Loguru | Structured logging |
| **AI Framework** | PydanticAI 1.0+ | Modern Python Agent framework |
| **Container** | Docker + Kubernetes | Production deployment |

## Core Innovations

### 1. Nine-Layer Tool Policy Engine
Hierarchical permission control system (1021 lines in `tools/policy.py`):
```
Layer 1: Profile Policy        (minimal/coding/messaging/full)
Layer 2: Provider Profile      (per AI provider settings)
Layer 3: Global Allow/Deny     (system-wide rules)
Layer 4: Global Provider       (provider-specific globals)
Layer 5: Agent Policy          (per-agent configuration)
Layer 6: Agent Provider        (agent + provider combo)
Layer 7: Group/Channel         (channel-specific rules)
Layer 8: Sandbox Policy        (isolation enforcement)
Layer 9: Subagent Policy       (child agent restrictions)
```

### 2. Bootstrap File System (8 files)
Markdown-driven agent configuration in `~/.lurkbot/`:
- `SOUL.md` - Core personality & values (not passed to subagents)
- `IDENTITY.md` - Name & appearance (not passed to subagents)
- `USER.md` - User preferences (not passed to subagents)
- `AGENTS.md` - Workspace guidelines (passed to subagents)
- `TOOLS.md` - Tool configuration (passed to subagents)
- `MEMORY.md` - Long-term memory (main session only)
- `HEARTBEAT.md` - Periodic check tasks (main session only)
- `BOOTSTRAP.md` - First-run setup (deleted after completion)

### 3. 23-Part System Prompt Generator
Modular prompt construction in `agents/system_prompt.py` (592 lines).

### 4. Multi-Dimensional Session Isolation
5 session types: main, group, topic, dm, subagent with automatic routing.

### 5. Adaptive Context Compaction
Intelligent chunking with multi-stage summarization in `agents/compaction.py`.

## Module Structure (30+ Modules)

```
src/lurkbot/
├── agents/           # AI agent runtime
│   ├── bootstrap.py      # Bootstrap file loading
│   ├── system_prompt.py  # 23-part prompt generator
│   ├── compaction.py     # Context compression
│   ├── runtime.py        # Agent execution
│   └── subagent/         # Subagent communication
├── tools/            # Tool system
│   ├── policy.py         # 9-layer policy engine (1021 lines)
│   ├── registry.py       # Tool registration
│   └── builtin/          # 22 built-in tools
├── sessions/         # Session management
│   ├── store.py          # JSONL persistence
│   └── manager.py        # Session lifecycle
├── gateway/          # WebSocket gateway
│   ├── server.py         # WebSocket server
│   ├── app.py            # FastAPI application
│   └── protocol.py       # RPC protocol
├── channels/         # Channel adapters
│   ├── telegram.py       # Telegram adapter
│   ├── discord.py        # Discord adapter
│   ├── slack.py          # Slack adapter
│   ├── wework.py         # WeWork (企业微信)
│   ├── dingtalk.py       # DingTalk (钉钉)
│   └── feishu.py         # Feishu (飞书)
├── plugins/          # Plugin system
│   ├── loader.py         # Plugin discovery
│   ├── manager.py        # Plugin lifecycle
│   └── sandbox.py        # Sandbox execution
├── skills/           # Skills system
│   └── registry.py       # Skill loading
├── hooks/            # Hook system
│   └── registry.py       # 10 event types
├── tenants/          # Multi-tenant system
│   ├── quota.py          # Quota management
│   ├── policy.py         # Policy enforcement
│   └── audit.py          # Audit logging
├── monitoring/       # Monitoring system
│   ├── metrics.py        # Prometheus metrics
│   └── exporter.py       # Metrics export
├── security/         # Security system
│   ├── audit.py          # Security audit
│   └── sandbox.py        # Docker sandbox
├── infra/            # Infrastructure (8 subsystems)
│   ├── system_events/    # Event queue
│   ├── system_presence/  # Node presence
│   ├── tailscale/        # VPN integration
│   ├── ssh_tunnel/       # SSH tunneling
│   ├── bonjour/          # mDNS discovery
│   ├── device_pairing/   # Device pairing
│   ├── exec_approvals/   # Exec approval
│   └── voicewake/        # Voice wake
├── browser/          # Browser automation
│   └── playwright.py     # Playwright integration
├── memory/           # Memory system
│   └── vector.py         # Vector search
├── autonomous/       # Autonomous operation
│   ├── heartbeat.py      # Heartbeat runner
│   └── cron.py           # Cron scheduler
├── acp/              # Agent Communication Protocol
│   └── protocol.py       # ACP implementation
├── daemon/           # Daemon management
│   └── service.py        # Cross-platform daemon
├── tui/              # Terminal UI
│   └── components.py     # Rich components
├── tts/              # Text-to-speech
│   └── providers.py      # Edge/ElevenLabs/OpenAI
├── canvas/           # Canvas rendering
├── media/            # Media understanding
├── auto_reply/       # Auto-reply system
├── routing/          # Message routing
├── auth/             # Authentication
├── usage/            # Usage tracking
├── wizard/           # Configuration wizard
├── config/           # Configuration
├── cli/              # CLI commands
└── logging/          # Logging system
```

## Development Commands

```bash
make help       # Show all available commands
make dev        # Install dev dependencies
make test       # Run tests with pytest
make lint       # Run ruff linter
make format     # Format code with ruff
make typecheck  # Run mypy type checker
make check      # Run all checks (lint + typecheck + test)
make gateway    # Start gateway server
```

## Testing

```bash
# Run all tests
pytest -xvs

# Run with coverage
pytest --cov=src --cov-report=term-missing

# Run specific module tests
pytest tests/integration/test_e2e_chat_flow.py -xvs
pytest tests/tenants/test_audit.py -xvs
```

## Docker Deployment

```bash
# Build and run
docker compose up -d

# Health check
curl http://localhost:18789/health
```

## Kubernetes Deployment

```bash
# Apply all manifests
kubectl apply -k k8s/

# Verify
kubectl get pods -n lurkbot
```

## Key Files Reference

| File | Lines | Description |
|------|-------|-------------|
| `tools/policy.py` | 1021 | Nine-layer policy engine |
| `agents/system_prompt.py` | 592 | 23-part prompt generator |
| `agents/bootstrap.py` | ~400 | Bootstrap file loading |
| `agents/compaction.py` | ~300 | Context compression |
| `gateway/server.py` | ~500 | WebSocket server |
| `sessions/manager.py` | ~400 | Session management |

## Reference

- Original inspiration: [OpenClaw/Moltbot](https://github.com/openclaw/openclaw)
- AI Framework: [PydanticAI](https://ai.pydantic.dev/)
- Documentation: `docs/` directory
