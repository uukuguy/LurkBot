# Next Session Guide

## Session Context

**Last Session Date**: 2026-01-29
**Current Status**: Phase 9 完成，Phase 5-9 全部完成
**Design Document**: `docs/design/LURKBOT_COMPLETE_DESIGN.md` (v2.3)
**Architecture Document**: `docs/design/MOLTBOT_COMPLETE_ARCHITECTURE.md` (v3.0, 32 章节)

## What Was Accomplished

### 今日完成的工作

1. **Phase 9 Gateway WebSocket 协议** - 全部完成：

   | 组件 | 文件 | 状态 |
   |------|------|------|
   | ErrorCode, ErrorShape | `gateway/protocol/frames.py` | ✅ 完成 |
   | ClientInfo, ServerInfo | `gateway/protocol/frames.py` | ✅ 完成 |
   | ConnectParams, HelloOk | `gateway/protocol/frames.py` | ✅ 完成 |
   | EventFrame, RequestFrame | `gateway/protocol/frames.py` | ✅ 完成 |
   | ResponseFrame, Features | `gateway/protocol/frames.py` | ✅ 完成 |
   | EventBroadcaster | `gateway/events.py` | ✅ 完成 |
   | MethodRegistry | `gateway/methods.py` | ✅ 完成 |
   | GatewayServer | `gateway/server.py` | ✅ 完成 |
   | 单元测试 | `tests/main/test_phase9_gateway.py` | ✅ 通过 (12 tests) |

2. **Phase 8 Auth Profile + Context Compaction** - 已完成：

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

2. **Gateway WebSocket 协议功能**:
   - 协议帧结构: Hello/HelloOk 握手, Event/Request/Response 帧
   - 错误码系统: 7 种错误类型 (NOT_LINKED, AGENT_TIMEOUT, METHOD_NOT_FOUND 等)
   - 事件广播: 订阅/发布机制, sessionKey 过滤, 事件类型过滤
   - RPC 方法注册: 方法注册/调用/列表, 上下文传递
   - WebSocket 服务器: 连接管理, 握手流程, 消息路由
   - 协议版本: v1, 支持多客户端连接

3. **Auth Profile 系统功能** (Phase 8):
   - 凭据类型支持: API Key, Token, OAuth
   - 冷却算法: 指数退避 (60s → 300s → 1500s → 3600s)
   - Profile 优先级排序: lastUsed 轮换 + 冷却分离
   - 使用统计跟踪: error_count, failure_counts
   - JSONL 持久化存储
   - 凭据验证和过期检查

4. **Context Compaction 系统功能** (Phase 8):
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
| **Phase 9** | Gateway WebSocket 协议 | ✅ 完成 |
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

# 2. 验证 Phase 9 模块
python -c "from lurkbot.gateway.protocol import HelloOk, EventFrame; print('Gateway Protocol OK')"
python -c "from lurkbot.gateway.events import get_event_broadcaster; print('Event Broadcaster OK')"
python -c "from lurkbot.gateway.methods import get_method_registry; print('Method Registry OK')"
python -c "from lurkbot.gateway.server import get_gateway_server; print('Gateway Server OK')"

# 3. 选择下一步方向：
# 方案 A: 开始 Phase 10 - 技能和插件系统
# 方案 B: 开始 Phase 12 - Auto-Reply 系统（消息处理核心，P0 优先级）
# 方案 C: 开始 Phase 11 - A2UI Canvas Host
```

## 新增模块结构

### Phase 9 完成的目录结构
```
src/lurkbot/
├── gateway/                     # Phase 9 [新增]
│   ├── __init__.py             # 模块导出
│   ├── protocol/
│   │   ├── __init__.py         # 协议导出
│   │   └── frames.py           # 协议帧结构定义
│   ├── events.py               # 事件广播系统
│   ├── methods.py              # RPC 方法注册系统
│   └── server.py               # WebSocket 服务器
├── auth/                        # Phase 8 [已完成]
│   ├── __init__.py             # 模块导出
│   └── profiles.py             # Auth Profile 系统
├── agents/
│   ├── compaction.py           # Phase 8 [已完成] - Context Compaction
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
├── test_phase8_auth_compaction.py   # Phase 8 测试 (29 tests)
└── test_phase9_gateway.py           # Phase 9 测试 (12 tests)
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
| Phase 12 | Auto-Reply | **P0** | 消息处理核心 |
| Phase 10 | Skills + Plugins | P1 | 扩展系统 |
| Phase 11 | A2UI Canvas | P1 | 界面系统 |

---

**Document Updated**: 2026-01-29
**Progress**: 9/28 Phases 完成 (32%)
**Total Tests**: 97 passing (Phase 6: 16, Phase 7: 40, Phase 8: 29, Phase 9: 12)
**Next Action**:
1. 开始 Phase 10 - 技能和插件系统
2. 或跳到 Phase 12 (Auto-Reply) - 消息处理核心 (P0 优先级)
3. 阶段完成后与 MoltBot 对比验证
