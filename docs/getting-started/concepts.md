# Core Concepts

Understanding LurkBot's architecture will help you use it effectively.

## Overall Architecture

LurkBot adopts a **PydanticAI Framework + Gateway-Centric Architecture** where all messages flow through a central WebSocket server:

```
┌──────────────────────────────────────────────────────────┐
│              External Messaging Platforms                 │
│  Telegram   Discord   Slack   WhatsApp   Signal   Matrix │
└────────────────────┬─────────────────────────────────────┘
                     │
                ┌────▼─────┐
                │ Gateway  │  ← Central Control Plane (FastAPI + WebSocket)
                │ :18789   │     Port: ws://127.0.0.1:18789
                └────┬─────┘
                     │
        ┌────────────┼────────────┐
        │            │            │
    ┌───▼────┐  ┌───▼─────┐  ┌──▼────┐
    │PydanticAI │ Channel │  │ 22     │
    │ Agent   │  │ Adapters│  │Built-in│
    │ Runtime │  │         │  │ Tools  │
    └─────────┘  └─────────┘  └───────┘
```

## Core Components

### Gateway Server

The Gateway is the communication hub, built on FastAPI:

- **WebSocket Server**: Async ASGI server, default port `ws://127.0.0.1:18789`
- **RPC Method Registry**: Provides sessions.*, tools.*, channels.* RPC interfaces
- **Event Broadcaster**: Pushes system events to connected clients
- **Connection Management**: Handles handshake, authentication, subscriptions

Start Gateway:
```bash
lurkbot gateway start
```

Implementation location: `src/lurkbot/gateway/server.py:48` (GatewayServer class)

### Channels (Platform Adapters)

Channels convert external platform messages to LurkBot's internal format:

| Channel | Platform | Status |
|---------|----------|---------|
| Telegram | python-telegram-bot | ✅ Implemented |
| Discord | discord.py | ✅ Implemented |
| Slack | Slack Bolt Python SDK | ✅ Implemented |
| CLI | Terminal interaction | ✅ Implemented |
| WhatsApp | Planned | ⏳ Pending |

Each channel adapter's responsibilities:
- Receive platform-native message events
- Convert to standard ChannelMessage objects
- Handle platform-specific authentication
- Manage user/group allowlists

### Agent Runtime (Based on PydanticAI)

The Agent runtime is not a custom implementation but built using the **PydanticAI** framework:

```python
# src/lurkbot/agents/runtime.py:95
Agent[AgentDependencies, str | DeferredToolRequests]
```

**AgentDependencies** structure (dependency injection):
- `context: AgentContext` - Contains session_id, workspace_dir, model_id, etc.
- `message_history: list[dict]` - Conversation history

**Supported AI Models** (via PydanticAI):
- **Anthropic**: `claude-sonnet-4-20250514`, `claude-opus-4-5-20251101`
- **OpenAI**: `gpt-4o`, `gpt-4o-mini`
- **Google**: `gemini-2.0-flash`, `gemini-1.5-pro`
- **Ollama**: Local model support

Model format: `{provider}:{model_id}`, e.g., `anthropic:claude-sonnet-4-20250514`

### Sessions

Sessions represent individual conversation contexts, each is an independent namespace:

| Type | Description | Trust Level |
|------|-------------|-------------|
| `main` | Direct messages (DM with owner) | Fully trusted |
| `group` | Group conversations | Partially trusted, sandboxed |
| `dm` | DM from other users | Partially trusted |
| `topic` | Forum topic threads | Low trust, sandboxed |
| `subagent` | Subagent-exclusive sessions | Isolated environment |

Each session carries:
- `session_id` / `session_key` - Unique identifier
- `session_type` - One of the 5 types above
- `workspace_dir` - Working directory (agent's file sandbox root)
- `message_channel` - Associated messaging platform
- Conversation history and context

### Tools (22 Native Tools)

LurkBot includes 22 built-in tools, categorized by priority:

**P0 Level (Core Tools):** 6 tools
- `exec` - Execute shell commands
- `process` - Background process management
- `read` - Read files
- `write` - Write files
- `edit` - Edit files (search/replace)
- `apply_patch` - Apply unified diff patches

**P1 Level (Session/Automation Tools):** 12 tools
- `sessions_spawn`, `sessions_send`, `sessions_list`, `sessions_history` - Session control
- `session_status`, `agents_list` - Status queries
- `memory_search`, `memory_get` - Semantic memory
- `web_search`, `web_fetch` - Web access
- `message` - Send messages
- `cron`, `gateway` - Automation & gateway communication

**P2 Level (Media and Device Tools):** 4 tools
- `image` - Image understanding & generation
- `tts` - Text-to-speech
- `nodes` - Node discovery
- `browser` - Browser automation (depends on Playwright)

Complete tool documentation: `src/lurkbot/tools/builtin/__init__.py:1-46`

### Nine-Layer Tool Policy System

LurkBot employs a layered tool permission control system (`src/lurkbot/tools/policy.py`):

```
Layer 1: Profile Policy        (minimal/coding/messaging/full)
    ↓
Layer 2: Provider Profile      (Provider-level Profile)
    ↓
Layer 3: Global Allow/Deny     (Global tool allow/deny lists)
    ↓
Layer 4: Global Provider       (Provider-level global policy)
    ↓
Layer 5: Agent Policy          (Specific agent tool policy)
    ↓
Layer 6: Agent Provider        (Agent + Provider combination policy)
    ↓
Layer 7: Group/Channel Policy  (Group/channel level restrictions)
    ↓
Layer 8: Sandbox Policy        (Additional restrictions in sandbox)
    ↓
Layer 9: Subagent Policy       (Subagent default deny list)
```

**Tool Groups** (Group Management):
- `group:fs` - File system tools
- `group:runtime` - Execution environment tools
- `group:sessions` - Session management tools
- `group:memory` - Memory tools
- `group:web` - Web tools
- `group:automation` - Automation tools
- `group:lurkbot` - All native tools

### Bootstrap File System

LurkBot uses 8 types of Markdown files to define agent personality and context:

| File | Purpose | Visible to Subagent |
|------|---------|-------------------|
| `SOUL.md` | Core personality & values | ❌ No |
| `IDENTITY.md` | Name, emoji, appearance | ❌ No |
| `USER.md` | User preferences & context | ❌ No |
| `AGENTS.md` | Workspace guidelines & rules | ✅ Yes |
| `TOOLS.md` | Tool descriptions & config | ✅ Yes |
| `HEARTBEAT.md` | Periodic check tasks (main session only) | ❌ No |
| `MEMORY.md` | Long-term memory (main session only) | ❌ No |
| `BOOTSTRAP.md` | First-run setup (deleted after completion) | ❌ No |

File path: Default `~/clawd/`, configurable via `LURKBOT_PROFILE` for multi-environment (e.g., `~/clawd-work`)

Source code location: `src/lurkbot/agents/bootstrap.py:1-15`

### Skills (Extension System)

Skills are a Markdown-based plugin system with metadata defined via frontmatter:

```markdown
# ~/.lurkbot/skills/my-skill.md
---
name: my-custom-skill
description: Custom skill description
requires:
  - some-external-tool
---

# Skill Instructions
Detailed skill instructions go here...
```

Skill loading paths (priority high to low):
1. Workspace level: `.lurkbot/skills/`
2. User level: `~/.lurkbot/skills/`
3. Built-in: Shipped with LurkBot

## Message Processing Flow

```
1️⃣  User sends message on Telegram
    ↓
2️⃣  Telegram Channel Adapter receives message
    ↓
3️⃣  Convert to standard ChannelMessage object
    ↓
4️⃣  Gateway RPC method handles (agents.process_message)
    ↓
5️⃣  Agent Runtime initialization:
    • Load session context
    • Read bootstrap files
    • Apply nine-layer tool policy
    ↓
6️⃣  Call PydanticAI Agent (Model: Claude/GPT/Gemini)
    ↓
7️⃣  AI returns tool call decision
    ↓
8️⃣  Tool Executor:
    • Verify permissions (within policy?)
    • Choose execution environment (sandbox or host)
    • Return result
    ↓
9️⃣  Agent receives tool result, continues reasoning
    ↓
🔟  Generate final response
    ↓
1️⃣1️⃣  Gateway routes to Telegram Channel
    ↓
1️⃣2️⃣  User receives formatted response
```

## Session Lifecycle

```
Session Created → Active → Idle → Compacted → Archived
                ↑             ↓
                └─────────────┘
              (Reactivated on new message)

Timeline:
- Created: First message arrives
- Active: Ongoing conversation (default 24 hours)
- Idle: No activity for 24+ hours
- Compacted: History compression (long conversation integration)
- Archived: Fully saved, no longer updated
```

## Configuration Layering System

LurkBot uses a progressive override configuration loading mechanism:

```
Priority from low to high:

1. Compile-time defaults
   ↓
2. System config (~/.lurkbot/config.json)
   ↓
3. Environment variables (LURKBOT_*)
   ↓
4. Workspace config (.lurkbot/config.json)
   ↓
5. CLI arguments and runtime overrides
```

Example: Setting AI model
```bash
# Default (compile-time)
DEFAULT_MODEL=claude-3-5-sonnet

# System global config
~/.lurkbot/config.json: { "default_model": "claude-opus" }

# Environment variable (higher priority)
export LURKBOT_DEFAULT_MODEL=gpt-4o

# Workspace config (highest, except CLI args)
.lurkbot/config.json: { "default_model": "claude-sonnet-4" }

# Final used: claude-sonnet-4 ✅
```

## Sandbox Isolation Mode

Untrusted sessions (`group`, `topic`, etc.) run in Docker containers, providing:

- **Read-only filesystem**: Tools can only read, not write critical system files
- **Network isolation**: Cannot access host machine network
- **Resource limits**: Memory, CPU, disk quotas
- **Process isolation**: Workspace independent from other sessions
- **Time limits**: Tool execution has timeout protection

## Next Steps

Now that you understand LurkBot's core concepts, continue learning:

- **Quick Start**: [Quick Start Guide](quick-start.md) - Experience the complete flow in 5 minutes
- **CLI Commands**: [Command Reference](../user-guide/cli/index.md) - Master the lurkbot command tool
- **Channel Configuration**: [Platform Integration](../user-guide/channels/index.md) - Connect Telegram/Discord/Slack
- **Tool Security**: [Policy Management](../user-guide/tools/tool-policies.md) - Nine-layer policy explained
- **Architecture Deep Dive**: [System Architecture](../developer/architecture.md) - PydanticAI + Gateway tech stack
