"""
Phase 20 TUI 终端界面系统测试

测试 TUI 模块的所有组件
"""

import asyncio
from datetime import datetime
from uuid import uuid4

import pytest

# ============ Types 测试 ============


class TestTuiTypes:
    """TUI 类型测试"""

    def test_activity_status_enum(self):
        """测试活动状态枚举"""
        from lurkbot.tui import ActivityStatus

        assert ActivityStatus.IDLE == "idle"
        assert ActivityStatus.SENDING == "sending"
        assert ActivityStatus.WAITING == "waiting"
        assert ActivityStatus.STREAMING == "streaming"

    def test_message_role_enum(self):
        """测试消息角色枚举"""
        from lurkbot.tui import MessageRole

        assert MessageRole.USER == "user"
        assert MessageRole.ASSISTANT == "assistant"
        assert MessageRole.SYSTEM == "system"
        assert MessageRole.TOOL == "tool"

    def test_thinking_level_enum(self):
        """测试 Thinking 级别枚举"""
        from lurkbot.tui import ThinkingLevel

        assert ThinkingLevel.OFF == "off"
        assert ThinkingLevel.LOW == "low"
        assert ThinkingLevel.MEDIUM == "medium"
        assert ThinkingLevel.HIGH == "high"

    def test_tui_state_defaults(self):
        """测试 TUI 状态默认值"""
        from lurkbot.tui import TuiState, ActivityStatus, ThinkingLevel

        state = TuiState()

        assert state.agent_default_id == "default"
        assert state.current_agent_id == "default"
        assert state.session_main_key == ""
        assert state.current_session_key == ""
        assert state.active_chat_run_id is None
        assert state.is_connected is False
        assert state.connection_status == "disconnected"
        assert state.activity_status == ActivityStatus.IDLE
        assert state.tools_expanded is False
        assert state.show_thinking is False
        assert state.thinking_level == ThinkingLevel.OFF
        assert state.current_model is None

    def test_chat_message(self):
        """测试聊天消息"""
        from lurkbot.tui import ChatMessage, MessageRole

        msg = ChatMessage(
            id="test-id",
            role=MessageRole.USER,
            content="Hello",
        )

        assert msg.id == "test-id"
        assert msg.role == MessageRole.USER
        assert msg.content == "Hello"
        assert msg.thinking is None
        assert msg.tool_calls == []
        assert msg.is_streaming is False

    def test_tui_command(self):
        """测试 TUI 命令"""
        from lurkbot.tui import TuiCommand

        cmd = TuiCommand(
            name="/help",
            aliases=["/h", "/?"],
            description="Show help",
            usage="/help [command]",
        )

        assert cmd.name == "/help"
        assert "/h" in cmd.aliases
        assert cmd.description == "Show help"

    def test_tui_event(self):
        """测试 TUI 事件"""
        from lurkbot.tui import TuiEvent, TuiEventType

        event = TuiEvent(
            type=TuiEventType.CONNECTED,
            data={"url": "ws://localhost:3000"},
        )

        assert event.type == TuiEventType.CONNECTED
        assert event.data["url"] == "ws://localhost:3000"
        assert event.timestamp is not None

    def test_tui_theme(self):
        """测试 TUI 主题"""
        from lurkbot.tui import TuiTheme, DEFAULT_THEME

        theme = TuiTheme()

        assert theme.primary == "blue"
        assert theme.user_message == "green"
        assert theme.assistant_message == "white"
        assert theme.error_message == "red"

        # 默认主题
        assert DEFAULT_THEME.primary == "blue"

    def test_tui_config(self):
        """测试 TUI 配置"""
        from lurkbot.tui import TuiConfig, ThinkingLevel

        config = TuiConfig()

        assert config.gateway_url == "ws://localhost:3000"
        assert config.gateway_token is None
        assert config.show_timestamps is False
        assert config.auto_scroll is True
        assert config.default_thinking_level == ThinkingLevel.OFF


# ============ Stream Assembler 测试 ============


class TestStreamAssembler:
    """流式组装器测试"""

    def test_create_assembler(self):
        """测试创建组装器"""
        from lurkbot.tui import TuiStreamAssembler

        assembler = TuiStreamAssembler()
        assert assembler.active_runs() == []

    def test_ingest_content_delta(self):
        """测试处理内容增量"""
        from lurkbot.tui import TuiStreamAssembler

        assembler = TuiStreamAssembler()

        # 第一个增量
        result = assembler.ingest_delta("run-1", {"content": "Hello"})
        assert "Hello" in result

        # 第二个增量
        result = assembler.ingest_delta("run-1", {"content": " World"})
        assert "Hello World" in result

    def test_ingest_thinking_delta(self):
        """测试处理 thinking 增量"""
        from lurkbot.tui import TuiStreamAssembler

        assembler = TuiStreamAssembler()

        # 不显示 thinking
        result = assembler.ingest_delta("run-1", {"thinking": "Let me think..."})
        assert "thinking" not in result.lower()

        # 显示 thinking
        result = assembler.ingest_delta("run-1", {"thinking": " more"}, show_thinking=True)
        assert "thinking" in result.lower()

    def test_ingest_tool_call(self):
        """测试处理工具调用"""
        from lurkbot.tui import TuiStreamAssembler

        assembler = TuiStreamAssembler()

        result = assembler.ingest_delta(
            "run-1",
            {
                "tool_call": {
                    "id": "tc-1",
                    "name": "search",
                    "arguments": '{"query": "test"}',
                }
            },
        )

        tool_calls = assembler.get_tool_calls("run-1")
        assert len(tool_calls) == 1
        assert tool_calls[0]["name"] == "search"

    def test_finalize(self):
        """测试最终化"""
        from lurkbot.tui import TuiStreamAssembler

        assembler = TuiStreamAssembler()

        assembler.ingest_delta("run-1", {"content": "Final content"})
        content = assembler.finalize("run-1")

        assert content == "Final content"
        assert not assembler.has_run("run-1")

    def test_clear(self):
        """测试清理"""
        from lurkbot.tui import TuiStreamAssembler

        assembler = TuiStreamAssembler()

        assembler.ingest_delta("run-1", {"content": "Test"})
        assembler.ingest_delta("run-2", {"content": "Test"})

        assert len(assembler.active_runs()) == 2

        assembler.clear("run-1")
        assert len(assembler.active_runs()) == 1

        assembler.clear()
        assert len(assembler.active_runs()) == 0


# ============ Formatters 测试 ============


class TestFormatters:
    """格式化器测试"""

    def test_create_formatter(self):
        """测试创建格式化器"""
        from lurkbot.tui import TuiFormatter

        formatter = TuiFormatter()
        assert formatter.theme is not None

    def test_format_user_message(self):
        """测试格式化用户消息"""
        from lurkbot.tui import TuiFormatter, ChatMessage, MessageRole

        formatter = TuiFormatter()
        msg = ChatMessage(
            id="test",
            role=MessageRole.USER,
            content="Hello",
        )

        panel = formatter.format_message(msg)
        assert panel is not None

    def test_format_assistant_message(self):
        """测试格式化助手消息"""
        from lurkbot.tui import TuiFormatter, ChatMessage, MessageRole

        formatter = TuiFormatter()
        msg = ChatMessage(
            id="test",
            role=MessageRole.ASSISTANT,
            content="Hi there!",
        )

        panel = formatter.format_message(msg)
        assert panel is not None

    def test_format_streaming_message(self):
        """测试格式化流式消息"""
        from lurkbot.tui import TuiFormatter, ChatMessage, MessageRole

        formatter = TuiFormatter()
        msg = ChatMessage(
            id="test",
            role=MessageRole.ASSISTANT,
            content="Streaming...",
            is_streaming=True,
        )

        panel = formatter.format_message(msg)
        assert panel is not None

    def test_format_status_bar(self):
        """测试格式化状态栏"""
        from lurkbot.tui import TuiFormatter, TuiState

        formatter = TuiFormatter()
        state = TuiState()

        text = formatter.format_status_bar(state)
        assert text is not None

    def test_format_help(self):
        """测试格式化帮助"""
        from lurkbot.tui import TuiFormatter

        formatter = TuiFormatter()
        commands = [
            {"name": "/help", "description": "Show help"},
            {"name": "/status", "description": "Show status"},
        ]

        panel = formatter.format_help(commands)
        assert panel is not None

    def test_format_error(self):
        """测试格式化错误"""
        from lurkbot.tui import TuiFormatter

        formatter = TuiFormatter()
        panel = formatter.format_error("Something went wrong")
        assert panel is not None

    def test_format_success(self):
        """测试格式化成功"""
        from lurkbot.tui import TuiFormatter

        formatter = TuiFormatter()
        panel = formatter.format_success("Operation completed")
        assert panel is not None


# ============ Keybindings 测试 ============


class TestKeybindings:
    """快捷键测试"""

    def test_key_action_enum(self):
        """测试快捷键动作枚举"""
        from lurkbot.tui import KeyAction

        assert KeyAction.SUBMIT == "submit"
        assert KeyAction.CANCEL == "cancel"
        assert KeyAction.EXIT == "exit"

    def test_key_binding(self):
        """测试快捷键绑定"""
        from lurkbot.tui import KeyBinding, KeyAction

        binding = KeyBinding(
            key="enter",
            action=KeyAction.SUBMIT,
            description="Send message",
        )

        assert binding.key == "enter"
        assert binding.action == KeyAction.SUBMIT

    def test_default_keybindings(self):
        """测试默认快捷键"""
        from lurkbot.tui import DEFAULT_KEYBINDINGS, KeyAction

        # 检查必要的绑定存在
        keys = {b.key for b in DEFAULT_KEYBINDINGS}
        assert "enter" in keys
        assert "ctrl+c" in keys
        assert "ctrl+d" in keys

    def test_keybinding_manager(self):
        """测试快捷键管理器"""
        from lurkbot.tui import KeyBindingManager, KeyAction

        manager = KeyBindingManager()

        # 获取动作
        action = manager.get_action("enter", "input_focused")
        assert action == KeyAction.SUBMIT

        # 获取帮助
        help_text = manager.get_help_text()
        assert len(help_text) > 0

    def test_register_handler(self):
        """测试注册处理器"""
        from lurkbot.tui import KeyBindingManager, KeyAction

        manager = KeyBindingManager()
        called = []

        def handler():
            called.append(True)

        manager.register_handler(KeyAction.SUBMIT, handler)
        manager.handle_key("enter", "input_focused")

        assert len(called) == 1


# ============ Commands 测试 ============


class TestCommands:
    """命令处理器测试"""

    def test_create_command_handler(self):
        """测试创建命令处理器"""
        from lurkbot.tui import CommandHandler

        handler = CommandHandler()
        assert handler is not None

    def test_is_command(self):
        """测试命令检测"""
        from lurkbot.tui import CommandHandler

        handler = CommandHandler()

        assert handler.is_command("/help")
        assert handler.is_command("/status")
        assert handler.is_command("!ls")
        assert not handler.is_command("hello")
        assert not handler.is_command("")

    def test_parse_command(self):
        """测试命令解析"""
        from lurkbot.tui import CommandHandler

        handler = CommandHandler()

        cmd, args = handler.parse_command("/help")
        assert cmd == "/help"
        assert args == []

        cmd, args = handler.parse_command("/agent test-agent")
        assert cmd == "/agent"
        assert args == ["test-agent"]

        cmd, args = handler.parse_command("!ls -la")
        assert cmd == "!"
        assert args == ["ls -la"]

    def test_get_commands(self):
        """测试获取命令列表"""
        from lurkbot.tui import CommandHandler

        handler = CommandHandler()
        commands = handler.get_commands()

        assert len(commands) > 0
        names = [c.name for c in commands]
        assert "/help" in names
        assert "/status" in names
        assert "/agent" in names

    @pytest.mark.asyncio
    async def test_execute_help(self):
        """测试执行 help 命令"""
        from lurkbot.tui import CommandHandler, TuiState

        handler = CommandHandler()
        state = TuiState()

        result = await handler.execute("/help", state)

        assert result.success
        assert "Available commands" in result.message

    @pytest.mark.asyncio
    async def test_execute_status(self):
        """测试执行 status 命令"""
        from lurkbot.tui import CommandHandler, TuiState

        handler = CommandHandler()
        state = TuiState()

        result = await handler.execute("/status", state)

        assert result.success
        assert "Gateway Status" in result.message

    @pytest.mark.asyncio
    async def test_execute_agent(self):
        """测试执行 agent 命令"""
        from lurkbot.tui import CommandHandler, TuiState

        handler = CommandHandler()
        state = TuiState()

        # 无参数 - 显示当前
        result = await handler.execute("/agent", state)
        assert result.success
        assert "Current agent" in result.message

        # 切换 agent
        result = await handler.execute("/agent new-agent", state)
        assert result.success
        assert state.current_agent_id == "new-agent"

    @pytest.mark.asyncio
    async def test_execute_model(self):
        """测试执行 model 命令"""
        from lurkbot.tui import CommandHandler, TuiState

        handler = CommandHandler()
        state = TuiState()

        # 设置模型
        result = await handler.execute("/model claude-3-opus", state)
        assert result.success
        assert state.current_model == "claude-3-opus"

        # 重置模型
        result = await handler.execute("/model default", state)
        assert result.success
        assert state.current_model is None

    @pytest.mark.asyncio
    async def test_execute_think(self):
        """测试执行 think 命令"""
        from lurkbot.tui import CommandHandler, TuiState, ThinkingLevel

        handler = CommandHandler()
        state = TuiState()

        result = await handler.execute("/think high", state)
        assert result.success
        assert state.thinking_level == ThinkingLevel.HIGH
        assert state.show_thinking is True

        result = await handler.execute("/think off", state)
        assert result.success
        assert state.thinking_level == ThinkingLevel.OFF
        assert state.show_thinking is False

    @pytest.mark.asyncio
    async def test_execute_new(self):
        """测试执行 new 命令"""
        from lurkbot.tui import CommandHandler, TuiState

        handler = CommandHandler()
        state = TuiState()
        state.current_session_key = "old-session"

        result = await handler.execute("/new", state)
        assert result.success
        assert state.current_session_key != "old-session"
        assert state.current_session_key.startswith("tui:")

    @pytest.mark.asyncio
    async def test_execute_unknown_command(self):
        """测试执行未知命令"""
        from lurkbot.tui import CommandHandler, TuiState

        handler = CommandHandler()
        state = TuiState()

        result = await handler.execute("/unknown", state)
        assert not result.success
        assert "Unknown command" in result.message

    @pytest.mark.asyncio
    async def test_execute_bash(self):
        """测试执行 bash 命令"""
        from lurkbot.tui import CommandHandler, TuiState

        handler = CommandHandler()
        state = TuiState()

        result = await handler.execute("!echo hello", state)
        assert result.success
        assert "hello" in result.message


# ============ Events 测试 ============


class TestEvents:
    """事件处理器测试"""

    def test_create_event_handler(self):
        """测试创建事件处理器"""
        from lurkbot.tui import TuiEventHandler, TuiState

        state = TuiState()
        handler = TuiEventHandler(state)

        assert handler is not None
        assert handler.messages == []

    @pytest.mark.asyncio
    async def test_handle_connected_event(self):
        """测试处理连接事件"""
        from lurkbot.tui import TuiEventHandler, TuiState, TuiEvent, TuiEventType

        state = TuiState()
        handler = TuiEventHandler(state)

        event = TuiEvent(type=TuiEventType.CONNECTED)
        await handler.handle_event(event)

        assert state.is_connected is True
        assert len(handler.messages) == 1

    @pytest.mark.asyncio
    async def test_handle_disconnected_event(self):
        """测试处理断开事件"""
        from lurkbot.tui import TuiEventHandler, TuiState, TuiEvent, TuiEventType

        state = TuiState()
        state.is_connected = True
        handler = TuiEventHandler(state)

        event = TuiEvent(type=TuiEventType.DISCONNECTED)
        await handler.handle_event(event)

        assert state.is_connected is False

    @pytest.mark.asyncio
    async def test_handle_stream_delta(self):
        """测试处理流式增量"""
        from lurkbot.tui import TuiEventHandler, TuiState, ActivityStatus

        state = TuiState()
        handler = TuiEventHandler(state)

        await handler.handle_stream_delta("run-1", {"content": "Hello"})

        assert state.activity_status == ActivityStatus.STREAMING
        assert state.active_chat_run_id == "run-1"

    @pytest.mark.asyncio
    async def test_finalize_stream(self):
        """测试完成流式"""
        from lurkbot.tui import TuiEventHandler, TuiState, MessageRole

        state = TuiState()
        handler = TuiEventHandler(state)

        await handler.handle_stream_delta("run-1", {"content": "Hello World"})
        message = await handler.finalize_stream("run-1")

        assert message.content == "Hello World"
        assert message.role == MessageRole.ASSISTANT
        assert len(handler.messages) == 1

    def test_add_user_message(self):
        """测试添加用户消息"""
        from lurkbot.tui import TuiEventHandler, TuiState, MessageRole

        state = TuiState()
        handler = TuiEventHandler(state)

        message = handler.add_user_message("Hello")

        assert message.role == MessageRole.USER
        assert message.content == "Hello"
        assert len(handler.messages) == 1

    def test_add_system_message(self):
        """测试添加系统消息"""
        from lurkbot.tui import TuiEventHandler, TuiState, MessageRole

        state = TuiState()
        handler = TuiEventHandler(state)

        message = handler.add_system_message("System info")

        assert message.role == MessageRole.SYSTEM
        assert message.content == "System info"

    def test_clear_messages(self):
        """测试清除消息"""
        from lurkbot.tui import TuiEventHandler, TuiState

        state = TuiState()
        handler = TuiEventHandler(state)

        handler.add_user_message("Test 1")
        handler.add_user_message("Test 2")
        assert len(handler.messages) == 2

        handler.clear_messages()
        assert len(handler.messages) == 0

    def test_input_history(self):
        """测试输入历史"""
        from lurkbot.tui import InputHistory

        history = InputHistory()

        history.add("first")
        history.add("second")
        history.add("third")

        # 向上导航
        assert history.prev() == "third"
        assert history.prev() == "second"
        assert history.prev() == "first"
        assert history.prev() is None  # 到顶了

        # 向下导航
        assert history.next() == "second"
        assert history.next() == "third"

    def test_input_history_no_duplicates(self):
        """测试输入历史不重复"""
        from lurkbot.tui import InputHistory

        history = InputHistory()

        history.add("same")
        history.add("same")
        history.add("same")

        assert len(history.items) == 1


# ============ Components 测试 ============


class TestChatLog:
    """聊天日志组件测试"""

    def test_create_chat_log(self):
        """测试创建聊天日志"""
        from lurkbot.tui import ChatLog

        chat_log = ChatLog()
        assert chat_log.messages == []

    def test_add_message(self):
        """测试添加消息"""
        from lurkbot.tui import ChatLog, ChatMessage, MessageRole

        chat_log = ChatLog()
        msg = ChatMessage(
            id="test",
            role=MessageRole.USER,
            content="Hello",
        )

        chat_log.add_message(msg)
        assert len(chat_log.messages) == 1

    def test_update_streaming(self):
        """测试更新流式内容"""
        from lurkbot.tui import ChatLog

        chat_log = ChatLog()

        chat_log.update_streaming("run-1", "Streaming content...")
        chat_log.finalize_streaming("run-1")

    def test_clear(self):
        """测试清除"""
        from lurkbot.tui import ChatLog, ChatMessage, MessageRole

        chat_log = ChatLog()
        chat_log.add_message(
            ChatMessage(id="1", role=MessageRole.USER, content="Test")
        )

        chat_log.clear()
        assert len(chat_log.messages) == 0

    def test_scroll(self):
        """测试滚动"""
        from lurkbot.tui import ChatLog

        chat_log = ChatLog()

        chat_log.scroll_up()
        chat_log.scroll_down()
        chat_log.scroll_to_top()

        offset, visible, total = chat_log.get_scroll_info()
        assert offset == 0

    def test_render(self):
        """测试渲染"""
        from lurkbot.tui import ChatLog

        chat_log = ChatLog()
        renderable = chat_log.render()
        assert renderable is not None


class TestThinkingIndicator:
    """Thinking 指示器测试"""

    def test_create_indicator(self):
        """测试创建指示器"""
        from lurkbot.tui import ThinkingIndicator

        indicator = ThinkingIndicator()
        assert not indicator.is_thinking

    def test_start_stop(self):
        """测试开始停止"""
        from lurkbot.tui import ThinkingIndicator

        indicator = ThinkingIndicator()

        indicator.start()
        assert indicator.is_thinking

        indicator.stop()
        assert not indicator.is_thinking

    def test_update_content(self):
        """测试更新内容"""
        from lurkbot.tui import ThinkingIndicator

        indicator = ThinkingIndicator()
        indicator.start()

        indicator.update_content("Thinking about...")
        indicator.append_content(" something")

    def test_render(self):
        """测试渲染"""
        from lurkbot.tui import ThinkingIndicator

        indicator = ThinkingIndicator()

        # 未思考时
        renderable = indicator.render()
        assert renderable is not None

        # 思考时
        indicator.start()
        indicator.update_content("Processing...")
        renderable = indicator.render()
        assert renderable is not None


class TestStreamingIndicator:
    """流式指示器测试"""

    def test_create_indicator(self):
        """测试创建指示器"""
        from lurkbot.tui import StreamingIndicator

        indicator = StreamingIndicator()
        assert not indicator.is_streaming

    def test_start_stop(self):
        """测试开始停止"""
        from lurkbot.tui import StreamingIndicator

        indicator = StreamingIndicator()

        indicator.start()
        assert indicator.is_streaming

        indicator.stop()
        assert not indicator.is_streaming

    def test_render(self):
        """测试渲染"""
        from lurkbot.tui import StreamingIndicator

        indicator = StreamingIndicator()
        indicator.start()

        renderable = indicator.render()
        assert renderable is not None


class TestInputBox:
    """输入框测试"""

    def test_create_input_box(self):
        """测试创建输入框"""
        from lurkbot.tui import InputBox

        input_box = InputBox()
        assert input_box.content == ""
        assert input_box.is_empty

    def test_set_content(self):
        """测试设置内容"""
        from lurkbot.tui import InputBox

        input_box = InputBox()
        input_box.set_content("Hello")

        assert input_box.content == "Hello"
        assert not input_box.is_empty

    def test_insert(self):
        """测试插入"""
        from lurkbot.tui import InputBox

        input_box = InputBox()
        input_box.insert("Hello")
        input_box.insert(" World")

        assert input_box.content == "Hello World"

    def test_delete(self):
        """测试删除"""
        from lurkbot.tui import InputBox

        input_box = InputBox()
        input_box.set_content("Hello")

        input_box.delete_char()
        assert input_box.content == "Hell"

    def test_cursor_movement(self):
        """测试光标移动"""
        from lurkbot.tui import InputBox

        input_box = InputBox()
        input_box.set_content("Hello")

        input_box.move_cursor_home()
        input_box.move_cursor_right()
        input_box.move_cursor_end()
        input_box.move_cursor_left()

    def test_submit(self):
        """测试提交"""
        from lurkbot.tui import InputBox

        input_box = InputBox()
        input_box.set_content("Hello")

        content = input_box.submit()

        assert content == "Hello"
        assert input_box.content == ""

    def test_history_navigation(self):
        """测试历史导航"""
        from lurkbot.tui import InputBox

        input_box = InputBox()

        input_box.set_content("first")
        input_box.submit()

        input_box.set_content("second")
        input_box.submit()

        input_box.history_prev()
        assert input_box.content == "second"

        input_box.history_prev()
        assert input_box.content == "first"

    def test_focus(self):
        """测试焦点"""
        from lurkbot.tui import InputBox

        input_box = InputBox()
        assert input_box.is_focused

        input_box.blur()
        assert not input_box.is_focused

        input_box.focus()
        assert input_box.is_focused

    def test_render(self):
        """测试渲染"""
        from lurkbot.tui import InputBox

        input_box = InputBox()
        input_box.set_content("Test input")

        renderable = input_box.render()
        assert renderable is not None


class TestCommandCompleter:
    """命令补全器测试"""

    def test_create_completer(self):
        """测试创建补全器"""
        from lurkbot.tui import CommandCompleter

        completer = CommandCompleter()
        assert completer is not None

    def test_set_commands(self):
        """测试设置命令"""
        from lurkbot.tui import CommandCompleter

        completer = CommandCompleter()
        completer.set_commands(["/help", "/status", "/agent"])

    def test_get_completions(self):
        """测试获取补全"""
        from lurkbot.tui import CommandCompleter

        completer = CommandCompleter(["/help", "/status", "/agent"])

        completions = completer.get_completions("/h")
        assert "/help" in completions

        completions = completer.get_completions("/s")
        assert "/status" in completions

    def test_complete(self):
        """测试补全"""
        from lurkbot.tui import CommandCompleter

        completer = CommandCompleter(["/help", "/status", "/agent"])

        # 唯一匹配
        result = completer.complete("/he")
        assert result == "/help"

        # 无匹配
        result = completer.complete("/xyz")
        assert result is None


# ============ App 测试 ============


class TestTuiApp:
    """TUI 应用测试"""

    def test_create_app(self):
        """测试创建应用"""
        from lurkbot.tui import TuiApp

        app = TuiApp()
        assert app is not None
        assert not app.is_running

    def test_app_config(self):
        """测试应用配置"""
        from lurkbot.tui import TuiApp, TuiAppConfig

        config = TuiAppConfig(
            gateway_url="ws://localhost:8080",
            show_thinking=True,
        )

        app = TuiApp(config)
        assert app.config.gateway_url == "ws://localhost:8080"
        assert app.config.show_thinking is True

    def test_app_state(self):
        """测试应用状态"""
        from lurkbot.tui import TuiApp

        app = TuiApp()
        state = app.state

        assert state.agent_default_id == "default"
        assert not state.is_connected


# ============ Gateway Chat 测试 ============


class TestGatewayChat:
    """Gateway 通信测试"""

    def test_create_gateway_chat(self):
        """测试创建 Gateway 通信"""
        from lurkbot.tui import GatewayChat

        gateway = GatewayChat()
        assert gateway is not None
        assert not gateway.connected

    def test_gateway_config(self):
        """测试 Gateway 配置"""
        from lurkbot.tui import GatewayChat

        gateway = GatewayChat(
            url="ws://localhost:8080",
            token="test-token",
        )

        assert gateway.url == "ws://localhost:8080"
        assert gateway.token == "test-token"

    def test_connection_info(self):
        """测试连接信息"""
        from lurkbot.tui import GatewayChat

        gateway = GatewayChat()
        info = gateway.connection_info

        assert info.url == "ws://localhost:3000"
        assert not info.connected


# ============ 集成测试 ============


class TestIntegration:
    """集成测试"""

    def test_module_imports(self):
        """测试模块导入"""
        from lurkbot.tui import (
            # Types
            ActivityStatus,
            MessageRole,
            ThinkingLevel,
            TuiState,
            TuiConfig,
            TuiTheme,
            ChatMessage,
            TuiCommand,
            TuiEvent,
            TuiEventType,
            # Components
            TuiStreamAssembler,
            TuiFormatter,
            KeyBindingManager,
            GatewayChat,
            CommandHandler,
            TuiEventHandler,
            ChatLog,
            ThinkingIndicator,
            InputBox,
            # App
            TuiApp,
            run_tui,
        )

        # 验证所有导入成功
        assert ActivityStatus is not None
        assert TuiApp is not None

    @pytest.mark.asyncio
    async def test_full_command_flow(self):
        """测试完整命令流程"""
        from lurkbot.tui import CommandHandler, TuiState, ThinkingLevel

        handler = CommandHandler()
        state = TuiState()

        # 执行一系列命令
        await handler.execute("/help", state)
        await handler.execute("/status", state)
        await handler.execute("/agent test-agent", state)
        await handler.execute("/model claude-3-opus", state)
        await handler.execute("/think high", state)
        await handler.execute("/new", state)

        # 验证状态变化
        assert state.current_agent_id == "test-agent"
        assert state.current_model == "claude-3-opus"
        assert state.thinking_level == ThinkingLevel.HIGH
        assert state.current_session_key.startswith("tui:")

    @pytest.mark.asyncio
    async def test_event_flow(self):
        """测试事件流程"""
        from lurkbot.tui import (
            TuiEventHandler,
            TuiState,
            TuiEvent,
            TuiEventType,
            ActivityStatus,
        )

        state = TuiState()
        handler = TuiEventHandler(state)

        # 连接
        await handler.handle_event(TuiEvent(type=TuiEventType.CONNECTED))
        assert state.is_connected

        # 流式响应
        await handler.handle_stream_delta("run-1", {"content": "Hello "})
        await handler.handle_stream_delta("run-1", {"content": "World"})
        assert state.activity_status == ActivityStatus.STREAMING

        # 完成
        message = await handler.finalize_stream("run-1")
        assert message.content == "Hello World"

        # 断开
        await handler.handle_event(TuiEvent(type=TuiEventType.DISCONNECTED))
        assert not state.is_connected
