"""
Browser Server - 浏览器控制服务器

对标 MoltBot src/browser/server.ts

提供 HTTP API 来控制浏览器自动化。
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from pydantic import BaseModel

from .config import load_browser_config, load_server_config
from .playwright_session import PlaywrightSession, get_session
from .routes import act_router, navigate_router, screenshot_router, tabs_router
from .types import (
    BrowserConfig,
    BrowserNotConnectedError,
    BrowserStatus,
    EvaluateRequest,
    EvaluateResponse,
    ServerConfig,
)


# ============================================================================
# Application State
# ============================================================================

class BrowserServerState:
    """服务器状态"""
    session: PlaywrightSession | None = None
    config: BrowserConfig | None = None
    server_config: ServerConfig | None = None


state = BrowserServerState()


# ============================================================================
# Lifespan
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """应用生命周期管理"""
    # 启动时
    logger.info("Starting browser server...")

    state.config = load_browser_config()
    state.server_config = load_server_config()

    # 可选：自动启动浏览器
    # await _connect_browser()

    yield

    # 关闭时
    logger.info("Shutting down browser server...")

    if state.session:
        await state.session.close()
        state.session = None


# ============================================================================
# FastAPI Application
# ============================================================================

def create_browser_app(
    browser_config: BrowserConfig | None = None,
    server_config: ServerConfig | None = None,
) -> FastAPI:
    """
    创建浏览器控制应用

    Args:
        browser_config: 浏览器配置
        server_config: 服务器配置

    Returns:
        FastAPI 应用实例
    """
    server_cfg = server_config or load_server_config()

    app = FastAPI(
        title="LurkBot Browser Server",
        description="Browser automation HTTP API",
        version="1.0.0",
        lifespan=lifespan,
    )

    # CORS 中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=server_cfg.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 注册路由
    app.include_router(act_router)
    app.include_router(navigate_router)
    app.include_router(screenshot_router)
    app.include_router(tabs_router)

    # 根路由
    @app.get("/")
    async def root() -> dict:
        return {
            "service": "LurkBot Browser Server",
            "version": "1.0.0",
            "status": "running",
        }

    # 状态端点
    @app.get("/status", response_model=BrowserStatus)
    async def get_status() -> BrowserStatus:
        """获取浏览器状态"""
        session = await get_session(state.config)
        return await session.get_status()

    # 连接端点
    @app.post("/connect")
    async def connect_browser(cdp_endpoint: str | None = None) -> dict:
        """
        连接到浏览器

        Args:
            cdp_endpoint: CDP 端点（如果提供则连接到已有浏览器）
        """
        try:
            session = await get_session(state.config)

            if session.is_connected:
                return {"success": True, "message": "Already connected"}

            if cdp_endpoint:
                await session.connect_cdp(cdp_endpoint)
            else:
                await session.launch()

            state.session = session
            return {"success": True, "message": "Connected"}

        except Exception as e:
            logger.error(f"Connect failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    # 断开连接
    @app.post("/disconnect")
    async def disconnect_browser() -> dict:
        """断开浏览器连接"""
        try:
            session = await get_session(state.config)
            await session.close()
            state.session = None
            return {"success": True, "message": "Disconnected"}
        except Exception as e:
            logger.error(f"Disconnect failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    # JavaScript 执行
    @app.post("/evaluate", response_model=EvaluateResponse)
    async def evaluate_js(request: EvaluateRequest) -> EvaluateResponse:
        """
        执行 JavaScript

        Args:
            request: 执行请求
                - expression: JavaScript 表达式
                - arg: 可选参数
        """
        import time
        start_time = time.time()

        try:
            session = await get_session(state.config)

            if not session.is_connected:
                raise BrowserNotConnectedError()

            result = await session.evaluate(request.expression, request.arg)

            duration_ms = (time.time() - start_time) * 1000

            return EvaluateResponse(
                success=True,
                result=result,
                duration_ms=duration_ms,
            )

        except BrowserNotConnectedError as e:
            raise HTTPException(status_code=503, detail=str(e))
        except Exception as e:
            logger.error(f"Evaluate failed: {e}")
            return EvaluateResponse(
                success=False,
                error=str(e),
            )

    # 健康检查
    @app.get("/health")
    async def health_check() -> dict:
        """健康检查"""
        session = await get_session(state.config)
        return {
            "status": "healthy",
            "browser_connected": session.is_connected,
        }

    return app


# ============================================================================
# Default App Instance
# ============================================================================

app = create_browser_app()


# ============================================================================
# Server Runner
# ============================================================================

async def run_browser_server(
    host: str | None = None,
    port: int | None = None,
    browser_config: BrowserConfig | None = None,
    server_config: ServerConfig | None = None,
    auto_launch: bool = False,
) -> None:
    """
    运行浏览器服务器

    Args:
        host: 绑定地址
        port: 端口
        browser_config: 浏览器配置
        server_config: 服务器配置
        auto_launch: 是否自动启动浏览器
    """
    import uvicorn

    server_cfg = server_config or load_server_config()
    browser_cfg = browser_config or load_browser_config()

    final_host = host or server_cfg.host
    final_port = port or server_cfg.port

    # 更新全局状态
    state.config = browser_cfg
    state.server_config = server_cfg

    # 自动启动浏览器
    if auto_launch:
        session = await get_session(browser_cfg)
        await session.launch()
        state.session = session

    logger.info(f"Starting browser server at {final_host}:{final_port}")

    config = uvicorn.Config(
        app=create_browser_app(browser_cfg, server_cfg),
        host=final_host,
        port=final_port,
        log_level="info" if server_cfg.debug else "warning",
    )

    server = uvicorn.Server(config)
    await server.serve()


def start_browser_server(
    host: str | None = None,
    port: int | None = None,
    auto_launch: bool = False,
) -> None:
    """
    同步启动浏览器服务器

    Args:
        host: 绑定地址
        port: 端口
        auto_launch: 是否自动启动浏览器
    """
    asyncio.run(run_browser_server(
        host=host,
        port=port,
        auto_launch=auto_launch,
    ))


# ============================================================================
# CLI Entry Point
# ============================================================================

def main() -> None:
    """CLI 入口点"""
    import argparse

    parser = argparse.ArgumentParser(description="LurkBot Browser Server")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host")
    parser.add_argument("--port", type=int, default=9333, help="Bind port")
    parser.add_argument("--auto-launch", action="store_true", help="Auto launch browser")
    parser.add_argument("--headless", action="store_true", help="Run in headless mode")

    args = parser.parse_args()

    start_browser_server(
        host=args.host,
        port=args.port,
        auto_launch=args.auto_launch,
    )


if __name__ == "__main__":
    main()


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    "app",
    "create_browser_app",
    "run_browser_server",
    "start_browser_server",
    "BrowserServerState",
    "state",
]
