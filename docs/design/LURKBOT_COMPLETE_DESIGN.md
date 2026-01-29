# LurkBot 完整复刻设计方案 v3.0

> **文档版本**: 3.0
> **更新日期**: 2026-01-29
> **基于**: MOLTBOT_COMPLETE_ARCHITECTURE.md v3.0 (32 章节) 深度分析
> **核心原则**: 完全复刻 MoltBot，不遗漏任何功能
> **模块总数**: 32 个模块（对齐 MoltBot 架构）
> **实施阶段**: 28 个阶段

---

## 目录

- [一、设计方案总览](#一设计方案总览)
- [二、框架选型最终决定](#二框架选型最终决定)
- [三、核心模块设计](#三核心模块设计)
- [四、A2UI 界面系统设计](#四a2ui-界面系统设计)
- [五、Auto-Reply 自动回复系统设计](#五auto-reply-自动回复系统设计)
- [六、Routing 消息路由系统设计](#六routing-消息路由系统设计)
- [七、Daemon 守护进程系统设计](#七daemon-守护进程系统设计)
- [八、Hooks 扩展系统设计](#八hooks-扩展系统设计)
- [九、Security 安全审计系统设计](#九security-安全审计系统设计)
- [十、Infra 基础设施设计](#十infra-基础设施设计)
- [十一、Media Understanding 设计](#十一media-understanding-设计)
- [十二、Provider Usage 设计](#十二provider-usage-设计)
- [十三、ACP 协议系统设计](#十三acp-协议系统设计)
- [十四、Browser 浏览器自动化设计](#十四browser-浏览器自动化设计)
- [十五、TUI 终端界面设计](#十五tui-终端界面设计)
- [十六、TTS 语音合成设计](#十六tts-语音合成设计)
- [十七、Wizard 配置向导设计](#十七wizard-配置向导设计)
- [十八、功能完整性检查清单](#十八功能完整性检查清单)
- [十九、实施计划（28 阶段）](#十九实施计划28-阶段)
- [二十、验证策略](#二十验证策略)
- [附录：完整模块目录结构](#附录完整模块目录结构)

---

## 一、设计方案总览

### 1.1 复刻目标

**必须 100% 复刻的功能**:

| 类别 | MoltBot 功能 | 复刻优先级 |
|------|-------------|-----------|
| **Agent 运行时** | Pi SDK Agent Loop | P0 |
| **Bootstrap** | 8 个 Bootstrap 文件系统 | P0 |
| **系统提示词** | 23 节结构 + PromptMode | P0 |
| **工具系统** | 22 原生工具 + 九层策略 | P0 |
| **会话管理** | 5 种会话类型 + Key 格式 | P0 |
| **子代理** | Spawn/Send/Announce Flow | P0 |
| **Heartbeat** | 心跳系统 + 事件 | P0 |
| **Cron** | 定时任务 + 两种 Payload | P0 |
| **Auth Profiles** | 凭据轮换 + 冷却算法 | P1 |
| **Context Compaction** | 自适应压缩 + 分阶段摘要 | P1 |
| **Gateway 协议** | WebSocket + 完整帧结构 | P1 |
| **技能系统** | YAML Frontmatter + 加载优先级 | P1 |
| **插件系统** | 100+ 运行时 API 注入 | P2 |
| **内存系统** | 向量搜索 + sqlite-vec | P2 |
| **错误处理** | 渠道特定重试策略 | P2 |
| **A2UI 界面系统** | Canvas + 声明式 UI | P2 |

### 1.2 架构映射（最终版）

```
MoltBot (TypeScript)              LurkBot (Python)
─────────────────────────────────────────────────────────
Pi SDK createAgentSession     →   PydanticAI Agent
Pi SDK session.prompt()       →   agent.run() / agent.run_stream()
Pi SDK subscribe()            →   agent.run_stream_events()
Pi SDK tools                  →   @agent.tool 装饰器
Pi SDK interrupt/approval     →   DeferredToolRequests + requires_approval
Pi SDK SessionManager         →   lurkbot.sessions.SessionStore (JSONL)
Bootstrap files               →   lurkbot.agents.bootstrap
System prompt (592 lines)     →   lurkbot.agents.system_prompt
Tool policy (9 layers)        →   lurkbot.tools.policy
Auth profiles                 →   lurkbot.auth.profiles
Subagent announce             →   lurkbot.agents.subagent
Heartbeat runner              →   lurkbot.autonomous.heartbeat
Cron service                  →   lurkbot.autonomous.cron
Compaction                    →   lurkbot.agents.compaction
Gateway protocol              →   lurkbot.gateway.protocol
Skills                        →   lurkbot.skills
Plugins                       →   lurkbot.plugins
Memory (sqlite-vec)           →   lurkbot.memory
Retry policy                  →   lurkbot.infra.retry
Canvas Host (A2UI)            →   lurkbot.canvas_host
```

---

## 二、框架选型最终决定

### 2.1 最终选型: PydanticAI

**选择 PydanticAI 而非 LangGraph 的理由**:

| 考量 | PydanticAI | LangGraph | 结论 |
|------|-----------|-----------|------|
| **类型安全** | ✅ Pydantic 原生 | ⚠️ 一般 | PydanticAI |
| **Human-in-the-Loop** | ✅ DeferredToolRequests | ✅ interrupt() | 持平 |
| **学习曲线** | 平缓 | 陡峭（图形概念） | PydanticAI |
| **代码简洁** | ✅ 装饰器模式 | ⚠️ 图形定义繁琐 | PydanticAI |
| **与 LurkBot 兼容** | ✅ 高度兼容 | ⚠️ 需大量重构 | PydanticAI |
| **流式 API** | ✅ handle_ag_ui_request | ⚠️ 需手动实现 | PydanticAI |

### 2.2 PydanticAI v1.0.5 关键 API

```python
from pydantic_ai import (
    Agent,
    RunContext,
    ApprovalRequired,
    DeferredToolRequests,
    DeferredToolResults,
    CallDeferred,
)
from pydantic_ai.ag_ui import handle_ag_ui_request
from pydantic_ai.messages import (
    AgentStreamEvent,
    FinalResultEvent,
    FunctionToolCallEvent,
    FunctionToolResultEvent,
    PartDeltaEvent,
    PartStartEvent,
    TextPartDelta,
)

# Agent 创建
agent = Agent[AgentDeps, str | DeferredToolRequests](
    'anthropic:claude-sonnet-4-20250514',
    deps_type=AgentDeps,
    output_type=[str, DeferredToolRequests],
    system_prompt=system_prompt,
)

# 工具定义（需要审批）
@agent.tool(requires_approval=True)
async def dangerous_tool(ctx: RunContext[AgentDeps], command: str) -> str:
    return await execute(command)

# 条件审批
@agent.tool
async def conditional_tool(ctx: RunContext[AgentDeps], path: str) -> str:
    if path in PROTECTED_PATHS and not ctx.tool_call_approved:
        raise ApprovalRequired
    return f"Operated on {path}"

# 流式运行
async with agent.run_stream(prompt, deps=deps) as run:
    async for text in run.stream_text():
        yield text

# 事件流
async for event in agent.run_stream_events(prompt, deps=deps):
    if isinstance(event, FunctionToolCallEvent):
        print(f"Tool: {event.part.tool_name}")

# FastAPI 集成
@app.post('/chat')
async def chat(request: Request) -> Response:
    return await handle_ag_ui_request(agent, request)
```

---

## 三、核心模块设计

### 3.1 Agent 运行时 (`lurkbot.agents.runtime`)

```python
# 文件: src/lurkbot/agents/runtime.py

from dataclasses import dataclass, field
from pydantic_ai import Agent, RunContext, DeferredToolRequests
from pydantic import BaseModel

@dataclass
class AgentContext:
    """Agent 运行上下文（对标 MoltBot EmbeddedRunAttemptParams）"""
    session_id: str
    session_key: str
    session_type: str  # main/group/dm/topic/subagent
    workspace: str
    channel: str
    user_id: str | None = None
    model: str = "anthropic:claude-sonnet-4-20250514"
    thinking_level: str = "medium"  # off/low/medium/high
    prompt_mode: str = "full"  # full/minimal/none
    sandbox_enabled: bool = False
    is_subagent: bool = False
    tools_enabled: list[str] = field(default_factory=list)
    tools_disabled: list[str] = field(default_factory=list)

class AgentDependencies(BaseModel):
    """Agent 依赖注入"""
    context: AgentContext
    tool_registry: "ToolRegistry"
    bootstrap_files: "BootstrapFiles"
    message_history: list[dict] = []

    class Config:
        arbitrary_types_allowed = True

async def run_embedded_agent(
    context: AgentContext,
    prompt: str,
    images: list[str] | None = None,
) -> "AgentRunResult":
    """
    对标 MoltBot runEmbeddedPiAgent()

    流程:
    1. 加载 Bootstrap 文件
    2. 生成系统提示词
    3. 应用工具策略
    4. 创建 Agent
    5. 运行 Agent Loop
    6. 处理审批（如有）
    7. 处理上下文溢出（自动压缩）
    8. Auth Profile 轮换（如失败）
    """
    # 1. 加载 Bootstrap
    bootstrap = await load_bootstrap_files(
        workspace_dir=context.workspace,
        session_type=context.session_type,
    )

    # 2. 生成系统提示词
    system_prompt = build_system_prompt(
        context=context,
        bootstrap_files=bootstrap,
        prompt_mode=context.prompt_mode,
    )

    # 3. 应用工具策略
    tools = filter_tools_by_policy(
        tools=get_all_tools(),
        context=ToolPolicyContext(
            profile=context.tool_profile,
            provider=context.model.split(":")[0],
            model=context.model,
            session_type=context.session_type,
            channel=context.channel,
            sandbox_mode=context.sandbox_enabled,
            is_subagent=context.is_subagent,
        )
    )

    # 4. 创建 Agent
    agent = create_agent(
        model=context.model,
        system_prompt=system_prompt,
        tools=tools,
        thinking_level=context.thinking_level,
    )

    # 5. 运行 Agent Loop（带重试和 Failover）
    deps = AgentDependencies(
        context=context,
        tool_registry=tool_registry,
        bootstrap_files=bootstrap,
    )

    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            result = await agent.run(prompt, deps=deps)

            # 处理审批
            if isinstance(result.output, DeferredToolRequests):
                return AgentRunResult(
                    status="approval_pending",
                    deferred_requests=result.output,
                    messages=result.all_messages(),
                )

            return AgentRunResult(
                status="completed",
                output=result.output,
                messages=result.all_messages(),
            )

        except ContextOverflowError:
            # 自动压缩
            compacted = await compact_messages(
                messages=deps.message_history,
                context_window=get_context_window(context.model),
            )
            deps.message_history = compacted
            continue

        except AuthError as e:
            # Auth Profile 轮换
            rotated = await rotate_auth_profile(context.model)
            if rotated and attempt < max_attempts - 1:
                continue
            raise

    raise AgentError("Max attempts exceeded")
```

### 3.2 Bootstrap 文件系统 (`lurkbot.agents.bootstrap`)

```python
# 文件: src/lurkbot/agents/bootstrap.py

from pathlib import Path
from dataclasses import dataclass
from typing import Literal

# 对标 MoltBot BOOTSTRAP_FILES
BOOTSTRAP_FILES = [
    "SOUL.md",
    "IDENTITY.md",
    "USER.md",
    "AGENTS.md",
    "TOOLS.md",
    "HEARTBEAT.md",
    "MEMORY.md",
    "BOOTSTRAP.md",
]

# 对标 MoltBot SUBAGENT_BOOTSTRAP_ALLOWLIST
SUBAGENT_BOOTSTRAP_ALLOWLIST = {"AGENTS.md", "TOOLS.md"}

# 对标 MoltBot BOOTSTRAP_MAX_CHARS
BOOTSTRAP_MAX_CHARS = 20_000

@dataclass
class BootstrapFile:
    name: str
    content: str
    path: str

@dataclass
class BootstrapFiles:
    soul: BootstrapFile | None = None
    identity: BootstrapFile | None = None
    user: BootstrapFile | None = None
    agents: BootstrapFile | None = None
    tools: BootstrapFile | None = None
    heartbeat: BootstrapFile | None = None
    memory: BootstrapFile | None = None
    bootstrap: BootstrapFile | None = None

    def get_all(self) -> list[BootstrapFile]:
        """获取所有非空文件"""
        return [f for f in [
            self.soul, self.identity, self.user, self.agents,
            self.tools, self.heartbeat, self.memory, self.bootstrap
        ] if f is not None]

    def get_for_prompt(self) -> list[BootstrapFile]:
        """获取用于系统提示词的文件（按 MoltBot 顺序）"""
        return [f for f in [
            self.soul, self.identity, self.user, self.agents, self.tools
        ] if f is not None]

async def load_bootstrap_files(
    workspace_dir: str,
    session_type: Literal["main", "group", "dm", "topic", "subagent"],
) -> BootstrapFiles:
    """
    加载 Bootstrap 文件

    对标 MoltBot loadBootstrapFiles() 和 filterBootstrapFilesForSession()

    规则:
    - 子代理只加载 AGENTS.md 和 TOOLS.md
    - 群组会话不加载 MEMORY.md
    - 所有文件截断到 BOOTSTRAP_MAX_CHARS
    """
    workspace = Path(workspace_dir)
    files = BootstrapFiles()

    for filename in BOOTSTRAP_FILES:
        # 子代理过滤
        if session_type == "subagent" and filename not in SUBAGENT_BOOTSTRAP_ALLOWLIST:
            continue

        # 群组会话不加载 MEMORY.md
        if session_type == "group" and filename == "MEMORY.md":
            continue

        filepath = workspace / filename
        if filepath.exists():
            content = await _read_and_trim(filepath, BOOTSTRAP_MAX_CHARS)
            attr_name = filename.replace(".md", "").lower()
            setattr(files, attr_name, BootstrapFile(
                name=filename,
                content=content,
                path=str(filepath),
            ))

    return files

async def _read_and_trim(path: Path, max_chars: int) -> str:
    """
    读取并截断文件（保留头70%+尾20%）

    对标 MoltBot readAndTrim()
    """
    content = path.read_text(encoding="utf-8")
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

### 3.3 系统提示词生成 (`lurkbot.agents.system_prompt`)

```python
# 文件: src/lurkbot/agents/system_prompt.py

from typing import Literal
from datetime import datetime
import platform

# 对标 MoltBot PromptMode
PromptMode = Literal["full", "minimal", "none"]

def build_system_prompt(
    context: "AgentContext",
    bootstrap_files: "BootstrapFiles",
    prompt_mode: PromptMode = "full",
    tools: list["Tool"] | None = None,
    skills: list["Skill"] | None = None,
    heartbeat_prompt: str | None = None,
    sandbox_info: dict | None = None,
    tts_hint: str | None = None,
    reaction_guidance: str | None = None,
    model_alias_lines: list[str] | None = None,
    reasoning_tag_hint: str | None = None,
) -> str:
    """
    构建系统提示词

    对标 MoltBot buildEmbeddedSystemPrompt() (592 lines)

    完整 23 节结构:
    1.  身份行
    2.  ## Tooling
    3.  ## Tool Call Style
    4.  ## Moltbot CLI Quick Reference
    5.  ## Skills (mandatory)
    6.  ## Memory Recall
    7.  ## User Identity
    8.  ## Current Date & Time
    9.  ## Workspace
    10. ## Documentation
    11. ## Sandbox
    12. ## Workspace Files (injected)
    13. ## Reply Tags
    14. ## Messaging
    15. ## Voice (TTS)
    16. ## Moltbot Self-Update
    17. ## Model Aliases
    18. # Project Context
    19. ## Silent Replies
    20. ## Heartbeats
    21. ## Runtime
    22. ## Reactions
    23. ## Reasoning Format
    """
    if prompt_mode == "none":
        return "You are a personal assistant running inside LurkBot."

    lines: list[str] = []

    # 1. 身份行
    lines.append("You are a personal assistant running inside LurkBot.")
    lines.append("")

    # 2. ## Tooling
    if tools:
        lines.append("## Tooling")
        lines.append("")
        for tool in tools:
            lines.append(f"- **{tool.name}**: {tool.description}")
        lines.append("")

    # 3. ## Tool Call Style
    lines.append("## Tool Call Style")
    lines.append("When using tools, briefly explain what you're about to do.")
    lines.append("")

    # 4. ## LurkBot CLI Quick Reference
    lines.append("## LurkBot CLI Quick Reference")
    lines.append("- `lurkbot chat start` - Start interactive chat")
    lines.append("- `lurkbot sessions list` - List sessions")
    lines.append("- `lurkbot cron list` - List scheduled tasks")
    lines.append("")

    # 5. ## Skills (mandatory) - 非 minimal 模式
    if prompt_mode != "minimal" and skills:
        lines.append("## Skills (mandatory)")
        lines.append("Before replying: scan <available_skills> <description> entries.")
        lines.append("- If exactly one skill clearly applies: read its SKILL.md at <location> with `read`, then follow it.")
        lines.append("- If multiple could apply: choose the most specific one, then read/follow it.")
        lines.append("- If none clearly apply: do not read any SKILL.md.")
        lines.append("")
        lines.append("<available_skills>")
        for skill in skills:
            lines.append(f"- {skill.name}: {skill.description}")
        lines.append("</available_skills>")
        lines.append("")

    # 6. ## Memory Recall - 非 minimal 且有内存工具
    if prompt_mode != "minimal" and _has_memory_tools(tools):
        lines.append("## Memory Recall")
        lines.append("Before answering questions about past events, search your memory first using `memory_search`.")
        lines.append("")

    # 7. ## User Identity - 非 minimal 且有所有者信息
    if prompt_mode != "minimal" and context.user_id:
        lines.append("## User Identity")
        lines.append(f"Owner: {context.user_id}")
        lines.append("")

    # 8. ## Current Date & Time
    lines.append("## Current Date & Time")
    now = datetime.now()
    lines.append(f"Current time: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"Timezone: {context.timezone or 'UTC'}")
    lines.append("")

    # 9. ## Workspace
    lines.append("## Workspace")
    lines.append(f"Working directory: {context.workspace}")
    lines.append("")

    # 10. ## Documentation - 非 minimal
    if prompt_mode != "minimal" and context.docs_path:
        lines.append("## Documentation")
        lines.append(f"LurkBot documentation: {context.docs_path}")
        lines.append("")

    # 11. ## Sandbox
    if sandbox_info and sandbox_info.get("enabled"):
        lines.append("## Sandbox")
        lines.append("You are running in a restricted sandbox environment.")
        lines.append(f"Container: {sandbox_info.get('container', 'unknown')}")
        lines.append(f"Restrictions: {sandbox_info.get('restrictions', 'Limited file access')}")
        lines.append("")

    # 12. ## Workspace Files (injected)
    lines.append("## Workspace Files")
    lines.append("The following files are injected from your workspace:")
    for f in bootstrap_files.get_for_prompt():
        lines.append(f"- {f.name}")
    lines.append("")

    # 13. ## Reply Tags - 非 minimal
    if prompt_mode != "minimal":
        lines.append("## Reply Tags")
        lines.append("Use [[reply_to:message_id]] to quote a specific message.")
        lines.append("")

    # 14. ## Messaging - 非 minimal
    if prompt_mode != "minimal":
        lines.append("## Messaging")
        lines.append("Use the `message` tool for sending messages to channels.")
        lines.append("Available actions: send, delete, react, pin, poll, thread, event, media")
        lines.append("")

    # 15. ## Voice (TTS) - 非 minimal 且有 TTS 提示
    if prompt_mode != "minimal" and tts_hint:
        lines.append("## Voice (TTS)")
        lines.append(tts_hint)
        lines.append("")

    # 16. ## LurkBot Self-Update - 非 minimal 且有 Gateway
    if prompt_mode != "minimal" and context.has_gateway:
        lines.append("## LurkBot Self-Update")
        lines.append("Do not attempt to update LurkBot without explicit user permission.")
        lines.append("")

    # 17. ## Model Aliases - 非 minimal 且有别名
    if prompt_mode != "minimal" and model_alias_lines:
        lines.append("## Model Aliases")
        for alias in model_alias_lines:
            lines.append(alias)
        lines.append("")

    # 18. # Project Context - Bootstrap 文件内容
    if bootstrap_files.get_for_prompt():
        lines.append("# Project Context")
        lines.append("")
        lines.append("If SOUL.md is present, embody its persona and tone.")
        lines.append("")

        for f in bootstrap_files.get_for_prompt():
            lines.append(f"## {f.name}")
            lines.append("")
            lines.append(f.content)
            lines.append("")

    # 19. ## Silent Replies - 非 minimal
    if prompt_mode != "minimal":
        lines.append("## Silent Replies")
        lines.append("Use SILENT_REPLY_TOKEN when no response is needed.")
        lines.append("")

    # 20. ## Heartbeats - 非 minimal
    if prompt_mode != "minimal":
        lines.append("## Heartbeats")
        lines.append("Respond with HEARTBEAT_OK if periodic check requires no action.")
        if heartbeat_prompt:
            lines.append(heartbeat_prompt)
        lines.append("")

    # 21. ## Runtime
    lines.append("## Runtime")
    lines.append(build_runtime_line(context))
    lines.append("")

    # 22. ## Reactions - 有反应指导
    if reaction_guidance:
        lines.append("## Reactions")
        lines.append(reaction_guidance)
        lines.append("")

    # 23. ## Reasoning Format - 有推理提示
    if reasoning_tag_hint:
        lines.append("## Reasoning Format")
        lines.append(reasoning_tag_hint)
        lines.append("")

    # 子代理/群组特殊章节
    if context.is_subagent:
        lines.append("## Subagent Context")
        lines.append("You are a subagent spawned for a specific task.")
        lines.append("Focus on the task and return results concisely.")
        lines.append("Do NOT use session management tools or message tools directly.")
        lines.append("")
    elif context.session_type == "group":
        lines.append("## Group Chat Context")
        lines.append("You are participating in a group conversation.")
        lines.append("Be mindful of privacy and avoid sharing sensitive information.")
        lines.append("")

    return "\n".join(lines)

def build_runtime_line(context: "AgentContext") -> str:
    """
    构建 Runtime 行

    对标 MoltBot buildRuntimeLine()

    格式: Runtime: agent=xxx | host=xxx | os=xxx | model=xxx | channel=xxx | thinking=xxx
    """
    parts = [
        f"agent={context.session_id}",
        f"host={platform.node()}",
        f"os={platform.system()} ({platform.machine()})",
        f"python={platform.python_version()}",
        f"model={context.model}",
    ]

    if context.workspace:
        parts.append(f"repo={context.workspace}")

    if context.channel:
        parts.append(f"channel={context.channel}")

    if context.capabilities:
        parts.append(f"capabilities={','.join(context.capabilities)}")

    parts.append(f"thinking={context.thinking_level}")

    return "Runtime: " + " | ".join(parts)

def _has_memory_tools(tools: list | None) -> bool:
    if not tools:
        return False
    return any(t.name in ("memory_search", "memory_get") for t in tools)
```

### 3.4 九层工具策略 (`lurkbot.tools.policy`)

```python
# 文件: src/lurkbot/tools/policy.py

from dataclasses import dataclass, field
from enum import Enum
from typing import Literal

class ToolProfile(str, Enum):
    """工具配置文件 - 对标 MoltBot ToolProfileId"""
    MINIMAL = "minimal"
    CODING = "coding"
    MESSAGING = "messaging"
    FULL = "full"

# 对标 MoltBot TOOL_GROUPS
TOOL_GROUPS: dict[str, list[str]] = {
    "group:memory": ["memory_search", "memory_get"],
    "group:web": ["web_search", "web_fetch"],
    "group:fs": ["read", "write", "edit", "apply_patch"],
    "group:runtime": ["bash", "exec"],
    "group:sessions": [
        "sessions_spawn", "sessions_send", "sessions_list",
        "sessions_history", "session_status", "agents_list"
    ],
    "group:ui": ["browser", "canvas"],
    "group:automation": ["cron", "gateway"],
    "group:messaging": ["message"],
    "group:nodes": ["nodes"],
    "group:tts": ["tts"],
    "group:image": ["image"],
}

# 对标 MoltBot TOOL_PROFILES
TOOL_PROFILES: dict[ToolProfile, dict] = {
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
        "allow": ["*"]  # 允许所有
    }
}

# 对标 MoltBot SUBAGENT_DENY_LIST
SUBAGENT_DENY_LIST: list[str] = [
    "sessions_list", "sessions_history", "sessions_send",
    "sessions_spawn", "gateway", "agents_list", "session_status",
    "cron", "memory_search", "memory_get"
]

# 沙箱模式禁用的工具
SANDBOX_DENY_LIST: list[str] = [
    "bash", "exec", "write", "edit", "apply_patch"
]

# 群组聊天禁用的工具
GROUP_DENY_LIST: list[str] = [
    "bash", "exec", "write", "edit", "apply_patch",
    "sessions_spawn", "cron"
]

@dataclass
class ToolPolicyContext:
    """工具策略上下文 - 九层过滤的输入"""
    # Layer 1: Profile
    profile: ToolProfile = ToolProfile.FULL

    # Layer 2: Provider
    provider: str = "anthropic"

    # Layer 3: Model
    model: str = ""

    # Layer 4: Global
    global_allow: list[str] = field(default_factory=list)
    global_deny: list[str] = field(default_factory=list)

    # Layer 5: Agent type
    agent_type: Literal["embedded", "cli", "web"] = "embedded"

    # Layer 6: Session type & Channel
    session_type: str = "main"
    channel: str = ""

    # Layer 7: Sandbox
    sandbox_mode: bool = False

    # Layer 8: Subagent
    is_subagent: bool = False

    # Layer 9: Plugin tools (handled separately)

def filter_tools_by_policy(
    tools: list["Tool"],
    context: ToolPolicyContext,
) -> list["Tool"]:
    """
    应用九层工具策略过滤

    对标 MoltBot filterToolsByPolicy() 完整逻辑

    Layer 1: Profile-based     → 根据认证配置过滤（minimal/coding/messaging/full）
    Layer 2: Provider-based    → 提供商能力（OpenAI/Anthropic/Ollama/Google）
    Layer 3: Model-based       → 不同模型支持不同工具
    Layer 4: Global exclusions → 全局禁用的工具
    Layer 5: Agent-type        → embedded/cli/web 不同代理类型
    Layer 6: Group/Channel     → 群组聊天限制危险工具
    Layer 7: Sandbox mode      → 沙箱模式禁用文件系统工具
    Layer 8: Subagent          → 子代理限制递归生成
    Layer 9: Plugin merge      → 合并插件注册的工具（在外部处理）
    """
    result = list(tools)

    # Layer 1: Profile-based filtering
    profile_policy = TOOL_PROFILES.get(context.profile, TOOL_PROFILES[ToolProfile.FULL])
    if profile_policy.get("allow") != ["*"]:
        allowed = expand_tool_groups(profile_policy.get("allow", []))
        result = [t for t in result if t.name in allowed]

    # Layer 2: Provider-based filtering
    result = _filter_by_provider(result, context.provider)

    # Layer 3: Model-based filtering
    result = _filter_by_model(result, context.model)

    # Layer 4: Global exclusions
    if context.global_deny:
        denied = expand_tool_groups(context.global_deny)
        result = [t for t in result if t.name not in denied]
    if context.global_allow:
        allowed = expand_tool_groups(context.global_allow)
        result = [t for t in result if t.name in allowed]

    # Layer 5: Agent-type filtering
    # (embedded 通常有完整工具，cli/web 可能限制某些)
    pass  # 根据需要实现

    # Layer 6: Group/Channel filtering
    if context.session_type == "group":
        result = [t for t in result if t.name not in GROUP_DENY_LIST]

    # Layer 7: Sandbox mode filtering
    if context.sandbox_mode:
        result = [t for t in result if t.name not in SANDBOX_DENY_LIST]

    # Layer 8: Subagent filtering
    if context.is_subagent:
        result = [t for t in result if t.name not in SUBAGENT_DENY_LIST]

    return result

def expand_tool_groups(items: list[str]) -> set[str]:
    """展开工具组到具体工具名"""
    expanded = set()
    for item in items:
        if item.startswith("group:"):
            expanded.update(TOOL_GROUPS.get(item, []))
        elif item == "*":
            # 通配符 - 返回所有已知工具
            for tools in TOOL_GROUPS.values():
                expanded.update(tools)
        else:
            expanded.add(item)
    return expanded

def _filter_by_provider(tools: list, provider: str) -> list:
    """根据提供商过滤工具"""
    # 某些提供商可能不支持某些工具
    # 例如 Ollama 可能不支持 image 生成
    provider_deny = {
        "ollama": ["image", "canvas"],
        "google": [],  # Google 支持所有
    }
    denied = provider_deny.get(provider, [])
    return [t for t in tools if t.name not in denied]

def _filter_by_model(tools: list, model: str) -> list:
    """根据模型过滤工具"""
    # 某些模型可能有特定限制
    # 例如 GPT-3.5 可能不支持某些复杂工具
    if "gpt-3.5" in model:
        return [t for t in tools if t.name not in ["browser", "canvas"]]
    return tools
```

### 3.5 会话管理 (`lurkbot.sessions`)

```python
# 文件: src/lurkbot/sessions/manager.py

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Literal
import json

# 对标 MoltBot SessionType
SessionType = Literal["main", "group", "dm", "topic", "subagent"]

@dataclass
class SessionEntry:
    """
    会话元数据

    对标 MoltBot sessions.json 结构
    """
    session_id: str
    session_key: str
    session_type: SessionType
    created_at: int  # timestamp ms
    updated_at: int  # timestamp ms
    channel: str | None = None
    last_channel: str | None = None
    model: str | None = None
    model_provider: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    parent_session: str | None = None  # 对于子代理
    label: str | None = None  # 可选标签

def build_session_key(
    agent_id: str,
    session_type: SessionType,
    channel_id: str | None = None,
    group_id: str | None = None,
    child_id: str | None = None,
) -> str:
    """
    构建会话 Key

    对标 MoltBot session-key.ts

    格式:
    - 主会话: "agent:{agentId}:main"
    - 群组会话: "agent:{agentId}:group:{channelId}:{groupId}"
    - 子代理会话: "agent:{agentId}:subagent:{childId}"
    - 全局会话: "global"
    """
    if session_type == "main":
        return f"agent:{agent_id}:main"
    elif session_type == "group":
        return f"agent:{agent_id}:group:{channel_id}:{group_id}"
    elif session_type == "dm":
        return f"agent:{agent_id}:dm:{channel_id}"
    elif session_type == "topic":
        return f"agent:{agent_id}:topic:{channel_id}:{group_id}"
    elif session_type == "subagent":
        return f"agent:{agent_id}:subagent:{child_id}"
    else:
        return "global"

def is_subagent_session_key(session_key: str) -> bool:
    """判断是否为子代理会话 Key"""
    return ":subagent:" in session_key

class SessionStore:
    """
    会话存储

    对标 MoltBot ACP session 存储

    文件结构:
    - ~/.lurkbot/agents/{agentId}/sessions.json  # 会话元数据
    - ~/.lurkbot/agents/{agentId}/{sessionId}.jsonl  # 对话历史
    """

    def __init__(self, base_dir: str, agent_id: str):
        self.base_dir = Path(base_dir)
        self.agent_id = agent_id
        self.sessions_file = self.base_dir / "agents" / agent_id / "sessions.json"
        self._sessions: dict[str, SessionEntry] = {}
        self._load()

    def _load(self):
        if self.sessions_file.exists():
            data = json.loads(self.sessions_file.read_text())
            for key, entry in data.items():
                self._sessions[key] = SessionEntry(**entry)

    def _save(self):
        self.sessions_file.parent.mkdir(parents=True, exist_ok=True)
        data = {k: v.__dict__ for k, v in self._sessions.items()}
        self.sessions_file.write_text(json.dumps(data, indent=2))

    def get(self, session_key: str) -> SessionEntry | None:
        return self._sessions.get(session_key)

    def create(
        self,
        session_type: SessionType,
        channel: str | None = None,
        **kwargs,
    ) -> SessionEntry:
        import uuid
        session_id = f"ses_{uuid.uuid4().hex[:12]}"
        session_key = build_session_key(
            agent_id=self.agent_id,
            session_type=session_type,
            **kwargs,
        )
        now = int(datetime.now().timestamp() * 1000)
        entry = SessionEntry(
            session_id=session_id,
            session_key=session_key,
            session_type=session_type,
            created_at=now,
            updated_at=now,
            channel=channel,
        )
        self._sessions[session_key] = entry
        self._save()
        return entry

    def update(self, session_key: str, **kwargs):
        if session_key in self._sessions:
            entry = self._sessions[session_key]
            for k, v in kwargs.items():
                if hasattr(entry, k):
                    setattr(entry, k, v)
            entry.updated_at = int(datetime.now().timestamp() * 1000)
            self._save()

    def delete(self, session_key: str):
        if session_key in self._sessions:
            del self._sessions[session_key]
            self._save()

    def list(self, session_type: SessionType | None = None) -> list[SessionEntry]:
        entries = list(self._sessions.values())
        if session_type:
            entries = [e for e in entries if e.session_type == session_type]
        return sorted(entries, key=lambda e: e.updated_at, reverse=True)
```

### 3.6 子代理系统 (`lurkbot.agents.subagent`)

```python
# 文件: src/lurkbot/agents/subagent.py

from dataclasses import dataclass
from typing import Literal
from datetime import datetime

SubagentOutcome = Literal["ok", "error", "timeout", "unknown"]

@dataclass
class SubagentResult:
    """子代理执行结果"""
    session_key: str
    run_id: str
    outcome: SubagentOutcome
    result: str | None = None
    error: str | None = None
    duration_ms: int = 0
    tokens_used: int = 0

def build_subagent_system_prompt(
    requester_session_key: str | None,
    child_session_key: str,
    task: str,
    label: str | None = None,
) -> str:
    """
    构建子代理系统提示词

    对标 MoltBot buildSubagentSystemPrompt()
    """
    task_text = task or "(no specific task)"
    label_text = label or child_session_key.split(":")[-1]

    return f"""
# Subagent Context

You are a **subagent** spawned by the main agent for a specific task.

## Your Role
- You were created to handle: {task_text}
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
- NO using the `message` tool directly
- NO spawning other subagents

## Session Context
- Label: {label_text}
- Requester session: {requester_session_key or "unknown"}
- Your session: {child_session_key}
"""

async def run_subagent_announce_flow(
    child_session_key: str,
    child_run_id: str,
    requester_session_key: str,
    task: str,
    timeout_ms: int,
    cleanup: Literal["delete", "keep"],
    started_at: datetime,
) -> bool:
    """
    子代理结果汇报流程

    对标 MoltBot runSubagentAnnounceFlow()

    流程:
    1. 等待子代理完成
    2. 读取子代理最后回复
    3. 构建统计行
    4. 构建汇报消息
    5. 发送到主代理
    6. 清理（如果配置）
    """
    import asyncio
    from lurkbot.gateway.client import call_gateway

    # 1. 等待子代理完成
    try:
        await asyncio.wait_for(
            call_gateway({
                "method": "agent.wait",
                "params": {"runId": child_run_id, "timeoutMs": timeout_ms},
            }),
            timeout=timeout_ms / 1000 + 5,  # 额外 5 秒缓冲
        )
        outcome: SubagentOutcome = "ok"
    except asyncio.TimeoutError:
        outcome = "timeout"
    except Exception as e:
        outcome = "error"

    ended_at = datetime.now()

    # 2. 读取子代理最后回复
    reply = await read_latest_assistant_reply(child_session_key)

    # 3. 构建统计行
    stats_line = await build_subagent_stats_line(
        session_key=child_session_key,
        started_at=started_at,
        ended_at=ended_at,
    )

    # 4. 构建汇报消息
    status_label = {
        "ok": "completed",
        "error": "failed",
        "timeout": "timed out",
        "unknown": "ended",
    }[outcome]

    task_label = task[:50] + "..." if len(task) > 50 else task

    trigger_message = f"""
A background task "{task_label}" just {status_label}.

Findings:
{reply or "(no output)"}

{stats_line}

Summarize this naturally for the user. Keep it brief (1-2 sentences).
"""

    # 5. 发送到主代理
    await call_gateway({
        "method": "agent",
        "params": {
            "sessionKey": requester_session_key,
            "message": trigger_message,
            "deliver": True,
        },
    })

    # 6. 清理
    if cleanup == "delete":
        await call_gateway({
            "method": "sessions.delete",
            "params": {"key": child_session_key},
        })

    return outcome == "ok"

async def read_latest_assistant_reply(session_key: str) -> str | None:
    """读取会话中最后一条助手回复"""
    # 实现从 JSONL 文件读取
    pass

async def build_subagent_stats_line(
    session_key: str,
    started_at: datetime,
    ended_at: datetime,
) -> str:
    """构建统计行"""
    duration = (ended_at - started_at).total_seconds()
    return f"[Stats: duration={duration:.1f}s]"
```

### 3.7 Heartbeat 心跳系统 (`lurkbot.autonomous.heartbeat`)

```python
# 文件: src/lurkbot/autonomous/heartbeat.py

from dataclasses import dataclass
from datetime import datetime, time
from typing import Literal
from pathlib import Path
import asyncio

@dataclass
class HeartbeatConfig:
    """
    心跳配置

    对标 MoltBot HeartbeatConfig
    """
    enabled: bool = True
    every: str = "5m"  # "5m", "30s", etc.
    prompt: str | None = None
    target: Literal["main", "last"] = "last"
    model: str | None = None
    ack_max_chars: int = 100
    session: str | None = None
    active_hours: "ActiveHours | None" = None
    include_reasoning: bool = False

@dataclass
class ActiveHours:
    """活动时间窗口"""
    start: str  # "HH:MM"
    end: str    # "HH:MM" or "24:00"
    timezone: str = "local"  # "user" | "local" | specific tz

@dataclass
class HeartbeatEventPayload:
    """
    心跳事件 Payload

    对标 MoltBot HeartbeatEventPayload
    """
    ts: int
    status: Literal["sent", "ok-empty", "ok-token", "skipped", "failed"]
    to: str | None = None
    preview: str | None = None
    duration_ms: int | None = None
    has_media: bool = False
    reason: str | None = None
    channel: str | None = None
    silent: bool = False
    indicator_type: Literal["ok", "alert", "error"] | None = None

# Token 常量
HEARTBEAT_OK_TOKEN = "HEARTBEAT_OK"
DEFAULT_HEARTBEAT_EVERY = "5m"
DEFAULT_HEARTBEAT_ACK_MAX_CHARS = 100
DEFAULT_HEARTBEAT_TARGET = "last"

class HeartbeatRunner:
    """
    心跳运行器

    对标 MoltBot HeartbeatRunner
    """

    def __init__(
        self,
        workspace_dir: str,
        agent_id: str,
        config: HeartbeatConfig,
    ):
        self.workspace = Path(workspace_dir)
        self.agent_id = agent_id
        self.config = config
        self._running = False
        self._last_event: HeartbeatEventPayload | None = None
        self._event_listeners: list[callable] = []
        self._recent_messages: list[str] = []  # 24小时内的消息（去重用）

    def on_event(self, listener: callable):
        """注册事件监听器"""
        self._event_listeners.append(listener)

    def get_last_event(self) -> HeartbeatEventPayload | None:
        """获取最后一次心跳事件"""
        return self._last_event

    async def start(self):
        """启动心跳循环"""
        self._running = True
        interval_seconds = self._parse_interval(self.config.every)

        while self._running:
            result = await self.run_once()
            self._emit_event(result)
            await asyncio.sleep(interval_seconds)

    def stop(self):
        """停止心跳循环"""
        self._running = False

    async def run_once(self) -> HeartbeatEventPayload:
        """
        执行一次心跳检查

        对标 MoltBot runHeartbeatOnce()

        流程:
        1. 检查是否启用
        2. 检查是否在活动时间内
        3. 检查是否有请求在执行
        4. 读取 HEARTBEAT.md
        5. 解析会话和投递目标
        6. 调用 LLM 获取响应
        7. 检查是否为 HEARTBEAT_OK
        8. 抑制重复
        9. 投递消息
        """
        start_time = datetime.now()

        # 1. 检查是否启用
        if not self.config.enabled:
            return self._create_event("skipped", reason="disabled")

        # 2. 检查是否在活动时间内
        if not self._is_within_active_hours():
            return self._create_event("skipped", reason="quiet-hours")

        # 3. 检查是否有请求在执行
        if await self._has_requests_in_flight():
            return self._create_event("skipped", reason="requests-in-flight")

        # 4. 读取 HEARTBEAT.md
        heartbeat_file = self.workspace / "HEARTBEAT.md"
        if not heartbeat_file.exists():
            return self._create_event("skipped", reason="no-heartbeat-file")

        content = heartbeat_file.read_text().strip()
        if self._is_effectively_empty(content):
            return self._create_event("ok-empty", reason="empty-heartbeat-file")

        # 5. 构建心跳提示词
        prompt = self.config.prompt or self._build_default_prompt(content)

        # 6. 调用 LLM
        try:
            reply = await self._get_reply(prompt)
        except Exception as e:
            return self._create_event("failed", reason=str(e))

        # 7. 检查是否为 HEARTBEAT_OK
        stripped = self._strip_heartbeat_token(reply)
        if stripped["is_heartbeat_ok"]:
            return self._create_event(
                "ok-token",
                duration_ms=self._duration_ms(start_time),
            )

        # 8. 抑制重复
        if self._is_duplicate_within_24h(stripped["text"]):
            return self._create_event("skipped", reason="duplicate")

        # 9. 投递消息
        await self._deliver_message(stripped["text"])

        return self._create_event(
            "sent",
            preview=stripped["text"][:100],
            duration_ms=self._duration_ms(start_time),
        )

    def _is_within_active_hours(self) -> bool:
        """检查是否在活动时间窗口内"""
        if not self.config.active_hours:
            return True

        now = datetime.now().time()
        start = time.fromisoformat(self.config.active_hours.start)
        end_str = self.config.active_hours.end
        if end_str == "24:00":
            end = time(23, 59, 59)
        else:
            end = time.fromisoformat(end_str)

        if start <= end:
            return start <= now <= end
        else:
            # 跨午夜
            return now >= start or now <= end

    def _strip_heartbeat_token(self, text: str) -> dict:
        """提取 HEARTBEAT_OK token"""
        stripped = text.strip()
        if HEARTBEAT_OK_TOKEN in stripped:
            cleaned = stripped.replace(HEARTBEAT_OK_TOKEN, "").strip()
            return {"is_heartbeat_ok": True, "text": cleaned}
        return {"is_heartbeat_ok": False, "text": stripped}

    def _is_duplicate_within_24h(self, text: str) -> bool:
        """检查是否为 24 小时内的重复消息"""
        # 简化实现 - 存储最近消息的 hash
        text_hash = hash(text)
        if text_hash in self._recent_messages:
            return True
        self._recent_messages.append(text_hash)
        # 保留最近 100 条
        if len(self._recent_messages) > 100:
            self._recent_messages = self._recent_messages[-100:]
        return False

    def _is_effectively_empty(self, content: str) -> bool:
        """检查内容是否实际为空"""
        lines = [l.strip() for l in content.split("\n") if l.strip()]
        # 移除注释行
        lines = [l for l in lines if not l.startswith("#")]
        return len(lines) == 0

    def _build_default_prompt(self, content: str) -> str:
        return f"""
## Heartbeat Check

It's time for your periodic check. Please review and handle these tasks:

{content}

After completing checks:
1. If anything needs user attention, notify them
2. If no action needed, respond with HEARTBEAT_OK

Keep responses brief and actionable.
"""

    def _create_event(
        self,
        status: str,
        **kwargs,
    ) -> HeartbeatEventPayload:
        return HeartbeatEventPayload(
            ts=int(datetime.now().timestamp() * 1000),
            status=status,
            **kwargs,
        )

    def _emit_event(self, event: HeartbeatEventPayload):
        self._last_event = event
        for listener in self._event_listeners:
            try:
                listener(event)
            except Exception:
                pass

    def _duration_ms(self, start: datetime) -> int:
        return int((datetime.now() - start).total_seconds() * 1000)

    def _parse_interval(self, interval: str) -> float:
        """解析时间间隔字符串"""
        if interval.endswith("s"):
            return float(interval[:-1])
        elif interval.endswith("m"):
            return float(interval[:-1]) * 60
        elif interval.endswith("h"):
            return float(interval[:-1]) * 3600
        else:
            return 300  # 默认 5 分钟

    async def _has_requests_in_flight(self) -> bool:
        # 实现检查是否有进行中的请求
        return False

    async def _get_reply(self, prompt: str) -> str:
        # 调用 LLM 获取回复
        pass

    async def _deliver_message(self, text: str):
        # 投递消息到目标渠道
        pass
```

### 3.8 Cron 定时任务 (`lurkbot.autonomous.cron`)

```python
# 文件: src/lurkbot/autonomous/cron.py

from dataclasses import dataclass, field
from typing import Literal
from datetime import datetime
import uuid

@dataclass
class CronSchedule:
    """
    Cron 调度配置

    对标 MoltBot CronSchedule
    """
    kind: Literal["at", "every", "cron"]
    at_ms: int | None = None      # for "at": 单次执行时间戳
    every_ms: int | None = None   # for "every": 周期间隔
    anchor_ms: int | None = None  # for "every": 锚点时间
    expr: str | None = None       # for "cron": Cron 表达式
    tz: str = "UTC"               # 时区

@dataclass
class CronPayload:
    """
    Cron 执行 Payload

    对标 MoltBot CronPayload

    两种类型:
    - systemEvent: 向主会话注入文本事件（轻量级提醒）
    - agentTurn: 运行隔离会话中的代理任务（重量级任务）
    """
    kind: Literal["systemEvent", "agentTurn"]

    # 共用字段
    message: str = ""

    # agentTurn 专用
    model: str | None = None
    thinking: str | None = None
    timeout_seconds: int = 3600
    deliver: bool = True
    channel: str | None = None  # "last" | specific channel
    to: str | None = None
    best_effort_deliver: bool = False

@dataclass
class CronJobState:
    """Cron Job 运行状态"""
    next_run_at_ms: int | None = None
    running_at_ms: int | None = None
    last_run_at_ms: int | None = None
    last_status: Literal["ok", "error", "skipped"] | None = None
    last_error: str | None = None
    last_duration_ms: int | None = None

@dataclass
class CronJob:
    """
    Cron Job 定义

    对标 MoltBot CronJob
    """
    id: str
    name: str
    description: str | None = None
    enabled: bool = True
    delete_after_run: bool = False
    created_at_ms: int = field(default_factory=lambda: int(datetime.now().timestamp() * 1000))
    updated_at_ms: int = field(default_factory=lambda: int(datetime.now().timestamp() * 1000))

    schedule: CronSchedule = field(default_factory=lambda: CronSchedule(kind="every", every_ms=3600000))
    session_target: Literal["main", "isolated"] = "main"
    wake_mode: Literal["next-heartbeat", "now"] = "next-heartbeat"
    payload: CronPayload = field(default_factory=lambda: CronPayload(kind="systemEvent"))

    # 隔离会话配置
    isolation: dict | None = None
    # {
    #   "postToMainPrefix": str,
    #   "postToMainMode": "summary" | "full",
    #   "postToMainMaxChars": int,
    # }

    state: CronJobState = field(default_factory=CronJobState)
    agent_id: str | None = None

class CronService:
    """
    Cron 服务

    对标 MoltBot CronService
    """

    def __init__(self, storage_path: str, agent_id: str):
        self.storage_path = storage_path
        self.agent_id = agent_id
        self.jobs: dict[str, CronJob] = {}
        self._running = False
        self._load()

    def start(self):
        """启动 Cron 服务"""
        self._running = True
        # 启动调度循环
        import asyncio
        asyncio.create_task(self._scheduler_loop())

    def stop(self):
        """停止 Cron 服务"""
        self._running = False

    def status(self) -> dict:
        """获取服务状态"""
        return {
            "running": self._running,
            "jobs_count": len(self.jobs),
            "next_run": self._get_next_run(),
        }

    def list(self, agent_id: str | None = None) -> list[CronJob]:
        """列出所有 Jobs"""
        jobs = list(self.jobs.values())
        if agent_id:
            jobs = [j for j in jobs if j.agent_id == agent_id]
        return jobs

    def add(self, job_input: dict) -> CronJob:
        """添加 Job"""
        job_id = f"cron_{uuid.uuid4().hex[:8]}"
        job = CronJob(id=job_id, **job_input)

        # 验证规则
        self._validate_job(job)

        self.jobs[job_id] = job
        self._save()
        return job

    def update(self, job_id: str, patch: dict) -> CronJob:
        """更新 Job"""
        if job_id not in self.jobs:
            raise ValueError(f"Job not found: {job_id}")

        job = self.jobs[job_id]
        for k, v in patch.items():
            if hasattr(job, k):
                setattr(job, k, v)
        job.updated_at_ms = int(datetime.now().timestamp() * 1000)
        self._save()
        return job

    def remove(self, job_id: str):
        """删除 Job"""
        if job_id in self.jobs:
            del self.jobs[job_id]
            self._save()

    async def run(self, job_id: str, mode: Literal["due", "force"] = "due") -> dict:
        """
        运行 Job

        mode:
        - "due": 只在到期时运行
        - "force": 强制立即运行
        """
        if job_id not in self.jobs:
            raise ValueError(f"Job not found: {job_id}")

        job = self.jobs[job_id]

        if mode == "due" and not self._is_due(job):
            return {"status": "skipped", "reason": "not due"}

        return await self._execute_job(job)

    def wake(self, mode: Literal["next-heartbeat", "now"] = "next-heartbeat"):
        """唤醒调度器"""
        # 触发立即检查
        pass

    def _validate_job(self, job: CronJob):
        """验证 Job 配置"""
        # main 会话只能用 systemEvent
        if job.session_target == "main" and job.payload.kind != "systemEvent":
            raise ValueError("main session must use systemEvent payload")

        # isolated 会话只能用 agentTurn
        if job.session_target == "isolated" and job.payload.kind != "agentTurn":
            raise ValueError("isolated session must use agentTurn payload")

    def _is_due(self, job: CronJob) -> bool:
        """检查 Job 是否到期"""
        now = int(datetime.now().timestamp() * 1000)
        next_run = job.state.next_run_at_ms
        return next_run is not None and now >= next_run

    async def _execute_job(self, job: CronJob) -> dict:
        """执行 Job"""
        start_time = datetime.now()
        job.state.running_at_ms = int(start_time.timestamp() * 1000)

        try:
            if job.payload.kind == "systemEvent":
                result = await self._execute_system_event(job)
            else:
                result = await self._execute_agent_turn(job)

            job.state.last_status = "ok"
            job.state.last_run_at_ms = job.state.running_at_ms
            job.state.last_duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            # 计算下次运行时间
            self._schedule_next_run(job)

            # 单次执行后删除
            if job.delete_after_run:
                self.remove(job.id)

            return result

        except Exception as e:
            job.state.last_status = "error"
            job.state.last_error = str(e)
            return {"status": "error", "error": str(e)}

        finally:
            job.state.running_at_ms = None
            self._save()

    async def _execute_system_event(self, job: CronJob) -> dict:
        """执行 systemEvent 类型的 Job"""
        from lurkbot.gateway.client import call_gateway

        await call_gateway({
            "method": "chat.inject",
            "params": {
                "sessionKey": f"agent:{self.agent_id}:main",
                "message": job.payload.message,
            },
        })
        return {"status": "ok", "type": "systemEvent"}

    async def _execute_agent_turn(self, job: CronJob) -> dict:
        """执行 agentTurn 类型的 Job"""
        from lurkbot.agents.runtime import run_embedded_agent

        # 创建隔离会话
        session_id = f"cron_{job.id}_{int(datetime.now().timestamp())}"

        result = await run_embedded_agent(
            context={
                "session_id": session_id,
                "session_type": "subagent",
                "model": job.payload.model,
                "thinking_level": job.payload.thinking or "medium",
            },
            prompt=job.payload.message,
        )

        # 如果需要投递到主会话
        if job.payload.deliver and job.isolation:
            await self._post_to_main(job, result)

        return {"status": "ok", "type": "agentTurn", "result": result}

    def _schedule_next_run(self, job: CronJob):
        """计算下次运行时间"""
        now = int(datetime.now().timestamp() * 1000)

        if job.schedule.kind == "at":
            # 单次执行，不需要下次
            job.state.next_run_at_ms = None

        elif job.schedule.kind == "every":
            # 周期执行
            interval = job.schedule.every_ms or 3600000
            job.state.next_run_at_ms = now + interval

        elif job.schedule.kind == "cron":
            # Cron 表达式
            from croniter import croniter
            cron = croniter(job.schedule.expr, datetime.now())
            next_dt = cron.get_next(datetime)
            job.state.next_run_at_ms = int(next_dt.timestamp() * 1000)

    async def _scheduler_loop(self):
        """调度器主循环"""
        import asyncio
        while self._running:
            for job in self.jobs.values():
                if job.enabled and self._is_due(job):
                    await self._execute_job(job)
            await asyncio.sleep(1)  # 每秒检查一次

    def _load(self):
        # 从文件加载 jobs
        pass

    def _save(self):
        # 保存 jobs 到文件
        pass

    def _get_next_run(self) -> int | None:
        """获取下一个要执行的时间"""
        next_times = [
            j.state.next_run_at_ms
            for j in self.jobs.values()
            if j.enabled and j.state.next_run_at_ms
        ]
        return min(next_times) if next_times else None

    async def _post_to_main(self, job: CronJob, result):
        """将隔离会话结果投递到主会话"""
        pass
```

### 3.9 Auth Profile 系统 (`lurkbot.auth.profiles`)

```python
# 文件: src/lurkbot/auth/profiles.py

from dataclasses import dataclass, field
from typing import Literal
from datetime import datetime
import json
from pathlib import Path

@dataclass
class AuthCredential:
    """
    认证凭据

    对标 MoltBot AuthProfileCredential
    """
    type: Literal["api_key", "token", "oauth"]
    key: str | None = None      # for api_key
    token: str | None = None    # for token
    expires: int | None = None  # for token (timestamp)
    access: str | None = None   # for oauth
    refresh: str | None = None  # for oauth

@dataclass
class ProfileUsageStats:
    """
    使用统计

    对标 MoltBot ProfileUsageStats
    """
    last_used: int | None = None
    error_count: int = 0
    cooldown_until: int | None = None
    disabled_until: int | None = None
    disabled_reason: str | None = None
    failure_counts: dict[str, int] = field(default_factory=dict)
    # failure_counts: { "auth": 2, "rate_limit": 1, "timeout": 0, ... }

@dataclass
class AuthProfileStore:
    """
    Profile 存储

    对标 MoltBot AuthProfileStore
    """
    profiles: dict[str, AuthCredential] = field(default_factory=dict)
    usage_stats: dict[str, ProfileUsageStats] = field(default_factory=dict)
    order: dict[str, list[str]] = field(default_factory=dict)
    # order: { "anthropic": ["profile1", "profile2"], "openai": [...] }

def calculate_cooldown_ms(error_count: int) -> int:
    """
    计算冷却时间

    对标 MoltBot calculateAuthProfileCooldownMs()

    公式: cooldown = min(1 hour, 60 sec × 5^(errorCount-1))
    - errorCount=1 → 60s
    - errorCount=2 → 300s (5m)
    - errorCount=3 → 1500s (25m)
    - errorCount=4+ → 3600s (1h) 上限
    """
    base = 60 * 1000  # 60 seconds in ms
    factor = pow(5, max(0, error_count - 1))
    return min(3600 * 1000, int(base * factor))  # max 1 hour

def resolve_auth_profile_order(
    store: AuthProfileStore,
    provider: str,
    preferred_profile: str | None = None,
) -> list[str]:
    """
    解析 Profile 顺序

    对标 MoltBot resolveAuthProfileOrder()

    算法:
    1. 规范化提供商名称
    2. 确定基础顺序
    3. 过滤有效配置文件
    4. 分离：可用 vs 冷却中
    5. 可用的按 lastUsed 排序（最旧优先 = 轮换）
    6. 冷却中的按冷却结束时间排序
    7. 优先指定的 Profile
    """
    normalized_provider = normalize_provider_id(provider)
    now = int(datetime.now().timestamp() * 1000)

    # 确定基础顺序
    base_order = (
        store.order.get(normalized_provider) or
        [p for p in store.profiles.keys() if match_provider(p, normalized_provider)]
    )

    # 过滤有效配置文件
    valid_profiles = [
        p for p in base_order
        if p in store.profiles and is_valid_credential(store.profiles[p])
    ]

    # 分离可用和冷却中的
    available: list[str] = []
    in_cooldown: list[str] = []

    for p in valid_profiles:
        stats = store.usage_stats.get(p, ProfileUsageStats())
        if stats.cooldown_until and stats.cooldown_until > now:
            in_cooldown.append(p)
        else:
            available.append(p)

    # 按 lastUsed 排序（最旧优先）
    available.sort(key=lambda p: store.usage_stats.get(p, ProfileUsageStats()).last_used or 0)

    # 按冷却结束时间排序
    in_cooldown.sort(key=lambda p: store.usage_stats.get(p, ProfileUsageStats()).cooldown_until or 0)

    # 合并
    result = available + in_cooldown

    # 优先指定的 Profile
    if preferred_profile and preferred_profile in result:
        result = [preferred_profile] + [p for p in result if p != preferred_profile]

    return result

def mark_profile_failure(
    store: AuthProfileStore,
    profile_id: str,
    reason: str | None = None,
):
    """
    标记 Profile 失败

    对标 MoltBot markAuthProfileFailure()
    """
    if profile_id not in store.usage_stats:
        store.usage_stats[profile_id] = ProfileUsageStats()

    stats = store.usage_stats[profile_id]
    stats.error_count += 1
    stats.cooldown_until = int(datetime.now().timestamp() * 1000) + calculate_cooldown_ms(stats.error_count)

    if reason:
        stats.failure_counts[reason] = stats.failure_counts.get(reason, 0) + 1

def mark_profile_success(
    store: AuthProfileStore,
    profile_id: str,
):
    """标记 Profile 成功"""
    if profile_id not in store.usage_stats:
        store.usage_stats[profile_id] = ProfileUsageStats()

    stats = store.usage_stats[profile_id]
    stats.last_used = int(datetime.now().timestamp() * 1000)
    stats.error_count = 0
    stats.cooldown_until = None

def normalize_provider_id(provider: str) -> str:
    """规范化提供商 ID"""
    return provider.lower().split(":")[0]

def match_provider(profile_id: str, provider: str) -> bool:
    """检查 Profile 是否匹配提供商"""
    return profile_id.lower().startswith(provider.lower())

def is_valid_credential(cred: AuthCredential) -> bool:
    """检查凭据是否有效"""
    if cred.type == "api_key":
        return bool(cred.key)
    elif cred.type == "token":
        if not cred.token:
            return False
        if cred.expires and cred.expires < datetime.now().timestamp() * 1000:
            return False
        return True
    elif cred.type == "oauth":
        return bool(cred.access)
    return False
```

### 3.10 Context Compaction (`lurkbot.agents.compaction`)

```python
# 文件: src/lurkbot/agents/compaction.py

from dataclasses import dataclass

# 对标 MoltBot compaction.ts 常量
BASE_CHUNK_RATIO = 0.4      # 40% 保留最近历史
MIN_CHUNK_RATIO = 0.15      # 最小 15%
SAFETY_MARGIN = 1.2         # 20% 估算缓冲
DEFAULT_CONTEXT_TOKENS = 128000  # 默认上下文窗口

MERGE_SUMMARIES_INSTRUCTIONS = (
    "Merge these partial summaries into a single cohesive summary. "
    "Preserve decisions, TODOs, open questions, and any constraints."
)

def estimate_tokens(text: str, model: str = "claude") -> int:
    """
    估算文本的 token 数

    简化实现: 约 4 字符 = 1 token
    """
    return len(text) // 4 + 1

def estimate_messages_tokens(messages: list[dict]) -> int:
    """估算消息列表的 token 数"""
    total = 0
    for msg in messages:
        content = msg.get("content", "")
        if isinstance(content, str):
            total += estimate_tokens(content)
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    total += estimate_tokens(block.get("text", ""))
    return total

def split_messages_by_token_share(
    messages: list[dict],
    parts: int = 2,
) -> list[list[dict]]:
    """
    按 Token 比例分割消息

    对标 MoltBot splitMessagesByTokenShare()
    """
    if not messages:
        return []

    total_tokens = estimate_messages_tokens(messages)
    target_tokens = total_tokens / parts

    chunks: list[list[dict]] = []
    current: list[dict] = []
    current_tokens = 0

    for message in messages:
        message_tokens = estimate_messages_tokens([message])

        if (
            len(chunks) < parts - 1 and
            current and
            current_tokens + message_tokens > target_tokens
        ):
            chunks.append(current)
            current = []
            current_tokens = 0

        current.append(message)
        current_tokens += message_tokens

    if current:
        chunks.append(current)

    return chunks

def chunk_messages_by_max_tokens(
    messages: list[dict],
    max_tokens: int,
) -> list[list[dict]]:
    """
    按最大 Token 数分块

    对标 MoltBot chunkMessagesByMaxTokens()
    """
    chunks: list[list[dict]] = []
    current_chunk: list[dict] = []
    current_tokens = 0

    for message in messages:
        message_tokens = estimate_messages_tokens([message])

        if current_chunk and current_tokens + message_tokens > max_tokens:
            chunks.append(current_chunk)
            current_chunk = []
            current_tokens = 0

        current_chunk.append(message)
        current_tokens += message_tokens

    if current_chunk:
        chunks.append(current_chunk)

    return chunks

def compute_adaptive_chunk_ratio(
    messages: list[dict],
    context_window: int,
) -> float:
    """
    计算自适应分块比例

    对标 MoltBot computeAdaptiveChunkRatio()

    逻辑:
    - 如果平均消息 > 上下文的 10%，减少分块比例
    - 确保不低于 MIN_CHUNK_RATIO
    """
    if not messages:
        return BASE_CHUNK_RATIO

    total_tokens = estimate_messages_tokens(messages)
    avg_tokens = total_tokens / len(messages)

    # 应用安全边界
    safe_avg_tokens = avg_tokens * SAFETY_MARGIN
    avg_ratio = safe_avg_tokens / context_window

    # 如果平均消息 > 上下文的 10%，减少分块比例
    if avg_ratio > 0.1:
        reduction = min(avg_ratio * 2, BASE_CHUNK_RATIO - MIN_CHUNK_RATIO)
        return max(MIN_CHUNK_RATIO, BASE_CHUNK_RATIO - reduction)

    return BASE_CHUNK_RATIO

async def summarize_in_stages(
    messages: list[dict],
    llm_client,
    reserve_tokens: int,
    max_chunk_tokens: int,
    context_window: int,
    parts: int = 2,
) -> str:
    """
    分阶段摘要

    对标 MoltBot summarizeInStages()

    流程:
    1. 将消息分成多个部分
    2. 对每个部分生成摘要
    3. 合并所有部分摘要
    """
    # 分割消息
    splits = split_messages_by_token_share(messages, parts)

    # 生成部分摘要
    partial_summaries: list[str] = []
    for chunk in splits:
        summary = await _summarize_chunk(chunk, llm_client)
        partial_summaries.append(summary)

    # 如果只有一个摘要，直接返回
    if len(partial_summaries) == 1:
        return partial_summaries[0]

    # 合并摘要
    return await _merge_summaries(partial_summaries, llm_client)

async def _summarize_chunk(messages: list[dict], llm_client) -> str:
    """摘要单个消息块"""
    prompt = """Summarize the following conversation, focusing on:
1. Key decisions made
2. Important information shared
3. Unresolved tasks or questions
4. Context needed for continuing the conversation

Be concise but preserve essential information.

Conversation:
"""
    for msg in messages:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        if isinstance(content, str):
            prompt += f"\n{role}: {content[:1000]}..."  # 截断长消息

    response = await llm_client.chat([
        {"role": "system", "content": "You are a conversation summarizer."},
        {"role": "user", "content": prompt}
    ])

    return response.text

async def _merge_summaries(summaries: list[str], llm_client) -> str:
    """合并多个摘要"""
    prompt = f"{MERGE_SUMMARIES_INSTRUCTIONS}\n\nSummaries:\n"
    for i, summary in enumerate(summaries, 1):
        prompt += f"\n--- Part {i} ---\n{summary}\n"

    response = await llm_client.chat([
        {"role": "system", "content": "You are a conversation summarizer."},
        {"role": "user", "content": prompt}
    ])

    return response.text

async def compact_messages(
    messages: list[dict],
    context_window: int,
    reserve_tokens: int = 16384,
    llm_client=None,
) -> list[dict]:
    """
    压缩消息历史

    返回压缩后的消息列表，包含摘要和保留的最近消息
    """
    total_tokens = estimate_messages_tokens(messages)

    # 如果不需要压缩，直接返回
    if total_tokens <= context_window - reserve_tokens:
        return messages

    # 计算自适应比例
    ratio = compute_adaptive_chunk_ratio(messages, context_window)

    # 计算要保留的最近消息数量
    target_recent_tokens = int(context_window * ratio)
    recent_messages: list[dict] = []
    recent_tokens = 0

    for msg in reversed(messages):
        msg_tokens = estimate_messages_tokens([msg])
        if recent_tokens + msg_tokens > target_recent_tokens:
            break
        recent_messages.insert(0, msg)
        recent_tokens += msg_tokens

    # 需要压缩的旧消息
    old_messages = messages[:-len(recent_messages)] if recent_messages else messages

    # 生成摘要
    summary = await summarize_in_stages(
        messages=old_messages,
        llm_client=llm_client,
        reserve_tokens=reserve_tokens,
        max_chunk_tokens=context_window // 4,
        context_window=context_window,
    )

    # 构建压缩后的消息
    return [
        {
            "role": "system",
            "content": f"[Previous conversation summary]\n\n{summary}"
        }
    ] + recent_messages
```

---

## 四、A2UI 界面系统设计

### 4.1 A2UI 概述

A2UI（Agent-to-User Interface）是由 Anthropic 和 Google 联合开源的声明式 UI 格式，MoltBot 中已有完整实现。LurkBot 需要复刻此功能以支持 Agent 生成动态界面。

> **MoltBot 实现分析**: 详见 [MOLTBOT_COMPLETE_ARCHITECTURE.md - 十九、A2UI 界面系统](./MOLTBOT_COMPLETE_ARCHITECTURE.md#十九a2ui-界面系统)

#### 设计目标

| 目标 | 描述 |
|------|------|
| **完全复刻** | 支持所有 MoltBot A2UI 功能 |
| **声明式 API** | Agent 描述"要展示什么"，而非"如何渲染" |
| **跨平台** | 支持 Web、移动端渲染 |
| **流式友好** | 支持 JSONL 流式传输 |

### 4.2 模块设计

#### 4.2.1 Canvas Host (`lurkbot.canvas_host`)

```python
# 文件: src/lurkbot/canvas_host/server.py

from fastapi import APIRouter, WebSocket, HTTPException
from pydantic import BaseModel
from typing import Any
import json

router = APIRouter(prefix="/a2ui")

class PushRequest(BaseModel):
    """A2UI 推送请求"""
    jsonl: str
    session_id: str

class A2UIState(BaseModel):
    """A2UI 状态"""
    surfaces: dict[str, dict] = {}
    data_model: dict[str, Any] = {}

class CanvasHost:
    """
    Canvas Host 服务

    对标 MoltBot src/canvas-host/server.ts

    职责:
    - 管理 WebSocket 客户端连接
    - 维护 A2UI 状态
    - 广播消息到客户端
    """

    def __init__(self):
        self.clients: dict[str, set[WebSocket]] = {}
        self.state: dict[str, A2UIState] = {}

    async def broadcast(self, session_id: str, messages: list[dict]):
        """广播 A2UI 消息到所有连接的客户端"""
        clients = self.clients.get(session_id, set())

        for message in messages:
            self._update_state(session_id, message)
            payload = json.dumps(message)

            for client in list(clients):
                try:
                    await client.send_text(payload)
                except Exception:
                    clients.discard(client)

    def _update_state(self, session_id: str, message: dict):
        """更新内部状态"""
        if session_id not in self.state:
            self.state[session_id] = A2UIState()

        state = self.state[session_id]
        msg_type = message.get("type")

        if msg_type == "surfaceUpdate":
            state.surfaces[message["surfaceId"]] = message["surface"]
        elif msg_type == "dataModelUpdate":
            self._set_nested(state.data_model, message["path"], message["value"])
        elif msg_type == "deleteSurface":
            state.surfaces.pop(message.get("surfaceId"), None)
        elif msg_type == "reset":
            self.state[session_id] = A2UIState()

    def _set_nested(self, data: dict, path: str, value: Any):
        """设置嵌套数据"""
        keys = path.split(".")
        for key in keys[:-1]:
            data = data.setdefault(key, {})
        data[keys[-1]] = value

    async def reset(self, session_id: str):
        """重置会话状态"""
        self.state.pop(session_id, None)
        await self.broadcast(session_id, [{"type": "reset"}])

    def get_state(self, session_id: str) -> A2UIState:
        """获取当前状态"""
        return self.state.get(session_id, A2UIState())

# 全局实例
canvas_host = CanvasHost()

@router.post("/push")
async def push_a2ui(request: PushRequest):
    """推送 A2UI JSONL 消息"""
    from lurkbot.canvas_host.validation import parse_jsonl, validate_messages

    messages = parse_jsonl(request.jsonl)
    if not validate_messages(messages):
        raise HTTPException(400, "Invalid A2UI JSONL")

    await canvas_host.broadcast(request.session_id, messages)
    return {"success": True, "message_count": len(messages)}

@router.post("/reset")
async def reset_canvas(session_id: str):
    """重置画布状态"""
    await canvas_host.reset(session_id)
    return {"success": True}

@router.get("/state")
async def get_state(session_id: str):
    """获取当前状态"""
    state = canvas_host.get_state(session_id)
    return state.model_dump()

@router.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket 连接端点"""
    await websocket.accept()

    # 注册客户端
    if session_id not in canvas_host.clients:
        canvas_host.clients[session_id] = set()
    canvas_host.clients[session_id].add(websocket)

    try:
        # 发送当前状态同步
        state = canvas_host.get_state(session_id)
        if state.surfaces or state.data_model:
            await websocket.send_json({
                "type": "state_sync",
                "state": state.model_dump()
            })

        # 保持连接并处理客户端消息
        while True:
            data = await websocket.receive_text()
            callback = json.loads(data)

            if callback.get("type") == "callback":
                # 转发回调到 Agent
                await _handle_callback(session_id, callback)

    finally:
        canvas_host.clients[session_id].discard(websocket)

async def _handle_callback(session_id: str, callback: dict):
    """处理客户端回调"""
    from lurkbot.gateway.client import call_gateway

    await call_gateway({
        "method": "chat.inject",
        "params": {
            "sessionKey": session_id,
            "message": f"[A2UI Callback] {callback.get('id')}: {json.dumps(callback.get('data', {}))}",
        },
    })
```

#### 4.2.2 JSONL 验证 (`lurkbot.canvas_host.validation`)

```python
# 文件: src/lurkbot/canvas_host/validation.py

from typing import Literal, Any, Union
from pydantic import BaseModel, ValidationError
import json

class SurfaceUpdateMessage(BaseModel):
    """Surface 更新消息"""
    type: Literal["surfaceUpdate"]
    surfaceId: str
    surface: dict

class DataModelUpdateMessage(BaseModel):
    """数据模型更新消息"""
    type: Literal["dataModelUpdate"]
    path: str
    value: Any

class DeleteSurfaceMessage(BaseModel):
    """删除 Surface 消息"""
    type: Literal["deleteSurface"]
    surfaceId: str

class BeginRenderingMessage(BaseModel):
    """开始渲染消息"""
    type: Literal["beginRendering"]
    sessionId: str | None = None

class ResetMessage(BaseModel):
    """重置消息"""
    type: Literal["reset"]

# A2UI 消息联合类型
A2UIMessage = Union[
    SurfaceUpdateMessage,
    DataModelUpdateMessage,
    DeleteSurfaceMessage,
    BeginRenderingMessage,
    ResetMessage,
]

def parse_jsonl(jsonl: str) -> list[dict]:
    """
    解析 JSONL 字符串为消息列表

    对标 MoltBot src/cli/nodes-cli/a2ui-jsonl.ts
    """
    messages = []
    for line in jsonl.strip().split('\n'):
        line = line.strip()
        if line:
            try:
                messages.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return messages

def validate_messages(messages: list[dict]) -> bool:
    """
    验证 A2UI 消息格式

    对标 MoltBot src/canvas-host/a2ui.ts
    """
    for msg in messages:
        msg_type = msg.get("type")
        try:
            if msg_type == "surfaceUpdate":
                SurfaceUpdateMessage(**msg)
            elif msg_type == "dataModelUpdate":
                DataModelUpdateMessage(**msg)
            elif msg_type == "deleteSurface":
                DeleteSurfaceMessage(**msg)
            elif msg_type == "beginRendering":
                BeginRenderingMessage(**msg)
            elif msg_type == "reset":
                ResetMessage(**msg)
            else:
                return False
        except ValidationError:
            return False
    return True

def validate_surface(surface: dict) -> bool:
    """验证 Surface 组件结构"""
    required_types = {
        "text", "image", "button", "input", "link",
        "container", "card", "list", "grid", "tabs",
        "form", "select", "checkbox", "slider", "toggle",
    }
    surface_type = surface.get("type")
    return surface_type in required_types
```

#### 4.2.3 Canvas Tool (`lurkbot.tools.builtin.canvas`)

```python
# 文件: src/lurkbot/tools/builtin/canvas.py

from pydantic import BaseModel, Field
from typing import Literal
from pydantic_ai import RunContext

class CanvasToolParams(BaseModel):
    """Canvas 工具参数"""
    action: Literal["present", "hide", "navigate", "eval", "a2ui_push", "a2ui_reset"] = Field(
        description="要执行的操作"
    )
    content: str | None = Field(
        default=None,
        description="展示的内容 (用于 present action)"
    )
    content_type: Literal["html", "markdown", "url"] | None = Field(
        default=None,
        description="内容类型 (用于 present action)"
    )
    url: str | None = Field(
        default=None,
        description="导航 URL (用于 navigate action)"
    )
    script: str | None = Field(
        default=None,
        description="JavaScript 脚本 (用于 eval action)"
    )
    jsonl: str | None = Field(
        default=None,
        description="A2UI JSONL 消息 (用于 a2ui_push action)"
    )
    title: str | None = Field(
        default=None,
        description="画布标题"
    )
    fullscreen: bool = Field(
        default=False,
        description="是否全屏显示"
    )

async def canvas_tool(
    ctx: RunContext["AgentDependencies"],
    params: CanvasToolParams,
) -> dict:
    """
    Canvas 工具 - 管理可视化画布和 A2UI 界面

    对标 MoltBot src/agents/tools/canvas-tool.ts

    Actions:
    - present: 展示 HTML/Markdown/URL 内容
    - hide: 隐藏画布
    - navigate: 导航到 URL
    - eval: 执行 JavaScript (沙箱化)
    - a2ui_push: 推送 A2UI JSONL 消息
    - a2ui_reset: 重置 A2UI 画布
    """
    from lurkbot.canvas_host.server import canvas_host
    from lurkbot.canvas_host.validation import parse_jsonl, validate_messages

    session_id = ctx.deps.context.session_id

    if params.action == "a2ui_push":
        if not params.jsonl:
            return {"success": False, "error": "jsonl is required for a2ui_push"}

        messages = parse_jsonl(params.jsonl)
        if not validate_messages(messages):
            return {"success": False, "error": "Invalid A2UI JSONL format"}

        await canvas_host.broadcast(session_id, messages)
        return {"success": True, "pushed": len(messages)}

    elif params.action == "a2ui_reset":
        await canvas_host.reset(session_id)
        return {"success": True, "message": "Canvas reset"}

    elif params.action == "present":
        if not params.content:
            return {"success": False, "error": "content is required for present"}

        # 构建 surface 消息
        surface = {
            "type": "container",
            "children": [{"type": "text", "content": params.content}]
        }
        if params.content_type == "html":
            surface = {"type": "html", "content": params.content}
        elif params.content_type == "url":
            surface = {"type": "iframe", "src": params.content}

        message = {
            "type": "surfaceUpdate",
            "surfaceId": "main",
            "surface": surface,
        }
        await canvas_host.broadcast(session_id, [message])
        return {"success": True}

    elif params.action == "hide":
        message = {"type": "deleteSurface", "surfaceId": "main"}
        await canvas_host.broadcast(session_id, [message])
        return {"success": True}

    elif params.action == "navigate":
        if not params.url:
            return {"success": False, "error": "url is required for navigate"}

        surface = {"type": "iframe", "src": params.url}
        message = {
            "type": "surfaceUpdate",
            "surfaceId": "main",
            "surface": surface,
        }
        await canvas_host.broadcast(session_id, [message])
        return {"success": True, "navigated_to": params.url}

    elif params.action == "eval":
        # 注意: 沙箱化执行，仅支持有限操作
        return {
            "success": False,
            "error": "eval action requires client-side execution (not implemented)"
        }

    return {"success": False, "error": f"Unknown action: {params.action}"}

# 工具定义（用于注册到 Agent）
CANVAS_TOOL_DEFINITION = {
    "name": "canvas",
    "description": """Canvas 工具 - 管理可视化画布和 A2UI 界面。

可用 Actions:
- a2ui_push: 推送 A2UI JSONL 消息创建/更新 UI
- a2ui_reset: 重置 A2UI 画布
- present: 展示 HTML/Markdown/URL 内容
- hide: 隐藏画布
- navigate: 导航到指定 URL

A2UI JSONL 示例:
{"type":"surfaceUpdate","surfaceId":"main","surface":{"type":"text","content":"Hello!"}}
{"type":"dataModelUpdate","path":"user.name","value":"Alice"}
""",
    "function": canvas_tool,
    "params_type": CanvasToolParams,
}
```

#### 4.2.4 系统提示词扩展

在 `system_prompt.py` 的 23 节结构中添加 A2UI 相关章节：

```python
# 在 build_system_prompt() 中添加（位于 ## Messaging 之后）

# 14.5 ## Canvas & A2UI - 有 canvas 工具时
if prompt_mode != "minimal" and _has_canvas_tool(tools):
    lines.append("## Canvas & A2UI")
    lines.append("")
    lines.append("When the user requests visual output (charts, forms, dashboards):")
    lines.append("1. Use the `canvas` tool with `action: \"a2ui_push\"`")
    lines.append("2. Generate valid A2UI JSONL messages")
    lines.append("3. Each line must be a complete JSON object")
    lines.append("4. Use `surfaceUpdate` to create/update UI components")
    lines.append("5. Use `dataModelUpdate` for data binding")
    lines.append("6. Remember: A2UI is declarative - describe WHAT to show, not HOW")
    lines.append("")
    lines.append("A2UI Component Quick Reference:")
    lines.append("- `text`: Display text content")
    lines.append("- `button`: Interactive button with callback")
    lines.append("- `input`: Text input field")
    lines.append("- `container`: Layout container (row/column)")
    lines.append("- `card`: Card with title and content")
    lines.append("- `list`: Render a list of items")
    lines.append("- `image`: Display images")
    lines.append("")

def _has_canvas_tool(tools: list | None) -> bool:
    if not tools:
        return False
    return any(t.name == "canvas" for t in tools)
```

### 4.3 工具策略集成

在 `policy.py` 中更新工具分组：

```python
# 更新 TOOL_GROUPS
TOOL_GROUPS: dict[str, list[str]] = {
    # ... 现有分组
    "group:ui": ["browser", "canvas"],  # canvas 包含 A2UI 功能
}

# canvas 工具默认在 full 和 coding profile 中可用
TOOL_PROFILES[ToolProfile.FULL]["allow"].append("canvas")
TOOL_PROFILES[ToolProfile.CODING]["allow"].append("canvas")
```

### 4.4 文件清单

```
src/lurkbot/
├── canvas_host/
│   ├── __init__.py
│   ├── server.py           # Canvas Host 服务 + WebSocket
│   └── validation.py       # A2UI JSONL 验证
└── tools/
    └── builtin/
        └── canvas.py       # Canvas 工具定义
```

---

## 五、Auto-Reply 自动回复系统设计

### 5.1 系统概述

Auto-Reply 是 LurkBot 的消息处理核心，负责：
- 消息接收和分发
- 指令解析和处理
- 流式响应递送
- 队列管理

> **对标**: MoltBot `src/auto-reply/` (23,000+ 行 TypeScript 代码)

### 5.2 模块结构

```
src/lurkbot/auto_reply/
├── __init__.py
├── tokens.py                 # 回复令牌（HEARTBEAT_OK, NO_REPLY）
├── directives.py             # 指令提取
├── envelope.py               # 消息包装结构
├── status.py                 # 状态管理
├── inbound_debounce.py       # 消息防抖
├── queue/
│   ├── __init__.py
│   ├── directive.py          # 队列指令
│   ├── types.py              # 队列类型
│   ├── enqueue.py            # 入队逻辑
│   ├── drain.py              # 出队逻辑
│   ├── state.py              # 状态管理
│   └── cleanup.py            # 清理逻辑
├── reply_tags.py             # [[reply_to_current]] 标签
├── reply_directives.py       # 回复指令
├── agent_runner.py           # Agent 运行时
└── deliver.py                # 回复递送
```

### 5.3 Reply Directives 指令系统

```python
# 文件: src/lurkbot/auto_reply/directives.py

from typing import Literal, TypedDict
from dataclasses import dataclass
import re

# 思维级别
ThinkLevel = Literal["off", "low", "medium", "high"]
# 用法: /think:high 或 /t:medium

# 冗余级别
VerboseLevel = Literal["off", "low", "high"]
# 用法: /verbose:high 或 /v:low

# 推理级别
ReasoningLevel = Literal["off", "on", "stream"]
# 用法: /reasoning

# 提权级别
ElevatedLevel = Literal["off", "ask", "on", "full"]
# 用法: /elevated:on

@dataclass
class DirectiveResult:
    cleaned: str
    level: str | None
    has_directive: bool

def extract_level_directive(
    body: str,
    names: list[str],
    normalize_fn: callable,
) -> DirectiveResult:
    """
    通用指令提取函数

    对标 MoltBot extractLevelDirective()

    匹配模式: /directive_name [: | space] optional_level
    支持: /think, /think:medium, /think medium
    """
    pattern = rf"/({'|'.join(names)})\s*[:\s]?\s*(\w+)?"
    match = re.search(pattern, body, re.IGNORECASE)

    if not match:
        return DirectiveResult(cleaned=body, level=None, has_directive=False)

    raw_level = match.group(2)
    level = normalize_fn(raw_level) if raw_level else normalize_fn("default")
    cleaned = re.sub(pattern, "", body).strip()

    return DirectiveResult(cleaned=cleaned, level=level, has_directive=True)

def extract_think_directive(body: str) -> DirectiveResult:
    """提取思维级别指令"""
    def normalize(level: str) -> ThinkLevel:
        mapping = {
            "off": "off", "0": "off", "none": "off",
            "low": "low", "1": "low", "l": "low",
            "medium": "medium", "2": "medium", "m": "medium", "default": "medium",
            "high": "high", "3": "high", "h": "high",
        }
        return mapping.get(level.lower(), "medium")

    return extract_level_directive(body, ["think", "t"], normalize)

def extract_verbose_directive(body: str) -> DirectiveResult:
    """提取冗余级别指令"""
    def normalize(level: str) -> VerboseLevel:
        mapping = {
            "off": "off", "0": "off", "none": "off", "default": "off",
            "low": "low", "1": "low", "l": "low",
            "high": "high", "2": "high", "h": "high",
        }
        return mapping.get(level.lower(), "off")

    return extract_level_directive(body, ["verbose", "v"], normalize)
```

### 5.4 Queue 队列处理机制

```python
# 文件: src/lurkbot/auto_reply/queue/types.py

from typing import Literal, TypedDict
from dataclasses import dataclass
from datetime import datetime

# 队列模式
QueueMode = Literal[
    "steer",           # 引导模式：等待用户确认
    "followup",        # 跟进模式：主 Agent 后自动执行
    "collect",         # 收集模式：批处理多条消息
    "steer-backlog",   # 引导+积压管理
    "interrupt",       # 中断当前执行
    "queue",           # 标准 FIFO
]

# 丢弃策略
QueueDropPolicy = Literal[
    "old",        # 丢弃最旧
    "new",        # 丢弃最新
    "summarize",  # 总结超出的消息
]

@dataclass
class QueueDirective:
    cleaned: str
    queue_mode: QueueMode | None
    queue_reset: bool
    debounce_ms: int | None
    cap: int | None
    drop_policy: QueueDropPolicy | None

@dataclass
class QueueItem:
    id: str
    session_key: str
    content: str
    priority: int
    created_at: datetime
    metadata: dict
```

### 5.5 流式响应递送

```python
# 文件: src/lurkbot/auto_reply/deliver.py

from typing import AsyncIterator, Literal
import asyncio

# 三层流式架构
# Layer 1: Agent Runtime Stream - agent.run_stream()
# Layer 2: Event Stream - partial_reply, tool_result, reasoning_stream
# Layer 3: Block Reply Stream - 分块递送

ChunkMode = Literal["length", "paragraph", "sentence"]

async def deliver_block_reply(
    reply_result: "ReplyPayload",
    session_key: str,
    text_limit: int = 4096,       # WhatsApp: 4096
    chunk_mode: ChunkMode = "length",
):
    """
    Block Reply 递送

    对标 MoltBot deliverWebReply()
    """
    # 1. Markdown 表格转换
    converted = convert_markdown_tables(reply_result.text)

    # 2. 分块
    chunks = chunk_markdown_text(converted, text_limit, chunk_mode)

    # 3. 递送（带重试）
    for chunk in chunks:
        await send_with_retry(chunk, "text")

    # 4. 媒体递送
    for media_url in reply_result.media_list:
        media = await load_media(media_url)
        await send_media(media)

def chunk_markdown_text(
    text: str,
    max_length: int,
    mode: ChunkMode,
) -> list[str]:
    """按指定模式分块"""
    if mode == "length":
        return [text[i:i+max_length] for i in range(0, len(text), max_length)]
    elif mode == "paragraph":
        return _chunk_by_paragraph(text, max_length)
    elif mode == "sentence":
        return _chunk_by_sentence(text, max_length)
```

### 5.6 Silent Reply 机制

```python
# 文件: src/lurkbot/auto_reply/tokens.py

# 特殊令牌
SILENT_REPLY_TOKEN = "NO_REPLY"
HEARTBEAT_TOKEN = "HEARTBEAT_OK"

def is_silent_reply_text(text: str | None) -> bool:
    """
    检测静默回复

    "/NO_REPLY" 或文本结尾有 "NO_REPLY"
    用于避免重复回复（已通过 message 工具发送）
    """
    if not text:
        return False
    return text.strip().endswith(SILENT_REPLY_TOKEN) or text.startswith(f"/{SILENT_REPLY_TOKEN}")

def is_heartbeat_ok(text: str | None) -> bool:
    """检测心跳确认"""
    if not text:
        return False
    return HEARTBEAT_TOKEN in text
```

---

## 六、Routing 消息路由系统设计

### 6.1 系统概述

Routing 系统负责消息的路由决策和分发，包括会话隔离和广播支持。

> **对标**: MoltBot `src/routing/`

### 6.2 模块结构

```
src/lurkbot/routing/
├── __init__.py
├── router.py              # 路由决策
├── session_key.py         # Session Key 生成
├── dispatcher.py          # 消息分发
├── broadcast.py           # 广播支持
└── bindings.py            # 绑定配置
```

### 6.3 路由决策流程（6 层）

```python
# 文件: src/lurkbot/routing/router.py

from dataclasses import dataclass
from typing import Literal

@dataclass
class RoutingContext:
    channel: str
    peer_kind: Literal["dm", "group", "guild", "team"]
    peer_id: str
    account_id: str | None = None
    guild_id: str | None = None   # Discord
    team_id: str | None = None    # Slack

def resolve_agent_for_message(
    ctx: RoutingContext,
    bindings: list["RoutingBinding"],
    agents: list["AgentConfig"],
) -> str:
    """
    路由决策流程（6 层）

    对标 MoltBot routing 决策逻辑

    层级顺序:
    1. 精确对等匹配 (bindings with peer.kind + peer.id)
    2. Guild 匹配 (Discord guildId)
    3. Team 匹配 (Slack teamId)
    4. 账户匹配 (channel accountId)
    5. 通道匹配 (任何该通道的账户)
    6. 默认 Agent (agents.list[].default 或首个)
    """
    # 1. 精确对等匹配
    for binding in bindings:
        if binding.match_peer(ctx.peer_kind, ctx.peer_id):
            return binding.agent_id

    # 2. Guild 匹配
    if ctx.guild_id:
        for binding in bindings:
            if binding.match_guild(ctx.guild_id):
                return binding.agent_id

    # 3. Team 匹配
    if ctx.team_id:
        for binding in bindings:
            if binding.match_team(ctx.team_id):
                return binding.agent_id

    # 4. 账户匹配
    if ctx.account_id:
        for binding in bindings:
            if binding.match_account(ctx.account_id):
                return binding.agent_id

    # 5. 通道匹配
    for binding in bindings:
        if binding.match_channel(ctx.channel):
            return binding.agent_id

    # 6. 默认 Agent
    for agent in agents:
        if agent.default:
            return agent.id

    return agents[0].id if agents else "main"
```

### 6.4 Session Key 会话隔离

```python
# 文件: src/lurkbot/routing/session_key.py

def build_session_key(
    agent_id: str,
    channel: str,
    session_type: str,
    peer_id: str | None = None,
    guild_id: str | None = None,
    channel_id: str | None = None,
    thread_id: str | None = None,
    topic_id: str | None = None,
) -> str:
    """
    构建 Session Key

    格式示例:
    - 直接消息 → "agent:main:main"
    - Telegram 群组 → "agent:main:telegram:group:-1001234567890"
    - Discord → "agent:main:discord:guild:123456:channel:789"
    - Slack 线程 → "agent:main:slack:channel:C123:thread:1234567890.0001"
    - Telegram Topic → "agent:main:telegram:group:-100123:topic:42"
    """
    parts = [f"agent:{agent_id}"]

    if session_type == "main":
        parts.append("main")
    elif session_type == "group":
        parts.extend([channel, "group", peer_id])
    elif session_type == "guild":
        parts.extend([channel, "guild", guild_id])
        if channel_id:
            parts.extend(["channel", channel_id])
    elif session_type == "thread":
        parts.extend([channel, "channel", channel_id, "thread", thread_id])
    elif session_type == "topic":
        parts.extend([channel, "group", peer_id, "topic", topic_id])

    return ":".join(filter(None, parts))
```

### 6.5 Broadcast 广播

```python
# 文件: src/lurkbot/routing/broadcast.py

from dataclasses import dataclass
from typing import Literal

@dataclass
class BroadcastConfig:
    strategy: Literal["parallel", "sequential"] = "parallel"
    targets: dict[str, list[str]] = None  # peer_id -> [agent_ids]

async def broadcast_message(
    message: str,
    peer_id: str,
    config: BroadcastConfig,
):
    """
    广播消息到多个 Agent

    对标 MoltBot broadcast 配置
    """
    agent_ids = config.targets.get(peer_id, [])

    if config.strategy == "parallel":
        await asyncio.gather(*[
            send_to_agent(agent_id, message)
            for agent_id in agent_ids
        ])
    else:
        for agent_id in agent_ids:
            await send_to_agent(agent_id, message)
```

---

## 七、Daemon 守护进程系统设计

### 7.1 系统概述

Daemon 系统提供跨平台的后台服务管理：
- macOS: launchd (LaunchAgent)
- Linux: systemd (user service)
- Windows: schtasks (计划任务)

> **对标**: MoltBot `src/daemon/`

### 7.2 模块结构

```
src/lurkbot/daemon/
├── __init__.py
├── service.py            # 统一服务接口
├── constants.py          # 服务标签常量
├── paths.py              # 路径解析
├── launchd.py            # macOS 实现
├── systemd.py            # Linux 实现
├── schtasks.py           # Windows 实现
├── diagnostics.py        # 错误诊断
└── inspect.py            # 服务检查
```

### 7.3 统一服务接口

```python
# 文件: src/lurkbot/daemon/service.py

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal
import platform

@dataclass
class ServiceRuntime:
    status: Literal["running", "stopped", "unknown"]
    state: str | None = None
    sub_state: str | None = None
    pid: int | None = None
    last_exit_status: int | None = None
    last_exit_reason: str | None = None

@dataclass
class ServiceInstallArgs:
    port: int = 18789
    bind: str = "loopback"
    profile: str | None = None
    workspace: str | None = None

class GatewayService(ABC):
    """统一服务接口"""

    @property
    @abstractmethod
    def label(self) -> str:
        """服务标签"""
        pass

    @abstractmethod
    async def install(self, args: ServiceInstallArgs) -> None:
        """安装服务"""
        pass

    @abstractmethod
    async def uninstall(self) -> None:
        """卸载服务"""
        pass

    @abstractmethod
    async def start(self) -> None:
        """启动服务"""
        pass

    @abstractmethod
    async def stop(self) -> None:
        """停止服务"""
        pass

    @abstractmethod
    async def restart(self) -> None:
        """重启服务"""
        pass

    @abstractmethod
    async def is_loaded(self) -> bool:
        """检查是否已加载"""
        pass

    @abstractmethod
    async def get_runtime(self) -> ServiceRuntime:
        """获取运行时状态"""
        pass

def resolve_gateway_service() -> GatewayService:
    """
    根据平台选择服务实现

    对标 MoltBot resolveGatewayService()
    """
    system = platform.system()
    if system == "Darwin":
        from .launchd import LaunchdService
        return LaunchdService()
    elif system == "Linux":
        from .systemd import SystemdService
        return SystemdService()
    elif system == "Windows":
        from .schtasks import SchtasksService
        return SchtasksService()
    else:
        raise RuntimeError(f"Unsupported platform: {system}")
```

### 7.4 macOS Launchd 实现

```python
# 文件: src/lurkbot/daemon/launchd.py

import plistlib
from pathlib import Path

GATEWAY_LAUNCH_AGENT_LABEL = "bot.lurk.gateway"

class LaunchdService(GatewayService):

    def __init__(self, profile: str | None = None):
        self.profile = profile
        self._label = self._resolve_label(profile)

    def _resolve_label(self, profile: str | None) -> str:
        """解析服务标签（支持多实例）"""
        if profile:
            return f"bot.lurk.{profile}"
        return GATEWAY_LAUNCH_AGENT_LABEL

    @property
    def label(self) -> str:
        return self._label

    @property
    def plist_path(self) -> Path:
        return Path.home() / "Library" / "LaunchAgents" / f"{self._label}.plist"

    async def install(self, args: ServiceInstallArgs) -> None:
        """安装 LaunchAgent"""
        plist = {
            "Label": self._label,
            "RunAtLoad": True,
            "KeepAlive": True,
            "ProgramArguments": [
                "/usr/local/bin/lurkbot",
                "gateway", "run",
                "--port", str(args.port),
                "--bind", args.bind,
            ],
            "StandardOutPath": str(self._log_path / "gateway.log"),
            "StandardErrorPath": str(self._log_path / "gateway.err.log"),
        }

        self.plist_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.plist_path, "wb") as f:
            plistlib.dump(plist, f)

        await self._launchctl("load", str(self.plist_path))

    async def uninstall(self) -> None:
        """卸载 LaunchAgent"""
        await self._launchctl("unload", str(self.plist_path))
        self.plist_path.unlink(missing_ok=True)
```

### 7.5 Linux Systemd 实现

```python
# 文件: src/lurkbot/daemon/systemd.py

from pathlib import Path

SYSTEMD_SERVICE_NAME = "lurkbot-gateway"

class SystemdService(GatewayService):

    def __init__(self, profile: str | None = None):
        self.profile = profile
        self._name = self._resolve_name(profile)

    def _resolve_name(self, profile: str | None) -> str:
        if profile:
            return f"{SYSTEMD_SERVICE_NAME}-{profile}"
        return SYSTEMD_SERVICE_NAME

    @property
    def label(self) -> str:
        return self._name

    @property
    def unit_path(self) -> Path:
        return Path.home() / ".config" / "systemd" / "user" / f"{self._name}.service"

    async def install(self, args: ServiceInstallArgs) -> None:
        """安装 Systemd User Service"""
        unit_content = f"""[Unit]
Description=LurkBot Gateway
After=network-online.target

[Service]
ExecStart=/usr/local/bin/lurkbot gateway run --port {args.port} --bind {args.bind}
WorkingDirectory={Path.home() / ".lurkbot"}
Restart=always
RestartSec=5
KillMode=process

[Install]
WantedBy=default.target
"""

        self.unit_path.parent.mkdir(parents=True, exist_ok=True)
        self.unit_path.write_text(unit_content)

        await self._systemctl("--user", "daemon-reload")
        await self._systemctl("--user", "enable", self._name)
        await self._enable_linger()
```

---

## 八、Hooks 扩展系统设计

### 8.1 系统概述

Hooks 是事件驱动的扩展系统，允许在特定事件发生时执行自定义逻辑。

> **对标**: MoltBot `src/hooks/`

### 8.2 模块结构

```
src/lurkbot/hooks/
├── __init__.py
├── registry.py           # 钩子注册
├── events.py             # 事件类型
├── discovery.py          # 钩子发现
├── loader.py             # 钩子加载
└── bundled/              # 预装钩子
    ├── __init__.py
    ├── session_memory.py # /new 时保存会话快照
    └── command_logger.py # 命令事件日志
```

### 8.3 钩子事件类型

```python
# 文件: src/lurkbot/hooks/events.py

from typing import Literal, TypedDict
from dataclasses import dataclass, field
from datetime import datetime

InternalHookEventType = Literal["command", "session", "agent", "gateway"]

# 事件示例:
# "command:new"        # /new 命令
# "command:reset"      # /reset 命令
# "session:*"          # 会话事件
# "agent:bootstrap"    # Agent 启动
# "gateway:startup"    # Gateway 启动

@dataclass
class InternalHookEvent:
    type: InternalHookEventType
    action: str
    session_key: str
    context: dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    messages: list[str] = field(default_factory=list)

    @property
    def event_name(self) -> str:
        return f"{self.type}:{self.action}"
```

### 8.4 钩子处理器

```python
# 文件: src/lurkbot/hooks/registry.py

from typing import Callable, Awaitable
from collections import defaultdict

HookHandler = Callable[["InternalHookEvent"], Awaitable[None]]

class HookRegistry:
    """钩子注册表"""

    def __init__(self):
        self._handlers: dict[str, list[HookHandler]] = defaultdict(list)

    def register(self, event_name: str, handler: HookHandler) -> None:
        """
        注册钩子

        对标 MoltBot registerInternalHook()
        """
        self._handlers[event_name].append(handler)

    async def trigger(self, event: "InternalHookEvent") -> None:
        """
        触发钩子

        对标 MoltBot triggerInternalHook()
        """
        # 精确匹配
        for handler in self._handlers.get(event.event_name, []):
            await handler(event)

        # 通配符匹配
        wildcard_key = f"{event.type}:*"
        for handler in self._handlers.get(wildcard_key, []):
            await handler(event)

# 全局实例
hook_registry = HookRegistry()

def register_internal_hook(event_name: str):
    """装饰器：注册钩子"""
    def decorator(func: HookHandler):
        hook_registry.register(event_name, func)
        return func
    return decorator
```

### 8.5 钩子发现机制

```python
# 文件: src/lurkbot/hooks/discovery.py

from pathlib import Path
import yaml

# 优先级顺序:
# 1. <workspace>/hooks/           # 最高优先级
# 2. ~/.lurkbot/hooks/            # 用户安装
# 3. <lurkbot>/hooks/bundled/     # 预装

def discover_hooks(workspace_dir: str | None = None) -> list["HookInfo"]:
    """
    发现所有可用钩子

    对标 MoltBot hook 发现机制
    """
    hooks = []
    search_paths = []

    if workspace_dir:
        search_paths.append(Path(workspace_dir) / "hooks")

    search_paths.append(Path.home() / ".lurkbot" / "hooks")
    search_paths.append(Path(__file__).parent / "bundled")

    for path in search_paths:
        if path.exists():
            for hook_dir in path.iterdir():
                if hook_dir.is_dir():
                    hook_info = _load_hook_info(hook_dir)
                    if hook_info:
                        hooks.append(hook_info)

    return hooks

def _load_hook_info(hook_dir: Path) -> "HookInfo | None":
    """加载钩子信息"""
    hook_md = hook_dir / "HOOK.md"
    if not hook_md.exists():
        return None

    content = hook_md.read_text()
    # 解析 YAML frontmatter
    if content.startswith("---"):
        _, frontmatter, _ = content.split("---", 2)
        metadata = yaml.safe_load(frontmatter)
        return HookInfo(
            name=hook_dir.name,
            path=hook_dir,
            emoji=metadata.get("lurkbot", {}).get("emoji", "🪝"),
            events=metadata.get("lurkbot", {}).get("events", []),
            requires=metadata.get("lurkbot", {}).get("requires", {}),
        )
    return None
```

---

## 九、Security 安全审计系统设计

### 9.1 系统概述

Security 系统提供安全检查和审计功能，确保系统配置的安全性。

> **对标**: MoltBot `src/security/`

### 9.2 模块结构

```
src/lurkbot/security/
├── __init__.py
├── audit.py              # 审计功能
├── dm_policy.py          # DM 策略
├── model_check.py        # 模型安全检查
└── warnings.py           # 警告生成
```

### 9.3 审计范围

```python
# 文件: src/lurkbot/security/audit.py

from dataclasses import dataclass
from typing import Literal

@dataclass
class SecurityFinding:
    level: Literal["critical", "warning", "info"]
    message: str
    fix: str | None = None

async def audit_security(deep: bool = False) -> list[SecurityFinding]:
    """
    执行安全审计

    对标 MoltBot security audit
    """
    findings = []

    # A. Gateway 网络暴露检查
    findings.extend(await _audit_gateway_exposure())

    # B. DM 策略检查
    findings.extend(await _audit_dm_policy())

    # C. 模型安全检查
    if deep:
        findings.extend(await _audit_model_safety())

    return findings

async def _audit_gateway_exposure() -> list[SecurityFinding]:
    """
    Gateway 网络暴露检查

    绑定配置:
    - bind = "loopback" (127.0.0.1) → ✅ 安全
    - bind = "lan" (192.168.x.x) → ⚠️ 需认证
    - bind = "auto" (0.0.0.0) → ⚠️ 危险
    """
    findings = []
    config = load_gateway_config()

    is_exposed = config.bind in ("lan", "auto", "0.0.0.0")
    has_auth = config.auth and config.auth.mode in ("token", "password")

    if is_exposed and not has_auth:
        findings.append(SecurityFinding(
            level="critical",
            message="Gateway bound to network without authentication. Anyone on your network can fully control your agent.",
            fix="lurkbot config set gateway.bind loopback",
        ))

    return findings

async def _audit_dm_policy() -> list[SecurityFinding]:
    """
    DM 策略检查

    检查项:
    - 多发件人共享 main session → 建议隔离
    """
    findings = []
    config = load_dm_policy()

    if config.dm_scope == "main" and config.is_multi_user:
        findings.append(SecurityFinding(
            level="warning",
            message="Multiple senders share the main session. Consider isolating sessions.",
            fix='lurkbot config set session.dmScope "per-channel-peer"',
        ))

    return findings
```

### 9.4 CLI 命令

```python
# 文件: src/lurkbot/cli/security.py

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer()
console = Console()

@app.command()
def audit(
    deep: bool = typer.Option(False, "--deep", help="执行深度审计"),
    fix: bool = typer.Option(False, "--fix", help="自动修复"),
):
    """
    执行安全审计

    用法:
    - lurkbot security audit          # 标准审计
    - lurkbot security audit --deep   # 深度审计
    - lurkbot security audit --fix    # 自动修复
    """
    import asyncio
    from ..security.audit import audit_security, apply_fixes

    findings = asyncio.run(audit_security(deep=deep))

    if not findings:
        console.print("[green]✓[/green] No security issues found")
        return

    # 显示发现
    for finding in findings:
        icon = {"critical": "🔴", "warning": "🟡", "info": "🔵"}[finding.level]
        console.print(f"\n{icon} {finding.level.upper()}: {finding.message}")
        if finding.fix:
            console.print(f"   Fix: {finding.fix}")

    if fix:
        asyncio.run(apply_fixes(findings))
```

---

## 十、Infra 基础设施设计

### 10.1 系统概述

Infra 模块包含 8 个核心基础设施子系统。

> **对标**: MoltBot `src/infra/`

### 10.2 模块结构

```
src/lurkbot/infra/
├── __init__.py
├── errors.py                 # 错误类型
├── retry.py                  # 重试策略
├── system_events/            # 系统事件队列
│   ├── __init__.py
│   ├── audio.py              # 音频输入事件
│   ├── clipboard.py          # 剪贴板事件
│   └── file_watch.py         # 文件变化事件
├── system_presence/          # 设备在线状态
│   └── presence.py
├── tailscale/                # Tailscale VPN 集成
│   └── client.py
├── ssh_tunnel/               # SSH 隧道
│   └── manager.py
├── bonjour/                  # mDNS 服务发现
│   └── discovery.py
├── device_pairing/           # PKI 设备配对
│   ├── keypair.py
│   ├── exchange.py
│   └── trust.py
├── exec_approvals/           # 执行审批系统
│   └── approver.py
└── voicewake/                # 语音唤醒
    └── detector.py
```

### 10.3 系统事件队列

```python
# 文件: src/lurkbot/infra/system_events/__init__.py

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime

MAX_EVENTS_PER_SESSION = 20

@dataclass
class SystemEvent:
    text: str
    ts: datetime

class SystemEventQueue:
    """
    轻量级内存事件总线

    对标 MoltBot system-events.ts
    """

    def __init__(self):
        self._queues: dict[str, list[SystemEvent]] = defaultdict(list)
        self._last_event: dict[str, str] = {}

    def enqueue(self, session_key: str, text: str) -> None:
        """入队事件（自动去重连续相同事件）"""
        if self._last_event.get(session_key) == text:
            return

        self._last_event[session_key] = text
        queue = self._queues[session_key]
        queue.append(SystemEvent(text=text, ts=datetime.now()))

        # 保持最多 20 条
        if len(queue) > MAX_EVENTS_PER_SESSION:
            self._queues[session_key] = queue[-MAX_EVENTS_PER_SESSION:]

    def drain(self, session_key: str) -> list[SystemEvent]:
        """出队所有事件"""
        events = self._queues.pop(session_key, [])
        self._last_event.pop(session_key, None)
        return events

# 全局实例
system_event_queue = SystemEventQueue()
```

### 10.4 系统存在感

```python
# 文件: src/lurkbot/infra/system_presence/presence.py

from dataclasses import dataclass
from typing import Literal
from datetime import datetime, timedelta
from cachetools import TTLCache

@dataclass
class SystemPresence:
    host: str | None = None
    ip: str | None = None
    version: str | None = None
    platform: str | None = None
    mode: Literal["gateway", "node"] | None = None
    reason: Literal["self", "discovered", "imported"] | None = None
    roles: list[str] | None = None
    scopes: list[str] | None = None

# 5 分钟 TTL，最多 200 节点
_presence_cache = TTLCache(maxsize=200, ttl=300)

def update_system_presence(node_id: str, presence: SystemPresence) -> None:
    """更新节点存在感"""
    _presence_cache[node_id] = presence

def list_system_presence() -> dict[str, SystemPresence]:
    """列出所有在线节点"""
    return dict(_presence_cache)
```

### 10.5 Tailscale 集成

```python
# 文件: src/lurkbot/infra/tailscale/client.py

import subprocess
import shutil
from pathlib import Path
from functools import lru_cache

@lru_cache
def find_tailscale_binary() -> str | None:
    """
    查找 Tailscale 二进制文件（4 层策略）

    1. which tailscale
    2. macOS /Applications/Tailscale.app
    3. find /usr/local
    4. locate tailscale
    """
    # 1. which
    result = shutil.which("tailscale")
    if result:
        return result

    # 2. macOS app
    macos_path = Path("/Applications/Tailscale.app/Contents/MacOS/Tailscale")
    if macos_path.exists():
        return str(macos_path)

    # 3-4. find/locate (慢，作为后备)
    return None

async def get_tailnet_hostname() -> str | None:
    """获取 Tailnet 主机名"""
    binary = find_tailscale_binary()
    if not binary:
        return None

    result = subprocess.run(
        [binary, "status", "--json"],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        import json
        data = json.loads(result.stdout)
        return data.get("Self", {}).get("DNSName")
    return None
```

---

## 十一、Media Understanding 设计

### 11.1 系统概述

Media Understanding 系统在消息进入回复流水线前，自动理解和摘要化入站多媒体。

> **对标**: MoltBot `src/media-understanding/`

### 11.2 模块结构

```
src/lurkbot/media/
├── __init__.py
├── understand.py         # 核心理解逻辑
├── config.py             # 能力配置
└── providers/
    ├── __init__.py
    ├── openai.py
    ├── anthropic.py
    ├── gemini.py
    └── local.py          # 本地 CLI 降级
```

### 11.3 处理流程

```python
# 文件: src/lurkbot/media/understand.py

from dataclasses import dataclass
from typing import Literal

MediaType = Literal["image", "audio", "video", "document"]

@dataclass
class MediaUnderstandingResult:
    success: bool
    summary: str | None = None
    error: str | None = None
    provider_used: str | None = None

async def understand_media(
    media_url: str,
    media_type: MediaType,
    config: "MediaConfig",
) -> MediaUnderstandingResult:
    """
    理解多媒体内容

    流程:
    1. 按能力过滤提供商
    2. 选择第一个合格模型
    3. 执行理解任务
    4. 若失败 → 降级到下一个
    """
    for provider_config in config.get_providers_for_type(media_type):
        try:
            provider = get_provider(provider_config.provider)
            summary = await provider.understand(
                media_url=media_url,
                media_type=media_type,
                model=provider_config.model,
                max_chars=config.get_max_chars(media_type),
            )
            return MediaUnderstandingResult(
                success=True,
                summary=summary,
                provider_used=provider_config.provider,
            )
        except Exception as e:
            continue  # 降级到下一个

    return MediaUnderstandingResult(
        success=False,
        error="All providers failed",
    )
```

---

## 十二、Provider Usage 设计

### 12.1 系统概述

Provider Usage 系统追踪 API 使用量和成本，支持多提供商多窗口监控。

> **对标**: MoltBot `src/provider-usage/`

### 12.2 模块结构

```
src/lurkbot/usage/
├── __init__.py
├── monitor.py            # 使用量监控
├── format.py             # 格式化输出
└── providers/
    ├── __init__.py
    ├── anthropic.py
    ├── openai.py
    └── google.py
```

### 12.3 核心数据结构

```python
# 文件: src/lurkbot/usage/monitor.py

from dataclasses import dataclass
from typing import Literal

@dataclass
class UsageWindow:
    label: str           # "5h", "Week", "Sonnet"
    used_percent: float  # 0-100
    reset_at: int | None = None  # Unix 时间戳

@dataclass
class ProviderUsageSnapshot:
    provider: str
    display_name: str
    windows: list[UsageWindow]
    plan: str | None = None
    error: str | None = None

@dataclass
class UsageSummary:
    updated_at: int
    providers: list[ProviderUsageSnapshot]

async def fetch_all_usage() -> UsageSummary:
    """获取所有提供商使用量"""
    from datetime import datetime
    import asyncio

    providers = []
    tasks = [
        fetch_anthropic_usage(),
        fetch_openai_usage(),
        fetch_google_usage(),
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)
    for result in results:
        if isinstance(result, ProviderUsageSnapshot):
            providers.append(result)

    return UsageSummary(
        updated_at=int(datetime.now().timestamp() * 1000),
        providers=providers,
    )
```

---

## 十三、ACP 协议系统设计

### 13.1 系统概述

ACP（Agent Control Protocol）是 LurkBot 与 IDE 集成的标准协议实现。

> **对标**: MoltBot `src/acp/` (基于 @agentclientprotocol/sdk)

### 13.2 模块结构

```
src/lurkbot/acp/
├── __init__.py
├── server.py             # ACP 服务器
├── translator.py         # 协议翻译器
├── session.py            # 会话管理
├── event_mapper.py       # 事件映射
└── types.py              # 类型定义
```

### 13.3 架构设计

```
┌─────────────────────────────────────────┐
│         IDE / Client (stdIO)            │
└─────────────────┬───────────────────────┘
                  ↕ ndJSON 双向流
┌─────────────────────────────────────────┐
│    ACPServer (协议层)                    │
└─────────────────┬───────────────────────┘
                  ↕
┌─────────────────────────────────────────┐
│    ACPGatewayAgent (协议翻译器)         │
└─────────────────┬───────────────────────┘
                  ↕
┌─────────────────────────────────────────┐
│    GatewayClient (WebSocket)            │
└─────────────────┬───────────────────────┘
                  ↕
┌─────────────────────────────────────────┐
│    LurkBot Gateway                      │
└─────────────────────────────────────────┘
```

### 13.4 核心实现

```python
# 文件: src/lurkbot/acp/server.py

import sys
import json
from dataclasses import dataclass

@dataclass
class ACPSession:
    session_id: str
    session_key: str
    cwd: str
    created_at: int
    active_run_id: str | None = None

class ACPServer:
    """
    ACP 服务器 - ndJSON 双向流通信

    对标 MoltBot ACP server
    """

    def __init__(self):
        self._sessions: dict[str, ACPSession] = {}
        self._pending_prompts: dict[str, "PendingPrompt"] = {}

    async def run(self):
        """运行 ACP 服务器（stdin/stdout）"""
        async for line in self._read_lines():
            message = json.loads(line)
            response = await self._handle_message(message)
            if response:
                self._write_message(response)

    async def _handle_message(self, message: dict) -> dict | None:
        method = message.get("method")

        if method == "initialize":
            return self._handle_initialize(message)
        elif method == "prompt":
            return await self._handle_prompt(message)
        elif method == "cancel":
            return await self._handle_cancel(message)

        return None

    def _handle_initialize(self, message: dict) -> dict:
        """处理初始化请求"""
        return {
            "protocolVersion": "1.0",
            "agentCapabilities": {
                "loadSession": True,
                "promptCapabilities": {
                    "image": True,
                    "audio": False,
                    "embeddedContext": True,
                },
                "mcpCapabilities": {
                    "http": False,
                    "sse": False,
                },
            },
        }
```

---

## 十四、Browser 浏览器自动化设计

### 14.1 系统概述

Browser 模块提供完整的浏览器自动化能力，支持 Playwright 和 CDP。

> **对标**: MoltBot `src/browser/`

### 14.2 模块结构

```
src/lurkbot/browser/
├── __init__.py
├── server.py                 # 控制服务器
├── config.py                 # 配置解析
├── chrome.py                 # Chrome 启动管理
├── cdp.py                    # CDP 操作
├── playwright_session.py     # Playwright 会话
├── role_snapshot.py          # 角色快照
├── screenshot.py             # 截图处理
├── extension_relay.py        # 扩展中继
└── routes/
    ├── __init__.py
    ├── act.py                # /act 端点
    ├── navigate.py           # /navigate 端点
    └── screenshot.py         # /screenshot 端点
```

### 14.3 HTTP 路由

| 端点 | 方法 | 功能 |
|------|------|------|
| `/status` | GET | 浏览器状态 |
| `/tabs` | GET/POST/DELETE | 标签页管理 |
| `/act` | POST | 执行动作 |
| `/navigate` | POST | 导航 |
| `/screenshot` | POST | 截图 |
| `/snapshot/role` | POST | 角色快照 |
| `/evaluate` | POST | 执行 JavaScript |

### 14.4 核心实现

```python
# 文件: src/lurkbot/browser/server.py

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Literal

app = FastAPI()

BrowserAction = Literal[
    "click", "doubleClick",
    "type", "press",
    "drag", "hover",
    "fill", "selectOption",
    "wait",
]

class ActRequest(BaseModel):
    action: BrowserAction
    selector: str | None = None
    text: str | None = None
    key: str | None = None

@app.post("/act")
async def act(request: ActRequest):
    """执行浏览器动作"""
    from .playwright_session import get_page

    page = await get_page()

    if request.action == "click":
        await page.click(request.selector)
    elif request.action == "type":
        await page.type(request.selector, request.text)
    elif request.action == "press":
        await page.keyboard.press(request.key)
    # ... 更多动作

    return {"success": True}
```

---

## 十五、TUI 终端界面设计

### 15.1 系统概述

TUI 是交互式终端界面，提供实时聊天、命令处理和多 Agent 支持。

> **对标**: MoltBot `src/tui/`

### 15.2 模块结构

```
src/lurkbot/tui/
├── __init__.py
├── app.py                    # TUI 主应用
├── stream_assembler.py       # 流式响应组装
├── formatters.py             # 格式化
├── keybindings.py            # 快捷键定义
└── components/
    ├── __init__.py
    ├── chat_log.py           # 聊天窗口
    ├── thinking.py           # 思考指示器
    └── input_box.py          # 输入框
```

### 15.3 命令系统

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

### 15.4 流式响应组装

```python
# 文件: src/lurkbot/tui/stream_assembler.py

class TuiStreamAssembler:
    """
    分离 thinking 块和 content 块

    对标 MoltBot TuiStreamAssembler
    """

    def __init__(self):
        self._runs: dict[str, dict] = {}

    def ingest_delta(
        self,
        run_id: str,
        message: dict,
        show_thinking: bool,
    ) -> str:
        """
        处理增量消息

        返回新的显示文本
        """
        if run_id not in self._runs:
            self._runs[run_id] = {"thinking": "", "content": ""}

        run_state = self._runs[run_id]

        # 提取 thinking 块
        if "thinking" in message:
            run_state["thinking"] += message["thinking"]

        # 提取 content 块
        if "content" in message:
            run_state["content"] += message["content"]

        # 合成显示文本
        if show_thinking and run_state["thinking"]:
            return f"[thinking]\n{run_state['thinking']}\n[/thinking]\n\n{run_state['content']}"
        return run_state["content"]

    def finalize(self, run_id: str) -> str:
        """最终化并清理"""
        run_state = self._runs.pop(run_id, {"content": ""})
        return run_state["content"]
```

---

## 十六、TTS 语音合成设计

### 16.1 系统概述

TTS 是多 Provider 的文本转语音系统，支持 OpenAI、ElevenLabs、Edge TTS。

> **对标**: MoltBot `src/tts/`

### 16.2 模块结构

```
src/lurkbot/tts/
├── __init__.py
├── engine.py                 # TTS 引擎
├── directive_parser.py       # [[tts:...]] 解析
├── summarizer.py             # 长文本摘要
└── providers/
    ├── __init__.py
    ├── openai.py
    ├── elevenlabs.py
    └── edge.py               # 免费 Edge TTS
```

### 16.3 配置结构

```python
# 文件: src/lurkbot/tts/engine.py

from dataclasses import dataclass
from typing import Literal

@dataclass
class TTSConfig:
    auto: Literal["off", "always", "inbound", "tagged"] = "off"
    mode: Literal["delta", "final"] = "final"
    provider: Literal["openai", "elevenlabs", "edge"] = "openai"
    summary_model: str | None = None

@dataclass
class OpenAITTSConfig:
    api_key: str | None = None
    model: str = "tts-1"
    voice: str = "alloy"  # alloy|ash|coral|echo|fable|onyx|nova|sage|shimmer

@dataclass
class ElevenLabsTTSConfig:
    api_key: str | None = None
    voice_id: str = "21m00Tcm4TlvDq8ikWAM"
    model_id: str = "eleven_monolingual_v1"

@dataclass
class EdgeTTSConfig:
    enabled: bool = True
    voice: str = "en-US-AriaNeural"
    lang: str = "en-US"
```

### 16.4 Directive 系统

```python
# 文件: src/lurkbot/tts/directive_parser.py

import re
from dataclasses import dataclass

@dataclass
class TTSDirective:
    provider: str | None = None
    voice: str | None = None
    text: str | None = None

def parse_tts_directives(text: str) -> tuple[str, list[TTSDirective]]:
    """
    解析 TTS 指令

    格式:
    - [[tts:provider=openai voice=nova]]<文本>
    - [[tts:text]]<自定义音频文本>[[/tts:text]]
    """
    directives = []

    # 解析 provider/voice 指令
    pattern = r"\[\[tts:([^\]]+)\]\]"
    for match in re.finditer(pattern, text):
        attrs = match.group(1)
        directive = TTSDirective()

        for pair in attrs.split():
            if "=" in pair:
                key, value = pair.split("=", 1)
                setattr(directive, key, value)

        directives.append(directive)

    # 清理文本
    cleaned = re.sub(pattern, "", text)

    return cleaned, directives
```

---

## 十七、Wizard 配置向导设计

### 17.1 系统概述

Wizard 是分步式交互配置系统，用于初始化和配置 LurkBot。

> **对标**: MoltBot `src/wizard/`

### 17.2 模块结构

```
src/lurkbot/wizard/
├── __init__.py
├── onboarding.py             # 主流程
├── session.py                # 向导会话
├── prompts.py                # 交互提示
└── flows/
    ├── __init__.py
    ├── quickstart.py         # 快速开始
    ├── advanced.py           # 高级配置
    └── channel.py            # 通道配置
```

### 17.3 Onboarding 流程

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

### 17.4 Session 架构

```python
# 文件: src/lurkbot/wizard/session.py

from dataclasses import dataclass
from typing import Literal, Any
import asyncio

@dataclass
class WizardStep:
    id: str
    type: Literal["select", "multiselect", "text", "confirm"]
    prompt: str
    options: list[dict] | None = None
    default: Any = None

class WizardSession:
    """
    向导会话 - Promise-based 异步等待

    对标 MoltBot WizardSession
    """

    def __init__(self):
        self._steps: list[WizardStep] = []
        self._current_index = 0
        self._answers: dict[str, Any] = {}
        self._cancelled = False

    async def next(self) -> "WizardNextResult":
        """获取下一步"""
        if self._cancelled:
            return WizardNextResult(done=True, cancelled=True)

        if self._current_index >= len(self._steps):
            return WizardNextResult(done=True)

        step = self._steps[self._current_index]
        return WizardNextResult(done=False, step=step)

    async def answer(self, step_id: str, value: Any) -> None:
        """提交答案"""
        self._answers[step_id] = value
        self._current_index += 1

    def cancel(self) -> None:
        """取消向导"""
        self._cancelled = True
```

---

## 十八、功能完整性检查清单

### 18.1 核心功能检查（32 个模块对齐 MoltBot）

| # | MoltBot 功能 | LurkBot 设计 | 状态 |
|---|-------------|-------------|------|
| 1 | Pi SDK Agent Loop | PydanticAI Agent.run() | ✅ 设计完成 |
| 2 | 8 个 Bootstrap 文件 | agents/bootstrap.py | ✅ 已实现 |
| 3 | SUBAGENT_BOOTSTRAP_ALLOWLIST | agents/bootstrap.py | ✅ 已实现 |
| 4 | 23 节系统提示词 | agents/system_prompt.py | ✅ 已实现 |
| 5 | PromptMode (full/minimal/none) | agents/system_prompt.py | ✅ 已实现 |
| 6 | Runtime 行格式 | build_runtime_line() | ✅ 设计完成 |
| 7 | 22 原生工具 | tools/builtin/ | ⏳ 7/22 完成 |
| 8 | 九层工具策略 | tools/policy.py | ✅ 已实现 |
| 9 | 工具分组和配置文件 | tools/policy.py | ✅ 已实现 |
| 10 | 5 种会话类型 | sessions/ | ⏳ 设计完成 |
| 11 | 会话 Key 格式 | routing/session_key.py | ✅ 设计完成 |
| 12 | Subagent Spawn | agents/subagent/ | ⏳ 设计完成 |
| 13 | Subagent Announce Flow | agents/subagent/ | ⏳ 设计完成 |
| 14 | Heartbeat 系统 | autonomous/heartbeat/ | ⏳ 设计完成 |
| 15 | Heartbeat 事件 | autonomous/heartbeat/ | ⏳ 设计完成 |
| 16 | HEARTBEAT_OK Token | auto_reply/tokens.py | ✅ 设计完成 |
| 17 | Cron 调度类型 | autonomous/cron/ | ⏳ 设计完成 |
| 18 | Cron Payload 类型 | autonomous/cron/ | ⏳ 设计完成 |
| 19 | Auth Profile 轮换 | auth/profiles.py | ⏳ 设计完成 |
| 20 | 冷却计算 | auth/profiles.py | ⏳ 设计完成 |
| 21 | Context Compaction | agents/compaction.py | ⏳ 设计完成 |
| 22 | 自适应分块比例 | agents/compaction.py | ⏳ 设计完成 |
| 23 | 分阶段摘要 | agents/compaction.py | ⏳ 设计完成 |
| 24 | Human-in-the-Loop | DeferredToolRequests | ✅ 设计完成 |
| 25 | A2UI Canvas Host | canvas/ | ⏳ 设计完成 |
| 26 | A2UI JSONL 验证 | canvas/ | ⏳ 设计完成 |
| 27 | Canvas Tool | tools/builtin/canvas.py | ⏳ 设计完成 |
| 28 | Reply Directives | auto_reply/directives.py | ✅ 设计完成 |
| 29 | Queue 处理机制 | auto_reply/queue/ | ✅ 设计完成 |
| 30 | 流式响应递送 | auto_reply/deliver.py | ✅ 设计完成 |
| 31 | Daemon 守护进程 | daemon/ | ✅ 设计完成 |
| 32 | Media Understanding | media/ | ✅ 设计完成 |
| 33 | Provider Usage 监控 | usage/ | ✅ 设计完成 |
| 34 | Routing 消息路由 | routing/ | ✅ 设计完成 |
| 35 | Hooks 扩展系统 | hooks/ | ✅ 设计完成 |
| 36 | Security 安全审计 | security/ | ✅ 设计完成 |
| 37 | ACP 协议系统 | acp/ | ✅ 设计完成 |
| 38 | Browser 浏览器自动化 | browser/ | ✅ 设计完成 |
| 39 | TUI 终端界面 | tui/ | ✅ 设计完成 |
| 40 | TTS 语音合成 | tts/ | ✅ 设计完成 |
| 41 | Wizard 配置向导 | wizard/ | ✅ 设计完成 |
| 42 | Infra 系统事件 | infra/system_events/ | ✅ 设计完成 |
| 43 | Infra 设备状态 | infra/system_presence/ | ✅ 设计完成 |
| 44 | Infra Tailscale | infra/tailscale/ | ✅ 设计完成 |
| 45 | Infra SSH 隧道 | infra/ssh_tunnel/ | ⏳ 设计完成 |
| 46 | Infra mDNS 发现 | infra/bonjour/ | ⏳ 设计完成 |
| 47 | Infra 设备配对 | infra/device_pairing/ | ⏳ 设计完成 |
| 48 | Infra 执行审批 | infra/exec_approvals/ | ⏳ 设计完成 |
| 49 | Infra 语音唤醒 | infra/voicewake/ | ⏳ 设计完成 |
| 50 | Gateway 协议 | gateway/ | ⏳ 设计完成 |
| 51 | 技能系统 | skills/ | ⏳ 设计完成 |
| 52 | 插件系统 | plugins/ | ⏳ 设计完成 |
| 53 | 向量内存搜索 | memory/ | ⏳ 设计完成 |

### 18.2 状态图例

| 状态 | 含义 |
|------|------|
| ✅ 已实现 | 代码已完成并测试 |
| ✅ 设计完成 | 详细设计已完成，待实现 |
| ⏳ 设计完成 | 设计已完成，在实施队列中 |

---

## 十九、实施计划（28 阶段）

### 19.1 阶段划分（已完成 + 待完成）

| Phase | 模块 | 优先级 | 状态 | 依赖 |
|-------|------|--------|------|------|
| **Phase 1** | 项目重构 - 清理旧代码 | P0 | ✅ 完成 | - |
| **Phase 2** | PydanticAI 核心框架 | P0 | ✅ 完成 | Phase 1 |
| **Phase 3** | Bootstrap + 系统提示词 | P0 | ✅ 完成 | Phase 2 |
| **Phase 4** | 九层工具策略 | P0 | ✅ 完成 | Phase 2 |
| **Phase 5** | 剩余内置工具 (15个) | P0 | ⏳ 当前 | Phase 4 |
| **Phase 6** | 会话管理系统 | P0 | 待开始 | - |
| **Phase 7** | 子代理系统 | P0 | 待开始 | Phase 6 |
| **Phase 8** | 自主运行 (Heartbeat/Cron) | P0 | 待开始 | Phase 6 |
| **Phase 9** | Auto-Reply 系统 | P1 | 待开始 | - |
| **Phase 10** | Routing 消息路由 | P1 | 待开始 | Phase 6 |
| **Phase 11** | Auth Profiles | P1 | 待开始 | - |
| **Phase 12** | 上下文压缩 | P1 | 待开始 | - |
| **Phase 13** | Gateway 完整版 | P1 | 待开始 | Phase 6 |
| **Phase 14** | Hooks 系统 | P1 | 待开始 | - |
| **Phase 15** | Security 审计 | P1 | 待开始 | - |
| **Phase 16** | Infra 基础设施 | P1 | 待开始 | - |
| **Phase 17** | Daemon 守护进程 | P1 | 待开始 | - |
| **Phase 18** | 技能系统 | P1 | 待开始 | - |
| **Phase 19** | 插件系统 | P2 | 待开始 | Phase 14 |
| **Phase 20** | 向量内存 | P2 | 待开始 | - |
| **Phase 21** | Provider Usage | P2 | 待开始 | - |
| **Phase 22** | Media Understanding | P2 | 待开始 | - |
| **Phase 23** | A2UI Canvas | P2 | 待开始 | - |
| **Phase 24** | Browser 自动化 | P2 | 待开始 | - |
| **Phase 25** | TUI 终端界面 | P2 | 待开始 | - |
| **Phase 26** | TTS 语音合成 | P2 | 待开始 | - |
| **Phase 27** | ACP 协议 | P2 | 待开始 | Phase 13 |
| **Phase 28** | Wizard 向导 | P2 | 待开始 | - |

### 19.2 Phase 5: 剩余内置工具（当前阶段）

**目标**: 完成剩余 15 个内置工具

| 工具 | 功能 | 依赖 |
|------|------|------|
| sessions_list | 列出会话 | sessions/ |
| sessions_history | 获取历史 | sessions/ |
| sessions_send | 跨会话发送 | sessions/ |
| sessions_spawn | 生成子代理 | agents/subagent/ |
| session_status | 会话状态 | sessions/ |
| agents_list | 代理列表 | - |
| cron | 定时任务 | autonomous/cron/ |
| gateway | Gateway 通信 | gateway/ |
| browser | 浏览器控制 | browser/ |
| canvas | A2UI 画布 | canvas/ |
| image | 图像处理 | - |
| nodes | 节点管理 | infra/ |
| tts | 文本转语音 | tts/ |

### 19.3 Phase 6-8: P0 核心系统

#### Phase 6: 会话管理系统

```
src/lurkbot/sessions/
├── __init__.py
├── store.py              # JSONL 持久化
├── types.py              # 会话类型定义
├── routing.py            # 会话路由
└── manager.py            # 会话生命周期
```

#### Phase 7: 子代理系统

```
src/lurkbot/agents/subagent/
├── __init__.py
├── registry.py           # 子代理注册表
├── spawn.py              # Spawn 工作流
└── announce.py           # 结果汇报
```

#### Phase 8: 自主运行系统

```
src/lurkbot/autonomous/
├── __init__.py
├── heartbeat/
│   ├── runner.py         # 心跳运行器
│   ├── events.py         # 心跳事件
│   └── config.py         # 心跳配置
└── cron/
    ├── service.py        # Cron 服务
    ├── state.py          # 状态机
    └── types.py          # Job 类型
```

### 19.4 Phase 9-18: P1 核心功能

这些阶段的详细设计已在本文档的第五至十七章中完整描述。

### 19.5 Phase 19-28: P2 扩展功能

这些阶段的详细设计已在本文档的相应章节中完整描述。

### 19.6 实施优先级表

| 优先级 | 阶段范围 | 模块数 | 描述 |
|--------|----------|--------|------|
| **P0** | Phase 1-8 | 8 | 核心基础设施，必须首先完成 |
| **P1** | Phase 9-18 | 10 | 核心功能，完成后可独立运行 |
| **P2** | Phase 19-28 | 10 | 扩展功能，增强用户体验 |

---

## 二十、验证策略

### 20.1 单元测试

```bash
# 核心模块测试
pytest tests/test_bootstrap.py -xvs
pytest tests/test_system_prompt.py -xvs
pytest tests/test_tool_policy.py -xvs
pytest tests/test_compaction.py -xvs
pytest tests/test_sessions.py -xvs
pytest tests/test_subagent.py -xvs
pytest tests/test_heartbeat.py -xvs
pytest tests/test_cron.py -xvs
pytest tests/test_auth_profiles.py -xvs

# 新模块测试
pytest tests/test_auto_reply.py -xvs
pytest tests/test_routing.py -xvs
pytest tests/test_hooks.py -xvs
pytest tests/test_daemon.py -xvs
pytest tests/test_canvas.py -xvs
```

### 20.2 测试覆盖目标

| 优先级 | 模块类型 | 覆盖目标 |
|--------|----------|----------|
| P0 | 核心模块 | 90% |
| P1 | 功能模块 | 80% |
| P2 | 扩展模块 | 70% |

### 20.3 对比测试

1. **系统提示词对比**
   - 相同 Bootstrap 文件
   - 比较 MoltBot 和 LurkBot 生成的提示词
   - 确保 23 节结构一致

2. **工具策略对比**
   - 相同上下文
   - 比较过滤后的工具列表
   - 确保九层策略行为一致

3. **Heartbeat 行为对比**
   - 相同 HEARTBEAT.md 内容
   - 比较触发和投递行为

4. **Cron 执行对比**
   - 相同 Job 定义
   - 比较调度和执行结果

### 20.4 集成测试

- Agent + Tools 端到端测试
- Session 持久化测试
- Gateway 连接测试
- 子代理通信测试

### 20.5 E2E 验证

- CLI 命令完整性
- Daemon 服务管理
- 多渠道消息流转

---

## 附录：完整模块目录结构

```
src/lurkbot/
├── __init__.py
├── agents/                    # 第三章: Agent 运行时系统
│   ├── __init__.py
│   ├── types.py              # 核心类型定义
│   ├── runtime.py            # PydanticAI 运行时
│   ├── api.py                # FastAPI 端点
│   ├── bootstrap.py          # Bootstrap 文件系统
│   ├── system_prompt.py      # 系统提示词生成
│   ├── compaction.py         # 上下文压缩系统
│   └── subagent/             # 子代理通信协议
│       ├── __init__.py
│       ├── registry.py
│       ├── announce.py
│       └── spawn.py
│
├── tools/                     # 工具系统
│   ├── __init__.py
│   ├── policy.py             # 九层工具策略
│   └── builtin/              # 22 个原生工具
│       ├── __init__.py
│       ├── common.py
│       ├── fs_safe.py
│       ├── exec_tool.py
│       ├── fs_tools.py
│       ├── web_tools.py
│       ├── memory_tools.py
│       ├── message_tool.py
│       ├── sessions_tools.py
│       ├── cron_tool.py
│       ├── browser_tool.py
│       ├── canvas_tool.py
│       ├── image_tool.py
│       ├── nodes_tool.py
│       ├── gateway_tool.py
│       └── tts_tool.py
│
├── sessions/                  # 会话管理系统
│   ├── __init__.py
│   ├── store.py
│   ├── types.py
│   ├── routing.py
│   └── manager.py
│
├── autonomous/                # 自主运行
│   ├── __init__.py
│   ├── heartbeat/
│   │   ├── __init__.py
│   │   ├── runner.py
│   │   ├── events.py
│   │   └── config.py
│   └── cron/
│       ├── __init__.py
│       ├── service.py
│       ├── state.py
│       └── types.py
│
├── auth/                      # 认证配置文件系统
│   ├── __init__.py
│   └── profiles.py
│
├── skills/                    # 技能系统
│   ├── __init__.py
│   ├── frontmatter.py
│   ├── workspace.py
│   ├── registry.py
│   └── loader.py
│
├── gateway/                   # Gateway 协议
│   ├── __init__.py
│   ├── server.py
│   ├── protocol/
│   └── hub.py
│
├── memory/                    # 内存和向量搜索
│   ├── __init__.py
│   ├── embeddings/
│   ├── sqlite_vec.py
│   ├── search.py
│   └── sync.py
│
├── plugins/                   # 插件系统
│   ├── __init__.py
│   ├── loader.py
│   ├── manifest.py
│   ├── runtime.py
│   └── commands.py
│
├── auto_reply/                # Auto-Reply 系统
│   ├── __init__.py
│   ├── tokens.py
│   ├── directives.py
│   ├── queue/
│   │   ├── __init__.py
│   │   ├── directive.py
│   │   ├── types.py
│   │   ├── enqueue.py
│   │   ├── drain.py
│   │   └── state.py
│   ├── reply_tags.py
│   └── deliver.py
│
├── daemon/                    # Daemon 守护进程
│   ├── __init__.py
│   ├── service.py
│   ├── launchd.py
│   ├── systemd.py
│   ├── schtasks.py
│   └── diagnostics.py
│
├── media/                     # Media Understanding
│   ├── __init__.py
│   ├── understand.py
│   ├── providers/
│   │   ├── __init__.py
│   │   ├── openai.py
│   │   ├── anthropic.py
│   │   └── gemini.py
│   └── config.py
│
├── usage/                     # Provider Usage
│   ├── __init__.py
│   ├── monitor.py
│   ├── providers/
│   │   ├── __init__.py
│   │   ├── anthropic.py
│   │   └── openai.py
│   └── format.py
│
├── routing/                   # Routing 系统
│   ├── __init__.py
│   ├── router.py
│   ├── session_key.py
│   ├── dispatcher.py
│   └── broadcast.py
│
├── hooks/                     # Hooks 扩展
│   ├── __init__.py
│   ├── registry.py
│   ├── events.py
│   ├── discovery.py
│   ├── loader.py
│   └── bundled/
│       ├── __init__.py
│       └── session_memory.py
│
├── security/                  # Security 审计
│   ├── __init__.py
│   ├── audit.py
│   ├── dm_policy.py
│   └── model_check.py
│
├── acp/                       # ACP 协议
│   ├── __init__.py
│   ├── server.py
│   ├── translator.py
│   ├── session.py
│   └── event_mapper.py
│
├── browser/                   # Browser 自动化
│   ├── __init__.py
│   ├── server.py
│   ├── chrome.py
│   ├── cdp.py
│   ├── playwright_session.py
│   └── routes/
│       ├── __init__.py
│       ├── act.py
│       └── screenshot.py
│
├── canvas/                    # A2UI 界面
│   ├── __init__.py
│   ├── host.py
│   ├── a2ui.py
│   └── state.py
│
├── tui/                       # TUI 终端界面
│   ├── __init__.py
│   ├── app.py
│   ├── stream_assembler.py
│   └── components/
│       ├── __init__.py
│       └── chat_log.py
│
├── tts/                       # TTS 语音合成
│   ├── __init__.py
│   ├── engine.py
│   ├── directive_parser.py
│   └── providers/
│       ├── __init__.py
│       ├── openai.py
│       └── edge.py
│
├── wizard/                    # Wizard 配置向导
│   ├── __init__.py
│   ├── onboarding.py
│   ├── session.py
│   └── flows/
│       ├── __init__.py
│       └── quickstart.py
│
├── infra/                     # Infra 基础设施
│   ├── __init__.py
│   ├── errors.py
│   ├── retry.py
│   ├── system_events/
│   │   ├── __init__.py
│   │   └── events.py
│   ├── system_presence/
│   │   ├── __init__.py
│   │   └── presence.py
│   ├── tailscale/
│   │   ├── __init__.py
│   │   └── client.py
│   ├── ssh_tunnel/
│   │   ├── __init__.py
│   │   └── manager.py
│   ├── bonjour/
│   │   ├── __init__.py
│   │   └── discovery.py
│   ├── device_pairing/
│   │   ├── __init__.py
│   │   └── keypair.py
│   ├── exec_approvals/
│   │   ├── __init__.py
│   │   └── approver.py
│   └── voicewake/
│       ├── __init__.py
│       └── detector.py
│
├── config/                    # 配置管理
│   ├── __init__.py
│   ├── settings.py
│   └── schema.py
│
├── logging/                   # 日志系统
│   └── __init__.py
│
└── cli/                       # CLI 入口
    ├── __init__.py
    └── main.py
```

---

**文档完成**: 2026-01-29
**文档版本**: 3.0
**文档类型**: 完整复刻设计方案

**更新历史**:
- v1.0: 初始设计
- v2.0: 完整设计
- v2.1: 添加 A2UI 界面系统设计
- v2.2: 添加 Auto-Reply、Daemon、Media、Hooks、Security 等模块
- v2.3: 添加 ACP、Browser、TUI、TTS、Wizard、Infra 等模块
- v3.0: 全面重构，对齐 MoltBot v3.0 架构（32 章节），扩展到 28 个实施阶段

**下一步**: 按 Phase 顺序实施，当前在 Phase 5（剩余内置工具）
