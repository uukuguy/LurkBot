"""技能 Frontmatter 解析器

实现 MoltBot 技能的 YAML Frontmatter 解析功能。
参考：MOLTBOT_COMPLETE_ARCHITECTURE.md 第 12.1 节
"""

import json
import re
from typing import Any

import yaml
from pydantic import BaseModel, Field


# ============================================================================
# Pydantic Models
# ============================================================================


class SkillRequirements(BaseModel):
    """技能依赖要求"""

    bins: list[str] = Field(default_factory=list, description="必需的二进制命令")
    any_bins: list[str] = Field(default_factory=list, description="任一可用的二进制命令")
    env: list[str] = Field(default_factory=list, description="必需的环境变量")
    config: list[str] = Field(default_factory=list, description="必需的配置项")


class SkillInstallStep(BaseModel):
    """技能安装步骤"""

    kind: str = Field(..., description="安装类型: brew|node|go|uv|download")
    id: str = Field(..., description="技能 ID")
    label: str = Field(..., description="显示名称")
    formula: str | None = Field(None, description="Homebrew formula")
    package: str | None = Field(None, description="NPM package")
    module: str | None = Field(None, description="Python module")
    url: str | None = Field(None, description="下载 URL")
    bins: list[str] = Field(default_factory=list, description="生成的二进制文件")
    os: list[str] = Field(default_factory=list, description="支持的操作系统")


class MoltbotMetadata(BaseModel):
    """Moltbot 特定元数据"""

    skill_key: str | None = Field(None, description="自定义技能 key")
    emoji: str | None = Field(None, description="技能图标 emoji")
    homepage: str | None = Field(None, description="主页 URL")
    primary_env: str | None = Field(None, description="主要环境: node|python|go|rust")
    always: bool = Field(False, description="是否总是加载")
    os: list[str] = Field(default_factory=list, description="支持的操作系统")
    requires: SkillRequirements | None = Field(None, description="依赖要求")
    install: list[SkillInstallStep] = Field(default_factory=list, description="安装步骤")


class SkillFrontmatter(BaseModel):
    """技能 Frontmatter 数据"""

    # 基本元数据
    name: str | None = Field(None, description="技能名称")
    description: str = Field(..., description="技能描述")
    version: str | None = Field(None, description="技能版本")
    tags: list[str] = Field(default_factory=list, description="标签")
    tools: list[str] = Field(default_factory=list, description="包装的 Tools 列表")

    # 调用策略
    user_invocable: bool = Field(True, description="用户可通过 /skill-name 调用")
    disable_model_invocation: bool = Field(False, description="禁用模型自动调用")

    # Moltbot 特定元数据
    metadata: MoltbotMetadata | None = Field(None, description="Moltbot 元数据")


# ============================================================================
# Frontmatter 解析
# ============================================================================


def parse_skill_frontmatter(content: str) -> tuple[SkillFrontmatter, str]:
    """解析技能文件的 YAML Frontmatter

    Args:
        content: 技能文件内容（包含 YAML Frontmatter）

    Returns:
        (frontmatter, body): 解析后的 Frontmatter 和正文内容

    Raises:
        ValueError: Frontmatter 格式错误或缺少必需字段
    """
    # 匹配 YAML Frontmatter (--- ... ---)
    pattern = r"^---\s*\n(.*?)\n---\s*\n(.*)$"
    match = re.match(pattern, content, re.DOTALL)

    if not match:
        raise ValueError("技能文件缺少 YAML Frontmatter (--- ... ---)")

    yaml_content = match.group(1)
    body_content = match.group(2).strip()

    # 解析 YAML
    try:
        data = yaml.safe_load(yaml_content)
    except yaml.YAMLError as e:
        raise ValueError(f"YAML 解析失败: {e}")

    if not isinstance(data, dict):
        raise ValueError("Frontmatter 必须是 YAML 对象")

    # 处理 metadata 字段（JSON5 格式字符串）
    if "metadata" in data and isinstance(data["metadata"], str):
        metadata_str = data["metadata"].strip()
        try:
            # 尝试解析为 JSON（JSON5 在这里简化为 JSON）
            metadata_dict = json.loads(metadata_str)
            if "moltbot" in metadata_dict:
                # 转换 key 格式：camelCase -> snake_case
                moltbot_data = _convert_keys_to_snake_case(metadata_dict["moltbot"])
                data["metadata"] = moltbot_data
            else:
                data["metadata"] = None
        except json.JSONDecodeError as e:
            raise ValueError(f"metadata JSON 解析失败: {e}")
    else:
        data["metadata"] = None

    # 转换 key 格式：camelCase -> snake_case
    data = _convert_keys_to_snake_case(data)

    # 验证和构造 Pydantic 模型
    try:
        frontmatter = SkillFrontmatter(**data)
    except Exception as e:
        raise ValueError(f"Frontmatter 验证失败: {e}")

    return frontmatter, body_content


def _convert_keys_to_snake_case(data: Any) -> Any:
    """递归转换字典的 key 从 camelCase 到 snake_case

    Args:
        data: 输入数据（dict, list, 或其他类型）

    Returns:
        转换后的数据
    """
    if isinstance(data, dict):
        result = {}
        for key, value in data.items():
            # camelCase -> snake_case
            snake_key = re.sub(r"(?<!^)(?=[A-Z])", "_", key).lower()
            result[snake_key] = _convert_keys_to_snake_case(value)
        return result
    elif isinstance(data, list):
        return [_convert_keys_to_snake_case(item) for item in data]
    else:
        return data


# ============================================================================
# 辅助函数
# ============================================================================


def validate_skill_file(file_path: str) -> tuple[SkillFrontmatter, str]:
    """验证并解析技能文件

    Args:
        file_path: 技能文件路径

    Returns:
        (frontmatter, body): 解析后的 Frontmatter 和正文内容

    Raises:
        FileNotFoundError: 文件不存在
        ValueError: 文件格式错误
    """
    with open(file_path, encoding="utf-8") as f:
        content = f.read()

    return parse_skill_frontmatter(content)
