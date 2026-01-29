"""
Screenshot Route - 截图端点

对标 MoltBot src/browser/routes/screenshot.ts
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from loguru import logger

from ..playwright_session import get_session
from ..role_snapshot import get_aria_snapshot, get_role_snapshot
from ..screenshot import capture_screenshot_response
from ..types import (
    BrowserNotConnectedError,
    RoleSnapshotRequest,
    RoleSnapshotResponse,
    ScreenshotRequest,
    ScreenshotResponse,
)

router = APIRouter(tags=["screenshot"])


# ============================================================================
# Screenshot Endpoints
# ============================================================================

@router.post("/screenshot", response_model=ScreenshotResponse)
async def take_screenshot(request: ScreenshotRequest) -> ScreenshotResponse:
    """
    截取页面截图

    Args:
        request: 截图请求
            - fullPage: 是否截取整页
            - selector: 截取特定元素
            - format: 图片格式 (png|jpeg)
            - quality: 图片质量 (仅 jpeg)
            - omitBackground: 是否忽略背景

    Returns:
        ScreenshotResponse (包含 base64 编码的图片)
    """
    try:
        session = await get_session()

        if not session.is_connected:
            raise BrowserNotConnectedError()

        return await capture_screenshot_response(session, request)

    except BrowserNotConnectedError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Screenshot failed: {e}")
        return ScreenshotResponse(
            success=False,
            format=request.format,
            error=str(e),
        )


@router.get("/screenshot")
async def get_screenshot(
    full_page: bool = False,
    format: str = "png",
    quality: int | None = None,
) -> Response:
    """
    获取截图（直接返回图片）

    Args:
        full_page: 是否截取整页
        format: 图片格式
        quality: 图片质量

    Returns:
        图片响应
    """
    try:
        session = await get_session()

        if not session.is_connected:
            raise BrowserNotConnectedError()

        data = await session.screenshot(
            full_page=full_page,
            format=format,
            quality=quality,
        )

        media_type = f"image/{format}"
        return Response(content=data, media_type=media_type)

    except BrowserNotConnectedError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Screenshot failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Snapshot Endpoints
# ============================================================================

@router.post("/snapshot/role", response_model=RoleSnapshotResponse)
async def get_role_snapshot_endpoint(
    request: RoleSnapshotRequest,
) -> RoleSnapshotResponse:
    """
    获取页面角色快照

    角色快照是页面可访问性树的结构化表示，
    便于 AI Agent 理解页面结构。

    Args:
        request: 快照请求
            - includeHidden: 是否包含隐藏元素
            - maxDepth: 最大深度
            - rootSelector: 根元素选择器

    Returns:
        RoleSnapshotResponse
    """
    try:
        session = await get_session()

        if not session.is_connected:
            raise BrowserNotConnectedError()

        return await get_role_snapshot(
            session,
            include_hidden=request.include_hidden,
            max_depth=request.max_depth,
            root_selector=request.root_selector,
        )

    except BrowserNotConnectedError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Role snapshot failed: {e}")
        return RoleSnapshotResponse(
            success=False,
            error=str(e),
        )


from pydantic import BaseModel


class AriaSnapshotRequest(BaseModel):
    """ARIA 快照请求"""
    selector: str | None = None


class AriaSnapshotResponse(BaseModel):
    """ARIA 快照响应"""
    success: bool
    snapshot: str | None = None
    error: str | None = None


@router.post("/snapshot/aria", response_model=AriaSnapshotResponse)
async def get_aria_snapshot_endpoint(
    request: AriaSnapshotRequest,
) -> AriaSnapshotResponse:
    """
    获取 ARIA 快照

    ARIA 快照是更简洁的可访问性表示，
    适合直接传递给 AI。

    Args:
        request: 快照请求

    Returns:
        AriaSnapshotResponse
    """
    try:
        session = await get_session()

        if not session.is_connected:
            raise BrowserNotConnectedError()

        snapshot = await get_aria_snapshot(session, request.selector)

        return AriaSnapshotResponse(
            success=True,
            snapshot=snapshot,
        )

    except BrowserNotConnectedError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"ARIA snapshot failed: {e}")
        return AriaSnapshotResponse(
            success=False,
            error=str(e),
        )


@router.get("/snapshot/aria")
async def get_aria_snapshot_text(selector: str | None = None) -> Response:
    """
    获取 ARIA 快照（纯文本）

    Args:
        selector: 可选的元素选择器

    Returns:
        纯文本响应
    """
    try:
        session = await get_session()

        if not session.is_connected:
            raise BrowserNotConnectedError()

        snapshot = await get_aria_snapshot(session, selector)

        return Response(content=snapshot, media_type="text/plain")

    except BrowserNotConnectedError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"ARIA snapshot failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Exports
# ============================================================================

__all__ = ["router"]
