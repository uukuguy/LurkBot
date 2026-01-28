# LurkBot Architecture Design Document

## Overview

LurkBot is a Python rewrite of moltbot, a multi-channel AI assistant platform. This document describes the core architectural design of the system.

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         LurkBot System                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐       │
│  │   Telegram   │    │   Discord    │    │    Slack     │       │
│  │   Channel    │    │   Channel    │    │   Channel    │       │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘       │
│         │                   │                   │                │
│         └───────────────────┼───────────────────┘                │
│                             │                                    │
│                             ▼                                    │
│                    ┌────────────────┐                            │
│                    │    Gateway     │                            │
│                    │  (WebSocket)   │                            │
│                    └────────┬───────┘                            │
│                             │                                    │
│                             ▼                                    │
│                    ┌────────────────┐                            │
│                    │  Agent Runtime │                            │
│                    │                │                            │
│                    │  ┌──────────┐  │                            │
│                    │  │  Claude  │  │                            │
│                    │  │   GPT    │  │                            │
│                    │  │  Gemini  │  │                            │
│                    │  └──────────┘  │                            │
│                    └────────────────┘                            │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Core Modules

#### 1. Gateway

**Responsibilities**:
- WebSocket server acting as system control plane
- Client connection management
- Message routing to appropriate Channels and Agents
- RPC interface provider

**Key Files**:
- `src/lurkbot/gateway/server.py` - Server implementation
- `src/lurkbot/gateway/protocol.py` - Protocol definitions

#### 2. Agents

**Responsibilities**:
- AI model integration (Claude, GPT, Gemini, etc.)
- Session management
- Context maintenance
- Tool invocation

**Key Files**:
- `src/lurkbot/agents/base.py` - Base class definitions
- `src/lurkbot/agents/runtime.py` - Runtime management

#### 3. Channels

**Responsibilities**:
- Messaging platform adapters (Telegram, Discord, Slack, etc.)
- Message format conversion
- User permission control

**Key Files**:
- `src/lurkbot/channels/base.py` - Base class definitions
- `src/lurkbot/channels/telegram.py` - Telegram adapter

#### 4. CLI

**Responsibilities**:
- Command-line operation entry point
- Configuration management
- Service start/stop control

**Key Files**:
- `src/lurkbot/cli/main.py` - CLI entry point

## Data Flow

### Message Processing Flow

```
1. User sends message on Telegram/Discord/Slack
2. Channel adapter receives and converts to internal format
3. Gateway routes message to corresponding Session
4. Agent Runtime processes message, invokes AI model
5. AI response returns through Gateway
6. Channel adapter formats and sends response
```

### WebSocket Protocol

**Message Types**:
- `connect` - Connection handshake
- `req` - RPC request
- `res` - RPC response
- `event` - Server push event
- `channel_message` - Channel message

## Technology Stack

| Component | Technology | Description |
|-----------|-----------|-------------|
| Web Framework | FastAPI | HTTP/WebSocket server |
| Validation | Pydantic | Schema validation |
| CLI | Typer | Command-line interface |
| Logging | Loguru | Structured logging |
| Package Manager | uv | Fast Python package manager |

## Extension Points

### Adding New Channels

1. Inherit from `Channel` base class
2. Implement `start()`, `stop()`, `send()`, `send_typing()` methods
3. Add corresponding Settings class in configuration
4. Register startup logic in CLI

### Adding New AI Models

1. Inherit from `Agent` base class
2. Implement `chat()` and `stream_chat()` methods
3. Add model recognition logic in `AgentRuntime.get_agent()`

## Configuration Management

Configuration is managed through environment variables and config files:

- Environment variable prefix: `LURKBOT_`
- Nested delimiter: `__`
- Config file: `~/.lurkbot/config.json`

Example:
```bash
export LURKBOT_GATEWAY__PORT=8080
export LURKBOT_ANTHROPIC_API_KEY=sk-xxx
```
