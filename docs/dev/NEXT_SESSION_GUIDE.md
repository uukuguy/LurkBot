# Next Session Guide

## Session Context

**Last Session Date**: 2026-01-29
**Current Status**: Phase 5 进行中 - P0 ✅, P1 部分完成
**Design Document**: `docs/design/LURKBOT_COMPLETE_DESIGN.md`

## What Was Accomplished

### Phase 5: P1 工具实现 (今日新增)

完成了 4 个 P1 工具的实现：

**创建/更新文件**:
- `src/lurkbot/tools/builtin/memory_tools.py`: 内存工具（~350 行）
  - memory_search_tool - 关键词搜索（框架支持向量搜索）
  - memory_get_tool - 读取内存文件
  - MemoryManager - 内存管理器
  - 支持 MEMORY.md 和 memory/*.md 文件

- `src/lurkbot/tools/builtin/web_tools.py`: Web 工具（~400 行）
  - web_fetch_tool - 获取网页内容
  - web_search_tool - 网络搜索
  - html_to_markdown - HTML 转 Markdown
  - 支持 Tavily、Serper、Mock 搜索提供者
  - 带缓存功能

- `src/lurkbot/tools/builtin/message_tool.py`: 消息工具（~500 行）
  - message_tool - 多渠道消息发送
  - 支持操作: send, delete, react, pin, unpin, poll, thread, event, media
  - MessageChannel 基类 + CLIChannel 实现
  - 可扩展的渠道注册系统

- `tests/test_builtin_tools.py`: 新增 58 个测试用例

**测试结果**:
```
306 passed in 1.57s
```

## Implementation Plan (10 Phases)

| Phase | 内容 | 状态 |
|-------|------|------|
| **Phase 1** | 项目重构 - 清理旧代码，搭建新目录结构 | ✅ 完成 |
| **Phase 2** | PydanticAI 核心框架集成 | ✅ 完成 |
| **Phase 3** | Bootstrap 文件系统 + 系统提示词生成器 | ✅ 完成 |
| **Phase 4** | 九层工具策略系统 | ✅ 完成 |
| **Phase 5** | 22 个原生工具实现 | 🔄 进行中 (P0 ✅, P1 部分完成, P2 待开始) |
| **Phase 6** | 会话管理 + 子代理系统 | ⏳ 待开始 |
| **Phase 7** | Heartbeat + Cron 自主运行系统 | ⏳ 待开始 |
| **Phase 8** | Auth Profile + Context Compaction | ⏳ 待开始 |
| **Phase 9** | Gateway WebSocket 协议 | ⏳ 待开始 |
| **Phase 10** | 技能和插件系统 | ⏳ 待开始 |

## Phase 5 Progress

### P0 工具 ✅ 已完成
| 工具 | 文件 | 状态 |
|------|------|------|
| exec | exec_tool.py | ✅ |
| process | exec_tool.py | ✅ |
| read | fs_tools.py | ✅ |
| write | fs_tools.py | ✅ |
| edit | fs_tools.py | ✅ |
| apply_patch | fs_tools.py | ✅ |

### P1 工具 🔄 部分完成
| 工具 | 描述 | 状态 | 备注 |
|------|------|------|------|
| memory_search | 内存语义搜索 | ✅ | memory_tools.py |
| memory_get | 读取内存文件 | ✅ | memory_tools.py |
| web_search | 网络搜索 | ✅ | web_tools.py |
| web_fetch | 获取网页内容 | ✅ | web_tools.py |
| message | 发送渠道消息 | ✅ | message_tool.py |
| sessions_list | 列出会话 | ⏳ | 依赖 Phase 6 |
| sessions_history | 会话历史 | ⏳ | 依赖 Phase 6 |
| sessions_send | 发送消息到会话 | ⏳ | 依赖 Phase 6 |
| sessions_spawn | 创建新会话 | ⏳ | 依赖 Phase 6 |
| session_status | 会话状态 | ⏳ | 依赖 Phase 6 |
| agents_list | 代理列表 | ⏳ | 依赖 Phase 6 |

### P2 工具 ⏳ 待开始
| 工具 | 描述 | 状态 |
|------|------|------|
| browser | 浏览器自动化 | ⏳ |
| canvas | Canvas 绘制 | ⏳ |
| image | 图像理解 | ⏳ |
| cron | 定时任务 | ⏳ |
| gateway | 网关通讯 | ⏳ |
| nodes | 节点管理 | ⏳ |
| tts | 文本转语音 | ⏳ |

## Key References

### 已实现的工具模块
```python
# lurkbot.tools.builtin
from lurkbot.tools.builtin import (
    # P0 工具
    exec_tool, process_tool,
    read_tool, write_tool, edit_tool, apply_patch_tool,
    # P1 工具
    memory_search_tool, memory_get_tool,
    web_search_tool, web_fetch_tool,
    message_tool,
    # 通用
    ToolResult, json_result, error_result,
    read_string_param, read_number_param, read_bool_param,
    # 安全
    SafeOpenError, open_file_within_root_sync, is_path_within_root,
    # 配置
    MemorySearchConfig, WebSearchConfig, WebFetchConfig, MessageConfig,
)
```

### 工具文件清单
```
src/lurkbot/tools/builtin/
├── __init__.py         # 模块导出
├── common.py           # 通用类型和函数（~300 行）
├── exec_tool.py        # exec, process 工具（~600 行）
├── fs_safe.py          # 安全文件操作（~250 行）
├── fs_tools.py         # read, write, edit, apply_patch（~400 行）
├── memory_tools.py     # memory_search, memory_get（~350 行）
├── web_tools.py        # web_search, web_fetch（~400 行）
└── message_tool.py     # message（~500 行）
```

## Quick Start for Next Session

```bash
# 1. 运行测试确认当前状态
python -m pytest tests/ -xvs

# 2. 选择下一步方向：
# 方案 A: 继续 Phase 5 - 实现 P2 工具（browser, cron, gateway 等）
# 方案 B: 开始 Phase 6 - 会话管理系统（sessions_* 工具依赖此阶段）

# 3. 查看设计文档
# docs/design/LURKBOT_COMPLETE_DESIGN.md
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

### 依赖关系说明
- **sessions_* 工具** 依赖 Phase 6 的会话管理基础设施
- **gateway 工具** 依赖 Phase 9 的 WebSocket 协议实现
- **cron 工具** 依赖 Phase 7 的自主运行系统

---

**Document Updated**: 2026-01-29
**Next Action**:
1. 开始 Phase 6（会话管理）以解锁 sessions_* 工具
2. 或继续 Phase 5 实现 P2 工具（browser, cron, image 等）
