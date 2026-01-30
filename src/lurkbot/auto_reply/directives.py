"""
Auto-Reply Directives - 指令提取系统

对标 MoltBot src/auto-reply/directives.ts
"""

import re
from dataclasses import dataclass
from typing import Literal, Callable


# 思维级别
ThinkLevel = Literal["off", "low", "medium", "high"]

# 冗余级别
VerboseLevel = Literal["off", "low", "high"]

# 推理级别
ReasoningLevel = Literal["off", "on", "stream"]

# 提权级别
ElevatedLevel = Literal["off", "ask", "on", "full"]


@dataclass
class DirectiveResult:
    """指令提取结果"""
    cleaned: str
    level: str | None
    has_directive: bool


def extract_level_directive(
    body: str,
    names: list[str],
    normalize_fn: Callable[[str], str],
) -> DirectiveResult:
    """
    通用指令提取函数

    对标 MoltBot extractLevelDirective()

    匹配模式: /directive_name [: | space] optional_level
    支持: /think, /think:medium, /think medium
    """
    # 匹配 /directive 或 /directive:level
    # 只匹配指令部分，不匹配后续文本
    pattern = rf"/({'|'.join(names)})(?::(\w+))?\b"
    match = re.search(pattern, body, re.IGNORECASE)

    if not match:
        return DirectiveResult(cleaned=body, level=None, has_directive=False)

    raw_level = match.group(2)
    level = normalize_fn(raw_level) if raw_level else normalize_fn("default")
    # 移除匹配的指令，保留剩余文本
    cleaned = body[:match.start()] + body[match.end():].strip()

    return DirectiveResult(cleaned=cleaned, level=level, has_directive=True)


def extract_think_directive(body: str) -> DirectiveResult:
    """
    提取思维级别指令

    对标 MoltBot extractThinkDirective()

    用法: /think, /think:high, /t:medium
    """
    def normalize(level: str) -> ThinkLevel:
        mapping = {
            "off": "off", "0": "off", "none": "off",
            "low": "low", "1": "low", "l": "low",
            "medium": "medium", "2": "medium", "m": "medium", "default": "medium",
            "high": "high", "3": "high", "h": "high",
        }
        return mapping.get(level.lower(), "medium")

    return extract_level_directive(body, ["think", "t"], normalize)


def extract_verbose_directive(body: str) -> DirectiveResult:
    """
    提取冗余级别指令

    对标 MoltBot extractVerboseDirective()

    用法: /verbose, /verbose:high, /v:low
    """
    def normalize(level: str) -> VerboseLevel:
        mapping = {
            "off": "off", "0": "off", "none": "off", "default": "off",
            "low": "low", "1": "low", "l": "low",
            "high": "high", "2": "high", "h": "high",
        }
        return mapping.get(level.lower(), "off")

    return extract_level_directive(body, ["verbose", "v"], normalize)


def extract_reasoning_directive(body: str) -> DirectiveResult:
    """
    提取推理级别指令

    对标 MoltBot extractReasoningDirective()

    用法: /reasoning, /reasoning:stream
    """
    def normalize(level: str) -> ReasoningLevel:
        mapping = {
            "off": "off", "0": "off", "none": "off",
            "on": "on", "1": "on", "default": "on",
            "stream": "stream", "2": "stream", "s": "stream",
        }
        return mapping.get(level.lower(), "on")

    return extract_level_directive(body, ["reasoning", "r"], normalize)


def extract_elevated_directive(body: str) -> DirectiveResult:
    """
    提取提权级别指令

    对标 MoltBot extractElevatedDirective()

    用法: /elevated, /elevated:on, /elevated:full
    """
    def normalize(level: str) -> ElevatedLevel:
        mapping = {
            "off": "off", "0": "off", "none": "off",
            "ask": "ask", "1": "ask", "default": "ask",
            "on": "on", "2": "on",
            "full": "full", "3": "full", "f": "full",
        }
        return mapping.get(level.lower(), "ask")

    return extract_level_directive(body, ["elevated", "e"], normalize)
