# Next Session Guide

## Session Context

**Last Session Date**: 2026-01-29
**Current Status**: Phase 15 完成，Phase 5-17 全部完成 (除 Phase 18-23)
**Design Document**: `docs/design/LURKBOT_COMPLETE_DESIGN.md` (v2.3)
**Architecture Document**: `docs/design/MOLTBOT_COMPLETE_ARCHITECTURE.md` (v3.0, 32 章节)

## What Was Accomplished

### 今日完成的工作

1. **Phase 15 Provider Usage 监控系统** - 全部完成：

   | 组件 | 文件 | 状态 |
   |------|------|------|
   | 类型定义 | `usage/types.py` | ✅ 完成 |
   | 使用量跟踪 | `usage/tracker.py` | ✅ 完成 |
   | 成本数据存储 | `usage/store.py` | ✅ 完成 |
   | 格式化输出 | `usage/formatter.py` | ✅ 完成 |
   | 模块导出 | `usage/__init__.py` | ✅ 完成 |
   | 单元测试 | `tests/main/test_phase15_usage.py` | ✅ 通过 (24 tests) |

2. **Phase 14 Media Understanding 媒体理解系统** - 全部完成：

   | 组件 | 文件 | 状态 |
   |------|------|------|
   | 核心理解逻辑 | `media/understand.py` | ✅ 完成 |
   | 配置系统 | `media/config.py` | ✅ 完成 |
   | OpenAI 提供商 | `media/providers/openai.py` | ✅ 完成 |
   | Anthropic 提供商 | `media/providers/anthropic.py` | ✅ 完成 |
   | Gemini 提供商 | `media/providers/gemini.py` | ✅ 完成 |
   | 本地降级提供商 | `media/providers/local.py` | ✅ 完成 |
   | 模块导出 | `media/__init__.py` | ✅ 完成 |
   | 单元测试 | `tests/test_media_understanding.py` | ✅ 通过 (12 tests) |

2. **Phase 17 Security 安全审计系统** - 全部完成：

   | 组件 | 文件 | 状态 |
   |------|------|------|
   | 安全审计核心 | `security/audit.py` | ✅ 完成 |
   | DM 策略检查 | `security/dm_policy.py` | ✅ 完成 |
   | 模型安全检查 | `security/model_check.py` | ✅ 完成 |
   | 警告格式化 | `security/warnings.py` | ✅ 完成 |
   | CLI 命令 | `cli/security.py` | ✅ 完成 |
   | 模块导出 | `security/__init__.py` | ✅ 完成 |
   | 单元测试 | `tests/main/test_phase17_security.py` | ✅ 通过 (27 tests) |

3. **Phase 16 Hooks 扩展系统** - 全部完成：

   | 组件 | 文件 | 状态 |
   |------|------|------|
   | 钩子类型定义 | `hooks/types.py` | ✅ 完成 |
   | 钩子注册表 | `hooks/registry.py` | ✅ 完成 |
   | 钩子发现机制 | `hooks/discovery.py` | ✅ 完成 |
   | 预装钩子 | `hooks/bundled/__init__.py` | ✅ 完成 |
   | Hooks 工具 | `tools/builtin/hooks_tool.py` | ✅ 完成 |
   | 示例钩子 | `docs/examples/hooks/example-hook/` | ✅ 完成 |
   | 模块导出 | `hooks/__init__.py` | ✅ 完成 |
   | 单元测试 | `tests/main/test_phase16_hooks.py` | ✅ 通过 (22 tests) |

3. **Phase 13 Daemon 守护进程系统** - 全部完成：

   | 组件 | 文件 | 状态 |
   |------|------|------|
   | 统一服务接口 | `daemon/service.py` | ✅ 完成 |
   | 常量定义 | `daemon/constants.py` | ✅ 完成 |
   | 路径工具 | `daemon/paths.py` | ✅ 完成 |
   | macOS Launchd | `daemon/launchd.py` | ✅ 完成 |
   | Linux Systemd | `daemon/systemd.py` | ✅ 完成 |
   | Windows Schtasks | `daemon/schtasks.py` | ✅ 完成 |
   | 诊断工具 | `daemon/diagnostics.py` | ✅ 完成 |
   | 检查工具 | `daemon/inspect.py` | ✅ 完成 |
   | 模块导出 | `daemon/__init__.py` | ✅ 完成 |
   | 单元测试 | `tests/main/test_phase13_daemon.py` | ✅ 通过 (26 tests) |

4. **Phase 11 A2UI Canvas Host 系统** - 全部完成：

   | 组件 | 文件 | 状态 |
   |------|------|------|
   | A2UI 协议定义 | `canvas/protocol.py` | ✅ 完成 |
   | Canvas Host 服务器 | `canvas/server.py` | ✅ 完成 |
   | Canvas Client 助手 | `canvas/client.py` | ✅ 完成 |
   | 模块导出 | `canvas/__init__.py` | ✅ 完成 |
   | 单元测试 | `tests/main/test_phase11_canvas.py` | ✅ 通过 (34 tests) |

5. **Phase 10 技能和插件系统** - 全部完成：

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

6. **Phase 12 Auto-Reply + Routing 系统** - 全部完成：

   | 组件 | 文件 | 状态 |
   |------|------|------|
   | Reply Tokens | `auto_reply/tokens.py` | ✅ 完成 |
   | Directives | `auto_reply/directives.py` | ✅ 完成 |
   | Queue Types | `auto_reply/queue/types.py` | ✅ 完成 |
   | Session Key | `routing/session_key.py` | ✅ 完成 |
   | Router | `routing/router.py` | ✅ 完成 |
   | 单元测试 | `tests/main/test_phase12_auto_reply_routing.py` | ✅ 通过 (38 tests) |

7. **Phase 9 Gateway WebSocket 协议** - 全部完成：

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

8. **Phase 8 Auth Profile + Context Compaction** - 已完成：

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

2. **Security 安全审计系统功能** (Phase 17):
   - 安全审计: audit_security() 主函数，支持标准/深度模式
   - Gateway 网络暴露检查: 检测 bind 配置和认证状态
   - DM 策略检查: 多用户会话隔离策略验证
   - 模型安全检查: 危险工具权限、文件系统/网络访问检查
   - 自动修复: apply_fixes() 自动应用关键安全修复
   - CLI 命令: security audit, check-dm-policy, check-gateway
   - 警告格式化: Rich 格式化输出，严重级别统计

3. **Gateway WebSocket 协议功能**:
   - 协议帧结构: Hello/HelloOk 握手, Event/Request/Response 帧
   - 错误码系统: 7 种错误类型 (NOT_LINKED, AGENT_TIMEOUT, METHOD_NOT_FOUND 等)
   - 事件广播: 订阅/发布机制, sessionKey 过滤, 事件类型过滤
   - RPC 方法注册: 方法注册/调用/列表, 上下文传递
   - WebSocket 服务器: 连接管理, 握手流程, 消息路由
   - 协议版本: v1, 支持多客户端连接

4. **Auth Profile 系统功能** (Phase 8):
   - 凭据类型支持: API Key, Token, OAuth
   - 冷却算法: 指数退避 (60s → 300s → 1500s → 3600s)
   - Profile 优先级排序: lastUsed 轮换 + 冷却分离
   - 使用统计跟踪: error_count, failure_counts
   - JSONL 持久化存储
   - 凭据验证和过期检查

5. **Context Compaction 系统功能** (Phase 8):
   - Token 估算: ~4 chars = 1 token
   - 自适应分块比例: 40% → 15% (根据消息大小)
   - 消息分割: 按 token 比例 / 最大 token 数
   - 分阶段摘要: 多部分摘要 + 合并
   - 压缩入口: compact_messages() 主函数

6. **技能系统功能** (Phase 10):
   - YAML Frontmatter 解析: 元数据、调用策略、依赖要求
   - 技能加载优先级: 工作区 > 受管 > 打包 > 额外目录
   - 技能注册表: 按 key、tag 查询，用户/模型可调用过滤
   - 自动集成到系统提示词: 动态生成 &lt;available_skills&gt; 列表

7. **插件系统功能** (Phase 10):
   - Manifest 验证: plugin.json 解析和格式验证
   - 插件发现: .plugins/, node_modules/@lurkbot/plugin-*
   - 动态加载: Python 模块导入、依赖检查、沙箱隔离
   - 生命周期管理: load/unload/enable/disable
   - 版本去重: 保留最新版本

8. **A2UI Canvas Host 系统功能** (Phase 11):
   - A2UI 协议定义: 10 种 Surface 组件类型 (Text, Image, Button, Input, Container 等)
   - 5 种消息类型: SurfaceUpdate, DataModelUpdate, DeleteSurface, BeginRendering, Reset
   - Canvas Host 服务器: WebSocket 连接管理、状态维护、消息广播
   - Canvas Client 助手: 链式 API、便捷组件构建方法
   - JSONL 解析和序列化: parse_jsonl(), to_jsonl()
   - 多会话隔离: 每个会话独立的 Surface 和数据模型状态

9. **Daemon 守护进程系统功能** (Phase 13):
   - 跨平台服务管理: macOS (launchd), Linux (systemd), Windows (schtasks)
   - 统一服务接口: install, uninstall, start, stop, restart, is_loaded, get_runtime
   - 服务状态查询: 运行状态、PID、退出状态、平台特定状态
   - 路径管理: 日志目录、运行时目录、配置文件路径
   - 诊断工具: 服务状态诊断、日志检查、端口可用性检查
   - 检查工具: 服务信息查询、格式化输出

10. **Hooks 扩展系统功能** (Phase 16):
   - 钩子事件类型: command, session, agent, gateway
   - 钩子注册表: 优先级排序、模式匹配、触发器管理
   - 钩子发现机制: workspace > user > bundled 优先级
   - 钩子包结构: HOOK.md (frontmatter) + handler.py
   - 预装钩子: session-memory, command-logger, boot-md
   - 依赖检查: bins, env, python_packages
   - Hooks 工具: list, trigger, discover, info 命令

11. **Media Understanding 媒体理解系统功能** (Phase 14):
   - 媒体类型支持: Image, Audio, Video, Document
   - 多提供商架构: OpenAI, Anthropic, Gemini, Local
   - 智能降级机制: 按优先级自动降级到下一个提供商
   - 配置系统: 灵活的提供商配置和媒体类型设置
   - 批量处理: 支持批量理解多个媒体文件
   - OpenAI Provider: GPT-4 Vision (图片), Whisper (音频), GPT-4 (文档)
   - Anthropic Provider: Claude Vision (图片), Claude (文档)
   - Gemini Provider: Gemini Vision (图片), Gemini (音频/视频/文档)
   - Local Provider: PIL (图片元数据), ffprobe (音频/视频), PyPDF2 (PDF)

12. **Provider Usage 监控系统功能** (Phase 15):
   - 实时配额监控: 追踪 API 使用量和限制 (5h, Week, Model-specific)
   - 成本估算: 基于 token 使用量估算成本
   - 多提供商支持: Anthropic, OpenAI, Google, GitHub Copilot 等
   - 会话成本追踪: 每会话和每日成本汇总
   - 使用量归一化: 统一不同 SDK 的命名约定
   - 成本计算: ModelCostConfig 配置 + 自动估算
   - 格式化输出: USD 金额、token 数量、重置时间格式化
   - JSONL 解析: 从会话文件中提取使用量和成本数据

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
| **Phase 11** | A2UI Canvas Host | ✅ 完成 |
| **Phase 12** | Auto-Reply + Routing | ✅ 完成 |
| **Phase 13** | Daemon 守护进程 | ✅ 完成 |
| **Phase 16** | Hooks 扩展系统 | ✅ 完成 |
| **Phase 17** | Security 安全审计 | ✅ 完成 |
| **Phase 14** | Media Understanding | ✅ 完成 |
| **Phase 15** | Provider Usage 监控 | ✅ 完成 |
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

# 2. 验证 Phase 15 模块
python -c "from lurkbot.usage import load_provider_usage_summary, format_usage_summary_line; print('Provider Usage OK')"

# 3. 选择下一步方向：
# 方案 A: 开始 Phase 18 - ACP 协议系统 (推荐)
# 方案 B: 开始 Phase 19 - Browser 浏览器自动化
# 方案 C: 开始 Phase 20 - TUI 终端界面
```

## 新增模块结构

### Phase 15 完成的目录结构
```
src/lurkbot/
├── usage/                       # Phase 15 [新增]
│   ├── __init__.py             # 模块导出
│   ├── types.py                # 类型定义
│   ├── tracker.py              # 使用量跟踪
│   ├── store.py                # 成本数据存储
│   └── formatter.py            # 格式化输出
├── media/                       # Phase 14
│   ├── __init__.py
│   ├── understand.py
│   ├── config.py
│   └── providers/
│       ├── __init__.py
│       ├── openai.py
│       ├── anthropic.py
│       ├── gemini.py
│       └── local.py
├── security/                    # Phase 17
│   ├── __init__.py
│   ├── audit.py
│   ├── dm_policy.py
│   ├── model_check.py
│   └── warnings.py
├── hooks/                       # Phase 16
│   ├── __init__.py
│   ├── types.py
│   ├── registry.py
│   ├── discovery.py
│   └── bundled/
│       └── __init__.py
├── daemon/                      # Phase 13
│   ├── __init__.py
│   ├── service.py
│   ├── constants.py
│   ├── paths.py
│   ├── launchd.py
│   ├── systemd.py
│   ├── schtasks.py
│   ├── diagnostics.py
│   └── inspect.py
├── canvas/                      # Phase 11
│   ├── __init__.py
│   ├── protocol.py
│   ├── server.py
│   └── client.py
├── skills/                      # Phase 10
│   ├── __init__.py
│   ├── frontmatter.py
│   ├── workspace.py
│   └── registry.py
├── plugins/                     # Phase 10
│   ├── __init__.py
│   ├── manifest.py
│   ├── schema_validator.py
│   └── loader.py
└── gateway/                     # Phase 9
    ├── __init__.py
    ├── protocol/
    │   └── frames.py
    ├── events.py
    ├── methods.py
    └── server.py
```

### Phase 16 完成的目录结构
```
src/lurkbot/
├── hooks/                       # Phase 16 [新增]
│   ├── __init__.py             # 模块导出
│   ├── types.py                # 钩子类型定义
│   ├── registry.py             # 钩子注册表
│   ├── discovery.py            # 钩子发现机制
│   └── bundled/                # 预装钩子
│       └── __init__.py         # 预装钩子实现
├── daemon/                      # Phase 13
│   ├── __init__.py
│   ├── service.py
│   ├── constants.py
│   ├── paths.py
│   ├── launchd.py
│   ├── systemd.py
│   ├── schtasks.py
│   ├── diagnostics.py
│   └── inspect.py
├── canvas/                      # Phase 11
│   ├── __init__.py
│   ├── protocol.py
│   ├── server.py
│   └── client.py
├── skills/                      # Phase 10
│   ├── __init__.py
│   ├── frontmatter.py
│   ├── workspace.py
│   └── registry.py
├── plugins/                     # Phase 10
│   ├── __init__.py
│   ├── manifest.py
│   ├── schema_validator.py
│   └── loader.py
└── gateway/                     # Phase 9
    ├── __init__.py
    ├── protocol/
    │   └── frames.py
    ├── events.py
    ├── methods.py
    └── server.py
```

### Phase 13 完成的目录结构
```
src/lurkbot/
├── daemon/                      # Phase 13 [新增]
│   ├── __init__.py             # 模块导出
│   ├── service.py              # 统一服务接口
│   ├── constants.py            # 常量定义
│   ├── paths.py                # 路径工具
│   ├── launchd.py              # macOS Launchd 实现
│   ├── systemd.py              # Linux Systemd 实现
│   ├── schtasks.py             # Windows Schtasks 实现
│   ├── diagnostics.py          # 诊断工具
│   └── inspect.py              # 检查工具
├── canvas/                      # Phase 11
│   ├── __init__.py
│   ├── protocol.py
│   ├── server.py
│   └── client.py
├── skills/                      # Phase 10
│   ├── __init__.py
│   ├── frontmatter.py
│   ├── workspace.py
│   └── registry.py
├── plugins/                     # Phase 10
│   ├── __init__.py
│   ├── manifest.py
│   ├── schema_validator.py
│   └── loader.py
└── gateway/                     # Phase 9
    ├── __init__.py
    ├── protocol/
    │   └── frames.py
    ├── events.py
    ├── methods.py
    └── server.py
```

### Phase 11 完成的目录结构
```
src/lurkbot/
├── canvas/                      # Phase 11 [新增]
│   ├── __init__.py             # 模块导出
│   ├── protocol.py             # A2UI 协议定义
│   ├── server.py               # Canvas Host 服务器
│   └── client.py               # Canvas Client 助手
├── skills/                      # Phase 10
│   ├── __init__.py
│   ├── frontmatter.py
│   ├── workspace.py
│   └── registry.py
├── plugins/                     # Phase 10
│   ├── __init__.py
│   ├── manifest.py
│   ├── schema_validator.py
│   └── loader.py
└── gateway/                     # Phase 9
    ├── __init__.py
    ├── protocol/
    │   └── frames.py
    ├── events.py
    ├── methods.py
    └── server.py
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
├── test_phase11_canvas.py           # Phase 11 测试 (34 tests)
├── test_phase12_auto_reply_routing.py # Phase 12 测试 (38 tests)
├── test_phase13_daemon.py           # Phase 13 测试 (26 tests)
├── test_phase16_hooks.py            # Phase 16 测试 (22 tests)
├── test_phase17_security.py         # Phase 17 测试 (27 tests)
└── test_phase15_usage.py            # Phase 15 测试 (24 tests)

tests/
└── test_media_understanding.py      # Phase 14 测试 (12 tests)
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
| Phase 18 | ACP 协议系统 | P1 | IDE 集成协议，核心功能 |
| Phase 19 | Browser 浏览器自动化 | P2 | 浏览器控制和自动化 |
| Phase 20 | TUI 终端界面 | P2 | 交互式终端界面 |

---

**Document Updated**: 2026-01-29
**Progress**: 16/23 Phases 完成 (69.6%)
**Total Tests**: 289 passing (Phase 6: 16, Phase 7: 40, Phase 8: 29, Phase 9: 12, Phase 10: 23, Phase 11: 34, Phase 12: 38, Phase 13: 26, Phase 14: 12, Phase 15: 24, Phase 16: 22, Phase 17: 27), 2 skipped
**Next Action**:
1. 开始 Phase 18 - ACP 协议系统 (P1 优先级，IDE 集成)
2. 或开始 Phase 19 - Browser 浏览器自动化 (浏览器控制)
3. 或开始 Phase 20 - TUI 终端界面 (交互式终端)
4. 阶段完成后与 MoltBot 对比验证
