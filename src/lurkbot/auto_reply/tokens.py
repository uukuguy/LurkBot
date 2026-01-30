"""
Auto-Reply Tokens - 特殊回复令牌

对标 MoltBot src/auto-reply/tokens.ts
"""

# 特殊令牌常量
SILENT_REPLY_TOKEN = "NO_REPLY"
HEARTBEAT_TOKEN = "HEARTBEAT_OK"


def is_silent_reply_text(text: str | None) -> bool:
    """
    检测静默回复

    用于避免重复回复（已通过 message 工具发送）

    匹配模式:
    - "/NO_REPLY" 开头
    - "NO_REPLY" 结尾

    对标 MoltBot isSilentReplyText()
    """
    if not text:
        return False

    stripped = text.strip()
    return (
        stripped.endswith(SILENT_REPLY_TOKEN)
        or stripped.startswith(f"/{SILENT_REPLY_TOKEN}")
    )


def is_heartbeat_ok(text: str | None) -> bool:
    """
    检测心跳确认

    用于 Heartbeat 系统的响应检测

    对标 MoltBot isHeartbeatOk()
    """
    if not text:
        return False

    return HEARTBEAT_TOKEN in text


def strip_silent_token(text: str) -> str:
    """
    移除静默令牌

    用于清理包含 NO_REPLY 的文本
    """
    if not text:
        return text

    # 移除 /NO_REPLY 前缀
    if text.startswith(f"/{SILENT_REPLY_TOKEN}"):
        text = text[len(f"/{SILENT_REPLY_TOKEN}"):].strip()

    # 移除 NO_REPLY 后缀
    if text.endswith(SILENT_REPLY_TOKEN):
        text = text[:-len(SILENT_REPLY_TOKEN)].strip()

    return text


def strip_heartbeat_token(text: str) -> str:
    """
    移除心跳令牌

    用于清理包含 HEARTBEAT_OK 的文本
    """
    if not text:
        return text

    return text.replace(HEARTBEAT_TOKEN, "").strip()
