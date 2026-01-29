"""
Media Understanding 核心理解逻辑
在消息进入回复流水线前，自动理解和摘要化入站多媒体
"""

from dataclasses import dataclass
from typing import Literal, Protocol, runtime_checkable
import asyncio
from loguru import logger

MediaType = Literal["image", "audio", "video", "document"]


@dataclass
class MediaUnderstandingResult:
    """媒体理解结果"""
    success: bool
    summary: str | None = None
    error: str | None = None
    provider_used: str | None = None


@runtime_checkable
class MediaProvider(Protocol):
    """媒体提供商协议"""

    async def understand(
        self,
        media_url: str,
        media_type: MediaType,
        model: str,
        max_chars: int,
    ) -> str:
        """理解媒体内容并返回摘要"""
        ...

    def supports_type(self, media_type: MediaType) -> bool:
        """检查是否支持指定媒体类型"""
        ...


async def understand_media(
    media_url: str,
    media_type: MediaType,
    config: "MediaConfig",
) -> MediaUnderstandingResult:
    """
    理解多媒体内容

    流程:
    1. 按能力过滤提供商
    2. 选择第一个合格模型
    3. 执行理解任务
    4. 若失败 → 降级到下一个

    Args:
        media_url: 媒体文件URL
        media_type: 媒体类型
        config: 媒体配置

    Returns:
        MediaUnderstandingResult: 理解结果
    """
    logger.info(f"开始理解媒体: {media_url} (类型: {media_type})")

    # 获取支持该媒体类型的提供商配置
    provider_configs = config.get_providers_for_type(media_type)
    if not provider_configs:
        logger.warning(f"没有找到支持 {media_type} 类型的提供商")
        return MediaUnderstandingResult(
            success=False,
            error=f"No providers available for media type: {media_type}",
        )

    # 按优先级尝试每个提供商
    for provider_config in provider_configs:
        try:
            logger.debug(f"尝试使用提供商: {provider_config.provider}")

            # 获取提供商实例
            provider = get_provider(provider_config.provider)
            if not provider:
                logger.warning(f"提供商 {provider_config.provider} 不可用")
                continue

            # 检查提供商是否支持该媒体类型
            if not provider.supports_type(media_type):
                logger.warning(f"提供商 {provider_config.provider} 不支持 {media_type}")
                continue

            # 执行理解任务
            summary = await provider.understand(
                media_url=media_url,
                media_type=media_type,
                model=provider_config.model,
                max_chars=config.get_max_chars(media_type),
            )

            logger.success(f"成功使用 {provider_config.provider} 理解媒体")
            return MediaUnderstandingResult(
                success=True,
                summary=summary,
                provider_used=provider_config.provider,
            )

        except Exception as e:
            logger.warning(f"提供商 {provider_config.provider} 失败: {e}")
            continue  # 降级到下一个提供商

    # 所有提供商都失败了
    logger.error("所有提供商都无法理解该媒体")
    return MediaUnderstandingResult(
        success=False,
        error="All providers failed to understand the media",
    )


def get_provider(provider_name: str) -> MediaProvider | None:
    """
    获取媒体提供商实例

    Args:
        provider_name: 提供商名称 (openai, anthropic, gemini, local)

    Returns:
        MediaProvider | None: 提供商实例或None
    """
    try:
        if provider_name == "openai":
            from .providers.openai import OpenAIProvider
            return OpenAIProvider()
        elif provider_name == "anthropic":
            from .providers.anthropic import AnthropicProvider
            return AnthropicProvider()
        elif provider_name == "gemini":
            from .providers.gemini import GeminiProvider
            return GeminiProvider()
        elif provider_name == "local":
            from .providers.local import LocalProvider
            return LocalProvider()
        else:
            logger.error(f"未知的提供商: {provider_name}")
            return None
    except ImportError as e:
        logger.warning(f"无法导入提供商 {provider_name}: {e}")
        return None


async def batch_understand_media(
    media_items: list[tuple[str, MediaType]],
    config: "MediaConfig",
    max_concurrent: int = 3,
) -> list[MediaUnderstandingResult]:
    """
    批量理解多个媒体文件

    Args:
        media_items: 媒体项目列表 [(url, type), ...]
        config: 媒体配置
        max_concurrent: 最大并发数

    Returns:
        list[MediaUnderstandingResult]: 理解结果列表
    """
    logger.info(f"开始批量理解 {len(media_items)} 个媒体文件")

    semaphore = asyncio.Semaphore(max_concurrent)

    async def understand_with_semaphore(media_url: str, media_type: MediaType):
        async with semaphore:
            return await understand_media(media_url, media_type, config)

    tasks = [
        understand_with_semaphore(url, media_type)
        for url, media_type in media_items
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # 处理异常结果
    processed_results = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error(f"批量处理第 {i} 项时出错: {result}")
            processed_results.append(MediaUnderstandingResult(
                success=False,
                error=str(result),
            ))
        else:
            processed_results.append(result)

    logger.info(f"批量理解完成，成功: {sum(1 for r in processed_results if r.success)}/{len(processed_results)}")
    return processed_results