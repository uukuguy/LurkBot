"""
Performance metrics collector.

This module provides functionality to collect system performance metrics
including CPU usage, memory usage, request latency, and throughput.
"""

import asyncio
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Deque

import psutil
from loguru import logger


@dataclass
class PerformanceMetrics:
    """Performance metrics snapshot."""

    timestamp: float
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_available_mb: float
    request_count: int = 0
    request_latency_ms: float = 0.0
    throughput_rps: float = 0.0
    error_count: int = 0

    def to_dict(self) -> dict:
        """Convert metrics to dictionary."""
        return {
            "timestamp": self.timestamp,
            "cpu_percent": self.cpu_percent,
            "memory_percent": self.memory_percent,
            "memory_used_mb": self.memory_used_mb,
            "memory_available_mb": self.memory_available_mb,
            "request_count": self.request_count,
            "request_latency_ms": self.request_latency_ms,
            "throughput_rps": self.throughput_rps,
            "error_count": self.error_count,
        }


@dataclass
class MetricsStats:
    """Aggregated metrics statistics."""

    avg_cpu_percent: float = 0.0
    max_cpu_percent: float = 0.0
    avg_memory_percent: float = 0.0
    max_memory_percent: float = 0.0
    avg_latency_ms: float = 0.0
    max_latency_ms: float = 0.0
    total_requests: int = 0
    total_errors: int = 0
    avg_throughput_rps: float = 0.0
    uptime_seconds: float = 0.0

    def to_dict(self) -> dict:
        """Convert stats to dictionary."""
        return {
            "avg_cpu_percent": self.avg_cpu_percent,
            "max_cpu_percent": self.max_cpu_percent,
            "avg_memory_percent": self.avg_memory_percent,
            "max_memory_percent": self.max_memory_percent,
            "avg_latency_ms": self.avg_latency_ms,
            "max_latency_ms": self.max_latency_ms,
            "total_requests": self.total_requests,
            "total_errors": self.total_errors,
            "avg_throughput_rps": self.avg_throughput_rps,
            "uptime_seconds": self.uptime_seconds,
        }


class MetricsCollector:
    """
    Metrics collector for system performance monitoring.

    Collects CPU usage, memory usage, request metrics, and provides
    aggregated statistics over time windows.
    """

    def __init__(
        self,
        history_size: int = 1000,
        collection_interval: float = 1.0,
    ):
        """
        Initialize metrics collector.

        Args:
            history_size: Maximum number of metrics to keep in history
            collection_interval: Interval between collections in seconds
        """
        self.history_size = history_size
        self.collection_interval = collection_interval

        # Metrics history
        self.metrics_history: Deque[PerformanceMetrics] = deque(maxlen=history_size)

        # Request tracking
        self.request_count = 0
        self.error_count = 0
        self.request_latencies: Deque[float] = deque(maxlen=1000)

        # Start time
        self.start_time = time.time()

        # Collection task
        self._collection_task: asyncio.Task | None = None
        self._running = False

        logger.info(
            f"MetricsCollector initialized with history_size={history_size}, "
            f"collection_interval={collection_interval}s"
        )

    def collect(self) -> PerformanceMetrics:
        """
        Collect current performance metrics.

        Returns:
            PerformanceMetrics: Current metrics snapshot
        """
        # Get CPU and memory metrics
        cpu_percent = psutil.cpu_percent(interval=None)
        memory = psutil.virtual_memory()

        # Calculate request metrics
        avg_latency = (
            sum(self.request_latencies) / len(self.request_latencies)
            if self.request_latencies
            else 0.0
        )

        # Calculate throughput (requests per second)
        uptime = time.time() - self.start_time
        throughput = self.request_count / uptime if uptime > 0 else 0.0

        metrics = PerformanceMetrics(
            timestamp=time.time(),
            cpu_percent=cpu_percent,
            memory_percent=memory.percent,
            memory_used_mb=memory.used / (1024 * 1024),
            memory_available_mb=memory.available / (1024 * 1024),
            request_count=self.request_count,
            request_latency_ms=avg_latency,
            throughput_rps=throughput,
            error_count=self.error_count,
        )

        # Add to history
        self.metrics_history.append(metrics)

        return metrics

    def record_request(self, latency_ms: float, is_error: bool = False) -> None:
        """
        Record a request with its latency.

        Args:
            latency_ms: Request latency in milliseconds
            is_error: Whether the request resulted in an error
        """
        self.request_count += 1
        self.request_latencies.append(latency_ms)

        if is_error:
            self.error_count += 1

    def get_stats(self, window_seconds: float | None = None) -> MetricsStats:
        """
        Get aggregated statistics.

        Args:
            window_seconds: Time window for statistics (None for all history)

        Returns:
            MetricsStats: Aggregated statistics
        """
        if not self.metrics_history:
            return MetricsStats()

        # Filter metrics by time window
        if window_seconds is not None:
            cutoff_time = time.time() - window_seconds
            metrics = [m for m in self.metrics_history if m.timestamp >= cutoff_time]
        else:
            metrics = list(self.metrics_history)

        if not metrics:
            return MetricsStats()

        # Calculate statistics
        cpu_percents = [m.cpu_percent for m in metrics]
        memory_percents = [m.memory_percent for m in metrics]
        latencies = [m.request_latency_ms for m in metrics if m.request_latency_ms > 0]
        throughputs = [m.throughput_rps for m in metrics]

        return MetricsStats(
            avg_cpu_percent=sum(cpu_percents) / len(cpu_percents),
            max_cpu_percent=max(cpu_percents),
            avg_memory_percent=sum(memory_percents) / len(memory_percents),
            max_memory_percent=max(memory_percents),
            avg_latency_ms=sum(latencies) / len(latencies) if latencies else 0.0,
            max_latency_ms=max(latencies) if latencies else 0.0,
            total_requests=self.request_count,
            total_errors=self.error_count,
            avg_throughput_rps=sum(throughputs) / len(throughputs) if throughputs else 0.0,
            uptime_seconds=time.time() - self.start_time,
        )

    def get_current_metrics(self) -> PerformanceMetrics:
        """
        Get the most recent metrics.

        Returns:
            PerformanceMetrics: Most recent metrics or a new collection
        """
        if self.metrics_history:
            return self.metrics_history[-1]
        return self.collect()

    def get_history(
        self,
        limit: int | None = None,
        window_seconds: float | None = None,
    ) -> list[PerformanceMetrics]:
        """
        Get metrics history.

        Args:
            limit: Maximum number of metrics to return
            window_seconds: Time window for metrics (None for all history)

        Returns:
            list[PerformanceMetrics]: List of metrics
        """
        # Filter by time window
        if window_seconds is not None:
            cutoff_time = time.time() - window_seconds
            metrics = [m for m in self.metrics_history if m.timestamp >= cutoff_time]
        else:
            metrics = list(self.metrics_history)

        # Apply limit
        if limit is not None:
            metrics = metrics[-limit:]

        return metrics

    async def start_collection(self) -> None:
        """Start automatic metrics collection."""
        if self._running:
            logger.warning("Metrics collection already running")
            return

        self._running = True
        self._collection_task = asyncio.create_task(self._collection_loop())
        logger.info("Started automatic metrics collection")

    async def stop_collection(self) -> None:
        """Stop automatic metrics collection."""
        if not self._running:
            return

        self._running = False
        if self._collection_task:
            self._collection_task.cancel()
            try:
                await self._collection_task
            except asyncio.CancelledError:
                pass
            self._collection_task = None

        logger.info("Stopped automatic metrics collection")

    async def _collection_loop(self) -> None:
        """Background task for automatic metrics collection."""
        logger.info(f"Metrics collection loop started (interval={self.collection_interval}s)")

        try:
            while self._running:
                self.collect()
                await asyncio.sleep(self.collection_interval)
        except asyncio.CancelledError:
            logger.info("Metrics collection loop cancelled")
            raise
        except Exception as e:
            logger.error(f"Error in metrics collection loop: {e}")
            raise

    def reset(self) -> None:
        """Reset all metrics and statistics."""
        self.metrics_history.clear()
        self.request_latencies.clear()
        self.request_count = 0
        self.error_count = 0
        self.start_time = time.time()
        logger.info("Metrics collector reset")

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"MetricsCollector(history_size={self.history_size}, "
            f"collection_interval={self.collection_interval}, "
            f"metrics_count={len(self.metrics_history)})"
        )
