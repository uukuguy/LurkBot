<div align="center">

# 🦎 LurkBot

**企业级多渠道 AI 助手平台**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Tests: 625+](https://img.shields.io/badge/tests-625%2B%20passed-brightgreen.svg)](#测试)
[![Version: v1.0.0-alpha.1](https://img.shields.io/badge/version-v1.0.0--alpha.1-orange.svg)](#开发路线)

[功能特性](#功能特性) • [核心创新](#核心创新) • [快速开始](#快速开始) • [架构](#架构) • [文档](docs/index.md) • [English](README.md)

</div>

---

## 为什么选择 LurkBot？

**LurkBot** 是一个生产就绪的多渠道 AI 助手平台 Python 实现，具有业界首创的创新功能，如**九层工具策略引擎**和 **Bootstrap 文件系统**。专为企业和高级用户打造：

- **多渠道覆盖** — Telegram、Discord、Slack、企业微信、钉钉、飞书等
- **真正执行工具** — 22 个原生工具，Docker 沙箱隔离
- **企业级多租户** — 配额管理、审计日志、合规报告
- **生产级部署** — Docker + Kubernetes，支持 HPA、健康检查和监控
- **本地优先控制** — 你的数据、你的设备、你的规则

> *"一个真正能帮你做事的个人 AI 助手 — 安全、可扩展。"*

---

## 核心创新

### 🏆 业界首创功能

| 创新点 | 描述 |
|--------|------|
| **九层工具策略引擎** | 层级权限控制：Profile → Provider → Global → Agent → Channel → Sandbox → Subagent |
| **Bootstrap 文件系统** | 8 个 Markdown 文件定义 Agent 人格、记忆和行为 |
| **23 部分系统提示词生成器** | 模块化、可配置的提示词构建，支持动态部分 |
| **多维度会话隔离** | 5 种会话类型，自动路由和策略执行 |
| **自适应上下文压缩** | 智能分块与多阶段摘要 |
| **子代理通信协议** | 层级任务委派，深度限制（最多 3 层） |

### 🔧 技术亮点

```
┌─────────────────────────────────────────────────────────────────┐
│                      九层工具策略引擎                             │
├─────────────────────────────────────────────────────────────────┤
│  第 1 层: Profile 策略      (minimal/coding/messaging/full)      │
│  第 2 层: Provider Profile  (按 AI 提供商设置)                   │
│  第 3 层: 全局允许/拒绝     (系统级规则)                         │
│  第 4 层: 全局 Provider     (提供商特定全局规则)                 │
│  第 5 层: Agent 策略        (按代理配置)                         │
│  第 6 层: Agent Provider    (代理 + 提供商组合)                  │
│  第 7 层: 群组/频道         (频道特定规则)                       │
│  第 8 层: 沙箱策略          (隔离执行)                           │
│  第 9 层: 子代理策略        (子代理限制)                         │
└─────────────────────────────────────────────────────────────────┘
```

---

## 功能特性

### 核心平台 (v1.0.0 - 100% 完成)

| 功能 | 描述 |
|------|------|
| **多渠道支持** | Telegram、Discord、Slack、企业微信、钉钉、飞书 + 可扩展适配器 |
| **多模型 AI** | Claude、GPT、Gemini、Ollama、DeepSeek、Qwen、Kimi、ChatGLM（13+ 模型） |
| **22 个原生工具** | exec、read、write、edit、web_search、browser、memory、sessions、cron、canvas、tts... |
| **WebSocket Gateway** | 完整的控制平面，支持 RPC 协议 |
| **会话管理** | 5 种会话类型，JSONL 持久化 |
| **子代理系统** | 层级任务委派，通信协议 |

### 企业功能

| 功能 | 描述 |
|------|------|
| **多租户系统** | 4 个层级（免费/基础/专业/企业），配额管理 |
| **审计日志** | 完整操作审计，合规报告 |
| **告警系统** | 配额告警、异常检测、通知渠道 |
| **监控** | Prometheus 指标、性能仪表板 |
| **安全** | Docker 沙箱、九层策略、执行审批 |

### 生产部署

| 功能 | 描述 |
|------|------|
| **Docker** | 多阶段构建、非 root 用户、健康检查 |
| **Kubernetes** | Deployment、HPA、PDB、Ingress、ConfigMap、Secrets |
| **健康端点** | `/health`、`/ready`、`/live` 探针 |
| **可观测性** | 结构化日志、指标导出 |

### 中国生态支持 🇨🇳

| 功能 | 描述 |
|------|------|
| **企业消息平台** | 企业微信、钉钉、飞书 |
| **国产大模型** | DeepSeek、通义千问、Kimi、智谱 + 9 个更多模型（OpenAI 兼容 API） |
| **向量数据库** | sqlite-vec 轻量级语义搜索 |

---

## 架构

### 系统概览

```
┌─────────────────────────────────────────────────────────────────┐
│                          用户界面层                               │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │
│  │   TUI    │  │  Web UI  │  │   CLI    │  │  Wizard  │        │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘        │
└───────┼─────────────┼──────────────┼─────────────┼──────────────┘
        │             │              │             │
┌───────┴─────────────┴──────────────┴─────────────┴──────────────┐
│                    Gateway WebSocket 层                          │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │    Gateway 服务器 (FastAPI + WebSocket + RPC 协议)         │ │
│  │    - 协议处理  - 事件广播  - 会话管理                      │ │
│  └──────────────────────────┬─────────────────────────────────┘ │
└─────────────────────────────┼───────────────────────────────────┘
                              │
┌─────────────────────────────┴───────────────────────────────────┐
│                          核心服务层                               │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │   Agent     │  │   Session    │  │  Auto-Reply  │           │
│  │   Runtime   │  │   Manager    │  │  & Routing   │           │
│  └──────┬──────┘  └──────┬───────┘  └──────┬───────┘           │
│         │                │                  │                   │
│  ┌──────┴────────────────┴──────────────────┴───────┐          │
│  │                消息处理中心                        │          │
│  │  - 消息路由  - 队列管理  - 事件分发               │          │
│  └──────┬────────────────────────────────────┬──────┘          │
└─────────┼────────────────────────────────────┼──────────────────┘
          │                                    │
┌─────────┴────────────────────────────────────┴──────────────────┐
│                         渠道适配层                                │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │
│  │Telegram  │  │ Discord  │  │  Slack   │  │ 企业微信  │        │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                      │
│  │   钉钉   │  │   飞书   │  │   Mock   │                      │
│  └──────────┘  └──────────┘  └──────────┘                      │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                         支撑服务层                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  工具系统    │  │    安全      │  │   基础设施   │          │
│  │ - 22 工具   │  │ - 审计       │  │ - Tailscale  │          │
│  │ - 九层策略  │  │ - 沙箱       │  │ - Bonjour    │          │
│  │ - 插件      │  │ - 审批       │  │ - SSH 隧道   │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  Skills &    │  │    Hooks     │  │   多租户     │          │
│  │  Plugins     │  │    系统      │  │   系统       │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
```

### Bootstrap 文件系统

```
~/.lurkbot/
├── SOUL.md       # 核心人格与价值观（不传递给子代理）
├── IDENTITY.md   # 名称与外观（不传递给子代理）
├── USER.md       # 用户偏好（不传递给子代理）
├── AGENTS.md     # 工作区指南（传递给子代理）
├── TOOLS.md      # 工具配置（传递给子代理）
├── MEMORY.md     # 长期记忆（仅主会话）
├── HEARTBEAT.md  # 定期检查任务（仅主会话）
└── BOOTSTRAP.md  # 首次运行设置（完成后删除）
```

### 模块结构（30+ 模块）

```
src/lurkbot/
├── agents/           # AI Agent 运行时（bootstrap、system_prompt、compaction）
├── tools/            # 22 个内置工具 + 九层策略引擎
├── sessions/         # 会话管理 + JSONL 持久化
├── gateway/          # WebSocket 服务器 + RPC 协议 + FastAPI 应用
├── channels/         # 渠道适配器（Telegram、Discord、Slack、企业微信...）
├── plugins/          # 插件系统（加载器、管理器、沙箱）
├── skills/           # Skills 系统 + ClawHub 集成
├── hooks/            # 事件驱动 Hook 系统（10 种事件类型）
├── tenants/          # 多租户系统（配额、策略、审计）
├── monitoring/       # Prometheus 指标 + 性能追踪
├── security/         # 安全审计 + 沙箱隔离
├── infra/            # 8 个基础设施子系统
├── browser/          # Playwright 浏览器自动化
├── memory/           # 向量搜索 + 知识持久化
├── autonomous/       # Heartbeat + Cron 自主运行
├── acp/              # Agent 通信协议
├── daemon/           # 跨平台 Daemon 管理
├── tui/              # 终端 UI（Rich 组件）
├── tts/              # 文本转语音（Edge/ElevenLabs/OpenAI）
├── canvas/           # Canvas 渲染系统
├── media/            # 媒体理解（4 个提供商）
├── auto_reply/       # 自动回复队列系统
├── routing/          # 6 层消息路由
├── auth/             # 认证 + Profile 轮换
├── usage/            # 使用量追踪 + 成本计算
├── wizard/           # 配置向导
├── config/           # 配置管理
├── cli/              # 命令行接口（Typer）
└── logging/          # 结构化日志（Loguru）
```

---

## 快速开始

### 前置要求

- **Python 3.12+**
- **[uv](https://docs.astral.sh/uv/)**（推荐）或 pip
- **Docker**（可选，用于沙箱隔离和部署）

### 安装

```bash
# 克隆仓库
git clone https://github.com/uukuguy/lurkbot.git
cd lurkbot

# 安装依赖
make dev

# 验证安装
make test
```

### 配置

创建 `~/.lurkbot/.env`：

```bash
# AI 提供商（选择一个或多个）
LURKBOT_ANTHROPIC_API_KEY=sk-ant-...
LURKBOT_OPENAI_API_KEY=sk-...

# Telegram Bot（可选）
LURKBOT_TELEGRAM__BOT_TOKEN=123456:ABC...
LURKBOT_TELEGRAM__ENABLED=true
```

### 运行

```bash
# 启动 Gateway
lurkbot gateway --host 0.0.0.0 --port 18789
# Gateway listening on ws://127.0.0.1:18789

# 开始聊天（CLI 模式）
lurkbot agent chat
```

### Docker 部署

```bash
# 使用 Docker Compose 快速启动
cp .env.example .env
# 编辑 .env 填入 API 密钥
docker compose up -d

# 验证
curl http://localhost:18789/health
```

### Kubernetes 部署

```bash
# 应用所有配置
kubectl apply -k k8s/

# 验证
kubectl get pods -n lurkbot
kubectl port-forward svc/lurkbot-gateway 18789:18789 -n lurkbot
```

---

## 插件系统

LurkBot 提供强大的插件系统来扩展功能：

### 内置示例插件

| 插件 | 描述 | 权限 |
|------|------|------|
| **weather-plugin** | 通过 wttr.in API 获取实时天气 | network |
| **time-utils-plugin** | 多时区时间转换 | none |
| **system-info-plugin** | CPU、内存、磁盘监控 | filesystem |

### 快速示例

```python
# .plugins/hello-plugin/main.py
async def execute(context):
    name = context.input_data.get("name", "World")
    return {"message": f"Hello, {name}!"}
```

```bash
# 使用插件
lurkbot plugin exec hello-plugin --input '{"name": "Alice"}'
```

详见 [插件文档](docs/design/PLUGIN_USER_GUIDE.md)。

---

## 测试

### 测试统计

| 类别 | 测试数 | 状态 |
|------|--------|------|
| 集成测试 | 219 | ✅ 通过 |
| Phase 测试 | 343+ | ✅ 通过 |
| 单元测试 | 100+ | ✅ 通过 |
| **总计** | **625+** | **✅ 100% 通过** |

### 运行测试

```bash
# 运行所有测试
make test

# 带覆盖率运行
pytest --cov=src --cov-report=term-missing

# 运行特定测试
pytest tests/integration/test_e2e_chat_flow.py -xvs
```

---

## 文档

📚 **[完整文档](docs/index.md)**

### 快速链接

| 章节 | 描述 |
|------|------|
| [快速入门](docs/getting-started/index.md) | 安装、快速开始、第一个 Bot |
| [用户指南](docs/user-guide/index.md) | CLI、渠道、Agent、工具、配置 |
| [高级功能](docs/advanced/index.md) | Gateway、Hooks、Skills、Daemon、Cron |
| [开发者指南](docs/developer/index.md) | 架构、贡献、扩展 |
| [API 参考](docs/api/index.md) | CLI 参考、RPC 方法 |
| [部署指南](docs/deploy/DEPLOYMENT_GUIDE.md) | Docker、Kubernetes 部署 |

### 设计文档

- [架构设计](docs/design/ARCHITECTURE_DESIGN.md)
- [插件系统设计](docs/design/PLUGIN_SYSTEM_DESIGN.md)
- [中国生态指南](docs/design/CHINA_ECOSYSTEM_GUIDE.md)

---

## 技术栈

| 组件 | 技术 |
|------|------|
| **AI 框架** | PydanticAI 1.0+ |
| **Web 框架** | FastAPI + Uvicorn |
| **数据验证** | Pydantic 2.10+ |
| **CLI** | Typer + Rich |
| **日志** | Loguru |
| **包管理器** | uv |
| **容器** | Docker + Kubernetes |
| **向量数据库** | ChromaDB + sqlite-vec |
| **浏览器** | Playwright |

---

## 开发路线

### ✅ v1.0.0（当前版本）

- [x] 核心基础设施（Gateway、Agent Runtime、Sessions）
- [x] 22 个原生工具 + 九层策略引擎
- [x] 多渠道支持（7 个平台）
- [x] 多模型 AI（13+ 模型）
- [x] 插件系统（3 个示例插件）
- [x] 多租户系统（配额管理）
- [x] 监控 + 审计日志
- [x] Docker + Kubernetes 部署
- [x] 625+ 测试（100% 通过）

### 🔮 未来计划

- [ ] CI/CD 流水线（GitHub Actions + ArgoCD）
- [ ] 增强可观测性（Grafana 仪表板）
- [ ] 更多渠道适配器
- [ ] 插件市场

---

## 对比：Moltbot vs LurkBot

| 特性 | Moltbot (TypeScript) | LurkBot (Python) |
|------|---------------------|------------------|
| **语言** | Node.js 22+ | Python 3.12+ |
| **代码量** | ~411,783 行 | ~79,520 行 |
| **Agent 框架** | Pi SDK | PydanticAI |
| **多租户** | ❌ | ✅ |
| **监控** | 基础 | Prometheus |
| **K8s 部署** | ❌ | ✅ |
| **中国生态** | 部分 | 完整 |
| **状态** | 生产环境 | v1.0.0 生产环境 |

---

## 许可证

MIT 许可证 — 详见 [LICENSE](LICENSE) 文件。

---

## 致谢

LurkBot 灵感来自 [**OpenClaw/Moltbot**](https://github.com/openclaw/openclaw)。特别感谢开源 AI 助手社区。

---

<div align="center">

**基于 Python 构建 • 由 PydanticAI 驱动 • 生产就绪**

[⭐ GitHub 上点星](https://github.com/uukuguy/lurkbot) • [📖 文档](docs/index.md) • [🐛 问题反馈](https://github.com/uukuguy/lurkbot/issues)

</div>
