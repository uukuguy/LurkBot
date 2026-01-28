# MoltBot 完整架构分析文档（中文版）

> **文档版本**: 2.0
> **更新日期**: 2026-01-29
> **基于**: MoltBot TypeScript 源码深度分析

---

## 目录

- [一、项目概述](#一项目概述)
- [二、核心架构概览](#二核心架构概览)
- [三、Agent 运行时系统](#三agent-运行时系统)
- [四、Bootstrap 文件系统](#四bootstrap-文件系统)
- [五、系统提示词生成](#五系统提示词生成)
- [六、工具系统与九层策略](#六工具系统与九层策略)
- [七、会话管理系统](#七会话管理系统)
- [八、子代理通信协议](#八子代理通信协议)
- [九、Heartbeat 心跳系统](#九heartbeat-心跳系统)
- [十、Cron 定时任务系统](#十cron-定时任务系统)
- [十一、认证配置文件系统](#十一认证配置文件系统)
- [十二、技能系统](#十二技能系统)
- [十三、上下文压缩系统](#十三上下文压缩系统)
- [十四、Gateway 协议](#十四gateway-协议)
- [十五、Python 复刻指南](#十五python-复刻指南)

---

## 一、项目概述

### 1.1 项目规模

基于对 `./github.com/moltbot/src` 目录的深度分析：

| 指标 | 数值 |
|------|------|
| **总代码行数** | ~411,783 LOC |
| **TypeScript 文件数** | 810+ |
| **顶层目录数** | 47 |
| **核心模块代码量** | agents(40K), gateway(23K), auto-reply(20K), infra(19K), config(13K) |

### 1.2 核心特性

1. **多渠道支持**: Telegram, Discord, Slack, WhatsApp, Signal, iMessage, MS Teams, Matrix 等
2. **多模型集成**: Anthropic, OpenAI, Google Gemini, AWS Bedrock, Ollama
3. **自主运行能力**: Heartbeat 心跳、Cron 定时任务、Subagent 子代理
4. **完整工具系统**: 22 个原生工具，九层策略过滤
5. **沙箱隔离**: Docker 容器化执行
6. **技能和插件**: 可扩展的技能和插件系统
7. **长期记忆**: 向量搜索和语义检索

---

## 二、核心架构概览

### 2.1 架构设计哲学

MoltBot 采用 **Gateway-Centric Architecture**（网关中心架构），核心思想是：

- **单一控制平面**: 所有消息通过 WebSocket Gateway 路由
- **协议标准化**: 定义统一的内部消息格式
- **模块解耦**: Channel、Agent、Tool 各自独立
- **事件驱动**: 使用发布订阅模式处理异步事件
- **SDK 集成**: 核心 Agent Loop 委托给 Pi SDK

### 2.2 系统架构图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         MoltBot 完整架构                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────── 消息渠道层 ──────────────┐    ┌────────── 控制层 ──────────┐ │
│  │ Telegram  Discord  Slack  Signal      │    │ CLI  WebSocket  HTTP API  │ │
│  │ WhatsApp  iMessage  MSTeams  Matrix   │    │ mDNS Discovery            │ │
│  └────────────────┬───────────────────────┘    └──────────┬────────────────┘ │
│                   │                                       │                  │
│                   └───────────────┬───────────────────────┘                  │
│                                   ▼                                          │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                     WebSocket Gateway (核心枢纽)                        │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐    │   │
│  │  │ 协议处理      │  │ 消息路由      │  │ RPC 方法                   │    │   │
│  │  │ • hello/ok   │  │ • session    │  │ • agent.*                │    │   │
│  │  │ • req/res    │  │ • channel    │  │ • sessions.*             │    │   │
│  │  │ • event      │  │ • broadcast  │  │ • cron.*                 │    │   │
│  │  └──────────────┘  └──────────────┘  └──────────────────────────┘    │   │
│  └──────────────────────────────────┬───────────────────────────────────┘   │
│                                     │                                        │
│                                     ▼                                        │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                     Agent Runtime (代理运行时)                         │   │
│  │                                                                       │   │
│  │  ┌─────────────────────────────────────────────────────────────────┐ │   │
│  │  │                    Pi SDK Integration                           │ │   │
│  │  │  • createAgentSession()  • session.prompt()  • subscribe()     │ │   │
│  │  │  • codingTools  • SessionManager  • streamSimple               │ │   │
│  │  └─────────────────────────────────────────────────────────────────┘ │   │
│  │                                                                       │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐   │   │
│  │  │ Bootstrap    │  │ System       │  │ Tool Policy              │   │   │
│  │  │ • SOUL.md    │  │ Prompt       │  │ • 9 层过滤               │   │   │
│  │  │ • AGENTS.md  │  │ Generator    │  │ • profile/provider/model │   │   │
│  │  │ • TOOLS.md   │  │ (592 lines)  │  │ • sandbox/subagent       │   │   │
│  │  └──────────────┘  └──────────────┘  └──────────────────────────┘   │   │
│  │                                                                       │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                        自主运行层                                         ││
│  │  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────┐  ││
│  │  │ Heartbeat        │  │ Cron Service     │  │ Subagent Registry    │  ││
│  │  │ • 定期唤醒        │  │ • at/every/cron  │  │ • spawn/announce    │  ││
│  │  │ • 活动时间窗口    │  │ • systemEvent    │  │ • 结果汇报           │  ││
│  │  │ • HEARTBEAT_OK   │  │ • agentTurn      │  │ • 清理策略           │  ││
│  │  └──────────────────┘  └──────────────────┘  └──────────────────────┘  ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 三、Agent 运行时系统

### 3.1 核心入口函数

**文件**: `src/agents/pi-embedded-runner/run.ts`

Agent 执行的主入口 `runEmbeddedPiAgent()` 负责：
1. 模型解析和验证
2. 认证配置管理
3. 上下文窗口检查
4. 错误处理和重试
5. 配置文件 Failover 逻辑

### 3.2 执行流程

```
runEmbeddedPiAgent()
    │
    ├─→ 解析模型配置
    ├─→ 上下文窗口检查
    ├─→ 认证 Profile 轮转
    │
    └─→ while (true) {
            │
            ├─→ runEmbeddedAttempt()
            │       ├─→ 创建工具集
            │       ├─→ 构建系统提示词
            │       ├─→ 创建 Pi SDK Session
            │       ├─→ 订阅事件
            │       └─→ session.prompt()
            │
            ├─→ 上下文溢出? → 压缩并重试
            ├─→ 认证失败? → 切换 Profile 并重试
            │
            └─→ 返回结果
        }
```

### 3.3 事件类型

```typescript
type SessionEvent =
  | { type: "message_start" }       // 消息开始
  | { type: "text_delta"; delta }   // 文本增量
  | { type: "text_end"; text }      // 文本结束
  | { type: "tool_start"; toolName, toolId }  // 工具开始
  | { type: "tool_delta"; delta }   // 工具增量
  | { type: "tool_end"; result }    // 工具结束
  | { type: "compaction_retry" }    // 压缩重试
  | { type: "error"; error }        // 错误
```

---

## 四、Bootstrap 文件系统

### 4.1 文件列表与作用

| 文件 | 作用 | 主会话 | 子代理 | 群组 |
|------|------|--------|--------|------|
| **SOUL.md** | 人格核心（不可覆盖） | ✅ | ❌ | ✅ |
| **IDENTITY.md** | 身份认同（名字、emoji） | ✅ | ❌ | ✅ |
| **USER.md** | 用户偏好（时区、称呼） | ✅ | ❌ | ✅ |
| **AGENTS.md** | 工作区指导和规则 | ✅ | ✅ | ✅ |
| **TOOLS.md** | 本地工具和配置说明 | ✅ | ✅ | ✅ |
| **HEARTBEAT.md** | 心跳任务列表 | ✅ | ❌ | ❌ |
| **MEMORY.md** | 长期记忆 | ✅ | ❌ | ❌ |
| **BOOTSTRAP.md** | 首次运行仪式 | ✅ | ❌ | ❌ |

### 4.2 子代理过滤

子代理只能访问 `AGENTS.md` 和 `TOOLS.md`：

```typescript
const SUBAGENT_BOOTSTRAP_ALLOWLIST = new Set([
  "AGENTS.md",
  "TOOLS.md",
]);

function filterBootstrapFilesForSession(files, sessionKey) {
  if (!isSubagentSessionKey(sessionKey)) return files;
  return files.filter((f) => SUBAGENT_BOOTSTRAP_ALLOWLIST.has(f.name));
}
```

### 4.3 文件截断策略

当文件超过 `max_chars` 限制时，保留 **头部 70%** 和 **尾部 20%**：

```typescript
// 头部 70% + "[... content trimmed ...]" + 尾部 20%
```

---

## 五、系统提示词生成

### 5.1 提示词模式

```typescript
type PromptMode = "full" | "minimal" | "none";

// full:    所有章节（主代理默认）
// minimal: 精简章节（子代理：Tooling, Workspace, Runtime）
// none:    仅基本身份行
```

### 5.2 完整提示词结构（23 个章节）

| # | 章节 | 条件 |
|---|------|------|
| 1 | 身份行 | 始终 |
| 2 | ## Tooling | 始终 |
| 3 | ## Tool Call Style | 始终 |
| 4 | ## Moltbot CLI Quick Reference | 始终 |
| 5 | ## Skills (mandatory) | !minimal |
| 6 | ## Memory Recall | !minimal + 有内存工具 |
| 7 | ## User Identity | ownerLine + !minimal |
| 8 | ## Current Date & Time | userTimezone |
| 9 | ## Workspace | 始终 |
| 10 | ## Documentation | docsPath + !minimal |
| 11 | ## Sandbox | sandboxInfo.enabled |
| 12 | ## Workspace Files (injected) | 始终 |
| 13 | ## Reply Tags | !minimal |
| 14 | ## Messaging | !minimal |
| 15 | ## Voice (TTS) | !minimal + ttsHint |
| 16 | ## Moltbot Self-Update | hasGateway + !minimal |
| 17 | ## Model Aliases | modelAliasLines + !minimal |
| 18 | # Project Context | contextFiles.length > 0 |
| 19 | ## Silent Replies | !minimal |
| 20 | ## Heartbeats | !minimal |
| 21 | ## Runtime | 始终 |
| 22 | ## Reactions | reactionGuidance |
| 23 | ## Reasoning Format | reasoningTagHint |

### 5.3 Runtime 行示例

```
Runtime: agent=main | host=m1-max | repo=/Users/user/projects |
         os=macOS (arm64) | node=22.0.0 | model=claude-opus-4-5-20251101 |
         channel=discord | capabilities=inlineButtons | thinking=medium
```

---

## 六、工具系统与九层策略

### 6.1 完整工具列表（22 个原生工具）

#### 会话管理（6 个）
- `sessions_spawn` - 生成子代理
- `sessions_send` - 跨会话消息
- `sessions_list` - 列出会话
- `sessions_history` - 会话历史
- `session_status` - 会话状态
- `agents_list` - 代理列表

#### 定时任务（1 个）
- `cron` - 定时任务管理

#### 通信（1 个）
- `message` - 多渠道消息

#### 内容获取（2 个）
- `web_search` - 网络搜索
- `web_fetch` - 网页获取

#### 媒体（3 个）
- `browser` - 浏览器控制
- `image` - 图像处理
- `canvas` - 可视化画布

#### 内存（2 个）
- `memory_search` - 语义搜索
- `memory_get` - 精确读取

#### 系统（3 个）
- `nodes` - 节点管理
- `gateway` - Gateway API
- `tts` - 文本转语音

#### 编码（4 个）
- `bash`/`exec` - Shell 命令
- `read` - 文件读取
- `write` - 文件写入
- `edit`/`apply_patch` - 文件编辑

### 6.2 工具分组

```typescript
const TOOL_GROUPS = {
  "group:memory":    ["memory_search", "memory_get"],
  "group:web":       ["web_search", "web_fetch"],
  "group:fs":        ["read", "write", "edit", "apply_patch"],
  "group:runtime":   ["exec", "process"],
  "group:sessions":  ["sessions_*"],
  "group:ui":        ["browser", "canvas"],
  "group:automation":["cron", "gateway"],
  "group:messaging": ["message"],
  "group:nodes":     ["nodes"],
};
```

### 6.3 工具配置文件

| Profile | 允许的工具 |
|---------|-----------|
| `minimal` | session_status |
| `coding` | group:fs, group:runtime, group:sessions, group:memory, image |
| `messaging` | group:messaging, sessions_list, sessions_history, sessions_send, session_status |
| `full` | 所有工具 |

### 6.4 九层策略过滤

```
Layer 1: Profile-based     → 根据配置文件过滤
Layer 2: Provider-based    → 提供商能力
Layer 3: Model-based       → 模型支持
Layer 4: Global exclusions → 全局禁用
Layer 5: Agent-type        → 代理类型
Layer 6: Group/Channel     → 群组/渠道
Layer 7: Sandbox mode      → 沙箱模式
Layer 8: Subagent          → 子代理
Layer 9: Plugin merge      → 插件工具
```

### 6.5 子代理禁用列表

```typescript
const SUBAGENT_DENY_LIST = [
  "sessions_list", "sessions_history", "sessions_send",
  "sessions_spawn", "gateway", "agents_list", "session_status",
  "cron", "memory_search", "memory_get"
];
```

---

## 七、会话管理系统

### 7.1 会话类型

| 类型 | 说明 | 工具权限 |
|------|------|----------|
| `main` | 用户直接对话 | 完整 |
| `group` | 群组会话 | 沙箱隔离 |
| `dm` | 其他用户私聊 | 部分信任 |
| `topic` | 论坛主题 | 沙箱隔离 |
| `subagent` | 子代理会话 | 工具受限 |

### 7.2 会话 Key 格式

```
主会话:     agent:{agentId}:main
群组会话:   agent:{agentId}:group:{channelId}:{groupId}
子代理会话: agent:{agentId}:subagent:{childId}
全局会话:   global
```

---

## 八、子代理通信协议

### 8.1 Spawn 参数

```typescript
interface SessionsSpawnParams {
  task: string;              // 任务描述
  agentId?: string;          // 目标代理
  model?: string;            // 模型覆盖
  thinking?: "low" | "medium" | "high";
  runTimeoutSeconds?: number; // 默认 3600
  cleanup?: "delete" | "keep";
  label?: string;            // 可选标签
}
```

### 8.2 子代理系统提示词

子代理有专门的系统提示词，强调：
- 专注于分配的任务
- 不发起用户对话
- 不使用 message 工具
- 不创建 cron 任务
- 完成后被终止是正常的

### 8.3 结果汇报流程

1. 等待子代理完成
2. 读取最后回复
3. 构建统计信息
4. 发送汇报消息到主代理
5. 可选清理子代理会话

---

## 九、Heartbeat 心跳系统

### 9.1 配置选项

```typescript
type HeartbeatConfig = {
  enabled?: boolean;
  every?: string;           // "5m", "30s"
  prompt?: string;          // 自定义提示词
  target?: "main" | "last"; // 投递目标
  model?: string;           // 模型覆盖
  ackMaxChars?: number;     // 默认 100
  activeHours?: {
    start: "HH:MM";
    end: "HH:MM" | "24:00";
    timezone?: "user" | "local" | string;
  };
};
```

### 9.2 心跳流程

1. 检查是否启用
2. 检查是否在活动时间内
3. 检查是否有请求在执行
4. 读取 HEARTBEAT.md
5. 调用 LLM 获取响应
6. 检查是否为 HEARTBEAT_OK
7. 抑制重复消息
8. 投递到目标渠道

### 9.3 特殊令牌

```
HEARTBEAT_OK  - 表示没有需要注意的事项
SILENT_REPLY_TOKEN - 表示不需要发送消息
```

---

## 十、Cron 定时任务系统

### 10.1 调度类型

```typescript
type CronSchedule =
  | { kind: "at"; atMs: number }      // 单次执行
  | { kind: "every"; everyMs: number } // 周期执行
  | { kind: "cron"; expr: string; tz?: string }; // Cron 表达式
```

### 10.2 Payload 类型

```typescript
type CronPayload =
  | { kind: "systemEvent"; text: string }  // 轻量级提醒
  | { kind: "agentTurn"; message: string; ... }; // 重量级任务
```

### 10.3 Cron 服务 API

- `start()` / `stop()` - 生命周期
- `list()` - 列出任务
- `add()` / `update()` / `remove()` - CRUD
- `run()` - 立即执行
- `wake()` - 唤醒模式

---

## 十一、认证配置文件系统

### 11.1 凭据类型

```typescript
type AuthProfileCredential =
  | { type: "api_key"; key: string }
  | { type: "token"; token: string; expires?: number }
  | { type: "oauth"; access: string; refresh?: string };
```

### 11.2 使用统计

```typescript
type ProfileUsageStats = {
  lastUsed?: number;
  errorCount?: number;
  cooldownUntil?: number;
  disabledUntil?: number;
  disabledReason?: string;
  failureCounts?: Record<string, number>;
};
```

### 11.3 Profile 选择算法

1. 规范化提供商名称
2. 确定基础顺序
3. 过滤有效配置文件
4. 分离可用 vs 冷却中
5. 可用的按 lastUsed 排序（轮换）
6. 优先指定的 Profile

### 11.4 冷却计算

```
cooldown = min(1 hour, 60 sec × 5^(errorCount-1))
errorCount=1 → 300ms
errorCount=2 → 1.5s
errorCount=3 → 7.5s
errorCount=4+ → 1 hour
```

---

## 十二、技能系统

### 12.1 技能 Frontmatter

```yaml
---
description: What this skill does
tags: [tag1, tag2]
user-invocable: true
disable-model-invocation: false
metadata: |
  {
    "moltbot": {
      "skillKey": "custom-key",
      "requires": {
        "bins": ["ffmpeg"],
        "env": ["API_KEY"]
      },
      "install": [
        { "kind": "brew", "formula": "ffmpeg" }
      ]
    }
  }
---
# Skill Content
```

### 12.2 加载优先级

```
工作区技能 > 受管技能 > 打包技能 > 额外目录
```

---

## 十三、上下文压缩系统

### 13.1 核心常量

```typescript
BASE_CHUNK_RATIO = 0.4;   // 40% 保留最近历史
MIN_CHUNK_RATIO = 0.15;   // 最小 15%
SAFETY_MARGIN = 1.2;      // 20% 估算缓冲
DEFAULT_CONTEXT_TOKENS = 128000;
```

### 13.2 压缩策略

1. 估算总 Token 数
2. 按比例分块
3. 对旧消息生成摘要
4. 合并部分摘要
5. 保留最近历史

---

## 十四、Gateway 协议

### 14.1 帧类型

- `hello` / `hello-ok` - 连接握手
- `request` / `response` - RPC 调用
- `event` - 事件推送

### 14.2 错误码

- `NOT_LINKED` - 认证提供商未连接
- `NOT_PAIRED` - 设备未配对
- `AGENT_TIMEOUT` - 代理操作超时
- `INVALID_REQUEST` - 无效请求
- `UNAVAILABLE` - 服务不可用

### 14.3 Gateway 方法

```
agents.*:     代理操作
chat.*:       聊天操作
sessions.*:   会话操作
cron.*:       定时任务
config.*:     配置管理
channels.*:   渠道管理
```

---

## 十五、Python 复刻指南

### 15.1 技术栈映射

| MoltBot (TS) | LurkBot (Python) |
|--------------|------------------|
| Pi SDK | PydanticAI |
| Express | FastAPI |
| TypeBox | Pydantic |
| Commander | Typer |
| Winston | Loguru |
| Vitest | pytest |

### 15.2 模块映射

```
src/agents/          →  lurkbot/agents/
src/gateway/         →  lurkbot/gateway/
src/channels/        →  lurkbot/channels/
src/config/          →  lurkbot/config/
src/cli/             →  lurkbot/cli/
src/infra/           →  lurkbot/infra/
src/cron/            →  lurkbot/cron/
src/memory/          →  lurkbot/memory/
```

### 15.3 关键文件清单

| 功能 | MoltBot 文件 | 说明 |
|------|-------------|------|
| Agent 入口 | agents/pi-embedded-runner/run.ts | 主执行函数 |
| 系统提示词 | agents/system-prompt.ts | 592 行 |
| Bootstrap | agents/workspace.ts | 文件加载 |
| 工具策略 | agents/tool-policy.ts | 九层过滤 |
| 心跳 | infra/heartbeat-runner.ts | 901 行 |
| Cron | cron/service.ts | 定时服务 |
| Auth Profiles | agents/auth-profiles/ | 认证轮换 |
| 压缩 | agents/compaction.ts | 上下文压缩 |
| 子代理 | agents/subagent-announce.ts | 结果汇报 |
| Gateway | gateway/protocol/schema/ | 协议定义 |

### 15.4 实施优先级

**Phase 1**: 核心框架
- PydanticAI Agent 运行时
- Bootstrap 文件系统
- 系统提示词生成
- 基础工具策略

**Phase 2**: 工具系统
- 九层策略完整实现
- 22 个原生工具
- 沙箱隔离

**Phase 3**: 自主运行
- Heartbeat 心跳
- Cron 定时任务
- Subagent 子代理

**Phase 4**: 高级功能
- Auth Profile 轮换
- Context Compaction
- Gateway 协议
- 内存向量搜索

---

**文档完成**: 2026-01-29
**文档类型**: MoltBot 完整架构分析（中文版）
**下一步**: 按 Phase 顺序实施 LurkBot 复刻
