"""Image tool for image understanding and generation.

Ported from moltbot/src/agents/tools/image-tool.ts

This tool provides image capabilities:
- Image understanding (analyze images, extract text, describe content)
- Image generation (via DALL-E or other providers)
- Image manipulation (resize, crop, convert)

Note: Full functionality requires external API integration.
"""

from __future__ import annotations

import base64
import io
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from lurkbot.tools.builtin.common import (
    ToolResult,
    ToolResultContent,
    ToolResultContentType,
    error_result,
    image_result,
    json_result,
    text_result,
)


# =============================================================================
# Type Definitions
# =============================================================================


class ImageUnderstandParams(BaseModel):
    """Parameters for understanding/analyzing an image."""

    path: str | None = None
    url: str | None = None
    base64: str | None = None
    prompt: str = "Describe this image in detail"
    extract_text: bool = Field(default=False, alias="extractText")

    class Config:
        populate_by_name = True


class ImageGenerateParams(BaseModel):
    """Parameters for generating an image."""

    prompt: str
    model: str | None = None  # dall-e-3, dall-e-2, etc.
    size: str | None = None  # 1024x1024, 1792x1024, etc.
    quality: Literal["standard", "hd"] | None = None
    style: Literal["vivid", "natural"] | None = None
    n: int = 1


class ImageResizeParams(BaseModel):
    """Parameters for resizing an image."""

    path: str | None = None
    url: str | None = None
    base64: str | None = None
    width: int | None = None
    height: int | None = None
    max_size: int | None = Field(default=None, alias="maxSize")
    format: Literal["png", "jpeg", "webp"] | None = None
    quality: int | None = None  # JPEG quality 1-100

    class Config:
        populate_by_name = True


class ImageParams(BaseModel):
    """Parameters for image tool.

    Matches moltbot image tool operations.
    """

    op: Literal["understand", "generate", "resize", "info"]

    # For understand operation
    path: str | None = None
    url: str | None = None
    base64_data: str | None = Field(default=None, alias="base64")
    prompt: str | None = None
    extract_text: bool | None = Field(default=None, alias="extractText")

    # For generate operation
    model: str | None = None
    size: str | None = None
    quality: str | None = None
    style: str | None = None
    n: int | None = None

    # For resize operation
    width: int | None = None
    height: int | None = None
    max_size: int | None = Field(default=None, alias="maxSize")
    format: str | None = None

    class Config:
        populate_by_name = True


# =============================================================================
# Image Tool Configuration
# =============================================================================


class ImageToolConfig(BaseModel):
    """Configuration for image tool."""

    # Understanding provider
    understand_provider: Literal["openai", "anthropic", "gemini", "local"] = Field(
        default="openai", alias="understandProvider"
    )
    understand_model: str | None = Field(default=None, alias="understandModel")

    # Generation provider
    generate_provider: Literal["openai", "stability", "local"] = Field(
        default="openai", alias="generateProvider"
    )
    generate_model: str = Field(default="dall-e-3", alias="generateModel")

    # Limits
    max_image_size_bytes: int = Field(
        default=20 * 1024 * 1024, alias="maxImageSizeBytes"
    )  # 20MB
    max_dimension: int = Field(default=4096, alias="maxDimension")

    class Config:
        populate_by_name = True


_config: ImageToolConfig | None = None


def get_image_config() -> ImageToolConfig:
    """Get the global image tool configuration."""
    global _config
    if _config is None:
        _config = ImageToolConfig()
    return _config


def configure_image_tool(config: ImageToolConfig) -> None:
    """Configure the image tool."""
    global _config
    _config = config


# =============================================================================
# Image Tool Implementation
# =============================================================================


async def image_tool(params: dict[str, Any]) -> ToolResult:
    """Execute image tool operations.

    Args:
        params: Tool parameters containing 'op' and operation-specific fields

    Returns:
        ToolResult with operation result or error
    """
    try:
        image_params = ImageParams.model_validate(params)
    except Exception as e:
        return error_result(f"Invalid parameters: {e}")

    config = get_image_config()

    match image_params.op:
        case "understand":
            return await _image_understand(image_params, config)
        case "generate":
            return await _image_generate(image_params, config)
        case "resize":
            return await _image_resize(image_params, config)
        case "info":
            return await _image_info(image_params, config)
        case _:
            return error_result(f"Unknown operation: {image_params.op}")


async def _image_understand(params: ImageParams, config: ImageToolConfig) -> ToolResult:
    """Analyze/understand an image.

    This sends the image to a vision-capable model for analysis.
    """
    # Get image data
    image_data = await _get_image_data(params)
    if isinstance(image_data, ToolResult):
        return image_data  # Error result

    prompt = params.prompt or "Describe this image in detail"

    # TODO: Implement actual vision model integration
    # For now, return a placeholder response
    #
    # In full implementation, this would:
    # 1. Send image to OpenAI GPT-4V, Anthropic Claude, or Gemini
    # 2. Get description/analysis back
    # 3. Optionally extract text (OCR)

    return json_result(
        {
            "status": "placeholder",
            "message": "Image understanding requires vision model integration",
            "imageSize": len(image_data) if image_data else 0,
            "prompt": prompt,
            "extractText": params.extract_text,
        }
    )


async def _image_generate(params: ImageParams, config: ImageToolConfig) -> ToolResult:
    """Generate an image from a text prompt.

    This calls an image generation API like DALL-E.
    """
    if not params.prompt:
        return error_result("Missing required field: prompt")

    # TODO: Implement actual image generation
    # For now, return a placeholder response
    #
    # In full implementation, this would:
    # 1. Call OpenAI DALL-E API or Stability AI
    # 2. Return the generated image
    # 3. Optionally save to file

    return json_result(
        {
            "status": "placeholder",
            "message": "Image generation requires API integration",
            "prompt": params.prompt,
            "model": params.model or config.generate_model,
            "size": params.size or "1024x1024",
            "quality": params.quality or "standard",
            "style": params.style or "vivid",
        }
    )


async def _image_resize(params: ImageParams, config: ImageToolConfig) -> ToolResult:
    """Resize an image.

    This uses PIL/Pillow for image manipulation.
    """
    # Get image data
    image_data = await _get_image_data(params)
    if isinstance(image_data, ToolResult):
        return image_data  # Error result

    try:
        # Try to import PIL
        from PIL import Image

        # Load image
        img = Image.open(io.BytesIO(image_data))
        original_size = img.size

        # Calculate new size
        new_width = params.width
        new_height = params.height

        if params.max_size:
            # Scale to fit within max_size
            max_dim = max(img.width, img.height)
            if max_dim > params.max_size:
                scale = params.max_size / max_dim
                new_width = int(img.width * scale)
                new_height = int(img.height * scale)
        elif new_width and not new_height:
            # Scale height proportionally
            scale = new_width / img.width
            new_height = int(img.height * scale)
        elif new_height and not new_width:
            # Scale width proportionally
            scale = new_height / img.height
            new_width = int(img.width * scale)
        elif not new_width and not new_height:
            return error_result("Must specify width, height, or maxSize")

        # Resize
        img_resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

        # Get output format
        output_format = params.format or "png"
        if output_format == "jpeg":
            output_format = "JPEG"
            if img_resized.mode == "RGBA":
                img_resized = img_resized.convert("RGB")
        elif output_format == "webp":
            output_format = "WEBP"
        else:
            output_format = "PNG"

        # Save to bytes
        output = io.BytesIO()
        save_kwargs = {}
        if output_format == "JPEG" and params.quality:
            save_kwargs["quality"] = params.quality
        img_resized.save(output, format=output_format, **save_kwargs)
        output_data = output.getvalue()

        # Return result
        return json_result(
            {
                "success": True,
                "originalSize": list(original_size),
                "newSize": [new_width, new_height],
                "format": output_format.lower(),
                "bytes": len(output_data),
                "base64": base64.b64encode(output_data).decode("utf-8"),
            }
        )

    except ImportError:
        return error_result(
            "PIL/Pillow not installed. Install with: pip install Pillow"
        )
    except Exception as e:
        return error_result(f"Image resize failed: {e}")


async def _image_info(params: ImageParams, config: ImageToolConfig) -> ToolResult:
    """Get information about an image."""
    # Get image data
    image_data = await _get_image_data(params)
    if isinstance(image_data, ToolResult):
        return image_data  # Error result

    try:
        from PIL import Image

        img = Image.open(io.BytesIO(image_data))

        return json_result(
            {
                "width": img.width,
                "height": img.height,
                "mode": img.mode,
                "format": img.format,
                "bytes": len(image_data),
                "info": dict(img.info) if img.info else {},
            }
        )

    except ImportError:
        # Return basic info without PIL
        return json_result(
            {
                "bytes": len(image_data),
                "note": "PIL not installed, limited info available",
            }
        )
    except Exception as e:
        return error_result(f"Failed to get image info: {e}")


# =============================================================================
# Helper Functions
# =============================================================================


async def _get_image_data(params: ImageParams) -> bytes | ToolResult:
    """Get image data from path, URL, or base64.

    Args:
        params: Image parameters with path, url, or base64

    Returns:
        Image bytes or ToolResult error
    """
    if params.base64_data:
        try:
            return base64.b64decode(params.base64_data)
        except Exception as e:
            return error_result(f"Invalid base64 data: {e}")

    if params.path:
        try:
            path = Path(params.path)
            if not path.exists():
                return error_result(f"File not found: {params.path}")
            return path.read_bytes()
        except Exception as e:
            return error_result(f"Failed to read file: {e}")

    if params.url:
        try:
            import httpx

            async with httpx.AsyncClient() as client:
                response = await client.get(params.url, timeout=30.0)
                response.raise_for_status()
                return response.content
        except ImportError:
            return error_result("httpx not installed. Install with: pip install httpx")
        except Exception as e:
            return error_result(f"Failed to fetch URL: {e}")

    return error_result("Must provide path, url, or base64 data")


# =============================================================================
# Tool Factory Function
# =============================================================================


def create_image_tool() -> tuple[str, str, dict[str, Any], Any]:
    """Create the image tool definition.

    Returns:
        Tuple of (name, description, schema, handler)
    """
    name = "image"
    description = """Image understanding, generation, and manipulation.

Operations:
- understand: Analyze an image using a vision model
- generate: Create an image from a text prompt
- resize: Resize/convert an image
- info: Get image metadata

Input sources:
- path: Local file path
- url: Remote URL
- base64: Base64-encoded image data

Examples:
- Analyze: {"op": "understand", "path": "/path/to/image.png", "prompt": "What is in this image?"}
- Generate: {"op": "generate", "prompt": "A sunset over mountains", "size": "1024x1024"}
- Resize: {"op": "resize", "path": "/path/to/image.png", "width": 512}"""

    schema = {
        "type": "object",
        "properties": {
            "op": {
                "type": "string",
                "enum": ["understand", "generate", "resize", "info"],
                "description": "Operation to perform",
            },
            "path": {
                "type": "string",
                "description": "Local file path to image",
            },
            "url": {
                "type": "string",
                "description": "URL to fetch image from",
            },
            "base64": {
                "type": "string",
                "description": "Base64-encoded image data",
            },
            "prompt": {
                "type": "string",
                "description": "Prompt for understand/generate operations",
            },
            "extractText": {
                "type": "boolean",
                "description": "Extract text from image (OCR)",
            },
            "model": {
                "type": "string",
                "description": "Model to use for generation (dall-e-3, dall-e-2)",
            },
            "size": {
                "type": "string",
                "description": "Image size for generation (1024x1024, etc.)",
            },
            "quality": {
                "type": "string",
                "enum": ["standard", "hd"],
                "description": "Image quality for generation",
            },
            "style": {
                "type": "string",
                "enum": ["vivid", "natural"],
                "description": "Image style for DALL-E 3",
            },
            "width": {
                "type": "number",
                "description": "Target width for resize",
            },
            "height": {
                "type": "number",
                "description": "Target height for resize",
            },
            "maxSize": {
                "type": "number",
                "description": "Maximum dimension for resize (maintains aspect ratio)",
            },
            "format": {
                "type": "string",
                "enum": ["png", "jpeg", "webp"],
                "description": "Output format for resize",
            },
        },
        "required": ["op"],
    }

    return name, description, schema, image_tool
