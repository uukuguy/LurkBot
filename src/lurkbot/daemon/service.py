"""
Daemon Service - 统一服务接口

对标: MoltBot src/daemon/service.ts

提供跨平台的守护进程服务抽象接口。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal
import platform


@dataclass
class ServiceRuntime:
    """
    服务运行时状态

    对标: MoltBot ServiceRuntime
    """

    status: Literal["running", "stopped", "unknown"]
    """服务运行状态"""

    state: str | None = None
    """平台特定的状态字符串"""

    sub_state: str | None = None
    """平台特定的子状态字符串"""

    pid: int | None = None
    """进程 PID"""

    last_exit_status: int | None = None
    """最后退出状态码"""

    last_exit_reason: str | None = None
    """最后退出原因"""


@dataclass
class ServiceInstallArgs:
    """
    服务安装参数

    对标: MoltBot ServiceInstallArgs
    """

    port: int = 18789
    """Gateway 监听端口"""

    bind: str = "loopback"
    """绑定地址类型: loopback / lan"""

    profile: str | None = None
    """Profile 名称（用于多实例）"""

    workspace: str | None = None
    """工作区路径"""


class GatewayService(ABC):
    """
    守护进程服务抽象接口

    对标: MoltBot GatewayService

    支持平台:
    - macOS: launchd (LaunchAgent)
    - Linux: systemd (user service)
    - Windows: schtasks (计划任务)
    """

    @property
    @abstractmethod
    def label(self) -> str:
        """
        服务标签/名称

        不同平台的标签格式:
        - macOS: bot.lurk.gateway (reverse domain notation)
        - Linux: lurkbot-gateway (systemd unit name)
        - Windows: lurkbot-gateway (task name)
        """
        pass

    @abstractmethod
    async def install(self, args: ServiceInstallArgs) -> None:
        """
        安装服务

        Args:
            args: 安装参数

        Raises:
            RuntimeError: 安装失败
        """
        pass

    @abstractmethod
    async def uninstall(self) -> None:
        """
        卸载服务

        Raises:
            RuntimeError: 卸载失败
        """
        pass

    @abstractmethod
    async def start(self) -> None:
        """
        启动服务

        Raises:
            RuntimeError: 启动失败
        """
        pass

    @abstractmethod
    async def stop(self) -> None:
        """
        停止服务

        Raises:
            RuntimeError: 停止失败
        """
        pass

    @abstractmethod
    async def restart(self) -> None:
        """
        重启服务

        Raises:
            RuntimeError: 重启失败
        """
        pass

    @abstractmethod
    async def is_loaded(self) -> bool:
        """
        检查服务是否已加载

        Returns:
            True 如果服务已安装并加载
        """
        pass

    @abstractmethod
    async def get_runtime(self) -> ServiceRuntime:
        """
        获取运行时状态

        Returns:
            ServiceRuntime: 当前运行时状态
        """
        pass


def resolve_gateway_service(profile: str | None = None) -> GatewayService:
    """
    根据平台选择服务实现

    对标: MoltBot resolveGatewayService()

    Args:
        profile: 可选的 Profile 名称（用于多实例）

    Returns:
        GatewayService: 平台特定的服务实现

    Raises:
        RuntimeError: 不支持的平台
    """
    system = platform.system()

    if system == "Darwin":
        from .launchd import LaunchdService

        return LaunchdService(profile=profile)

    elif system == "Linux":
        from .systemd import SystemdService

        return SystemdService(profile=profile)

    elif system == "Windows":
        from .schtasks import SchtasksService

        return SchtasksService(profile=profile)

    else:
        raise RuntimeError(f"Unsupported platform: {system}")


__all__ = [
    "ServiceRuntime",
    "ServiceInstallArgs",
    "GatewayService",
    "resolve_gateway_service",
]
