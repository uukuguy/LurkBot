"""
Monitoring configuration.

This module provides configuration for the monitoring system.
"""

from pydantic import BaseModel, ConfigDict, Field


class MonitoringConfig(BaseModel):
    """Monitoring system configuration."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "enabled": True,
                "collection_interval": 1.0,
                "history_size": 1000,
                "prometheus_enabled": True,
                "prometheus_port": 9090,
                "cpu_threshold_percent": 80.0,
                "memory_threshold_percent": 80.0,
                "latency_threshold_ms": 1000.0,
                "error_rate_threshold": 0.05,
            }
        }
    )

    # Collection settings
    enabled: bool = Field(
        default=True,
        description="Enable metrics collection",
    )
    collection_interval: float = Field(
        default=1.0,
        ge=0.1,
        le=60.0,
        description="Metrics collection interval in seconds",
    )
    history_size: int = Field(
        default=1000,
        ge=100,
        le=10000,
        description="Maximum number of metrics to keep in history",
    )

    # Prometheus settings
    prometheus_enabled: bool = Field(
        default=True,
        description="Enable Prometheus exporter",
    )
    prometheus_port: int = Field(
        default=9090,
        ge=1024,
        le=65535,
        description="Prometheus HTTP server port",
    )

    # Alert thresholds
    cpu_threshold_percent: float = Field(
        default=80.0,
        ge=0.0,
        le=100.0,
        description="CPU usage alert threshold",
    )
    memory_threshold_percent: float = Field(
        default=80.0,
        ge=0.0,
        le=100.0,
        description="Memory usage alert threshold",
    )
    latency_threshold_ms: float = Field(
        default=1000.0,
        ge=0.0,
        description="Request latency alert threshold in milliseconds",
    )
    error_rate_threshold: float = Field(
        default=0.05,
        ge=0.0,
        le=1.0,
        description="Error rate alert threshold (0.0-1.0)",
    )


# Default configuration
DEFAULT_MONITORING_CONFIG = MonitoringConfig()
