# Next Session Guide

## Session Context

**Last Session Date**: 2026-01-28
**Phase Completed**: Project Initialization
**Status**: ✅ Foundation Complete

## What Was Accomplished

### 1. Project Structure ✅
- Created complete Python project structure with `uv` package manager
- Implemented core modules: gateway, agents, channels, config, cli, utils
- Set up development tooling: Makefile, pyproject.toml, .gitignore
- All tests passing (9/9)

### 2. Core Implementations ✅

**Gateway Module** (`src/lurkbot/gateway/`):
- WebSocket server using FastAPI
- Protocol definitions (Message types, RPC framework)
- Connection management

**Agent Module** (`src/lurkbot/agents/`):
- Base Agent class with abstract methods
- Claude integration (streaming support)
- Session management
- AgentRuntime for session lifecycle

**Channel Module** (`src/lurkbot/channels/`):
- Base Channel abstraction
- Telegram adapter (python-telegram-bot)

**Config Module** (`src/lurkbot/config/`):
- Pydantic Settings-based configuration
- Environment variable support
- Nested configuration structure

**CLI Module** (`src/lurkbot/cli/`):
- Typer-based command-line interface
- Commands: gateway, channels, config
- Rich terminal output

### 3. Documentation ✅

**Design Documents** (bilingual):
- `ARCHITECTURE_DESIGN.md` / `.zh.md` - System architecture
- `MOLTBOT_ANALYSIS.md` / `.zh.md` - Original project in-depth analysis
- `WORK_LOG.md` - Development log (Chinese)

**Project Documents**:
- `README.md` - Project overview (English)
- `CLAUDE.md` - Project instructions for Claude (English)

## Current State

### Working Features
- ✅ Configuration loading (env vars + settings)
- ✅ Gateway WebSocket server
- ✅ Claude agent (chat + streaming)
- ✅ Telegram channel adapter
- ✅ Basic CLI commands

### Test Coverage
- Config tests: 3/3 passing
- Protocol tests: 6/6 passing
- Total: 9/9 passing

## Next Phase Priorities

### Phase 2: Tool System Implementation (High Priority)

**Objective**: Implement the tool execution framework to enable AI agents to perform actions.

#### Tasks:
1. **Tool Registry** (`src/lurkbot/tools/registry.py`)
   - Tool registration and discovery
   - Tool policy enforcement
   - Execution context management

2. **Built-in Tools**
   - `bash.py` - Shell command execution
   - `read.py` / `write.py` / `edit.py` - File operations
   - `browser.py` - Browser automation (Playwright)

3. **Sandbox System** (`src/lurkbot/tools/sandbox.py`)
   - Docker container management
   - Workspace mounting
   - Resource limits
   - Security isolation

4. **Agent Tool Integration**
   - Update Agent base class to support tool calls
   - Implement tool call parsing from Claude responses
   - Tool execution loop

#### Reference Files:
- Original moltbot: `github.com/moltbot/src/agents/tools/`
- Design doc: `docs/design/MOLTBOT_ANALYSIS.md` (Section: Agent Module - Tool System)

### Phase 3: Additional Channels (Medium Priority)

**Objective**: Expand channel support beyond Telegram.

#### Tasks:
1. **Discord Channel** (`src/lurkbot/channels/discord.py`)
   - discord.py integration
   - Mention gating
   - Guild/channel permissions

2. **Slack Channel** (`src/lurkbot/channels/slack.py`)
   - slack-sdk integration
   - Socket Mode support
   - Thread handling

#### Reference Files:
- Original moltbot: `github.com/moltbot/src/discord/`, `src/slack/`
- Design doc: `docs/design/MOLTBOT_ANALYSIS.md` (Section: Channel Module)

### Phase 4: Session Persistence (Medium Priority)

**Objective**: Persist conversation history and session state.

#### Tasks:
1. **Session Store** (`src/lurkbot/agents/session_store.py`)
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
