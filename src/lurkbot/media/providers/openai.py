"""
OpenAI 媒体理解提供商
使用 OpenAI GPT-4 Vision 和 Whisper API 进行媒体理解
"""

import os
import asyncio
from typing import Optional
from loguru import logger

from ..understand import MediaProvider, MediaType


class OpenAIProvider(MediaProvider):
    """OpenAI 媒体理解提供商"""

    def __init__(self, api_key: Optional[str] = None):
        """
        初始化 OpenAI 提供商

        Args:
            api_key: OpenAI API 密钥，如果为 None 则从环境变量获取
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key is required")

        self._client = None

    @property
    def client(self):
        """延迟初始化 OpenAI 客户端"""
        if self._client is None:
            try:
                import openai
                self._client = openai.AsyncOpenAI(api_key=self.api_key)
            except ImportError:
                raise ImportError("openai package is required for OpenAI provider")
        return self._client

    def supports_type(self, media_type: MediaType) -> bool:
        """检查是否支持指定媒体类型"""
        # OpenAI 支持图片 (GPT-4 Vision)、音频 (Whisper) 和文档
        return media_type in ["image", "audio", "document"]

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
            raise ValueError(f"OpenAI provider does not support media type: {media_type}")

        logger.debug(f"OpenAI 开始处理 {media_type}: {media_url}")

        try:
            if media_type == "image":
                return await self._understand_image(media_url, model, max_chars)
            elif media_type == "audio":
                return await self._understand_audio(media_url, model, max_chars)
            elif media_type == "document":
                return await self._understand_document(media_url, model, max_chars)
            else:
                raise ValueError(f"Unsupported media type: {media_type}")

        except Exception as e:
            logger.error(f"OpenAI 处理失败: {e}")
            raise

    async def _understand_image(self, image_url: str, model: str, max_chars: int) -> str:
        """使用 GPT-4 Vision 理解图片"""
        try:
            response = await self.client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": f"请详细描述这张图片的内容，包括主要对象、场景、文字等信息。请控制在 {max_chars} 字符以内。"
                            },
                            {
                                "type": "image_url",
                                "image_url": {"url": image_url}
                            }
                        ]
                    }
                ],
                max_tokens=max_chars // 2,  # 估算 token 数量
                temperature=0.1,
            )

            content = response.choices[0].message.content
            if not content:
                raise ValueError("OpenAI returned empty response")

            # 确保不超过字符限制
            if len(content) > max_chars:
                content = content[:max_chars-3] + "..."

            logger.success(f"OpenAI 成功处理图片，返回 {len(content)} 字符")
            return content

        except Exception as e:
            logger.error(f"OpenAI 图片处理失败: {e}")
            raise

    async def _understand_audio(self, audio_url: str, model: str, max_chars: int) -> str:
        """使用 Whisper API 理解音频"""
        try:
            # 下载音频文件
            import aiohttp
            import tempfile
            import os

            async with aiohttp.ClientSession() as session:
                async with session.get(audio_url) as response:
                    if response.status != 200:
                        raise ValueError(f"Failed to download audio: {response.status}")

                    # 保存到临时文件
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_file:
                        temp_file.write(await response.read())
                        temp_path = temp_file.name

            try:
                # 使用 Whisper 转录音频
                with open(temp_path, "rb") as audio_file:
                    transcript = await self.client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file,
                        response_format="text"
                    )

                # 如果转录结果太长，使用 GPT 进行摘要
                if len(transcript) > max_chars:
                    summary_response = await self.client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {
                                "role": "user",
                                "content": f"请将以下音频转录内容总结为 {max_chars} 字符以内的摘要：\n\n{transcript}"
                            }
                        ],
                        max_tokens=max_chars // 2,
                        temperature=0.1,
                    )
                    content = summary_response.choices[0].message.content or transcript[:max_chars-3] + "..."
                else:
                    content = transcript

                logger.success(f"OpenAI 成功处理音频，返回 {len(content)} 字符")
                return content

            finally:
                # 清理临时文件
                if os.path.exists(temp_path):
                    os.unlink(temp_path)

        except Exception as e:
            logger.error(f"OpenAI 音频处理失败: {e}")
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

            # 使用 GPT 分析文档
            response = await self.client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "user",
                        "content": f"请分析以下文档内容并提供摘要，控制在 {max_chars} 字符以内：\n\n{processed_content}"
                    }
                ],
                max_tokens=max_chars // 2,
                temperature=0.1,
            )

            content = response.choices[0].message.content
            if not content:
                raise ValueError("OpenAI returned empty response")

            # 确保不超过字符限制
            if len(content) > max_chars:
                content = content[:max_chars-3] + "..."

            logger.success(f"OpenAI 成功处理文档，返回 {len(content)} 字符")
            return content

        except Exception as e:
            logger.error(f"OpenAI 文档处理失败: {e}")
            raise