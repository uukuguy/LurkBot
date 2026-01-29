# Next Session Guide

## Session Context

**Last Session Date**: 2026-01-30
**Current Status**: Phase 20 完成，Phase 5-20 全部完成 (除 Phase 21-23)
**Design Document**: `docs/design/LURKBOT_COMPLETE_DESIGN.md` (v2.3)
**Architecture Document**: `docs/design/MOLTBOT_COMPLETE_ARCHITECTURE.md` (v3.0, 32 章节)

## What Was Accomplished

### 今日完成的工作

1. **Phase 20 TUI 终端界面系统** - 全部完成：

   | 组件 | 文件 | 状态 |
   |------|------|------|
   | 类型定义 | `tui/types.py` | ✅ 完成 |
   | 流式组装器 | `tui/stream_assembler.py` | ✅ 完成 |
   | 格式化器 | `tui/formatters.py` | ✅ 完成 |
   | 快捷键绑定 | `tui/keybindings.py` | ✅ 完成 |
   | Gateway 通信 | `tui/gateway_chat.py` | ✅ 完成 |
   | 命令处理器 | `tui/commands.py` | ✅ 完成 |
   | 事件处理器 | `tui/events.py` | ✅ 完成 |
   | 聊天日志组件 | `tui/components/chat_log.py` | ✅ 完成 |
   | Thinking 组件 | `tui/components/thinking.py` | ✅ 完成 |
   | 输入框组件 | `tui/components/input_box.py` | ✅ 完成 |
   | 主应用 | `tui/app.py` | ✅ 完成 |
   | 模块导出 | `tui/__init__.py` | ✅ 完成 |
   | 单元测试 | `tests/main/test_phase20_tui.py` | ✅ 通过 (85 tests) |

## TUI 终端界面系统功能 (Phase 20)

### 核心功能
- **交互式聊天**: 实时聊天界面，支持流式响应
- **命令系统**: /help, /status, /agent, /model, /think, /sessions 等
- **快捷键**: 完整的键盘绑定支持
- **Gateway 通信**: WebSocket 连接 Gateway 服务器
- **流式响应**: 分离 thinking/content 块的流式组装

### 命令系统
| 命令 | 功能 |
|------|------|
| `/help` | 显示帮助 |
| `/status` | 网关状态 |
| `/agent [id]` | 切换 Agent |
| `/model [ref]` | 设置模型 |
| `/think <level>` | 设置 thinking 级别 (off/low/medium/high) |
| `/sessions` | 列出会话 |
| `/new` | 重置会话 |
| `/abort` | 中止运行 |
| `/clear` | 清除显示 |
| `/tools` | 切换工具详情 |
| `/exit` | 退出 TUI |
| `!command` | 执行 bash 命令 |

### 组件结构
```
src/lurkbot/tui/
├── __init__.py              # 模块导出
├── types.py                 # 类型定义 (TuiState, ActivityStatus, etc.)
├── stream_assembler.py      # 流式响应组装器
├── formatters.py            # Rich 格式化器
├── keybindings.py           # 快捷键定义
├── gateway_chat.py          # Gateway WebSocket 通信
├── commands.py              # 命令处理器
├── events.py                # 事件处理器
├── app.py                   # TUI 主应用
└── components/
    ├── __init__.py
    ├── chat_log.py          # 聊天日志组件
    ├── thinking.py          # Thinking 指示器
    └── input_box.py         # 输入框组件
```

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
| **Phase 20** | TUI 终端界面 | ✅ 完成 |
| **Phase 21** | TTS 语音合成 | ⏳ 待开始 |
| **Phase 22** | Wizard 配置向导 | ⏳ 待开始 |
| **Phase 23** | Infra 基础设施 | ⏳ 待开始 |

## Quick Start for Next Session

```bash
# 1. 运行测试确认当前状态
python -m pytest tests/main/ -xvs

# 2. 验证 Phase 20 TUI 模块
python -c "from lurkbot.tui import TuiApp, run_tui, CommandHandler; print('TUI OK')"

# 3. 选择下一步方向：
# 方案 A: 开始 Phase 21 - TTS 语音合成 (推荐)
# 方案 B: 开始 Phase 22 - Wizard 配置向导
# 方案 C: 开始 Phase 23 - Infra 基础设施
```

## Phase 20 完成的目录结构
```
src/lurkbot/
├── tui/                         # Phase 20 [新增]
│   ├── __init__.py             # 模块导出
│   ├── types.py                # TUI 类型定义
│   ├── stream_assembler.py     # 流式响应组装器
│   ├── formatters.py           # Rich 格式化器
│   ├── keybindings.py          # 快捷键定义
│   ├── gateway_chat.py         # Gateway WebSocket 通信
│   ├── commands.py             # 命令处理器
│   ├── events.py               # 事件处理器
│   ├── app.py                  # TUI 主应用
│   └── components/
│       ├── __init__.py
│       ├── chat_log.py         # 聊天日志组件
│       ├── thinking.py         # Thinking 指示器
│       └── input_box.py        # 输入框组件
├── browser/                     # Phase 19
│   └── ...
├── acp/                         # Phase 18
│   └── ...
├── security/                    # Phase 17
│   └── ...
├── hooks/                       # Phase 16
│   └── ...
├── usage/                       # Phase 15
│   └── ...
├── media/                       # Phase 14
│   └── ...
├── daemon/                      # Phase 13
│   └── ...
└── ...
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
├── test_phase18_acp.py              # Phase 18 测试 (41 tests)
├── test_phase19_browser.py          # Phase 19 测试 (49 tests)
└── test_phase20_tui.py              # Phase 20 测试 (85 tests) [新增]

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
- **TUI**: Rich (用于格式化输出)

### 下一阶段建议优先级
| Phase | 模块 | 优先级 | 理由 |
|-------|------|--------|------|
| Phase 21 | TTS 语音合成 | P1 | 多 Provider 文本转语音 |
| Phase 22 | Wizard 配置向导 | P2 | 交互式配置系统 |
| Phase 23 | Infra 基础设施 | P3 | 网络发现、SSH 隧道等 |

### Phase 21 TTS 语音合成设计预览

模块结构:
```
src/lurkbot/tts/
├── __init__.py
├── engine.py                 # TTS 引擎
├── directive_parser.py       # [[tts:...]] 解析
├── summarizer.py             # 长文本摘要
└── providers/
    ├── __init__.py
    ├── openai.py             # OpenAI TTS
    ├── elevenlabs.py         # ElevenLabs TTS
    └── edge.py               # 免费 Edge TTS
```

配置结构:
```python
@dataclass
class TTSConfig:
    auto: Literal["off", "always", "inbound", "tagged"] = "off"
    mode: Literal["delta", "final"] = "final"
    provider: Literal["openai", "elevenlabs", "edge"] = "openai"
    summary_model: str | None = None
```

---

**Document Updated**: 2026-01-30
**Progress**: 20/23 Phases 完成 (87.0%)
**Total Tests**: 464 passing (Phase 6: 16, Phase 7: 40, Phase 8: 29, Phase 9: 12, Phase 10: 23, Phase 11: 34, Phase 12: 38, Phase 13: 26, Phase 14: 12, Phase 15: 24, Phase 16: 22, Phase 17: 27, Phase 18: 41, Phase 19: 49, Phase 20: 85), 2 skipped
**Next Action**:
1. 开始 Phase 21 - TTS 语音合成 (P1 优先级)
2. 或开始 Phase 22 - Wizard 配置向导
3. 或开始 Phase 23 - Infra 基础设施
4. 阶段完成后与 MoltBot 对比验证
