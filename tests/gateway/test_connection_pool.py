"""连接池模块测试"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.websockets import WebSocketState

from lurkbot.gateway.connection_pool import HTTPConnectionPool, WebSocketConnectionManager


class TestHTTPConnectionPool:
    """HTTP 连接池测试"""

    @pytest.mark.asyncio
    async def test_init(self):
        """测试初始化"""
        pool = HTTPConnectionPool(
            max_connections=50,
            max_connections_per_host=20,
            connect_timeout=5.0,
            total_timeout=30.0,
        )

        assert pool.max_connections == 50
        assert pool.max_connections_per_host == 20
        assert pool.session is None
        assert not pool._closed

    @pytest.mark.asyncio
    async def test_start_and_close(self):
        """测试启动和关闭"""
        pool = HTTPConnectionPool()

        # 启动
        await pool.start()
        assert pool.session is not None
        assert not pool._closed

        # 关闭
        await pool.close()
        assert pool.session is None
        assert pool._closed

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """测试上下文管理器"""
        async with HTTPConnectionPool() as pool:
            assert pool.session is not None
            assert not pool._closed

        assert pool._closed

    @pytest.mark.asyncio
    async def test_get_session(self):
        """测试获取 session"""
        pool = HTTPConnectionPool()

        # 未启动时应抛出异常
        with pytest.raises(RuntimeError, match="HTTP 连接池未启动"):
            pool.get_session()

        # 启动后可以获取
        await pool.start()
        session = pool.get_session()
        assert session is not None

        await pool.close()

    @pytest.mark.asyncio
    async def test_get_stats(self):
        """测试获取统计信息"""
        pool = HTTPConnectionPool(max_connections=50, max_connections_per_host=20)

        # 未启动时
        stats = pool.get_stats()
        assert stats["total_connections"] == 0
        assert stats["max_connections"] == 50
        assert stats["max_connections_per_host"] == 20

        # 启动后
        await pool.start()
        stats = pool.get_stats()
        assert "total_connections" in stats
        assert stats["max_connections"] == 50

        await pool.close()

    @pytest.mark.asyncio
    async def test_double_start(self):
        """测试重复启动"""
        pool = HTTPConnectionPool()

        await pool.start()
        await pool.start()  # 应该不会报错

        await pool.close()

    @pytest.mark.asyncio
    async def test_double_close(self):
        """测试重复关闭"""
        pool = HTTPConnectionPool()

        await pool.start()
        await pool.close()
        await pool.close()  # 应该不会报错


class TestWebSocketConnectionManager:
    """WebSocket 连接管理器测试"""

    @pytest.mark.asyncio
    async def test_init(self):
        """测试初始化"""
        manager = WebSocketConnectionManager(
            max_connections=500,
            health_check_interval=30.0,
            connection_timeout=120.0,
        )

        assert manager.max_connections == 500
        assert manager.health_check_interval == 30.0
        assert manager.connection_timeout == 120.0
        assert len(manager.connections) == 0
        assert not manager._closed

    @pytest.mark.asyncio
    async def test_start_and_close(self):
        """测试启动和关闭"""
        manager = WebSocketConnectionManager()

        # 启动
        await manager.start()
        assert manager._health_check_task is not None
        assert not manager._closed

        # 关闭
        await manager.close()
        assert manager._health_check_task is None
        assert manager._closed

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """测试上下文管理器"""
        async with WebSocketConnectionManager() as manager:
            assert manager._health_check_task is not None
            assert not manager._closed

        assert manager._closed

    @pytest.mark.asyncio
    async def test_add_connection(self):
        """测试添加连接"""
        manager = WebSocketConnectionManager(max_connections=2)

        # 创建模拟连接
        conn1 = MagicMock()
        conn2 = MagicMock()
        conn3 = MagicMock()

        # 添加连接
        await manager.add_connection("conn1", conn1)
        assert len(manager.connections) == 1

        await manager.add_connection("conn2", conn2)
        assert len(manager.connections) == 2

        # 超过最大连接数
        with pytest.raises(ValueError, match="达到最大连接数限制"):
            await manager.add_connection("conn3", conn3)

    @pytest.mark.asyncio
    async def test_remove_connection(self):
        """测试移除连接"""
        manager = WebSocketConnectionManager()

        # 创建模拟连接
        conn = MagicMock()
        conn.close = AsyncMock()

        # 添加并移除
        await manager.add_connection("conn1", conn)
        assert len(manager.connections) == 1

        await manager.remove_connection("conn1")
        assert len(manager.connections) == 0
        conn.close.assert_called_once()

        # 移除不存在的连接
        await manager.remove_connection("nonexistent")  # 应该不会报错

    @pytest.mark.asyncio
    async def test_get_connection(self):
        """测试获取连接"""
        manager = WebSocketConnectionManager()

        # 创建模拟连接
        conn = MagicMock()

        # 添加连接
        await manager.add_connection("conn1", conn)

        # 获取连接
        result = manager.get_connection("conn1")
        assert result is conn

        # 获取不存在的连接
        result = manager.get_connection("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_stats(self):
        """测试获取统计信息"""
        manager = WebSocketConnectionManager(max_connections=100)

        # 空连接
        stats = manager.get_stats()
        assert stats["total_connections"] == 0
        assert stats["max_connections"] == 100
        assert stats["connection_ids"] == []

        # 添加连接
        conn = MagicMock()
        await manager.add_connection("conn1", conn)

        stats = manager.get_stats()
        assert stats["total_connections"] == 1
        assert "conn1" in stats["connection_ids"]

    @pytest.mark.asyncio
    async def test_health_check_removes_disconnected(self):
        """测试健康检查移除断开的连接"""
        manager = WebSocketConnectionManager()

        # 创建模拟连接（已连接）
        conn1 = MagicMock()
        conn1.websocket = MagicMock()
        conn1.websocket.client_state = WebSocketState.CONNECTED
        conn1.close = AsyncMock()

        # 创建模拟连接（已断开）
        conn2 = MagicMock()
        conn2.websocket = MagicMock()
        conn2.websocket.client_state = WebSocketState.DISCONNECTED
        conn2.close = AsyncMock()

        # 添加连接
        await manager.add_connection("conn1", conn1)
        await manager.add_connection("conn2", conn2)
        assert len(manager.connections) == 2

        # 执行健康检查
        await manager.health_check()

        # 断开的连接应该被移除
        assert len(manager.connections) == 1
        assert "conn1" in manager.connections
        assert "conn2" not in manager.connections
        conn2.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_health_check_removes_invalid(self):
        """测试健康检查移除无效连接"""
        manager = WebSocketConnectionManager()

        # 创建无效连接（没有 websocket 属性）
        conn = MagicMock(spec=[])  # 空 spec，没有任何属性
        conn.close = AsyncMock()

        await manager.add_connection("conn1", conn)
        assert len(manager.connections) == 1

        # 执行健康检查
        await manager.health_check()

        # 无效连接应该被移除
        assert len(manager.connections) == 0
        conn.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_health_check_empty_connections(self):
        """测试空连接列表的健康检查"""
        manager = WebSocketConnectionManager()

        # 执行健康检查（无连接）
        await manager.health_check()  # 应该不会报错

    @pytest.mark.asyncio
    async def test_health_check_loop(self):
        """测试健康检查循环"""
        manager = WebSocketConnectionManager(health_check_interval=0.1)

        # 创建模拟连接（已断开）
        conn = MagicMock()
        conn.websocket = MagicMock()
        conn.websocket.client_state = WebSocketState.DISCONNECTED
        conn.close = AsyncMock()

        await manager.start()
        await manager.add_connection("conn1", conn)

        # 等待健康检查执行
        await asyncio.sleep(0.2)

        # 断开的连接应该被移除
        assert len(manager.connections) == 0

        await manager.close()

    @pytest.mark.asyncio
    async def test_close_removes_all_connections(self):
        """测试关闭时移除所有连接"""
        manager = WebSocketConnectionManager()

        # 创建多个模拟连接
        conn1 = MagicMock()
        conn1.close = AsyncMock()
        conn2 = MagicMock()
        conn2.close = AsyncMock()

        await manager.add_connection("conn1", conn1)
        await manager.add_connection("conn2", conn2)
        assert len(manager.connections) == 2

        # 关闭管理器
        await manager.close()

        # 所有连接应该被移除
        assert len(manager.connections) == 0
        conn1.close.assert_called_once()
        conn2.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_double_start(self):
        """测试重复启动"""
        manager = WebSocketConnectionManager()

        await manager.start()
        await manager.start()  # 应该不会报错

        await manager.close()

    @pytest.mark.asyncio
    async def test_double_close(self):
        """测试重复关闭"""
        manager = WebSocketConnectionManager()

        await manager.start()
        await manager.close()
        await manager.close()  # 应该不会报错
