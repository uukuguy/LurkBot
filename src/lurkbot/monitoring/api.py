"""
Monitoring API endpoints.

This module provides FastAPI endpoints for querying metrics and statistics.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from .collector import MetricsCollector, MetricsStats, PerformanceMetrics
from .config import MonitoringConfig


class MetricsResponse(BaseModel):
    """Response model for metrics."""

    timestamp: float
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_available_mb: float
    request_count: int
    request_latency_ms: float
    throughput_rps: float
    error_count: int


class StatsResponse(BaseModel):
    """Response model for statistics."""

    avg_cpu_percent: float
    max_cpu_percent: float
    avg_memory_percent: float
    max_memory_percent: float
    avg_latency_ms: float
    max_latency_ms: float
    total_requests: int
    total_errors: int
    avg_throughput_rps: float
    uptime_seconds: float


class HealthResponse(BaseModel):
    """Response model for health check."""

    status: str
    cpu_healthy: bool
    memory_healthy: bool
    latency_healthy: bool
    error_rate_healthy: bool
    message: str | None = None


def create_monitoring_router(
    metrics_collector: MetricsCollector,
    config: MonitoringConfig,
) -> APIRouter:
    """
    Create monitoring API router.

    Args:
        metrics_collector: MetricsCollector instance
        config: MonitoringConfig instance

    Returns:
        APIRouter: FastAPI router with monitoring endpoints
    """
    router = APIRouter(prefix="/metrics", tags=["monitoring"])

    @router.get("/current", response_model=MetricsResponse)
    async def get_current_metrics():
        """Get current performance metrics."""
        metrics = metrics_collector.get_current_metrics()
        return MetricsResponse(**metrics.to_dict())

    @router.get("/stats", response_model=StatsResponse)
    async def get_stats(
        window_seconds: float | None = Query(
            None,
            description="Time window for statistics in seconds",
            ge=1.0,
        ),
    ):
        """Get aggregated statistics."""
        stats = metrics_collector.get_stats(window_seconds=window_seconds)
        return StatsResponse(**stats.to_dict())

    @router.get("/history", response_model=list[MetricsResponse])
    async def get_history(
        limit: int | None = Query(
            None,
            description="Maximum number of metrics to return",
            ge=1,
            le=1000,
        ),
        window_seconds: float | None = Query(
            None,
            description="Time window for metrics in seconds",
            ge=1.0,
        ),
    ):
        """Get metrics history."""
        history = metrics_collector.get_history(
            limit=limit,
            window_seconds=window_seconds,
        )
        return [MetricsResponse(**m.to_dict()) for m in history]

    @router.get("/health", response_model=HealthResponse)
    async def get_health():
        """Get system health status based on thresholds."""
        current = metrics_collector.get_current_metrics()
        stats = metrics_collector.get_stats()

        # Check thresholds
        cpu_healthy = current.cpu_percent < config.cpu_threshold_percent
        memory_healthy = current.memory_percent < config.memory_threshold_percent
        latency_healthy = stats.avg_latency_ms < config.latency_threshold_ms

        # Calculate error rate
        error_rate = (
            stats.total_errors / stats.total_requests
            if stats.total_requests > 0
            else 0.0
        )
        error_rate_healthy = error_rate < config.error_rate_threshold

        # Determine overall status
        all_healthy = all([cpu_healthy, memory_healthy, latency_healthy, error_rate_healthy])
        status = "healthy" if all_healthy else "unhealthy"

        # Build message
        issues = []
        if not cpu_healthy:
            issues.append(f"CPU usage {current.cpu_percent:.1f}% exceeds threshold")
        if not memory_healthy:
            issues.append(f"Memory usage {current.memory_percent:.1f}% exceeds threshold")
        if not latency_healthy:
            issues.append(f"Latency {stats.avg_latency_ms:.1f}ms exceeds threshold")
        if not error_rate_healthy:
            issues.append(f"Error rate {error_rate:.2%} exceeds threshold")

        message = "; ".join(issues) if issues else None

        return HealthResponse(
            status=status,
            cpu_healthy=cpu_healthy,
            memory_healthy=memory_healthy,
            latency_healthy=latency_healthy,
            error_rate_healthy=error_rate_healthy,
            message=message,
        )

    @router.post("/reset")
    async def reset_metrics():
        """Reset all metrics and statistics."""
        metrics_collector.reset()
        return {"status": "success", "message": "Metrics reset successfully"}

    return router
