# Next Session Guide - Phase 1.2

**Last Updated**: 2026-01-31
**Current Phase**: Phase 1.1 Complete ✅
**Next Phase**: Phase 1.2 - OpenClaw Skills Installation

---

## Phase 1.1 Completion Summary

### What Was Done ✅

1. **ClawHub API Client** - Full async implementation with httpx
2. **SkillRegistry Extensions** - install_from_clawhub(), check_updates()
3. **Skills CLI Commands** - 6 subcommands (search, info, install, list, update, remove)
4. **Data Model Updates** - Extended SkillFrontmatter with name, version, tools
5. **Tests** - 4 passing unit tests
6. **Documentation** - Complete user guide and API reference

### Files Created/Modified

**New Files (5)**:
- `src/lurkbot/skills/clawhub.py` (311 lines)
- `src/lurkbot/cli/skills.py` (321 lines)
- `tests/test_skills_clawhub.py` (56 lines)
- `docs/main/CLAWHUB_INTEGRATION.md` (417 lines)
- `docs/main/PHASE_1_1_SUMMARY.md` (summary doc)

**Modified Files (5)**:
- `src/lurkbot/skills/registry.py` (+114 lines)
- `src/lurkbot/skills/frontmatter.py` (+3 fields)
- `src/lurkbot/skills/workspace.py` (path fix)
- `src/lurkbot/skills/__init__.py` (+6 exports)
- `src/lurkbot/cli/main.py` (+2 lines)

### Current Status

```bash
# Working commands
lurkbot skills list        # Shows 13 bundled skills
lurkbot skills search      # Search ClawHub (API not tested yet)
lurkbot skills install     # Install from ClawHub (API not tested yet)

# Test status
pytest tests/test_skills_clawhub.py  # 4/4 passing
```

---

## Phase 1.2 Plan - Install OpenClaw Skills

### Objective

Install 12 high-priority skills from OpenClaw ecosystem to LurkBot.

### High-Priority Skills (12 Total)

#### Essential Skills (4)
1. **openclaw/mcporter** - MCP tools framework
2. **openclaw/summarize** - Content summarization
3. **openclaw/github** - GitHub integration
4. **openclaw/notion** - Cloud knowledge base

#### Communication Skills (4)
5. **openclaw/himalaya** - Email client
6. **openclaw/openai-whisper** - Offline speech recognition
7. **openclaw/discord** - Discord integration
8. **openclaw/slack** - Slack integration

#### Productivity Skills (4)
9. **openclaw/obsidian** - Local Markdown notes
10. **openclaw/weather** - Weather lookup
11. **openclaw/goplaces** - Place search
12. **openclaw/clawdhub** - Skill management hub

### Installation Commands

```bash
# Essential (install first)
lurkbot skills install openclaw/mcporter
lurkbot skills install openclaw/summarize
lurkbot skills install openclaw/github
lurkbot skills install openclaw/notion

# Communication
lurkbot skills install openclaw/himalaya
lurkbot skills install openclaw/openai-whisper
lurkbot skills install openclaw/discord
lurkbot skills install openclaw/slack

# Productivity
lurkbot skills install openclaw/obsidian
lurkbot skills install openclaw/weather
lurkbot skills install openclaw/goplaces
lurkbot skills install openclaw/clawdhub
```

### Expected Results

- Skills installed to `.skill-bundles/<skill-name>/`
- Total skills: 13 (bundled) + 12 (installed) = 25 skills
- Each skill includes SKILL.md with metadata and usage examples

---

## Known Issues and Limitations

### ⚠️ Critical: ClawHub API May Not Exist

**Problem**: The ClawHub API implementation is based on assumed endpoints:
```
https://api.clawhub.ai/v1/skills/search
https://api.clawhub.ai/v1/skills/{slug}
https://api.clawhub.ai/v1/skills/{slug}/versions
```

**Impact**: Installation commands will fail if API doesn't exist or uses different schema.

**Solutions**:
1. **Check ClawHub API docs** - Find actual API specification
2. **Use OpenClaw CLI** - Fall back to `claw install` command wrapper
3. **Manual installation** - Download skills from GitHub and extract to `.skill-bundles/`

### Manual Installation Fallback

If ClawHub API is not available:

```bash
# Example: Install weather skill manually
cd .skill-bundles
git clone https://github.com/openclaw/skills openclaw-skills
cp -r openclaw-skills/weather ./weather
lurkbot skills list  # Verify installation
```

### Other Limitations

1. **Integration tests missing** - Only unit tests implemented
2. **Update installation incomplete** - `update` command checks but doesn't install
3. **Dependency validation incomplete** - System dependencies not verified
4. **No progress indicators** - Long downloads have no progress feedback

---

## Architecture Notes

### Skill Loading Priority

```
Priority 1: .skills/         (workspace, highest)
Priority 2: .skill-bundles/  (managed, ClawHub)
Priority 3: skills/          (bundled, built-in)
Priority 4: extra dirs       (user-defined, lowest)
```

### Tool vs Skill Distinction

**System-Level Tools (6)** - Keep as pure Tools:
- exec, process, read, write, edit, apply_patch
- High performance + 9-layer security filtering

**Business-Level Tools (16)** - Wrapped by Skills:
- sessions (6 tools), memory (2), web (2), messaging (1), etc.
- Skill provides documentation, configuration, usage examples

**Community Skills (52+)** - Standalone implementations:
- From ClawHub/OpenClaw ecosystem
- May use external tools, APIs, or wrap LurkBot tools

### Installation Flow

```
Search → Info → Dependencies → Download → Verify → Extract → Reload
  ↓       ↓         ↓            ↓         ↓         ↓        ↓
 Find   Metadata  Recursive   SHA256   tar.gz   .skill-  Registry
 skill   + vers   install     check    unzip    bundles/  reload
```

---

## Quick Start for Next Session

### 1. Verify Current Status

```bash
# Check installation
lurkbot skills list

# Should show 13 bundled skills:
# cron, gateway, github, hooks, media, memory,
# messaging, nodes, sessions, tts, weather, web, web-search

# Run tests
pytest tests/test_skills_clawhub.py -xvs
# Should show: 4 passed, 1 warning
```

### 2. Test ClawHub API (if available)

```bash
# Try searching
lurkbot skills search weather

# Try getting info
lurkbot skills info openclaw/weather

# If these fail, ClawHub API may not exist or use different endpoints
```

### 3. Proceed with Installation

**Option A: ClawHub API Works**
- Use `lurkbot skills install` commands listed above
- Verify each installation with `lurkbot skills list`

**Option B: ClawHub API Not Available**
- Implement fallback to OpenClaw CLI (`claw install`)
- Or manually download skills from GitHub
- Or adjust ClawHubClient to match real API

### 4. Verify Installations

```bash
# After each install
lurkbot skills list --source managed

# Check skill details
lurkbot skills info <slug>
```

---

## Development Tasks for Phase 1.2

### If ClawHub API Works

- [ ] Install 4 essential skills
- [ ] Install 4 communication skills
- [ ] Install 4 productivity skills
- [ ] Verify all skills load correctly
- [ ] Test skill invocation (if applicable)
- [ ] Update documentation with installation results

### If ClawHub API Doesn't Work

- [ ] Research actual ClawHub API endpoints
- [ ] Option 1: Adapt ClawHubClient to real API
- [ ] Option 2: Implement OpenClaw CLI wrapper
- [ ] Option 3: Manual installation procedure
- [ ] Update CLAWHUB_INTEGRATION.md with findings
- [ ] Create fallback installation guide

### Additional Tasks

- [ ] Add integration tests with real API calls
- [ ] Implement progress indicators for downloads
- [ ] Add dependency validation (check bins/env)
- [ ] Complete `update` command installation logic
- [ ] Add skill removal verification

---

## Testing Checklist

Before ending Phase 1.2:

```bash
# 1. Skills loaded
lurkbot skills list | grep -c "managed"  # Should be > 0

# 2. Skill count
lurkbot skills list | grep "Installed Skills" | grep -o "[0-9]\+"  # Should be 25+

# 3. Tests passing
pytest tests/test_skills* -xvs  # All pass

# 4. CLI working
lurkbot skills --help  # Shows all commands

# 5. Files exist
ls .skill-bundles/  # Shows installed skills
```

---

## References

### Documentation
- `docs/main/CLAWHUB_INTEGRATION.md` - User guide
- `docs/main/PHASE_1_1_SUMMARY.md` - Phase 1.1 summary
- `docs/design/COMPARISON_ANALYSIS.md` - LurkBot vs Moltbot/OpenClaw

### Implementation
- `src/lurkbot/skills/clawhub.py` - ClawHub API client
- `src/lurkbot/cli/skills.py` - CLI commands
- `src/lurkbot/skills/registry.py` - Installation logic

### External Resources
- [OpenClaw Repository](https://github.com/openclaw/openclaw)
- [ClawHub Website](https://clawhub.ai) - If exists
- [OpenClaw Skills](https://github.com/openclaw/skills)

---

## Questions to Answer in Next Session

1. **Does ClawHub API exist?**
   - If yes: What are the real endpoints?
   - If no: What's the alternative installation method?

2. **Which installation method to use?**
   - ClawHub API (if available)
   - OpenClaw CLI wrapper
   - Manual GitHub download

3. **How many skills to install?**
   - All 12 recommended?
   - Subset based on priority?
   - Wait for API confirmation?

4. **Should we implement Agent auto-install?** (Phase 1.3)
   - Extract skill requirements from prompts
   - Auto-install or request approval

---

## Success Criteria for Phase 1.2

- [ ] At least 5 OpenClaw skills successfully installed
- [ ] Skills appear in `lurkbot skills list --source managed`
- [ ] Each skill has valid SKILL.md in `.skill-bundles/`
- [ ] No critical errors during installation
- [ ] Documentation updated with installation results

---

**Status**: Ready to start Phase 1.2
**Estimated Time**: 1-2 hours (depending on API availability)
**Priority**: High (expands LurkBot skill ecosystem)
