"""动态技能学习的数据模型

定义了技能模板、学习模式和技能元数据的数据结构。
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class SkillType(str, Enum):
    """技能类型"""

    WORKFLOW = "workflow"  # 工作流程
    COMMAND = "command"  # 命令执行
    ANALYSIS = "analysis"  # 分析任务
    GENERATION = "generation"  # 生成任务
    TRANSFORMATION = "transformation"  # 数据转换
    CUSTOM = "custom"  # 自定义


class PatternType(str, Enum):
    """模式类型"""

    REPEATED_TASK = "repeated_task"  # 重复任务
    SEQUENTIAL_STEPS = "sequential_steps"  # 顺序步骤
    CONDITIONAL_LOGIC = "conditional_logic"  # 条件逻辑
    DATA_PROCESSING = "data_processing"  # 数据处理
    ERROR_HANDLING = "error_handling"  # 错误处理


class SkillAction(BaseModel):
    """技能中的单个操作步骤"""

    step_number: int = Field(ge=1, description="步骤编号")
    action_type: str = Field(description="操作类型，如：run_command, call_api, transform_data")
    description: str = Field(description="操作描述")
    parameters: dict[str, Any] = Field(default_factory=dict, description="操作参数")
    expected_output: str | None = Field(default=None, description="预期输出描述")


class SkillTemplate(BaseModel):
    """技能模板"""

    skill_id: str = Field(description="技能唯一标识符")
    name: str = Field(description="技能名称")
    description: str = Field(description="技能描述")
    skill_type: SkillType = Field(description="技能类型")
    pattern_type: PatternType = Field(description="识别出的模式类型")

    # 触发条件
    trigger_keywords: list[str] = Field(
        default_factory=list, description="触发关键词"
    )
    trigger_pattern: str | None = Field(default=None, description="触发模式（正则表达式）")

    # 执行步骤
    actions: list[SkillAction] = Field(description="操作步骤列表")

    # 元数据
    learned_from_session: str = Field(description="学习来源会话 ID")
    learned_from_user: str = Field(description="学习来源用户 ID")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    usage_count: int = Field(default=0, description="使用次数")
    success_count: int = Field(default=0, description="成功次数")
    last_used_at: datetime | None = Field(default=None, description="最后使用时间")

    # 版本控制
    version: int = Field(default=1, description="版本号")
    parent_skill_id: str | None = Field(default=None, description="父技能 ID（如果是改进版本）")

    # 可选的示例
    examples: list[str] = Field(default_factory=list, description="使用示例")


class DetectedPattern(BaseModel):
    """检测到的对话模式"""

    pattern_type: PatternType = Field(description="模式类型")
    description: str = Field(description="模式描述")
    confidence: float = Field(ge=0.0, le=1.0, description="置信度")

    # 模式特征
    repeated_actions: list[str] = Field(
        default_factory=list, description="重复的操作"
    )
    common_keywords: list[str] = Field(
        default_factory=list, description="常见关键词"
    )
    step_sequence: list[str] = Field(default_factory=list, description="步骤序列")

    # 上下文信息
    session_ids: list[str] = Field(description="相关会话 ID")
    occurrence_count: int = Field(ge=1, description="出现次数")
    first_seen: datetime = Field(description="首次出现时间")
    last_seen: datetime = Field(description="最后出现时间")


class SkillLearningResult(BaseModel):
    """技能学习结果"""

    detected_patterns: list[DetectedPattern] = Field(
        default_factory=list, description="检测到的模式"
    )
    suggested_skills: list[SkillTemplate] = Field(
        default_factory=list, description="建议的技能模板"
    )
    should_prompt_user: bool = Field(
        default=False, description="是否应该提示用户创建技能"
    )
    prompt_message: str | None = Field(
        default=None, description="提示用户的消息"
    )


class SkillExecutionContext(BaseModel):
    """技能执行上下文"""

    skill_id: str = Field(description="技能 ID")
    user_id: str = Field(description="用户 ID")
    session_id: str = Field(description="会话 ID")
    input_data: dict[str, Any] = Field(default_factory=dict, description="输入数据")
    started_at: datetime = Field(default_factory=datetime.now, description="开始时间")


class SkillExecutionResult(BaseModel):
    """技能执行结果"""

    skill_id: str = Field(description="技能 ID")
    success: bool = Field(description="是否成功")
    output_data: dict[str, Any] = Field(default_factory=dict, description="输出数据")
    error_message: str | None = Field(default=None, description="错误消息")
    execution_time_ms: float = Field(description="执行时间（毫秒）")
    completed_at: datetime = Field(default_factory=datetime.now, description="完成时间")
