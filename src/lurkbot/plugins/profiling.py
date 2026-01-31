"""插件性能分析系统

提供详细的插件性能分析和监控工具。

核心功能：
1. 执行时间统计 - 记录插件执行时间
2. 资源使用监控 - 监控 CPU、内存使用
3. 性能报告生成 - 生成详细性能报告
4. 瓶颈分析 - 识别性能瓶颈
"""

import asyncio
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable

import psutil
from loguru import logger
from pydantic import BaseModel, Field


# ============================================================================
# 性能指标模型
# ============================================================================


class MetricType(str, Enum):
    """指标类型"""

    EXECUTION_TIME = "execution_time"  # 执行时间
    CPU_USAGE = "cpu_usage"  # CPU 使用率
    MEMORY_USAGE = "memory_usage"  # 内存使用
    IO_OPERATIONS = "io_operations"  # IO 操作
    NETWORK_REQUESTS = "network_requests"  # 网络请求


@dataclass
class PerformanceMetric:
    """性能指标"""

    plugin_name: str
    metric_type: MetricType
    value: float
    unit: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionProfile:
    """执行性能分析"""

    plugin_name: str
    start_time: float
    end_time: float
    execution_time: float
    cpu_percent: float
    memory_mb: float
    success: bool
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class PerformanceReport(BaseModel):
    """性能报告"""

    plugin_name: str = Field(..., description="插件名称")
    total_executions: int = Field(0, description="总执行次数")
    successful_executions: int = Field(0, description="成功执行次数")
    failed_executions: int = Field(0, description="失败执行次数")
    avg_execution_time: float = Field(0.0, description="平均执行时间（秒）")
    min_execution_time: float = Field(0.0, description="最小执行时间（秒）")
    max_execution_time: float = Field(0.0, description="最大执行时间（秒）")
    avg_cpu_percent: float = Field(0.0, description="平均 CPU 使用率（%）")
    avg_memory_mb: float = Field(0.0, description="平均内存使用（MB）")
    total_cpu_time: float = Field(0.0, description="总 CPU 时间（秒）")
    total_memory_mb: float = Field(0.0, description="总内存使用（MB）")
    generated_at: datetime = Field(default_factory=datetime.now, description="生成时间")


# ============================================================================
# 性能分析器
# ============================================================================


class PerformanceProfiler:
    """性能分析器

    负责收集和分析插件性能数据。
    """

    def __init__(self):
        """初始化性能分析器"""
        self._profiles: dict[str, list[ExecutionProfile]] = defaultdict(list)
        self._metrics: dict[str, list[PerformanceMetric]] = defaultdict(list)
        self._active_profiles: dict[str, ExecutionProfile] = {}
        self._process = psutil.Process()

    async def start_profiling(self, plugin_name: str) -> str:
        """开始性能分析

        Args:
            plugin_name: 插件名称

        Returns:
            分析会话 ID
        """
        session_id = f"{plugin_name}_{time.time()}"

        # 记录初始状态
        profile = ExecutionProfile(
            plugin_name=plugin_name,
            start_time=time.time(),
            end_time=0.0,
            execution_time=0.0,
            cpu_percent=0.0,
            memory_mb=0.0,
            success=False,
        )

        self._active_profiles[session_id] = profile
        logger.debug(f"开始性能分析: {plugin_name} (session: {session_id})")

        return session_id

    async def stop_profiling(
        self, session_id: str, success: bool = True, error: str | None = None
    ) -> ExecutionProfile:
        """停止性能分析

        Args:
            session_id: 分析会话 ID
            success: 是否成功
            error: 错误信息

        Returns:
            执行性能分析结果
        """
        if session_id not in self._active_profiles:
            raise ValueError(f"无效的会话 ID: {session_id}")

        profile = self._active_profiles[session_id]

        # 记录结束状态
        profile.end_time = time.time()
        profile.execution_time = profile.end_time - profile.start_time
        profile.success = success
        profile.error = error

        # 获取资源使用情况
        try:
            profile.cpu_percent = self._process.cpu_percent()
            profile.memory_mb = self._process.memory_info().rss / 1024 / 1024
        except Exception as e:
            logger.warning(f"获取资源使用失败: {e}")

        # 保存分析结果
        self._profiles[profile.plugin_name].append(profile)

        # 记录指标
        await self._record_metric(
            plugin_name=profile.plugin_name,
            metric_type=MetricType.EXECUTION_TIME,
            value=profile.execution_time,
            unit="seconds",
        )

        await self._record_metric(
            plugin_name=profile.plugin_name,
            metric_type=MetricType.CPU_USAGE,
            value=profile.cpu_percent,
            unit="percent",
        )

        await self._record_metric(
            plugin_name=profile.plugin_name,
            metric_type=MetricType.MEMORY_USAGE,
            value=profile.memory_mb,
            unit="MB",
        )

        # 清理活跃会话
        del self._active_profiles[session_id]

        logger.debug(
            f"停止性能分析: {profile.plugin_name} "
            f"(time: {profile.execution_time:.3f}s, "
            f"cpu: {profile.cpu_percent:.1f}%, "
            f"mem: {profile.memory_mb:.1f}MB)"
        )

        return profile

    async def profile_execution(
        self, plugin_name: str, func: Callable, *args, **kwargs
    ) -> tuple[Any, ExecutionProfile]:
        """分析函数执行性能

        Args:
            plugin_name: 插件名称
            func: 要分析的函数
            *args: 函数参数
            **kwargs: 函数关键字参数

        Returns:
            (函数返回值, 性能分析结果)
        """
        session_id = await self.start_profiling(plugin_name)

        try:
            # 执行函数
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)

            profile = await self.stop_profiling(session_id, success=True)
            return result, profile

        except Exception as e:
            profile = await self.stop_profiling(
                session_id, success=False, error=str(e)
            )
            raise

    async def _record_metric(
        self,
        plugin_name: str,
        metric_type: MetricType,
        value: float,
        unit: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """记录性能指标

        Args:
            plugin_name: 插件名称
            metric_type: 指标类型
            value: 指标值
            unit: 单位
            metadata: 元数据
        """
        metric = PerformanceMetric(
            plugin_name=plugin_name,
            metric_type=metric_type,
            value=value,
            unit=unit,
            metadata=metadata or {},
        )

        self._metrics[plugin_name].append(metric)

    def get_profiles(
        self, plugin_name: str, limit: int = 100
    ) -> list[ExecutionProfile]:
        """获取性能分析记录

        Args:
            plugin_name: 插件名称
            limit: 返回数量限制

        Returns:
            性能分析记录列表
        """
        profiles = self._profiles.get(plugin_name, [])
        return profiles[-limit:]

    def get_metrics(
        self,
        plugin_name: str,
        metric_type: MetricType | None = None,
        limit: int = 100,
    ) -> list[PerformanceMetric]:
        """获取性能指标

        Args:
            plugin_name: 插件名称
            metric_type: 指标类型（可选）
            limit: 返回数量限制

        Returns:
            性能指标列表
        """
        metrics = self._metrics.get(plugin_name, [])

        if metric_type:
            metrics = [m for m in metrics if m.metric_type == metric_type]

        return metrics[-limit:]

    def generate_report(self, plugin_name: str) -> PerformanceReport:
        """生成性能报告

        Args:
            plugin_name: 插件名称

        Returns:
            性能报告
        """
        profiles = self._profiles.get(plugin_name, [])

        if not profiles:
            return PerformanceReport(plugin_name=plugin_name)

        # 统计数据
        total_executions = len(profiles)
        successful_executions = sum(1 for p in profiles if p.success)
        failed_executions = total_executions - successful_executions

        execution_times = [p.execution_time for p in profiles]
        cpu_percents = [p.cpu_percent for p in profiles]
        memory_mbs = [p.memory_mb for p in profiles]

        return PerformanceReport(
            plugin_name=plugin_name,
            total_executions=total_executions,
            successful_executions=successful_executions,
            failed_executions=failed_executions,
            avg_execution_time=sum(execution_times) / len(execution_times),
            min_execution_time=min(execution_times),
            max_execution_time=max(execution_times),
            avg_cpu_percent=sum(cpu_percents) / len(cpu_percents),
            avg_memory_mb=sum(memory_mbs) / len(memory_mbs),
            total_cpu_time=sum(
                p.execution_time * p.cpu_percent / 100 for p in profiles
            ),
            total_memory_mb=sum(memory_mbs),
        )

    def identify_bottlenecks(
        self, plugin_name: str, threshold_percentile: float = 0.9
    ) -> dict[str, Any]:
        """识别性能瓶颈

        Args:
            plugin_name: 插件名称
            threshold_percentile: 阈值百分位（默认 90%）

        Returns:
            瓶颈分析结果
        """
        profiles = self._profiles.get(plugin_name, [])

        if not profiles:
            return {"plugin_name": plugin_name, "bottlenecks": []}

        # 计算阈值
        execution_times = sorted([p.execution_time for p in profiles])
        cpu_percents = sorted([p.cpu_percent for p in profiles])
        memory_mbs = sorted([p.memory_mb for p in profiles])

        time_threshold = execution_times[int(len(execution_times) * threshold_percentile)]
        cpu_threshold = cpu_percents[int(len(cpu_percents) * threshold_percentile)]
        memory_threshold = memory_mbs[int(len(memory_mbs) * threshold_percentile)]

        bottlenecks = []

        # 识别慢执行
        slow_executions = [p for p in profiles if p.execution_time > time_threshold]
        if slow_executions:
            bottlenecks.append(
                {
                    "type": "slow_execution",
                    "count": len(slow_executions),
                    "threshold": time_threshold,
                    "avg_time": sum(p.execution_time for p in slow_executions)
                    / len(slow_executions),
                }
            )

        # 识别高 CPU 使用
        high_cpu = [p for p in profiles if p.cpu_percent > cpu_threshold]
        if high_cpu:
            bottlenecks.append(
                {
                    "type": "high_cpu",
                    "count": len(high_cpu),
                    "threshold": cpu_threshold,
                    "avg_cpu": sum(p.cpu_percent for p in high_cpu) / len(high_cpu),
                }
            )

        # 识别高内存使用
        high_memory = [p for p in profiles if p.memory_mb > memory_threshold]
        if high_memory:
            bottlenecks.append(
                {
                    "type": "high_memory",
                    "count": len(high_memory),
                    "threshold": memory_threshold,
                    "avg_memory": sum(p.memory_mb for p in high_memory)
                    / len(high_memory),
                }
            )

        return {"plugin_name": plugin_name, "bottlenecks": bottlenecks}

    def compare_plugins(self, plugin_names: list[str]) -> dict[str, PerformanceReport]:
        """比较多个插件的性能

        Args:
            plugin_names: 插件名称列表

        Returns:
            性能报告字典
        """
        return {name: self.generate_report(name) for name in plugin_names}

    def clear_data(self, plugin_name: str | None = None) -> int:
        """清空性能数据

        Args:
            plugin_name: 插件名称（可选，不指定则清空所有）

        Returns:
            清空的记录数
        """
        if plugin_name:
            count = len(self._profiles.get(plugin_name, []))
            self._profiles.pop(plugin_name, None)
            self._metrics.pop(plugin_name, None)
            logger.info(f"清空性能数据: {plugin_name} ({count} 条)")
            return count
        else:
            count = sum(len(profiles) for profiles in self._profiles.values())
            self._profiles.clear()
            self._metrics.clear()
            logger.info(f"清空所有性能数据 ({count} 条)")
            return count


# ============================================================================
# 全局单例
# ============================================================================

_profiler: PerformanceProfiler | None = None


def get_profiler() -> PerformanceProfiler:
    """获取全局性能分析器实例

    Returns:
        PerformanceProfiler 实例
    """
    global _profiler
    if _profiler is None:
        _profiler = PerformanceProfiler()
    return _profiler


def reset_profiler() -> None:
    """重置全局性能分析器（主要用于测试）"""
    global _profiler
    _profiler = None
