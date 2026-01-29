# Next Session Guide

## Session Context

**Last Session Date**: 2026-01-29
**Current Status**: 架构文档更新完成，Phase 5 部分完成
**Design Document**: `docs/design/LURKBOT_COMPLETE_DESIGN.md` (v2.2)
**Architecture Document**: `docs/design/MOLTBOT_COMPLETE_ARCHITECTURE.md` (已添加 7 个新章节)

## What Was Accomplished

### 今日完成的工作

1. **MoltBot 架构文档大幅更新** - 发现并记录了 7 个重要遗漏模块：

   | 章节 | 模块 | 代码量 |
   |------|------|--------|
   | 二十 | Auto-Reply 自动回复系统 | ~23K LOC |
   | 二十一 | Daemon 守护进程系统 | ~33 文件 |
   | 二十二 | Media Understanding 多媒体理解 | ~22 文件 |
   | 二十三 | Provider Usage 使用量监控 | ~19 文件 |
   | 二十四 | Routing 消息路由系统 | ~6 文件 |
   | 二十五 | Hooks 扩展系统 | ~30 文件 |
   | 二十六 | Security 安全审计系统 | ~11 文件 |

2. **LurkBot 设计文档更新 (v2.2)**：
   - 新增 Phase 12-17 实施计划
   - 总实施周期从 13 周扩展到 18 周
   - 功能检查清单从 27 项扩展到 37 项
   - 关键文件清单新增 6 个模块目录

3. **文档覆盖率提升**: 从 ~30% 提升到 ~85%

## Implementation Plan (17 Phases)

| Phase | 内容 | 状态 |
|-------|------|------|
| **Phase 1** | 项目重构 - 清理旧代码 | ✅ 完成 |
| **Phase 2** | PydanticAI 核心框架集成 | ✅ 完成 |
| **Phase 3** | Bootstrap 文件系统 + 系统提示词 | ✅ 完成 |
| **Phase 4** | 九层工具策略系统 | ✅ 完成 |
| **Phase 5** | 22 个原生工具实现 | 🔄 进行中 |
| **Phase 6** | 会话管理 + 子代理系统 | ⏳ 待开始 |
| **Phase 7** | Heartbeat + Cron 自主运行系统 | ⏳ 待开始 |
| **Phase 8** | Auth Profile + Context Compaction | ⏳ 待开始 |
| **Phase 9** | Gateway WebSocket 协议 | ⏳ 待开始 |
| **Phase 10** | 技能和插件系统 | ⏳ 待开始 |
| **Phase 11** | A2UI Canvas Host | ⏳ 待开始 |
| **Phase 12** | Auto-Reply + Routing | ⏳ **新增** |
| **Phase 13** | Daemon 守护进程 | ⏳ **新增** |
| **Phase 14** | Media Understanding | ⏳ **新增** |
| **Phase 15** | Provider Usage 监控 | ⏳ **新增** |
| **Phase 16** | Hooks 扩展系统 | ⏳ **新增** |
| **Phase 17** | Security 安全审计 | ⏳ **新增** |

## 新增模块概述

### Auto-Reply 系统 (Phase 12)
- **Reply Directives**: `/think`, `/verbose`, `/reasoning`, `/elevated`
- **Queue 模式**: steer, followup, collect, interrupt
- **流式响应**: 三层架构（Agent Stream → Event Stream → Block Reply）
- **命令注册**: ChatCommandDefinition 类型系统

### Daemon 系统 (Phase 13)
- **跨平台**: macOS (launchd), Linux (systemd), Windows (schtasks)
- **统一接口**: GatewayService 抽象
- **多实例**: CLAWDBOT_PROFILE 支持

### Media Understanding (Phase 14)
- **支持类型**: 图像、音频、视频、文档
- **降级策略**: 云 API → 本地 CLI
- **能力过滤**: 按模型能力选择处理器

### Provider Usage (Phase 15)
- **多窗口追踪**: 5h/7d/模型级
- **重置倒计时**: 自动计算
- **支持提供商**: Anthropic, OpenAI, Google, MiniMax 等

### Hooks 扩展 (Phase 16)
- **事件类型**: command, session, agent, gateway
- **发现机制**: workspace/hooks → ~/.clawdbot/hooks → bundled
- **预装钩子**: session-memory, command-logger, boot-md

### Security 审计 (Phase 17)
- **网络检查**: Gateway 绑定和认证
- **DM 策略**: open/disabled/locked
- **自动修复**: --fix 选项

## Quick Start for Next Session

```bash
# 1. 运行测试确认当前状态
python -m pytest tests/ -xvs

# 2. 查看更新后的设计文档
cat docs/design/LURKBOT_COMPLETE_DESIGN.md | head -200

# 3. 查看 MoltBot 架构文档（含新章节）
cat docs/design/MOLTBOT_COMPLETE_ARCHITECTURE.md | head -50

# 4. 选择下一步方向：
# 方案 A: 继续 Phase 5 - 完成剩余工具
# 方案 B: 开始 Phase 6 - 会话管理系统
# 方案 C: 跳到 Phase 12 - Auto-Reply 系统（消息处理核心）
```

## Key References

### 文档位置
```
docs/design/
├── MOLTBOT_ANALYSIS.md              # 基础分析
├── MOLTBOT_COMPLETE_ARCHITECTURE.md # 完整架构（26 章 + 附录）
└── LURKBOT_COMPLETE_DESIGN.md       # 复刻设计（v2.2, 17 阶段）
```

### 新增模块目录结构预览
```
src/lurkbot/
├── auto_reply/          # Phase 12 [新增]
│   ├── directives.py
│   ├── queue/
│   ├── streaming.py
│   └── commands.py
├── routing/             # Phase 12 [新增]
│   ├── session_key.py
│   └── dispatcher.py
├── daemon/              # Phase 13 [新增]
│   ├── service.py
│   ├── launchd.py
│   └── systemd.py
├── media/               # Phase 14 [新增]
│   └── understanding.py
├── hooks/               # Phase 16 [新增]
│   ├── registry.py
│   └── events.py
└── security/            # Phase 17 [新增]
    └── audit.py
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

### 新发现的重要模块优先级
| 模块 | 优先级 | 理由 |
|------|--------|------|
| Auto-Reply | **P0** | 消息处理核心，影响所有交互 |
| Daemon | P1 | 生产环境部署必需 |
| Routing | P1 | 多渠道消息分发 |
| Media | P1 | 多媒体支持 |
| Hooks | P2 | 扩展性 |
| Security | P2 | 安全审计 |
| Provider Usage | P2 | 成本监控 |

---

**Document Updated**: 2026-01-29
**Next Action**:
1. 继续 Phase 5 或开始 Phase 6
2. 考虑优先实现 Phase 12 (Auto-Reply) - 这是消息处理的核心
3. 阶段完成后与 MoltBot 对比验证
