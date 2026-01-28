# Next Session Guide

## Session Context

**Last Session Date**: 2026-01-29 (续)
**Phase Completed**: Phase 3 - Sandbox & Advanced Tools (85% complete)
**Status**: ✅ Tool Approval System + Bash Sandbox Integration

## What Was Accomplished

### Phase 3: Sandbox & Advanced Tools (85% complete)

**Previous Session (70%)**:
- ✅ Docker Sandbox Infrastructure
- ✅ Browser Tool (Playwright)

**Current Session (+15%)**:

**1. Tool Approval Workflow** ✅
- Created `tools/approval.py` module with complete approval lifecycle
- `ApprovalManager`: Async approval handling with timeout
- `ApprovalRequest`: Request data model (tool, command, session)
- `ApprovalRecord`: Complete approval record with timestamps
- `ApprovalDecision`: Enum (APPROVE/DENY/TIMEOUT)
- **Features**:
  - Async waiting with `wait_for_decision()`
  - Timeout auto-deny (default: 5 minutes)
  - Real-time resolution via `resolve()`
  - Snapshot queries with `get_snapshot()`
  - Pending list with `get_all_pending()`
- **Tests**: 19 approval tests, all passing

**2. Bash Tool Sandbox Integration** ✅
- Modified `tools/builtin/bash.py` to use sandbox
- Session-based execution strategy:
  - MAIN: Direct subprocess execution
  - GROUP/TOPIC: Docker sandbox execution
- Fixed circular import (TYPE_CHECKING + lazy import)
- **Policy Update**:
  - Allowed sessions: MAIN + GROUP + TOPIC
  - Still requires approval for all sessions
- **Tests**: 7 sandbox integration tests (1 policy + 6 Docker-gated)

**3. Test Coverage** ✅
- **Total tests**: 87 tests (70 passed, 17 skipped)
  - Approval: 19 ✅
  - Bash Sandbox: 1 ✅ (6 Docker tests skipped)
  - Existing: 50 ✅
- **Test Commands**:
  ```bash
  make test                    # Core tests (70 passed)
  pytest --docker             # With Docker tests
  pytest tests/test_approval.py -xvs  # Approval tests only
  ```

## Next Phase Priorities

### Phase 3 Completion (15% remaining)

**Objective**: Integrate approval system into Agent Runtime and Channels

#### Tasks:
1. **Integrate Approval into Agent Runtime** (High Priority) - **未完成**
   - Check if tool requires approval before execution
   - Create approval request via ApprovalManager
   - Wait for user decision
   - Handle timeout (auto-deny)
   - Execute tool only after approval
   - **Design**:
     - Add `approval_manager` to AgentRuntime
     - Check `tool.policy.requires_approval`
     - For GROUP/TOPIC: always require approval for dangerous tools
     - For MAIN: optional approval (configurable)

2. **Channel Notification System** (High Priority) - **未完成**
   - Send approval request via Channel (Telegram, etc.)
   - Format notification with command, session, security context
   - Parse user response (approve/deny)
   - Call `approval_manager.resolve()` with user decision
   - **Message Format**:
     ```
     🔒 Tool Approval Required
     Tool: bash
     Command: rm -rf /tmp/test
     Session: GROUP @example_group
     Security: Sandbox enabled

     Reply: /approve {id} or /deny {id}
     Expires in: 5 minutes
     ```

3. **E2E Integration Tests** (Medium Priority)
   - Gateway + Agent + Tool + Approval flow
   - Test approval timeout
   - Test sandbox execution after approval
   - Mock Channel responses

#### Dependencies:
- `AgentRuntime` needs to be functional
- `Channel` system needs message sending capability
- Gateway needs to route approval responses

#### Reference Files:
- Original moltbot: `github.com/moltbot/src/agents/tools/`
- Approval docs: `github.com/moltbot/docs/tools/exec-approvals.md`
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
2. ✅ ~~No Sandbox~~ - **SOLVED** (Phase 3)
3. ✅ ~~No Tool Approval~~ - **PARTIALLY SOLVED** (Phase 3, 85%)
   - ⚠️ Approval manager implemented
   - ⚠️ Bash tool integrated with sandbox
   - ❌ Not integrated into Agent Runtime yet
   - ❌ No Channel notification system
4. ⚠️ **No Persistence** - Sessions lost on restart
5. ⚠️ **Single Channel** - Only Telegram implemented
6. ⚠️ **Limited Testing** - Need E2E integration tests

### Technical Debt
- [ ] Add type hints to all functions (mostly done, need review)
- [ ] Add docstrings to all public APIs (partially done)
- [ ] Implement proper error handling with custom exceptions
- [x] Add logging throughout the codebase (using loguru)
- [ ] Create integration tests for Gateway + Agent + Channel + Approval
- [ ] E2E test with real Claude API (requires ANTHROPIC_API_KEY)
- [ ] Update architecture documentation with Phase 3 approval changes

### Security Notes
- Docker sandbox is **production-ready** for GROUP/TOPIC sessions
- Browser tool should **only run in MAIN/DM** sessions (no sandbox support yet)
- Path traversal protection in File tools (Read/Write)
- Timeout protection in all tools
- **Approval system implemented but not enforced yet** (needs Agent Runtime integration)

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
