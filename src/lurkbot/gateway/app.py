"""
Gateway FastAPI Application

提供 HTTP API 和 WebSocket 端点用于 AI Agent 通信。
"""

from __future__ import annotations

import os
import time
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from pydantic import BaseModel

from lurkbot.gateway.server import get_gateway_server


# ============================================================================
# Health Check Models
# ============================================================================


class HealthStatus(BaseModel):
    """健康检查响应"""

    status: str
    version: str
    uptime_seconds: float
    connections: int
    tenant_support: bool


class ReadinessStatus(BaseModel):
    """就绪检查响应"""

    ready: bool
    checks: dict[str, bool]


# ============================================================================
# Application State
# ============================================================================


class GatewayAppState:
    """Gateway 应用状态"""

    start_time: float = 0.0
    version: str = "0.1.0"


state = GatewayAppState()


# ============================================================================
# Lifespan
# ============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """应用生命周期管理"""
    # 启动时
    logger.info("Starting LurkBot Gateway...")
    state.start_time = time.time()

    # 加载版本信息
    try:
        from lurkbot import __version__

        state.version = __version__
    except ImportError:
        state.version = "0.1.0"

    yield

    # 关闭时
    logger.info("Shutting down LurkBot Gateway...")


# ============================================================================
# FastAPI Application Factory
# ============================================================================


def create_gateway_app(
    cors_origins: list[str] | None = None,
    include_tenant_api: bool = True,
    include_monitoring_api: bool = True,
    include_audit_api: bool = True,
) -> FastAPI:
    """
    创建 Gateway FastAPI 应用

    Args:
        cors_origins: CORS 允许的源列表
        include_tenant_api: 是否包含租户 API
        include_monitoring_api: 是否包含监控 API
        include_audit_api: 是否包含审计 API

    Returns:
        FastAPI 应用实例
    """
    app = FastAPI(
        title="LurkBot Gateway",
        description="Multi-channel AI assistant gateway server",
        version=state.version or "0.1.0",
        lifespan=lifespan,
    )

    # CORS 中间件
    origins = cors_origins or ["*"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # -------------------------------------------------------------------------
    # Health Check Endpoints
    # -------------------------------------------------------------------------

    @app.get("/health", response_model=HealthStatus, tags=["Health"])
    async def health_check() -> HealthStatus:
        """
        健康检查端点

        用于 Docker/Kubernetes 健康检查探针。
        """
        gateway = get_gateway_server()
        uptime = time.time() - state.start_time if state.start_time > 0 else 0

        # 检查租户支持
        tenant_support = False
        try:
            from lurkbot.tenants import TenantManager

            tenant_support = True
        except ImportError:
            pass

        return HealthStatus(
            status="healthy",
            version=state.version,
            uptime_seconds=uptime,
            connections=len(gateway._connections),
            tenant_support=tenant_support,
        )

    @app.get("/ready", response_model=ReadinessStatus, tags=["Health"])
    async def readiness_check() -> ReadinessStatus:
        """
        就绪检查端点

        用于 Kubernetes 就绪探针，检查服务是否准备好接收流量。
        """
        checks = {
            "gateway": True,
            "config": True,
        }

        # 检查配置
        try:
            config_dir = os.path.expanduser("~/.lurkbot")
            checks["config"] = os.path.isdir(config_dir)
        except Exception:
            checks["config"] = False

        # 检查租户系统
        try:
            from lurkbot.tenants import TenantManager

            checks["tenants"] = True
        except ImportError:
            checks["tenants"] = False

        # 检查 AI 提供商
        checks["ai_provider"] = bool(
            os.environ.get("LURKBOT_ANTHROPIC_API_KEY")
            or os.environ.get("LURKBOT_OPENAI_API_KEY")
            or os.environ.get("DEEPSEEK_API_KEY")
        )

        all_ready = all(checks.values())

        return ReadinessStatus(ready=all_ready, checks=checks)

    @app.get("/live", tags=["Health"])
    async def liveness_check() -> dict:
        """
        存活检查端点

        用于 Kubernetes 存活探针，检查服务是否存活。
        """
        return {"alive": True}

    # -------------------------------------------------------------------------
    # Root Endpoint
    # -------------------------------------------------------------------------

    @app.get("/", tags=["Info"])
    async def root() -> dict:
        """根端点"""
        return {
            "service": "LurkBot Gateway",
            "version": state.version,
            "status": "running",
            "docs": "/docs",
        }

    @app.get("/info", tags=["Info"])
    async def info() -> dict:
        """服务信息"""
        gateway = get_gateway_server()
        return {
            "name": "LurkBot Gateway",
            "version": state.version,
            "protocol_version": gateway.PROTOCOL_VERSION,
            "connections": len(gateway._connections),
            "features": {
                "websocket": True,
                "multi_tenant": True,
                "policy_engine": True,
                "audit_logging": True,
            },
        }

    # -------------------------------------------------------------------------
    # WebSocket Endpoint
    # -------------------------------------------------------------------------

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket) -> None:
        """WebSocket 连接端点"""
        gateway = get_gateway_server()
        await gateway.handle_connection(websocket)

    # -------------------------------------------------------------------------
    # Optional API Routers
    # -------------------------------------------------------------------------

    # 租户 API
    if include_tenant_api:
        try:
            from lurkbot.tenants.api import create_tenant_router

            tenant_router = create_tenant_router()
            app.include_router(tenant_router, prefix="/api/v1")
            logger.info("Tenant API enabled")
        except ImportError:
            logger.debug("Tenant API not available")

    # 监控 API
    if include_monitoring_api:
        try:
            from lurkbot.monitoring.api import create_monitoring_router
            from lurkbot.monitoring.collector import MetricsCollector
            from lurkbot.monitoring.config import MonitoringConfig

            # Create default monitoring components
            monitoring_config = MonitoringConfig()
            metrics_collector = MetricsCollector(
                history_size=monitoring_config.history_size,
                collection_interval=monitoring_config.collection_interval,
            )
            monitoring_router = create_monitoring_router(
                metrics_collector=metrics_collector,
                config=monitoring_config,
            )
            app.include_router(monitoring_router, prefix="/api/v1")
            logger.info("Monitoring API enabled")
        except ImportError:
            logger.debug("Monitoring API not available")

    # 审计 API
    if include_audit_api:
        try:
            from lurkbot.tenants.audit.api import create_audit_router

            audit_router = create_audit_router()
            app.include_router(audit_router, prefix="/api/v1")
            logger.info("Audit API enabled")
        except ImportError:
            logger.debug("Audit API not available")

    # 告警 API
    try:
        from lurkbot.tenants.alerts.api import create_alerts_router

        alerts_router = create_alerts_router()
        app.include_router(alerts_router, prefix="/api/v1")
        logger.info("Alerts API enabled")
    except ImportError:
        logger.debug("Alerts API not available")

    return app


# ============================================================================
# Server Runner
# ============================================================================


async def run_gateway_server(
    host: str | None = None,
    port: int | None = None,
    reload: bool = False,
) -> None:
    """
    运行 Gateway 服务器

    Args:
        host: 绑定地址
        port: 端口
        reload: 是否启用热重载
    """
    import uvicorn

    final_host = host or os.environ.get("LURKBOT_GATEWAY_HOST", "0.0.0.0")
    final_port = port or int(os.environ.get("LURKBOT_GATEWAY_PORT", "18789"))

    logger.info(f"Starting Gateway server at {final_host}:{final_port}")

    config = uvicorn.Config(
        app=create_gateway_app(),
        host=final_host,
        port=final_port,
        log_level="info",
        reload=reload,
    )

    server = uvicorn.Server(config)
    await server.serve()


def start_gateway_server(
    host: str | None = None,
    port: int | None = None,
    reload: bool = False,
) -> None:
    """
    同步启动 Gateway 服务器

    Args:
        host: 绑定地址
        port: 端口
        reload: 是否启用热重载
    """
    import asyncio

    asyncio.run(run_gateway_server(host=host, port=port, reload=reload))


# ============================================================================
# Default App Instance
# ============================================================================

app = create_gateway_app()


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    "app",
    "create_gateway_app",
    "run_gateway_server",
    "start_gateway_server",
    "HealthStatus",
    "ReadinessStatus",
    "GatewayAppState",
    "state",
]
