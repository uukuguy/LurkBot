"""性能测试配置和工具

提供性能测试的配置、工具函数和报告生成
"""

import json
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class PerformanceMetrics:
    """性能指标"""

    test_name: str
    group: str
    min_time: float  # 最小执行时间 (秒)
    max_time: float  # 最大执行时间 (秒)
    mean_time: float  # 平均执行时间 (秒)
    median_time: float  # 中位数执行时间 (秒)
    stddev: float  # 标准差
    iterations: int  # 迭代次数
    ops_per_second: float  # 每秒操作数
    timestamp: str  # 时间戳


@dataclass
class PerformanceReport:
    """性能报告"""

    test_suite: str
    total_tests: int
    total_time: float
    metrics: list[PerformanceMetrics]
    timestamp: str
    environment: dict[str, Any]


class PerformanceReporter:
    """性能报告生成器"""

    def __init__(self, output_dir: str | Path = "tests/performance/reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def save_report(self, report: PerformanceReport, filename: str | None = None):
        """保存性能报告"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"performance_report_{timestamp}.json"

        filepath = self.output_dir / filename
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(asdict(report), f, indent=2, ensure_ascii=False)

        print(f"Performance report saved to: {filepath}")
        return filepath

    def generate_markdown_report(self, report: PerformanceReport) -> str:
        """生成 Markdown 格式的性能报告"""
        lines = [
            f"# {report.test_suite} - 性能测试报告",
            "",
            f"**生成时间**: {report.timestamp}",
            f"**总测试数**: {report.total_tests}",
            f"**总耗时**: {report.total_time:.2f}s",
            "",
            "## 环境信息",
            "",
        ]

        for key, value in report.environment.items():
            lines.append(f"- **{key}**: {value}")

        lines.extend(["", "## 性能指标", ""])

        # 按组分组
        groups: dict[str, list[PerformanceMetrics]] = {}
        for metric in report.metrics:
            if metric.group not in groups:
                groups[metric.group] = []
            groups[metric.group].append(metric)

        for group, metrics in groups.items():
            lines.extend([f"### {group}", ""])
            lines.append("| 测试名称 | 平均时间 | 中位数 | 最小值 | 最大值 | OPS | 迭代次数 |")
            lines.append("|---------|---------|--------|--------|--------|-----|----------|")

            for metric in metrics:
                lines.append(
                    f"| {metric.test_name} | "
                    f"{metric.mean_time*1000:.2f}ms | "
                    f"{metric.median_time*1000:.2f}ms | "
                    f"{metric.min_time*1000:.2f}ms | "
                    f"{metric.max_time*1000:.2f}ms | "
                    f"{metric.ops_per_second:.0f} | "
                    f"{metric.iterations} |"
                )

            lines.append("")

        return "\n".join(lines)

    def save_markdown_report(
        self, report: PerformanceReport, filename: str | None = None
    ):
        """保存 Markdown 格式的性能报告"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"performance_report_{timestamp}.md"

        filepath = self.output_dir / filename
        content = self.generate_markdown_report(report)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        print(f"Markdown report saved to: {filepath}")
        return filepath


def get_system_info() -> dict[str, Any]:
    """获取系统信息"""
    import platform
    import sys

    try:
        import psutil

        cpu_count = psutil.cpu_count()
        memory_total = psutil.virtual_memory().total / (1024**3)  # GB
    except ImportError:
        cpu_count = "N/A"
        memory_total = "N/A"

    return {
        "python_version": sys.version,
        "platform": platform.platform(),
        "processor": platform.processor(),
        "cpu_count": cpu_count,
        "memory_total_gb": f"{memory_total:.2f}" if isinstance(memory_total, float) else memory_total,
    }


class PerformanceTimer:
    """性能计时器"""

    def __init__(self):
        self.start_time = None
        self.end_time = None

    def __enter__(self):
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, *args):
        self.end_time = time.perf_counter()

    @property
    def elapsed(self) -> float:
        """获取经过的时间 (秒)"""
        if self.start_time is None:
            return 0.0
        if self.end_time is None:
            return time.perf_counter() - self.start_time
        return self.end_time - self.start_time


def format_time(seconds: float) -> str:
    """格式化时间"""
    if seconds < 0.001:
        return f"{seconds * 1_000_000:.2f}µs"
    elif seconds < 1:
        return f"{seconds * 1000:.2f}ms"
    else:
        return f"{seconds:.2f}s"


def format_ops(ops: float) -> str:
    """格式化操作数"""
    if ops >= 1_000_000:
        return f"{ops / 1_000_000:.2f}M ops/s"
    elif ops >= 1_000:
        return f"{ops / 1_000:.2f}K ops/s"
    else:
        return f"{ops:.2f} ops/s"
