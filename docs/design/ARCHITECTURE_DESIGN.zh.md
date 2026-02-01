# LurkBot 架构设计文档

## 概述

LurkBot 是一个企业级多渠道 AI 助手平台，使用 Python 实现。v1.0.0 版本具有业界首创的创新特性，包括**九层工具策略引擎**、**Bootstrap 文件系统**和 **23 部分系统提示词生成器**。

**版本**: v1.0.0-alpha.1（内部集成测试）
**代码规模**: ~79,520 行 Python 代码
**测试**: 625+ 测试用例（100% 通过）
**模块**: 30+ 核心模块

## 系统架构

### 整体架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                          用户界面层                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │
│  │   TUI    │  │  Web UI  │  │   CLI    │  │  Wizard  │        │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘        │
└───────┼─────────────┼──────────────┼─────────────┼──────────────┘
        │             │              │             │
┌───────┴─────────────┴──────────────┴─────────────┴──────────────┐
│                    Gateway WebSocket 层                          │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │    Gateway 服务器 (FastAPI + WebSocket + RPC 协议)          │ │
│  │    - 协议处理  - 事件广播  - 会话管理                        │ │
│  └──────────────────────────┬─────────────────────────────────┘ │
└─────────────────────────────┼───────────────────────────────────┘
                              │
┌─────────────────────────────┴───────────────────────────────────┐
│                         核心服务层                               │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │   Agent     │  │   Session    │  │  自动回复    │           │
│  │   运行时    │  │   管理器     │  │  & 路由      │           │
│  └──────┬──────┘  └──────┬───────┘  └──────┬───────┘           │
│         │                │                  │                   │
│  ┌──────┴────────────────┴──────────────────┴───────┐          │
│  │                消息处理中心                        │          │
│  │  - 消息路由  - 队列管理  - 事件处理               │          │
│  └──────┬────────────────────────────────────┬──────┘          │
└─────────┼────────────────────────────────────┼──────────────────┘
          │                                    │
┌─────────┴────────────────────────────────────┴──────────────────┐
│                        渠道适配器层                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │
│  │Telegram  │  │ Discord  │  │  Slack   │  │  企业微信 │        │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                      │
│  │   钉钉   │  │   飞书   │  │   Mock   │                      │
│  └──────────┘  └──────────┘  └──────────┘                      │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                        支撑服务层                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  工具系统    │  │   安全模块   │  │   基础设施   │          │
│  │ - 22 工具   │  │ - 审计日志   │  │ - Tailscale  │          │
│  │ - 9层策略   │  │ - 沙箱隔离   │  │ - Bonjour    │          │
│  │ - 插件系统  │  │ - 执行审批   │  │ - SSH 隧道   │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   技能 &    │  │    Hooks     │  │   多租户     │          │
│  │   插件      │  │    系统      │  │   系统       │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
```

## 核心创新

### 1. 九层工具策略引擎

业界首创的分层权限控制系统（`tools/policy.py` 中 1021 行代码）：

```
┌─────────────────────────────────────────────────────────────────┐
│                      九层工具策略引擎                            │
├─────────────────────────────────────────────────────────────────┤
│  第1层: Profile 策略       (minimal/coding/messaging/full)      │
│  第2层: Provider Profile   (每个 AI 提供商的设置)               │
│  第3层: 全局允许/拒绝      (系统级规则)                         │
│  第4层: 全局 Provider      (提供商特定的全局规则)               │
│  第5层: Agent 策略         (每个 Agent 的配置)                  │
│  第6层: Agent Provider     (Agent + Provider 组合)              │
│  第7层: 群组/渠道          (渠道特定规则)                       │
│  第8层: 沙箱策略           (隔离执行)                           │
│  第9层: 子代理策略         (子代理限制)                         │
└─────────────────────────────────────────────────────────────────┘
```

**核心特性**：
- 通配符模式匹配（`*`、`group:*`）
- 工具组展开（`group:fs`、`group:runtime`）
- 插件工具动态注入
- 拒绝优先原则（Deny 始终优先）
- 特殊规则：`apply_patch` 继承 `exec` 权限

### 2. Bootstrap 文件系统

8 个 Markdown 文件定义 Agent 的个性和行为：

```
~/.lurkbot/
├── SOUL.md       # 核心个性和价值观（不传递给子代理）
├── IDENTITY.md   # 名称和外观（不传递给子代理）
├── USER.md       # 用户偏好（不传递给子代理）
├── AGENTS.md     # 工作区指南（传递给子代理）
├── TOOLS.md      # 工具配置（传递给子代理）
├── MEMORY.md     # 长期记忆（仅主会话）
├── HEARTBEAT.md  # 定期检查任务（仅主会话）
└── BOOTSTRAP.md  # 首次运行设置（完成后删除）
```

**核心特性**：
- 子代理白名单机制（仅 `AGENTS.md` 和 `TOOLS.md`）
- 内容截断策略（70% 头部 + 20% 尾部）
- 最大字符限制（20,000 字符）
- 动态加载和热更新

### 3. 23 部分系统提示词生成器

模块化、可配置的提示词构建（`agents/system_prompt.py` 中 592 行代码）：

```
1. Core Identity          # 核心身份
2. Runtime Info           # 运行时信息
3. Workspace Context      # 工作区上下文
4. Bootstrap Files        # Bootstrap 文件内容
5. Tool Descriptions      # 工具描述
6. Skills Prompt          # 技能提示
7. Model Aliases          # 模型别名
8. Reasoning Guidance     # 推理指导
9. Think Level            # 思考级别
10. Sandbox Info          # 沙箱信息
11. Elevated Mode         # 提权模式
12. Heartbeat Prompt      # 心跳提示
13. Auto-Reply Tokens     # 自动回复令牌
14. Message Tool Hints    # 消息工具提示
15. TTS Hints             # TTS 提示
16. Reaction Guidance     # 反应指导
17. Markdown Capability   # Markdown 能力
18. Owner Numbers         # 所有者号码
19. User Timezone         # 用户时区
20. Docs Path             # 文档路径
21. Workspace Notes       # 工作区备注
22. Extra System Prompt   # 额外系统提示
23. Reasoning Tag Hint    # 推理标签提示
```

### 4. 多维会话隔离

5 种会话类型，自动路由：

```python
class SessionType(str, Enum):
    MAIN = "main"           # 主会话
    GROUP = "group"         # 群组会话
    TOPIC = "topic"         # 话题会话
    DM = "dm"              # 私聊会话
    SUBAGENT = "subagent"  # 子代理会话
```

**会话键格式**：
```
main                                    # 主会话
telegram:group:123456                   # Telegram 群组
discord:topic:789012:thread:345678      # Discord 话题
telegram:dm:user123                     # Telegram 私聊
main:subagent:task-analyzer:abc123      # 子代理会话
```

### 5. 自适应上下文压缩

智能分块与多阶段摘要：

```python
# 1. 分块策略
chunk_messages_by_max_tokens(
    messages,
    max_tokens=4000,
    chunk_ratio=0.3  # 自适应调整
)

# 2. 多阶段摘要
summarize_in_stages(
    chunks,
    model="claude-3-haiku",
    merge_threshold=3
)

# 3. 自适应比例
compute_adaptive_chunk_ratio(
    total_tokens=50000,
    target_tokens=8000,
    base_ratio=0.3,
    min_ratio=0.1
)
```

## 核心模块

### 1. Gateway（网关）

**职责**：
- WebSocket 服务器作为系统控制平面
- 客户端连接管理
- 消息路由到 Channels 和 Agents
- RPC 接口提供
- 健康检查端点（`/health`、`/ready`、`/live`）

**关键文件**：
- `server.py` - WebSocket 服务器（~500 行）
- `app.py` - FastAPI 应用
- `protocol.py` - 协议定义

### 2. Agents（AI 代理）

**职责**：
- AI 模型集成（Claude、GPT、Gemini、Ollama 等）
- 会话管理
- 上下文维护
- 工具调用
- 子代理生成

**关键文件**：
- `runtime.py` - Agent 执行
- `bootstrap.py` - Bootstrap 文件加载（~400 行）
- `system_prompt.py` - 23 部分提示词生成器（592 行）
- `compaction.py` - 上下文压缩（~300 行）
- `subagent/` - 子代理通信协议

### 3. Tools（工具系统）

**职责**：
- 22 个内置工具
- 九层策略引擎
- 工具注册和发现
- 插件工具集成

**关键文件**：
- `policy.py` - 九层策略引擎（1021 行）
- `registry.py` - 工具注册
- `builtin/` - 22 个内置工具

**内置工具**：
| 类别 | 工具 |
|------|------|
| 文件系统 | read, write, edit, apply_patch |
| 运行时 | exec, process |
| 会话 | sessions_spawn, sessions_send, sessions_list, sessions_history, session_status, agents_list |
| 记忆 | memory_search, memory_get |
| 网络 | web_search, web_fetch |
| 自动化 | cron, gateway |
| 媒体 | image, canvas |
| 系统 | nodes, tts |
| 浏览器 | browser |

### 4. Sessions（会话管理）

**职责**：
- 会话生命周期管理
- JSONL 持久化
- 子代理深度限制（最大 3 层）
- 跨会话消息传递

**关键文件**：
- `store.py` - JSONL 持久化
- `manager.py` - 会话生命周期（~400 行）

### 5. Channels（渠道适配器）

**职责**：
- 消息平台适配器
- 消息格式转换
- 用户权限控制

**支持的渠道**：
- Telegram（python-telegram-bot）
- Discord（discord.py）
- Slack（slack-sdk）
- 企业微信（WeWork）
- 钉钉（DingTalk）
- 飞书（Feishu）
- Mock（测试用）

### 6. Plugins（插件系统）

**职责**：
- 插件发现和加载
- 插件生命周期管理
- 沙箱执行
- 权限控制

**插件类型**：
```python
class PluginType(str, Enum):
    CHANNEL = "channel"      # 渠道适配器
    TOOL = "tool"           # 工具插件
    HOOK = "hook"           # Hook 扩展
    SKILL = "skill"         # 技能插件
    MIDDLEWARE = "middleware" # 中间件
```

### 7. Tenants（多租户系统）

**职责**：
- 多租户管理
- 配额执行
- 策略管理
- 审计日志

**租户层级**：
```python
class TenantTier(str, Enum):
    FREE = "free"              # 免费版
    BASIC = "basic"            # 基础版
    PROFESSIONAL = "professional" # 专业版
    ENTERPRISE = "enterprise"   # 企业版
```

### 8. Infrastructure（基础设施）

8 个基础设施子系统：

| 子系统 | 描述 |
|--------|------|
| system_events | 跨会话事件队列 |
| system_presence | 节点在线状态 |
| tailscale | VPN 集成 |
| ssh_tunnel | SSH 隧道 |
| bonjour | mDNS 发现 |
| device_pairing | 设备配对 |
| exec_approvals | 执行审批 |
| voicewake | 语音唤醒 |

## 数据流

### 消息处理流程

```
1. 用户在 Telegram/Discord/Slack/企业微信/钉钉/飞书 发送消息
2. 渠道适配器接收并转换为内部格式
3. Gateway 路由消息到对应的 Session
4. Agent Runtime 处理消息：
   a. 加载 Bootstrap 文件
   b. 生成 23 部分系统提示词
   c. 应用 9 层工具策略
   d. 调用 AI 模型
5. AI 响应通过 Gateway 返回
6. 渠道适配器格式化并发送响应
```

### 子代理通信流程

```
1. Spawn（生成）
   └─> sessions_spawn(agent_id, prompt, label)

2. Announce（声明）
   └─> 子代理向父代理报告启动

3. Execute（执行）
   └─> 子代理独立执行任务

4. Report（报告）
   └─> sessions_send(parent_session, result)

5. Cleanup（清理）
   └─> 自动或手动关闭会话
```

## 技术栈

| 组件 | 技术 | 描述 |
|------|------|------|
| AI 框架 | PydanticAI 1.0+ | 现代 Python Agent 框架 |
| Web 框架 | FastAPI + Uvicorn | 异步 ASGI 服务器 |
| 数据验证 | Pydantic 2.10+ | 类型安全和数据验证 |
| CLI | Typer + Rich | 现代命令行界面 |
| 日志 | Loguru | 结构化日志 |
| 包管理 | uv | 快速 Python 包管理器 |
| 容器 | Docker + Kubernetes | 生产部署 |
| 向量数据库 | ChromaDB + sqlite-vec | 语义搜索 |
| 浏览器 | Playwright | 浏览器自动化 |

## 扩展点

### 添加新渠道

1. 继承 `ChannelAdapter` 基类
2. 实现 `start()`、`stop()`、`send()`、`send_typing()` 方法
3. 在配置中添加对应的 Settings 类
4. 在 CLI 中注册启动逻辑

### 添加新 AI 模型

1. 在 PydanticAI 中配置模型
2. 在配置中添加模型别名
3. 更新 Provider 设置

### 添加新工具

1. 使用 `@tool` 装饰器创建工具函数
2. 在工具注册表中注册
3. 添加到适当的工具组
4. 根据需要更新策略

### 添加新插件

1. 在 `.plugins/` 中创建插件目录
2. 定义 `plugin.json` 清单
3. 实现带有 `execute()` 函数的 `main.py`
4. 配置权限

## 配置管理

配置通过环境变量和配置文件管理：

- 环境变量前缀：`LURKBOT_`
- 嵌套分隔符：`__`
- 配置文件：`~/.lurkbot/config.json`

示例：
```bash
export LURKBOT_GATEWAY__PORT=18789
export LURKBOT_ANTHROPIC_API_KEY=sk-xxx
export LURKBOT_OPENAI_API_KEY=sk-xxx
```

## 生产部署

### Docker

```bash
# 构建并运行
docker compose up -d

# 健康检查
curl http://localhost:18789/health
```

### Kubernetes

```bash
# 应用所有清单
kubectl apply -k k8s/

# 验证
kubectl get pods -n lurkbot
```

### 健康检查端点

| 端点 | 描述 |
|------|------|
| `/health` | 通用健康检查 |
| `/ready` | 就绪探针 |
| `/live` | 存活探针 |

## 安全

### 沙箱隔离

- Docker 容器保护
- 资源限制（内存/CPU）
- 网络隔离
- 只读根文件系统

### 执行审批

- 命令白名单
- 交互式审批
- 安全检查

### 审计日志

- 完整操作审计
- 合规报告
- 异常检测
