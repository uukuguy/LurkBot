"""
Routing Session Key - 会话键构建

对标 MoltBot src/routing/session-key.ts
"""


def build_session_key(
    agent_id: str,
    channel: str,
    session_type: str,
    peer_id: str | None = None,
    guild_id: str | None = None,
    channel_id: str | None = None,
    thread_id: str | None = None,
    topic_id: str | None = None,
) -> str:
    """
    构建 Session Key

    对标 MoltBot buildSessionKey()

    格式示例:
    - 主会话 → "agent:main:main"
    - DM → "agent:main:dm:telegram:123456"
    - Telegram 群组 → "agent:main:group:telegram:-1001234567890"
    - Discord Guild → "agent:main:guild:discord:123456:channel:789"
    - Slack 线程 → "agent:main:thread:slack:C123:thread:1234567890.0001"
    - Telegram Topic → "agent:main:topic:telegram:-100123:topic:42"
    """
    parts = [f"agent:{agent_id}"]

    if session_type == "main":
        parts.append("main")
    elif session_type == "dm":
        parts.extend(["dm", channel, peer_id])
    elif session_type == "group":
        parts.extend(["group", channel, peer_id])
    elif session_type == "guild":
        parts.extend(["guild", channel, guild_id])
        if channel_id:
            parts.extend(["channel", channel_id])
    elif session_type == "thread":
        parts.extend(["thread", channel, channel_id, "thread", thread_id])
    elif session_type == "topic":
        parts.extend(["topic", channel, peer_id, "topic", topic_id])

    return ":".join(filter(None, parts))
