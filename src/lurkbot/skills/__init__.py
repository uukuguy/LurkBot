"""技能系统模块

实现 MoltBot 技能系统，包括：
- Frontmatter 解析
- 技能加载优先级
- 技能注册和管理
- ClawHub 集成
"""

from .clawhub import (
    ClawHubClient,
    ClawHubSkill,
    ClawHubVersion,
    download_skill,
    get_skill_info,
    search_skills,
)
from .frontmatter import (
    MoltbotMetadata,
    SkillFrontmatter,
    SkillInstallStep,
    SkillRequirements,
    parse_skill_frontmatter,
    validate_skill_file,
)
from .registry import SkillManager, SkillRegistry, get_skill_manager
from .workspace import (
    SkillEntry,
    SkillSource,
    deduplicate_skills,
    discover_skills,
    load_all_skills,
)

__all__ = [
    # Frontmatter
    "SkillFrontmatter",
    "MoltbotMetadata",
    "SkillRequirements",
    "SkillInstallStep",
    "parse_skill_frontmatter",
    "validate_skill_file",
    # Workspace
    "SkillEntry",
    "SkillSource",
    "discover_skills",
    "deduplicate_skills",
    "load_all_skills",
    # Registry
    "SkillRegistry",
    "SkillManager",
    "get_skill_manager",
    # ClawHub
    "ClawHubClient",
    "ClawHubSkill",
    "ClawHubVersion",
    "search_skills",
    "get_skill_info",
    "download_skill",
]
