"""Performance tests for monitoring system."""

import asyncio
import time

import pytest

from lurkbot.monitoring import MetricsCollector, PrometheusExporter


class TestMonitoringPerformance:
    """Performance tests for monitoring system."""

    def test_collection_overhead(self, benchmark):
        """Test metrics collection overhead."""
        collector = MetricsCollector()

        def collect_metrics():
            return collector.collect()

        result = benchmark(collect_metrics)
        assert result is not None

        # Collection should be fast (< 10ms)
        assert benchmark.stats["mean"] < 0.01

    def test_record_request_overhead(self, benchmark):
        """Test request recording overhead."""
        collector = MetricsCollector()

        def record_request():
            collector.record_request(latency_ms=50.0, is_error=False)

        benchmark(record_request)

        # Recording should be very fast (< 1ms)
        assert benchmark.stats["mean"] < 0.001

    def test_get_stats_overhead(self, benchmark):
        """Test statistics calculation overhead."""
        collector = MetricsCollector()

        # Collect some metrics
        for _ in range(100):
            collector.collect()

        def get_stats():
            return collector.get_stats()

        result = benchmark(get_stats)
        assert result is not None

        # Stats calculation should be fast (< 5ms)
        assert benchmark.stats["mean"] < 0.005

    def test_get_history_overhead(self, benchmark):
        """Test history retrieval overhead."""
        collector = MetricsCollector()

        # Collect some metrics
        for _ in range(100):
            collector.collect()

        def get_history():
            return collector.get_history(limit=50)

        result = benchmark(get_history)
        assert len(result) == 50

        # History retrieval should be fast (< 1ms)
        assert benchmark.stats["mean"] < 0.001

    def test_prometheus_collection_overhead(self, benchmark):
        """Test Prometheus metrics collection overhead."""
        collector = MetricsCollector()
        collector.collect()
        collector.record_request(50.0)

        exporter = PrometheusExporter(collector, port=9091)

        def collect_prometheus_metrics():
            return list(exporter.system_collector.collect())

        result = benchmark(collect_prometheus_metrics)
        assert len(result) > 0

        # Prometheus collection should be fast (< 5ms)
        assert benchmark.stats["mean"] < 0.005

    def test_concurrent_collection_overhead(self, benchmark):
        """Test concurrent metrics collection overhead."""
        collector = MetricsCollector()

        def concurrent_operations():
            # Simulate concurrent requests (synchronous version)
            for _ in range(10):
                collector.record_request(50.0, is_error=False)

            # Collect metrics
            collector.collect()

        # Run benchmark
        result = benchmark.pedantic(
            concurrent_operations,
            rounds=10,
            iterations=1,
        )

        # Concurrent operations should be fast (< 1ms)
        assert benchmark.stats["mean"] < 0.001

    def test_memory_overhead(self):
        """Test memory overhead of metrics collection."""
        import sys

        collector = MetricsCollector(history_size=1000)

        # Get initial size
        initial_size = sys.getsizeof(collector.metrics_history)

        # Collect 1000 metrics
        for _ in range(1000):
            collector.collect()

        # Get final size
        final_size = sys.getsizeof(collector.metrics_history)

        # Memory overhead should be reasonable (< 1MB for 1000 metrics)
        memory_overhead = final_size - initial_size
        assert memory_overhead < 1024 * 1024  # 1MB

    def test_collection_throughput(self):
        """Test metrics collection throughput."""
        collector = MetricsCollector()

        start_time = time.time()
        iterations = 1000

        for _ in range(iterations):
            collector.collect()

        elapsed = time.time() - start_time
        throughput = iterations / elapsed

        # Should be able to collect at least 100 metrics per second
        assert throughput > 100

    def test_request_recording_throughput(self):
        """Test request recording throughput."""
        collector = MetricsCollector()

        start_time = time.time()
        iterations = 10000

        for i in range(iterations):
            collector.record_request(latency_ms=float(i % 100), is_error=i % 10 == 0)

        elapsed = time.time() - start_time
        throughput = iterations / elapsed

        # Should be able to record at least 10000 requests per second
        assert throughput > 10000

    @pytest.mark.asyncio
    async def test_automatic_collection_overhead(self):
        """Test automatic collection overhead."""
        collector = MetricsCollector(collection_interval=0.1)

        # Start automatic collection
        await collector.start_collection()

        # Simulate application work
        start_time = time.time()
        work_iterations = 1000

        for _ in range(work_iterations):
            # Simulate some work
            await asyncio.sleep(0.001)

        elapsed = time.time() - start_time

        # Stop collection
        await collector.stop_collection()

        # Calculate overhead
        # Expected time without monitoring: work_iterations * 0.001 = 1.0s
        # Actual time should be close (overhead < 20%)
        expected_time = work_iterations * 0.001
        overhead_percent = ((elapsed - expected_time) / expected_time) * 100

        assert overhead_percent < 20.0

    def test_stats_calculation_scalability(self):
        """Test statistics calculation with large history."""
        collector = MetricsCollector(history_size=10000)

        # Collect many metrics
        for _ in range(10000):
            collector.collect()

        # Measure stats calculation time
        start_time = time.time()
        stats = collector.get_stats()
        elapsed = time.time() - start_time

        # Stats calculation should be fast even with large history (< 50ms)
        assert elapsed < 0.05
        assert stats.uptime_seconds > 0

    def test_history_filtering_performance(self):
        """Test history filtering performance."""
        collector = MetricsCollector(history_size=10000)

        # Collect many metrics
        for _ in range(10000):
            collector.collect()
            time.sleep(0.001)

        # Measure filtering time
        start_time = time.time()
        history = collector.get_history(window_seconds=5.0)
        elapsed = time.time() - start_time

        # Filtering should be fast (< 10ms)
        assert elapsed < 0.01
        assert len(history) > 0


class TestMonitoringAccuracy:
    """Accuracy tests for monitoring system."""

    def test_metrics_accuracy(self):
        """Test metrics collection accuracy."""
        collector = MetricsCollector()

        # Collect metrics
        metrics = collector.collect()

        # CPU and memory should be reasonable
        assert 0 <= metrics.cpu_percent <= 100
        assert 0 <= metrics.memory_percent <= 100
        assert metrics.memory_used_mb >= 0
        assert metrics.memory_available_mb >= 0

    def test_request_counting_accuracy(self):
        """Test request counting accuracy."""
        collector = MetricsCollector()

        # Record requests
        for i in range(100):
            collector.record_request(latency_ms=float(i), is_error=i % 10 == 0)

        assert collector.request_count == 100
        assert collector.error_count == 10

    def test_latency_calculation_accuracy(self):
        """Test latency calculation accuracy."""
        collector = MetricsCollector()

        # Record requests with known latencies
        latencies = [10.0, 20.0, 30.0, 40.0, 50.0]
        for latency in latencies:
            collector.record_request(latency_ms=latency)

        # Collect metrics
        collector.collect()
        stats = collector.get_stats()

        # Average latency should be 30.0
        expected_avg = sum(latencies) / len(latencies)
        assert abs(stats.avg_latency_ms - expected_avg) < 0.1

    def test_throughput_calculation_accuracy(self):
        """Test throughput calculation accuracy."""
        collector = MetricsCollector()

        # Record requests
        for _ in range(100):
            collector.record_request(latency_ms=50.0)

        # Wait a bit
        time.sleep(1.0)

        # Collect metrics
        metrics = collector.collect()

        # Throughput should be approximately 100 requests per second
        assert 50 < metrics.throughput_rps < 150  # Allow some variance

    def test_stats_window_accuracy(self):
        """Test statistics time window accuracy."""
        collector = MetricsCollector()

        # Collect metrics over time
        for _ in range(5):
            collector.collect()
            time.sleep(0.2)

        # Get stats for last 0.5 seconds
        stats = collector.get_stats(window_seconds=1.0)

        # Should have metrics from the window
        assert stats.uptime_seconds > 0
