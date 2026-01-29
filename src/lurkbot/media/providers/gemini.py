"""
Google Gemini 媒体理解提供商
使用 Google Gemini API 进行多媒体理解
"""

import os
import asyncio
from typing import Optional
from loguru import logger

from ..understand import MediaProvider, MediaType


class GeminiProvider(MediaProvider):
    """Google Gemini 媒体理解提供商"""

    def __init__(self, api_key: Optional[str] = None):
        """
        初始化 Gemini 提供商

        Args:
            api_key: Google API 密钥，如果为 None 则从环境变量获取
        """
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("Google API key is required")

        self._client = None

    @property
    def client(self):
        """延迟初始化 Gemini 客户端"""
        if self._client is None:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
                self._client = genai
            except ImportError:
                raise ImportError("google-generativeai package is required for Gemini provider")
        return self._client

    def supports_type(self, media_type: MediaType) -> bool:
        """检查是否支持指定媒体类型"""
        # Gemini 支持图片、音频、视频和文档
        return media_type in ["image", "audio", "video", "document"]

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
            raise ValueError(f"Gemini provider does not support media type: {media_type}")

        logger.debug(f"Gemini 开始处理 {media_type}: {media_url}")

        try:
            if media_type == "image":
                return await self._understand_image(media_url, model, max_chars)
            elif media_type == "audio":
                return await self._understand_audio(media_url, model, max_chars)
            elif media_type == "video":
                return await self._understand_video(media_url, model, max_chars)
            elif media_type == "document":
                return await self._understand_document(media_url, model, max_chars)
            else:
                raise ValueError(f"Unsupported media type: {media_type}")

        except Exception as e:
            logger.error(f"Gemini 处理失败: {e}")
            raise

    async def _understand_image(self, image_url: str, model: str, max_chars: int) -> str:
        """使用 Gemini Vision 理解图片"""
        try:
            # 下载图片
            import aiohttp
            import tempfile
            import os
            from PIL import Image

            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as response:
                    if response.status != 200:
                        raise ValueError(f"Failed to download image: {response.status}")

                    image_data = await response.read()

            # 保存到临时文件
            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp_file:
                temp_file.write(image_data)
                temp_path = temp_file.name

            try:
                # 上传图片到 Gemini
                uploaded_file = self.client.upload_file(temp_path)

                # 创建模型实例
                model_instance = self.client.GenerativeModel(model)

                # 生成内容
                prompt = f"请详细描述这张图片的内容，包括主要对象、场景、文字等信息。请控制在 {max_chars} 字符以内。"

                response = await asyncio.to_thread(
                    model_instance.generate_content,
                    [prompt, uploaded_file]
                )

                content = response.text
                if not content:
                    raise ValueError("Gemini returned empty response")

                # 确保不超过字符限制
                if len(content) > max_chars:
                    content = content[:max_chars-3] + "..."

                logger.success(f"Gemini 成功处理图片，返回 {len(content)} 字符")
                return content

            finally:
                # 清理临时文件
                if os.path.exists(temp_path):
                    os.unlink(temp_path)

        except Exception as e:
            logger.error(f"Gemini 图片处理失败: {e}")
            raise

    async def _understand_audio(self, audio_url: str, model: str, max_chars: int) -> str:
        """使用 Gemini 理解音频"""
        try:
            # 下载音频文件
            import aiohttp
            import tempfile
            import os

            async with aiohttp.ClientSession() as session:
                async with session.get(audio_url) as response:
                    if response.status != 200:
                        raise ValueError(f"Failed to download audio: {response.status}")

                    audio_data = await response.read()

            # 保存到临时文件
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_file:
                temp_file.write(audio_data)
                temp_path = temp_file.name

            try:
                # 上传音频到 Gemini
                uploaded_file = self.client.upload_file(temp_path)

                # 创建模型实例
                model_instance = self.client.GenerativeModel(model)

                # 生成内容
                prompt = f"请转录并总结这个音频文件的内容，控制在 {max_chars} 字符以内。"

                response = await asyncio.to_thread(
                    model_instance.generate_content,
                    [prompt, uploaded_file]
                )

                content = response.text
                if not content:
                    raise ValueError("Gemini returned empty response")

                # 确保不超过字符限制
                if len(content) > max_chars:
                    content = content[:max_chars-3] + "..."

                logger.success(f"Gemini 成功处理音频，返回 {len(content)} 字符")
                return content

            finally:
                # 清理临时文件
                if os.path.exists(temp_path):
                    os.unlink(temp_path)

        except Exception as e:
            logger.error(f"Gemini 音频处理失败: {e}")
            raise

    async def _understand_video(self, video_url: str, model: str, max_chars: int) -> str:
        """使用 Gemini 理解视频"""
        try:
            # 下载视频文件
            import aiohttp
            import tempfile
            import os

            async with aiohttp.ClientSession() as session:
                async with session.get(video_url) as response:
                    if response.status != 200:
                        raise ValueError(f"Failed to download video: {response.status}")

                    video_data = await response.read()

            # 保存到临时文件
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_file:
                temp_file.write(video_data)
                temp_path = temp_file.name

            try:
                # 上传视频到 Gemini
                uploaded_file = self.client.upload_file(temp_path)

                # 等待文件处理完成
                import time
                while uploaded_file.state.name == "PROCESSING":
                    await asyncio.sleep(1)
                    uploaded_file = self.client.get_file(uploaded_file.name)

                if uploaded_file.state.name == "FAILED":
                    raise ValueError("Video processing failed")

                # 创建模型实例
                model_instance = self.client.GenerativeModel(model)

                # 生成内容
                prompt = f"请描述这个视频的内容，包括主要场景、动作、对话等信息。请控制在 {max_chars} 字符以内。"

                response = await asyncio.to_thread(
                    model_instance.generate_content,
                    [prompt, uploaded_file]
                )

                content = response.text
                if not content:
                    raise ValueError("Gemini returned empty response")

                # 确保不超过字符限制
                if len(content) > max_chars:
                    content = content[:max_chars-3] + "..."

                logger.success(f"Gemini 成功处理视频，返回 {len(content)} 字符")
                return content

            finally:
                # 清理临时文件
                if os.path.exists(temp_path):
                    os.unlink(temp_path)

        except Exception as e:
            logger.error(f"Gemini 视频处理失败: {e}")
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

            # 创建模型实例
            model_instance = self.client.GenerativeModel(model)

            # 生成内容
            prompt = f"请分析以下文档内容并提供摘要，控制在 {max_chars} 字符以内：\n\n{processed_content}"

            response = await asyncio.to_thread(
                model_instance.generate_content,
                prompt
            )

            content = response.text
            if not content:
                raise ValueError("Gemini returned empty response")

            # 确保不超过字符限制
            if len(content) > max_chars:
                content = content[:max_chars-3] + "..."

            logger.success(f"Gemini 成功处理文档，返回 {len(content)} 字符")
            return content

        except Exception as e:
            logger.error(f"Gemini 文档处理失败: {e}")
            raise