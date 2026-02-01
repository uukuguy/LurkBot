"""连接池管理模块

提供 HTTP 连接池和 WebSocket 连接管理功能，优化连接复用和资源管理。

主要功能：
- HTTP 连接池管理（基于 aiohttp）
- WebSocket 连接生命周期管理
- 连接健康检查
- 连接池监控指标
"""

import asyncio
from typing import TYPE_CHECKING

import aiohttp
from loguru import logger

if TYPE_CHECKING:
    from lurkbot.gateway.connection import GatewayConnection


class HTTPConnectionPool:
    """HTTP 连接池

    使用 aiohttp ClientSession 和 TCPConnector 实现高效的 HTTP 连接池。

    特性：
    - 连接复用
    - 连接数限制
    - 超时控制
    - DNS 缓存

    Args:
        max_connections: 最大总连接数（默认 100）
        max_connections_per_host: 每个主机最大连接数（默认 30）
        connect_timeout: 连接超时时间（秒，默认 10.0）
        sock_read_timeout: 读取超时时间（秒，默认 30.0）
        total_timeout: 总超时时间（秒，默认 60.0）
        keepalive_timeout: Keep-Alive 超时时间（秒，默认 30.0）
        ttl_dns_cache: DNS 缓存 TTL（秒，默认 300）
    """

    def __init__(
        self,
        max_connections: int = 100,
        max_connections_per_host: int = 30,
        connect_timeout: float = 10.0,
        sock_read_timeout: float = 30.0,
        total_timeout: float = 60.0,
        keepalive_timeout: float = 30.0,
        ttl_dns_cache: int = 300,
    ):
        self.max_connections = max_connections
        self.max_connections_per_host = max_connections_per_host

        # 创建 TCPConnector
        self.connector = aiohttp.TCPConnector(
            limit=max_connections,
            limit_per_host=max_connections_per_host,
            keepalive_timeout=keepalive_timeout,
            ttl_dns_cache=ttl_dns_cache,
            enable_cleanup_closed=True,
        )

        # 创建超时配置
        self.timeout = aiohttp.ClientTimeout(
            total=total_timeout,
            connect=connect_timeout,
            sock_read=sock_read_timeout,
        )

        self.session: aiohttp.ClientSession | None = None
        self._closed = False

        logger.info(
            f"HTTP 连接池初始化: "
            f"max_connections={max_connections}, "
            f"max_per_host={max_connections_per_host}, "
            f"timeout={total_timeout}s"
        )

    async def start(self) -> None:
        """启动连接池"""
        if self.session is not None:
            logger.warning("HTTP 连接池已启动")
            return

        self.session = aiohttp.ClientSession(
            connector=self.connector,
            timeout=self.timeout,
        )
        self._closed = False
        logger.info("HTTP 连接池已启动")

    async def close(self) -> None:
        """关闭连接池"""
        if self._closed:
            return

        if self.session is not None:
            await self.session.close()
            self.session = None

        await self.connector.close()
        self._closed = True
        logger.info("HTTP 连接池已关闭")

    def get_session(self) -> aiohttp.ClientSession:
        """获取 ClientSession

        Returns:
            aiohttp.ClientSession 实例

        Raises:
            RuntimeError: 如果连接池未启动
        """
        if self.session is None:
            raise RuntimeError("HTTP 连接池未启动，请先调用 start()")
        return self.session

    def get_stats(self) -> dict:
        """获取连接池统计信息

        Returns:
            包含连接池统计信息的字典
        """
        if self.session is None or self.session.connector is None:
            return {
                "total_connections": 0,
                "acquired_connections": 0,
                "max_connections": self.max_connections,
                "max_connections_per_host": self.max_connections_per_host,
            }

        # 获取 connector 统计信息
        connector = self.session.connector
        return {
            "total_connections": len(connector._conns),  # type: ignore
            "acquired_connections": len(connector._acquired),  # type: ignore
            "max_connections": self.max_connections,
            "max_connections_per_host": self.max_connections_per_host,
        }

    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close()


class WebSocketConnectionManager:
    """WebSocket 连接管理器

    管理 WebSocket 连接的生命周期，包括连接添加、移除和健康检查。

    特性：
    - 连接数限制
    - 连接健康检查
    - 自动清理失效连接
    - 连接统计

    Args:
        max_connections: 最大连接数（默认 1000）
        health_check_interval: 健康检查间隔（秒，默认 60）
        connection_timeout: 连接超时时间（秒，默认 300）
    """

    def __init__(
        self,
        max_connections: int = 1000,
        health_check_interval: float = 60.0,
        connection_timeout: float = 300.0,
    ):
        self.max_connections = max_connections
        self.health_check_interval = health_check_interval
        self.connection_timeout = connection_timeout

        self.connections: dict[str, "GatewayConnection"] = {}
        self._health_check_task: asyncio.Task | None = None
        self._closed = False

        logger.info(
            f"WebSocket 连接管理器初始化: "
            f"max_connections={max_connections}, "
            f"health_check_interval={health_check_interval}s"
        )

    async def start(self) -> None:
        """启动连接管理器"""
        if self._health_check_task is not None:
            logger.warning("WebSocket 连接管理器已启动")
            return

        self._closed = False
        self._health_check_task = asyncio.create_task(self._health_check_loop())
        logger.info("WebSocket 连接管理器已启动")

    async def close(self) -> None:
        """关闭连接管理器"""
        if self._closed:
            return

        self._closed = True

        # 取消健康检查任务
        if self._health_check_task is not None:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
            self._health_check_task = None

        # 关闭所有连接
        for conn_id in list(self.connections.keys()):
            await self.remove_connection(conn_id)

        logger.info("WebSocket 连接管理器已关闭")

    async def add_connection(self, conn_id: str, connection: "GatewayConnection") -> None:
        """添加连接

        Args:
            conn_id: 连接 ID
            connection: GatewayConnection 实例

        Raises:
            ValueError: 如果达到最大连接数
        """
        if len(self.connections) >= self.max_connections:
            raise ValueError(
                f"达到最大连接数限制: {self.max_connections}"
            )

        self.connections[conn_id] = connection
        logger.debug(f"添加连接: {conn_id}, 当前连接数: {len(self.connections)}")

    async def remove_connection(self, conn_id: str) -> None:
        """移除连接

        Args:
            conn_id: 连接 ID
        """
        if conn_id not in self.connections:
            return

        connection = self.connections[conn_id]
        try:
            await connection.close()
        except Exception as e:
            logger.error(f"关闭连接失败: {conn_id}, 错误: {e}")
        finally:
            del self.connections[conn_id]
            logger.debug(f"移除连接: {conn_id}, 当前连接数: {len(self.connections)}")

    def get_connection(self, conn_id: str) -> "GatewayConnection | None":
        """获取连接

        Args:
            conn_id: 连接 ID

        Returns:
            GatewayConnection 实例，如果不存在则返回 None
        """
        return self.connections.get(conn_id)

    def get_stats(self) -> dict:
        """获取连接统计信息

        Returns:
            包含连接统计信息的字典
        """
        return {
            "total_connections": len(self.connections),
            "max_connections": self.max_connections,
            "connection_ids": list(self.connections.keys()),
        }

    async def health_check(self) -> None:
        """执行健康检查

        检查所有连接的状态，移除失效连接。
        """
        if not self.connections:
            return

        logger.debug(f"开始健康检查，当前连接数: {len(self.connections)}")

        # 检查所有连接
        failed_connections = []
        for conn_id, connection in list(self.connections.items()):
            try:
                # 检查 WebSocket 连接状态
                if not hasattr(connection, "websocket"):
                    failed_connections.append(conn_id)
                    continue

                websocket = connection.websocket
                if not hasattr(websocket, "client_state"):
                    failed_connections.append(conn_id)
                    continue

                # 检查连接是否已断开
                from starlette.websockets import WebSocketState
                if websocket.client_state != WebSocketState.CONNECTED:
                    failed_connections.append(conn_id)

            except Exception as e:
                logger.error(f"健康检查失败: {conn_id}, 错误: {e}")
                failed_connections.append(conn_id)

        # 移除失效连接
        for conn_id in failed_connections:
            logger.info(f"移除失效连接: {conn_id}")
            await self.remove_connection(conn_id)

        if failed_connections:
            logger.info(
                f"健康检查完成，移除 {len(failed_connections)} 个失效连接，"
                f"当前连接数: {len(self.connections)}"
            )

    async def _health_check_loop(self) -> None:
        """健康检查循环"""
        logger.info(f"健康检查循环已启动，间隔: {self.health_check_interval}s")

        while not self._closed:
            try:
                await asyncio.sleep(self.health_check_interval)
                await self.health_check()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"健康检查循环错误: {e}")

        logger.info("健康检查循环已停止")

    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close()
