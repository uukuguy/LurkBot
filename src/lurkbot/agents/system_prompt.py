"""System prompt generator for LurkBot agent.

This module generates the complete system prompt following MoltBot's 23-section structure.
Each section is conditionally included based on prompt mode and available features.

Reference: moltbot/src/agents/system-prompt.ts
"""

from dataclasses import dataclass, field
from typing import Any, Literal

from lurkbot.agents.bootstrap import ContextFile
from lurkbot.agents.types import PromptMode, ThinkLevel


# Token constants (from MoltBot's auto-reply/tokens.ts)
SILENT_REPLY_TOKEN = "NO_REPLY"
HEARTBEAT_TOKEN = "HEARTBEAT_OK"

# Default heartbeat prompt (from MoltBot's auto-reply/heartbeat.ts)
DEFAULT_HEARTBEAT_PROMPT = (
    "Read HEARTBEAT.md if it exists (workspace context). Follow it strictly. "
    "Do not infer or repeat old tasks from prior chats. If nothing needs attention, "
    "reply HEARTBEAT_OK."
)

# Channel definitions (from MoltBot's channels/registry.ts)
CHAT_CHANNEL_ORDER = [
    "telegram",
    "whatsapp",
    "discord",
    "googlechat",
    "slack",
    "signal",
    "imessage",
]

INTERNAL_MESSAGE_CHANNEL = "webchat"

# Markdown-capable channels
MARKDOWN_CAPABLE_CHANNELS = {
    "slack",
    "telegram",
    "signal",
    "discord",
    "googlechat",
    "tui",
    INTERNAL_MESSAGE_CHANNEL,
}

# Core tool summaries (from MoltBot's system-prompt.ts)
CORE_TOOL_SUMMARIES: dict[str, str] = {
    "read": "Read file contents",
    "write": "Create or overwrite files",
    "edit": "Make precise edits to files",
    "apply_patch": "Apply multi-file patches",
    "grep": "Search file contents for patterns",
    "find": "Find files by glob pattern",
    "ls": "List directory contents",
    "exec": "Run shell commands (pty available for TTY-required CLIs)",
    "process": "Manage background exec sessions",
    "web_search": "Search the web (Brave API)",
    "web_fetch": "Fetch and extract readable content from a URL",
    "browser": "Control web browser",
    "canvas": "Present/eval/snapshot the Canvas",
    "nodes": "List/describe/notify/camera/screen on paired nodes",
    "cron": (
        "Manage cron jobs and wake events (use for reminders; when scheduling a "
        "reminder, write the systemEvent text as something that will read like a "
        "reminder when it fires, and mention that it is a reminder depending on "
        "the time gap between setting and firing; include recent context in "
        "reminder text if appropriate)"
    ),
    "message": "Send messages and channel actions",
    "gateway": "Restart, apply config, or run updates on the running LurkBot process",
    "agents_list": "List agent ids allowed for sessions_spawn",
    "sessions_list": "List other sessions (incl. sub-agents) with filters/last",
    "sessions_history": "Fetch history for another session/sub-agent",
    "sessions_send": "Send a message to another session/sub-agent",
    "sessions_spawn": "Spawn a sub-agent session",
    "session_status": (
        "Show a /status-equivalent status card (usage + time + Reasoning/Verbose/Elevated); "
        "use for model-use questions (📊 session_status); optional per-session model override"
    ),
    "image": "Analyze an image with the configured image model",
}

# Tool ordering (core tools first, then extras alphabetically)
TOOL_ORDER = [
    "read",
    "write",
    "edit",
    "apply_patch",
    "grep",
    "find",
    "ls",
    "exec",
    "process",
    "web_search",
    "web_fetch",
    "browser",
    "canvas",
    "nodes",
    "cron",
    "message",
    "gateway",
    "agents_list",
    "sessions_list",
    "sessions_history",
    "sessions_send",
    "session_status",
    "image",
]


@dataclass
class RuntimeInfo:
    """Runtime information for the agent."""

    agent_id: str | None = None
    host: str | None = None
    os: str | None = None
    arch: str | None = None
    node: str | None = None  # Python version for LurkBot
    model: str | None = None
    default_model: str | None = None
    channel: str | None = None
    capabilities: list[str] = field(default_factory=list)
    repo_root: str | None = None


@dataclass
class SandboxInfo:
    """Sandbox environment information."""

    enabled: bool = False
    workspace_dir: str | None = None
    workspace_access: Literal["none", "ro", "rw"] | None = None
    agent_workspace_mount: str | None = None
    browser_bridge_url: str | None = None
    browser_novnc_url: str | None = None
    host_browser_allowed: bool | None = None
    elevated_allowed: bool = False
    elevated_default_level: Literal["on", "off", "ask", "full"] = "off"


@dataclass
class ReactionGuidance:
    """Reaction guidance configuration."""

    level: Literal["minimal", "extensive"]
    channel: str


@dataclass
class SystemPromptParams:
    """Parameters for system prompt generation.

    Matches MoltBot's buildAgentSystemPrompt params.
    """

    # Required
    workspace_dir: str

    # Optional - Core Configuration
    default_think_level: ThinkLevel = ThinkLevel.MEDIUM
    reasoning_level: Literal["off", "on", "stream"] = "off"
    extra_system_prompt: str | None = None

    # Optional - User Information
    owner_numbers: list[str] = field(default_factory=list)
    user_timezone: str | None = None

    # Optional - Tools & Skills
    tool_names: list[str] = field(default_factory=list)
    tool_summaries: dict[str, str] = field(default_factory=dict)
    skills_prompt: str | None = None

    # Optional - Models & Reasoning
    model_alias_lines: list[str] = field(default_factory=list)
    reasoning_tag_hint: bool = False

    # Optional - Context Files
    context_files: list[ContextFile] = field(default_factory=list)

    # Optional - Features
    heartbeat_prompt: str | None = None
    docs_path: str | None = None
    workspace_notes: list[str] = field(default_factory=list)
    tts_hint: str | None = None
    message_tool_hints: list[str] = field(default_factory=list)

    # Optional - Prompt Mode
    prompt_mode: PromptMode = PromptMode.FULL

    # Optional - Runtime Info
    runtime_info: RuntimeInfo | None = None

    # Optional - Sandbox Environment
    sandbox_info: SandboxInfo | None = None

    # Optional - Reactions Guidance
    reaction_guidance: ReactionGuidance | None = None


def list_deliverable_message_channels() -> list[str]:
    """List all deliverable message channels.

    Returns the core channel IDs. Plugin channels would be added dynamically.
    """
    return list(CHAT_CHANNEL_ORDER)


def _build_skills_section(
    skills_prompt: str | None,
    is_minimal: bool,
    read_tool_name: str,
) -> list[str]:
    """Build the Skills section (section 5).

    如果 skills_prompt 为空，尝试自动从 SkillManager 加载技能列表。
    """
    if is_minimal:
        return []

    # 尝试使用提供的 skills_prompt
    trimmed = skills_prompt.strip() if skills_prompt else ""

    # 如果没有提供 skills_prompt，尝试自动生成
    if not trimmed:
        try:
            from lurkbot.skills import get_skill_manager

            manager = get_skill_manager()
            model_invocable_skills = manager.registry.find_model_invocable()

            if model_invocable_skills:
                # 生成技能列表
                skill_lines = ["<available_skills>"]
                for skill in model_invocable_skills:
                    location = str(skill.file_path)
                    description = skill.frontmatter.description
                    skill_lines.append(f"- {skill.key}: {description}")
                    skill_lines.append(f"  <location>{location}</location>")
                skill_lines.append("</available_skills>")
                trimmed = "\n".join(skill_lines)
        except Exception:
            # 如果加载失败，跳过技能章节
            return []

    if not trimmed:
        return []

    return [
        "## Skills (mandatory)",
        "Before replying: scan <available_skills> <description> entries.",
        f"- If exactly one skill clearly applies: read its SKILL.md at <location> with `{read_tool_name}`, then follow it.",
        "- If multiple could apply: choose the most specific one, then read/follow it.",
        "- If none clearly apply: do not read any SKILL.md.",
        "Constraints: never read more than one skill up front; only read after selecting.",
        trimmed,
        "",
    ]


def _build_memory_section(
    is_minimal: bool,
    available_tools: set[str],
) -> list[str]:
    """Build the Memory Recall section (section 6)."""
    if is_minimal:
        return []
    if "memory_search" not in available_tools and "memory_get" not in available_tools:
        return []
    return [
        "## Memory Recall",
        "Before answering anything about prior work, decisions, dates, people, preferences, "
        "or todos: run memory_search on MEMORY.md + memory/*.md; then use memory_get to pull "
        "only the needed lines. If low confidence after search, say you checked.",
        "",
    ]


def _build_user_identity_section(
    owner_line: str | None,
    is_minimal: bool,
) -> list[str]:
    """Build the User Identity section (section 12)."""
    if not owner_line or is_minimal:
        return []
    return ["## User Identity", owner_line, ""]


def _build_time_section(user_timezone: str | None) -> list[str]:
    """Build the Current Date & Time section (section 13)."""
    if not user_timezone:
        return []
    return ["## Current Date & Time", f"Time zone: {user_timezone}", ""]


def _build_reply_tags_section(is_minimal: bool) -> list[str]:
    """Build the Reply Tags section (section 15)."""
    if is_minimal:
        return []
    return [
        "## Reply Tags",
        "To request a native reply/quote on supported surfaces, include one tag in your reply:",
        "- [[reply_to_current]] replies to the triggering message.",
        "- [[reply_to:<id>]] replies to a specific message id when you have it.",
        "Whitespace inside the tag is allowed (e.g. [[ reply_to_current ]] / [[ reply_to: 123 ]]).",
        "Tags are stripped before sending; support depends on the current channel config.",
        "",
    ]


def _build_messaging_section(
    is_minimal: bool,
    available_tools: set[str],
    message_channel_options: str,
    inline_buttons_enabled: bool,
    runtime_channel: str | None,
    message_tool_hints: list[str] | None,
) -> list[str]:
    """Build the Messaging section (section 16)."""
    if is_minimal:
        return []

    lines = [
        "## Messaging",
        "- Reply in current session → automatically routes to the source channel (Signal, Telegram, etc.)",
        "- Cross-session messaging → use sessions_send(sessionKey, message)",
        "- Never use exec/curl for provider messaging; LurkBot handles all routing internally.",
    ]

    if "message" in available_tools:
        message_lines = [
            "",
            "### message tool",
            "- Use `message` for proactive sends + channel actions (polls, reactions, etc.).",
            "- For `action=send`, include `to` and `message`.",
            f"- If multiple channels are configured, pass `channel` ({message_channel_options}).",
            f"- If you use `message` (`action=send`) to deliver your user-visible reply, "
            f"respond with ONLY: {SILENT_REPLY_TOKEN} (avoid duplicate replies).",
        ]

        if inline_buttons_enabled:
            message_lines.append(
                "- Inline buttons supported. Use `action=send` with `buttons=[[{text,callback_data}]]` "
                "(callback_data routes back as a user message)."
            )
        elif runtime_channel:
            message_lines.append(
                f"- Inline buttons not enabled for {runtime_channel}. If you need them, "
                f"ask to set {runtime_channel}.capabilities.inlineButtons "
                '("dm"|"group"|"all"|"allowlist").'
            )

        if message_tool_hints:
            message_lines.extend(message_tool_hints)

        lines.append("\n".join(line for line in message_lines if line))

    lines.append("")
    return lines


def _build_voice_section(is_minimal: bool, tts_hint: str | None) -> list[str]:
    """Build the Voice (TTS) section (section 17)."""
    if is_minimal:
        return []
    hint = tts_hint.strip() if tts_hint else ""
    if not hint:
        return []
    return ["## Voice (TTS)", hint, ""]


def _build_docs_section(
    docs_path: str | None,
    is_minimal: bool,
    read_tool_name: str,
) -> list[str]:
    """Build the Documentation section (section 10)."""
    trimmed_path = docs_path.strip() if docs_path else ""
    if not trimmed_path or is_minimal:
        return []
    return [
        "## Documentation",
        f"LurkBot docs: {trimmed_path}",
        "Mirror: https://docs.molt.bot",
        "Source: https://github.com/moltbot/moltbot",
        "Community: https://discord.com/invite/clawd",
        "Find new skills: https://clawdhub.com",
        "For LurkBot behavior, commands, config, or architecture: consult local docs first.",
        "When diagnosing issues, run `lurkbot status` yourself when possible; "
        "only ask the user if you lack access (e.g., sandboxed).",
        "",
    ]


def build_runtime_line(
    runtime_info: RuntimeInfo | None,
    runtime_channel: str | None,
    runtime_capabilities: list[str],
    default_think_level: ThinkLevel,
) -> str:
    """Build the Runtime info line (section 24).

    Format: Runtime: agent=<id> | host=<host> | repo=<root> | os=<os> (<arch>) | ...
    """
    parts = []

    if runtime_info:
        if runtime_info.agent_id:
            parts.append(f"agent={runtime_info.agent_id}")
        if runtime_info.host:
            parts.append(f"host={runtime_info.host}")
        if runtime_info.repo_root:
            parts.append(f"repo={runtime_info.repo_root}")
        if runtime_info.os:
            os_part = f"os={runtime_info.os}"
            if runtime_info.arch:
                os_part += f" ({runtime_info.arch})"
            parts.append(os_part)
        elif runtime_info.arch:
            parts.append(f"arch={runtime_info.arch}")
        if runtime_info.node:
            parts.append(f"python={runtime_info.node}")  # Use python instead of node
        if runtime_info.model:
            parts.append(f"model={runtime_info.model}")
        if runtime_info.default_model:
            parts.append(f"default_model={runtime_info.default_model}")

    if runtime_channel:
        parts.append(f"channel={runtime_channel}")
        caps = ",".join(runtime_capabilities) if runtime_capabilities else "none"
        parts.append(f"capabilities={caps}")

    parts.append(f"thinking={default_think_level.value}")

    return f"Runtime: {' | '.join(parts)}"


def build_agent_system_prompt(params: SystemPromptParams) -> str:
    """Build the complete system prompt following MoltBot's 23-section structure.

    This is the main entry point for system prompt generation.

    Args:
        params: System prompt parameters

    Returns:
        Complete system prompt string
    """
    # Process tool names - preserve caller casing while deduping by lowercase
    raw_tool_names = [tool.strip() for tool in params.tool_names]
    canonical_tool_names = [t for t in raw_tool_names if t]

    # Map normalized (lowercase) to canonical (original case)
    canonical_by_normalized: dict[str, str] = {}
    for name in canonical_tool_names:
        normalized = name.lower()
        if normalized not in canonical_by_normalized:
            canonical_by_normalized[normalized] = name

    def resolve_tool_name(normalized: str) -> str:
        return canonical_by_normalized.get(normalized, normalized)

    normalized_tools = [tool.lower() for tool in canonical_tool_names]
    available_tools = set(normalized_tools)

    # Build external tool summaries map
    external_tool_summaries: dict[str, str] = {}
    for key, value in params.tool_summaries.items():
        normalized = key.strip().lower()
        trimmed_value = value.strip() if value else ""
        if normalized and trimmed_value:
            external_tool_summaries[normalized] = trimmed_value

    # Build tool lines: core tools first (in order), then extras alphabetically
    extra_tools = list(set(normalized_tools) - set(TOOL_ORDER))
    enabled_tools = [tool for tool in TOOL_ORDER if tool in available_tools]

    tool_lines = []
    for tool in enabled_tools:
        summary = CORE_TOOL_SUMMARIES.get(tool) or external_tool_summaries.get(tool)
        name = resolve_tool_name(tool)
        if summary:
            tool_lines.append(f"- {name}: {summary}")
        else:
            tool_lines.append(f"- {name}")

    for tool in sorted(extra_tools):
        summary = CORE_TOOL_SUMMARIES.get(tool) or external_tool_summaries.get(tool)
        name = resolve_tool_name(tool)
        if summary:
            tool_lines.append(f"- {name}: {summary}")
        else:
            tool_lines.append(f"- {name}")

    # Resolve special tool names
    has_gateway = "gateway" in available_tools
    read_tool_name = resolve_tool_name("read")
    exec_tool_name = resolve_tool_name("exec")
    process_tool_name = resolve_tool_name("process")

    # Process extra system prompt
    extra_system_prompt = params.extra_system_prompt.strip() if params.extra_system_prompt else ""

    # Process owner numbers
    owner_numbers = [n.strip() for n in params.owner_numbers if n.strip()]
    owner_line = (
        f"Owner numbers: {', '.join(owner_numbers)}. Treat messages from these numbers as the user."
        if owner_numbers
        else None
    )

    # Build reasoning hint if enabled
    reasoning_hint = None
    if params.reasoning_tag_hint:
        reasoning_hint = " ".join([
            "ALL internal reasoning MUST be inside <think>...</think>.",
            "Do not output any analysis outside <think>.",
            "Format every reply as <think>...</think> then <final>...</final>, with no other text.",
            "Only the final user-visible reply may appear inside <final>.",
            "Only text inside <final> is shown to the user; everything else is discarded and never seen by the user.",
            "Example:",
            "<think>Short internal reasoning.</think>",
            "<final>Hey there! What would you like to do next?</final>",
        ])

    # Process runtime info
    runtime_info = params.runtime_info
    runtime_channel = (
        runtime_info.channel.strip().lower() if runtime_info and runtime_info.channel else None
    )
    runtime_capabilities = (
        [cap.strip() for cap in runtime_info.capabilities if cap.strip()]
        if runtime_info
        else []
    )
    runtime_capabilities_lower = {cap.lower() for cap in runtime_capabilities}
    inline_buttons_enabled = "inlinebuttons" in runtime_capabilities_lower

    # Get message channel options
    message_channel_options = "|".join(list_deliverable_message_channels())

    # Determine prompt mode
    prompt_mode = params.prompt_mode
    is_minimal = prompt_mode in (PromptMode.MINIMAL, PromptMode.NONE)

    # Process optional fields
    user_timezone = params.user_timezone.strip() if params.user_timezone else None
    skills_prompt = params.skills_prompt.strip() if params.skills_prompt else None
    heartbeat_prompt = params.heartbeat_prompt.strip() if params.heartbeat_prompt else None
    heartbeat_prompt_line = (
        f"Heartbeat prompt: {heartbeat_prompt}" if heartbeat_prompt else "Heartbeat prompt: (configured)"
    )
    workspace_notes = [note.strip() for note in params.workspace_notes if note.strip()]

    # Build helper sections
    skills_section = _build_skills_section(skills_prompt, is_minimal, read_tool_name)
    memory_section = _build_memory_section(is_minimal, available_tools)
    docs_section = _build_docs_section(params.docs_path, is_minimal, read_tool_name)

    # For "none" mode, return just the basic identity line
    if prompt_mode == PromptMode.NONE:
        return "You are a personal assistant running inside LurkBot."

    # Build the complete prompt
    lines: list[str] = [
        "You are a personal assistant running inside LurkBot.",
        "",
        "## Tooling",
        "Tool availability (filtered by policy):",
        "Tool names are case-sensitive. Call tools exactly as listed.",
    ]

    # Add tool lines
    if tool_lines:
        lines.append("\n".join(tool_lines))
    else:
        # Fallback tool list when no tools are provided
        fallback_tools = [
            "Pi lists the standard tools above. This runtime enables:",
            "- grep: search file contents for patterns",
            "- find: find files by glob pattern",
            "- ls: list directory contents",
            "- apply_patch: apply multi-file patches",
            f"- {exec_tool_name}: run shell commands (supports background via yieldMs/background)",
            f"- {process_tool_name}: manage background exec sessions",
            "- browser: control lurkbot's dedicated browser",
            "- canvas: present/eval/snapshot the Canvas",
            "- nodes: list/describe/notify/camera/screen on paired nodes",
            "- cron: manage cron jobs and wake events (use for reminders; when scheduling a reminder, "
            "write the systemEvent text as something that will read like a reminder when it fires, "
            "and mention that it is a reminder depending on the time gap between setting and firing; "
            "include recent context in reminder text if appropriate)",
            "- sessions_list: list sessions",
            "- sessions_history: fetch session history",
            "- sessions_send: send to another session",
        ]
        lines.append("\n".join(fallback_tools))

    lines.extend([
        "TOOLS.md does not control tool availability; it is user guidance for how to use external tools.",
        "If a task is more complex or takes longer, spawn a sub-agent. It will do the work for you "
        "and ping you when it's done. You can always check up on it.",
        "",
        "## Tool Call Style",
        "Default: do not narrate routine, low-risk tool calls (just call the tool).",
        "Narrate only when it helps: multi-step work, complex/challenging problems, sensitive actions "
        "(e.g., deletions), or when the user explicitly asks.",
        "Keep narration brief and value-dense; avoid repeating obvious steps.",
        "Use plain human language for narration unless in a technical context.",
        "",
        "## LurkBot CLI Quick Reference",
        "LurkBot is controlled via subcommands. Do not invent commands.",
        "To manage the Gateway daemon service (start/stop/restart):",
        "- lurkbot gateway status",
        "- lurkbot gateway start",
        "- lurkbot gateway stop",
        "- lurkbot gateway restart",
        "If unsure, ask the user to run `lurkbot help` (or `lurkbot gateway --help`) and paste the output.",
        "",
    ])

    # Add skills section
    lines.extend(skills_section)

    # Add memory section
    lines.extend(memory_section)

    # Add self-update section (skip for subagent/none modes)
    if has_gateway and not is_minimal:
        lines.extend([
            "## LurkBot Self-Update",
            "\n".join([
                "Get Updates (self-update) is ONLY allowed when the user explicitly asks for it.",
                "Do not run config.apply or update.run unless the user explicitly requests an update "
                "or config change; if it's not explicit, ask first.",
                "Actions: config.get, config.schema, config.apply (validate + write full config, then restart), "
                "update.run (update deps or git, then restart).",
                "After restart, LurkBot pings the last active session automatically.",
            ]),
            "",
        ])

    # Add model aliases section (skip for subagent/none modes)
    if params.model_alias_lines and not is_minimal:
        lines.extend([
            "## Model Aliases",
            "Prefer aliases when specifying model overrides; full provider/model is also accepted.",
            "\n".join(params.model_alias_lines),
            "",
        ])

    # Add workspace section
    lines.extend([
        "## Workspace",
        f"Your working directory is: {params.workspace_dir}",
        "Treat this directory as the single global workspace for file operations "
        "unless explicitly instructed otherwise.",
    ])
    lines.extend(workspace_notes)
    lines.append("")

    # Add docs section
    lines.extend(docs_section)

    # Add sandbox section
    if params.sandbox_info and params.sandbox_info.enabled:
        sandbox_lines = [
            "## Sandbox",
            "You are running in a sandboxed runtime (tools execute in Docker).",
            "Some tools may be unavailable due to sandbox policy.",
            "Sub-agents stay sandboxed (no elevated/host access). Need outside-sandbox read/write? "
            "Don't spawn; ask first.",
        ]

        if params.sandbox_info.workspace_dir:
            sandbox_lines.append(f"Sandbox workspace: {params.sandbox_info.workspace_dir}")

        if params.sandbox_info.workspace_access:
            access_line = f"Agent workspace access: {params.sandbox_info.workspace_access}"
            if params.sandbox_info.agent_workspace_mount:
                access_line += f" (mounted at {params.sandbox_info.agent_workspace_mount})"
            sandbox_lines.append(access_line)

        if params.sandbox_info.browser_bridge_url:
            sandbox_lines.append("Sandbox browser: enabled.")

        if params.sandbox_info.browser_novnc_url:
            sandbox_lines.append(f"Sandbox browser observer (noVNC): {params.sandbox_info.browser_novnc_url}")

        if params.sandbox_info.host_browser_allowed is True:
            sandbox_lines.append("Host browser control: allowed.")
        elif params.sandbox_info.host_browser_allowed is False:
            sandbox_lines.append("Host browser control: blocked.")

        if params.sandbox_info.elevated_allowed:
            sandbox_lines.extend([
                "Elevated exec is available for this session.",
                "User can toggle with /elevated on|off|ask|full.",
                "You may also send /elevated on|off|ask|full when needed.",
                f"Current elevated level: {params.sandbox_info.elevated_default_level} "
                "(ask runs exec on host with approvals; full auto-approves).",
            ])

        lines.extend(["\n".join(line for line in sandbox_lines if line), ""])

    # Add user identity section
    lines.extend(_build_user_identity_section(owner_line, is_minimal))

    # Add time section
    lines.extend(_build_time_section(user_timezone))

    # Add workspace files (injected) section
    lines.extend([
        "## Workspace Files (injected)",
        "These user-editable files are loaded by LurkBot and included below in Project Context.",
        "",
    ])

    # Add reply tags section
    lines.extend(_build_reply_tags_section(is_minimal))

    # Add messaging section
    lines.extend(_build_messaging_section(
        is_minimal,
        available_tools,
        message_channel_options,
        inline_buttons_enabled,
        runtime_channel,
        params.message_tool_hints,
    ))

    # Add voice section
    lines.extend(_build_voice_section(is_minimal, params.tts_hint))

    # Add extra system prompt (Group Chat Context or Subagent Context)
    if extra_system_prompt:
        # Use "Subagent Context" header for minimal mode (subagents), otherwise "Group Chat Context"
        context_header = "## Subagent Context" if prompt_mode == PromptMode.MINIMAL else "## Group Chat Context"
        lines.extend([context_header, extra_system_prompt, ""])

    # Add reactions section
    if params.reaction_guidance:
        level = params.reaction_guidance.level
        channel = params.reaction_guidance.channel

        if level == "minimal":
            guidance_text = "\n".join([
                f"Reactions are enabled for {channel} in MINIMAL mode.",
                "React ONLY when truly relevant:",
                "- Acknowledge important user requests or confirmations",
                "- Express genuine sentiment (humor, appreciation) sparingly",
                "- Avoid reacting to routine messages or your own replies",
                "Guideline: at most 1 reaction per 5-10 exchanges.",
            ])
        else:
            guidance_text = "\n".join([
                f"Reactions are enabled for {channel} in EXTENSIVE mode.",
                "Feel free to react liberally:",
                "- Acknowledge messages with appropriate emojis",
                "- Express sentiment and personality through reactions",
                "- React to interesting content, humor, or notable events",
                "- Use reactions to confirm understanding or agreement",
                "Guideline: react whenever it feels natural.",
            ])

        lines.extend(["## Reactions", guidance_text, ""])

    # Add reasoning format section
    if reasoning_hint:
        lines.extend(["## Reasoning Format", reasoning_hint, ""])

    # Add project context section
    context_files = params.context_files
    if context_files:
        # Check for SOUL.md
        has_soul_file = any(
            file.path.strip().replace("\\", "/").split("/")[-1].lower() == "soul.md"
            for file in context_files
        )

        lines.extend([
            "# Project Context",
            "",
            "The following project context files have been loaded:",
        ])

        if has_soul_file:
            lines.append(
                "If SOUL.md is present, embody its persona and tone. Avoid stiff, generic replies; "
                "follow its guidance unless higher-priority instructions override it."
            )

        lines.append("")

        for file in context_files:
            lines.extend([f"## {file.path}", "", file.content, ""])

    # Add silent replies section (skip for subagent/none modes)
    if not is_minimal:
        lines.extend([
            "## Silent Replies",
            f"When you have nothing to say, respond with ONLY: {SILENT_REPLY_TOKEN}",
            "",
            "⚠️ Rules:",
            "- It must be your ENTIRE message — nothing else",
            f'- Never append it to an actual response (never include "{SILENT_REPLY_TOKEN}" in real replies)',
            "- Never wrap it in markdown or code blocks",
            "",
            f'❌ Wrong: "Here\'s help... {SILENT_REPLY_TOKEN}"',
            f'❌ Wrong: "{SILENT_REPLY_TOKEN}"',
            f"✅ Right: {SILENT_REPLY_TOKEN}",
            "",
        ])

    # Add heartbeats section (skip for subagent/none modes)
    if not is_minimal:
        lines.extend([
            "## Heartbeats",
            heartbeat_prompt_line,
            "If you receive a heartbeat poll (a user message matching the heartbeat prompt above), "
            "and there is nothing that needs attention, reply exactly:",
            "HEARTBEAT_OK",
            'LurkBot treats a leading/trailing "HEARTBEAT_OK" as a heartbeat ack (and may discard it).',
            'If something needs attention, do NOT include "HEARTBEAT_OK"; reply with the alert text instead.',
            "",
        ])

    # Add runtime section
    lines.extend([
        "## Runtime",
        build_runtime_line(runtime_info, runtime_channel, runtime_capabilities, params.default_think_level),
        f"Reasoning: {params.reasoning_level} (hidden unless on/stream). "
        "Toggle /reasoning; /status shows Reasoning when enabled.",
    ])

    # Join all lines, filtering out empty strings that might create extra blank lines
    return "\n".join(line for line in lines if line is not None)


def is_silent_reply_text(text: str | None, token: str = SILENT_REPLY_TOKEN) -> bool:
    """Check if text is a silent reply (starts or ends with token).

    Matches MoltBot's isSilentReplyText function.
    """
    if not text:
        return False

    import re

    escaped = re.escape(token)

    # Check if starts with token (followed by end or non-word char)
    prefix_pattern = rf"^\s*{escaped}(?=$|\W)"
    if re.search(prefix_pattern, text):
        return True

    # Check if ends with token
    suffix_pattern = rf"\b{escaped}\b\W*$"
    return bool(re.search(suffix_pattern, text))
