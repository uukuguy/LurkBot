"""插件 Manifest 验证和发现

实现插件发现、Manifest 解析和验证。
"""

import json
from pathlib import Path

from loguru import logger

from .manifest import PluginManifest, validate_plugin_name, validate_semantic_version


# ============================================================================
# Manifest 验证
# ============================================================================


class ManifestValidator:
    """插件 Manifest 验证器"""

    @staticmethod
    def validate(manifest: PluginManifest) -> list[str]:
        """验证插件 Manifest

        Args:
            manifest: 插件清单

        Returns:
            错误列表（空列表表示验证通过）
        """
        errors: list[str] = []

        # 验证名称格式
        if not validate_plugin_name(manifest.name):
            errors.append(
                f"插件名称格式错误: {manifest.name} "
                "(只能包含小写字母、数字、连字符，必须以字母开头，长度 3-50 字符)"
            )

        # 验证版本格式
        if not validate_semantic_version(manifest.version):
            errors.append(
                f"插件版本格式错误: {manifest.version} (必须符合语义化版本格式)"
            )

        # 验证入口文件（只检查格式，不检查文件是否存在）
        if not manifest.entry:
            errors.append("缺少插件入口文件")

        return errors

    @staticmethod
    def validate_from_file(manifest_path: Path) -> tuple[PluginManifest | None, list[str]]:
        """从文件验证 Manifest

        Args:
            manifest_path: plugin.json 文件路径

        Returns:
            (manifest, errors): 解析后的 Manifest 和错误列表
        """
        errors: list[str] = []

        # 检查文件是否存在
        if not manifest_path.exists():
            errors.append(f"Manifest 文件不存在: {manifest_path}")
            return None, errors

        # 读取并解析 JSON
        try:
            with open(manifest_path, encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            errors.append(f"Manifest JSON 解析失败: {e}")
            return None, errors
        except Exception as e:
            errors.append(f"读取 Manifest 文件失败: {e}")
            return None, errors

        # 构造 Pydantic 模型
        try:
            manifest = PluginManifest(**data)
        except Exception as e:
            errors.append(f"Manifest 验证失败: {e}")
            return None, errors

        # 业务逻辑验证
        validation_errors = ManifestValidator.validate(manifest)
        errors.extend(validation_errors)

        if errors:
            return manifest, errors
        else:
            return manifest, []


# ============================================================================
# 插件发现
# ============================================================================


def discover_plugins_in_dir(directory: Path) -> list[tuple[Path, PluginManifest]]:
    """在指定目录中发现插件

    插件发现规则：
    - 查找所有 plugin.json 文件
    - 解析并验证 Manifest
    - 跳过无效的插件

    Args:
        directory: 目录路径

    Returns:
        插件列表：[(plugin_dir, manifest), ...]
    """
    plugins: list[tuple[Path, PluginManifest]] = []

    if not directory.exists():
        logger.debug(f"插件目录不存在: {directory}")
        return plugins

    # 查找所有 plugin.json 文件
    for manifest_file in directory.rglob("plugin.json"):
        plugin_dir = manifest_file.parent

        # 验证 Manifest
        manifest, errors = ManifestValidator.validate_from_file(manifest_file)

        if errors:
            logger.warning(
                f"跳过无效插件 {plugin_dir.name}: {', '.join(errors)}"
            )
            continue

        if manifest is None:
            continue

        plugins.append((plugin_dir, manifest))
        logger.debug(f"发现插件: {manifest.name} v{manifest.version} (path={plugin_dir})")

    return plugins


def discover_all_plugins(
    workspace_root: Path | str | None = None,
    extra_dirs: list[Path | str] | None = None,
) -> list[tuple[Path, PluginManifest]]:
    """发现所有插件

    插件搜索路径：
    1. 工作区插件：.plugins/
    2. Node modules：node_modules/@lurkbot/plugin-*
    3. 额外目录

    Args:
        workspace_root: 工作区根目录（默认为当前目录）
        extra_dirs: 额外的插件目录列表

    Returns:
        插件列表：[(plugin_dir, manifest), ...]
    """
    if workspace_root is None:
        workspace_root = Path.cwd()
    else:
        workspace_root = Path(workspace_root)

    all_plugins: list[tuple[Path, PluginManifest]] = []

    # 1. 工作区插件：.plugins/
    workspace_plugins_dir = workspace_root / ".plugins"
    if workspace_plugins_dir.exists():
        plugins = discover_plugins_in_dir(workspace_plugins_dir)
        all_plugins.extend(plugins)
        logger.debug(f"工作区插件目录发现 {len(plugins)} 个插件")

    # 2. Node modules：node_modules/@lurkbot/plugin-*
    node_modules_dir = workspace_root / "node_modules" / "@lurkbot"
    if node_modules_dir.exists():
        for plugin_dir in node_modules_dir.iterdir():
            if plugin_dir.is_dir() and plugin_dir.name.startswith("plugin-"):
                manifest_file = plugin_dir / "plugin.json"
                if manifest_file.exists():
                    manifest, errors = ManifestValidator.validate_from_file(manifest_file)
                    if not errors and manifest is not None:
                        all_plugins.append((plugin_dir, manifest))
                        logger.debug(f"发现 npm 插件: {manifest.name}")

    # 3. 额外目录
    if extra_dirs:
        for extra_dir in extra_dirs:
            extra_path = Path(extra_dir)
            if extra_path.exists():
                plugins = discover_plugins_in_dir(extra_path)
                all_plugins.extend(plugins)
                logger.debug(f"额外目录 {extra_dir} 发现 {len(plugins)} 个插件")

    logger.info(f"共发现 {len(all_plugins)} 个有效插件")
    return all_plugins


# ============================================================================
# 插件去重
# ============================================================================


def deduplicate_plugins(
    plugins: list[tuple[Path, PluginManifest]]
) -> dict[str, tuple[Path, PluginManifest]]:
    """去重插件（保留最新版本）

    Args:
        plugins: 插件列表

    Returns:
        去重后的插件字典 {name: (plugin_dir, manifest)}
    """
    result: dict[str, tuple[Path, PluginManifest]] = {}

    for plugin_dir, manifest in plugins:
        name = manifest.name

        if name not in result:
            result[name] = (plugin_dir, manifest)
            logger.debug(f"加载插件: {name} v{manifest.version}")
        else:
            # 比较版本，保留最新的
            existing_dir, existing_manifest = result[name]
            if _compare_versions(manifest.version, existing_manifest.version) > 0:
                result[name] = (plugin_dir, manifest)
                logger.debug(
                    f"替换插件: {name} v{existing_manifest.version} -> v{manifest.version}"
                )
            else:
                logger.debug(
                    f"跳过插件: {name} v{manifest.version} (已有 v{existing_manifest.version})"
                )

    return result


def _compare_versions(v1: str, v2: str) -> int:
    """比较语义化版本号

    Args:
        v1: 版本 1
        v2: 版本 2

    Returns:
        1 if v1 > v2, -1 if v1 < v2, 0 if v1 == v2
    """
    # 简化版本比较（只比较 major.minor.patch）
    parts1 = v1.split("-")[0].split("+")[0].split(".")
    parts2 = v2.split("-")[0].split("+")[0].split(".")

    for p1, p2 in zip(parts1, parts2):
        n1, n2 = int(p1), int(p2)
        if n1 > n2:
            return 1
        elif n1 < n2:
            return -1

    # 长度不同，长的版本更大
    if len(parts1) > len(parts2):
        return 1
    elif len(parts1) < len(parts2):
        return -1
    else:
        return 0
