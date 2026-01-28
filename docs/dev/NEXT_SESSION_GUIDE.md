# Next Session Guide

## Session Context

**Last Session Date**: 2026-01-29 (续-5)
**Phase Completed**: Phase 6 - Skills System (100% ✅)
**Status**: ✅ Skills Parser, Loader, Registry and Bundled Skills Implemented

## What Was Accomplished

### Phase 6: Skills System (100% COMPLETE ✅)

**1. Skill Types** (`src/lurkbot/skills/types.py`) ✅
- `SkillRequirements` - Binary/env/config requirements
- `SkillMetadata` - Moltbot-specific metadata (emoji, requires, install)
- `SkillFrontmatter` - Parsed YAML frontmatter model
- `SkillEntry` - Complete skill representation
- `SkillSnapshot` - Cached skill state for versioning

**2. Skill Parser** (`src/lurkbot/skills/parser.py`) ✅
- YAML frontmatter parsing with regex
- JSON metadata field parsing
- Source type detection (bundled/managed/workspace/extra)
- Directory loading with skill discovery

**3. Skill Loader** (`src/lurkbot/skills/loader.py`) ✅
- Multi-source loading with precedence:
  1. Extra directories (lowest)
  2. Bundled skills
  3. Managed skills (~/.lurkbot/config/skills)
  4. Workspace skills (highest)
- Eligibility checking:
  - OS platform matching
  - Required binaries (bins)
  - Any binaries (anyBins)
  - Environment variables (env)
  - Always-on skills bypass checks
- Snapshot building for AI context

**4. Skill Registry** (`src/lurkbot/skills/registry.py`) ✅
- Thread-safe skill management
- Hot-reload support via `refresh()`
- Skill lookup by name, emoji
- Prompt generation for AI context
- Version tracking for cache invalidation

**5. Configuration** (`src/lurkbot/config/settings.py`) ✅
- Added `SkillSettings` model
- `allow_bundled` - Bundled skill allowlist
- `extra_dirs` - Additional skill directories
- `entries` - Per-skill configuration

**6. Bundled Skills** (`skills/`) ✅
- `github/SKILL.md` - GitHub CLI integration
- `weather/SKILL.md` - Weather queries (wttr.in)
- `web-search/SKILL.md` - Web search capabilities

**7. Test Coverage** ✅
- Created `tests/test_skills.py` with 42 unit tests:
  - Type/model tests
  - Parser tests
  - Loader tests
  - Registry tests
  - Integration tests

**Test Results**:
```
176 passed, 4 skipped (browser tests), 13 deselected (docker tests)
```

## Configuration Reference

### Skills Settings

```bash
# Enable/disable skills system
LURKBOT_SKILLS__ENABLED=true

# Allowlist specific bundled skills (null = all, [] = none)
LURKBOT_SKILLS__ALLOW_BUNDLED=["github", "weather"]

# Add extra skill directories
LURKBOT_SKILLS__EXTRA_DIRS=["/path/to/skills"]
```

### Skill File Format (SKILL.md)

```yaml
---
name: skill-name
description: Short description of the skill
homepage: https://example.com
metadata: {"moltbot":{"emoji":"🔧","requires":{"bins":["tool"]}}}
---

# Skill Name

Markdown documentation and examples...
```

### Metadata Fields

```json
{
  "moltbot": {
    "emoji": "🔧",
    "always": false,
    "os": ["darwin", "linux"],
    "requires": {
      "bins": ["required_binary"],
      "anyBins": ["optional1", "optional2"],
      "env": ["API_KEY"],
      "config": ["some.config.path"]
    },
    "install": [
      {"kind": "brew", "formula": "tool", "bins": ["tool"]}
    ]
  }
}
```

## Next Phase Priorities

### Phase 7: Multi-Model Support (Next Priority)

**Objective**: Add support for multiple AI providers

#### Tasks:
1. **Model Adapters**
   - OpenAI GPT adapter
   - Google Gemini adapter
   - Ollama local adapter

2. **Model Selection**
   - Per-session model selection
   - Model fallback chains

3. **Configuration**
   - Model-specific settings
   - API key management

### Phase 8: Web Interface (Future)

**Objective**: Add web-based control interface

#### Tasks:
1. HTTP API endpoints for session management
2. WebSocket real-time updates
3. Simple web dashboard

## Known Issues & Limitations

### Resolved in Phase 6
- ✅ ~~No Skills System~~ - **SOLVED** (Phase 6)

### Remaining Limitations
1. ⚠️ **Single Model** - Only Claude supported (Future Phase 7)
2. ⚠️ **No Web Interface** - Future Phase 8

### Technical Debt
- [ ] Fix unused argument warnings in other modules
- [ ] Add docstrings to all public APIs
- [x] Add type hints to functions
- [x] Create tests for skills
- [ ] E2E test with real APIs
- [ ] Skills hot-reload file watching

## Important Notes for Next Session

### Code Style Reminders
- Use `async/await` for I/O operations
- Use `loguru.logger` for logging
- Use `datetime.now(UTC)` instead of `datetime.utcnow()`
- Use Pydantic models for data validation
- Use `all()/any()` instead of for loops for eligibility checks

### Testing Guidelines
```bash
make test                       # All core tests (excludes docker)
pytest -m "not docker"          # Explicit skip docker tests
pytest tests/test_skills.py     # Skills tests only
make lint                       # Check code style
make format                     # Auto-fix formatting
```

### Configuration
- Settings loaded from environment: `LURKBOT_*`
- Nested settings use `__`: `LURKBOT_SKILLS__ALLOW_BUNDLED`
- Skills directory: `~/.lurkbot/config/skills/`

## Quick Start Commands

```bash
# Install dependencies
make dev

# Run tests
make test
pytest -m "not docker"

# Check code
make lint
make format

# Run CLI
make cli ARGS="--help"
make gateway
```

## File Structure Reference

```
src/lurkbot/
├── skills/                     # ✅ Phase 6 (NEW)
│   ├── __init__.py            # Exports main classes
│   ├── types.py               # Pydantic models
│   ├── parser.py              # YAML frontmatter parser
│   ├── loader.py              # Multi-source skill loader
│   └── registry.py            # Thread-safe skill registry
├── storage/                    # ✅ Phase 4
│   ├── __init__.py
│   └── jsonl.py
├── sandbox/                    # ✅ Phase 3
│   └── ...
├── tools/
│   ├── builtin/
│   │   ├── bash.py
│   │   ├── file_ops.py
│   │   └── browser.py
│   ├── base.py
│   ├── registry.py
│   └── approval.py
├── agents/
│   ├── base.py
│   └── runtime.py
├── channels/                   # ✅ Phase 5
│   ├── __init__.py
│   ├── base.py
│   ├── telegram.py
│   ├── discord.py
│   ├── slack.py
│   └── registry.py
└── config/
    └── settings.py            # ✅ Updated with SkillSettings

skills/                         # ✅ Phase 6 (NEW)
├── github/
│   └── SKILL.md
├── weather/
│   └── SKILL.md
└── web-search/
    └── SKILL.md

tests/
├── test_skills.py             # ✅ Phase 6 (42 tests - NEW)
├── test_channels.py           # ✅ Phase 5
├── test_session_storage.py    # ✅ Phase 4
├── test_approval.py           # ✅ Phase 3
├── test_approval_integration.py
├── test_tools.py              # ✅ Phase 2
└── ...
```

---

**Document Updated**: 2026-01-29 (Session 续-5)
**Next Review**: Start of next session
**Progress**: Phase 6 (100% ✅) → Ready for Phase 7 (Multi-Model Support)
