"""Skill registry for managing loaded skills."""

from collections.abc import Iterator
from pathlib import Path
from threading import Lock

from loguru import logger

from .loader import SkillLoader
from .types import SkillEntry, SkillSnapshot


class SkillRegistry:
    """Registry for managing loaded skills.

    Thread-safe registry that provides access to loaded skills
    and supports hot-reloading.
    """

    def __init__(
        self,
        data_dir: Path | None = None,
        workspace: Path | None = None,
        extra_dirs: list[Path] | None = None,
        allow_bundled: list[str] | None = None,
        auto_load: bool = True,
    ):
        """Initialize the skill registry.

        Args:
            data_dir: Application data directory (~/.lurkbot).
            workspace: Workspace directory for workspace skills.
            extra_dirs: Additional directories to load skills from.
            allow_bundled: List of bundled skill names to allow (None = all).
            auto_load: Whether to load skills immediately on init.
        """
        self._loader = SkillLoader(
            data_dir=data_dir,
            workspace=workspace,
            extra_dirs=extra_dirs,
            allow_bundled=allow_bundled,
        )
        self._skills: dict[str, SkillEntry] = {}
        self._snapshot: SkillSnapshot | None = None
        self._lock = Lock()
        self._version = 0

        if auto_load:
            self.refresh()

    def refresh(self) -> None:
        """Reload all skills from sources.

        This is thread-safe and will update the internal skill registry.
        """
        with self._lock:
            skills = self._loader.load_all()
            self._skills = {skill.name: skill for skill in skills}
            self._snapshot = self._loader.build_snapshot(skills)
            self._version += 1
            logger.info(f"Skill registry refreshed: {len(self._skills)} skills (v{self._version})")

    def get(self, name: str) -> SkillEntry | None:
        """Get a skill by name.

        Args:
            name: The skill name.

        Returns:
            SkillEntry if found, None otherwise.
        """
        with self._lock:
            return self._skills.get(name)

    def list_skills(self) -> list[str]:
        """Get a list of all skill names.

        Returns:
            List of skill names.
        """
        with self._lock:
            return list(self._skills.keys())

    def get_all(self) -> list[SkillEntry]:
        """Get all loaded skills.

        Returns:
            List of all skill entries.
        """
        with self._lock:
            return list(self._skills.values())

    def get_snapshot(self) -> SkillSnapshot:
        """Get the current skill snapshot.

        Returns:
            SkillSnapshot with prompt and skill list.
        """
        with self._lock:
            if self._snapshot is None:
                self._snapshot = self._loader.build_snapshot(list(self._skills.values()))
            return self._snapshot

    def get_prompt(self) -> str:
        """Get the combined skills prompt for AI context.

        Returns:
            Formatted skills documentation for AI context.
        """
        return self.get_snapshot().prompt

    def is_available(self, name: str) -> bool:
        """Check if a skill is available.

        Args:
            name: The skill name to check.

        Returns:
            True if the skill is loaded and available.
        """
        with self._lock:
            return name in self._skills

    def get_by_emoji(self, emoji: str) -> SkillEntry | None:
        """Find a skill by its emoji icon.

        Args:
            emoji: The emoji to search for.

        Returns:
            SkillEntry if found, None otherwise.
        """
        with self._lock:
            for skill in self._skills.values():
                if skill.emoji == emoji:
                    return skill
            return None

    def filter_by_source(self, source_type: str) -> list[SkillEntry]:
        """Get skills filtered by source type.

        Args:
            source_type: One of "bundled", "managed", "workspace", "extra".

        Returns:
            List of skills from the specified source.
        """
        with self._lock:
            return [skill for skill in self._skills.values() if skill.source_type == source_type]

    @property
    def version(self) -> int:
        """Get the current registry version (increments on refresh)."""
        return self._version

    def __len__(self) -> int:
        """Get the number of loaded skills."""
        with self._lock:
            return len(self._skills)

    def __iter__(self) -> Iterator[SkillEntry]:
        """Iterate over all loaded skills."""
        with self._lock:
            return iter(list(self._skills.values()))

    def __contains__(self, name: str) -> bool:
        """Check if a skill name is in the registry."""
        return self.is_available(name)


# Global registry instance (lazy initialization)
_global_registry: SkillRegistry | None = None


def get_skill_registry(
    data_dir: Path | None = None,
    workspace: Path | None = None,
    **kwargs,
) -> SkillRegistry:
    """Get or create the global skill registry.

    Args:
        data_dir: Application data directory.
        workspace: Workspace directory.
        **kwargs: Additional arguments for SkillRegistry.

    Returns:
        The global SkillRegistry instance.
    """
    global _global_registry
    if _global_registry is None:
        _global_registry = SkillRegistry(
            data_dir=data_dir,
            workspace=workspace,
            **kwargs,
        )
    return _global_registry


def reset_skill_registry() -> None:
    """Reset the global skill registry (mainly for testing)."""
    global _global_registry
    _global_registry = None
