"""Tests for bootstrap file system."""

import os
import tempfile
from pathlib import Path

import pytest

from lurkbot.agents.bootstrap import (
    AGENTS_FILENAME,
    BOOTSTRAP_FILENAME,
    DEFAULT_BOOTSTRAP_MAX_CHARS,
    HEARTBEAT_FILENAME,
    IDENTITY_FILENAME,
    MEMORY_FILENAME,
    SOUL_FILENAME,
    SUBAGENT_BOOTSTRAP_ALLOWLIST,
    TOOLS_FILENAME,
    USER_FILENAME,
    BootstrapFile,
    ContextFile,
    build_bootstrap_context_files,
    filter_bootstrap_files_for_session,
    get_default_workspace_dir,
    is_subagent_session_key,
    load_workspace_bootstrap_files,
    resolve_bootstrap_context_for_run,
    trim_bootstrap_content,
)


class TestBootstrapConstants:
    """Tests for bootstrap constants."""

    def test_file_names(self):
        """Test bootstrap file name constants."""
        assert AGENTS_FILENAME == "AGENTS.md"
        assert SOUL_FILENAME == "SOUL.md"
        assert TOOLS_FILENAME == "TOOLS.md"
        assert IDENTITY_FILENAME == "IDENTITY.md"
        assert USER_FILENAME == "USER.md"
        assert HEARTBEAT_FILENAME == "HEARTBEAT.md"
        assert BOOTSTRAP_FILENAME == "BOOTSTRAP.md"
        assert MEMORY_FILENAME == "MEMORY.md"

    def test_subagent_allowlist(self):
        """Test subagent bootstrap allowlist."""
        assert AGENTS_FILENAME in SUBAGENT_BOOTSTRAP_ALLOWLIST
        assert TOOLS_FILENAME in SUBAGENT_BOOTSTRAP_ALLOWLIST
        assert SOUL_FILENAME not in SUBAGENT_BOOTSTRAP_ALLOWLIST
        assert MEMORY_FILENAME not in SUBAGENT_BOOTSTRAP_ALLOWLIST

    def test_default_max_chars(self):
        """Test default max chars constant."""
        assert DEFAULT_BOOTSTRAP_MAX_CHARS == 20_000


class TestSubagentSessionKey:
    """Tests for subagent session key detection."""

    def test_main_session_not_subagent(self):
        """Test main session is not detected as subagent."""
        assert not is_subagent_session_key("agent:main:main")

    def test_group_session_not_subagent(self):
        """Test group session is not detected as subagent."""
        assert not is_subagent_session_key("agent:main:group:discord:123")

    def test_subagent_session_detected(self):
        """Test subagent session is detected."""
        assert is_subagent_session_key("agent:main:subagent:abc123")
        assert is_subagent_session_key("agent:test:subagent")

    def test_none_session_key(self):
        """Test None session key returns False."""
        assert not is_subagent_session_key(None)


class TestTrimBootstrapContent:
    """Tests for bootstrap content trimming."""

    def test_short_content_not_trimmed(self):
        """Test short content is not trimmed."""
        content = "Short content"
        result = trim_bootstrap_content(content, "test.md", 1000)

        assert result.content == content
        assert result.truncated is False
        assert result.max_chars == 1000
        assert result.original_length == len(content)

    def test_long_content_trimmed(self):
        """Test long content is trimmed."""
        content = "x" * 1000
        result = trim_bootstrap_content(content, "test.md", 100)

        assert result.truncated is True
        assert result.original_length == 1000
        assert "truncated" in result.content.lower()
        assert "test.md" in result.content

    def test_content_trailing_whitespace_stripped(self):
        """Test trailing whitespace is stripped."""
        content = "Content with spaces   \n\n"
        result = trim_bootstrap_content(content, "test.md", 1000)

        assert not result.content.endswith(" ")
        assert not result.content.endswith("\n")


class TestFilterBootstrapFiles:
    """Tests for bootstrap file filtering."""

    def test_main_session_gets_all_files(self):
        """Test main session gets all bootstrap files."""
        files = [
            BootstrapFile(name=AGENTS_FILENAME, path="/test/AGENTS.md"),
            BootstrapFile(name=SOUL_FILENAME, path="/test/SOUL.md"),
            BootstrapFile(name=MEMORY_FILENAME, path="/test/MEMORY.md"),
        ]

        result = filter_bootstrap_files_for_session(files, "agent:main:main")

        assert len(result) == 3

    def test_subagent_gets_limited_files(self):
        """Test subagent session only gets allowed files."""
        files = [
            BootstrapFile(name=AGENTS_FILENAME, path="/test/AGENTS.md"),
            BootstrapFile(name=TOOLS_FILENAME, path="/test/TOOLS.md"),
            BootstrapFile(name=SOUL_FILENAME, path="/test/SOUL.md"),
            BootstrapFile(name=MEMORY_FILENAME, path="/test/MEMORY.md"),
        ]

        result = filter_bootstrap_files_for_session(files, "agent:main:subagent:abc")

        assert len(result) == 2
        names = [f.name for f in result]
        assert AGENTS_FILENAME in names
        assert TOOLS_FILENAME in names
        assert SOUL_FILENAME not in names

    def test_none_session_key_gets_all_files(self):
        """Test None session key gets all files."""
        files = [
            BootstrapFile(name=AGENTS_FILENAME, path="/test/AGENTS.md"),
            BootstrapFile(name=SOUL_FILENAME, path="/test/SOUL.md"),
        ]

        result = filter_bootstrap_files_for_session(files, None)

        assert len(result) == 2


class TestBuildBootstrapContextFiles:
    """Tests for building context files."""

    def test_missing_file_marked(self):
        """Test missing files are marked in context."""
        files = [BootstrapFile(name=AGENTS_FILENAME, path="/test/AGENTS.md", missing=True)]

        result = build_bootstrap_context_files(files)

        assert len(result) == 1
        assert "[MISSING]" in result[0].content

    def test_content_included(self):
        """Test file content is included in context."""
        files = [
            BootstrapFile(
                name=AGENTS_FILENAME,
                path="/test/AGENTS.md",
                content="# Agents\nTest content",
                missing=False,
            )
        ]

        result = build_bootstrap_context_files(files)

        assert len(result) == 1
        assert result[0].path == AGENTS_FILENAME
        assert "Test content" in result[0].content

    def test_empty_content_skipped(self):
        """Test empty content files are skipped."""
        files = [
            BootstrapFile(
                name=AGENTS_FILENAME, path="/test/AGENTS.md", content="", missing=False
            ),
            BootstrapFile(
                name=SOUL_FILENAME, path="/test/SOUL.md", content="Soul content", missing=False
            ),
        ]

        result = build_bootstrap_context_files(files)

        assert len(result) == 1
        assert result[0].path == SOUL_FILENAME


class TestLoadWorkspaceBootstrapFiles:
    """Tests for loading workspace bootstrap files."""

    @pytest.mark.asyncio
    async def test_load_existing_files(self):
        """Test loading existing bootstrap files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files
            agents_path = Path(tmpdir) / AGENTS_FILENAME
            agents_path.write_text("# Agents\nTest agents content")

            soul_path = Path(tmpdir) / SOUL_FILENAME
            soul_path.write_text("# Soul\nTest soul content")

            result = await load_workspace_bootstrap_files(tmpdir)

            # Check that files were loaded
            agents_file = next((f for f in result if f.name == AGENTS_FILENAME), None)
            assert agents_file is not None
            assert agents_file.missing is False
            assert "Test agents content" in agents_file.content

            soul_file = next((f for f in result if f.name == SOUL_FILENAME), None)
            assert soul_file is not None
            assert soul_file.missing is False

    @pytest.mark.asyncio
    async def test_missing_files_marked(self):
        """Test missing files are marked as such."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = await load_workspace_bootstrap_files(tmpdir)

            # All standard files should be marked as missing
            for file in result:
                if file.name not in [MEMORY_FILENAME, "memory.md"]:
                    assert file.missing is True


class TestResolveBootstrapContextForRun:
    """Tests for resolving bootstrap context."""

    @pytest.mark.asyncio
    async def test_full_resolution(self):
        """Test full bootstrap context resolution."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create some test files
            agents_path = Path(tmpdir) / AGENTS_FILENAME
            agents_path.write_text("# Agents\nTest content")

            bootstrap_files, context_files = await resolve_bootstrap_context_for_run(tmpdir)

            # Check bootstrap files
            assert len(bootstrap_files) > 0

            # Check context files
            context_names = [f.path for f in context_files]
            assert AGENTS_FILENAME in context_names


class TestGetDefaultWorkspaceDir:
    """Tests for default workspace directory."""

    def test_default_dir(self):
        """Test default workspace directory."""
        result = get_default_workspace_dir()
        assert "clawd" in result

    def test_with_profile_env(self, monkeypatch):
        """Test workspace directory with profile."""
        monkeypatch.setenv("LURKBOT_PROFILE", "test")
        result = get_default_workspace_dir()
        assert "clawd-test" in result

    def test_default_profile_ignored(self, monkeypatch):
        """Test 'default' profile is ignored."""
        monkeypatch.setenv("LURKBOT_PROFILE", "default")
        result = get_default_workspace_dir()
        assert "clawd-default" not in result
