"""Voice Wake types.

对标 MoltBot `src/infra/voicewake.ts`
"""

from dataclasses import dataclass, field


@dataclass
class VoiceWakeConfig:
    """语音唤醒配置"""

    # 触发词列表
    triggers: list[str] = field(default_factory=list)

    # 更新时间戳（毫秒）
    updated_at_ms: int = 0


# 默认触发词
DEFAULT_VOICE_WAKE_TRIGGERS = ["lurkbot", "claude", "computer"]
