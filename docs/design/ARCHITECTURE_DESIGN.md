# LurkBot Architecture Design Document

## Overview

LurkBot is an enterprise-grade multi-channel AI assistant platform implemented in Python. Version 1.0.0 features industry-first innovations including the **Nine-Layer Tool Policy Engine**, **Bootstrap File System**, and **23-Part System Prompt Generator**.

**Version**: v1.0.0-alpha.1 (Internal Integration Testing)
**Code Size**: ~79,520 lines Python
**Tests**: 625+ (100% passing)
**Modules**: 30+ core modules

## System Architecture

### High-Level Architecture

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

## Core Innovations

### 1. Nine-Layer Tool Policy Engine

The industry-first hierarchical permission control system (1021 lines in `tools/policy.py`):

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

**Key Features**:
- Wildcard pattern matching (`*`, `group:*`)
- Tool group expansion (`group:fs`, `group:runtime`)
- Plugin tool dynamic injection
- Deny-first principle (Deny always wins)
- Special rules: `apply_patch` inherits `exec` permissions

### 2. Bootstrap File System

8 Markdown files define agent personality and behavior:

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

**Key Features**:
- Subagent whitelist mechanism (only `AGENTS.md` and `TOOLS.md`)
- Content truncation strategy (70% head + 20% tail)
- Maximum character limit (20,000 characters)
- Dynamic loading and hot updates

### 3. 23-Part System Prompt Generator

Modular, configurable prompt construction (592 lines in `agents/system_prompt.py`):

```
1. Core Identity          # Core identity
2. Runtime Info           # Runtime information
3. Workspace Context      # Workspace context
4. Bootstrap Files        # Bootstrap file content
5. Tool Descriptions      # Tool descriptions
6. Skills Prompt          # Skills prompt
7. Model Aliases          # Model aliases
8. Reasoning Guidance     # Reasoning guidance
9. Think Level            # Think level
10. Sandbox Info          # Sandbox information
11. Elevated Mode         # Elevated mode
12. Heartbeat Prompt      # Heartbeat prompt
13. Auto-Reply Tokens     # Auto-reply tokens
14. Message Tool Hints    # Message tool hints
15. TTS Hints             # TTS hints
16. Reaction Guidance     # Reaction guidance
17. Markdown Capability   # Markdown capability
18. Owner Numbers         # Owner numbers
19. User Timezone         # User timezone
20. Docs Path             # Docs path
21. Workspace Notes       # Workspace notes
22. Extra System Prompt   # Extra system prompt
23. Reasoning Tag Hint    # Reasoning tag hint
```

### 4. Multi-Dimensional Session Isolation

5 session types with automatic routing:

```python
class SessionType(str, Enum):
    MAIN = "main"           # Main session
    GROUP = "group"         # Group session
    TOPIC = "topic"         # Topic session
    DM = "dm"              # Direct message session
    SUBAGENT = "subagent"  # Subagent session
```

**Session Key Format**:
```
main                                    # Main session
telegram:group:123456                   # Telegram group
discord:topic:789012:thread:345678      # Discord topic
telegram:dm:user123                     # Telegram DM
main:subagent:task-analyzer:abc123      # Subagent session
```

### 5. Adaptive Context Compaction

Intelligent chunking with multi-stage summarization:

```python
# 1. Chunking strategy
chunk_messages_by_max_tokens(
    messages,
    max_tokens=4000,
    chunk_ratio=0.3  # Adaptive adjustment
)

# 2. Multi-stage summarization
summarize_in_stages(
    chunks,
    model="claude-3-haiku",
    merge_threshold=3
)

# 3. Adaptive ratio
compute_adaptive_chunk_ratio(
    total_tokens=50000,
    target_tokens=8000,
    base_ratio=0.3,
    min_ratio=0.1
)
```

## Core Modules

### 1. Gateway (`gateway/`)

**Responsibilities**:
- WebSocket server as system control plane
- Client connection management
- Message routing to Channels and Agents
- RPC interface provider
- Health check endpoints (`/health`, `/ready`, `/live`)

**Key Files**:
- `server.py` - WebSocket server (~500 lines)
- `app.py` - FastAPI application
- `protocol.py` - Protocol definitions

### 2. Agents (`agents/`)

**Responsibilities**:
- AI model integration (Claude, GPT, Gemini, Ollama, etc.)
- Session management
- Context maintenance
- Tool invocation
- Subagent spawning

**Key Files**:
- `runtime.py` - Agent execution
- `bootstrap.py` - Bootstrap file loading (~400 lines)
- `system_prompt.py` - 23-part prompt generator (592 lines)
- `compaction.py` - Context compression (~300 lines)
- `subagent/` - Subagent communication protocol

### 3. Tools (`tools/`)

**Responsibilities**:
- 22 built-in tools
- Nine-layer policy engine
- Tool registration and discovery
- Plugin tool integration

**Key Files**:
- `policy.py` - Nine-layer policy engine (1021 lines)
- `registry.py` - Tool registration
- `builtin/` - 22 built-in tools

**Built-in Tools**:
| Category | Tools |
|----------|-------|
| File System | read, write, edit, apply_patch |
| Runtime | exec, process |
| Sessions | sessions_spawn, sessions_send, sessions_list, sessions_history, session_status, agents_list |
| Memory | memory_search, memory_get |
| Web | web_search, web_fetch |
| Automation | cron, gateway |
| Media | image, canvas |
| System | nodes, tts |
| Browser | browser |

### 4. Sessions (`sessions/`)

**Responsibilities**:
- Session lifecycle management
- JSONL persistence
- Subagent depth limiting (max 3 levels)
- Cross-session messaging

**Key Files**:
- `store.py` - JSONL persistence
- `manager.py` - Session lifecycle (~400 lines)

### 5. Channels (`channels/`)

**Responsibilities**:
- Messaging platform adapters
- Message format conversion
- User permission control

**Supported Channels**:
- Telegram (python-telegram-bot)
- Discord (discord.py)
- Slack (slack-sdk)
- WeWork (企业微信)
- DingTalk (钉钉)
- Feishu (飞书)
- Mock (testing)

### 6. Plugins (`plugins/`)

**Responsibilities**:
- Plugin discovery and loading
- Plugin lifecycle management
- Sandbox execution
- Permission control

**Plugin Types**:
```python
class PluginType(str, Enum):
    CHANNEL = "channel"      # Channel adapter
    TOOL = "tool"           # Tool plugin
    HOOK = "hook"           # Hook extension
    SKILL = "skill"         # Skill plugin
    MIDDLEWARE = "middleware" # Middleware
```

### 7. Tenants (`tenants/`)

**Responsibilities**:
- Multi-tenant management
- Quota enforcement
- Policy management
- Audit logging

**Tenant Tiers**:
```python
class TenantTier(str, Enum):
    FREE = "free"              # Free tier
    BASIC = "basic"            # Basic tier
    PROFESSIONAL = "professional" # Professional tier
    ENTERPRISE = "enterprise"   # Enterprise tier
```

### 8. Infrastructure (`infra/`)

8 infrastructure subsystems:

| Subsystem | Description |
|-----------|-------------|
| system_events | Cross-session event queue |
| system_presence | Node online status |
| tailscale | VPN integration |
| ssh_tunnel | SSH tunneling |
| bonjour | mDNS discovery |
| device_pairing | Device pairing |
| exec_approvals | Execution approval |
| voicewake | Voice wake |

## Data Flow

### Message Processing Flow

```
1. User sends message on Telegram/Discord/Slack/WeWork/DingTalk/Feishu
2. Channel adapter receives and converts to internal format
3. Gateway routes message to corresponding Session
4. Agent Runtime processes message:
   a. Load Bootstrap files
   b. Generate 23-part system prompt
   c. Apply 9-layer tool policy
   d. Invoke AI model
5. AI response returns through Gateway
6. Channel adapter formats and sends response
```

### Subagent Communication Flow

```
1. Spawn (Generation)
   └─> sessions_spawn(agent_id, prompt, label)

2. Announce (Declaration)
   └─> Subagent reports startup to parent

3. Execute (Execution)
   └─> Subagent executes task independently

4. Report (Reporting)
   └─> sessions_send(parent_session, result)

5. Cleanup (Cleanup)
   └─> Automatic or manual session closure
```

## Technology Stack

| Component | Technology | Description |
|-----------|-----------|-------------|
| AI Framework | PydanticAI 1.0+ | Modern Python Agent framework |
| Web Framework | FastAPI + Uvicorn | Async ASGI server |
| Validation | Pydantic 2.10+ | Type safety and data validation |
| CLI | Typer + Rich | Modern command-line interface |
| Logging | Loguru | Structured logging |
| Package Manager | uv | Fast Python package manager |
| Container | Docker + Kubernetes | Production deployment |
| Vector DB | ChromaDB + sqlite-vec | Semantic search |
| Browser | Playwright | Browser automation |

## Extension Points

### Adding New Channels

1. Inherit from `ChannelAdapter` base class
2. Implement `start()`, `stop()`, `send()`, `send_typing()` methods
3. Add corresponding Settings class in configuration
4. Register startup logic in CLI

### Adding New AI Models

1. Configure model in PydanticAI
2. Add model alias in configuration
3. Update provider settings

### Adding New Tools

1. Create tool function with `@tool` decorator
2. Register in tool registry
3. Add to appropriate tool group
4. Update policy if needed

### Adding New Plugins

1. Create plugin directory in `.plugins/`
2. Define `plugin.json` manifest
3. Implement `main.py` with `execute()` function
4. Configure permissions

## Configuration Management

Configuration is managed through environment variables and config files:

- Environment variable prefix: `LURKBOT_`
- Nested delimiter: `__`
- Config file: `~/.lurkbot/config.json`

Example:
```bash
export LURKBOT_GATEWAY__PORT=18789
export LURKBOT_ANTHROPIC_API_KEY=sk-xxx
export LURKBOT_OPENAI_API_KEY=sk-xxx
```

## Production Deployment

### Docker

```bash
# Build and run
docker compose up -d

# Health check
curl http://localhost:18789/health
```

### Kubernetes

```bash
# Apply all manifests
kubectl apply -k k8s/

# Verify
kubectl get pods -n lurkbot
```

### Health Endpoints

| Endpoint | Description |
|----------|-------------|
| `/health` | General health check |
| `/ready` | Readiness probe |
| `/live` | Liveness probe |

## Security

### Sandbox Isolation

- Docker container protection
- Resource limits (memory/CPU)
- Network isolation
- Read-only root filesystem

### Execution Approval

- Command whitelist
- Interactive approval
- Security checks

### Audit Logging

- Complete operation audit
- Compliance reporting
- Anomaly detection
