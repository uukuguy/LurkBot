"""租户中间件

提供 FastAPI 中间件用于租户验证和上下文设置。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from fastapi import Request, Response
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from .errors import TenantError, TenantInactiveError, TenantNotFoundError
from .isolation import set_current_tenant

if TYPE_CHECKING:
    from .manager import TenantManager


class TenantMiddleware(BaseHTTPMiddleware):
    """租户中间件

    从请求中提取 tenant_id 并设置租户上下文。
    """

    # 默认 Header 名称
    TENANT_HEADER = "X-Tenant-ID"
    # 默认 Query 参数名称
    TENANT_QUERY_PARAM = "tenant_id"

    def __init__(
        self,
        app: ASGIApp,
        tenant_manager: TenantManager,
        header_name: str | None = None,
        query_param: str | None = None,
        required: bool = False,
        exclude_paths: list[str] | None = None,
    ) -> None:
        """初始化租户中间件

        Args:
            app: ASGI 应用
            tenant_manager: 租户管理器
            header_name: 自定义 Header 名称
            query_param: 自定义 Query 参数名称
            required: 是否必须提供 tenant_id
            exclude_paths: 排除的路径列表（不进行租户验证）
        """
        super().__init__(app)
        self._tenant_manager = tenant_manager
        self._header_name = header_name or self.TENANT_HEADER
        self._query_param = query_param or self.TENANT_QUERY_PARAM
        self._required = required
        self._exclude_paths = exclude_paths or ["/health", "/docs", "/openapi.json"]

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Response],
    ) -> Response:
        """处理请求

        Args:
            request: HTTP 请求
            call_next: 下一个处理器

        Returns:
            HTTP 响应
        """
        # 检查是否排除路径
        if self._is_excluded_path(request.url.path):
            return await call_next(request)

        # 提取 tenant_id
        tenant_id = self._extract_tenant_id(request)

        if not tenant_id:
            if self._required:
                return self._error_response(
                    status_code=401,
                    code="AUTHENTICATION_REQUIRED",
                    message="Missing tenant_id",
                )
            # 无 tenant_id 时继续处理（向后兼容）
            return await call_next(request)

        try:
            # 验证租户
            tenant = await self._tenant_manager.get_tenant(tenant_id)

            if not tenant:
                return self._error_response(
                    status_code=404,
                    code="TENANT_NOT_FOUND",
                    message=f"Tenant not found: {tenant_id}",
                )

            if not tenant.is_active():
                return self._error_response(
                    status_code=403,
                    code="TENANT_INACTIVE",
                    message=f"Tenant is not active: {tenant_id}, status={tenant.status.value}",
                )

            # 设置租户上下文
            context = await self._tenant_manager.enter_context(tenant_id)

            # 将租户信息添加到请求状态
            request.state.tenant_id = tenant_id
            request.state.tenant = tenant
            request.state.tenant_context = context

            logger.debug(f"Tenant context set: {tenant_id}")

            try:
                response = await call_next(request)
                return response
            finally:
                # 退出租户上下文
                await self._tenant_manager.exit_context()

        except TenantNotFoundError as e:
            return self._error_response(
                status_code=404,
                code=e.code.value,
                message=e.message,
            )
        except TenantInactiveError as e:
            return self._error_response(
                status_code=403,
                code=e.code.value,
                message=e.message,
            )
        except TenantError as e:
            return self._error_response(
                status_code=400,
                code=e.code.value,
                message=e.message,
            )
        except Exception as e:
            logger.error(f"Tenant middleware error: {e}")
            return self._error_response(
                status_code=500,
                code="INTERNAL_ERROR",
                message="Internal server error",
            )

    def _extract_tenant_id(self, request: Request) -> str | None:
        """从请求中提取 tenant_id

        优先级：Header > Query Parameter

        Args:
            request: HTTP 请求

        Returns:
            tenant_id 或 None
        """
        # 从 Header 提取
        tenant_id = request.headers.get(self._header_name)
        if tenant_id:
            return tenant_id

        # 从 Query 参数提取
        tenant_id = request.query_params.get(self._query_param)
        if tenant_id:
            return tenant_id

        return None

    def _is_excluded_path(self, path: str) -> bool:
        """检查是否为排除路径

        Args:
            path: 请求路径

        Returns:
            是否排除
        """
        for excluded in self._exclude_paths:
            if path.startswith(excluded):
                return True
        return False

    def _error_response(
        self,
        status_code: int,
        code: str,
        message: str,
    ) -> Response:
        """创建错误响应

        Args:
            status_code: HTTP 状态码
            code: 错误码
            message: 错误消息

        Returns:
            JSON 错误响应
        """
        import json

        return Response(
            content=json.dumps({
                "error": {
                    "code": code,
                    "message": message,
                }
            }),
            status_code=status_code,
            media_type="application/json",
        )


def get_tenant_from_request(request: Request) -> tuple[str | None, any]:
    """从请求中获取租户信息

    Args:
        request: HTTP 请求

    Returns:
        (tenant_id, tenant) 元组
    """
    tenant_id = getattr(request.state, "tenant_id", None)
    tenant = getattr(request.state, "tenant", None)
    return tenant_id, tenant


def require_tenant(request: Request) -> str:
    """要求请求包含租户信息

    Args:
        request: HTTP 请求

    Returns:
        tenant_id

    Raises:
        ValueError: 无租户信息
    """
    tenant_id = getattr(request.state, "tenant_id", None)
    if not tenant_id:
        raise ValueError("Tenant context not available")
    return tenant_id
