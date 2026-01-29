"""技能注册表和管理器

实现技能的注册、查询和生命周期管理。
"""

from pathlib import Path

from loguru import logger

from .workspace import SkillEntry, load_all_skills


# ============================================================================
# 技能注册表
# ============================================================================


class SkillRegistry:
    """技能注册表

    用于存储和查询已加载的技能。
    """

    def __init__(self):
        self._skills: dict[str, SkillEntry] = {}

    def register(self, skill: SkillEntry) -> None:
        """注册技能

        Args:
            skill: 技能条目
        """
        if skill.key in self._skills:
            logger.warning(f"技能 {skill.key} 已注册，将被覆盖")

        self._skills[skill.key] = skill
        logger.debug(f"注册技能: {skill.key} (source={skill.source})")

    def unregister(self, key: str) -> bool:
        """注销技能

        Args:
            key: 技能 key

        Returns:
            是否成功注销
        """
        if key in self._skills:
            del self._skills[key]
            logger.debug(f"注销技能: {key}")
            return True
        return False

    def get(self, key: str) -> SkillEntry | None:
        """获取技能

        Args:
            key: 技能 key

        Returns:
            技能条目（如果存在）
        """
        return self._skills.get(key)

    def has(self, key: str) -> bool:
        """检查技能是否存在

        Args:
            key: 技能 key

        Returns:
            是否存在
        """
        return key in self._skills

    def list_all(self) -> list[SkillEntry]:
        """列出所有技能

        Returns:
            技能列表（按 key 排序）
        """
        return sorted(self._skills.values(), key=lambda s: s.key)

    def find_by_tag(self, tag: str) -> list[SkillEntry]:
        """按标签查找技能

        Args:
            tag: 标签

        Returns:
            匹配的技能列表
        """
        return [
            skill
            for skill in self._skills.values()
            if tag in skill.frontmatter.tags
        ]

    def find_user_invocable(self) -> list[SkillEntry]:
        """查找用户可调用的技能

        Returns:
            用户可调用的技能列表
        """
        return [
            skill
            for skill in self._skills.values()
            if skill.frontmatter.user_invocable
        ]

    def find_model_invocable(self) -> list[SkillEntry]:
        """查找模型可调用的技能

        Returns:
            模型可调用的技能列表
        """
        return [
            skill
            for skill in self._skills.values()
            if not skill.frontmatter.disable_model_invocation
        ]

    def clear(self) -> None:
        """清空所有技能"""
        self._skills.clear()
        logger.debug("清空技能注册表")

    def __len__(self) -> int:
        return len(self._skills)

    def __repr__(self) -> str:
        return f"SkillRegistry(count={len(self._skills)})"


# ============================================================================
# 技能管理器
# ============================================================================


class SkillManager:
    """技能管理器

    负责技能的生命周期管理：
    - 加载技能
    - 重载技能
    - 技能查询
    """

    def __init__(self):
        self.registry = SkillRegistry()
        self._workspace_root: Path | None = None
        self._extra_dirs: list[Path] = []

    def load_skills(
        self,
        workspace_root: Path | str | None = None,
        extra_dirs: list[Path | str] | None = None,
        clear: bool = True,
    ) -> int:
        """加载技能

        Args:
            workspace_root: 工作区根目录
            extra_dirs: 额外的技能目录列表
            clear: 是否清空现有技能

        Returns:
            加载的技能数量
        """
        if clear:
            self.registry.clear()

        # 保存配置以供重载
        if workspace_root is not None:
            self._workspace_root = Path(workspace_root)
        if extra_dirs is not None:
            self._extra_dirs = [Path(d) for d in extra_dirs]

        # 加载技能
        skills = load_all_skills(workspace_root, extra_dirs)

        # 注册到 registry
        for skill in skills.values():
            self.registry.register(skill)

        logger.info(f"技能管理器加载了 {len(skills)} 个技能")
        return len(skills)

    def reload_skills(self) -> int:
        """重载技能

        使用之前的配置重新加载技能。

        Returns:
            加载的技能数量
        """
        logger.info("重载技能...")
        return self.load_skills(
            workspace_root=self._workspace_root,
            extra_dirs=self._extra_dirs,
            clear=True,
        )

    def get_skill(self, key: str) -> SkillEntry | None:
        """获取技能

        Args:
            key: 技能 key

        Returns:
            技能条目（如果存在）
        """
        return self.registry.get(key)

    def list_skills(self) -> list[SkillEntry]:
        """列出所有技能

        Returns:
            技能列表
        """
        return self.registry.list_all()

    def search_skills(
        self,
        tag: str | None = None,
        user_invocable: bool | None = None,
        model_invocable: bool | None = None,
    ) -> list[SkillEntry]:
        """搜索技能

        Args:
            tag: 按标签过滤（可选）
            user_invocable: 按用户可调用过滤（可选）
            model_invocable: 按模型可调用过滤（可选）

        Returns:
            匹配的技能列表
        """
        skills = self.registry.list_all()

        if tag is not None:
            skills = [s for s in skills if tag in s.frontmatter.tags]

        if user_invocable is not None:
            skills = [s for s in skills if s.frontmatter.user_invocable == user_invocable]

        if model_invocable is not None:
            skills = [
                s
                for s in skills
                if (not s.frontmatter.disable_model_invocation) == model_invocable
            ]

        return skills

    def __repr__(self) -> str:
        return f"SkillManager(skills={len(self.registry)})"


# ============================================================================
# 全局单例
# ============================================================================

_global_skill_manager: SkillManager | None = None


def get_skill_manager() -> SkillManager:
    """获取全局技能管理器单例

    Returns:
        SkillManager 实例
    """
    global _global_skill_manager
    if _global_skill_manager is None:
        _global_skill_manager = SkillManager()
    return _global_skill_manager
