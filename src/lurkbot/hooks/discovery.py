"""
Hooks 扩展系统 - 发现机制

负责从不同优先级目录发现和加载钩子包。
"""

import os
import importlib.util
from pathlib import Path
from typing import Optional
from loguru import logger
import yaml

from .types import HookMetadata, HookPackage, HookHandler, HookRequirements


def discover_hooks(
    workspace_dir: Optional[str] = None,
    user_hooks_dir: Optional[str] = None,
    bundled_hooks_dir: Optional[str] = None,
) -> list[HookPackage]:
    """
    按优先级发现钩子包

    优先级顺序:
    1. <workspace>/hooks/           # 最高优先级
    2. ~/.lurkbot/hooks/            # 用户安装
    3. <lurkbot>/hooks/bundled/     # 预装

    Args:
        workspace_dir: 工作区目录
        user_hooks_dir: 用户钩子目录
        bundled_hooks_dir: 预装钩子目录

    Returns:
        发现的钩子包列表
    """
    search_dirs: list[Path] = []

    # 1. 工作区钩子
    if workspace_dir:
        workspace_hooks = Path(workspace_dir) / "hooks"
        if workspace_hooks.exists():
            search_dirs.append(workspace_hooks)

    # 2. 用户钩子
    if user_hooks_dir:
        user_hooks = Path(user_hooks_dir)
    else:
        user_hooks = Path.home() / ".lurkbot" / "hooks"

    if user_hooks.exists():
        search_dirs.append(user_hooks)

    # 3. 预装钩子
    if bundled_hooks_dir:
        bundled_hooks = Path(bundled_hooks_dir)
    else:
        # 默认为当前模块的 bundled 子目录
        bundled_hooks = Path(__file__).parent / "bundled"

    if bundled_hooks.exists():
        search_dirs.append(bundled_hooks)

    # 发现所有钩子
    discovered_packages: list[HookPackage] = []
    seen_names: set[str] = set()

    for search_dir in search_dirs:
        logger.debug(f"Searching for hooks in: {search_dir}")

        for hook_dir in search_dir.iterdir():
            if not hook_dir.is_dir():
                continue

            try:
                package = load_hook_from_path(hook_dir)
                if package:
                    # 去重: 优先级高的目录中的钩子会覆盖低优先级的同名钩子
                    if package.metadata.name in seen_names:
                        logger.debug(
                            f"Skipping duplicate hook '{package.metadata.name}' from {hook_dir}"
                        )
                        continue

                    discovered_packages.append(package)
                    seen_names.add(package.metadata.name)
                    logger.info(
                        f"Discovered hook '{package.metadata.name}' from {hook_dir}"
                    )
            except Exception as e:
                logger.warning(f"Failed to load hook from {hook_dir}: {e}")

    return discovered_packages


def load_hook_from_path(hook_dir: Path) -> Optional[HookPackage]:
    """
    从目录加载钩子包

    钩子包结构:
    my-hook/
    ├── HOOK.md          # YAML frontmatter + 文档
    └── handler.py       # HookHandler 函数

    Args:
        hook_dir: 钩子目录

    Returns:
        钩子包，如果加载失败则返回 None
    """
    hook_md = hook_dir / "HOOK.md"
    handler_py = hook_dir / "handler.py"

    if not hook_md.exists():
        logger.warning(f"Missing HOOK.md in {hook_dir}")
        return None

    if not handler_py.exists():
        logger.warning(f"Missing handler.py in {hook_dir}")
        return None

    # 1. 解析 HOOK.md frontmatter
    metadata = parse_hook_metadata(hook_md)
    if not metadata:
        return None

    # 2. 加载 handler.py
    handler = load_hook_handler(handler_py)
    if not handler:
        return None

    # 3. 检查依赖
    if not check_hook_requirements(metadata.requires):
        logger.warning(
            f"Hook '{metadata.name}' requirements not met, disabling"
        )
        metadata.enabled = False

    return HookPackage(
        metadata=metadata,
        handler=handler,
        source_path=str(hook_dir),
    )


def parse_hook_metadata(hook_md: Path) -> Optional[HookMetadata]:
    """
    解析 HOOK.md 的 YAML frontmatter

    格式:
    ---
    name: session-memory
    emoji: 💾
    events:
      - command:new
    description: Save session snapshot on /new command
    requires:
      bins:
        - node
      env:
        - API_KEY
    enabled: true
    priority: 100
    ---

    Args:
        hook_md: HOOK.md 文件路径

    Returns:
        钩子元数据，如果解析失败则返回 None
    """
    try:
        content = hook_md.read_text(encoding="utf-8")

        # 提取 frontmatter
        if not content.startswith("---"):
            logger.warning(f"HOOK.md missing frontmatter: {hook_md}")
            return None

        parts = content.split("---", 2)
        if len(parts) < 3:
            logger.warning(f"Invalid frontmatter format: {hook_md}")
            return None

        frontmatter_text = parts[1].strip()
        frontmatter_data = yaml.safe_load(frontmatter_text)

        # 解析 requires
        requires_data = frontmatter_data.get("requires", {})
        requires = HookRequirements(
            bins=requires_data.get("bins", []),
            env=requires_data.get("env", []),
            python_packages=requires_data.get("python_packages", []),
        )

        metadata = HookMetadata(
            name=frontmatter_data["name"],
            emoji=frontmatter_data.get("emoji", "🔌"),
            events=frontmatter_data.get("events", []),
            description=frontmatter_data.get("description", ""),
            requires=requires,
            enabled=frontmatter_data.get("enabled", True),
            priority=frontmatter_data.get("priority", 100),
        )

        return metadata

    except Exception as e:
        logger.error(f"Failed to parse HOOK.md {hook_md}: {e}")
        return None


def load_hook_handler(handler_py: Path) -> Optional[HookHandler]:
    """
    加载 handler.py 中的 HookHandler 函数

    handler.py 必须导出一个名为 'handler' 的异步函数:
    async def handler(event: InternalHookEvent) -> None:
        ...

    Args:
        handler_py: handler.py 文件路径

    Returns:
        钩子处理器函数，如果加载失败则返回 None
    """
    try:
        # 动态导入模块
        spec = importlib.util.spec_from_file_location("hook_handler", handler_py)
        if not spec or not spec.loader:
            logger.error(f"Failed to load spec for {handler_py}")
            return None

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # 获取 handler 函数
        if not hasattr(module, "handler"):
            logger.error(f"handler.py missing 'handler' function: {handler_py}")
            return None

        handler = getattr(module, "handler")

        # 验证是否为异步函数
        if not callable(handler):
            logger.error(f"'handler' is not callable: {handler_py}")
            return None

        return handler

    except Exception as e:
        logger.error(f"Failed to load handler.py {handler_py}: {e}")
        return None


def check_hook_requirements(requires: HookRequirements) -> bool:
    """
    检查钩子依赖是否满足

    Args:
        requires: 钩子依赖要求

    Returns:
        是否满足所有依赖
    """
    # 检查二进制文件
    for bin_name in requires.bins:
        if not _check_binary_exists(bin_name):
            logger.warning(f"Required binary not found: {bin_name}")
            return False

    # 检查环境变量
    for env_var in requires.env:
        if env_var not in os.environ:
            logger.warning(f"Required env var not set: {env_var}")
            return False

    # 检查 Python 包
    for package in requires.python_packages:
        if not _check_python_package(package):
            logger.warning(f"Required Python package not found: {package}")
            return False

    return True


def _check_binary_exists(bin_name: str) -> bool:
    """检查二进制文件是否存在于 PATH"""
    import shutil

    return shutil.which(bin_name) is not None


def _check_python_package(package_name: str) -> bool:
    """检查 Python 包是否已安装"""
    try:
        importlib.import_module(package_name)
        return True
    except ImportError:
        return False
