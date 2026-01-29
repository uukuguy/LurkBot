"""
Gateway RPC 方法注册系统

对标 MoltBot src/gateway/methods.ts
"""

from typing import Callable, Awaitable, Any
from dataclasses import dataclass
from loguru import logger

from lurkbot.gateway.protocol.frames import ErrorCode, ErrorShape


@dataclass
class MethodContext:
    """RPC 方法上下文"""

    params: dict | None
    session_key: str | None


MethodHandler = Callable[[MethodContext], Awaitable[dict | None]]


class MethodRegistry:
    """
    RPC 方法注册表

    对标 MoltBot MethodRegistry
    """

    def __init__(self):
        self._methods: dict[str, MethodHandler] = {}

    def register(self, method_name: str, handler: MethodHandler) -> None:
        """注册 RPC 方法"""
        self._methods[method_name] = handler
        logger.debug(f"Registered RPC method: {method_name}")

    def unregister(self, method_name: str) -> None:
        """取消注册 RPC 方法"""
        if method_name in self._methods:
            del self._methods[method_name]
            logger.debug(f"Unregistered RPC method: {method_name}")

    async def invoke(
        self,
        method_name: str,
        params: dict | None = None,
        session_key: str | None = None,
    ) -> dict | None:
        """调用 RPC 方法"""
        handler = self._methods.get(method_name)
        if not handler:
            raise ValueError(f"Method not found: {method_name}")

        context = MethodContext(params=params, session_key=session_key)
        return await handler(context)

    def list_methods(self) -> list[str]:
        """列出所有已注册的方法"""
        return list(self._methods.keys())

    def has_method(self, method_name: str) -> bool:
        """检查方法是否存在"""
        return method_name in self._methods


# 全局方法注册表实例
_method_registry = MethodRegistry()


def get_method_registry() -> MethodRegistry:
    """获取全局方法注册表"""
    return _method_registry

