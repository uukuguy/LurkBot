"""主动任务识别的数据模型

定义了任务分析、建议和识别结果的数据结构。
"""

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class IntentType(str, Enum):
    """用户意图类型"""

    QUESTION = "question"  # 提问
    REQUEST = "request"  # 请求执行任务
    COMPLAINT = "complaint"  # 抱怨/问题反馈
    FEEDBACK = "feedback"  # 反馈意见
    EXPLORATION = "exploration"  # 探索性询问
    UNKNOWN = "unknown"  # 未知意图


class TaskPriority(str, Enum):
    """任务优先级"""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class SentimentType(str, Enum):
    """情感类型"""

    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


class InputAnalysis(BaseModel):
    """用户输入的分析结果"""

    intent: IntentType = Field(description="识别出的用户意图")
    sentiment: SentimentType = Field(description="情感倾向")
    key_topics: list[str] = Field(
        default_factory=list, description="关键主题词，1-3个词"
    )
    implicit_needs: list[str] = Field(
        default_factory=list, description="隐含需求描述"
    )
    confidence: float = Field(ge=0.0, le=1.0, description="分析置信度")


class TaskSuggestion(BaseModel):
    """任务建议"""

    task_type: str = Field(description="任务类型，如：debug, investigate, optimize")
    description: str = Field(description="任务描述")
    priority: TaskPriority = Field(description="优先级")
    actions: list[str] = Field(description="建议的具体操作步骤")
    rationale: str = Field(description="建议理由")
    confidence: float = Field(ge=0.0, le=1.0, description="建议置信度")


class ProactiveResult(BaseModel):
    """主动识别结果"""

    analysis: InputAnalysis = Field(description="输入分析结果")
    suggestions: list[TaskSuggestion] = Field(
        default_factory=list, description="任务建议列表"
    )
    should_suggest: bool = Field(
        default=False, description="是否应该向用户展示建议"
    )
    timestamp: datetime = Field(default_factory=datetime.now, description="识别时间")


class ContextPattern(BaseModel):
    """上下文模式（用于模式识别）"""

    pattern_type: Literal["repeated_question", "sequential_task", "error_pattern"] = (
        Field(description="模式类型")
    )
    description: str = Field(description="模式描述")
    occurrences: int = Field(ge=1, description="出现次数")
    first_seen: datetime = Field(description="首次出现时间")
    last_seen: datetime = Field(description="最后出现时间")
    related_sessions: list[str] = Field(description="相关会话 ID")
