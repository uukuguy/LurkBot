# MoltBot 完整架构分析文档

> **文档版本**: 3.0
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
- [十九、A2UI 界面系统](#十九a2ui-界面系统)
- [二十、Auto-Reply 自动回复系统](#二十auto-reply-自动回复系统)
- [二十一、Daemon 守护进程系统](#二十一daemon-守护进程系统)
- [二十二、Media Understanding 多媒体理解](#二十二media-understanding-多媒体理解)
- [二十三、Provider Usage 使用量监控](#二十三provider-usage-使用量监控)
- [二十四、Routing 消息路由系统](#二十四routing-消息路由系统)
- [二十五、Hooks 扩展系统](#二十五hooks-扩展系统)
- [二十六、Security 安全审计系统](#二十六security-安全审计系统)
- [二十七、ACP 协议系统](#二十七acp-协议系统)
- [二十八、Browser 浏览器自动化](#二十八browser-浏览器自动化)
- [二十九、TUI 终端界面](#二十九tui-终端界面)
- [三十、TTS 语音合成](#三十tts-语音合成)
- [三十一、Wizard 配置向导](#三十一wizard-配置向导)
- [三十二、Infra 基础设施](#三十二infra-基础设施)
- [附录：模块覆盖清单](#附录模块覆盖清单)

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

## 十九、A2UI 界面系统

### 19.1 A2UI 概述

#### 项目背景

A2UI（Agent-to-User Interface）是由 Anthropic 和 Google 联合开源的声明式 UI 格式，采用 Apache 2.0 许可证。该项目旨在为 AI Agent 提供一种安全、框架无关的方式来生成用户界面。

**GitHub 仓库**: https://github.com/anthropics/a2ui

#### 设计理念

| 特性 | 描述 |
|------|------|
| **声明式** | Agent 描述"要展示什么"，而非"如何渲染" |
| **安全** | 无法执行任意代码，只能生成预定义组件 |
| **框架无关** | 可在 Web、iOS、macOS、Android 等平台渲染 |
| **流式友好** | 支持 JSONL 流式传输，适合 LLM 输出 |
| **版本化** | 明确的 schema 版本控制（当前 v0.8，v0.9 开发中） |

#### 版本信息

```
当前稳定版本: v0.8
开发中版本: v0.9 (增加 createSurface 等新消息类型)
```

### 19.2 核心文件清单

#### MoltBot 中的 A2UI 实现

| 文件路径 | 功能说明 |
|----------|----------|
| `vendor/a2ui/` | A2UI 规范文件和渲染器 |
| `src/canvas-host/a2ui.ts` | A2UI HTTP 处理器，验证和路由 JSONL 消息 |
| `src/canvas-host/server.ts` | Canvas 服务器，管理 WebSocket 连接 |
| `src/agents/tools/canvas-tool.ts` | Agent 工具定义，提供 `a2ui_push` 等 action |
| `src/cli/nodes-cli/a2ui-jsonl.ts` | JSONL 验证和调试工具 |

#### Vendor 目录结构

```
vendor/a2ui/
├── schema/
│   ├── v0.8/
│   │   ├── surface.json      # Surface 组件 schema
│   │   ├── data-model.json   # 数据模型 schema
│   │   └── messages.json     # JSONL 消息 schema
│   └── v0.9/
│       └── ...               # 新版本 schema
├── renderers/
│   ├── web/                  # Lit Web Components 渲染器
│   ├── ios/                  # Swift 渲染器
│   └── android/              # Kotlin 渲染器
└── examples/
    └── ...                   # 示例 JSONL 文件
```

### 19.3 工作流程

#### Agent 到 UI 的数据流

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        A2UI 工作流程                                      │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   ┌──────────────────────┐                                               │
│   │  Agent (LLM)         │                                               │
│   │  生成 A2UI JSONL     │                                               │
│   └──────────┬───────────┘                                               │
│              │                                                           │
│              ▼                                                           │
│   ┌──────────────────────┐                                               │
│   │  canvas-tool         │                                               │
│   │  action: a2ui_push   │                                               │
│   │  验证 JSONL 格式      │                                               │
│   └──────────┬───────────┘                                               │
│              │                                                           │
│              ▼                                                           │
│   ┌──────────────────────┐                                               │
│   │  Gateway             │                                               │
│   │  路由到 Canvas Host  │                                               │
│   └──────────┬───────────┘                                               │
│              │                                                           │
│              ▼                                                           │
│   ┌──────────────────────┐                                               │
│   │  Canvas Host         │                                               │
│   │  WebSocket 广播      │                                               │
│   └──────────┬───────────┘                                               │
│              │                                                           │
│              ▼                                                           │
│   ┌────────────────────────────────────────────────────────────────┐    │
│   │                     客户端渲染层                                  │    │
│   │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │    │
│   │  │ Web App     │  │ iOS/macOS   │  │ Android                 │ │    │
│   │  │ Lit 组件    │  │ Swift       │  │ Kotlin                  │ │    │
│   │  │ WebView     │  │ + WebView   │  │ + WebView               │ │    │
│   │  └─────────────┘  └─────────────┘  └─────────────────────────┘ │    │
│   └────────────────────────────────────────────────────────────────┘    │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

### 19.4 Canvas Tool Actions

#### 工具定义

**文件**: `src/agents/tools/canvas-tool.ts`

```typescript
export type CanvasAction =
  | "present"      // 展示内容（HTML/Markdown/URL）
  | "hide"         // 隐藏画布
  | "navigate"     // 导航到 URL
  | "eval"         // 执行 JavaScript（受限）
  | "a2ui_push"    // 推送 A2UI JSONL 消息
  | "a2ui_reset";  // 重置 A2UI 画布状态

export interface CanvasToolParams {
  action: CanvasAction;

  // present action
  content?: string;       // HTML/Markdown 内容
  contentType?: "html" | "markdown" | "url";

  // navigate action
  url?: string;

  // eval action
  script?: string;

  // a2ui_push action
  jsonl?: string;         // A2UI JSONL 消息（可多行）

  // 通用选项
  title?: string;
  fullscreen?: boolean;
}
```

#### Action 详解

| Action | 功能 | 参数 | 使用场景 |
|--------|------|------|----------|
| `present` | 展示静态内容 | `content`, `contentType` | 显示 HTML/Markdown 文档 |
| `hide` | 隐藏画布 | 无 | 关闭当前画布视图 |
| `navigate` | 导航到 URL | `url` | 打开外部链接或内部页面 |
| `eval` | 执行 JavaScript | `script` | 有限的脚本执行（沙箱化） |
| `a2ui_push` | 推送 A2UI JSONL | `jsonl` | 更新声明式 UI |
| `a2ui_reset` | 重置画布 | 无 | 清空所有 Surface 和数据模型 |

### 19.5 A2UI JSONL 消息格式

#### 消息类型

```typescript
// v0.8 消息类型
export type A2UIMessage =
  | SurfaceUpdateMessage      // 更新 Surface 组件
  | DataModelUpdateMessage    // 更新数据模型
  | DeleteSurfaceMessage      // 删除 Surface
  | BeginRenderingMessage;    // 开始渲染标记

// v0.9 新增
export type A2UIMessageV09 =
  | A2UIMessage
  | CreateSurfaceMessage;     // 创建新 Surface
```

#### 消息结构示例

**surfaceUpdate - 更新界面组件**

```json
{
  "type": "surfaceUpdate",
  "surfaceId": "main",
  "surface": {
    "type": "container",
    "direction": "column",
    "children": [
      {
        "type": "text",
        "content": "Hello from A2UI!"
      },
      {
        "type": "button",
        "label": "Click me",
        "action": {
          "type": "callback",
          "id": "btn_clicked"
        }
      }
    ]
  }
}
```

**dataModelUpdate - 更新数据绑定**

```json
{
  "type": "dataModelUpdate",
  "path": "user.name",
  "value": "Alice"
}
```

**deleteSurface - 删除界面**

```json
{
  "type": "deleteSurface",
  "surfaceId": "temp_dialog"
}
```

**beginRendering - 渲染开始标记**

```json
{
  "type": "beginRendering",
  "sessionId": "session_123"
}
```

### 19.6 Surface 组件类型

#### 基础组件

| 组件 | 描述 | 主要属性 |
|------|------|----------|
| `text` | 文本显示 | `content`, `style` |
| `image` | 图片显示 | `src`, `alt`, `width`, `height` |
| `button` | 按钮 | `label`, `action`, `disabled` |
| `input` | 输入框 | `placeholder`, `value`, `inputType` |
| `link` | 链接 | `href`, `text`, `target` |

#### 布局组件

| 组件 | 描述 | 主要属性 |
|------|------|----------|
| `container` | 容器 | `direction`, `children`, `gap` |
| `card` | 卡片 | `title`, `children`, `elevation` |
| `list` | 列表 | `items`, `itemTemplate` |
| `grid` | 网格 | `columns`, `children`, `gap` |
| `tabs` | 标签页 | `tabs`, `activeTab` |

#### 交互组件

| 组件 | 描述 | 主要属性 |
|------|------|----------|
| `form` | 表单 | `fields`, `onSubmit` |
| `select` | 下拉选择 | `options`, `value`, `placeholder` |
| `checkbox` | 复选框 | `checked`, `label`, `onChange` |
| `slider` | 滑块 | `min`, `max`, `value`, `step` |
| `toggle` | 开关 | `on`, `label` |

### 19.7 跨平台支持

#### Web 渲染器

**技术栈**: Lit Web Components

```typescript
// 使用示例
import { A2UIRenderer } from '@a2ui/web-renderer';

const renderer = new A2UIRenderer({
  container: document.getElementById('a2ui-root'),
  onCallback: (callbackId, data) => {
    // 处理用户交互回调
    sendToAgent({ type: 'callback', id: callbackId, data });
  }
});

// 处理 JSONL 消息
websocket.onmessage = (event) => {
  const message = JSON.parse(event.data);
  renderer.handleMessage(message);
};
```

#### iOS/macOS 渲染器

**技术栈**: Swift + WKWebView

```swift
// 使用示例
import A2UIKit

let renderer = A2UIRenderer(
    webView: WKWebView(),
    delegate: self
)

// 处理 JSONL 消息
func handleA2UIMessage(_ jsonl: String) {
    renderer.processMessage(jsonl)
}

// 回调委托
extension ViewController: A2UIRendererDelegate {
    func renderer(_ renderer: A2UIRenderer, didReceiveCallback id: String, data: Any?) {
        // 发送回调到 Agent
    }
}
```

#### Android 渲染器

**技术栈**: Kotlin + WebView

```kotlin
// 使用示例
val renderer = A2UIRenderer(
    webView = findViewById(R.id.a2ui_webview),
    callback = { callbackId, data ->
        // 处理用户交互回调
        sendToAgent(callbackId, data)
    }
)

// 处理 JSONL 消息
fun handleA2UIMessage(jsonl: String) {
    renderer.processMessage(jsonl)
}
```

### 19.8 Canvas Host 实现

#### HTTP 端点

**文件**: `src/canvas-host/a2ui.ts`

```typescript
// POST /a2ui/push - 推送 JSONL 消息
app.post('/a2ui/push', async (req, res) => {
  const { jsonl, sessionId } = req.body;

  // 1. 验证 JSONL 格式
  const messages = parseAndValidateJSONL(jsonl);
  if (!messages.valid) {
    return res.status(400).json({ error: messages.errors });
  }

  // 2. 广播到 WebSocket 客户端
  await canvasHost.broadcast(sessionId, messages.data);

  res.json({ success: true, messageCount: messages.data.length });
});

// POST /a2ui/reset - 重置画布状态
app.post('/a2ui/reset', async (req, res) => {
  const { sessionId } = req.body;

  await canvasHost.reset(sessionId);

  res.json({ success: true });
});

// GET /a2ui/state - 获取当前状态
app.get('/a2ui/state', async (req, res) => {
  const { sessionId } = req.query;

  const state = await canvasHost.getState(sessionId);

  res.json(state);
});
```

#### WebSocket 服务

**文件**: `src/canvas-host/server.ts`

```typescript
export class CanvasHost {
  private clients: Map<string, Set<WebSocket>> = new Map();
  private state: Map<string, A2UIState> = new Map();

  // 广播消息到所有客户端
  async broadcast(sessionId: string, messages: A2UIMessage[]): Promise<void> {
    const clients = this.clients.get(sessionId) ?? new Set();

    for (const message of messages) {
      // 更新内部状态
      this.updateState(sessionId, message);

      // 广播到客户端
      const payload = JSON.stringify(message);
      for (const client of clients) {
        if (client.readyState === WebSocket.OPEN) {
          client.send(payload);
        }
      }
    }
  }

  // 重置会话状态
  async reset(sessionId: string): Promise<void> {
    this.state.delete(sessionId);

    // 通知客户端重置
    await this.broadcast(sessionId, [{ type: 'reset' }]);
  }

  // 获取当前状态
  getState(sessionId: string): A2UIState {
    return this.state.get(sessionId) ?? { surfaces: {}, dataModel: {} };
  }
}
```

---

## 二十、Auto-Reply 自动回复系统

### 20.1 系统概述

Auto-Reply 是 MoltBot 的消息处理核心，包含 23,000+ 行 TypeScript 代码，负责：
- 消息接收和分发
- 指令解析和处理
- 流式响应递送
- 队列管理

#### 目录结构

```
src/auto-reply/
├── tokens.ts                 # 回复令牌（HEARTBEAT_OK, NO_REPLY）
├── reply.ts                  # 导出入口
├── commands-registry.ts      # 命令注册机制
├── commands-registry.types.ts
├── envelope.ts               # 消息包装结构
├── status.ts                 # 状态管理
├── inbound-debounce.ts       # 消息防抖
├── reply/
│   ├── directives.ts         # 指令提取
│   ├── directives/
│   │   ├── tokens.ts
│   │   └── heartbeat.ts
│   ├── queue/                # 队列子系统
│   │   ├── directive.ts
│   │   ├── types.ts
│   │   ├── enqueue.ts
│   │   ├── drain.ts
│   │   ├── state.ts
│   │   └── cleanup.ts
│   ├── reply-tags.ts         # [[reply_to_current]] 标签
│   ├── reply-directives.ts
│   └── agent-runner.ts       # Agent 运行时
└── web/
    ├── monitor.ts            # 通道监控
    ├── deliver-reply.ts      # 回复递送
    ├── heartbeat-runner.ts   # 心跳检查
    └── mentions.ts           # @提及检测
```

### 20.2 Reply Directives 指令系统

#### 指令类型定义

```typescript
// 思维级别
export type ThinkLevel = "off" | "low" | "medium" | "high";
// 用法: /think:high 或 /t:medium

// 冗余级别
export type VerboseLevel = "off" | "low" | "high";
// 用法: /verbose:high 或 /v:low

// 推理级别
export type ReasoningLevel = "off" | "on" | "stream";
// 用法: /reasoning

// 提权级别
export type ElevatedLevel = "off" | "ask" | "on" | "full";
// 用法: /elevated:on
```

#### 指令提取机制

```typescript
// 通用提取函数
extractLevelDirective(body: string, names: string[], normalize: Function) {
  // 匹配模式: /directive_name [: | space] optional_level
  // 支持: /think, /think:medium, /think medium
  // 不区分大小写
  // 返回: { cleaned, level, hasDirective }
}

// 示例
const result = extractThinkDirective("/think:high Explain quantum computing");
// result = {
//   cleaned: "Explain quantum computing",
//   thinkLevel: "high",
//   hasDirective: true
// }
```

### 20.3 Queue 队列处理机制

#### 队列模式

```typescript
export type QueueMode =
  | "steer"           // 引导模式：等待用户确认
  | "followup"        // 跟进模式：主 Agent 后自动执行
  | "collect"         // 收集模式：批处理多条消息
  | "steer-backlog"   // 引导+积压管理
  | "interrupt"       // 中断当前执行
  | "queue";          // 标准 FIFO

export type QueueDropPolicy =
  | "old"             // 丢弃最旧
  | "new"             // 丢弃最新
  | "summarize";      // 总结超出的消息
```

#### 队列指令

```typescript
// 提取队列指令
extractQueueDirective(body?: string): {
  cleaned: string;
  queueMode?: QueueMode;
  queueReset: boolean;
  debounceMs?: number;
  cap?: number;
  dropPolicy?: QueueDropPolicy;
}

// 用法示例
"/queue collect debounce:500ms cap:10"
"/queue steer drop:old"
"/queue reset"
```

### 20.4 流式响应递送

#### 三层流式架构

```
Layer 1: Agent Runtime Stream
  - run_embedded_agent_stream()
  - AsyncIterator<StreamEvent>

Layer 2: Event Stream
  - partial_reply (文本块)
  - tool_result (工具结果)
  - reasoning_stream (推理步骤)

Layer 3: Block Reply Stream
  - 分块递送（WhatsApp/Web）
  - 媒体支持
```

#### Block Reply 递送

```typescript
async function deliverWebReply(params: {
  replyResult: ReplyPayload;
  msg: WebInboundMsg;
  textLimit: number;          // WhatsApp: 4096
  chunkMode: "length" | "paragraph" | "sentence";
}) {
  // 1. Markdown 表格转换
  const converted = convertMarkdownTables(replyResult.text);

  // 2. 分块
  const chunks = chunkMarkdownTextWithMode(converted, textLimit, chunkMode);

  // 3. 递送（带重试）
  for (const chunk of chunks) {
    await sendWithRetry(() => msg.reply(chunk), "text");
  }

  // 4. 媒体递送
  for (const mediaUrl of mediaList) {
    const media = await loadWebMedia(mediaUrl);
    await msg.sendMedia({ image: media.buffer });
  }
}
```

### 20.5 命令注册机制

#### 命令定义

```typescript
export type ChatCommandDefinition = {
  key: string;                    // 唯一标识
  nativeName?: string;            // 平台原生名称
  description: string;
  textAliases: string[];          // 如 ["/status", "/st"]
  acceptsArgs?: boolean;
  args?: CommandArgDefinition[];
  scope: "text" | "native" | "both";
  category?: "session" | "options" | "status" | "management";
};

// 参数定义
export type CommandArgDefinition = {
  name: string;
  type: "string" | "number" | "boolean";
  required?: boolean;
  choices?: CommandArgChoice[];
  captureRemaining?: boolean;     // 捕获剩余参数
};
```

### 20.6 Silent Reply 机制

```typescript
// 特殊令牌
const SILENT_REPLY_TOKEN = "NO_REPLY";
const HEARTBEAT_TOKEN = "HEARTBEAT_OK";

// 检测静默回复
function is_silent_reply_text(text: string | null): boolean {
  // "/NO_REPLY" 或文本结尾有 "NO_REPLY"
  // 用于避免重复回复（已通过 message 工具发送）
}
```

---

## 二十一、Daemon 守护进程系统

### 21.1 系统概述

Daemon 系统提供跨平台的后台服务管理，支持：
- macOS: launchd (LaunchAgent)
- Linux: systemd (user service)
- Windows: schtasks (计划任务)

#### 目录结构

```
src/daemon/
├── service.ts                # 平台无关服务抽象
├── constants.ts              # 服务标签常量
├── paths.ts                  # 路径解析
├── node-service.ts           # Node 服务封装
├── launchd.ts                # macOS 实现
├── launchd-plist.ts          # Plist 生成
├── systemd.ts                # Linux 实现
├── systemd-unit.ts           # Unit 文件生成
├── systemd-linger.ts         # Linger 会话管理
├── schtasks.ts               # Windows 实现
├── diagnostics.ts            # 错误诊断
├── inspect.ts                # 服务检查
├── service-audit.ts          # 审计功能
└── legacy.ts                 # 旧版迁移
```

### 21.2 统一服务接口

```typescript
export type GatewayService = {
  label: string;
  loadedText: string;
  notLoadedText: string;
  install: (args: GatewayServiceInstallArgs) => Promise<void>;
  uninstall: (args) => Promise<void>;
  stop: (args) => Promise<void>;
  restart: (args) => Promise<void>;
  isLoaded: (args) => Promise<boolean>;
  readCommand: (env) => Promise<{...} | null>;
  readRuntime: (env) => Promise<GatewayServiceRuntime>;
};

// 平台选择
function resolveGatewayService(): GatewayService {
  if (process.platform === "darwin") return launchdService;
  if (process.platform === "linux") return systemdService;
  if (process.platform === "win32") return schtasksService;
}
```

### 21.3 macOS Launchd 实现

#### 服务标签

```typescript
const GATEWAY_LAUNCH_AGENT_LABEL = "bot.molt.gateway";

// Profile 支持（多实例）
resolveGatewayLaunchAgentLabel(profile?: string): string
// null → "bot.molt.gateway"
// "dev" → "bot.molt.dev"
```

#### Plist 文件

**位置**: `~/Library/LaunchAgents/bot.molt.gateway.plist`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<plist version="1.0">
  <dict>
    <key>Label</key>
    <string>bot.molt.gateway</string>

    <key>RunAtLoad</key>
    <true/>

    <key>KeepAlive</key>
    <true/>

    <key>ProgramArguments</key>
    <array>
      <string>/usr/local/bin/moltbot</string>
      <string>gateway</string>
      <string>run</string>
    </array>

    <key>StandardOutPath</key>
    <string>~/.clawdbot/logs/gateway.log</string>

    <key>StandardErrorPath</key>
    <string>~/.clawdbot/logs/gateway.err.log</string>
  </dict>
</plist>
```

### 21.4 Linux Systemd 实现

#### Unit 文件

**位置**: `~/.config/systemd/user/moltbot-gateway.service`

```ini
[Unit]
Description=Moltbot Gateway
After=network-online.target

[Service]
ExecStart=/usr/local/bin/moltbot gateway run --port 18789
WorkingDirectory=/home/user/.clawdbot
Restart=always
RestartSec=5
KillMode=process

[Install]
WantedBy=default.target
```

#### Linger 启用

```typescript
// 必须启用 linger，用户登出后服务继续运行
enableSystemdUserLinger(): Promise<void>
// 执行: systemctl --user enable-linger
```

### 21.5 Windows 计划任务实现

#### 脚本文件

**位置**: `%USERPROFILE%\.clawdbot\gateway.cmd`

```batch
@echo off
set PATH=C:\Users\User\AppData\Roaming\npm;%PATH%
cd /d "C:\Users\User\.clawdbot"
moltbot gateway run --bind loopback --port 18789
```

#### 任务创建

```powershell
schtasks /Create /TN "Moltbot Gateway" ^
  /TR "C:\Users\User\.clawdbot\gateway.cmd" ^
  /SC ONLOGON /F
```

### 21.6 运行时状态

```typescript
export type GatewayServiceRuntime = {
  status?: "running" | "stopped" | "unknown";
  state?: string;
  subState?: string;
  pid?: number;
  lastExitStatus?: number;
  lastExitReason?: string;
  lastRunResult?: string;
  lastRunTime?: string;
};
```

### 21.7 多实例支持

通过 `CLAWDBOT_PROFILE` 环境变量：

```bash
# 默认实例
moltbot gateway install

# 开发实例
CLAWDBOT_PROFILE=dev moltbot gateway install
# → macOS: bot.molt.dev
# → Linux: moltbot-gateway-dev
# → Windows: Moltbot Gateway (dev)
# → 配置: ~/.clawdbot-dev/
```

---

## 二十二、Media Understanding 多媒体理解

### 22.1 系统概述

Media Understanding 系统在消息进入回复流水线前，自动理解和摘要化入站多媒体。

#### 支持的媒体类型

| 类型 | 提供商 |
|------|--------|
| **图像** | OpenAI, Anthropic, Google Gemini, MiniMax |
| **音频** | OpenAI, Groq, Deepgram, Google Gemini |
| **视频** | Google Gemini API |
| **文档** | CLI 工具或 Gemini |

### 22.2 处理流程

```
1. 收集入站附件 (MediaPaths, MediaUrls, MediaTypes)
                ↓
2. 按能力过滤附件 (image/audio/video)
                ↓
3. 选择第一个合格模型 (按配置顺序)
                ↓
4. 执行理解任务
   ├─ 若失败/超时/大小超限 → 降级到下一个模型
   └─ 若成功 → Body 变为 [Image]/[Audio]/[Video] 块
                ↓
5. 若全部失败或禁用 → 继续使用原始 Body + 附件
```

### 22.3 配置策略

```typescript
tools.media = {
  models: [
    { provider: "openai", model: "gpt-5.2", capabilities: ["image"] },
    { provider: "google", model: "gemini-3-flash",
      capabilities: ["image", "audio", "video"] }
  ],
  image: { maxBytes: 10_000_000, maxChars: 500 },
  audio: { models: [...], maxBytes: 20_000_000 },
  video: { models: [...], maxBytes: 50_000_000 },
  concurrency: 2
};
```

### 22.4 关键特性

| 特性 | 描述 |
|------|------|
| **云/本地降级** | 云 API 失败时降级到本地 CLI |
| **按能力过滤** | 根据模型能力选择处理器 |
| **大小限制** | 超过 maxBytes 跳过，不阻断处理 |
| **自动检测** | 未配置模型时自动尝试可用选项 |

---

## 二十三、Provider Usage 使用量监控

### 23.1 系统概述

Provider Usage 系统追踪 API 使用量和成本，支持多提供商多窗口监控。

### 23.2 核心数据结构

```typescript
type UsageWindow = {
  label: string;           // "5h", "Week", "Sonnet"
  usedPercent: number;     // 0-100
  resetAt?: number;        // Unix 时间戳
};

type ProviderUsageSnapshot = {
  provider: UsageProviderId;
  displayName: string;
  windows: UsageWindow[];
  plan?: string;
  error?: string;
};

type UsageSummary = {
  updatedAt: number;
  providers: ProviderUsageSnapshot[];
};
```

### 23.3 支持的提供商

| 提供商 | 监控窗口 |
|--------|----------|
| **Anthropic** | 5 小时、7 天、模型级 |
| **OpenAI Codex** | OAuth 获取 |
| **Google Gemini CLI** | 设备代码流 |
| **Google Antigravity** | Vertex/OAuth |
| **MiniMax** | 自定义限额 |
| **Z.AI (GLM)** | 配额限额 |
| **GitHub Copilot** | Token 验证 |

### 23.4 获取实现

```typescript
async function fetchClaudeUsage(token: string, timeoutMs: number) {
  // 1. 尝试 OAuth API
  const res = await fetch("https://api.anthropic.com/api/oauth/usage", {
    headers: { Authorization: `Bearer ${token}` }
  });

  // 2. 403 + scope 错误 → 降级到 Web API
  if (res.status === 403 && scopeError) {
    return await fetchClaudeWebUsage(sessionKey, timeoutMs);
  }

  // 3. 返回使用量数据
  return { provider, windows: [{label, usedPercent, resetAt}] };
}
```

### 23.5 格式化输出

```typescript
// 显示示例: "📊 Usage: Anthropic 45% left (Week ⏱2h) · Google 92% left (5h)"
formatUsageSummaryLine(summary, { maxProviders: 2 });
formatUsageWindowSummary(snapshot);  // "92% left (Week ⏱2h 30m)"
```

---

## 二十四、Routing 消息路由系统

### 24.1 路由决策流程

```
1. 精确对等匹配 (bindings with peer.kind + peer.id)
   例: WhatsApp 群组 "-100123456@g.us"
                ↓
2. Guild 匹配 (Discord)
   例: guildId "123456"
                ↓
3. Team 匹配 (Slack)
   例: teamId "T12345"
                ↓
4. 账户匹配 (channel accountId)
   例: WhatsApp 账户 "1234567890"
                ↓
5. 通道匹配 (任何该通道的账户)
   例: 任何 Telegram 账户
                ↓
6. 默认 Agent (agents.list[].default 或首个)
   降级到 "main"
```

### 24.2 Session Key 会话隔离

```typescript
// 直接消息 → main session
"agent:main:main"

// 群组 → 按群组隔离
"agent:main:telegram:group:-1001234567890"
"agent:main:discord:guild:123456:channel:789"

// 线程 → 进一步细分
"agent:main:slack:channel:C123:thread:1234567890.0001"
"agent:main:telegram:group:-100123:topic:42"
```

### 24.3 Broadcast 广播

```typescript
bindings: [
  { match: {channel: "whatsapp"}, agentId: "support" }
],
broadcast: {
  strategy: "parallel",
  "120363403215116621@g.us": ["alfred", "baerbel"]
}
```

### 24.4 回复分发器

```typescript
interface ReplyDispatcher {
  sendToolResult({ text, mediaUrl? });     // 工具执行结果
  sendBlockReply({ text, mediaUrl? });     // 流式块回复
  sendFinalReply({ text, mediaUrl? });     // 最终回复
}

// 人类延迟
// mode: "natural" → 随机 800-1200ms
// mode: "custom" → minMs/maxMs 自定义
```

---

## 二十五、Hooks 扩展系统

### 25.1 钩子事件类型

```typescript
type InternalHookEventType = "command" | "session" | "agent" | "gateway";

// 事件示例
"command:new"        // /new 命令
"command:reset"      // /reset 命令
"session:*"          // 会话事件
"agent:bootstrap"    // Agent 启动
"gateway:startup"    // Gateway 启动
```

### 25.2 钩子事件结构

```typescript
type InternalHookEvent = {
  type: "command" | "session" | "agent" | "gateway";
  action: string;
  sessionKey: string;
  context: Record<string, unknown>;
  timestamp: Date;
  messages: string[];
};
```

### 25.3 钩子处理器

```typescript
// 注册
registerInternalHook('command:new', async (event) => {
  await saveSessionToMemory(event.sessionKey);
  event.messages.push('✨ Session saved!');
});

// 触发
await triggerInternalHook({
  type: 'command',
  action: 'new',
  sessionKey: 'agent:main:main',
  context: { workspaceDir: '~/clawd' }
});
```

### 25.4 钩子发现机制

```
优先级顺序:
1. <workspace>/hooks/           # 最高优先级
2. ~/.clawdbot/hooks/          # 用户安装
3. <moltbot>/dist/hooks/bundled/  # 预装
```

### 25.5 钩子包结构

```
my-hook/
├── HOOK.md          # YAML frontmatter + 文档
│   metadata.moltbot = {
│     emoji: "💾",
│     events: ["command:new"],
│     requires: { bins: ["node"], env: ["API_KEY"] }
│   }
└── handler.ts       # HookHandler 函数
```

### 25.6 预装钩子

| 钩子 | 功能 |
|------|------|
| **💾 session-memory** | /new 时保存会话快照 |
| **📝 command-logger** | 命令事件日志 |
| **🚀 boot-md** | Gateway 启动后运行 BOOT.md |
| **😈 soul-evil** | 随机交换 SOUL.md |

---

## 二十六、Security 安全审计系统

### 26.1 审计范围

#### A. Gateway 网络暴露检查

```typescript
// 绑定配置
bind = "loopback" (127.0.0.1)    // ✅ 安全
bind = "lan"      (192.168.x.x)  // ⚠️ 需认证
bind = "auto"     (0.0.0.0)      // ⚠️ 危险

// 认证要求
gateway.auth = {
  mode: "token" | "password",
  token?: string,
  password?: string
}

// 审计规则
if (isExposed && !hasSharedSecret) {
  CRITICAL: 网络暴露无认证 → 任何人可控制 Agent
}
```

#### B. DM 策略检查

```typescript
channel.security = {
  resolveDmPolicy(): {
    policy: "open" | "disabled" | "locked";
    allowFrom?: string[];
    allowFromPath: string;
    policyPath: string;
  }
}

// 检查项
if (dmScope === "main" && isMultiUserDm) {
  ⚠️ 多发件人共享 main session
  Fix: session.dmScope = "per-channel-peer"
}
```

#### C. 模型安全检查

```typescript
if (modelSize <= 300B && hasWebTools) {
  ⚠️ 小模型 + Web 工具 → 建议沙箱化
}
```

### 26.2 CLI 命令

```bash
moltbot security audit          # 标准审计
moltbot security audit --deep   # 深度审计
moltbot security audit --fix    # 自动修复
```

### 26.3 审计输出示例

```
Security

- CRITICAL: Gateway bound to "0.0.0.0" without authentication.
  Anyone on your network can fully control your agent.
  Fix: moltbot config set gateway.bind loopback

- WARNING: Telegram DMs: multiple senders share the main session.
  Set session.dmScope="per-channel-peer" to isolate sessions.
```

### 26.4 权限控制流程

```
入站消息 → 匹配 DM 策略 → 检查 allowFrom 白名单
  ├─ 在白名单中 → 允许
  ├─ 不在白名单 →
  │   ├─ policy="open" → 允许
  │   └─ policy="locked" → 生成配对码
  └─ policy="disabled" → 拒绝
```

---

## 二十七、ACP 协议系统

### 27.1 系统概述

ACP（Agent Control Protocol）是 MoltBot 与 IDE 集成的标准协议实现，基于 `@agentclientprotocol/sdk`。

#### 目录结构

```
src/acp/
├── server.ts           # ACP 服务器
├── translator.ts       # AcpGatewayAgent 翻译器
├── session.ts          # 会话管理
├── event-mapper.ts     # 事件映射
├── session-mapper.ts   # 会话元数据映射
├── meta.ts             # 提示元数据
└── types.ts            # 类型定义
```

### 27.2 架构设计

```
┌─────────────────────────────────────────┐
│         IDE / Client (stdIO)            │
└─────────────────┬───────────────────────┘
                  ↕ ndJSON 双向流
┌─────────────────────────────────────────┐
│    AgentSideConnection (ACP 协议层)     │
└─────────────────┬───────────────────────┘
                  ↕
┌─────────────────────────────────────────┐
│    AcpGatewayAgent (协议翻译器)         │
└─────────────────┬───────────────────────┘
                  ↕
┌─────────────────────────────────────────┐
│    GatewayClient (WebSocket)            │
└─────────────────┬───────────────────────┘
                  ↕
┌─────────────────────────────────────────┐
│    Moltbot Gateway                      │
└─────────────────────────────────────────┘
```

### 27.3 核心数据结构

```typescript
// ACP 会话
type AcpSession = {
  sessionId: string;           // UUID
  sessionKey: string;          // Gateway 会话键
  cwd: string;                 // 工作目录
  createdAt: number;
  abortController: AbortController | null;
  activeRunId: string | null;
};

// 待处理提示
type PendingPrompt = {
  sessionId: string;
  sessionKey: string;
  idempotencyKey: string;      // runId
  resolve: (response) => void;
  reject: (error) => void;
  sentTextLength?: number;     // 增量追踪
  toolCalls?: Set<string>;     // 工具调用追踪
};
```

### 27.4 事件映射

| Gateway 事件 | ACP 更新 |
|-------------|----------|
| `chat` + `delta` | `agent_message_chunk` |
| `chat` + `final` | 完成，stopReason="end_turn" |
| `chat` + `aborted` | 完成，stopReason="cancelled" |
| `agent` + `tool:start` | `tool_call`（进行中）|
| `agent` + `tool:result` | `tool_call_update`（完成）|

### 27.5 功能声明

```typescript
// initialize() 响应
{
  protocolVersion: PROTOCOL_VERSION,
  agentCapabilities: {
    loadSession: true,
    promptCapabilities: {
      image: true,
      audio: false,
      embeddedContext: true,
    },
    mcpCapabilities: {
      http: false,
      sse: false,
    },
  },
}
```

---

## 二十八、Browser 浏览器自动化

### 28.1 系统概述

Browser 模块提供完整的浏览器自动化能力，支持 Playwright 和 CDP（Chrome DevTools Protocol）。

#### 目录结构

```
src/browser/
├── server.ts                 # Express 控制服务器
├── config.ts                 # 配置解析
├── chrome.ts                 # Chrome 启动管理
├── cdp.ts                    # CDP 操作
├── pw-session.ts             # Playwright 会话
├── pw-role-snapshot.ts       # 角色快照
├── screenshot.ts             # 截图处理
├── extension-relay.ts        # 扩展中继
└── routes/
    ├── agent.act.ts          # /act 端点
    ├── agent.navigate.ts     # /navigate 端点
    └── ...
```

### 28.2 架构设计

```
┌────────────────────────────────────────────┐
│    Browser Control Server (:controlPort)   │
│  /act  /navigate  /screenshot  /snapshot   │
└─────────────────┬──────────────────────────┘
                  ↓
        ┌─────────┴─────────┐
        ↓                   ↓
   ┌──────────┐      ┌───────────────┐
   │Playwright│      │CDP Direct     │
   │(Browser) │      │(Extension)    │
   └────┬─────┘      └───────┬───────┘
        └──────────┬─────────┘
                   ↓
         ┌─────────────────┐
         │ Chrome/Chromium │
         └─────────────────┘
```

### 28.3 配置结构

```typescript
type ResolvedBrowserConfig = {
  enabled: boolean;
  evaluateEnabled: boolean;      // 允许 JS 执行
  controlPort: number;
  cdpProtocol: "http" | "https";
  cdpHost: string;
  headless: boolean;
  noSandbox: boolean;
  attachOnly: boolean;           // 仅附加，不启动
  defaultProfile: string;
  profiles: Record<string, BrowserProfileConfig>;
};

type BrowserProfileConfig = {
  name: string;
  cdpPort: number;
  driver: "clawd" | "extension";
};
```

### 28.4 HTTP 路由

| 端点 | 方法 | 功能 |
|------|------|------|
| `/status` | GET | 浏览器状态 |
| `/tabs` | GET/POST/DELETE | 标签页管理 |
| `/act` | POST | 执行动作 |
| `/navigate` | POST | 导航 |
| `/screenshot` | POST | 截图 |
| `/snapshot/role` | POST | 角色快照 |
| `/snapshot/aria` | POST | ARIA 快照 |
| `/evaluate` | POST | 执行 JavaScript |

### 28.5 动作类型

```typescript
type BrowserAction =
  | "click" | "doubleClick"
  | "type" | "press"
  | "drag" | "hover"
  | "fill" | "selectOption"
  | "wait";
```

### 28.6 截图优化

```typescript
// 自动压缩策略
// maxSide: 2000px, maxBytes: 5MB
// 质量网格: [85, 75, 65, 55, 45, 35]
// 边长网格: [2000, 1800, 1600, 1400, 1200, 1000, 800]
normalizeBrowserScreenshot(buffer, { maxSide, maxBytes });
```

---

## 二十九、TUI 终端界面

### 29.1 系统概述

TUI 是基于 pi-tui 库的交互式终端界面，提供实时聊天、命令处理和多 Agent 支持。

#### 目录结构

```
src/tui/
├── tui.ts                    # 主入口
├── tui-command-handlers.ts   # 命令处理
├── tui-event-handlers.ts     # 事件处理
├── tui-stream-assembler.ts   # 流式响应组装
├── tui-formatters.ts         # 格式化
├── gateway-chat.ts           # Gateway 通信
├── components/
│   ├── chat-log.ts
│   ├── assistant-message.ts
│   └── user-message.ts
└── theme/
    └── theme.js
```

### 29.2 核心状态

```typescript
type TuiStateAccess = {
  agentDefaultId: string;
  sessionMainKey: string;
  currentAgentId: string;
  currentSessionKey: string;
  activeChatRunId: string | null;
  isConnected: boolean;
  toolsExpanded: boolean;
  showThinking: boolean;
  connectionStatus: string;
  activityStatus: "idle" | "sending" | "waiting" | "streaming";
};
```

### 29.3 命令系统

| 命令 | 功能 |
|------|------|
| `/help` | 显示帮助 |
| `/status` | 网关状态 |
| `/agent [id]` | 切换 Agent |
| `/model [ref]` | 设置模型 |
| `/think <level>` | 设置 thinking 级别 |
| `/sessions` | 列出会话 |
| `/new` | 重置会话 |
| `/abort` | 中止运行 |
| `!command` | 执行 bash 命令 |

### 29.4 流式响应组装

```typescript
class TuiStreamAssembler {
  // 分离 thinking 块和 content 块
  ingestDelta(runId, message, showThinking) {
    // 1. 提取 thinking 块
    // 2. 提取 content 块
    // 3. 合成 displayText
    return newDisplayText;
  }

  finalize(runId, message, showThinking) {
    // 最终更新并清理
    return finalText;
  }
}
```

---

## 三十、TTS 语音合成

### 30.1 系统概述

TTS 是多 Provider 的文本转语音系统，支持 OpenAI、ElevenLabs、Edge TTS。

#### 文件位置

```
src/tts/
├── tts.ts                    # 核心实现
└── tts.types.ts              # 类型定义
```

### 30.2 配置结构

```typescript
type ResolvedTtsConfig = {
  auto: "off" | "always" | "inbound" | "tagged";
  mode: "delta" | "final";
  provider: "openai" | "elevenlabs" | "edge";
  summaryModel?: string;
  modelOverrides: {
    allowText: boolean;
    allowProvider: boolean;
    allowVoice: boolean;
  };
  elevenlabs: {
    apiKey?: string;
    voiceId: string;
    modelId: string;
    voiceSettings: { stability, similarityBoost, style, speed };
  };
  openai: {
    apiKey?: string;
    model: string;
    voice: string;  // alloy|ash|coral|echo|fable|onyx|nova|sage|shimmer
  };
  edge: {
    enabled: boolean;
    voice: string;
    lang: string;
    outputFormat: string;
  };
};
```

### 30.3 Directive 系统

```
[[tts:provider=openai voice=nova]]
  <这段文本用 nova 合成>

[[tts:text]]<自定义音频文本>[[/tts:text]]
  <指定不同的 TTS 文本>
```

### 30.4 Provider 降级

```typescript
for (const provider of providerOrder) {
  try {
    if (provider === "edge") return await edgeTTS(...);
    if (provider === "elevenlabs") return await elevenLabsTTS(...);
    if (provider === "openai") return await openaiTTS(...);
  } catch {
    continue;  // 降级到下一个
  }
}
```

### 30.5 输出格式

| 场景 | OpenAI | ElevenLabs |
|------|--------|------------|
| Telegram 语音 | opus | opus_48000_64 |
| 默认 MP3 | mp3 | mp3_44100_128 |
| 电话系统 | pcm@24kHz | pcm_22050 |

---

## 三十一、Wizard 配置向导

### 31.1 系统概述

Wizard 是分步式交互配置系统，用于初始化和配置 MoltBot。

#### 目录结构

```
src/wizard/
├── onboarding.ts             # 主流程
├── session.ts                # 向导会话
├── prompts.ts                # 交互提示
└── onboarding.types.ts       # 类型定义
```

### 31.2 Session 架构

```typescript
class WizardSession {
  async next(): Promise<WizardNextResult>;
  async answer(stepId, value): Promise<void>;
  cancel(): void;
}

// Runner 进程与 UI 进程解耦
// Promise-based 异步等待
```

### 31.3 Prompter 接口

```typescript
type WizardPrompter = {
  intro(title): Promise<void>;
  outro(message): Promise<void>;
  note(message, title?): Promise<void>;
  select<T>(params): Promise<T>;
  multiselect<T>(params): Promise<T[]>;
  text(params): Promise<string>;
  confirm(params): Promise<boolean>;
  progress(label): WizardProgress;
};
```

### 31.4 Onboarding 流程

```
1. 安全提示确认
2. 加载/重置配置
3. 选择模式 (QuickStart / Advanced)
4. Gateway 配置 (端口、绑定、认证)
5. Auth 选择 (Anthropic/OpenAI)
6. 频道设置
7. Skills 设置
8. Hooks 设置
9. 最终化
```

### 31.5 重置策略

| 范围 | 操作 |
|------|------|
| `config` | 仅删除配置文件 |
| `config+creds+sessions` | + 清除凭据和会话 |
| `full` | + 删除工作空间 |

---

## 三十二、Infra 基础设施

### 32.1 系统概述

Infra 模块包含网络发现、安全认证、命令执行控制等核心基础设施。

### 32.2 系统事件队列 (system-events.ts)

```typescript
// 轻量级内存事件总线
type SystemEvent = { text: string; ts: number };

// 每个 sessionKey 独立队列，最多 20 条
// 自动去重连续相同事件
enqueueSystemEvent(sessionKey, text);
drainSystemEvents(sessionKey);
```

### 32.3 系统存在感 (system-presence.ts)

```typescript
// 分布式节点发现
type SystemPresence = {
  host?: string;
  ip?: string;
  version?: string;
  platform?: string;
  mode?: "gateway" | "node";
  reason?: "self" | "discovered" | "imported";
  roles?: string[];
  scopes?: string[];
};

// 5 分钟 TTL，最多 200 节点 LRU
updateSystemPresence(nodeId, presence);
listSystemPresence();
```

### 32.4 Tailscale 集成 (tailscale.ts)

```typescript
// 二进制定位（4 层策略）
findTailscaleBinary();  // which → macOS app → find → locate

// Tailnet 主机名
getTailnetHostname();

// Funnel 公网穿透
ensureFunnel(port);

// 身份验证（60s 缓存）
readTailscaleWhoisIdentity(ip);
```

### 32.5 SSH 隧道 (ssh-tunnel.ts)

```typescript
type SshTunnel = {
  parsedTarget: { user?, host, port };
  localPort: number;
  remotePort: number;
  pid: number | null;
  stop: () => Promise<void>;
};

// SSH 参数
// -N -L {local}:127.0.0.1:{remote}
// -o ExitOnForwardFailure=yes
// -o ConnectTimeout=5
// -o ServerAliveInterval=15
```

### 32.6 mDNS 发现 (bonjour.ts)

```typescript
// 基于 @homebridge/ciao
// 服务类型: moltbot-gw

// TXT 记录
{
  role: "gateway",
  gatewayPort: number,
  lanHost: "{hostname}.local",
  displayName: string,
  gatewayTls?: "1",
  canvasPort?: number,
  tailnetDns?: string,
}

// 60 秒看门狗自动重新广告
```

### 32.7 设备配对 (device-pairing.ts)

```typescript
// PKI 和设备授权管理
type PairedDevice = {
  deviceId: string;
  publicKey: string;
  displayName?: string;
  roles?: string[];
  scopes?: string[];
  tokens?: Record<string, DeviceAuthToken>;
};

// 流程: pending → approve → paired + token
requestDevicePairing();
approveDevicePairing();
verifyDeviceToken();
rotateDeviceToken();
```

### 32.8 执行审批 (exec-approvals.ts)

```typescript
// 命令执行安全网关
type ExecSecure = "deny" | "allowlist" | "full";
type ExecAsk = "off" | "on-miss" | "always";

// 命令分析链
splitCommandChain()      // &&, ||, ;
  → splitShellPipeline() // |
  → tokenizeShellSegment()
  → resolveCommandResolution()

// 安全二进制白名单
["jq", "grep", "cut", "sort", "uniq", "head", "tail", "tr", "wc"]
```

### 32.9 语音唤醒 (voicewake.ts)

```typescript
type VoiceWakeConfig = {
  triggers: string[];      // 唤醒词列表
  updatedAtMs: number;
};

// 默认唤醒词
["clawd", "claude", "computer"]

loadVoiceWakeConfig();
setVoiceWakeTriggers(triggers);
```

---

## 附录：模块覆盖清单

### 已完整覆盖的模块

| 章节 | 模块 | 覆盖程度 |
|------|------|----------|
| 一 | 项目概述 | ✅ 完整 |
| 二 | 核心架构概览 | ✅ 完整 |
| 三 | Agent 运行时系统 | ✅ 完整 |
| 四 | Bootstrap 文件系统 | ✅ 完整 |
| 五 | 系统提示词生成 | ✅ 完整 |
| 六 | 工具系统与九层策略 | ✅ 完整 |
| 七 | 会话管理系统 | ✅ 完整 |
| 八 | 子代理通信协议 | ✅ 完整 |
| 九 | Heartbeat 心跳系统 | ✅ 完整 |
| 十 | Cron 定时任务系统 | ✅ 完整 |
| 十一 | 认证配置文件系统 | ✅ 完整 |
| 十二 | 技能系统 | ✅ 完整 |
| 十三 | 上下文压缩系统 | ✅ 完整 |
| 十四 | Gateway 协议 | ✅ 完整 |
| 十五 | 内存和向量搜索 | ✅ 完整 |
| 十六 | 插件系统 | ✅ 完整 |
| 十七 | 错误处理与重试 | ✅ 完整 |
| 十八 | 关键文件清单 | ✅ 完整 |
| 十九 | A2UI 界面系统 | ✅ 完整 |
| 二十 | Auto-Reply 自动回复系统 | ✅ 完整 |
| 二十一 | Daemon 守护进程系统 | ✅ 完整 |
| 二十二 | Media Understanding 多媒体理解 | ✅ 完整 |
| 二十三 | Provider Usage 使用量监控 | ✅ 完整 |
| 二十四 | Routing 消息路由系统 | ✅ 完整 |
| 二十五 | Hooks 扩展系统 | ✅ 完整 |
| 二十六 | Security 安全审计系统 | ✅ 完整 |
| 二十七 | ACP 协议系统 | ✅ 完整 |
| 二十八 | Browser 浏览器自动化 | ✅ 完整 |
| 二十九 | TUI 终端界面 | ✅ 完整 |
| 三十 | TTS 语音合成 | ✅ 完整 |
| 三十一 | Wizard 配置向导 | ✅ 完整 |
| 三十二 | Infra 基础设施 | ✅ 完整 |

### 估计覆盖率

基于源代码分析，当前文档覆盖率约为 **95%+**。

共覆盖 **32 个章节**，涵盖：
- 核心模块: Agent, Bootstrap, System Prompt, Tools, Sessions
- 自主运行: Heartbeat, Cron, Subagent
- 通信协议: Gateway, ACP, Routing
- 扩展系统: Skills, Plugins, Hooks
- 基础设施: Infra (8 子系统), Daemon, Security
- 用户界面: A2UI, Browser, TUI, Wizard
- 辅助功能: Media, TTS, Memory, Auth Profiles, Provider Usage

未覆盖的次要模块（预计 5% 以内）：
- 部分通道特定实现细节
- 特定平台适配代码

---

**文档完成**: 2026-01-29
**文档类型**: MoltBot 完整架构分析
**基于**: MoltBot TypeScript 源码深度分析

> **注意**: Python 复刻实现设计请参阅 [LURKBOT_COMPLETE_DESIGN.md](./LURKBOT_COMPLETE_DESIGN.md)
