# Next Session Guide

## Session Context

**Last Session Date**: 2026-01-29
**Current Status**: Phase 7 完成，Phase 5-7 全部完成
**Design Document**: `docs/design/LURKBOT_COMPLETE_DESIGN.md` (v2.3)
**Architecture Document**: `docs/design/MOLTBOT_COMPLETE_ARCHITECTURE.md` (v3.0, 32 章节)

## What Was Accomplished

### 今日完成的工作

1. **Phase 7 Heartbeat + Cron 自主运行系统** - 全部完成：

   | 组件 | 文件 | 状态 |
   |------|------|------|
   | HeartbeatConfig | `autonomous/heartbeat/__init__.py` | ✅ 完成 |
   | HeartbeatEventPayload | `autonomous/heartbeat/__init__.py` | ✅ 完成 |
   | HeartbeatRunner | `autonomous/heartbeat/__init__.py` | ✅ 完成 |
   | ActiveHours | `autonomous/heartbeat/__init__.py` | ✅ 完成 |
   | CronSchedule (at/every/cron) | `autonomous/cron/__init__.py` | ✅ 完成 |
   | CronPayload (systemEvent/agentTurn) | `autonomous/cron/__init__.py` | ✅ 完成 |
   | CronJob | `autonomous/cron/__init__.py` | ✅ 完成 |
   | CronService | `autonomous/cron/__init__.py` | ✅ 完成 |
   | 单元测试 | `tests/main/test_phase7_autonomous.py` | ✅ 通过 (40 tests) |

2. **Heartbeat 系统功能**:
   - 周期性心跳检查 (configurable interval)
   - 活动时间窗口支持 (active hours)
   - HEARTBEAT_OK token 处理 (静默确认)
   - 24 小时内重复消息抑制
   - 事件发射和监听器系统
   - HEARTBEAT.md 文件读取

3. **Cron 系统功能**:
   - 三种调度类型: at (单次), every (周期), cron (表达式)
   - 两种 Payload 类型: systemEvent (轻量级), agentTurn (重量级)
   - Job CRUD 操作: add, update, remove, list, get
   - 执行控制: run (due/force), wake
   - JSONL 持久化存储
   - 调度循环 (scheduler loop)

## Implementation Plan (23 Phases)

| Phase | 内容 | 状态 |
|-------|------|------|
| **Phase 1** | 项目重构 - 清理旧代码 | ✅ 完成 |
| **Phase 2** | PydanticAI 核心框架集成 | ✅ 完成 |
| **Phase 3** | Bootstrap 文件系统 + 系统提示词 | ✅ 完成 |
| **Phase 4** | 九层工具策略系统 | ✅ 完成 |
| **Phase 5** | 22 个原生工具实现 | ✅ 完成 |
| **Phase 6** | 会话管理 + 子代理系统 | ✅ 完成 |
| **Phase 7** | Heartbeat + Cron 自主运行系统 | ✅ 完成 |
| **Phase 8** | Auth Profile + Context Compaction | ⏳ 待开始 |
| **Phase 9** | Gateway WebSocket 协议 | ⏳ 待开始 |
| **Phase 10** | 技能和插件系统 | ⏳ 待开始 |
| **Phase 11** | A2UI Canvas Host | ⏳ 待开始 |
| **Phase 12** | Auto-Reply + Routing | ⏳ 待开始 |
| **Phase 13** | Daemon 守护进程 | ⏳ 待开始 |
| **Phase 14** | Media Understanding | ⏳ 待开始 |
| **Phase 15** | Provider Usage 监控 | ⏳ 待开始 |
| **Phase 16** | Hooks 扩展系统 | ⏳ 待开始 |
| **Phase 17** | Security 安全审计 | ⏳ 待开始 |
| **Phase 18** | ACP 协议系统 | ⏳ 待开始 |
| **Phase 19** | Browser 浏览器自动化 | ⏳ 待开始 |
| **Phase 20** | TUI 终端界面 | ⏳ 待开始 |
| **Phase 21** | TTS 语音合成 | ⏳ 待开始 |
| **Phase 22** | Wizard 配置向导 | ⏳ 待开始 |
| **Phase 23** | Infra 基础设施 | ⏳ 待开始 |

## Quick Start for Next Session

```bash
# 1. 运行测试确认当前状态
python -m pytest tests/main/ -xvs

# 2. 验证 autonomous 模块
python -c "from lurkbot.autonomous import HeartbeatRunner, CronService; print('OK')"

# 3. 选择下一步方向：
# 方案 A: 开始 Phase 8 - Auth Profile + Context Compaction
# 方案 B: 开始 Phase 9 - Gateway WebSocket 协议
# 方案 C: 跳到 Phase 12 - Auto-Reply 系统（消息处理核心）
```

## 新增模块结构

### Phase 7 完成的目录结构
```
src/lurkbot/
├── autonomous/                  # Phase 7 [新增/更新]
│   ├── __init__.py             # 模块导出
│   ├── heartbeat/
│   │   └── __init__.py         # HeartbeatConfig, HeartbeatRunner, HeartbeatEventPayload
│   └── cron/
│       └── __init__.py         # CronSchedule, CronPayload, CronJob, CronService
├── sessions/                    # Phase 6 [已完成]
│   ├── __init__.py             # 模块导出
│   ├── types.py                # SessionEntry, MessageEntry
│   ├── store.py                # SessionStore (JSONL 持久化)
│   └── manager.py              # SessionManager (生命周期管理)
├── agents/
│   ├── subagent/               # Phase 6 [已完成]
│   │   └── __init__.py         # 子代理系统
│   └── types.py                # AgentContext, SessionType
└── tools/builtin/
    ├── session_tools.py        # Phase 6 - 6 个 Session 工具
    ├── cron_tool.py            # Phase 5 - Cron 工具
    └── __init__.py             # 工具导出
```

## Key References

### 文档位置
```
docs/design/
├── MOLTBOT_ANALYSIS.md              # 基础分析
├── MOLTBOT_COMPLETE_ARCHITECTURE.md # 完整架构（32 章节，v3.0）
└── LURKBOT_COMPLETE_DESIGN.md       # 复刻设计（v2.3, 23 阶段）
```

### 测试文件
```
tests/main/
├── test_phase6_sessions.py     # Phase 6 测试 (16 tests)
└── test_phase7_autonomous.py   # Phase 7 测试 (40 tests)
```

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

### 下一阶段建议优先级
| Phase | 模块 | 优先级 | 理由 |
|-------|------|--------|------|
| Phase 8 | Auth Profile + Compaction | P1 | 凭据管理和上下文优化 |
| Phase 9 | Gateway | P1 | 多端通信协议 |
| Phase 12 | Auto-Reply | **P0** | 消息处理核心 |

---

**Document Updated**: 2026-01-29
**Progress**: 7/23 Phases 完成 (30%)
**Total Tests**: 56 passing (Phase 6: 16, Phase 7: 40)
**Next Action**:
1. 开始 Phase 8 - Auth Profile + Context Compaction
2. 或跳到 Phase 12 (Auto-Reply) - 消息处理核心
3. 阶段完成后与 MoltBot 对比验证
