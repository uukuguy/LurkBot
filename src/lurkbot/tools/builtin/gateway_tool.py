"""Gateway tool for Gateway API communication.

Ported from moltbot/src/agents/tools/gateway-tool.ts

This tool provides a bridge to the Gateway WebSocket API, allowing
the agent to make RPC calls to the gateway server for:
- Session management
- Cron job control
- Channel operations
- Configuration management
- System information
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from lurkbot.tools.builtin.common import (
    ToolResult,
    error_result,
    json_result,
    text_result,
)


# =============================================================================
# Type Definitions (from moltbot/src/gateway/protocol)
# =============================================================================


class GatewayError(BaseModel):
    """Gateway error response."""

    code: str
    message: str
    details: dict[str, Any] | None = None


class GatewayRequest(BaseModel):
    """Gateway RPC request."""

    id: str = Field(default_factory=lambda: str(uuid4())[:8])
    type: Literal["request"] = "request"
    method: str
    params: dict[str, Any] | None = None
    session_key: str | None = Field(default=None, alias="sessionKey")

    class Config:
        populate_by_name = True


class GatewayResponse(BaseModel):
    """Gateway RPC response."""

    id: str
    type: Literal["response"] = "response"
    result: Any | None = None
    error: GatewayError | None = None


# =============================================================================
# Gateway Tool Parameters
# =============================================================================


class GatewayParams(BaseModel):
    """Parameters for gateway tool.

    Matches moltbot gateway tool schema.
    """

    method: str
    params: dict[str, Any] | None = None
    timeout_ms: int | None = Field(default=30000, alias="timeoutMs")

    class Config:
        populate_by_name = True


# =============================================================================
# Gateway Connection State
# =============================================================================


class GatewayConnection:
    """Gateway connection state and management.

    Note: Full implementation uses WebSocket connection.
    This is a placeholder for local development.
    """

    def __init__(self, url: str | None = None):
        self.url = url
        self.connected = False
        self._pending: dict[str, asyncio.Future] = {}

    async def connect(self) -> bool:
        """Connect to gateway server."""
        # TODO: Implement WebSocket connection
        self.connected = True
        return True

    async def disconnect(self) -> None:
        """Disconnect from gateway server."""
        self.connected = False
        for future in self._pending.values():
            if not future.done():
                future.cancel()
        self._pending.clear()

    async def call(
        self,
        method: str,
        params: dict[str, Any] | None = None,
        timeout_ms: int = 30000,
    ) -> dict[str, Any]:
        """Make an RPC call to the gateway.

        Args:
            method: RPC method name (e.g., "agents.list", "cron.status")
            params: Method parameters
            timeout_ms: Timeout in milliseconds

        Returns:
            Response result dict

        Raises:
            Exception: If call fails or times out
        """
        request_id = str(uuid4())[:8]

        # In full implementation, this would:
        # 1. Send request over WebSocket
        # 2. Wait for matching response
        # 3. Handle timeout

        # For now, simulate local handling for common methods
        result = await self._handle_local(method, params)
        if result is not None:
            return result

        # Fall back to error for unhandled methods
        raise Exception(f"Gateway not connected or method not implemented: {method}")

    async def _handle_local(
        self, method: str, params: dict[str, Any] | None
    ) -> dict[str, Any] | None:
        """Handle method locally if possible.

        This is a placeholder for when gateway is not connected.
        In production, all calls go through the WebSocket.
        """
        # Parse method namespace
        parts = method.split(".")
        if len(parts) != 2:
            return None

        namespace, action = parts

        match namespace:
            case "agents":
                return self._handle_agents(action, params)
            case "sessions":
                return self._handle_sessions(action, params)
            case "cron":
                return self._handle_cron(action, params)
            case "config":
                return self._handle_config(action, params)
            case "channels":
                return self._handle_channels(action, params)
            case "models":
                return self._handle_models(action, params)
            case _:
                return None

    def _handle_agents(
        self, action: str, params: dict[str, Any] | None
    ) -> dict[str, Any] | None:
        """Handle agents.* methods locally."""
        match action:
            case "list":
                return {
                    "agents": [
                        {
                            "id": "main",
                            "name": "Main Agent",
                            "status": "idle",
                        }
                    ]
                }
            case "identity":
                return {
                    "agentId": params.get("agentId", "main") if params else "main",
                    "name": "LurkBot",
                    "emoji": "🤖",
                }
            case _:
                return None

    def _handle_sessions(
        self, action: str, params: dict[str, Any] | None
    ) -> dict[str, Any] | None:
        """Handle sessions.* methods locally."""
        match action:
            case "list":
                return {
                    "sessions": [],
                    "count": 0,
                }
            case _:
                return None

    def _handle_cron(
        self, action: str, params: dict[str, Any] | None
    ) -> dict[str, Any] | None:
        """Handle cron.* methods locally."""
        match action:
            case "status":
                return {
                    "running": True,
                    "jobCount": 0,
                }
            case "list":
                return {
                    "jobs": [],
                    "count": 0,
                }
            case _:
                return None

    def _handle_config(
        self, action: str, params: dict[str, Any] | None
    ) -> dict[str, Any] | None:
        """Handle config.* methods locally."""
        match action:
            case "get":
                return {
                    "config": {},
                }
            case "schema":
                return {
                    "schema": {},
                }
            case _:
                return None

    def _handle_channels(
        self, action: str, params: dict[str, Any] | None
    ) -> dict[str, Any] | None:
        """Handle channels.* methods locally."""
        match action:
            case "status":
                return {
                    "channels": [],
                }
            case _:
                return None

    def _handle_models(
        self, action: str, params: dict[str, Any] | None
    ) -> dict[str, Any] | None:
        """Handle models.* methods locally."""
        match action:
            case "list":
                return {
                    "models": [
                        {
                            "id": "claude-opus-4-5-20251101",
                            "name": "Claude Opus 4.5",
                            "provider": "anthropic",
                        },
                        {
                            "id": "claude-sonnet-4-20250514",
                            "name": "Claude Sonnet 4",
                            "provider": "anthropic",
                        },
                        {
                            "id": "gpt-4o",
                            "name": "GPT-4o",
                            "provider": "openai",
                        },
                    ]
                }
            case _:
                return None


# Global gateway connection
_gateway: GatewayConnection | None = None


def get_gateway() -> GatewayConnection:
    """Get the global gateway connection."""
    global _gateway
    if _gateway is None:
        _gateway = GatewayConnection()
    return _gateway


def configure_gateway(url: str) -> None:
    """Configure the gateway connection URL."""
    global _gateway
    _gateway = GatewayConnection(url)


# =============================================================================
# Gateway Tool Implementation
# =============================================================================


async def gateway_tool(params: dict[str, Any]) -> ToolResult:
    """Execute gateway RPC calls.

    Args:
        params: Tool parameters containing 'method' and optional 'params'

    Returns:
        ToolResult with RPC result or error
    """
    try:
        gw_params = GatewayParams.model_validate(params)
    except Exception as e:
        return error_result(f"Invalid parameters: {e}")

    gateway = get_gateway()

    try:
        result = await gateway.call(
            method=gw_params.method,
            params=gw_params.params,
            timeout_ms=gw_params.timeout_ms or 30000,
        )
        return json_result(result)

    except asyncio.TimeoutError:
        return error_result(f"Gateway call timed out: {gw_params.method}")
    except Exception as e:
        return error_result(f"Gateway call failed: {e}")


# =============================================================================
# Convenience Functions
# =============================================================================


async def call_gateway(
    method: str,
    params: dict[str, Any] | None = None,
    timeout_ms: int = 30000,
) -> dict[str, Any]:
    """Convenience function for making gateway calls.

    Args:
        method: RPC method name
        params: Method parameters
        timeout_ms: Timeout in milliseconds

    Returns:
        Response result dict
    """
    gateway = get_gateway()
    return await gateway.call(method, params, timeout_ms)


# =============================================================================
# Tool Factory Function
# =============================================================================


def create_gateway_tool() -> tuple[str, str, dict[str, Any], Any]:
    """Create the gateway tool definition.

    Returns:
        Tuple of (name, description, schema, handler)
    """
    name = "gateway"
    description = """Make RPC calls to the Gateway API.

Available method namespaces:
- agents.*: Agent management (list, identity)
- sessions.*: Session management (list, history, send, spawn)
- cron.*: Cron job control (status, list, add, update, remove, run)
- config.*: Configuration (get, schema, apply, set)
- channels.*: Channel status and control
- models.*: Model listing
- device-pair.*: Device pairing
- logs.*: Log tailing

Examples:
- List agents: {"method": "agents.list"}
- Get cron status: {"method": "cron.status"}
- List models: {"method": "models.list"}
- Get config: {"method": "config.get", "params": {"key": "general"}}"""

    schema = {
        "type": "object",
        "properties": {
            "method": {
                "type": "string",
                "description": "RPC method name (e.g., 'agents.list', 'cron.status')",
            },
            "params": {
                "type": "object",
                "description": "Method parameters (optional)",
            },
            "timeoutMs": {
                "type": "number",
                "description": "Timeout in milliseconds (default: 30000)",
            },
        },
        "required": ["method"],
    }

    return name, description, schema, gateway_tool
