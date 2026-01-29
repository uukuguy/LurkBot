"""Phase 10: 技能和插件系统单元测试

测试 Skills 和 Plugins 系统的功能。
"""

import json
import tempfile
from pathlib import Path

import pytest

from lurkbot.plugins import (
    ManifestValidator,
    PluginLoader,
    PluginManifest,
    PluginState,
    PluginType,
    deduplicate_plugins,
    discover_all_plugins,
    validate_plugin_name,
    validate_semantic_version,
)
from lurkbot.skills import (
    SkillEntry,
    SkillFrontmatter,
    SkillManager,
    SkillRegistry,
    SkillSource,
    deduplicate_skills,
    discover_skills,
    load_all_skills,
    parse_skill_frontmatter,
    validate_skill_file,
)


# ============================================================================
# Skills: Frontmatter 解析测试
# ============================================================================


class TestSkillsFrontmatter:
    """测试技能 Frontmatter 解析"""

    def test_parse_basic_frontmatter(self):
        """测试基本 Frontmatter 解析"""
        content = """---
description: Test skill
tags: [test, demo]
user-invocable: true
disable-model-invocation: false
---
# Skill Content

This is the skill body.
"""
        frontmatter, body = parse_skill_frontmatter(content)

        assert frontmatter.description == "Test skill"
        assert frontmatter.tags == ["test", "demo"]
        assert frontmatter.user_invocable is True
        assert frontmatter.disable_model_invocation is False
        assert "This is the skill body" in body

    def test_parse_frontmatter_with_metadata(self):
        """测试带 Moltbot 元数据的 Frontmatter"""
        content = """---
description: Advanced skill
tags: [advanced]
metadata: |
  {
    "moltbot": {
      "skillKey": "custom-key",
      "emoji": "🎯",
      "homepage": "https://example.com",
      "primaryEnv": "python"
    }
  }
---
Skill content here.
"""
        frontmatter, body = parse_skill_frontmatter(content)

        assert frontmatter.metadata is not None
        assert frontmatter.metadata.skill_key == "custom-key"
        assert frontmatter.metadata.emoji == "🎯"
        assert frontmatter.metadata.homepage == "https://example.com"
        assert frontmatter.metadata.primary_env == "python"

    def test_parse_frontmatter_with_requirements(self):
        """测试带依赖要求的 Frontmatter"""
        content = """---
description: Skill with requirements
metadata: |
  {
    "moltbot": {
      "requires": {
        "bins": ["ffmpeg", "git"],
        "anyBins": ["python3", "python"],
        "env": ["OPENAI_API_KEY"],
        "config": ["tool.example"]
      }
    }
  }
---
Content.
"""
        frontmatter, _ = parse_skill_frontmatter(content)

        assert frontmatter.metadata is not None
        assert frontmatter.metadata.requires is not None
        assert frontmatter.metadata.requires.bins == ["ffmpeg", "git"]
        assert frontmatter.metadata.requires.any_bins == ["python3", "python"]
        assert frontmatter.metadata.requires.env == ["OPENAI_API_KEY"]

    def test_parse_missing_frontmatter(self):
        """测试缺少 Frontmatter 的情况"""
        content = "# Just a markdown file without frontmatter"

        with pytest.raises(ValueError, match="缺少 YAML Frontmatter"):
            parse_skill_frontmatter(content)

    def test_parse_invalid_yaml(self):
        """测试无效的 YAML"""
        content = """---
description: [invalid yaml
---
Content.
"""
        with pytest.raises(ValueError, match="YAML 解析失败"):
            parse_skill_frontmatter(content)


# ============================================================================
# Skills: 技能加载优先级测试
# ============================================================================


class TestSkillsWorkspace:
    """测试技能加载优先级系统"""

    def test_discover_skills_in_empty_workspace(self):
        """测试空工作区"""
        with tempfile.TemporaryDirectory() as tmpdir:
            skills = discover_skills(tmpdir)
            assert len(skills) == 0

    def test_discover_skills_with_priority(self):
        """测试技能优先级"""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)

            # 创建不同优先级的技能目录
            (workspace / ".skills").mkdir()
            (workspace / ".skill-bundles").mkdir()

            # 工作区技能 (优先级 1)
            skill1_dir = workspace / ".skills" / "skill1"
            skill1_dir.mkdir()
            (skill1_dir / "SKILL.md").write_text("""---
description: Workspace skill
---
Content.
""")

            # 受管技能 (优先级 2)
            skill2_dir = workspace / ".skill-bundles" / "skill2"
            skill2_dir.mkdir()
            (skill2_dir / "SKILL.md").write_text("""---
description: Managed skill
---
Content.
""")

            skills = discover_skills(workspace)
            assert len(skills) == 2
            assert skills[0].source == SkillSource.WORKSPACE
            assert skills[0].priority == 1
            assert skills[1].source == SkillSource.MANAGED
            assert skills[1].priority == 2

    def test_deduplicate_skills(self):
        """测试技能去重（保留优先级高的）"""
        skill1 = SkillEntry(
            key="test-skill",
            source=SkillSource.WORKSPACE,
            priority=1,
            file_path=Path("/path1"),
            frontmatter=SkillFrontmatter(description="Workspace version"),
            content="Content 1",
        )
        skill2 = SkillEntry(
            key="test-skill",
            source=SkillSource.BUNDLED,
            priority=3,
            file_path=Path("/path2"),
            frontmatter=SkillFrontmatter(description="Bundled version"),
            content="Content 2",
        )

        result = deduplicate_skills([skill1, skill2])

        assert len(result) == 1
        assert result["test-skill"].source == SkillSource.WORKSPACE


# ============================================================================
# Skills: 技能注册和管理器测试
# ============================================================================


class TestSkillsRegistry:
    """测试技能注册表"""

    def test_register_and_get(self):
        """测试注册和获取技能"""
        registry = SkillRegistry()
        skill = SkillEntry(
            key="test-skill",
            source=SkillSource.WORKSPACE,
            priority=1,
            file_path=Path("/test"),
            frontmatter=SkillFrontmatter(description="Test", tags=["test"]),
            content="Content",
        )

        registry.register(skill)
        assert registry.has("test-skill")
        retrieved = registry.get("test-skill")
        assert retrieved is not None
        assert retrieved.key == "test-skill"

    def test_find_by_tag(self):
        """测试按标签查找"""
        registry = SkillRegistry()

        skill1 = SkillEntry(
            key="skill1",
            source=SkillSource.WORKSPACE,
            priority=1,
            file_path=Path("/s1"),
            frontmatter=SkillFrontmatter(description="S1", tags=["python"]),
            content="",
        )
        skill2 = SkillEntry(
            key="skill2",
            source=SkillSource.WORKSPACE,
            priority=1,
            file_path=Path("/s2"),
            frontmatter=SkillFrontmatter(description="S2", tags=["javascript"]),
            content="",
        )

        registry.register(skill1)
        registry.register(skill2)

        python_skills = registry.find_by_tag("python")
        assert len(python_skills) == 1
        assert python_skills[0].key == "skill1"

    def test_find_user_invocable(self):
        """测试查找用户可调用的技能"""
        registry = SkillRegistry()

        skill1 = SkillEntry(
            key="skill1",
            source=SkillSource.WORKSPACE,
            priority=1,
            file_path=Path("/s1"),
            frontmatter=SkillFrontmatter(
                description="S1", user_invocable=True
            ),
            content="",
        )
        skill2 = SkillEntry(
            key="skill2",
            source=SkillSource.WORKSPACE,
            priority=1,
            file_path=Path("/s2"),
            frontmatter=SkillFrontmatter(
                description="S2", user_invocable=False
            ),
            content="",
        )

        registry.register(skill1)
        registry.register(skill2)

        user_skills = registry.find_user_invocable()
        assert len(user_skills) == 1
        assert user_skills[0].key == "skill1"


class TestSkillsManager:
    """测试技能管理器"""

    def test_load_and_reload(self):
        """测试加载和重载技能"""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            (workspace / ".skills").mkdir()

            # 创建测试技能
            skill_dir = workspace / ".skills" / "test"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text("""---
description: Test skill
---
Content.
""")

            manager = SkillManager()
            count = manager.load_skills(workspace)

            assert count == 1
            assert manager.get_skill("test") is not None

            # 测试重载
            count = manager.reload_skills()
            assert count == 1

    def test_search_skills(self):
        """测试技能搜索"""
        manager = SkillManager()

        skill1 = SkillEntry(
            key="skill1",
            source=SkillSource.WORKSPACE,
            priority=1,
            file_path=Path("/s1"),
            frontmatter=SkillFrontmatter(
                description="S1", tags=["python"], user_invocable=True
            ),
            content="",
        )

        manager.registry.register(skill1)

        results = manager.search_skills(tag="python", user_invocable=True)
        assert len(results) == 1


# ============================================================================
# Plugins: Manifest 验证测试
# ============================================================================


class TestPluginsManifest:
    """测试插件 Manifest 验证"""

    def test_validate_plugin_name(self):
        """测试插件名称验证"""
        assert validate_plugin_name("my-plugin") is True
        assert validate_plugin_name("test123") is True
        assert validate_plugin_name("a") is False  # 太短
        assert validate_plugin_name("My-Plugin") is False  # 大写
        assert validate_plugin_name("my_plugin") is False  # 下划线
        assert validate_plugin_name("123plugin") is False  # 数字开头

    def test_validate_semantic_version(self):
        """测试语义化版本验证"""
        assert validate_semantic_version("1.0.0") is True
        assert validate_semantic_version("1.2.3") is True
        assert validate_semantic_version("1.0.0-alpha") is True
        assert validate_semantic_version("1.0.0+build") is True
        assert validate_semantic_version("1.0") is False
        assert validate_semantic_version("v1.0.0") is False

    def test_manifest_validator(self):
        """测试 Manifest 验证器"""
        manifest = PluginManifest(
            name="test-plugin",
            version="1.0.0",
            description="Test plugin",
            type=PluginType.TOOL,
            entry="main.py",
        )

        errors = ManifestValidator.validate(manifest)
        assert len(errors) == 0

    def test_manifest_validator_with_errors(self):
        """测试 Manifest 验证失败"""
        manifest = PluginManifest(
            name="Invalid_Name",  # 无效名称
            version="1.0",  # 无效版本
            description="Test",
            entry="",  # 缺少入口
        )

        errors = ManifestValidator.validate(manifest)
        assert len(errors) >= 2  # 至少有名称和版本错误


# ============================================================================
# Plugins: 插件发现测试
# ============================================================================


class TestPluginsDiscovery:
    """测试插件发现"""

    def test_discover_plugins_in_empty_dir(self):
        """测试空目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            plugins = discover_all_plugins(tmpdir)
            assert len(plugins) == 0

    def test_discover_plugins(self):
        """测试插件发现"""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            plugins_dir = workspace / ".plugins"
            plugins_dir.mkdir()

            # 创建测试插件
            plugin_dir = plugins_dir / "test-plugin"
            plugin_dir.mkdir()

            manifest = {
                "name": "test-plugin",
                "version": "1.0.0",
                "description": "Test plugin",
                "type": "tool",
                "entry": "main.py",
            }

            (plugin_dir / "plugin.json").write_text(json.dumps(manifest))
            (plugin_dir / "main.py").write_text("# Plugin code")

            plugins = discover_all_plugins(workspace)
            assert len(plugins) == 1
            assert plugins[0][1].name == "test-plugin"

    def test_deduplicate_plugins(self):
        """测试插件去重（保留最新版本）"""
        manifest1 = PluginManifest(
            name="test-plugin",
            version="1.0.0",
            description="V1",
            entry="main.py",
        )
        manifest2 = PluginManifest(
            name="test-plugin",
            version="2.0.0",
            description="V2",
            entry="main.py",
        )

        plugins = [
            (Path("/path1"), manifest1),
            (Path("/path2"), manifest2),
        ]

        result = deduplicate_plugins(plugins)
        assert len(result) == 1
        assert result["test-plugin"][1].version == "2.0.0"


# ============================================================================
# Plugins: 插件加载器测试
# ============================================================================


class TestPluginLoader:
    """测试插件加载器"""

    def test_load_plugin(self):
        """测试插件加载"""
        with tempfile.TemporaryDirectory() as tmpdir:
            plugin_dir = Path(tmpdir)

            # 创建插件文件
            manifest = PluginManifest(
                name="test-plugin",
                version="1.0.0",
                description="Test",
                entry="plugin.py",
            )

            # 创建简单的 Python 插件
            (plugin_dir / "plugin.py").write_text("""
def hello():
    return "Hello from plugin"
""")

            loader = PluginLoader()
            plugin = loader.load(plugin_dir, manifest)

            assert plugin.state == PluginState.LOADED
            assert plugin.module is not None
            assert hasattr(plugin.module, "hello")

    def test_enable_disable_plugin(self):
        """测试启用和禁用插件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            plugin_dir = Path(tmpdir)

            manifest = PluginManifest(
                name="test-plugin",
                version="1.0.0",
                description="Test",
                entry="plugin.py",
                main_class="TestPlugin",
            )

            # 创建带生命周期方法的插件
            (plugin_dir / "plugin.py").write_text("""
class TestPlugin:
    def __init__(self):
        self.enabled = False

    def on_enable(self):
        self.enabled = True

    def on_disable(self):
        self.enabled = False
""")

            loader = PluginLoader()
            plugin = loader.load(plugin_dir, manifest)

            # 启用
            success = loader.enable("test-plugin")
            assert success is True
            assert plugin.state == PluginState.ENABLED

            # 禁用
            success = loader.disable("test-plugin")
            assert success is True
            assert plugin.state == PluginState.DISABLED

    def test_unload_plugin(self):
        """测试卸载插件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            plugin_dir = Path(tmpdir)

            manifest = PluginManifest(
                name="test-plugin",
                version="1.0.0",
                description="Test",
                entry="plugin.py",
            )

            (plugin_dir / "plugin.py").write_text("# Plugin code")

            loader = PluginLoader()
            loader.load(plugin_dir, manifest)

            assert loader.get("test-plugin") is not None

            success = loader.unload("test-plugin")
            assert success is True
            assert loader.get("test-plugin") is None


if __name__ == "__main__":
    pytest.main([__file__, "-xvs"])
