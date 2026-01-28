"""Nine-layer tool policy system.

This module implements MoltBot's nine-layer tool policy filtering system,
which controls which tools are available in different contexts.

The nine layers are applied in order:
1. Profile Policy - tools.profile (minimal/coding/messaging/full)
2. Provider Profile Policy - tools.byProvider[provider].profile
3. Global Allow/Deny Policy - tools.allow / tools.deny
4. Global Provider Policy - tools.byProvider[provider].allow/deny
5. Agent Policy - agents.list[].tools.allow/deny
6. Agent Provider Policy - agents.list[].tools.byProvider[provider].allow/deny
7. Group/Channel Policy - group-level tool restrictions
8. Sandbox Policy - sandbox.tools.allow/deny (when sandboxed)
9. Subagent Policy - default deny list for subagent sessions
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Literal, TypedDict

if TYPE_CHECKING:
    from collections.abc import Callable

# =============================================================================
# Tool Profile Types
# =============================================================================


class ToolProfileId(str, Enum):
    """Tool profile identifiers.

    These map to predefined sets of allowed tools.
    """

    MINIMAL = "minimal"
    CODING = "coding"
    MESSAGING = "messaging"
    FULL = "full"


# =============================================================================
# Tool Name Aliases
# =============================================================================

# Canonical aliases for tool names (maps alias -> canonical name)
TOOL_NAME_ALIASES: dict[str, str] = {
    "bash": "exec",
    "apply-patch": "apply_patch",
}


# =============================================================================
# Tool Groups
# =============================================================================

# NOTE: Keep canonical (lowercase) tool names here.
TOOL_GROUPS: dict[str, list[str]] = {
    # Memory tools
    "group:memory": ["memory_search", "memory_get"],
    # Web tools
    "group:web": ["web_search", "web_fetch"],
    # Basic workspace/file tools
    "group:fs": ["read", "write", "edit", "apply_patch"],
    # Host/runtime execution tools
    "group:runtime": ["exec", "process"],
    # Session management tools
    "group:sessions": [
        "sessions_list",
        "sessions_history",
        "sessions_send",
        "sessions_spawn",
        "session_status",
    ],
    # UI helpers
    "group:ui": ["browser", "canvas"],
    # Automation + infra
    "group:automation": ["cron", "gateway"],
    # Messaging surface
    "group:messaging": ["message"],
    # Nodes + device tools
    "group:nodes": ["nodes"],
    # All LurkBot native tools (excludes provider plugins)
    "group:lurkbot": [
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
        "sessions_spawn",
        "session_status",
        "memory_search",
        "memory_get",
        "web_search",
        "web_fetch",
        "image",
    ],
    # Alias for moltbot compatibility
    "group:moltbot": [
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
        "sessions_spawn",
        "session_status",
        "memory_search",
        "memory_get",
        "web_search",
        "web_fetch",
        "image",
    ],
}


# =============================================================================
# Tool Profiles
# =============================================================================


class ToolProfilePolicy(TypedDict, total=False):
    """Tool profile policy definition."""

    allow: list[str]
    deny: list[str]


TOOL_PROFILES: dict[ToolProfileId, ToolProfilePolicy] = {
    ToolProfileId.MINIMAL: {
        "allow": ["session_status"],
    },
    ToolProfileId.CODING: {
        "allow": ["group:fs", "group:runtime", "group:sessions", "group:memory", "image"],
    },
    ToolProfileId.MESSAGING: {
        "allow": [
            "group:messaging",
            "sessions_list",
            "sessions_history",
            "sessions_send",
            "session_status",
        ],
    },
    ToolProfileId.FULL: {},  # Empty = allow everything
}


# =============================================================================
# Default Subagent Tool Deny List
# =============================================================================

DEFAULT_SUBAGENT_TOOL_DENY: list[str] = [
    # Session management - main agent orchestrates
    "sessions_list",
    "sessions_history",
    "sessions_send",
    "sessions_spawn",
    # System admin - dangerous from subagent
    "gateway",
    "agents_list",
    # Interactive setup - not a task
    "whatsapp_login",
    # Status/scheduling - main agent coordinates
    "session_status",
    "cron",
    # Memory - pass relevant info in spawn prompt instead
    "memory_search",
    "memory_get",
]


# =============================================================================
# Policy Types
# =============================================================================


class ToolPolicy(TypedDict, total=False):
    """Tool policy with allow/deny lists."""

    allow: list[str]
    deny: list[str]


@dataclass
class ToolPolicyConfig:
    """Tool policy configuration."""

    allow: list[str] | None = None
    also_allow: list[str] | None = None
    deny: list[str] | None = None
    profile: str | None = None


@dataclass
class PluginToolGroups:
    """Plugin tool group mappings."""

    all: list[str] = field(default_factory=list)
    by_plugin: dict[str, list[str]] = field(default_factory=dict)


@dataclass
class AllowlistResolution:
    """Result of allowlist resolution."""

    policy: ToolPolicy | None
    unknown_allowlist: list[str]
    stripped_allowlist: bool


# =============================================================================
# Tool Name Normalization
# =============================================================================


def normalize_tool_name(name: str) -> str:
    """Normalize a tool name to its canonical form.

    Args:
        name: The tool name to normalize

    Returns:
        The normalized (lowercase, alias-resolved) tool name
    """
    normalized = name.strip().lower()
    return TOOL_NAME_ALIASES.get(normalized, normalized)


def normalize_tool_list(tools: list[str] | None) -> list[str]:
    """Normalize a list of tool names.

    Args:
        tools: List of tool names to normalize

    Returns:
        List of normalized tool names (empty list if input is None)
    """
    if not tools:
        return []
    return [n for n in (normalize_tool_name(t) for t in tools) if n]


# =============================================================================
# Tool Group Expansion
# =============================================================================


def expand_tool_groups(tools: list[str] | None) -> list[str]:
    """Expand tool group references to individual tool names.

    Args:
        tools: List of tool names/groups to expand

    Returns:
        List of individual tool names with groups expanded
    """
    normalized = normalize_tool_list(tools)
    expanded: list[str] = []

    for value in normalized:
        group = TOOL_GROUPS.get(value)
        if group:
            expanded.extend(group)
        else:
            expanded.append(value)

    # Return unique values while preserving order
    return list(dict.fromkeys(expanded))


def expand_plugin_groups(
    tools: list[str] | None,
    groups: PluginToolGroups,
) -> list[str] | None:
    """Expand plugin tool group references.

    Args:
        tools: List of tool names/groups to expand
        groups: Plugin tool group mappings

    Returns:
        List of tool names with plugin groups expanded
    """
    if not tools or len(tools) == 0:
        return tools

    expanded: list[str] = []
    for entry in tools:
        normalized = normalize_tool_name(entry)

        # Handle group:plugins special case
        if normalized == "group:plugins":
            if groups.all:
                expanded.extend(groups.all)
            else:
                expanded.append(normalized)
            continue

        # Check if it's a plugin ID
        plugin_tools = groups.by_plugin.get(normalized)
        if plugin_tools:
            expanded.extend(plugin_tools)
            continue

        expanded.append(normalized)

    # Return unique values
    return list(dict.fromkeys(expanded))


def expand_policy_with_plugin_groups(
    policy: ToolPolicy | None,
    groups: PluginToolGroups,
) -> ToolPolicy | None:
    """Expand plugin groups in a policy's allow/deny lists.

    Args:
        policy: The policy to expand
        groups: Plugin tool group mappings

    Returns:
        Policy with expanded plugin groups, or None if policy is None
    """
    if not policy:
        return None

    result: ToolPolicy = {}
    if policy.get("allow"):
        result["allow"] = expand_plugin_groups(policy["allow"], groups) or []
    if policy.get("deny"):
        result["deny"] = expand_plugin_groups(policy["deny"], groups) or []

    return result if result else None


# =============================================================================
# Pattern Matching
# =============================================================================

CompiledPatternKind = Literal["all", "exact", "regex"]


@dataclass
class CompiledPattern:
    """A compiled pattern for matching tool names."""

    kind: CompiledPatternKind
    value: str | re.Pattern[str] | None = None


def compile_pattern(pattern: str) -> CompiledPattern:
    """Compile a pattern string into a CompiledPattern.

    Args:
        pattern: The pattern to compile (supports * wildcards)

    Returns:
        A compiled pattern for matching
    """
    normalized = normalize_tool_name(pattern)
    if not normalized:
        return CompiledPattern(kind="exact", value="")
    if normalized == "*":
        return CompiledPattern(kind="all")
    if "*" not in normalized:
        return CompiledPattern(kind="exact", value=normalized)

    # Convert glob pattern to regex
    escaped = re.escape(normalized)
    regex_str = f"^{escaped.replace(r'\*', '.*')}$"
    return CompiledPattern(kind="regex", value=re.compile(regex_str))


def compile_patterns(patterns: list[str] | None) -> list[CompiledPattern]:
    """Compile a list of patterns.

    Args:
        patterns: List of pattern strings

    Returns:
        List of compiled patterns
    """
    if not patterns:
        return []

    expanded = expand_tool_groups(patterns)
    compiled = [compile_pattern(p) for p in expanded]
    # Filter out empty exact patterns
    return [p for p in compiled if not (p.kind == "exact" and p.value == "")]


def matches_any(name: str, patterns: list[CompiledPattern]) -> bool:
    """Check if a name matches any of the compiled patterns.

    Args:
        name: The tool name to check
        patterns: List of compiled patterns

    Returns:
        True if the name matches any pattern
    """
    for pattern in patterns:
        if pattern.kind == "all":
            return True
        if pattern.kind == "exact" and name == pattern.value:
            return True
        if pattern.kind == "regex" and isinstance(pattern.value, re.Pattern):
            if pattern.value.match(name):
                return True
    return False


# =============================================================================
# Tool Policy Matcher
# =============================================================================


def make_tool_policy_matcher(policy: ToolPolicy) -> Callable[[str], bool]:
    """Create a matcher function for a tool policy.

    The matching logic:
    1. Deny always wins - if a tool is denied, it stays denied
    2. If allow list is empty, everything is allowed (unless denied)
    3. If allow list is specified, only matching tools pass
    4. Special case: apply_patch is allowed if exec is allowed

    Args:
        policy: The tool policy with allow/deny lists

    Returns:
        A function that takes a tool name and returns True if allowed
    """
    deny = compile_patterns(policy.get("deny"))
    allow = compile_patterns(policy.get("allow"))

    def matcher(name: str) -> bool:
        normalized = normalize_tool_name(name)

        # Deny always wins
        if matches_any(normalized, deny):
            return False

        # If no allow list, everything is allowed
        if len(allow) == 0:
            return True

        # Check if explicitly allowed
        if matches_any(normalized, allow):
            return True

        # Special case: apply_patch is allowed if exec is allowed
        if normalized == "apply_patch" and matches_any("exec", allow):
            return True

        return False

    return matcher


# =============================================================================
# Tool Filtering
# =============================================================================


@dataclass
class Tool:
    """Represents a tool with a name.

    This is a minimal interface for filtering tools.
    Actual tool implementations may have more fields.
    """

    name: str


def filter_tools_by_policy(
    tools: list[Tool],
    policy: ToolPolicy | None,
) -> list[Tool]:
    """Filter tools by a policy.

    Args:
        tools: List of tools to filter
        policy: The policy to apply (if None, all tools pass)

    Returns:
        Filtered list of tools
    """
    if not policy:
        return tools

    matcher = make_tool_policy_matcher(policy)
    return [tool for tool in tools if matcher(tool.name)]


def is_tool_allowed_by_policy_name(name: str, policy: ToolPolicy | None) -> bool:
    """Check if a tool name is allowed by a policy.

    Args:
        name: The tool name to check
        policy: The policy to check against

    Returns:
        True if the tool is allowed
    """
    if not policy:
        return True
    return make_tool_policy_matcher(policy)(name)


def is_tool_allowed_by_policies(
    name: str,
    policies: list[ToolPolicy | None],
) -> bool:
    """Check if a tool is allowed by all policies.

    Args:
        name: The tool name to check
        policies: List of policies to check against

    Returns:
        True if the tool is allowed by all policies
    """
    return all(is_tool_allowed_by_policy_name(name, policy) for policy in policies)


# =============================================================================
# Profile Policy Resolution
# =============================================================================


def resolve_tool_profile_policy(profile: str | None) -> ToolPolicy | None:
    """Resolve a tool profile to its policy.

    Args:
        profile: The profile ID (minimal/coding/messaging/full)

    Returns:
        The resolved policy, or None if profile is invalid
    """
    if not profile:
        return None

    try:
        profile_id = ToolProfileId(profile)
    except ValueError:
        return None

    resolved = TOOL_PROFILES.get(profile_id)
    if not resolved:
        return None

    # Empty profile (full) means allow everything
    if not resolved.get("allow") and not resolved.get("deny"):
        return None

    policy: ToolPolicy = {}
    if resolved.get("allow"):
        policy["allow"] = list(resolved["allow"])
    if resolved.get("deny"):
        policy["deny"] = list(resolved["deny"])

    return policy if policy else None


# =============================================================================
# Allow List Utilities
# =============================================================================


def union_allow(base: list[str] | None, extra: list[str] | None) -> list[str] | None:
    """Union two allow lists.

    If the user is using alsoAllow without an allowlist, treat it as additive
    on top of an implicit allow-all policy.

    Args:
        base: The base allow list
        extra: Additional items to allow (alsoAllow)

    Returns:
        Combined allow list
    """
    if not extra or len(extra) == 0:
        return base

    # If no base allowlist, treat alsoAllow as additive on allow-all
    if not base or len(base) == 0:
        return list(dict.fromkeys(["*", *extra]))

    return list(dict.fromkeys([*base, *extra]))


def pick_tool_policy(config: ToolPolicyConfig | None) -> ToolPolicy | None:
    """Extract a tool policy from a config.

    Args:
        config: The tool policy configuration

    Returns:
        The extracted policy, or None if no policy specified
    """
    if not config:
        return None

    allow: list[str] | None
    if config.allow:
        allow = union_allow(config.allow, config.also_allow)
    elif config.also_allow and len(config.also_allow) > 0:
        allow = union_allow(None, config.also_allow)
    else:
        allow = None

    deny = config.deny if config.deny else None

    if not allow and not deny:
        return None

    policy: ToolPolicy = {}
    if allow:
        policy["allow"] = allow
    if deny:
        policy["deny"] = deny

    return policy


# =============================================================================
# Explicit Allowlist Collection
# =============================================================================


def collect_explicit_allowlist(policies: list[ToolPolicy | None]) -> list[str]:
    """Collect all explicit allow entries from multiple policies.

    Args:
        policies: List of policies to collect from

    Returns:
        Combined list of all allow entries
    """
    entries: list[str] = []
    for policy in policies:
        if not policy or not policy.get("allow"):
            continue
        for value in policy["allow"]:
            if isinstance(value, str):
                trimmed = value.strip()
                if trimmed:
                    entries.append(trimmed)
    return entries


# =============================================================================
# Plugin Tool Groups Builder
# =============================================================================


def build_plugin_tool_groups(
    tools: list[Tool],
    tool_meta: Callable[[Tool], dict[str, str] | None],
) -> PluginToolGroups:
    """Build plugin tool groups from a list of tools.

    Args:
        tools: List of tools
        tool_meta: Function to get plugin metadata from a tool

    Returns:
        Plugin tool groups mapping
    """
    groups = PluginToolGroups()

    for tool in tools:
        meta = tool_meta(tool)
        if not meta:
            continue

        name = normalize_tool_name(tool.name)
        groups.all.append(name)

        plugin_id = meta.get("pluginId", "").lower()
        if plugin_id:
            if plugin_id not in groups.by_plugin:
                groups.by_plugin[plugin_id] = []
            groups.by_plugin[plugin_id].append(name)

    return groups


# =============================================================================
# Strip Plugin-Only Allowlist
# =============================================================================


def strip_plugin_only_allowlist(
    policy: ToolPolicy | None,
    groups: PluginToolGroups,
    core_tools: set[str],
) -> AllowlistResolution:
    """Strip allowlist if it contains only plugin tools.

    When an allowlist contains only plugin tools, we strip it to avoid
    accidentally disabling core tools. Users who want additive behavior
    should prefer `tools.alsoAllow`.

    Args:
        policy: The policy to check
        groups: Plugin tool groups
        core_tools: Set of core tool names

    Returns:
        Resolution result with potentially stripped policy
    """
    if not policy or not policy.get("allow") or len(policy["allow"]) == 0:
        return AllowlistResolution(
            policy=policy,
            unknown_allowlist=[],
            stripped_allowlist=False,
        )

    normalized = normalize_tool_list(policy["allow"])
    if len(normalized) == 0:
        return AllowlistResolution(
            policy=policy,
            unknown_allowlist=[],
            stripped_allowlist=False,
        )

    plugin_ids = set(groups.by_plugin.keys())
    plugin_tools = set(groups.all)
    unknown_allowlist: list[str] = []
    has_core_entry = False

    for entry in normalized:
        is_plugin_entry = (
            entry == "group:plugins" or entry in plugin_ids or entry in plugin_tools
        )
        expanded = expand_tool_groups([entry])
        is_core_entry = any(tool in core_tools for tool in expanded)

        if is_core_entry:
            has_core_entry = True
        if not is_core_entry and not is_plugin_entry:
            unknown_allowlist.append(entry)

    stripped_allowlist = not has_core_entry

    # Strip the allowlist if it doesn't contain any core tools
    if stripped_allowlist:
        result_policy: ToolPolicy = dict(policy)
        result_policy.pop("allow", None)
        return AllowlistResolution(
            policy=result_policy if result_policy else None,
            unknown_allowlist=list(dict.fromkeys(unknown_allowlist)),
            stripped_allowlist=True,
        )

    return AllowlistResolution(
        policy=policy,
        unknown_allowlist=list(dict.fromkeys(unknown_allowlist)),
        stripped_allowlist=False,
    )


# =============================================================================
# Subagent Tool Policy
# =============================================================================


def resolve_subagent_tool_policy(
    config_deny: list[str] | None = None,
    config_allow: list[str] | None = None,
) -> ToolPolicy:
    """Resolve the tool policy for subagent sessions.

    Subagents have a default deny list to prevent self-orchestration
    and access to sensitive tools.

    Args:
        config_deny: Additional tools to deny (from config)
        config_allow: Tools to allow (from config)

    Returns:
        The resolved subagent tool policy
    """
    deny = list(DEFAULT_SUBAGENT_TOOL_DENY)
    if config_deny:
        deny.extend(config_deny)

    policy: ToolPolicy = {"deny": deny}
    if config_allow:
        policy["allow"] = config_allow

    return policy


# =============================================================================
# Effective Tool Policy Resolution
# =============================================================================


@dataclass
class EffectiveToolPolicy:
    """Resolved effective tool policy from all sources."""

    agent_id: str | None = None
    global_policy: ToolPolicy | None = None
    global_provider_policy: ToolPolicy | None = None
    agent_policy: ToolPolicy | None = None
    agent_provider_policy: ToolPolicy | None = None
    profile: str | None = None
    provider_profile: str | None = None
    profile_also_allow: list[str] | None = None
    provider_profile_also_allow: list[str] | None = None


# =============================================================================
# Nine-Layer Tool Filtering
# =============================================================================


@dataclass
class ToolFilterContext:
    """Context for nine-layer tool filtering."""

    # Layer 1: Profile policy
    profile: str | None = None
    profile_also_allow: list[str] | None = None

    # Layer 2: Provider profile policy
    provider_profile: str | None = None
    provider_profile_also_allow: list[str] | None = None

    # Layer 3: Global allow/deny
    global_policy: ToolPolicy | None = None

    # Layer 4: Global provider policy
    global_provider_policy: ToolPolicy | None = None

    # Layer 5: Agent policy
    agent_policy: ToolPolicy | None = None

    # Layer 6: Agent provider policy
    agent_provider_policy: ToolPolicy | None = None

    # Layer 7: Group/channel policy
    group_policy: ToolPolicy | None = None

    # Layer 8: Sandbox policy
    sandbox_policy: ToolPolicy | None = None

    # Layer 9: Subagent policy
    subagent_policy: ToolPolicy | None = None

    # Plugin groups for expansion
    plugin_groups: PluginToolGroups = field(default_factory=PluginToolGroups)

    # Core tool names for allowlist stripping
    core_tool_names: set[str] = field(default_factory=set)


def filter_tools_nine_layers(
    tools: list[Tool],
    context: ToolFilterContext,
) -> list[Tool]:
    """Apply nine-layer tool filtering.

    The layers are applied in order:
    1. Profile Policy
    2. Provider Profile Policy
    3. Global Allow/Deny Policy
    4. Global Provider Policy
    5. Agent Policy
    6. Agent Provider Policy
    7. Group/Channel Policy
    8. Sandbox Policy
    9. Subagent Policy

    Args:
        tools: List of tools to filter
        context: The filter context containing all policy layers

    Returns:
        Filtered list of tools
    """

    def resolve_policy(
        policy: ToolPolicy | None,
        _label: str,  # Used for logging in MoltBot, kept for compatibility
    ) -> ToolPolicy | None:
        """Resolve a policy with plugin group expansion and allowlist stripping."""
        if not policy:
            return None

        resolved = strip_plugin_only_allowlist(
            policy, context.plugin_groups, context.core_tool_names
        )
        return expand_policy_with_plugin_groups(resolved.policy, context.plugin_groups)

    # Prepare profile policies with alsoAllow
    profile_policy = resolve_tool_profile_policy(context.profile)
    if profile_policy and context.profile_also_allow:
        allow = union_allow(profile_policy.get("allow"), context.profile_also_allow)
        if allow:
            profile_policy["allow"] = allow

    provider_profile_policy = resolve_tool_profile_policy(context.provider_profile)
    if provider_profile_policy and context.provider_profile_also_allow:
        allow = union_allow(
            provider_profile_policy.get("allow"), context.provider_profile_also_allow
        )
        if allow:
            provider_profile_policy["allow"] = allow

    # Resolve all policies with plugin expansion
    profile_expanded = resolve_policy(
        profile_policy,
        f"tools.profile ({context.profile})" if context.profile else "tools.profile",
    )
    provider_profile_expanded = resolve_policy(
        provider_profile_policy,
        f"tools.byProvider.profile ({context.provider_profile})"
        if context.provider_profile
        else "tools.byProvider.profile",
    )
    global_expanded = resolve_policy(context.global_policy, "tools.allow")
    global_provider_expanded = resolve_policy(
        context.global_provider_policy, "tools.byProvider.allow"
    )
    agent_expanded = resolve_policy(context.agent_policy, "agent tools.allow")
    agent_provider_expanded = resolve_policy(
        context.agent_provider_policy, "agent tools.byProvider.allow"
    )
    group_expanded = resolve_policy(context.group_policy, "group tools.allow")
    sandbox_expanded = expand_policy_with_plugin_groups(
        context.sandbox_policy, context.plugin_groups
    )
    subagent_expanded = expand_policy_with_plugin_groups(
        context.subagent_policy, context.plugin_groups
    )

    # Apply filters in order
    # Layer 1: Profile policy
    filtered = (
        filter_tools_by_policy(tools, profile_expanded)
        if profile_expanded
        else tools
    )

    # Layer 2: Provider profile policy
    filtered = (
        filter_tools_by_policy(filtered, provider_profile_expanded)
        if provider_profile_expanded
        else filtered
    )

    # Layer 3: Global allow/deny
    filtered = (
        filter_tools_by_policy(filtered, global_expanded)
        if global_expanded
        else filtered
    )

    # Layer 4: Global provider policy
    filtered = (
        filter_tools_by_policy(filtered, global_provider_expanded)
        if global_provider_expanded
        else filtered
    )

    # Layer 5: Agent policy
    filtered = (
        filter_tools_by_policy(filtered, agent_expanded)
        if agent_expanded
        else filtered
    )

    # Layer 6: Agent provider policy
    filtered = (
        filter_tools_by_policy(filtered, agent_provider_expanded)
        if agent_provider_expanded
        else filtered
    )

    # Layer 7: Group/channel policy
    filtered = (
        filter_tools_by_policy(filtered, group_expanded)
        if group_expanded
        else filtered
    )

    # Layer 8: Sandbox policy
    filtered = (
        filter_tools_by_policy(filtered, sandbox_expanded)
        if sandbox_expanded
        else filtered
    )

    # Layer 9: Subagent policy
    filtered = (
        filter_tools_by_policy(filtered, subagent_expanded)
        if subagent_expanded
        else filtered
    )

    return filtered
