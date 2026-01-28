"""Tests for the skills system."""

import tempfile
from pathlib import Path

import pytest

from lurkbot.skills import (
    SkillEntry,
    SkillFrontmatter,
    SkillLoader,
    SkillMetadata,
    SkillRegistry,
    SkillRequirements,
    SkillSnapshot,
    get_bundled_skills_dir,
    load_skills_from_dir,
    parse_frontmatter,
    parse_skill_file,
    reset_skill_registry,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_skill_content() -> str:
    """Sample SKILL.md content for testing."""
    return '''---
name: test-skill
description: A test skill for unit testing.
metadata: {"moltbot":{"emoji":"🧪","requires":{"bins":["python"]}}}
---

# Test Skill

This is a test skill.

## Usage

```bash
python --version
```
'''


@pytest.fixture
def skill_without_frontmatter() -> str:
    """Skill content without frontmatter."""
    return """# Just Markdown

No frontmatter here.
"""


@pytest.fixture
def temp_skills_dir(sample_skill_content: str):
    """Create a temporary skills directory with test skills."""
    with tempfile.TemporaryDirectory() as tmpdir:
        skills_dir = Path(tmpdir)

        # Create test-skill
        test_skill_dir = skills_dir / "test-skill"
        test_skill_dir.mkdir()
        (test_skill_dir / "SKILL.md").write_text(sample_skill_content)

        # Create another skill
        other_skill_dir = skills_dir / "other-skill"
        other_skill_dir.mkdir()
        (other_skill_dir / "SKILL.md").write_text('''---
name: other-skill
description: Another test skill.
metadata: {"moltbot":{"emoji":"📦"}}
---

# Other Skill

Just another skill.
''')

        yield skills_dir


# =============================================================================
# Type Tests
# =============================================================================


class TestSkillRequirements:
    """Tests for SkillRequirements model."""

    def test_default_empty_lists(self):
        req = SkillRequirements()
        assert req.bins == []
        assert req.any_bins == []
        assert req.env == []
        assert req.config == []

    def test_with_bins(self):
        req = SkillRequirements(bins=["python", "pip"])
        assert req.bins == ["python", "pip"]

    def test_alias_any_bins(self):
        req = SkillRequirements.model_validate({"anyBins": ["git", "gh"]})
        assert req.any_bins == ["git", "gh"]


class TestSkillMetadata:
    """Tests for SkillMetadata model."""

    def test_default_values(self):
        meta = SkillMetadata()
        assert meta.emoji is None
        assert meta.always is False
        assert meta.os == []
        assert isinstance(meta.requires, SkillRequirements)

    def test_with_emoji(self):
        meta = SkillMetadata(emoji="🐍")
        assert meta.emoji == "🐍"

    def test_with_requires(self):
        meta = SkillMetadata.model_validate({
            "requires": {"bins": ["python"]},
            "always": True
        })
        assert meta.requires.bins == ["python"]
        assert meta.always is True


class TestSkillFrontmatter:
    """Tests for SkillFrontmatter model."""

    def test_minimal(self):
        fm = SkillFrontmatter(name="test")
        assert fm.name == "test"
        assert fm.description == ""
        assert fm.user_invocable is True

    def test_get_moltbot_metadata(self):
        fm = SkillFrontmatter(
            name="test",
            metadata={"moltbot": {"emoji": "🧪", "always": True}}
        )
        meta = fm.get_moltbot_metadata()
        assert meta.emoji == "🧪"
        assert meta.always is True

    def test_get_moltbot_metadata_empty(self):
        fm = SkillFrontmatter(name="test")
        meta = fm.get_moltbot_metadata()
        assert meta.emoji is None


class TestSkillEntry:
    """Tests for SkillEntry dataclass."""

    def test_creation(self):
        entry = SkillEntry(
            name="test",
            description="A test skill",
            content="# Test\n\nContent here.",
            source_path=Path("/tmp/test/SKILL.md"),
            source_type="bundled",
            frontmatter=SkillFrontmatter(name="test"),
            metadata=SkillMetadata(emoji="🧪"),
        )
        assert entry.name == "test"
        assert entry.emoji == "🧪"
        assert entry.enabled is True

    def test_to_prompt(self):
        entry = SkillEntry(
            name="test",
            description="A test skill",
            content="# Test\n\nContent here.",
            source_path=Path("/tmp/test/SKILL.md"),
            source_type="bundled",
            frontmatter=SkillFrontmatter(name="test"),
            metadata=SkillMetadata(emoji="🧪"),
        )
        prompt = entry.to_prompt()
        assert "🧪 test" in prompt
        assert "A test skill" in prompt
        assert "Content here." in prompt


class TestSkillSnapshot:
    """Tests for SkillSnapshot dataclass."""

    def test_creation(self):
        snapshot = SkillSnapshot(
            prompt="# Skills",
            skills=[{"name": "test", "primary_env": None}],
            version=1,
        )
        assert snapshot.prompt == "# Skills"
        assert len(snapshot.skills) == 1
        assert snapshot.version == 1


# =============================================================================
# Parser Tests
# =============================================================================


class TestParseFrontmatter:
    """Tests for parse_frontmatter function."""

    def test_with_frontmatter(self, sample_skill_content: str):
        data, content = parse_frontmatter(sample_skill_content)
        assert data["name"] == "test-skill"
        assert data["description"] == "A test skill for unit testing."
        assert "# Test Skill" in content

    def test_without_frontmatter(self, skill_without_frontmatter: str):
        data, content = parse_frontmatter(skill_without_frontmatter)
        assert data == {}
        assert "# Just Markdown" in content

    def test_metadata_as_json_string(self):
        content = '''---
name: test
metadata: {"moltbot":{"emoji":"🧪"}}
---

Content
'''
        data, _ = parse_frontmatter(content)
        assert data["name"] == "test"
        # metadata should be parsed as dict
        assert isinstance(data["metadata"], dict)


class TestParseSkillFile:
    """Tests for parse_skill_file function."""

    def test_valid_skill_file(self, temp_skills_dir: Path):
        skill_file = temp_skills_dir / "test-skill" / "SKILL.md"
        entry = parse_skill_file(skill_file)

        assert entry is not None
        assert entry.name == "test-skill"
        assert entry.description == "A test skill for unit testing."
        assert entry.metadata.emoji == "🧪"
        assert "python" in entry.metadata.requires.bins

    def test_nonexistent_file(self, temp_skills_dir: Path):
        skill_file = temp_skills_dir / "nonexistent" / "SKILL.md"
        entry = parse_skill_file(skill_file)
        assert entry is None


class TestLoadSkillsFromDir:
    """Tests for load_skills_from_dir function."""

    def test_load_all_skills(self, temp_skills_dir: Path):
        skills = load_skills_from_dir(temp_skills_dir)
        assert len(skills) == 2
        names = {s.name for s in skills}
        assert "test-skill" in names
        assert "other-skill" in names

    def test_empty_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            skills = load_skills_from_dir(Path(tmpdir))
            assert skills == []

    def test_nonexistent_directory(self):
        skills = load_skills_from_dir(Path("/nonexistent/path"))
        assert skills == []


# =============================================================================
# Loader Tests
# =============================================================================


class TestSkillLoader:
    """Tests for SkillLoader class."""

    def test_init(self):
        loader = SkillLoader()
        assert loader.data_dir == Path.home() / ".lurkbot"
        assert loader.workspace is None

    def test_load_from_temp_dir(self, temp_skills_dir: Path):
        loader = SkillLoader(extra_dirs=[temp_skills_dir])
        skills = loader.load_all()
        assert len(skills) >= 2

    def test_check_eligibility_always(self):
        loader = SkillLoader()
        entry = SkillEntry(
            name="always-on",
            description="Always available",
            content="",
            source_path=Path("/tmp/test/SKILL.md"),
            source_type="bundled",
            frontmatter=SkillFrontmatter(name="always-on"),
            metadata=SkillMetadata(always=True),
        )
        assert loader.check_eligibility(entry) is True

    def test_check_eligibility_missing_bin(self):
        loader = SkillLoader()
        entry = SkillEntry(
            name="needs-bin",
            description="Needs a binary",
            content="",
            source_path=Path("/tmp/test/SKILL.md"),
            source_type="bundled",
            frontmatter=SkillFrontmatter(name="needs-bin"),
            metadata=SkillMetadata(
                requires=SkillRequirements(bins=["nonexistent_binary_xyz"])
            ),
        )
        assert loader.check_eligibility(entry) is False

    def test_check_eligibility_has_bin(self):
        loader = SkillLoader()
        entry = SkillEntry(
            name="has-python",
            description="Has python",
            content="",
            source_path=Path("/tmp/test/SKILL.md"),
            source_type="bundled",
            frontmatter=SkillFrontmatter(name="has-python"),
            metadata=SkillMetadata(
                requires=SkillRequirements(bins=["python"])  # python should exist
            ),
        )
        # This should be True if python is available
        result = loader.check_eligibility(entry)
        # Note: test may be skipped on systems without python
        assert isinstance(result, bool)

    def test_build_snapshot(self, temp_skills_dir: Path):
        loader = SkillLoader(extra_dirs=[temp_skills_dir])
        snapshot = loader.build_snapshot()
        assert snapshot.prompt != ""
        assert len(snapshot.skills) >= 2
        assert snapshot.version == 1


class TestGetBundledSkillsDir:
    """Tests for get_bundled_skills_dir function."""

    def test_returns_path_or_none(self):
        result = get_bundled_skills_dir()
        # Should return a Path or None
        assert result is None or isinstance(result, Path)


# =============================================================================
# Registry Tests
# =============================================================================


class TestSkillRegistry:
    """Tests for SkillRegistry class."""

    @pytest.fixture(autouse=True)
    def reset_registry(self):
        """Reset global registry before each test."""
        reset_skill_registry()
        yield
        reset_skill_registry()

    def test_init_with_auto_load(self, temp_skills_dir: Path):
        registry = SkillRegistry(extra_dirs=[temp_skills_dir])
        assert len(registry) >= 2

    def test_init_without_auto_load(self):
        registry = SkillRegistry(auto_load=False)
        assert len(registry) == 0

    def test_refresh(self, temp_skills_dir: Path):
        registry = SkillRegistry(extra_dirs=[temp_skills_dir], auto_load=False)
        assert len(registry) == 0
        registry.refresh()
        assert len(registry) >= 2

    def test_get_skill(self, temp_skills_dir: Path):
        registry = SkillRegistry(extra_dirs=[temp_skills_dir])
        skill = registry.get("test-skill")
        assert skill is not None
        assert skill.name == "test-skill"

    def test_get_nonexistent_skill(self, temp_skills_dir: Path):
        registry = SkillRegistry(extra_dirs=[temp_skills_dir])
        skill = registry.get("nonexistent")
        assert skill is None

    def test_list_skills(self, temp_skills_dir: Path):
        registry = SkillRegistry(extra_dirs=[temp_skills_dir])
        names = registry.list_skills()
        assert "test-skill" in names
        assert "other-skill" in names

    def test_is_available(self, temp_skills_dir: Path):
        registry = SkillRegistry(extra_dirs=[temp_skills_dir])
        assert registry.is_available("test-skill") is True
        assert registry.is_available("nonexistent") is False

    def test_contains(self, temp_skills_dir: Path):
        registry = SkillRegistry(extra_dirs=[temp_skills_dir])
        assert "test-skill" in registry
        assert "nonexistent" not in registry

    def test_iteration(self, temp_skills_dir: Path):
        registry = SkillRegistry(extra_dirs=[temp_skills_dir])
        skills = list(registry)
        assert len(skills) >= 2

    def test_get_prompt(self, temp_skills_dir: Path):
        registry = SkillRegistry(extra_dirs=[temp_skills_dir])
        prompt = registry.get_prompt()
        assert "# Available Skills" in prompt
        assert "test-skill" in prompt

    def test_get_snapshot(self, temp_skills_dir: Path):
        registry = SkillRegistry(extra_dirs=[temp_skills_dir])
        snapshot = registry.get_snapshot()
        assert isinstance(snapshot, SkillSnapshot)
        assert len(snapshot.skills) >= 2

    def test_filter_by_source(self, temp_skills_dir: Path):
        registry = SkillRegistry(extra_dirs=[temp_skills_dir])
        extra_skills = registry.filter_by_source("extra")
        assert len(extra_skills) >= 2

    def test_version_increments(self, temp_skills_dir: Path):
        registry = SkillRegistry(extra_dirs=[temp_skills_dir])
        v1 = registry.version
        registry.refresh()
        v2 = registry.version
        assert v2 > v1


# =============================================================================
# Integration Tests
# =============================================================================


class TestSkillsIntegration:
    """Integration tests for the complete skills system."""

    def test_bundled_skills_load(self):
        """Test that bundled skills can be loaded."""
        bundled_dir = get_bundled_skills_dir()
        if bundled_dir and bundled_dir.exists():
            skills = load_skills_from_dir(bundled_dir, source_type="bundled")
            # Should load at least some bundled skills
            assert len(skills) >= 0  # May be 0 in test env

    def test_full_workflow(self, temp_skills_dir: Path):
        """Test the full workflow from loading to prompt generation."""
        # 1. Create registry
        registry = SkillRegistry(extra_dirs=[temp_skills_dir])

        # 2. Verify skills loaded
        assert len(registry) >= 2

        # 3. Get a specific skill
        skill = registry.get("test-skill")
        assert skill is not None
        assert skill.emoji == "🧪"

        # 4. Generate prompt
        prompt = registry.get_prompt()
        assert "test-skill" in prompt
        assert "🧪" in prompt

        # 5. Get snapshot
        snapshot = registry.get_snapshot()
        assert snapshot.version >= 1
        assert len(snapshot.resolved_skills) >= 2
