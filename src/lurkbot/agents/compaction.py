"""
Context Compaction System - 上下文自适应压缩

对标 MoltBot agents/compaction.ts

功能:
- Token 估算 (简化实现：~4 chars = 1 token)
- 自适应分块比例计算
- 消息分割 (按 Token 比例 / 最大 Token 数)
- 分阶段摘要生成
- 压缩消息历史
"""

from typing import Protocol
from loguru import logger


# ============================================================================
# Constants (对标 MoltBot compaction.ts)
# ============================================================================

BASE_CHUNK_RATIO = 0.4  # 40% 保留最近历史
MIN_CHUNK_RATIO = 0.15  # 最小 15%
SAFETY_MARGIN = 1.2  # 20% 估算缓冲
DEFAULT_CONTEXT_TOKENS = 128000  # 默认上下文窗口

MERGE_SUMMARIES_INSTRUCTIONS = (
    "Merge these partial summaries into a single cohesive summary. "
    "Preserve decisions, TODOs, open questions, and any constraints."
)


# ============================================================================
# LLM Client Protocol (for summarization)
# ============================================================================


class LLMClient(Protocol):
    """LLM 客户端协议（用于摘要生成）"""

    async def chat(self, messages: list[dict]) -> "LLMResponse":
        ...


class LLMResponse(Protocol):
    """LLM 响应协议"""

    text: str


# ============================================================================
# Token Estimation
# ============================================================================


def estimate_tokens(text: str, model: str = "claude") -> int:
    """
    估算文本的 token 数

    对标 MoltBot estimateTokens()

    简化实现: 约 4 字符 = 1 token
    （更精确的实现需要使用 tiktoken 或类似库）
    """
    return len(text) // 4 + 1


def estimate_messages_tokens(messages: list[dict]) -> int:
    """
    估算消息列表的 token 数

    对标 MoltBot estimateMessagesTokens()
    """
    total = 0
    for msg in messages:
        content = msg.get("content", "")
        if isinstance(content, str):
            total += estimate_tokens(content)
        elif isinstance(content, list):
            # 处理多模态内容
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    total += estimate_tokens(block.get("text", ""))
    return total


# ============================================================================
# Message Splitting
# ============================================================================


def split_messages_by_token_share(
    messages: list[dict],
    parts: int = 2,
) -> list[list[dict]]:
    """
    按 Token 比例分割消息

    对标 MoltBot splitMessagesByTokenShare()

    逻辑:
    - 尽量将消息平均分成 `parts` 部分
    - 每部分 token 数大致相等
    """
    if not messages:
        return []

    total_tokens = estimate_messages_tokens(messages)
    target_tokens = total_tokens / parts

    chunks: list[list[dict]] = []
    current: list[dict] = []
    current_tokens = 0

    for message in messages:
        message_tokens = estimate_messages_tokens([message])

        # 如果当前块接近目标大小且还未达到所需部分数，开始新块
        if (
            len(chunks) < parts - 1
            and current
            and current_tokens + message_tokens > target_tokens
        ):
            chunks.append(current)
            current = []
            current_tokens = 0

        current.append(message)
        current_tokens += message_tokens

    # 添加最后一块
    if current:
        chunks.append(current)

    return chunks


def chunk_messages_by_max_tokens(
    messages: list[dict],
    max_tokens: int,
) -> list[list[dict]]:
    """
    按最大 Token 数分块

    对标 MoltBot chunkMessagesByMaxTokens()

    逻辑:
    - 每块不超过 max_tokens
    - 不会分割单个消息
    """
    chunks: list[list[dict]] = []
    current_chunk: list[dict] = []
    current_tokens = 0

    for message in messages:
        message_tokens = estimate_messages_tokens([message])

        # 如果加上当前消息会超出限制，先保存当前块
        if current_chunk and current_tokens + message_tokens > max_tokens:
            chunks.append(current_chunk)
            current_chunk = []
            current_tokens = 0

        current_chunk.append(message)
        current_tokens += message_tokens

    # 添加最后一块
    if current_chunk:
        chunks.append(current_chunk)

    return chunks


# ============================================================================
# Adaptive Chunk Ratio
# ============================================================================


def compute_adaptive_chunk_ratio(
    messages: list[dict],
    context_window: int,
) -> float:
    """
    计算自适应分块比例

    对标 MoltBot computeAdaptiveChunkRatio()

    逻辑:
    - 如果平均消息 > 上下文的 10%，减少分块比例
    - 确保不低于 MIN_CHUNK_RATIO

    目的:
    - 避免保留消息过多导致压缩效果不佳
    - 适应长消息场景
    """
    if not messages:
        return BASE_CHUNK_RATIO

    total_tokens = estimate_messages_tokens(messages)
    avg_tokens = total_tokens / len(messages)

    # 应用安全边界
    safe_avg_tokens = avg_tokens * SAFETY_MARGIN
    avg_ratio = safe_avg_tokens / context_window

    # 如果平均消息 > 上下文的 10%，减少分块比例
    if avg_ratio > 0.1:
        reduction = min(avg_ratio * 2, BASE_CHUNK_RATIO - MIN_CHUNK_RATIO)
        return max(MIN_CHUNK_RATIO, BASE_CHUNK_RATIO - reduction)

    return BASE_CHUNK_RATIO


# ============================================================================
# Summarization (对标 MoltBot summarizeInStages)
# ============================================================================


async def summarize_in_stages(
    messages: list[dict],
    llm_client: LLMClient,
    reserve_tokens: int,
    max_chunk_tokens: int,
    context_window: int,
    parts: int = 2,
) -> str:
    """
    分阶段摘要

    对标 MoltBot summarizeInStages()

    流程:
    1. 将消息分成多个部分
    2. 对每个部分生成摘要
    3. 合并所有部分摘要

    参数:
    - messages: 要摘要的消息
    - llm_client: LLM 客户端
    - reserve_tokens: 预留 token (用于系统提示词等)
    - max_chunk_tokens: 每块最大 token 数
    - context_window: 上下文窗口大小
    - parts: 分成几部分（默认 2）
    """
    # 分割消息
    splits = split_messages_by_token_share(messages, parts)

    logger.debug(
        f"Summarizing {len(messages)} messages in {len(splits)} parts "
        f"(parts={parts}, max_chunk_tokens={max_chunk_tokens})"
    )

    # 生成部分摘要
    partial_summaries: list[str] = []
    for i, chunk in enumerate(splits, 1):
        logger.debug(f"Summarizing part {i}/{len(splits)} ({len(chunk)} messages)")
        summary = await _summarize_chunk(chunk, llm_client)
        partial_summaries.append(summary)

    # 如果只有一个摘要，直接返回
    if len(partial_summaries) == 1:
        return partial_summaries[0]

    # 合并摘要
    logger.debug(f"Merging {len(partial_summaries)} partial summaries")
    return await _merge_summaries(partial_summaries, llm_client)


async def _summarize_chunk(messages: list[dict], llm_client: LLMClient) -> str:
    """
    摘要单个消息块

    提示词要求:
    1. 关键决策
    2. 重要信息
    3. 未解决的任务或问题
    4. 继续对话所需的上下文
    """
    prompt = """Summarize the following conversation, focusing on:
1. Key decisions made
2. Important information shared
3. Unresolved tasks or questions
4. Context needed for continuing the conversation

Be concise but preserve essential information.

Conversation:
"""
    for msg in messages:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        if isinstance(content, str):
            # 截断长消息以避免超出上下文
            prompt += f"\n{role}: {content[:1000]}"
            if len(content) > 1000:
                prompt += "..."

    response = await llm_client.chat(
        [
            {"role": "system", "content": "You are a conversation summarizer."},
            {"role": "user", "content": prompt},
        ]
    )

    return response.text


async def _merge_summaries(summaries: list[str], llm_client: LLMClient) -> str:
    """
    合并多个摘要

    使用 MERGE_SUMMARIES_INSTRUCTIONS 作为指导
    """
    prompt = f"{MERGE_SUMMARIES_INSTRUCTIONS}\n\nSummaries:\n"
    for i, summary in enumerate(summaries, 1):
        prompt += f"\n--- Part {i} ---\n{summary}\n"

    response = await llm_client.chat(
        [
            {"role": "system", "content": "You are a conversation summarizer."},
            {"role": "user", "content": prompt},
        ]
    )

    return response.text


# ============================================================================
# Main Compaction Entry Point
# ============================================================================


async def compact_messages(
    messages: list[dict],
    context_window: int,
    reserve_tokens: int = 16384,
    llm_client: LLMClient | None = None,
) -> list[dict]:
    """
    压缩消息历史

    对标 MoltBot compactMessages()

    流程:
    1. 检查是否需要压缩
    2. 计算自适应保留比例
    3. 保留最近的消息
    4. 摘要旧消息
    5. 返回 [摘要消息] + [保留的最近消息]

    参数:
    - messages: 消息历史
    - context_window: 上下文窗口大小
    - reserve_tokens: 预留 token (用于系统提示词等)
    - llm_client: LLM 客户端（用于摘要）

    返回:
    - 压缩后的消息列表
    """
    total_tokens = estimate_messages_tokens(messages)

    logger.debug(
        f"Compacting {len(messages)} messages "
        f"({total_tokens} tokens, window={context_window}, reserve={reserve_tokens})"
    )

    # 如果不需要压缩，直接返回
    if total_tokens <= context_window - reserve_tokens:
        logger.debug("No compaction needed")
        return messages

    # 计算自适应比例
    ratio = compute_adaptive_chunk_ratio(messages, context_window)
    logger.debug(f"Adaptive chunk ratio: {ratio:.2f}")

    # 计算要保留的最近消息数量
    target_recent_tokens = int(context_window * ratio)
    recent_messages: list[dict] = []
    recent_tokens = 0

    # 从后向前收集最近的消息
    for msg in reversed(messages):
        msg_tokens = estimate_messages_tokens([msg])
        if recent_tokens + msg_tokens > target_recent_tokens:
            break
        recent_messages.insert(0, msg)
        recent_tokens += msg_tokens

    # 需要压缩的旧消息
    old_messages = messages[: -len(recent_messages)] if recent_messages else messages

    logger.debug(
        f"Splitting: {len(old_messages)} old messages (to summarize), "
        f"{len(recent_messages)} recent messages (to keep)"
    )

    if not llm_client:
        logger.warning("No LLM client provided, returning recent messages only")
        return recent_messages

    # 生成摘要
    summary = await summarize_in_stages(
        messages=old_messages,
        llm_client=llm_client,
        reserve_tokens=reserve_tokens,
        max_chunk_tokens=context_window // 4,
        context_window=context_window,
    )

    # 构建压缩后的消息
    compacted = [
        {"role": "system", "content": f"[Previous conversation summary]\n\n{summary}"}
    ] + recent_messages

    compacted_tokens = estimate_messages_tokens(compacted)
    logger.info(
        f"Compaction complete: {len(messages)} → {len(compacted)} messages, "
        f"{total_tokens} → {compacted_tokens} tokens "
        f"({compacted_tokens/total_tokens*100:.1f}% remaining)"
    )

    return compacted
