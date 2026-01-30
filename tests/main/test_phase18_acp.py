"""
Phase 18: ACP 协议系统测试

测试 ACP (Agent Client Protocol) 协议的核心功能：
- 类型定义验证
- 会话管理
- 事件映射
- 协议翻译
- 服务器功能
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ============================================================================
# ACP 类型定义测试
# ============================================================================


class TestACPTypes:
    """ACP 类型定义测试"""

    def test_text_content_block(self):
        """测试文本内容块"""
        from lurkbot.acp import TextContentBlock

        block = TextContentBlock(text="Hello, World!")
        assert block.type == "text"
        assert block.text == "Hello, World!"

        # 序列化
        data = block.model_dump()
        assert data["type"] == "text"
        assert data["text"] == "Hello, World!"

    def test_image_content_block(self):
        """测试图片内容块"""
        from lurkbot.acp import ImageContentBlock

        block = ImageContentBlock(data="base64data", media_type="image/png")
        assert block.type == "image"
        assert block.data == "base64data"
        assert block.media_type == "image/png"

        # 序列化时使用别名
        data = block.model_dump(by_alias=True)
        assert data["mediaType"] == "image/png"

    def test_implementation(self):
        """测试实现信息"""
        from lurkbot.acp import Implementation

        impl = Implementation(name="test-agent", title="Test Agent", version="1.0.0")
        assert impl.name == "test-agent"
        assert impl.title == "Test Agent"
        assert impl.version == "1.0.0"

    def test_agent_capabilities(self):
        """测试 Agent 能力"""
        from lurkbot.acp import AgentCapabilities, PromptCapabilities

        caps = AgentCapabilities(
            load_session=True,
            prompt_capabilities=PromptCapabilities(image=True, audio=False),
        )
        assert caps.load_session is True
        assert caps.prompt_capabilities.image is True
        assert caps.prompt_capabilities.audio is False

    def test_mcp_server_types(self):
        """测试 MCP 服务器类型"""
        from lurkbot.acp import McpServerStdio, HttpMcpServer, SseMcpServer

        # Stdio
        stdio = McpServerStdio(command="python", args=["-m", "mcp"])
        assert stdio.type == "stdio"
        assert stdio.command == "python"

        # HTTP
        http = HttpMcpServer(url="http://localhost:8080")
        assert http.type == "http"
        assert http.url == "http://localhost:8080"

        # SSE
        sse = SseMcpServer(url="http://localhost:8081/sse")
        assert sse.type == "sse"


class TestACPRequests:
    """ACP 请求/响应类型测试"""

    def test_initialize_request_response(self):
        """测试初始化请求响应"""
        from lurkbot.acp import (
            InitializeRequest,
            InitializeResponse,
            Implementation,
            AgentCapabilities,
            PROTOCOL_VERSION,
        )

        # 请求
        req = InitializeRequest(protocol_version=1)
        assert req.protocol_version == 1

        # 响应
        resp = InitializeResponse(
            protocol_version=PROTOCOL_VERSION,
            agent_info=Implementation(name="lurkbot", version="0.1.0"),
            agent_capabilities=AgentCapabilities(load_session=True),
        )
        assert resp.protocol_version == PROTOCOL_VERSION

    def test_new_session_request_response(self):
        """测试新建会话请求响应"""
        from lurkbot.acp import NewSessionRequest, NewSessionResponse, ModeInfo

        req = NewSessionRequest(cwd="/home/user/project")
        assert req.cwd == "/home/user/project"

        resp = NewSessionResponse(
            session_id="abc123",
            modes=[ModeInfo(id="default", title="Default")],
        )
        assert resp.session_id == "abc123"
        assert len(resp.modes) == 1

    def test_prompt_request_response(self):
        """测试 Prompt 请求响应"""
        from lurkbot.acp import (
            PromptRequest,
            PromptResponse,
            TextContentBlock,
            StopReason,
        )

        req = PromptRequest(
            session_id="abc123",
            prompt=[TextContentBlock(text="Hello")],
        )
        assert req.session_id == "abc123"
        assert len(req.prompt) == 1

        resp = PromptResponse(stop_reason=StopReason.END_TURN)
        assert resp.stop_reason == StopReason.END_TURN

    def test_session_notification(self):
        """测试会话通知"""
        from lurkbot.acp import (
            SessionNotification,
            AgentMessageChunk,
            TextContentBlock,
        )

        content = TextContentBlock(text="Response")
        update = AgentMessageChunk(content=content)
        notification = SessionNotification(session_id="abc123", update=update)

        assert notification.session_id == "abc123"
        assert notification.update.type == "agentMessage"


# ============================================================================
# ACP 会话管理测试
# ============================================================================


class TestACPSessionManager:
    """ACP 会话管理测试"""

    def test_create_session(self):
        """测试创建会话"""
        from lurkbot.acp import ACPSessionManager

        manager = ACPSessionManager()
        session = manager.create_session(cwd="/home/user")

        assert session.session_id is not None
        assert session.cwd == "/home/user"
        assert session.status == "idle"
        assert session.active_run_id is None

    def test_get_session(self):
        """测试获取会话"""
        from lurkbot.acp import ACPSessionManager

        manager = ACPSessionManager()
        session = manager.create_session(cwd="/test")

        retrieved = manager.get_session(session.session_id)
        assert retrieved is not None
        assert retrieved.session_id == session.session_id

        # 不存在的会话
        assert manager.get_session("nonexistent") is None

    def test_load_session(self):
        """测试加载会话"""
        from lurkbot.acp import ACPSessionManager

        manager = ACPSessionManager()
        session = manager.create_session(cwd="/old/path")
        session_id = session.session_id

        # 加载并更新 cwd
        loaded = manager.load_session(session_id, "/new/path")
        assert loaded is not None
        assert loaded.cwd == "/new/path"

    def test_delete_session(self):
        """测试删除会话"""
        from lurkbot.acp import ACPSessionManager

        manager = ACPSessionManager()
        session = manager.create_session(cwd="/test")
        session_id = session.session_id

        assert manager.delete_session(session_id) is True
        assert manager.get_session(session_id) is None
        assert manager.delete_session(session_id) is False  # 已删除

    def test_set_active_run(self):
        """测试设置活跃运行"""
        from lurkbot.acp import ACPSessionManager

        manager = ACPSessionManager()
        session = manager.create_session(cwd="/test")

        manager.set_active_run(session.session_id, "run-123")
        assert session.active_run_id == "run-123"
        assert session.status == "active"

        manager.set_active_run(session.session_id, None)
        assert session.active_run_id is None
        assert session.status == "idle"

    def test_cancel_session(self):
        """测试取消会话"""
        from lurkbot.acp import ACPSessionManager

        manager = ACPSessionManager()
        session = manager.create_session(cwd="/test")
        manager.set_active_run(session.session_id, "run-123")

        assert manager.cancel_session(session.session_id) is True
        assert session.status == "cancelled"
        assert session.active_run_id is None

    def test_set_mode_and_model(self):
        """测试设置模式和模型"""
        from lurkbot.acp import ACPSessionManager

        manager = ACPSessionManager()
        session = manager.create_session(cwd="/test")

        assert manager.set_mode(session.session_id, "code") is True
        assert session.mode_id == "code"

        assert manager.set_model(session.session_id, "claude-3") is True
        assert session.model_id == "claude-3"

    def test_list_sessions(self):
        """测试列出会话"""
        from lurkbot.acp import ACPSessionManager

        manager = ACPSessionManager()
        manager.create_session(cwd="/test1")
        manager.create_session(cwd="/test2")

        sessions = manager.list_sessions()
        assert len(sessions) == 2

    @pytest.mark.asyncio
    async def test_pending_prompts(self):
        """测试待处理 Prompt"""
        from lurkbot.acp import ACPSessionManager

        manager = ACPSessionManager()
        session = manager.create_session(cwd="/test")

        # 创建待处理 Prompt
        pending = await manager.create_pending_prompt(session.session_id)
        assert pending.prompt_id is not None
        assert pending.session_id == session.session_id

        # 解决 Prompt
        result = {"stopReason": "end_turn"}
        assert await manager.resolve_prompt(pending.prompt_id, result) is True

        # 等待结果
        received = await pending.future
        assert received == result


# ============================================================================
# ACP 事件映射测试
# ============================================================================


class TestACPEventMapper:
    """ACP 事件映射测试"""

    @pytest.mark.asyncio
    async def test_map_agent_message_event(self):
        """测试映射 Agent 消息事件"""
        from lurkbot.acp import EventMapper
        from lurkbot.gateway.protocol.frames import EventFrame

        mapper = EventMapper()
        event = EventFrame(
            id="evt_001",
            at=1000000,
            event="agent.message.delta",
            payload={"content": "Hello"},
        )

        notification = await mapper.map_gateway_event(event, "session-123")
        assert notification is not None
        assert notification.session_id == "session-123"
        assert notification.update.type == "agentMessage"

    @pytest.mark.asyncio
    async def test_map_thinking_event(self):
        """测试映射思考事件"""
        from lurkbot.acp import EventMapper
        from lurkbot.gateway.protocol.frames import EventFrame

        mapper = EventMapper()
        event = EventFrame(
            id="evt_002",
            at=1000000,
            event="agent.thinking.delta",
            payload={"thinking": "Let me think..."},
        )

        notification = await mapper.map_gateway_event(event, "session-123")
        assert notification is not None
        assert notification.update.type == "agentThought"

    @pytest.mark.asyncio
    async def test_map_tool_start_event(self):
        """测试映射工具调用开始事件"""
        from lurkbot.acp import EventMapper
        from lurkbot.gateway.protocol.frames import EventFrame

        mapper = EventMapper()
        event = EventFrame(
            id="evt_003",
            at=1000000,
            event="agent.tool.start",
            payload={
                "toolCallId": "tc-001",
                "toolName": "read_file",
                "toolInput": {"path": "/test.txt"},
            },
        )

        notification = await mapper.map_gateway_event(event, "session-123")
        assert notification is not None
        assert notification.update.type == "toolCallStart"

    @pytest.mark.asyncio
    async def test_map_unknown_event(self):
        """测试未知事件"""
        from lurkbot.acp import EventMapper
        from lurkbot.gateway.protocol.frames import EventFrame

        mapper = EventMapper()
        event = EventFrame(
            id="evt_004",
            at=1000000,
            event="unknown.event",
            payload={},
        )

        notification = await mapper.map_gateway_event(event, "session-123")
        assert notification is None


class TestACPHelperFunctions:
    """ACP 辅助函数测试"""

    def test_text_block(self):
        """测试 text_block 辅助函数"""
        from lurkbot.acp import text_block

        block = text_block("Hello")
        assert block.type == "text"
        assert block.text == "Hello"

    def test_update_agent_message(self):
        """测试 update_agent_message 辅助函数"""
        from lurkbot.acp import text_block, update_agent_message

        content = text_block("Response")
        update = update_agent_message(content)
        assert update.type == "agentMessage"
        assert update.content.text == "Response"

    def test_start_tool_call(self):
        """测试 start_tool_call 辅助函数"""
        from lurkbot.acp import start_tool_call

        update = start_tool_call("tc-001", "read_file", {"path": "/test"})
        assert update.type == "toolCallStart"
        assert update.tool_call_id == "tc-001"
        assert update.tool_name == "read_file"

    def test_plan_entry_and_update(self):
        """测试计划相关辅助函数"""
        from lurkbot.acp import plan_entry, update_plan

        entry1 = plan_entry("1", "Step 1", "completed")
        entry2 = plan_entry("2", "Step 2", "in_progress")

        update = update_plan([entry1, entry2])
        assert update.type == "planUpdate"
        assert len(update.entries) == 2


# ============================================================================
# ACP 翻译器测试
# ============================================================================


class TestACPTranslator:
    """ACP 翻译器测试"""

    def test_extract_prompt_text(self):
        """测试提取 Prompt 文本"""
        from lurkbot.acp import ACPGatewayTranslator, TextContentBlock

        translator = ACPGatewayTranslator()

        # TextContentBlock 对象
        blocks = [
            TextContentBlock(text="Hello"),
            TextContentBlock(text="World"),
        ]
        text = translator._extract_prompt_text(blocks)
        assert text == "Hello\nWorld"

        # 字典形式
        dict_blocks = [
            {"type": "text", "text": "Foo"},
            {"type": "text", "text": "Bar"},
        ]
        text = translator._extract_prompt_text(dict_blocks)
        assert text == "Foo\nBar"

    @pytest.mark.asyncio
    async def test_subscribe_unsubscribe_events(self):
        """测试事件订阅和取消"""
        from lurkbot.acp import ACPGatewayTranslator, get_session_manager

        translator = ACPGatewayTranslator()
        session_manager = get_session_manager()
        session = session_manager.create_session(cwd="/test")

        callback = AsyncMock()
        await translator.subscribe_to_events(session.session_id, callback)

        # 验证订阅
        assert session.session_id in translator._active_subscriptions

        # 取消订阅
        await translator.unsubscribe_from_events(session.session_id)
        assert session.session_id not in translator._active_subscriptions


# ============================================================================
# ACP 服务器测试
# ============================================================================


class TestACPServer:
    """ACP 服务器测试"""

    def test_server_creation(self):
        """测试服务器创建"""
        from lurkbot.acp import ACPServer

        server = ACPServer()
        assert server.AGENT_NAME == "LurkBot"
        assert server._initialized is False
        assert server._running is False

    @pytest.mark.asyncio
    async def test_handle_initialize(self):
        """测试处理初始化请求"""
        from lurkbot.acp import ACPServer, PROTOCOL_VERSION

        server = ACPServer()

        params = {"protocolVersion": 1}
        result = await server._handle_initialize(params)

        assert result is not None
        assert result["protocolVersion"] == PROTOCOL_VERSION
        assert "agentInfo" in result
        assert "agentCapabilities" in result
        assert server._initialized is True

    @pytest.mark.asyncio
    async def test_handle_new_session(self):
        """测试处理新建会话请求"""
        from lurkbot.acp import ACPServer

        server = ACPServer()

        params = {"cwd": "/home/user/project", "mcpServers": []}
        result = await server._handle_new_session(params)

        assert result is not None
        assert "sessionId" in result
        assert "modes" in result

    @pytest.mark.asyncio
    async def test_handle_load_session(self):
        """测试处理加载会话请求"""
        from lurkbot.acp import ACPServer, get_session_manager

        server = ACPServer()
        session_manager = get_session_manager()

        # 先创建会话
        session = session_manager.create_session(cwd="/old")

        params = {"sessionId": session.session_id, "cwd": "/new"}
        result = await server._handle_load_session(params)

        assert result is not None
        assert "modes" in result

    @pytest.mark.asyncio
    async def test_handle_set_mode(self):
        """测试处理设置模式请求"""
        from lurkbot.acp import ACPServer, get_session_manager

        server = ACPServer()
        session_manager = get_session_manager()
        session = session_manager.create_session(cwd="/test")

        params = {"sessionId": session.session_id, "modeId": "code"}
        result = await server._handle_set_mode(params)

        assert result is not None
        assert session.mode_id == "code"

    @pytest.mark.asyncio
    async def test_dispatch_unknown_method(self):
        """测试分发未知方法"""
        from lurkbot.acp import ACPServer

        server = ACPServer()

        with pytest.raises(ValueError, match="Method not found"):
            await server._dispatch_method("unknown/method", {})

    @pytest.mark.asyncio
    async def test_dispatch_extension_method(self):
        """测试分发扩展方法"""
        from lurkbot.acp import ACPServer

        server = ACPServer()

        # 扩展方法以 _ 开头
        result = await server._dispatch_method("_custom/method", {})
        assert result == {}


class TestACPGlobalFunctions:
    """ACP 全局函数测试"""

    def test_get_acp_server(self):
        """测试获取全局 ACP 服务器"""
        from lurkbot.acp import get_acp_server

        server1 = get_acp_server()
        server2 = get_acp_server()
        assert server1 is server2  # 应该是同一个实例

    def test_get_session_manager(self):
        """测试获取全局会话管理器"""
        from lurkbot.acp import get_session_manager

        manager1 = get_session_manager()
        manager2 = get_session_manager()
        assert manager1 is manager2

    def test_get_event_mapper(self):
        """测试获取全局事件映射器"""
        from lurkbot.acp import get_event_mapper

        mapper1 = get_event_mapper()
        mapper2 = get_event_mapper()
        assert mapper1 is mapper2

    def test_get_translator(self):
        """测试获取全局翻译器"""
        from lurkbot.acp import get_translator

        translator1 = get_translator()
        translator2 = get_translator()
        assert translator1 is translator2


# ============================================================================
# ACP 集成测试
# ============================================================================


class TestACPIntegration:
    """ACP 集成测试"""

    @pytest.mark.asyncio
    async def test_full_session_lifecycle(self):
        """测试完整会话生命周期"""
        from lurkbot.acp import (
            ACPServer,
            ACPSessionManager,
            TextContentBlock,
        )

        # 创建服务器和会话管理器
        server = ACPServer()
        manager = ACPSessionManager()

        # 1. 初始化
        init_result = await server._handle_initialize({"protocolVersion": 1})
        assert init_result["protocolVersion"] == 1

        # 2. 创建会话
        session = manager.create_session(cwd="/project")
        assert session.status == "idle"

        # 3. 设置模式
        manager.set_mode(session.session_id, "code")
        assert session.mode_id == "code"

        # 4. 设置活跃运行
        manager.set_active_run(session.session_id, "run-001")
        assert session.status == "active"

        # 5. 取消
        manager.cancel_session(session.session_id)
        assert session.status == "cancelled"

        # 6. 删除
        manager.delete_session(session.session_id)
        assert manager.get_session(session.session_id) is None

    def test_module_exports(self):
        """测试模块导出"""
        import lurkbot.acp as acp

        # 检查主要类
        assert hasattr(acp, "ACPServer")
        assert hasattr(acp, "ACPSession")
        assert hasattr(acp, "ACPSessionManager")
        assert hasattr(acp, "ACPGatewayTranslator")
        assert hasattr(acp, "EventMapper")

        # 检查类型
        assert hasattr(acp, "TextContentBlock")
        assert hasattr(acp, "ImageContentBlock")
        assert hasattr(acp, "Implementation")
        assert hasattr(acp, "AgentCapabilities")

        # 检查辅助函数
        assert hasattr(acp, "text_block")
        assert hasattr(acp, "update_agent_message")
        assert hasattr(acp, "start_tool_call")

        # 检查全局函数
        assert hasattr(acp, "get_acp_server")
        assert hasattr(acp, "get_session_manager")
        assert hasattr(acp, "run_acp_server")
