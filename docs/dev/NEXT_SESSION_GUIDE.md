# Next Session Guide

## Session Context

**Last Session Date**: 2026-01-28
**Phase Completed**: Phase 2 - Tool System (90% complete)
**Status**: ✅ Core Tool System Implemented

## What Was Accomplished

### Phase 2: Tool System Implementation ✅

**1. Tool Infrastructure** ✅
- Created `tools/base.py` with Tool, ToolPolicy, SessionType, ToolResult
- Created `tools/registry.py` for tool registration and policy enforcement
- 10 infrastructure tests passing

**2. Built-in Tools** ✅
- `BashTool`: Execute shell commands with timeout protection (8 tests)
- `ReadFileTool`: Read files with path traversal protection (7 tests)
- `WriteFileTool`: Write files with directory creation (7 tests)
- All security measures implemented

**3. Agent Integration** ✅
- Modified `agents/base.py` to add SessionType to AgentContext
- Modified `agents/runtime.py` to integrate ToolRegistry
- Implemented tool calling loop in ClaudeAgent.chat()
- Used Context7 to query Anthropic API documentation
- All 41 tests passing (32 tool tests + 9 existing tests)

**4. Testing** ✅
- Comprehensive unit tests for all tools
- Integration test script (`tests/integration_test_tools.py`)
- Path traversal attack prevention verified
- Timeout protection verified

### Test Coverage
- Total tests: 41/41 passing ✅
- Tool system tests: 32 tests
- Integration tests: Manual verification ✅

## Next Phase Priorities

### Phase 2 Completion (10% remaining)

**Objective**: Complete end-to-end testing with real Claude API

#### Tasks:
1. **E2E Test with Claude API** (High Priority)
   - Create test script that calls AgentRuntime with real API
   - Test tool calling with actual Claude responses
   - Verify tool execution loop works correctly
   - **Requires**: ANTHROPIC_API_KEY environment variable

2. **Documentation Updates** (Medium Priority)
   - Update `docs/design/ARCHITECTURE_DESIGN.md` with tool system architecture
   - Add tool system section with architecture diagram
   - Document tool calling flow

### Phase 3: Sandbox & Advanced Tools (Next Priority)

**Objective**: Docker container isolation for untrusted sessions and browser automation

#### Tasks:
1. **Docker Sandbox** (`src/lurkbot/sandbox/docker.py`)
   - Docker container management for GROUP/TOPIC sessions
   - Workspace mounting (read-only)
   - Resource limits (memory, CPU, timeout)
   - Tool execution in isolated environment

2. **Browser Tool** (`src/lurkbot/tools/builtin/browser.py`)
   - Playwright integration
   - Navigate, screenshot, extract text
   - Safe browsing in sandbox

3. **Tool Approval Workflow** (`src/lurkbot/tools/approval.py`)
   - Store pending tool approvals
   - Notify user via channel
   - Handle approval/denial responses

#### Reference Files:
- Original moltbot: `github.com/moltbot/src/agents/tools/`
- Design doc: `docs/design/MOLTBOT_ANALYSIS.md` (Section: Tool System)

### Phase 4: Session Persistence (Medium Priority)

**Objective**: Persist conversation history and session state

#### Tasks:
1. **Session Store** (`src/lurkbot/storage/jsonl.py`)
   - JSONL format storage
   - Session loading/saving
   - History management

2. **Storage Location**
   - Default: `~/.lurkbot/sessions/`
   - Configurable via settings

#### Reference:
- Original format: `~/.clawdbot/sessions/{session_id}.jsonl`
- Design doc: `docs/design/MOLTBOT_ANALYSIS.md` (Section: Session Persistence)

## Known Issues & Limitations

### Current Limitations
1. **No Tool System**: Agents cannot execute tools yet
2. **No Persistence**: Sessions lost on restart
3. **Single Channel**: Only Telegram implemented
4. **No Sandbox**: Tool execution not isolated
5. **Limited Testing**: Need integration tests

### Technical Debt
- [ ] Add type hints to all functions
- [ ] Add docstrings to all public APIs
- [ ] Implement proper error handling with custom exceptions
- [ ] Add logging throughout the codebase
- [ ] Create integration tests for Gateway + Agent + Channel

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

### Configuration
- Settings loaded from environment variables: `LURKBOT_*`
- Nested settings use `__`: `LURKBOT_GATEWAY__PORT=8080`
- API keys: `LURKBOT_ANTHROPIC_API_KEY`, `LURKBOT_OPENAI_API_KEY`

### Git Workflow
- Check status: `git status -sb`
- Stage changes: `git add <files>`
- Commit: `git commit -m "message"`
- **Note**: Never auto-commit without explicit user instruction

## Quick Start Commands

```bash
# Install dependencies
make dev

# Run tests
make test

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

## Success Criteria for Next Phase

- [ ] Tool registry implemented and tested
- [ ] At least 3 built-in tools working (bash, read, write)
- [ ] Agent can call tools and process results
- [ ] Docker sandbox isolation working
- [ ] Integration tests for tool execution
- [ ] Documentation updated with tool usage examples

---

**Document Updated**: 2026-01-28
**Next Review**: Start of next session
