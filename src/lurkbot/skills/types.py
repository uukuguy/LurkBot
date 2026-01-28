"""Skill system types and models."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field


class InstallSpec(BaseModel):
    """Installation specification for a skill dependency."""

    id: str | None = None
    kind: Literal["brew", "apt", "pip", "uv", "go", "npm", "download"] = "pip"
    label: str | None = None
    bins: list[str] = Field(default_factory=list)
    os: list[str] = Field(default_factory=list)
    # Kind-specific fields
    formula: str | None = None  # brew
    package: str | None = None  # apt, npm, pip
    module: str | None = None  # uv, pip
    url: str | None = None  # download


class SkillRequirements(BaseModel):
    """Skill requirements for eligibility checking."""

    bins: list[str] = Field(default_factory=list)
    any_bins: list[str] = Field(default_factory=list, alias="anyBins")
    env: list[str] = Field(default_factory=list)
    config: list[str] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


class SkillMetadata(BaseModel):
    """Moltbot-specific skill metadata from the 'moltbot' key in frontmatter."""

    emoji: str | None = None
    homepage: str | None = None
    skill_key: str | None = Field(default=None, alias="skillKey")
    primary_env: str | None = Field(default=None, alias="primaryEnv")
    always: bool = False
    os: list[str] = Field(default_factory=list)
    requires: SkillRequirements = Field(default_factory=SkillRequirements)
    install: list[InstallSpec] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


class SkillFrontmatter(BaseModel):
    """Parsed YAML frontmatter from a skill file."""

    name: str
    description: str = ""
    homepage: str | None = None
    user_invocable: bool = Field(default=True, alias="user-invocable")
    disable_model_invocation: bool = Field(default=False, alias="disable-model-invocation")
    command_dispatch: str | None = Field(default=None, alias="command-dispatch")
    command_tool: str | None = Field(default=None, alias="command-tool")
    command_arg_mode: str = Field(default="raw", alias="command-arg-mode")
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = {"populate_by_name": True}

    def get_moltbot_metadata(self) -> SkillMetadata:
        """Extract and parse the moltbot-specific metadata."""
        moltbot_data = self.metadata.get("moltbot", {})
        if not isinstance(moltbot_data, dict):
            return SkillMetadata()
        return SkillMetadata.model_validate(moltbot_data)


@dataclass
class SkillEntry:
    """A loaded skill entry with parsed content."""

    name: str
    description: str
    content: str  # Markdown content after frontmatter
    source_path: Path
    source_type: Literal["bundled", "managed", "workspace", "extra"]
    frontmatter: SkillFrontmatter
    metadata: SkillMetadata = field(default_factory=SkillMetadata)
    enabled: bool = True

    @property
    def emoji(self) -> str:
        """Get the skill's emoji icon."""
        return self.metadata.emoji or ""

    @property
    def primary_env(self) -> str | None:
        """Get the primary environment variable name."""
        return self.metadata.primary_env

    def to_prompt(self) -> str:
        """Convert skill to prompt text for AI context."""
        lines = [f"## {self.emoji} {self.name}" if self.emoji else f"## {self.name}"]
        if self.description:
            lines.append(f"\n{self.description}")
        if self.content.strip():
            lines.append(f"\n{self.content.strip()}")
        return "\n".join(lines)


@dataclass
class SkillSnapshot:
    """A snapshot of loaded skills for caching and versioning."""

    prompt: str  # Combined prompt text for AI context
    skills: list[dict[str, Any]]  # List of {name, primary_env}
    version: int = 0
    resolved_skills: list[SkillEntry] = field(default_factory=list)
