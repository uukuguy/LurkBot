# MoltBot 完整架构分析文档

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
- [十五、内存和向量搜索](#十五内存和向量搜索)
- [十六、插件系统](#十六插件系统)
- [十七、错误处理与重试](#十七错误处理与重试)
- [十八、关键文件清单](#十八关键文件清单)

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

### 2.1 系统架构图

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
│  │  └──────────────┘  └──────────────┘  │ • config.*               │    │   │
│  │                                       │ • channels.*             │    │   │
│  │                                       └──────────────────────────┘    │   │
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
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐   │   │
│  │  │ Session      │  │ Context      │  │ Auth Profile             │   │   │
│  │  │ Management   │  │ Compaction   │  │ Rotation                 │   │   │
│  │  │ • main/group │  │ • chunking   │  │ • failover               │   │   │
│  │  │ • dm/topic   │  │ • summarize  │  │ • cooldown               │   │   │
│  │  └──────────────┘  └──────────────┘  └──────────────────────────┘   │   │
│  │                                                                       │   │
│  └──────────────────────────────────┬───────────────────────────────────┘   │
│                                     │                                        │
│                                     ▼                                        │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                       Tool Execution Layer                            │   │
│  │                                                                       │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │   │
│  │  │ 编码工具     │  │ 会话工具     │  │ 消息工具     │  │ 系统工具     │ │   │
│  │  │ read/write  │  │ spawn/send  │  │ message     │  │ cron        │ │   │
│  │  │ edit/patch  │  │ list/history│  │ web_search  │  │ gateway     │ │   │
│  │  │ bash/exec   │  │ status      │  │ web_fetch   │  │ nodes       │ │   │
│  │  │ grep/find   │  │ agents_list │  │ browser     │  │ tts         │ │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘ │   │
│  │                                                                       │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────────┐  │   │
│  │  │ 内存工具     │  │ 媒体工具     │  │ 沙箱执行                      │  │   │
│  │  │ memory_     │  │ image       │  │ • Docker 容器               │  │   │
│  │  │   search    │  │ canvas      │  │ • 路径限制                   │  │   │
│  │  │   get       │  │             │  │ • 审批工作流                  │  │   │
│  │  └─────────────┘  └─────────────┘  └─────────────────────────────┘  │   │
│  │                                                                       │   │
│  └───────────────────────────────────────────────────────────────────────┘   │
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
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                        扩展层                                             ││
│  │  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────┐  ││
│  │  │ Skills System    │  │ Plugin System    │  │ Memory/RAG           │  ││
│  │  │ • YAML frontmatter│ │ • manifest       │  │ • sqlite-vec        │  ││
│  │  │ • workspace优先   │  │ • dynamic load   │  │ • embeddings        │  ││
│  │  │ • requirements   │  │ • runtime inject │  │ • semantic search   │  ││
│  │  └──────────────────┘  └──────────────────┘  └──────────────────────┘  ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 数据流

```
用户消息 → Channel Adapter → Gateway → Session Routing → Agent Runtime
                                                              │
                                                              ▼
                                               ┌──────────────────────────┐
                                               │ 1. 加载 Bootstrap 文件     │
                                               │ 2. 生成系统提示词          │
                                               │ 3. 应用工具策略            │
                                               │ 4. 创建 Pi SDK Session    │
                                               └──────────────────────────┘
                                                              │
                                                              ▼
                                               ┌──────────────────────────┐
                                               │ Pi SDK Agent Loop        │
                                               │ • session.prompt()       │
                                               │ • Tool Call Events       │
                                               │ • Tool Execution         │
                                               │ • Tool Result Feedback   │
                                               │ • Loop until done        │
                                               └──────────────────────────┘
                                                              │
                                                              ▼
流式响应 ← subscribeEmbeddedPiSession() ← 事件订阅
```

---

## 三、Agent 运行时系统

### 3.1 核心入口函数

**文件**: `src/agents/pi-embedded-runner/run.ts`

```typescript
export async function runEmbeddedPiAgent(
  params: RunEmbeddedPiAgentParams,
): Promise<EmbeddedPiRunResult> {
  // 1. 解析模型配置
  const { model, authStorage, modelRegistry } = resolveModel(...);

  // 2. 上下文窗口检查
  const ctxGuard = evaluateContextWindowGuard({ ... });

  // 3. 认证 Profile 轮转
  const profileOrder = resolveAuthProfileOrder({ ... });

  // 4. 主循环 - 支持重试和 Failover
  while (true) {
    // 4.1 执行单次尝试
    const attempt = await runEmbeddedAttempt({ ... });

    // 4.2 上下文溢出自动压缩
    if (isContextOverflowError(errorText)) {
      const compactResult = await compactEmbeddedPiSessionDirect({ ... });
      if (compactResult.compacted) continue;
    }

    // 4.3 认证失败切换 Profile
    if (shouldRotate) {
      const rotated = await advanceAuthProfile();
      if (rotated) continue;
    }

    return { payloads, meta };
  }
}
```

### 3.2 单次执行尝试

**文件**: `src/agents/pi-embedded-runner/run/attempt.ts`

```typescript
export async function runEmbeddedAttempt(
  params: EmbeddedRunAttemptParams,
): Promise<EmbeddedRunAttemptResult> {
  // 1. 创建工具集
  const toolsRaw = createMoltbotCodingTools({ ... });
  const tools = sanitizeToolsForGoogle({ tools: toolsRaw, provider });

  // 2. 构建系统提示词
  const appendPrompt = buildEmbeddedSystemPrompt({ ... });
  const systemPrompt = createSystemPromptOverride(appendPrompt);

  // 3. 拆分工具（内置 vs 自定义）
  const { builtInTools, customTools } = splitSdkTools({ tools });

  // 4. 创建 Pi SDK Agent 会话
  ({ session } = await createAgentSession({
    cwd: resolvedWorkspace,
    model,
    thinkingLevel: mapThinkingLevel(params.thinkLevel),
    systemPrompt,
    tools: builtInTools,
    customTools: allCustomTools,
    sessionManager,
    skills: [],
    contextFiles: [],
  }));

  // 5. 订阅会话事件（流式响应）
  const subscription = subscribeEmbeddedPiSession({
    session: activeSession,
    onToolResult: params.onToolResult,
    onBlockReply: params.onBlockReply,
  });

  // 6. 发送 Prompt（触发 Agent Loop）
  await activeSession.prompt(effectivePrompt, { images });

  return { aborted, timedOut, assistantTexts, toolMetas, ... };
}
```

### 3.3 事件订阅

**文件**: `src/agents/pi-embedded-subscribe.ts`

```typescript
type SessionEvent =
  | { type: "message_start" }
  | { type: "text_delta"; delta: string }
  | { type: "text_end"; text: string }
  | { type: "tool_start"; toolName: string; toolId: string }
  | { type: "tool_delta"; delta: string }
  | { type: "tool_end"; toolName: string; result: any }
  | { type: "compaction_retry" }
  | { type: "error"; error: Error };

export function subscribeEmbeddedPiSession(params) {
  const state = {
    assistantTexts: [],
    toolMetas: [],
    deltaBuffer: "",
    blockState: { thinking: false, final: false },
    messagingToolSentTexts: [],
  };

  const unsubscribe = params.session.subscribe(
    createEmbeddedPiSessionEventHandler(ctx)
  );

  return {
    assistantTexts,
    toolMetas,
    unsubscribe,
    isCompacting: () => state.compactionInFlight,
    didSendViaMessagingTool: () => messagingToolSentTexts.length > 0,
  };
}
```

---

## 四、Bootstrap 文件系统

### 4.1 文件列表与作用

**文件**: `src/agents/workspace.ts`

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

### 4.2 子代理过滤逻辑

```typescript
// src/agents/workspace.ts
export const SUBAGENT_BOOTSTRAP_ALLOWLIST = new Set([
  DEFAULT_AGENTS_FILENAME,  // "AGENTS.md"
  DEFAULT_TOOLS_FILENAME,   // "TOOLS.md"
]);

export function filterBootstrapFilesForSession(
  files: BootstrapFile[],
  sessionKey?: string,
): BootstrapFile[] {
  if (!sessionKey || !isSubagentSessionKey(sessionKey)) {
    return files;
  }
  return files.filter((file) => SUBAGENT_BOOTSTRAP_ALLOWLIST.has(file.name));
}
```

### 4.3 文件加载与截断

```typescript
// 加载并截断文件（保留头70%+尾20%）
async function readAndTrim(path: Path, maxChars: number): Promise<string> {
  const content = await fs.readFile(path, "utf-8");
  if (content.length <= maxChars) {
    return content;
  }

  const headSize = Math.floor(maxChars * 0.7);
  const tailSize = Math.floor(maxChars * 0.2);
  return (
    content.slice(0, headSize) +
    "\n\n[... content trimmed ...]\n\n" +
    content.slice(-tailSize)
  );
}
```

---

## 五、系统提示词生成

### 5.1 提示词模式

**文件**: `src/agents/system-prompt.ts` (592 行)

```typescript
export type PromptMode = "full" | "minimal" | "none";

// full: 所有章节（主代理默认）
// minimal: 精简章节（子代理使用）
// none: 仅基本身份行
```

### 5.2 完整提示词结构

| # | 章节 | 条件 | 内容 |
|---|------|------|------|
| 1 | **身份行** | 始终 | "You are a personal assistant running inside Moltbot." |
| 2 | **## Tooling** | 始终 | 工具列表和摘要 |
| 3 | **## Tool Call Style** | 始终 | 何时说明工作 |
| 4 | **## Moltbot CLI Quick Reference** | 始终 | CLI 命令参考 |
| 5 | **## Skills (mandatory)** | !minimal | 技能加载指导 |
| 6 | **## Memory Recall** | !minimal + 有内存工具 | 在回答前搜索记忆 |
| 7 | **## User Identity** | ownerLine + !minimal | 所有者号码 |
| 8 | **## Current Date & Time** | userTimezone | 时区信息 |
| 9 | **## Workspace** | 始终 | 工作目录和笔记 |
| 10 | **## Documentation** | docsPath + !minimal | 文档路径 |
| 11 | **## Sandbox** | sandboxInfo.enabled | 沙箱限制和配置 |
| 12 | **## Workspace Files (injected)** | 始终 | 注入的启动文件 |
| 13 | **## Reply Tags** | !minimal | [[reply_to:id]] 语法 |
| 14 | **## Messaging** | !minimal | message 工具使用 |
| 15 | **## Voice (TTS)** | !minimal + ttsHint | TTS 配置 |
| 16 | **## Moltbot Self-Update** | hasGateway + !minimal | 自更新规则 |
| 17 | **## Model Aliases** | modelAliasLines + !minimal | 模型别名 |
| 18 | **# Project Context** | contextFiles.length > 0 | Bootstrap 文件内容 |
| 19 | **## Silent Replies** | !minimal | SILENT_REPLY_TOKEN |
| 20 | **## Heartbeats** | !minimal | HEARTBEAT_OK 处理 |
| 21 | **## Runtime** | 始终 | 运行时信息行 |
| 22 | **## Reactions** | reactionGuidance | 表情反应指导 |
| 23 | **## Reasoning Format** | reasoningTagHint | <think>/<final> 格式 |

### 5.3 Runtime 行格式

```typescript
export function buildRuntimeLine(...): string {
  return `Runtime: ${[
    runtimeInfo?.agentId ? `agent=${runtimeInfo.agentId}` : "",
    runtimeInfo?.host ? `host=${runtimeInfo.host}` : "",
    runtimeInfo?.repoRoot ? `repo=${runtimeInfo.repoRoot}` : "",
    runtimeInfo?.os ? `os=${runtimeInfo.os} (${runtimeInfo?.arch})` : "",
    runtimeInfo?.node ? `node=${runtimeInfo.node}` : "",
    runtimeInfo?.model ? `model=${runtimeInfo.model}` : "",
    runtimeChannel ? `channel=${runtimeChannel}` : "",
    runtimeCapabilities.length > 0 ? `capabilities=${runtimeCapabilities.join(",")}` : "",
    `thinking=${defaultThinkLevel ?? "off"}`,
  ].filter(Boolean).join(" | ")}`;
}

// 示例输出:
// Runtime: agent=main | host=m1-max | repo=/Users/user/projects |
//          os=macOS (arm64) | node=22.0.0 | model=claude-opus-4-5-20251101 |
//          channel=discord | capabilities=inlineButtons | thinking=medium
```

---

## 六、工具系统与九层策略

### 6.1 完整工具列表（22个原生工具）

**文件**: `src/agents/tool-policy.ts`

#### 会话管理工具（6个）

| 工具 | 功能 | 子代理 |
|------|------|--------|
| `sessions_spawn` | 生成隔离子代理会话 | 🚫 |
| `sessions_send` | 跨会话消息发送 | 🚫 |
| `sessions_list` | 列出可访问会话 | 🚫 |
| `sessions_history` | 获取会话历史 | 🚫 |
| `session_status` | 查询会话状态 | 🚫 |
| `agents_list` | 列出可用代理 | 🚫 |

#### 定时任务（1个）

| 工具 | 功能 |
|------|------|
| `cron` | 定时任务管理（status/list/add/update/remove/run/runs/wake） |

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

| 工具 | 功能 | 子代理 |
|------|------|--------|
| `memory_search` | 语义搜索 MEMORY.md | 🚫 |
| `memory_get` | 精确读取内存文件 | 🚫 |

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
| `bash` / `exec` | Shell 命令执行 |
| `read` | 文件读取 |
| `write` | 文件写入 |
| `edit` / `apply_patch` | 文件编辑 |

### 6.2 工具分组

```typescript
export const TOOL_GROUPS: Record<string, string[]> = {
  "group:memory": ["memory_search", "memory_get"],
  "group:web": ["web_search", "web_fetch"],
  "group:fs": ["read", "write", "edit", "apply_patch"],
  "group:runtime": ["exec", "process"],
  "group:sessions": [
    "sessions_list", "sessions_history", "sessions_send",
    "sessions_spawn", "session_status"
  ],
  "group:ui": ["browser", "canvas"],
  "group:automation": ["cron", "gateway"],
  "group:messaging": ["message"],
  "group:nodes": ["nodes"],
  "group:moltbot": [/* 所有22个原生工具 */],
};
```

### 6.3 工具配置文件

```typescript
export type ToolProfileId = "minimal" | "coding" | "messaging" | "full";

export const TOOL_PROFILES: Record<ToolProfileId, ToolProfilePolicy> = {
  minimal: {
    allow: ["session_status"],
  },
  coding: {
    allow: [
      "group:fs", "group:runtime", "group:sessions",
      "group:memory", "image"
    ],
  },
  messaging: {
    allow: [
      "group:messaging", "sessions_list", "sessions_history",
      "sessions_send", "session_status"
    ],
  },
  full: {
    // 允许所有工具
  },
};
```

### 6.4 九层策略过滤

```
Layer 1: Profile-based     → 根据认证配置过滤（minimal/coding/messaging/full）
Layer 2: Provider-based    → 提供商能力（OpenAI/Anthropic/Ollama/Google）
Layer 3: Model-based       → 不同模型支持不同工具
Layer 4: Global exclusions → 全局禁用的工具
Layer 5: Agent-type        → embedded/cli/web 不同代理类型
Layer 6: Group/Channel     → 群组聊天限制危险工具
Layer 7: Sandbox mode      → 沙箱模式禁用文件系统工具
Layer 8: Subagent          → 子代理限制递归生成
Layer 9: Plugin merge      → 合并插件注册的工具
```

### 6.5 子代理禁用列表

```typescript
export const SUBAGENT_DENY_LIST: string[] = [
  "sessions_list", "sessions_history", "sessions_send",
  "sessions_spawn", "gateway", "agents_list", "session_status",
  "cron", "memory_search", "memory_get"
];
```

### 6.6 策略过滤实现

```typescript
export function filterToolsByPolicy(
  tools: AnyAgentTool[],
  policy: ToolPolicy | undefined
): AnyAgentTool[] {
  if (!policy?.allow) return tools;

  const allowSet = new Set(
    policy.allow.map((name) => normalizeToolName(name))
  );

  return tools.filter((tool) =>
    allowSet.has(normalizeToolName(tool.name))
  );
}

export function resolveToolProfilePolicy(
  profile?: string | ToolProfileId
): ToolProfilePolicy {
  const normalized = normalizeToolProfile(profile);
  return TOOL_PROFILES[normalized] ?? TOOL_PROFILES.full;
}

export function expandToolGroups(items: string[]): Set<string> {
  const expanded = new Set<string>();
  for (const item of items) {
    if (item.startsWith("group:")) {
      const group = TOOL_GROUPS[item];
      if (group) {
        for (const tool of group) {
          expanded.add(tool);
        }
      }
    } else {
      expanded.add(item);
    }
  }
  return expanded;
}
```

---

## 七、会话管理系统

### 7.1 会话类型

```typescript
export type SessionType = "main" | "group" | "dm" | "topic" | "subagent";

// main:     用户直接对话，受信任，完整工具
// group:    群组会话，沙箱隔离，只读工具
// dm:       其他用户私聊，部分信任
// topic:    论坛主题，沙箱隔离
// subagent: 子代理会话，工具受限
```

### 7.2 会话 Key 格式

```typescript
// 主会话
"agent:{agentId}:main"

// 群组会话
"agent:{agentId}:group:{channelId}:{groupId}"

// 子代理会话
"agent:{agentId}:subagent:{childId}"

// 全局会话
"global"
```

### 7.3 会话存储

```typescript
// 文件位置: ~/.clawdbot/agents/{agentId}/sessions.json
{
  "agent:main:main": {
    "sessionId": "ses_abc123",
    "sessionKey": "agent:main:main",
    "createdAt": 1706500000000,
    "updatedAt": 1706550000000,
    "channel": "telegram",
    "lastChannel": "discord",
    "model": "claude-opus-4-5-20251101",
    "modelProvider": "anthropic",
    "inputTokens": 15000,
    "outputTokens": 3000,
    "totalTokens": 18000
  }
}

// 对话历史: ~/.clawdbot/agents/{agentId}/{sessionId}.jsonl
```

---

## 八、子代理通信协议

### 8.1 Spawn 工具

**文件**: `src/agents/tools/sessions-spawn-tool.ts`

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

// 返回结构
{
  success: boolean;
  sessionKey: string;
  runId: string;
  result?: string;
}
```

### 8.2 子代理系统提示词

**文件**: `src/agents/subagent-announce.ts`

```typescript
export function buildSubagentSystemPrompt(params: {
  requesterSessionKey?: string;
  requesterOrigin?: DeliveryContext;
  childSessionKey: string;
  label?: string;
  task?: string;
}): string {
  return `
# Subagent Context

You are a **subagent** spawned by the main agent for a specific task.

## Your Role
- You were created to handle: ${taskText}
- Complete this task. That's your entire purpose.
- You are NOT the main agent. Don't try to be.

## Rules
1. **Stay focused** - Do your assigned task, nothing else
2. **Complete the task** - Your final message will be automatically reported
3. **Don't initiate** - No heartbeats, no proactive actions, no side quests
4. **Be ephemeral** - You may be terminated after task completion

## What You DON'T Do
- NO user conversations (that's main agent's job)
- NO external messages unless explicitly tasked
- NO cron jobs or persistent state
- NO pretending to be the main agent
- NO using the \`message\` tool directly

## Session Context
- Label: ${params.label}
- Requester session: ${params.requesterSessionKey}
- Your session: ${params.childSessionKey}
`;
}
```

### 8.3 结果汇报流程

```typescript
export async function runSubagentAnnounceFlow(params: {
  childSessionKey: string;
  childRunId: string;
  requesterSessionKey: string;
  requesterOrigin?: DeliveryContext;
  task: string;
  timeoutMs: number;
  cleanup: "delete" | "keep";
  outcome?: SubagentRunOutcome;
}): Promise<boolean> {
  // 1. 等待子代理完成
  const wait = await callGateway({
    method: "agent.wait",
    params: { runId: params.childRunId, timeoutMs },
  });

  // 2. 读取子代理最后回复
  const reply = await readLatestAssistantReply({
    sessionKey: params.childSessionKey,
  });

  // 3. 构建统计行
  const statsLine = await buildSubagentStatsLine({
    sessionKey: params.childSessionKey,
    startedAt: params.startedAt,
    endedAt: params.endedAt,
  });

  // 4. 构建汇报消息
  const triggerMessage = `
A background task "${taskLabel}" just ${statusLabel}.

Findings:
${reply || "(no output)"}

${statsLine}

Summarize this naturally for the user. Keep it brief (1-2 sentences).
`;

  // 5. 发送到主代理
  await callGateway({
    method: "agent",
    params: {
      sessionKey: params.requesterSessionKey,
      message: triggerMessage,
      deliver: true,
    },
  });

  // 6. 清理（如果配置）
  if (params.cleanup === "delete") {
    await callGateway({
      method: "sessions.delete",
      params: { key: params.childSessionKey },
    });
  }
}
```

---

## 九、Heartbeat 心跳系统

### 9.1 核心配置

**文件**: `src/infra/heartbeat-runner.ts`

```typescript
export type HeartbeatConfig = {
  enabled?: boolean;
  every?: string;           // "5m", "30s", etc.
  prompt?: string;          // 自定义提示词
  target?: "main" | "last"; // 默认 "last"
  model?: string;           // 模型覆盖
  ackMaxChars?: number;     // 默认 100
  session?: string;         // 会话覆盖
  activeHours?: {
    start: "HH:MM";
    end: "HH:MM" | "24:00";
    timezone?: "user" | "local" | string;
  };
  includeReasoning?: boolean;
};

// 默认值
const DEFAULT_HEARTBEAT_EVERY = "5m";
const DEFAULT_HEARTBEAT_ACK_MAX_CHARS = 100;
const DEFAULT_HEARTBEAT_TARGET = "last";
```

### 9.2 心跳运行流程

```typescript
export async function runHeartbeatOnce(opts: HeartbeatRunOpts): Promise<HeartbeatRunResult> {
  // 1. 检查：是否启用，是否在活动时间内，是否有请求在执行
  if (!heartbeat?.enabled) return { status: "skipped", reason: "disabled" };
  if (!isWithinActiveHours(cfg, heartbeat)) return { status: "skipped", reason: "quiet-hours" };
  if (getQueueSize() > 0) return { status: "skipped", reason: "requests-in-flight" };

  // 2. 读取 HEARTBEAT.md
  const heartbeatContent = await readHeartbeatFile(workspaceDir);
  if (isHeartbeatContentEffectivelyEmpty(heartbeatContent)) {
    return { status: "skipped", reason: "empty-heartbeat-file" };
  }

  // 3. 解析会话和投递目标
  const { sessionKey } = resolveHeartbeatSession(cfg, agentId, heartbeat);
  const target = resolveHeartbeatDeliveryTarget(...);

  // 4. 调用 LLM 获取响应
  const reply = await getReplyFromConfig({
    sessionKey,
    prompt: heartbeatPrompt,
    model: heartbeat?.model,
  });

  // 5. 检查是否为 HEARTBEAT_OK
  const stripped = stripHeartbeatToken(reply.text);
  if (stripped.isHeartbeatOk) {
    return { status: "ran", result: "ok-token", durationMs };
  }

  // 6. 抑制重复
  if (isDuplicateWithin24Hours(stripped.text)) {
    return { status: "skipped", reason: "duplicate" };
  }

  // 7. 投递消息
  await deliverOutboundPayloads({ payloads: [stripped], target });

  return { status: "ran", result: "sent", durationMs };
}
```

### 9.3 心跳事件

```typescript
export type HeartbeatEventPayload = {
  ts: number;
  status: "sent" | "ok-empty" | "ok-token" | "skipped" | "failed";
  to?: string;
  preview?: string;
  durationMs?: number;
  hasMedia?: boolean;
  reason?: string;
  channel?: string;
  silent?: boolean;
  indicatorType?: "ok" | "alert" | "error";
};

// 发射事件
emitHeartbeatEvent(payload);

// 监听事件
onHeartbeatEvent((event) => { ... });

// 获取最后事件
const lastEvent = getLastHeartbeatEvent();
```

---

## 十、Cron 定时任务系统

### 10.1 Cron Job 结构

**文件**: `src/gateway/protocol/schema/cron.ts`

```typescript
export type CronJob = {
  id: string;
  agentId?: string;
  name: string;
  description?: string;
  enabled: boolean;
  deleteAfterRun?: boolean;
  createdAtMs: number;
  updatedAtMs: number;

  schedule: CronSchedule;
  sessionTarget: "main" | "isolated";
  wakeMode: "next-heartbeat" | "now";
  payload: CronPayload;

  isolation?: {
    postToMainPrefix?: string;
    postToMainMode?: "summary" | "full";
    postToMainMaxChars?: number;
  };

  state: {
    nextRunAtMs?: number;
    runningAtMs?: number;
    lastRunAtMs?: number;
    lastStatus?: "ok" | "error" | "skipped";
    lastError?: string;
    lastDurationMs?: number;
  };
};
```

### 10.2 调度类型

```typescript
export type CronSchedule =
  | { kind: "at"; atMs: number }           // 单次执行
  | { kind: "every"; everyMs: number; anchorMs?: number }  // 周期执行
  | { kind: "cron"; expr: string; tz?: string };           // Cron 表达式
```

### 10.3 Payload 类型

```typescript
export type CronPayload =
  | {
      kind: "systemEvent";
      text: string;
    }
  | {
      kind: "agentTurn";
      message: string;
      model?: string;
      thinking?: string;
      timeoutSeconds?: number;
      deliver?: boolean;
      channel?: "last" | string;
      to?: string;
      bestEffortDeliver?: boolean;
    };

// systemEvent: 向主会话注入文本事件（轻量级提醒）
// agentTurn: 运行隔离会话中的代理任务（重量级任务）
```

### 10.4 Cron 服务 API

```typescript
export class CronService {
  start(): void;
  stop(): void;
  status(): CronServiceStatus;
  list(opts?: { agentId?: string }): CronJob[];
  add(input: CronJobInput): CronJob;
  update(id: string, patch: Partial<CronJob>): CronJob;
  remove(id: string): void;
  run(id: string, mode?: "due" | "force"): Promise<CronRunResult>;
  wake(opts?: { mode?: "next-heartbeat" | "now" }): void;
}
```

---

## 十一、认证配置文件系统

### 11.1 配置文件存储

**文件**: `src/agents/auth-profiles/store.ts`

```typescript
export type AuthProfileStore = {
  profiles: {
    [profileId: string]: AuthProfileCredential;
  };

  usageStats: {
    [profileId: string]: ProfileUsageStats;
  };

  order?: {
    [normalizedProvider: string]: string[];
  };
};
```

### 11.2 凭据类型

```typescript
export type AuthProfileCredential =
  | { type: "api_key"; key: string }
  | { type: "token"; token: string; expires?: number }
  | { type: "oauth"; access: string; refresh?: string };
```

### 11.3 使用统计

```typescript
export type ProfileUsageStats = {
  lastUsed?: number;
  errorCount?: number;
  cooldownUntil?: number;
  disabledUntil?: number;
  disabledReason?: string;
  failureCounts?: {
    [reason: string]: number;
  };
};
```

### 11.4 Profile 选择算法

**文件**: `src/agents/auth-profiles/order.ts`

```typescript
export function resolveAuthProfileOrder(params: {
  cfg: MoltbotConfig;
  store: AuthProfileStore;
  provider: string;
  preferredProfile?: string;
}): string[] {
  // 1. 规范化提供商名称
  const normalizedProvider = normalizeProviderId(provider);

  // 2. 确定基础顺序
  let baseOrder = store.order?.[normalizedProvider]
    || cfg.auth?.order?.[normalizedProvider]
    || Object.keys(store.profiles).filter(p => matchProvider(p, normalizedProvider));

  // 3. 过滤有效配置文件
  const validProfiles = baseOrder.filter(p => isValidCredential(store.profiles[p]));

  // 4. 分离：可用 vs 冷却中
  const available: string[] = [];
  const inCooldown: string[] = [];
  for (const p of validProfiles) {
    const stats = store.usageStats[p];
    if (stats?.cooldownUntil && stats.cooldownUntil > Date.now()) {
      inCooldown.push(p);
    } else {
      available.push(p);
    }
  }

  // 5. 可用的按 lastUsed 排序（最旧优先 = 轮换）
  available.sort((a, b) => {
    const aUsed = store.usageStats[a]?.lastUsed ?? 0;
    const bUsed = store.usageStats[b]?.lastUsed ?? 0;
    return aUsed - bUsed;
  });

  // 6. 冷却中的按冷却结束时间排序
  inCooldown.sort((a, b) => {
    const aUntil = store.usageStats[a]?.cooldownUntil ?? 0;
    const bUntil = store.usageStats[b]?.cooldownUntil ?? 0;
    return aUntil - bUntil;
  });

  // 7. 优先指定的 Profile
  let result = [...available, ...inCooldown];
  if (preferredProfile && result.includes(preferredProfile)) {
    result = [preferredProfile, ...result.filter(p => p !== preferredProfile)];
  }

  return result;
}
```

### 11.5 冷却计算

```typescript
export function calculateAuthProfileCooldownMs(errorCount: number): number {
  // cooldown = min(1 hour, 60 sec × 5^(errorCount-1))
  // errorCount=1 → 300ms
  // errorCount=2 → 1.5s
  // errorCount=3 → 7.5s
  // errorCount=4+ → 1 hour (3600000ms)
  const base = 60 * 1000; // 60 seconds
  const factor = Math.pow(5, Math.max(0, errorCount - 1));
  return Math.min(3600 * 1000, base * factor);
}

export function markAuthProfileFailure(
  store: AuthProfileStore,
  profileId: string,
  reason?: string,
): void {
  const stats = store.usageStats[profileId] ?? {};
  stats.errorCount = (stats.errorCount ?? 0) + 1;
  stats.cooldownUntil = Date.now() + calculateAuthProfileCooldownMs(stats.errorCount);

  if (reason) {
    stats.failureCounts = stats.failureCounts ?? {};
    stats.failureCounts[reason] = (stats.failureCounts[reason] ?? 0) + 1;
  }

  store.usageStats[profileId] = stats;
}
```

---

## 十二、技能系统

### 12.1 技能 Frontmatter

**文件**: `src/agents/skills/frontmatter.ts`

```yaml
---
# 基本元数据
description: What this skill does
tags: [tag1, tag2]

# 调用策略
user-invocable: true     # 用户可通过 /skill-name 调用
disable-model-invocation: false  # 模型可以自动调用

# Moltbot 特定元数据 (JSON5 格式)
metadata: |
  {
    "moltbot": {
      "skillKey": "custom-key",
      "emoji": "🎯",
      "homepage": "https://...",
      "primaryEnv": "node|python|go|rust",
      "always": true/false,
      "os": ["darwin", "linux", "win32"],

      "requires": {
        "bins": ["ffmpeg", "git"],
        "anyBins": ["python3", "python"],
        "env": ["OPENAI_API_KEY"],
        "config": ["tool.clawdbot.example"]
      },

      "install": [
        {
          "kind": "brew|node|go|uv|download",
          "id": "skill-id",
          "label": "Display name",
          "formula": "homebrew/formula",
          "package": "npm-package",
          "module": "python-module",
          "url": "download-url",
          "bins": ["resulting-binary"],
          "os": ["darwin"]
        }
      ]
    }
  }
---
# Skill Content

Your skill instructions here...
```

### 12.2 技能加载优先级

**文件**: `src/agents/skills/workspace.ts`

```
优先级（从高到低）:
1. 工作区技能: .skills/
2. 受管技能: .skill-bundles/
3. 打包技能: bundled skills
4. 额外目录: additional skill directories
```

### 12.3 系统提示词中的技能章节

```
## Skills (mandatory)
Before replying: scan <available_skills> <description> entries.
- If exactly one skill clearly applies: read its SKILL.md at <location> with `read`, then follow it.
- If multiple could apply: choose the most specific one, then read/follow it.
- If none clearly apply: do not read any SKILL.md.
Constraints: never read more than one skill up front; only read after selecting.

<available_skills>
- 1password: Manage passwords and secrets via 1Password CLI
- github: Interact with GitHub repositories
...
</available_skills>
```

---

## 十三、上下文压缩系统

### 13.1 核心常量

**文件**: `src/agents/compaction.ts`

```typescript
export const BASE_CHUNK_RATIO = 0.4;   // 40% 保留最近历史
export const MIN_CHUNK_RATIO = 0.15;   // 最小 15%
export const SAFETY_MARGIN = 1.2;      // 20% 估算缓冲
export const DEFAULT_CONTEXT_TOKENS = 128000;  // 默认上下文窗口

const MERGE_SUMMARIES_INSTRUCTIONS =
  "Merge these partial summaries into a single cohesive summary. " +
  "Preserve decisions, TODOs, open questions, and any constraints.";
```

### 13.2 Token 估算

```typescript
export function estimateMessagesTokens(messages: AgentMessage[]): number {
  return messages.reduce((sum, message) => sum + estimateTokens(message), 0);
}
```

### 13.3 消息分块

```typescript
// 按 Token 比例分割
export function splitMessagesByTokenShare(
  messages: AgentMessage[],
  parts = 2,
): AgentMessage[][] {
  const totalTokens = estimateMessagesTokens(messages);
  const targetTokens = totalTokens / parts;
  const chunks: AgentMessage[][] = [];
  let current: AgentMessage[] = [];
  let currentTokens = 0;

  for (const message of messages) {
    const messageTokens = estimateTokens(message);
    if (chunks.length < parts - 1 && current.length > 0 &&
        currentTokens + messageTokens > targetTokens) {
      chunks.push(current);
      current = [];
      currentTokens = 0;
    }
    current.push(message);
    currentTokens += messageTokens;
  }

  if (current.length > 0) chunks.push(current);
  return chunks;
}

// 按最大 Token 分块
export function chunkMessagesByMaxTokens(
  messages: AgentMessage[],
  maxTokens: number,
): AgentMessage[][] {
  const chunks: AgentMessage[][] = [];
  let currentChunk: AgentMessage[] = [];
  let currentTokens = 0;

  for (const message of messages) {
    const messageTokens = estimateTokens(message);
    if (currentChunk.length > 0 && currentTokens + messageTokens > maxTokens) {
      chunks.push(currentChunk);
      currentChunk = [];
      currentTokens = 0;
    }
    currentChunk.push(message);
    currentTokens += messageTokens;
  }

  if (currentChunk.length > 0) chunks.push(currentChunk);
  return chunks;
}
```

### 13.4 自适应分块比例

```typescript
export function computeAdaptiveChunkRatio(
  messages: AgentMessage[],
  contextWindow: number,
): number {
  if (messages.length === 0) return BASE_CHUNK_RATIO;

  const totalTokens = estimateMessagesTokens(messages);
  const avgTokens = totalTokens / messages.length;

  // 应用安全边界
  const safeAvgTokens = avgTokens * SAFETY_MARGIN;
  const avgRatio = safeAvgTokens / contextWindow;

  // 如果平均消息 > 上下文的 10%，减少分块比例
  if (avgRatio > 0.1) {
    const reduction = Math.min(avgRatio * 2, BASE_CHUNK_RATIO - MIN_CHUNK_RATIO);
    return Math.max(MIN_CHUNK_RATIO, BASE_CHUNK_RATIO - reduction);
  }

  return BASE_CHUNK_RATIO;
}
```

### 13.5 分阶段摘要

```typescript
export async function summarizeInStages(params: {
  messages: AgentMessage[];
  model: ExtensionContext["model"];
  apiKey: string;
  signal: AbortSignal;
  reserveTokens: number;
  maxChunkTokens: number;
  contextWindow: number;
  parts?: number;
}): Promise<string> {
  const parts = params.parts ?? 2;
  const splits = splitMessagesByTokenShare(messages, parts);

  // 1. 对每个分块生成部分摘要
  const partialSummaries: string[] = [];
  for (const chunk of splits) {
    partialSummaries.push(await summarizeWithFallback({ ...params, messages: chunk }));
  }

  // 2. 合并部分摘要
  if (partialSummaries.length === 1) return partialSummaries[0];

  const summaryMessages = partialSummaries.map((summary) => ({
    role: "user",
    content: summary,
    timestamp: Date.now(),
  }));

  return summarizeWithFallback({
    ...params,
    messages: summaryMessages,
    customInstructions: MERGE_SUMMARIES_INSTRUCTIONS,
  });
}
```

---

## 十四、Gateway 协议

### 14.1 连接流程

```
1. CLIENT → SERVER: { type: "hello", protocol: 1, client: {...} }
2. SERVER → CLIENT: { type: "hello-ok", protocol: 1, server: {...}, features: {...} }
3. 双向通信: { type: "event" | "request" | "response" }
```

### 14.2 帧结构

**文件**: `src/gateway/protocol/schema/frames.ts`

```typescript
// 连接参数
export type ConnectParams = {
  minProtocol: number;
  maxProtocol: number;
  client: {
    id: string;
    displayName?: string;
    version: string;
    platform: string;
    mode: "app" | "web" | "cli";
  };
  caps?: string[];
  auth?: { token?: string; password?: string };
};

// Hello OK 响应
export type HelloOk = {
  type: "hello-ok";
  protocol: number;
  server: {
    version: string;
    host?: string;
    connId: string;
  };
  features: {
    methods: string[];
    events: string[];
  };
  snapshot: Snapshot;
};

// 事件帧
export type EventFrame = {
  id: string;
  type: "event";
  at: number;
  event: string;
  payload?: object;
  sessionKey?: string;
};

// 请求帧
export type RequestFrame = {
  id: string;
  type: "request";
  method: string;
  params?: object;
  sessionKey?: string;
};

// 响应帧
export type ResponseFrame = {
  id: string;
  type: "response";
  result?: object;
  error?: ErrorShape;
};
```

### 14.3 错误码

```typescript
export enum ErrorCode {
  NOT_LINKED = "NOT_LINKED",       // 认证提供商未连接
  NOT_PAIRED = "NOT_PAIRED",       // 设备未配对
  AGENT_TIMEOUT = "AGENT_TIMEOUT", // 代理操作超时
  INVALID_REQUEST = "INVALID_REQUEST", // 无效请求
  UNAVAILABLE = "UNAVAILABLE",     // 服务暂时不可用
}
```

### 14.4 Gateway 方法

```
agents.*:     agents.list(), agents.identity()
chat.*:       chat.send(), chat.inject(), chat.abort(), chat.history()
sessions.*:   sessions.list(), sessions.history(), sessions.send(), sessions.spawn()
cron.*:       cron.list(), cron.add(), cron.update(), cron.remove(), cron.run()
config.*:     config.get(), config.schema(), config.apply(), config.set()
channels.*:   channels.status(), channels.logout()
device-pair.*: device-pair.list(), device-pair.approve()
models.*:     models.list()
logs.*:       logs.tail()
```

---

## 十五、内存和向量搜索

### 15.1 内存目录结构

**文件**: `src/memory/`

```
memory/
├── embeddings/          # 多提供商（OpenAI、Gemini、Node-Llama）
├── sqlite.ts            # SQLite 存储
├── sqlite-vec.ts        # 向量扩展
├── search-manager.ts    # 语义搜索
├── memory-schema.ts     # 数据库初始化
└── sync-*.ts           # 文件同步
```

### 15.2 内存工具

```typescript
// memory_search: 语义搜索
const results = await memorySearch({
  query: "user preferences",
  maxResults: 10,
  minScore: 0.5,
});

// memory_get: 精确读取
const content = await memoryGet({
  path: "memory/2026-01-29.md",
  lines: "10-20",
});
```

### 15.3 Embedding 提供商

```typescript
type EmbeddingProvider = "openai" | "gemini" | "node-llama" | "local";

// 默认: OpenAI text-embedding-3-small
const embedding = await generateEmbedding(text, {
  provider: "openai",
  model: "text-embedding-3-small",
});
```

---

## 十六、插件系统

### 16.1 插件目录结构

**文件**: `src/plugins/`, `src/plugin-sdk/`

```
plugins/
├── manifest-registry.ts  # 插件发现与验证
├── loader.ts            # 动态 ESM/CommonJS 加载
├── runtime/types.ts     # 100+ 运行时 API 注入
├── commands.ts          # 插件命令注册
├── http-path.ts         # URL 路由
├── schema-validator.ts  # Manifest 验证
├── enable.ts            # 生命周期管理
└── install.ts           # 包安装
```

### 16.2 插件运行时注入

```typescript
// 插件可以访问的 API
interface PluginRuntime {
  // 回复调度器
  replyDispatcher: ReplyDispatcher;

  // 内存工具
  memorySearch: (query: string) => Promise<MemoryResult[]>;
  memoryGet: (path: string) => Promise<string>;

  // 频道操作
  sendMessage: (channel: string, message: string) => Promise<void>;
  sendTyping: (channel: string) => Promise<void>;

  // 配置加载
  loadConfig: () => MoltbotConfig;

  // 会话管理
  getSession: (key: string) => SessionEntry | undefined;

  // 媒体处理
  fetchMedia: (url: string) => Promise<Buffer>;
  resizeImage: (buffer: Buffer, width: number) => Promise<Buffer>;

  // 命令执行
  exec: (cmd: string, opts?: ExecOpts) => Promise<ExecResult>;

  // 平台特定
  telegram: TelegramAPI;
  discord: DiscordAPI;
  slack: SlackAPI;
}
```

---

## 十七、错误处理与重试

### 17.1 错误类型

**文件**: `src/infra/errors.ts`

```typescript
export class ConfigError extends Error { ... }
export class ChannelError extends Error { ... }
export class ToolError extends Error { ... }
export class AgentError extends Error { ... }
export class AuthError extends Error { ... }
```

### 17.2 重试策略

**文件**: `src/infra/retry-policy.ts`, `src/infra/retry.ts`

```typescript
// 渠道特定的重试策略
const DISCORD_RETRY_POLICY = {
  maxRetries: 3,
  minDelayMs: 500,
  maxDelayMs: 30000,
  jitter: 0.1,
  isRetryable: (error) => error instanceof RateLimitError,
};

const TELEGRAM_RETRY_POLICY = {
  maxRetries: 3,
  minDelayMs: 400,
  maxDelayMs: 30000,
  isRetryable: (error) => /429|timeout|unavailable/i.test(error.message),
};

// 重试框架
export async function retryAsync<T>(
  fn: () => Promise<T>,
  policy: RetryPolicy,
): Promise<T> {
  let attempt = 0;
  while (true) {
    try {
      return await fn();
    } catch (error) {
      attempt++;
      if (attempt >= policy.maxRetries || !policy.isRetryable(error)) {
        throw error;
      }
      const delay = exponentialBackoff(attempt, policy);
      policy.onRetry?.(error, attempt);
      await sleep(delay);
    }
  }
}
```

---

## 十八、关键文件清单

### 18.1 Agent 运行时

| 文件 | 说明 |
|------|------|
| `agents/pi-embedded-runner/run.ts` | Agent 执行主入口 |
| `agents/pi-embedded-runner/run/attempt.ts` | 单次执行逻辑 |
| `agents/pi-embedded-subscribe.ts` | 流式响应处理 |
| `agents/system-prompt.ts` | 系统提示词生成 (592 行) |
| `agents/workspace.ts` | Bootstrap 文件加载 |
| `agents/compaction.ts` | 上下文压缩 |

### 18.2 工具系统

| 文件 | 说明 |
|------|------|
| `agents/tool-policy.ts` | 工具分组和策略 |
| `agents/pi-tools.ts` | 工具创建 |
| `agents/pi-tools.policy.ts` | 策略过滤 |
| `agents/bash-tools.exec.ts` | Bash/Exec 工具 |
| `agents/moltbot-tools.ts` | Moltbot 特有工具 |

### 18.3 会话和子代理

| 文件 | 说明 |
|------|------|
| `acp/session.ts` | ACP 会话存储 |
| `agents/subagent-announce.ts` | 子代理汇报 |
| `agents/subagent-registry.ts` | 子代理生命周期 |
| `agents/tools/sessions-spawn-tool.ts` | Spawn 工具 |

### 18.4 自主运行

| 文件 | 说明 |
|------|------|
| `infra/heartbeat-runner.ts` | 心跳管理 (901 行) |
| `infra/heartbeat-events.ts` | 心跳事件 |
| `cron/service.ts` | Cron 服务 |
| `cron/service/state.ts` | Cron 状态机 |

### 18.5 认证和配置

| 文件 | 说明 |
|------|------|
| `agents/auth-profiles/store.ts` | 配置文件存储 |
| `agents/auth-profiles/order.ts` | Profile 选择 |
| `agents/auth-profiles/usage.ts` | 使用统计 |
| `config/config.ts` | 配置加载 |

### 18.6 Gateway

| 文件 | 说明 |
|------|------|
| `gateway/server.impl.ts` | Gateway 服务器 |
| `gateway/protocol/schema/frames.ts` | 协议帧 |
| `gateway/protocol/schema/cron.ts` | Cron 协议 |
| `gateway/server-cron.ts` | Cron 集成 |

### 18.7 技能和插件

| 文件 | 说明 |
|------|------|
| `agents/skills/frontmatter.ts` | YAML 解析 |
| `agents/skills/workspace.ts` | 技能发现 |
| `plugins/loader.ts` | 插件加载 |
| `plugins/manifest-registry.ts` | Manifest 验证 |

---

**文档完成**: 2026-01-29
**文档类型**: MoltBot 完整架构分析
**基于**: MoltBot TypeScript 源码深度分析
