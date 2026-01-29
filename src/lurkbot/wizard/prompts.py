"""
Wizard 提示接口

对标 MoltBot wizard/prompts.ts
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Callable, Protocol, TypeVar

T = TypeVar("T")


# ============================================================================
# 参数类型
# ============================================================================


@dataclass
class WizardSelectParams:
    """单选提示参数"""

    message: str
    options: list[dict[str, Any]]  # [{value, label, hint?}]
    initial_value: Any = None


@dataclass
class WizardMultiSelectParams:
    """多选提示参数"""

    message: str
    options: list[dict[str, Any]]  # [{value, label, hint?}]
    initial_values: list[Any] | None = None


@dataclass
class WizardTextParams:
    """文本输入提示参数"""

    message: str
    initial_value: str | None = None
    placeholder: str | None = None
    validate: Callable[[str], str | None] | None = None


@dataclass
class WizardConfirmParams:
    """确认提示参数"""

    message: str
    initial_value: bool = False


# ============================================================================
# 进度接口
# ============================================================================


class WizardProgress(ABC):
    """
    向导进度接口

    对标 MoltBot WizardProgress
    """

    @abstractmethod
    def update(self, message: str) -> None:
        """更新进度消息"""
        ...

    @abstractmethod
    def stop(self, message: str | None = None) -> None:
        """停止进度显示"""
        ...


# ============================================================================
# 提示器协议
# ============================================================================


class WizardPrompter(Protocol):
    """
    向导提示器协议

    对标 MoltBot WizardPrompter
    """

    async def intro(self, title: str) -> None:
        """显示向导介绍"""
        ...

    async def outro(self, message: str) -> None:
        """显示向导结束"""
        ...

    async def note(self, message: str, title: str | None = None) -> None:
        """显示提示信息"""
        ...

    async def select(self, params: WizardSelectParams) -> Any:
        """单选提示"""
        ...

    async def multiselect(self, params: WizardMultiSelectParams) -> list[Any]:
        """多选提示"""
        ...

    async def text(self, params: WizardTextParams) -> str:
        """文本输入提示"""
        ...

    async def confirm(self, params: WizardConfirmParams) -> bool:
        """确认提示"""
        ...

    def progress(self, label: str) -> WizardProgress:
        """显示进度"""
        ...


# ============================================================================
# 异常
# ============================================================================


class WizardCancelledError(Exception):
    """
    向导取消异常

    对标 MoltBot WizardCancelledError
    """

    def __init__(self, message: str = "wizard cancelled") -> None:
        super().__init__(message)
        self.message = message


class WizardValidationError(Exception):
    """向导验证错误"""

    def __init__(self, message: str, field: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.field = field


# ============================================================================
# 工具函数
# ============================================================================


def create_select_option(
    value: Any,
    label: str,
    hint: str | None = None,
) -> dict[str, Any]:
    """创建选择选项"""
    opt: dict[str, Any] = {"value": value, "label": label}
    if hint:
        opt["hint"] = hint
    return opt


def create_select_params(
    message: str,
    options: list[tuple[Any, str] | tuple[Any, str, str]],
    initial_value: Any = None,
) -> WizardSelectParams:
    """
    创建单选提示参数的辅助函数

    options: [(value, label) | (value, label, hint)]
    """
    opt_list = []
    for opt in options:
        if len(opt) == 2:
            opt_list.append(create_select_option(opt[0], opt[1]))
        else:
            opt_list.append(create_select_option(opt[0], opt[1], opt[2]))
    return WizardSelectParams(
        message=message,
        options=opt_list,
        initial_value=initial_value,
    )
