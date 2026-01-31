#!/usr/bin/env python3
"""性能测试运行脚本

运行所有性能测试并生成报告
"""

import sys
import subprocess
from pathlib import Path
from datetime import datetime

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))
sys.path.insert(0, str(project_root))

from tests.performance.utils import (
    PerformanceReporter,
    get_system_info,
)


def run_performance_tests():
    """运行性能测试"""
    print("=" * 80)
    print("LurkBot 性能测试套件")
    print("=" * 80)
    print()

    # 获取系统信息
    print("系统信息:")
    system_info = get_system_info()
    for key, value in system_info.items():
        print(f"  {key}: {value}")
    print()

    # 运行 pytest-benchmark
    print("运行性能测试...")
    print("-" * 80)

    cmd = [
        "pytest",
        "tests/performance/",
        "--benchmark-only",
        "--benchmark-autosave",
        "--benchmark-save-data",
        "--benchmark-json=tests/performance/reports/benchmark_results.json",
        "-v",
    ]

    try:
        result = subprocess.run(cmd, check=True, capture_output=False)
        print()
        print("-" * 80)
        print("✅ 性能测试完成!")
        print()

        # 生成报告
        print("生成性能报告...")
        generate_report()

        return 0

    except subprocess.CalledProcessError as e:
        print()
        print("-" * 80)
        print(f"❌ 性能测试失败: {e}")
        return 1


def generate_report():
    """生成性能报告"""
    import json

    # 读取 benchmark 结果
    results_file = Path("tests/performance/reports/benchmark_results.json")

    if not results_file.exists():
        print("⚠️  未找到 benchmark 结果文件")
        return

    with open(results_file, "r") as f:
        data = json.load(f)

    # 提取指标
    from tests.performance.utils import PerformanceMetrics, PerformanceReport

    metrics = []
    for benchmark in data.get("benchmarks", []):
        stats = benchmark.get("stats", {})
        metric = PerformanceMetrics(
            test_name=benchmark.get("name", "unknown"),
            group=benchmark.get("group", "default"),
            min_time=stats.get("min", 0),
            max_time=stats.get("max", 0),
            mean_time=stats.get("mean", 0),
            median_time=stats.get("median", 0),
            stddev=stats.get("stddev", 0),
            iterations=stats.get("iterations", 0),
            ops_per_second=stats.get("ops", 0),
            timestamp=datetime.now().isoformat(),
        )
        metrics.append(metric)

    # 创建报告
    report = PerformanceReport(
        test_suite="LurkBot Performance Tests",
        total_tests=len(metrics),
        total_time=sum(m.mean_time * m.iterations for m in metrics),
        metrics=metrics,
        timestamp=datetime.now().isoformat(),
        environment=get_system_info(),
    )

    # 保存报告
    reporter = PerformanceReporter()
    json_file = reporter.save_report(report)
    md_file = reporter.save_markdown_report(report)

    print(f"✅ JSON 报告: {json_file}")
    print(f"✅ Markdown 报告: {md_file}")
    print()

    # 打印摘要
    print("性能测试摘要:")
    print(f"  总测试数: {report.total_tests}")
    print(f"  总耗时: {report.total_time:.2f}s")
    print()

    # 按组统计
    groups: dict[str, list[PerformanceMetrics]] = {}
    for metric in metrics:
        if metric.group not in groups:
            groups[metric.group] = []
        groups[metric.group].append(metric)

    for group, group_metrics in groups.items():
        avg_time = sum(m.mean_time for m in group_metrics) / len(group_metrics)
        print(f"  {group}: {len(group_metrics)} 个测试, 平均 {avg_time*1000:.2f}ms")


def main():
    """主函数"""
    return run_performance_tests()


if __name__ == "__main__":
    sys.exit(main())
