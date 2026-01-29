"""Built-in tools (22 native tools).

This module provides all native tools for the LurkBot agent:

P0 - Core tools (✅ Implemented):
- exec: Execute shell commands
- process: Manage background processes
- read: Read file contents
- write: Write to files
- edit: Edit files with search/replace
- apply_patch: Apply unified diff patches

P1 - Session tools (✅ Implemented):
- sessions_spawn: Create new agent sessions
- sessions_send: Send messages to sessions
- sessions_list: List agent sessions
- sessions_history: Get session history
- session_status: Get session status
- agents_list: List available agents

P1 - Memory tools (✅ Implemented):
- memory_search: Semantic search in memory
- memory_get: Read from memory files

P1 - Web tools (✅ Implemented):
- web_search: Search the web
- web_fetch: Fetch web page content

P1 - Message tool (✅ Implemented):
- message: Send messages to channels

P1 - Automation tools (✅ Implemented):
- cron: Scheduled tasks management
- gateway: Gateway API communication

P2 - Media tools (✅ Implemented):
- image: Image understanding and generation

P2 - System tools (✅ Implemented):
- nodes: Node discovery and management
- tts: Text-to-speech synthesis

P2 - Pending tools:
- browser: Browser automation (depends on Playwright)
- canvas: Canvas drawing (depends on A2UI)
"""

from lurkbot.tools.builtin.common import (
    # Types
    ActionGate,
    ParamError,
    ToolResult,
    ToolResultContent,
    ToolResultContentType,
    # Result helpers
    error_result,
    image_result,
    json_result,
    text_result,
    # Parameter helpers
    read_bool_param,
    read_dict_param,
    read_number_param,
    read_string_array_param,
    read_string_or_number_param,
    read_string_param,
    # Utility functions
    chunk_string,
    clamp_number,
    coerce_env,
    create_action_gate,
    truncate_middle,
)
from lurkbot.tools.builtin.exec_tool import (
    # Types
    ExecAsk,
    ExecHost,
    ExecSecurity,
    ExecStatus,
    ExecToolDefaults,
    ExecParams,
    ProcessParams,
    ProcessSession,
    # Functions
    exec_tool,
    process_tool,
    create_exec_tool,
    create_process_tool,
    # Session registry
    add_session,
    get_session,
    remove_session,
    kill_session,
)
from lurkbot.tools.builtin.fs_safe import (
    SafeOpenError,
    SafeOpenErrorCode,
    SafeOpenResult,
    is_path_within_root,
    open_file_within_root,
    open_file_within_root_sync,
    resolve_safe_path,
)
from lurkbot.tools.builtin.fs_tools import (
    # Types
    ReadParams,
    WriteParams,
    EditParams,
    ApplyPatchParams,
    # Functions
    read_tool,
    write_tool,
    edit_tool,
    apply_patch_tool,
    create_read_tool,
    create_write_tool,
    create_edit_tool,
    create_apply_patch_tool,
)
from lurkbot.tools.builtin.memory_tools import (
    # Types
    MemorySearchParams,
    MemoryGetParams,
    MemorySearchConfig,
    MemorySearchResult,
    MemoryManager,
    # Functions
    memory_search_tool,
    memory_get_tool,
    get_memory_manager,
    create_memory_search_tool,
    create_memory_get_tool,
)
from lurkbot.tools.builtin.web_tools import (
    # Types
    WebFetchParams,
    WebSearchParams,
    WebFetchConfig,
    WebSearchConfig,
    SearchResult,
    # Functions
    web_fetch_tool,
    web_search_tool,
    html_to_markdown,
    create_web_fetch_tool,
    create_web_search_tool,
)
from lurkbot.tools.builtin.message_tool import (
    # Types
    MessageAction,
    MessageConfig,
    MessageChannel,
    MessageParams,
    # Functions
    message_tool,
    register_channel,
    get_channel,
    create_message_tool,
    # Channel classes
    CLIChannel,
)
from lurkbot.tools.builtin.cron_tool import (
    # Types
    CronJob,
    CronJobState,
    CronParams,
    CronRunResult,
    CronSchedule,
    CronServiceStatus,
    # Functions
    cron_tool,
    create_cron_tool,
    get_cron_store,
)
from lurkbot.tools.builtin.gateway_tool import (
    # Types
    GatewayConnection,
    GatewayError,
    GatewayParams,
    GatewayRequest,
    GatewayResponse,
    # Functions
    gateway_tool,
    create_gateway_tool,
    call_gateway,
    configure_gateway,
    get_gateway,
)
from lurkbot.tools.builtin.image_tool import (
    # Types
    ImageParams,
    ImageToolConfig,
    # Functions
    image_tool,
    create_image_tool,
    configure_image_tool,
    get_image_config,
)
from lurkbot.tools.builtin.nodes_tool import (
    # Types
    NodeExecResult,
    NodeInfo,
    NodeRegistry,
    NodesParams,
    # Functions
    nodes_tool,
    create_nodes_tool,
    get_node_registry,
)
from lurkbot.tools.builtin.tts_tool import (
    # Types
    TTSConfig,
    TTSDirective,
    TTSParams,
    TTSResult,
    TTSVoice,
    # Functions
    tts_tool,
    create_tts_tool,
    configure_tts,
    get_tts_config,
)
from lurkbot.tools.builtin.session_tools import (
    # Types
    SessionsSpawnParams,
    SessionsSendParams,
    SessionsListParams,
    SessionsHistoryParams,
    SessionStatusParams,
    AgentsListParams,
    # Functions
    sessions_spawn_tool,
    sessions_send_tool,
    sessions_list_tool,
    sessions_history_tool,
    session_status_tool,
    agents_list_tool,
    # Factory functions
    create_sessions_spawn_tool,
    create_sessions_send_tool,
    create_sessions_list_tool,
    create_sessions_history_tool,
    create_session_status_tool,
    create_agents_list_tool,
)

__all__ = [
    # Common types
    "ActionGate",
    "ParamError",
    "ToolResult",
    "ToolResultContent",
    "ToolResultContentType",
    # Common result helpers
    "error_result",
    "image_result",
    "json_result",
    "text_result",
    # Common parameter helpers
    "read_bool_param",
    "read_dict_param",
    "read_number_param",
    "read_string_array_param",
    "read_string_or_number_param",
    "read_string_param",
    # Common utility functions
    "chunk_string",
    "clamp_number",
    "coerce_env",
    "create_action_gate",
    "truncate_middle",
    # Exec tool
    "ExecAsk",
    "ExecHost",
    "ExecSecurity",
    "ExecStatus",
    "ExecToolDefaults",
    "ExecParams",
    "ProcessParams",
    "ProcessSession",
    "exec_tool",
    "process_tool",
    "create_exec_tool",
    "create_process_tool",
    "add_session",
    "get_session",
    "remove_session",
    "kill_session",
    # FS safe
    "SafeOpenError",
    "SafeOpenErrorCode",
    "SafeOpenResult",
    "is_path_within_root",
    "open_file_within_root",
    "open_file_within_root_sync",
    "resolve_safe_path",
    # FS tools
    "ReadParams",
    "WriteParams",
    "EditParams",
    "ApplyPatchParams",
    "read_tool",
    "write_tool",
    "edit_tool",
    "apply_patch_tool",
    "create_read_tool",
    "create_write_tool",
    "create_edit_tool",
    "create_apply_patch_tool",
    # Memory tools
    "MemorySearchParams",
    "MemoryGetParams",
    "MemorySearchConfig",
    "MemorySearchResult",
    "MemoryManager",
    "memory_search_tool",
    "memory_get_tool",
    "get_memory_manager",
    "create_memory_search_tool",
    "create_memory_get_tool",
    # Web tools
    "WebFetchParams",
    "WebSearchParams",
    "WebFetchConfig",
    "WebSearchConfig",
    "SearchResult",
    "web_fetch_tool",
    "web_search_tool",
    "html_to_markdown",
    "create_web_fetch_tool",
    "create_web_search_tool",
    # Message tool
    "MessageAction",
    "MessageConfig",
    "MessageChannel",
    "MessageParams",
    "message_tool",
    "register_channel",
    "get_channel",
    "create_message_tool",
    "CLIChannel",
    # Session tools
    "SessionsSpawnParams",
    "SessionsSendParams",
    "SessionsListParams",
    "SessionsHistoryParams",
    "SessionStatusParams",
    "AgentsListParams",
    "sessions_spawn_tool",
    "sessions_send_tool",
    "sessions_list_tool",
    "sessions_history_tool",
    "session_status_tool",
    "agents_list_tool",
    "create_sessions_spawn_tool",
    "create_sessions_send_tool",
    "create_sessions_list_tool",
    "create_sessions_history_tool",
    "create_session_status_tool",
    "create_agents_list_tool",
]
