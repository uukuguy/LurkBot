"""Skill loader with eligibility checking."""

import os
import shutil
import sys
from pathlib import Path

from loguru import logger

from .parser import load_skills_from_dir
from .types import SkillEntry, SkillMetadata, SkillSnapshot


def get_bundled_skills_dir() -> Path | None:
    """Get the bundled skills directory path.

    Resolution order:
    1. LURKBOT_BUNDLED_SKILLS_DIR environment variable
    2. Sibling 'skills' directory to the package
    3. Package root 'skills' directory

    Returns:
        Path to bundled skills directory or None if not found.
    """
    # Check environment variable
    env_dir = os.environ.get("LURKBOT_BUNDLED_SKILLS_DIR")
    if env_dir:
        path = Path(env_dir)
        if path.exists():
            return path

    # Check sibling to package
    package_dir = Path(__file__).parent.parent.parent.parent
    skills_dir = package_dir / "skills"
    if skills_dir.exists():
        return skills_dir

    # Check package root (for development)
    project_root = package_dir.parent
    skills_dir = project_root / "skills"
    if skills_dir.exists():
        return skills_dir

    return None


def get_managed_skills_dir(data_dir: Path) -> Path:
    """Get the managed skills directory path.

    Args:
        data_dir: The application data directory (~/.lurkbot).

    Returns:
        Path to managed skills directory.
    """
    return data_dir / "config" / "skills"


def get_workspace_skills_dir(workspace: Path) -> Path:
    """Get the workspace skills directory path.

    Args:
        workspace: The workspace directory.

    Returns:
        Path to workspace skills directory.
    """
    return workspace / "skills"


class SkillLoader:
    """Loader for skills from multiple sources."""

    def __init__(
        self,
        data_dir: Path | None = None,
        workspace: Path | None = None,
        extra_dirs: list[Path] | None = None,
        allow_bundled: list[str] | None = None,
    ):
        """Initialize the skill loader.

        Args:
            data_dir: Application data directory (~/.lurkbot).
            workspace: Workspace directory for workspace skills.
            extra_dirs: Additional directories to load skills from.
            allow_bundled: List of bundled skill names to allow (None = all).
        """
        self.data_dir = data_dir or Path.home() / ".lurkbot"
        self.workspace = workspace
        self.extra_dirs = extra_dirs or []
        self.allow_bundled = allow_bundled
        self._cached_bins: set[str] | None = None

    def load_all(self) -> list[SkillEntry]:
        """Load skills from all sources.

        Loading precedence (lowest to highest priority):
        1. Extra directories
        2. Bundled skills
        3. Managed skills
        4. Workspace skills

        Returns:
            List of loaded and eligible skills.
        """
        all_skills: dict[str, SkillEntry] = {}

        # 1. Load from extra directories (lowest priority)
        for extra_dir in self.extra_dirs:
            skills = load_skills_from_dir(extra_dir, source_type="extra")
            for skill in skills:
                all_skills[skill.name] = skill

        # 2. Load bundled skills
        bundled_dir = get_bundled_skills_dir()
        if bundled_dir:
            skills = load_skills_from_dir(bundled_dir, source_type="bundled")
            for skill in skills:
                # Check allowlist for bundled skills
                if self.allow_bundled is not None and skill.name not in self.allow_bundled:
                    logger.debug(f"Skipping bundled skill not in allowlist: {skill.name}")
                    continue
                all_skills[skill.name] = skill

        # 3. Load managed skills
        managed_dir = get_managed_skills_dir(self.data_dir)
        if managed_dir.exists():
            skills = load_skills_from_dir(managed_dir, source_type="managed")
            for skill in skills:
                all_skills[skill.name] = skill

        # 4. Load workspace skills (highest priority)
        if self.workspace:
            workspace_dir = get_workspace_skills_dir(self.workspace)
            if workspace_dir.exists():
                skills = load_skills_from_dir(workspace_dir, source_type="workspace")
                for skill in skills:
                    all_skills[skill.name] = skill

        # Filter by eligibility
        eligible_skills = [
            skill for skill in all_skills.values() if self.check_eligibility(skill)
        ]

        logger.info(
            f"Loaded {len(eligible_skills)} skills "
            f"({len(all_skills)} total, {len(all_skills) - len(eligible_skills)} filtered)"
        )

        return eligible_skills

    def check_eligibility(self, skill: SkillEntry) -> bool:
        """Check if a skill meets all requirements for inclusion.

        Args:
            skill: The skill entry to check.

        Returns:
            True if the skill is eligible, False otherwise.
        """
        metadata = skill.metadata

        # Always include if marked as 'always'
        if metadata.always:
            return True

        # Check OS platform
        if not self._check_os(metadata):
            logger.debug(f"Skill {skill.name} skipped: OS mismatch")
            return False

        # Check required binaries
        if not self._check_required_bins(metadata):
            logger.debug(f"Skill {skill.name} skipped: missing required binaries")
            return False

        # Check any binaries
        if not self._check_any_bins(metadata):
            logger.debug(f"Skill {skill.name} skipped: missing any of required binaries")
            return False

        # Check environment variables
        if not self._check_env_vars(metadata):
            logger.debug(f"Skill {skill.name} skipped: missing environment variables")
            return False

        return True

    def _check_os(self, metadata: SkillMetadata) -> bool:
        """Check if the current OS is supported."""
        if not metadata.os:
            return True

        current_os = sys.platform
        # Map common platform names
        os_map = {
            "darwin": ["darwin", "macos", "mac"],
            "linux": ["linux"],
            "win32": ["win32", "windows"],
        }

        for supported_os in metadata.os:
            supported_os_lower = supported_os.lower()
            if current_os in os_map.get(supported_os_lower, [supported_os_lower]):
                return True
            if supported_os_lower in os_map.get(current_os, []):
                return True

        return False

    def _check_required_bins(self, metadata: SkillMetadata) -> bool:
        """Check if all required binaries are available."""
        if not metadata.requires.bins:
            return True
        return all(self._has_binary(binary) for binary in metadata.requires.bins)

    def _check_any_bins(self, metadata: SkillMetadata) -> bool:
        """Check if at least one of the any_bins is available."""
        if not metadata.requires.any_bins:
            return True
        return any(self._has_binary(binary) for binary in metadata.requires.any_bins)

    def _check_env_vars(self, metadata: SkillMetadata) -> bool:
        """Check if all required environment variables are set."""
        if not metadata.requires.env:
            return True
        return all(os.environ.get(env_var) for env_var in metadata.requires.env)

    def _has_binary(self, binary: str) -> bool:
        """Check if a binary is available in PATH."""
        return shutil.which(binary) is not None

    def build_snapshot(self, skills: list[SkillEntry] | None = None) -> SkillSnapshot:
        """Build a skill snapshot from loaded skills.

        Args:
            skills: List of skills to include. If None, loads all skills.

        Returns:
            SkillSnapshot with prompt text and skill list.
        """
        if skills is None:
            skills = self.load_all()

        # Build prompt text
        prompt_parts = ["# Available Skills\n"]
        skill_list = []

        for skill in skills:
            prompt_parts.append(skill.to_prompt())
            skill_list.append({
                "name": skill.name,
                "primary_env": skill.primary_env,
            })

        return SkillSnapshot(
            prompt="\n\n".join(prompt_parts),
            skills=skill_list,
            version=1,
            resolved_skills=skills,
        )
