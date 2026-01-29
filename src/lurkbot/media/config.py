"""
Media Understanding 配置系统
管理媒体理解的提供商配置和能力设置
"""

from dataclasses import dataclass, field
from typing import Literal
import os
from pathlib import Path
from loguru import logger

from .understand import MediaType

ProviderName = Literal["openai", "anthropic", "gemini", "local"]


@dataclass
class ProviderConfig:
    """提供商配置"""
    provider: ProviderName
    model: str
    enabled: bool = True
    priority: int = 0  # 数字越小优先级越高
    supported_types: list[MediaType] = field(default_factory=lambda: ["image", "audio", "video", "document"])
    max_file_size_mb: int = 20  # 最大文件大小限制 (MB)

    def supports_type(self, media_type: MediaType) -> bool:
        """检查是否支持指定媒体类型"""
        return media_type in self.supported_types


@dataclass
class MediaConfig:
    """媒体理解配置"""
    providers: list[ProviderConfig] = field(default_factory=list)
    max_chars: dict[MediaType, int] = field(default_factory=lambda: {
        "image": 500,
        "audio": 1000,
        "video": 800,
        "document": 1200,
    })
    timeout_seconds: int = 30
    max_concurrent: int = 3

    def get_providers_for_type(self, media_type: MediaType) -> list[ProviderConfig]:
        """
        获取支持指定媒体类型的提供商配置，按优先级排序

        Args:
            media_type: 媒体类型

        Returns:
            list[ProviderConfig]: 支持该类型的提供商配置列表，按优先级排序
        """
        # 过滤出启用且支持该类型的提供商
        compatible_providers = [
            provider for provider in self.providers
            if provider.enabled and provider.supports_type(media_type)
        ]

        # 按优先级排序 (priority 数字越小优先级越高)
        compatible_providers.sort(key=lambda p: p.priority)

        logger.debug(f"找到 {len(compatible_providers)} 个支持 {media_type} 的提供商")
        return compatible_providers

    def get_max_chars(self, media_type: MediaType) -> int:
        """获取指定媒体类型的最大字符数限制"""
        return self.max_chars.get(media_type, 500)

    def add_provider(self, provider_config: ProviderConfig) -> None:
        """添加提供商配置"""
        # 检查是否已存在相同提供商
        existing_index = None
        for i, existing in enumerate(self.providers):
            if existing.provider == provider_config.provider:
                existing_index = i
                break

        if existing_index is not None:
            logger.info(f"更新现有提供商配置: {provider_config.provider}")
            self.providers[existing_index] = provider_config
        else:
            logger.info(f"添加新提供商配置: {provider_config.provider}")
            self.providers.append(provider_config)

    def remove_provider(self, provider_name: ProviderName) -> bool:
        """
        移除提供商配置

        Args:
            provider_name: 提供商名称

        Returns:
            bool: 是否成功移除
        """
        for i, provider in enumerate(self.providers):
            if provider.provider == provider_name:
                del self.providers[i]
                logger.info(f"移除提供商配置: {provider_name}")
                return True

        logger.warning(f"未找到提供商配置: {provider_name}")
        return False

    def enable_provider(self, provider_name: ProviderName) -> bool:
        """启用提供商"""
        for provider in self.providers:
            if provider.provider == provider_name:
                provider.enabled = True
                logger.info(f"启用提供商: {provider_name}")
                return True

        logger.warning(f"未找到提供商配置: {provider_name}")
        return False

    def disable_provider(self, provider_name: ProviderName) -> bool:
        """禁用提供商"""
        for provider in self.providers:
            if provider.provider == provider_name:
                provider.enabled = False
                logger.info(f"禁用提供商: {provider_name}")
                return True

        logger.warning(f"未找到提供商配置: {provider_name}")
        return False


def get_default_config() -> MediaConfig:
    """
    获取默认媒体配置

    Returns:
        MediaConfig: 默认配置
    """
    providers = []

    # OpenAI 配置 (优先级最高)
    if os.getenv("OPENAI_API_KEY"):
        providers.append(ProviderConfig(
            provider="openai",
            model="gpt-4o",
            priority=0,
            supported_types=["image", "audio", "document"],
            max_file_size_mb=20,
        ))

    # Anthropic 配置
    if os.getenv("ANTHROPIC_API_KEY"):
        providers.append(ProviderConfig(
            provider="anthropic",
            model="claude-3-5-sonnet-20241022",
            priority=1,
            supported_types=["image", "document"],
            max_file_size_mb=10,
        ))

    # Google Gemini 配置
    if os.getenv("GOOGLE_API_KEY"):
        providers.append(ProviderConfig(
            provider="gemini",
            model="gemini-1.5-pro",
            priority=2,
            supported_types=["image", "audio", "video", "document"],
            max_file_size_mb=20,
        ))

    # 本地降级配置 (优先级最低)
    providers.append(ProviderConfig(
        provider="local",
        model="local-cli",
        priority=99,
        supported_types=["image", "audio", "video", "document"],
        max_file_size_mb=100,
    ))

    return MediaConfig(providers=providers)


def load_config_from_file(config_path: str | Path) -> MediaConfig:
    """
    从文件加载媒体配置

    Args:
        config_path: 配置文件路径

    Returns:
        MediaConfig: 加载的配置
    """
    config_path = Path(config_path)

    if not config_path.exists():
        logger.warning(f"配置文件不存在: {config_path}")
        return get_default_config()

    try:
        import json

        with open(config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 解析提供商配置
        providers = []
        for provider_data in data.get("providers", []):
            providers.append(ProviderConfig(
                provider=provider_data["provider"],
                model=provider_data["model"],
                enabled=provider_data.get("enabled", True),
                priority=provider_data.get("priority", 0),
                supported_types=provider_data.get("supported_types", ["image", "audio", "video", "document"]),
                max_file_size_mb=provider_data.get("max_file_size_mb", 20),
            ))

        # 解析其他配置
        max_chars = data.get("max_chars", {
            "image": 500,
            "audio": 1000,
            "video": 800,
            "document": 1200,
        })

        config = MediaConfig(
            providers=providers,
            max_chars=max_chars,
            timeout_seconds=data.get("timeout_seconds", 30),
            max_concurrent=data.get("max_concurrent", 3),
        )

        logger.info(f"成功加载配置文件: {config_path}")
        return config

    except Exception as e:
        logger.error(f"加载配置文件失败: {e}")
        return get_default_config()


def save_config_to_file(config: MediaConfig, config_path: str | Path) -> bool:
    """
    保存媒体配置到文件

    Args:
        config: 媒体配置
        config_path: 配置文件路径

    Returns:
        bool: 是否保存成功
    """
    config_path = Path(config_path)

    try:
        import json

        # 确保目录存在
        config_path.parent.mkdir(parents=True, exist_ok=True)

        # 序列化配置
        data = {
            "providers": [
                {
                    "provider": p.provider,
                    "model": p.model,
                    "enabled": p.enabled,
                    "priority": p.priority,
                    "supported_types": p.supported_types,
                    "max_file_size_mb": p.max_file_size_mb,
                }
                for p in config.providers
            ],
            "max_chars": config.max_chars,
            "timeout_seconds": config.timeout_seconds,
            "max_concurrent": config.max_concurrent,
        }

        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(f"成功保存配置文件: {config_path}")
        return True

    except Exception as e:
        logger.error(f"保存配置文件失败: {e}")
        return False