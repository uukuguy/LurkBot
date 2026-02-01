"""Tests for monitoring API."""

import time

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from lurkbot.monitoring import MetricsCollector, MonitoringConfig, create_monitoring_router


@pytest.fixture
def collector():
    """Create metrics collector for testing."""
    return MetricsCollector()


@pytest.fixture
def config():
    """Create monitoring config for testing."""
    return MonitoringConfig(
        cpu_threshold_percent=80.0,
        memory_threshold_percent=80.0,
        latency_threshold_ms=1000.0,
        error_rate_threshold=0.05,
    )


@pytest.fixture
def app(collector, config):
    """Create FastAPI app with monitoring router."""
    app = FastAPI()
    router = create_monitoring_router(collector, config)
    app.include_router(router)
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


class TestMonitoringAPI:
    """Tests for monitoring API endpoints."""

    def test_get_current_metrics(self, client, collector):
        """Test GET /metrics/current endpoint."""
        # Collect some metrics
        collector.collect()

        response = client.get("/metrics/current")
        assert response.status_code == 200

        data = response.json()
        assert "timestamp" in data
        assert "cpu_percent" in data
        assert "memory_percent" in data
        assert "memory_used_mb" in data
        assert "memory_available_mb" in data
        assert "request_count" in data
        assert "request_latency_ms" in data
        assert "throughput_rps" in data
        assert "error_count" in data

    def test_get_stats(self, client, collector):
        """Test GET /metrics/stats endpoint."""
        # Collect some metrics
        for _ in range(3):
            collector.collect()
            time.sleep(0.1)

        response = client.get("/metrics/stats")
        assert response.status_code == 200

        data = response.json()
        assert "avg_cpu_percent" in data
        assert "max_cpu_percent" in data
        assert "avg_memory_percent" in data
        assert "max_memory_percent" in data
        assert "avg_latency_ms" in data
        assert "max_latency_ms" in data
        assert "total_requests" in data
        assert "total_errors" in data
        assert "avg_throughput_rps" in data
        assert "uptime_seconds" in data

    def test_get_stats_with_window(self, client, collector):
        """Test GET /metrics/stats with time window."""
        # Collect some metrics
        for _ in range(3):
            collector.collect()
            time.sleep(0.5)

        response = client.get("/metrics/stats?window_seconds=1.0")
        assert response.status_code == 200

        data = response.json()
        assert "uptime_seconds" in data

    def test_get_history(self, client, collector):
        """Test GET /metrics/history endpoint."""
        # Collect some metrics
        for _ in range(5):
            collector.collect()
            time.sleep(0.05)

        response = client.get("/metrics/history")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 5

        # Check first metric
        metric = data[0]
        assert "timestamp" in metric
        assert "cpu_percent" in metric
        assert "memory_percent" in metric

    def test_get_history_with_limit(self, client, collector):
        """Test GET /metrics/history with limit."""
        # Collect some metrics
        for _ in range(5):
            collector.collect()

        response = client.get("/metrics/history?limit=3")
        assert response.status_code == 200

        data = response.json()
        assert len(data) == 3

    def test_get_history_with_window(self, client, collector):
        """Test GET /metrics/history with time window."""
        # Collect some metrics
        for _ in range(5):
            collector.collect()
            time.sleep(0.3)

        response = client.get("/metrics/history?window_seconds=1.0")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 5

    def test_get_health_healthy(self, client, collector, config):
        """Test GET /metrics/health when system is healthy."""
        # Collect metrics (should be healthy by default)
        collector.collect()

        response = client.get("/metrics/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert data["cpu_healthy"] is True
        assert data["memory_healthy"] is True
        assert data["latency_healthy"] is True
        assert data["error_rate_healthy"] is True
        assert data["message"] is None

    def test_get_health_unhealthy_error_rate(self, client, collector, config):
        """Test GET /metrics/health with high error rate."""
        # Record requests with high error rate
        for _ in range(10):
            collector.record_request(50.0, is_error=False)
        for _ in range(5):
            collector.record_request(50.0, is_error=True)

        collector.collect()

        response = client.get("/metrics/health")
        assert response.status_code == 200

        data = response.json()
        # Error rate is 5/15 = 0.33, which exceeds threshold of 0.05
        assert data["status"] == "unhealthy"
        assert data["error_rate_healthy"] is False
        assert data["message"] is not None
        assert "Error rate" in data["message"]

    def test_reset_metrics(self, client, collector):
        """Test POST /metrics/reset endpoint."""
        # Collect some data
        collector.collect()
        collector.record_request(50.0)

        assert len(collector.metrics_history) > 0
        assert collector.request_count > 0

        response = client.post("/metrics/reset")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "success"

        # Verify reset
        assert len(collector.metrics_history) == 0
        assert collector.request_count == 0

    def test_invalid_query_params(self, client):
        """Test invalid query parameters."""
        # Invalid limit (too large)
        response = client.get("/metrics/history?limit=2000")
        assert response.status_code == 422

        # Invalid window_seconds (negative)
        response = client.get("/metrics/stats?window_seconds=-1")
        assert response.status_code == 422
