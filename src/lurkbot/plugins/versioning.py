"""插件版本管理系统

支持插件多版本共存、版本切换和回滚机制。

核心功能：
1. 版本解析和比较 - 支持语义化版本
2. 多版本加载 - 同时加载多个版本
3. 版本切换 - 动态切换插件版本
4. 回滚机制 - 支持版本回滚
"""

import re
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from loguru import logger
from pydantic import BaseModel, Field


# ============================================================================
# 版本模型
# ============================================================================


@dataclass
class SemanticVersion:
    """语义化版本

    格式: major.minor.patch[-prerelease][+build]
    例如: 1.2.3-alpha.1+build.123
    """

    major: int
    minor: int
    patch: int
    prerelease: str | None = None
    build: str | None = None

    @classmethod
    def parse(cls, version_str: str) -> "SemanticVersion":
        """解析版本字符串

        Args:
            version_str: 版本字符串

        Returns:
            SemanticVersion 实例

        Raises:
            ValueError: 版本格式不正确
        """
        # 正则表达式匹配语义化版本
        pattern = r"^(\d+)\.(\d+)\.(\d+)(?:-([a-zA-Z0-9.-]+))?(?:\+([a-zA-Z0-9.-]+))?$"
        match = re.match(pattern, version_str)

        if not match:
            raise ValueError(f"无效的版本格式: {version_str}")

        major, minor, patch, prerelease, build = match.groups()

        return cls(
            major=int(major),
            minor=int(minor),
            patch=int(patch),
            prerelease=prerelease,
            build=build,
        )

    def __str__(self) -> str:
        """转换为字符串"""
        version = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease:
            version += f"-{self.prerelease}"
        if self.build:
            version += f"+{self.build}"
        return version

    def __eq__(self, other: object) -> bool:
        """相等比较"""
        if not isinstance(other, SemanticVersion):
            return False
        return (
            self.major == other.major
            and self.minor == other.minor
            and self.patch == other.patch
            and self.prerelease == other.prerelease
        )

    def __lt__(self, other: "SemanticVersion") -> bool:
        """小于比较"""
        # 比较主版本号
        if self.major != other.major:
            return self.major < other.major

        # 比较次版本号
        if self.minor != other.minor:
            return self.minor < other.minor

        # 比较修订号
        if self.patch != other.patch:
            return self.patch < other.patch

        # 比较预发布版本
        if self.prerelease is None and other.prerelease is None:
            return False
        if self.prerelease is None:
            return False  # 正式版本 > 预发布版本
        if other.prerelease is None:
            return True  # 预发布版本 < 正式版本

        return self.prerelease < other.prerelease

    def __le__(self, other: "SemanticVersion") -> bool:
        """小于等于比较"""
        return self == other or self < other

    def __gt__(self, other: "SemanticVersion") -> bool:
        """大于比较"""
        return not self <= other

    def __ge__(self, other: "SemanticVersion") -> bool:
        """大于等于比较"""
        return not self < other


class VersionStatus(str, Enum):
    """版本状态"""

    ACTIVE = "active"  # 活跃版本
    INACTIVE = "inactive"  # 非活跃版本
    DEPRECATED = "deprecated"  # 已弃用版本


# ============================================================================
# 插件版本信息
# ============================================================================


class PluginVersion(BaseModel):
    """插件版本信息"""

    plugin_name: str = Field(..., description="插件名称")
    version: str = Field(..., description="版本号")
    status: VersionStatus = Field(VersionStatus.INACTIVE, description="版本状态")
    installed_at: datetime = Field(default_factory=datetime.now, description="安装时间")
    metadata: dict[str, Any] = Field(default_factory=dict, description="版本元数据")

    @property
    def semantic_version(self) -> SemanticVersion:
        """获取语义化版本对象"""
        return SemanticVersion.parse(self.version)


class VersionHistory(BaseModel):
    """版本历史记录"""

    plugin_name: str = Field(..., description="插件名称")
    from_version: str = Field(..., description="源版本")
    to_version: str = Field(..., description="目标版本")
    action: str = Field(..., description="操作类型（upgrade/downgrade/switch）")
    timestamp: datetime = Field(default_factory=datetime.now, description="时间戳")
    success: bool = Field(True, description="是否成功")
    reason: str | None = Field(None, description="原因")


# ============================================================================
# 版本管理器
# ============================================================================


class VersionManager:
    """版本管理器

    负责管理插件的多个版本，支持版本切换和回滚。
    """

    def __init__(self):
        """初始化版本管理器"""
        # 存储所有版本: {plugin_name: {version: PluginVersion}}
        self._versions: dict[str, dict[str, PluginVersion]] = {}
        # 当前活跃版本: {plugin_name: version}
        self._active_versions: dict[str, str] = {}
        # 版本历史
        self._history: list[VersionHistory] = []

    def register_version(
        self,
        plugin_name: str,
        version: str,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """注册插件版本

        Args:
            plugin_name: 插件名称
            version: 版本号
            metadata: 版本元数据

        Returns:
            是否成功注册
        """
        try:
            # 验证版本格式
            SemanticVersion.parse(version)

            if plugin_name not in self._versions:
                self._versions[plugin_name] = {}

            # 检查版本是否已存在
            if version in self._versions[plugin_name]:
                logger.warning(f"版本已存在: {plugin_name}@{version}")
                return False

            # 创建版本信息
            plugin_version = PluginVersion(
                plugin_name=plugin_name,
                version=version,
                metadata=metadata or {},
            )

            self._versions[plugin_name][version] = plugin_version
            logger.info(f"注册版本: {plugin_name}@{version}")

            return True

        except ValueError as e:
            logger.error(f"注册版本失败: {e}")
            return False

    def unregister_version(self, plugin_name: str, version: str) -> bool:
        """注销插件版本

        Args:
            plugin_name: 插件名称
            version: 版本号

        Returns:
            是否成功注销
        """
        if plugin_name not in self._versions:
            return False

        if version not in self._versions[plugin_name]:
            return False

        # 不能注销活跃版本
        if self._active_versions.get(plugin_name) == version:
            logger.error(f"无法注销活跃版本: {plugin_name}@{version}")
            return False

        del self._versions[plugin_name][version]
        logger.info(f"注销版本: {plugin_name}@{version}")

        return True

    def set_active_version(self, plugin_name: str, version: str) -> bool:
        """设置活跃版本

        Args:
            plugin_name: 插件名称
            version: 版本号

        Returns:
            是否成功设置
        """
        if plugin_name not in self._versions:
            logger.error(f"插件不存在: {plugin_name}")
            return False

        if version not in self._versions[plugin_name]:
            logger.error(f"版本不存在: {plugin_name}@{version}")
            return False

        # 记录旧版本
        old_version = self._active_versions.get(plugin_name)

        # 更新活跃版本
        self._active_versions[plugin_name] = version

        # 更新版本状态
        for v, pv in self._versions[plugin_name].items():
            pv.status = VersionStatus.ACTIVE if v == version else VersionStatus.INACTIVE

        # 记录历史
        if old_version:
            action = self._determine_action(old_version, version)
            self._record_history(
                plugin_name=plugin_name,
                from_version=old_version,
                to_version=version,
                action=action,
                success=True,
            )

        logger.info(f"设置活跃版本: {plugin_name}@{version}")
        return True

    def get_active_version(self, plugin_name: str) -> str | None:
        """获取活跃版本

        Args:
            plugin_name: 插件名称

        Returns:
            活跃版本号，如果不存在返回 None
        """
        return self._active_versions.get(plugin_name)

    def get_all_versions(self, plugin_name: str) -> list[str]:
        """获取所有版本

        Args:
            plugin_name: 插件名称

        Returns:
            版本号列表（按版本号排序）
        """
        if plugin_name not in self._versions:
            return []

        versions = list(self._versions[plugin_name].keys())
        # 按语义化版本排序
        versions.sort(key=lambda v: SemanticVersion.parse(v))

        return versions

    def get_latest_version(self, plugin_name: str) -> str | None:
        """获取最新版本

        Args:
            plugin_name: 插件名称

        Returns:
            最新版本号，如果不存在返回 None
        """
        versions = self.get_all_versions(plugin_name)
        return versions[-1] if versions else None

    def upgrade_to_latest(self, plugin_name: str) -> bool:
        """升级到最新版本

        Args:
            plugin_name: 插件名称

        Returns:
            是否成功升级
        """
        latest = self.get_latest_version(plugin_name)
        if not latest:
            return False

        return self.set_active_version(plugin_name, latest)

    def rollback(self, plugin_name: str) -> bool:
        """回滚到上一个版本

        Args:
            plugin_name: 插件名称

        Returns:
            是否成功回滚
        """
        # 查找最近的版本切换记录
        recent_history = [
            h for h in reversed(self._history) if h.plugin_name == plugin_name
        ]

        if not recent_history:
            logger.error(f"没有版本历史: {plugin_name}")
            return False

        last_change = recent_history[0]
        target_version = last_change.from_version

        # 检查目标版本是否存在
        if target_version not in self._versions.get(plugin_name, {}):
            logger.error(f"回滚目标版本不存在: {plugin_name}@{target_version}")
            return False

        success = self.set_active_version(plugin_name, target_version)

        if success:
            logger.info(f"回滚成功: {plugin_name} -> {target_version}")

        return success

    def get_version_info(self, plugin_name: str, version: str) -> PluginVersion | None:
        """获取版本信息

        Args:
            plugin_name: 插件名称
            version: 版本号

        Returns:
            版本信息，如果不存在返回 None
        """
        if plugin_name not in self._versions:
            return None
        return self._versions[plugin_name].get(version)

    def get_history(
        self, plugin_name: str | None = None, limit: int = 100
    ) -> list[VersionHistory]:
        """获取版本历史

        Args:
            plugin_name: 插件名称（可选）
            limit: 返回数量限制

        Returns:
            版本历史列表
        """
        history = self._history.copy()

        if plugin_name:
            history = [h for h in history if h.plugin_name == plugin_name]

        # 按时间倒序排序
        history.sort(key=lambda x: x.timestamp, reverse=True)

        return history[:limit]

    def _determine_action(self, from_version: str, to_version: str) -> str:
        """判断版本切换动作

        Args:
            from_version: 源版本
            to_version: 目标版本

        Returns:
            动作类型（upgrade/downgrade/switch）
        """
        try:
            from_ver = SemanticVersion.parse(from_version)
            to_ver = SemanticVersion.parse(to_version)

            if to_ver > from_ver:
                return "upgrade"
            elif to_ver < from_ver:
                return "downgrade"
            else:
                return "switch"
        except ValueError:
            return "switch"

    def _record_history(
        self,
        plugin_name: str,
        from_version: str,
        to_version: str,
        action: str,
        success: bool,
        reason: str | None = None,
    ) -> None:
        """记录版本历史

        Args:
            plugin_name: 插件名称
            from_version: 源版本
            to_version: 目标版本
            action: 操作类型
            success: 是否成功
            reason: 原因
        """
        history = VersionHistory(
            plugin_name=plugin_name,
            from_version=from_version,
            to_version=to_version,
            action=action,
            success=success,
            reason=reason,
        )
        self._history.append(history)

    def clear(self) -> None:
        """清空所有数据"""
        self._versions.clear()
        self._active_versions.clear()
        self._history.clear()
        logger.debug("清空版本管理器")


# ============================================================================
# 全局单例
# ============================================================================

_version_manager: VersionManager | None = None


def get_version_manager() -> VersionManager:
    """获取全局版本管理器实例

    Returns:
        VersionManager 实例
    """
    global _version_manager
    if _version_manager is None:
        _version_manager = VersionManager()
    return _version_manager


def reset_version_manager() -> None:
    """重置全局版本管理器（主要用于测试）"""
    global _version_manager
    _version_manager = None
