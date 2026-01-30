"""
ACP 协议类型定义

实现 Agent Client Protocol (ACP) 的核心类型
基于官方 ACP Python SDK (agent-client-protocol) 的设计

对标 MoltBot src/acp/types.ts
"""

from enum import Enum
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


# ============================================================================
# 协议版本
# ============================================================================

PROTOCOL_VERSION = 1


# ============================================================================
# 内容块类型 (Content Blocks)
# ============================================================================


class TextContentBlock(BaseModel):
    """文本内容块"""

    type: Literal["text"] = "text"
    text: str


class ImageContentBlock(BaseModel):
    """图片内容块"""

    model_config = ConfigDict(populate_by_name=True)

    type: Literal["image"] = "image"
    data: str  # base64 encoded
    media_type: str = Field(alias="mediaType")


class AudioContentBlock(BaseModel):
    """音频内容块"""

    model_config = ConfigDict(populate_by_name=True)

    type: Literal["audio"] = "audio"
    data: str  # base64 encoded
    media_type: str = Field(alias="mediaType")


class ResourceContentBlock(BaseModel):
    """资源链接内容块"""

    model_config = ConfigDict(populate_by_name=True)

    type: Literal["resource"] = "resource"
    uri: str
    name: str | None = None
    mime_type: str | None = Field(None, alias="mimeType")


class EmbeddedResourceContentBlock(BaseModel):
    """嵌入式资源内容块"""

    model_config = ConfigDict(populate_by_name=True)

    type: Literal["embeddedResource"] = "embeddedResource"
    uri: str
    name: str | None = None
    mime_type: str | None = Field(None, alias="mimeType")
    text: str | None = None
    data: str | None = None  # base64 for binary


ContentBlock = (
    TextContentBlock
    | ImageContentBlock
    | AudioContentBlock
    | ResourceContentBlock
    | EmbeddedResourceContentBlock
)


# ============================================================================
# 实现信息 (Implementation)
# ============================================================================


class Implementation(BaseModel):
    """Agent/Client 实现信息"""

    name: str
    title: str | None = None
    version: str


# ============================================================================
# MCP 服务器配置
# ============================================================================


class McpServerStdio(BaseModel):
    """Stdio 类型 MCP 服务器"""

    type: Literal["stdio"] = "stdio"
    command: str
    args: list[str] = []
    env: dict[str, str] = {}


class HttpMcpServer(BaseModel):
    """HTTP 类型 MCP 服务器"""

    type: Literal["http"] = "http"
    url: str
    headers: dict[str, str] = {}


class SseMcpServer(BaseModel):
    """SSE 类型 MCP 服务器"""

    type: Literal["sse"] = "sse"
    url: str
    headers: dict[str, str] = {}


McpServer = McpServerStdio | HttpMcpServer | SseMcpServer


# ============================================================================
# 能力声明 (Capabilities)
# ============================================================================


class PromptCapabilities(BaseModel):
    """Prompt 能力"""

    image: bool = False
    audio: bool = False
    embedded_context: bool = Field(False, alias="embeddedContext")

    model_config = ConfigDict(populate_by_name=True)  # replaces Config class


class McpCapabilities(BaseModel):
    """MCP 能力"""

    http: bool = False
    sse: bool = False
    stdio: bool = True


class ClientCapabilities(BaseModel):
    """客户端能力"""

    # 客户端支持的特性


class AgentCapabilities(BaseModel):
    """Agent 能力"""

    load_session: bool = Field(False, alias="loadSession")
    prompt_capabilities: PromptCapabilities | None = Field(None, alias="promptCapabilities")
    mcp_capabilities: McpCapabilities | None = Field(None, alias="mcpCapabilities")

    model_config = ConfigDict(populate_by_name=True)  # replaces Config class


# ============================================================================
# 停止原因 (Stop Reasons)
# ============================================================================


class StopReason(str, Enum):
    """Agent 停止原因"""

    END_TURN = "end_turn"
    MAX_TOKENS = "max_tokens"
    STOP_SEQUENCE = "stop_sequence"
    TOOL_USE = "tool_use"
    CANCELLED = "cancelled"
    ERROR = "error"


# ============================================================================
# 会话更新类型 (Session Updates)
# ============================================================================


class UserMessageChunk(BaseModel):
    """用户消息块"""

    type: Literal["userMessage"] = "userMessage"
    content: ContentBlock


class AgentMessageChunk(BaseModel):
    """Agent 消息块"""

    type: Literal["agentMessage"] = "agentMessage"
    content: ContentBlock


class AgentThoughtChunk(BaseModel):
    """Agent 思考块"""

    type: Literal["agentThought"] = "agentThought"
    content: TextContentBlock


class ToolCallStart(BaseModel):
    """工具调用开始"""

    type: Literal["toolCallStart"] = "toolCallStart"
    tool_call_id: str = Field(alias="toolCallId")
    tool_name: str = Field(alias="toolName")
    tool_input: dict | None = Field(None, alias="toolInput")

    model_config = ConfigDict(populate_by_name=True)  # replaces Config class


class ToolCallProgress(BaseModel):
    """工具调用进度"""

    type: Literal["toolCallProgress"] = "toolCallProgress"
    tool_call_id: str = Field(alias="toolCallId")
    content: ContentBlock | None = None

    model_config = ConfigDict(populate_by_name=True)  # replaces Config class


class ToolCallUpdate(BaseModel):
    """工具调用更新"""

    tool_call_id: str = Field(alias="toolCallId")
    tool_name: str = Field(alias="toolName")
    tool_input: dict | None = Field(None, alias="toolInput")
    status: Literal["running", "completed", "error"] = "running"

    model_config = ConfigDict(populate_by_name=True)  # replaces Config class


class PlanEntry(BaseModel):
    """计划条目"""

    id: str
    title: str
    status: Literal["pending", "in_progress", "completed", "error"] = "pending"


class AgentPlanUpdate(BaseModel):
    """Agent 计划更新"""

    type: Literal["planUpdate"] = "planUpdate"
    entries: list[PlanEntry]


class ModeInfo(BaseModel):
    """模式信息"""

    id: str
    title: str
    description: str | None = None


class CurrentModeUpdate(BaseModel):
    """当前模式更新"""

    type: Literal["currentMode"] = "currentMode"
    mode: ModeInfo | None = None


class CommandInfo(BaseModel):
    """命令信息"""

    id: str
    title: str
    description: str | None = None


class AvailableCommandsUpdate(BaseModel):
    """可用命令更新"""

    type: Literal["availableCommands"] = "availableCommands"
    commands: list[CommandInfo]


class ConfigOptionUpdate(BaseModel):
    """配置选项更新"""

    type: Literal["configOption"] = "configOption"
    key: str
    value: str | int | bool | None


class SessionInfoUpdate(BaseModel):
    """会话信息更新"""

    type: Literal["sessionInfo"] = "sessionInfo"
    session_id: str = Field(alias="sessionId")
    title: str | None = None
    cwd: str | None = None

    model_config = ConfigDict(populate_by_name=True)  # replaces Config class


SessionUpdate = (
    UserMessageChunk
    | AgentMessageChunk
    | AgentThoughtChunk
    | ToolCallStart
    | ToolCallProgress
    | AgentPlanUpdate
    | CurrentModeUpdate
    | AvailableCommandsUpdate
    | ConfigOptionUpdate
    | SessionInfoUpdate
)


# ============================================================================
# 权限相关
# ============================================================================


class PermissionOption(BaseModel):
    """权限选项"""

    id: str
    title: str
    description: str | None = None
    allow_all: bool = Field(False, alias="allowAll")

    model_config = ConfigDict(populate_by_name=True)  # replaces Config class


class PermissionResponse(BaseModel):
    """权限响应"""

    granted: bool
    option_id: str | None = Field(None, alias="optionId")

    model_config = ConfigDict(populate_by_name=True)  # replaces Config class


# ============================================================================
# 环境变量
# ============================================================================


class EnvVariable(BaseModel):
    """环境变量"""

    name: str
    value: str


# ============================================================================
# JSON-RPC 消息
# ============================================================================


class JsonRpcRequest(BaseModel):
    """JSON-RPC 请求"""

    jsonrpc: Literal["2.0"] = "2.0"
    id: int | str
    method: str
    params: dict | None = None


class JsonRpcResponse(BaseModel):
    """JSON-RPC 响应"""

    jsonrpc: Literal["2.0"] = "2.0"
    id: int | str | None
    result: dict | None = None
    error: dict | None = None


class JsonRpcNotification(BaseModel):
    """JSON-RPC 通知"""

    jsonrpc: Literal["2.0"] = "2.0"
    method: str
    params: dict | None = None


# ============================================================================
# ACP 方法请求/响应
# ============================================================================


class InitializeRequest(BaseModel):
    """初始化请求"""

    protocol_version: int = Field(alias="protocolVersion")
    client_info: Implementation | None = Field(None, alias="clientInfo")
    client_capabilities: ClientCapabilities | None = Field(None, alias="clientCapabilities")

    model_config = ConfigDict(populate_by_name=True)  # replaces Config class


class InitializeResponse(BaseModel):
    """初始化响应"""

    protocol_version: int = Field(alias="protocolVersion")
    agent_info: Implementation | None = Field(None, alias="agentInfo")
    agent_capabilities: AgentCapabilities | None = Field(None, alias="agentCapabilities")

    model_config = ConfigDict(populate_by_name=True)  # replaces Config class


class NewSessionRequest(BaseModel):
    """新建会话请求"""

    cwd: str
    mcp_servers: list[McpServer] = Field([], alias="mcpServers")

    model_config = ConfigDict(populate_by_name=True)  # replaces Config class


class NewSessionResponse(BaseModel):
    """新建会话响应"""

    session_id: str = Field(alias="sessionId")
    modes: list[ModeInfo] | None = None

    model_config = ConfigDict(populate_by_name=True)  # replaces Config class


class LoadSessionRequest(BaseModel):
    """加载会话请求"""

    session_id: str = Field(alias="sessionId")
    cwd: str
    mcp_servers: list[McpServer] = Field([], alias="mcpServers")

    model_config = ConfigDict(populate_by_name=True)  # replaces Config class


class LoadSessionResponse(BaseModel):
    """加载会话响应"""

    modes: list[ModeInfo] | None = None


class PromptRequest(BaseModel):
    """Prompt 请求"""

    session_id: str = Field(alias="sessionId")
    prompt: list[ContentBlock]

    model_config = ConfigDict(populate_by_name=True)  # replaces Config class


class PromptResponse(BaseModel):
    """Prompt 响应"""

    stop_reason: StopReason | str = Field(alias="stopReason")

    model_config = ConfigDict(populate_by_name=True)  # replaces Config class


class CancelNotification(BaseModel):
    """取消通知"""

    session_id: str = Field(alias="sessionId")

    model_config = ConfigDict(populate_by_name=True)  # replaces Config class


class SessionNotification(BaseModel):
    """会话更新通知"""

    session_id: str = Field(alias="sessionId")
    update: SessionUpdate

    model_config = ConfigDict(populate_by_name=True)  # replaces Config class


class RequestPermissionRequest(BaseModel):
    """请求权限"""

    session_id: str = Field(alias="sessionId")
    tool_call: ToolCallUpdate = Field(alias="toolCall")
    options: list[PermissionOption]

    model_config = ConfigDict(populate_by_name=True)  # replaces Config class


class RequestPermissionResponse(BaseModel):
    """权限响应"""

    granted: bool
    option_id: str | None = Field(None, alias="optionId")

    model_config = ConfigDict(populate_by_name=True)  # replaces Config class


class ReadTextFileRequest(BaseModel):
    """读取文本文件请求"""

    session_id: str = Field(alias="sessionId")
    path: str
    line: int | None = None
    limit: int | None = None

    model_config = ConfigDict(populate_by_name=True)  # replaces Config class


class ReadTextFileResponse(BaseModel):
    """读取文本文件响应"""

    content: str
    truncated: bool = False


class WriteTextFileRequest(BaseModel):
    """写入文本文件请求"""

    session_id: str = Field(alias="sessionId")
    path: str
    content: str

    model_config = ConfigDict(populate_by_name=True)  # replaces Config class


class WriteTextFileResponse(BaseModel):
    """写入文本文件响应"""

    success: bool = True


class SetSessionModeRequest(BaseModel):
    """设置会话模式请求"""

    session_id: str = Field(alias="sessionId")
    mode_id: str = Field(alias="modeId")

    model_config = ConfigDict(populate_by_name=True)  # replaces Config class


class SetSessionModeResponse(BaseModel):
    """设置会话模式响应"""

    success: bool = True


class SetSessionModelRequest(BaseModel):
    """设置会话模型请求"""

    session_id: str = Field(alias="sessionId")
    model_id: str = Field(alias="modelId")

    model_config = ConfigDict(populate_by_name=True)  # replaces Config class


class SetSessionModelResponse(BaseModel):
    """设置会话模型响应"""

    success: bool = True


# ============================================================================
# 终端相关
# ============================================================================


class CreateTerminalRequest(BaseModel):
    """创建终端请求"""

    session_id: str = Field(alias="sessionId")
    command: str
    args: list[str] = []
    cwd: str | None = None
    env: list[EnvVariable] | None = None
    output_byte_limit: int | None = Field(None, alias="outputByteLimit")

    model_config = ConfigDict(populate_by_name=True)  # replaces Config class


class CreateTerminalResponse(BaseModel):
    """创建终端响应"""

    terminal_id: str = Field(alias="terminalId")

    model_config = ConfigDict(populate_by_name=True)  # replaces Config class


class TerminalOutputRequest(BaseModel):
    """终端输出请求"""

    session_id: str = Field(alias="sessionId")
    terminal_id: str = Field(alias="terminalId")

    model_config = ConfigDict(populate_by_name=True)  # replaces Config class


class TerminalOutputResponse(BaseModel):
    """终端输出响应"""

    output: str
    exited: bool = False
    exit_code: int | None = Field(None, alias="exitCode")

    model_config = ConfigDict(populate_by_name=True)  # replaces Config class


class WaitForTerminalExitRequest(BaseModel):
    """等待终端退出请求"""

    session_id: str = Field(alias="sessionId")
    terminal_id: str = Field(alias="terminalId")

    model_config = ConfigDict(populate_by_name=True)  # replaces Config class


class WaitForTerminalExitResponse(BaseModel):
    """等待终端退出响应"""

    exit_code: int = Field(alias="exitCode")

    model_config = ConfigDict(populate_by_name=True)  # replaces Config class


class KillTerminalCommandRequest(BaseModel):
    """终止终端请求"""

    session_id: str = Field(alias="sessionId")
    terminal_id: str = Field(alias="terminalId")

    model_config = ConfigDict(populate_by_name=True)  # replaces Config class


class KillTerminalCommandResponse(BaseModel):
    """终止终端响应"""

    success: bool = True


class ReleaseTerminalRequest(BaseModel):
    """释放终端请求"""

    session_id: str = Field(alias="sessionId")
    terminal_id: str = Field(alias="terminalId")

    model_config = ConfigDict(populate_by_name=True)  # replaces Config class


class ReleaseTerminalResponse(BaseModel):
    """释放终端响应"""

    success: bool = True
