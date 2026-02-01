"""配置提供者模块

支持多种配置中心集成：
- LocalFileProvider: 本地文件配置
- NacosProvider: 阿里云 Nacos 配置中心
- ConsulProvider: HashiCorp Consul KV
"""

from .base import (
    ConfigChangeCallback,
    ConfigItem,
    ConfigProvider,
    LocalFileProvider,
    ProviderConfig,
    ProviderStatus,
)
from .consul import ConsulConfig, ConsulProvider, create_consul_provider
from .nacos import NacosConfig, NacosProvider, create_nacos_provider

__all__ = [
    # Base
    "ConfigProvider",
    "ProviderConfig",
    "ProviderStatus",
    "ConfigItem",
    "ConfigChangeCallback",
    "LocalFileProvider",
    # Nacos
    "NacosProvider",
    "NacosConfig",
    "create_nacos_provider",
    # Consul
    "ConsulProvider",
    "ConsulConfig",
    "create_consul_provider",
]
