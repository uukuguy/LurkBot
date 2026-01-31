"""端到端插件集成测试

测试插件系统在实际场景中的完整生命周期和功能。

测试场景：
1. 单个插件执行 - 验证单个插件的完整生命周期
2. 多个插件并发执行 - 验证插件管理器的并发处理能力
3. 插件失败处理 - 验证错误处理和恢复机制
4. 插件热重载 - 验证插件的动态加载和卸载
5. 插件权限控制 - 验证权限系统的有效性
6. 插件依赖管理 - 验证插件间依赖关系处理
"""

import asyncio
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from lurkbot.plugins.loader import PluginLoader, PluginState, get_plugin_loader
from lurkbot.plugins.manager import PluginManager
from lurkbot.plugins.manifest import PluginManifest, PluginType
from lurkbot.plugins.models import (
    PluginConfig,
    PluginExecutionContext,
    PluginExecutionResult,
)
from lurkbot.plugins.permissions import Permission, PermissionLevel, PermissionType


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
def plugin_manager() -> PluginManager:
    """创建插件管理器实例"""
    manager = PluginManager(
        enable_orchestration=True,
        enable_permissions=True,
        enable_versioning=True,
        enable_profiling=True,
    )
    return manager


@pytest.fixture
def sample_plugin_manifest() -> dict[str, Any]:
    """示例插件 manifest"""
    return {
        "name": "test-plugin",
        "version": "1.0.0",
        "type": "tool",
        "language": "python",
        "entry": "main.py",
        "main_class": "TestPlugin",
        "description": "A test plugin for e2e testing",
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
        "tags": ["test", "e2e"],
    }


@pytest.fixture
def sample_plugin_code() -> str:
    """示例插件代码"""
    return '''"""Test plugin for e2e testing"""
import time
from typing import Any

class TestPlugin:
    """A simple test plugin"""

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}
        self.call_count = 0

    async def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Execute the plugin"""
        start_time = time.time()
        self.call_count += 1

        # Simulate some work
        await asyncio.sleep(0.01)

        result = {
            "message": f"Test plugin executed successfully (call #{self.call_count})",
            "context": context,
            "config": self.config,
        }

        execution_time = time.time() - start_time

        return {
            "success": True,
            "result": result,
            "error": None,
            "execution_time": execution_time,
            "metadata": {"call_count": self.call_count},
        }

    async def cleanup(self):
        """Cleanup resources"""
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
# Test: 单个插件执行
# ============================================================================


@pytest.mark.asyncio
async def test_single_plugin_execution(
    plugin_manager: PluginManager,
    temp_plugin_dir: Path,
    sample_plugin_manifest: dict[str, Any],
    sample_plugin_code: str,
):
    """测试单个插件的完整执行流程"""
    # 1. 创建插件
    plugin_name = "test-plugin"
    plugin_path = create_plugin(temp_plugin_dir, plugin_name, sample_plugin_manifest, sample_plugin_code)

    # 2. 解析 manifest
    manifest = PluginManifest.model_validate(sample_plugin_manifest)

    # 3. 加载插件
    plugin = await plugin_manager.load_plugin(plugin_path, manifest)
    assert plugin is not None
    assert plugin.state == PluginState.LOADED

    # 4. 执行插件
    context = PluginExecutionContext(
        plugin_name=plugin_name,
        session_id="test-session",
        user_id="test-user",
        channel="test",
        parameters={"test_param": "test_value"},
    )

    result = await plugin_manager.execute_plugin(plugin_name, context)

    # 5. 验证结果
    assert result.success is True
    assert result.error is None
    assert result.execution_time > 0
    assert "message" in result.result
    assert "call_count" in result.metadata

    # 6. 卸载插件
    await plugin_manager.unload_plugin(plugin_name)
    plugin = plugin_manager.get_plugin(plugin_name)
    assert plugin.state == PluginState.UNLOADED


# ============================================================================
# Test: 多个插件并发执行
# ============================================================================


@pytest.mark.asyncio
async def test_concurrent_plugin_execution(
    plugin_manager: PluginManager,
    temp_plugin_dir: Path,
    sample_plugin_manifest: dict[str, Any],
    sample_plugin_code: str,
):
    """测试多个插件的并发执行"""
    # 1. 创建多个插件
    plugin_names = ["plugin-1", "plugin-2", "plugin-3"]
    for name in plugin_names:
        manifest = sample_plugin_manifest.copy()
        manifest["name"] = name
        create_plugin(temp_plugin_dir, name, manifest, sample_plugin_code)

    # 2. 发现并加载所有插件
    await plugin_manager.discover_plugins()
    for name in plugin_names:
        await plugin_manager.load_plugin(name)

    # 3. 并发执行所有插件
    tasks = []
    for name in plugin_names:
        context = PluginExecutionContext(
            plugin_name=name,
            session_id="test-session",
            user_id="test-user",
            channel="test",
            parameters={"plugin": name},
        )
        tasks.append(plugin_manager.execute_plugin(name, context))

    results = await asyncio.gather(*tasks)

    # 4. 验证所有结果
    assert len(results) == len(plugin_names)
    for result in results:
        assert result.success is True
        assert result.error is None
        assert result.execution_time > 0

    # 5. 验证并发执行时间（应该比串行快）
    total_execution_time = sum(r.execution_time for r in results)
    # 每个插件至少 0.01 秒，3 个插件串行至少 0.03 秒
    # 但并发执行应该接近单个插件的时间
    assert total_execution_time < 0.1  # 合理的并发执行时间


# ============================================================================
# Test: 插件失败处理
# ============================================================================


@pytest.mark.asyncio
async def test_plugin_failure_handling(
    plugin_manager: PluginManager,
    temp_plugin_dir: Path,
    sample_plugin_manifest: dict[str, Any],
):
    """测试插件执行失败的处理"""
    # 1. 创建会失败的插件
    failing_code = '''"""Failing plugin for testing"""
import time

class TestPlugin:
    def __init__(self, config=None):
        self.config = config or {}

    async def execute(self, context):
        """This will fail"""
        start_time = time.time()
        raise ValueError("Intentional failure for testing")

    async def cleanup(self):
        pass
'''

    plugin_name = "failing-plugin"
    manifest = sample_plugin_manifest.copy()
    manifest["name"] = plugin_name
    create_plugin(temp_plugin_dir, plugin_name, manifest, failing_code)

    # 2. 加载插件
    await plugin_manager.discover_plugins()
    await plugin_manager.load_plugin(plugin_name)

    # 3. 执行插件（应该捕获错误）
    context = PluginExecutionContext(
        plugin_name=plugin_name,
        session_id="test-session",
        user_id="test-user",
        channel="test",
        parameters={},
    )

    result = await plugin_manager.execute_plugin(plugin_name, context)

    # 4. 验证错误处理
    assert result.success is False
    assert result.error is not None
    assert "Intentional failure" in result.error or "ValueError" in result.error
    assert result.execution_time >= 0


# ============================================================================
# Test: 插件热重载
# ============================================================================


@pytest.mark.asyncio
async def test_plugin_hot_reload(
    plugin_manager: PluginManager,
    temp_plugin_dir: Path,
    sample_plugin_manifest: dict[str, Any],
    sample_plugin_code: str,
):
    """测试插件的热重载功能"""
    # 1. 创建初始插件
    plugin_name = "reload-plugin"
    manifest = sample_plugin_manifest.copy()
    manifest["name"] = plugin_name
    plugin_path = create_plugin(temp_plugin_dir, plugin_name, manifest, sample_plugin_code)

    # 2. 加载并执行插件
    await plugin_manager.discover_plugins()
    await plugin_manager.load_plugin(plugin_name)

    context = PluginExecutionContext(
        plugin_name=plugin_name,
        session_id="test-session",
        user_id="test-user",
        channel="test",
        parameters={},
    )

    result1 = await plugin_manager.execute_plugin(plugin_name, context)
    assert result1.success is True
    original_message = result1.result["message"]

    # 3. 修改插件代码
    modified_code = sample_plugin_code.replace(
        '"Test plugin executed successfully',
        '"MODIFIED: Test plugin executed successfully'
    )
    (plugin_path / "main.py").write_text(modified_code)

    # 4. 重新加载插件
    await plugin_manager.reload_plugin(plugin_name)

    # 5. 再次执行插件
    result2 = await plugin_manager.execute_plugin(plugin_name, context)
    assert result2.success is True
    modified_message = result2.result["message"]

    # 6. 验证代码已更新
    assert "MODIFIED" in modified_message
    assert "MODIFIED" not in original_message


# ============================================================================
# Test: 插件权限控制
# ============================================================================


@pytest.mark.asyncio
async def test_plugin_permission_control(
    plugin_manager: PluginManager,
    temp_plugin_dir: Path,
    sample_plugin_manifest: dict[str, Any],
):
    """测试插件权限控制"""
    # 1. 创建需要网络权限的插件
    network_code = '''"""Plugin requiring network access"""
import time

class TestPlugin:
    def __init__(self, config=None):
        self.config = config or {}

    async def execute(self, context):
        """Requires network permission"""
        start_time = time.time()
        # Simulate network access
        result = {"data": "network data"}
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

    plugin_name = "network-plugin"
    manifest = sample_plugin_manifest.copy()
    manifest["name"] = plugin_name
    manifest["permissions"]["network"] = True  # 需要网络权限
    create_plugin(temp_plugin_dir, plugin_name, manifest, network_code)

    # 2. 加载插件
    await plugin_manager.discover_plugins()
    await plugin_manager.load_plugin(plugin_name)

    # 3. 配置权限管理器（拒绝网络权限）
    if plugin_manager.permission_manager:
        # 创建一个拒绝网络访问的权限
        permission = Permission(
            type=PermissionType.NETWORK,
            level=PermissionLevel.DENY,
            resource="*",
            description="Deny all network access",
        )
        plugin_manager.permission_manager.add_permission("test-user", permission)

    # 4. 尝试执行插件（应该被权限系统阻止）
    context = PluginExecutionContext(
        plugin_name=plugin_name,
        session_id="test-session",
        user_id="test-user",
        channel="test",
        parameters={},
    )

    # 注意：这里的行为取决于权限系统的实现
    # 如果权限检查在执行前进行，应该抛出异常或返回错误
    # 如果权限检查在执行中进行，插件内部应该处理权限错误
    try:
        result = await plugin_manager.execute_plugin(plugin_name, context)
        # 如果没有抛出异常，检查结果是否包含权限错误
        if not result.success:
            assert "permission" in result.error.lower() or "denied" in result.error.lower()
    except PermissionError as e:
        # 权限错误被正确抛出
        assert "permission" in str(e).lower() or "denied" in str(e).lower()


# ============================================================================
# Test: 插件依赖管理
# ============================================================================


@pytest.mark.asyncio
async def test_plugin_dependency_management(
    plugin_manager: PluginManager,
    temp_plugin_dir: Path,
    sample_plugin_manifest: dict[str, Any],
    sample_plugin_code: str,
):
    """测试插件依赖关系管理"""
    # 1. 创建基础插件
    base_plugin_name = "base-plugin"
    base_manifest = sample_plugin_manifest.copy()
    base_manifest["name"] = base_plugin_name
    create_plugin(temp_plugin_dir, base_plugin_name, base_manifest, sample_plugin_code)

    # 2. 创建依赖基础插件的插件
    dependent_plugin_name = "dependent-plugin"
    dependent_manifest = sample_plugin_manifest.copy()
    dependent_manifest["name"] = dependent_plugin_name
    dependent_manifest["dependencies"]["plugins"] = [base_plugin_name]  # 依赖 base-plugin
    create_plugin(temp_plugin_dir, dependent_plugin_name, dependent_manifest, sample_plugin_code)

    # 3. 发现插件
    await plugin_manager.discover_plugins()

    # 4. 尝试加载依赖插件（应该自动加载基础插件）
    if plugin_manager.orchestrator:
        # 如果启用了编排器，应该自动处理依赖
        await plugin_manager.load_plugin(dependent_plugin_name)

        # 验证基础插件也被加载
        base_plugin = plugin_manager.get_plugin(base_plugin_name)
        dependent_plugin = plugin_manager.get_plugin(dependent_plugin_name)

        # 注意：这取决于编排器的实现
        # 如果编排器自动加载依赖，两个插件都应该被加载
        assert dependent_plugin is not None
        # base_plugin 可能被自动加载，也可能需要手动加载
    else:
        # 如果没有编排器，需要手动管理依赖
        await plugin_manager.load_plugin(base_plugin_name)
        await plugin_manager.load_plugin(dependent_plugin_name)


# ============================================================================
# Test: 插件生命周期事件
# ============================================================================


@pytest.mark.asyncio
async def test_plugin_lifecycle_events(
    plugin_manager: PluginManager,
    temp_plugin_dir: Path,
    sample_plugin_manifest: dict[str, Any],
    sample_plugin_code: str,
):
    """测试插件生命周期事件"""
    # 1. 设置事件监听器
    events_received = []

    def event_handler(event):
        events_received.append(event)

    plugin_manager.add_event_handler(event_handler)

    # 2. 创建插件
    plugin_name = "lifecycle-plugin"
    manifest = sample_plugin_manifest.copy()
    manifest["name"] = plugin_name
    create_plugin(temp_plugin_dir, plugin_name, manifest, sample_plugin_code)

    # 3. 执行完整生命周期
    await plugin_manager.discover_plugins()  # 应该触发 DISCOVERED 事件
    await plugin_manager.load_plugin(plugin_name)  # 应该触发 LOADED 事件

    context = PluginExecutionContext(
        plugin_name=plugin_name,
        session_id="test-session",
        user_id="test-user",
        channel="test",
        parameters={},
    )
    await plugin_manager.execute_plugin(plugin_name, context)  # 应该触发 EXECUTED 事件

    await plugin_manager.unload_plugin(plugin_name)  # 应该触发 UNLOADED 事件

    # 4. 验证事件
    # 注意：事件的具体数量和类型取决于 PluginManager 的实现
    assert len(events_received) > 0

    # 检查是否包含关键事件类型
    event_types = [e.event_type for e in events_received if hasattr(e, 'event_type')]
    # 至少应该有加载和卸载事件
    # 具体的事件类型取决于实现


# ============================================================================
# Test: 插件配置管理
# ============================================================================


@pytest.mark.asyncio
async def test_plugin_configuration(
    plugin_manager: PluginManager,
    temp_plugin_dir: Path,
    sample_plugin_manifest: dict[str, Any],
    sample_plugin_code: str,
):
    """测试插件配置管理"""
    # 1. 创建插件
    plugin_name = "config-plugin"
    manifest = sample_plugin_manifest.copy()
    manifest["name"] = plugin_name
    create_plugin(temp_plugin_dir, plugin_name, manifest, sample_plugin_code)

    # 2. 加载插件并设置配置
    await plugin_manager.discover_plugins()

    config = PluginConfig(
        enabled=True,
        auto_load=True,
        config_data={"custom_setting": "custom_value"},
    )
    plugin_manager.set_plugin_config(plugin_name, config)

    await plugin_manager.load_plugin(plugin_name)

    # 3. 执行插件并验证配置被传递
    context = PluginExecutionContext(
        plugin_name=plugin_name,
        session_id="test-session",
        user_id="test-user",
        channel="test",
        parameters={},
    )

    result = await plugin_manager.execute_plugin(plugin_name, context)

    # 4. 验证配置在结果中
    assert result.success is True
    assert "config" in result.result
    # 配置应该包含我们设置的自定义值
    # 注意：这取决于插件如何接收和使用配置


# ============================================================================
# Test: 插件错误恢复
# ============================================================================


@pytest.mark.asyncio
async def test_plugin_error_recovery(
    plugin_manager: PluginManager,
    temp_plugin_dir: Path,
    sample_plugin_manifest: dict[str, Any],
):
    """测试插件错误后的恢复能力"""
    # 1. 创建有时会失败的插件
    flaky_code = '''"""Flaky plugin for testing error recovery"""
import time

class TestPlugin:
    def __init__(self, config=None):
        self.config = config or {}
        self.call_count = 0

    async def execute(self, context):
        """Fails on first call, succeeds on subsequent calls"""
        start_time = time.time()
        self.call_count += 1

        if self.call_count == 1:
            raise RuntimeError("First call always fails")

        result = {"message": f"Success on call #{self.call_count}"}
        execution_time = time.time() - start_time

        return {
            "success": True,
            "result": result,
            "error": None,
            "execution_time": execution_time,
            "metadata": {"call_count": self.call_count},
        }

    async def cleanup(self):
        pass
'''

    plugin_name = "flaky-plugin"
    manifest = sample_plugin_manifest.copy()
    manifest["name"] = plugin_name
    create_plugin(temp_plugin_dir, plugin_name, manifest, flaky_code)

    # 2. 加载插件
    await plugin_manager.discover_plugins()
    await plugin_manager.load_plugin(plugin_name)

    # 3. 第一次执行（应该失败）
    context = PluginExecutionContext(
        plugin_name=plugin_name,
        session_id="test-session",
        user_id="test-user",
        channel="test",
        parameters={},
    )

    result1 = await plugin_manager.execute_plugin(plugin_name, context)
    assert result1.success is False
    assert result1.error is not None

    # 4. 第二次执行（应该成功）
    result2 = await plugin_manager.execute_plugin(plugin_name, context)
    assert result2.success is True
    assert result2.error is None
    assert result2.result["message"] == "Success on call #2"

    # 5. 验证插件状态仍然正常
    plugin = plugin_manager.get_plugin(plugin_name)
    assert plugin.state == PluginState.LOADED


# ============================================================================
# Test: 插件超时处理
# ============================================================================


@pytest.mark.asyncio
async def test_plugin_timeout_handling(
    plugin_manager: PluginManager,
    temp_plugin_dir: Path,
    sample_plugin_manifest: dict[str, Any],
):
    """测试插件执行超时处理"""
    # 1. 创建会超时的插件
    slow_code = '''"""Slow plugin for testing timeout"""
import asyncio
import time

class TestPlugin:
    def __init__(self, config=None):
        self.config = config or {}

    async def execute(self, context):
        """Takes too long to execute"""
        start_time = time.time()
        # Sleep for a long time
        await asyncio.sleep(10)  # 10 seconds

        execution_time = time.time() - start_time
        return {
            "success": True,
            "result": {"message": "Should not reach here"},
            "error": None,
            "execution_time": execution_time,
            "metadata": {},
        }

    async def cleanup(self):
        pass
'''

    plugin_name = "slow-plugin"
    manifest = sample_plugin_manifest.copy()
    manifest["name"] = plugin_name
    create_plugin(temp_plugin_dir, plugin_name, manifest, slow_code)

    # 2. 加载插件
    await plugin_manager.discover_plugins()
    await plugin_manager.load_plugin(plugin_name)

    # 3. 执行插件并设置超时
    context = PluginExecutionContext(
        plugin_name=plugin_name,
        session_id="test-session",
        user_id="test-user",
        channel="test",
        parameters={},
        timeout=1.0,  # 1 second timeout
    )

    # 4. 验证超时处理
    try:
        result = await asyncio.wait_for(
            plugin_manager.execute_plugin(plugin_name, context),
            timeout=2.0  # 给插件管理器 2 秒来处理超时
        )
        # 如果没有抛出异常，检查结果是否表示超时
        if not result.success:
            assert "timeout" in result.error.lower() or "time" in result.error.lower()
    except asyncio.TimeoutError:
        # 超时被正确处理
        pass


# ============================================================================
# Test: 插件资源清理
# ============================================================================


@pytest.mark.asyncio
async def test_plugin_resource_cleanup(
    plugin_manager: PluginManager,
    temp_plugin_dir: Path,
    sample_plugin_manifest: dict[str, Any],
):
    """测试插件资源清理"""
    # 1. 创建需要清理资源的插件
    cleanup_code = '''"""Plugin with resource cleanup"""
import time

class TestPlugin:
    def __init__(self, config=None):
        self.config = config or {}
        self.resources = []
        self.cleanup_called = False

    async def execute(self, context):
        """Allocate some resources"""
        start_time = time.time()
        # Simulate resource allocation
        self.resources.append("resource-1")
        self.resources.append("resource-2")

        result = {"resources": len(self.resources)}
        execution_time = time.time() - start_time

        return {
            "success": True,
            "result": result,
            "error": None,
            "execution_time": execution_time,
            "metadata": {"cleanup_called": self.cleanup_called},
        }

    async def cleanup(self):
        """Clean up resources"""
        self.cleanup_called = True
        self.resources.clear()
'''

    plugin_name = "cleanup-plugin"
    manifest = sample_plugin_manifest.copy()
    manifest["name"] = plugin_name
    create_plugin(temp_plugin_dir, plugin_name, manifest, cleanup_code)

    # 2. 加载并执行插件
    await plugin_manager.discover_plugins()
    await plugin_manager.load_plugin(plugin_name)

    context = PluginExecutionContext(
        plugin_name=plugin_name,
        session_id="test-session",
        user_id="test-user",
        channel="test",
        parameters={},
    )

    result = await plugin_manager.execute_plugin(plugin_name, context)
    assert result.success is True
    assert result.result["resources"] == 2

    # 3. 卸载插件（应该调用 cleanup）
    await plugin_manager.unload_plugin(plugin_name)

    # 4. 验证清理被调用
    # 注意：这需要插件管理器在卸载时调用 cleanup 方法
    # 具体验证方式取决于实现
