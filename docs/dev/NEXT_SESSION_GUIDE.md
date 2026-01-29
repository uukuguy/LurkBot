# Next Session Guide

## Session Context

**Last Session Date**: 2026-01-30
**Current Status**: Phase 19 完成，Phase 5-19 全部完成 (除 Phase 20-23)
**Design Document**: `docs/design/LURKBOT_COMPLETE_DESIGN.md` (v2.3)
**Architecture Document**: `docs/design/MOLTBOT_COMPLETE_ARCHITECTURE.md` (v3.0, 32 章节)

## What Was Accomplished

### 今日完成的工作

1. **Phase 19 Browser 浏览器自动化系统** - 全部完成：

   | 组件 | 文件 | 状态 |
   |------|------|------|
   | 类型定义 | `browser/types.py` | ✅ 完成 |
   | 配置管理 | `browser/config.py` | ✅ 完成 |
   | Chrome 管理器 | `browser/chrome.py` | ✅ 完成 |
   | CDP 客户端 | `browser/cdp.py` | ✅ 完成 |
   | Playwright 会话 | `browser/playwright_session.py` | ✅ 完成 |
   | 角色快照 | `browser/role_snapshot.py` | ✅ 完成 |
   | 截图处理 | `browser/screenshot.py` | ✅ 完成 |
   | 扩展中继 | `browser/extension_relay.py` | ✅ 完成 |
   | HTTP 服务器 | `browser/server.py` | ✅ 完成 |
   | 路由端点 | `browser/routes/*.py` | ✅ 完成 |
   | 模块导出 | `browser/__init__.py` | ✅ 完成 |
   | 单元测试 | `tests/main/test_phase19_browser.py` | ✅ 通过 (49 tests) |

## Browser 浏览器自动化系统功能 (Phase 19)

### 核心功能
- **Playwright 集成**: 支持 Chromium/Firefox/WebKit 浏览器自动化
- **CDP 支持**: Chrome DevTools Protocol 直接通信
- **角色快照**: 页面可访问性树的结构化表示
- **截图处理**: 全页/元素截图，支持裁剪和注释
- **HTTP API**: FastAPI 服务器提供 RESTful 端点

### 类型定义 (types.py)
- **动作类型**: BrowserAction (click, type, fill, press, hover, drag 等)
- **请求模型**: ActRequest, NavigateRequest, ScreenshotRequest, EvaluateRequest
- **响应模型**: BrowserStatus, ActResponse, NavigateResponse, ScreenshotResponse
- **角色节点**: RoleNode 用于可访问性树表示
- **配置**: BrowserConfig, ServerConfig
- **错误类型**: BrowserError, BrowserNotConnectedError, BrowserTimeoutError

### Playwright 会话 (playwright_session.py)
- **会话管理**: launch(), connect_cdp(), close()
- **页面管理**: new_page(), close_page(), switch_to_page()
- **导航**: navigate(), reload(), go_back(), go_forward()
- **动作**: click(), type(), fill(), press(), hover(), drag()
- **截图**: screenshot(), wait_for_selector()

### HTTP 路由
| 端点 | 方法 | 功能 |
|------|------|------|
| `/status` | GET | 浏览器状态 |
| `/connect` | POST | 连接浏览器 |
| `/tabs` | GET/POST/DELETE | 标签页管理 |
| `/act` | POST | 执行动作 |
| `/navigate` | POST | 导航 |
| `/screenshot` | GET/POST | 截图 |
| `/snapshot/role` | POST | 角色快照 |
| `/snapshot/aria` | GET/POST | ARIA 快照 |
| `/evaluate` | POST | 执行 JavaScript |

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
| **Phase 14** | Media Understanding | ✅ 完成 |
| **Phase 15** | Provider Usage 监控 | ✅ 完成 |
| **Phase 16** | Hooks 扩展系统 | ✅ 完成 |
| **Phase 17** | Security 安全审计 | ✅ 完成 |
| **Phase 18** | ACP 协议系统 | ✅ 完成 |
| **Phase 19** | Browser 浏览器自动化 | ✅ 完成 |
| **Phase 20** | TUI 终端界面 | ⏳ 待开始 |
| **Phase 21** | TTS 语音合成 | ⏳ 待开始 |
| **Phase 22** | Wizard 配置向导 | ⏳ 待开始 |
| **Phase 23** | Infra 基础设施 | ⏳ 待开始 |

## Quick Start for Next Session

```bash
# 1. 运行测试确认当前状态
python -m pytest tests/main/ -xvs

# 2. 验证 Phase 18 ACP 模块
python -c "from lurkbot.acp import ACPServer, run_acp_server, text_block; print('ACP OK')"

# 3. 选择下一步方向：
# 方案 A: 开始 Phase 19 - Browser 浏览器自动化 (推荐)
# 方案 B: 开始 Phase 20 - TUI 终端界面
# 方案 C: 开始 Phase 21 - TTS 语音合成
```

## Phase 18 完成的目录结构
```
src/lurkbot/
├── acp/                         # Phase 18 [新增]
│   ├── __init__.py             # 模块导出
│   ├── types.py                # ACP 类型定义 (PROTOCOL_VERSION, ContentBlock, etc.)
│   ├── session.py              # 会话管理 (ACPSession, ACPSessionManager)
│   ├── event_mapper.py         # 事件映射器 (EventMapper)
│   ├── translator.py           # 协议翻译器 (ACPGatewayTranslator)
│   └── server.py               # ACP 服务器 (ACPServer, run_acp_server)
├── usage/                       # Phase 15
│   ├── __init__.py
│   ├── types.py
│   ├── tracker.py
│   ├── store.py
│   └── formatter.py
├── media/                       # Phase 14
│   ├── __init__.py
│   ├── understand.py
│   ├── config.py
│   └── providers/
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
├── test_phase15_usage.py            # Phase 15 测试 (24 tests)
├── test_phase16_hooks.py            # Phase 16 测试 (22 tests)
├── test_phase17_security.py         # Phase 17 测试 (27 tests)
└── test_phase18_acp.py              # Phase 18 测试 (41 tests) [新增]

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
| Phase 19 | Browser 浏览器自动化 | P1 | Playwright/CDP 浏览器控制 |
| Phase 20 | TUI 终端界面 | P2 | 交互式终端界面 |
| Phase 21 | TTS 语音合成 | P3 | 文本转语音功能 |

### Phase 19 Browser 浏览器自动化设计预览

模块结构:
```
src/lurkbot/browser/
├── __init__.py
├── server.py                 # 控制服务器
├── config.py                 # 配置解析
├── chrome.py                 # Chrome 启动管理
├── cdp.py                    # CDP 操作
├── playwright_session.py     # Playwright 会话
├── role_snapshot.py          # 角色快照
├── screenshot.py             # 截图处理
├── extension_relay.py        # 扩展中继
└── routes/
    ├── __init__.py
    ├── act.py                # /act 端点
    ├── navigate.py           # /navigate 端点
    └── screenshot.py         # /screenshot 端点
```

HTTP 路由:
| 端点 | 方法 | 功能 |
|------|------|------|
| `/status` | GET | 浏览器状态 |
| `/tabs` | GET/POST/DELETE | 标签页管理 |
| `/act` | POST | 执行动作 (click, type, etc.) |
| `/navigate` | POST | 导航 |
| `/screenshot` | POST | 截图 |
| `/snapshot/role` | POST | 角色快照 |
| `/evaluate` | POST | 执行 JavaScript |

---

**Document Updated**: 2026-01-30
**Progress**: 17/23 Phases 完成 (73.9%)
**Total Tests**: 330 passing (Phase 6: 16, Phase 7: 40, Phase 8: 29, Phase 9: 12, Phase 10: 23, Phase 11: 34, Phase 12: 38, Phase 13: 26, Phase 14: 12, Phase 15: 24, Phase 16: 22, Phase 17: 27, Phase 18: 41), 2 skipped
**Next Action**:
1. 开始 Phase 19 - Browser 浏览器自动化 (P1 优先级)
2. 或开始 Phase 20 - TUI 终端界面
3. 或开始 Phase 21 - TTS 语音合成
4. 阶段完成后与 MoltBot 对比验证
