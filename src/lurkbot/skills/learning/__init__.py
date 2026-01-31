"""动态技能学习模块

提供从对话中学习新技能并保存为可复用模板的功能。
"""

from .models import (
    DetectedPattern,
    PatternType,
    SkillAction,
    SkillExecutionContext,
    SkillExecutionResult,
    SkillLearningResult,
    SkillTemplate,
    SkillType,
)
from .pattern_detector import PatternDetector
from .skill_storage import SkillStorage, get_skill_storage
from .template_generator import TemplateGenerator

__all__ = [
    "PatternDetector",
    "TemplateGenerator",
    "SkillStorage",
    "get_skill_storage",
    "SkillTemplate",
    "SkillAction",
    "DetectedPattern",
    "SkillLearningResult",
    "SkillExecutionContext",
    "SkillExecutionResult",
    "SkillType",
    "PatternType",
]
