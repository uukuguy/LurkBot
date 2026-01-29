# Next Session Guide

## Session Context

**Last Session Date**: 2026-01-29
**Current Status**: Phase 10 完成，Phase 5-12 全部完成
**Design Document**: `docs/design/LURKBOT_COMPLETE_DESIGN.md` (v2.3)
**Architecture Document**: `docs/design/MOLTBOT_COMPLETE_ARCHITECTURE.md` (v3.0, 32 章节)

## What Was Accomplished

### 今日完成的工作

1. **Phase 10 技能和插件系统** - 全部完成：

   | 组件 | 文件 | 状态 |
   |------|------|------|
   | Frontmatter 解析 | `skills/frontmatter.py` | ✅ 完成 |
   | 技能加载优先级 | `skills/workspace.py` | ✅ 完成 |
   | 技能注册表 | `skills/registry.py` | ✅ 完成 |
   | 插件 Manifest | `plugins/manifest.py` | ✅ 完成 |
   | Manifest 验证器 | `plugins/schema_validator.py` | ✅ 完成 |
   | 插件动态加载器 | `plugins/loader.py` | ✅ 完成 |
   | 系统提示词集成 | `agents/system_prompt.py` | ✅ 完成 |
   | 单元测试 | `tests/main/test_phase10_skills_plugins.py` | ✅ 通过 (23 tests) |

2. **Phase 12 Auto-Reply + Routing 系统** - 全部完成：

   | 组件 | 文件 | 状态 |
   |------|------|------|
   | Reply Tokens | `auto_reply/tokens.py` | ✅ 完成 |
   | Directives | `auto_reply/directives.py` | ✅ 完成 |
   | Queue Types | `auto_reply/queue/types.py` | ✅ 完成 |
   | Session Key | `routing/session_key.py` | ✅ 完成 |
   | Router | `routing/router.py` | ✅ 完成 |
   | 单元测试 | `tests/main/test_phase12_auto_reply_routing.py` | ✅ 通过 (38 tests) |

2. **Phase 9 Gateway WebSocket 协议** - 全部完成：

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

5. **技能系统功能** (Phase 10):
   - YAML Frontmatter 解析: 元数据、调用策略、依赖要求
   - 技能加载优先级: 工作区 > 受管 > 打包 > 额外目录
   - 技能注册表: 按 key、tag 查询，用户/模型可调用过滤
   - 自动集成到系统提示词: 动态生成 &lt;available_skills&gt; 列表

6. **插件系统功能** (Phase 10):
   - Manifest 验证: plugin.json 解析和格式验证
   - 插件发现: .plugins/, node_modules/@lurkbot/plugin-*
   - 动态加载: Python 模块导入、依赖检查、沙箱隔离
   - 生命周期管理: load/unload/enable/disable
   - 版本去重: 保留最新版本

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
| **Phase 10** | 技能和插件系统 | ✅ 完成 |
| **Phase 11** | A2UI Canvas Host | ⏳ 待开始 |
| **Phase 12** | Auto-Reply + Routing | ✅ 完成 |
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

# 2. 验证 Phase 10 模块
python -c "from lurkbot.skills import SkillManager, get_skill_manager; print('Skills OK')"
python -c "from lurkbot.plugins import PluginLoader, get_plugin_loader; print('Plugins OK')"

# 3. 选择下一步方向：
# 方案 A: 开始 Phase 11 - A2UI Canvas Host
# 方案 B: 开始 Phase 13 - Daemon 守护进程
# 方案 C: 开始 Phase 14 - Media Understanding
```

## 新增模块结构

### Phase 10 完成的目录结构
```
src/lurkbot/
├── skills/                      # Phase 10 [新增]
│   ├── __init__.py             # 模块导出
│   ├── frontmatter.py          # YAML Frontmatter 解析
│   ├── workspace.py            # 技能加载优先级系统
│   └── registry.py             # 技能注册表和管理器
├── plugins/                     # Phase 10 [新增]
│   ├── __init__.py             # 模块导出
│   ├── manifest.py             # 插件 Manifest 数据模型
│   ├── schema_validator.py    # Manifest 验证和发现
│   └── loader.py               # 插件动态加载器
├── gateway/                     # Phase 9
│   ├── __init__.py
│   ├── protocol/
│   │   └── frames.py
│   ├── events.py
│   ├── methods.py
│   └── server.py
└── agents/
    ├── system_prompt.py        # Phase 10 [更新] - 集成技能系统
    └── ...
```

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
├── test_phase9_gateway.py           # Phase 9 测试 (12 tests)
├── test_phase10_skills_plugins.py   # Phase 10 测试 (23 tests)
└── test_phase12_auto_reply_routing.py # Phase 12 测试 (38 tests)
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
| Phase 11 | A2UI Canvas | P1 | 界面系统 |
| Phase 13 | Daemon | P2 | 守护进程 |
| Phase 14 | Media Understanding | P2 | 媒体理解 |

---

**Document Updated**: 2026-01-29
**Progress**: 11/23 Phases 完成 (48%)
**Total Tests**: 158 passing (Phase 6: 16, Phase 7: 40, Phase 8: 29, Phase 9: 12, Phase 10: 23, Phase 12: 38)
**Next Action**:
1. 开始 Phase 11 - A2UI Canvas Host (P1 优先级)
2. 或开始 Phase 13 - Daemon 守护进程 (P2 优先级)
3. 或开始 Phase 14 - Media Understanding (P2 优先级)
4. 阶段完成后与 MoltBot 对比验证
1. 开始 Phase 11 - A2UI Canvas Host (P1 优先级)
2. 或开始 Phase 13 - Daemon 守护进程 (P2 优先级)
3. 或开始 Phase 14 - Media Understanding (P2 优先级)
4. 阶段完成后与 MoltBot 对比验证
