"""Agent runtime and execution.

This module contains the core agent infrastructure for LurkBot:
- types.py: Core data types (AgentContext, AgentRunResult, etc.)
- runtime.py: PydanticAI Agent runtime (run_embedded_agent)
- api.py: FastAPI HTTP/SSE endpoints
- bootstrap.py: Bootstrap file system (8 files)
- system_prompt.py: System prompt generator (23 sections)
- compaction.py: Context compaction [TODO]
- subagent.py: Subagent communication [TODO]
"""

from lurkbot.agents.types import (
    AgentContext,
    AgentRunResult,
    PromptMode,
    SessionType,
    StreamEvent,
    ThinkLevel,
    ToolResultFormat,
    VerboseLevel,
    build_session_key,
    parse_session_key,
)

from lurkbot.agents.runtime import (
    AgentDependencies,
    create_agent,
    resolve_model_id,
    run_embedded_agent,
    run_embedded_agent_events,
    run_embedded_agent_stream,
)

from lurkbot.agents.api import (
    ChatRequest,
    ChatResponse,
    create_app,
    create_chat_api,
)

from lurkbot.agents.bootstrap import (
    AGENTS_FILENAME,
    BOOTSTRAP_FILENAME,
    BootstrapFile,
    ContextFile,
    DEFAULT_BOOTSTRAP_MAX_CHARS,
    HEARTBEAT_FILENAME,
    IDENTITY_FILENAME,
    MEMORY_FILENAME,
    SOUL_FILENAME,
    SUBAGENT_BOOTSTRAP_ALLOWLIST,
    TOOLS_FILENAME,
    USER_FILENAME,
    build_bootstrap_context_files,
    ensure_agent_workspace,
    filter_bootstrap_files_for_session,
    get_default_workspace_dir,
    is_subagent_session_key,
    load_workspace_bootstrap_files,
    resolve_bootstrap_context_for_run,
    resolve_bootstrap_files_for_run,
    trim_bootstrap_content,
)

from lurkbot.agents.system_prompt import (
    CHAT_CHANNEL_ORDER,
    CORE_TOOL_SUMMARIES,
    DEFAULT_HEARTBEAT_PROMPT,
    HEARTBEAT_TOKEN,
    INTERNAL_MESSAGE_CHANNEL,
    MARKDOWN_CAPABLE_CHANNELS,
    SILENT_REPLY_TOKEN,
    TOOL_ORDER,
    ReactionGuidance,
    RuntimeInfo,
    SandboxInfo,
    SystemPromptParams,
    build_agent_system_prompt,
    build_runtime_line,
    is_silent_reply_text,
    list_deliverable_message_channels,
)

__all__ = [
    # Types
    "AgentContext",
    "AgentDependencies",
    "AgentRunResult",
    "PromptMode",
    "SessionType",
    "StreamEvent",
    "ThinkLevel",
    "ToolResultFormat",
    "VerboseLevel",
    # Session key utilities
    "build_session_key",
    "parse_session_key",
    # Runtime functions
    "create_agent",
    "resolve_model_id",
    "run_embedded_agent",
    "run_embedded_agent_events",
    "run_embedded_agent_stream",
    # API
    "ChatRequest",
    "ChatResponse",
    "create_app",
    "create_chat_api",
    # Bootstrap - Constants
    "AGENTS_FILENAME",
    "BOOTSTRAP_FILENAME",
    "DEFAULT_BOOTSTRAP_MAX_CHARS",
    "HEARTBEAT_FILENAME",
    "IDENTITY_FILENAME",
    "MEMORY_FILENAME",
    "SOUL_FILENAME",
    "SUBAGENT_BOOTSTRAP_ALLOWLIST",
    "TOOLS_FILENAME",
    "USER_FILENAME",
    # Bootstrap - Types
    "BootstrapFile",
    "ContextFile",
    # Bootstrap - Functions
    "build_bootstrap_context_files",
    "ensure_agent_workspace",
    "filter_bootstrap_files_for_session",
    "get_default_workspace_dir",
    "is_subagent_session_key",
    "load_workspace_bootstrap_files",
    "resolve_bootstrap_context_for_run",
    "resolve_bootstrap_files_for_run",
    "trim_bootstrap_content",
    # System Prompt - Constants
    "CHAT_CHANNEL_ORDER",
    "CORE_TOOL_SUMMARIES",
    "DEFAULT_HEARTBEAT_PROMPT",
    "HEARTBEAT_TOKEN",
    "INTERNAL_MESSAGE_CHANNEL",
    "MARKDOWN_CAPABLE_CHANNELS",
    "SILENT_REPLY_TOKEN",
    "TOOL_ORDER",
    # System Prompt - Types
    "ReactionGuidance",
    "RuntimeInfo",
    "SandboxInfo",
    "SystemPromptParams",
    # System Prompt - Functions
    "build_agent_system_prompt",
    "build_runtime_line",
    "is_silent_reply_text",
    "list_deliverable_message_channels",
]
