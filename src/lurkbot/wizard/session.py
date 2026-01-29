"""
Wizard 会话管理

对标 MoltBot wizard/session.ts
"""

import asyncio
import uuid
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

from .prompts import (
    WizardConfirmParams,
    WizardMultiSelectParams,
    WizardProgress,
    WizardPrompter,
    WizardSelectParams,
    WizardTextParams,
    WizardCancelledError,
)
from .types import (
    WizardNextResult,
    WizardSelectOption,
    WizardSessionStatus,
    WizardStep,
    WizardStepExecutor,
    WizardStepType,
)


# ============================================================================
# Deferred 模式
# ============================================================================


@dataclass
class Deferred:
    """
    Deferred Promise 模式

    用于异步等待答案

    对标 MoltBot createDeferred()
    """

    _future: asyncio.Future = field(default_factory=lambda: asyncio.Future())

    @property
    def promise(self) -> asyncio.Future:
        """获取 Future"""
        return self._future

    def resolve(self, value: Any) -> None:
        """解析值"""
        if not self._future.done():
            self._future.set_result(value)

    def reject(self, error: BaseException) -> None:
        """拒绝（设置异常）"""
        if not self._future.done():
            self._future.set_exception(error)


def create_deferred() -> Deferred:
    """创建 Deferred 对象"""
    return Deferred()


# ============================================================================
# Session Prompter
# ============================================================================


class NoOpProgress(WizardProgress):
    """空进度实现"""

    def update(self, message: str) -> None:
        pass

    def stop(self, message: str | None = None) -> None:
        pass


class WizardSessionPrompter:
    """
    向导会话提示器

    将提示调用转换为 WizardStep 对象

    对标 MoltBot WizardSessionPrompter
    """

    def __init__(self, session: "WizardSession") -> None:
        self._session = session

    async def intro(self, title: str) -> None:
        """显示向导介绍"""
        await self._prompt(
            step_type=WizardStepType.NOTE,
            title=title,
            message="",
            executor=WizardStepExecutor.CLIENT,
        )

    async def outro(self, message: str) -> None:
        """显示向导结束"""
        await self._prompt(
            step_type=WizardStepType.NOTE,
            title="Done",
            message=message,
            executor=WizardStepExecutor.CLIENT,
        )

    async def note(self, message: str, title: str | None = None) -> None:
        """显示提示信息"""
        await self._prompt(
            step_type=WizardStepType.NOTE,
            title=title,
            message=message,
            executor=WizardStepExecutor.CLIENT,
        )

    async def select(self, params: WizardSelectParams) -> Any:
        """单选提示"""
        options = [
            WizardSelectOption(
                value=opt.get("value"),
                label=opt.get("label", ""),
                hint=opt.get("hint"),
            )
            for opt in params.options
        ]
        result = await self._prompt(
            step_type=WizardStepType.SELECT,
            message=params.message,
            options=options,
            initial_value=params.initial_value,
            executor=WizardStepExecutor.CLIENT,
        )
        return result

    async def multiselect(self, params: WizardMultiSelectParams) -> list[Any]:
        """多选提示"""
        options = [
            WizardSelectOption(
                value=opt.get("value"),
                label=opt.get("label", ""),
                hint=opt.get("hint"),
            )
            for opt in params.options
        ]
        result = await self._prompt(
            step_type=WizardStepType.MULTISELECT,
            message=params.message,
            options=options,
            initial_value=params.initial_values,
            executor=WizardStepExecutor.CLIENT,
        )
        if isinstance(result, list):
            return result
        return []

    async def text(self, params: WizardTextParams) -> str:
        """文本输入提示"""
        result = await self._prompt(
            step_type=WizardStepType.TEXT,
            message=params.message,
            initial_value=params.initial_value,
            placeholder=params.placeholder,
            executor=WizardStepExecutor.CLIENT,
        )

        # 转换为字符串
        if result is None:
            value = ""
        elif isinstance(result, str):
            value = result
        elif isinstance(result, (int, float, bool)):
            value = str(result)
        else:
            value = ""

        # 验证
        if params.validate:
            error = params.validate(value)
            if error:
                raise ValueError(error)

        return value

    async def confirm(self, params: WizardConfirmParams) -> bool:
        """确认提示"""
        result = await self._prompt(
            step_type=WizardStepType.CONFIRM,
            message=params.message,
            initial_value=params.initial_value,
            executor=WizardStepExecutor.CLIENT,
        )
        return bool(result)

    def progress(self, label: str) -> WizardProgress:
        """显示进度"""
        return NoOpProgress()

    async def _prompt(
        self,
        step_type: WizardStepType,
        message: str | None = None,
        title: str | None = None,
        options: list[WizardSelectOption] | None = None,
        initial_value: Any = None,
        placeholder: str | None = None,
        sensitive: bool = False,
        executor: WizardStepExecutor = WizardStepExecutor.CLIENT,
    ) -> Any:
        """内部提示方法"""
        step = WizardStep(
            id=str(uuid.uuid4()),
            type=step_type,
            title=title,
            message=message,
            options=options,
            initial_value=initial_value,
            placeholder=placeholder,
            sensitive=sensitive,
            executor=executor,
        )
        return await self._session.await_answer(step)


# ============================================================================
# Wizard Session
# ============================================================================


class WizardSession:
    """
    向导会话

    管理向导的步骤流程和状态

    对标 MoltBot WizardSession
    """

    def __init__(
        self,
        runner: Callable[[WizardPrompter], Awaitable[None]],
    ) -> None:
        """
        初始化向导会话

        Args:
            runner: 向导运行函数，接收 prompter 参数
        """
        self._current_step: WizardStep | None = None
        self._step_deferred: Deferred | None = None
        self._answer_deferreds: dict[str, Deferred] = {}
        self._status = WizardSessionStatus.RUNNING
        self._error: str | None = None
        self._runner = runner

        # 启动运行器
        prompter = WizardSessionPrompter(self)
        asyncio.create_task(self._run(prompter))

    async def next(self) -> WizardNextResult:
        """
        获取下一个步骤

        对标 MoltBot WizardSession.next()
        """
        # 如果有当前步骤，返回它
        if self._current_step:
            return WizardNextResult(
                done=False,
                step=self._current_step,
                status=self._status,
            )

        # 如果会话不在运行状态，返回完成
        if self._status != WizardSessionStatus.RUNNING:
            return WizardNextResult(
                done=True,
                status=self._status,
                error=self._error,
            )

        # 等待下一个步骤
        if not self._step_deferred:
            self._step_deferred = create_deferred()

        step = await self._step_deferred.promise

        if step:
            return WizardNextResult(
                done=False,
                step=step,
                status=self._status,
            )

        return WizardNextResult(
            done=True,
            status=self._status,
            error=self._error,
        )

    async def answer(self, step_id: str, value: Any) -> None:
        """
        提交答案

        对标 MoltBot WizardSession.answer()
        """
        deferred = self._answer_deferreds.get(step_id)
        if not deferred:
            raise RuntimeError("wizard: no pending step")

        del self._answer_deferreds[step_id]
        self._current_step = None
        deferred.resolve(value)

    def cancel(self) -> None:
        """
        取消向导

        对标 MoltBot WizardSession.cancel()
        """
        if self._status != WizardSessionStatus.RUNNING:
            return

        self._status = WizardSessionStatus.CANCELLED
        self._error = "cancelled"
        self._current_step = None

        # 拒绝所有待处理的答案
        for deferred in self._answer_deferreds.values():
            deferred.reject(WizardCancelledError())

        self._answer_deferreds.clear()
        self._resolve_step(None)

    def push_step(self, step: WizardStep) -> None:
        """推入新步骤"""
        self._current_step = step
        self._resolve_step(step)

    async def await_answer(self, step: WizardStep) -> Any:
        """
        等待答案

        对标 MoltBot WizardSession.awaitAnswer()
        """
        if self._status != WizardSessionStatus.RUNNING:
            raise RuntimeError("wizard: session not running")

        self.push_step(step)
        deferred = create_deferred()
        self._answer_deferreds[step.id] = deferred
        return await deferred.promise

    def get_status(self) -> WizardSessionStatus:
        """获取会话状态"""
        return self._status

    def get_error(self) -> str | None:
        """获取错误信息"""
        return self._error

    async def _run(self, prompter: WizardPrompter) -> None:
        """运行向导"""
        try:
            await self._runner(prompter)
            self._status = WizardSessionStatus.DONE
        except WizardCancelledError as e:
            self._status = WizardSessionStatus.CANCELLED
            self._error = e.message
        except Exception as e:
            self._status = WizardSessionStatus.ERROR
            self._error = str(e)
        finally:
            self._resolve_step(None)

    def _resolve_step(self, step: WizardStep | None) -> None:
        """解析步骤"""
        if not self._step_deferred:
            return

        deferred = self._step_deferred
        self._step_deferred = None
        deferred.resolve(step)
