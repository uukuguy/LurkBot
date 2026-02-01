"""缓存配置模块

提供缓存系统的配置管理。
"""

from pydantic import Field
from pydantic_settings import BaseSettings


class CacheConfig(BaseSettings):
    """缓存配置

    支持通过环境变量配置：
    - CACHE_L1_MAXSIZE: L1 最大缓存条目数
    - CACHE_L1_TTL: L1 过期时间（秒）
    - CACHE_L2_URL: L2 Redis 连接 URL
    - CACHE_L2_TTL: L2 过期时间（秒）
    - CACHE_L2_ENABLED: 是否启用 L2
    - CACHE_L2_MAX_CONNECTIONS: L2 最大连接数
    """

    # L1 配置（内存缓存）
    l1_maxsize: int = Field(
        default=1000,
        description="L1 最大缓存条目数",
        ge=1,
    )
    l1_ttl: int = Field(
        default=60,
        description="L1 过期时间（秒）",
        ge=1,
    )

    # L2 配置（Redis 缓存）
    l2_url: str = Field(
        default="redis://localhost:6379",
        description="L2 Redis 连接 URL",
    )
    l2_ttl: int = Field(
        default=300,
        description="L2 过期时间（秒）",
        ge=1,
    )
    l2_enabled: bool = Field(
        default=True,
        description="是否启用 L2",
    )
    l2_max_connections: int = Field(
        default=10,
        description="L2 最大连接数",
        ge=1,
    )

    class Config:
        env_prefix = "CACHE_"
        case_sensitive = False


# 默认配置实例
default_cache_config = CacheConfig()
