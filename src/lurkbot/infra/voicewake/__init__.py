"""Voice Wake Management.

管理语音唤醒触发词。

对标 MoltBot `src/infra/voicewake.ts`
"""

import asyncio
import json
import os
import time
from pathlib import Path
from typing import Any

from .types import DEFAULT_VOICE_WAKE_TRIGGERS, VoiceWakeConfig

__all__ = [
    "VoiceWakeConfig",
    "DEFAULT_VOICE_WAKE_TRIGGERS",
    "VoiceWakeManager",
    "voice_wake_manager",
    "get_voice_wake_triggers",
    "set_voice_wake_triggers",
    "load_voice_wake_config",
]

# 默认路径
DEFAULT_VOICEWAKE_FILE = Path.home() / ".lurkbot" / "settings" / "voicewake.json"


def _get_ms_timestamp() -> int:
    """获取毫秒时间戳。"""
    return int(time.time() * 1000)


def _sanitize_triggers(triggers: list[str]) -> list[str]:
    """
    清理触发词列表。

    - 去除空白
    - 过滤空字符串
    - 空列表返回默认值
    """
    result = [t.strip() for t in triggers if t and t.strip()]
    if not result:
        return list(DEFAULT_VOICE_WAKE_TRIGGERS)
    return result


class VoiceWakeManager:
    """
    语音唤醒管理器。

    管理语音唤醒触发词的配置。

    对标 MoltBot voicewake.ts
    """

    def __init__(self, file_path: Path | None = None) -> None:
        self._file_path = file_path or DEFAULT_VOICEWAKE_FILE
        self._lock = asyncio.Lock()
        self._config: VoiceWakeConfig | None = None

    async def _ensure_dir(self) -> None:
        """确保目录存在。"""
        self._file_path.parent.mkdir(parents=True, exist_ok=True)

    async def load(self, *, force: bool = False) -> VoiceWakeConfig:
        """
        加载配置。

        Args:
            force: 是否强制重新加载

        Returns:
            配置
        """
        if not force and self._config is not None:
            return self._config

        async with self._lock:
            if not self._file_path.exists():
                # 返回默认配置
                self._config = VoiceWakeConfig(
                    triggers=list(DEFAULT_VOICE_WAKE_TRIGGERS),
                    updated_at_ms=_get_ms_timestamp(),
                )
                return self._config

            try:
                raw = json.loads(self._file_path.read_text())
                self._config = VoiceWakeConfig(
                    triggers=raw.get("triggers", list(DEFAULT_VOICE_WAKE_TRIGGERS)),
                    updated_at_ms=raw.get("updatedAtMs", 0),
                )
            except (json.JSONDecodeError, KeyError):
                self._config = VoiceWakeConfig(
                    triggers=list(DEFAULT_VOICE_WAKE_TRIGGERS),
                    updated_at_ms=_get_ms_timestamp(),
                )

            return self._config

    async def _save_internal(self) -> None:
        """保存配置（内部使用，需要持有锁）。"""
        if not self._config:
            return

        await self._ensure_dir()

        raw: dict[str, Any] = {
            "triggers": self._config.triggers,
            "updatedAtMs": self._config.updated_at_ms,
        }

        # 原子写入
        temp_file = self._file_path.with_suffix(".tmp")
        temp_file.write_text(json.dumps(raw, indent=2))
        os.chmod(temp_file, 0o600)
        temp_file.rename(self._file_path)

    async def save(self) -> None:
        """保存配置。"""
        if not self._config:
            return

        async with self._lock:
            await self._save_internal()

    async def get_triggers(self) -> list[str]:
        """
        获取触发词列表。

        Returns:
            触发词列表
        """
        config = await self.load()
        return list(config.triggers)

    async def set_triggers(self, triggers: list[str]) -> list[str]:
        """
        设置触发词列表。

        Args:
            triggers: 新的触发词列表

        Returns:
            清理后的触发词列表
        """
        await self.load()

        async with self._lock:
            self._config.triggers = _sanitize_triggers(triggers)
            self._config.updated_at_ms = _get_ms_timestamp()
            await self._save_internal()

        return list(self._config.triggers)

    async def add_trigger(self, trigger: str) -> bool:
        """
        添加触发词。

        Args:
            trigger: 触发词

        Returns:
            是否添加成功（已存在则返回 False）
        """
        await self.load()

        trigger = trigger.strip()
        if not trigger:
            return False

        async with self._lock:
            if trigger.lower() in [t.lower() for t in self._config.triggers]:
                return False

            self._config.triggers.append(trigger)
            self._config.updated_at_ms = _get_ms_timestamp()
            await self._save_internal()

        return True

    async def remove_trigger(self, trigger: str) -> bool:
        """
        移除触发词。

        Args:
            trigger: 触发词

        Returns:
            是否移除成功
        """
        await self.load()

        trigger = trigger.strip().lower()

        async with self._lock:
            original_len = len(self._config.triggers)
            self._config.triggers = [
                t for t in self._config.triggers
                if t.lower() != trigger
            ]

            if len(self._config.triggers) < original_len:
                # 如果删光了，恢复默认
                if not self._config.triggers:
                    self._config.triggers = list(DEFAULT_VOICE_WAKE_TRIGGERS)
                self._config.updated_at_ms = _get_ms_timestamp()
                await self._save_internal()
                return True

            return False

    async def reset_to_default(self) -> list[str]:
        """
        重置为默认触发词。

        Returns:
            默认触发词列表
        """
        await self.load()

        async with self._lock:
            self._config.triggers = list(DEFAULT_VOICE_WAKE_TRIGGERS)
            self._config.updated_at_ms = _get_ms_timestamp()
            await self._save_internal()

        return list(self._config.triggers)

    def is_trigger(self, text: str) -> bool:
        """
        检查文本是否包含触发词。

        Args:
            text: 要检查的文本

        Returns:
            是否包含触发词
        """
        if not self._config:
            # 未加载时使用默认
            triggers = DEFAULT_VOICE_WAKE_TRIGGERS
        else:
            triggers = self._config.triggers

        text_lower = text.lower()
        for trigger in triggers:
            if trigger.lower() in text_lower:
                return True

        return False


# 全局实例
voice_wake_manager = VoiceWakeManager()


# 便捷函数
async def get_voice_wake_triggers() -> list[str]:
    """获取触发词列表。"""
    return await voice_wake_manager.get_triggers()


async def set_voice_wake_triggers(triggers: list[str]) -> list[str]:
    """设置触发词列表。"""
    return await voice_wake_manager.set_triggers(triggers)


async def load_voice_wake_config(base_dir: Path | None = None) -> VoiceWakeConfig:
    """
    加载语音唤醒配置。

    Args:
        base_dir: 基础目录（可选）

    Returns:
        配置
    """
    if base_dir:
        manager = VoiceWakeManager(base_dir / "settings" / "voicewake.json")
        return await manager.load()
    return await voice_wake_manager.load()
