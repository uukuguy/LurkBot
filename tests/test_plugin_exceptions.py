"""插件异常类测试"""

import pytest

from lurkbot.plugins.exceptions import (
    PluginAlreadyRegisteredError,
    PluginConfigError,
    PluginCyclicDependencyError,
    PluginDependencyError,
    PluginError,
    PluginExecutionError,
    PluginLoadError,
    PluginManifestError,
    PluginNotFoundError,
    PluginOrchestrationError,
    PluginPermissionError,
    PluginRegistryError,
    PluginResourceError,
    PluginSandboxError,
    PluginSandboxViolationError,
    PluginTimeoutError,
    PluginVersionConflictError,
    PluginVersionError,
    PluginVersionNotFoundError,
)


# ============================================================================
# 基础异常测试
# ============================================================================


def test_plugin_error_basic():
    """测试基础插件错误"""
    error = PluginError("Test error")
    assert str(error) == "Test error"
    assert error.message == "Test error"
    assert error.plugin_name is None
    assert error.context == {}


def test_plugin_error_with_plugin_name():
    """测试带插件名称的错误"""
    error = PluginError("Test error", plugin_name="test-plugin")
    assert str(error) == "[test-plugin] Test error"
    assert error.plugin_name == "test-plugin"


def test_plugin_error_with_context():
    """测试带上下文的错误"""
    error = PluginError("Test error", context={"key": "value", "number": 42})
    assert "Context:" in str(error)
    assert "key=value" in str(error)
    assert "number=42" in str(error)


def test_plugin_error_full():
    """��试完整的错误信息"""
    error = PluginError(
        "Test error",
        plugin_name="test-plugin",
        context={"operation": "load", "file": "plugin.py"},
    )
    error_str = str(error)
    assert "[test-plugin]" in error_str
    assert "Test error" in error_str
    assert "Context:" in error_str
    assert "operation=load" in error_str
    assert "file=plugin.py" in error_str


# ============================================================================
# 加载相关异常测试
# ============================================================================


def test_plugin_load_error():
    """测试插件加载错误"""
    error = PluginLoadError("Failed to load plugin", plugin_name="test-plugin")
    assert isinstance(error, PluginError)
    assert "[test-plugin]" in str(error)


def test_plugin_manifest_error():
    """测试插件清单错误"""
    error = PluginManifestError("Invalid manifest", plugin_name="test-plugin")
    assert isinstance(error, PluginLoadError)
    assert isinstance(error, PluginError)


def test_plugin_dependency_error():
    """测试插件依赖错误"""
    error = PluginDependencyError(
        "Missing dependencies",
        plugin_name="test-plugin",
        missing_dependencies=["dep1", "dep2"],
    )
    assert isinstance(error, PluginLoadError)
    assert error.missing_dependencies == ["dep1", "dep2"]
    assert "missing_dependencies=dep1, dep2" in str(error)


# ============================================================================
# 执行相关异常测试
# ============================================================================


def test_plugin_execution_error():
    """测试插件执行错误"""
    error = PluginExecutionError("Execution failed", plugin_name="test-plugin")
    assert isinstance(error, PluginError)
    assert "[test-plugin]" in str(error)


def test_plugin_timeout_error():
    """测试插件超时错误"""
    error = PluginTimeoutError(
        "Execution timeout", plugin_name="test-plugin", timeout=30.0
    )
    assert isinstance(error, PluginExecutionError)
    assert error.timeout == 30.0
    assert "timeout=30.0s" in str(error)


def test_plugin_resource_error():
    """测试插件资源错误"""
    error = PluginResourceError(
        "Memory limit exceeded",
        plugin_name="test-plugin",
        resource_type="memory",
        limit="512MB",
        actual="600MB",
    )
    assert isinstance(error, PluginExecutionError)
    assert error.resource_type == "memory"
    assert error.limit == "512MB"
    assert error.actual == "600MB"
    assert "resource=memory" in str(error)
    assert "limit=512MB" in str(error)
    assert "actual=600MB" in str(error)


# ============================================================================
# 权限相关异常测试
# ============================================================================


def test_plugin_permission_error():
    """测试插件权限错误"""
    error = PluginPermissionError(
        "Permission denied",
        plugin_name="test-plugin",
        permission_type="filesystem.write",
        resource="/etc/passwd",
    )
    assert isinstance(error, PluginError)
    assert error.permission_type == "filesystem.write"
    assert error.resource == "/etc/passwd"
    assert "permission=filesystem.write" in str(error)
    assert "resource=/etc/passwd" in str(error)


# ============================================================================
# 版本相关异常测试
# ============================================================================


def test_plugin_version_error():
    """测试插件版本错误"""
    error = PluginVersionError(
        "Invalid version", plugin_name="test-plugin", version="1.0.0"
    )
    assert isinstance(error, PluginError)
    assert error.version == "1.0.0"
    assert "version=1.0.0" in str(error)


def test_plugin_version_not_found_error():
    """测试插件版本不存在错误"""
    error = PluginVersionNotFoundError(
        "Version not found", plugin_name="test-plugin", version="2.0.0"
    )
    assert isinstance(error, PluginVersionError)
    assert error.version == "2.0.0"


def test_plugin_version_conflict_error():
    """测试插件版本冲突错误"""
    error = PluginVersionConflictError(
        "Version conflict", plugin_name="test-plugin", version="1.0.0"
    )
    assert isinstance(error, PluginVersionError)


# ============================================================================
# 注册相关异常测试
# ============================================================================


def test_plugin_registry_error():
    """测试插件注册表错误"""
    error = PluginRegistryError("Registry error", plugin_name="test-plugin")
    assert isinstance(error, PluginError)


def test_plugin_already_registered_error():
    """测试插件已注册错误"""
    error = PluginAlreadyRegisteredError(
        "Plugin already registered", plugin_name="test-plugin"
    )
    assert isinstance(error, PluginRegistryError)


def test_plugin_not_found_error():
    """测试插件未找到错误"""
    error = PluginNotFoundError("Plugin not found", plugin_name="test-plugin")
    assert isinstance(error, PluginRegistryError)


# ============================================================================
# 配置相关异常测试
# ============================================================================


def test_plugin_config_error():
    """测试插件配置错误"""
    error = PluginConfigError(
        "Invalid config", plugin_name="test-plugin", config_key="api_key"
    )
    assert isinstance(error, PluginError)
    assert error.config_key == "api_key"
    assert "config_key=api_key" in str(error)


# ============================================================================
# 沙箱相关异常测试
# ============================================================================


def test_plugin_sandbox_error():
    """测试插件沙箱错误"""
    error = PluginSandboxError("Sandbox error", plugin_name="test-plugin")
    assert isinstance(error, PluginError)


def test_plugin_sandbox_violation_error():
    """测试插件沙箱违规错误"""
    error = PluginSandboxViolationError(
        "Sandbox violation", plugin_name="test-plugin", violation_type="filesystem"
    )
    assert isinstance(error, PluginSandboxError)
    assert error.violation_type == "filesystem"
    assert "violation=filesystem" in str(error)


# ============================================================================
# 编排相关异常��试
# ============================================================================


def test_plugin_orchestration_error():
    """测试插件编排错误"""
    error = PluginOrchestrationError("Orchestration error", plugin_name="test-plugin")
    assert isinstance(error, PluginError)


def test_plugin_cyclic_dependency_error():
    """测试插件循环依赖错误"""
    error = PluginCyclicDependencyError(
        "Cyclic dependency detected",
        plugin_name="plugin-a",
        cycle=["plugin-a", "plugin-b", "plugin-c", "plugin-a"],
    )
    assert isinstance(error, PluginOrchestrationError)
    assert error.cycle == ["plugin-a", "plugin-b", "plugin-c", "plugin-a"]
    assert "cycle=plugin-a -> plugin-b -> plugin-c -> plugin-a" in str(error)


# ============================================================================
# 异常继承层次测试
# ============================================================================


def test_exception_hierarchy():
    """测试异常继承层次"""
    # 所有异常都应该继承自 PluginError
    assert issubclass(PluginLoadError, PluginError)
    assert issubclass(PluginManifestError, PluginLoadError)
    assert issubclass(PluginDependencyError, PluginLoadError)
    assert issubclass(PluginExecutionError, PluginError)
    assert issubclass(PluginTimeoutError, PluginExecutionError)
    assert issubclass(PluginResourceError, PluginExecutionError)
    assert issubclass(PluginPermissionError, PluginError)
    assert issubclass(PluginVersionError, PluginError)
    assert issubclass(PluginVersionNotFoundError, PluginVersionError)
    assert issubclass(PluginVersionConflictError, PluginVersionError)
    assert issubclass(PluginRegistryError, PluginError)
    assert issubclass(PluginAlreadyRegisteredError, PluginRegistryError)
    assert issubclass(PluginNotFoundError, PluginRegistryError)
    assert issubclass(PluginConfigError, PluginError)
    assert issubclass(PluginSandboxError, PluginError)
    assert issubclass(PluginSandboxViolationError, PluginSandboxError)
    assert issubclass(PluginOrchestrationError, PluginError)
    assert issubclass(PluginCyclicDependencyError, PluginOrchestrationError)

    # 所有异常都应该继承自 Exception
    assert issubclass(PluginError, Exception)


def test_exception_catching():
    """测试异常捕获"""
    # 可以通过基类捕获派生类异常
    try:
        raise PluginManifestError("Test")
    except PluginLoadError:
        pass  # 应该能捕获

    try:
        raise PluginTimeoutError("Test")
    except PluginExecutionError:
        pass  # 应该能捕获

    try:
        raise PluginVersionNotFoundError("Test")
    except PluginVersionError:
        pass  # 应该能捕获

    # 可以通过 PluginError 捕获所有插件异常
    try:
        raise PluginCyclicDependencyError("Test")
    except PluginError:
        pass  # 应该能捕获
