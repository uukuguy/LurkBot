"""插件市场

提供插件发现、下载、安装和版本管理功能。
"""

import asyncio
import hashlib
import json
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
from loguru import logger
from pydantic import BaseModel, Field

from .manager import PluginManager
from .manifest import PluginManifest
from .schema_validator import ManifestValidator


# ============================================================================
# 数据模型
# ============================================================================


class PluginPackageInfo(BaseModel):
    """插件包信息"""

    name: str = Field(..., description="插件名称")
    version: str = Field(..., description="插件版本")
    description: str = Field(..., description="插件描述")
    author: str = Field(..., description="作者")
    download_url: str = Field(..., description="下载地址")
    checksum: str | None = Field(None, description="SHA256 校验和")
    dependencies: list[str] = Field(default_factory=list, description="依赖列表")
    tags: list[str] = Field(default_factory=list, description="标签")
    downloads: int = Field(0, description="下载次数")
    rating: float = Field(0.0, description="评分")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")


class PluginIndex(BaseModel):
    """插件索引"""

    version: str = Field("1.0.0", description="索引版本")
    plugins: dict[str, list[PluginPackageInfo]] = Field(
        default_factory=dict, description="插件列表（按名称分组）"
    )
    last_updated: datetime = Field(default_factory=datetime.now, description="最后更新时间")


# ============================================================================
# 插件市场
# ============================================================================


class PluginMarketplace:
    """插件市场

    提供插件发现、下载、安装和版本管理功能。
    """

    def __init__(
        self,
        manager: PluginManager,
        index_url: str | None = None,
        cache_dir: Path | None = None,
    ):
        """初始化市场

        Args:
            manager: 插件管理器
            index_url: 插件索引 URL
            cache_dir: 缓存目录
        """
        self.manager = manager
        self.index_url = index_url or "https://plugins.lurkbot.io/index.json"
        self.cache_dir = cache_dir or Path.home() / ".lurkbot" / "plugin_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self._index: PluginIndex | None = None
        self._client = httpx.AsyncClient(timeout=30.0)

    async def close(self) -> None:
        """关闭市场"""
        await self._client.aclose()

    async def refresh_index(self) -> None:
        """刷新插件索引"""
        logger.info(f"刷新插件索引: {self.index_url}")

        try:
            response = await self._client.get(self.index_url)
            response.raise_for_status()

            data = response.json()
            self._index = PluginIndex(**data)

            # 保存到本地缓存
            cache_file = self.cache_dir / "index.json"
            cache_file.write_text(json.dumps(data, indent=2, default=str))

            logger.info(f"插件索引刷新成功，共 {len(self._index.plugins)} 个插件")

        except Exception as e:
            logger.error(f"刷新插件索引失败: {e}")

            # 尝试从缓存加载
            cache_file = self.cache_dir / "index.json"
            if cache_file.exists():
                logger.info("从缓存加载插件索引")
                data = json.loads(cache_file.read_text())
                self._index = PluginIndex(**data)
            else:
                raise

    async def search(
        self,
        query: str | None = None,
        tags: list[str] | None = None,
        limit: int = 10,
    ) -> list[PluginPackageInfo]:
        """搜索插件

        Args:
            query: 搜索关键词
            tags: 标签过滤
            limit: 返回数量限制

        Returns:
            插件包信息列表
        """
        if self._index is None:
            await self.refresh_index()

        results: list[PluginPackageInfo] = []

        # 遍历所有插件
        for plugin_versions in self._index.plugins.values():
            if not plugin_versions:
                continue

            # 取最新版本
            latest = plugin_versions[0]

            # 关键词过滤
            if query:
                query_lower = query.lower()
                if not (
                    query_lower in latest.name.lower()
                    or query_lower in latest.description.lower()
                ):
                    continue

            # 标签过滤
            if tags:
                if not any(tag in latest.tags for tag in tags):
                    continue

            results.append(latest)

        # 按评分和下载量排序
        results.sort(key=lambda p: (p.rating, p.downloads), reverse=True)

        return results[:limit]

    async def get_plugin_info(
        self, name: str, version: str | None = None
    ) -> PluginPackageInfo | None:
        """获取插件信息

        Args:
            name: 插件名称
            version: 插件版本（None 表示最新版本）

        Returns:
            插件包信息，如果不存在则返回 None
        """
        if self._index is None:
            await self.refresh_index()

        versions = self._index.plugins.get(name)
        if not versions:
            return None

        if version is None:
            return versions[0]  # 返回最新版本

        for pkg in versions:
            if pkg.version == version:
                return pkg

        return None

    async def download_plugin(
        self, name: str, version: str | None = None
    ) -> Path:
        """下载插件

        Args:
            name: 插件名称
            version: 插件版本（None 表示最新版本）

        Returns:
            下载的插件目录路径
        """
        # 获取插件信息
        pkg_info = await self.get_plugin_info(name, version)
        if not pkg_info:
            raise ValueError(f"插件 {name} 不存在")

        logger.info(f"下载插件: {pkg_info.name} v{pkg_info.version}")

        # 检查缓存
        cache_key = f"{pkg_info.name}-{pkg_info.version}"
        cached_dir = self.cache_dir / cache_key
        if cached_dir.exists():
            logger.info(f"使用缓存的插件: {cached_dir}")
            return cached_dir

        # 下载插件包
        try:
            response = await self._client.get(pkg_info.download_url)
            response.raise_for_status()

            # 验证校验和
            if pkg_info.checksum:
                actual_checksum = hashlib.sha256(response.content).hexdigest()
                if actual_checksum != pkg_info.checksum:
                    raise ValueError(
                        f"校验和不匹配: expected={pkg_info.checksum}, actual={actual_checksum}"
                    )

            # 解压到临时目录
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                archive_path = temp_path / "plugin.tar.gz"
                archive_path.write_bytes(response.content)

                # 解压
                shutil.unpack_archive(archive_path, temp_path)

                # 查找插件目录（包含 manifest.json 的目录）
                plugin_dir = None
                for item in temp_path.iterdir():
                    if item.is_dir() and (item / "manifest.json").exists():
                        plugin_dir = item
                        break

                if not plugin_dir:
                    raise ValueError("插件包中未找到 manifest.json")

                # 移动到缓存目录
                shutil.move(str(plugin_dir), str(cached_dir))

            logger.info(f"插件下载成功: {cached_dir}")
            return cached_dir

        except Exception as e:
            logger.error(f"下载插件失败: {e}")
            raise

    async def install_plugin(
        self,
        name: str,
        version: str | None = None,
        target_dir: Path | None = None,
    ) -> bool:
        """安装插件

        Args:
            name: 插件名称
            version: 插件版本（None 表示最新版本）
            target_dir: 目标目录（None 表示默认插件目录）

        Returns:
            是否安装成功
        """
        logger.info(f"安装插件: {name} v{version or 'latest'}")

        try:
            # 下载插件
            plugin_dir = await self.download_plugin(name, version)

            # 验证 manifest
            manifest, errors = ManifestValidator.validate_from_file(
                plugin_dir / "manifest.json"
            )
            if errors:
                logger.error(f"插件 manifest 验证失败: {errors}")
                return False

            # 检查依赖
            if manifest.dependencies:
                logger.info(f"检查依赖: {manifest.dependencies}")
                for dep in manifest.dependencies:
                    if not await self._check_dependency(dep):
                        logger.error(f"依赖 {dep} 未满足")
                        return False

            # 确定目标目录
            if target_dir is None:
                target_dir = Path("plugins") / manifest.name
            else:
                target_dir = target_dir / manifest.name

            # 复制插件文件
            if target_dir.exists():
                logger.warning(f"插件目录已存在，将被覆盖: {target_dir}")
                shutil.rmtree(target_dir)

            shutil.copytree(plugin_dir, target_dir)

            # 加载插件
            await self.manager.load_plugin(target_dir, manifest)

            logger.info(f"插件 {name} 安装成功")
            return True

        except Exception as e:
            logger.error(f"安装插件失败: {e}")
            return False

    async def uninstall_plugin(self, name: str, remove_files: bool = True) -> bool:
        """卸载插件

        Args:
            name: 插件名称
            remove_files: 是否删除插件文件

        Returns:
            是否卸载成功
        """
        logger.info(f"卸载插件: {name}")

        try:
            # 卸载插件
            success = await self.manager.unload_plugin(name)

            if success and remove_files:
                # 删除插件文件
                plugin = self.manager.loader.get(name)
                if plugin:
                    plugin_dir = plugin.plugin_dir
                    if plugin_dir.exists():
                        shutil.rmtree(plugin_dir)
                        logger.info(f"删除插件文件: {plugin_dir}")

            return success

        except Exception as e:
            logger.error(f"卸载插件失败: {e}")
            return False

    async def update_plugin(self, name: str) -> bool:
        """更新插件到最新版本

        Args:
            name: 插件名称

        Returns:
            是否更新成功
        """
        logger.info(f"更新插件: {name}")

        try:
            # 获取当前版本
            plugin = self.manager.loader.get(name)
            if not plugin:
                logger.error(f"插件 {name} 未安装")
                return False

            current_version = plugin.manifest.version

            # 获取最新版本
            latest_info = await self.get_plugin_info(name)
            if not latest_info:
                logger.error(f"插件 {name} 在市场中不存在")
                return False

            if latest_info.version == current_version:
                logger.info(f"插件 {name} 已是最新版本: {current_version}")
                return True

            logger.info(
                f"更新插件 {name}: {current_version} -> {latest_info.version}"
            )

            # 卸载旧版本
            await self.uninstall_plugin(name, remove_files=True)

            # 安装新版本
            return await self.install_plugin(name, latest_info.version)

        except Exception as e:
            logger.error(f"更新插件失败: {e}")
            return False

    async def list_installed(self) -> list[tuple[str, str]]:
        """列出已安装的插件

        Returns:
            (插件名称, 版本) 列表
        """
        plugins = []
        for name in self.manager.loader._plugins.keys():
            plugin = self.manager.loader.get(name)
            if plugin:
                plugins.append((plugin.manifest.name, plugin.manifest.version))
        return plugins

    async def _check_dependency(self, dep: str) -> bool:
        """检查依赖是否满足

        Args:
            dep: 依赖描述（格式: name@version 或 name）

        Returns:
            是否满足依赖
        """
        # 解析依赖
        if "@" in dep:
            dep_name, dep_version = dep.split("@", 1)
        else:
            dep_name = dep
            dep_version = None

        # 检查是否已安装
        plugin = self.manager.loader.get(dep_name)
        if not plugin:
            return False

        # 检查版本
        if dep_version and plugin.manifest.version != dep_version:
            return False

        return True


# ============================================================================
# 全局单例
# ============================================================================

_marketplace: PluginMarketplace | None = None


def get_marketplace(
    manager: PluginManager | None = None,
    index_url: str | None = None,
    cache_dir: Path | None = None,
) -> PluginMarketplace:
    """获取插件市场单例

    Args:
        manager: 插件管理器
        index_url: 插件索引 URL
        cache_dir: 缓存目录

    Returns:
        插件市场实例
    """
    global _marketplace
    if _marketplace is None:
        if manager is None:
            raise ValueError("首次调用必须提供 manager 参数")
        _marketplace = PluginMarketplace(manager, index_url, cache_dir)
    return _marketplace
