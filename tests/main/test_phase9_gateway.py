"""
Phase 9: Gateway WebSocket 协议测试

测试模块:
1. Protocol Frames (协议帧结构)
2. Event Broadcaster (事件广播)
3. Method Registry (RPC 方法注册)
4. Gateway Server (WebSocket 服务器)
"""

import pytest
import time
from lurkbot.gateway.protocol.frames import (
    ErrorCode,
    ErrorShape,
    ClientInfo,
    ConnectParams,
    ServerInfo,
    Features,
    Snapshot,
    HelloOk,
    EventFrame,
    RequestFrame,
    ResponseFrame,
)


class TestProtocolFrames:
    """测试协议帧结构"""

    def test_error_code_enum(self):
        """测试错误码枚举"""
        assert ErrorCode.NOT_LINKED == "NOT_LINKED"
        assert ErrorCode.AGENT_TIMEOUT == "AGENT_TIMEOUT"
        assert ErrorCode.METHOD_NOT_FOUND == "METHOD_NOT_FOUND"

    def test_error_shape(self):
        """测试错误结构"""
        error = ErrorShape(
            code=ErrorCode.INVALID_REQUEST,
            message="Invalid parameter",
            details={"param": "missing_field"},
        )
        assert error.code == ErrorCode.INVALID_REQUEST
        assert error.message == "Invalid parameter"
        assert error.details["param"] == "missing_field"

    def test_client_info(self):
        """测试客户端信息"""
        client = ClientInfo(
            id="client-123",
            display_name="Test Client",
            version="1.0.0",
            platform="darwin",
            mode="cli",
        )
        assert client.id == "client-123"
        assert client.mode == "cli"

        # 测试别名
        data = client.model_dump(by_alias=True)
        assert "displayName" in data

    def test_event_frame(self):
        """测试事件帧"""
        event = EventFrame(
            id="evt_001",
            at=int(time.time() * 1000),
            event="agent.response",
            payload={"text": "Hello"},
            session_key="agent:test:main",
        )
        assert event.type == "event"
        assert event.event == "agent.response"

    def test_request_frame(self):
        """测试请求帧"""
        request = RequestFrame(
            id="req_001",
            method="agents.list",
            params={"filter": "active"},
            session_key="agent:test:main",
        )
        assert request.type == "request"
        assert request.method == "agents.list"

    def test_response_frame_success(self):
        """测试成功响应帧"""
        response = ResponseFrame(
            id="req_001",
            result={"agents": []},
        )
        assert response.type == "response"
        assert response.result is not None
        assert response.error is None

    def test_response_frame_error(self):
        """测试错误响应帧"""
        response = ResponseFrame(
            id="req_001",
            error=ErrorShape(
                code=ErrorCode.METHOD_NOT_FOUND,
                message="Method not found",
            ),
        )
        assert response.error is not None
        assert response.result is None


class TestEventBroadcaster:
    """测试事件广播器"""

    @pytest.mark.asyncio
    async def test_emit_event(self):
        """测试发送事件"""
        from lurkbot.gateway.events import EventBroadcaster

        broadcaster = EventBroadcaster()
        event = await broadcaster.emit("test.event", payload={"key": "value"})

        assert event.event == "test.event"
        assert event.payload["key"] == "value"

    @pytest.mark.asyncio
    async def test_event_subscription(self):
        """测试事件订阅"""
        from lurkbot.gateway.events import EventBroadcaster

        broadcaster = EventBroadcaster()
        received_events = []

        async def callback(event):
            received_events.append(event)

        subscriber = broadcaster.subscribe(callback)
        await broadcaster.emit("test.event")

        # 等待事件传递
        import asyncio

        await asyncio.sleep(0.01)

        assert len(received_events) == 1
        assert received_events[0].event == "test.event"


class TestMethodRegistry:
    """测试 RPC 方法注册"""

    @pytest.mark.asyncio
    async def test_register_and_invoke(self):
        """测试注册和调用方法"""
        from lurkbot.gateway.methods import MethodRegistry, MethodContext

        registry = MethodRegistry()

        async def test_method(ctx: MethodContext):
            return {"result": "success"}

        registry.register("test.method", test_method)
        result = await registry.invoke("test.method")

        assert result["result"] == "success"

    @pytest.mark.asyncio
    async def test_method_not_found(self):
        """测试方法不存在"""
        from lurkbot.gateway.methods import MethodRegistry

        registry = MethodRegistry()

        with pytest.raises(ValueError, match="Method not found"):
            await registry.invoke("non.existent.method")

    def test_list_methods(self):
        """测试列出方法"""
        from lurkbot.gateway.methods import MethodRegistry, MethodContext

        registry = MethodRegistry()

        async def method1(ctx):
            pass

        async def method2(ctx):
            pass

        registry.register("method1", method1)
        registry.register("method2", method2)

        methods = registry.list_methods()
        assert "method1" in methods
        assert "method2" in methods

