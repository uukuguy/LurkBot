"""
本地媒体理解提供商
使用本地工具和库进行基础媒体处理
"""

import os
import subprocess
import shutil
from typing import Dict, Any, Optional, List
import logging
from pathlib import Path

from ..understand import MediaProvider, MediaUnderstandingResult

logger = logging.getLogger(__name__)


class LocalProvider(MediaProvider):
    """
    本地媒体理解提供商
    使用本地安装的工具进行基础媒体分析
    """

    def __init__(self):
        """初始化本地提供商"""
        self.available_tools = self._check_available_tools()
        logger.info(f"本地提供商初始化完成，可用工具: {list(self.available_tools.keys())}")

    def _check_available_tools(self) -> Dict[str, bool]:
        """检查本地可用的工具"""
        tools = {}

        # 检查 Python 库
        try:
            import PIL
            tools['PIL'] = True
        except ImportError:
            tools['PIL'] = False

        try:
            import cv2
            tools['opencv'] = True
        except ImportError:
            tools['opencv'] = False

        try:
            import eyed3
            tools['eyed3'] = True
        except ImportError:
            tools['eyed3'] = False

        try:
            import PyPDF2
            tools['PyPDF2'] = True
        except ImportError:
            tools['PyPDF2'] = False

        # 检查系统工具
        tools['ffmpeg'] = shutil.which('ffmpeg') is not None
        tools['file'] = shutil.which('file') is not None
        tools['exiftool'] = shutil.which('exiftool') is not None

        return tools

    def supports_type(self, media_type: str) -> bool:
        """检查是否支持指定的媒体类型"""
        support_map = {
            "image": self.available_tools.get('PIL', False) or self.available_tools.get('opencv', False),
            "audio": self.available_tools.get('eyed3', False) or self.available_tools.get('ffmpeg', False),
            "video": self.available_tools.get('ffmpeg', False),
            "document": self.available_tools.get('PyPDF2', False) or self.available_tools.get('file', False),
        }
        return support_map.get(media_type, False)

    async def understand(
        self,
        media_url: str,
        media_type: str,
        prompt: str = "请描述这个媒体文件的内容",
        **kwargs
    ) -> str:
        """
        使用本地工具理解媒体内容

        Args:
            media_url: 媒体文件URL或路径
            media_type: 媒体类型
            prompt: 分析提示（本地提供商会忽略此参数）
            **kwargs: 其他参数

        Returns:
            分析结果字符串
        """
        if not self.supports_type(media_type):
            raise ValueError(f"本地提供商不支持媒体类型: {media_type}")

        try:
            if media_type == "image":
                return await self._analyze_image(media_url)
            elif media_type == "audio":
                return await self._analyze_audio(media_url)
            elif media_type == "video":
                return await self._analyze_video(media_url)
            elif media_type == "document":
                return await self._analyze_document(media_url)
            else:
                return f"不支持的媒体类型: {media_type}"

        except Exception as e:
            logger.error(f"本地分析失败: {e}")
            raise

    async def _analyze_image(self, image_path: str) -> str:
        """分析图片文件"""
        results = []

        # 使用 file 命令获取基本信息
        if self.available_tools.get('file'):
            try:
                result = subprocess.run(
                    ['file', image_path],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0:
                    results.append(f"文件类型: {result.stdout.strip()}")
            except Exception as e:
                logger.warning(f"file 命令执行失败: {e}")

        # 使用 PIL 获取图片信息
        if self.available_tools.get('PIL'):
            try:
                from PIL import Image
                with Image.open(image_path) as img:
                    results.append(f"图片尺寸: {img.size[0]}x{img.size[1]}")
                    results.append(f"图片模式: {img.mode}")
                    results.append(f"图片格式: {img.format}")

                    # 获取颜色统计
                    if img.mode in ['RGB', 'RGBA']:
                        colors = img.getcolors(maxcolors=256*256*256)
                        if colors:
                            dominant_color = max(colors, key=lambda x: x[0])
                            results.append(f"主要颜色信息: 出现 {dominant_color[0]} 次")
            except Exception as e:
                logger.warning(f"PIL 分析失败: {e}")

        # 使用 exiftool 获取元数据
        if self.available_tools.get('exiftool'):
            try:
                result = subprocess.run(
                    ['exiftool', '-j', image_path],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0:
                    import json
                    metadata = json.loads(result.stdout)[0]
                    if 'CreateDate' in metadata:
                        results.append(f"创建时间: {metadata['CreateDate']}")
                    if 'Make' in metadata and 'Model' in metadata:
                        results.append(f"设备信息: {metadata['Make']} {metadata['Model']}")
            except Exception as e:
                logger.warning(f"exiftool 执行失败: {e}")

        if not results:
            results.append("无法获取图片信息")

        return "图片分析结果:\n" + "\n".join(f"- {result}" for result in results)

    async def _analyze_audio(self, audio_path: str) -> str:
        """分析音频文件"""
        results = []

        # 使用 file 命令获取基本信息
        if self.available_tools.get('file'):
            try:
                result = subprocess.run(
                    ['file', audio_path],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0:
                    results.append(f"文件类型: {result.stdout.strip()}")
            except Exception as e:
                logger.warning(f"file 命令执行失败: {e}")

        # 使用 ffmpeg 获取音频信息
        if self.available_tools.get('ffmpeg'):
            try:
                result = subprocess.run(
                    ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', '-show_streams', audio_path],
                    capture_output=True,
                    text=True,
                    timeout=15
                )
                if result.returncode == 0:
                    import json
                    data = json.loads(result.stdout)

                    if 'format' in data:
                        format_info = data['format']
                        if 'duration' in format_info:
                            duration = float(format_info['duration'])
                            results.append(f"时长: {duration:.2f} 秒")
                        if 'bit_rate' in format_info:
                            results.append(f"比特率: {format_info['bit_rate']} bps")

                    if 'streams' in data:
                        for stream in data['streams']:
                            if stream.get('codec_type') == 'audio':
                                if 'codec_name' in stream:
                                    results.append(f"音频编码: {stream['codec_name']}")
                                if 'sample_rate' in stream:
                                    results.append(f"采样率: {stream['sample_rate']} Hz")
                                if 'channels' in stream:
                                    results.append(f"声道数: {stream['channels']}")
                                break
            except Exception as e:
                logger.warning(f"ffprobe 执行失败: {e}")

        # 使用 eyed3 获取 MP3 标签信息
        if self.available_tools.get('eyed3') and audio_path.lower().endswith('.mp3'):
            try:
                import eyed3
                audiofile = eyed3.load(audio_path)
                if audiofile and audiofile.tag:
                    tag = audiofile.tag
                    if tag.title:
                        results.append(f"标题: {tag.title}")
                    if tag.artist:
                        results.append(f"艺术家: {tag.artist}")
                    if tag.album:
                        results.append(f"专辑: {tag.album}")
                    if tag.recording_date:
                        results.append(f"录制日期: {tag.recording_date}")
            except Exception as e:
                logger.warning(f"eyed3 分析失败: {e}")

        if not results:
            results.append("无法获取音频信息")

        return "音频分析结果:\n" + "\n".join(f"- {result}" for result in results)

    async def _analyze_video(self, video_path: str) -> str:
        """分析视频文件"""
        results = []

        # 使用 file 命令获取基本信息
        if self.available_tools.get('file'):
            try:
                result = subprocess.run(
                    ['file', video_path],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0:
                    results.append(f"文件类型: {result.stdout.strip()}")
            except Exception as e:
                logger.warning(f"file 命令执行失败: {e}")

        # 使用 ffmpeg 获取视频信息
        if self.available_tools.get('ffmpeg'):
            try:
                result = subprocess.run(
                    ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', '-show_streams', video_path],
                    capture_output=True,
                    text=True,
                    timeout=20
                )
                if result.returncode == 0:
                    import json
                    data = json.loads(result.stdout)

                    if 'format' in data:
                        format_info = data['format']
                        if 'duration' in format_info:
                            duration = float(format_info['duration'])
                            results.append(f"时长: {duration:.2f} 秒")
                        if 'bit_rate' in format_info:
                            results.append(f"比特率: {format_info['bit_rate']} bps")
                        if 'size' in format_info:
                            size_mb = int(format_info['size']) / (1024 * 1024)
                            results.append(f"文件大小: {size_mb:.2f} MB")

                    if 'streams' in data:
                        for stream in data['streams']:
                            if stream.get('codec_type') == 'video':
                                if 'codec_name' in stream:
                                    results.append(f"视频编码: {stream['codec_name']}")
                                if 'width' in stream and 'height' in stream:
                                    results.append(f"分辨率: {stream['width']}x{stream['height']}")
                                if 'r_frame_rate' in stream:
                                    fps = stream['r_frame_rate']
                                    if '/' in fps:
                                        num, den = fps.split('/')
                                        fps_val = float(num) / float(den)
                                        results.append(f"帧率: {fps_val:.2f} fps")
                            elif stream.get('codec_type') == 'audio':
                                if 'codec_name' in stream:
                                    results.append(f"音频编码: {stream['codec_name']}")
                                if 'sample_rate' in stream:
                                    results.append(f"音频采样率: {stream['sample_rate']} Hz")
            except Exception as e:
                logger.warning(f"ffprobe 执行失败: {e}")

        if not results:
            results.append("无法获取视频信息")

        return "视频分析结果:\n" + "\n".join(f"- {result}" for result in results)

    async def _analyze_document(self, doc_path: str) -> str:
        """分析文档文件"""
        results = []

        # 使用 file 命令获取基本信息
        if self.available_tools.get('file'):
            try:
                result = subprocess.run(
                    ['file', doc_path],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0:
                    results.append(f"文件类型: {result.stdout.strip()}")
            except Exception as e:
                logger.warning(f"file 命令执行失败: {e}")

        # 获取文件大小
        try:
            file_size = os.path.getsize(doc_path)
            if file_size < 1024:
                results.append(f"文件大小: {file_size} 字节")
            elif file_size < 1024 * 1024:
                results.append(f"文件大小: {file_size / 1024:.2f} KB")
            else:
                results.append(f"文件大小: {file_size / (1024 * 1024):.2f} MB")
        except Exception as e:
            logger.warning(f"获取文件大小失败: {e}")

        # 分析 PDF 文件
        if self.available_tools.get('PyPDF2') and doc_path.lower().endswith('.pdf'):
            try:
                import PyPDF2
                with open(doc_path, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    results.append(f"PDF 页数: {len(pdf_reader.pages)}")

                    # 获取元数据
                    if pdf_reader.metadata:
                        metadata = pdf_reader.metadata
                        if metadata.get('/Title'):
                            results.append(f"标题: {metadata['/Title']}")
                        if metadata.get('/Author'):
                            results.append(f"作者: {metadata['/Author']}")
                        if metadata.get('/Creator'):
                            results.append(f"创建者: {metadata['/Creator']}")

                    # 尝试提取第一页的文本（前100个字符）
                    if len(pdf_reader.pages) > 0:
                        first_page = pdf_reader.pages[0]
                        text = first_page.extract_text()
                        if text:
                            preview = text.strip()[:100]
                            if preview:
                                results.append(f"内容预览: {preview}...")
            except Exception as e:
                logger.warning(f"PDF 分析失败: {e}")

        # 分析文本文件
        if doc_path.lower().endswith(('.txt', '.md', '.py', '.js', '.html', '.css', '.json', '.xml')):
            try:
                with open(doc_path, 'r', encoding='utf-8', errors='ignore') as file:
                    content = file.read()
                    lines = content.split('\n')
                    results.append(f"行数: {len(lines)}")
                    results.append(f"字符数: {len(content)}")

                    # 内容预览
                    preview = content.strip()[:100]
                    if preview:
                        results.append(f"内容预览: {preview}...")
            except Exception as e:
                logger.warning(f"文本文件分析失败: {e}")

        if not results:
            results.append("无法获取文档信息")

        return "文档分析结果:\n" + "\n".join(f"- {result}" for result in results)

    def get_model_for_type(self, media_type: str) -> str:
        """获取用于指定媒体类型的模型名称"""
        return "local-tools"

    def __str__(self) -> str:
        return f"LocalProvider(available_tools={list(self.available_tools.keys())})"