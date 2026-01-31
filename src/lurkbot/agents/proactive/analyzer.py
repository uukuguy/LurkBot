"""输入分析器 - 分析用户输入的意图和情感

使用 LLM 进行结构化分析，识别用户意图、情感、关键主题和隐含需求。
"""

from loguru import logger
from pydantic_ai import Agent

from .models import InputAnalysis, IntentType, SentimentType


class InputAnalyzer:
    """分析用户输入，识别意图、情感和隐含需求"""

    def __init__(self, model: str = "openai:gpt-4o-mini"):
        """初始化分析器

        Args:
            model: 使用的模型标识符
        """
        self.model = model
        self._agent = self._create_agent()

    def _create_agent(self) -> Agent:
        """创建用于分析的 Agent"""
        system_prompt = """你是一个用户意图分析专家。你的任务是分析用户输入，识别：
1. 用户的主要意图（提问、请求、抱怨、反馈、探索）
2. 情感倾向（积极、中性、消极）
3. 关键主题词（1-3个最重要的词）
4. 隐含需求（用户可能没有明说，但暗示的需求）

分析要深入，尤其注意：
- 抱怨背后的真实问题
- 简单问题背后的复杂需求
- 情绪化表达中的实际诉求

输出必须是结构化的 JSON，包含 intent, sentiment, key_topics, implicit_needs, confidence。
"""

        agent: Agent[None, InputAnalysis] = Agent(
            self.model,
            system_prompt=system_prompt,
            output_type=InputAnalysis,
        )
        return agent

    async def analyze(
        self,
        prompt: str,
        context_history: list[dict] | None = None,
    ) -> InputAnalysis:
        """分析用户输入

        Args:
            prompt: 用户输入的文本
            context_history: 可选的历史上下文，格式: [{"role": "user"|"assistant", "content": "..."}]

        Returns:
            InputAnalysis: 分析结果
        """
        try:
            # 构建分析提示
            analysis_prompt = f"用户输入：{prompt}"

            # 如果有历史上下文，添加到提示中
            if context_history:
                recent_history = context_history[-3:]  # 只取最近3条
                history_text = "\n".join(
                    [f"{h['role']}: {h['content']}" for h in recent_history]
                )
                analysis_prompt += (
                    f"\n\n最近的对话历史：\n{history_text}\n\n基于以上历史进行分析。"
                )

            # 运行分析
            result = await self._agent.run(analysis_prompt)
            return result.data

        except Exception as e:
            logger.error(f"分析用户输入失败: {e}")
            # 返回默认分析结果
            return InputAnalysis(
                intent=IntentType.UNKNOWN,
                sentiment=SentimentType.NEUTRAL,
                key_topics=[],
                implicit_needs=[],
                confidence=0.0,
            )

    def should_trigger_proactive(self, analysis: InputAnalysis) -> bool:
        """判断是否应该触发主动建议

        Args:
            analysis: 输入分析结果

        Returns:
            bool: 是否应该触发主动建议
        """
        # 触发条件：
        # 1. 消极情感 + 抱怨意图
        # 2. 存在隐含需求
        # 3. 置信度较高（>0.6）

        if analysis.confidence < 0.6:
            return False

        # 消极情感且是抱怨
        if (
            analysis.sentiment == SentimentType.NEGATIVE
            and analysis.intent == IntentType.COMPLAINT
        ):
            return True

        # 有隐含需求
        if len(analysis.implicit_needs) > 0:
            return True

        return False
