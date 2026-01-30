"""
ACP (Agent Client Protocol) 协议系统

实现 LurkBot 与 IDE 集成的标准协议
基于官方 ACP Python SDK (agent-client-protocol) 的设计

对标 MoltBot src/acp/ (基于 @agentclientprotocol/sdk)

架构:
    IDE (stdIO) ↔ ACPServer ↔ ACPGatewayTranslator ↔ Gateway

主要组件:
    - server.py: ACP 服务器（ndJSON 双向流通信）
    - translator.py: 协议翻译器（ACP <-> Gateway）
    - session.py: 会话管理
    - event_mapper.py: 事件映射
    - types.py: ACP 类型定义
"""

from lurkbot.acp.types import (
    # 协议版本
    PROTOCOL_VERSION,
    # 内容块
    TextContentBlock,
    ImageContentBlock,
    AudioContentBlock,
    ResourceContentBlock,
    EmbeddedResourceContentBlock,
    ContentBlock,
    # 实现信息
    Implementation,
    # MCP 服务器
    McpServerStdio,
    HttpMcpServer,
    SseMcpServer,
    McpServer,
    # 能力声明
    PromptCapabilities,
    McpCapabilities,
    ClientCapabilities,
    AgentCapabilities,
    # 停止原因
    StopReason,
    # 会话更新
    UserMessageChunk,
    AgentMessageChunk,
    AgentThoughtChunk,
    ToolCallStart,
    ToolCallProgress,
    ToolCallUpdate,
    AgentPlanUpdate,
    CurrentModeUpdate,
    AvailableCommandsUpdate,
    ConfigOptionUpdate,
    SessionInfoUpdate,
    SessionUpdate,
    PlanEntry,
    ModeInfo,
    CommandInfo,
    # 权限
    PermissionOption,
    PermissionResponse,
    # 环境变量
    EnvVariable,
    # JSON-RPC
    JsonRpcRequest,
    JsonRpcResponse,
    JsonRpcNotification,
    # 请求/响应
    InitializeRequest,
    InitializeResponse,
    NewSessionRequest,
    NewSessionResponse,
    LoadSessionRequest,
    LoadSessionResponse,
    PromptRequest,
    PromptResponse,
    CancelNotification,
    SessionNotification,
    RequestPermissionRequest,
    RequestPermissionResponse,
    ReadTextFileRequest,
    ReadTextFileResponse,
    WriteTextFileRequest,
    WriteTextFileResponse,
    SetSessionModeRequest,
    SetSessionModeResponse,
    SetSessionModelRequest,
    SetSessionModelResponse,
    # 终端
    CreateTerminalRequest,
    CreateTerminalResponse,
    TerminalOutputRequest,
    TerminalOutputResponse,
    WaitForTerminalExitRequest,
    WaitForTerminalExitResponse,
    KillTerminalCommandRequest,
    KillTerminalCommandResponse,
    ReleaseTerminalRequest,
    ReleaseTerminalResponse,
)

from lurkbot.acp.session import (
    ACPSession,
    PendingPrompt,
    ACPSessionManager,
    get_session_manager,
)

from lurkbot.acp.event_mapper import (
    EventMapper,
    get_event_mapper,
    # 辅助函数
    text_block,
    update_agent_message,
    update_user_message,
    update_agent_thought,
    start_tool_call,
    update_plan,
    plan_entry,
)

from lurkbot.acp.translator import (
    ACPGatewayTranslator,
    get_translator,
)

from lurkbot.acp.server import (
    ACPServer,
    get_acp_server,
    run_acp_server,
)

__all__ = [
    # 协议版本
    "PROTOCOL_VERSION",
    # 内容块
    "TextContentBlock",
    "ImageContentBlock",
    "AudioContentBlock",
    "ResourceContentBlock",
    "EmbeddedResourceContentBlock",
    "ContentBlock",
    # 实现信息
    "Implementation",
    # MCP 服务器
    "McpServerStdio",
    "HttpMcpServer",
    "SseMcpServer",
    "McpServer",
    # 能力声明
    "PromptCapabilities",
    "McpCapabilities",
    "ClientCapabilities",
    "AgentCapabilities",
    # 停止原因
    "StopReason",
    # 会话更新
    "UserMessageChunk",
    "AgentMessageChunk",
    "AgentThoughtChunk",
    "ToolCallStart",
    "ToolCallProgress",
    "ToolCallUpdate",
    "AgentPlanUpdate",
    "CurrentModeUpdate",
    "AvailableCommandsUpdate",
    "ConfigOptionUpdate",
    "SessionInfoUpdate",
    "SessionUpdate",
    "PlanEntry",
    "ModeInfo",
    "CommandInfo",
    # 权限
    "PermissionOption",
    "PermissionResponse",
    # 环境变量
    "EnvVariable",
    # JSON-RPC
    "JsonRpcRequest",
    "JsonRpcResponse",
    "JsonRpcNotification",
    # 请求/响应
    "InitializeRequest",
    "InitializeResponse",
    "NewSessionRequest",
    "NewSessionResponse",
    "LoadSessionRequest",
    "LoadSessionResponse",
    "PromptRequest",
    "PromptResponse",
    "CancelNotification",
    "SessionNotification",
    "RequestPermissionRequest",
    "RequestPermissionResponse",
    "ReadTextFileRequest",
    "ReadTextFileResponse",
    "WriteTextFileRequest",
    "WriteTextFileResponse",
    "SetSessionModeRequest",
    "SetSessionModeResponse",
    "SetSessionModelRequest",
    "SetSessionModelResponse",
    # 终端
    "CreateTerminalRequest",
    "CreateTerminalResponse",
    "TerminalOutputRequest",
    "TerminalOutputResponse",
    "WaitForTerminalExitRequest",
    "WaitForTerminalExitResponse",
    "KillTerminalCommandRequest",
    "KillTerminalCommandResponse",
    "ReleaseTerminalRequest",
    "ReleaseTerminalResponse",
    # 会话管理
    "ACPSession",
    "PendingPrompt",
    "ACPSessionManager",
    "get_session_manager",
    # 事件映射
    "EventMapper",
    "get_event_mapper",
    # 辅助函数
    "text_block",
    "update_agent_message",
    "update_user_message",
    "update_agent_thought",
    "start_tool_call",
    "update_plan",
    "plan_entry",
    # 翻译器
    "ACPGatewayTranslator",
    "get_translator",
    # 服务器
    "ACPServer",
    "get_acp_server",
    "run_acp_server",
]
