"""
Gateway 协议定义

对标 MoltBot src/gateway/protocol/
"""

from lurkbot.gateway.protocol.frames import (
    ConnectParams,
    HelloOk,
    EventFrame,
    RequestFrame,
    ResponseFrame,
    ErrorCode,
    ErrorShape,
    ClientInfo,
    ServerInfo,
    Features,
    Snapshot,
)

__all__ = [
    "ConnectParams",
    "HelloOk",
    "EventFrame",
    "RequestFrame",
    "ResponseFrame",
    "ErrorCode",
    "ErrorShape",
    "ClientInfo",
    "ServerInfo",
    "Features",
    "Snapshot",
]
