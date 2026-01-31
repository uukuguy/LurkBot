"""任务建议器 - 基于分析结果生成任务建议

根据用户意图分析和历史模式，生成可操作的任务建议。
"""

from loguru import logger
from pydantic import BaseModel, Field
from pydantic_ai import Agent

from .models import InputAnalysis, TaskPriority, TaskSuggestion


class SuggestionRequest(BaseModel):
    """建议请求数据"""

    user_prompt: str = Field(description="用户原始输入")
    analysis: InputAnalysis = Field(description="输入分析结果")
    context_summary: str | None = Field(
        default=None, description="上下文摘要（可选）"
    )


class SuggestionResponse(BaseModel):
    """LLM 返回的建议响应"""

    suggestions: list[TaskSuggestion] = Field(description="任务建议列表")


class TaskSuggester:
    """生成任务建议"""

    def __init__(self, model: str = "openai:gpt-4o-mini"):
        """初始化建议器

        Args:
            model: 使用的模型标识符
        """
        self.model = model
        self._agent = self._create_agent()

    def _create_agent(self) -> Agent:
        """创建用于生成建议的 Agent"""
        system_prompt = """你是一个任务建议专家。基于用户的输入分析，你需要生成可操作的任务建议。

输入信息包括：
- 用户原始输入
- 意图分析（intent, sentiment, key_topics, implicit_needs）
- 可选的上下文摘要

你的任务是生成 1-3 个具体的任务建议，每个建议包括：
1. task_type: 任务类型（如：debug, investigate, optimize, learn, document）
2. description: 简洁的任务描述（1-2句话）
3. priority: 优先级（high/medium/low）
4. actions: 3-5个具体操作步骤
5. rationale: 为什么建议这个任务（基于分析结果）
6. confidence: 建议置信度（0-1）

建议原则：
- 优先解决用户的实际痛点
- 建议要具体可执行
- 考虑用户的隐含需求
- 不要建议用户已经明确要做的事情（那不是"主动"建议）

特别注意：
- 如果用户在抱怨，建议调查问题根源
- 如果用户在探索，建议相关学习资源
- 如果用户反复询问类似问题，建议创建文档或自动化
"""

        agent: Agent[None, SuggestionResponse] = Agent(
            self.model,
            system_prompt=system_prompt,
            output_type=SuggestionResponse,
        )
        return agent

    async def suggest(
        self,
        user_prompt: str,
        analysis: InputAnalysis,
        context_summary: str | None = None,
    ) -> list[TaskSuggestion]:
        """生成任务建议

        Args:
            user_prompt: 用户原始输入
            analysis: 输入分析结果
            context_summary: 可选的上下文摘要

        Returns:
            list[TaskSuggestion]: 任务建议列表
        """
        try:
            # 构建请求
            request_text = f"""用户输入：{user_prompt}

意图分析：
- 意图：{analysis.intent.value}
- 情感：{analysis.sentiment.value}
- 关键主题：{', '.join(analysis.key_topics) if analysis.key_topics else '无'}
- 隐含需求：{', '.join(analysis.implicit_needs) if analysis.implicit_needs else '无'}
- 置信度：{analysis.confidence:.2f}
"""

            if context_summary:
                request_text += f"\n上下文摘要：{context_summary}"

            # 运行建议生成
            result = await self._agent.run(request_text)
            suggestions = result.data.suggestions

            # 按置信度和优先级排序
            suggestions.sort(
                key=lambda s: (
                    self._priority_weight(s.priority),
                    s.confidence,
                ),
                reverse=True,
            )

            logger.info(f"为用户生成了 {len(suggestions)} 个任务建议")
            return suggestions

        except Exception as e:
            logger.error(f"生成任务建议失败: {e}")
            return []

    def _priority_weight(self, priority: TaskPriority) -> int:
        """优先级权重"""
        weights = {
            TaskPriority.HIGH: 3,
            TaskPriority.MEDIUM: 2,
            TaskPriority.LOW: 1,
        }
        return weights.get(priority, 0)

    def format_suggestions_for_prompt(self, suggestions: list[TaskSuggestion]) -> str:
        """将建议格式化为适合添加到 prompt 的文本

        Args:
            suggestions: 任务建议列表

        Returns:
            str: 格式化的建议文本
        """
        if not suggestions:
            return ""

        lines = ["## 💡 主动建议", ""]
        lines.append("基于你的输入，我注意到以下可能有帮助的任务：")
        lines.append("")

        for i, suggestion in enumerate(suggestions[:3], 1):  # 最多3个
            priority_emoji = {
                TaskPriority.HIGH: "🔴",
                TaskPriority.MEDIUM: "🟡",
                TaskPriority.LOW: "🟢",
            }
            emoji = priority_emoji.get(suggestion.priority, "⚪")

            lines.append(f"### {emoji} {i}. {suggestion.description}")
            lines.append(f"**类型**: {suggestion.task_type}")
            lines.append(f"**理由**: {suggestion.rationale}")
            lines.append("**建议步骤**:")
            for action in suggestion.actions:
                lines.append(f"- {action}")
            lines.append("")

        lines.append("你希望我帮你执行哪个任务，还是继续你的原始请求？")
        return "\n".join(lines)
