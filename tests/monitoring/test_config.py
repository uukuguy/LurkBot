"""Tests for monitoring configuration."""

import pytest
from pydantic import ValidationError

from lurkbot.monitoring import DEFAULT_MONITORING_CONFIG, MonitoringConfig


class TestMonitoringConfig:
    """Tests for MonitoringConfig."""

    def test_default_config(self):
        """Test default configuration."""
        config = MonitoringConfig()

        assert config.enabled is True
        assert config.collection_interval == 1.0
        assert config.history_size == 1000
        assert config.prometheus_enabled is True
        assert config.prometheus_port == 9090
        assert config.cpu_threshold_percent == 80.0
        assert config.memory_threshold_percent == 80.0
        assert config.latency_threshold_ms == 1000.0
        assert config.error_rate_threshold == 0.05

    def test_custom_config(self):
        """Test custom configuration."""
        config = MonitoringConfig(
            enabled=False,
            collection_interval=2.0,
            history_size=500,
            prometheus_enabled=False,
            prometheus_port=8080,
            cpu_threshold_percent=90.0,
            memory_threshold_percent=85.0,
            latency_threshold_ms=500.0,
            error_rate_threshold=0.1,
        )

        assert config.enabled is False
        assert config.collection_interval == 2.0
        assert config.history_size == 500
        assert config.prometheus_enabled is False
        assert config.prometheus_port == 8080
        assert config.cpu_threshold_percent == 90.0
        assert config.memory_threshold_percent == 85.0
        assert config.latency_threshold_ms == 500.0
        assert config.error_rate_threshold == 0.1

    def test_collection_interval_validation(self):
        """Test collection interval validation."""
        # Valid values
        config = MonitoringConfig(collection_interval=0.1)
        assert config.collection_interval == 0.1

        config = MonitoringConfig(collection_interval=60.0)
        assert config.collection_interval == 60.0

        # Invalid values
        with pytest.raises(ValidationError):
            MonitoringConfig(collection_interval=0.05)  # Too small

        with pytest.raises(ValidationError):
            MonitoringConfig(collection_interval=61.0)  # Too large

    def test_history_size_validation(self):
        """Test history size validation."""
        # Valid values
        config = MonitoringConfig(history_size=100)
        assert config.history_size == 100

        config = MonitoringConfig(history_size=10000)
        assert config.history_size == 10000

        # Invalid values
        with pytest.raises(ValidationError):
            MonitoringConfig(history_size=50)  # Too small

        with pytest.raises(ValidationError):
            MonitoringConfig(history_size=20000)  # Too large

    def test_prometheus_port_validation(self):
        """Test Prometheus port validation."""
        # Valid values
        config = MonitoringConfig(prometheus_port=1024)
        assert config.prometheus_port == 1024

        config = MonitoringConfig(prometheus_port=65535)
        assert config.prometheus_port == 65535

        # Invalid values
        with pytest.raises(ValidationError):
            MonitoringConfig(prometheus_port=80)  # Too small

        with pytest.raises(ValidationError):
            MonitoringConfig(prometheus_port=70000)  # Too large

    def test_threshold_validation(self):
        """Test threshold validation."""
        # Valid CPU threshold
        config = MonitoringConfig(cpu_threshold_percent=50.0)
        assert config.cpu_threshold_percent == 50.0

        # Valid memory threshold
        config = MonitoringConfig(memory_threshold_percent=75.0)
        assert config.memory_threshold_percent == 75.0

        # Valid latency threshold
        config = MonitoringConfig(latency_threshold_ms=2000.0)
        assert config.latency_threshold_ms == 2000.0

        # Valid error rate threshold
        config = MonitoringConfig(error_rate_threshold=0.1)
        assert config.error_rate_threshold == 0.1

        # Invalid thresholds
        with pytest.raises(ValidationError):
            MonitoringConfig(cpu_threshold_percent=-10.0)

        with pytest.raises(ValidationError):
            MonitoringConfig(cpu_threshold_percent=110.0)

        with pytest.raises(ValidationError):
            MonitoringConfig(error_rate_threshold=1.5)

    def test_default_monitoring_config(self):
        """Test DEFAULT_MONITORING_CONFIG constant."""
        assert isinstance(DEFAULT_MONITORING_CONFIG, MonitoringConfig)
        assert DEFAULT_MONITORING_CONFIG.enabled is True
        assert DEFAULT_MONITORING_CONFIG.collection_interval == 1.0

    def test_config_serialization(self):
        """Test configuration serialization."""
        config = MonitoringConfig(
            enabled=True,
            collection_interval=2.0,
            history_size=500,
        )

        # Convert to dict
        data = config.model_dump()
        assert isinstance(data, dict)
        assert data["enabled"] is True
        assert data["collection_interval"] == 2.0
        assert data["history_size"] == 500

        # Convert to JSON
        json_str = config.model_dump_json()
        assert isinstance(json_str, str)
        assert "enabled" in json_str

    def test_config_from_dict(self):
        """Test creating configuration from dictionary."""
        data = {
            "enabled": False,
            "collection_interval": 3.0,
            "history_size": 2000,
            "prometheus_port": 8080,
        }

        config = MonitoringConfig(**data)
        assert config.enabled is False
        assert config.collection_interval == 3.0
        assert config.history_size == 2000
        assert config.prometheus_port == 8080
