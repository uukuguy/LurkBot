"""连接池性能测试

测试 HTTP 连接池和 WebSocket 连接管理的性能提升。
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from starlette.websockets import WebSocketState

from lurkbot.gateway.connection_pool import HTTPConnectionPool, WebSocketConnectionManager


class TestHTTPConnectionPoolPerformance:
    """HTTP 连接池性能测试"""

    @pytest.mark.benchmark(group="http_pool")
    def test_session_creation_with_pool(self, benchmark):
        """测试使用连接池创建 session 的性能"""

        async def create_with_pool():
            pool = HTTPConnectionPool()
            await pool.start()
            session = pool.get_session()
            await pool.close()
            return session

        result = benchmark(lambda: asyncio.run(create_with_pool()))
        assert result is not None

    @pytest.mark.benchmark(group="http_pool")
    def test_session_creation_without_pool(self, benchmark):
        """测试不使用连接池创建 session 的性能（基线）"""
        import aiohttp

        async def create_without_pool():
            session = aiohttp.ClientSession()
            await session.close()
            return session

        result = benchmark(lambda: asyncio.run(create_without_pool()))
        assert result is not None

    @pytest.mark.benchmark(group="http_pool")
    def test_get_stats_performance(self, benchmark):
        """测试获取统计信息的性能"""

        async def get_stats():
            pool = HTTPConnectionPool()
            await pool.start()
            stats = pool.get_stats()
            await pool.close()
            return stats

        result = benchmark(lambda: asyncio.run(get_stats()))
        assert result is not None


class TestWebSocketConnectionManagerPerformance:
    """WebSocket 连接管理器性能测试"""

    @pytest.mark.benchmark(group="ws_manager")
    def test_add_connection_performance(self, benchmark):
        """测试添加连接的性能"""

        async def add_connections():
            manager = WebSocketConnectionManager(max_connections=1000)
            connections = []

            # 创建 100 个模拟连接
            for i in range(100):
                conn = MagicMock()
                conn.close = AsyncMock()
                connections.append((f"conn{i}", conn))

            # 添加所有连接
            for conn_id, conn in connections:
                await manager.add_connection(conn_id, conn)

            # 清理
            for conn_id, _ in connections:
                await manager.remove_connection(conn_id)

            return len(connections)

        result = benchmark(lambda: asyncio.run(add_connections()))
        assert result == 100

    @pytest.mark.benchmark(group="ws_manager")
    def test_remove_connection_performance(self, benchmark):
        """测试移除连接的性能"""

        async def remove_connections():
            manager = WebSocketConnectionManager(max_connections=1000)
            connections = []

            # 创建并添加 100 个模拟连接
            for i in range(100):
                conn = MagicMock()
                conn.close = AsyncMock()
                conn_id = f"conn{i}"
                await manager.add_connection(conn_id, conn)
                connections.append(conn_id)

            # 移除所有连接
            for conn_id in connections:
                await manager.remove_connection(conn_id)

            return len(connections)

        result = benchmark(lambda: asyncio.run(remove_connections()))
        assert result == 100

    @pytest.mark.benchmark(group="ws_manager")
    def test_health_check_performance(self, benchmark):
        """测试健康检查的性能"""

        async def health_check():
            manager = WebSocketConnectionManager()

            # 创建 100 个模拟连接（50 个正常，50 个断开）
            for i in range(100):
                conn = MagicMock()
                conn.websocket = MagicMock()
                conn.websocket.client_state = (
                    WebSocketState.CONNECTED if i < 50 else WebSocketState.DISCONNECTED
                )
                conn.close = AsyncMock()
                await manager.add_connection(f"conn{i}", conn)

            # 执行健康检查
            await manager.health_check()

            # 应该剩余 50 个连接
            remaining = len(manager.connections)

            # 清理
            for conn_id in list(manager.connections.keys()):
                await manager.remove_connection(conn_id)

            return remaining

        result = benchmark(lambda: asyncio.run(health_check()))
        assert result == 50

    @pytest.mark.benchmark(group="ws_manager")
    def test_get_connection_performance(self, benchmark):
        """测试获取连接的性能"""

        async def get_connections():
            manager = WebSocketConnectionManager()

            # 添加 100 个连接
            for i in range(100):
                conn = MagicMock()
                conn.close = AsyncMock()
                await manager.add_connection(f"conn{i}", conn)

            # 获取所有连接
            results = []
            for i in range(100):
                conn = manager.get_connection(f"conn{i}")
                results.append(conn)

            # 清理
            for i in range(100):
                await manager.remove_connection(f"conn{i}")

            return len(results)

        result = benchmark(lambda: asyncio.run(get_connections()))
        assert result == 100

    @pytest.mark.benchmark(group="ws_manager")
    def test_get_stats_performance(self, benchmark):
        """测试获取统计信息的性能"""

        async def get_stats():
            manager = WebSocketConnectionManager()

            # 添加 100 个连接
            for i in range(100):
                conn = MagicMock()
                conn.close = AsyncMock()
                await manager.add_connection(f"conn{i}", conn)

            # 获取统计信息
            stats = manager.get_stats()

            # 清理
            for i in range(100):
                await manager.remove_connection(f"conn{i}")

            return stats

        result = benchmark(lambda: asyncio.run(get_stats()))
        assert result["total_connections"] == 100


class TestConnectionPoolIntegration:
    """连接池集成性能测试"""

    @pytest.mark.benchmark(group="integration")
    def test_concurrent_operations(self, benchmark):
        """测试并发操作的性能"""

        async def concurrent_ops():
            # 创建 HTTP 连接池
            http_pool = HTTPConnectionPool(max_connections=50)
            await http_pool.start()

            # 创建 WebSocket 连接管理器
            ws_manager = WebSocketConnectionManager(max_connections=100)

            # 并发添加 50 个 WebSocket 连接
            tasks = []
            for i in range(50):
                conn = MagicMock()
                conn.close = AsyncMock()
                task = ws_manager.add_connection(f"conn{i}", conn)
                tasks.append(task)

            await asyncio.gather(*tasks)

            # 获取统计信息
            http_stats = http_pool.get_stats()
            ws_stats = ws_manager.get_stats()

            # 清理
            for i in range(50):
                await ws_manager.remove_connection(f"conn{i}")
            await http_pool.close()

            return {
                "http_connections": http_stats["total_connections"],
                "ws_connections": ws_stats["total_connections"],
            }

        result = benchmark(lambda: asyncio.run(concurrent_ops()))
        assert result["ws_connections"] == 50

    @pytest.mark.benchmark(group="integration")
    def test_lifecycle_performance(self, benchmark):
        """测试完整生命周期的性能"""

        async def lifecycle():
            # 创建并启动
            http_pool = HTTPConnectionPool()
            ws_manager = WebSocketConnectionManager()

            await http_pool.start()
            await ws_manager.start()

            # 添加一些连接
            for i in range(10):
                conn = MagicMock()
                conn.close = AsyncMock()
                await ws_manager.add_connection(f"conn{i}", conn)

            # 获取统计信息
            http_stats = http_pool.get_stats()
            ws_stats = ws_manager.get_stats()

            # 关闭
            await ws_manager.close()
            await http_pool.close()

            return {
                "http_stats": http_stats,
                "ws_stats": ws_stats,
            }

        result = benchmark(lambda: asyncio.run(lifecycle()))
        assert result["ws_stats"]["total_connections"] == 10
