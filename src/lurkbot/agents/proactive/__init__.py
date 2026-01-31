"""主动任务识别模块

提供主动分析用户输入并生成任务建议的功能。
"""

from .analyzer import InputAnalyzer
from .models import (
    ContextPattern,
    InputAnalysis,
    IntentType,
    ProactiveResult,
    SentimentType,
    TaskPriority,
    TaskSuggestion,
)
from .suggester import TaskSuggester

__all__ = [
    "InputAnalyzer",
    "TaskSuggester",
    "InputAnalysis",
    "TaskSuggestion",
    "ProactiveResult",
    "IntentType",
    "SentimentType",
    "TaskPriority",
    "ContextPattern",
]
