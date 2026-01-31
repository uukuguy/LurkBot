"""插件市场测试"""

import json
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from lurkbot.plugins.manager import PluginManager
from lurkbot.plugins.marketplace import (
    PluginIndex,
    PluginMarketplace,
    PluginPackageInfo,
    get_marketplace,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def plugin_manager():
    """创建插件管理器"""
    return PluginManager()


@pytest.fixture
def marketplace(plugin_manager, tmp_path):
    """创建插件市场"""
    cache_dir = tmp_path / "cache"
    return PluginMarketplace(
        plugin_manager,
        index_url="https://test.example.com/index.json",
        cache_dir=cache_dir,
    )


@pytest.fixture
def sample_index():
    """创建示例索引"""
    return PluginIndex(
        version="1.0.0",
        plugins={
            "test-plugin": [
                PluginPackageInfo(
                    name="test-plugin",
                    version="1.0.0",
                    description="Test plugin",
                    author="Test Author",
                    download_url="https://test.example.com/test-plugin-1.0.0.tar.gz",
                    checksum="abc123",
                    tags=["test", "example"],
                    downloads=100,
                    rating=4.5,
                )
            ],
            "another-plugin": [
                PluginPackageInfo(
                    name="another-plugin",
                    version="2.0.0",
                    description="Another plugin",
                    author="Another Author",
                    download_url="https://test.example.com/another-plugin-2.0.0.tar.gz",
                    tags=["utility"],
                    downloads=50,
                    rating=4.0,
                )
            ],
        },
    )


# ============================================================================
# PluginPackageInfo 测试
# ============================================================================


def test_plugin_package_info_creation():
    """测试插件包信息创建"""
    info = PluginPackageInfo(
        name="test-plugin",
        version="1.0.0",
        description="Test plugin",
        author="Test Author",
        download_url="https://example.com/plugin.tar.gz",
    )
    assert info.name == "test-plugin"
    assert info.version == "1.0.0"
    assert info.downloads == 0
    assert info.rating == 0.0


# ============================================================================
# PluginIndex 测试
# ============================================================================


def test_plugin_index_creation(sample_index):
    """测试插件索引创建"""
    assert sample_index.version == "1.0.0"
    assert len(sample_index.plugins) == 2
    assert "test-plugin" in sample_index.plugins


# ============================================================================
# PluginMarketplace 测试
# ============================================================================


def test_marketplace_init(marketplace, tmp_path):
    """测试市场初始化"""
    assert marketplace.manager is not None
    assert marketplace.index_url == "https://test.example.com/index.json"
    assert marketplace.cache_dir == tmp_path / "cache"
    assert marketplace.cache_dir.exists()


@pytest.mark.asyncio
async def test_marketplace_close(marketplace):
    """测试市场关闭"""
    await marketplace.close()
    # 验证 HTTP 客户端已关闭
    assert marketplace._client.is_closed


@pytest.mark.asyncio
async def test_refresh_index_success(marketplace, sample_index):
    """测试刷新索引成功"""
    # Mock HTTP 响应
    mock_response = MagicMock()
    mock_response.json.return_value = sample_index.model_dump(mode="json")
    mock_response.raise_for_status = MagicMock()

    with patch.object(marketplace._client, "get", return_value=mock_response):
        await marketplace.refresh_index()

    assert marketplace._index is not None
    assert len(marketplace._index.plugins) == 2


@pytest.mark.asyncio
async def test_refresh_index_from_cache(marketplace, sample_index, tmp_path):
    """测试从缓存加载索引"""
    # 创建缓存文件
    cache_file = marketplace.cache_dir / "index.json"
    cache_file.write_text(json.dumps(sample_index.model_dump(mode="json"), default=str))

    # Mock HTTP 请求失败
    with patch.object(
        marketplace._client, "get", side_effect=Exception("Network error")
    ):
        await marketplace.refresh_index()

    # 应该从缓存加载
    assert marketplace._index is not None
    assert len(marketplace._index.plugins) == 2


@pytest.mark.asyncio
async def test_search_by_query(marketplace, sample_index):
    """测试按关键词搜索"""
    marketplace._index = sample_index

    results = await marketplace.search(query="test")
    assert len(results) == 1
    assert results[0].name == "test-plugin"


@pytest.mark.asyncio
async def test_search_by_tags(marketplace, sample_index):
    """测试按标签搜索"""
    marketplace._index = sample_index

    results = await marketplace.search(tags=["utility"])
    assert len(results) == 1
    assert results[0].name == "another-plugin"


@pytest.mark.asyncio
async def test_search_with_limit(marketplace, sample_index):
    """测试搜索数量限制"""
    marketplace._index = sample_index

    results = await marketplace.search(limit=1)
    assert len(results) == 1


@pytest.mark.asyncio
async def test_get_plugin_info_latest(marketplace, sample_index):
    """测试获取最新版本插件信息"""
    marketplace._index = sample_index

    info = await marketplace.get_plugin_info("test-plugin")
    assert info is not None
    assert info.name == "test-plugin"
    assert info.version == "1.0.0"


@pytest.mark.asyncio
async def test_get_plugin_info_specific_version(marketplace, sample_index):
    """测试获取指定版本插件信息"""
    marketplace._index = sample_index

    info = await marketplace.get_plugin_info("test-plugin", "1.0.0")
    assert info is not None
    assert info.version == "1.0.0"


@pytest.mark.asyncio
async def test_get_plugin_info_not_found(marketplace, sample_index):
    """测试获取不存在的插件"""
    marketplace._index = sample_index

    info = await marketplace.get_plugin_info("non-existent")
    assert info is None


@pytest.mark.asyncio
async def test_list_installed(marketplace, plugin_manager):
    """测试列出已安装插件"""
    # 这个测试需要实际加载插件，暂时跳过
    installed = await marketplace.list_installed()
    assert isinstance(installed, list)


# ============================================================================
# 全局单例测试
# ============================================================================


def test_get_marketplace_singleton(plugin_manager, tmp_path):
    """测试全局单例"""
    # 清除全局单例
    import lurkbot.plugins.marketplace as marketplace_module

    marketplace_module._marketplace = None

    # 首次调用需要提供参数
    cache_dir = tmp_path / "cache"
    market1 = get_marketplace(plugin_manager, cache_dir=cache_dir)
    assert market1 is not None

    # 第二次调用返回同一个实例
    market2 = get_marketplace()
    assert market1 is market2

    # 清理
    marketplace_module._marketplace = None


def test_get_marketplace_no_manager():
    """测试没有提供管理器时抛出异常"""
    # 清除全局单例
    import lurkbot.plugins.marketplace as marketplace_module

    marketplace_module._marketplace = None

    # 首次调用没有提供管理器应该抛出异常
    with pytest.raises(ValueError, match="首次调用必须提供 manager 参数"):
        get_marketplace()

    # 清理
    marketplace_module._marketplace = None
