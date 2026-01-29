"""
Gateway 协议帧结构定义

对标 MoltBot src/gateway/protocol/schema/frames.ts
"""

from enum import Enum
from typing import Literal
from pydantic import BaseModel, Field


class ErrorCode(str, Enum):
    """错误码枚举"""

    NOT_LINKED = "NOT_LINKED"  # 认证提供商未连接
    NOT_PAIRED = "NOT_PAIRED"  # 设备未配对
    AGENT_TIMEOUT = "AGENT_TIMEOUT"  # 代理操作超时
    INVALID_REQUEST = "INVALID_REQUEST"  # 无效请求
    UNAVAILABLE = "UNAVAILABLE"  # 服务暂时不可用
    METHOD_NOT_FOUND = "METHOD_NOT_FOUND"  # 方法不存在
    INTERNAL_ERROR = "INTERNAL_ERROR"  # 内部错误


class ErrorShape(BaseModel):
    """错误结构"""

    code: ErrorCode
    message: str
    details: dict | None = None


class ClientInfo(BaseModel):
    """客户端信息"""

    id: str
    display_name: str | None = Field(None, alias="displayName")
    version: str
    platform: str
    mode: Literal["app", "web", "cli"]

    class Config:
        populate_by_name = True


class ConnectParams(BaseModel):
    """连接参数 (hello 握手)"""

    min_protocol: int = Field(alias="minProtocol")
    max_protocol: int = Field(alias="maxProtocol")
    client: ClientInfo
    caps: list[str] | None = None
    auth: dict[str, str] | None = None  # token, password

    class Config:
        populate_by_name = True


class ServerInfo(BaseModel):
    """服务器信息"""

    version: str
    host: str | None = None
    conn_id: str = Field(alias="connId")

    class Config:
        populate_by_name = True


class Features(BaseModel):
    """服务器功能列表"""

    methods: list[str]
    events: list[str]


class Snapshot(BaseModel):
    """初始快照数据"""

    sessions: list[dict] = []
    cron_jobs: list[dict] = Field([], alias="cronJobs")
    channels: list[dict] = []

    class Config:
        populate_by_name = True


class HelloOk(BaseModel):
    """Hello OK 响应帧"""

    type: Literal["hello-ok"] = "hello-ok"
    protocol: int
    server: ServerInfo
    features: Features
    snapshot: Snapshot


class EventFrame(BaseModel):
    """事件帧"""

    id: str
    type: Literal["event"] = "event"
    at: int  # timestamp ms
    event: str
    payload: dict | None = None
    session_key: str | None = Field(None, alias="sessionKey")

    class Config:
        populate_by_name = True


class RequestFrame(BaseModel):
    """请求帧"""

    id: str
    type: Literal["request"] = "request"
    method: str
    params: dict | None = None
    session_key: str | None = Field(None, alias="sessionKey")

    class Config:
        populate_by_name = True


class ResponseFrame(BaseModel):
    """响应帧"""

    id: str
    type: Literal["response"] = "response"
    result: dict | None = None
    error: ErrorShape | None = None
