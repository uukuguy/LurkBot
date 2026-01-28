# Moltbot In-Depth Analysis Report

> **Note**: Code examples in this document are from the original TypeScript project moltbot, used to illustrate design concepts and implementation approaches. Python rewrites should use corresponding Python best practices.

## Table of Contents

- [Project Overview](#project-overview)
- [Core Architecture](#core-architecture)
- [Module Deep Dive](#module-deep-dive)
- [Technical Implementation Details](#technical-implementation-details)
- [Best Practices](#best-practices)
- [Python Rewrite Recommendations](#python-rewrite-recommendations)

---

## Project Overview

### Basic Information

- **Project Name**: moltbot (formerly clawdbot)
- **Version**: 2026.1.27-beta.1
- **Language**: TypeScript (Node.js 22+)
- **License**: MIT
- **Positioning**: Personal AI assistant platform with multi-channel messaging support

### Core Features

1. **Multi-Channel Support**: Telegram, Discord, Slack, WhatsApp, Signal, iMessage, Google Chat, etc.
2. **AI Model Integration**: Claude, GPT, Gemini, Ollama, etc.
3. **Tool System**: bash, browser, canvas, file operations, etc.
4. **Sandbox Isolation**: Docker container isolation for secure tool execution
5. **Skills System**: Extensible skill plugins
6. **WebSocket Gateway**: Unified control plane

---

## Core Architecture

### 1. Architectural Philosophy

Moltbot adopts a **Gateway-Centric Architecture**, with core principles:

- **Single Control Plane**: All messages route through WebSocket Gateway
- **Protocol Standardization**: Unified internal message format
- **Module Decoupling**: Channel, Agent, Tool are independent
- **Event-Driven**: Publish-subscribe pattern for async events

### 2. System Architecture Diagram

```
┌────────────────────────────────────────────────────────────────┐
│                        Moltbot System                           │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────── External Layer ──────────────┐               │
│  │                                              │               │
│  │  Telegram  Discord  Slack  WhatsApp         │               │
│  │  Signal    iMessage GoogleChat  ...         │               │
│  │                                              │               │
│  └──────────────────┬───────────────────────────┘               │
│                     │                                           │
│  ┌──────────────────▼──────────────────────┐                   │
│  │          Channel Adapters               │                   │
│  │  - Message format conversion            │                   │
│  │  - Permission control (allowlist)       │                   │
│  │  - Typing indicators                    │                   │
│  └──────────────────┬──────────────────────┘                   │
│                     │                                           │
│  ┌──────────────────▼──────────────────────┐                   │
│  │      WebSocket Gateway (Control Hub)    │                   │
│  │  - Connection management                │                   │
│  │  - Message routing                      │                   │
│  │  - RPC framework                        │                   │
│  │  - Event broadcasting                   │                   │
│  │  - HTTP endpoints (webhooks, canvas)    │                   │
│  └──────────────────┬──────────────────────┘                   │
│                     │                                           │
│  ┌──────────────────▼──────────────────────┐                   │
│  │         Agent Runtime                   │                   │
│  │  ┌────────────────────────────────┐     │                   │
│  │  │    Session Management          │     │                   │
│  │  │  - main session (DM)           │     │                   │
│  │  │  - group session (isolated)    │     │                   │
│  │  │  - topic session (forum)       │     │                   │
│  │  └────────────────────────────────┘     │                   │
│  │  ┌────────────────────────────────┐     │                   │
│  │  │    Model Adapters              │     │                   │
│  │  │  - Claude (Anthropic)          │     │                   │
│  │  │  - GPT (OpenAI)                │     │                   │
│  │  │  - Gemini (Google)             │     │                   │
│  │  │  - Ollama (local)              │     │                   │
│  │  └────────────────────────────────┘     │                   │
│  │  ┌────────────────────────────────┐     │                   │
│  │  │    Tool Execution              │     │                   │
│  │  │  - Built-in tools              │     │                   │
│  │  │  - Sandbox mode                │     │                   │
│  │  │  - Approval workflow           │     │                   │
│  │  └────────────────────────────────┘     │                   │
│  └─────────────────────────────────────────┘                   │
│                                                                 │
│  ┌───────────── Extension Layer ─────────────┐                 │
│  │  - Skills (1password, github)             │                 │
│  │  - Plugins (hooks, extensions)            │                 │
│  │  - Memory/RAG                             │                 │
│  └───────────────────────────────────────────┘                 │
│                                                                 │
└────────────────────────────────────────────────────────────────┘
```

### 3. Data Flow Example

#### User Message Processing Flow

```
1. User sends "Write a Python script to read CSV" on Telegram
   ↓
2. Telegram Bot API receives message
   ↓
3. TelegramChannel adapter:
   - Check allowlist (is this user allowed?)
   - Convert to internal ChannelMessage format
   ↓
4. Gateway receives and routes:
   - Determine session_id (based on chat_id + user_id)
   - Send message to Agent Runtime
   ↓
5. Agent Runtime:
   - Get or create Session
   - Load conversation history
   - Call AI model (Claude)
   ↓
6. Claude API:
   - Return response with tool calls (read_file, write_file)
   ↓
7. Tool Execution:
   - Check tool policy (is this allowed?)
   - Execute in sandbox (if group session)
   - Return tool execution results
   ↓
8. Agent Runtime:
   - Send tool results back to Claude
   - Claude generates final response
   ↓
9. Gateway routes response:
   - Stream to TelegramChannel
   ↓
10. TelegramChannel:
    - Format message (Markdown support)
    - Send via Telegram Bot API
    ↓
11. User receives response
```

---

## Module Deep Dive

### 1. Gateway Module

#### File Structure

- `src/gateway/server.impl.ts` - Main server implementation
- `src/gateway/protocol/` - Protocol definitions
- `src/gateway/server-methods/` - RPC method implementations
- `src/gateway/server-channels.ts` - Channel lifecycle management
- `src/gateway/server-cron.ts` - Scheduled tasks
- `src/gateway/server-browser.ts` - Browser control
- `src/gateway/discovery.ts` - mDNS discovery service

#### Core Features

**WebSocket Protocol**: Defines unified message format including connection handshake, RPC request/response, event push, etc.

**RPC Framework**: Supports sync and async (streaming) method calls with TypeBox message validation.

**Connection Management**: Maintains active connections, supports message routing and broadcasting.

#### Key Design Patterns

1. **RPC Pattern**: Request/response model
2. **Event Broadcasting**: Server-initiated event push
3. **Idempotency**: Request IDs ensure operation idempotency
4. **Schema Validation**: Message format validation

---

### 2. Agent Module

#### File Structure

- `src/agents/agent.impl.ts` - Agent core implementation
- `src/agents/session/` - Session management
- `src/agents/tools/` - Tool system
- `src/agents/skills/` - Skills system
- `src/agents/auth-profiles/` - API Key management
- `src/agents/memory/` - RAG integration

#### Core Features

**Session Management**

Session types:
- `main`: User direct conversation, trusted
- `group`: Group chat, sandboxed
- `dm`: Other user DMs, partially trusted
- `topic`: Forum topics, sandboxed

Each session contains:
- Conversation history
- Tool policy (allowed/denied tools)
- Workspace path
- Metadata

**Tool System**

Built-in tools:
- `bash` - Execute shell commands
- `read`/`write`/`edit` - File operations
- `browser` - Browser automation (Playwright)
- `canvas` - Visual workspace
- `nodes` - Device control (camera, screen, location)
- `sessions_*` - Multi-agent coordination
- `message` - Send messages

Tool policies: Control tool permissions based on session type

**Sandbox Isolation**

Uses Docker containers to isolate untrusted sessions:
- Read-only filesystem
- No network access
- Memory and CPU limits
- Workspace mount

**Model Adapters**

Supports multiple AI models:
- Claude (Anthropic)
- GPT (OpenAI)
- Gemini (Google)
- Ollama (local)

Unified interface with streaming support.

---

### 3. Channel Module

#### Channel Abstraction

All Channel implementations share a unified interface:
- `start()` / `stop()` - Lifecycle management
- `send()` - Send messages
- `sendTyping()` - Send typing indicator
- Event emission - Trigger events when receiving messages

#### Main Channel Implementations

**Telegram**: Uses grammY framework, supports Bot API

**Discord**: Uses discord.js, requires @bot mention to respond

**Slack**: Uses Bolt SDK, supports Socket Mode

**WhatsApp**: Uses Baileys library, QR code pairing

**Signal**: Uses signal-cli command-line tool

**iMessage**: macOS only, uses imsg library

#### Key Features

- **Allowlist Control**: Whitelist users/groups
- **Mention Gating**: Requires mention to respond
- **Typing Indicators**: Send typing status
- **Format Conversion**: Unified internal message format

---

### 4. Configuration System

#### Config File Location

`~/.clawdbot/moltbot.json` (JSON5 format)

#### Main Configuration Items

**Gateway Config**:
- Listen address and port
- Authentication mode (token/password/none)
- mDNS discovery

**Agent Config**:
- Default model
- Workspace path
- Sandbox policy

**Channel Config**:
- Tokens and keys for each channel
- Allowlist/blocklist
- Mention gating

**Auth Profiles**:
- AI provider API Keys
- Environment variable substitution support

#### Environment Variable Substitution

Config can use `${VAR_NAME}` to reference environment variables, avoiding plaintext secrets.

---

### 5. CLI System

#### Main Commands

- `gateway start` - Start gateway server
- `agent chat` - Interactive chat
- `message send` - Send messages
- `channels list` - List channels
- `config show` - Show configuration
- `onboard` - Setup wizard
- `doctor` - Health checks
- `skills list` - List skills

#### User-Friendly Features

- Interactive wizards (using @clack/prompts)
- Colored output and progress indicators
- Auto-completion and help docs
- Error hints and fix suggestions

---

## Technical Implementation Details

### 1. Protocol Layer Design

Uses TypeBox to define message formats:
- Faster validation performance
- Generates standard JSON Schema
- Smaller bundle size

### 2. Streaming Response

Uses async generators for streaming:
- WebSocket bidirectional communication
- Low latency
- Binary data support

### 3. Session Persistence

Uses JSONL (JSON Lines) format for session storage:
- One JSON object per line
- Easy to append
- Easy to restore

Storage location: `~/.clawdbot/sessions/{session_id}.jsonl`

### 4. Docker Sandbox

Creates isolated containers:
- Ubuntu base image
- Read-only filesystem
- No network access
- Resource limits (memory, CPU)
- Workspace mount

### 5. Skills System

Skill file format: Markdown + YAML frontmatter

Structure:
- Frontmatter: Metadata (name, description, dependencies)
- Content: Skill documentation and usage examples

Loading locations:
- Bundled skills: Packaged with project
- Workspace skills: `~/.clawdbot/skills/`

---

## Best Practices

### 1. Security Practices

#### API Key Management

- ✅ Use environment variables
- ✅ Use system keychain
- ❌ Avoid plaintext storage

#### Sandbox Isolation

Set policies by session type:
- `main`: No sandbox (trusted)
- `group`/`topic`: Always sandbox
- `dm`: Use sandbox (partially trusted)

#### Tool Policies

Restrict tools by session type:
- `main`: Allow all tools
- `group`: Only read-only operations
- `dm`: Minimal permissions

### 2. Performance Optimization

#### Connection Pooling

- Model client pooling
- Docker container reuse
- Reduce initialization overhead

#### Lazy Loading

- Lazy load Channels
- Lazy load AI clients
- Create resources on-demand

#### Caching Strategy

- Session cache (LRU)
- Config cache
- Async disk writes

### 3. Error Handling

#### Layered Error Handling

Define error types:
- `ConfigError`
- `ChannelError`
- `ToolError`
- `AgentError`

Unified error format with error codes and details.

#### Retry Mechanism

API calls use exponential backoff retry:
- Max retry count
- Delay calculation (exponential/linear)
- Error logging

### 4. Testing Strategy

#### Unit Tests

- Tool functionality tests
- Protocol parsing tests
- Config validation tests

#### Integration Tests

- Gateway E2E tests
- Channel integration tests
- Docker sandbox tests

Use mocks for external services.

---

## Python Rewrite Recommendations

### 1. Technology Stack Selection

| Component | TypeScript | Python Recommended |
|-----------|------------|-------------------|
| Web Framework | Express | **FastAPI** |
| Validation | TypeBox/Zod | **Pydantic** |
| CLI | Commander | **Typer** |
| Logging | Winston | **Loguru** |
| Testing | Vitest | **pytest** |
| AI SDK | TS SDK | **Official Python SDKs** |
| Async | Node.js | **asyncio** |
| Docker | dockerode | **docker-py** |

### 2. Module Mapping

```
TypeScript           →  Python
src/gateway/         →  lurkbot/gateway/
src/agents/          →  lurkbot/agents/
src/channels/        →  lurkbot/channels/
src/telegram/        →  lurkbot/channels/telegram/
src/config/          →  lurkbot/config/
src/cli/             →  lurkbot/cli/
```

### 3. Key Differences Handling

#### WebSocket

FastAPI has native WebSocket support using decorators for endpoints.

#### Async Streaming

Python async generator syntax is similar, using `async def` and `yield`.

#### Docker Operations

Use docker-py official client.

#### Telegram Bot

Use python-telegram-bot library with similar API.

### 4. Project Structure

```
lurkbot/
├── pyproject.toml
├── Makefile
├── src/lurkbot/
│   ├── gateway/
│   ├── agents/
│   ├── channels/
│   ├── config/
│   ├── cli/
│   └── utils/
├── tests/
└── docs/
```

### 5. Implementation Priorities

**Phase 1: Core Features**
- Config system
- Gateway server
- Agent Runtime (Claude)
- Telegram Channel
- Basic CLI

**Phase 2: Tool System**
- Tool registry
- Bash/File tools
- Browser tool

**Phase 3: Advanced Features**
- Sandbox isolation
- Session persistence
- More channels
- Skills system

**Phase 4: Production Ready**
- Error handling
- Logging/monitoring
- Test coverage
- Documentation

---

## Summary

### Core Advantages

1. **Clear Architecture**: Gateway-Centric design
2. **Secure and Reliable**: Sandbox isolation
3. **Highly Extensible**: Plugin-based design
4. **User-Friendly**: CLI wizards

### Key Design Patterns

1. **Gateway Pattern**: Unified control plane
2. **Adapter Pattern**: Channel/Model adaptation
3. **Strategy Pattern**: Tool strategies
4. **Plugin Pattern**: Skills and extensions

### Python Rewrite Essentials

1. Use FastAPI + Pydantic
2. Use asyncio
3. Use official Python SDKs
4. Maintain original architecture
5. Simplify configuration management

---

**Document Version**: 1.0
**Updated**: 2026-01-28
**Based on**: moltbot v2026.1.27-beta.1
