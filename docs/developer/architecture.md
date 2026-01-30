# Architecture

This document describes LurkBot's internal architecture and design decisions, based on the actual code implementation.

## System Overview

LurkBot is built on a **PydanticAI Framework + Gateway-Centric Architecture**. The system uses PydanticAI as the core agent framework, with FastAPI providing the WebSocket gateway server.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           LurkBot System                                 │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                    Gateway (FastAPI + WebSocket)                    │ │
│  │                        ws://127.0.0.1:18789                         │ │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ │ │
│  │  │WebSocket │ │  RPC     │ │ Session  │ │  Event   │ │Connection│ │ │
│  │  │ Server   │ │ Methods  │ │ Manager  │ │Broadcast │ │ Handler  │ │ │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘ │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│         ↑              ↑              ↑              ↑                   │
│         │              │              │              │                   │
│  ┌──────┴──────┐ ┌─────┴─────┐ ┌─────┴─────┐ ┌─────┴─────┐             │
│  │   Channel   │ │ PydanticAI│ │  22 Tools │ │ Bootstrap │             │
│  │   Adapters  │ │   Agent   │ │ + Policy  │ │  System   │             │
│  └─────────────┘ └───────────┘ └───────────┘ └───────────┘             │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## Technology Stack

| Component | Technology | Source Location |
|-----------|------------|-----------------|
| Agent Framework | **PydanticAI** | `src/lurkbot/agents/runtime.py` |
| Web Framework | **FastAPI** | `src/lurkbot/gateway/app.py` |
| CLI | **Typer** | `src/lurkbot/cli/` |
| Data Validation | **Pydantic** | Throughout |
| Logging | **Loguru** | `src/lurkbot/logging.py` |
| Package Manager | **uv** | `pyproject.toml` |

## Core Components

### Gateway Server

The Gateway is the central communication hub, built on FastAPI with WebSocket support.

> Source: `src/lurkbot/gateway/server.py`

**Key Classes:**

```python
# src/lurkbot/gateway/server.py:48
class GatewayServer:
    """Gateway WebSocket server."""

    VERSION = "0.1.0"
    PROTOCOL_VERSION = 1

    def __init__(self):
        self._connections: Set[GatewayConnection] = set()
        self._event_broadcaster = get_event_broadcaster()
        self._method_registry = get_method_registry()

    async def handle_connection(self, websocket: WebSocket) -> None:
        """Handle WebSocket connection."""

    async def _handshake(self, connection: GatewayConnection) -> None:
        """Process handshake."""

    async def _message_loop(self, connection: GatewayConnection) -> None:
        """Main message loop."""
```

**Connection Management:**

```python
# src/lurkbot/gateway/server.py:29
class GatewayConnection:
    """Single WebSocket connection."""

    def __init__(self, websocket: WebSocket, conn_id: str):
        self.websocket = websocket
        self.conn_id = conn_id
        self.client_info = None
        self.authenticated = False

    async def send_json(self, data: dict) -> None:
        """Send JSON message."""

    async def receive_json(self) -> dict:
        """Receive JSON message."""
```

**Protocol Frames** (from `src/lurkbot/gateway/protocol/frames.py`):
- `HelloOk` - Handshake response
- `ServerInfo` - Server metadata
- `RequestFrame` / `ResponseFrame` - RPC communication
- `EventFrame` - Event notifications

### Agent Runtime (PydanticAI)

The Agent Runtime uses **PydanticAI** framework, not a custom implementation.

> Source: `src/lurkbot/agents/runtime.py`

**Agent Type Definition:**

```python
# src/lurkbot/agents/runtime.py:95
Agent[AgentDependencies, str | DeferredToolRequests]
```

**Dependencies Injection:**

```python
# src/lurkbot/agents/runtime.py:32
class AgentDependencies(BaseModel):
    """Dependencies injected into the agent at runtime."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    context: AgentContext
    message_history: list[dict[str, Any]] = []
```

**Model Mapping:**

```python
# src/lurkbot/agents/runtime.py:46-63
MODEL_MAPPING = {
    "anthropic": {
        "claude-sonnet-4-20250514": "anthropic:claude-sonnet-4-20250514",
        "claude-opus-4-5-20251101": "anthropic:claude-opus-4-5-20251101",
        "claude-3-5-sonnet-20241022": "anthropic:claude-3-5-sonnet-20241022",
    },
    "openai": {
        "gpt-4o": "openai:gpt-4o",
        "gpt-4o-mini": "openai:gpt-4o-mini",
    },
    "google": {
        "gemini-2.0-flash": "google-gla:gemini-2.0-flash",
        "gemini-1.5-pro": "google-gla:gemini-1.5-pro",
    },
}
```

**Agent Creation:**

```python
# src/lurkbot/agents/runtime.py:91
def create_agent(
    model: str,
    system_prompt: str,
    deps_type: type = AgentDependencies,
) -> Agent[AgentDependencies, str | DeferredToolRequests]:
    """Create a PydanticAI Agent instance."""
```

### Bootstrap File System

LurkBot uses 8 Markdown files to define agent personality and context.

> Source: `src/lurkbot/agents/bootstrap.py`

**File Types:**

```python
# src/lurkbot/agents/bootstrap.py:27-35
AGENTS_FILENAME = "AGENTS.md"
SOUL_FILENAME = "SOUL.md"
TOOLS_FILENAME = "TOOLS.md"
IDENTITY_FILENAME = "IDENTITY.md"
USER_FILENAME = "USER.md"
HEARTBEAT_FILENAME = "HEARTBEAT.md"
BOOTSTRAP_FILENAME = "BOOTSTRAP.md"
MEMORY_FILENAME = "MEMORY.md"
```

**Subagent Allowlist:**

```python
# src/lurkbot/agents/bootstrap.py:51
SUBAGENT_BOOTSTRAP_ALLOWLIST: set[str] = {AGENTS_FILENAME, TOOLS_FILENAME}
```

**Bootstrap File Structure:**

```python
# src/lurkbot/agents/bootstrap.py:62
@dataclass
class BootstrapFile:
    """A workspace bootstrap file."""

    name: BootstrapFileName
    path: str
    content: str | None = None
    missing: bool = False
```

### Tool System (22 Native Tools)

LurkBot provides 22 built-in tools organized by priority.

> Source: `src/lurkbot/tools/builtin/__init__.py`

**Tool Categories:**

| Priority | Tools | Module |
|----------|-------|--------|
| P0 (Core) | exec, process, read, write, edit, apply_patch | `exec_tool.py`, `fs_tools.py` |
| P1 (Session) | sessions_spawn, sessions_send, sessions_list, sessions_history, session_status, agents_list | `session_tools.py` |
| P1 (Memory) | memory_search, memory_get | `memory_tools.py` |
| P1 (Web) | web_search, web_fetch | `web_tools.py` |
| P1 (Automation) | message, cron, gateway | `message_tool.py`, `cron_tool.py`, `gateway_tool.py` |
| P2 (Media) | image, tts, nodes, browser | `image_tool.py`, `tts_tool.py`, `nodes_tool.py` |

**Tool Result Structure:**

```python
# src/lurkbot/tools/builtin/common.py
@dataclass
class ToolResult:
    success: bool
    content: list[ToolResultContent]
    error: str | None = None

class ToolResultContentType(str, Enum):
    TEXT = "text"
    JSON = "json"
    IMAGE = "image"
```

### Nine-Layer Policy System

Tool access is controlled by a sophisticated nine-layer filtering system.

> Source: `src/lurkbot/tools/policy.py`

**Policy Layers:**

```python
# src/lurkbot/tools/policy.py:836-867
@dataclass
class ToolFilterContext:
    """Context for nine-layer tool filtering."""

    # Layer 1: Profile policy
    profile: str | None = None
    profile_also_allow: list[str] | None = None

    # Layer 2: Provider profile policy
    provider_profile: str | None = None
    provider_profile_also_allow: list[str] | None = None

    # Layer 3: Global allow/deny
    global_policy: ToolPolicy | None = None

    # Layer 4: Global provider policy
    global_provider_policy: ToolPolicy | None = None

    # Layer 5: Agent policy
    agent_policy: ToolPolicy | None = None

    # Layer 6: Agent provider policy
    agent_provider_policy: ToolPolicy | None = None

    # Layer 7: Group/channel policy
    group_policy: ToolPolicy | None = None

    # Layer 8: Sandbox policy
    sandbox_policy: ToolPolicy | None = None

    # Layer 9: Subagent policy
    subagent_policy: ToolPolicy | None = None
```

**Profile Types:**

```python
# src/lurkbot/tools/policy.py:33-42
class ToolProfileId(str, Enum):
    MINIMAL = "minimal"   # session_status only
    CODING = "coding"     # fs, runtime, sessions, memory, image
    MESSAGING = "messaging"  # messaging, session queries
    FULL = "full"         # all tools
```

**Tool Groups:**

```python
# src/lurkbot/tools/policy.py:61-126
TOOL_GROUPS = {
    "group:memory": ["memory_search", "memory_get"],
    "group:web": ["web_search", "web_fetch"],
    "group:fs": ["read", "write", "edit", "apply_patch"],
    "group:runtime": ["exec", "process"],
    "group:sessions": ["sessions_list", "sessions_history", ...],
    "group:ui": ["browser", "canvas"],
    "group:automation": ["cron", "gateway"],
    "group:messaging": ["message"],
    "group:nodes": ["nodes"],
    "group:lurkbot": [/* all native tools */],
}
```

## Data Flow

### Message Processing Pipeline

```
1. External Platform (Telegram, Discord, Slack, CLI)
   │
   ▼
2. Channel Adapter
   │ - Receives platform-native message
   │ - Converts to ChannelMessage object
   │ - Applies allowlist filtering
   │
   ▼
3. Gateway WebSocket Server
   │ - Accepts connection (ws://127.0.0.1:18789)
   │ - Processes RPC request
   │ - Routes to appropriate method handler
   │
   ▼
4. Session Manager
   │ - Identifies or creates session
   │ - Loads session context
   │ - Determines session type (main/group/dm/topic/subagent)
   │
   ▼
5. Bootstrap Processor
   │ - Loads workspace bootstrap files
   │ - Filters by session type (subagent allowlist)
   │ - Builds system prompt
   │
   ▼
6. PydanticAI Agent
   │ - Injects AgentDependencies
   │ - Calls AI model (Claude/GPT/Gemini)
   │ - Handles streaming response
   │
   ▼
7. Tool Executor (if tool call requested)
   │ - Applies nine-layer policy filtering
   │ - Selects execution environment (sandbox/host)
   │ - Executes tool and returns result
   │
   ▼
8. Agent continues reasoning with tool result
   │
   ▼
9. Final response generated
   │
   ▼
10. Gateway routes to Channel Adapter
    │
    ▼
11. User receives formatted response
```

### Tool Execution Flow

```
Tool Request from AI
    │
    ▼
┌─────────────────────┐
│ Nine-Layer Policy   │
│ Filter              │
│ (ToolFilterContext) │
└──────────┬──────────┘
           │
    ┌──────┴──────┐
    │             │
    ▼             ▼
 Allowed       Denied
    │             │
    ▼             ▼
┌─────────┐   Return
│ Sandbox │   Error
│ Check   │
└────┬────┘
     │
  ┌──┴──┐
  │     │
  ▼     ▼
Host  Docker
Exec  Container
  │     │
  └──┬──┘
     │
     ▼
 ToolResult
     │
     ▼
 Return to Agent
```

## Session Types

| Type | Trust Level | Sandbox | Bootstrap Files | Use Case |
|------|-------------|---------|-----------------|----------|
| `main` | Full | No | All 8 files | Owner's direct messages |
| `dm` | Partial | Optional | All 8 files | DMs from other users |
| `group` | Low | Yes | All 8 files | Group chat conversations |
| `topic` | Low | Yes | All 8 files | Forum topic threads |
| `subagent` | Isolated | Yes | AGENTS.md, TOOLS.md only | Spawned sub-agents |

## Directory Structure

```
src/lurkbot/
├── agents/
│   ├── __init__.py
│   ├── runtime.py      # PydanticAI Agent creation
│   ├── bootstrap.py    # Bootstrap file system
│   ├── types.py        # AgentContext, etc.
│   └── api.py          # Agent API endpoints
├── gateway/
│   ├── __init__.py
│   ├── server.py       # GatewayServer, GatewayConnection
│   ├── app.py          # FastAPI application
│   ├── events.py       # Event broadcaster
│   ├── methods.py      # RPC method registry
│   └── protocol/
│       └── frames.py   # Protocol frame types
├── channels/
│   ├── __init__.py
│   ├── base.py         # ChannelAdapter interface
│   ├── telegram.py     # Telegram adapter
│   ├── discord.py      # Discord adapter
│   └── slack.py        # Slack adapter
├── tools/
│   ├── __init__.py
│   ├── policy.py       # Nine-layer policy system
│   └── builtin/
│       ├── __init__.py # Tool exports
│       ├── common.py   # ToolResult, helpers
│       ├── exec_tool.py
│       ├── fs_tools.py
│       ├── memory_tools.py
│       ├── web_tools.py
│       ├── session_tools.py
│       ├── message_tool.py
│       ├── cron_tool.py
│       ├── gateway_tool.py
│       ├── image_tool.py
│       ├── tts_tool.py
│       └── nodes_tool.py
├── cli/
│   ├── __init__.py
│   ├── main.py         # Typer app
│   └── commands/       # CLI subcommands
├── config/
│   └── settings.py     # Configuration management
└── logging.py          # Loguru setup
```

## Design Decisions

### Why PydanticAI?

- **Type Safety**: Full Pydantic integration for validation
- **Async Native**: Built for async/await patterns
- **Tool System**: Clean tool definition and execution
- **Streaming**: Native support for response streaming
- **Multi-Model**: Easy provider switching

### Why FastAPI + WebSocket?

- **Performance**: ASGI-native async server
- **Real-time**: Bidirectional WebSocket communication
- **Standards**: OpenAPI, JSON Schema support
- **Ecosystem**: Rich middleware and tooling

### Why Nine-Layer Policy?

- **Granularity**: Fine-grained control at multiple levels
- **Flexibility**: Different policies for different contexts
- **Security**: Defense in depth approach
- **Inheritance**: Policies compose naturally

## Performance Considerations

### Potential Bottlenecks

1. **AI API Calls**: Mitigate with streaming, connection pooling
2. **Tool Execution**: Mitigate with timeouts, parallel execution
3. **Session Storage**: Mitigate with compaction, lazy loading
4. **Bootstrap Loading**: Mitigate with caching, truncation

### Optimization Strategies

- Connection pooling for AI providers (via PydanticAI)
- In-memory session caching
- Bootstrap content truncation (HEAD_RATIO=0.7, TAIL_RATIO=0.2)
- Docker container reuse for sandbox execution

---

## See Also

- [Contributing](contributing.md) - How to contribute
- [Extending](extending/index.md) - Add custom components
- [API Reference](../api/index.md) - Complete API documentation
- [Core Concepts](../getting-started/concepts.md) - User-facing overview
