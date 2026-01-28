<div align="center">

# 🦎 LurkBot

**真正做事的 AI — Python 实现**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

[特性](#特性) • [安装](#安装) • [快速开始](#快速开始) • [文档](#文档) • [架构](#架构)

</div>

---

## 项目简介

**LurkBot** 是 [**moltbot**](https://github.com/moltbot/moltbot) 的忠实 Python 重写版本 — moltbot 是 2026 年初爆火的开源个人 AI 助手。LurkBot 专为喜欢 Python 生态的爱好者和开发者打造，在保持 moltbot 强大架构的同时，充分发挥 Python 的优势。

### 为什么选择 LurkBot？

- **Python 原生**：充分利用 Python 丰富的生态（FastAPI、asyncio、Docker SDK）
- **学习资源**：通过清晰、带类型注解的 Python 代码学习 AI 代理架构
- **生产就绪**：与 moltbot 同等的企业级设计，不同的实现语言
- **社区驱动**：为更喜欢 PyPI 而非 npm 的 Python 开发者打造

---

## 特性

### 核心能力

- **🔌 多渠道消息**：WhatsApp、Telegram、Discord、Slack、Signal、iMessage 等
- **🤖 多模型支持**：Claude、GPT、Gemini、Ollama（本地）及任何 OpenAI 兼容 API
- **🌐 WebSocket 网关**：本地优先的控制平面，管理会话、渠道和工具
- **🛠️ 工具执行**：浏览器自动化、文件操作、Shell 命令、自定义工具
- **🔒 沙箱隔离**：基于 Docker 的安全隔离（群聊、公开频道等不可信环境）
- **💬 会话管理**：持久化对话，上下文跟踪
- **📱 设备节点**：控制 iOS/macOS/Android 设备（相机、屏幕、位置）

### 架构亮点

- **网关中心设计**：单一控制平面路由所有消息
- **会话隔离**：按用户/渠道/主题隔离，可配置策略
- **工具策略**：细粒度控制每个会话可执行的操作
- **技能系统**：可扩展的插件架构支持自定义能力
- **流式响应**：通过 WebSocket 实时输出 AI 回复

---

## 安装

### 环境要求

- **Python 3.12+**
- **[uv](https://docs.astral.sh/uv/)**（推荐）或 pip
- **Docker**（可选，用于沙箱隔离）

### 快速安装

```bash
# 克隆仓库
git clone https://github.com/yourusername/lurkbot.git
cd lurkbot

# 安装依赖
make dev

# 验证安装
make test
```

### 配置

创建 `~/.lurkbot/.env` 文件：

```bash
# AI 提供商（选择其一）
LURKBOT_ANTHROPIC_API_KEY=sk-ant-...
LURKBOT_OPENAI_API_KEY=sk-...

# Telegram Bot（可选）
LURKBOT_TELEGRAM__BOT_TOKEN=123456:ABC...
LURKBOT_TELEGRAM__ENABLED=true
```

---

## 快速开始

### 启动网关

```bash
make gateway
# 网关监听在 ws://127.0.0.1:18789
```

### 交互式聊天（CLI）

```bash
lurkbot agent chat
# 直接与 Claude 对话
```

### 启用 Telegram

1. 通过 [@BotFather](https://t.me/botfather) 创建 Bot
2. 将 token 添加到 `.env`：`LURKBOT_TELEGRAM__BOT_TOKEN=...`
3. 重启网关：`make gateway`

---

## 文档

### 项目文档

- **[架构设计](docs/design/ARCHITECTURE_DESIGN.zh.md)**：系统架构与设计决策
- **[Moltbot 分析](docs/design/MOLTBOT_ANALYSIS.zh.md)**：原 TypeScript 实现的深度分析
- **[下次会话指南](docs/dev/NEXT_SESSION_GUIDE.md)**：开发路线图和优先级

### 外部资源

- **[Moltbot 官方文档](https://docs.molt.bot/)**：原项目文档
- **[Moltbot GitHub](https://github.com/moltbot/moltbot)**：TypeScript 参考实现

---

## 架构

### 系统概览

```
┌─────────────────────────────────────────────────────────────┐
│  Telegram   Discord   Slack   WhatsApp   Signal   iMessage  │
└────────────────────────┬────────────────────────────────────┘
                         │
                    ┌────▼────┐
                    │ Gateway │ (WebSocket 服务器)
                    └────┬────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
    ┌───▼───┐      ┌────▼────┐      ┌───▼────┐
    │ Agent │      │ Channel │      │  Tool  │
    │Runtime│      │Adapters │      │Registry│
    └───┬───┘      └─────────┘      └───┬────┘
        │                                │
    ┌───▼──────────┐              ┌─────▼─────┐
    │Claude/GPT/   │              │bash/文件/ │
    │Gemini/Ollama │              │浏览器/... │
    └──────────────┘              └───────────┘
```

### 关键设计模式

- **网关模式**：集中式消息路由和会话管理
- **适配器模式**：消息平台和 AI 模型的统一接口
- **策略模式**：按会话的工具策略和沙箱模式
- **插件模式**：可扩展的技能和自定义工具

详细架构请参阅 [ARCHITECTURE_DESIGN.zh.md](docs/design/ARCHITECTURE_DESIGN.zh.md)。

---

## 开发

### 项目结构

```
lurkbot/
├── src/lurkbot/
│   ├── gateway/          # WebSocket 服务器 + RPC 协议
│   ├── agents/           # AI 代理运行时 + 模型适配器
│   ├── channels/         # 消息平台适配器
│   ├── tools/            # 内置工具实现
│   ├── config/           # 配置管理
│   ├── cli/              # 命令行界面
│   └── utils/            # 日志、工具函数
├── tests/                # pytest 测试套件
├── docs/                 # 文档
│   ├── design/           # 架构文档（中英双语）
│   └── dev/              # 开发指南
└── Makefile              # 开发命令
```

### 常用命令

```bash
make help       # 显示所有可用命令
make dev        # 安装开发依赖
make test       # 运行 pytest 测试
make lint       # 运行 ruff 代码检查
make format     # 使用 ruff 格式化代码
make typecheck  # 运行 mypy 类型检查
make check      # 运行所有检查（lint + typecheck + test）
```

### 贡献指南

我们欢迎贡献！LurkBot 的目标是**忠实移植** moltbot，同时拥抱 Python 习惯用法：

- 遵循现有代码风格（ruff、mypy strict mode）
- 为新功能添加测试
- API 变更时更新文档
- 不确定时参考 moltbot 的 TypeScript 实现

---

## 开发路线

### ✅ Phase 1：基础搭建（已完成）
- [x] Gateway WebSocket 服务器
- [x] Agent 运行时（Claude 集成）
- [x] Telegram 渠道适配器
- [x] 配置系统
- [x] CLI 接口

### 🚧 Phase 2：工具系统（进行中）
- [ ] 工具注册表和策略引擎
- [ ] 内置工具（bash、文件操作、浏览器）
- [ ] Docker 沙箱隔离
- [ ] 工具调用与 AI 模型集成

### 📋 Phase 3：渠道扩展
- [ ] Discord 适配器
- [ ] Slack 适配器
- [ ] WhatsApp 适配器（Baileys）
- [ ] Signal 适配器

### 📋 Phase 4：高级特性
- [ ] 会话持久化（JSONL 格式）
- [ ] 技能系统
- [ ] 多代理协作
- [ ] 设备节点（iOS/macOS/Android）

---

## 对比：Moltbot vs LurkBot

| 特性 | Moltbot (TypeScript) | LurkBot (Python) |
|------|---------------------|------------------|
| **语言** | Node.js 22+ | Python 3.12+ |
| **包管理器** | pnpm | uv |
| **Web 框架** | Express | FastAPI |
| **数据验证** | TypeBox/Zod | Pydantic |
| **CLI** | Commander | Typer |
| **测试** | Vitest | pytest |
| **架构** | Gateway-Centric | Gateway-Centric |
| **状态** | 生产环境 | 开发中 |

---

## 开源许可

MIT License - 详见 [LICENSE](LICENSE) 文件。

---

## 致谢

LurkBot 是社区驱动的 [**moltbot**](https://github.com/moltbot/moltbot) Python 移植版本，原项目由 [Peter Steinberger](https://github.com/steipete) 创建。特别感谢 moltbot 社区创造了如此出色的 AI 助手平台。

---

<div align="center">

**Python 打造 • Moltbot 启发 • 社区驱动**

[⭐ Star on GitHub](https://github.com/yourusername/lurkbot) • [📖 阅读文档](docs/) • [💬 加入 Discord](#)

</div>
