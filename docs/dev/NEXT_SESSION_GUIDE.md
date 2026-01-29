# Next Session Guide

## Session Context

**Last Session Date**: 2026-01-30
**Current Status**: Phase 21 完成，Phase 5-21 全部完成 (除 Phase 22-23)
**Design Document**: `docs/design/LURKBOT_COMPLETE_DESIGN.md` (v2.3)
**Architecture Document**: `docs/design/MOLTBOT_COMPLETE_ARCHITECTURE.md` (v3.0, 32 章节)

## What Was Accomplished

### 今日完成的工作

1. **Phase 21 TTS 语音合成系统** - 全部完成：

   | 组件 | 文件 | 状态 |
   |------|------|------|
   | 类型定义 | `tts/types.py` | ✅ 完成 |
   | 用户偏好系统 | `tts/prefs.py` | ✅ 完成 |
   | Directive 解析器 | `tts/directive_parser.py` | ✅ 完成 |
   | 文本摘要器 | `tts/summarizer.py` | ✅ 完成 |
   | Provider 基类 | `tts/providers/base.py` | ✅ 完成 |
   | OpenAI Provider | `tts/providers/openai.py` | ✅ 完成 |
   | ElevenLabs Provider | `tts/providers/elevenlabs.py` | ✅ 完成 |
   | Edge Provider | `tts/providers/edge.py` | ✅ 完成 |
   | TTS 引擎 | `tts/engine.py` | ✅ 完成 |
   | TTS 工具 | `tools/tts_tool.py` | ✅ 更新 |
   | 模块导出 | `tts/__init__.py` | ✅ 完成 |
   | 单元测试 | `tests/main/test_phase21_tts.py` | ✅ 通过 (57 tests) |

## TTS 语音合成系统功能 (Phase 21)

### 核心功能
- **多 Provider 支持**: OpenAI TTS, ElevenLabs, Edge TTS (免费)
- **Directive 解析**: `[[tts:provider=openai voice=nova]]` 内联指令
- **文本摘要**: 长文本自动截断/分割
- **用户偏好**: 持久化 TTS 设置
- **Provider 回退**: 自动切换到可用 provider

### Provider 配置
| Provider | 模型 | 特点 |
|----------|------|------|
| OpenAI | gpt-4o-mini-tts, tts-1, tts-1-hd | 高质量，需 API Key |
| ElevenLabs | eleven_multilingual_v2 | 多语言，需 API Key |
| Edge | 多种声音 | 免费，无需 API Key |

### Directive 语法
```
[[tts:provider=openai voice=nova]]
[[tts:text]]自定义 TTS 文本[[/tts:text]]
[[tts:provider=elevenlabs voice_id=xxx model_id=xxx]]
```

### 组件结构
```
src/lurkbot/tts/
├── __init__.py              # 模块导出
├── types.py                 # 类型定义 (TtsProvider, TtsConfig, etc.)
├── prefs.py                 # 用户偏好管理
├── directive_parser.py      # [[tts:...]] 指令解析器
├── summarizer.py            # 文本摘要器
├── engine.py                # TTS 引擎
└── providers/
    ├── __init__.py
    ├── base.py              # Provider 基类
    ├── openai.py            # OpenAI TTS Provider
    ├── elevenlabs.py        # ElevenLabs TTS Provider
    └── edge.py              # Edge TTS Provider (免费)
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
| **Phase 21** | TTS 语音合成 | ✅ 完成 |
| **Phase 22** | Wizard 配置向导 | ⏳ 待开始 |
| **Phase 23** | Infra 基础设施 | ⏳ 待开始 |

## Quick Start for Next Session

```bash
# 1. 运行测试确认当前状态
python -m pytest tests/main/ -xvs

# 2. 验证 Phase 21 TTS 模块
python -c "from lurkbot.tts import TtsEngine, TtsSummarizer, parse_tts_directives; print('TTS OK')"

# 3. 选择下一步方向：
# 方案 A: 开始 Phase 22 - Wizard 配置向导 (推荐)
# 方案 B: 开始 Phase 23 - Infra 基础设施
```

## Phase 21 完成的目录结构
```
src/lurkbot/
├── tts/                         # Phase 21 [新增]
│   ├── __init__.py             # 模块导出
│   ├── types.py                # TTS 类型定义
│   ├── prefs.py                # 用户偏好管理
│   ├── directive_parser.py     # [[tts:...]] 指令解析器
│   ├── summarizer.py           # 文本摘要器
│   ├── engine.py               # TTS 引擎
│   └── providers/
│       ├── __init__.py
│       ├── base.py             # Provider 基类
│       ├── openai.py           # OpenAI TTS Provider
│       ├── elevenlabs.py       # ElevenLabs TTS Provider
│       └── edge.py             # Edge TTS Provider
├── tui/                         # Phase 20
│   └── ...
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
├── test_phase20_tui.py              # Phase 20 测试 (85 tests)
└── test_phase21_tts.py              # Phase 21 测试 (57 tests) [新增]

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
- **TTS**: edge-tts (免费), httpx (API 调用)

### 下一阶段建议优先级
| Phase | 模块 | 优先级 | 理由 |
|-------|------|--------|------|
| Phase 22 | Wizard 配置向导 | P1 | 交互式配置系统 |
| Phase 23 | Infra 基础设施 | P2 | 网络发现、SSH 隧道等 |

### Phase 22 Wizard 配置向导设计预览

模块结构:
```
src/lurkbot/wizard/
├── __init__.py
├── types.py                  # Wizard 类型定义
├── prompts.py                # 交互式提示
├── validators.py             # 输入验证
├── steps/
│   ├── __init__.py
│   ├── provider.py           # Provider 配置步骤
│   ├── channel.py            # Channel 配置步骤
│   └── tts.py                # TTS 配置步骤
└── wizard.py                 # 主向导入口
```

---

**Document Updated**: 2026-01-30
**Progress**: 21/23 Phases 完成 (91.3%)
**Total Tests**: 521 passing (Phase 6: 16, Phase 7: 40, Phase 8: 29, Phase 9: 12, Phase 10: 23, Phase 11: 34, Phase 12: 38, Phase 13: 26, Phase 14: 12, Phase 15: 24, Phase 16: 22, Phase 17: 27, Phase 18: 41, Phase 19: 49, Phase 20: 85, Phase 21: 57), 2 skipped
**Next Action**:
1. 开始 Phase 22 - Wizard 配置向导 (P1 优先级)
2. 或开始 Phase 23 - Infra 基础设施
3. 阶段完成后与 MoltBot 对比验证
