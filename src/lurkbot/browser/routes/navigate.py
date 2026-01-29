"""
Navigate Route - 导航端点

对标 MoltBot src/browser/routes/navigate.ts
"""

from __future__ import annotations

import time

from fastapi import APIRouter, HTTPException
from loguru import logger

from ..playwright_session import get_session
from ..types import (
    BrowserNotConnectedError,
    NavigateRequest,
    NavigateResponse,
)

router = APIRouter(prefix="/navigate", tags=["navigation"])


# ============================================================================
# Navigate Endpoints
# ============================================================================

@router.post("", response_model=NavigateResponse)
async def navigate(request: NavigateRequest) -> NavigateResponse:
    """
    导航到 URL

    Args:
        request: 导航请求
            - url: 目标 URL
            - waitUntil: 等待条件 (load|domcontentloaded|networkidle|commit)
            - timeout: 超时时间（毫秒）
            - referer: Referer 头

    Returns:
        NavigateResponse
    """
    start_time = time.time()

    try:
        session = await get_session()

        if not session.is_connected:
            raise BrowserNotConnectedError()

        page = session.page
        if not page:
            raise BrowserNotConnectedError()

        # 执行导航
        response = await page.goto(
            request.url,
            wait_until=request.wait_until,
            timeout=request.timeout,
            referer=request.referer,
        )

        # 获取页面信息
        title = await page.title()
        current_url = page.url
        status = response.status if response else None

        duration_ms = (time.time() - start_time) * 1000

        return NavigateResponse(
            success=True,
            url=current_url,
            title=title,
            status=status,
            duration_ms=duration_ms,
        )

    except BrowserNotConnectedError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Navigation failed: {e}")
        duration_ms = (time.time() - start_time) * 1000
        return NavigateResponse(
            success=False,
            url=request.url,
            error=str(e),
            duration_ms=duration_ms,
        )


@router.post("/back", response_model=NavigateResponse)
async def go_back() -> NavigateResponse:
    """后退到上一页"""
    start_time = time.time()

    try:
        session = await get_session()

        if not session.is_connected:
            raise BrowserNotConnectedError()

        await session.go_back()

        page = session.page
        title = await page.title() if page else None
        current_url = page.url if page else ""

        duration_ms = (time.time() - start_time) * 1000

        return NavigateResponse(
            success=True,
            url=current_url,
            title=title,
            duration_ms=duration_ms,
        )

    except BrowserNotConnectedError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Go back failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/forward", response_model=NavigateResponse)
async def go_forward() -> NavigateResponse:
    """前进到下一页"""
    start_time = time.time()

    try:
        session = await get_session()

        if not session.is_connected:
            raise BrowserNotConnectedError()

        await session.go_forward()

        page = session.page
        title = await page.title() if page else None
        current_url = page.url if page else ""

        duration_ms = (time.time() - start_time) * 1000

        return NavigateResponse(
            success=True,
            url=current_url,
            title=title,
            duration_ms=duration_ms,
        )

    except BrowserNotConnectedError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Go forward failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reload", response_model=NavigateResponse)
async def reload(wait_until: str = "load") -> NavigateResponse:
    """
    重新加载页面

    Args:
        wait_until: 等待条件
    """
    start_time = time.time()

    try:
        session = await get_session()

        if not session.is_connected:
            raise BrowserNotConnectedError()

        await session.reload(wait_until=wait_until)

        page = session.page
        title = await page.title() if page else None
        current_url = page.url if page else ""

        duration_ms = (time.time() - start_time) * 1000

        return NavigateResponse(
            success=True,
            url=current_url,
            title=title,
            duration_ms=duration_ms,
        )

    except BrowserNotConnectedError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Reload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# URL Info
# ============================================================================

from pydantic import BaseModel


class UrlInfoResponse(BaseModel):
    """URL 信息响应"""
    url: str
    title: str | None = None
    content_type: str | None = None


@router.get("/info", response_model=UrlInfoResponse)
async def get_url_info() -> UrlInfoResponse:
    """获取当前页面 URL 信息"""
    try:
        session = await get_session()

        if not session.is_connected:
            raise BrowserNotConnectedError()

        page = session.page
        if not page:
            raise BrowserNotConnectedError()

        return UrlInfoResponse(
            url=page.url,
            title=await page.title(),
        )

    except BrowserNotConnectedError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Get URL info failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Wait for Navigation
# ============================================================================

class WaitForNavigationRequest(BaseModel):
    """等待导航请求"""
    url: str | None = None
    wait_until: str = "load"
    timeout: float = 30000


@router.post("/wait", response_model=NavigateResponse)
async def wait_for_navigation(request: WaitForNavigationRequest) -> NavigateResponse:
    """等待导航完成"""
    start_time = time.time()

    try:
        session = await get_session()

        if not session.is_connected:
            raise BrowserNotConnectedError()

        page = session.page
        if not page:
            raise BrowserNotConnectedError()

        if request.url:
            await session.wait_for_url(request.url, timeout=request.timeout)
        else:
            await session.wait_for_load_state(
                request.wait_until,
                timeout=request.timeout,
            )

        title = await page.title()
        current_url = page.url

        duration_ms = (time.time() - start_time) * 1000

        return NavigateResponse(
            success=True,
            url=current_url,
            title=title,
            duration_ms=duration_ms,
        )

    except BrowserNotConnectedError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Wait for navigation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Exports
# ============================================================================

__all__ = ["router"]
