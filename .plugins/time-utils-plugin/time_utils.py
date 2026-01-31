"""Time utilities plugin for LurkBot.

This plugin provides time-related utility functions.
"""

import time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from lurkbot.logging import get_logger
from lurkbot.plugins.models import (
    PluginExecutionContext,
    PluginExecutionResult,
)

logger = get_logger("time-utils-plugin")


class TimeUtilsPlugin:
    """时间工具插件

    提供时间相关的工具函数，包括：
    - 多时区时间查询
    - 时间格式转换
    - 时间差计算

    示例:
        >>> plugin = TimeUtilsPlugin()
        >>> context = PluginExecutionContext(
        ...     user_id="user123",
        ...     channel_id="channel456",
        ...     session_id="session789",
        ...     input_data={"query": "现在几点了？"},
        ...     parameters={"timezone": "Asia/Shanghai"},
        ... )
        >>> result = await plugin.execute(context)
        >>> print(result.data)
        {'timezone': 'Asia/Shanghai', 'current_time': '2026-01-31 20:00:00', ...}
    """

    # 常用时区映射
    TIMEZONE_MAP = {
        "北京": "Asia/Shanghai",
        "上海": "Asia/Shanghai",
        "东京": "Asia/Tokyo",
        "首尔": "Asia/Seoul",
        "新加坡": "Asia/Singapore",
        "香港": "Asia/Hong_Kong",
        "台北": "Asia/Taipei",
        "纽约": "America/New_York",
        "洛杉矶": "America/Los_Angeles",
        "伦敦": "Europe/London",
        "巴黎": "Europe/Paris",
        "悉尼": "Australia/Sydney",
    }

    def __init__(self):
        """初始化时间工具插件"""
        self.default_timezone = "Asia/Shanghai"

    async def execute(
        self, context: PluginExecutionContext
    ) -> PluginExecutionResult:
        """执行时间工具功能

        Args:
            context: 插件执行上下文

        Returns:
            PluginExecutionResult: 包含时间信息的执行结果
        """
        start_time = time.time()

        try:
            # 获取时区参数
            timezone_str = context.parameters.get("timezone", self.default_timezone)

            # 尝试从查询中提取时区
            query = context.input_data.get("query", "")
            extracted_tz = self._extract_timezone_from_query(query)
            if extracted_tz:
                timezone_str = extracted_tz

            logger.info(f"查询时区时间: {timezone_str}")

            # 获取时间信息
            time_info = self._get_time_info(timezone_str)

            execution_time = time.time() - start_time
            return PluginExecutionResult(
                success=True,
                result=self._format_time_text(time_info),
                error=None,
                execution_time=execution_time,
                metadata={"timezone": timezone_str, "data": time_info},
            )

        except Exception as e:
            logger.error(f"时间查询异常: {e}")
            execution_time = time.time() - start_time
            return PluginExecutionResult(
                success=False,
                result=None,
                error=str(e),
                execution_time=execution_time,
            )

    def _get_time_info(self, timezone_str: str) -> dict:
        """获取指定时区的时间信息

        Args:
            timezone_str: 时区字符串（如 "Asia/Shanghai"）

        Returns:
            dict: 时间信息字典
        """
        try:
            tz = ZoneInfo(timezone_str)
        except Exception:
            # 如果时区无效，使用默认时区
            logger.warning(f"无效的时区: {timezone_str}，使用默认时区")
            tz = ZoneInfo(self.default_timezone)
            timezone_str = self.default_timezone

        now = datetime.now(tz)
        utc_now = datetime.now(timezone.utc)

        # 计算与 UTC 的时差
        offset = now.utcoffset()
        offset_hours = offset.total_seconds() / 3600 if offset else 0

        time_info = {
            "timezone": timezone_str,
            "current_time": now.strftime("%Y-%m-%d %H:%M:%S"),
            "current_date": now.strftime("%Y-%m-%d"),
            "current_time_only": now.strftime("%H:%M:%S"),
            "weekday": now.strftime("%A"),
            "weekday_cn": self._get_weekday_cn(now.weekday()),
            "utc_time": utc_now.strftime("%Y-%m-%d %H:%M:%S"),
            "utc_offset": f"UTC{offset_hours:+.1f}",
            "timestamp": int(now.timestamp()),
            "iso_format": now.isoformat(),
        }

        return time_info

    def _extract_timezone_from_query(self, query: str) -> str | None:
        """从用户查询中提取时区

        Args:
            query: 用户查询文本

        Returns:
            str | None: 提取的时区字符串，如果未找到则返回 None
        """
        for city_name, tz_str in self.TIMEZONE_MAP.items():
            if city_name in query:
                return tz_str
        return None

    def _get_weekday_cn(self, weekday: int) -> str:
        """获取中文星期名称

        Args:
            weekday: 星期数（0=周一，6=周日）

        Returns:
            str: 中文星期名称
        """
        weekdays_cn = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        return weekdays_cn[weekday]

    def _format_time_text(self, time_info: dict) -> str:
        """格式化时间信息为文本

        Args:
            time_info: 时间信息字典

        Returns:
            str: 格式化的时间文本
        """
        return (
            f"{time_info['timezone']} 当前时间：\n"
            f"- 日期时间：{time_info['current_time']}\n"
            f"- 日期：{time_info['current_date']} ({time_info['weekday_cn']})\n"
            f"- 时间：{time_info['current_time_only']}\n"
            f"- UTC 时间：{time_info['utc_time']}\n"
            f"- 时区偏移：{time_info['utc_offset']}\n"
            f"- Unix 时间戳：{time_info['timestamp']}"
        )
