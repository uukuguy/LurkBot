"""
高性能 JSON 工具模块

使用 orjson 提供比标准 json 库快 2-3 倍的性能。
提供兼容层处理 bytes/str 转换。
"""

from typing import Any

import orjson


def dumps(obj: Any, *, indent: bool = False, sort_keys: bool = False) -> str:
    """
    将 Python 对象序列化为 JSON 字符串

    Args:
        obj: 要序列化的对象
        indent: 是否格式化输出（2 空格缩进）
        sort_keys: 是否排序字典键

    Returns:
        JSON 字符串

    Note:
        使用 orjson 实现，比标准 json.dumps() 快 2-3 倍
    """
    options = 0
    if indent:
        options |= orjson.OPT_INDENT_2
    if sort_keys:
        options |= orjson.OPT_SORT_KEYS

    # orjson.dumps() 返回 bytes，需要解码为 str
    return orjson.dumps(obj, option=options).decode("utf-8")


def dumps_bytes(obj: Any, *, indent: bool = False, sort_keys: bool = False) -> bytes:
    """
    将 Python 对象序列化为 JSON bytes

    Args:
        obj: 要序列化的对象
        indent: 是否格式化输出（2 空格缩进）
        sort_keys: 是否排序字典键

    Returns:
        JSON bytes

    Note:
        直接返回 bytes，避免解码开销，适用于网络传输
    """
    options = 0
    if indent:
        options |= orjson.OPT_INDENT_2
    if sort_keys:
        options |= orjson.OPT_SORT_KEYS

    return orjson.dumps(obj, option=options)


def loads(s: str | bytes) -> Any:
    """
    将 JSON 字符串或 bytes 反序列化为 Python 对象

    Args:
        s: JSON 字符串或 bytes

    Returns:
        Python 对象

    Note:
        使用 orjson 实现，比标准 json.loads() 快 2-3 倍
    """
    return orjson.loads(s)


# 兼容标准 json 库的异常
JSONDecodeError = orjson.JSONDecodeError
