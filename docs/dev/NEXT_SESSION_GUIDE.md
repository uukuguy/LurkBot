# Next Session Guide

## Session Context

**Last Session Date**: 2026-01-30
**Current Status**: Phase 22 完成，Phase 5-22 全部完成 (除 Phase 23)
**Design Document**: `docs/design/LURKBOT_COMPLETE_DESIGN.md` (v2.3)
**Architecture Document**: `docs/design/MOLTBOT_COMPLETE_ARCHITECTURE.md` (v3.0, 32 章节)

## What Was Accomplished

### 今日完成的工作

1. **Phase 22 Wizard 配置向导** - 全部完成：

   | 组件 | 文件 | 状态 |
   |------|------|------|
   | 类型定义 | `wizard/types.py` | ✅ 完成 |
   | 提示器接口 | `wizard/prompts.py` | ✅ 完成 |
   | 会话管理 | `wizard/session.py` | ✅ 完成 |
   | Gateway 配置流程 | `wizard/flows/gateway.py` | ✅ 完成 |
   | Onboarding 流程 | `wizard/flows/onboarding.py` | ✅ 完成 |
   | Rich CLI 提示器 | `wizard/rich_prompter.py` | ✅ 完成 |
   | CLI 命令集成 | `cli/main.py` | ✅ 完成 |
   | 单元测试 | `tests/unit/wizard/test_wizard.py` | ✅ 通过 (25 tests) |

## Wizard 配置向导功能 (Phase 22)

### 核心功能
- **交互式配置**: 引导用户完成 LurkBot 初始设置
- **多种流程**: quickstart (快速) 和 advanced (高级) 模式
- **Gateway 配置**: 本地/远程网关设置
- **Session 管理**: 会话状态跟踪和错误处理
- **Rich CLI 界面**: 美观的终端交互体验

### CLI 命令
```bash
# 交互式配置向导
lurkbot wizard                    # 完整交互式设置
lurkbot wizard --flow quickstart  # 快速设置
lurkbot wizard --mode local       # 本地网关设置
lurkbot wizard --mode remote      # 远程网关设置

# 重置配置
lurkbot reset                     # 交互式重置
lurkbot reset --scope full        # 完全重置
lurkbot reset --scope config -f   # 强制重置配置
```

### 组件结构
```
src/lurkbot/wizard/
├── __init__.py              # 模块导出
├── types.py                 # 类型定义 (SetupMode, SetupFlow, WizardStep, etc.)
├── prompts.py               # 提示器接口 (Prompter 协议)
├── session.py               # 会话管理 (WizardSession, Deferred)
├── rich_prompter.py         # Rich CLI 提示器实现
└── flows/
    ├── __init__.py
    ├── gateway.py           # Gateway 配置流程
    └── onboarding.py        # Onboarding 主流程
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
| **Phase 22** | Wizard 配置向导 | ✅ 完成 |
| **Phase 23** | Infra 基础设施 | ⏳ 待开始 |

## Quick Start for Next Session

```bash
# 1. 运行测试确认当前状态
python -m pytest tests/main/ -xvs

# 2. 验证 Phase 22 Wizard 模块
python -m lurkbot.cli.main wizard --help

# 3. 验证所有测试通过
python -m pytest tests/unit/wizard/ -v

# 4. 开始 Phase 23 - Infra 基础设施
```

## Phase 22 完成的目录结构
```
src/lurkbot/
├── wizard/                      # Phase 22 [新增]
│   ├── __init__.py             # 模块导出
│   ├── types.py                # Wizard 类型定义
│   ├── prompts.py              # 提示器接口
│   ├── session.py              # 会话管理
│   ├── rich_prompter.py        # Rich CLI 提示器
│   └── flows/
│       ├── __init__.py
│       ├── gateway.py          # Gateway 配置流程
│       └── onboarding.py       # Onboarding 流程
├── tts/                         # Phase 21
│   └── ...
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
└── test_phase21_tts.py              # Phase 21 测试 (57 tests)

tests/unit/wizard/
└── test_wizard.py                   # Phase 22 测试 (25 tests) [新增]

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
| Phase 23 | Infra 基础设施 | P1 | 最后一个阶段，网络发现、SSH 隧道等 |

### Phase 23 Infra 基础设施设计预览

模块结构:
```
src/lurkbot/infra/
├── __init__.py
├── types.py                  # Infra 类型定义
├── discovery.py              # 网络发现服务
├── tunnel.py                 # SSH 隧道管理
├── health.py                 # 健康检查
└── metrics.py                # 指标收集
```

主要功能:
- **网络发现**: mDNS/Bonjour 服务发现
- **SSH 隧道**: 远程端口转发
- **健康检查**: 服务状态监控
- **指标收集**: Prometheus 格式指标

---

**Document Updated**: 2026-01-30
**Progress**: 22/23 Phases 完成 (95.7%)
**Total Tests**: 546 passing (Phase 6: 16, Phase 7: 40, Phase 8: 29, Phase 9: 12, Phase 10: 23, Phase 11: 34, Phase 12: 38, Phase 13: 26, Phase 14: 12, Phase 15: 24, Phase 16: 22, Phase 17: 27, Phase 18: 41, Phase 19: 49, Phase 20: 85, Phase 21: 57, Phase 22: 25), 2 skipped
**Next Action**:
1. 开始 Phase 23 - Infra 基础设施 (最后一个阶段)
2. 阶段完成后与 MoltBot 对比验证
3. 完成所有 23 个阶段后进行全面集成测试
