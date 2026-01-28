# MoltBot 完整复刻设计报告与实施计划

## 任务目标

深入研究 MoltBot（TypeScript 原版），创建能够**完整复刻**其功能的 LurkBot（Python 版）设计与实施计划。

**核心原则**: 先忠实原版复刻，再考虑优化

---

## 第一部分：MoltBot 完整架构发现

### 1.1 之前分析未发现的关键组件

通过深入代码探索，发现以下**之前未提及**的重要系统：

#### A. 错误处理与恢复机制

**文件**: `/src/infra/errors.ts`, `/src/infra/retry-policy.ts`, `/src/infra/retry.ts`

```typescript
// 渠道特定的重试策略
Discord: 3次重试, 500ms-30s延迟, 0.1抖动, RateLimitError检测
Telegram: 3次重试, 400ms-30s延迟, 正则匹配(429, timeout, unavailable)

// 重试框架
retryAsync({
  shouldRetry: (error) => isRetryable(error),
  retryAfterMs: (error, attempt) => exponentialBackoff(attempt),
  onRetry: (error, attempt) => log.warn(`Retry ${attempt}`)
})
```

#### B. 认证配置文件系统（Auth Profiles）

**文件**: `/src/agents/auth-profiles/`

```
核心组件:
├── profiles.ts      # 凭据存储（ApiKey/Token/OAuth）
├── order.ts         # 轮换顺序管理
├── oauth.ts         # OAuth 令牌刷新
├── session-override.ts  # 会话级认证覆盖
├── external-cli-sync.ts # CLI 同步
└── doctor.ts        # 诊断和修复

ProfileUsageStats:
- lastUsed: 上次使用时间
- cooldownUntil: 冷却截止
- disabledUntil: 禁用截止
- failureCounts: { auth, format, rate_limit, billing, timeout, unknown }
```

#### C. 插件系统

**文件**: `/src/plugins/`, `/src/plugin-sdk/`

```
插件架构:
├── manifest-registry.ts  # 插件发现与验证
├── loader.ts            # 动态 ESM/CommonJS 加载
├── runtime/types.ts     # 100+ 运行时 API 注入
├── commands.ts          # 插件命令注册
├── http-path.ts         # URL 路由
├── schema-validator.ts  # Manifest 验证
├── enable.ts            # 生命周期管理
└── install.ts           # 包安装

插件运行时注入:
- 回复调度器、内存工具、频道操作
- 配置加载、会话管理
- 媒体处理（获取、调整大小、MIME检测）
- 带超时的命令执行
- 平台特定操作（Discord/Telegram/Slack）
```

#### D. 技能系统完整实现

**文件**: `/src/agents/skills/`

```yaml
# 技能 YAML 前置配置
name: skill-name
description: "..."
events: ["command:new", "session:start"]
requires:
  bins: ["jq", "curl"]
  env: ["API_KEY"]
install:
  - kind: brew
    formula: jq
```

```
技能组件:
├── workspace.ts      # 从 /skills 目录加载
├── plugin-skills.ts  # 从插件加载
├── bundled-dir.ts    # 内置技能
├── env-overrides.ts  # 环境变量覆盖
├── config.ts         # 配置过滤
└── frontmatter.ts    # YAML 解析

技能优先级: 工作区 > 受管 > 打包 > 额外目录
```

#### E. 消息格式与协议

**文件**: `/src/gateway/protocol/schema/`

```typescript
// Gateway 协议帧
ConnectParams { minProtocol, maxProtocol, client, auth }
HelloOk { type, protocol, server, features, snapshot }
RequestFrame { type: "req", id, method, params }
ResponseFrame { type: "res", id, ok, payload?, error? }
EventFrame { type: "event", event, payload }
TickEvent { ts }  // 心跳
ShutdownEvent { reason, restartExpectedMs? }

// 错误码
NOT_LINKED, NOT_PAIRED, AGENT_TIMEOUT, INVALID_REQUEST, UNAVAILABLE
```

#### F. 日志与监控系统

**文件**: `/src/logging/`

```
├── console.ts     # 子系统过滤、时间戳、ANSI颜色
├── logger.ts      # Pino日志、文件轮换、级别管理
├── subsystem.ts   # 每模块日志创建
└── levels.ts      # 日志级别规范化
```

#### G. 配置系统架构

**文件**: `/src/config/`

```
├── zod-schema.*.ts      # Zod 验证
├── config.ts            # 文件 I/O + JSONL
├── validation.ts        # Schema 强制执行
├── paths.ts             # 目录结构解析
├── sessions.json        # 会话元数据
├── talk.ts              # 对话语气
├── types.tts.ts         # TTS 配置
└── types.msteams.ts     # 平台特定
```

#### H. 子代理通信协议

**文件**: `/src/auto-reply/reply/commands-subagents.ts`

```
指令语法:
[[subagent:agent-id]]
命令内容
[[/subagent]]

执行流程:
1. 主代理发出 [[subagent:id]] 指令
2. Gateway 解析指令
3. 转发到子代理（带上下文）
4. 等待子代理完成
5. 集成响应到主消息
```

#### I. 内存系统

**文件**: `/src/memory/`

```
├── embeddings/          # 多提供商（OpenAI、Gemini、Node-Llama）
├── sqlite.ts, sqlite-vec.ts  # 向量存储
├── search-manager.ts    # 语义搜索
├── memory-schema.ms     # 数据库初始化
└── sync-*.ts           # 文件同步
```

#### J. 路由系统

**文件**: `/src/routing/`

```
├── resolve-route.ts   # 频道→代理映射
├── session-key.ts     # 分层会话范围
└── bindings.ts        # 频道-代理亲和规则
```

---

### 1.2 Bootstrap Files 完整内容

#### 文件位置与作用

| 文件 | 作用 | 主会话 | 子代理 | 群组 |
|------|------|--------|--------|------|
| **SOUL.md** | 人格核心（不可覆盖） | ✅ | ❌ | ✅ |
| **IDENTITY.md** | 身份认同（名字、emoji） | ✅ | ❌ | ✅ |
| **USER.md** | 用户偏好（时区、称呼） | ✅ | ❌ | ✅ |
| **AGENTS.md** | 工作区指导和规则 | ✅ | ✅ | ✅ |
| **TOOLS.md** | 本地工具和配置说明 | ✅ | ✅ | ✅ |
| **HEARTBEAT.md** | 心跳任务列表（可选） | ✅ | ❌ | ❌ |
| **MEMORY.md** | 长期记忆 | ✅ | ❌ | ❌ |
| **BOOTSTRAP.md** | 首次运行仪式（完成后删除） | ✅ | ❌ | ❌ |

#### SOUL.md 核心内容

```markdown
## Core Truths
- Be genuinely helpful, not performatively helpful
- Have opinions; be resourceful before asking
- Earn trust through competence
- Remember you're a guest in their life

## Boundaries
- Private things stay private
- Ask before acting externally
- Never send half-baked replies to messaging surfaces
```

#### AGENTS.md 核心责任（每次会话开始）

```markdown
1. 读取 SOUL.md（你是谁）
2. 读取 USER.md（你帮助谁）
3. 读取 memory/YYYY-MM-DD.md（今天和昨天的上下文）
4. 如果主会话: 读取 MEMORY.md（长期记忆）

心跳系统:
- 定期检查（邮件、日历、提及、天气）
- 在 memory/heartbeat-state.json 中追踪最后检查时间
- 进行记忆维护（整理日报并更新 MEMORY.md）
```

---

### 1.3 完整工具列表（22个原生工具）

#### 会话管理工具（6个）

| 工具 | 功能 | 子代理限制 |
|------|------|-----------|
| `sessions_spawn` | 生成隔离子代理会话 | 🚫 禁用 |
| `sessions_send` | 跨会话消息发送 | 🚫 禁用 |
| `sessions_list` | 列出可访问会话 | 🚫 禁用 |
| `sessions_history` | 获取会话历史 | 🚫 禁用 |
| `session_status` | 查询会话状态 | 🚫 禁用 |
| `agents_list` | 列出可用代理 | 🚫 禁用 |

#### 定时任务（1个）

| 工具 | 功能 |
|------|------|
| `cron` | 定时任务管理（status/list/add/update/remove/run/runs/wake） |

```typescript
// Cron 调度类型
"at": 单次执行 → { kind: "at", atMs: <时间戳> }
"every": 周期执行 → { kind: "every", everyMs: <间隔> }
"cron": Cron表达式 → { kind: "cron", expr: "0 9 * * MON" }

// Payload 类型
"systemEvent": 向主会话注入文本事件
"agentTurn": 运行隔离会话中的代理任务
```

#### 通信工具（1个）

| 工具 | 功能 |
|------|------|
| `message` | 多渠道消息发送（send/delete/react/pin/poll/thread/event/media） |

#### 内容获取（2个）

| 工具 | 功能 |
|------|------|
| `web_search` | 网络搜索（Brave/Perplexity） |
| `web_fetch` | 获取网页内容 |

#### 媒体和浏览（3个）

| 工具 | 功能 |
|------|------|
| `browser` | 无头浏览器控制 |
| `image` | 图像生成/处理 |
| `canvas` | 可视化画布 |

#### 内存工具（2个）

| 工具 | 功能 | 子代理限制 |
|------|------|-----------|
| `memory_search` | 语义搜索 MEMORY.md | 🚫 禁用 |
| `memory_get` | 精确读取内存文件 | 🚫 禁用 |

#### 系统工具（2个）

| 工具 | 功能 |
|------|------|
| `nodes` | 节点发现和远程命令 |
| `gateway` | Gateway API 桥接 |

#### TTS（1个）

| 工具 | 功能 |
|------|------|
| `tts` | 文本转语音 |

#### Pi Coding Tools（4个）

| 工具 | 功能 |
|------|------|
| `bash` | Shell 命令执行 |
| `read` | 文件读取 |
| `write` | 文件写入 |
| `edit` / `apply_patch` | 文件编辑 |

---

### 1.4 九层工具策略系统

```
Layer 1: Profile-based     → 根据认证配置过滤（minimal/coding/messaging/full）
Layer 2: Provider-based    → 提供商能力（OpenAI/Anthropic/Ollama）
Layer 3: Model-based       → 不同模型支持不同工具
Layer 4: Global exclusions → 全局禁用的工具
Layer 5: Agent-type        → embedded/cli/web 不同代理类型
Layer 6: Group/Channel     → 群组聊天限制危险工具
Layer 7: Sandbox mode      → 沙箱模式禁用文件系统工具
Layer 8: Subagent          → 子代理限制递归生成
Layer 9: Plugin merge      → 合并插件注册的工具
```

**工具分组定义**:

```typescript
TOOL_GROUPS = {
  "group:memory":    ["memory_search", "memory_get"],
  "group:web":       ["web_search", "web_fetch"],
  "group:fs":        ["read", "write", "edit", "apply_patch"],
  "group:runtime":   ["exec", "process"],
  "group:sessions":  ["sessions_*"],
  "group:ui":        ["browser", "canvas"],
  "group:automation":["cron", "gateway"],
  "group:messaging": ["message"],
  "group:nodes":     ["nodes"],
  "group:moltbot":   [/* 所有22个原生工具 */]
}
```

---

### 1.5 系统提示词完整结构

**生成入口**: `buildEmbeddedSystemPrompt()`

```
1.  身份行: "You are a personal assistant running inside Moltbot."
2.  ## Tooling - 可用工具列表和说明
3.  ## Tool Call Style - 何时说明工作
4.  ## Moltbot CLI Quick Reference
5.  ## Skills (mandatory) - 技能描述和加载指导
6.  ## Memory Recall - 在使用前搜索记忆
7.  ## User Identity - 所有者号码（如果配置）
8.  ## Current Date & Time - 时区信息
9.  ## Workspace - 工作目录和笔记
10. ## Documentation - Moltbot 文档路径
11. [如果沙盒] ## Sandbox - 沙盒限制
12. ## Workspace Files (injected) - 注入的启动文件
13. ## Reply Tags - 本地回复/引用标签
14. ## Messaging - message 工具使用
15. ## Voice (TTS) - 语音提示
16. [如果子代理] ## Subagent Context 或 [如果群组] ## Group Chat Context
17. [如果推理] ## Reasoning Format
18. # Project Context - 注入的启动文件内容
19. ## Silent Replies - SILENT_REPLY_TOKEN 使用
20. ## Heartbeats - 心跳 ack 处理
21. ## Runtime - 运行时信息行
```

**Runtime 行示例**:
```
Runtime: agent=main | host=m1-max | os=macOS (arm64) | node=22.0.0 |
model=claude-opus-4-5-20251101 | repo=/Users/user/projects |
channel=discord | thinking=medium
```

---

## 第二部分：Python 智能体框架深度评估

### 2.1 候选框架对比

| 特性 | LangGraph | PydanticAI | Pi SDK (原版) |
|------|-----------|------------|--------------|
| **成熟度** | 1.0 稳定版 (2025.10) | V1 (2025.9) | 成熟 |
| **Tool Use Loop** | ✅ 图形节点 | ✅ 内置循环 | ✅ agentLoop |
| **状态持久化** | ✅ 多后端 (SQLite/Postgres/Memory) | ⚠️ 基础 | ✅ 完整 |
| **Human-in-the-Loop** | ✅ `interrupt()` | ⚠️ 需自实现 | ✅ 完整 |
| **流式事件** | ✅ 完整 | ✅ 完整 | ✅ 完整 |
| **MCP 支持** | ✅ 通过 langchain-mcp-adapters | ✅ 原生 | N/A |
| **类型安全** | ⚠️ 一般 | ✅ 优秀 (Pydantic) | TypeScript |
| **复杂工作流** | ✅ 优秀（图形） | ⚠️ 基础 | ✅ 良好 |
| **学习曲线** | 陡峭（图形概念） | 平缓（Python 原生） | 中等 |
| **社区/文档** | ✅ 大型生态 | ✅ 增长中 | 小众 |

### 2.2 框架能力详细分析

#### LangGraph 优势

```python
# 1. 完整的 Human-in-the-Loop
from langgraph.types import interrupt, Command
from langgraph.checkpoint.memory import InMemorySaver

def approval_node(state):
    approval = interrupt({
        "question": "Do you approve?",
        "proposal": state["messages"][-1]["content"]
    })
    if approval:
        return {"messages": [{"role": "system", "content": "Approved"}]}
    return {"messages": [{"role": "system", "content": "Rejected"}]}

# 恢复执行
for chunk in graph.stream(Command(resume="approved"), config):
    print(chunk)

# 2. 多后端持久化
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.checkpoint.postgres import PostgresSaver

checkpointer = SqliteSaver.from_conn_string("sessions.db")
graph = workflow.compile(checkpointer=checkpointer)

# 3. MCP 集成
from langchain_mcp_adapters.client import MultiServerMCPClient

client = MultiServerMCPClient({
    "math": {"command": "python", "args": ["math_server.py"], "transport": "stdio"},
    "weather": {"url": "http://localhost:8000/mcp", "transport": "streamable_http"}
})
tools = await client.get_tools()
```

#### PydanticAI 优势

```python
# 1. 类型安全的工具定义
from pydantic_ai import Agent, RunContext
from pydantic import BaseModel

class WeatherResult(BaseModel):
    temperature: float
    condition: str

agent = Agent[WeatherService, WeatherResult](
    'openai:gpt-4o',
    deps_type=WeatherService,
    output_type=WeatherResult,
)

@agent.tool
async def get_weather(ctx: RunContext[WeatherService], city: str) -> str:
    return await ctx.deps.fetch_weather(city)

# 2. 完整的流式事件
async for event in agent.run_stream_events(prompt):
    if isinstance(event, PartDeltaEvent):
        if isinstance(event.delta, TextPartDelta):
            print(event.delta.content_delta, end="")
    elif isinstance(event, FunctionToolCallEvent):
        print(f"Tool: {event.part.tool_name}")
```

### 2.3 框架选型建议

**推荐方案**: **LangGraph 作为核心框架**

**理由**:

1. **Human-in-the-Loop 原生支持** - MoltBot 的审批系统可以直接映射到 `interrupt()`
2. **状态持久化成熟** - SQLite/Postgres 后端直接可用
3. **复杂工作流** - 图形结构适合 MoltBot 的多阶段处理
4. **MCP 集成** - langchain-mcp-adapters 提供完整支持
5. **生态成熟** - 1.0 稳定版，大量生产案例

**可选方案**: **LangGraph + PydanticAI 混合**

- 用 PydanticAI 定义工具和验证（类型安全）
- 用 LangGraph 编排工作流（状态管理）

---

## 第三部分：完整复刻实施计划

### 3.1 架构映射

```
MoltBot (TypeScript)              LurkBot (Python)
─────────────────────────────────────────────────────────
Pi SDK agentLoop              →   LangGraph StateGraph
Pi SDK Agent                  →   LangGraph CompiledGraph
Pi SDK tools                  →   LangGraph ToolNode
Pi SDK interrupt              →   LangGraph interrupt()
Pi SDK checkpointer           →   LangGraph SqliteSaver
Pi SDK events                 →   LangGraph stream()
Bootstrap files               →   lurkbot.agents.bootstrap
System prompt                 →   lurkbot.agents.system_prompt
Tool policy                   →   lurkbot.tools.policy
Auth profiles                 →   lurkbot.auth.profiles
Plugins                       →   lurkbot.plugins
Skills                        →   lurkbot.skills
Memory (sqlite-vec)           →   lurkbot.memory (sqlite-vec)
Gateway protocol              →   lurkbot.gateway.protocol
```

### 3.2 实施阶段

#### Phase 1: 核心 Agent 框架（2周）

**目标**: 用 LangGraph 实现 MoltBot 的 Agent Loop

```python
# 文件: src/lurkbot/agents/graph.py

from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import interrupt, Command
from langgraph.prebuilt import ToolNode

class AgentState(MessagesState):
    """扩展消息状态"""
    session_id: str
    session_type: str  # main/group/dm/topic
    workspace: str
    tools_enabled: list[str]
    approval_pending: dict | None

def build_agent_graph(
    tools: list,
    checkpointer: SqliteSaver,
    system_prompt: str,
) -> CompiledGraph:
    """构建 LangGraph Agent"""

    builder = StateGraph(AgentState)

    # 节点定义
    builder.add_node("call_model", call_model_node)
    builder.add_node("execute_tools", ToolNode(tools))
    builder.add_node("approval", approval_node)

    # 边定义
    builder.add_edge(START, "call_model")
    builder.add_conditional_edges(
        "call_model",
        route_after_model,
        {
            "tools": "execute_tools",
            "approval": "approval",
            "end": END,
        }
    )
    builder.add_edge("execute_tools", "call_model")
    builder.add_conditional_edges(
        "approval",
        route_after_approval,
        {
            "execute": "execute_tools",
            "reject": "call_model",
        }
    )

    return builder.compile(checkpointer=checkpointer)

async def approval_node(state: AgentState):
    """Human-in-the-Loop 审批节点"""
    pending = state["approval_pending"]
    if not pending:
        return state

    # 使用 LangGraph interrupt 等待用户决策
    decision = interrupt({
        "type": "approval_request",
        "tool_name": pending["tool_name"],
        "command": pending.get("command"),
        "args": pending["args"],
        "expires_in": 300,  # 5分钟
    })

    if decision == "approve":
        return {**state, "approval_pending": None}
    else:
        return {
            **state,
            "approval_pending": None,
            "messages": state["messages"] + [{
                "role": "tool",
                "content": f"Tool execution denied: {pending['tool_name']}",
                "tool_call_id": pending["tool_call_id"],
            }]
        }
```

#### Phase 2: Bootstrap 和系统提示词（1周）

**目标**: 完整复刻 MoltBot 的提示词架构

```python
# 文件: src/lurkbot/agents/bootstrap.py

from pathlib import Path
from dataclasses import dataclass

BOOTSTRAP_FILES = [
    "SOUL.md", "IDENTITY.md", "USER.md", "AGENTS.md",
    "TOOLS.md", "HEARTBEAT.md", "MEMORY.md", "BOOTSTRAP.md"
]

SUBAGENT_ALLOWLIST = {"AGENTS.md", "TOOLS.md"}

@dataclass
class BootstrapFiles:
    soul: str | None = None
    identity: str | None = None
    user: str | None = None
    agents: str | None = None
    tools: str | None = None
    heartbeat: str | None = None
    memory: str | None = None
    bootstrap: str | None = None

async def load_bootstrap_files(
    workspace_dir: str,
    session_type: str,
) -> BootstrapFiles:
    """加载 Bootstrap 文件"""
    workspace = Path(workspace_dir)
    files = BootstrapFiles()

    for filename in BOOTSTRAP_FILES:
        # 子代理只加载允许列表中的文件
        if session_type != "main" and filename not in SUBAGENT_ALLOWLIST:
            continue

        # 群组会话不加载 MEMORY.md
        if session_type == "group" and filename == "MEMORY.md":
            continue

        filepath = workspace / filename
        if filepath.exists():
            content = await _read_and_trim(filepath, max_chars=20_000)
            setattr(files, filename.replace(".md", "").lower(), content)

    return files

async def _read_and_trim(path: Path, max_chars: int) -> str:
    """读取并截断文件（保留头70%+尾20%）"""
    content = path.read_text()
    if len(content) <= max_chars:
        return content

    head_size = int(max_chars * 0.7)
    tail_size = int(max_chars * 0.2)
    return (
        content[:head_size] +
        "\n\n[... content trimmed ...]\n\n" +
        content[-tail_size:]
    )
```

#### Phase 3: 工具系统和策略（1.5周）

**目标**: 实现九层工具策略系统

```python
# 文件: src/lurkbot/tools/policy.py

from dataclasses import dataclass, field
from enum import Enum

class ToolProfile(str, Enum):
    MINIMAL = "minimal"
    CODING = "coding"
    MESSAGING = "messaging"
    FULL = "full"

TOOL_GROUPS = {
    "group:memory": ["memory_search", "memory_get"],
    "group:web": ["web_search", "web_fetch"],
    "group:fs": ["read", "write", "edit", "apply_patch"],
    "group:runtime": ["bash", "exec"],
    "group:sessions": [
        "sessions_spawn", "sessions_send", "sessions_list",
        "sessions_history", "session_status"
    ],
    "group:ui": ["browser", "canvas"],
    "group:automation": ["cron", "gateway"],
    "group:messaging": ["message"],
}

TOOL_PROFILES = {
    ToolProfile.MINIMAL: {
        "allow": ["session_status"]
    },
    ToolProfile.CODING: {
        "allow": [
            "group:fs", "group:runtime", "group:sessions",
            "group:memory", "image"
        ]
    },
    ToolProfile.MESSAGING: {
        "allow": [
            "group:messaging", "sessions_list", "sessions_history",
            "sessions_send", "session_status"
        ]
    },
    ToolProfile.FULL: {
        "allow": ["*"]
    }
}

SUBAGENT_DENY_LIST = [
    "sessions_list", "sessions_history", "sessions_send",
    "sessions_spawn", "gateway", "agents_list", "session_status",
    "cron", "memory_search", "memory_get"
]

@dataclass
class ToolPolicyContext:
    profile: ToolProfile = ToolProfile.FULL
    provider: str = "anthropic"
    model: str = ""
    session_type: str = "main"
    channel: str = ""
    sandbox_mode: bool = False
    is_subagent: bool = False
    global_allow: list[str] = field(default_factory=list)
    global_deny: list[str] = field(default_factory=list)
    agent_allow: list[str] = field(default_factory=list)
    agent_deny: list[str] = field(default_factory=list)

def filter_tools_by_policy(
    tools: list,
    context: ToolPolicyContext,
) -> list:
    """应用九层策略过滤"""
    result = list(tools)

    # Layer 1: Profile
    result = _filter_by_profile(result, context.profile)

    # Layer 2: Provider
    result = _filter_by_provider(result, context.provider)

    # Layer 3: Model
    result = _filter_by_model(result, context.model)

    # Layer 4: Global exclusions
    result = _filter_by_list(result, context.global_allow, context.global_deny)

    # Layer 5: Agent-type
    result = _filter_by_agent_type(result, context.session_type)

    # Layer 6: Group/Channel
    result = _filter_by_channel(result, context.channel, context.session_type)

    # Layer 7: Sandbox
    if context.sandbox_mode:
        result = _filter_by_sandbox(result)

    # Layer 8: Subagent
    if context.is_subagent:
        result = [t for t in result if t.name not in SUBAGENT_DENY_LIST]

    # Layer 9: Plugin tools (merged elsewhere)

    return result

def _expand_groups(items: list[str]) -> set[str]:
    """展开工具组"""
    expanded = set()
    for item in items:
        if item.startswith("group:"):
            expanded.update(TOOL_GROUPS.get(item, []))
        else:
            expanded.add(item)
    return expanded
```

#### Phase 4: 自主运行能力（2周）

**目标**: 实现 Heartbeat、Cron、Sessions Spawn/Send

（详细代码见计划文件）

#### Phase 5: Context Compaction（1周）

**目标**: 实现自动上下文压缩

#### Phase 6: Gateway 和渠道适配器（1.5周）

**目标**: 实现 WebSocket Gateway 和多渠道支持

#### Phase 7: 内存系统（1周）

**目标**: 实现向量搜索和长期记忆

---

### 3.3 验证计划

#### 单元测试

```bash
# 核心组件测试
pytest tests/test_bootstrap.py -xvs
pytest tests/test_system_prompt.py -xvs
pytest tests/test_tool_policy.py -xvs
pytest tests/test_compaction.py -xvs
pytest tests/test_approval.py -xvs

# 工具测试
pytest tests/test_cron_tool.py -xvs
pytest tests/test_sessions_tools.py -xvs
pytest tests/test_memory_tools.py -xvs
```

#### 集成测试

```bash
# 启动 Gateway
python -m lurkbot.gateway.server

# 测试完整对话流程
python -m lurkbot.cli chat --model anthropic/claude-sonnet-4-20250514

# 测试心跳触发
python -m lurkbot.cli heartbeat --trigger

# 测试子代理生成
python -m lurkbot.cli spawn --task "Analyze code"
```

#### 对比测试

```
1. 相同的 Bootstrap 文件在 MoltBot 和 LurkBot 上执行
2. 对比系统提示词生成结果
3. 对比工具调用行为
4. 对比审批流程
5. 对比长对话压缩行为
```

---

### 3.4 时间线

| 阶段 | 内容 | 时间 |
|------|------|------|
| Phase 1 | 核心 Agent 框架（LangGraph） | 2周 |
| Phase 2 | Bootstrap 和系统提示词 | 1周 |
| Phase 3 | 工具系统和策略 | 1.5周 |
| Phase 4 | 自主运行能力 | 2周 |
| Phase 5 | Context Compaction | 1周 |
| Phase 6 | Gateway 和渠道适配器 | 1.5周 |
| Phase 7 | 内存系统 | 1周 |
| **总计** | | **10周** |

---

### 3.5 关键文件清单

```
src/lurkbot/
├── agents/
│   ├── graph.py          # LangGraph Agent 图形
│   ├── bootstrap.py      # Bootstrap 文件加载
│   ├── system_prompt.py  # 系统提示词生成
│   ├── compaction.py     # 上下文压缩
│   └── runtime.py        # Agent 运行时
├── tools/
│   ├── policy.py         # 九层工具策略
│   ├── registry.py       # 工具注册表
│   ├── approval.py       # 审批管理器
│   └── builtin/
│       ├── cron.py       # 定时任务
│       ├── sessions.py   # 会话管理工具
│       ├── memory.py     # 内存工具
│       ├── message.py    # 消息工具
│       └── browser.py    # 浏览器工具
├── autonomous/
│   ├── heartbeat.py      # 心跳管理器
│   └── scheduler.py      # 任务调度器
├── memory/
│   ├── store.py          # 内存存储
│   └── embeddings.py     # 向量嵌入
├── gateway/
│   ├── server.py         # WebSocket 服务器
│   ├── protocol.py       # 协议定义
│   └── channels/         # 渠道适配器
│       ├── telegram.py
│       ├── discord.py
│       └── web.py
├── auth/
│   ├── profiles.py       # 认证配置文件
│   └── oauth.py          # OAuth 管理
├── plugins/
│   ├── loader.py         # 插件加载器
│   └── registry.py       # 插件注册表
├── skills/
│   ├── loader.py         # 技能加载器
│   └── config.py         # 技能配置
└── config/
    ├── schema.py         # 配置 Schema
    └── settings.py       # 设置管理
```

---

**文档完成**: 2026-01-29
**文档类型**: 完整复刻设计报告与实施计划
**下一步**: 按 Phase 顺序实施
