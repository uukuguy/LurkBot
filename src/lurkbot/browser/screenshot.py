"""
Screenshot - 截图处理模块

对标 MoltBot src/browser/screenshot.ts
"""

from __future__ import annotations

import base64
import io
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from loguru import logger

from .playwright_session import PlaywrightSession, get_session
from .types import BrowserNotConnectedError, ScreenshotRequest, ScreenshotResponse

# PIL 导入（可选依赖）
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    Image = Any


# ============================================================================
# Screenshot Options
# ============================================================================

@dataclass
class ScreenshotOptions:
    """截图选项"""
    full_page: bool = False
    selector: str | None = None
    format: str = "png"  # png | jpeg
    quality: int | None = None  # 0-100, only for jpeg
    omit_background: bool = False
    scale: str = "device"  # css | device
    clip: dict | None = None  # {"x": int, "y": int, "width": int, "height": int}
    mask: list[str] | None = None  # 要遮罩的选择器列表
    animations: str = "disabled"  # disabled | allow
    caret: str = "hide"  # hide | initial


# ============================================================================
# Screenshot Capture
# ============================================================================

async def capture_screenshot(
    session: PlaywrightSession | None = None,
    options: ScreenshotOptions | None = None,
) -> bytes:
    """
    捕获截图

    Args:
        session: Playwright 会话
        options: 截图选项

    Returns:
        图片数据（bytes）
    """
    if session is None:
        session = await get_session()

    page = session.page
    if not page:
        raise BrowserNotConnectedError()

    opts = options or ScreenshotOptions()

    # 构建 Playwright 选项
    playwright_options = {
        "type": opts.format,
        "omit_background": opts.omit_background,
        "scale": opts.scale,
        "animations": opts.animations,
        "caret": opts.caret,
    }

    if opts.format == "jpeg" and opts.quality:
        playwright_options["quality"] = opts.quality

    if opts.clip:
        playwright_options["clip"] = opts.clip

    # 处理遮罩
    if opts.mask:
        mask_locators = [page.locator(sel) for sel in opts.mask]
        playwright_options["mask"] = mask_locators

    # 执行截图
    if opts.selector:
        element = page.locator(opts.selector)
        return await element.screenshot(**playwright_options)
    else:
        playwright_options["full_page"] = opts.full_page
        return await page.screenshot(**playwright_options)


async def capture_screenshot_base64(
    session: PlaywrightSession | None = None,
    options: ScreenshotOptions | None = None,
) -> str:
    """
    捕获截图并返回 Base64 编码

    Args:
        session: Playwright 会话
        options: 截图选项

    Returns:
        Base64 编码的图片数据
    """
    data = await capture_screenshot(session, options)
    return base64.b64encode(data).decode("utf-8")


async def capture_screenshot_response(
    session: PlaywrightSession | None = None,
    request: ScreenshotRequest | None = None,
) -> ScreenshotResponse:
    """
    捕获截图并返回响应对象

    Args:
        session: Playwright 会话
        request: 截图请求

    Returns:
        ScreenshotResponse
    """
    req = request or ScreenshotRequest()

    options = ScreenshotOptions(
        full_page=req.full_page,
        selector=req.selector,
        format=req.format,
        quality=req.quality,
        omit_background=req.omit_background,
        scale=req.scale,
    )

    try:
        data = await capture_screenshot(session, options)
        data_base64 = base64.b64encode(data).decode("utf-8")

        # 获取图片尺寸
        width, height = 0, 0
        if PIL_AVAILABLE:
            img = Image.open(io.BytesIO(data))
            width, height = img.size

        return ScreenshotResponse(
            success=True,
            format=req.format,
            width=width,
            height=height,
            data=data_base64,
        )

    except Exception as e:
        logger.error(f"Screenshot capture failed: {e}")
        return ScreenshotResponse(
            success=False,
            format=req.format,
            error=str(e),
        )


async def save_screenshot(
    path: str | Path,
    session: PlaywrightSession | None = None,
    options: ScreenshotOptions | None = None,
) -> bool:
    """
    捕获截图并保存到文件

    Args:
        path: 保存路径
        session: Playwright 会话
        options: 截图选项

    Returns:
        是否成功
    """
    try:
        data = await capture_screenshot(session, options)
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        logger.info(f"Screenshot saved to: {path}")
        return True
    except Exception as e:
        logger.error(f"Failed to save screenshot: {e}")
        return False


# ============================================================================
# Image Processing
# ============================================================================

def resize_image(
    data: bytes,
    max_width: int | None = None,
    max_height: int | None = None,
    quality: int = 85,
) -> bytes:
    """
    调整图片大小

    Args:
        data: 原始图片数据
        max_width: 最大宽度
        max_height: 最大高度
        quality: 输出质量（仅 JPEG）

    Returns:
        调整后的图片数据
    """
    if not PIL_AVAILABLE:
        logger.warning("PIL not available, returning original image")
        return data

    img = Image.open(io.BytesIO(data))
    original_width, original_height = img.size

    # 计算新尺寸
    new_width, new_height = original_width, original_height

    if max_width and original_width > max_width:
        ratio = max_width / original_width
        new_width = max_width
        new_height = int(original_height * ratio)

    if max_height and new_height > max_height:
        ratio = max_height / new_height
        new_height = max_height
        new_width = int(new_width * ratio)

    # 如果不需要调整
    if new_width == original_width and new_height == original_height:
        return data

    # 调整大小
    img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

    # 输出
    output = io.BytesIO()
    img_format = img.format or "PNG"
    if img_format.upper() == "JPEG":
        img.save(output, format=img_format, quality=quality)
    else:
        img.save(output, format=img_format)

    return output.getvalue()


def crop_image(
    data: bytes,
    x: int,
    y: int,
    width: int,
    height: int,
) -> bytes:
    """
    裁剪图片

    Args:
        data: 原始图片数据
        x: 左上角 X 坐标
        y: 左上角 Y 坐标
        width: 宽度
        height: 高度

    Returns:
        裁剪后的图片数据
    """
    if not PIL_AVAILABLE:
        raise ImportError("PIL is required for image cropping")

    img = Image.open(io.BytesIO(data))
    cropped = img.crop((x, y, x + width, y + height))

    output = io.BytesIO()
    img_format = img.format or "PNG"
    cropped.save(output, format=img_format)

    return output.getvalue()


def add_highlight_box(
    data: bytes,
    x: int,
    y: int,
    width: int,
    height: int,
    color: tuple = (255, 0, 0),
    line_width: int = 3,
) -> bytes:
    """
    在图片上添加高亮框

    Args:
        data: 原始图片数据
        x: 左上角 X 坐标
        y: 左上角 Y 坐标
        width: 宽度
        height: 高度
        color: 框颜色 (R, G, B)
        line_width: 线宽

    Returns:
        添加高亮框后的图片数据
    """
    if not PIL_AVAILABLE:
        raise ImportError("PIL is required for image annotation")

    from PIL import ImageDraw

    img = Image.open(io.BytesIO(data))
    draw = ImageDraw.Draw(img)

    # 绘制矩形框
    draw.rectangle(
        [x, y, x + width, y + height],
        outline=color,
        width=line_width,
    )

    output = io.BytesIO()
    img_format = img.format or "PNG"
    img.save(output, format=img_format)

    return output.getvalue()


def add_annotation(
    data: bytes,
    text: str,
    x: int,
    y: int,
    color: tuple = (255, 0, 0),
    font_size: int = 16,
) -> bytes:
    """
    在图片上添加文本注释

    Args:
        data: 原始图片数据
        text: 注释文本
        x: X 坐标
        y: Y 坐标
        color: 文本颜色 (R, G, B)
        font_size: 字体大小

    Returns:
        添加注释后的图片数据
    """
    if not PIL_AVAILABLE:
        raise ImportError("PIL is required for image annotation")

    from PIL import ImageDraw, ImageFont

    img = Image.open(io.BytesIO(data))
    draw = ImageDraw.Draw(img)

    # 尝试使用默认字体
    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except Exception:
        font = ImageFont.load_default()

    draw.text((x, y), text, fill=color, font=font)

    output = io.BytesIO()
    img_format = img.format or "PNG"
    img.save(output, format=img_format)

    return output.getvalue()


def image_to_data_url(
    data: bytes,
    format: str = "png",
) -> str:
    """
    将图片数据转换为 Data URL

    Args:
        data: 图片数据
        format: 图片格式

    Returns:
        Data URL
    """
    mime_type = f"image/{format}"
    base64_data = base64.b64encode(data).decode("utf-8")
    return f"data:{mime_type};base64,{base64_data}"


def data_url_to_image(data_url: str) -> bytes:
    """
    将 Data URL 转换为图片数据

    Args:
        data_url: Data URL

    Returns:
        图片数据
    """
    if not data_url.startswith("data:"):
        raise ValueError("Invalid data URL")

    # 解析 data URL
    header, data = data_url.split(",", 1)
    return base64.b64decode(data)


def get_image_info(data: bytes) -> dict[str, Any]:
    """
    获取图片信息

    Args:
        data: 图片数据

    Returns:
        图片信息字典
    """
    if not PIL_AVAILABLE:
        return {
            "size_bytes": len(data),
            "pil_available": False,
        }

    img = Image.open(io.BytesIO(data))

    return {
        "width": img.width,
        "height": img.height,
        "format": img.format,
        "mode": img.mode,
        "size_bytes": len(data),
        "pil_available": True,
    }


# ============================================================================
# Comparison
# ============================================================================

def compare_screenshots(
    data1: bytes,
    data2: bytes,
    threshold: float = 0.05,
) -> dict[str, Any]:
    """
    比较两张截图

    Args:
        data1: 第一张图片数据
        data2: 第二张图片数据
        threshold: 差异阈值（0-1）

    Returns:
        比较结果
    """
    if not PIL_AVAILABLE:
        raise ImportError("PIL is required for image comparison")

    import numpy as np

    img1 = Image.open(io.BytesIO(data1))
    img2 = Image.open(io.BytesIO(data2))

    # 确保尺寸相同
    if img1.size != img2.size:
        return {
            "identical": False,
            "reason": "size_mismatch",
            "size1": img1.size,
            "size2": img2.size,
        }

    # 转换为 numpy 数组
    arr1 = np.array(img1)
    arr2 = np.array(img2)

    # 计算差异
    diff = np.abs(arr1.astype(float) - arr2.astype(float))
    max_diff = diff.max()
    mean_diff = diff.mean()
    diff_ratio = np.count_nonzero(diff) / diff.size

    identical = diff_ratio < threshold

    return {
        "identical": identical,
        "diff_ratio": diff_ratio,
        "max_diff": float(max_diff),
        "mean_diff": float(mean_diff),
        "threshold": threshold,
    }


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    "PIL_AVAILABLE",
    "ScreenshotOptions",
    "capture_screenshot",
    "capture_screenshot_base64",
    "capture_screenshot_response",
    "save_screenshot",
    "resize_image",
    "crop_image",
    "add_highlight_box",
    "add_annotation",
    "image_to_data_url",
    "data_url_to_image",
    "get_image_info",
    "compare_screenshots",
]
