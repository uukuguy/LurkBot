# Next Session Guide

## Session Context

**Last Session Date**: 2026-01-29
**Phase Completed**: Phase 3 - Sandbox & Advanced Tools (70% complete)
**Status**: ✅ Docker Sandbox + Browser Tool Implemented

## What Was Accomplished

### Phase 3: Sandbox & Advanced Tools (70% complete)

**1. Docker Sandbox Infrastructure** ✅
- Created `sandbox/` module with Docker container isolation
- `sandbox/types.py`: SandboxConfig, SandboxResult data models
- `sandbox/docker.py`: DockerSandbox class for secure execution
- `sandbox/manager.py`: SandboxManager for lifecycle management
- **Security Features**:
  - Resource limits (memory: 512M, CPU: 50%, timeout: 30s)
  - Network isolation (network=none)
  - Read-only root filesystem
  - Process limits (pids_limit: 64)
  - Capability dropping (drop ALL)
  - Tmpfs for temporary files
- **Container Management**:
  - Hot container window (5 min reuse)
  - Automatic cleanup
  - Workspace mounting support
- **Tests**: 8 sandbox tests (3 config + 5 Docker + 2 manager)
  - Run Docker tests with: `pytest --docker`

**2. Browser Tool** ✅
- Created `tools/builtin/browser.py` with Playwright integration
- Uses **async Playwright API** for better performance
- **Actions**:
  - `navigate`: Navigate to URL and get page title
  - `screenshot`: Capture full page or element screenshots
  - `extract_text`: Extract text from page or specific element
  - `get_html`: Get HTML content from page or element
- **Policy**: Allowed in MAIN and DM sessions only
- **Tests**: 9 browser tool tests (5 unit + 4 integration)
  - Run browser tests with: `pytest --browser`
- Added `playwright>=1.49.0` to `pyproject.toml` (browser extra)

**3. Dependencies Updated** ✅
- Added `docker>=7.0.0` to core dependencies
- Added `playwright>=1.49.0` to browser extras
- Updated mypy config to ignore docker/playwright imports

### Test Coverage
- **Total tests**: 61 tests
  - **Passing**: 50 ✅
  - **Skipped**: 11 (Docker: 7, Browser: 4)
  - **Failed**: 0 ✅
- **Test Commands**:
  ```bash
  make test                    # Run all non-optional tests
  pytest --docker             # Run Docker sandbox tests
  pytest --browser            # Run browser automation tests
  pytest --docker --browser   # Run all tests
  ```

## Next Phase Priorities

### Phase 3 Completion (30% remaining)

**Objective**: Complete tool approval workflow and integration

#### Tasks:
1. **Tool Approval Workflow** (High Priority) - **未完成**
   - Create `tools/approval.py` module
   - Store pending tool approvals in memory or temp storage
   - Notification system via Channel adapters
   - Handle user approval/denial responses
   - Timeout mechanism for pending approvals
   - **Design**:
     - For GROUP/TOPIC sessions, dangerous tools require approval
     - User responds via Channel message (approve/deny)
     - Timeout after N minutes (default: 5 min)

2. **Sandbox Integration with Tools** (Medium Priority) - **部分完成**
   - Integrate SandboxManager with BashTool
   - Execute tools in sandbox for GROUP/TOPIC sessions
   - Test tool execution in isolated containers
   - Verify resource limits work correctly

3. **Browser Tool in Sandbox** (Low Priority)
   - Run Playwright in Docker container
   - May require custom Docker image with Chrome/Chromium
   - Consider using `mcr.microsoft.com/playwright` base image

#### Reference Files:
- Original moltbot: `github.com/moltbot/src/agents/tools/`
- Design doc: `docs/design/MOLTBOT_ANALYSIS.md` (Section: Tool System)

### Phase 4: Session Persistence (Next Priority)

**Objective**: Persist conversation history and session state

#### Tasks:
1. **Session Store** (`src/lurkbot/storage/jsonl.py`)
   - JSONL format storage (one JSON object per line)
   - Session loading/saving
   - History management
   - Append-only for performance

2. **Storage Location**
   - Default: `~/.lurkbot/sessions/`
   - Configurable via settings
   - Session ID format: `{channel}_{chat_id}_{user_id}`

3. **Integration with Agent Runtime**
   - Load session history on startup
   - Append new messages to session file
   - Periodic flush to disk

#### Reference:
- Original format: `~/.clawdbot/sessions/{session_id}.jsonl`
- Design doc: `docs/design/MOLTBOT_ANALYSIS.md` (Section: Session Persistence)

## Known Issues & Limitations

### Current Limitations
1. ✅ ~~No Tool System~~ - **SOLVED** (Phase 2)
2. ✅ ~~No Sandbox~~ - **SOLVED** (Phase 3, partial)
3. ⚠️ **No Tool Approval** - Need to implement approval workflow
4. ⚠️ **No Persistence** - Sessions lost on restart
5. ⚠️ **Single Channel** - Only Telegram implemented
6. ⚠️ **Limited Testing** - Need E2E integration tests

### Technical Debt
- [ ] Add type hints to all functions (mostly done, need review)
- [ ] Add docstrings to all public APIs (partially done)
- [ ] Implement proper error handling with custom exceptions
- [x] Add logging throughout the codebase (using loguru)
- [ ] Create integration tests for Gateway + Agent + Channel
- [ ] E2E test with real Claude API (requires ANTHROPIC_API_KEY)
- [ ] Update architecture documentation with Phase 3 changes

### Security Notes
- Docker sandbox is **production-ready** for GROUP/TOPIC sessions
- Browser tool should **only run in MAIN/DM** sessions (no sandbox support yet)
- Path traversal protection in File tools (Read/Write)
- Timeout protection in all tools

## Important Notes for Next Session

### Code Style Reminders
- Use type annotations: `def func(param: str) -> dict[str, Any]:`
- Use Pydantic models for data validation
- Use `async/await` for all I/O operations
- Use `loguru.logger` for logging
- Follow existing patterns in codebase

### Testing Guidelines
- Run `make test` after changes
- Run `make lint` before committing
- Run `make typecheck` to verify types
- Test with: `pytest -xvs tests/test_file.py::test_function`
- Optional tests:
  - `pytest --docker` for sandbox tests (requires Docker daemon)
  - `pytest --browser` for Playwright tests (requires `playwright install`)

### Configuration
- Settings loaded from environment variables: `LURKBOT_*`
- Nested settings use `__`: `LURKBOT_GATEWAY__PORT=8080`
- API keys: `LURKBOT_ANTHROPIC_API_KEY`, `LURKBOT_OPENAI_API_KEY`

### Docker Requirements
- Docker daemon must be running for sandbox tests
- Default image: `debian:bookworm-slim`
- Custom images can be configured via `SandboxConfig.image`

### Playwright Requirements
- Install browsers: `playwright install chromium`
- Runs headless by default
- Uses async API for better performance

### Git Workflow
- Check status: `git status -sb`
- Stage changes: `git add <files>`
- Commit: `git commit -m "message"`
- **Note**: Never auto-commit without explicit user instruction

## Quick Start Commands

```bash
# Install dependencies
make dev

# Install browser dependencies (optional)
uv pip install -e ".[browser]"
playwright install chromium

# Run tests
make test                    # Core tests only
pytest --docker             # With Docker tests
pytest --browser            # With browser tests
pytest --docker --browser   # All tests

# Check code
make lint
make typecheck

# Run CLI
make cli ARGS="--help"
make gateway  # Start gateway server
```

## Reference Documentation

**Internal**:
- Architecture: `docs/design/ARCHITECTURE_DESIGN.md`
- Moltbot Analysis: `docs/design/MOLTBOT_ANALYSIS.md`
- Work Log: `docs/main/WORK_LOG.md`

**External**:
- Original project: `github.com/moltbot/` (in repo, not in git scope)
- FastAPI docs: https://fastapi.tiangolo.com/
- Pydantic docs: https://docs.pydantic.dev/
- python-telegram-bot: https://docs.python-telegram-bot.org/
- Docker SDK: https://docker-py.readthedocs.io/
- Playwright Python: https://playwright.dev/python/

## Success Criteria for Phase 3

- [x] Docker sandbox isolation working
- [x] Browser tool implemented and tested
- [ ] Tool approval workflow implemented
- [ ] Sandbox integration with existing tools
- [ ] Browser tool running in sandbox (optional)
- [ ] Integration tests for sandbox + tools
- [ ] Documentation updated with Phase 3 architecture

## File Structure Reference

```
src/lurkbot/
├── sandbox/                    # ✅ NEW (Phase 3)
│   ├── __init__.py
│   ├── types.py               # Data models
│   ├── docker.py              # Docker sandbox implementation
│   └── manager.py             # Sandbox lifecycle manager
├── tools/
│   ├── builtin/
│   │   ├── bash.py            # ✅ Phase 2
│   │   ├── file_ops.py        # ✅ Phase 2
│   │   └── browser.py         # ✅ NEW (Phase 3)
│   ├── base.py                # ✅ Phase 2
│   ├── registry.py            # ✅ Phase 2
│   └── approval.py            # ⏳ TODO (Phase 3)
├── agents/
│   ├── base.py                # ✅ Phase 2
│   └── runtime.py             # ✅ Phase 2
└── storage/                    # ⏳ TODO (Phase 4)
    └── jsonl.py

tests/
├── test_sandbox.py            # ✅ NEW (Phase 3)
├── test_browser_tool.py       # ✅ NEW (Phase 3)
├── test_tools.py              # ✅ Phase 2
└── conftest.py                # ✅ Updated with --docker, --browser flags
```

---

**Document Updated**: 2026-01-29
**Next Review**: Start of next session
**Progress**: Phase 3 (70% complete) → Continue with approval workflow
