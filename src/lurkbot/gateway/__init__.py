"""Gateway protocol and server.

This module contains gateway infrastructure:
- protocol.py: Protocol frame definitions (RequestFrame, ResponseFrame, EventFrame)
- server.py: WebSocket server
- client.py: Gateway client
- app.py: FastAPI application with health checks
"""

from lurkbot.gateway.app import (
    GatewayAppState,
    HealthStatus,
    ReadinessStatus,
    app,
    create_gateway_app,
    run_gateway_server,
    start_gateway_server,
    state,
)
from lurkbot.gateway.server import GatewayConnection, GatewayServer, get_gateway_server

__all__ = [
    # App
    "app",
    "create_gateway_app",
    "run_gateway_server",
    "start_gateway_server",
    "GatewayAppState",
    "state",
    # Health
    "HealthStatus",
    "ReadinessStatus",
    # Server
    "GatewayServer",
    "GatewayConnection",
    "get_gateway_server",
]
