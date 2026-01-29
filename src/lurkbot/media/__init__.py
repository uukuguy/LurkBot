"""
Media Understanding 系统主模块
为 LurkBot 提供多媒体内容理解能力
"""

from .understand import (
    MediaType,
    MediaUnderstandingResult,
    MediaProvider,
    understand_media,
    batch_understand_media,
)
from .config import (
    MediaConfig,
    ProviderConfig,
    ProviderName,
    get_default_config,
    load_config_from_file,
    save_config_to_file,
)
from .providers import (
    OpenAIProvider,
    AnthropicProvider,
    GeminiProvider,
    LocalProvider,
)

__all__ = [
    # 核心类型和函数
    "MediaType",
    "MediaUnderstandingResult",
    "MediaProvider",
    "understand_media",
    "batch_understand_media",

    # 配置相关
    "MediaConfig",
    "ProviderConfig",
    "ProviderName",
    "get_default_config",
    "load_config_from_file",
    "save_config_to_file",

    # 提供商
    "OpenAIProvider",
    "AnthropicProvider",
    "GeminiProvider",
    "LocalProvider",
]

# 版本信息
__version__ = "0.1.0"