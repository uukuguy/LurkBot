"""配置提供者单元测试"""

import asyncio
import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from lurkbot.config.providers import (
    ConfigItem,
    ConfigProvider,
    ConsulConfig,
    ConsulProvider,
    LocalFileProvider,
    NacosConfig,
    NacosProvider,
    ProviderConfig,
    ProviderStatus,
    create_consul_provider,
    create_nacos_provider,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def temp_config_dir():
    """创建临时配置目录"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def provider_config():
    """创建基础提供者配置"""
    return ProviderConfig(
        name="test",
        timeout=5.0,
        retry_count=2,
        cache_enabled=True,
        cache_ttl=60,
    )


@pytest.fixture
async def local_provider(temp_config_dir, provider_config):
    """创建本地文件提供者"""
    provider = LocalFileProvider(provider_config, temp_config_dir)
    await provider.connect()
    yield provider
    await provider.disconnect()


# ============================================================================
# ConfigItem Tests
# ============================================================================


class TestConfigItem:
    """ConfigItem 测试"""

    def test_create_item(self):
        """测试创建配置项"""
        item = ConfigItem(
            key="test.key",
            value={"foo": "bar"},
            version="v1",
            content_type="json",
        )

        assert item.key == "test.key"
        assert item.value == {"foo": "bar"}
        assert item.version == "v1"
        assert item.content_type == "json"


# ============================================================================
# ProviderConfig Tests
# ============================================================================


class TestProviderConfig:
    """ProviderConfig 测试"""

    def test_default_values(self):
        """测试默认值"""
        config = ProviderConfig(name="test")

        assert config.enabled is True
        assert config.timeout == 5.0
        assert config.retry_count == 3
        assert config.cache_enabled is True
        assert config.cache_ttl == 300
        assert config.watch_enabled is True


# ============================================================================
# LocalFileProvider Tests
# ============================================================================


class TestLocalFileProvider:
    """LocalFileProvider 测试"""

    @pytest.mark.asyncio
    async def test_connect(self, temp_config_dir, provider_config):
        """测试连接"""
        provider = LocalFileProvider(provider_config, temp_config_dir)
        result = await provider.connect()

        assert result is True
        assert provider.is_connected is True
        assert provider.status == ProviderStatus.CONNECTED

        await provider.disconnect()

    @pytest.mark.asyncio
    async def test_connect_nonexistent_dir(self, provider_config):
        """测试连接不存在的目录"""
        provider = LocalFileProvider(provider_config, Path("/nonexistent"))
        result = await provider.connect()

        assert result is False
        assert provider.status == ProviderStatus.ERROR

    @pytest.mark.asyncio
    async def test_set_and_get(self, local_provider, temp_config_dir):
        """测试设置和获取配置"""
        result = await local_provider.set("test", {"key": "value"})
        assert result is True

        # 验证文件已创建
        assert (temp_config_dir / "test.json").exists()

        value = await local_provider.get("test")
        assert value == {"key": "value"}

    @pytest.mark.asyncio
    async def test_get_nonexistent(self, local_provider):
        """测试获取不存在的配置"""
        value = await local_provider.get("nonexistent", default="default")
        assert value == "default"

    @pytest.mark.asyncio
    async def test_delete(self, local_provider, temp_config_dir):
        """测试删除配置"""
        await local_provider.set("to_delete", {"key": "value"})
        assert (temp_config_dir / "to_delete.json").exists()

        result = await local_provider.delete("to_delete")
        assert result is True
        assert not (temp_config_dir / "to_delete.json").exists()

    @pytest.mark.asyncio
    async def test_list_keys(self, local_provider):
        """测试列出配置键"""
        await local_provider.set("app.config", {"a": 1})
        await local_provider.set("app.settings", {"b": 2})
        await local_provider.set("other", {"c": 3})

        keys = await local_provider.list_keys("app")
        assert "app.config" in keys
        assert "app.settings" in keys
        assert "other" not in keys

    @pytest.mark.asyncio
    async def test_health_check(self, local_provider):
        """测试健康检查"""
        result = await local_provider.health_check()
        assert result is True

    @pytest.mark.asyncio
    async def test_cache(self, local_provider, temp_config_dir):
        """测试缓存"""
        await local_provider.set("cached", {"value": 1})

        # 第一次获取（从文件）
        value1 = await local_provider.get("cached")
        assert value1 == {"value": 1}

        # 修改文件
        with open(temp_config_dir / "cached.json", "w") as f:
            json.dump({"value": 2}, f)

        # 第二次获取（从缓存）
        value2 = await local_provider.get("cached")
        assert value2 == {"value": 1}  # 仍然是缓存值

    @pytest.mark.asyncio
    async def test_callback(self, local_provider):
        """测试变更回调"""
        changes = []

        def callback(key, old_value, new_value):
            changes.append((key, old_value, new_value))

        local_provider.add_callback(callback)

        await local_provider.set("callback_test", {"v": 1})
        await local_provider.set("callback_test", {"v": 2})

        # 第二次设置应该触发回调
        assert len(changes) == 1
        assert changes[0][0] == "callback_test"
        assert changes[0][1] == {"v": 1}
        assert changes[0][2] == {"v": 2}


# ============================================================================
# NacosProvider Tests (Mocked)
# ============================================================================


class TestNacosProvider:
    """NacosProvider 测试（使用 Mock）"""

    @pytest.fixture
    def nacos_config(self):
        """创建 Nacos 配置"""
        return NacosConfig(
            name="nacos",
            server_addr="localhost:8848",
            namespace="test",
            group="DEFAULT_GROUP",
        )

    @pytest.mark.asyncio
    async def test_connect_success(self, nacos_config):
        """测试连接成功"""
        provider = NacosProvider(nacos_config)

        # Mock httpx.AsyncClient
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            result = await provider._connect()
            assert result is True

    @pytest.mark.asyncio
    async def test_get_config(self, nacos_config):
        """测试获取配置"""
        provider = NacosProvider(nacos_config)
        provider._connected = True

        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '{"key": "value"}'
        mock_client.get = AsyncMock(return_value=mock_response)
        provider._client = mock_client

        item = await provider._get("test.config")

        assert item is not None
        assert item.key == "test.config"
        assert item.value == {"key": "value"}
        assert item.content_type == "json"

    @pytest.mark.asyncio
    async def test_get_config_not_found(self, nacos_config):
        """测试获取不存在的配置"""
        provider = NacosProvider(nacos_config)
        provider._connected = True

        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_client.get = AsyncMock(return_value=mock_response)
        provider._client = mock_client

        item = await provider._get("nonexistent")
        assert item is None

    @pytest.mark.asyncio
    async def test_set_config(self, nacos_config):
        """测试设置配置"""
        provider = NacosProvider(nacos_config)
        provider._connected = True

        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "true"
        mock_client.post = AsyncMock(return_value=mock_response)
        provider._client = mock_client

        result = await provider._set("test.config", {"key": "value"})
        assert result is True

    @pytest.mark.asyncio
    async def test_delete_config(self, nacos_config):
        """测试删除配置"""
        provider = NacosProvider(nacos_config)
        provider._connected = True

        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "true"
        mock_client.delete = AsyncMock(return_value=mock_response)
        provider._client = mock_client

        result = await provider._delete("test.config")
        assert result is True

    def test_create_nacos_provider(self):
        """测试工厂函数"""
        provider = create_nacos_provider(
            server_addr="localhost:8848",
            namespace="test",
            group="TEST_GROUP",
        )

        assert isinstance(provider, NacosProvider)
        assert provider.nacos_config.server_addr == "localhost:8848"
        assert provider.nacos_config.namespace == "test"
        assert provider.nacos_config.group == "TEST_GROUP"


# ============================================================================
# ConsulProvider Tests (Mocked)
# ============================================================================


class TestConsulProvider:
    """ConsulProvider 测试（使用 Mock）"""

    @pytest.fixture
    def consul_config(self):
        """创建 Consul 配置"""
        return ConsulConfig(
            name="consul",
            host="localhost",
            port=8500,
            prefix="config/",
        )

    @pytest.mark.asyncio
    async def test_connect_success(self, consul_config):
        """测试连接成功"""
        provider = ConsulProvider(consul_config)

        with patch.object(provider, "_client", new_callable=AsyncMock) as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = '"127.0.0.1:8300"'
            mock_client.get = AsyncMock(return_value=mock_response)

            result = await provider._health_check()
            assert result is True

    @pytest.mark.asyncio
    async def test_get_config(self, consul_config):
        """测试获取配置"""
        import base64

        provider = ConsulProvider(consul_config)
        provider._connected = True

        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json = MagicMock(
            return_value=[
                {
                    "Key": "config/test.config",
                    "Value": base64.b64encode(b'{"key": "value"}').decode(),
                    "ModifyIndex": 123,
                    "CreateIndex": 100,
                }
            ]
        )
        mock_client.get = AsyncMock(return_value=mock_response)
        provider._client = mock_client

        item = await provider._get("test.config")

        assert item is not None
        assert item.key == "test.config"
        assert item.value == {"key": "value"}
        assert item.version == "123"

    @pytest.mark.asyncio
    async def test_get_config_not_found(self, consul_config):
        """测试获取不存在的配置"""
        provider = ConsulProvider(consul_config)
        provider._connected = True

        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_client.get = AsyncMock(return_value=mock_response)
        provider._client = mock_client

        item = await provider._get("nonexistent")
        assert item is None

    @pytest.mark.asyncio
    async def test_set_config(self, consul_config):
        """测试设置配置"""
        provider = ConsulProvider(consul_config)
        provider._connected = True

        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "true"
        mock_client.put = AsyncMock(return_value=mock_response)
        provider._client = mock_client

        result = await provider._set("test.config", {"key": "value"})
        assert result is True

    @pytest.mark.asyncio
    async def test_delete_config(self, consul_config):
        """测试删除配置"""
        provider = ConsulProvider(consul_config)
        provider._connected = True

        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "true"
        mock_client.delete = AsyncMock(return_value=mock_response)
        provider._client = mock_client

        result = await provider._delete("test.config")
        assert result is True

    @pytest.mark.asyncio
    async def test_list_keys(self, consul_config):
        """测试列出配置键"""
        provider = ConsulProvider(consul_config)
        provider._connected = True

        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json = MagicMock(
            return_value=["config/app.config", "config/app.settings"]
        )
        mock_client.get = AsyncMock(return_value=mock_response)
        provider._client = mock_client

        keys = await provider._list("app")

        assert "app.config" in keys
        assert "app.settings" in keys

    def test_create_consul_provider(self):
        """测试工厂函数"""
        provider = create_consul_provider(
            host="consul.example.com",
            port=8500,
            token="secret-token",
            prefix="myapp/",
        )

        assert isinstance(provider, ConsulProvider)
        assert provider.consul_config.host == "consul.example.com"
        assert provider.consul_config.port == 8500
        assert provider.consul_config.token == "secret-token"
        assert provider.consul_config.prefix == "myapp/"

    def test_get_full_key(self, consul_config):
        """测试获取完整键名"""
        provider = ConsulProvider(consul_config)

        assert provider._get_full_key("test") == "config/test"
        assert provider._get_full_key("config/test") == "config/test"

    def test_strip_prefix(self, consul_config):
        """测试去除键前缀"""
        provider = ConsulProvider(consul_config)

        assert provider._strip_prefix("config/test") == "test"
        assert provider._strip_prefix("test") == "test"


# ============================================================================
# Integration Tests
# ============================================================================


class TestProviderIntegration:
    """提供者集成测试"""

    @pytest.mark.asyncio
    async def test_provider_lifecycle(self, temp_config_dir, provider_config):
        """测试提供者生命周期"""
        provider = LocalFileProvider(provider_config, temp_config_dir)

        # 初始状态
        assert provider.status == ProviderStatus.DISCONNECTED
        assert provider.is_connected is False

        # 连接
        await provider.connect()
        assert provider.status == ProviderStatus.CONNECTED
        assert provider.is_connected is True

        # 操作
        await provider.set("lifecycle.test", {"status": "ok"})
        value = await provider.get("lifecycle.test")
        assert value == {"status": "ok"}

        # 断开
        await provider.disconnect()
        assert provider.status == ProviderStatus.DISCONNECTED
        assert provider.is_connected is False

    @pytest.mark.asyncio
    async def test_cache_fallback(self, temp_config_dir, provider_config):
        """测试缓存降级"""
        provider = LocalFileProvider(provider_config, temp_config_dir)
        await provider.connect()

        # 设置配置
        await provider.set("fallback.test", {"value": 1})

        # 获取一次（填充缓存）
        await provider.get("fallback.test")

        # 删除文件（模拟配置中心不可用）
        (temp_config_dir / "fallback.test.json").unlink()

        # 断开连接
        provider._connected = False

        # 应该从缓存获取
        value = await provider.get("fallback.test")
        assert value == {"value": 1}

        await provider.disconnect()

    @pytest.mark.asyncio
    async def test_multiple_callbacks(self, local_provider):
        """测试多个回调"""
        results1 = []
        results2 = []

        def callback1(key, old, new):
            results1.append((key, new))

        def callback2(key, old, new):
            results2.append((key, new))

        local_provider.add_callback(callback1)
        local_provider.add_callback(callback2)

        await local_provider.set("multi.callback", {"v": 1})
        await local_provider.set("multi.callback", {"v": 2})

        assert len(results1) == 1
        assert len(results2) == 1
        assert results1[0] == ("multi.callback", {"v": 2})
        assert results2[0] == ("multi.callback", {"v": 2})

        # 移除回调
        local_provider.remove_callback(callback1)
        await local_provider.set("multi.callback", {"v": 3})

        assert len(results1) == 1  # 不再增加
        assert len(results2) == 2  # 继续增加
