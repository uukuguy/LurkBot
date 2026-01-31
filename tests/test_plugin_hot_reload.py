"""插件热重载测试"""

import asyncio
import time
from pathlib import Path

import pytest

from lurkbot.plugins.hot_reload import (
    HotReloadManager,
    PluginReloadHandler,
    get_hot_reload_manager,
)
from lurkbot.plugins.loader import PluginState
from lurkbot.plugins.manager import PluginManager
from lurkbot.plugins.manifest import PluginManifest


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def plugin_manager():
    """创建插件管理器"""
    return PluginManager()


@pytest.fixture
def reload_handler(plugin_manager):
    """创建热重载处理器"""
    return PluginReloadHandler(plugin_manager, debounce_seconds=0.1)


@pytest.fixture
def hot_reload_manager(plugin_manager, tmp_path):
    """创建热重载管理器"""
    watch_paths = [tmp_path / "plugins"]
    watch_paths[0].mkdir(parents=True, exist_ok=True)
    return HotReloadManager(plugin_manager, watch_paths, debounce_seconds=0.1)


@pytest.fixture
def sample_plugin_dir(tmp_path):
    """创建示例插件目录"""
    plugin_dir = tmp_path / "plugins" / "test-plugin"
    plugin_dir.mkdir(parents=True, exist_ok=True)

    # 创建 manifest.json
    manifest_content = """{
    "name": "test-plugin",
    "version": "1.0.0",
    "description": "Test plugin",
    "author": {
        "name": "Test"
    },
    "entry": "main.py",
    "enabled": true,
    "permissions": {
        "filesystem": false,
        "network": false,
        "exec": false,
        "channels": []
    }
}"""
    (plugin_dir / "manifest.json").write_text(manifest_content)

    # 创建 main.py
    main_content = '''"""Test plugin"""

async def execute(context):
    """Execute plugin"""
    return {"result": "v1"}
'''
    (plugin_dir / "main.py").write_text(main_content)

    return plugin_dir


# ============================================================================
# PluginReloadHandler 测试
# ============================================================================


def test_reload_handler_init(reload_handler, plugin_manager):
    """测试处理器初始化"""
    assert reload_handler.manager == plugin_manager
    assert reload_handler.debounce_seconds == 0.1
    assert reload_handler._pending_reloads == {}


def test_find_plugin_dir(reload_handler, sample_plugin_dir):
    """测试查找插件目录"""
    # 测试插件文件
    main_py = sample_plugin_dir / "main.py"
    found_dir = reload_handler._find_plugin_dir(main_py)
    assert found_dir == sample_plugin_dir

    # 测试非插件文件
    non_plugin_file = sample_plugin_dir.parent / "other.py"
    non_plugin_file.write_text("# other")
    found_dir = reload_handler._find_plugin_dir(non_plugin_file)
    assert found_dir is None


@pytest.mark.asyncio
async def test_reload_handler_on_modified(reload_handler, sample_plugin_dir):
    """测试文件修改事件处理"""
    from watchdog.events import FileModifiedEvent

    # 模拟文件修改事件
    event = FileModifiedEvent(str(sample_plugin_dir / "main.py"))
    reload_handler.on_modified(event)

    # 检查是否记录了待重载的插件
    assert "test-plugin" in reload_handler._pending_reloads


@pytest.mark.asyncio
async def test_reload_handler_debounce(reload_handler, sample_plugin_dir, plugin_manager):
    """测试防抖机制"""
    from watchdog.events import FileModifiedEvent
    from lurkbot.plugins.schema_validator import ManifestValidator

    # 加载插件
    manifest, errors = ManifestValidator.validate_from_file(sample_plugin_dir / "manifest.json")
    assert manifest is not None, f"Manifest validation failed: {errors}"
    await plugin_manager.load_plugin(sample_plugin_dir, manifest)

    # 模拟多次文件修改
    event = FileModifiedEvent(str(sample_plugin_dir / "main.py"))
    reload_handler.on_modified(event)
    reload_handler.on_modified(event)
    reload_handler.on_modified(event)

    # 应该只有一个待重载的插件
    assert len(reload_handler._pending_reloads) == 1

    # 等待防抖时间
    await asyncio.sleep(0.15)

    # 处理待重载的插件
    await reload_handler.process_pending_reloads()

    # 待重载列表应该为空
    assert len(reload_handler._pending_reloads) == 0


@pytest.mark.asyncio
async def test_reload_plugin_success(reload_handler, sample_plugin_dir, plugin_manager):
    """测试插件重载成功"""
    from lurkbot.plugins.schema_validator import ManifestValidator

    # 加载插件
    manifest, errors = ManifestValidator.validate_from_file(sample_plugin_dir / "manifest.json")
    assert manifest is not None, f"Manifest validation failed: {errors}"
    await plugin_manager.load_plugin(sample_plugin_dir, manifest)
    await plugin_manager.enable_plugin("test-plugin")

    # 修改插件代码
    main_py = sample_plugin_dir / "main.py"
    main_py.write_text(
        '''"""Test plugin"""

async def execute(context):
    """Execute plugin"""
    return {"result": "v2"}
'''
    )

    # 重载插件
    await reload_handler._reload_plugin("test-plugin")

    # 检查插件是否重载成功
    plugin = plugin_manager.loader.get("test-plugin")
    assert plugin is not None
    assert plugin.state in [PluginState.LOADED, PluginState.ENABLED]

    # 检查插件是否仍然启用
    assert plugin_manager.is_enabled("test-plugin")


@pytest.mark.asyncio
async def test_reload_plugin_not_found(reload_handler, plugin_manager):
    """测试重载不存在的插件"""
    # 重载不存在的插件（应该不会抛出异常）
    await reload_handler._reload_plugin("non-existent-plugin")


# ============================================================================
# HotReloadManager 测试
# ============================================================================


def test_hot_reload_manager_init(hot_reload_manager, plugin_manager):
    """测试管理器初始化"""
    assert hot_reload_manager.manager == plugin_manager
    assert hot_reload_manager.debounce_seconds == 0.1
    assert not hot_reload_manager._running


def test_hot_reload_manager_start_stop(hot_reload_manager):
    """测试启动和停止"""
    # 启动
    hot_reload_manager.start()
    assert hot_reload_manager._running
    assert hot_reload_manager._observer is not None
    assert hot_reload_manager._handler is not None

    # 停止
    hot_reload_manager.stop()
    assert not hot_reload_manager._running
    assert hot_reload_manager._observer is None


def test_hot_reload_manager_add_watch_path(hot_reload_manager, tmp_path):
    """测试添加监控路径"""
    new_path = tmp_path / "new_plugins"
    new_path.mkdir(parents=True, exist_ok=True)

    # 添加路径
    hot_reload_manager.add_watch_path(new_path)
    assert new_path in hot_reload_manager.watch_paths

    # 重复添加（应该忽略）
    hot_reload_manager.add_watch_path(new_path)
    assert hot_reload_manager.watch_paths.count(new_path) == 1


def test_hot_reload_manager_remove_watch_path(hot_reload_manager, tmp_path):
    """测试移除监控路径"""
    path = hot_reload_manager.watch_paths[0]

    # 移除路径
    hot_reload_manager.remove_watch_path(path)
    assert path not in hot_reload_manager.watch_paths


@pytest.mark.asyncio
async def test_hot_reload_integration(hot_reload_manager, sample_plugin_dir, plugin_manager):
    """测试热重载集成"""
    from lurkbot.plugins.schema_validator import ManifestValidator

    # 加载插件
    manifest, errors = ManifestValidator.validate_from_file(sample_plugin_dir / "manifest.json")
    assert manifest is not None, f"Manifest validation failed: {errors}"
    await plugin_manager.load_plugin(sample_plugin_dir, manifest)
    await plugin_manager.enable_plugin("test-plugin")

    # 启动热重载
    hot_reload_manager.start()

    try:
        # 修改插件代码
        main_py = sample_plugin_dir / "main.py"
        await asyncio.sleep(0.1)  # 确保文件系统事件可以被捕获
        main_py.write_text(
            '''"""Test plugin"""

async def execute(context):
    """Execute plugin"""
    return {"result": "v2"}
'''
        )

        # 等待热重载完成
        await asyncio.sleep(0.5)

        # 检查插件是否重载成功
        plugin = plugin_manager.loader.get("test-plugin")
        assert plugin is not None
        assert plugin.state in [PluginState.LOADED, PluginState.ENABLED]

    finally:
        # 停止热重载
        hot_reload_manager.stop()


# ============================================================================
# 全局单例测试
# ============================================================================


def test_get_hot_reload_manager_singleton(plugin_manager, tmp_path):
    """测试全局单例"""
    # 清除全局单例
    import lurkbot.plugins.hot_reload as hot_reload_module

    hot_reload_module._hot_reload_manager = None

    # 首次调用需要提供参数
    watch_paths = [tmp_path / "plugins"]
    manager1 = get_hot_reload_manager(plugin_manager, watch_paths)
    assert manager1 is not None

    # 第二次调用返回同一个实例
    manager2 = get_hot_reload_manager()
    assert manager1 is manager2

    # 清理
    hot_reload_module._hot_reload_manager = None


def test_get_hot_reload_manager_no_manager():
    """测试没有提供管理器时抛出异常"""
    # 清除全局单例
    import lurkbot.plugins.hot_reload as hot_reload_module

    hot_reload_module._hot_reload_manager = None

    # 首次调用没有提供管理器应该抛出异常
    with pytest.raises(ValueError, match="首次调用必须提供 manager 参数"):
        get_hot_reload_manager()

    # 清理
    hot_reload_module._hot_reload_manager = None
