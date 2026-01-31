# Phase 1.2 Research Summary - ClawHub Architecture Discovery

**Date**: 2026-01-31
**Status**: Research Complete, Implementation Paused
**Phase**: 1.2 (OpenClaw Skills Installation)

---

## Executive Summary

Phase 1.2 aimed to install 12 high-priority OpenClaw skills from ClawHub. During implementation, we discovered that ClawHub uses a **Convex backend** (not a traditional REST API), requiring significant architectural adaptation. The phase is paused pending decision on implementation approach.

### Key Findings

✅ **Phase 1.1 Deliverables Working**:
- ClawHub API client code complete (311 lines)
- Skills CLI commands implemented (6 subcommands)
- SkillRegistry extensions functional
- Unit tests passing (4/4)

⚠️ **Architecture Mismatch Discovered**:
- Assumed: REST API at `https://api.clawhub.ai/v1`
- Reality: Convex backend + TypeScript CLI tool
- Impact: Current implementation needs adaptation

📊 **Current Status**:
- **Bundled Skills**: 13 (fully working)
- **ClawHub Skills**: 0 (paused)
- **Target**: 25 total (13 + 12)

---

## Research Findings

### 1. ClawHub Architecture

#### What We Initially Assumed

```
┌─────────────────────────────────────────┐
│ REST API Architecture (Assumed)         │
├─────────────────────────────────────────┤
│                                         │
│  https://api.clawhub.ai/v1/skills       │
│     │                                   │
│     ├─ GET /search?q=weather            │
│     ├─ GET /{slug}                      │
│     ├─ GET /{slug}/versions             │
│     └─ GET /{slug}/download/{version}   │
│                                         │
└─────────────────────────────────────────┘
```

#### What Actually Exists

```
┌──────────────────────────────────────────────────────────┐
│ Convex Backend Architecture (Actual)                     │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  Frontend (SPA)                                          │
│    └─ https://clawhub.com/skills                        │
│       (React + TanStack Router, requires JavaScript)    │
│                                                          │
│  Backend (Convex)                                        │
│    ├─ Database + File Storage                           │
│    ├─ HTTP Actions (not REST endpoints)                 │
│    ├─ OpenAI text-embedding-3-small                     │
│    └─ Vector search                                     │
│                                                          │
│  CLI (Official Tool)                                     │
│    └─ clawhub (TypeScript/Bun)                          │
│       ├─ search <query>                                 │
│       ├─ install <slug>                                 │
│       ├─ update [slug]                                  │
│       ├─ list                                           │
│       └─ publish <path>                                 │
│                                                          │
│  Skills Archive                                          │
│    └─ github.com/openclaw/skills                        │
│       └─ skills/{author}/{skill-name}/SKILL.md          │
│          (747 authors, community contributions)         │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### 2. ClawHub CLI Commands

The official method to interact with ClawHub:

```bash
# Authentication
clawhub login                    # Browser or token auth
clawhub logout                   # Remove credentials
clawhub whoami                   # Validate token

# Skill Discovery
clawhub search <query>           # Vector search
clawhub explore                  # Browse latest updates
clawhub list                     # Show installed skills

# Skill Management
clawhub install <slug>           # Install to ./skills
clawhub update [slug]            # Update skill(s)
clawhub publish <path>           # Publish skill
clawhub sync                     # Batch publish

# Admin (owner/admin only)
clawhub delete <slug>            # Soft-delete skill
clawhub undelete <slug>          # Restore skill
clawhub star <slug>              # Highlight skill
```

**Environment Variables**:
- `CLAWHUB_SITE` - Custom ClawHub site URL
- `CLAWHUB_REGISTRY` - Custom registry URL
- `CLAWHUB_WORKDIR` - Working directory for skills

### 3. Skills Repository Structure

All skills are archived at `github.com/openclaw/skills`:

```
openclaw/skills/
├── skills/
│   ├── author1/
│   │   ├── skill-name/
│   │   │   ├── SKILL.md
│   │   │   ├── bin/            (optional executables)
│   │   │   └── ... (supporting files)
│   ├── author2/
│   │   └── another-skill/
│   │       └── SKILL.md
│   └── ... (747 author directories)
├── LICENSE
└── README.md
```

**Statistics**:
- **Total authors**: 747
- **Total skills**: Unknown (requires recursive scan)
- **Languages**: Python (47.2%), JavaScript (19.3%), Shell (14.3%), TypeScript (8.3%), others
- **Commits**: ~4,550

### 4. Popular Skills (from ClawHub Website)

Sample skills visible on clawhub.com/skills:

| Skill | Author | Category | Stats |
|-------|--------|----------|-------|
| **UI Test** | clawd21 | Testing | ⤓68 ⤒0 ★2 |
| **Moltlist Marketplace** | moltlist | Commerce | ⤓30 ⤒0 ★2 |
| **Stranger Danger** | jamesalmeida | Security | ⤓25 ⤒1 ★0 |
| **Konteks** | jamesalmeida | Memory | ⤓21 ⤒0 ★0 |
| **The Playground** | sam-temaki | Social | ⤓0 ⤒0 ★0 |
| **Molt Chess** | tedkaczynski-the-bot | Games | ⤓0 ⤒0 ★0 |

**Note**: Most listed skills are community experiments (AI social networks, marketplaces, games). The "Essential Skills" mentioned in Phase 1.2 plan (mcporter, summarize, github, notion) were not found on ClawHub website.

---

## Implementation Options Analysis

### Option A: Wrap clawhub CLI ⭐ Recommended (if ClawHub features needed)

**Architecture**:
```python
# Wrapper approach
class ClawHubCLIWrapper:
    def __init__(self):
        self.cli_path = shutil.which("clawhub")
        if not self.cli_path:
            raise RuntimeError("clawhub CLI not installed")

    async def search(self, query: str) -> list[dict]:
        result = subprocess.run(
            ["clawhub", "search", query, "--json"],
            capture_output=True,
            text=True,
            check=True
        )
        return json.loads(result.stdout)

    async def install(self, slug: str, workdir: Path):
        subprocess.run(
            ["clawhub", "install", slug, "--workdir", str(workdir)],
            check=True
        )
```

**Pros**:
- ✅ Uses official tool (guaranteed compatibility)
- ✅ Vector search (OpenAI embeddings)
- ✅ Authentication (GitHub OAuth)
- ✅ Version management
- ✅ Dependency resolution

**Cons**:
- ❌ Requires Node.js/Bun runtime (~50MB)
- ❌ Subprocess overhead (performance)
- ❌ Cross-platform testing (macOS/Linux/Windows)
- ❌ Installation complexity (additional dependency)

**Effort**: 3-5 days
- Install Node.js/Bun detection
- Subprocess wrapper implementation
- Error handling and logging
- Cross-platform testing
- Installation documentation

---

### Option B: GitHub Direct Download ⭐ Recommended (simple, no dependencies)

**Architecture**:
```python
class GitHubSkillsDownloader:
    REPO = "openclaw/skills"
    BASE_URL = "https://api.github.com/repos/openclaw/skills"

    async def search(self, query: str) -> list[str]:
        # GitHub code search API
        url = "https://api.github.com/search/code"
        params = {
            "q": f"repo:{self.REPO} path:skills filename:SKILL.md {query}",
            "per_page": 20
        }
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, params=params)
            items = resp.json()["items"]
            # Extract author/skill from path
            return [self._parse_skill_path(item["path"]) for item in items]

    async def download(self, author: str, skill: str, dest: Path):
        # Download using GitHub API
        url = f"{self.BASE_URL}/contents/skills/{author}/{skill}"
        # Recursively download directory
        ...
```

**Pros**:
- ✅ Pure Python (no external dependencies)
- ✅ Works offline (after git clone)
- ✅ Direct access to all 747 authors
- ✅ Simple implementation

**Cons**:
- ❌ No vector search (keyword only)
- ❌ No automatic updates
- ❌ Manual version management
- ❌ Need exact author/skill name

**Effort**: 2-3 days
- GitHub API integration
- Recursive directory download
- SKILL.md parsing
- Search implementation
- Basic tests

---

### Option C: Wait for Official Python SDK

**Pros**:
- ✅ Official support
- ✅ Proper typing and async
- ✅ Stable API

**Cons**:
- ❌ Doesn't exist yet
- ❌ Unknown timeline
- ❌ Blocks progress

**Effort**: 0 days (wait indefinitely)

---

## Decision Matrix

| Criteria | Option A (CLI Wrap) | Option B (GitHub) | Option C (Wait) |
|----------|---------------------|-------------------|-----------------|
| **Effort** | 3-5 days | 2-3 days | 0 days (indefinite) |
| **Dependencies** | Node.js/Bun | None | TBD |
| **Functionality** | Full (vector search, auth) | Basic (keyword search) | Full (TBD) |
| **Maintenance** | Medium | Low | Low |
| **User Experience** | Best | Good | Best (eventually) |
| **Risk** | Medium (subprocess) | Low | High (timeline) |
| **Recommendation** | If ClawHub features critical | If simple needs | If patience |

---

## Recommendations

### Short-term: Keep Current Bundled Skills ✅

**Rationale**:
- 13 bundled skills cover core functionality
- 22 tools across sessions, memory, web, messaging, automation, media
- Fully tested and working
- No external dependencies

**Skills Currently Available**:

| Skill | Category | Functionality |
|-------|----------|---------------|
| `sessions` | Core | 6 session management tools |
| `memory` | Core | 2 memory/vector search tools |
| `web` | Core | 2 web search/fetch tools |
| `messaging` | Core | 1 message tool |
| `cron` | Automation | Scheduled tasks |
| `gateway` | Automation | Gateway control |
| `hooks` | Automation | Event hooks |
| `media` | Media | Image processing |
| `tts` | Media | Text-to-speech |
| `nodes` | System | Node management |
| `github` | Productivity | GitHub integration |
| `weather` | Productivity | Weather lookup |
| `web-search` | Productivity | Web search |

---

### Mid-term: Pivot to Higher Priority Items 🎯

Given that ClawHub integration requires significant adaptation and current skills are sufficient, consider prioritizing:

#### Phase 2: 国内生态适配 (China Ecosystem)

**Rationale**: Critical for China deployment
- Enterprise WeChat (企业微信) adapter
- DingTalk (钉钉) adapter
- Feishu (飞书) adapter
- Domestic LLM support (DeepSeek, Qwen, Kimi, GLM)

**Effort**: 2-3 weeks
**Value**: High (enables China market)

#### Phase 4: 企业安全增强 (Enterprise Security)

**Rationale**: Critical for enterprise deployment
- Session encryption (AES-256)
- Structured audit logs (JSONL)
- RBAC permissions model
- Multi-tenant isolation

**Effort**: 3-4 weeks
**Value**: High (enables enterprise sales)

---

### Long-term: Revisit ClawHub When Conditions Met 🔄

**Trigger conditions**:
1. Official Python SDK released
2. Stable HTTP REST API documented
3. ClawHub features become business-critical
4. Community demand increases

**Actions then**:
- Adapt existing API client code
- Implement Option A or B (depending on needs)
- Install high-priority skills
- Update documentation

---

## Phase 1.2 Completion Criteria

### What Was Achieved ✅

1. **Research Complete**:
   - ✅ ClawHub architecture fully understood
   - ✅ Official CLI tool discovered and analyzed
   - ✅ Skills repository structure mapped
   - ✅ Implementation options evaluated

2. **Documentation Updated**:
   - ✅ CLAWHUB_INTEGRATION.md updated with findings
   - ✅ Architecture diagrams added
   - ✅ Implementation options documented
   - ✅ This research summary created

3. **Code Ready for Future**:
   - ✅ ClawHub API client code complete (can be adapted)
   - ✅ Skills CLI commands implemented (can be adapted)
   - ✅ Unit tests passing (4/4)

### What Was Not Achieved ⏸️

1. **Skills Installation**: 0/12 OpenClaw skills installed
2. **ClawHub Integration**: API client needs adaptation to match real architecture
3. **Phase 1.2 Original Goals**: Paused pending decision

### Why Paused

**Technical Reasons**:
- ClawHub uses Convex backend (not REST API)
- Requires either Node.js/Bun dependency or GitHub fallback
- Significant architectural adaptation needed

**Strategic Reasons**:
- Current 13 bundled skills are sufficient for core functionality
- Higher priority items exist (国内生态, 企业安全)
- ClawHub integration can be deferred without impact

**Resource Reasons**:
- 3-5 days effort for full integration
- Better ROI on other priorities
- Can revisit when conditions improve

---

## Next Steps

### Immediate Actions

1. ✅ **Update WORK_LOG.md** with Phase 1.2 findings
2. ✅ **Update NEXT_SESSION_GUIDE.md** for Phase 2 or Phase 4
3. ⏭️ **User Decision**: Choose next phase
   - Option A: Phase 2 (国内生态适配)
   - Option B: Phase 4 (企业安全增强)
   - Option C: Continue Phase 1.2 (pick implementation option)

### If Continuing Phase 1.2

**Option B (GitHub Fallback) - Recommended**:
- Day 1: Implement GitHub API client
- Day 2: Add search and download functionality
- Day 3: Testing and documentation
- Total: 2-3 days

**Option A (CLI Wrapper) - If Full Features Needed**:
- Day 1: Node.js/Bun detection and installation
- Day 2-3: Subprocess wrapper implementation
- Day 4: Error handling and logging
- Day 5: Cross-platform testing
- Total: 3-5 days

### If Pivoting to Phase 2 or 4

See respective planning documents:
- `docs/design/OPENCLAW_ALIGNMENT_PLAN.md` - Phases 2-5
- `docs/design/COMPARISON_ANALYSIS.md` - Strategic analysis

---

## Appendix: Code Statistics

### Phase 1.1 Deliverables

| File | Lines | Status |
|------|-------|--------|
| `src/lurkbot/skills/clawhub.py` | 311 | ✅ Complete |
| `src/lurkbot/cli/skills.py` | 321 | ✅ Complete |
| `src/lurkbot/skills/registry.py` | +114 | ✅ Complete |
| `tests/test_skills_clawhub.py` | 56 | ✅ 4/4 passing |
| `docs/main/CLAWHUB_INTEGRATION.md` | 417 → 600+ | ✅ Updated |
| `docs/main/PHASE_1_1_SUMMARY.md` | 158 | ✅ Complete |
| **Total** | **~1,400 lines** | **Ready for adaptation** |

### Test Results

```bash
$ pytest tests/test_skills_clawhub.py -xvs

tests/test_skills_clawhub.py::test_clawhub_client_init PASSED
tests/test_skills_clawhub.py::test_search PASSED
tests/test_skills_clawhub.py::test_info PASSED
tests/test_skills_clawhub.py::test_download PASSED

============================== 4 passed, 1 warning in 0.15s ==============================
```

---

## References

- [ClawHub Website](https://clawhub.com)
- [ClawHub Repository](https://github.com/openclaw/clawhub)
- [Skills Archive](https://github.com/openclaw/skills)
- [OpenClaw Documentation](https://docs.openclaw.ai/tools/skills)
- [Phase 1.1 Summary](./PHASE_1_1_SUMMARY.md)
- [Implementation Plan](./IMPLEMENTATION_PLAN.md)
- [Comparison Analysis](../design/COMPARISON_ANALYSIS.md)

---

**Document Status**: Complete
**Author**: Claude Sonnet 4.5
**Date**: 2026-01-31
**Phase**: 1.2 Research (Paused)
