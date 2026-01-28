"""LurkBot Skills System.

This module provides an extensible skills/plugins system that allows loading
skill documentation from markdown files with YAML frontmatter.

Skills are markdown files that provide context and examples for the AI agent
to learn specific capabilities like using GitHub CLI, checking weather, etc.

Usage:
    from lurkbot.skills import SkillRegistry, get_skill_registry

    # Get the global registry (loads skills automatically)
    registry = get_skill_registry()

    # List all available skills
    for skill in registry:
        print(f"{skill.emoji} {skill.name}: {skill.description}")

    # Get skills prompt for AI context
    prompt = registry.get_prompt()

    # Check if a specific skill is available
    if registry.is_available("github"):
        github_skill = registry.get("github")
"""

from .loader import SkillLoader, get_bundled_skills_dir
from .parser import load_skills_from_dir, parse_frontmatter, parse_skill_file
from .registry import SkillRegistry, get_skill_registry, reset_skill_registry
from .types import (
    InstallSpec,
    SkillEntry,
    SkillFrontmatter,
    SkillMetadata,
    SkillRequirements,
    SkillSnapshot,
)

__all__ = [
    # Types
    "InstallSpec",
    "SkillEntry",
    "SkillFrontmatter",
    "SkillMetadata",
    "SkillRequirements",
    "SkillSnapshot",
    # Parser
    "parse_frontmatter",
    "parse_skill_file",
    "load_skills_from_dir",
    # Loader
    "SkillLoader",
    "get_bundled_skills_dir",
    # Registry
    "SkillRegistry",
    "get_skill_registry",
    "reset_skill_registry",
]
