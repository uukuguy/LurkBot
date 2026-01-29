# Next Session Guide

## Session Context

**Last Session Date**: 2026-01-29
**Current Status**: Phase 8 完成，Phase 5-8 全部完成
**Design Document**: `docs/design/LURKBOT_COMPLETE_DESIGN.md` (v2.3)
**Architecture Document**: `docs/design/MOLTBOT_COMPLETE_ARCHITECTURE.md` (v3.0, 32 章节)

## What Was Accomplished

### 今日完成的工作

1. **Phase 8 Auth Profile + Context Compaction** - 全部完成：

   | 组件 | 文件 | 状态 |
   |------|------|------|
   | AuthCredential | `auth/profiles.py` | ✅ 完成 |
   | ProfileUsageStats | `auth/profiles.py` | ✅ 完成 |
   | AuthProfileStore | `auth/profiles.py` | ✅ 完成 |
   | calculate_cooldown_ms | `auth/profiles.py` | ✅ 完成 |
   | resolve_auth_profile_order | `auth/profiles.py` | ✅ 完成 |
   | rotate_auth_profile | `auth/profiles.py` | ✅ 完成 |
   | load/save_auth_profiles | `auth/profiles.py` | ✅ 完成 |
   | estimate_tokens | `agents/compaction.py` | ✅ 完成 |
   | split_messages_by_token_share | `agents/compaction.py` | ✅ 完成 |
   | compute_adaptive_chunk_ratio | `agents/compaction.py` | ✅ 完成 |
   | summarize_in_stages | `agents/compaction.py` | ✅ 完成 |
   | compact_messages | `agents/compaction.py` | ✅ 完成 |
   | 单元测试 | `tests/main/test_phase8_auth_compaction.py` | ✅ 通过 (29 tests) |

2. **Auth Profile 系统功能**:
   - 凭据类型支持: API Key, Token, OAuth
   - 冷却算法: 指数退避 (60s → 300s → 1500s → 3600s)
   - Profile 优先级排序: lastUsed 轮换 + 冷却分离
   - 使用统计跟踪: error_count, failure_counts
   - JSONL 持久化存储
   - 凭据验证和过期检查

3. **Context Compaction 系统功能**:
   - Token 估算: ~4 chars = 1 token
   - 自适应分块比例: 40% → 15% (根据消息大小)
   - 消息分割: 按 token 比例 / 最大 token 数
   - 分阶段摘要: 多部分摘要 + 合并
   - 压缩入口: compact_messages() 主函数

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
| **Phase 8** | Auth Profile + Context Compaction | ✅ 完成 |
| **Phase 9** | Gateway WebSocket 协议 | ⏳ 下一步 |
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

# 2. 验证 Phase 8 模块
python -c "from lurkbot.auth import AuthProfileStore, calculate_cooldown_ms; print('Auth OK')"
python -c "from lurkbot.agents import compact_messages, estimate_tokens; print('Compaction OK')"

# 3. 选择下一步方向：
# 方案 A: 开始 Phase 9 - Gateway WebSocket 协议
# 方案 B: 开始 Phase 12 - Auto-Reply 系统（消息处理核心）
# 方案 C: 开始 Phase 10 - 技能和插件系统
```

## 新增模块结构

### Phase 8 完成的目录结构
```
src/lurkbot/
├── auth/                        # Phase 8 [新增]
│   ├── __init__.py             # 模块导出
│   └── profiles.py             # Auth Profile 系统
├── agents/
│   ├── compaction.py           # Phase 8 [新增] - Context Compaction
│   ├── subagent/               # Phase 6 [已完成]
│   │   └── __init__.py         # 子代理系统
│   └── types.py                # AgentContext, SessionType
├── autonomous/                  # Phase 7 [已完成]
│   ├── __init__.py             # 模块导出
│   ├── heartbeat/
│   │   └── __init__.py         # HeartbeatConfig, HeartbeatRunner
│   └── cron/
│       └── __init__.py         # CronSchedule, CronJob, CronService
├── sessions/                    # Phase 6 [已完成]
│   ├── __init__.py             # 模块导出
│   ├── types.py                # SessionEntry, MessageEntry
│   ├── store.py                # SessionStore (JSONL 持久化)
│   └── manager.py              # SessionManager (生命周期管理)
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
├── test_phase6_sessions.py          # Phase 6 测试 (16 tests)
├── test_phase7_autonomous.py        # Phase 7 测试 (40 tests)
└── test_phase8_auth_compaction.py   # Phase 8 测试 (29 tests)
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
| Phase 9 | Gateway | P1 | 多端通信协议 |
| Phase 12 | Auto-Reply | **P0** | 消息处理核心 |
| Phase 10 | Skills + Plugins | P1 | 扩展系统 |

---

**Document Updated**: 2026-01-29
**Progress**: 8/23 Phases 完成 (35%)
**Total Tests**: 85 passing (Phase 6: 16, Phase 7: 40, Phase 8: 29)
**Next Action**:
1. 开始 Phase 9 - Gateway WebSocket 协议
2. 或跳到 Phase 12 (Auto-Reply) - 消息处理核心
3. 阶段完成后与 MoltBot 对比验证
