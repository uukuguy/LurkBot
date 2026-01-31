# ClawHub Integration

> **⚠️ Important Note (Updated 2026-01-31)**
>
> ClawHub uses a **Convex backend** (not a traditional REST API). The implementation in this document assumes HTTP API endpoints that may not exist. The official method to interact with ClawHub is through the `clawhub` CLI tool (TypeScript/Bun).
>
> **Current Status**: Phase 1.1 complete (API client code ready), but actual ClawHub integration requires either:
> 1. Installing and wrapping the Node.js `clawhub` CLI
> 2. Downloading skills directly from [github.com/openclaw/skills](https://github.com/openclaw/skills)
> 3. Waiting for an official Python SDK or stable HTTP API
>
> See [Phase 1.2 Research Findings](#phase-12-research-findings) below for details.

## Overview

LurkBot integrates with ClawHub (https://clawhub.com), the official skill marketplace for OpenClaw ecosystem. This allows you to discover, install, and manage skills from a centralized repository.

**Note**: The API client implementation is complete, but the assumed REST endpoints need verification/adjustment to match ClawHub's actual Convex-based architecture.

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

- [ClawHub Website](https://clawhub.com)
- [OpenClaw Repository](https://github.com/openclaw/openclaw)
- [ClawHub Repository](https://github.com/openclaw/clawhub)
- [Skills Archive](https://github.com/openclaw/skills)
- [OpenClaw Documentation](https://docs.openclaw.ai/tools/skills)

---

## Phase 1.2 Research Findings

**Date**: 2026-01-31

### ClawHub Architecture Discovery

During Phase 1.2 implementation, we discovered that ClawHub's architecture differs significantly from initially assumed:

#### Actual Architecture

```
┌─────────────────────────────────────────────────────────┐
│ ClawHub Architecture (Actual)                           │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Frontend: TanStack Start (React, Vite/Nitro)          │
│     │                                                   │
│     ├─ https://clawhub.com (SPA)                       │
│     └─ https://clawhub.com/skills (Vector search UI)   │
│                                                         │
│  Backend: Convex (Serverless)                          │
│     │                                                   │
│     ├─ Database + File Storage                         │
│     ├─ HTTP Actions (not REST API)                     │
│     ├─ OpenAI Embeddings (text-embedding-3-small)     │
│     └─ Vector Search                                   │
│                                                         │
│  CLI: clawhub (TypeScript/Bun)                         │
│     │                                                   │
│     ├─ search <query>     - Vector search              │
│     ├─ install <slug>     - Install skill              │
│     ├─ update [slug]      - Update skills              │
│     ├─ list               - List installed             │
│     ├─ publish <path>     - Publish skill              │
│     └─ sync               - Batch publish              │
│                                                         │
│  Skills Archive: github.com/openclaw/skills            │
│     │                                                   │
│     └─ skills/                                         │
│         ├─ author1/skill-name/SKILL.md                 │
│         ├─ author2/another-skill/SKILL.md              │
│         └─ ... (747 authors, unknown # of skills)      │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

#### What We Initially Assumed

```python
# Assumed REST API (NOT REAL)
BASE_URL = "https://api.clawhub.ai/v1"

GET  /skills/search?q=weather
GET  /skills/{slug}
GET  /skills/{slug}/versions
GET  /skills/{slug}/download/{version}
```

#### What Actually Exists

**Convex Backend**:
- No traditional REST endpoints
- Uses Convex HTTP actions (different architecture)
- Schema defined in `packages/schema/` (clawhub-schema)
- Routes in `convex/` directory

**CLI Tool**:
```bash
# Requires Node.js/Bun environment
./clawhub search weather
./clawhub install openclaw/weather
./clawhub update --all
```

**Skills Repository**:
- All skills archived at `github.com/openclaw/skills`
- Organized by author: `skills/{author}/{skill-name}/SKILL.md`
- 747 author directories (community contributions)

### Implementation Options

#### Option A: Wrap clawhub CLI (Recommended if needing ClawHub features)

**Pros**:
- ✅ Uses official tool
- ✅ Handles authentication, vector search, versioning
- ✅ Automatic updates from clawhub.com

**Cons**:
- ❌ Requires Node.js/Bun runtime
- ❌ Subprocess overhead
- ❌ Cross-platform complexity

**Implementation**:
```python
import subprocess
import shutil

class ClawHubCLIWrapper:
    def __init__(self):
        self.cli_path = shutil.which("clawhub")
        if not self.cli_path:
            raise RuntimeError("clawhub CLI not installed")

    async def search(self, query: str) -> list[dict]:
        result = subprocess.run(
            ["clawhub", "search", query, "--json"],
            capture_output=True,
            text=True
        )
        return json.loads(result.stdout)

    async def install(self, slug: str):
        subprocess.run(
            ["clawhub", "install", slug, "--dir", ".skill-bundles"],
            check=True
        )
```

#### Option B: GitHub Direct Download (Simplest)

**Pros**:
- ✅ No external dependencies
- ✅ Pure Python implementation
- ✅ Works offline (after initial clone)
- ✅ Direct access to all 747 authors

**Cons**:
- ❌ No vector search
- ❌ No automatic updates
- ❌ Manual version management
- ❌ Need to know exact author/skill name

**Implementation**:
```python
import httpx
import tarfile

class GitHubSkillsDownloader:
    REPO = "openclaw/skills"
    BASE_URL = f"https://api.github.com/repos/{REPO}"

    async def search(self, query: str) -> list[str]:
        # Simple GitHub code search
        url = "https://api.github.com/search/code"
        params = {
            "q": f"repo:{self.REPO} path:skills filename:SKILL.md {query}",
            "per_page": 20
        }
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, params=params)
            items = resp.json()["items"]
            return [item["path"] for item in items]

    async def download(self, author: str, skill: str) -> bytes:
        # Download specific skill directory as tarball
        url = f"https://github.com/{self.REPO}/archive/refs/heads/main.tar.gz"
        # Extract only skills/{author}/{skill}/
        ...
```

#### Option C: Wait for Official Python SDK

**Pros**:
- ✅ Official support
- ✅ Proper typing and async support
- ✅ Stable API

**Cons**:
- ❌ Doesn't exist yet
- ❌ Unknown timeline

### Current Status

**Phase 1.1**: ✅ Complete
- ClawHub API client implementation (assumes REST API)
- Skills CLI commands (search, install, update, list, remove)
- SkillRegistry extensions (install_from_clawhub, check_updates)
- Unit tests (4/4 passing)

**Phase 1.2**: ⏸️ Paused
- Installation of 12 high-priority OpenClaw skills
- Waiting for decision on implementation approach

### Recommendations

1. **Short-term**: Keep current 13 bundled skills
   - Covers core functionality (sessions, memory, web, messaging, etc.)
   - No external dependencies
   - Fully tested and working

2. **Mid-term**: Implement Option B (GitHub direct download)
   - Simple, pure Python
   - Good for specific, known skills
   - Low maintenance overhead

3. **Long-term**: Monitor for official Python SDK
   - Watch `openclaw/clawhub` for Python client
   - Or implement Option A if ClawHub integration becomes critical

### Alternative: Focus on Other Priorities

Given that:
- LurkBot's 13 bundled skills cover core functionality
- ClawHub integration requires significant adaptation
- Other high-priority items exist (国内生态, 企业安全)

It may be strategic to:
1. ✅ Keep ClawHub API client code (for future use)
2. ✅ Document the architecture findings (this section)
3. 🎯 Pivot to Phase 2 (国内生态适配) or Phase 4 (企业安全)
4. 🔄 Revisit ClawHub when official Python SDK or stable API exists

### Skills Currently Available (Bundled)

LurkBot's 13 bundled skills provide comprehensive functionality:

| Skill | Category | Tools Wrapped |
|-------|----------|---------------|
| `sessions` | Core | 6 session management tools |
| `memory` | Core | 2 memory/vector search tools |
| `web` | Core | 2 web search/fetch tools |
| `messaging` | Core | 1 message tool |
| `cron` | Automation | 1 cron scheduling tool |
| `gateway` | Automation | 1 gateway control tool |
| `hooks` | Automation | 1 hooks management tool |
| `media` | Media | 2 image/media tools |
| `tts` | Media | 1 text-to-speech tool |
| `nodes` | System | 1 nodes tool |
| `github` | Productivity | GitHub integration |
| `weather` | Productivity | Weather lookup |
| `web-search` | Productivity | Web search |

**Total**: 22 tools across 13 skills

### Skills Potentially Available (ClawHub)

According to OpenClaw documentation and ClawHub website:
- **Community skills**: 747 authors (unknown total count)
- **Popular categories**:
  - AI/ML integrations (Gemini, Whisper)
  - Communication (Discord, Slack, Email)
  - Productivity (Notion, Obsidian, Trello)
  - Development (GitHub, Docker, K8s)
  - Automation (cron, workflows)

---

**Document Updated**: 2026-01-31
**Status**: Phase 1.1 Complete, Phase 1.2 Paused
