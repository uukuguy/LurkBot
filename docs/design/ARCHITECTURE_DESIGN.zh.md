# LurkBot 架构设计文档

## 概述

LurkBot 是 moltbot 的 Python 重写版本，是一个多渠道 AI 助手平台。本文档描述系统的核心架构设计。

## 系统架构

### 整体架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                         LurkBot 系统                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐       │
│  │   Telegram   │    │   Discord    │    │    Slack     │       │
│  │   Channel    │    │   Channel    │    │   Channel    │       │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘       │
│         │                   │                   │                │
│         └───────────────────┼───────────────────┘                │
│                             │                                    │
│                             ▼                                    │
│                    ┌────────────────┐                            │
│                    │    Gateway     │                            │
│                    │  (WebSocket)   │                            │
│                    └────────┬───────┘                            │
│                             │                                    │
│                             ▼                                    │
│                    ┌────────────────┐                            │
│                    │  Agent Runtime │                            │
│                    │                │                            │
│                    │  ┌──────────┐  │                            │
│                    │  │  Claude  │  │                            │
│                    │  │   GPT    │  │                            │
│                    │  │  Gemini  │  │                            │
│                    │  └──────────┘  │                            │
│                    └────────────────┘                            │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 核心模块

#### 1. Gateway (网关)

**职责**：
- WebSocket 服务器，作为系统控制平面
- 管理客户端连接
- 路由消息到对应的 Channel 和 Agent
- 提供 RPC 接口

**关键文件**：
- `src/lurkbot/gateway/server.py` - 服务器实现
- `src/lurkbot/gateway/protocol.py` - 协议定义

#### 2. Agents (AI 代理)

**职责**：
- AI 模型集成（Claude、GPT、Gemini 等）
- 会话管理
- 上下文维护
- 工具调用

**关键文件**：
- `src/lurkbot/agents/base.py` - 基础类定义
- `src/lurkbot/agents/runtime.py` - 运行时管理

#### 3. Channels (渠道适配器)

**职责**：
- 消息平台适配（Telegram、Discord、Slack 等）
- 消息格式转换
- 用户权限控制

**关键文件**：
- `src/lurkbot/channels/base.py` - 基础类定义
- `src/lurkbot/channels/telegram.py` - Telegram 适配器

#### 4. CLI (命令行界面)

**职责**：
- 提供命令行操作入口
- 配置管理
- 服务启停控制

**关键文件**：
- `src/lurkbot/cli/main.py` - CLI 入口

## 数据流

### 消息处理流程

```
1. 用户在 Telegram/Discord/Slack 发送消息
2. Channel 适配器接收消息，转换为内部格式
3. Gateway 路由消息到对应的 Session
4. Agent Runtime 处理消息，调用 AI 模型
5. AI 响应通过 Gateway 返回
6. Channel 适配器格式化并发送响应
```

### WebSocket 协议

**消息类型**：
- `connect` - 连接握手
- `req` - RPC 请求
- `res` - RPC 响应
- `event` - 服务器推送事件
- `channel_message` - 渠道消息

## 技术选型

| 组件 | 技术 | 说明 |
|------|------|------|
| Web 框架 | FastAPI | HTTP/WebSocket 服务器 |
| 数据验证 | Pydantic | Schema 验证 |
| CLI | Typer | 命令行界面 |
| 日志 | Loguru | 结构化日志 |
| 包管理 | uv | 快速 Python 包管理器 |

## 扩展点

### 添加新的 Channel

1. 继承 `Channel` 基类
2. 实现 `start()`, `stop()`, `send()`, `send_typing()` 方法
3. 在配置中添加对应的 Settings 类
4. 在 CLI 中注册启动逻辑

### 添加新的 AI 模型

1. 继承 `Agent` 基类
2. 实现 `chat()` 和 `stream_chat()` 方法
3. 在 `AgentRuntime.get_agent()` 中添加模型识别逻辑

## 配置管理

配置通过环境变量和配置文件管理：

- 环境变量前缀：`LURKBOT_`
- 嵌套分隔符：`__`
- 配置文件：`~/.lurkbot/config.json`

示例：
```bash
export LURKBOT_GATEWAY__PORT=8080
export LURKBOT_ANTHROPIC_API_KEY=sk-xxx
```
