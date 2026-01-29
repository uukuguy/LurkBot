"""
Act Route - 执行浏览器动作

对标 MoltBot src/browser/routes/act.ts
"""

from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter, HTTPException
from loguru import logger

from ..playwright_session import get_session
from ..types import (
    ActRequest,
    ActResponse,
    BrowserAction,
    BrowserActionError,
    BrowserNotConnectedError,
)

router = APIRouter(prefix="/act", tags=["actions"])


# ============================================================================
# Act Endpoint
# ============================================================================

@router.post("", response_model=ActResponse)
async def execute_action(request: ActRequest) -> ActResponse:
    """
    执行浏览器动作

    支持的动作:
    - click: 点击元素
    - doubleClick: 双击元素
    - type: 输入文本（逐字符）
    - fill: 填充表单字段
    - press: 按键
    - hover: 悬停
    - drag: 拖拽
    - selectOption: 选择下拉选项
    - scroll: 滚动
    - focus: 聚焦
    - blur: 取消聚焦
    - check: 勾选复选框
    - uncheck: 取消勾选
    - wait: 等待
    """
    start_time = time.time()

    try:
        session = await get_session()

        if not session.is_connected:
            raise BrowserNotConnectedError()

        page = session.page
        if not page:
            raise BrowserNotConnectedError()

        # 执行动作
        await _execute_action(session, request)

        duration_ms = (time.time() - start_time) * 1000

        return ActResponse(
            success=True,
            action=request.action.value,
            selector=request.selector,
            duration_ms=duration_ms,
        )

    except BrowserNotConnectedError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except BrowserActionError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Action failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def _execute_action(session: Any, request: ActRequest) -> None:
    """执行具体动作"""
    action = request.action
    selector = request.selector
    timeout = request.timeout

    # 准备通用选项
    options: dict[str, Any] = {}
    if timeout:
        options["timeout"] = timeout
    if request.force:
        options["force"] = True
    if request.no_wait_after:
        options["no_wait_after"] = True

    # 分派动作
    if action == BrowserAction.CLICK:
        if not selector:
            raise BrowserActionError("Selector required for click", "click")
        await session.click(
            selector,
            button=request.button.value,
            position=request.position,
            modifiers=[m.value for m in request.modifiers] if request.modifiers else None,
            delay=request.delay or 0,
            **options,
        )

    elif action == BrowserAction.DOUBLE_CLICK:
        if not selector:
            raise BrowserActionError("Selector required for doubleClick", "doubleClick")
        await session.double_click(selector, **options)

    elif action == BrowserAction.TYPE:
        if not selector:
            raise BrowserActionError("Selector required for type", "type")
        if not request.text:
            raise BrowserActionError("Text required for type", "type")
        await session.type(
            selector,
            request.text,
            delay=request.delay or 0,
            timeout=timeout,
        )

    elif action == BrowserAction.FILL:
        if not selector:
            raise BrowserActionError("Selector required for fill", "fill")
        if request.text is None:
            raise BrowserActionError("Text required for fill", "fill")
        await session.fill(selector, request.text, **options)

    elif action == BrowserAction.PRESS:
        if not request.key:
            raise BrowserActionError("Key required for press", "press")
        await session.press(
            selector,
            request.key,
            delay=request.delay or 0,
            timeout=timeout,
        )

    elif action == BrowserAction.HOVER:
        if not selector:
            raise BrowserActionError("Selector required for hover", "hover")
        await session.hover(
            selector,
            position=request.position,
            **options,
        )

    elif action == BrowserAction.DRAG:
        # drag 需要特殊处理，需要两个选择器
        raise BrowserActionError(
            "Drag requires source and target selectors. Use /act/drag endpoint.",
            "drag",
        )

    elif action == BrowserAction.SELECT_OPTION:
        if not selector:
            raise BrowserActionError("Selector required for selectOption", "selectOption")
        if not request.text:
            raise BrowserActionError("Value required for selectOption", "selectOption")
        await session.select_option(selector, value=request.text, timeout=timeout)

    elif action == BrowserAction.SCROLL:
        position = request.position or {}
        await session.scroll(
            selector,
            x=position.get("x", 0),
            y=position.get("y", 0),
        )

    elif action == BrowserAction.FOCUS:
        if not selector:
            raise BrowserActionError("Selector required for focus", "focus")
        await session.focus(selector, timeout=timeout)

    elif action == BrowserAction.BLUR:
        if not selector:
            raise BrowserActionError("Selector required for blur", "blur")
        page = session.page
        await page.locator(selector).blur()

    elif action == BrowserAction.CHECK:
        if not selector:
            raise BrowserActionError("Selector required for check", "check")
        await session.check(selector, timeout=timeout)

    elif action == BrowserAction.UNCHECK:
        if not selector:
            raise BrowserActionError("Selector required for uncheck", "uncheck")
        await session.uncheck(selector, timeout=timeout)

    elif action == BrowserAction.WAIT:
        import asyncio
        wait_time = request.delay or 1000
        await asyncio.sleep(wait_time / 1000)

    else:
        raise BrowserActionError(f"Unknown action: {action}", str(action))


# ============================================================================
# Specialized Endpoints
# ============================================================================

from pydantic import BaseModel, Field


class DragRequest(BaseModel):
    """拖拽请求"""
    source: str
    target: str
    source_position: dict[str, int] | None = Field(default=None, alias="sourcePosition")
    target_position: dict[str, int] | None = Field(default=None, alias="targetPosition")
    timeout: float = 30000
    force: bool = False


@router.post("/drag", response_model=ActResponse)
async def execute_drag(request: DragRequest) -> ActResponse:
    """执行拖拽动作"""
    start_time = time.time()

    try:
        session = await get_session()

        if not session.is_connected:
            raise BrowserNotConnectedError()

        await session.drag(
            source=request.source,
            target=request.target,
            source_position=request.source_position,
            target_position=request.target_position,
            force=request.force,
            timeout=request.timeout,
        )

        duration_ms = (time.time() - start_time) * 1000

        return ActResponse(
            success=True,
            action="drag",
            selector=f"{request.source} -> {request.target}",
            duration_ms=duration_ms,
        )

    except Exception as e:
        logger.error(f"Drag failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class WaitForSelectorRequest(BaseModel):
    """等待选择器请求"""
    selector: str
    state: str = "visible"  # visible | hidden | attached | detached
    timeout: float = 30000


@router.post("/wait", response_model=ActResponse)
async def wait_for_selector(request: WaitForSelectorRequest) -> ActResponse:
    """等待选择器"""
    start_time = time.time()

    try:
        session = await get_session()

        if not session.is_connected:
            raise BrowserNotConnectedError()

        await session.wait_for_selector(
            request.selector,
            state=request.state,
            timeout=request.timeout,
        )

        duration_ms = (time.time() - start_time) * 1000

        return ActResponse(
            success=True,
            action="wait",
            selector=request.selector,
            duration_ms=duration_ms,
        )

    except Exception as e:
        logger.error(f"Wait failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Exports
# ============================================================================

__all__ = ["router"]
