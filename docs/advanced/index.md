# Advanced Features

This section covers advanced LurkBot features for power users.

## Overview

| Feature | Description | Status |
|---------|-------------|--------|
| [Gateway](gateway.md) | Central WebSocket control plane | Implemented |
| [Skills](skills.md) | Extensible plugin system | Implemented |
| [Hooks](hooks.md) | Event-driven automation | Implemented |
| [Cron Jobs](cron.md) | Scheduled tasks | Implemented |
| [Daemon Mode](daemon.md) | Background service operation | Implemented |

## Implementation Status

LurkBot advanced features are built on the PydanticAI framework with implementations mirroring MoltBot's architecture:

| Component | Source Location | Description |
|-----------|----------------|-------------|
| Gateway Server | `src/lurkbot/gateway/server.py` | WebSocket server with RPC methods |
| Hooks System | `src/lurkbot/hooks/` | Event-driven hook registration |
| Daemon Service | `src/lurkbot/daemon/service.py` | Cross-platform service management |
| Cron Tool | `src/lurkbot/tools/builtin/cron_tool.py` | Scheduled task management |
| Skills | `src/lurkbot/skills/` | Markdown-based plugin system |

## Quick Links

### Automation

- **[Cron Jobs](cron.md)** - Schedule recurring tasks with `at`, `every`, or cron expressions
- **[Hooks](hooks.md)** - Event-driven actions for command, session, agent, and gateway events

### Extensibility

- **[Skills](skills.md)** - Add custom capabilities with markdown-based plugins
- **[Gateway](gateway.md)** - Understand the WebSocket architecture

### Operations

- **[Daemon Mode](daemon.md)** - Run as a background service (launchd, systemd, schtasks)

## Getting Started

Most advanced features require the Gateway to be running:

```bash
lurkbot gateway start
```

For production use, consider [Daemon Mode](daemon.md):

```bash
# Install as system service
lurkbot daemon install

# Start the service
lurkbot daemon start
```

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    GatewayServer                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │  WebSocket  │  │   Method    │  │       Event         │  │
│  │   Handler   │  │  Registry   │  │    Broadcaster      │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
         ↑                   ↑                    ↑
         │                   │                    │
    ┌────┴────┐        ┌────┴────┐         ┌────┴────┐
    │  Hooks  │        │  Cron   │         │  Skills │
    │ Registry│        │  Tool   │         │ Manager │
    └─────────┘        └─────────┘         └─────────┘
```

Source: `src/lurkbot/gateway/server.py:49-62`

```python
class GatewayServer:
    VERSION = "0.1.0"
    PROTOCOL_VERSION = 1

    def __init__(self):
        self._connections: Set[GatewayConnection] = set()
        self._event_broadcaster = get_event_broadcaster()
        self._method_registry = get_method_registry()
```
