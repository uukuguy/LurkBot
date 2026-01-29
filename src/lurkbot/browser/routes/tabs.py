"""
Tabs Route - 标签页管理端点

对标 MoltBot src/browser/routes/tabs.ts
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from loguru import logger
from pydantic import BaseModel, Field

from ..playwright_session import get_session
from ..types import (
    BrowserNotConnectedError,
    TabInfo,
    TabRequest,
    TabsResponse,
)

router = APIRouter(prefix="/tabs", tags=["tabs"])


# ============================================================================
# Tab Endpoints
# ============================================================================

@router.get("", response_model=TabsResponse)
async def list_tabs() -> TabsResponse:
    """
    列出所有标签页

    Returns:
        TabsResponse 包含所有标签页信息
    """
    try:
        session = await get_session()

        if not session.is_connected:
            raise BrowserNotConnectedError()

        tabs = []
        active_tab = None

        for i, page in enumerate(session.pages):
            try:
                url = page.url
                title = await page.title()
            except Exception:
                url = "about:blank"
                title = ""

            is_active = page == session.page
            if is_active:
                active_tab = i

            tabs.append(TabInfo(
                id=i,
                url=url,
                title=title,
                active=is_active,
            ))

        return TabsResponse(
            tabs=tabs,
            active_tab=active_tab,
        )

    except BrowserNotConnectedError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"List tabs failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("", response_model=TabInfo)
async def create_tab(request: TabRequest) -> TabInfo:
    """
    创建新标签页

    Args:
        request: 标签页请求
            - url: 可选的初始 URL

    Returns:
        新标签页信息
    """
    try:
        session = await get_session()

        if not session.is_connected:
            raise BrowserNotConnectedError()

        page = await session.new_page(request.url)

        url = page.url
        title = await page.title()
        tab_id = len(session.pages) - 1

        return TabInfo(
            id=tab_id,
            url=url,
            title=title,
            active=True,
        )

    except BrowserNotConnectedError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Create tab failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{tab_id}")
async def close_tab(tab_id: int) -> dict:
    """
    关闭标签页

    Args:
        tab_id: 标签页 ID

    Returns:
        操作结果
    """
    try:
        session = await get_session()

        if not session.is_connected:
            raise BrowserNotConnectedError()

        if tab_id < 0 or tab_id >= len(session.pages):
            raise HTTPException(status_code=404, detail=f"Tab {tab_id} not found")

        await session.close_page(tab_id)

        return {"success": True, "closed": tab_id}

    except BrowserNotConnectedError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Close tab failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{tab_id}/activate", response_model=TabInfo)
async def activate_tab(tab_id: int) -> TabInfo:
    """
    激活标签页

    Args:
        tab_id: 标签页 ID

    Returns:
        激活的标签页信息
    """
    try:
        session = await get_session()

        if not session.is_connected:
            raise BrowserNotConnectedError()

        page = session.switch_to_page(tab_id)
        if not page:
            raise HTTPException(status_code=404, detail=f"Tab {tab_id} not found")

        url = page.url
        title = await page.title()

        return TabInfo(
            id=tab_id,
            url=url,
            title=title,
            active=True,
        )

    except BrowserNotConnectedError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Activate tab failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{tab_id}", response_model=TabInfo)
async def get_tab(tab_id: int) -> TabInfo:
    """
    获取标签页信息

    Args:
        tab_id: 标签页 ID

    Returns:
        标签页信息
    """
    try:
        session = await get_session()

        if not session.is_connected:
            raise BrowserNotConnectedError()

        if tab_id < 0 or tab_id >= len(session.pages):
            raise HTTPException(status_code=404, detail=f"Tab {tab_id} not found")

        page = session.pages[tab_id]
        url = page.url
        title = await page.title()
        is_active = page == session.page

        return TabInfo(
            id=tab_id,
            url=url,
            title=title,
            active=is_active,
        )

    except BrowserNotConnectedError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get tab failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Tab Navigation
# ============================================================================

class TabNavigateRequest(BaseModel):
    """标签页导航请求"""
    url: str
    wait_until: str = Field(default="load", alias="waitUntil")


@router.post("/{tab_id}/navigate", response_model=TabInfo)
async def navigate_tab(tab_id: int, request: TabNavigateRequest) -> TabInfo:
    """
    在指定标签页中导航

    Args:
        tab_id: 标签页 ID
        request: 导航请求

    Returns:
        更新后的标签页信息
    """
    try:
        session = await get_session()

        if not session.is_connected:
            raise BrowserNotConnectedError()

        if tab_id < 0 or tab_id >= len(session.pages):
            raise HTTPException(status_code=404, detail=f"Tab {tab_id} not found")

        page = session.pages[tab_id]
        await page.goto(request.url, wait_until=request.wait_until)

        url = page.url
        title = await page.title()
        is_active = page == session.page

        return TabInfo(
            id=tab_id,
            url=url,
            title=title,
            active=is_active,
        )

    except BrowserNotConnectedError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Navigate tab failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Exports
# ============================================================================

__all__ = ["router"]
