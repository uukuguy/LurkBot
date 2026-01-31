"""插件系统异常类

定义插件系统的统一异常类层次结构，提供清晰的错误消息和上下文信息。
"""

from typing import Any


# ============================================================================
# 基础异常类
# ============================================================================


class PluginError(Exception):
    """插件系统基础异常

    所有插件相关异常的基类，提供统一的错误消息格式和上下文信息。
    """

    def __init__(
        self,
        message: str,
        plugin_name: str | None = None,
        context: dict[str, Any] | None = None,
    ):
        """初始化异常

        Args:
            message: 错误消息
            plugin_name: 插件名称（可选）
            context: 错误上下文信息（可选）
        """
        self.message = message
        self.plugin_name = plugin_name
        self.context = context or {}
        super().__init__(self.format_message())

    def format_message(self) -> str:
        """格式化错误消息

        Returns:
            格式化后的错误消息
        """
        msg = self.message
        if self.plugin_name:
            msg = f"[{self.plugin_name}] {msg}"
        if self.context:
            context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            msg += f" | Context: {context_str}"
        return msg


# ============================================================================
# 插件加载相关异常
# ============================================================================


class PluginLoadError(PluginError):
    """插件加载错误

    当插件加载失败时抛出，例如：
    - 插件文件不存在
    - 插件清单格式错误
    - 依赖项缺失
    - 模块导入失败
    """

    pass


class PluginManifestError(PluginLoadError):
    """插件清单错误

    当插件清单（manifest.json）格式错误或缺少必需字段时抛出。
    """

    pass


class PluginDependencyError(PluginLoadError):
    """插件依赖错误

    当插件依赖项缺失或版本不兼容时抛出。
    """

    def __init__(
        self,
        message: str,
        plugin_name: str | None = None,
        missing_dependencies: list[str] | None = None,
        context: dict[str, Any] | None = None,
    ):
        """初始化依赖错误

        Args:
            message: 错误消息
            plugin_name: 插件名称
            missing_dependencies: 缺失的依赖列表
            context: 错误上下文
        """
        self.missing_dependencies = missing_dependencies or []
        if missing_dependencies:
            context = context or {}
            context["missing_dependencies"] = ", ".join(missing_dependencies)
        super().__init__(message, plugin_name, context)


# ============================================================================
# 插件执行相关异常
# ============================================================================


class PluginExecutionError(PluginError):
    """插件执行错误

    当插件执行过程中发生错误时抛出，例如：
    - 插件方法调用失败
    - 执行超时
    - 资源限制超出
    """

    pass


class PluginTimeoutError(PluginExecutionError):
    """插件执行超时错误

    当插件执行时间超过配置的最大执行时间时抛出。
    """

    def __init__(
        self,
        message: str,
        plugin_name: str | None = None,
        timeout: float | None = None,
        context: dict[str, Any] | None = None,
    ):
        """初始化超时错误

        Args:
            message: 错误消息
            plugin_name: 插件名称
            timeout: 超时时间（秒）
            context: 错误上下文
        """
        self.timeout = timeout
        if timeout:
            context = context or {}
            context["timeout"] = f"{timeout}s"
        super().__init__(message, plugin_name, context)


class PluginResourceError(PluginExecutionError):
    """插件资源限制错误

    当插件使用的资源（内存、CPU等）超过限制时抛出。
    """

    def __init__(
        self,
        message: str,
        plugin_name: str | None = None,
        resource_type: str | None = None,
        limit: Any = None,
        actual: Any = None,
        context: dict[str, Any] | None = None,
    ):
        """初始化资源错误

        Args:
            message: 错误消息
            plugin_name: 插件名称
            resource_type: 资源类型（memory, cpu等）
            limit: 资源限制
            actual: 实际使用量
            context: 错误上下文
        """
        self.resource_type = resource_type
        self.limit = limit
        self.actual = actual
        if resource_type and limit and actual:
            context = context or {}
            context["resource"] = resource_type
            context["limit"] = str(limit)
            context["actual"] = str(actual)
        super().__init__(message, plugin_name, context)


# ============================================================================
# 插件权限相关异常
# ============================================================================


class PluginPermissionError(PluginError):
    """插件权限错误

    当插件尝试执行未授权的操作时抛出，例如：
    - 访问未授权的文件系统路径
    - 访问未授权的网络资源
    - 执行未授权的命令
    """

    def __init__(
        self,
        message: str,
        plugin_name: str | None = None,
        permission_type: str | None = None,
        resource: str | None = None,
        context: dict[str, Any] | None = None,
    ):
        """初始化权限错误

        Args:
            message: 错误消息
            plugin_name: 插件名称
            permission_type: 权限类型
            resource: 尝试访问的资源
            context: 错误上下文
        """
        self.permission_type = permission_type
        self.resource = resource
        if permission_type:
            context = context or {}
            context["permission"] = permission_type
            if resource:
                context["resource"] = resource
        super().__init__(message, plugin_name, context)


# ============================================================================
# 插件版本相关异常
# ============================================================================


class PluginVersionError(PluginError):
    """插件版本错误

    当插件版本相关操作失败时抛出，例如：
    - 版本格式错误
    - 版本不存在
    - 版本切换失败
    """

    def __init__(
        self,
        message: str,
        plugin_name: str | None = None,
        version: str | None = None,
        context: dict[str, Any] | None = None,
    ):
        """初始化版本错误

        Args:
            message: 错误消息
            plugin_name: 插件名称
            version: 版本号
            context: 错误上下文
        """
        self.version = version
        if version:
            context = context or {}
            context["version"] = version
        super().__init__(message, plugin_name, context)


class PluginVersionNotFoundError(PluginVersionError):
    """插件版本不存在错误

    当尝试访问不存在的插件版本时抛出。
    """

    pass


class PluginVersionConflictError(PluginVersionError):
    """插件版本冲突错误

    当插件版本之间存在冲突时抛出。
    """

    pass


# ============================================================================
# 插件注册相关异常
# ============================================================================


class PluginRegistryError(PluginError):
    """插件注册表错误

    当插件注册表操作失败时抛出，例如：
    - 插件已注册
    - 插件未注册
    - 注册表文件损坏
    """

    pass


class PluginAlreadyRegisteredError(PluginRegistryError):
    """插件已注册错误

    当尝试注册已存在的插件时抛出。
    """

    pass


class PluginNotFoundError(PluginRegistryError):
    """插件未找到错误

    当尝试访问不存在的插件时抛出。
    """

    pass


# ============================================================================
# 插件配置相关异常
# ============================================================================


class PluginConfigError(PluginError):
    """插件配置错误

    当插件配置无效或缺失时抛出。
    """

    def __init__(
        self,
        message: str,
        plugin_name: str | None = None,
        config_key: str | None = None,
        context: dict[str, Any] | None = None,
    ):
        """初始化配置错误

        Args:
            message: 错误消息
            plugin_name: 插件名称
            config_key: 配置键
            context: 错误上下文
        """
        self.config_key = config_key
        if config_key:
            context = context or {}
            context["config_key"] = config_key
        super().__init__(message, plugin_name, context)


# ============================================================================
# 插件沙箱相关异常
# ============================================================================


class PluginSandboxError(PluginError):
    """插件沙箱错误

    当插件沙箱操作失败时抛出，例如：
    - 沙箱初始化失败
    - 沙箱限制违规
    """

    pass


class PluginSandboxViolationError(PluginSandboxError):
    """插件沙箱违规错误

    当插件违反沙箱限制时抛出。
    """

    def __init__(
        self,
        message: str,
        plugin_name: str | None = None,
        violation_type: str | None = None,
        context: dict[str, Any] | None = None,
    ):
        """初始化沙箱违规错误

        Args:
            message: 错误消息
            plugin_name: 插件名称
            violation_type: 违规类型
            context: 错误上下文
        """
        self.violation_type = violation_type
        if violation_type:
            context = context or {}
            context["violation"] = violation_type
        super().__init__(message, plugin_name, context)


# ============================================================================
# 插件编排相关异常
# ============================================================================


class PluginOrchestrationError(PluginError):
    """插件编排错误

    当插件编排操作失败时抛出，例如：
    - 循环依赖
    - 依赖解析失败
    """

    pass


class PluginCyclicDependencyError(PluginOrchestrationError):
    """插件循环依赖错误

    当检测到插件之间存在循环依赖时抛出。
    """

    def __init__(
        self,
        message: str,
        plugin_name: str | None = None,
        cycle: list[str] | None = None,
        context: dict[str, Any] | None = None,
    ):
        """初始化循环依赖错误

        Args:
            message: 错误消息
            plugin_name: 插件名称
            cycle: 循环依赖链
            context: 错误上下文
        """
        self.cycle = cycle or []
        if cycle:
            context = context or {}
            context["cycle"] = " -> ".join(cycle)
        super().__init__(message, plugin_name, context)
