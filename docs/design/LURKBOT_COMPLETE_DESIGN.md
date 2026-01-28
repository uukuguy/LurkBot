# LurkBot 完整复刻设计方案 v2.0

> **文档版本**: 2.0
> **更新日期**: 2026-01-29
> **基于**: MOLTBOT_COMPLETE_ARCHITECTURE.md 深度分析
> **核心原则**: 完全复刻 MoltBot，不遗漏任何功能

---

## 目录

- [一、设计方案总览](#一设计方案总览)
- [二、框架选型最终决定](#二框架选型最终决定)
- [三、核心模块设计](#三核心模块设计)
- [四、功能完整性检查清单](#四功能完整性检查清单)
- [五、实施计划](#五实施计划)
- [六、验证策略](#六验证策略)

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

## 四、功能完整性检查清单

### 4.1 核心功能检查

| # | MoltBot 功能 | LurkBot 设计 | 状态 |
|---|-------------|-------------|------|
| 1 | Pi SDK Agent Loop | PydanticAI Agent.run() | ✅ |
| 2 | 8 个 Bootstrap 文件 | bootstrap.py | ✅ |
| 3 | SUBAGENT_BOOTSTRAP_ALLOWLIST | bootstrap.py | ✅ |
| 4 | 23 节系统提示词 | system_prompt.py | ✅ |
| 5 | PromptMode (full/minimal/none) | system_prompt.py | ✅ |
| 6 | Runtime 行格式 | build_runtime_line() | ✅ |
| 7 | 22 原生工具 | tools/builtin/ | ✅ |
| 8 | 九层工具策略 | policy.py | ✅ |
| 9 | 工具分组和配置文件 | policy.py | ✅ |
| 10 | 5 种会话类型 | sessions/manager.py | ✅ |
| 11 | 会话 Key 格式 | build_session_key() | ✅ |
| 12 | Subagent Spawn | subagent.py | ✅ |
| 13 | Subagent Announce Flow | run_subagent_announce_flow() | ✅ |
| 14 | Heartbeat 系统 | heartbeat.py | ✅ |
| 15 | Heartbeat 事件 | HeartbeatEventPayload | ✅ |
| 16 | HEARTBEAT_OK Token | heartbeat.py | ✅ |
| 17 | Cron 调度类型 | cron.py | ✅ |
| 18 | Cron Payload 类型 | CronPayload | ✅ |
| 19 | Auth Profile 轮换 | profiles.py | ✅ |
| 20 | 冷却计算 | calculate_cooldown_ms() | ✅ |
| 21 | Context Compaction | compaction.py | ✅ |
| 22 | 自适应分块比例 | compute_adaptive_chunk_ratio() | ✅ |
| 23 | 分阶段摘要 | summarize_in_stages() | ✅ |
| 24 | Human-in-the-Loop | DeferredToolRequests | ✅ |

### 4.2 待实现功能

| # | 功能 | 优先级 | 说明 |
|---|------|--------|------|
| 1 | Gateway WebSocket 协议 | P1 | 完整帧结构 |
| 2 | 技能系统 | P1 | YAML Frontmatter 解析 |
| 3 | 插件系统 | P2 | 100+ 运行时 API |
| 4 | 内存向量搜索 | P2 | sqlite-vec 集成 |
| 5 | 错误处理与重试 | P2 | 渠道特定策略 |
| 6 | 路由系统 | P2 | 频道→代理映射 |

---

## 五、实施计划

### 5.1 阶段划分

| Phase | 内容 | 时间 | 依赖 |
|-------|------|------|------|
| **Phase 1** | 项目重构 - 清理旧代码 | 3天 | - |
| **Phase 2** | PydanticAI 核心框架 | 1周 | Phase 1 |
| **Phase 3** | Bootstrap + 系统提示词 | 1周 | Phase 2 |
| **Phase 4** | 九层工具策略 | 1周 | Phase 2 |
| **Phase 5** | 22 原生工具实现 | 2周 | Phase 4 |
| **Phase 6** | 会话管理 + 子代理 | 1周 | Phase 5 |
| **Phase 7** | Heartbeat + Cron | 1.5周 | Phase 6 |
| **Phase 8** | Auth Profile + Compaction | 1周 | Phase 2 |
| **Phase 9** | Gateway 协议 | 1.5周 | Phase 6 |
| **Phase 10** | 技能和插件系统 | 2周 | Phase 9 |
| **总计** | | **12周** | |

### 5.2 关键文件清单

```
src/lurkbot/
├── agents/
│   ├── runtime.py           # Agent 运行时（PydanticAI）
│   ├── bootstrap.py         # Bootstrap 文件系统
│   ├── system_prompt.py     # 系统提示词生成（23节）
│   ├── compaction.py        # 上下文压缩
│   └── subagent.py          # 子代理通信
├── tools/
│   ├── policy.py            # 九层工具策略
│   ├── registry.py          # 工具注册表
│   └── builtin/
│       ├── sessions.py      # 会话工具（6个）
│       ├── cron.py          # Cron 工具
│       ├── message.py       # 消息工具
│       ├── web.py           # Web 工具（2个）
│       ├── media.py         # 媒体工具（3个）
│       ├── memory.py        # 内存工具（2个）
│       ├── system.py        # 系统工具（2个）
│       ├── tts.py           # TTS 工具
│       └── coding.py        # 编码工具（4个）
├── sessions/
│   └── manager.py           # 会话管理器
├── autonomous/
│   ├── heartbeat.py         # 心跳系统
│   └── cron.py              # Cron 服务
├── auth/
│   └── profiles.py          # Auth Profile 系统
├── gateway/
│   ├── server.py            # WebSocket 服务器
│   ├── protocol.py          # 协议帧定义
│   └── client.py            # Gateway 客户端
├── skills/
│   └── loader.py            # 技能加载器
├── plugins/
│   └── loader.py            # 插件加载器
├── memory/
│   └── store.py             # 内存存储（向量搜索）
├── infra/
│   └── retry.py             # 重试策略
└── config/
    └── settings.py          # 配置管理
```

---

## 六、验证策略

### 6.1 单元测试

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
```

### 6.2 对比测试

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

---

**文档完成**: 2026-01-29
**文档版本**: 2.0
**文档类型**: 完整复刻设计方案
**下一步**: 按 Phase 顺序实施，每阶段完成后与 MoltBot 对比验证
