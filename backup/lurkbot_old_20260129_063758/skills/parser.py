"""YAML frontmatter parser for skill files."""

import json
import re
from pathlib import Path
from typing import Any

import yaml
from loguru import logger

from .types import SkillEntry, SkillFrontmatter

# Pattern to match YAML frontmatter block
FRONTMATTER_PATTERN = re.compile(r"^---\s*\n(.*?)\n---\s*\n?", re.DOTALL)


def parse_frontmatter(content: str) -> tuple[dict[str, Any], str]:
    """Parse YAML frontmatter from markdown content.

    Args:
        content: The raw markdown content with potential frontmatter.

    Returns:
        A tuple of (frontmatter_dict, remaining_content).
        If no frontmatter found, returns ({}, original_content).
    """
    match = FRONTMATTER_PATTERN.match(content)
    if not match:
        return {}, content

    frontmatter_text = match.group(1)
    remaining_content = content[match.end() :]

    try:
        # Parse YAML
        data = yaml.safe_load(frontmatter_text)
        if not isinstance(data, dict):
            logger.warning(f"Frontmatter is not a dict: {type(data)}")
            return {}, content
        return data, remaining_content
    except yaml.YAMLError as e:
        logger.warning(f"Failed to parse YAML frontmatter: {e}")
        return {}, content


def parse_metadata_field(data: dict[str, Any]) -> dict[str, Any]:
    """Parse the metadata field which may be a JSON string.

    Args:
        data: The frontmatter dict.

    Returns:
        The data dict with metadata parsed if it was a string.
    """
    metadata = data.get("metadata")
    if isinstance(metadata, str):
        try:
            data["metadata"] = json.loads(metadata)
        except json.JSONDecodeError:
            # Try to parse as relaxed JSON5-like format
            logger.warning(f"Failed to parse metadata as JSON: {metadata[:50]}...")
            data["metadata"] = {}
    return data


def parse_skill_file(path: Path) -> SkillEntry | None:
    """Parse a skill file (SKILL.md) and return a SkillEntry.

    Args:
        path: Path to the skill file.

    Returns:
        SkillEntry if successfully parsed, None otherwise.
    """
    if not path.exists():
        logger.warning(f"Skill file not found: {path}")
        return None

    try:
        content = path.read_text(encoding="utf-8")
    except OSError as e:
        logger.error(f"Failed to read skill file {path}: {e}")
        return None

    # Parse frontmatter
    raw_frontmatter, markdown_content = parse_frontmatter(content)
    if not raw_frontmatter:
        logger.warning(f"No frontmatter found in skill file: {path}")
        return None

    # Parse metadata field if it's a JSON string
    raw_frontmatter = parse_metadata_field(raw_frontmatter)

    # Validate and parse frontmatter
    try:
        frontmatter = SkillFrontmatter.model_validate(raw_frontmatter)
    except Exception as e:
        logger.error(f"Failed to validate skill frontmatter in {path}: {e}")
        return None

    # Extract moltbot metadata
    metadata = frontmatter.get_moltbot_metadata()

    # Determine source type based on path
    source_type = _determine_source_type(path)

    return SkillEntry(
        name=frontmatter.name,
        description=frontmatter.description,
        content=markdown_content,
        source_path=path,
        source_type=source_type,
        frontmatter=frontmatter,
        metadata=metadata,
    )


def _determine_source_type(path: Path) -> str:
    """Determine the source type based on the skill file path.

    Args:
        path: Path to the skill file.

    Returns:
        One of "bundled", "managed", "workspace", or "extra".
    """
    path_str = str(path)

    # Check common patterns
    if "/skills/" in path_str and "site-packages" not in path_str:
        # Could be bundled (in package) or workspace
        if ".lurkbot" in path_str:
            if "config/skills" in path_str:
                return "managed"
            return "extra"
        return "bundled"
    if "workspace" in path_str.lower():
        return "workspace"
    return "extra"


def load_skills_from_dir(
    directory: Path,
    source_type: str = "bundled",
) -> list[SkillEntry]:
    """Load all skills from a directory.

    Expects a structure like:
        directory/
            skill-name/
                SKILL.md

    Args:
        directory: Directory containing skill subdirectories.
        source_type: The source type to assign to loaded skills.

    Returns:
        List of successfully loaded SkillEntry objects.
    """
    if not directory.exists():
        logger.debug(f"Skills directory does not exist: {directory}")
        return []

    skills = []
    for skill_dir in directory.iterdir():
        if not skill_dir.is_dir():
            continue

        skill_file = skill_dir / "SKILL.md"
        if not skill_file.exists():
            # Also check for skill.md (lowercase)
            skill_file = skill_dir / "skill.md"
            if not skill_file.exists():
                continue

        entry = parse_skill_file(skill_file)
        if entry:
            # Override source type based on caller's knowledge
            entry.source_type = source_type  # type: ignore
            skills.append(entry)
            logger.debug(f"Loaded skill: {entry.name} from {skill_file}")

    return skills
