"""System information plugin for LurkBot.

This plugin provides system monitoring and information retrieval.
"""

import time

import psutil
from lurkbot.logging import get_logger
from lurkbot.plugins.models import (
    PluginExecutionContext,
    PluginExecutionResult,
)

logger = get_logger("system-info-plugin")


class SystemInfoPlugin:
    """系统信息插件

    提供系统监控和信息查询功能，包括：
    - CPU 使用率
    - 内存使用情况
    - 磁盘使用情况
    - 网络统计

    示例:
        >>> plugin = SystemInfoPlugin()
        >>> context = PluginExecutionContext(
        ...     user_id="user123",
        ...     channel_id="channel456",
        ...     session_id="session789",
        ...     input_data={"query": "系统状态如何？"},
        ...     parameters={},
        ... )
        >>> result = await plugin.execute(context)
        >>> print(result.data)
        {'cpu_percent': 25.5, 'memory_percent': 60.2, ...}
    """

    def __init__(self):
        """初始化系统信息插件"""
        pass

    async def execute(
        self, context: PluginExecutionContext
    ) -> PluginExecutionResult:
        """执行系统信息查询

        Args:
            context: 插件执行上下文

        Returns:
            PluginExecutionResult: 包含系统信息的执行结果
        """
        start_time = time.time()

        try:
            logger.info("查询系统信息")

            # 获取系统信息
            system_info = self._get_system_info()

            execution_time = time.time() - start_time
            return PluginExecutionResult(
                success=True,
                result=self._format_system_info_text(system_info),
                error=None,
                execution_time=execution_time,
                metadata={"data": system_info},
            )

        except Exception as e:
            logger.error(f"系统信息查询异常: {e}")
            execution_time = time.time() - start_time
            return PluginExecutionResult(
                success=False,
                result=None,
                error=str(e),
                execution_time=execution_time,
            )

    def _get_system_info(self) -> dict:
        """获取系统信息

        Returns:
            dict: 系统信息字典
        """
        # CPU 信息
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()
        cpu_freq = psutil.cpu_freq()

        # 内存信息
        memory = psutil.virtual_memory()

        # 磁盘信息
        disk = psutil.disk_usage("/")

        # 网络信息
        net_io = psutil.net_io_counters()

        system_info = {
            "cpu": {
                "percent": cpu_percent,
                "count": cpu_count,
                "frequency_mhz": cpu_freq.current if cpu_freq else None,
            },
            "memory": {
                "total_gb": round(memory.total / (1024**3), 2),
                "available_gb": round(memory.available / (1024**3), 2),
                "used_gb": round(memory.used / (1024**3), 2),
                "percent": memory.percent,
            },
            "disk": {
                "total_gb": round(disk.total / (1024**3), 2),
                "used_gb": round(disk.used / (1024**3), 2),
                "free_gb": round(disk.free / (1024**3), 2),
                "percent": disk.percent,
            },
            "network": {
                "bytes_sent_mb": round(net_io.bytes_sent / (1024**2), 2),
                "bytes_recv_mb": round(net_io.bytes_recv / (1024**2), 2),
                "packets_sent": net_io.packets_sent,
                "packets_recv": net_io.packets_recv,
            },
        }

        return system_info

    def _format_system_info_text(self, system_info: dict) -> str:
        """格式化系统信息为文本

        Args:
            system_info: 系统信息字典

        Returns:
            str: 格式化的系统信息文本
        """
        cpu = system_info["cpu"]
        memory = system_info["memory"]
        disk = system_info["disk"]
        network = system_info["network"]

        text = "系统信息：\n\n"

        # CPU 信息
        text += f"CPU:\n"
        text += f"- 使用率：{cpu['percent']}%\n"
        text += f"- 核心数：{cpu['count']}\n"
        if cpu["frequency_mhz"]:
            text += f"- 频率：{cpu['frequency_mhz']:.0f} MHz\n"

        # 内存信息
        text += f"\n内存:\n"
        text += f"- 总量：{memory['total_gb']} GB\n"
        text += f"- 已用：{memory['used_gb']} GB ({memory['percent']}%)\n"
        text += f"- 可用：{memory['available_gb']} GB\n"

        # 磁盘信息
        text += f"\n磁盘:\n"
        text += f"- 总量：{disk['total_gb']} GB\n"
        text += f"- 已用：{disk['used_gb']} GB ({disk['percent']}%)\n"
        text += f"- 可用：{disk['free_gb']} GB\n"

        # 网络信息
        text += f"\n网络:\n"
        text += f"- 发送：{network['bytes_sent_mb']} MB ({network['packets_sent']} 包)\n"
        text += f"- 接收：{network['bytes_recv_mb']} MB ({network['packets_recv']} 包)"

        return text
