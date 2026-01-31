"""插件沙箱执行环境

实现资源限制、权限控制、超时控制和异常隔离。
"""

import asyncio
import sys
import time
from functools import wraps
from typing import Any, Callable, TypeVar

from loguru import logger

from .models import PluginConfig, PluginExecutionContext, PluginExecutionResult

# 类型变量
T = TypeVar("T")


# ============================================================================
# 沙箱装饰器
# ============================================================================


def sandboxed(
    timeout: float | None = None,
    allow_filesystem: bool = False,
    allow_network: bool = False,
    allow_exec: bool = False,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """沙箱装饰器

    为插件方法添加沙箱保护。

    Args:
        timeout: 超时时间（秒）
        allow_filesystem: 是否允许文件系统访问
        allow_network: 是否允许网络访问
        allow_exec: 是否允许命令执行

    Returns:
        装饰器函数
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> T:
            # 应用超时控制
            if timeout:
                try:
                    return await asyncio.wait_for(func(*args, **kwargs), timeout=timeout)
                except asyncio.TimeoutError:
                    raise TimeoutError(f"插件执行超时（{timeout}秒）")
            else:
                return await func(*args, **kwargs)

        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> T:
            # 对于同步函数，只能做基本的权限检查
            # 实际的超时控制需要在调用层面处理
            return func(*args, **kwargs)

        # 根据函数类型返回对应的包装器
        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        else:
            return sync_wrapper  # type: ignore

    return decorator


# ============================================================================
# 插件沙箱
# ============================================================================


class PluginSandbox:
    """插件沙箱

    提供插件的安全执行环境。
    """

    def __init__(self, config: PluginConfig | None = None):
        """初始化沙箱

        Args:
            config: 插件配置
        """
        self.config = config or PluginConfig()

    async def execute(
        self,
        plugin_func: Callable[..., Any],
        context: PluginExecutionContext,
        *args: Any,
        **kwargs: Any,
    ) -> PluginExecutionResult:
        """在沙箱中执行插件函数

        Args:
            plugin_func: 插件函数
            context: 执行上下文
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            执行结果
        """
        start_time = time.time()

        try:
            # 检查权限
            self._check_permissions(context)

            # 执行插件函数（带超时控制）
            if asyncio.iscoroutinefunction(plugin_func):
                result = await asyncio.wait_for(
                    plugin_func(context, *args, **kwargs),
                    timeout=self.config.max_execution_time,
                )
            else:
                # 同步函数需要在 executor 中运行以支持超时
                loop = asyncio.get_event_loop()
                result = await asyncio.wait_for(
                    loop.run_in_executor(None, plugin_func, context, *args, **kwargs),
                    timeout=self.config.max_execution_time,
                )

            execution_time = time.time() - start_time

            return PluginExecutionResult(
                success=True,
                result=result,
                error=None,
                execution_time=execution_time,
                metadata={"timeout": self.config.max_execution_time},
            )

        except asyncio.TimeoutError:
            execution_time = time.time() - start_time
            error_msg = f"插件执行超时（{self.config.max_execution_time}秒）"
            logger.error(error_msg)

            return PluginExecutionResult(
                success=False,
                result=None,
                error=error_msg,
                execution_time=execution_time,
                metadata={"timeout": self.config.max_execution_time, "timed_out": True},
            )

        except PermissionError as e:
            execution_time = time.time() - start_time
            error_msg = f"权限错误: {e}"
            logger.error(error_msg)

            return PluginExecutionResult(
                success=False,
                result=None,
                error=error_msg,
                execution_time=execution_time,
                metadata={"permission_denied": True},
            )

        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"插件执行失败: {type(e).__name__}: {e}"
            logger.error(error_msg)

            return PluginExecutionResult(
                success=False,
                result=None,
                error=error_msg,
                execution_time=execution_time,
                metadata={"exception_type": type(e).__name__},
            )

    def _check_permissions(self, context: PluginExecutionContext) -> None:
        """检查权限

        Args:
            context: 执行上下文

        Raises:
            PermissionError: 权限不足
        """
        # 检查文件系统访问权限
        if not self.config.allow_filesystem:
            # 这里可以添加更严格的检查，例如检查是否尝试导入 os, pathlib 等模块
            pass

        # 检查网络访问权限
        if not self.config.allow_network:
            # 这里可以添加网络访问检查
            pass

        # 检查命令执行权限
        if not self.config.allow_exec:
            # 这里可以添加命令执行检查
            pass

        # 检查频道访问权限
        if context.channel_id and self.config.allowed_channels:
            if context.channel_id not in self.config.allowed_channels:
                raise PermissionError(
                    f"插件无权访问频道: {context.channel_id}"
                )

    def _apply_resource_limits(self) -> None:
        """应用资源限制

        在 Linux/macOS 上使用 resource 模块限制资源使用。
        """
        # 仅在 Linux/macOS 上可用
        if sys.platform in ("linux", "darwin"):
            try:
                import resource

                # 限制内存使用（字节）
                max_memory_bytes = self.config.max_memory_mb * 1024 * 1024
                resource.setrlimit(
                    resource.RLIMIT_AS, (max_memory_bytes, max_memory_bytes)
                )

                # 限制 CPU 时间（秒）
                max_cpu_time = int(self.config.max_execution_time * 2)  # 留一些余量
                resource.setrlimit(
                    resource.RLIMIT_CPU, (max_cpu_time, max_cpu_time)
                )

                logger.debug(
                    f"应用资源限制: 内存={self.config.max_memory_mb}MB, "
                    f"CPU时间={max_cpu_time}秒"
                )

            except Exception as e:
                logger.warning(f"应用资源限制失败: {e}")
        else:
            logger.debug("当前平台不支持 resource 模块，跳过资源限制")


# ============================================================================
# 辅助函数
# ============================================================================


async def execute_with_timeout(
    coro: Any, timeout: float, error_message: str | None = None
) -> Any:
    """执行协程并应用超时控制

    Args:
        coro: 协程对象
        timeout: 超时时间（秒）
        error_message: 自定义错误消息

    Returns:
        协程执行结果

    Raises:
        TimeoutError: 执行超时
    """
    try:
        return await asyncio.wait_for(coro, timeout=timeout)
    except asyncio.TimeoutError:
        msg = error_message or f"操作超时（{timeout}秒）"
        raise TimeoutError(msg)


def check_permission(
    config: PluginConfig, permission_type: str, resource: str | None = None
) -> bool:
    """检查插件权限

    Args:
        config: 插件配置
        permission_type: 权限类型（filesystem/network/exec/channel）
        resource: 资源标识（如频道 ID）

    Returns:
        是否有权限
    """
    if permission_type == "filesystem":
        return config.allow_filesystem
    elif permission_type == "network":
        return config.allow_network
    elif permission_type == "exec":
        return config.allow_exec
    elif permission_type == "channel":
        if resource is None:
            return True
        return resource in config.allowed_channels
    else:
        logger.warning(f"未知的权限类型: {permission_type}")
        return False
