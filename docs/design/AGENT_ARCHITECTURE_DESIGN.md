# LurkBot 智能体架构设计文档

## 文档概述

本文档详细分析 LurkBot 智能体系统的设计和代码实现，涵盖自动运行、推理、执行任务的核心机制。

---

## 一、智能体核心架构概览

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      LurkBot Agent Architecture                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────┐     ┌──────────────┐     ┌─────────────────┐          │
│  │   HTTP API  │     │  WebSocket   │     │   CLI / Chat    │          │
│  │  (FastAPI)  │     │   Gateway    │     │    Commands     │          │
│  └──────┬──────┘     └──────┬───────┘     └────────┬────────┘          │
│         │                   │                      │                    │
│         └───────────────────┼──────────────────────┘                    │
│                             ▼                                           │
│                    ┌─────────────────┐                                  │
│                    │  AgentRuntime   │ ← 会话管理 + 持久化               │
│                    │  (runtime.py)   │                                  │
│                    └────────┬────────┘                                  │
│                             │                                           │
│                             ▼                                           │
│                    ┌─────────────────┐                                  │
│                    │   ModelAgent    │ ← Tool Use Loop                  │
│                    │  (runtime.py)   │                                  │
│                    └────────┬────────┘                                  │
│                             │                                           │
│         ┌───────────────────┼───────────────────┐                       │
│         ▼                   ▼                   ▼                       │
│  ┌─────────────┐    ┌──────────────┐    ┌─────────────┐                │
│  │   Model     │    │    Tool      │    │  Approval   │                │
│  │  Registry   │    │   Registry   │    │   Manager   │                │
│  └──────┬──────┘    └──────┬───────┘    └──────┬──────┘                │
│         │                  │                    │                       │
│         ▼                  ▼                    ▼                       │
│  ┌─────────────┐    ┌──────────────┐    ┌─────────────┐                │
│  │  Adapters   │    │   Built-in   │    │   Channel   │                │
│  │ (Anthropic  │    │    Tools     │    │ Notification│                │
│  │  OpenAI     │    │ (bash,read,  │    │  (Telegram  │                │
│  │  Ollama)    │    │   write)     │    │   Discord)  │                │
│  └─────────────┘    └──────────────┘    └─────────────┘                │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 二、核心组件详解

### 2.1 Agent 基类

**文件**: `src/lurkbot/agents/base.py`

Agent 基类定义了智能体的核心接口，所有具体的 Agent 实现都必须继承此类。

```python
class Agent(ABC):
    """Base class for AI agents."""

    def __init__(self, model: str, **kwargs: Any) -> None:
        self.model = model
        self.config = kwargs

    @abstractmethod
    async def chat(self, context: AgentContext, message: str) -> str:
        """处理聊天消息并返回响应"""
        ...

    @abstractmethod
    async def stream_chat(self, context: AgentContext, message: str) -> AsyncIterator[str]:
        """流式处理聊天消息"""
        ...
```

**关键数据结构**:

```python
@dataclass
class AgentContext:
    """智能体执行上下文"""
    session_id: str           # 会话标识
    channel: str              # 渠道（telegram/discord）
    sender_id: str            # 发送者 ID
    sender_name: str | None   # 发送者名称
    workspace: str | None     # 工作目录
    messages: list[ChatMessage] = field(default_factory=list)  # 历史消息
    metadata: dict[str, Any] = field(default_factory=dict)     # 元数据
    session_type: SessionType = SessionType.MAIN  # 会话类型（安全控制）

class ChatMessage(BaseModel):
    """聊天消息"""
    role: str          # "user", "assistant", "system"
    content: str       # 消息内容
    name: str | None   # 可选名称
    tool_calls: list[dict[str, Any]] | None  # 工具调用
    tool_call_id: str | None                 # 工具调用 ID
```

### 2.2 ModelAgent（智能体核心实现）

**文件**: `src/lurkbot/agents/runtime.py:21-403`

ModelAgent 是智能体的核心实现，支持多模型适配器和工具使用循环。

**职责**:
- 实现 Tool Use Loop（工具使用循环）
- 调用 LLM 模型进行推理
- 执行工具并收集结果
- 处理审批流程

**初始化**:
```python
class ModelAgent(Agent):
    def __init__(
        self,
        model: str,
        model_registry: ModelRegistry,
        tool_registry: ToolRegistry | None = None,
        approval_manager: ApprovalManager | None = None,
        channel: Channel | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(model, **kwargs)
        self.model_registry = model_registry
        self.tool_registry = tool_registry
        self.approval_manager = approval_manager
        self.channel = channel
        self._adapter = model_registry.get_adapter(model)  # 获取模型适配器
```

### 2.3 AgentRuntime（会话运行时）

**文件**: `src/lurkbot/agents/runtime.py:405-710`

AgentRuntime 是会话管理的核心，负责协调所有组件。

**职责**:
- 会话生命周期管理（创建、获取、清除、删除）
- Agent 实例缓存和复用
- 消息持久化（JSONL 存储）
- 组件初始化协调

```python
class AgentRuntime:
    def __init__(self, settings: Settings, channel: Channel | None = None) -> None:
        self.settings = settings
        self.channel = channel
        self.sessions: dict[str, AgentContext] = {}      # 会话缓存
        self.agents: dict[str, Agent] = {}               # Agent 实例缓存

        # 核心组件初始化
        self.model_registry = ModelRegistry(settings)    # 模型注册表
        self.tool_registry = ToolRegistry()              # 工具注册表
        self._register_builtin_tools()                   # 注册内置工具
        self.approval_manager = ApprovalManager()        # 审批管理器

        # 会话持久化
        if settings.storage.enabled:
            self.session_store = SessionStore(settings.sessions_dir)
```

**核心方法**:
```python
async def chat(
    self,
    session_id: str,
    channel: str,
    sender_id: str,
    message: str,
    model: str | None = None,
) -> str:
    """处理聊天消息的主入口"""
    # 1. 获取或创建会话
    context = await self.get_or_create_session(session_id, channel, sender_id)

    # 2. 保存用户消息
    user_msg = ChatMessage(role="user", content=message)
    await self._save_message_to_store(session_id, user_msg)

    # 3. 获取 Agent 并处理消息
    agent = self.get_agent(model)
    response = await agent.chat(context, message)

    # 4. 保存助手响应
    assistant_msg = ChatMessage(role="assistant", content=response)
    await self._save_message_to_store(session_id, assistant_msg)

    return response
```

---

## 三、Tool Use Loop（工具使用循环）

### 3.1 核心流程图

```
                        ┌──────────────────┐
                        │   用户消息输入    │
                        └────────┬─────────┘
                                 │
                                 ▼
                   ┌─────────────────────────────┐
                   │  context.messages.append()  │
                   │    添加用户消息到上下文      │
                   └─────────────┬───────────────┘
                                 │
                                 ▼
                   ┌─────────────────────────────┐
                   │  tool_registry.get_schemas()│
                   │     获取可用工具列表         │
                   └─────────────┬───────────────┘
                                 │
              ┌──────────────────┴──────────────────┐
              │                                      │
              ▼                                      │
     ┌─────────────────────────────────────────────────────────┐
     │                    TOOL USE LOOP                        │
     │                 (最多 10 次迭代)                         │
     │  ┌─────────────────────────────────────────────────┐   │
     │  │                                                  │   │
     │  │   ┌──────────────────────────┐                  │   │
     │  │   │  adapter.chat(messages,  │ ← 调用 LLM API   │   │
     │  │   │      tools=tools)        │                  │   │
     │  │   └───────────┬──────────────┘                  │   │
     │  │               │                                  │   │
     │  │               ▼                                  │   │
     │  │   ┌──────────────────────────┐                  │   │
     │  │   │   response.tool_calls?   │                  │   │
     │  │   └───────────┬──────────────┘                  │   │
     │  │               │                                  │   │
     │  │       YES     │      NO                          │   │
     │  │       ┌───────┴───────┐                          │   │
     │  │       ▼               ▼                          │   │
     │  │  ┌─────────┐    ┌─────────────┐                  │   │
     │  │  │执行工具 │    │ 返回文本响应│ ──────────────► EXIT │
     │  │  └────┬────┘    └─────────────┘                  │   │
     │  │       │                                          │   │
     │  │       ▼                                          │   │
     │  │  ┌───────────────────────────────────────────┐  │   │
     │  │  │ 1. 获取工具 tool_registry.get(name)       │  │   │
     │  │  │ 2. 检查策略 check_policy(tool, session)    │  │   │
     │  │  │ 3. 检查审批 requires_approval?             │  │   │
     │  │  │    └── 是 → _handle_approval() 等待用户    │  │   │
     │  │  │ 4. 执行工具 tool.execute(args, workspace)  │  │   │
     │  │  │ 5. 收集结果 ToolResult                     │  │   │
     │  │  └───────────────────────────────────────────┘  │   │
     │  │       │                                          │   │
     │  │       ▼                                          │   │
     │  │  ┌───────────────────────────────────────────┐  │   │
     │  │  │ messages.append({                         │  │   │
     │  │  │   role: "user",                           │  │   │
     │  │  │   content: [tool_result blocks]           │  │   │
     │  │  │ })                                        │  │   │
     │  │  └───────────────────────────────────────────┘  │   │
     │  │       │                                          │   │
     │  │       └───────────── 继续循环 ───────────────────┘   │
     │  │                                                  │   │
     │  └──────────────────────────────────────────────────┘   │
     └─────────────────────────────────────────────────────────┘
                                 │
                                 ▼
                   ┌─────────────────────────────┐
                   │  context.messages.append()  │
                   │   保存助手响应到上下文       │
                   └─────────────┬───────────────┘
                                 │
                                 ▼
                        ┌──────────────────┐
                        │   返回响应文本    │
                        └──────────────────┘
```

### 3.2 代码实现详解

**文件**: `src/lurkbot/agents/runtime.py:47-136`

```python
async def chat(self, context: AgentContext, message: str) -> str:
    """处理聊天消息，支持工具使用循环

    循环流程:
    1. 发送消息给模型（附带可用工具）
    2. 如果模型要求使用工具，执行工具
    3. 将工具结果发回模型，继续对话
    4. 重复直到模型返回文本响应
    """
    # 1. 添加用户消息到上下文
    context.messages.append(ChatMessage(role="user", content=message))

    # 2. 准备 API 调用格式
    messages = self._prepare_messages(context)

    # 3. 获取当前会话可用的工具列表
    tools = None
    if self.tool_registry:
        tools = self.tool_registry.get_tool_schemas(context.session_type)

    # 4. Tool Use Loop - 最多 10 次迭代（防止无限循环）
    max_iterations = 10
    for iteration in range(max_iterations):

        # 4.1 调用 LLM API
        response = await self._adapter.chat(
            messages=messages,
            tools=tools if tools else None,
            **kwargs,
        )

        # 4.2 检查是否需要工具调用
        if response.tool_calls:
            # 构建助手消息（含 tool_use 块）
            assistant_content = self._build_assistant_content(response)
            messages.append({"role": "assistant", "content": assistant_content})

            # 执行工具
            tool_results = await self._execute_tools(response.tool_calls, context)

            # 将工具结果添加到消息（Anthropic 格式）
            messages.append({
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": r.tool_use_id,
                        "content": r.content,
                        "is_error": r.is_error,
                    }
                    for r in tool_results
                ]
            })
            # 继续循环，让模型处理工具结果

        elif response.stop_reason in ("end_turn", "stop", None):
            # 正常完成 - 返回文本响应
            assistant_message = response.text or ""
            context.messages.append(ChatMessage(role="assistant", content=assistant_message))
            return assistant_message

    # 达到最大迭代次数
    return "Error: Maximum tool execution iterations reached"
```

### 3.3 工具执行流程

**文件**: `src/lurkbot/agents/runtime.py:166-260`

```python
async def _execute_tools(
    self,
    tool_calls: list[ToolCall],
    context: AgentContext,
) -> list[ToolResult]:
    """执行请求的工具并返回结果"""
    results: list[ToolResult] = []

    for tc in tool_calls:
        tool_name = tc.name
        tool_input = tc.arguments
        tool_id = tc.id

        # 1. 从注册表获取工具
        tool = self.tool_registry.get(tool_name)
        if not tool:
            results.append(ToolResult(
                tool_use_id=tool_id,
                content=f"Error: Tool '{tool_name}' not found",
                is_error=True,
            ))
            continue

        # 2. 检查工具策略（会话类型权限）
        if not self.tool_registry.check_policy(tool, context.session_type):
            results.append(ToolResult(
                tool_use_id=tool_id,
                content=f"Error: Tool not allowed for session type",
                is_error=True,
            ))
            continue

        # 3. 检查是否需要用户审批
        if tool.policy.requires_approval and self.approval_manager:
            approval_result = await self._handle_approval(
                tool_name, tool_input, tool_id, context
            )
            if approval_result is not None:
                results.append(approval_result)
                continue

        # 4. 执行工具
        try:
            result = await tool.execute(
                tool_input,
                context.workspace or ".",
                context.session_type,
            )

            results.append(ToolResult(
                tool_use_id=tool_id,
                content=result.output or result.error or "No output",
                is_error=not result.success,
            ))

        except Exception as e:
            results.append(ToolResult(
                tool_use_id=tool_id,
                content=f"Execution error: {e}",
                is_error=True,
            ))

    return results
```

---

## 四、工具系统架构

### 4.1 工具基类

**文件**: `src/lurkbot/tools/base.py`

```python
class Tool(ABC):
    """工具抽象基类"""

    def __init__(self, name: str, description: str, policy: ToolPolicy | None = None):
        self.name = name                       # 工具名称
        self.description = description         # 工具描述
        self.policy = policy or ToolPolicy()   # 执行策略

    @abstractmethod
    async def execute(
        self,
        arguments: dict[str, Any],
        workspace: str,
        session_type: SessionType,
    ) -> ToolResult:
        """执行工具"""
        ...

    @abstractmethod
    def get_schema(self) -> dict[str, Any]:
        """获取工具 JSON Schema（给 LLM 使用）"""
        ...
```

### 4.2 工具策略（ToolPolicy）

**文件**: `src/lurkbot/tools/base.py:41-56`

```python
@dataclass
class ToolPolicy:
    """工具执行策略"""

    # 允许的会话类型（默认仅 MAIN）
    allowed_session_types: set[SessionType] = field(
        default_factory=lambda: {SessionType.MAIN}
    )

    # 是否需要用户审批
    requires_approval: bool = False

    # 是否需要沙箱隔离
    sandbox_required: bool = False

    # 最大执行时间（秒）
    max_execution_time: int = 30
```

### 4.3 会话类型与安全隔离

**文件**: `src/lurkbot/tools/base.py:11-25`

```python
class SessionType(str, Enum):
    """会话类型，用于工具策略控制"""

    MAIN = "main"     # 直接 DM（完全信任）
    GROUP = "group"   # 群组聊天（需要沙箱）
    DM = "dm"         # 其他用户 DM（部分信任）
    TOPIC = "topic"   # 论坛话题（需要沙箱）
```

**安全矩阵**:

| 会话类型 | 信任级别 | 沙箱隔离 | 默认审批 |
|----------|----------|----------|----------|
| MAIN     | 完全信任 | 否       | 否       |
| GROUP    | 低信任   | 是       | 是       |
| DM       | 部分信任 | 否       | 否       |
| TOPIC    | 低信任   | 是       | 是       |

### 4.4 工具注册表

**文件**: `src/lurkbot/tools/registry.py`

```python
class ToolRegistry:
    """工具注册表，带策略强制执行"""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        """注册工具"""
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        """按名称获取工具"""
        return self._tools.get(name)

    def check_policy(self, tool: Tool, session_type: SessionType) -> bool:
        """检查工具是否允许在此会话类型执行"""
        return session_type in tool.policy.allowed_session_types

    def get_tool_schemas(self, session_type: SessionType) -> list[dict[str, Any]]:
        """获取当前会话类型可用的所有工具 Schema"""
        tools = self.list_tools(session_type)
        return [tool.get_schema() for tool in tools]

    def list_tools(self, session_type: SessionType | None = None) -> list[Tool]:
        """列出所有工具，可按会话类型过滤"""
        if session_type is None:
            return list(self._tools.values())

        return [
            tool for tool in self._tools.values()
            if session_type in tool.policy.allowed_session_types
        ]
```

### 4.5 工具执行结果

```python
class ToolResult(BaseModel):
    """工具执行结果"""
    success: bool              # 是否成功
    output: str | None = None  # 标准输出
    error: str | None = None   # 错误信息
    exit_code: int | None = None  # 退出码（命令行工具）
```

---

## 五、审批系统（Human-in-the-Loop）

### 5.1 审批流程图

```
                    ┌──────────────────┐
                    │ Tool Requires    │
                    │    Approval      │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │ Create Approval  │
                    │    Request       │
                    └────────┬─────────┘
                             │
                             ▼
            ┌────────────────────────────────┐
            │ Send Notification via Channel  │
            │  (Telegram/Discord/Web)        │
            └───────────────┬────────────────┘
                            │
         ┌──────────────────┴──────────────────┐
         │                                      │
         ▼                                      ▼
┌─────────────────┐                   ┌─────────────────┐
│   User Reviews  │                   │   Timeout (5m)  │
│   /approve ID   │                   │   Auto-DENY     │
│   /deny ID      │                   │                 │
└────────┬────────┘                   └────────┬────────┘
         │                                      │
         ├──────────────────┬───────────────────┤
         ▼                  ▼                   ▼
    ┌─────────┐        ┌─────────┐        ┌──────────┐
    │ APPROVE │        │  DENY   │        │ TIMEOUT  │
    └────┬────┘        └────┬────┘        └────┬─────┘
         │                  │                   │
         ▼                  ▼                   ▼
    ┌─────────┐        ┌─────────────────────────┐
    │ Execute │        │  Return Error Result    │
    │  Tool   │        │  "Tool execution denied"│
    └─────────┘        └─────────────────────────┘
```

### 5.2 审批数据结构

**文件**: `src/lurkbot/tools/approval.py`

```python
class ApprovalDecision(str, Enum):
    """用户决策"""
    APPROVE = "approve"   # 批准
    DENY = "deny"         # 拒绝
    TIMEOUT = "timeout"   # 超时自动拒绝


class ApprovalRequest(BaseModel):
    """工具审批请求"""
    tool_name: str                    # 工具名称
    command: str | None               # 命令（bash 工具）
    args: dict[str, Any]              # 工具参数
    session_key: str                  # 会话标识
    agent_id: str | None              # Agent ID
    security_context: str | None      # 安全上下文
    reason: str | None                # 审批原因


class ApprovalRecord(BaseModel):
    """审批记录"""
    id: str                           # 审批 ID
    request: ApprovalRequest          # 审批请求
    created_at_ms: int                # 创建时间
    expires_at_ms: int                # 过期时间
    resolved_at_ms: int | None        # 解决时间
    decision: ApprovalDecision | None # 决策结果
    resolved_by: str | None           # 解决者 ID

    @property
    def is_expired(self) -> bool:
        """检查是否已过期"""
        return int(time.time() * 1000) >= self.expires_at_ms

    @property
    def is_resolved(self) -> bool:
        """检查是否已解决"""
        return self.decision is not None
```

### 5.3 审批管理器

**文件**: `src/lurkbot/tools/approval.py:72-268`

```python
class ApprovalManager:
    """审批生命周期管理器，支持超时处理"""

    def __init__(self) -> None:
        self._pending: dict[str, _PendingEntry] = {}   # 等待中的审批
        self._records: dict[str, ApprovalRecord] = {}  # 所有记录

    def create(
        self,
        request: ApprovalRequest,
        timeout_ms: int = 300000,  # 5 分钟默认超时
    ) -> ApprovalRecord:
        """创建审批记录"""
        now_ms = int(time.time() * 1000)
        record = ApprovalRecord(
            id=str(uuid.uuid4()),
            request=request,
            created_at_ms=now_ms,
            expires_at_ms=now_ms + timeout_ms,
        )
        self._records[record.id] = record
        return record

    async def wait_for_decision(self, record: ApprovalRecord) -> ApprovalDecision:
        """等待用户决策或超时（阻塞异步调用）"""
        # 如果已解决，直接返回
        if record.is_resolved:
            return record.decision

        # 计算剩余超时时间
        now_ms = int(time.time() * 1000)
        remaining_ms = record.expires_at_ms - now_ms

        if remaining_ms <= 0:
            record.decision = ApprovalDecision.TIMEOUT
            return ApprovalDecision.TIMEOUT

        # 创建 Future 等待决策
        future: asyncio.Future[ApprovalDecision] = asyncio.Future()
        timeout_task = asyncio.create_task(
            self._timeout_handler(record.id, remaining_ms / 1000, future)
        )

        # 存入待处理映射
        entry = _PendingEntry(record=record, future=future, timeout_task=timeout_task)
        self._pending[record.id] = entry

        try:
            decision = await future  # 阻塞等待
            return decision
        finally:
            self._pending.pop(record.id, None)
            if not timeout_task.done():
                timeout_task.cancel()

    def resolve(
        self,
        record_id: str,
        decision: ApprovalDecision,
        resolved_by: str | None = None,
    ) -> bool:
        """用户解决审批"""
        entry = self._pending.get(record_id)
        if not entry:
            return False

        # 更新记录
        entry.record.resolved_at_ms = int(time.time() * 1000)
        entry.record.decision = decision
        entry.record.resolved_by = resolved_by

        # 解决 Future
        if not entry.future.done():
            entry.future.set_result(decision)

        # 取消超时任务
        if not entry.timeout_task.done():
            entry.timeout_task.cancel()

        return True

    async def _timeout_handler(
        self,
        record_id: str,
        timeout_seconds: float,
        future: asyncio.Future
    ) -> None:
        """处理审批超时"""
        try:
            await asyncio.sleep(timeout_seconds)
            entry = self._pending.get(record_id)
            if entry and not entry.future.done():
                entry.record.decision = ApprovalDecision.TIMEOUT
                future.set_result(ApprovalDecision.TIMEOUT)
        except asyncio.CancelledError:
            pass  # 正常取消（审批已提前解决）
```

### 5.4 审批流程在 ModelAgent 中的实现

**文件**: `src/lurkbot/agents/runtime.py:262-342`

```python
async def _handle_approval(
    self,
    tool_name: str,
    tool_input: dict[str, Any],
    tool_id: str,
    context: AgentContext,
) -> ToolResult | None:
    """处理工具审批工作流

    Returns:
        ToolResult: 如果审批失败/拒绝
        None: 如果审批通过，继续执行工具
    """
    # 1. 创建审批请求
    command = tool_input.get("command") if tool_name == "bash" else None
    approval_request = ApprovalRequest(
        tool_name=tool_name,
        command=command,
        args=tool_input,
        session_key=context.session_id,
        agent_id=self.model,
        security_context=f"Session type: {context.session_type.value}",
        reason=f"Tool {tool_name} requires user approval",
    )

    # 2. 通过渠道发送通知
    if self.channel:
        try:
            record = self.approval_manager.create(approval_request)

            # 格式化通知消息
            notification = self._format_approval_notification(record, approval_request)

            # 发送给用户
            await self.channel.send(
                recipient_id=context.sender_id,
                content=notification,
            )

            # 3. 等待用户决策
            decision = await self.approval_manager.wait_for_decision(record)

            if decision == ApprovalDecision.APPROVE:
                return None  # 批准，继续执行
            else:
                # 拒绝或超时
                error_msg = f"Tool execution {'denied' if decision == ApprovalDecision.DENY else 'timed out'}"
                return ToolResult(
                    tool_use_id=tool_id,
                    content=f"Error: {error_msg}",
                    is_error=True,
                )
        except Exception as e:
            return ToolResult(
                tool_use_id=tool_id,
                content=f"Approval error: {e}",
                is_error=True,
            )
    else:
        # 无渠道可用，拒绝执行
        return ToolResult(
            tool_use_id=tool_id,
            content="Error: Tool requires approval but no channel available",
            is_error=True,
        )
```

---

## 六、多模型适配器系统

### 6.1 架构图

```
                    ┌────────────────────┐
                    │   ModelRegistry    │
                    │   (registry.py)    │
                    └─────────┬──────────┘
                              │
           ┌──────────────────┼──────────────────┐
           ▼                  ▼                  ▼
   ┌───────────────┐  ┌───────────────┐  ┌───────────────┐
   │   Anthropic   │  │    OpenAI     │  │    Ollama     │
   │    Adapter    │  │    Adapter    │  │    Adapter    │
   └───────┬───────┘  └───────┬───────┘  └───────┬───────┘
           │                  │                  │
           ▼                  ▼                  ▼
   ┌───────────────┐  ┌───────────────┐  ┌───────────────┐
   │ Claude Sonnet │  │  GPT-4o       │  │ Llama 3.3     │
   │ Claude Opus   │  │  GPT-4o Mini  │  │ Qwen 2.5      │
   │ Claude Haiku  │  │  O1-mini      │  │ DeepSeek R1   │
   └───────────────┘  └───────────────┘  └───────────────┘
```

### 6.2 模型适配器基类

**文件**: `src/lurkbot/models/base.py`

```python
class ModelAdapter(ABC):
    """模型适配器抽象基类

    每个适配器实现特定提供商（Anthropic, OpenAI, Ollama 等）的接口，
    同时提供统一的 API。
    """

    def __init__(
        self,
        config: ModelConfig,
        api_key: str | None = None,
        **kwargs: Any,
    ) -> None:
        self.config = config
        self.api_key = api_key
        self._client: Any = None

    @property
    @abstractmethod
    def client(self) -> Any:
        """懒加载并返回提供商客户端"""
        ...

    @abstractmethod
    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        tool_results: list[ToolResult] | None = None,
        **kwargs: Any,
    ) -> ModelResponse:
        """发送聊天请求"""
        ...

    @abstractmethod
    async def stream_chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        tool_results: list[ToolResult] | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[StreamChunk]:
        """流式聊天响应"""
        ...
```

### 6.3 Anthropic 适配器实现

**文件**: `src/lurkbot/models/adapters/anthropic.py`

```python
class AnthropicAdapter(ModelAdapter):
    """Anthropic Claude 模型适配器

    使用原生 Anthropic SDK，支持视觉、工具使用和扩展思考能力。
    """

    @property
    def client(self) -> Any:
        """懒加载 Anthropic 客户端"""
        if self._client is None:
            import anthropic
            self._client = anthropic.AsyncAnthropic(api_key=self.api_key)
        return self._client

    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        tool_results: list[ToolResult] | None = None,
        **kwargs: Any,
    ) -> ModelResponse:
        """发送聊天请求到 Claude"""
        # 准备消息（包含工具结果）
        api_messages = self._prepare_messages(messages, tool_results)

        # 构建请求参数
        request_params = {
            "model": self.config.model_id,
            "max_tokens": self._get_max_tokens(**kwargs),
            "messages": api_messages,
        }

        # 添加工具
        if tools:
            request_params["tools"] = tools

        # 调用 API
        response = await self.client.messages.create(**request_params)

        return self._parse_response(response)

    def _parse_response(self, response: Any) -> ModelResponse:
        """解析 Anthropic 响应为统一格式"""
        tool_calls: list[ToolCall] = []
        text_parts: list[str] = []

        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_calls.append(ToolCall(
                    id=block.id,
                    name=block.name,
                    arguments=block.input,
                ))

        return ModelResponse(
            text="\n".join(text_parts) if text_parts else None,
            tool_calls=tool_calls,
            stop_reason=response.stop_reason,
            usage={
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            },
        )
```

### 6.4 模型注册表

**文件**: `src/lurkbot/models/registry.py`

```python
class ModelRegistry:
    """模型配置和适配器注册表

    管理模型定义并按需懒加载创建适配器。
    支持内置模型和用户自定义模型。
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._models: dict[str, ModelConfig] = dict(BUILTIN_MODELS)  # 内置模型
        self._adapters: dict[str, ModelAdapter] = {}  # 适配器缓存
        self._load_custom_models()

    def get_adapter(self, model_id: str) -> ModelAdapter:
        """获取或创建指定模型的适配器"""
        if model_id in self._adapters:
            return self._adapters[model_id]

        config = self._models.get(model_id)
        if not config:
            raise ValueError(f"Unknown model: {model_id}")

        adapter = self._create_adapter(config)
        self._adapters[model_id] = adapter
        return adapter

    def _create_adapter(self, config: ModelConfig) -> ModelAdapter:
        """根据配置创建适配器"""
        if config.api_type == ApiType.ANTHROPIC:
            from lurkbot.models.adapters.anthropic import AnthropicAdapter
            api_key = self._settings.anthropic_api_key
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY not configured")
            return AnthropicAdapter(config, api_key)

        elif config.api_type == ApiType.OPENAI:
            from lurkbot.models.adapters.openai import OpenAIAdapter
            api_key = self._settings.openai_api_key
            if not api_key:
                raise ValueError("OPENAI_API_KEY not configured")
            return OpenAIAdapter(config, api_key)

        elif config.api_type == ApiType.OLLAMA:
            from lurkbot.models.adapters.ollama import OllamaAdapter
            base_url = getattr(self._settings.models, "ollama_base_url", "http://localhost:11434")
            return OllamaAdapter(config, base_url=base_url)

        else:
            raise ValueError(f"Unsupported API type: {config.api_type}")
```

### 6.5 格式转换说明

不同 LLM 提供商的工具格式存在差异，适配器负责转换：

| 格式项 | Anthropic | OpenAI |
|--------|-----------|--------|
| 工具参数 | `input_schema` | `parameters` |
| 工具调用块 | `tool_use` content block | `tool_calls` array |
| 工具结果 | user message with `tool_result` | `tool` role message |

---

## 七、会话持久化

### 7.1 JSONL 存储格式

**文件**: `src/lurkbot/storage/jsonl.py`

每个会话存储为独立的 `.jsonl` 文件，格式如下：

```
# 第一行：会话元数据
{"type": "meta", "session_id": "telegram_123_456", "channel": "telegram", ...}

# 后续行：消息记录
{"role": "user", "content": "Hello", "timestamp": "2026-01-29T10:00:00Z"}
{"role": "assistant", "content": "Hi there!", "timestamp": "2026-01-29T10:00:01Z"}
```

### 7.2 SessionStore 实现

```python
class SessionStore:
    """JSONL 会话存储

    特性：
    - 追加写入，性能优异
    - 会话历史懒加载
    - 自动创建会话文件
    - 线程安全异步操作
    """

    def __init__(self, sessions_dir: Path) -> None:
        self.sessions_dir = Path(sessions_dir)

    @staticmethod
    def generate_session_id(channel: str, chat_id: str, user_id: str) -> str:
        """生成会话 ID: {channel}_{chat_id}_{user_id}"""
        return f"{channel}_{chat_id}_{user_id}"

    async def load_messages(
        self,
        session_id: str,
        limit: int | None = None,
    ) -> list[SessionMessage]:
        """加载会话消息（可限制数量）"""
        path = self._get_session_path(session_id)
        if not path.exists():
            return []

        messages = []
        async with aiofiles.open(path, encoding="utf-8") as f:
            line_count = 0
            async for line in f:
                line_count += 1
                if line_count == 1:  # 跳过元数据行
                    continue
                if line.strip():
                    data = json.loads(line)
                    if "role" in data:
                        messages.append(SessionMessage.model_validate(data))
                if limit and len(messages) >= limit:
                    break

        return messages

    async def append_message(
        self,
        session_id: str,
        message: SessionMessage,
    ) -> None:
        """追加消息到会话"""
        path = self._get_session_path(session_id)
        async with aiofiles.open(path, mode="a", encoding="utf-8") as f:
            await f.write(message.model_dump_json() + "\n")
```

### 7.3 自动加载与保存

在 AgentRuntime 中：

```python
async def _load_session_from_store(context, channel, sender_id):
    """从存储加载会话历史"""
    stored_messages = await session_store.load_messages(
        session_id,
        limit=settings.storage.max_messages  # 限制加载消息数
    )
    for msg in stored_messages:
        context.messages.append(ChatMessage(...))


async def _save_message_to_store(session_id, message):
    """自动保存消息"""
    if settings.storage.auto_save:
        await session_store.append_message(session_id, message)
```

---

## 八、关键文件清单

| 组件 | 文件路径 | 说明 |
|------|----------|------|
| Agent 基类 | `agents/base.py` | Agent 接口定义 |
| ModelAgent | `agents/runtime.py:21-403` | Tool Use Loop 实现 |
| AgentRuntime | `agents/runtime.py:405-710` | 会话管理运行时 |
| Tool 基类 | `tools/base.py` | 工具抽象和策略 |
| ToolRegistry | `tools/registry.py` | 工具注册和策略检查 |
| ApprovalManager | `tools/approval.py:72-268` | 审批流程管理 |
| ModelRegistry | `models/registry.py` | 模型配置和适配器 |
| AnthropicAdapter | `models/adapters/anthropic.py` | Claude API 适配 |
| OpenAIAdapter | `models/adapters/openai.py` | OpenAI API 适配 |
| OllamaAdapter | `models/adapters/ollama.py` | Ollama API 适配 |
| SessionStore | `storage/jsonl.py` | JSONL 持久化存储 |

---

## 九、设计亮点总结

### 9.1 自动推理循环
- 最多 10 次迭代的 Tool Use Loop
- 模型可以连续调用多个工具
- 工具结果反馈给模型继续推理
- 直到 `stop_reason == "end_turn"` 才返回

### 9.2 安全隔离机制
- 基于 SessionType 的会话类型控制
- 工具策略强制执行（ToolPolicy）
- 沙箱隔离支持（GROUP/TOPIC）
- 人工审批流程（5分钟超时自动拒绝）

### 9.3 多模型支持
- 统一的 ModelAdapter 接口
- 支持 Anthropic、OpenAI、Ollama 三大提供商
- 自动格式转换
- 模型配置缓存和懒加载

### 9.4 会话持久化
- JSONL 追加写入，高性能
- 会话历史懒加载
- 可配置的消息数量限制
- 自动保存开关

### 9.5 流式响应
- 异步 API 设计
- 支持 SSE 流式返回
- WebSocket 事件系统

---

## 十、验证方式

可通过以下命令验证现有实现：

```bash
# 运行测试
pytest tests/ -xvs

# 启动 CLI 交互测试
lurkbot chat start
lurkbot models list
lurkbot sessions list
```

---

**文档创建日期**: 2026-01-29
**文档类型**: 架构设计分析文档
