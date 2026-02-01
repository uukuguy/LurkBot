"""Tests for monitoring module."""

import asyncio
import time

import pytest

from lurkbot.monitoring import MetricsCollector, PerformanceMetrics


class TestPerformanceMetrics:
    """Tests for PerformanceMetrics."""

    def test_create_metrics(self):
        """Test creating metrics."""
        metrics = PerformanceMetrics(
            timestamp=time.time(),
            cpu_percent=50.0,
            memory_percent=60.0,
            memory_used_mb=1024.0,
            memory_available_mb=2048.0,
            request_count=100,
            request_latency_ms=50.0,
            throughput_rps=10.0,
            error_count=5,
        )

        assert metrics.cpu_percent == 50.0
        assert metrics.memory_percent == 60.0
        assert metrics.request_count == 100
        assert metrics.error_count == 5

    def test_to_dict(self):
        """Test converting metrics to dictionary."""
        metrics = PerformanceMetrics(
            timestamp=time.time(),
            cpu_percent=50.0,
            memory_percent=60.0,
            memory_used_mb=1024.0,
            memory_available_mb=2048.0,
        )

        data = metrics.to_dict()
        assert isinstance(data, dict)
        assert data["cpu_percent"] == 50.0
        assert data["memory_percent"] == 60.0


class TestMetricsCollector:
    """Tests for MetricsCollector."""

    def test_init(self):
        """Test collector initialization."""
        collector = MetricsCollector(history_size=100, collection_interval=0.5)

        assert collector.history_size == 100
        assert collector.collection_interval == 0.5
        assert collector.request_count == 0
        assert collector.error_count == 0
        assert len(collector.metrics_history) == 0

    def test_collect(self):
        """Test collecting metrics."""
        collector = MetricsCollector()
        metrics = collector.collect()

        assert isinstance(metrics, PerformanceMetrics)
        assert metrics.cpu_percent >= 0
        assert metrics.memory_percent >= 0
        assert metrics.memory_used_mb >= 0
        assert metrics.memory_available_mb >= 0
        assert len(collector.metrics_history) == 1

    def test_record_request(self):
        """Test recording requests."""
        collector = MetricsCollector()

        # Record successful request
        collector.record_request(latency_ms=50.0, is_error=False)
        assert collector.request_count == 1
        assert collector.error_count == 0
        assert len(collector.request_latencies) == 1

        # Record error request
        collector.record_request(latency_ms=100.0, is_error=True)
        assert collector.request_count == 2
        assert collector.error_count == 1
        assert len(collector.request_latencies) == 2

    def test_get_stats(self):
        """Test getting statistics."""
        collector = MetricsCollector()

        # Collect some metrics
        for _ in range(5):
            collector.collect()
            time.sleep(0.1)

        stats = collector.get_stats()
        assert stats.avg_cpu_percent >= 0
        assert stats.max_cpu_percent >= 0
        assert stats.avg_memory_percent >= 0
        assert stats.max_memory_percent >= 0
        assert stats.uptime_seconds > 0

    def test_get_stats_with_window(self):
        """Test getting statistics with time window."""
        collector = MetricsCollector()

        # Collect metrics over time
        for _ in range(3):
            collector.collect()
            time.sleep(0.2)

        # Get stats for last 0.5 seconds
        stats = collector.get_stats(window_seconds=0.5)
        assert stats.uptime_seconds > 0

    def test_get_current_metrics(self):
        """Test getting current metrics."""
        collector = MetricsCollector()

        # No metrics yet - should collect new one
        metrics = collector.get_current_metrics()
        assert isinstance(metrics, PerformanceMetrics)
        assert len(collector.metrics_history) == 1

        # Should return last collected metrics
        metrics2 = collector.get_current_metrics()
        assert metrics2.timestamp == metrics.timestamp

    def test_get_history(self):
        """Test getting metrics history."""
        collector = MetricsCollector()

        # Collect some metrics
        for _ in range(5):
            collector.collect()
            time.sleep(0.05)

        # Get all history
        history = collector.get_history()
        assert len(history) == 5

        # Get limited history
        history = collector.get_history(limit=3)
        assert len(history) == 3

        # Get history with time window
        history = collector.get_history(window_seconds=0.2)
        assert len(history) <= 5

    def test_history_size_limit(self):
        """Test history size limit."""
        collector = MetricsCollector(history_size=10)

        # Collect more than history size
        for _ in range(15):
            collector.collect()

        assert len(collector.metrics_history) == 10

    @pytest.mark.asyncio
    async def test_start_stop_collection(self):
        """Test starting and stopping automatic collection."""
        collector = MetricsCollector(collection_interval=0.1)

        # Start collection
        await collector.start_collection()
        assert collector._running is True

        # Wait for some collections
        await asyncio.sleep(0.3)

        # Should have collected some metrics
        assert len(collector.metrics_history) >= 2

        # Stop collection
        await collector.stop_collection()
        assert collector._running is False

    @pytest.mark.asyncio
    async def test_collection_loop(self):
        """Test automatic collection loop."""
        collector = MetricsCollector(collection_interval=0.1)

        await collector.start_collection()
        initial_count = len(collector.metrics_history)

        # Wait for collections
        await asyncio.sleep(0.25)

        # Should have more metrics
        assert len(collector.metrics_history) > initial_count

        await collector.stop_collection()

    def test_reset(self):
        """Test resetting metrics."""
        collector = MetricsCollector()

        # Collect some data
        collector.collect()
        collector.record_request(50.0)
        collector.record_request(100.0, is_error=True)

        assert len(collector.metrics_history) > 0
        assert collector.request_count > 0
        assert collector.error_count > 0

        # Reset
        collector.reset()

        assert len(collector.metrics_history) == 0
        assert collector.request_count == 0
        assert collector.error_count == 0
        assert len(collector.request_latencies) == 0

    def test_repr(self):
        """Test string representation."""
        collector = MetricsCollector(history_size=100, collection_interval=1.0)
        repr_str = repr(collector)

        assert "MetricsCollector" in repr_str
        assert "history_size=100" in repr_str
        assert "collection_interval=1.0" in repr_str
