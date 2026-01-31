"""插件系统性能基准测试

测试插件系统的性能指标，确保满足性能要求。

性能目标：
- 单个插件执行 < 100ms（不含插件内部逻辑）
- 并发 3 个插件 < 500ms
- 插件加载 < 50ms
- 插件发现 < 200ms（100 个插件）
- 内存占用合理（< 100MB for 10 plugins）
"""

import asyncio
import tempfile
import time
from pathlib import Path
from typing import Any

import pytest

from lurkbot.plugins.loader import PluginLoader, get_plugin_loader
from lurkbot.plugins.manager import PluginManager
from lurkbot.plugins.models import PluginExecutionContext


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def temp_plugin_dir() -> Path:
    """创建临时插件目录"""
    with tempfile.TemporaryDirectory() as tmpdir:
        plugin_dir = Path(tmpdir) / ".plugins"
        plugin_dir.mkdir(parents=True)
        yield plugin_dir


@pytest.fixture
def plugin_manager(temp_plugin_dir: Path) -> PluginManager:
    """创建插件管理器实例"""
    loader = get_plugin_loader()
    # 添加临时插件目录到搜索路径
    loader._search_paths = [str(temp_plugin_dir)]
    manager = PluginManager(
        loader=loader,
        enable_orchestration=True,
        enable_permissions=True,
        enable_versioning=True,
        enable_profiling=True,
    )
    return manager


@pytest.fixture
def fast_plugin_manifest() -> dict[str, Any]:
    """快速插件 manifest"""
    return {
        "name": "fast-plugin",
        "version": "1.0.0",
        "type": "tool",
        "language": "python",
        "entry": "main.py",
        "main_class": "FastPlugin",
        "description": "A fast plugin for performance testing",
        "author": "Test Author",
        "dependencies": {
            "python": [],
            "system": [],
            "env": [],
        },
        "permissions": {
            "filesystem": False,
            "network": False,
            "exec": False,
            "channels": [],
        },
        "tags": ["performance", "test"],
    }


@pytest.fixture
def fast_plugin_code() -> str:
    """快速插件代码（最小化执行时间）"""
    return '''"""Fast plugin for performance testing"""
import time

class FastPlugin:
    """A minimal plugin for performance testing"""

    def __init__(self, config=None):
        self.config = config or {}

    async def execute(self, context):
        """Execute with minimal overhead"""
        start_time = time.time()

        # Minimal work
        result = {"status": "ok"}

        execution_time = time.time() - start_time

        return {
            "success": True,
            "result": result,
            "error": None,
            "execution_time": execution_time,
            "metadata": {},
        }

    async def cleanup(self):
        pass
'''


def create_plugin(
    plugin_dir: Path,
    name: str,
    manifest: dict[str, Any],
    code: str,
) -> Path:
    """创建测试插件"""
    plugin_path = plugin_dir / name
    plugin_path.mkdir(parents=True, exist_ok=True)

    # 写入 manifest
    import json
    (plugin_path / "plugin.json").write_text(json.dumps(manifest, indent=2))

    # 写入代码
    (plugin_path / "main.py").write_text(code)

    return plugin_path


# ============================================================================
# Performance Test: 单个插件执行
# ============================================================================


@pytest.mark.asyncio
async def test_single_plugin_execution_performance(
    plugin_manager: PluginManager,
    temp_plugin_dir: Path,
    fast_plugin_manifest: dict[str, Any],
    fast_plugin_code: str,
):
    """测试单个插件执行性能

    目标：< 100ms（不含插件内部逻辑）
    """
    # 1. 创建插件
    plugin_name = "fast-plugin"
    create_plugin(temp_plugin_dir, plugin_name, fast_plugin_manifest, fast_plugin_code)

    # 2. 加载插件
    await plugin_manager.discover_plugins()
    await plugin_manager.load_plugin(plugin_name)

    # 3. 预热（第一次执行可能较慢）
    context = PluginExecutionContext(
        plugin_name=plugin_name,
        session_id="test-session",
        user_id="test-user",
        channel="test",
        parameters={},
    )
    await plugin_manager.execute_plugin(plugin_name, context)

    # 4. 性能测试（执行 10 次取平均）
    execution_times = []
    for _ in range(10):
        start_time = time.perf_counter()
        result = await plugin_manager.execute_plugin(plugin_name, context)
        end_time = time.perf_counter()

        assert result.success is True
        execution_times.append((end_time - start_time) * 1000)  # 转换为毫秒

    # 5. 计算统计数据
    avg_time = sum(execution_times) / len(execution_times)
    min_time = min(execution_times)
    max_time = max(execution_times)

    print(f"\n单个插件执行性能:")
    print(f"  平均: {avg_time:.2f}ms")
    print(f"  最小: {min_time:.2f}ms")
    print(f"  最大: {max_time:.2f}ms")

    # 6. 验证性能目标
    assert avg_time < 100, f"平均执行时间 {avg_time:.2f}ms 超过目标 100ms"


# ============================================================================
# Performance Test: 并发插件执行
# ============================================================================


@pytest.mark.asyncio
async def test_concurrent_plugin_execution_performance(
    plugin_manager: PluginManager,
    temp_plugin_dir: Path,
    fast_plugin_manifest: dict[str, Any],
    fast_plugin_code: str,
):
    """测试并发插件执行性能

    目标：3 个插件并发 < 500ms
    """
    # 1. 创建 3 个插件
    plugin_names = ["plugin-1", "plugin-2", "plugin-3"]
    for name in plugin_names:
        manifest = fast_plugin_manifest.copy()
        manifest["name"] = name
        create_plugin(temp_plugin_dir, name, manifest, fast_plugin_code)

    # 2. 加载所有插件
    await plugin_manager.discover_plugins()
    for name in plugin_names:
        await plugin_manager.load_plugin(name)

    # 3. 预热
    for name in plugin_names:
        context = PluginExecutionContext(
            plugin_name=name,
            session_id="test-session",
            user_id="test-user",
            channel="test",
            parameters={},
        )
        await plugin_manager.execute_plugin(name, context)

    # 4. 性能测试（执行 5 次取平均）
    execution_times = []
    for _ in range(5):
        start_time = time.perf_counter()

        # 并发执行所有插件
        tasks = []
        for name in plugin_names:
            context = PluginExecutionContext(
                plugin_name=name,
                session_id="test-session",
                user_id="test-user",
                channel="test",
                parameters={},
            )
            tasks.append(plugin_manager.execute_plugin(name, context))

        results = await asyncio.gather(*tasks)

        end_time = time.perf_counter()

        # 验证所有结果
        assert all(r.success for r in results)
        execution_times.append((end_time - start_time) * 1000)  # 转换为毫秒

    # 5. 计算统计数据
    avg_time = sum(execution_times) / len(execution_times)
    min_time = min(execution_times)
    max_time = max(execution_times)

    print(f"\n并发插件执行性能 (3 个插件):")
    print(f"  平均: {avg_time:.2f}ms")
    print(f"  最小: {min_time:.2f}ms")
    print(f"  最大: {max_time:.2f}ms")

    # 6. 验证性能目标
    assert avg_time < 500, f"平均执行时间 {avg_time:.2f}ms 超过目标 500ms"


# ============================================================================
# Performance Test: 插件加载
# ============================================================================


@pytest.mark.asyncio
async def test_plugin_loading_performance(
    plugin_manager: PluginManager,
    temp_plugin_dir: Path,
    fast_plugin_manifest: dict[str, Any],
    fast_plugin_code: str,
):
    """测试插件加载性能

    目标：< 50ms
    """
    # 1. 创建插件
    plugin_name = "load-test-plugin"
    manifest = fast_plugin_manifest.copy()
    manifest["name"] = plugin_name
    create_plugin(temp_plugin_dir, plugin_name, manifest, fast_plugin_code)

    # 2. 发现插件
    await plugin_manager.discover_plugins()

    # 3. 性能测试（加载 10 次）
    loading_times = []
    for _ in range(10):
        # 先卸载（如果已加载）
        try:
            await plugin_manager.unload_plugin(plugin_name)
        except:
            pass

        # 测量加载时间
        start_time = time.perf_counter()
        await plugin_manager.load_plugin(plugin_name)
        end_time = time.perf_counter()

        loading_times.append((end_time - start_time) * 1000)  # 转换为毫秒

    # 4. 计算统计数据
    avg_time = sum(loading_times) / len(loading_times)
    min_time = min(loading_times)
    max_time = max(loading_times)

    print(f"\n插件加载性能:")
    print(f"  平均: {avg_time:.2f}ms")
    print(f"  最小: {min_time:.2f}ms")
    print(f"  最大: {max_time:.2f}ms")

    # 5. 验证性能目标
    assert avg_time < 50, f"平均加载时间 {avg_time:.2f}ms 超过目标 50ms"


# ============================================================================
# Performance Test: 插件发现
# ============================================================================


@pytest.mark.asyncio
async def test_plugin_discovery_performance(
    plugin_manager: PluginManager,
    temp_plugin_dir: Path,
    fast_plugin_manifest: dict[str, Any],
    fast_plugin_code: str,
):
    """测试插件发现性能

    目标：100 个插件 < 200ms
    """
    # 1. 创建 100 个插件
    num_plugins = 100
    for i in range(num_plugins):
        plugin_name = f"plugin-{i:03d}"
        manifest = fast_plugin_manifest.copy()
        manifest["name"] = plugin_name
        create_plugin(temp_plugin_dir, plugin_name, manifest, fast_plugin_code)

    # 2. 性能测试（发现 5 次取平均）
    discovery_times = []
    for _ in range(5):
        # 清空已发现的插件
        plugin_manager.loader._discovered_plugins.clear()

        # 测量发现时间
        start_time = time.perf_counter()
        await plugin_manager.discover_plugins()
        end_time = time.perf_counter()

        discovery_times.append((end_time - start_time) * 1000)  # 转换为毫秒

        # 验证发现了所有插件
        plugins = plugin_manager.list_plugins()
        assert len(plugins) == num_plugins

    # 3. 计算统计数据
    avg_time = sum(discovery_times) / len(discovery_times)
    min_time = min(discovery_times)
    max_time = max(discovery_times)

    print(f"\n插件发现性能 ({num_plugins} 个插件):")
    print(f"  平均: {avg_time:.2f}ms")
    print(f"  最小: {min_time:.2f}ms")
    print(f"  最大: {max_time:.2f}ms")

    # 4. 验证性能目标
    assert avg_time < 200, f"平均发现时间 {avg_time:.2f}ms 超过目标 200ms"


# ============================================================================
# Performance Test: 内存占用
# ============================================================================


@pytest.mark.asyncio
async def test_plugin_memory_usage(
    plugin_manager: PluginManager,
    temp_plugin_dir: Path,
    fast_plugin_manifest: dict[str, Any],
    fast_plugin_code: str,
):
    """测试插件内存占用

    目标：10 个插件 < 100MB
    """
    try:
        import psutil
        import os
    except ImportError:
        pytest.skip("psutil not installed, skipping memory test")

    # 1. 获取初始内存
    process = psutil.Process(os.getpid())
    initial_memory = process.memory_info().rss / 1024 / 1024  # MB

    # 2. 创建并加载 10 个插件
    num_plugins = 10
    for i in range(num_plugins):
        plugin_name = f"memory-plugin-{i}"
        manifest = fast_plugin_manifest.copy()
        manifest["name"] = plugin_name
        create_plugin(temp_plugin_dir, plugin_name, manifest, fast_plugin_code)

    await plugin_manager.discover_plugins()

    for i in range(num_plugins):
        plugin_name = f"memory-plugin-{i}"
        await plugin_manager.load_plugin(plugin_name)

    # 3. 获取加载后内存
    final_memory = process.memory_info().rss / 1024 / 1024  # MB
    memory_increase = final_memory - initial_memory

    print(f"\n内存占用 ({num_plugins} 个插件):")
    print(f"  初始: {initial_memory:.2f}MB")
    print(f"  最终: {final_memory:.2f}MB")
    print(f"  增加: {memory_increase:.2f}MB")
    print(f"  平均每个插件: {memory_increase / num_plugins:.2f}MB")

    # 4. 验证内存目标
    assert memory_increase < 100, f"内存增加 {memory_increase:.2f}MB 超过目标 100MB"


# ============================================================================
# Performance Test: 高负载场景
# ============================================================================


@pytest.mark.asyncio
async def test_high_load_performance(
    plugin_manager: PluginManager,
    temp_plugin_dir: Path,
    fast_plugin_manifest: dict[str, Any],
    fast_plugin_code: str,
):
    """测试高负载场景性能

    场景：10 个插件，每个执行 100 次
    """
    # 1. 创建 10 个插件
    num_plugins = 10
    plugin_names = []
    for i in range(num_plugins):
        plugin_name = f"load-plugin-{i}"
        plugin_names.append(plugin_name)
        manifest = fast_plugin_manifest.copy()
        manifest["name"] = plugin_name
        create_plugin(temp_plugin_dir, plugin_name, manifest, fast_plugin_code)

    # 2. 加载所有插件
    await plugin_manager.discover_plugins()
    for name in plugin_names:
        await plugin_manager.load_plugin(name)

    # 3. 高负载测试
    num_executions = 100
    start_time = time.perf_counter()

    tasks = []
    for _ in range(num_executions):
        for name in plugin_names:
            context = PluginExecutionContext(
                plugin_name=name,
                session_id="test-session",
                user_id="test-user",
                channel="test",
                parameters={},
            )
            tasks.append(plugin_manager.execute_plugin(name, context))

    results = await asyncio.gather(*tasks)
    end_time = time.perf_counter()

    # 4. 计算统计数据
    total_time = (end_time - start_time) * 1000  # 毫秒
    total_executions = num_plugins * num_executions
    avg_time_per_execution = total_time / total_executions
    throughput = total_executions / (total_time / 1000)  # 每秒执行次数

    print(f"\n高负载性能 ({num_plugins} 个插件 × {num_executions} 次):")
    print(f"  总时间: {total_time:.2f}ms")
    print(f"  总执行次数: {total_executions}")
    print(f"  平均每次: {avg_time_per_execution:.2f}ms")
    print(f"  吞吐量: {throughput:.2f} 次/秒")

    # 5. 验证所有执行成功
    assert all(r.success for r in results)
    assert len(results) == total_executions


# ============================================================================
# Performance Test: 插件缓存效果
# ============================================================================


@pytest.mark.asyncio
async def test_plugin_cache_performance(
    plugin_manager: PluginManager,
    temp_plugin_dir: Path,
    fast_plugin_manifest: dict[str, Any],
    fast_plugin_code: str,
):
    """测试插件缓存对性能的影响"""
    # 1. 创建插件
    plugin_name = "cache-test-plugin"
    create_plugin(temp_plugin_dir, plugin_name, fast_plugin_manifest, fast_plugin_code)

    # 2. 测试无缓存性能
    plugin_manager._cache_enabled = False
    await plugin_manager.discover_plugins()
    await plugin_manager.load_plugin(plugin_name)

    context = PluginExecutionContext(
        plugin_name=plugin_name,
        session_id="test-session",
        user_id="test-user",
        channel="test",
        parameters={},
    )

    # 预热
    await plugin_manager.execute_plugin(plugin_name, context)

    # 测量无缓存时间
    no_cache_times = []
    for _ in range(10):
        start_time = time.perf_counter()
        await plugin_manager.execute_plugin(plugin_name, context)
        end_time = time.perf_counter()
        no_cache_times.append((end_time - start_time) * 1000)

    avg_no_cache = sum(no_cache_times) / len(no_cache_times)

    # 3. 测试有缓存性能
    plugin_manager._cache_enabled = True

    # 测量有缓存时间
    cache_times = []
    for _ in range(10):
        start_time = time.perf_counter()
        await plugin_manager.execute_plugin(plugin_name, context)
        end_time = time.perf_counter()
        cache_times.append((end_time - start_time) * 1000)

    avg_cache = sum(cache_times) / len(cache_times)

    # 4. 计算性能提升
    improvement = ((avg_no_cache - avg_cache) / avg_no_cache) * 100

    print(f"\n缓存性能对比:")
    print(f"  无缓存: {avg_no_cache:.2f}ms")
    print(f"  有缓存: {avg_cache:.2f}ms")
    print(f"  性能提升: {improvement:.1f}%")

    # 5. 验证缓存有效（应该有一定的性能提升）
    # 注意：提升幅度取决于具体实现
    assert avg_cache <= avg_no_cache, "缓存应该不会降低性能"


# ============================================================================
# Performance Test: 插件热重载性能
# ============================================================================


@pytest.mark.asyncio
async def test_plugin_reload_performance(
    plugin_manager: PluginManager,
    temp_plugin_dir: Path,
    fast_plugin_manifest: dict[str, Any],
    fast_plugin_code: str,
):
    """测试插件热重载性能

    目标：< 100ms
    """
    # 1. 创建插件
    plugin_name = "reload-test-plugin"
    plugin_path = create_plugin(
        temp_plugin_dir, plugin_name, fast_plugin_manifest, fast_plugin_code
    )

    # 2. 加载插件
    await plugin_manager.discover_plugins()
    await plugin_manager.load_plugin(plugin_name)

    # 3. 性能测试（重载 10 次）
    reload_times = []
    for i in range(10):
        # 修改插件代码（触发重载）
        modified_code = fast_plugin_code.replace(
            '"status": "ok"',
            f'"status": "ok", "reload_count": {i}'
        )
        (plugin_path / "main.py").write_text(modified_code)

        # 测量重载时间
        start_time = time.perf_counter()
        await plugin_manager.reload_plugin(plugin_name)
        end_time = time.perf_counter()

        reload_times.append((end_time - start_time) * 1000)  # 转换为毫秒

    # 4. 计算统计数据
    avg_time = sum(reload_times) / len(reload_times)
    min_time = min(reload_times)
    max_time = max(reload_times)

    print(f"\n插件热重载性能:")
    print(f"  平均: {avg_time:.2f}ms")
    print(f"  最小: {min_time:.2f}ms")
    print(f"  最大: {max_time:.2f}ms")

    # 5. 验证性能目标
    assert avg_time < 100, f"平均重载时间 {avg_time:.2f}ms 超过目标 100ms"
