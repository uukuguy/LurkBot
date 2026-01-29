"""Tool system.

This module contains the tool infrastructure:
- policy.py: Nine-layer tool policy system
- tts_tool.py: TTS synthesis tool
- registry.py: Tool registry [TODO]
- builtin/: 22 native tools [TODO]
"""

from lurkbot.tools.policy import (
    # Constants
    DEFAULT_SUBAGENT_TOOL_DENY,
    TOOL_GROUPS,
    TOOL_NAME_ALIASES,
    TOOL_PROFILES,
    # Types and Enums
    AllowlistResolution,
    CompiledPattern,
    EffectiveToolPolicy,
    PluginToolGroups,
    Tool,
    ToolFilterContext,
    ToolPolicy,
    ToolPolicyConfig,
    ToolProfileId,
    ToolProfilePolicy,
    # Functions - Name normalization
    normalize_tool_name,
    normalize_tool_list,
    # Functions - Group expansion
    expand_tool_groups,
    expand_plugin_groups,
    expand_policy_with_plugin_groups,
    # Functions - Pattern matching
    compile_pattern,
    compile_patterns,
    matches_any,
    # Functions - Policy matching
    make_tool_policy_matcher,
    filter_tools_by_policy,
    is_tool_allowed_by_policy_name,
    is_tool_allowed_by_policies,
    # Functions - Profile resolution
    resolve_tool_profile_policy,
    # Functions - Allow list utilities
    union_allow,
    pick_tool_policy,
    collect_explicit_allowlist,
    # Functions - Plugin tools
    build_plugin_tool_groups,
    strip_plugin_only_allowlist,
    # Functions - Subagent policy
    resolve_subagent_tool_policy,
    # Functions - Nine-layer filtering
    filter_tools_nine_layers,
)

__all__ = [
    # Constants
    "DEFAULT_SUBAGENT_TOOL_DENY",
    "TOOL_GROUPS",
    "TOOL_NAME_ALIASES",
    "TOOL_PROFILES",
    # Types and Enums
    "AllowlistResolution",
    "CompiledPattern",
    "EffectiveToolPolicy",
    "PluginToolGroups",
    "Tool",
    "ToolFilterContext",
    "ToolPolicy",
    "ToolPolicyConfig",
    "ToolProfileId",
    "ToolProfilePolicy",
    # Functions - Name normalization
    "normalize_tool_name",
    "normalize_tool_list",
    # Functions - Group expansion
    "expand_tool_groups",
    "expand_plugin_groups",
    "expand_policy_with_plugin_groups",
    # Functions - Pattern matching
    "compile_pattern",
    "compile_patterns",
    "matches_any",
    # Functions - Policy matching
    "make_tool_policy_matcher",
    "filter_tools_by_policy",
    "is_tool_allowed_by_policy_name",
    "is_tool_allowed_by_policies",
    # Functions - Profile resolution
    "resolve_tool_profile_policy",
    # Functions - Allow list utilities
    "union_allow",
    "pick_tool_policy",
    "collect_explicit_allowlist",
    # Functions - Plugin tools
    "build_plugin_tool_groups",
    "strip_plugin_only_allowlist",
    # Functions - Subagent policy
    "resolve_subagent_tool_policy",
    # Functions - Nine-layer filtering
    "filter_tools_nine_layers",
]
