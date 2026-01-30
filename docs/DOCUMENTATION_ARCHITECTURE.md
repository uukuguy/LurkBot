# LurkBot 文档体系架构设计

> **文档版本**: 1.0
> **创建日期**: 2026-01-30
> **目标 URL**: https://github.com/uukuguy/lurkbot/docs

---

## 一、文档体系概览

### 1.1 设计原则

1. **用户优先**: 文档面向最终用户，而非内部开发者
2. **渐进式**: 从简单到复杂，逐步深入
3. **实用性**: 每个文档都有明确的使用场景
4. **可维护**: 结构清晰，易于更新

### 1.2 目标受众

| 受众类型 | 需求 | 对应文档 |
|----------|------|----------|
| **新用户** | 快速上手、了解功能 | 快速入门、功能概览 |
| **普通用户** | 日常使用、配置调整 | 用户指南、配置参考 |
| **高级用户** | 深度定制、扩展开发 | 高级配置、扩展开发 |
| **开发者** | 贡献代码、理解架构 | 开发者指南、架构文档 |

---

## 二、文档目录结构

```
docs/
├── index.md                          # 文档首页（导航入口）
├── README.md                         # 文档说明（GitHub 显示）
│
├── getting-started/                  # 快速入门
│   ├── index.md                      # 入门概览
│   ├── installation.md               # 安装指南
│   ├── quick-start.md                # 5 分钟快速开始
│   ├── first-bot.md                  # 创建第一个 Bot
│   └── concepts.md                   # 核心概念介绍
│
├── user-guide/                       # 用户指南
│   ├── index.md                      # 用户指南概览
│   ├── cli/                          # CLI 使用
│   │   ├── index.md                  # CLI 概览
│   │   ├── commands.md               # 命令参考
│   │   └── interactive-chat.md       # 交互式聊天
│   ├── channels/                     # 渠道配置
│   │   ├── index.md                  # 渠道概览
│   │   ├── telegram.md               # Telegram 配置
│   │   ├── discord.md                # Discord 配置
│   │   ├── slack.md                  # Slack 配置
│   │   └── more-channels.md          # 更多渠道
│   ├── agents/                       # Agent 配置
│   │   ├── index.md                  # Agent 概览
│   │   ├── models.md                 # AI 模型配置
│   │   ├── sessions.md               # 会话管理
│   │   └── subagents.md              # 子代理系统
│   ├── tools/                        # 工具使用
│   │   ├── index.md                  # 工具概览
│   │   ├── builtin-tools.md          # 内置工具列表
│   │   ├── tool-policies.md          # 工具策略
│   │   └── sandbox.md                # 沙箱隔离
│   └── configuration/                # 配置管理
│       ├── index.md                  # 配置概览
│       ├── config-file.md            # 配置文件格式
│       ├── environment.md            # 环境变量
│       └── auth-profiles.md          # 认证配置
│
├── advanced/                         # 高级功能
│   ├── index.md                      # 高级功能概览
│   ├── gateway.md                    # Gateway 服务
│   ├── skills.md                     # 技能系统
│   ├── hooks.md                      # Hooks 扩展
│   ├── auto-reply.md                 # 自动回复
│   ├── cron.md                       # 定时任务
│   ├── daemon.md                     # 守护进程
│   ├── browser.md                    # 浏览器自动化
│   ├── tts.md                        # 语音合成
│   └── media.md                      # 多媒体理解
│
├── developer/                        # 开发者文档
│   ├── index.md                      # 开发者指南概览
│   ├── architecture.md               # 系统架构
│   ├── contributing.md               # 贡献指南
│   ├── code-style.md                 # 代码规范
│   ├── testing.md                    # 测试指南
│   └── extending/                    # 扩展开发
│       ├── custom-tools.md           # 自定义工具
│       ├── custom-channels.md        # 自定义渠道
│       └── custom-skills.md          # 自定义技能
│
├── api/                              # API 参考
│   ├── index.md                      # API 概览
│   ├── gateway-protocol.md           # Gateway 协议
│   ├── rpc-methods.md                # RPC 方法
│   └── events.md                     # 事件类型
│
├── reference/                        # 参考手册
│   ├── index.md                      # 参考手册概览
│   ├── cli-reference.md              # CLI 完整参考
│   ├── config-reference.md           # 配置完整参考
│   ├── tool-reference.md             # 工具完整参考
│   └── glossary.md                   # 术语表
│
├── troubleshooting/                  # 故障排除
│   ├── index.md                      # 故障排除概览
│   ├── common-issues.md              # 常见问题
│   ├── faq.md                        # FAQ
│   └── debugging.md                  # 调试指南
│
└── design/                           # 设计文档（现有，保留）
    ├── ARCHITECTURE_DESIGN.md        # 架构设计
    ├── MOLTBOT_ANALYSIS.md           # MoltBot 分析
    └── ...                           # 其他设计文档
```

---

## 三、核心文档内容规划

### 3.1 快速入门 (getting-started/)

#### index.md - 入门概览
- LurkBot 是什么
- 核心功能列表
- 与 MoltBot 的关系
- 文档导航指引

#### installation.md - 安装指南
- 系统要求 (Python 3.12+, Docker)
- 使用 uv 安装
- 使用 pip 安装
- 从源码安装
- 验证安装

#### quick-start.md - 5 分钟快速开始
- 最小配置
- 启动 Gateway
- CLI 交互聊天
- 下一步指引

#### first-bot.md - 创建第一个 Bot
- 创建 Telegram Bot
- 配置 API Key
- 连接到 LurkBot
- 测试对话

#### concepts.md - 核心概念
- Gateway（网关）
- Agent（代理）
- Channel（渠道）
- Session（会话）
- Tool（工具）
- Skill（技能）

### 3.2 用户指南 (user-guide/)

#### CLI 使用
- 命令概览
- gateway 命令
- agent 命令
- config 命令
- 交互式聊天模式

#### 渠道配置
- 支持的渠道列表
- 各渠道配置步骤
- 允许列表配置
- 提及触发配置

#### Agent 配置
- 支持的 AI 模型
- 模型切换
- 会话类型
- 子代理使用

#### 工具使用
- 22 个内置工具介绍
- 工具策略配置
- 沙箱模式说明

### 3.3 高级功能 (advanced/)

- Gateway WebSocket 服务
- 技能系统扩展
- Hooks 事件钩子
- 自动回复规则
- 定时任务配置
- 守护进程模式
- 浏览器自动化
- TTS 语音合成
- 多媒体理解

### 3.4 开发者文档 (developer/)

- 系统架构概览
- 模块依赖关系
- 贡献流程
- 代码规范
- 测试编写
- 扩展开发指南

### 3.5 API 参考 (api/)

- Gateway WebSocket 协议
- RPC 方法列表
- 事件类型定义
- 数据结构说明

---

## 四、文档风格指南

### 4.1 语言规范

| 文档类型 | 语言 | 说明 |
|----------|------|------|
| 用户文档 | 英文 | 面向国际用户 |
| 设计文档 | 中文 | 内部开发参考 |
| API 参考 | 英文 | 技术规范 |
| 代码注释 | 英文 | 代码内文档 |

### 4.2 格式规范

1. **标题层级**: 最多 4 级 (# ## ### ####)
2. **代码块**: 必须指定语言类型
3. **表格**: 用于对比和列表信息
4. **提示框**: 使用 GitHub 风格的提示框

```markdown
> [!NOTE]
> 提示信息

> [!WARNING]
> 警告信息

> [!IMPORTANT]
> 重要信息
```

### 4.3 内容规范

1. **开头**: 简短说明文档目的
2. **目录**: 长文档需要目录
3. **示例**: 每个功能都有代码示例
4. **链接**: 相关文档互相链接

---

## 五、实施计划

### Phase 1: 基础框架
- [ ] 创建目录结构
- [ ] 编写 docs/index.md
- [ ] 编写 docs/README.md

### Phase 2: 快速入门
- [ ] installation.md
- [ ] quick-start.md
- [ ] first-bot.md
- [ ] concepts.md

### Phase 3: 用户指南
- [ ] CLI 使用文档
- [ ] 渠道配置文档
- [ ] Agent 配置文档
- [ ] 工具使用文档

### Phase 4: 高级功能
- [ ] Gateway 文档
- [ ] Skills 文档
- [ ] Hooks 文档
- [ ] 其他高级功能

### Phase 5: 开发者文档
- [ ] 架构文档
- [ ] 贡献指南
- [ ] 扩展开发

### Phase 6: 参考手册
- [ ] CLI 参考
- [ ] 配置参考
- [ ] API 参考

---

## 六、与现有文档的关系

### 6.1 保留的文档

| 现有文档 | 位置 | 用途 |
|----------|------|------|
| ARCHITECTURE_DESIGN.md | docs/design/ | 内部架构参考 |
| MOLTBOT_ANALYSIS.md | docs/design/ | MoltBot 分析 |
| LURKBOT_COMPLETE_DESIGN.md | docs/design/ | 完整设计方案 |
| PROJECT_COMPLETION_REPORT.md | docs/main/ | 项目完成报告 |

### 6.2 迁移计划

- `docs/design/` 保持不变，作为内部设计文档
- `docs/dev/` 保持不变，作为开发日志
- 新建的用户文档放在新目录结构中

---

## 七、文档发布

### 7.1 GitHub Pages 配置

```yaml
# .github/workflows/docs.yml
name: Deploy Docs
on:
  push:
    branches: [main]
    paths: ['docs/**']
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - name: Install MkDocs
        run: pip install mkdocs-material
      - name: Build and Deploy
        run: mkdocs gh-deploy --force
```

### 7.2 MkDocs 配置

```yaml
# mkdocs.yml
site_name: LurkBot Documentation
site_url: https://uukuguy.github.io/lurkbot/
repo_url: https://github.com/uukuguy/lurkbot
theme:
  name: material
  palette:
    primary: green
  features:
    - navigation.tabs
    - navigation.sections
    - search.suggest
nav:
  - Home: index.md
  - Getting Started:
    - Overview: getting-started/index.md
    - Installation: getting-started/installation.md
    - Quick Start: getting-started/quick-start.md
  - User Guide:
    - Overview: user-guide/index.md
    - CLI: user-guide/cli/index.md
    - Channels: user-guide/channels/index.md
  # ... 更多导航
```

---

**文档版本**: 1.0
**创建日期**: 2026-01-30
**状态**: 设计完成，待实施
