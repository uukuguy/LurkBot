# ClawHub Integration

## Overview

LurkBot now integrates with ClawHub (https://clawhub.ai), the official skill marketplace for OpenClaw/Moltbot ecosystem. This allows you to discover, install, and manage skills from a centralized repository.

## Features

- **Search Skills**: Find skills by keywords, tags, or categories
- **Install Skills**: Download and install skills with automatic dependency resolution
- **Update Skills**: Check for and install updates to installed skills
- **List Skills**: View all installed skills from different sources
- **Remove Skills**: Uninstall skills you no longer need

## Usage

### Search for Skills

```bash
# Search by keyword
lurkbot skills search weather

# Filter by tags
lurkbot skills search github --tag productivity

# Limit results
lurkbot skills search notion --limit 10
```

### Get Skill Information

```bash
# View detailed information
lurkbot skills info openclaw/weather

# Shows: name, version, author, downloads, rating, tags, etc.
```

### Install Skills

```bash
# Install latest version
lurkbot skills install openclaw/weather

# Install specific version
lurkbot skills install openclaw/github --version 1.2.0

# Force reinstall
lurkbot skills install openclaw/notion --force
```

The installer will:
1. Check if the skill already exists
2. Recursively install dependencies
3. Download and verify the package (SHA256 checksum)
4. Extract to `.skill-bundles/` directory
5. Reload the skill registry

### List Installed Skills

```bash
# List all skills
lurkbot skills list

# Filter by source
lurkbot skills list --source bundled   # Built-in skills
lurkbot skills list --source managed   # ClawHub skills
lurkbot skills list --source workspace # Local .skills/
```

### Check for Updates

```bash
# Check for updates (dry run)
lurkbot skills update --dry-run

# Install updates
lurkbot skills update
```

### Remove Skills

```bash
# Remove a skill (with confirmation)
lurkbot skills remove weather

# Force remove without confirmation
lurkbot skills remove github --force
```

## Skill Sources

LurkBot loads skills from multiple sources with priority order:

1. **Workspace** (`.skills/`) - Priority 1 (highest)
   - Project-specific skills
   - Override bundled or managed skills

2. **Managed** (`.skill-bundles/`) - Priority 2
   - Skills installed from ClawHub
   - Automatic dependency management

3. **Bundled** (`skills/`) - Priority 3
   - Built-in skills shipped with LurkBot
   - 10 Tool wrapper skills + community skills

4. **Extra** (custom directories) - Priority 4+ (lowest)
   - User-defined skill directories

## API Reference

### ClawHubClient

```python
from lurkbot.skills import ClawHubClient

async with ClawHubClient() as client:
    # Search skills
    skills = await client.search("weather", limit=10)

    # Get skill info
    skill = await client.info("openclaw/weather")

    # List versions
    versions = await client.list_versions("openclaw/weather")

    # Download skill
    package = await client.download("openclaw/weather", version="1.0.0")
```

### SkillManager

```python
from lurkbot.skills import get_skill_manager

manager = get_skill_manager()

# Load skills
manager.load_skills(workspace_root=".")

# Install from ClawHub
skill = await manager.install_from_clawhub(
    slug="openclaw/weather",
    version="1.0.0",
    workspace_root=".",
)

# Check updates
updates = await manager.check_updates()
```

## Architecture

### Tool-Skill Relationship

```
┌─────────────────────────────────────────────────────────┐
│ Layer 4: User Interface                                 │
│ • /skill-name commands                                  │
│ • Natural language requests                             │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│ Layer 3: Skills (Business Logic)                        │
│ • SKILL.md documentation                                │
│ • Metadata and configuration                            │
│ • Wraps one or more Tools                               │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│ Layer 2: Tools (System Functions)                       │
│ • Python async functions                                │
│ • Tool Policy security filtering                        │
│ • Atomic operations                                     │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│ Layer 1: System Infrastructure                          │
│ • File system, network, processes                       │
└─────────────────────────────────────────────────────────┘
```

### Skill Types

**1. Tool Wrapper Skills** (10 built-in)
- `sessions` - Wraps 6 session management tools
- `memory` - Wraps 2 memory/knowledge tools
- `web` - Wraps 2 web search/fetch tools
- `messaging` - Wraps message tool
- `cron`, `gateway`, `media`, `nodes`, `tts`, `hooks`

**2. Standalone Skills** (community)
- OpenClaw ecosystem: 52 skills available
- Examples: weather, github, notion, slack, discord
- Can be installed from ClawHub

## Configuration

### Environment Variables

```bash
# Optional: Custom ClawHub API URL
export CLAWHUB_API_URL="https://api.clawhub.ai/v1"
```

### Skill Metadata

Skills can include ClawHub metadata in frontmatter:

```yaml
---
name: weather
description: Weather lookup using wttr.in
version: 1.0.0
metadata:
  moltbot:
    clawhub_slug: openclaw/weather
    emoji: "🌤️"
---
```

## Development

### Running Tests

```bash
# Run ClawHub integration tests
pytest tests/test_skills_clawhub.py -xvs

# Run all skills tests
pytest tests/test_skills* -xvs
```

### Creating Skills

See [SKILL_DEVELOPMENT.md](./SKILL_DEVELOPMENT.md) for guidelines on creating your own skills.

## Troubleshooting

### Skill Not Found

```bash
# Check if skill exists on ClawHub
lurkbot skills search <skill-name>

# View available versions
lurkbot skills info <slug>
```

### Installation Fails

```bash
# Try force reinstall
lurkbot skills install <slug> --force

# Check logs for detailed errors
# Logs are output to stderr
```

### Update Check Fails

Skills must have `clawhub_slug` metadata to check for updates:

```yaml
metadata:
  moltbot:
    clawhub_slug: openclaw/skill-name
```

## Next Steps

### Phase 1.2: OpenClaw Skills Integration

Install high-priority skills from OpenClaw ecosystem:

```bash
# Essential skills
lurkbot skills install openclaw/mcporter     # MCP tools framework
lurkbot skills install openclaw/summarize    # Content summarization
lurkbot skills install openclaw/github       # GitHub integration
lurkbot skills install openclaw/notion       # Notion workspace

# Communication
lurkbot skills install openclaw/himalaya     # Email client
lurkbot skills install openclaw/discord      # Discord integration
lurkbot skills install openclaw/slack        # Slack integration

# Local tools (no VPN required)
lurkbot skills install openclaw/obsidian     # Local Markdown notes
lurkbot skills install openclaw/weather      # Weather lookup
lurkbot skills install openclaw/openai-whisper  # Offline speech recognition
```

See [IMPLEMENTATION_PLAN.md](./IMPLEMENTATION_PLAN.md) for the complete roadmap.

## References

- [ClawHub Website](https://clawhub.ai)
- [OpenClaw Repository](https://github.com/openclaw/openclaw)
- [Moltbot Original](https://github.com/moltbot/moltbot)
- [LurkBot Skills Documentation](./skills/)
