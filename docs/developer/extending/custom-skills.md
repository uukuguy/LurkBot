# Custom Skills

Learn how to create custom skills to extend LurkBot's capabilities.

## Overview

Skills are markdown-based plugins that add specialized knowledge and behaviors to LurkBot. They're the easiest way to extend functionality without writing Python code.

## Skill Architecture

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

### SkillSource Types

Source: `src/lurkbot/skills/workspace.py:27-33`

```python
class SkillSource(str, Enum):
    """Skill source types."""
    WORKSPACE = "workspace"  # .skills/
    MANAGED = "managed"      # .skill-bundles/
    BUNDLED = "bundled"      # bundled skills
    EXTRA = "extra"          # additional directories
```

## Skill Structure

A skill is a markdown file with YAML frontmatter:

```markdown
---
description: Brief description of the skill
tags:
  - tag1
  - tag2
userInvocable: true
disableModelInvocation: false
---

# Skill Title

System prompt content goes here...
```

## Creating a Skill

### Step 1: Create the File

Create `.skills/my-skill/SKILL.md` or `.skills/my-skill.skill.md`:

```markdown
---
description: Python development expertise with modern best practices
tags:
  - python
  - development
  - coding
userInvocable: true
---

# Python Expert

You are an expert Python developer with deep knowledge of:

- Python 3.12+ features
- Modern Python best practices
- Popular frameworks (FastAPI, Django, Flask)
- Testing with pytest
- Type hints and mypy
- Package management with uv/pip

## Guidelines

When helping with Python code:

1. Use type hints for all functions
2. Follow PEP 8 style guidelines
3. Prefer f-strings over .format()
4. Use pathlib for file operations
5. Handle exceptions appropriately

## Code Style

```python
# Good example
def process_data(items: list[str]) -> dict[str, int]:
    """Process items and return counts."""
    return {item: len(item) for item in items}
```

## Common Patterns

### Async/Await
```python
async def fetch_data(url: str) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        return response.json()
```
```

### Step 2: Verify Loading

Skills are auto-discovered. Check with the SkillManager:

```python
from lurkbot.skills.registry import get_skill_manager

manager = get_skill_manager()
manager.load_skills(workspace_root=".")

# List all skills
for skill in manager.list_skills():
    print(f"{skill.key}: {skill.frontmatter.description}")

# Get specific skill
skill = manager.get_skill("python-expert")
```

### Step 3: Use the Skill

The skill activates automatically based on context, or manually via `/skill-name`.

## Skill Frontmatter

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

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `description` | string | Brief description (required) |

### Optional Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `tags` | array | `[]` | Keywords for discovery |
| `userInvocable` | boolean | `true` | User can invoke via /skill-name |
| `disableModelInvocation` | boolean | `false` | Disable model auto-invocation |
| `metadata` | object | `null` | MoltBot-specific metadata |

### MoltBot Metadata

Source: `src/lurkbot/skills/frontmatter.py:43-53`

```python
class MoltbotMetadata(BaseModel):
    """Moltbot-specific metadata."""
    skill_key: str | None = None      # Custom skill key
    emoji: str | None = None          # Skill icon emoji
    homepage: str | None = None       # Homepage URL
    primary_env: str | None = None    # node|python|go|rust
    always: bool = False              # Always load
    os: list[str] = []                # Supported OS
    requires: SkillRequirements | None = None
    install: list[SkillInstallStep] = []
```

## Skill Discovery

### Priority Order

Source: `src/lurkbot/skills/workspace.py:56-117`

Skills are discovered in priority order (lower number = higher priority):

| Priority | Source | Directory | Description |
|----------|--------|-----------|-------------|
| 1 | workspace | `.skills/` | Project-specific skills |
| 2 | managed | `.skill-bundles/` | Managed skill bundles |
| 3 | bundled | Package `skills/` | Built-in skills |
| 4+ | extra | Custom directories | Additional skill paths |

### File Naming Conventions

- `SKILL.md` - Standard skill file (key = parent directory name)
- `{name}.skill.md` - Named skill file (key = filename without `.skill.md`)

Example directory structure:

```
.skills/
├── python-expert/
│   └── SKILL.md           # key: "python-expert"
├── git-helper.skill.md    # key: "git-helper"
└── docker/
    └── SKILL.md           # key: "docker"
```

### Deduplication

Source: `src/lurkbot/skills/workspace.py:193-215`

When multiple skills have the same key, the one with higher priority (lower number) wins:

```python
def deduplicate_skills(skills: list[SkillEntry]) -> dict[str, SkillEntry]:
    """Deduplicate skills (keep highest priority)."""
    result: dict[str, SkillEntry] = {}
    for skill in skills:
        if skill.key not in result:
            result[skill.key] = skill
    return result
```

## Skill Types

### Knowledge Skills

Add domain expertise:

```markdown
---
description: Kubernetes expertise for container orchestration
tags:
  - kubernetes
  - k8s
  - containers
---

# Kubernetes Expert

You are an expert in Kubernetes and container orchestration.

## Core Concepts

- **Pods**: Smallest deployable units
- **Deployments**: Declarative updates for Pods
- **Services**: Network abstraction for Pods
- **ConfigMaps**: Configuration data
- **Secrets**: Sensitive data

## Best Practices

1. Use namespaces for isolation
2. Set resource limits
3. Use liveness/readiness probes
4. Implement proper RBAC
```

### Task Skills

Define specific workflows:

```markdown
---
description: Pull request review workflow
tags:
  - git
  - review
  - workflow
---

# PR Review Workflow

When reviewing a pull request:

1. **Fetch the PR**
   ```bash
   gh pr checkout <number>
   ```

2. **Review changes**
   - Check code style
   - Verify tests pass
   - Look for security issues

3. **Provide feedback**
   - Be constructive
   - Suggest improvements
   - Approve or request changes
```

### Subagent Skills

Create specialized subagents:

```markdown
---
description: Research specialist for information gathering
tags:
  - research
  - subagent
---

# Researcher Subagent

You are a research specialist. When given a topic:

1. Search for relevant information
2. Gather multiple sources
3. Verify facts across sources
4. Synthesize findings
5. Present a comprehensive summary

## Research Guidelines

- Use authoritative sources
- Cross-reference information
- Note conflicting information
- Cite sources
```

## Skill Manager API

### SkillManager Class

Source: `src/lurkbot/skills/registry.py:140-257`

```python
class SkillManager:
    """Skill manager for lifecycle management."""

    def load_skills(
        self,
        workspace_root: Path | str | None = None,
        extra_dirs: list[Path | str] | None = None,
        clear: bool = True,
    ) -> int:
        """Load skills from directories."""

    def reload_skills(self) -> int:
        """Reload skills with previous configuration."""

    def get_skill(self, key: str) -> SkillEntry | None:
        """Get skill by key."""

    def list_skills(self) -> list[SkillEntry]:
        """List all skills."""

    def search_skills(
        self,
        tag: str | None = None,
        user_invocable: bool | None = None,
        model_invocable: bool | None = None,
    ) -> list[SkillEntry]:
        """Search skills with filters."""
```

### SkillRegistry Class

Source: `src/lurkbot/skills/registry.py:18-132`

```python
class SkillRegistry:
    """Skill registry for storage and queries."""

    def register(self, skill: SkillEntry) -> None:
        """Register a skill."""

    def unregister(self, key: str) -> bool:
        """Unregister a skill."""

    def get(self, key: str) -> SkillEntry | None:
        """Get skill by key."""

    def has(self, key: str) -> bool:
        """Check if skill exists."""

    def list_all(self) -> list[SkillEntry]:
        """List all skills (sorted by key)."""

    def find_by_tag(self, tag: str) -> list[SkillEntry]:
        """Find skills by tag."""

    def find_user_invocable(self) -> list[SkillEntry]:
        """Find user-invocable skills."""

    def find_model_invocable(self) -> list[SkillEntry]:
        """Find model-invocable skills."""
```

### Global Singleton

Source: `src/lurkbot/skills/registry.py:267-276`

```python
from lurkbot.skills.registry import get_skill_manager

# Get global skill manager
manager = get_skill_manager()
```

## Skill Requirements

Source: `src/lurkbot/skills/frontmatter.py:20-26`

Define dependencies for your skill:

```markdown
---
description: Docker assistance
metadata: |
  {"moltbot": {
    "requires": {
      "bins": ["docker"],
      "anyBins": ["docker-compose", "docker compose"],
      "env": ["DOCKER_HOST"]
    }
  }}
---
```

```python
class SkillRequirements(BaseModel):
    """Skill dependency requirements."""
    bins: list[str] = []      # Required binaries
    any_bins: list[str] = []  # Any one of these binaries
    env: list[str] = []       # Required environment variables
    config: list[str] = []    # Required config items
```

## Testing Skills

### Manual Testing

1. Create the skill file
2. Load skills with SkillManager
3. Verify skill is discovered
4. Test various prompts

### Automated Testing

```python
# tests/skills/test_python_expert.py
import pytest
from lurkbot.skills.registry import SkillManager
from lurkbot.skills.frontmatter import parse_skill_frontmatter

def test_skill_frontmatter_parsing():
    content = """---
description: Test skill
tags:
  - test
userInvocable: true
---

# Test Skill

Content here.
"""
    frontmatter, body = parse_skill_frontmatter(content)

    assert frontmatter.description == "Test skill"
    assert "test" in frontmatter.tags
    assert frontmatter.user_invocable is True
    assert "Content here" in body

def test_skill_discovery(tmp_path):
    # Create test skill
    skill_dir = tmp_path / ".skills" / "test-skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("""---
description: Test skill
---

# Test
""")

    manager = SkillManager()
    count = manager.load_skills(workspace_root=tmp_path)

    assert count == 1
    skill = manager.get_skill("test-skill")
    assert skill is not None
    assert skill.key == "test-skill"
```

## Best Practices

1. **Keep focused**: One skill per domain
2. **Clear descriptions**: Help discovery and auto-invocation
3. **Provide examples**: Show expected usage patterns
4. **Document dependencies**: List requirements in metadata
5. **Test thoroughly**: Verify behavior with different prompts
6. **Use tags**: Enable discovery by topic
7. **Consider invocation**: Set `userInvocable` and `disableModelInvocation` appropriately

---

## See Also

- [Skills Overview](../../advanced/skills.md) - User documentation
- [Custom Tools](custom-tools.md) - Create tools
- [Custom Channels](custom-channels.md) - Create channels
- [Architecture](../architecture.md) - System design
