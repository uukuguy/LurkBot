"""
Hooks 扩展系统 - 注册表

管理钩子的注册、查询和触发。
"""

import fnmatch
from typing import Optional
from loguru import logger

from .types import InternalHookEvent, HookHandler, HookPackage


class HookRegistry:
    """钩子注册表"""

    def __init__(self):
        self._hooks: dict[str, list[HookPackage]] = {}

    def register(
        self,
        event_pattern: str,
        package: HookPackage,
    ) -> None:
        """
        注册钩子到事件模式

        Args:
            event_pattern: 事件模式，如 "command:new", "session:*", "agent:bootstrap"
            package: 钩子包
        """
        if event_pattern not in self._hooks:
            self._hooks[event_pattern] = []

        # 按优先级插入 (priority 越小越靠前)
        packages = self._hooks[event_pattern]
        insert_pos = 0
        for i, pkg in enumerate(packages):
            if package.metadata.priority < pkg.metadata.priority:
                insert_pos = i
                break
            insert_pos = i + 1

        packages.insert(insert_pos, package)
        logger.debug(
            f"Registered hook '{package.metadata.name}' for pattern '{event_pattern}' "
            f"(priority={package.metadata.priority})"
        )

    def unregister(self, event_pattern: str, hook_name: str) -> bool:
        """
        取消注册钩子

        Args:
            event_pattern: 事件模式
            hook_name: 钩子名称

        Returns:
            是否成功取消注册
        """
        if event_pattern not in self._hooks:
            return False

        packages = self._hooks[event_pattern]
        for i, pkg in enumerate(packages):
            if pkg.metadata.name == hook_name:
                packages.pop(i)
                logger.debug(
                    f"Unregistered hook '{hook_name}' from pattern '{event_pattern}'"
                )
                return True

        return False

    def get_handlers_for_event(self, event: InternalHookEvent) -> list[HookPackage]:
        """
        获取匹配事件的所有钩子处理器

        Args:
            event: 钩子事件

        Returns:
            匹配的钩子包列表 (已按优先级排序)
        """
        event_key = f"{event.type}:{event.action}"
        matched_packages: list[HookPackage] = []

        for pattern, packages in self._hooks.items():
            if self._match_event_pattern(event_key, pattern):
                for pkg in packages:
                    if pkg.metadata.enabled:
                        matched_packages.append(pkg)

        # 按优先级排序
        matched_packages.sort(key=lambda p: p.metadata.priority)
        return matched_packages

    def _match_event_pattern(self, event_key: str, pattern: str) -> bool:
        """
        匹配事件模式

        支持通配符:
        - "command:*" 匹配所有 command 事件
        - "session:*" 匹配所有 session 事件
        - "command:new" 精确匹配

        Args:
            event_key: 事件键，如 "command:new"
            pattern: 模式，如 "command:*"

        Returns:
            是否匹配
        """
        return fnmatch.fnmatch(event_key, pattern)

    async def trigger(self, event: InternalHookEvent) -> None:
        """
        触发事件，执行所有匹配的钩子处理器

        Args:
            event: 钩子事件
        """
        packages = self.get_handlers_for_event(event)

        if not packages:
            logger.debug(f"No hooks registered for event '{event.type}:{event.action}'")
            return

        logger.info(
            f"Triggering {len(packages)} hook(s) for event '{event.type}:{event.action}'"
        )

        for pkg in packages:
            try:
                logger.debug(f"Executing hook '{pkg.metadata.name}'")
                await pkg.handler(event)
            except Exception as e:
                logger.error(
                    f"Hook '{pkg.metadata.name}' failed: {e}",
                    exc_info=True,
                )
                event.messages.append(f"❌ Hook '{pkg.metadata.name}' failed: {e}")

    def list_hooks(self, event_pattern: Optional[str] = None) -> list[HookPackage]:
        """
        列出所有注册的钩子

        Args:
            event_pattern: 可选的事件模式过滤

        Returns:
            钩子包列表
        """
        if event_pattern:
            return self._hooks.get(event_pattern, [])

        all_packages: list[HookPackage] = []
        for packages in self._hooks.values():
            all_packages.extend(packages)

        return all_packages


# 全局注册表实例
_global_registry = HookRegistry()


def register_internal_hook(event_pattern: str, package: HookPackage) -> None:
    """
    注册钩子到全局注册表

    Args:
        event_pattern: 事件模式
        package: 钩子包
    """
    _global_registry.register(event_pattern, package)


async def trigger_internal_hook(event: InternalHookEvent) -> None:
    """
    触发钩子事件

    Args:
        event: 钩子事件
    """
    await _global_registry.trigger(event)


def get_global_registry() -> HookRegistry:
    """获取全局钩子注册表"""
    return _global_registry
