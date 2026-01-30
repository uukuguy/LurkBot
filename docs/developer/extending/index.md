# Extending LurkBot

LurkBot is designed to be extensible. This section covers how to add custom functionality.

## Extension Points

| Extension | Description | Difficulty |
|-----------|-------------|------------|
| [Custom Tools](custom-tools.md) | Create new agent capabilities | Easy |
| [Custom Skills](custom-skills.md) | Build markdown-based plugins | Easy |
| [Custom Channels](custom-channels.md) | Add messaging platforms | Medium |

## Quick Start

### Custom Tool (Easiest)

Create a new tool following the PydanticAI pattern:

```python
# src/lurkbot/tools/builtin/my_tool.py
from pydantic import BaseModel, Field
from .common import ToolResult, text_result, error_result

class MyToolParams(BaseModel):
    """Parameters for my_tool."""
    query: str = Field(..., description="The search query")
    limit: int = Field(default=10, description="Maximum results")

async def my_tool(params: MyToolParams) -> ToolResult:
    """Execute my custom tool.

    Returns:
        ToolResult with text content
    """
    try:
        results = await do_search(params.query, params.limit)
        return text_result(f"Found {len(results)} results")
    except Exception as e:
        return error_result(str(e))
```

### Custom Skill (Easy)

Create a skill with markdown and YAML frontmatter:

```markdown
<!-- .skills/my-skill/SKILL.md -->
---
description: My custom skill for specialized tasks
tags:
  - custom
  - example
userInvocable: true
disableModelInvocation: false
---

# My Skill

You are an expert in [domain]...

## Guidelines

1. Follow best practices
2. Provide clear explanations
```

Skills are auto-discovered from these locations (in priority order):

1. `.skills/` - Workspace skills (highest priority)
2. `.skill-bundles/` - Managed skills
3. Bundled skills - Package defaults

## Tool Result Types

LurkBot tools return structured results (`src/lurkbot/tools/builtin/common.py:41`):

```python
@dataclass
class ToolResult:
    """Standard tool result format."""
    content: list[ToolResultContent] = field(default_factory=list)
    details: Any | None = None

    def to_text(self) -> str:
        """Get the text content of the result."""
        texts = [c.text for c in self.content if c.text]
        return "\n".join(texts)
```

### Result Content Types

```python
class ToolResultContentType(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    DOCUMENT = "document"
```

### Helper Functions

```python
# Create text result
from lurkbot.tools.builtin.common import text_result
result = text_result("Operation completed successfully")

# Create JSON result
from lurkbot.tools.builtin.common import json_result
result = json_result({"status": "ok", "count": 42})

# Create error result
from lurkbot.tools.builtin.common import error_result
result = error_result("Something went wrong", {"code": 500})

# Create image result
from lurkbot.tools.builtin.common import image_result
result = image_result(
    label="Screenshot",
    path="/tmp/screenshot.png",
    base64_data=encoded_data,
    mime_type="image/png"
)
```

## Skill System Architecture

### SkillEntry Structure

Source: `src/lurkbot/skills/workspace.py:37-48`

```python
@dataclass
class SkillEntry:
    """Skill entry."""
    key: str              # Unique identifier
    source: SkillSource   # workspace/managed/bundled/extra
    priority: int         # Lower = higher priority
    file_path: Path       # Skill file path
    frontmatter: SkillFrontmatter  # Parsed metadata
    content: str          # Skill body content
```

### SkillFrontmatter Fields

Source: `src/lurkbot/skills/frontmatter.py:56-68`

```python
class SkillFrontmatter(BaseModel):
    """Skill frontmatter data."""
    # Basic metadata
    description: str      # Required: skill description
    tags: list[str] = []  # Optional: tags for discovery

    # Invocation policy
    user_invocable: bool = True           # User can invoke via /skill-name
    disable_model_invocation: bool = False # Disable auto-invocation

    # MoltBot-specific metadata
    metadata: MoltbotMetadata | None = None
```

### Skill Discovery

Skills are discovered in priority order (`src/lurkbot/skills/workspace.py:56-117`):

| Priority | Source | Directory |
|----------|--------|-----------|
| 1 | workspace | `.skills/` |
| 2 | managed | `.skill-bundles/` |
| 3 | bundled | Package `skills/` |
| 4+ | extra | Additional directories |

File naming conventions:
- `SKILL.md` - Standard skill file (key = parent directory name)
- `{name}.skill.md` - Named skill file (key = filename without `.skill.md`)

## Tool Policy Integration

Custom tools must be added to the policy system for access control.

### Tool Groups

Source: `src/lurkbot/tools/policy.py:62-126`

```python
TOOL_GROUPS = {
    "group:fs": ["read", "write", "edit", "apply_patch"],
    "group:runtime": ["exec", "process"],
    "group:sessions": ["sessions_list", "sessions_history", ...],
    "group:memory": ["memory_search", "memory_get"],
    "group:web": ["web_search", "web_fetch"],
    "group:automation": ["cron", "gateway"],
    "group:messaging": ["message"],
    "group:nodes": ["nodes"],
    "group:lurkbot": [/* all native tools */],
}
```

### Adding to a Group

To make your tool available in a profile, add it to the appropriate group:

```python
# In src/lurkbot/tools/policy.py
TOOL_GROUPS = {
    # ...existing groups...
    "group:custom": ["my_tool", "another_tool"],
}
```

## Best Practices

1. **Follow conventions**: Match existing code style (ruff, mypy)
2. **Write tests**: Ensure reliability with pytest
3. **Document**: Help others use your extension
4. **Handle errors**: Return meaningful error results
5. **Consider security**: Validate inputs, respect policy system
6. **Use type hints**: Python 3.12+ syntax required

## Next Steps

- [Custom Tools](custom-tools.md) - Detailed tool creation guide
- [Custom Skills](custom-skills.md) - Skill development patterns
- [Custom Channels](custom-channels.md) - Channel adapter implementation
