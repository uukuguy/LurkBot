# Tool Policy Management

LurkBot employs a nine-layer policy filtering system that provides fine-grained control over which tools are available in different contexts. This design approach is inherited from MoltBot and enables flexible permission management through layered filtering.

> Source code: `src/lurkbot/tools/policy.py`

## Nine-Layer Policy System

Policies are applied in sequence, with each layer further restricting tool access:

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

**Filtering Logic** (`src/lurkbot/tools/policy.py:876-1020`):
- Each layer's result feeds into the next as input
- Deny lists take priority over Allow lists
- An empty Allow list means "allow all" (unless Denied)

---

## Profile Policies (Layer 1)

LurkBot predefines 4 tool configuration profiles:

### minimal (Minimal Access)

Allows only `session_status` tool.

```bash
LURKBOT_TOOLS__PROFILE=minimal
```

### coding (Development Mode)

```python
# src/lurkbot/tools/policy.py:146
TOOL_PROFILES[ToolProfileId.CODING] = {
    "allow": [
        "group:fs",       # read, write, edit, apply_patch
        "group:runtime",  # exec, process
        "group:sessions", # sessions_*
        "group:memory",   # memory_search, memory_get
        "image"
    ]
}
```

Ideal for code development, includes file operations, command execution, session management.

### messaging (Messaging Mode)

```python
# src/lurkbot/tools/policy.py:149-156
TOOL_PROFILES[ToolProfileId.MESSAGING] = {
    "allow": [
        "group:messaging",    # message tool
        "sessions_list",
        "sessions_history",
        "sessions_send",
        "session_status",
    ]
}
```

Focuses on message sending and session queries, excludes file/command operations.

### full (Unrestricted)

```python
# src/lurkbot/tools/policy.py:158
TOOL_PROFILES[ToolProfileId.FULL] = {}  # Empty = allow all
```

No restrictions, allows all tools.

---

## Tool Groups

For simplified configuration, policies support tool group references:

```python
# src/lurkbot/tools/policy.py:62-126
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
    "group:lurkbot": [/* all LurkBot native tools */],
}
```

**Usage Example**:
```json
{
  "tools": {
    "allow": ["group:fs", "group:web"],
    "deny": ["group:runtime"]
  }
}
```

---

## Policy Matching Logic

### Deny Takes Priority

```python
# src/lurkbot/tools/policy.py:449-468
def matcher(name: str) -> bool:
    # 1. Deny always wins
    if matches_any(normalized, deny):
        return False

    # 2. If no allow list, everything is allowed
    if len(allow) == 0:
        return True

    # 3. Check explicit allow
    if matches_any(normalized, allow):
        return True

    # 4. Special rule: apply_patch follows exec permission
    if normalized == "apply_patch" and matches_any("exec", allow):
        return True

    return False
```

### Pattern Matching

Supports wildcards and regex:

```python
# src/lurkbot/tools/policy.py:364-384
def compile_pattern(pattern: str) -> CompiledPattern:
    if pattern == "*":
        return CompiledPattern(kind="all")
    if "*" not in pattern:
        return CompiledPattern(kind="exact", value=pattern)

    # Convert to regex
    regex_str = f"^{escaped.replace(r'\*', '.*')}$"
    return CompiledPattern(kind="regex", value=re.compile(regex_str))
```

**Examples**:
- `"*"` - Match all tools
- `"exec"` - Exact match
- `"sessions_*"` - Wildcard (matches sessions_list, sessions_send, etc.)
- `"web*"` - Match tools starting with "web"

---

## Subagent Policy (Layer 9)

Subagents have a default deny list to prevent recursive self-orchestration and sensitive tool access:

```python
# src/lurkbot/tools/policy.py:165-182
DEFAULT_SUBAGENT_TOOL_DENY = [
    # Session management - main agent orchestrates
    "sessions_list",
    "sessions_history",
    "sessions_send",
    "sessions_spawn",

    # System admin - dangerous from subagent
    "gateway",
    "agents_list",

    # Interactive setup - not a task
    "whatsapp_login",

    # Status/scheduling - main agent coordinates
    "session_status",
    "cron",

    # Memory - pass relevant info via spawn prompt instead
    "memory_search",
    "memory_get",
]
```

This list can be overridden via configuration:

```python
# src/lurkbot/tools/policy.py:784-808
def resolve_subagent_tool_policy(
    config_deny: list[str] | None = None,
    config_allow: list[str] | None = None,
) -> ToolPolicy:
    deny = list(DEFAULT_SUBAGENT_TOOL_DENY)
    if config_deny:
        deny.extend(config_deny)

    policy: ToolPolicy = {"deny": deny}
    if config_allow:
        policy["allow"] = config_allow

    return policy
```

---

## Tool Name Aliases

For compatibility with different naming conventions:

```python
# src/lurkbot/tools/policy.py:50-53
TOOL_NAME_ALIASES = {
    "bash": "exec",
    "apply-patch": "apply_patch",
}
```

All tool names are normalized to lowercase and aliases applied before matching.

---

## Configuration Examples

### JSON Configuration File

`~/.lurkbot/config.json`:
```json
{
  "tools": {
    "profile": "coding",
    "alsoAllow": ["web_search", "web_fetch"],
    "deny": ["exec"],
    "byProvider": {
      "anthropic": {
        "profile": "full"
      }
    }
  }
}
```

### Environment Variables

```bash
# Global Profile
export LURKBOT_TOOLS__PROFILE=coding

# Global deny list
export LURKBOT_TOOLS__DENY=exec,process

# Global allow list
export LURKBOT_TOOLS__ALLOW=read,write,edit

# Sandbox policy
export LURKBOT_SANDBOX__TOOLS__ALLOW=read,web_search
export LURKBOT_SANDBOX__TOOLS__DENY=exec,write
```

### Agent-Level Policy

`~/clawd/AGENTS.md` (frontmatter):
```yaml
---
agents:
  - id: coding-assistant
    tools:
      profile: coding
      alsoAllow:
        - web_search
        - web_fetch
      deny:
        - exec
---
```

---

## Plugin Group Expansion

If you have plugin tools installed, use `group:plugins` and plugin IDs:

```python
# src/lurkbot/tools/policy.py:305-321
def expand_plugin_groups(
    tools: list[str] | None,
    groups: PluginToolGroups,
) -> list[str] | None:
    expanded = []
    for entry in tools:
        if normalized == "group:plugins":
            expanded.extend(groups.all)
            continue

        plugin_tools = groups.by_plugin.get(normalized)
        if plugin_tools:
            expanded.extend(plugin_tools)
            continue

        expanded.append(normalized)

    return list(dict.fromkeys(expanded))
```

**Example**:
```json
{
  "tools": {
    "allow": ["group:lurkbot", "my-plugin-id"]
  }
}
```

---

## Debugging Policy Conflicts

### Check if Tool is Allowed

```python
from lurkbot.tools.policy import is_tool_allowed_by_policy_name

allowed = is_tool_allowed_by_policy_name("exec", policy)
```

### Trace Policy Layers

Nine-layer filtering is applied in order by `filter_tools_nine_layers()`:

```python
# src/lurkbot/tools/policy.py:876-1020
def filter_tools_nine_layers(
    tools: list[Tool],
    context: ToolFilterContext,
) -> list[Tool]:
    # Filter by each layer in order
    filtered = filter_by_profile(tools)
    filtered = filter_by_provider_profile(filtered)
    filtered = filter_by_global_policy(filtered)
    # ... continue applying remaining layers
    return filtered
```

Enable debug logging:
```bash
export LURKBOT_LOG_LEVEL=DEBUG
```

Log output example:
```
[policy] Applying Layer 1: tools.profile (coding)
[policy] After Layer 1: 18 tools
[policy] Applying Layer 3: tools.allow
[policy] After Layer 3: 12 tools
[policy] Applying Layer 9: subagent policy
[policy] Final: 10 tools
```

---

## Best Practices

### 1. Use Profiles Instead of Manual Lists

❌ Not recommended:
```json
{
  "tools": {
    "allow": ["read", "write", "edit", "exec", "process", ...]
  }
}
```

✅ Recommended:
```json
{
  "tools": {
    "profile": "coding",
    "alsoAllow": ["web_search"]
  }
}
```

### 2. Deny Over Allow

When you need to disable only a few tools:

```json
{
  "tools": {
    "profile": "full",
    "deny": ["exec", "process"]
  }
}
```

### 3. Use Tool Groups to Simplify

```json
{
  "tools": {
    "allow": ["group:fs", "group:web"],
    "deny": ["group:runtime"]
  }
}
```

### 4. Configure Subagent Policies Explicitly

For subagents, provide explicit tool lists instead of relying on the default deny list:

```python
subagent_tools = {
    "allow": ["read", "write", "edit", "web_search"],
    "deny": []  # Explicitly empty to override defaults
}
```

---

## See Also

- [Built-in Tools Reference](builtin-tools.md) - Details of 22 native tools
- [Sandbox Mode](sandbox.md) - Docker isolation execution
- [Bootstrap Files](../../getting-started/concepts.md#bootstrap-file-system) - AGENTS.md and TOOLS.md configuration
