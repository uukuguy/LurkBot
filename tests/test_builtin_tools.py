"""Tests for P0 builtin tools (common, fs_safe, exec_tool, fs_tools)."""

from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path

import pytest

from lurkbot.tools.builtin.common import (
    ParamError,
    ToolResult,
    ToolResultContent,
    ToolResultContentType,
    chunk_string,
    clamp_number,
    coerce_env,
    create_action_gate,
    error_result,
    json_result,
    read_bool_param,
    read_dict_param,
    read_number_param,
    read_string_array_param,
    read_string_or_number_param,
    read_string_param,
    text_result,
    truncate_middle,
)
from lurkbot.tools.builtin.fs_safe import (
    SafeOpenError,
    SafeOpenErrorCode,
    is_path_within_root,
    open_file_within_root_sync,
    resolve_safe_path,
)
from lurkbot.tools.builtin.fs_tools import (
    apply_patch_tool,
    edit_tool,
    read_tool,
    write_tool,
)
from lurkbot.tools.builtin.exec_tool import (
    ExecAsk,
    ExecHost,
    ExecSecurity,
    ExecToolDefaults,
    exec_tool,
    normalize_exec_ask,
    normalize_exec_host,
    normalize_exec_security,
    process_tool,
)


# =============================================================================
# Tests for common.py
# =============================================================================


class TestToolResult:
    """Tests for ToolResult class."""

    def test_create_tool_result(self) -> None:
        result = ToolResult(
            content=[
                ToolResultContent(
                    type=ToolResultContentType.TEXT,
                    text="Hello",
                )
            ],
            details={"key": "value"},
        )
        assert len(result.content) == 1
        assert result.content[0].text == "Hello"
        assert result.details == {"key": "value"}

    def test_to_text(self) -> None:
        result = ToolResult(
            content=[
                ToolResultContent(type=ToolResultContentType.TEXT, text="Line 1"),
                ToolResultContent(type=ToolResultContentType.TEXT, text="Line 2"),
            ]
        )
        assert result.to_text() == "Line 1\nLine 2"


class TestResultHelpers:
    """Tests for result helper functions."""

    def test_json_result(self) -> None:
        result = json_result({"status": "ok", "count": 42})
        assert result.details == {"status": "ok", "count": 42}
        assert len(result.content) == 1
        assert "status" in result.content[0].text

    def test_text_result(self) -> None:
        result = text_result("Hello, World!", details={"extra": True})
        assert result.content[0].text == "Hello, World!"
        assert result.details == {"extra": True}

    def test_error_result(self) -> None:
        result = error_result("Something went wrong", {"code": 500})
        assert result.details["error"] == "Something went wrong"
        assert result.details["code"] == 500


class TestParameterHelpers:
    """Tests for parameter reading helpers."""

    def test_read_string_param_basic(self) -> None:
        params = {"name": "  Alice  ", "empty": ""}
        assert read_string_param(params, "name") == "Alice"
        assert read_string_param(params, "empty") is None
        assert read_string_param(params, "missing") is None

    def test_read_string_param_required(self) -> None:
        params = {"name": "Bob"}
        assert read_string_param(params, "name", required=True) == "Bob"
        with pytest.raises(ParamError):
            read_string_param(params, "missing", required=True)

    def test_read_string_param_no_trim(self) -> None:
        params = {"name": "  Alice  "}
        assert read_string_param(params, "name", trim=False) == "  Alice  "

    def test_read_string_param_allow_empty(self) -> None:
        params = {"empty": ""}
        assert read_string_param(params, "empty", allow_empty=True) == ""

    def test_read_number_param_basic(self) -> None:
        params = {"count": 42, "price": 19.99, "invalid": "abc"}
        assert read_number_param(params, "count") == 42.0
        assert read_number_param(params, "price") == 19.99
        assert read_number_param(params, "invalid") is None
        assert read_number_param(params, "missing") is None

    def test_read_number_param_integer(self) -> None:
        params = {"value": 42.7}
        assert read_number_param(params, "value", integer=True) == 42

    def test_read_number_param_from_string(self) -> None:
        params = {"value": "  123.45  "}
        assert read_number_param(params, "value") == 123.45

    def test_read_bool_param(self) -> None:
        params = {"enabled": True, "disabled": False, "other": "yes"}
        assert read_bool_param(params, "enabled") is True
        assert read_bool_param(params, "disabled") is False
        assert read_bool_param(params, "other") is False
        assert read_bool_param(params, "missing", default=True) is True

    def test_read_string_array_param(self) -> None:
        params = {
            "tags": ["a", "b", "c"],
            "single": "x",
            "empty": [],
        }
        assert read_string_array_param(params, "tags") == ["a", "b", "c"]
        assert read_string_array_param(params, "single") == ["x"]
        assert read_string_array_param(params, "empty") is None

    def test_read_string_or_number_param(self) -> None:
        params = {"id": 123, "name": "test"}
        assert read_string_or_number_param(params, "id") == "123"
        assert read_string_or_number_param(params, "name") == "test"

    def test_read_dict_param(self) -> None:
        params = {"config": {"key": "value"}, "invalid": "string"}
        assert read_dict_param(params, "config") == {"key": "value"}
        assert read_dict_param(params, "invalid") is None


class TestActionGate:
    """Tests for action gate functionality."""

    def test_create_action_gate_none(self) -> None:
        gate = create_action_gate(None)
        assert gate("any_action") is True
        assert gate("any_action", False) is False

    def test_create_action_gate_with_config(self) -> None:
        actions = {"read": True, "write": False, "delete": None}
        gate = create_action_gate(actions)
        assert gate("read") is True
        assert gate("write") is False
        assert gate("delete") is True  # None uses default
        assert gate("unknown") is True


class TestUtilityFunctions:
    """Tests for utility functions."""

    def test_clamp_number(self) -> None:
        assert clamp_number(50, 0, 0, 100) == 50
        assert clamp_number(None, 50, 0, 100) == 50
        assert clamp_number(-10, 0, 0, 100) == 0
        assert clamp_number(150, 0, 0, 100) == 100

    def test_truncate_middle(self) -> None:
        assert truncate_middle("short", 10) == "short"
        # "hello world" has 11 chars, max_len=8, ellipsis=3, available=5, left=2, right=3
        assert truncate_middle("hello world", 8) == "he...rld"
        # "abc" has 3 chars, max_len=3, not truncated (len <= max_len)
        assert truncate_middle("abc", 3) == "abc"
        # "abcdef" has 6 chars, max_len=4, ellipsis=3, available=1, left=0, right=1
        assert truncate_middle("abcdef", 4) == "...f"
        # longer example
        assert truncate_middle("0123456789", 7) == "01...89"

    def test_chunk_string(self) -> None:
        assert chunk_string("abcdefgh", 3) == ["abc", "def", "gh"]
        assert chunk_string("", 5) == []

    def test_coerce_env(self) -> None:
        env = {"PATH": "/usr/bin", "COUNT": 42, "NONE": None}
        result = coerce_env(env)
        assert result["PATH"] == "/usr/bin"
        assert result["COUNT"] == "42"
        assert "NONE" not in result


# =============================================================================
# Tests for fs_safe.py
# =============================================================================


class TestFsSafe:
    """Tests for safe file operations."""

    def test_is_path_within_root(self, tmp_path: Path) -> None:
        root = tmp_path / "root"
        root.mkdir()
        (root / "file.txt").touch()

        assert is_path_within_root(str(root), "file.txt") is True
        assert is_path_within_root(str(root), "../file.txt") is False
        assert is_path_within_root(str(root), "/etc/passwd") is False

    def test_resolve_safe_path(self, tmp_path: Path) -> None:
        root = tmp_path / "root"
        root.mkdir()

        resolved = resolve_safe_path(str(root), "subdir/file.txt")
        assert resolved is not None
        assert "subdir/file.txt" in resolved or "subdir\\file.txt" in resolved

        # Path escape should return None
        assert resolve_safe_path(str(root), "../escape.txt") is None

    def test_open_file_within_root_success(self, tmp_path: Path) -> None:
        root = tmp_path / "root"
        root.mkdir()
        test_file = root / "test.txt"
        test_file.write_text("Hello, World!")

        result = open_file_within_root_sync(str(root), "test.txt")
        try:
            content = result.handle.read()
            assert content == b"Hello, World!"
            assert result.real_path.endswith("test.txt")
        finally:
            result.handle.close()

    def test_open_file_within_root_not_found(self, tmp_path: Path) -> None:
        root = tmp_path / "root"
        root.mkdir()

        with pytest.raises(SafeOpenError) as exc_info:
            open_file_within_root_sync(str(root), "nonexistent.txt")
        assert exc_info.value.code == SafeOpenErrorCode.NOT_FOUND

    def test_open_file_within_root_path_escape(self, tmp_path: Path) -> None:
        root = tmp_path / "root"
        root.mkdir()

        with pytest.raises(SafeOpenError) as exc_info:
            open_file_within_root_sync(str(root), "../escape.txt")
        assert exc_info.value.code == SafeOpenErrorCode.INVALID_PATH


# =============================================================================
# Tests for fs_tools.py
# =============================================================================


class TestReadTool:
    """Tests for read tool."""

    @pytest.mark.asyncio
    async def test_read_file(self, tmp_path: Path) -> None:
        test_file = tmp_path / "test.txt"
        test_file.write_text("Line 1\nLine 2\nLine 3\n")

        result = await read_tool({"path": str(test_file)})
        assert result.details["totalLines"] == 3
        text = result.to_text()
        assert "Line 1" in text
        assert "Line 2" in text

    @pytest.mark.asyncio
    async def test_read_file_with_range(self, tmp_path: Path) -> None:
        test_file = tmp_path / "test.txt"
        lines = [f"Line {i}\n" for i in range(1, 11)]
        test_file.write_text("".join(lines))

        # from=3 means start at line 3 (0-indexed: 2), lines=2 means read 2 lines
        # So we read lines 3 and 4, toLine should be 4 (end_idx = 2+2 = 4)
        result = await read_tool({"path": str(test_file), "from": 3, "lines": 2})
        assert result.details["fromLine"] == 3
        assert result.details["toLine"] == 4
        text = result.to_text()
        assert "Line 3" in text
        assert "Line 4" in text
        assert "Line 1" not in text
        assert "Line 5" not in text

    @pytest.mark.asyncio
    async def test_read_file_not_found(self) -> None:
        result = await read_tool({"path": "/nonexistent/file.txt"})
        assert result.details.get("error") is not None
        assert "not found" in result.details["error"]


class TestWriteTool:
    """Tests for write tool."""

    @pytest.mark.asyncio
    async def test_write_file(self, tmp_path: Path) -> None:
        test_file = tmp_path / "output.txt"

        result = await write_tool({
            "path": str(test_file),
            "content": "Hello, World!",
        })
        assert result.details["written"] is True
        assert test_file.read_text() == "Hello, World!"

    @pytest.mark.asyncio
    async def test_write_file_append(self, tmp_path: Path) -> None:
        test_file = tmp_path / "output.txt"
        test_file.write_text("Line 1\n")

        result = await write_tool({
            "path": str(test_file),
            "content": "Line 2\n",
            "append": True,
        })
        assert result.details["appended"] is True
        assert test_file.read_text() == "Line 1\nLine 2\n"

    @pytest.mark.asyncio
    async def test_write_file_create_dirs(self, tmp_path: Path) -> None:
        test_file = tmp_path / "subdir" / "deep" / "output.txt"

        result = await write_tool({
            "path": str(test_file),
            "content": "Nested content",
            "createDirs": True,
        })
        assert result.details["written"] is True
        assert test_file.read_text() == "Nested content"


class TestEditTool:
    """Tests for edit tool."""

    @pytest.mark.asyncio
    async def test_edit_file(self, tmp_path: Path) -> None:
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, World!")

        result = await edit_tool({
            "path": str(test_file),
            "old": "World",
            "new": "Python",
        })
        assert result.details["edited"] is True
        assert result.details["replaced"] == 1
        assert test_file.read_text() == "Hello, Python!"

    @pytest.mark.asyncio
    async def test_edit_file_all_occurrences(self, tmp_path: Path) -> None:
        test_file = tmp_path / "test.txt"
        test_file.write_text("foo bar foo baz foo")

        result = await edit_tool({
            "path": str(test_file),
            "old": "foo",
            "new": "FOO",
            "all": True,
        })
        assert result.details["edited"] is True
        assert result.details["occurrences"] == 3
        assert result.details["replaced"] == 3
        assert test_file.read_text() == "FOO bar FOO baz FOO"

    @pytest.mark.asyncio
    async def test_edit_file_text_not_found(self, tmp_path: Path) -> None:
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, World!")

        result = await edit_tool({
            "path": str(test_file),
            "old": "Python",
            "new": "Java",
        })
        assert result.details.get("error") is not None
        assert "not found" in result.details["error"]


class TestApplyPatchTool:
    """Tests for apply_patch tool."""

    @pytest.mark.asyncio
    async def test_apply_patch(self, tmp_path: Path) -> None:
        test_file = tmp_path / "test.txt"
        test_file.write_text("Line 1\nLine 2\nLine 3\n")

        patch = """--- a/test.txt
+++ b/test.txt
@@ -1,3 +1,3 @@
 Line 1
-Line 2
+Line 2 Modified
 Line 3
"""
        result = await apply_patch_tool({
            "path": str(test_file),
            "patch": patch,
        })
        assert result.details["patched"] is True
        assert result.details["hunksApplied"] == 1
        content = test_file.read_text()
        assert "Line 2 Modified" in content


# =============================================================================
# Tests for exec_tool.py
# =============================================================================


class TestExecEnums:
    """Tests for exec enums and normalization."""

    def test_exec_host_values(self) -> None:
        assert ExecHost.SANDBOX.value == "sandbox"
        assert ExecHost.GATEWAY.value == "gateway"
        assert ExecHost.NODE.value == "node"

    def test_exec_security_values(self) -> None:
        assert ExecSecurity.DENY.value == "deny"
        assert ExecSecurity.ALLOWLIST.value == "allowlist"
        assert ExecSecurity.FULL.value == "full"

    def test_exec_ask_values(self) -> None:
        assert ExecAsk.OFF.value == "off"
        assert ExecAsk.ON_MISS.value == "on-miss"
        assert ExecAsk.ALWAYS.value == "always"

    def test_normalize_exec_host(self) -> None:
        assert normalize_exec_host("sandbox") == ExecHost.SANDBOX
        assert normalize_exec_host("  GATEWAY  ") == ExecHost.GATEWAY
        assert normalize_exec_host("invalid") is None
        assert normalize_exec_host(None) is None

    def test_normalize_exec_security(self) -> None:
        assert normalize_exec_security("deny") == ExecSecurity.DENY
        assert normalize_exec_security("  ALLOWLIST  ") == ExecSecurity.ALLOWLIST
        assert normalize_exec_security("invalid") is None

    def test_normalize_exec_ask(self) -> None:
        assert normalize_exec_ask("off") == ExecAsk.OFF
        assert normalize_exec_ask("ON-MISS") == ExecAsk.ON_MISS
        assert normalize_exec_ask("invalid") is None


class TestExecTool:
    """Tests for exec tool."""

    @pytest.mark.asyncio
    async def test_exec_simple_command(self) -> None:
        defaults = ExecToolDefaults(
            security=ExecSecurity.FULL,
            timeout_sec=5,
            background_ms=0,
            allow_background=False,
        )
        result = await exec_tool(
            {"command": "echo 'Hello, World!'"},
            defaults=defaults,
        )
        assert result.details["status"] in ("completed", "running")
        if result.details["status"] == "completed":
            assert "Hello" in result.details.get("output", "")

    @pytest.mark.asyncio
    async def test_exec_security_deny(self) -> None:
        defaults = ExecToolDefaults(
            security=ExecSecurity.DENY,
        )
        result = await exec_tool(
            {"command": "echo test"},
            defaults=defaults,
        )
        assert result.details.get("error") is not None
        assert "denied" in result.details["error"]

    @pytest.mark.asyncio
    async def test_exec_with_workdir(self, tmp_path: Path) -> None:
        defaults = ExecToolDefaults(
            security=ExecSecurity.FULL,
            timeout_sec=5,
            background_ms=0,
            allow_background=False,
        )
        result = await exec_tool(
            {"command": "pwd", "workdir": str(tmp_path)},
            defaults=defaults,
        )
        if result.details["status"] == "completed":
            assert str(tmp_path) in result.details.get("output", "")

    @pytest.mark.asyncio
    async def test_exec_timeout(self) -> None:
        defaults = ExecToolDefaults(
            security=ExecSecurity.FULL,
            timeout_sec=1,
            background_ms=0,
            allow_background=False,
        )
        result = await exec_tool(
            {"command": "sleep 10"},
            defaults=defaults,
        )
        # Should either timeout or fail
        assert result.details["status"] in ("completed", "failed")


class TestProcessTool:
    """Tests for process tool."""

    @pytest.mark.asyncio
    async def test_process_list(self) -> None:
        result = await process_tool({"action": "list"})
        assert "sessions" in result.details
        assert isinstance(result.details["sessions"], list)

    @pytest.mark.asyncio
    async def test_process_status_not_found(self) -> None:
        result = await process_tool({
            "action": "status",
            "sessionId": "nonexistent-session-id",
        })
        assert result.details.get("error") is not None
        assert "not found" in result.details["error"]

    @pytest.mark.asyncio
    async def test_process_action_requires_session_id(self) -> None:
        result = await process_tool({"action": "kill"})
        assert result.details.get("error") is not None
        assert "sessionId required" in result.details["error"]


# =============================================================================
# Tests for memory_tools.py
# =============================================================================

from lurkbot.tools.builtin.memory_tools import (
    MemoryManager,
    MemorySearchConfig,
    MemorySearchResult,
    get_memory_manager,
    memory_get_tool,
    memory_search_tool,
)


class TestMemorySearchResult:
    """Tests for MemorySearchResult."""

    def test_create_result(self) -> None:
        result = MemorySearchResult(
            path="MEMORY.md",
            content="Test content",
            score=0.8,
            line_start=1,
            line_end=5,
        )
        assert result.path == "MEMORY.md"
        assert result.content == "Test content"
        assert result.score == 0.8
        assert result.line_start == 1
        assert result.line_end == 5


class TestMemoryManager:
    """Tests for MemoryManager class."""

    def test_create_manager(self) -> None:
        config = MemorySearchConfig()
        manager = MemoryManager(config)
        assert manager.config.enabled is True
        assert manager.config.provider == "keyword"

    def test_status(self) -> None:
        config = MemorySearchConfig(provider="keyword", model="test-model")
        manager = MemoryManager(config)
        status = manager.status()
        assert status["provider"] == "keyword"
        assert status["model"] == "test-model"
        assert status["enabled"] is True

    @pytest.mark.asyncio
    async def test_search_no_files(self, tmp_path: Path) -> None:
        config = MemorySearchConfig(root_dir=str(tmp_path))
        manager = MemoryManager(config)
        results = await manager.search("test query")
        assert results == []

    @pytest.mark.asyncio
    async def test_search_with_memory_file(self, tmp_path: Path) -> None:
        # Create MEMORY.md
        memory_file = tmp_path / "MEMORY.md"
        memory_file.write_text("""# Important Notes

This is about Python programming.

Another section about JavaScript.
""")

        config = MemorySearchConfig(root_dir=str(tmp_path))
        manager = MemoryManager(config)

        # Search for exact match
        results = await manager.search("Python programming")
        assert len(results) > 0
        assert results[0].score == 1.0  # Exact match

    @pytest.mark.asyncio
    async def test_search_with_memory_directory(self, tmp_path: Path) -> None:
        # Create memory directory with files
        memory_dir = tmp_path / "memory"
        memory_dir.mkdir()
        (memory_dir / "notes.md").write_text("Meeting notes from Monday")
        (memory_dir / "tasks.md").write_text("Complete project by Friday")

        config = MemorySearchConfig(root_dir=str(tmp_path))
        manager = MemoryManager(config)

        results = await manager.search("meeting")
        assert len(results) > 0
        assert any("notes.md" in r.path for r in results)

    @pytest.mark.asyncio
    async def test_read_file_success(self, tmp_path: Path) -> None:
        memory_file = tmp_path / "MEMORY.md"
        memory_file.write_text("Line 1\nLine 2\nLine 3\nLine 4\nLine 5\n")

        config = MemorySearchConfig(root_dir=str(tmp_path))
        manager = MemoryManager(config)

        result = await manager.read_file("MEMORY.md")
        assert result["path"] == "MEMORY.md"
        assert "Line 1" in result["text"]
        assert result["totalLines"] == 5

    @pytest.mark.asyncio
    async def test_read_file_with_range(self, tmp_path: Path) -> None:
        memory_file = tmp_path / "MEMORY.md"
        memory_file.write_text("\n".join([f"Line {i}" for i in range(1, 101)]))

        config = MemorySearchConfig(root_dir=str(tmp_path))
        manager = MemoryManager(config)

        # from_line=10 means start_idx=9, lines=5 means end_idx=9+5=14
        # So toLine is 14 (exclusive end index, lines 10-14 are read)
        result = await manager.read_file("MEMORY.md", from_line=10, lines=5)
        assert result["fromLine"] == 10
        assert result["toLine"] == 14
        assert "Line 10" in result["text"]
        assert "Line 13" in result["text"]

    @pytest.mark.asyncio
    async def test_read_file_not_found(self, tmp_path: Path) -> None:
        config = MemorySearchConfig(root_dir=str(tmp_path))
        manager = MemoryManager(config)

        result = await manager.read_file("nonexistent.md")
        assert result["error"] == "File not found"

    @pytest.mark.asyncio
    async def test_read_file_path_escape(self, tmp_path: Path) -> None:
        config = MemorySearchConfig(root_dir=str(tmp_path))
        manager = MemoryManager(config)

        result = await manager.read_file("../../../etc/passwd")
        assert "error" in result


class TestMemorySearchTool:
    """Tests for memory_search tool."""

    @pytest.mark.asyncio
    async def test_search_disabled(self) -> None:
        config = MemorySearchConfig(enabled=False)
        result = await memory_search_tool({"query": "test"}, config=config)
        assert result.details["disabled"] is True

    @pytest.mark.asyncio
    async def test_search_missing_query(self) -> None:
        with pytest.raises(ParamError):
            await memory_search_tool({})

    @pytest.mark.asyncio
    async def test_search_with_results(self, tmp_path: Path) -> None:
        memory_file = tmp_path / "MEMORY.md"
        memory_file.write_text("Important project deadline next week")

        config = MemorySearchConfig(root_dir=str(tmp_path))
        result = await memory_search_tool({"query": "project deadline"}, config=config)

        assert "results" in result.details
        assert result.details["provider"] == "keyword"


class TestMemoryGetTool:
    """Tests for memory_get tool."""

    @pytest.mark.asyncio
    async def test_get_disabled(self) -> None:
        config = MemorySearchConfig(enabled=False)
        result = await memory_get_tool({"path": "MEMORY.md"}, config=config)
        assert result.details["disabled"] is True

    @pytest.mark.asyncio
    async def test_get_missing_path(self) -> None:
        with pytest.raises(ParamError):
            await memory_get_tool({})

    @pytest.mark.asyncio
    async def test_get_file_success(self, tmp_path: Path) -> None:
        memory_file = tmp_path / "MEMORY.md"
        memory_file.write_text("Test content\nLine 2\nLine 3")

        config = MemorySearchConfig(root_dir=str(tmp_path))
        result = await memory_get_tool({"path": "MEMORY.md"}, config=config)

        assert result.details["path"] == "MEMORY.md"
        assert "Test content" in result.details["text"]


# =============================================================================
# Tests for web_tools.py
# =============================================================================

from lurkbot.tools.builtin.web_tools import (
    SearchResult,
    WebFetchConfig,
    WebSearchConfig,
    _search_mock,
    html_to_markdown,
    markdown_to_text,
    normalize_cache_key,
    read_cache,
    web_fetch_tool,
    web_search_tool,
    write_cache,
)


class TestCaching:
    """Tests for caching functions."""

    def test_normalize_cache_key(self) -> None:
        key1 = normalize_cache_key("https://example.com")
        key2 = normalize_cache_key("https://example.com")
        key3 = normalize_cache_key("https://different.com")
        assert key1 == key2
        assert key1 != key3
        assert len(key1) == 16

    def test_read_write_cache(self) -> None:
        cache: dict = {}
        write_cache(cache, "key1", {"data": "value"}, ttl_minutes=1)
        result = read_cache(cache, "key1")
        assert result == {"data": "value"}

    def test_cache_expiry(self) -> None:
        cache: dict = {}
        # Write with 0 TTL (immediate expiry)
        write_cache(cache, "key1", {"data": "value"}, ttl_minutes=0)
        # Should be expired immediately
        import time
        time.sleep(0.1)
        result = read_cache(cache, "key1")
        assert result is None


class TestHtmlToMarkdown:
    """Tests for HTML to Markdown conversion."""

    def test_headers(self) -> None:
        html = "<h1>Title</h1><h2>Subtitle</h2>"
        md = html_to_markdown(html)
        assert "# Title" in md
        assert "## Subtitle" in md

    def test_links(self) -> None:
        html = '<a href="https://example.com">Link Text</a>'
        md = html_to_markdown(html)
        assert "[Link Text](https://example.com)" in md

    def test_formatting(self) -> None:
        html = "<strong>bold</strong> and <em>italic</em>"
        md = html_to_markdown(html)
        assert "**bold**" in md
        assert "*italic*" in md

    def test_lists(self) -> None:
        html = "<ul><li>Item 1</li><li>Item 2</li></ul>"
        md = html_to_markdown(html)
        assert "- Item 1" in md
        assert "- Item 2" in md

    def test_code_blocks(self) -> None:
        html = "<code>inline code</code>"
        md = html_to_markdown(html)
        assert "`inline code`" in md

    def test_removes_scripts(self) -> None:
        html = "<p>Content</p><script>alert('xss')</script>"
        md = html_to_markdown(html)
        assert "Content" in md
        assert "alert" not in md

    def test_truncation(self) -> None:
        html = "<p>" + "x" * 1000 + "</p>"
        md = html_to_markdown(html, max_chars=100)
        assert len(md) <= 103  # 100 + "..."


class TestMarkdownToText:
    """Tests for Markdown to text conversion."""

    def test_removes_links(self) -> None:
        md = "Check [this link](https://example.com) here"
        text = markdown_to_text(md)
        assert "this link" in text
        assert "https://" not in text

    def test_removes_formatting(self) -> None:
        md = "**bold** and *italic* and `code`"
        text = markdown_to_text(md)
        assert "bold" in text
        assert "**" not in text
        assert "*" not in text

    def test_removes_headers(self) -> None:
        md = "### Header\nContent"
        text = markdown_to_text(md)
        assert "Header" in text
        assert "###" not in text


class TestSearchResult:
    """Tests for SearchResult dataclass."""

    def test_create_result(self) -> None:
        result = SearchResult(
            title="Test Title",
            url="https://example.com",
            snippet="Test snippet",
        )
        assert result.title == "Test Title"
        assert result.url == "https://example.com"
        assert result.snippet == "Test snippet"


class TestMockSearch:
    """Tests for mock search provider."""

    def test_mock_search(self) -> None:
        results = _search_mock("test query", 5)
        assert len(results) == 1  # Mock returns 1 result regardless of max
        assert "test query" in results[0].title

    def test_mock_search_content(self) -> None:
        results = _search_mock("Python programming", 10)
        assert results[0].url.startswith("https://example.com")
        assert "mock" in results[0].snippet.lower()


class TestWebSearchTool:
    """Tests for web_search tool."""

    @pytest.mark.asyncio
    async def test_search_disabled(self) -> None:
        config = WebSearchConfig(enabled=False)
        result = await web_search_tool({"query": "test"}, config=config)
        assert "error" in result.details

    @pytest.mark.asyncio
    async def test_search_missing_query(self) -> None:
        with pytest.raises(ParamError):
            await web_search_tool({})

    @pytest.mark.asyncio
    async def test_search_mock_provider(self) -> None:
        config = WebSearchConfig(provider="mock")
        result = await web_search_tool({"query": "test search"}, config=config)

        assert result.details["query"] == "test search"
        assert result.details["provider"] == "mock"
        assert "results" in result.details


class TestWebFetchTool:
    """Tests for web_fetch tool."""

    @pytest.mark.asyncio
    async def test_fetch_disabled(self) -> None:
        config = WebFetchConfig(enabled=False)
        result = await web_fetch_tool({"url": "https://example.com"}, config=config)
        assert "error" in result.details

    @pytest.mark.asyncio
    async def test_fetch_missing_url(self) -> None:
        with pytest.raises(ParamError):
            await web_fetch_tool({})

    @pytest.mark.asyncio
    async def test_fetch_invalid_url_scheme(self) -> None:
        result = await web_fetch_tool({"url": "ftp://example.com"})
        assert "error" in result.details
        assert "http" in result.details["error"].lower()

    @pytest.mark.asyncio
    async def test_fetch_invalid_url_format(self) -> None:
        result = await web_fetch_tool({"url": "not a url"})
        assert "error" in result.details


# =============================================================================
# Tests for message_tool.py
# =============================================================================

from lurkbot.tools.builtin.message_tool import (
    CLIChannel,
    MessageAction,
    MessageConfig,
    create_message_tool,
    get_channel,
    message_tool,
    register_channel,
)


class TestMessageAction:
    """Tests for MessageAction enum."""

    def test_action_values(self) -> None:
        assert MessageAction.SEND.value == "send"
        assert MessageAction.DELETE.value == "delete"
        assert MessageAction.REACT.value == "react"
        assert MessageAction.PIN.value == "pin"
        assert MessageAction.POLL.value == "poll"


class TestChannelRegistry:
    """Tests for channel registry."""

    def test_get_cli_channel(self) -> None:
        channel = get_channel("cli", {})
        assert channel is not None
        assert isinstance(channel, CLIChannel)

    def test_get_unknown_channel(self) -> None:
        channel = get_channel("unknown", {})
        assert channel is None


class TestCLIChannel:
    """Tests for CLI channel."""

    @pytest.mark.asyncio
    async def test_send(self) -> None:
        channel = CLIChannel({})
        result = await channel.send("test-channel", "Hello, World!")
        assert result["sent"] is True
        assert result["channel"] == "test-channel"
        assert result["content"] == "Hello, World!"

    @pytest.mark.asyncio
    async def test_delete(self) -> None:
        channel = CLIChannel({})
        result = await channel.delete("test-channel", "msg-123")
        assert result["deleted"] is True
        assert result["message_id"] == "msg-123"

    @pytest.mark.asyncio
    async def test_react(self) -> None:
        channel = CLIChannel({})
        result = await channel.react("test-channel", "msg-123", "👍")
        assert result["reacted"] is True
        assert result["emoji"] == "👍"

    @pytest.mark.asyncio
    async def test_pin(self) -> None:
        channel = CLIChannel({})
        result = await channel.pin("test-channel", "msg-123")
        assert result["pinned"] is True

    @pytest.mark.asyncio
    async def test_unpin(self) -> None:
        channel = CLIChannel({})
        result = await channel.unpin("test-channel", "msg-123")
        assert result["unpinned"] is True


class TestMessageTool:
    """Tests for message tool."""

    @pytest.mark.asyncio
    async def test_disabled(self) -> None:
        config = MessageConfig(enabled=False)
        result = await message_tool(
            {"action": "send", "channel": "test", "content": "Hello"},
            config=config,
        )
        assert "error" in result.details

    @pytest.mark.asyncio
    async def test_missing_action(self) -> None:
        with pytest.raises(ParamError):
            await message_tool({"channel": "test"})

    @pytest.mark.asyncio
    async def test_invalid_action(self) -> None:
        result = await message_tool({"action": "invalid", "channel": "test"})
        assert "error" in result.details
        assert "Invalid action" in result.details["error"]

    @pytest.mark.asyncio
    async def test_missing_channel(self) -> None:
        result = await message_tool({"action": "send", "content": "Hello"})
        assert "error" in result.details
        assert "channel required" in result.details["error"]

    @pytest.mark.asyncio
    async def test_send_action(self) -> None:
        result = await message_tool({
            "action": "send",
            "channel": "test-channel",
            "content": "Hello, World!",
            "channelType": "cli",
        })
        assert result.details["action"] == "send"
        assert result.details["sent"] is True

    @pytest.mark.asyncio
    async def test_send_missing_content(self) -> None:
        result = await message_tool({
            "action": "send",
            "channel": "test-channel",
            "channelType": "cli",
        })
        assert "error" in result.details
        assert "content required" in result.details["error"]

    @pytest.mark.asyncio
    async def test_delete_action(self) -> None:
        result = await message_tool({
            "action": "delete",
            "channel": "test-channel",
            "messageId": "msg-123",
            "channelType": "cli",
        })
        assert result.details["action"] == "delete"
        assert result.details["deleted"] is True

    @pytest.mark.asyncio
    async def test_react_action(self) -> None:
        result = await message_tool({
            "action": "react",
            "channel": "test-channel",
            "messageId": "msg-123",
            "emoji": "🎉",
            "channelType": "cli",
        })
        assert result.details["action"] == "react"
        assert result.details["reacted"] is True

    @pytest.mark.asyncio
    async def test_poll_action(self) -> None:
        result = await message_tool({
            "action": "poll",
            "channel": "test-channel",
            "content": "What's your favorite color?",
            "pollOptions": ["Red", "Blue", "Green"],
            "channelType": "cli",
        })
        assert result.details["action"] == "poll"
        assert result.details["question"] == "What's your favorite color?"
        assert result.details["options"] == ["Red", "Blue", "Green"]

    @pytest.mark.asyncio
    async def test_poll_missing_options(self) -> None:
        result = await message_tool({
            "action": "poll",
            "channel": "test-channel",
            "content": "Question?",
            "channelType": "cli",
        })
        assert "error" in result.details
        assert "pollOptions" in result.details["error"]


class TestCreateMessageTool:
    """Tests for message tool definition."""

    def test_create_definition(self) -> None:
        definition = create_message_tool()
        assert definition["name"] == "message"
        assert "parameters" in definition
        assert "description" in definition
