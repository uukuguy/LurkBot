"""Tests for Prometheus exporter."""

import pytest
from prometheus_client import CollectorRegistry

from lurkbot.monitoring import MetricsCollector, PrometheusExporter


class TestPrometheusExporter:
    """Tests for PrometheusExporter."""

    def test_init(self):
        """Test exporter initialization."""
        collector = MetricsCollector()
        exporter = PrometheusExporter(collector, port=9091)

        assert exporter.metrics_collector is collector
        assert exporter.port == 9091
        assert isinstance(exporter.registry, CollectorRegistry)
        assert exporter.is_running() is False

    def test_init_with_custom_registry(self):
        """Test initialization with custom registry."""
        collector = MetricsCollector()
        registry = CollectorRegistry()
        exporter = PrometheusExporter(collector, port=9091, registry=registry)

        assert exporter.registry is registry

    def test_system_collector(self):
        """Test SystemMetricsCollector."""
        collector = MetricsCollector()
        collector.collect()
        collector.record_request(50.0)

        exporter = PrometheusExporter(collector, port=9091)

        # Collect metrics
        metrics = list(exporter.system_collector.collect())

        # Should have multiple metric families
        assert len(metrics) > 0

        # Check metric names
        metric_names = [m.name for m in metrics]
        assert "lurkbot_cpu_percent" in metric_names
        assert "lurkbot_memory_percent" in metric_names
        assert "lurkbot_memory_used_mb" in metric_names
        assert "lurkbot_memory_available_mb" in metric_names
        assert "lurkbot_requests_total" in metric_names
        assert "lurkbot_errors_total" in metric_names
        assert "lurkbot_request_latency_ms" in metric_names
        assert "lurkbot_throughput_rps" in metric_names
        assert "lurkbot_uptime_seconds" in metric_names

    def test_repr(self):
        """Test string representation."""
        collector = MetricsCollector()
        exporter = PrometheusExporter(collector, port=9091)

        repr_str = repr(exporter)
        assert "PrometheusExporter" in repr_str
        assert "port=9091" in repr_str
        assert "running=False" in repr_str

    # Note: We skip testing start_http_server() as it starts a real HTTP server
    # which would require more complex test setup and teardown
