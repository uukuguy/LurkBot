"""
Phase 11: A2UI Canvas Host 系统测试

测试范围:
- A2UI 协议定义 (protocol.py)
- Canvas Host 服务器 (server.py)
- Canvas Client 助手 (client.py)
"""

import pytest

from lurkbot.canvas import (
    A2UIState,
    ButtonSurface,
    CallbackAction,
    CanvasHost,
    ContainerSurface,
    DataModelUpdateMessage,
    DeleteSurfaceMessage,
    ImageSurface,
    ResetMessage,
    SurfaceUpdateMessage,
    TextSurface,
    parse_jsonl,
    to_jsonl,
)
from lurkbot.canvas.client import CanvasClient, create_button_surface, create_text_surface


# ============================================================================
# A2UI Protocol Tests
# ============================================================================


class TestA2UIProtocol:
    """测试 A2UI 协议定义"""

    def test_text_surface(self):
        """测试文本 Surface"""
        surface = TextSurface(content="Hello")
        assert surface.type == "text"
        assert surface.content == "Hello"
        assert surface.style is None

    def test_text_surface_with_style(self):
        """测试带样式的文本 Surface"""
        surface = TextSurface(content="Styled", style={"fontSize": "16px", "color": "blue"})
        assert surface.style == {"fontSize": "16px", "color": "blue"}

    def test_image_surface(self):
        """测试图片 Surface"""
        surface = ImageSurface(src="https://example.com/image.png", alt="Test Image", width=100, height=50)
        assert surface.type == "image"
        assert surface.src == "https://example.com/image.png"
        assert surface.alt == "Test Image"
        assert surface.width == 100
        assert surface.height == 50

    def test_button_surface(self):
        """测试按钮 Surface"""
        action = CallbackAction(id="btn_click")
        surface = ButtonSurface(label="Click Me", action=action)
        assert surface.type == "button"
        assert surface.label == "Click Me"
        assert surface.action.type == "callback"
        assert surface.action.id == "btn_click"
        assert surface.disabled is False

    def test_container_surface(self):
        """测试容器 Surface"""
        child1 = TextSurface(content="Item 1")
        child2 = TextSurface(content="Item 2")
        surface = ContainerSurface(direction="row", children=[child1, child2], gap=10)
        assert surface.type == "container"
        assert surface.direction == "row"
        assert len(surface.children) == 2
        assert surface.gap == 10

    def test_surface_update_message(self):
        """测试 SurfaceUpdate 消息"""
        surface = TextSurface(content="Test")
        message = SurfaceUpdateMessage(surface_id="main", surface=surface)
        assert message.type == "surfaceUpdate"
        assert message.surface_id == "main"
        assert message.surface == surface

    def test_data_model_update_message(self):
        """测试 DataModelUpdate 消息"""
        message = DataModelUpdateMessage(path="user.name", value="Alice")
        assert message.type == "dataModelUpdate"
        assert message.path == "user.name"
        assert message.value == "Alice"

    def test_delete_surface_message(self):
        """测试 DeleteSurface 消息"""
        message = DeleteSurfaceMessage(surface_id="temp")
        assert message.type == "deleteSurface"
        assert message.surface_id == "temp"

    def test_reset_message(self):
        """测试 Reset 消息"""
        message = ResetMessage()
        assert message.type == "reset"


class TestJSONLParsing:
    """测试 JSONL 解析和序列化"""

    def test_parse_single_message(self):
        """测试解析单条消息"""
        jsonl = '{"type": "dataModelUpdate", "path": "count", "value": 42}'
        messages = parse_jsonl(jsonl)
        assert len(messages) == 1
        assert isinstance(messages[0], DataModelUpdateMessage)
        assert messages[0].path == "count"
        assert messages[0].value == 42

    def test_parse_multiple_messages(self):
        """测试解析多条消息"""
        jsonl = """
{"type": "dataModelUpdate", "path": "user.name", "value": "Alice"}
{"type": "dataModelUpdate", "path": "user.age", "value": 30}
{"type": "reset"}
"""
        messages = parse_jsonl(jsonl)
        assert len(messages) == 3
        assert isinstance(messages[0], DataModelUpdateMessage)
        assert isinstance(messages[1], DataModelUpdateMessage)
        assert isinstance(messages[2], ResetMessage)

    def test_parse_surface_update(self):
        """测试解析 SurfaceUpdate 消息"""
        jsonl = """
{"type": "surfaceUpdate", "surfaceId": "main", "surface": {"type": "text", "content": "Hello"}}
"""
        messages = parse_jsonl(jsonl)
        assert len(messages) == 1
        assert isinstance(messages[0], SurfaceUpdateMessage)
        assert messages[0].surface_id == "main"
        assert isinstance(messages[0].surface, TextSurface)
        assert messages[0].surface.content == "Hello"

    def test_parse_invalid_json(self):
        """测试解析无效 JSON"""
        jsonl = '{"type": "invalid'
        with pytest.raises(ValueError, match="Invalid JSON"):
            parse_jsonl(jsonl)

    def test_parse_unknown_message_type(self):
        """测试解析未知消息类型"""
        jsonl = '{"type": "unknown"}'
        with pytest.raises(ValueError, match="Unknown message type"):
            parse_jsonl(jsonl)

    def test_to_jsonl(self):
        """测试序列化为 JSONL"""
        messages = [
            DataModelUpdateMessage(path="count", value=1),
            ResetMessage(),
        ]
        jsonl = to_jsonl(messages)
        lines = jsonl.split("\n")
        assert len(lines) == 2

        # 验证可以解析回来
        parsed = parse_jsonl(jsonl)
        assert len(parsed) == 2


# ============================================================================
# Canvas Host Tests
# ============================================================================


class TestCanvasHost:
    """测试 Canvas Host 服务器"""

    @pytest.fixture
    def host(self):
        """创建 Canvas Host 实例"""
        return CanvasHost()

    @pytest.mark.asyncio
    async def test_initial_state(self, host):
        """测试初始状态"""
        state = host.get_state("session_1")
        assert state.surfaces == {}
        assert state.data_model == {}

    @pytest.mark.asyncio
    async def test_broadcast_surface_update(self, host):
        """测试广播 SurfaceUpdate 消息"""
        session_id = "session_1"
        surface = TextSurface(content="Hello")
        message = SurfaceUpdateMessage(surface_id="main", surface=surface)

        await host.broadcast(session_id, [message])

        state = host.get_state(session_id)
        assert "main" in state.surfaces
        assert state.surfaces["main"] == surface

    @pytest.mark.asyncio
    async def test_broadcast_data_model_update(self, host):
        """测试广播 DataModelUpdate 消息"""
        session_id = "session_1"
        message = DataModelUpdateMessage(path="user.name", value="Alice")

        await host.broadcast(session_id, [message])

        state = host.get_state(session_id)
        assert "user" in state.data_model
        assert state.data_model["user"]["name"] == "Alice"

    @pytest.mark.asyncio
    async def test_broadcast_nested_data_update(self, host):
        """测试嵌套数据更新"""
        session_id = "session_1"
        messages = [
            DataModelUpdateMessage(path="app.config.theme", value="dark"),
            DataModelUpdateMessage(path="app.config.lang", value="en"),
            DataModelUpdateMessage(path="app.version", value="1.0"),
        ]

        await host.broadcast(session_id, messages)

        state = host.get_state(session_id)
        assert state.data_model["app"]["config"]["theme"] == "dark"
        assert state.data_model["app"]["config"]["lang"] == "en"
        assert state.data_model["app"]["version"] == "1.0"

    @pytest.mark.asyncio
    async def test_broadcast_delete_surface(self, host):
        """测试删除 Surface"""
        session_id = "session_1"

        # 先添加
        surface = TextSurface(content="Temp")
        await host.broadcast(session_id, [SurfaceUpdateMessage(surface_id="temp", surface=surface)])

        # 验证存在
        assert "temp" in host.get_state(session_id).surfaces

        # 删除
        await host.broadcast(session_id, [DeleteSurfaceMessage(surface_id="temp")])

        # 验证已删除
        assert "temp" not in host.get_state(session_id).surfaces

    @pytest.mark.asyncio
    async def test_reset(self, host):
        """测试重置"""
        session_id = "session_1"

        # 添加一些状态
        messages = [
            SurfaceUpdateMessage(surface_id="main", surface=TextSurface(content="Test")),
            DataModelUpdateMessage(path="count", value=42),
        ]
        await host.broadcast(session_id, messages)

        # 验证状态存在
        state = host.get_state(session_id)
        assert len(state.surfaces) > 0
        assert len(state.data_model) > 0

        # 重置
        await host.reset(session_id)

        # 验证已清空
        state = host.get_state(session_id)
        assert len(state.surfaces) == 0
        assert len(state.data_model) == 0

    @pytest.mark.asyncio
    async def test_multiple_sessions(self, host):
        """测试多会话隔离"""
        # 会话 1
        await host.broadcast("session_1", [DataModelUpdateMessage(path="value", value=1)])

        # 会话 2
        await host.broadcast("session_2", [DataModelUpdateMessage(path="value", value=2)])

        # 验证隔离
        state1 = host.get_state("session_1")
        state2 = host.get_state("session_2")
        assert state1.data_model["value"] == 1
        assert state2.data_model["value"] == 2


# ============================================================================
# Canvas Client Tests
# ============================================================================


class TestCanvasClient:
    """测试 Canvas Client 助手"""

    def test_text(self):
        """测试文本方法"""
        client = CanvasClient()
        client.text("Hello World")

        messages = client.to_messages()
        assert len(messages) == 1
        assert isinstance(messages[0], SurfaceUpdateMessage)
        assert messages[0].surface_id == "main"
        assert isinstance(messages[0].surface, TextSurface)
        assert messages[0].surface.content == "Hello World"

    def test_button(self):
        """测试按钮方法"""
        client = CanvasClient()
        client.button("Click Me", "btn_callback")

        messages = client.to_messages()
        assert len(messages) == 1
        surface = messages[0].surface
        assert isinstance(surface, ButtonSurface)
        assert surface.label == "Click Me"
        assert surface.action.id == "btn_callback"

    def test_image(self):
        """测试图片方法"""
        client = CanvasClient()
        client.image("https://example.com/img.png", alt="Test", width=200)

        messages = client.to_messages()
        surface = messages[0].surface
        assert isinstance(surface, ImageSurface)
        assert surface.src == "https://example.com/img.png"
        assert surface.alt == "Test"
        assert surface.width == 200

    def test_data_update(self):
        """测试数据更新方法"""
        client = CanvasClient()
        client.data_update("user.name", "Alice")

        messages = client.to_messages()
        assert len(messages) == 1
        assert isinstance(messages[0], DataModelUpdateMessage)
        assert messages[0].path == "user.name"
        assert messages[0].value == "Alice"

    def test_delete_surface(self):
        """测试删除 Surface 方法"""
        client = CanvasClient()
        client.delete_surface("temp")

        messages = client.to_messages()
        assert len(messages) == 1
        assert isinstance(messages[0], DeleteSurfaceMessage)
        assert messages[0].surface_id == "temp"

    def test_reset(self):
        """测试重置方法"""
        client = CanvasClient()
        client.reset()

        messages = client.to_messages()
        assert len(messages) == 1
        assert isinstance(messages[0], ResetMessage)

    def test_chaining(self):
        """测试链式调用"""
        client = CanvasClient()
        client.text("Title").data_update("count", 1).button("Submit", "submit_btn")

        messages = client.to_messages()
        assert len(messages) == 3

    def test_to_jsonl(self):
        """测试转换为 JSONL"""
        client = CanvasClient()
        client.text("Hello").data_update("count", 1)

        jsonl = client.to_jsonl()
        lines = jsonl.split("\n")
        assert len(lines) == 2

        # 验证可以解析回来
        parsed = parse_jsonl(jsonl)
        assert len(parsed) == 2

    def test_container(self):
        """测试容器方法"""
        client = CanvasClient()
        children = [
            TextSurface(content="Item 1"),
            TextSurface(content="Item 2"),
        ]
        client.container(children, direction="row", gap=10)

        messages = client.to_messages()
        surface = messages[0].surface
        assert isinstance(surface, ContainerSurface)
        assert surface.direction == "row"
        assert len(surface.children) == 2
        assert surface.gap == 10


class TestCanvasHelpers:
    """测试便捷函数"""

    def test_create_text_surface(self):
        """测试创建文本 Surface"""
        surface = create_text_surface("Hello", style={"color": "red"})
        assert surface.content == "Hello"
        assert surface.style == {"color": "red"}

    def test_create_button_surface(self):
        """测试创建按钮 Surface"""
        surface = create_button_surface("Click", "callback_id", disabled=True)
        assert surface.label == "Click"
        assert surface.action.id == "callback_id"
        assert surface.disabled is True


# ============================================================================
# 测试计数验证
# ============================================================================


def test_phase11_test_count():
    """验证 Phase 11 测试数量"""
    import inspect

    test_classes = [
        TestA2UIProtocol,
        TestJSONLParsing,
        TestCanvasHost,
        TestCanvasClient,
        TestCanvasHelpers,
    ]

    total_tests = 0
    for cls in test_classes:
        methods = inspect.getmembers(cls, predicate=inspect.isfunction)
        test_methods = [m for m in methods if m[0].startswith("test_")]
        total_tests += len(test_methods)

    # 加上这个测试本身
    total_tests += 1

    print(f"\n✅ Phase 11 包含 {total_tests} 个测试")
    assert total_tests >= 30, f"Phase 11 should have at least 30 tests, got {total_tests}"
