# MoltBot TypeScript 智能体架构设计分析

## 一、概述

本文档分析 MoltBot（TypeScript 原版）的智能体架构设计和实现。MoltBot 是一个多渠道 AI 助手平台，基于 `@mariozechner/pi-agent-core` 和 `@mariozechner/pi-coding-agent` 库构建。

与 Python 版 LurkBot 的自实现架构不同，MoltBot 依赖外部 SDK 提供核心的 Agent Loop 和会话管理功能，同时在其上构建了丰富的工具系统、审批机制和多渠道支持。

---

## 二、核心架构图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    MoltBot Agent Architecture (TypeScript)               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────────┐     ┌──────────────┐     ┌─────────────────┐           │
│  │   ACP API   │     │  WebSocket   │     │   CLI Runner    │           │
│  │  (session)  │     │   Gateway    │     │  (cli-runner)   │           │
│  └──────┬──────┘     └──────┬───────┘     └────────┬────────┘           │
│         │                   │                      │                    │
│         └───────────────────┼──────────────────────┘                    │
│                             ▼                                           │
│                    ┌─────────────────────────┐                          │
│                    │  runEmbeddedPiAgent()   │  ← 入口函数              │
│                    │  (pi-embedded-runner)   │                          │
│                    └───────────┬─────────────┘                          │
│                                │                                        │
│                                ▼                                        │
│                    ┌─────────────────────────┐                          │
│                    │   runEmbeddedAttempt()  │  ← 单次执行尝试          │
│                    │   (run/attempt.ts)      │                          │
│                    └───────────┬─────────────┘                          │
│                                │                                        │
│         ┌──────────────────────┼────────────────────────┐              │
│         ▼                      ▼                        ▼              │
│  ┌─────────────────┐  ┌────────────────────┐  ┌─────────────────────┐ │
│  │   Pi SDK        │  │  MoltbotCodingTools │ │  Session Manager    │ │
│  │ createAgentSess │  │  (pi-tools.ts)     │  │  (pi-coding-agent)  │ │
│  └────────┬────────┘  └────────┬───────────┘  └─────────────────────┘ │
│           │                    │                                       │
│  ┌────────┴────────┐  ┌────────┴───────────────────────┐              │
│  │ @mariozechner/  │  │       Tool Categories          │              │
│  │ pi-coding-agent │  ├────────────────────────────────┤              │
│  │                 │  │ • Exec Tool (bash-tools.exec)  │              │
│  │ • streamSimple  │  │ • Process Tool (bash-process)  │              │
│  │ • SessionManager│  │ • Browser Tool                 │              │
│  │ • codingTools   │  │ • Message Tool                 │              │
│  │ • readTool      │  │ • Sessions Tools (spawn/send)  │              │
│  │ • editTool      │  │ • Web Search/Fetch             │              │
│  │ • writeTool     │  │ • Plugin Tools                 │              │
│  └─────────────────┘  └────────────────────────────────┘              │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 三、核心组件详解

### 3.1 Pi SDK 依赖

MoltBot 的 Agent 核心逻辑依赖于 `@mariozechner/pi-agent-core` 和 `@mariozechner/pi-coding-agent` 两个外部包。

**关键依赖**:
```typescript
// 从 @mariozechner/pi-coding-agent 导入
import {
  codingTools,          // 内置编码工具（read, write, edit, bash）
  createAgentSession,   // 创建 Agent 会话
  SessionManager,       // 会话状态管理
  SettingsManager,      // 配置管理
  createEditTool,       // 创建文件编辑工具
  createReadTool,       // 创建文件读取工具
  createWriteTool,      // 创建文件写入工具
} from "@mariozechner/pi-coding-agent";

// 从 @mariozechner/pi-ai 导入
import { streamSimple } from "@mariozechner/pi-ai";
```

### 3.2 runEmbeddedPiAgent - 主入口函数

**文件**: `src/agents/pi-embedded-runner/run.ts:70-679`

这是 Agent 执行的主入口，负责：
- 模型解析和验证
- 认证配置管理
- 上下文窗口检查
- 错误处理和重试
- 配置文件 Failover 逻辑

```typescript
export async function runEmbeddedPiAgent(
  params: RunEmbeddedPiAgentParams,
): Promise<EmbeddedPiRunResult> {
  // 1. 解析模型配置
  const { model, error, authStorage, modelRegistry } = resolveModel(
    provider, modelId, agentDir, params.config
  );

  // 2. 上下文窗口检查
  const ctxGuard = evaluateContextWindowGuard({ ... });

  // 3. 认证 Profile 轮转（支持多账户 Failover）
  const profileOrder = resolveAuthProfileOrder({ ... });

  // 4. 主循环 - 支持重试和 Failover
  while (true) {
    // 4.1 执行单次尝试
    const attempt = await runEmbeddedAttempt({ ... });

    // 4.2 错误处理 - 上下文溢出自动压缩
    if (isContextOverflowError(errorText)) {
      const compactResult = await compactEmbeddedPiSessionDirect({ ... });
      if (compactResult.compacted) continue;  // 重试
    }

    // 4.3 认证失败 - 切换 Profile
    if (shouldRotate) {
      const rotated = await advanceAuthProfile();
      if (rotated) continue;
    }

    // 4.4 返回结果
    return { payloads, meta };
  }
}
```

### 3.3 runEmbeddedAttempt - 单次执行尝试

**文件**: `src/agents/pi-embedded-runner/run/attempt.ts:133-884`

这是实际执行 Agent 对话的核心函数：

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

  // 4. 创建 Agent 会话（调用 Pi SDK）
  ({ session } = await createAgentSession({
    cwd: resolvedWorkspace,
    agentDir,
    authStorage,
    modelRegistry,
    model,
    thinkingLevel: mapThinkingLevel(params.thinkLevel),
    systemPrompt,
    tools: builtInTools,
    customTools: allCustomTools,
    sessionManager,
    settingsManager,
    skills: [],
    contextFiles: [],
  }));

  // 5. 订阅会话事件（流式响应）
  const subscription = subscribeEmbeddedPiSession({
    session: activeSession,
    onToolResult: params.onToolResult,
    onBlockReply: params.onBlockReply,
    ...
  });

  // 6. 发送 Prompt（触发 Agent Loop）
  await activeSession.prompt(effectivePrompt, { images: imageResult.images });

  // 7. 返回结果
  return {
    aborted,
    timedOut,
    promptError,
    sessionIdUsed,
    assistantTexts,
    toolMetas,
    lastAssistant,
    ...
  };
}
```

---

## 四、Tool Use Loop（工具使用循环）

### 4.1 架构说明

与 Python 版 LurkBot 自实现的 Tool Use Loop 不同，MoltBot 的 Tool Use Loop 由 `@mariozechner/pi-coding-agent` SDK 内部实现。MoltBot 通过以下方式与 SDK 交互：

1. **工具注册**: 通过 `createAgentSession` 传入工具列表
2. **事件订阅**: 通过 `session.subscribe()` 监听工具调用和响应事件
3. **流式响应**: 通过 `subscribeEmbeddedPiSession` 处理流式输出

### 4.2 事件流程图

```
                    ┌──────────────────┐
                    │   用户消息输入    │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────────┐
                    │ session.prompt(msg)  │
                    │   发送消息给 SDK     │
                    └────────┬─────────────┘
                             │
              ┌──────────────┴──────────────┐
              │     Pi SDK Agent Loop       │
              │    （内部实现，不可见）       │
              │                             │
              │  ┌───────────────────────┐  │
              │  │  1. 调用 LLM API      │  │
              │  │  2. 解析 Tool Calls   │  │
              │  │  3. 执行工具          │  │
              │  │  4. 工具结果反馈      │  │
              │  │  5. 循环直到完成      │  │
              │  └───────────────────────┘  │
              │                             │
              └──────────────┬──────────────┘
                             │
                             ▼
              ┌──────────────────────────────┐
              │ session.subscribe() 事件回调  │
              │                              │
              │  • message_start            │
              │  • text_delta               │
              │  • text_end                 │
              │  • tool_start               │
              │  • tool_delta               │
              │  • tool_end                 │
              │  • compaction_retry         │
              │  • error                    │
              └──────────────────────────────┘
```

### 4.3 subscribeEmbeddedPiSession 实现

**文件**: `src/agents/pi-embedded-subscribe.ts:30-499`

此函数负责订阅 Pi SDK 的会话事件并处理流式响应：

```typescript
export function subscribeEmbeddedPiSession(params: SubscribeEmbeddedPiSessionParams) {
  // 状态管理
  const state: EmbeddedPiSubscribeState = {
    assistantTexts: [],      // 助手文本累积
    toolMetas: [],           // 工具元数据
    toolMetaById: new Map(), // 按 ID 索引
    deltaBuffer: "",         // 流式 Delta 缓冲
    blockBuffer: "",         // 块缓冲
    blockState: {            // 块状态追踪
      thinking: false,       // 是否在 <think> 块内
      final: false,          // 是否在 <final> 块内
    },
    messagingToolSentTexts: [],  // 消息工具发送记录
    ...
  };

  // 事件处理器
  const unsubscribe = params.session.subscribe(
    createEmbeddedPiSessionEventHandler(ctx)
  );

  return {
    assistantTexts,
    toolMetas,
    unsubscribe,
    isCompacting: () => state.compactionInFlight,
    didSendViaMessagingTool: () => messagingToolSentTexts.length > 0,
    waitForCompactionRetry: () => state.compactionRetryPromise,
  };
}
```

---

## 五、工具系统架构

### 5.1 工具创建流程

**文件**: `src/agents/pi-tools.ts:107-420`

MoltBot 通过 `createMoltbotCodingTools()` 函数组装所有可用工具：

```typescript
export function createMoltbotCodingTools(options?: {
  exec?: ExecToolDefaults;
  sandbox?: SandboxContext;
  messageProvider?: string;
  config?: MoltbotConfig;
  ...
}): AnyAgentTool[] {
  // 1. 基础编码工具（来自 pi-coding-agent）
  const base = codingTools.flatMap((tool) => {
    if (tool.name === "read") {
      return sandbox ? [createSandboxedReadTool(sandboxRoot)]
                     : [createMoltbotReadTool(freshReadTool)];
    }
    if (tool.name === "write") {
      return sandbox ? [] : [createWriteTool(workspaceRoot)];
    }
    if (tool.name === "edit") {
      return sandbox ? [] : [createEditTool(workspaceRoot)];
    }
    return [tool];
  });

  // 2. Exec 工具（命令执行）
  const execTool = createExecTool({ ... });
  const processTool = createProcessTool({ ... });

  // 3. Moltbot 特有工具
  const moltbotTools = createMoltbotTools({
    sandboxBrowserBridgeUrl: sandbox?.browser?.bridgeUrl,
    agentSessionKey: options?.sessionKey,
    ...
  });

  // 4. 工具策略过滤
  const toolsFiltered = filterToolsByPolicy(tools, profilePolicy);
  const sandboxed = filterToolsByPolicy(toolsFiltered, sandboxPolicy);

  // 5. Schema 标准化
  const normalized = sandboxed.map(normalizeToolParameters);

  return normalized;
}
```

### 5.2 工具分类

```
┌────────────────────────────────────────────────────────────────┐
│                    MoltBot 工具体系                            │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │           核心编码工具 (来自 pi-coding-agent)            │  │
│  ├─────────────────────────────────────────────────────────┤  │
│  │ • read      - 文件读取                                  │  │
│  │ • write     - 文件写入                                  │  │
│  │ • edit      - 文件编辑                                  │  │
│  │ • glob      - 文件搜索                                  │  │
│  │ • grep      - 内容搜索                                  │  │
│  └─────────────────────────────────────────────────────────┘  │
│                                                                │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │           命令执行工具 (bash-tools.*)                    │  │
│  ├─────────────────────────────────────────────────────────┤  │
│  │ • exec      - 命令执行（支持 PTY、沙箱、审批）           │  │
│  │ • process   - 后台进程管理                               │  │
│  │ • apply_patch - OpenAI 补丁格式支持                      │  │
│  └─────────────────────────────────────────────────────────┘  │
│                                                                │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │           Moltbot 特有工具 (moltbot-tools.ts)           │  │
│  ├─────────────────────────────────────────────────────────┤  │
│  │ • browser   - 浏览器控制（支持沙箱隔离）                 │  │
│  │ • canvas    - 画布工具                                   │  │
│  │ • message   - 多渠道消息发送                             │  │
│  │ • web_search - 网页搜索                                  │  │
│  │ • web_fetch  - 网页获取                                  │  │
│  │ • image     - 图像处理                                   │  │
│  │ • tts       - 文本转语音                                 │  │
│  │ • cron      - 定时任务                                   │  │
│  │ • nodes     - 节点管理                                   │  │
│  │ • gateway   - 网关交互                                   │  │
│  └─────────────────────────────────────────────────────────┘  │
│                                                                │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │           会话管理工具 (tools/sessions-*.ts)            │  │
│  ├─────────────────────────────────────────────────────────┤  │
│  │ • sessions_list   - 列出会话                             │  │
│  │ • sessions_history - 查看历史                            │  │
│  │ • sessions_send   - 跨会话发送消息                       │  │
│  │ • sessions_spawn  - 创建子 Agent                         │  │
│  │ • session_status  - 会话状态                             │  │
│  │ • agents_list     - Agent 列表                           │  │
│  └─────────────────────────────────────────────────────────┘  │
│                                                                │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │           插件工具 (plugins/tools.ts)                    │  │
│  ├─────────────────────────────────────────────────────────┤  │
│  │ • 动态加载的第三方插件工具                               │  │
│  │ • 支持工具策略过滤和沙箱隔离                             │  │
│  └─────────────────────────────────────────────────────────┘  │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

### 5.3 Exec 工具详解

**文件**: `src/agents/bash-tools.exec.ts`

Exec 工具是 MoltBot 中最复杂的工具，支持多种执行模式和安全机制：

```typescript
type ExecHost = "sandbox" | "gateway" | "node";
type ExecSecurity = "deny" | "allowlist" | "full";
type ExecAsk = "off" | "on-miss" | "always";

// 执行模式
// sandbox  - Docker 容器内执行（最安全）
// gateway  - 远程 Gateway 执行
// node     - 本地 Node.js 执行（直接）

// 安全模式
// deny      - 拒绝所有命令
// allowlist - 仅允许白名单命令
// full      - 允许所有命令

// 审批模式
// off       - 无需审批
// on-miss   - 白名单外需审批
// always    - 总是需要审批
```

**关键特性**:
- PTY 支持（伪终端，支持交互式命令）
- 后台进程管理
- 超时控制
- Docker 沙箱隔离
- Gateway 远程执行
- 审批工作流集成

---

## 六、会话管理

### 6.1 ACP Session Store

**文件**: `src/acp/session.ts:1-86`

ACP (Agent Client Protocol) 会话存储提供内存中的会话管理：

```typescript
export type AcpSession = {
  sessionId: SessionId;
  sessionKey: string;
  cwd: string;
  createdAt: number;
  abortController: AbortController | null;
  activeRunId: string | null;
};

export function createInMemorySessionStore(): AcpSessionStore {
  const sessions = new Map<string, AcpSession>();
  const runIdToSessionId = new Map<string, string>();

  return {
    createSession: (params) => { ... },
    getSession: (sessionId) => sessions.get(sessionId),
    getSessionByRunId: (runId) => { ... },
    setActiveRun: (sessionId, runId, abortController) => { ... },
    clearActiveRun: (sessionId) => { ... },
    cancelActiveRun: (sessionId) => { ... },
  };
}
```

### 6.2 Pi SDK SessionManager

MoltBot 使用 Pi SDK 的 `SessionManager` 进行会话状态持久化：

```typescript
// 打开会话文件
const sessionManager = SessionManager.open(params.sessionFile);

// 准备会话
await prepareSessionManagerForRun({
  sessionManager,
  sessionFile: params.sessionFile,
  hadSessionFile,
  sessionId: params.sessionId,
  cwd: effectiveWorkspace,
});

// 获取会话上下文
const sessionContext = sessionManager.buildSessionContext();

// 分支操作（处理历史状态）
sessionManager.branch(leafEntry.parentId);
sessionManager.resetLeaf();
```

---

## 七、工具策略系统

### 7.1 策略层级

MoltBot 的工具策略系统支持多层级配置，从高到低优先级：

```
1. Profile Policy          - 用户配置文件策略
2. Provider Profile Policy - 按提供商的配置文件策略
3. Global Policy           - 全局工具策略
4. Global Provider Policy  - 按提供商的全局策略
5. Agent Policy            - Agent 级别策略
6. Agent Provider Policy   - 按提供商的 Agent 策略
7. Group Policy            - 群组级别策略
8. Sandbox Policy          - 沙箱策略
9. Subagent Policy         - 子 Agent 策略
```

### 7.2 策略过滤实现

**文件**: `src/agents/pi-tools.policy.ts`

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

export function isToolAllowedByPolicies(
  toolName: string,
  policies: (ToolPolicy | undefined)[]
): boolean {
  for (const policy of policies) {
    if (!policy?.allow) continue;
    const normalized = normalizeToolName(toolName);
    if (!policy.allow.some(
      (entry) => normalizeToolName(entry) === normalized
    )) {
      return false;
    }
  }
  return true;
}
```

---

## 八、多模型支持

### 8.1 认证 Profile 系统

MoltBot 支持多个认证 Profile，实现自动 Failover：

**文件**: `src/agents/auth-profiles.ts`

```typescript
// Profile 优先级顺序
const profileOrder = resolveAuthProfileOrder({
  cfg: params.config,
  store: authStore,
  provider,
  preferredProfile: preferredProfileId,
});

// Profile 轮转（遇到错误时切换）
const advanceAuthProfile = async (): Promise<boolean> => {
  let nextIndex = profileIndex + 1;
  while (nextIndex < profileCandidates.length) {
    const candidate = profileCandidates[nextIndex];
    if (isProfileInCooldown(authStore, candidate)) {
      nextIndex += 1;
      continue;
    }
    await applyApiKeyInfo(candidate);
    return true;
  }
  return false;
};
```

### 8.2 模型配置

MoltBot 通过 `models.json` 和 Pi SDK 的 Model Registry 管理模型配置：

```typescript
const { model, error, authStorage, modelRegistry } = resolveModel(
  provider,
  modelId,
  agentDir,
  params.config,
);

// 支持的提供商
// - anthropic
// - openai
// - google
// - github-copilot
// - bedrock (AWS)
// - ollama (本地)
```

---

## 九、沙箱隔离系统

### 9.1 沙箱架构

```
┌─────────────────────────────────────────────────────────┐
│                    Sandbox System                        │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌─────────────────────────────────────────────────┐    │
│  │              SandboxContext                      │    │
│  ├─────────────────────────────────────────────────┤    │
│  │ enabled: boolean                                │    │
│  │ containerName: string                           │    │
│  │ workspaceDir: string                            │    │
│  │ containerWorkdir: string                        │    │
│  │ workspaceAccess: "none" | "ro" | "rw"          │    │
│  │ browser: { bridgeUrl, allowHostControl }       │    │
│  │ docker: { env, mounts }                        │    │
│  │ tools: ToolPolicy                               │    │
│  └─────────────────────────────────────────────────┘    │
│                                                          │
│  ┌─────────────────────────────────────────────────┐    │
│  │           Sandboxed Tools                        │    │
│  ├─────────────────────────────────────────────────┤    │
│  │ • createSandboxedReadTool(sandboxRoot)         │    │
│  │ • createSandboxedEditTool(sandboxRoot)         │    │
│  │ • createSandboxedWriteTool(sandboxRoot)        │    │
│  │ • Docker Exec (containerized commands)         │    │
│  └─────────────────────────────────────────────────┘    │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### 9.2 沙箱工具实现

```typescript
// 沙箱化的 Read 工具
function createSandboxedReadTool(sandboxRoot: string) {
  return {
    name: "read",
    execute: async (args) => {
      const safePath = resolveSandboxPath(args.file_path, sandboxRoot);
      return fs.readFile(safePath, "utf-8");
    }
  };
}

// Docker 命令执行
function buildDockerExecArgs(sandbox: SandboxContext, command: string) {
  return [
    "docker", "exec",
    "-w", sandbox.containerWorkdir,
    ...sandbox.docker.env.map(e => ["-e", e]).flat(),
    sandbox.containerName,
    "sh", "-c", command
  ];
}
```

---

## 十、流式响应处理

### 10.1 事件类型

MoltBot 处理 Pi SDK 发出的多种事件：

```typescript
type SessionEvent =
  | { type: "message_start"; ... }      // 消息开始
  | { type: "text_delta"; delta: string } // 文本增量
  | { type: "text_end"; text: string }   // 文本结束
  | { type: "tool_start"; toolName: string; toolId: string }
  | { type: "tool_delta"; delta: string }
  | { type: "tool_end"; toolName: string; result: any }
  | { type: "compaction_retry" }         // 压缩重试
  | { type: "error"; error: Error };
```

### 10.2 流式文本处理

**关键特性**:
- `<think>`/`<thinking>` 块过滤
- `<final>` 块提取
- 代码块保护
- 块级分块输出
- 消息工具去重

```typescript
const stripBlockTags = (text: string, state: BlockState): string => {
  // 1. 处理 <think> 块（有状态，剥离内容）
  // 2. 处理 <final> 块（有状态，仅保留内部内容）
  // 3. 代码块保护（不处理代码块内的标签）
  ...
};
```

---

## 十一、与 Python LurkBot 的对比

| 特性 | MoltBot (TypeScript) | LurkBot (Python) |
|------|---------------------|------------------|
| Agent 核心 | Pi SDK (外部) | 自实现 |
| Tool Use Loop | SDK 内部实现 | 自实现（最多 10 次迭代） |
| 会话管理 | Pi SDK SessionManager | JSONL 存储 + AgentRuntime |
| 工具系统 | Pi SDK + 自定义扩展 | 完全自实现 |
| 多模型支持 | 通过 Pi SDK | 通过 ModelAdapter 接口 |
| 审批系统 | Gateway 集成 | ApprovalManager |
| 沙箱隔离 | Docker + 路径限制 | SessionType 策略 |
| 流式响应 | 事件订阅模式 | AsyncIterator |

---

## 十二、关键文件清单

| 组件 | 文件路径 | 说明 |
|------|----------|------|
| 主入口 | `pi-embedded-runner/run.ts` | Agent 执行入口 |
| 执行尝试 | `pi-embedded-runner/run/attempt.ts` | 单次执行逻辑 |
| 事件订阅 | `pi-embedded-subscribe.ts` | 流式响应处理 |
| 工具创建 | `pi-tools.ts` | 工具组装 |
| Exec 工具 | `bash-tools.exec.ts` | 命令执行 |
| Moltbot 工具 | `moltbot-tools.ts` | 特有工具集合 |
| ACP 会话 | `acp/session.ts` | 会话存储 |
| 认证管理 | `auth-profiles.ts` | 多账户管理 |
| 工具策略 | `pi-tools.policy.ts` | 策略过滤 |
| CLI 运行器 | `cli-runner.ts` | CLI 模式运行 |

---

## 十三、设计亮点

### 13.1 SDK 集成模式
- 核心 Agent Loop 委托给 Pi SDK
- 通过事件订阅实现流式处理
- 保持与 SDK 的松耦合

### 13.2 多层工具策略
- 支持 9 层策略优先级
- 灵活的工具过滤机制
- 插件工具动态加载

### 13.3 认证 Profile 轮转
- 自动 Failover 支持
- Cooldown 机制防止频繁重试
- 多账户负载分散

### 13.4 沙箱隔离
- Docker 容器化执行
- 路径限制保护
- 工具级别策略控制

---

**分析完成**: 2026-01-29
**文档类型**: 只读分析报告（不涉及代码修改）
