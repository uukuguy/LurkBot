"""Nodes tool for distributed node management.

Ported from moltbot/src/agents/tools/nodes-tool.ts

This tool provides node discovery and remote command execution:
- Discover nodes via mDNS/Bonjour
- Query node status
- Execute commands on remote nodes
- Manage node presence
"""

from __future__ import annotations

import asyncio
import shlex
import subprocess
import time
from dataclasses import dataclass, field
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
# Type Definitions
# =============================================================================


class NodeInfo(BaseModel):
    """Information about a discovered node."""

    id: str
    name: str
    host: str
    port: int
    version: str | None = None
    platform: str | None = None
    arch: str | None = None
    status: Literal["online", "offline", "busy", "unknown"] = "unknown"
    last_seen_ms: int | None = Field(default=None, alias="lastSeenMs")
    capabilities: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    class Config:
        populate_by_name = True


class NodeExecResult(BaseModel):
    """Result of executing a command on a node."""

    node_id: str = Field(alias="nodeId")
    success: bool
    exit_code: int | None = Field(default=None, alias="exitCode")
    stdout: str | None = None
    stderr: str | None = None
    duration_ms: int | None = Field(default=None, alias="durationMs")
    error: str | None = None

    class Config:
        populate_by_name = True


class NodesParams(BaseModel):
    """Parameters for nodes tool.

    Operations:
    - discover: Find nodes on the network
    - list: List known nodes
    - status: Get status of a specific node
    - exec: Execute command on a node
    - ping: Ping a node
    """

    op: Literal["discover", "list", "status", "exec", "ping"]

    # For status/exec/ping operations
    node_id: str | None = Field(default=None, alias="nodeId")

    # For exec operation
    command: str | None = None
    args: list[str] | None = None
    timeout_ms: int | None = Field(default=30000, alias="timeoutMs")
    cwd: str | None = None

    # For discover operation
    timeout_seconds: int | None = Field(default=5, alias="timeoutSeconds")

    class Config:
        populate_by_name = True


# =============================================================================
# Node Registry
# =============================================================================


@dataclass
class NodeRegistry:
    """Registry of known nodes.

    Note: Full implementation would use mDNS discovery and persistent storage.
    This is a placeholder for local development.
    """

    nodes: dict[str, NodeInfo] = field(default_factory=dict)
    local_node_id: str = field(default_factory=lambda: str(uuid4())[:8])

    def register(self, node: NodeInfo) -> None:
        """Register or update a node."""
        self.nodes[node.id] = node

    def unregister(self, node_id: str) -> bool:
        """Unregister a node."""
        if node_id in self.nodes:
            del self.nodes[node_id]
            return True
        return False

    def get(self, node_id: str) -> NodeInfo | None:
        """Get a node by ID."""
        return self.nodes.get(node_id)

    def list_all(self) -> list[NodeInfo]:
        """List all known nodes."""
        return list(self.nodes.values())

    def get_local(self) -> NodeInfo:
        """Get the local node info."""
        import platform

        return NodeInfo(
            id=self.local_node_id,
            name=platform.node(),
            host="localhost",
            port=0,
            version="0.1.0",
            platform=platform.system().lower(),
            arch=platform.machine(),
            status="online",
            lastSeenMs=int(time.time() * 1000),
            capabilities=["exec", "fs", "web"],
        )


# Global node registry
_registry: NodeRegistry | None = None


def get_node_registry() -> NodeRegistry:
    """Get the global node registry."""
    global _registry
    if _registry is None:
        _registry = NodeRegistry()
    return _registry


# =============================================================================
# Nodes Tool Implementation
# =============================================================================


async def nodes_tool(params: dict[str, Any]) -> ToolResult:
    """Execute nodes tool operations.

    Args:
        params: Tool parameters containing 'op' and operation-specific fields

    Returns:
        ToolResult with operation result or error
    """
    try:
        nodes_params = NodesParams.model_validate(params)
    except Exception as e:
        return error_result(f"Invalid parameters: {e}")

    registry = get_node_registry()

    match nodes_params.op:
        case "discover":
            return await _nodes_discover(registry, nodes_params)
        case "list":
            return _nodes_list(registry)
        case "status":
            return await _nodes_status(registry, nodes_params)
        case "exec":
            return await _nodes_exec(registry, nodes_params)
        case "ping":
            return await _nodes_ping(registry, nodes_params)
        case _:
            return error_result(f"Unknown operation: {nodes_params.op}")


async def _nodes_discover(registry: NodeRegistry, params: NodesParams) -> ToolResult:
    """Discover nodes on the network using mDNS/Bonjour.

    Note: Full implementation requires zeroconf library and network access.
    """
    timeout = params.timeout_seconds or 5

    # TODO: Implement actual mDNS discovery
    # For now, just add the local node and return

    local = registry.get_local()
    registry.register(local)

    # Simulate discovery delay
    await asyncio.sleep(0.1)

    return json_result(
        {
            "discovered": [local.model_dump(by_alias=True, exclude_none=True)],
            "count": 1,
            "timeoutSeconds": timeout,
            "note": "mDNS discovery not implemented, showing local node only",
        }
    )


def _nodes_list(registry: NodeRegistry) -> ToolResult:
    """List all known nodes."""
    nodes = registry.list_all()

    # Always include local node
    local = registry.get_local()
    if local.id not in [n.id for n in nodes]:
        nodes.insert(0, local)

    return json_result(
        {
            "nodes": [n.model_dump(by_alias=True, exclude_none=True) for n in nodes],
            "count": len(nodes),
            "localNodeId": local.id,
        }
    )


async def _nodes_status(registry: NodeRegistry, params: NodesParams) -> ToolResult:
    """Get status of a specific node."""
    if not params.node_id:
        return error_result("Missing required field: nodeId")

    # Check for local node
    local = registry.get_local()
    if params.node_id == local.id or params.node_id == "local":
        return json_result(
            {
                "node": local.model_dump(by_alias=True, exclude_none=True),
                "isLocal": True,
            }
        )

    # Look up in registry
    node = registry.get(params.node_id)
    if not node:
        return error_result(f"Node not found: {params.node_id}")

    # TODO: Actually ping the node to update status
    return json_result(
        {
            "node": node.model_dump(by_alias=True, exclude_none=True),
            "isLocal": False,
        }
    )


async def _nodes_exec(registry: NodeRegistry, params: NodesParams) -> ToolResult:
    """Execute a command on a node."""
    if not params.node_id:
        return error_result("Missing required field: nodeId")
    if not params.command:
        return error_result("Missing required field: command")

    local = registry.get_local()
    is_local = params.node_id == local.id or params.node_id == "local"

    if is_local:
        # Execute locally
        return await _exec_local(params)
    else:
        # Execute on remote node
        node = registry.get(params.node_id)
        if not node:
            return error_result(f"Node not found: {params.node_id}")

        return await _exec_remote(node, params)


async def _exec_local(params: NodesParams) -> ToolResult:
    """Execute command locally using subprocess with proper argument handling.

    Uses subprocess.run with explicit argument list (not shell=True) for security.
    This prevents command injection vulnerabilities.
    """
    start_ms = int(time.time() * 1000)
    timeout_s = (params.timeout_ms or 30000) / 1000

    try:
        # Build command as argument list (safe from shell injection)
        cmd_list = [params.command]
        if params.args:
            cmd_list.extend(params.args)

        # Execute without shell=True for security
        # Note: This means shell features like pipes and redirects won't work
        # If needed, those should be done via explicit piping in Python
        result = subprocess.run(
            cmd_list,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            cwd=params.cwd,
            shell=False,  # Explicitly disable shell for security
        )

        end_ms = int(time.time() * 1000)

        return json_result(
            NodeExecResult(
                nodeId="local",
                success=result.returncode == 0,
                exitCode=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                durationMs=end_ms - start_ms,
            ).model_dump(by_alias=True, exclude_none=True)
        )

    except FileNotFoundError as e:
        return json_result(
            NodeExecResult(
                nodeId="local",
                success=False,
                error=f"Command not found: {params.command}",
            ).model_dump(by_alias=True, exclude_none=True)
        )
    except subprocess.TimeoutExpired:
        return json_result(
            NodeExecResult(
                nodeId="local",
                success=False,
                error="Command timed out",
            ).model_dump(by_alias=True, exclude_none=True)
        )
    except Exception as e:
        return json_result(
            NodeExecResult(
                nodeId="local",
                success=False,
                error=str(e),
            ).model_dump(by_alias=True, exclude_none=True)
        )


async def _exec_remote(node: NodeInfo, params: NodesParams) -> ToolResult:
    """Execute command on a remote node.

    Note: Full implementation would use Gateway WebSocket or SSH.
    """
    # TODO: Implement remote execution via Gateway or SSH
    return json_result(
        NodeExecResult(
            nodeId=node.id,
            success=False,
            error="Remote execution not implemented. Use local node or SSH.",
        ).model_dump(by_alias=True, exclude_none=True)
    )


async def _nodes_ping(registry: NodeRegistry, params: NodesParams) -> ToolResult:
    """Ping a node to check connectivity."""
    if not params.node_id:
        return error_result("Missing required field: nodeId")

    local = registry.get_local()
    is_local = params.node_id == local.id or params.node_id == "local"

    start_ms = int(time.time() * 1000)

    if is_local:
        # Local ping always succeeds
        end_ms = int(time.time() * 1000)
        return json_result(
            {
                "nodeId": params.node_id,
                "reachable": True,
                "latencyMs": end_ms - start_ms,
                "isLocal": True,
            }
        )

    node = registry.get(params.node_id)
    if not node:
        return error_result(f"Node not found: {params.node_id}")

    # TODO: Actually ping the remote node
    # For now, simulate based on last_seen_ms
    end_ms = int(time.time() * 1000)
    is_recent = (
        node.last_seen_ms and (end_ms - node.last_seen_ms) < 60000
    )  # Within 1 minute

    return json_result(
        {
            "nodeId": params.node_id,
            "reachable": is_recent,
            "latencyMs": end_ms - start_ms if is_recent else None,
            "lastSeenMs": node.last_seen_ms,
            "note": "Actual network ping not implemented",
        }
    )


# =============================================================================
# Tool Factory Function
# =============================================================================


def create_nodes_tool() -> tuple[str, str, dict[str, Any], Any]:
    """Create the nodes tool definition.

    Returns:
        Tuple of (name, description, schema, handler)
    """
    name = "nodes"
    description = """Discover and manage distributed nodes.

Operations:
- discover: Find nodes on the network via mDNS/Bonjour
- list: List all known nodes
- status: Get status of a specific node
- exec: Execute a command on a node
- ping: Check node connectivity

Examples:
- Discover nodes: {"op": "discover", "timeoutSeconds": 5}
- List nodes: {"op": "list"}
- Execute locally: {"op": "exec", "nodeId": "local", "command": "ls", "args": ["-la"]}
- Ping node: {"op": "ping", "nodeId": "abc123"}"""

    schema = {
        "type": "object",
        "properties": {
            "op": {
                "type": "string",
                "enum": ["discover", "list", "status", "exec", "ping"],
                "description": "Operation to perform",
            },
            "nodeId": {
                "type": "string",
                "description": "Node ID (use 'local' for local node)",
            },
            "command": {
                "type": "string",
                "description": "Command to execute (for exec operation)",
            },
            "args": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Command arguments (for exec operation)",
            },
            "cwd": {
                "type": "string",
                "description": "Working directory (for exec operation)",
            },
            "timeoutMs": {
                "type": "number",
                "description": "Timeout in milliseconds (for exec operation)",
            },
            "timeoutSeconds": {
                "type": "number",
                "description": "Discovery timeout in seconds (for discover operation)",
            },
        },
        "required": ["op"],
    }

    return name, description, schema, nodes_tool
