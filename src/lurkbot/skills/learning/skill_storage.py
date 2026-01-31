"""技能存储 - 持久化技能模板

使用 JSON 文件存储学习到的技能模板。
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from loguru import logger

from .models import SkillTemplate


class SkillStorage:
    """技能模板的持久化存储"""

    def __init__(self, storage_dir: str = "./data/skills"):
        """初始化技能存储

        Args:
            storage_dir: 存储目录路径
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.index_file = self.storage_dir / "skills_index.json"
        self._ensure_index()

    def _ensure_index(self):
        """确保索引文件存在"""
        if not self.index_file.exists():
            self._save_index({})

    def _load_index(self) -> dict[str, Any]:
        """加载技能索引"""
        try:
            with open(self.index_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load skills index: {e}")
            return {}

    def _save_index(self, index: dict[str, Any]):
        """保存技能索引"""
        try:
            with open(self.index_file, "w", encoding="utf-8") as f:
                json.dump(index, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save skills index: {e}")

    def save_skill(self, skill: SkillTemplate) -> bool:
        """保存技能模板

        Args:
            skill: 技能模板

        Returns:
            bool: 是否成功
        """
        try:
            # 保存技能文件
            skill_file = self.storage_dir / f"{skill.skill_id}.json"
            skill_dict = skill.model_dump(mode="json")

            # 转换 datetime 为字符串
            skill_dict = self._serialize_datetimes(skill_dict)

            with open(skill_file, "w", encoding="utf-8") as f:
                json.dump(skill_dict, f, indent=2, ensure_ascii=False)

            # 更新索引
            index = self._load_index()
            index[skill.skill_id] = {
                "name": skill.name,
                "skill_type": skill.skill_type.value,
                "pattern_type": skill.pattern_type.value,
                "user_id": skill.learned_from_user,
                "created_at": skill.created_at.isoformat(),
                "usage_count": skill.usage_count,
            }
            self._save_index(index)

            logger.info(f"Saved skill: {skill.name} (ID: {skill.skill_id})")
            return True

        except Exception as e:
            logger.error(f"Failed to save skill {skill.skill_id}: {e}")
            return False

    def load_skill(self, skill_id: str) -> SkillTemplate | None:
        """加载技能模板

        Args:
            skill_id: 技能 ID

        Returns:
            SkillTemplate | None: 技能模板，不存在返回 None
        """
        try:
            skill_file = self.storage_dir / f"{skill_id}.json"
            if not skill_file.exists():
                return None

            with open(skill_file, "r", encoding="utf-8") as f:
                skill_dict = json.load(f)

            # 转换字符串为 datetime
            skill_dict = self._deserialize_datetimes(skill_dict)

            return SkillTemplate(**skill_dict)

        except Exception as e:
            logger.error(f"Failed to load skill {skill_id}: {e}")
            return None

    def list_skills(
        self,
        user_id: str | None = None,
        skill_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """列出技能

        Args:
            user_id: 可选的用户 ID 过滤
            skill_type: 可选的技能类型过滤

        Returns:
            list[dict]: 技能信息列表
        """
        index = self._load_index()
        skills = []

        for skill_id, info in index.items():
            # 应用过滤
            if user_id and info.get("user_id") != user_id:
                continue
            if skill_type and info.get("skill_type") != skill_type:
                continue

            skills.append({"skill_id": skill_id, **info})

        # 按创建时间排序
        skills.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return skills

    def delete_skill(self, skill_id: str) -> bool:
        """删除技能

        Args:
            skill_id: 技能 ID

        Returns:
            bool: 是否成功
        """
        try:
            # 删除技能文件
            skill_file = self.storage_dir / f"{skill_id}.json"
            if skill_file.exists():
                skill_file.unlink()

            # 更新索引
            index = self._load_index()
            if skill_id in index:
                del index[skill_id]
                self._save_index(index)

            logger.info(f"Deleted skill: {skill_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete skill {skill_id}: {e}")
            return False

    def update_usage(self, skill_id: str, success: bool = True) -> bool:
        """更新技能使用统计

        Args:
            skill_id: 技能 ID
            success: 是否成功执行

        Returns:
            bool: 是否成功更新
        """
        try:
            skill = self.load_skill(skill_id)
            if not skill:
                return False

            skill.usage_count += 1
            if success:
                skill.success_count += 1
            skill.last_used_at = datetime.now()

            return self.save_skill(skill)

        except Exception as e:
            logger.error(f"Failed to update usage for skill {skill_id}: {e}")
            return False

    def _serialize_datetimes(self, obj: Any) -> Any:
        """递归转换 datetime 为字符串"""
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, dict):
            return {k: self._serialize_datetimes(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._serialize_datetimes(item) for item in obj]
        return obj

    def _deserialize_datetimes(self, obj: Any) -> Any:
        """递归转换字符串为 datetime"""
        if isinstance(obj, dict):
            result = {}
            for k, v in obj.items():
                # 识别 datetime 字段
                if k in ["created_at", "last_used_at", "first_seen", "last_seen", "started_at", "completed_at"]:
                    if isinstance(v, str):
                        try:
                            result[k] = datetime.fromisoformat(v)
                        except:
                            result[k] = v
                    else:
                        result[k] = v
                else:
                    result[k] = self._deserialize_datetimes(v)
            return result
        elif isinstance(obj, list):
            return [self._deserialize_datetimes(item) for item in obj]
        return obj


# 全局单例
_storage_instance: SkillStorage | None = None


def get_skill_storage(storage_dir: str = "./data/skills") -> SkillStorage:
    """获取技能存储单例

    Args:
        storage_dir: 存储目录路径

    Returns:
        SkillStorage: 技能存储实例
    """
    global _storage_instance
    if _storage_instance is None:
        _storage_instance = SkillStorage(storage_dir)
    return _storage_instance
