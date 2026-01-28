# Next Session Guide

## Session Context

**Last Session Date**: 2026-01-29
**Current Status**: Phase 4 完成，Phase 5 准备开始
**Design Document**: `docs/design/LURKBOT_COMPLETE_DESIGN.md`

## What Was Accomplished

### Phase 4: 九层工具策略系统 ✅

完成了 MoltBot 九层工具策略系统的完整复刻：

**创建文件**:
- `src/lurkbot/tools/policy.py`: 九层工具策略系统（~750 行）
- `tests/test_tool_policy.py`: 99 个测试

**核心功能**:
- `ToolProfileId` 枚举（minimal/coding/messaging/full）
- `TOOL_GROUPS` 11 个工具组定义
- `DEFAULT_SUBAGENT_TOOL_DENY` 子代理禁用列表
- `filter_tools_nine_layers()` 九层过滤主函数
- 模式匹配（支持 * 通配符）
- Deny 优先规则
- alsoAllow 支持

**测试结果**:
```
198 passed in 0.31s
```

## Implementation Plan (10 Phases)

| Phase | 内容 | 状态 |
|-------|------|------|
| **Phase 1** | 项目重构 - 清理旧代码，搭建新目录结构 | ✅ 完成 |
| **Phase 2** | PydanticAI 核心框架集成 | ✅ 完成 |
| **Phase 3** | Bootstrap 文件系统 + 系统提示词生成器 | ✅ 完成 |
| **Phase 4** | 九层工具策略系统 | ✅ 完成 |
| **Phase 5** | 22 个原生工具实现 | 🔄 下一步 |
| **Phase 6** | 会话管理 + 子代理系统 | ⏳ 待开始 |
| **Phase 7** | Heartbeat + Cron 自主运行系统 | ⏳ 待开始 |
| **Phase 8** | Auth Profile + Context Compaction | ⏳ 待开始 |
| **Phase 9** | Gateway WebSocket 协议 | ⏳ 待开始 |
| **Phase 10** | 技能和插件系统 | ⏳ 待开始 |

## Task Status

```
#6  [completed]  Phase 1: 项目重构 ✅
#1  [completed]  Phase 2: PydanticAI 核心框架集成 ✅
#3  [completed]  Phase 3: Bootstrap 文件系统 ✅
#8  [completed]  Phase 3: 系统提示词生成器 ✅
#2  [completed]  Phase 4: 九层工具策略系统 ✅
#5  [pending]    Phase 5: 22个原生工具实现 ← 下一步
#4  [pending]    Phase 6: 会话管理 + 子代理系统 [blocked by #5]
#7  [pending]    Phase 7: Heartbeat + Cron 自主运行系统 [blocked by #4]
#9  [pending]    Phase 8: Auth Profile + Context Compaction
#10 [pending]    Phase 9: Gateway WebSocket 协议 [blocked by #4]
#11 [pending]    Phase 10: 技能和插件系统 [blocked by #10]
```

## Key References

### Design Documents
- **完整设计方案**: `docs/design/LURKBOT_COMPLETE_DESIGN.md` (v2.0)
- **架构分析**: `docs/design/MOLTBOT_COMPLETE_ARCHITECTURE.md`
- **中文架构分析**: `docs/design/MOLTBOT_ANALYSIS.zh.md`

### MoltBot Source Code
- **位置**: `./github.com/moltbot/`
- **核心模块**: `src/agents/`, `src/gateway/`, `src/tools/`
- **关键文件**:
  - `src/agents/system-prompt.ts` - 系统提示词生成 (592 行, 23 节)
  - `src/agents/tool-policy.ts` - 工具策略定义
  - `src/agents/pi-tools.policy.ts` - 工具过滤实现
  - `src/agents/bootstrap.ts` - Bootstrap 加载 (8 文件)
  - `src/infra/heartbeat-runner.ts` - 心跳系统
  - `src/agents/compaction.ts` - 上下文压缩

### PydanticAI Reference
- **Context7 ID**: `/pydantic/pydantic-ai`
- **关键功能**: Agent, @agent.tool, DeferredToolRequests, run_stream_events()

## Next Phase: Phase 5 - 22 个原生工具实现

### 工具清单

| 工具分类 | 工具名称 | 优先级 |
|----------|----------|--------|
| **文件系统** | read, write, edit, apply_patch | P0 |
| **执行** | exec, process | P0 |
| **会话管理** | sessions_list, sessions_history, sessions_send, sessions_spawn, session_status, agents_list | P1 |
| **内存** | memory_search, memory_get | P1 |
| **Web** | web_search, web_fetch | P1 |
| **UI** | browser, canvas | P2 |
| **自动化** | cron, gateway | P2 |
| **消息** | message | P1 |
| **其他** | image, nodes, tts | P2 |

### 实现策略

1. **先实现 P0 工具**（文件系统、执行）- 这些是代码生成的基础
2. **然后实现 P1 工具**（会话、内存、Web、消息）- 核心交互功能
3. **最后实现 P2 工具**（UI、自动化、其他）- 高级功能

### MoltBot 工具源码位置

```
github.com/moltbot/src/tools/
├── fs/             # read, write, edit, apply_patch
├── exec/           # exec, process
├── sessions/       # sessions_* 工具
├── memory/         # memory_search, memory_get
├── web/            # web_search, web_fetch
├── browser/        # browser
├── canvas/         # canvas
├── cron/           # cron
├── gateway/        # gateway
├── message/        # message
├── image/          # image
├── nodes/          # nodes
└── tts/            # tts
```

### 工具接口规范

每个工具需要实现：
1. **工具 schema** - PydanticAI @agent.tool 装饰器兼容
2. **执行函数** - 异步执行逻辑
3. **错误处理** - 统一错误格式
4. **测试用例** - 单元测试覆盖

## Important Notes

### 开发原则
1. **完全复刻**: 所有 MoltBot 功能必须实现，不能遗漏
2. **严格对标**: 时刻参考 MoltBot 源码确保一致性
3. **不自行乱编**: prompts 等关键内容必须从 MoltBot 源码提取
4. **有不明之处及时停下来问**: 遇到不确定的地方要确认

### 技术栈
- **Agent 框架**: PydanticAI
- **Web 框架**: FastAPI
- **验证**: Pydantic
- **CLI**: Typer
- **日志**: Loguru

### 已实现的关键常量

```python
# Bootstrap (lurkbot.agents.bootstrap)
BOOTSTRAP_FILES = ["SOUL.md", "IDENTITY.md", "USER.md", "AGENTS.md",
                   "TOOLS.md", "HEARTBEAT.md", "MEMORY.md", "BOOTSTRAP.md"]
SUBAGENT_BOOTSTRAP_ALLOWLIST = {"AGENTS.md", "TOOLS.md"}
DEFAULT_BOOTSTRAP_MAX_CHARS = 20000

# System Prompt (lurkbot.agents.system_prompt)
SILENT_REPLY_TOKEN = "NO_REPLY"
HEARTBEAT_TOKEN = "HEARTBEAT_OK"

# Tool Policy (lurkbot.tools.policy)
ToolProfileId = Enum("minimal", "coding", "messaging", "full")
TOOL_GROUPS = {"group:memory", "group:web", "group:fs", ...}
DEFAULT_SUBAGENT_TOOL_DENY = ["sessions_spawn", "gateway", "cron", ...]
```

## Quick Start for Next Session

```bash
# 1. 查看任务状态
# Claude Code 中使用 TaskList 命令

# 2. 运行测试确认当前状态
python -m pytest tests/ -xvs

# 3. 开始 Phase 5: 22 个原生工具实现
# 先从 P0 工具（文件系统、执行）开始

# 4. 查询 PydanticAI 文档（如需要）
# 使用 Context7 MCP: resolve-library-id + query-docs
```

---

**Document Updated**: 2026-01-29
**Next Action**: 开始 Phase 5 - 从 P0 工具（read, write, edit, apply_patch, exec, process）开始
