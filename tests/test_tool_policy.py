"""Tests for the nine-layer tool policy system.

These tests verify the tool policy system matches MoltBot's implementation.
"""

import pytest

from lurkbot.tools.policy import (
    # Constants
    DEFAULT_SUBAGENT_TOOL_DENY,
    TOOL_GROUPS,
    TOOL_NAME_ALIASES,
    TOOL_PROFILES,
    # Types and Enums
    AllowlistResolution,
    CompiledPattern,
    PluginToolGroups,
    Tool,
    ToolFilterContext,
    ToolPolicy,
    ToolPolicyConfig,
    ToolProfileId,
    # Functions
    build_plugin_tool_groups,
    collect_explicit_allowlist,
    compile_pattern,
    compile_patterns,
    expand_plugin_groups,
    expand_policy_with_plugin_groups,
    expand_tool_groups,
    filter_tools_by_policy,
    filter_tools_nine_layers,
    is_tool_allowed_by_policies,
    is_tool_allowed_by_policy_name,
    make_tool_policy_matcher,
    matches_any,
    normalize_tool_list,
    normalize_tool_name,
    pick_tool_policy,
    resolve_subagent_tool_policy,
    resolve_tool_profile_policy,
    strip_plugin_only_allowlist,
    union_allow,
)


# =============================================================================
# Test Constants
# =============================================================================


class TestConstants:
    """Tests for module constants."""

    def test_tool_name_aliases(self):
        """Test tool name aliases match MoltBot."""
        assert TOOL_NAME_ALIASES["bash"] == "exec"
        assert TOOL_NAME_ALIASES["apply-patch"] == "apply_patch"

    def test_tool_groups_exist(self):
        """Test all expected tool groups exist."""
        expected_groups = [
            "group:memory",
            "group:web",
            "group:fs",
            "group:runtime",
            "group:sessions",
            "group:ui",
            "group:automation",
            "group:messaging",
            "group:nodes",
            "group:lurkbot",
            "group:moltbot",  # alias for compatibility
        ]
        for group in expected_groups:
            assert group in TOOL_GROUPS, f"Missing group: {group}"

    def test_group_memory_tools(self):
        """Test memory group contains expected tools."""
        assert TOOL_GROUPS["group:memory"] == ["memory_search", "memory_get"]

    def test_group_fs_tools(self):
        """Test fs group contains expected tools."""
        assert TOOL_GROUPS["group:fs"] == ["read", "write", "edit", "apply_patch"]

    def test_group_sessions_tools(self):
        """Test sessions group contains expected tools."""
        expected = [
            "sessions_list",
            "sessions_history",
            "sessions_send",
            "sessions_spawn",
            "session_status",
        ]
        assert TOOL_GROUPS["group:sessions"] == expected

    def test_tool_profiles_exist(self):
        """Test all tool profiles exist."""
        assert ToolProfileId.MINIMAL in TOOL_PROFILES
        assert ToolProfileId.CODING in TOOL_PROFILES
        assert ToolProfileId.MESSAGING in TOOL_PROFILES
        assert ToolProfileId.FULL in TOOL_PROFILES

    def test_minimal_profile(self):
        """Test minimal profile only allows session_status."""
        assert TOOL_PROFILES[ToolProfileId.MINIMAL]["allow"] == ["session_status"]

    def test_full_profile_is_empty(self):
        """Test full profile has no restrictions (empty)."""
        assert TOOL_PROFILES[ToolProfileId.FULL] == {}

    def test_default_subagent_deny_list(self):
        """Test default subagent deny list matches MoltBot."""
        expected_denies = [
            "sessions_list",
            "sessions_history",
            "sessions_send",
            "sessions_spawn",
            "gateway",
            "agents_list",
            "whatsapp_login",
            "session_status",
            "cron",
            "memory_search",
            "memory_get",
        ]
        for tool in expected_denies:
            assert tool in DEFAULT_SUBAGENT_TOOL_DENY


# =============================================================================
# Test Tool Name Normalization
# =============================================================================


class TestNormalizeToolName:
    """Tests for normalize_tool_name function."""

    def test_lowercase(self):
        """Test names are lowercased."""
        assert normalize_tool_name("Read") == "read"
        assert normalize_tool_name("WRITE") == "write"

    def test_strip_whitespace(self):
        """Test whitespace is stripped."""
        assert normalize_tool_name("  read  ") == "read"

    def test_bash_alias(self):
        """Test bash is aliased to exec."""
        assert normalize_tool_name("bash") == "exec"
        assert normalize_tool_name("Bash") == "exec"

    def test_apply_patch_alias(self):
        """Test apply-patch is aliased to apply_patch."""
        assert normalize_tool_name("apply-patch") == "apply_patch"

    def test_no_alias(self):
        """Test names without aliases pass through."""
        assert normalize_tool_name("read") == "read"
        assert normalize_tool_name("custom_tool") == "custom_tool"


class TestNormalizeToolList:
    """Tests for normalize_tool_list function."""

    def test_none_returns_empty(self):
        """Test None returns empty list."""
        assert normalize_tool_list(None) == []

    def test_empty_returns_empty(self):
        """Test empty list returns empty list."""
        assert normalize_tool_list([]) == []

    def test_normalizes_all(self):
        """Test all names are normalized."""
        result = normalize_tool_list(["Read", "WRITE", "bash"])
        assert result == ["read", "write", "exec"]

    def test_filters_empty_strings(self):
        """Test empty strings are filtered."""
        result = normalize_tool_list(["read", "", "write"])
        assert result == ["read", "write"]


# =============================================================================
# Test Tool Group Expansion
# =============================================================================


class TestExpandToolGroups:
    """Tests for expand_tool_groups function."""

    def test_none_returns_empty(self):
        """Test None returns empty list."""
        assert expand_tool_groups(None) == []

    def test_single_tool(self):
        """Test single tool passes through."""
        assert expand_tool_groups(["read"]) == ["read"]

    def test_group_expands(self):
        """Test group is expanded to tools."""
        result = expand_tool_groups(["group:memory"])
        assert result == ["memory_search", "memory_get"]

    def test_mixed_expansion(self):
        """Test mixed groups and tools."""
        result = expand_tool_groups(["group:memory", "read"])
        assert "memory_search" in result
        assert "memory_get" in result
        assert "read" in result

    def test_deduplication(self):
        """Test duplicate tools are removed."""
        result = expand_tool_groups(["read", "read", "write"])
        assert result == ["read", "write"]

    def test_unknown_group_passes_through(self):
        """Test unknown group names pass through."""
        result = expand_tool_groups(["group:unknown"])
        assert result == ["group:unknown"]


# =============================================================================
# Test Pattern Matching
# =============================================================================


class TestCompilePattern:
    """Tests for compile_pattern function."""

    def test_all_pattern(self):
        """Test * compiles to all pattern."""
        pattern = compile_pattern("*")
        assert pattern.kind == "all"

    def test_exact_pattern(self):
        """Test simple name compiles to exact pattern."""
        pattern = compile_pattern("read")
        assert pattern.kind == "exact"
        assert pattern.value == "read"

    def test_regex_pattern(self):
        """Test wildcard compiles to regex pattern."""
        pattern = compile_pattern("web_*")
        assert pattern.kind == "regex"
        assert pattern.value is not None

    def test_empty_pattern(self):
        """Test empty string compiles to empty exact."""
        pattern = compile_pattern("")
        assert pattern.kind == "exact"
        assert pattern.value == ""

    def test_normalizes_pattern(self):
        """Test pattern is normalized."""
        pattern = compile_pattern("Bash")
        assert pattern.kind == "exact"
        assert pattern.value == "exec"


class TestCompilePatterns:
    """Tests for compile_patterns function."""

    def test_none_returns_empty(self):
        """Test None returns empty list."""
        assert compile_patterns(None) == []

    def test_expands_groups(self):
        """Test groups are expanded before compilation."""
        patterns = compile_patterns(["group:memory"])
        # Should have patterns for memory_search and memory_get
        assert len(patterns) == 2

    def test_filters_empty_exact(self):
        """Test empty exact patterns are filtered."""
        patterns = compile_patterns(["read", ""])
        assert len(patterns) == 1


class TestMatchesAny:
    """Tests for matches_any function."""

    def test_all_matches_everything(self):
        """Test 'all' pattern matches any name."""
        patterns = [CompiledPattern(kind="all")]
        assert matches_any("anything", patterns)

    def test_exact_matches_same(self):
        """Test exact pattern matches same name."""
        patterns = [CompiledPattern(kind="exact", value="read")]
        assert matches_any("read", patterns)

    def test_exact_not_matches_different(self):
        """Test exact pattern doesn't match different name."""
        patterns = [CompiledPattern(kind="exact", value="read")]
        assert not matches_any("write", patterns)

    def test_regex_matches(self):
        """Test regex pattern matches."""
        import re

        patterns = [CompiledPattern(kind="regex", value=re.compile(r"^web_.*$"))]
        assert matches_any("web_search", patterns)
        assert matches_any("web_fetch", patterns)
        assert not matches_any("read", patterns)

    def test_empty_patterns_no_match(self):
        """Test empty pattern list matches nothing."""
        assert not matches_any("anything", [])


# =============================================================================
# Test Tool Policy Matcher
# =============================================================================


class TestMakeToolPolicyMatcher:
    """Tests for make_tool_policy_matcher function."""

    def test_deny_wins(self):
        """Test deny always wins over allow."""
        policy: ToolPolicy = {"allow": ["*"], "deny": ["read"]}
        matcher = make_tool_policy_matcher(policy)
        assert not matcher("read")
        assert matcher("write")

    def test_empty_allow_allows_all(self):
        """Test empty allow list allows everything."""
        policy: ToolPolicy = {}
        matcher = make_tool_policy_matcher(policy)
        assert matcher("anything")

    def test_allow_restricts(self):
        """Test allow list restricts to specified tools."""
        policy: ToolPolicy = {"allow": ["read", "write"]}
        matcher = make_tool_policy_matcher(policy)
        assert matcher("read")
        assert matcher("write")
        assert not matcher("exec")

    def test_apply_patch_exec_special_case(self):
        """Test apply_patch is allowed if exec is allowed."""
        policy: ToolPolicy = {"allow": ["exec"]}
        matcher = make_tool_policy_matcher(policy)
        assert matcher("exec")
        assert matcher("apply_patch")

    def test_normalizes_names(self):
        """Test tool names are normalized."""
        policy: ToolPolicy = {"allow": ["exec"]}
        matcher = make_tool_policy_matcher(policy)
        assert matcher("bash")  # bash -> exec

    def test_wildcard_allow(self):
        """Test wildcard in allow list."""
        policy: ToolPolicy = {"allow": ["web_*"]}
        matcher = make_tool_policy_matcher(policy)
        assert matcher("web_search")
        assert matcher("web_fetch")
        assert not matcher("read")


# =============================================================================
# Test Filter Tools By Policy
# =============================================================================


class TestFilterToolsByPolicy:
    """Tests for filter_tools_by_policy function."""

    def test_none_policy_returns_all(self):
        """Test None policy returns all tools."""
        tools = [Tool(name="read"), Tool(name="write")]
        result = filter_tools_by_policy(tools, None)
        assert result == tools

    def test_allow_filters(self):
        """Test allow list filters tools."""
        tools = [Tool(name="read"), Tool(name="write"), Tool(name="exec")]
        policy: ToolPolicy = {"allow": ["read", "write"]}
        result = filter_tools_by_policy(tools, policy)
        assert len(result) == 2
        assert all(t.name in ["read", "write"] for t in result)

    def test_deny_filters(self):
        """Test deny list filters tools."""
        tools = [Tool(name="read"), Tool(name="write"), Tool(name="exec")]
        policy: ToolPolicy = {"deny": ["exec"]}
        result = filter_tools_by_policy(tools, policy)
        assert len(result) == 2
        assert all(t.name != "exec" for t in result)


class TestIsToolAllowedByPolicyName:
    """Tests for is_tool_allowed_by_policy_name function."""

    def test_none_policy_allows_all(self):
        """Test None policy allows everything."""
        assert is_tool_allowed_by_policy_name("anything", None)

    def test_allowed_by_policy(self):
        """Test tool allowed by policy."""
        policy: ToolPolicy = {"allow": ["read"]}
        assert is_tool_allowed_by_policy_name("read", policy)

    def test_denied_by_policy(self):
        """Test tool denied by policy."""
        policy: ToolPolicy = {"deny": ["read"]}
        assert not is_tool_allowed_by_policy_name("read", policy)


class TestIsToolAllowedByPolicies:
    """Tests for is_tool_allowed_by_policies function."""

    def test_allowed_by_all(self):
        """Test tool must be allowed by all policies."""
        policies: list[ToolPolicy | None] = [
            {"allow": ["read", "write"]},
            {"deny": ["exec"]},
        ]
        assert is_tool_allowed_by_policies("read", policies)

    def test_denied_by_one(self):
        """Test tool denied if any policy denies."""
        policies: list[ToolPolicy | None] = [
            {"allow": ["read"]},
            {"deny": ["read"]},  # This denies read
        ]
        assert not is_tool_allowed_by_policies("read", policies)


# =============================================================================
# Test Profile Resolution
# =============================================================================


class TestResolveToolProfilePolicy:
    """Tests for resolve_tool_profile_policy function."""

    def test_none_profile(self):
        """Test None profile returns None."""
        assert resolve_tool_profile_policy(None) is None

    def test_invalid_profile(self):
        """Test invalid profile returns None."""
        assert resolve_tool_profile_policy("invalid") is None

    def test_minimal_profile(self):
        """Test minimal profile resolves correctly."""
        policy = resolve_tool_profile_policy("minimal")
        assert policy is not None
        assert policy["allow"] == ["session_status"]

    def test_full_profile_returns_none(self):
        """Test full profile returns None (no restrictions)."""
        policy = resolve_tool_profile_policy("full")
        assert policy is None

    def test_coding_profile(self):
        """Test coding profile resolves correctly."""
        policy = resolve_tool_profile_policy("coding")
        assert policy is not None
        assert "allow" in policy
        assert "group:fs" in policy["allow"]


# =============================================================================
# Test Allow List Utilities
# =============================================================================


class TestUnionAllow:
    """Tests for union_allow function."""

    def test_no_extra_returns_base(self):
        """Test no extra returns base unchanged."""
        assert union_allow(["read"], None) == ["read"]
        assert union_allow(["read"], []) == ["read"]

    def test_no_base_adds_wildcard(self):
        """Test no base adds wildcard with alsoAllow."""
        result = union_allow(None, ["read"])
        assert "*" in result
        assert "read" in result

    def test_union_both(self):
        """Test union of base and extra."""
        result = union_allow(["read"], ["write"])
        assert "read" in result
        assert "write" in result

    def test_deduplication(self):
        """Test duplicates are removed."""
        result = union_allow(["read", "write"], ["write", "exec"])
        assert result.count("read") == 1
        assert result.count("write") == 1


class TestPickToolPolicy:
    """Tests for pick_tool_policy function."""

    def test_none_config(self):
        """Test None config returns None."""
        assert pick_tool_policy(None) is None

    def test_allow_only(self):
        """Test config with allow only."""
        config = ToolPolicyConfig(allow=["read"])
        policy = pick_tool_policy(config)
        assert policy is not None
        assert policy["allow"] == ["read"]

    def test_deny_only(self):
        """Test config with deny only."""
        config = ToolPolicyConfig(deny=["exec"])
        policy = pick_tool_policy(config)
        assert policy is not None
        assert policy["deny"] == ["exec"]

    def test_also_allow_no_base(self):
        """Test alsoAllow without allow creates implicit allow-all."""
        config = ToolPolicyConfig(also_allow=["read"])
        policy = pick_tool_policy(config)
        assert policy is not None
        assert "*" in policy["allow"]
        assert "read" in policy["allow"]

    def test_empty_config(self):
        """Test empty config returns None."""
        config = ToolPolicyConfig()
        assert pick_tool_policy(config) is None


class TestCollectExplicitAllowlist:
    """Tests for collect_explicit_allowlist function."""

    def test_empty_policies(self):
        """Test empty policies returns empty list."""
        assert collect_explicit_allowlist([]) == []

    def test_collects_all_allows(self):
        """Test collects allows from all policies."""
        policies: list[ToolPolicy | None] = [
            {"allow": ["read"]},
            {"allow": ["write"]},
        ]
        result = collect_explicit_allowlist(policies)
        assert "read" in result
        assert "write" in result

    def test_skips_none_policies(self):
        """Test skips None policies."""
        policies: list[ToolPolicy | None] = [None, {"allow": ["read"]}]
        result = collect_explicit_allowlist(policies)
        assert result == ["read"]


# =============================================================================
# Test Plugin Tool Groups
# =============================================================================


class TestBuildPluginToolGroups:
    """Tests for build_plugin_tool_groups function."""

    def test_empty_tools(self):
        """Test empty tools returns empty groups."""
        groups = build_plugin_tool_groups([], lambda t: None)
        assert groups.all == []
        assert groups.by_plugin == {}

    def test_groups_by_plugin(self):
        """Test tools are grouped by plugin."""
        tools = [
            Tool(name="plugin_a_tool1"),
            Tool(name="plugin_a_tool2"),
            Tool(name="plugin_b_tool1"),
        ]

        def get_meta(tool: Tool) -> dict[str, str] | None:
            if "plugin_a" in tool.name:
                return {"pluginId": "plugin_a"}
            if "plugin_b" in tool.name:
                return {"pluginId": "plugin_b"}
            return None

        groups = build_plugin_tool_groups(tools, get_meta)
        assert len(groups.all) == 3
        assert "plugin_a" in groups.by_plugin
        assert len(groups.by_plugin["plugin_a"]) == 2


class TestExpandPluginGroups:
    """Tests for expand_plugin_groups function."""

    def test_none_returns_none(self):
        """Test None returns None."""
        groups = PluginToolGroups()
        assert expand_plugin_groups(None, groups) is None

    def test_empty_returns_empty(self):
        """Test empty list returns empty list."""
        groups = PluginToolGroups()
        result = expand_plugin_groups([], groups)
        assert result == []

    def test_expands_group_plugins(self):
        """Test group:plugins is expanded."""
        groups = PluginToolGroups(all=["tool1", "tool2"])
        result = expand_plugin_groups(["group:plugins"], groups)
        assert result == ["tool1", "tool2"]

    def test_expands_plugin_id(self):
        """Test plugin ID is expanded to its tools."""
        groups = PluginToolGroups(by_plugin={"my_plugin": ["tool1", "tool2"]})
        result = expand_plugin_groups(["my_plugin"], groups)
        assert result == ["tool1", "tool2"]


class TestStripPluginOnlyAllowlist:
    """Tests for strip_plugin_only_allowlist function."""

    def test_none_policy(self):
        """Test None policy passes through."""
        groups = PluginToolGroups()
        result = strip_plugin_only_allowlist(None, groups, {"read"})
        assert result.policy is None
        assert result.stripped_allowlist is False

    def test_no_allow_list(self):
        """Test policy without allow passes through."""
        policy: ToolPolicy = {"deny": ["exec"]}
        groups = PluginToolGroups()
        result = strip_plugin_only_allowlist(policy, groups, {"read"})
        assert result.policy == policy
        assert result.stripped_allowlist is False

    def test_keeps_core_allowlist(self):
        """Test allowlist with core tools is kept."""
        policy: ToolPolicy = {"allow": ["read"]}
        groups = PluginToolGroups()
        result = strip_plugin_only_allowlist(policy, groups, {"read"})
        assert result.policy == policy
        assert result.stripped_allowlist is False

    def test_strips_plugin_only_allowlist(self):
        """Test allowlist with only plugin tools is stripped."""
        policy: ToolPolicy = {"allow": ["plugin_tool"]}
        groups = PluginToolGroups(all=["plugin_tool"])
        result = strip_plugin_only_allowlist(policy, groups, {"read"})
        assert "allow" not in (result.policy or {})
        assert result.stripped_allowlist is True


# =============================================================================
# Test Subagent Policy
# =============================================================================


class TestResolveSubagentToolPolicy:
    """Tests for resolve_subagent_tool_policy function."""

    def test_default_deny_list(self):
        """Test default deny list is included."""
        policy = resolve_subagent_tool_policy()
        assert "sessions_spawn" in policy["deny"]
        assert "gateway" in policy["deny"]
        assert "memory_search" in policy["deny"]

    def test_custom_deny(self):
        """Test custom deny is added."""
        policy = resolve_subagent_tool_policy(config_deny=["custom_tool"])
        assert "custom_tool" in policy["deny"]
        assert "sessions_spawn" in policy["deny"]  # Default still included

    def test_custom_allow(self):
        """Test custom allow is set."""
        policy = resolve_subagent_tool_policy(config_allow=["read"])
        assert policy.get("allow") == ["read"]


# =============================================================================
# Test Nine-Layer Filtering
# =============================================================================


class TestFilterToolsNineLayers:
    """Tests for filter_tools_nine_layers function."""

    @pytest.fixture
    def all_tools(self) -> list[Tool]:
        """Create a list of all tools for testing."""
        return [
            Tool(name="read"),
            Tool(name="write"),
            Tool(name="edit"),
            Tool(name="exec"),
            Tool(name="session_status"),
            Tool(name="sessions_spawn"),
            Tool(name="memory_search"),
            Tool(name="web_search"),
            Tool(name="message"),
        ]

    @pytest.fixture
    def core_tool_names(self, all_tools: list[Tool]) -> set[str]:
        """Create core tool names set from all tools."""
        return {normalize_tool_name(t.name) for t in all_tools}

    def test_no_filters_returns_all(self, all_tools: list[Tool], core_tool_names: set[str]):
        """Test no filters returns all tools."""
        context = ToolFilterContext(core_tool_names=core_tool_names)
        result = filter_tools_nine_layers(all_tools, context)
        assert len(result) == len(all_tools)

    def test_profile_filters(self, all_tools: list[Tool], core_tool_names: set[str]):
        """Test profile filter layer."""
        context = ToolFilterContext(
            profile="minimal",
            core_tool_names=core_tool_names,
        )
        result = filter_tools_nine_layers(all_tools, context)
        # Minimal only allows session_status
        assert len(result) == 1
        assert result[0].name == "session_status"

    def test_subagent_filters(self, all_tools: list[Tool], core_tool_names: set[str]):
        """Test subagent filter layer."""
        context = ToolFilterContext(
            subagent_policy=resolve_subagent_tool_policy(),
            core_tool_names=core_tool_names,
        )
        result = filter_tools_nine_layers(all_tools, context)
        # Subagent denies sessions_spawn, memory_search, session_status
        names = [t.name for t in result]
        assert "sessions_spawn" not in names
        assert "memory_search" not in names
        assert "session_status" not in names
        assert "read" in names  # Not denied

    def test_multiple_layers(self, all_tools: list[Tool], core_tool_names: set[str]):
        """Test multiple layers combine."""
        context = ToolFilterContext(
            global_policy={"allow": ["read", "write", "exec", "sessions_spawn"]},
            agent_policy={"deny": ["exec"]},
            core_tool_names=core_tool_names,
        )
        result = filter_tools_nine_layers(all_tools, context)
        names = [t.name for t in result]
        # Global allows: read, write, exec, sessions_spawn
        # Agent denies: exec
        assert "read" in names
        assert "write" in names
        assert "sessions_spawn" in names
        assert "exec" not in names

    def test_sandbox_policy(self, all_tools: list[Tool], core_tool_names: set[str]):
        """Test sandbox policy layer."""
        context = ToolFilterContext(
            sandbox_policy={"deny": ["exec", "write"]},
            core_tool_names=core_tool_names,
        )
        result = filter_tools_nine_layers(all_tools, context)
        names = [t.name for t in result]
        assert "exec" not in names
        assert "write" not in names
        assert "read" in names

    def test_group_policy(self, all_tools: list[Tool], core_tool_names: set[str]):
        """Test group/channel policy layer."""
        context = ToolFilterContext(
            group_policy={"allow": ["group:fs"]},  # read, write, edit, apply_patch
            core_tool_names=core_tool_names,
        )
        result = filter_tools_nine_layers(all_tools, context)
        names = [t.name for t in result]
        assert "read" in names
        assert "write" in names
        assert "edit" in names
        assert "exec" not in names
        assert "message" not in names

    def test_profile_with_also_allow(self, all_tools: list[Tool], core_tool_names: set[str]):
        """Test profile with alsoAllow extends the allow list."""
        context = ToolFilterContext(
            profile="minimal",  # Only session_status
            profile_also_allow=["read"],  # Add read
            core_tool_names=core_tool_names,
        )
        result = filter_tools_nine_layers(all_tools, context)
        names = [t.name for t in result]
        assert "session_status" in names
        assert "read" in names
        assert len(names) == 2

    def test_all_layers_apply_in_order(self, all_tools: list[Tool], core_tool_names: set[str]):
        """Test all nine layers apply in order."""
        context = ToolFilterContext(
            # Layer 1: Profile - start with full (no filter)
            profile="full",
            # Layer 3: Global - allow specific tools
            global_policy={"allow": ["read", "write", "exec", "session_status"]},
            # Layer 5: Agent - deny exec
            agent_policy={"deny": ["exec"]},
            # Layer 8: Sandbox - deny write
            sandbox_policy={"deny": ["write"]},
            core_tool_names=core_tool_names,
        )
        result = filter_tools_nine_layers(all_tools, context)
        names = [t.name for t in result]

        # After all layers:
        # - Global allows: read, write, exec, session_status
        # - Agent denies: exec
        # - Sandbox denies: write
        # Result: read, session_status
        assert "read" in names
        assert "session_status" in names
        assert "write" not in names  # Denied by sandbox
        assert "exec" not in names  # Denied by agent


# =============================================================================
# Test ToolProfileId Enum
# =============================================================================


class TestToolProfileId:
    """Tests for ToolProfileId enum."""

    def test_values(self):
        """Test enum values match MoltBot."""
        assert ToolProfileId.MINIMAL.value == "minimal"
        assert ToolProfileId.CODING.value == "coding"
        assert ToolProfileId.MESSAGING.value == "messaging"
        assert ToolProfileId.FULL.value == "full"

    def test_from_string(self):
        """Test enum can be created from string."""
        assert ToolProfileId("minimal") == ToolProfileId.MINIMAL
        assert ToolProfileId("full") == ToolProfileId.FULL


# =============================================================================
# Test Edge Cases
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_tool_list(self):
        """Test filtering empty tool list."""
        result = filter_tools_by_policy([], {"allow": ["read"]})
        assert result == []

    def test_wildcard_deny(self):
        """Test wildcard deny blocks everything."""
        tools = [Tool(name="read"), Tool(name="write")]
        policy: ToolPolicy = {"deny": ["*"]}
        result = filter_tools_by_policy(tools, policy)
        assert result == []

    def test_wildcard_allow(self):
        """Test wildcard allow allows everything."""
        tools = [Tool(name="read"), Tool(name="write")]
        policy: ToolPolicy = {"allow": ["*"]}
        result = filter_tools_by_policy(tools, policy)
        assert len(result) == 2

    def test_pattern_with_special_chars(self):
        """Test pattern with special regex characters."""
        pattern = compile_pattern("tool.name")
        assert pattern.kind == "exact"
        assert pattern.value == "tool.name"

    def test_case_insensitive_matching(self):
        """Test tool names are matched case-insensitively."""
        policy: ToolPolicy = {"allow": ["READ"]}
        matcher = make_tool_policy_matcher(policy)
        assert matcher("read")
        assert matcher("READ")
        assert matcher("Read")


# =============================================================================
# Integration Tests
# =============================================================================


class TestIntegration:
    """Integration tests for real-world scenarios."""

    def test_coding_profile_scenario(self):
        """Test coding profile allows expected tools."""
        tools = [
            Tool(name="read"),
            Tool(name="write"),
            Tool(name="edit"),
            Tool(name="exec"),
            Tool(name="sessions_spawn"),
            Tool(name="memory_search"),
            Tool(name="message"),
            Tool(name="cron"),
        ]
        core_tool_names = {normalize_tool_name(t.name) for t in tools}
        context = ToolFilterContext(profile="coding", core_tool_names=core_tool_names)
        result = filter_tools_nine_layers(tools, context)
        names = [t.name for t in result]

        # Coding allows: fs, runtime, sessions, memory
        assert "read" in names
        assert "write" in names
        assert "edit" in names
        assert "exec" in names
        assert "sessions_spawn" in names
        assert "memory_search" in names
        # Coding does not allow: messaging, automation
        assert "message" not in names
        assert "cron" not in names

    def test_messaging_profile_scenario(self):
        """Test messaging profile allows expected tools."""
        tools = [
            Tool(name="message"),
            Tool(name="sessions_list"),
            Tool(name="sessions_send"),
            Tool(name="session_status"),
            Tool(name="read"),
            Tool(name="exec"),
        ]
        core_tool_names = {normalize_tool_name(t.name) for t in tools}
        context = ToolFilterContext(profile="messaging", core_tool_names=core_tool_names)
        result = filter_tools_nine_layers(tools, context)
        names = [t.name for t in result]

        # Messaging allows: messaging, session tools
        assert "message" in names
        assert "sessions_list" in names
        assert "sessions_send" in names
        assert "session_status" in names
        # Messaging does not allow: fs, runtime
        assert "read" not in names
        assert "exec" not in names

    def test_subagent_in_sandbox(self):
        """Test subagent with sandbox restrictions."""
        tools = [
            Tool(name="read"),
            Tool(name="write"),
            Tool(name="exec"),
            Tool(name="sessions_spawn"),
            Tool(name="memory_search"),
            Tool(name="cron"),
        ]
        core_tool_names = {normalize_tool_name(t.name) for t in tools}
        context = ToolFilterContext(
            sandbox_policy={"deny": ["exec"]},
            subagent_policy=resolve_subagent_tool_policy(),
            core_tool_names=core_tool_names,
        )
        result = filter_tools_nine_layers(tools, context)
        names = [t.name for t in result]

        # Sandbox denies: exec
        # Subagent denies: sessions_spawn, memory_search, cron
        assert "read" in names
        assert "write" in names
        assert "exec" not in names
        assert "sessions_spawn" not in names
        assert "memory_search" not in names
        assert "cron" not in names
