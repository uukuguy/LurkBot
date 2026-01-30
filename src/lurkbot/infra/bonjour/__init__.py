"""Bonjour/mDNS Service Discovery.

基于 zeroconf 的本地网络服务发现。

对标 MoltBot `src/infra/bonjour.ts`
"""

import asyncio
import socket
import threading
from datetime import datetime
from typing import Callable

from .types import BonjourBrowseResult, BonjourConfig, BonjourService

__all__ = [
    "BonjourService",
    "BonjourBrowseResult",
    "BonjourConfig",
    "BonjourBrowser",
    "BonjourPublisher",
    "browse_services",
    "publish_service",
    "is_bonjour_available",
]

# 尝试导入 zeroconf
try:
    from zeroconf import ServiceBrowser, ServiceInfo, ServiceStateChange, Zeroconf

    ZEROCONF_AVAILABLE = True
except ImportError:
    ZEROCONF_AVAILABLE = False
    Zeroconf = None
    ServiceBrowser = None
    ServiceInfo = None
    ServiceStateChange = None


def is_bonjour_available() -> bool:
    """检查 Bonjour/zeroconf 是否可用。"""
    return ZEROCONF_AVAILABLE


class BonjourBrowser:
    """
    Bonjour 服务浏览器。

    发现本地网络上的服务。

    对标 MoltBot bonjour.ts 的 browse 功能
    """

    def __init__(self, config: BonjourConfig | None = None) -> None:
        self._config = config or BonjourConfig()
        self._zeroconf: Zeroconf | None = None
        self._browser: ServiceBrowser | None = None
        self._services: dict[str, BonjourService] = {}
        self._callbacks: list[Callable[[BonjourBrowseResult], None]] = []
        self._lock = threading.Lock()

    def _on_service_state_change(
        self,
        zeroconf: Zeroconf,
        service_type: str,
        name: str,
        state_change: ServiceStateChange,
    ) -> None:
        """服务状态变化回调。"""
        if state_change == ServiceStateChange.Added:
            # 解析服务信息
            info = zeroconf.get_service_info(service_type, name)
            if info:
                service = self._parse_service_info(info)
                with self._lock:
                    self._services[name] = service

                # 通知回调
                result = BonjourBrowseResult(service=service, event="added")
                for callback in self._callbacks:
                    try:
                        callback(result)
                    except Exception:
                        pass

        elif state_change == ServiceStateChange.Removed:
            with self._lock:
                service = self._services.pop(name, None)

            if service:
                result = BonjourBrowseResult(service=service, event="removed")
                for callback in self._callbacks:
                    try:
                        callback(result)
                    except Exception:
                        pass

        elif state_change == ServiceStateChange.Updated:
            info = zeroconf.get_service_info(service_type, name)
            if info:
                service = self._parse_service_info(info)
                with self._lock:
                    self._services[name] = service

                result = BonjourBrowseResult(service=service, event="updated")
                for callback in self._callbacks:
                    try:
                        callback(result)
                    except Exception:
                        pass

    def _parse_service_info(self, info: ServiceInfo) -> BonjourService:
        """解析 ServiceInfo 为 BonjourService。"""
        # 解析地址
        addresses = []
        if hasattr(info, "parsed_addresses"):
            addresses = list(info.parsed_addresses())
        elif hasattr(info, "addresses"):
            for addr in info.addresses:
                try:
                    addresses.append(socket.inet_ntoa(addr))
                except Exception:
                    pass

        # 解析 TXT 记录
        txt = {}
        if info.properties:
            for key, value in info.properties.items():
                if isinstance(key, bytes):
                    key = key.decode("utf-8", errors="replace")
                if isinstance(value, bytes):
                    value = value.decode("utf-8", errors="replace")
                txt[key] = value

        return BonjourService(
            name=info.name,
            type=info.type,
            domain="local",
            host=info.server,
            port=info.port,
            addresses=addresses,
            txt=txt,
            discovered_at=datetime.now(),
            last_seen=datetime.now(),
        )

    def start(self) -> bool:
        """
        开始浏览服务。

        Returns:
            是否成功启动
        """
        if not ZEROCONF_AVAILABLE:
            return False

        if self._zeroconf:
            return True

        try:
            self._zeroconf = Zeroconf()
            self._browser = ServiceBrowser(
                self._zeroconf,
                self._config.service_type + ".local.",
                handlers=[self._on_service_state_change],
            )
            return True
        except Exception:
            self.stop()
            return False

    def stop(self) -> None:
        """停止浏览服务。"""
        if self._browser:
            self._browser.cancel()
            self._browser = None

        if self._zeroconf:
            self._zeroconf.close()
            self._zeroconf = None

        with self._lock:
            self._services.clear()

    def list_services(self) -> list[BonjourService]:
        """
        列出已发现的服务。

        Returns:
            服务列表
        """
        with self._lock:
            return list(self._services.values())

    def on_service_change(
        self,
        callback: Callable[[BonjourBrowseResult], None],
    ) -> Callable[[], None]:
        """
        注册服务变化回调。

        Args:
            callback: 回调函数

        Returns:
            取消注册的函数
        """
        self._callbacks.append(callback)

        def unregister():
            if callback in self._callbacks:
                self._callbacks.remove(callback)

        return unregister

    def __enter__(self) -> "BonjourBrowser":
        self.start()
        return self

    def __exit__(self, *args) -> None:
        self.stop()


class BonjourPublisher:
    """
    Bonjour 服务发布器。

    在本地网络上发布服务。

    对标 MoltBot bonjour.ts 的 publish 功能
    """

    def __init__(self, config: BonjourConfig | None = None) -> None:
        self._config = config or BonjourConfig()
        self._zeroconf: Zeroconf | None = None
        self._service_info: ServiceInfo | None = None
        self._registered = False

    def register(
        self,
        name: str | None = None,
        port: int | None = None,
        txt: dict[str, str] | None = None,
    ) -> bool:
        """
        注册服务。

        Args:
            name: 服务名称（默认使用主机名）
            port: 端口号
            txt: TXT 记录

        Returns:
            是否成功注册
        """
        if not ZEROCONF_AVAILABLE:
            return False

        if self._registered:
            return True

        name = name or self._config.service_name or socket.gethostname()
        port = port or self._config.port
        txt = txt or self._config.txt_record

        try:
            self._zeroconf = Zeroconf()

            # 获取本机地址
            hostname = socket.gethostname()
            try:
                addresses = [socket.inet_aton(socket.gethostbyname(hostname))]
            except socket.gaierror:
                addresses = [socket.inet_aton("127.0.0.1")]

            # 创建服务信息
            self._service_info = ServiceInfo(
                self._config.service_type + ".local.",
                name + "." + self._config.service_type + ".local.",
                addresses=addresses,
                port=port,
                properties=txt,
                server=hostname + ".local.",
            )

            self._zeroconf.register_service(self._service_info)
            self._registered = True
            return True
        except Exception:
            self.unregister()
            return False

    def unregister(self) -> None:
        """取消注册服务。"""
        if self._zeroconf and self._service_info:
            try:
                self._zeroconf.unregister_service(self._service_info)
            except Exception:
                pass

        if self._zeroconf:
            try:
                self._zeroconf.close()
            except Exception:
                pass

        self._zeroconf = None
        self._service_info = None
        self._registered = False

    def update_txt(self, txt: dict[str, str]) -> bool:
        """
        更新 TXT 记录。

        Args:
            txt: 新的 TXT 记录

        Returns:
            是否成功更新
        """
        if not self._registered or not self._zeroconf or not self._service_info:
            return False

        try:
            self._service_info.properties = txt
            self._zeroconf.update_service(self._service_info)
            return True
        except Exception:
            return False

    def __enter__(self) -> "BonjourPublisher":
        self.register()
        return self

    def __exit__(self, *args) -> None:
        self.unregister()


async def browse_services(
    service_type: str = "_lurkbot._tcp",
    timeout: float = 10.0,
) -> list[BonjourService]:
    """
    浏览本地网络上的服务。

    Args:
        service_type: 服务类型
        timeout: 超时时间（秒）

    Returns:
        发现的服务列表
    """
    if not ZEROCONF_AVAILABLE:
        return []

    config = BonjourConfig(service_type=service_type)
    browser = BonjourBrowser(config)

    try:
        browser.start()
        await asyncio.sleep(timeout)
        return browser.list_services()
    finally:
        browser.stop()


def publish_service(
    name: str | None = None,
    service_type: str = "_lurkbot._tcp",
    port: int = 0,
    txt: dict[str, str] | None = None,
) -> BonjourPublisher:
    """
    发布服务到本地网络。

    Args:
        name: 服务名称
        service_type: 服务类型
        port: 端口号
        txt: TXT 记录

    Returns:
        发布器实例（用于管理生命周期）
    """
    config = BonjourConfig(
        service_type=service_type,
        service_name=name,
        port=port,
        txt_record=txt or {},
    )
    publisher = BonjourPublisher(config)
    publisher.register()
    return publisher
