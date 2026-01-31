"""模板生成器 - 从检测到的模式生成技能模板

基于识别出的模式，使用 LLM 生成结构化的技能模板。
"""

import uuid
from datetime import datetime

from loguru import logger
from pydantic import BaseModel, Field
from pydantic_ai import Agent

from .models import (
    DetectedPattern,
    PatternType,
    SkillAction,
    SkillTemplate,
    SkillType,
)


class GeneratedSkillResponse(BaseModel):
    """LLM 返回的技能生成响应"""

    name: str = Field(description="技能名称")
    description: str = Field(description="技能描述")
    skill_type: SkillType = Field(description="技能类型")
    trigger_keywords: list[str] = Field(description="触发关键词")
    actions: list[dict] = Field(description="操作步骤，每个包含 action_type, description, parameters")
    examples: list[str] = Field(description="使用示���")


class TemplateGenerator:
    """从模式生成技能模板"""

    def __init__(self, model: str = "openai:gpt-4o-mini"):
        """初始化模板生成器

        Args:
            model: 使用的模型标识符
        """
        self.model = model
        self._agent = self._create_agent()

    def _create_agent(self) -> Agent:
        """创建用于生成技能模板的 Agent"""
        system_prompt = """你是一个技能模板生成专家。基于检测到的用户行为模式，你需要生成可复用的技能模板。

输入信息包括：
- 模式类型（重复任务、顺序步骤、数据处理等）
- 模式描述
- 重复的操作
- 常见关键词
- 步骤序列

你的任务是生成一个结构化的技能模板，包括：
1. name: 简洁的技能名称（2-5个词）
2. description: 清晰的技能描述（1-2句话）
3. skill_type: 技能类型（workflow/command/analysis/generation/transformation）
4. trigger_keywords: 3-5个触发关键词
5. actions: 3-7个具体操作步骤，每个步骤包含：
   - action_type: 操作类型（如：run_command, call_api, transform_data, analyze_text）
   - description: 操作描述
   - parameters: 操作参数（dict）
6. examples: 2-3个使用示例

生成原则：
- 技能要具体可执行
- 步骤要清晰明确
- 参数要合理设置
- 示例要贴近实际使用场景
"""

        agent: Agent[None, GeneratedSkillResponse] = Agent(
            self.model,
            system_prompt=system_prompt,
            output_type=GeneratedSkillResponse,
        )
        return agent

    async def generate_template(
        self,
        pattern: DetectedPattern,
        user_id: str,
        session_id: str,
    ) -> SkillTemplate | None:
        """从模式生成技能模板

        Args:
            pattern: 检测到的模式
            user_id: 用户 ID
            session_id: 会话 ID

        Returns:
            SkillTemplate | None: 生成的技能模板，失败返回 None
        """
        try:
            # 构建生成请求
            request_text = f"""模式类型：{pattern.pattern_type.value}
模式描述：{pattern.description}
置信度：{pattern.confidence:.2f}

重复的操作：
{self._format_list(pattern.repeated_actions)}

常见关键词：
{', '.join(pattern.common_keywords) if pattern.common_keywords else '无'}

步骤序列：
{self._format_list(pattern.step_sequence)}

出现次数：{pattern.occurrence_count}

请基于以上信息生成一个可复用的技能模板。
"""

            # 运行生成
            result = await self._agent.run(request_text)
            generated = result.data

            # 转换为 SkillTemplate
            skill_id = str(uuid.uuid4())

            # 转换 actions
            actions = []
            for i, action_dict in enumerate(generated.actions, 1):
                actions.append(
                    SkillAction(
                        step_number=i,
                        action_type=action_dict.get("action_type", "custom_action"),
                        description=action_dict.get("description", ""),
                        parameters=action_dict.get("parameters", {}),
                        expected_output=action_dict.get("expected_output"),
                    )
                )

            template = SkillTemplate(
                skill_id=skill_id,
                name=generated.name,
                description=generated.description,
                skill_type=generated.skill_type,
                pattern_type=pattern.pattern_type,
                trigger_keywords=generated.trigger_keywords,
                actions=actions,
                learned_from_session=session_id,
                learned_from_user=user_id,
                created_at=datetime.now(),
                examples=generated.examples,
            )

            logger.info(f"Generated skill template: {template.name} (ID: {skill_id})")
            return template

        except Exception as e:
            logger.error(f"Failed to generate skill template: {e}")
            return None

    def _format_list(self, items: list[str]) -> str:
        """格式化列表为文本"""
        if not items:
            return "无"
        return "\n".join([f"- {item}" for item in items[:5]])  # 最多5个

    def format_template_for_user(self, template: SkillTemplate) -> str:
        """将技能模板格式化为用户友好的文本

        Args:
            template: 技能模板

        Returns:
            str: 格式化的文本
        """
        lines = [
            f"## 🎯 新技能建议: {template.name}",
            "",
            f"**描述**: {template.description}",
            f"**类型**: {template.skill_type.value}",
            f"**触发词**: {', '.join(template.trigger_keywords)}",
            "",
            "**操作步骤**:",
        ]

        for action in template.actions:
            lines.append(f"{action.step_number}. {action.description}")

        lines.append("")
        lines.append("**使用示例**:")
        for example in template.examples:
            lines.append(f"- {example}")

        lines.append("")
        lines.append("要创建这个技能吗？回复 '是' 或 '创建技能' 来保存它。")

        return "\n".join(lines)
