# Built-in Tools Reference

LurkBot includes 22 native tools organized into P0/P1/P2 priority levels. This documentation reflects the actual code implementation with detailed parameter specifications and usage notes.

> Source code: `src/lurkbot/tools/builtin/__init__.py`

---

## P0 Level - Core Tools (6 tools)

P0 tools are the foundational toolset, enabled by default in all configurations.

### exec (Command Execution)

Execute shell commands. This is one of the most commonly used tools.

**Alias**: `bash`

**Parameters** (`ExecParams`):

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `command` | string | Yes | Command to execute |
| `timeout` | number | No | Timeout in seconds, default 120s |
| `cwd` | string | No | Working directory (defaults to session workspace) |
| `env` | dict | No | Environment variable key-value pairs |

**Returns**: `ToolResult` (contains stdout/stderr/exit_code)

**Security Mechanisms**:
- Configurable `ExecSecurity` policy
- Support for `ExecAsk` confirmation (dangerous commands require user approval)
- Runs in sandbox mode when isolated

```python
# Internal usage example
from lurkbot.tools.builtin import exec_tool, ExecParams
result = await exec_tool(ExecParams(command="ls -la", timeout=30))
```

---

### process (Process Management)

Manage background process startup, monitoring, and termination.

**Parameters** (`ProcessParams`):

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `action` | string | Yes | `start` / `stop` / `list` / `status` |
| `command` | string | Conditional | Required when action=start |
| `session_id` | string | Conditional | Required when action=stop/status |

**Process Sessions**: Each background process is assigned a `ProcessSession` object, manageable via `add_session`, `get_session`, `remove_session`, `kill_session`.

```
Example conversation:
User: Start a background web server
Agent: [process start] python -m http.server 8000
       Process started, session_id: proc_abc123
```

---

### read (File Reading)

Read file contents and return them.

**Parameters** (`ReadParams`):

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `path` | string | Yes | File path (relative or absolute) |
| `encoding` | string | No | Encoding format, default `utf-8` |
| `offset` | number | No | Starting byte offset |
| `limit` | number | No | Maximum bytes to read |

**Security**: The `fs_safe` module ensures paths are within allowed bounds:
- `is_path_within_root()` - Check if path is within workspace
- `resolve_safe_path()` - Resolve and validate path
- `SafeOpenError` - Thrown when path violates rules

---

### write (File Writing)

Create or overwrite files.

**Parameters** (`WriteParams`):

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `path` | string | Yes | File path |
| `content` | string | Yes | Content to write |
| `encoding` | string | No | Encoding format, default `utf-8` |
| `create_dirs` | boolean | No | Auto-create parent directories |

**Behavior**: Overwrites if file exists, creates if it doesn't.

---

### edit (File Editing)

Edit files via search and replace.

**Parameters** (`EditParams`):

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `path` | string | Yes | File path |
| `old_text` | string | Yes | Text to find |
| `new_text` | string | Yes | Replacement text |
| `occurrence` | number | No | Which occurrence, default all |

**Advantage**: More precise than write, modifies only specified positions, reduces accidental overwrite risk.

---

### apply_patch (Patch Application)

Apply unified diff format patches.

**Parameters** (`ApplyPatchParams`):

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `path` | string | Yes | Target file path |
| `patch` | string | Yes | Unified diff format patch content |
| `dry_run` | boolean | No | Simulate only, don't modify |

**Special Rule**: When `exec` is allowed, `apply_patch` is automatically allowed (see policy.py:465)

---

## P1 Level - Session & Automation Tools (12 tools)

### Session Tools (6 tools)

#### sessions_spawn (Create Subagent)

**Parameters** (`SessionsSpawnParams`):

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `task` | string | Yes | Task description |
| `agent_id` | string | No | Specify agent configuration |
| `blocking` | boolean | No | Block and wait for result |

#### sessions_send (Send Message)

**Parameters** (`SessionsSendParams`):

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `session_key` | string | Yes | Target session identifier |
| `message` | string | Yes | Message content |

#### sessions_list / sessions_history / session_status / agents_list

These tools query session and agent status, with simpler parameters.

**Subagent Default Deny**:
Subagent sessions deny session management tools by default (prevents recursive self-orchestration):
```python
DEFAULT_SUBAGENT_TOOL_DENY = [
    "sessions_list", "sessions_history", "sessions_send",
    "sessions_spawn", "session_status", "agents_list", ...
]
```

---

### Memory Tools (2 tools)

#### memory_search (Semantic Search)

**Parameters** (`MemorySearchParams`):

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `query` | string | Yes | Search query |
| `limit` | number | No | Maximum results |
| `threshold` | number | No | Similarity threshold |

**Returns**: `MemorySearchResult` list

#### memory_get (Memory Read)

**Parameters** (`MemoryGetParams`):

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `key` | string | Yes | Memory key name |

---

### Web Tools (2 tools)

#### web_search (Web Search)

**Parameters** (`WebSearchParams`):

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `query` | string | Yes | Search keywords |
| `num_results` | number | No | Result count, default 5 |

**Returns**: `SearchResult` list (contains title, url, snippet)

#### web_fetch (Web Fetch)

**Parameters** (`WebFetchParams`):

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `url` | string | Yes | Target URL |
| `timeout` | number | No | Request timeout (seconds) |
| `extract_text` | boolean | No | Convert to plain text (html_to_markdown) |

---

### message (Message Sending)

Send messages to specified channels.

**Parameters** (`MessageParams`):

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `channel` | string | Yes | Target channel ID |
| `content` | string | Yes | Message content |
| `action` | string | No | `send` / `reply` / `edit` |

**Channel Registration**: Managed via `register_channel()` and `get_channel()`. `CLIChannel` is the built-in terminal channel implementation.

---

### cron (Scheduled Tasks)

Manage scheduled task creation, pausing, resuming, and deletion.

**Parameters** (`CronParams`):

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `action` | string | Yes | `create` / `list` / `pause` / `resume` / `delete` |
| `schedule` | string | Conditional | Cron expression, e.g., `0 9 * * *` |
| `task` | string | Conditional | Task content |
| `job_id` | string | Conditional | Required when operating existing tasks |

**Data Models**:
- `CronJob` - Task definition
- `CronJobState` - Task state
- `CronSchedule` - Time schedule
- `CronRunResult` - Execution result

---

### gateway (Gateway Communication)

Communicate with Gateway RPC interface.

**Parameters** (`GatewayParams`):

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `method` | string | Yes | RPC method name |
| `params` | dict | No | Method parameters |

**Helper Functions**:
- `configure_gateway()` - Configure connection
- `call_gateway()` - Send request
- `get_gateway()` - Get current connection

---

## P2 Level - Media & Device Tools (4 tools)

### image (Image Processing)

Image understanding and generation.

**Parameters** (`ImageParams`):

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `action` | string | Yes | `analyze` / `generate` / `edit` |
| `path` | string | Conditional | Image file path |
| `prompt` | string | Conditional | Generation/edit instructions |

---

### tts (Text-to-Speech)

Synthesize text to speech.

**Parameters** (`TTSParams`):

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `text` | string | Yes | Input text |
| `voice` | string | No | Voice character (`TTSVoice` enum) |
| `output` | string | No | Output file path |

**Configuration**: Set `TTSConfig` via `configure_tts()`

---

### nodes (Node Discovery)

Discover and manage other nodes in the network.

**Parameters** (`NodesParams`):

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `action` | string | Yes | `discover` / `list` / `exec` |
| `node_id` | string | Conditional | Required for remote execution |
| `command` | string | Conditional | Command to execute |

**Data Models**: `NodeInfo`, `NodeRegistry`, `NodeExecResult`

---

### browser (Browser Automation)

> **Status**: Pending implementation, depends on Playwright

Planned features:
- Page navigation
- Element click/input
- Screenshots
- PDF export

---

## Tool Result Format

All tools return a unified `ToolResult` structure:

```python
@dataclass
class ToolResult:
    success: bool
    content: list[ToolResultContent]
    error: str | None = None
```

**Result Content Types** (`ToolResultContentType`):
- `text` - Plain text
- `json` - JSON object
- `image` - Image (base64 or path)

**Helper Functions**:
- `text_result(text)` - Create text result
- `json_result(data)` - Create JSON result
- `image_result(data)` - Create image result
- `error_result(message)` - Create error result

---

## See Also

- [Tool Policies](tool-policies.md) - Nine-layer policy system explained
- [Sandbox Mode](sandbox.md) - Docker isolation mechanism
- [Developer Guide: Custom Tools](../../developer/extending/custom-tools.md) - Creating new tools
