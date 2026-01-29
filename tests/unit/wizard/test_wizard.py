"""
Wizard 模块单元测试

测试 Wizard 配置向导功能
"""

import asyncio
import pytest
from typing import Any
from unittest.mock import AsyncMock, MagicMock

from lurkbot.wizard import (
    WizardSession,
    WizardSessionStatus,
    WizardStepType,
    WizardStepExecutor,
    WizardPrompter,
    WizardCancelledError,
    WizardSelectOption,
    WizardStep,
    GatewaySettings,
    OnboardOptions,
    QuickstartGatewayDefaults,
    is_valid_ipv4,
    is_valid_port,
    create_select_option,
    DEFAULT_GATEWAY_PORT,
    DEFAULT_WORKSPACE,
)
from lurkbot.wizard.session import create_deferred, Deferred


# ============================================================================
# 类型定义测试
# ============================================================================


class TestWizardTypes:
    """测试 Wizard 类型定义"""

    def test_wizard_session_status_enum(self):
        """测试会话状态枚举"""
        assert WizardSessionStatus.RUNNING.value == "running"
        assert WizardSessionStatus.DONE.value == "done"
        assert WizardSessionStatus.CANCELLED.value == "cancelled"
        assert WizardSessionStatus.ERROR.value == "error"

    def test_wizard_step_type_enum(self):
        """测试步骤类型枚举"""
        assert WizardStepType.SELECT.value == "select"
        assert WizardStepType.MULTISELECT.value == "multiselect"
        assert WizardStepType.TEXT.value == "text"
        assert WizardStepType.CONFIRM.value == "confirm"
        assert WizardStepType.NOTE.value == "note"

    def test_wizard_step_executor_enum(self):
        """测试步骤执行器枚举"""
        assert WizardStepExecutor.CLIENT.value == "client"
        assert WizardStepExecutor.GATEWAY.value == "gateway"

    def test_wizard_select_option(self):
        """测试选择选项"""
        option = WizardSelectOption(
            value="test",
            label="Test Option",
            hint="A test hint",
        )
        assert option.value == "test"
        assert option.label == "Test Option"
        assert option.hint == "A test hint"

    def test_wizard_step(self):
        """测试向导步骤"""
        step = WizardStep(
            id="step-1",
            type=WizardStepType.SELECT,
            message="Choose an option",
            options=[
                WizardSelectOption(value="a", label="Option A"),
                WizardSelectOption(value="b", label="Option B"),
            ],
        )
        assert step.id == "step-1"
        assert step.type == WizardStepType.SELECT
        assert step.message == "Choose an option"
        assert len(step.options) == 2

    def test_gateway_settings(self):
        """测试 Gateway 设置"""
        settings = GatewaySettings(
            port=8080,
            bind="loopback",
            auth_mode="token",
            token="test-token",
        )
        assert settings.port == 8080
        assert settings.bind == "loopback"
        assert settings.auth_mode == "token"
        assert settings.token == "test-token"

    def test_onboard_options(self):
        """测试 Onboard 选项"""
        options = OnboardOptions(
            mode="local",
            flow="quickstart",
            workspace="/test/workspace",
            accept_risk=True,
        )
        assert options.mode == "local"
        assert options.flow == "quickstart"
        assert options.workspace == "/test/workspace"
        assert options.accept_risk is True

    def test_quickstart_gateway_defaults(self):
        """测试 QuickStart Gateway 默认值"""
        defaults = QuickstartGatewayDefaults()
        assert defaults.port == DEFAULT_GATEWAY_PORT
        assert defaults.bind == "loopback"
        assert defaults.auth_mode == "token"


# ============================================================================
# 验证函数测试
# ============================================================================


class TestValidators:
    """测试验证函数"""

    def test_is_valid_port(self):
        """测试端口验证"""
        assert is_valid_port(80) is True
        assert is_valid_port(443) is True
        assert is_valid_port(8080) is True
        assert is_valid_port(65535) is True
        assert is_valid_port(1) is True
        assert is_valid_port(0) is False
        assert is_valid_port(-1) is False
        assert is_valid_port(65536) is False
        assert is_valid_port(100000) is False

    def test_is_valid_ipv4(self):
        """测试 IPv4 验证"""
        assert is_valid_ipv4("127.0.0.1") is True
        assert is_valid_ipv4("192.168.1.1") is True
        assert is_valid_ipv4("0.0.0.0") is True
        assert is_valid_ipv4("255.255.255.255") is True
        assert is_valid_ipv4("10.0.0.1") is True
        assert is_valid_ipv4("256.0.0.1") is False
        assert is_valid_ipv4("192.168.1") is False
        assert is_valid_ipv4("192.168.1.1.1") is False
        assert is_valid_ipv4("abc.def.ghi.jkl") is False
        assert is_valid_ipv4("") is False


# ============================================================================
# 辅助函数测试
# ============================================================================


class TestHelperFunctions:
    """测试辅助函数"""

    def test_create_select_option(self):
        """测试创建选择选项"""
        option = create_select_option("value1", "Label 1", "Hint 1")
        assert option["value"] == "value1"
        assert option["label"] == "Label 1"
        assert option["hint"] == "Hint 1"

    def test_create_select_option_without_hint(self):
        """测试创建无提示的选择选项"""
        option = create_select_option("value2", "Label 2")
        assert option["value"] == "value2"
        assert option["label"] == "Label 2"
        assert option.get("hint") is None


# ============================================================================
# Deferred 测试
# ============================================================================


class TestDeferred:
    """测试 Deferred 模式"""

    def test_create_deferred(self):
        """测试创建 Deferred"""
        deferred = create_deferred()
        assert isinstance(deferred, Deferred)
        assert not deferred.promise.done()

    @pytest.mark.asyncio
    async def test_deferred_resolve(self):
        """测试 Deferred 解析"""
        deferred = create_deferred()
        deferred.resolve("test_value")
        result = await deferred.promise
        assert result == "test_value"

    @pytest.mark.asyncio
    async def test_deferred_reject(self):
        """测试 Deferred 拒绝"""
        deferred = create_deferred()
        deferred.reject(ValueError("test error"))
        with pytest.raises(ValueError, match="test error"):
            await deferred.promise

    @pytest.mark.asyncio
    async def test_deferred_resolve_only_once(self):
        """测试 Deferred 只能解析一次"""
        deferred = create_deferred()
        deferred.resolve("first")
        deferred.resolve("second")  # 应该被忽略
        result = await deferred.promise
        assert result == "first"


# ============================================================================
# WizardSession 测试
# ============================================================================


class TestWizardSession:
    """测试 WizardSession"""

    @pytest.mark.asyncio
    async def test_session_creation(self):
        """测试会话创建"""
        async def runner(prompter: WizardPrompter):
            pass

        session = WizardSession(runner)
        assert session.get_status() == WizardSessionStatus.RUNNING

    @pytest.mark.asyncio
    async def test_session_completes(self):
        """测试会话完成"""
        completed = asyncio.Event()

        async def runner(prompter: WizardPrompter):
            completed.set()

        session = WizardSession(runner)
        await completed.wait()
        await asyncio.sleep(0.01)  # 等待状态更新
        assert session.get_status() == WizardSessionStatus.DONE

    @pytest.mark.asyncio
    async def test_session_cancel(self):
        """测试会话取消"""
        started = asyncio.Event()

        async def runner(prompter: WizardPrompter):
            started.set()
            await asyncio.sleep(10)  # 长时间等待

        session = WizardSession(runner)
        await started.wait()
        session.cancel()
        assert session.get_status() == WizardSessionStatus.CANCELLED
        assert session.get_error() == "cancelled"

    @pytest.mark.asyncio
    async def test_session_error(self):
        """测试会话错误"""
        async def runner(prompter: WizardPrompter):
            raise RuntimeError("test error")

        session = WizardSession(runner)
        await asyncio.sleep(0.01)  # 等待错误处理
        assert session.get_status() == WizardSessionStatus.ERROR
        assert session.get_error() == "test error"

    @pytest.mark.asyncio
    async def test_session_next_returns_done_when_completed(self):
        """测试 next() 在完成时返回 done"""
        async def runner(prompter: WizardPrompter):
            pass

        session = WizardSession(runner)
        await asyncio.sleep(0.01)  # 等待完成
        result = await session.next()
        assert result.done is True
        assert result.status == WizardSessionStatus.DONE


# ============================================================================
# WizardCancelledError 测试
# ============================================================================


class TestWizardCancelledError:
    """测试 WizardCancelledError"""

    def test_default_message(self):
        """测试默认消息"""
        error = WizardCancelledError()
        assert error.message == "wizard cancelled"
        assert str(error) == "wizard cancelled"

    def test_custom_message(self):
        """测试自定义消息"""
        error = WizardCancelledError("user cancelled")
        assert error.message == "user cancelled"
        assert str(error) == "user cancelled"


# ============================================================================
# 常量测试
# ============================================================================


class TestConstants:
    """测试常量"""

    def test_default_gateway_port(self):
        """测试默认 Gateway 端口"""
        assert DEFAULT_GATEWAY_PORT == 18789

    def test_default_workspace(self):
        """测试默认工作区"""
        assert DEFAULT_WORKSPACE == "~/.lurkbot/workspace"
