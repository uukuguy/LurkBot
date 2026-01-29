"""
Anthropic 媒体理解提供商
使用 Anthropic Claude 进行图片和文档理解
"""

import os
import asyncio
from typing import Optional
from loguru import logger

from ..understand import MediaProvider, MediaType


class AnthropicProvider(MediaProvider):
    """Anthropic 媒体理解提供商"""

    def __init__(self, api_key: Optional[str] = None):
        """
        初始化 Anthropic 提供商

        Args:
            api_key: Anthropic API 密钥，如果为 None 则从环境变量获取
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("Anthropic API key is required")

        self._client = None

    @property
    def client(self):
        """延迟初始化 Anthropic 客户端"""
        if self._client is None:
            try:
                import anthropic
                self._client = anthropic.AsyncAnthropic(api_key=self.api_key)
            except ImportError:
                raise ImportError("anthropic package is required for Anthropic provider")
        return self._client

    def supports_type(self, media_type: MediaType) -> bool:
        """检查是否支持指定媒体类型"""
        # Anthropic 支持图片和文档，不支持音频和视频
        return media_type in ["image", "document"]

    async def understand(
        self,
        media_url: str,
        media_type: MediaType,
        model: str,
        max_chars: int,
    ) -> str:
        """
        理解媒体内容并返回摘要

        Args:
            media_url: 媒体文件URL
            media_type: 媒体类型
            model: 使用的模型名称
            max_chars: 最大字符数限制

        Returns:
            str: 媒体内容摘要

        Raises:
            ValueError: 不支持的媒体类型
            Exception: API 调用失败
        """
        if not self.supports_type(media_type):
            raise ValueError(f"Anthropic provider does not support media type: {media_type}")

        logger.debug(f"Anthropic 开始处理 {media_type}: {media_url}")

        try:
            if media_type == "image":
                return await self._understand_image(media_url, model, max_chars)
            elif media_type == "document":
                return await self._understand_document(media_url, model, max_chars)
            else:
                raise ValueError(f"Unsupported media type: {media_type}")

        except Exception as e:
            logger.error(f"Anthropic 处理失败: {e}")
            raise

    async def _understand_image(self, image_url: str, model: str, max_chars: int) -> str:
        """使用 Claude Vision 理解图片"""
        try:
            # 下载图片并转换为 base64
            import aiohttp
            import base64

            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as response:
                    if response.status != 200:
                        raise ValueError(f"Failed to download image: {response.status}")

                    image_data = await response.read()
                    content_type = response.headers.get('content-type', 'image/jpeg')

            # 转换为 base64
            image_base64 = base64.b64encode(image_data).decode('utf-8')

            # 确定图片格式
            if 'png' in content_type:
                media_type = "image/png"
            elif 'gif' in content_type:
                media_type = "image/gif"
            elif 'webp' in content_type:
                media_type = "image/webp"
            else:
                media_type = "image/jpeg"

            # 调用 Claude API
            response = await self.client.messages.create(
                model=model,
                max_tokens=max_chars // 2,  # 估算 token 数量
                temperature=0.1,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": media_type,
                                    "data": image_base64
                                }
                            },
                            {
                                "type": "text",
                                "text": f"请详细描述这张图片的内容，包括主要对象、场景、文字等信息。请控制在 {max_chars} 字符以内。"
                            }
                        ]
                    }
                ]
            )

            content = response.content[0].text if response.content else ""
            if not content:
                raise ValueError("Anthropic returned empty response")

            # 确保不超过字符限制
            if len(content) > max_chars:
                content = content[:max_chars-3] + "..."

            logger.success(f"Anthropic 成功处理图片，返回 {len(content)} 字符")
            return content

        except Exception as e:
            logger.error(f"Anthropic 图片处理失败: {e}")
            raise

    async def _understand_document(self, doc_url: str, model: str, max_chars: int) -> str:
        """理解文档内容"""
        try:
            # 下载文档内容
            import aiohttp

            async with aiohttp.ClientSession() as session:
                async with session.get(doc_url) as response:
                    if response.status != 200:
                        raise ValueError(f"Failed to download document: {response.status}")

                    content_type = response.headers.get('content-type', '').lower()
                    content = await response.text()

            # 根据内容类型处理
            if 'pdf' in content_type:
                # PDF 需要特殊处理，这里简化为文本提取
                processed_content = f"PDF 文档内容: {content[:2000]}..."
            else:
                # 纯文本或其他格式
                processed_content = content[:2000]  # 限制输入长度

            # 使用 Claude 分析文档
            response = await self.client.messages.create(
                model=model,
                max_tokens=max_chars // 2,
                temperature=0.1,
                messages=[
                    {
                        "role": "user",
                        "content": f"请分析以下文档内容并提供摘要，控制在 {max_chars} 字符以内：\n\n{processed_content}"
                    }
                ]
            )

            content = response.content[0].text if response.content else ""
            if not content:
                raise ValueError("Anthropic returned empty response")

            # 确保不超过字符限制
            if len(content) > max_chars:
                content = content[:max_chars-3] + "..."

            logger.success(f"Anthropic 成功处理文档，返回 {len(content)} 字符")
            return content

        except Exception as e:
            logger.error(f"Anthropic 文档处理失败: {e}")
            raise