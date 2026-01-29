"""插件 Manifest 数据模型

定义插件清单的 Pydantic 模型和验证规则。
参考：MOLTBOT_COMPLETE_ARCHITECTURE.md 第 16.1 节
"""

from enum import Enum

from pydantic import BaseModel, Field


# ============================================================================
# 枚举类型
# ============================================================================


class PluginType(str, Enum):
    """插件类型"""

    CHANNEL = "channel"  # 频道适配器
    TOOL = "tool"  # 工具插件
    HOOK = "hook"  # Hook 扩展
    SKILL = "skill"  # 技能插件
    MIDDLEWARE = "middleware"  # 中间件
    OTHER = "other"  # 其他


class PluginLanguage(str, Enum):
    """插件语言"""

    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"


# ============================================================================
# Manifest Models
# ============================================================================


class PluginAuthor(BaseModel):
    """插件作者信息"""

    name: str = Field(..., description="作者名称")
    email: str | None = Field(None, description="作者邮箱")
    url: str | None = Field(None, description="作者主页")


class PluginRepository(BaseModel):
    """插件仓库信息"""

    type: str = Field(..., description="仓库类型（如 git）")
    url: str = Field(..., description="仓库 URL")


class PluginDependencies(BaseModel):
    """插件依赖"""

    python: list[str] = Field(default_factory=list, description="Python 包依赖")
    system: list[str] = Field(default_factory=list, description="系统依赖（如 ffmpeg）")
    env: list[str] = Field(default_factory=list, description="环境变量依赖")


class PluginPermissions(BaseModel):
    """插件权限"""

    filesystem: bool = Field(False, description="文件系统访问")
    network: bool = Field(False, description="网络访问")
    exec: bool = Field(False, description="命令执行")
    channels: list[str] = Field(default_factory=list, description="频道访问权限")


class PluginManifest(BaseModel):
    """插件清单（plugin.json）

    定义插件的元数据、依赖和权限。
    """

    # 基本信息
    name: str = Field(..., description="插件名称（唯一标识）")
    version: str = Field(..., description="插件版本（语义化版本）")
    description: str = Field(..., description="插件描述")
    type: PluginType = Field(PluginType.OTHER, description="插件类型")
    language: PluginLanguage = Field(PluginLanguage.PYTHON, description="插件语言")

    # 作者和仓库
    author: PluginAuthor | None = Field(None, description="作者信息")
    repository: PluginRepository | None = Field(None, description="仓库信息")
    homepage: str | None = Field(None, description="主页 URL")
    license: str | None = Field(None, description="许可证（如 MIT）")

    # 入口点
    entry: str = Field(..., description="插件入口文件（相对路径）")
    main_class: str | None = Field(None, description="主类名（Python）")

    # 依赖和权限
    dependencies: PluginDependencies = Field(
        default_factory=PluginDependencies, description="依赖"
    )
    permissions: PluginPermissions = Field(
        default_factory=PluginPermissions, description="权限"
    )

    # 兼容性
    lurkbot_version: str | None = Field(None, description="LurkBot 版本要求（如 >=1.0.0）")
    os: list[str] = Field(
        default_factory=list, description="支持的操作系统（darwin, linux, win32）"
    )

    # 配置
    config_schema: dict | None = Field(None, description="配置 schema（JSON Schema）")
    default_config: dict | None = Field(None, description="默认配置")

    # 元数据
    tags: list[str] = Field(default_factory=list, description="标签")
    keywords: list[str] = Field(default_factory=list, description="关键词")
    enabled: bool = Field(True, description="是否默认启用")


# ============================================================================
# 验证辅助函数
# ============================================================================


def validate_plugin_name(name: str) -> bool:
    """验证插件名称格式

    插件名称规则：
    - 只能包含小写字母、数字、连字符
    - 必须以字母开头
    - 长度 3-50 字符

    Args:
        name: 插件名称

    Returns:
        是否有效
    """
    import re

    pattern = r"^[a-z][a-z0-9-]{2,49}$"
    return bool(re.match(pattern, name))


def validate_semantic_version(version: str) -> bool:
    """验证语义化版本格式

    版本格式：major.minor.patch (如 1.2.3)

    Args:
        version: 版本号

    Returns:
        是否有效
    """
    import re

    pattern = r"^\d+\.\d+\.\d+(-[a-z0-9.]+)?(\+[a-z0-9.]+)?$"
    return bool(re.match(pattern, version))
