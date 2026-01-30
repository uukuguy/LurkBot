"""技能加载优先级系统

实现 MoltBot 技能加载优先级：
1. 工作区技能：.skills/
2. 受管技能：.skill-bundles/
3. 打包技能：bundled skills
4. 额外目录：additional skill directories

参考：MOLTBOT_COMPLETE_ARCHITECTURE.md 第 12.2 节
"""

import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from loguru import logger

from .frontmatter import SkillFrontmatter, validate_skill_file


# ============================================================================
# 枚举和数据模型
# ============================================================================


class SkillSource(str, Enum):
    """技能来源类型"""

    WORKSPACE = "workspace"  # .skills/
    MANAGED = "managed"  # .skill-bundles/
    BUNDLED = "bundled"  # bundled skills
    EXTRA = "extra"  # additional directories


@dataclass
class SkillEntry:
    """技能条目"""

    key: str  # 技能唯一标识
    source: SkillSource  # 来源类型
    priority: int  # 优先级（数字越小优先级越高）
    file_path: Path  # 技能文件路径
    frontmatter: SkillFrontmatter  # Frontmatter 数据
    content: str  # 技能正文内容

    def __repr__(self) -> str:
        return f"SkillEntry(key={self.key!r}, source={self.source}, priority={self.priority})"


# ============================================================================
# 技能发现
# ============================================================================


def discover_skills(
    workspace_root: Path | str | None = None,
    extra_dirs: list[Path | str] | None = None,
) -> list[SkillEntry]:
    """发现所有技能文件

    按优先级顺序：
    1. 工作区技能：.skills/
    2. 受管技能：.skill-bundles/
    3. 打包技能：bundled skills
    4. 额外目录：additional skill directories

    Args:
        workspace_root: 工作区根目录（默认为当前目录）
        extra_dirs: 额外的技能目录列表

    Returns:
        按优先级排序的技能列表
    """
    if workspace_root is None:
        workspace_root = Path.cwd()
    else:
        workspace_root = Path(workspace_root)

    skills: list[SkillEntry] = []

    # 1. 工作区技能：.skills/
    workspace_skills_dir = workspace_root / ".skills"
    if workspace_skills_dir.exists():
        skills.extend(
            _discover_skills_in_dir(
                workspace_skills_dir, SkillSource.WORKSPACE, priority=1
            )
        )

    # 2. 受管技能：.skill-bundles/
    managed_skills_dir = workspace_root / ".skill-bundles"
    if managed_skills_dir.exists():
        skills.extend(
            _discover_skills_in_dir(managed_skills_dir, SkillSource.MANAGED, priority=2)
        )

    # 3. 打包技能：bundled skills (in project root skills/ directory)
    # Navigate from src/lurkbot/skills/workspace.py -> project_root/skills/
    bundled_skills_dir = Path(__file__).parent.parent.parent.parent / "skills"
    if bundled_skills_dir.exists():
        skills.extend(
            _discover_skills_in_dir(bundled_skills_dir, SkillSource.BUNDLED, priority=3)
        )

    # 4. 额外目录
    if extra_dirs:
        for i, extra_dir in enumerate(extra_dirs):
            extra_path = Path(extra_dir)
            if extra_path.exists():
                skills.extend(
                    _discover_skills_in_dir(extra_path, SkillSource.EXTRA, priority=4 + i)
                )

    # 按优先级排序
    skills.sort(key=lambda s: (s.priority, s.key))

    return skills


def _discover_skills_in_dir(
    directory: Path, source: SkillSource, priority: int
) -> list[SkillEntry]:
    """在指定目录中发现技能文件

    技能文件命名规则：
    - SKILL.md: 标准技能文件
    - {name}.skill.md: 命名技能文件

    Args:
        directory: 目录路径
        source: 技能来源
        priority: 优先级

    Returns:
        技能列表
    """
    skills: list[SkillEntry] = []

    # 查找所有技能文件
    skill_files = []

    # 查找 SKILL.md 文件
    for skill_md in directory.rglob("SKILL.md"):
        skill_files.append(skill_md)

    # 查找 *.skill.md 文件
    for skill_md in directory.rglob("*.skill.md"):
        skill_files.append(skill_md)

    # 解析每个技能文件
    for skill_file in skill_files:
        try:
            frontmatter, content = validate_skill_file(str(skill_file))

            # 生成技能 key
            if frontmatter.metadata and frontmatter.metadata.skill_key:
                # 使用自定义 key
                skill_key = frontmatter.metadata.skill_key
            else:
                # 使用目录名或文件名生成 key
                if skill_file.name == "SKILL.md":
                    skill_key = skill_file.parent.name
                else:
                    skill_key = skill_file.stem.replace(".skill", "")

            skills.append(
                SkillEntry(
                    key=skill_key,
                    source=source,
                    priority=priority,
                    file_path=skill_file,
                    frontmatter=frontmatter,
                    content=content,
                )
            )

            logger.debug(
                f"发现技能: {skill_key} (source={source}, path={skill_file.relative_to(directory)})"
            )

        except Exception as e:
            logger.warning(f"跳过无效技能文件 {skill_file}: {e}")
            continue

    return skills


# ============================================================================
# 技能去重
# ============================================================================


def deduplicate_skills(skills: list[SkillEntry]) -> dict[str, SkillEntry]:
    """去重技能列表（保留优先级最高的）

    Args:
        skills: 技能列表（已按优先级排序）

    Returns:
        去重后的技能字典 {key: SkillEntry}
    """
    result: dict[str, SkillEntry] = {}

    for skill in skills:
        if skill.key not in result:
            result[skill.key] = skill
            logger.debug(f"加载技能: {skill.key} (source={skill.source})")
        else:
            # 已存在，跳过（保留优先级更高的）
            existing = result[skill.key]
            logger.debug(
                f"跳过技能: {skill.key} (source={skill.source}, 优先级低于 {existing.source})"
            )

    return result


# ============================================================================
# 主函数
# ============================================================================


def load_all_skills(
    workspace_root: Path | str | None = None,
    extra_dirs: list[Path | str] | None = None,
) -> dict[str, SkillEntry]:
    """加载所有技能

    Args:
        workspace_root: 工作区根目录
        extra_dirs: 额外的技能目录列表

    Returns:
        技能字典 {key: SkillEntry}
    """
    logger.info("开始加载技能...")

    # 发现所有技能
    all_skills = discover_skills(workspace_root, extra_dirs)
    logger.info(f"发现 {len(all_skills)} 个技能文件")

    # 去重（保留优先级最高的）
    skills = deduplicate_skills(all_skills)
    logger.info(f"加载 {len(skills)} 个唯一技能")

    return skills
