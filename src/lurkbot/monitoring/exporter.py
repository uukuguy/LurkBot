"""
Prometheus metrics exporter.

This module provides functionality to export metrics to Prometheus
using the prometheus_client library.
"""

from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram, start_http_server
from prometheus_client.core import GaugeMetricFamily
from prometheus_client.registry import Collector
from loguru import logger

from .collector import MetricsCollector


class SystemMetricsCollector(Collector):
    """
    Custom Prometheus collector for system metrics.

    Collects metrics from MetricsCollector and exposes them in Prometheus format.
    """

    def __init__(self, metrics_collector: MetricsCollector):
        """
        Initialize system metrics collector.

        Args:
            metrics_collector: MetricsCollector instance to collect from
        """
        self.metrics_collector = metrics_collector

    def collect(self):
        """Collect metrics for Prometheus."""
        # Get current metrics
        current = self.metrics_collector.get_current_metrics()
        stats = self.metrics_collector.get_stats()

        # CPU metrics
        cpu_gauge = GaugeMetricFamily(
            "lurkbot_cpu_percent",
            "Current CPU usage percentage",
        )
        cpu_gauge.add_sample("lurkbot_cpu_percent", {}, current.cpu_percent)
        yield cpu_gauge

        # Memory metrics
        memory_percent_gauge = GaugeMetricFamily(
            "lurkbot_memory_percent",
            "Current memory usage percentage",
        )
        memory_percent_gauge.add_sample("lurkbot_memory_percent", {}, current.memory_percent)
        yield memory_percent_gauge

        memory_used_gauge = GaugeMetricFamily(
            "lurkbot_memory_used_mb",
            "Current memory used in MB",
        )
        memory_used_gauge.add_sample("lurkbot_memory_used_mb", {}, current.memory_used_mb)
        yield memory_used_gauge

        memory_available_gauge = GaugeMetricFamily(
            "lurkbot_memory_available_mb",
            "Current memory available in MB",
        )
        memory_available_gauge.add_sample(
            "lurkbot_memory_available_mb", {}, current.memory_available_mb
        )
        yield memory_available_gauge

        # Request metrics
        request_count_gauge = GaugeMetricFamily(
            "lurkbot_requests_total",
            "Total number of requests",
        )
        request_count_gauge.add_sample("lurkbot_requests_total", {}, stats.total_requests)
        yield request_count_gauge

        error_count_gauge = GaugeMetricFamily(
            "lurkbot_errors_total",
            "Total number of errors",
        )
        error_count_gauge.add_sample("lurkbot_errors_total", {}, stats.total_errors)
        yield error_count_gauge

        # Latency metrics
        latency_gauge = GaugeMetricFamily(
            "lurkbot_request_latency_ms",
            "Average request latency in milliseconds",
        )
        latency_gauge.add_sample("lurkbot_request_latency_ms", {}, stats.avg_latency_ms)
        yield latency_gauge

        # Throughput metrics
        throughput_gauge = GaugeMetricFamily(
            "lurkbot_throughput_rps",
            "Average throughput in requests per second",
        )
        throughput_gauge.add_sample("lurkbot_throughput_rps", {}, stats.avg_throughput_rps)
        yield throughput_gauge

        # Uptime metrics
        uptime_gauge = GaugeMetricFamily(
            "lurkbot_uptime_seconds",
            "System uptime in seconds",
        )
        uptime_gauge.add_sample("lurkbot_uptime_seconds", {}, stats.uptime_seconds)
        yield uptime_gauge


class PrometheusExporter:
    """
    Prometheus metrics exporter.

    Exports metrics from MetricsCollector to Prometheus format
    and optionally starts an HTTP server for scraping.
    """

    def __init__(
        self,
        metrics_collector: MetricsCollector,
        port: int = 9090,
        registry: CollectorRegistry | None = None,
    ):
        """
        Initialize Prometheus exporter.

        Args:
            metrics_collector: MetricsCollector instance to export from
            port: Port for Prometheus HTTP server
            registry: Custom registry (None for default)
        """
        self.metrics_collector = metrics_collector
        self.port = port
        self.registry = registry or CollectorRegistry()

        # Register custom collector
        self.system_collector = SystemMetricsCollector(metrics_collector)
        self.registry.register(self.system_collector)

        # HTTP server state
        self._server_started = False

        logger.info(f"PrometheusExporter initialized on port {port}")

    def start_http_server(self) -> None:
        """Start Prometheus HTTP server for metrics scraping."""
        if self._server_started:
            logger.warning("Prometheus HTTP server already started")
            return

        start_http_server(self.port, registry=self.registry)
        self._server_started = True
        logger.info(f"Prometheus HTTP server started on port {self.port}")
        logger.info(f"Metrics available at http://localhost:{self.port}/metrics")

    def is_running(self) -> bool:
        """Check if HTTP server is running."""
        return self._server_started

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"PrometheusExporter(port={self.port}, "
            f"running={self._server_started})"
        )
