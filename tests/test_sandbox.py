"""Tests for Docker sandbox."""

import pytest

from lurkbot.sandbox import DockerSandbox, SandboxConfig
from lurkbot.sandbox.manager import SandboxManager
from lurkbot.agents.base import SessionType


class TestSandboxConfig:
    """Test sandbox configuration."""

    def test_default_config(self):
        """Test default configuration."""
        config = SandboxConfig()
        assert config.image == "debian:bookworm-slim"
        assert config.memory_limit == "512m"
        assert config.cpu_quota == 50000
        assert config.read_only_root is True
        assert config.network == "none"
        assert config.user == "nobody"
        assert config.pids_limit == 64
        assert config.execution_timeout == 30

    def test_custom_config(self):
        """Test custom configuration."""
        config = SandboxConfig(
            memory_limit="1g",
            cpu_quota=100000,
            execution_timeout=60,
        )
        assert config.memory_limit == "1g"
        assert config.cpu_quota == 100000
        assert config.execution_timeout == 60


@pytest.mark.docker
class TestDockerSandbox:
    """Test Docker sandbox (requires Docker daemon)."""

    def test_simple_command(self, request):
        """Test simple command execution."""
        if not request.config.getoption("--docker"):
            pytest.skip("Docker tests require --docker flag")

        config = SandboxConfig(execution_timeout=10)
        sandbox = DockerSandbox(config)

        result = sandbox.execute("echo 'Hello, World!'")

        assert result.success is True
        assert result.exit_code == 0
        assert "Hello, World!" in result.stdout
        assert result.container_id is not None
        assert result.execution_time > 0

    def test_command_with_error(self, request):
        """Test command that fails."""
        if not request.config.getoption("--docker"):
            pytest.skip("Docker tests require --docker flag")

        config = SandboxConfig(execution_timeout=10)
        sandbox = DockerSandbox(config)

        result = sandbox.execute("exit 1")

        assert result.success is False
        assert result.exit_code == 1

    def test_timeout(self, request):
        """Test command timeout."""
        if not request.config.getoption("--docker"):
            pytest.skip("Docker tests require --docker flag")

        config = SandboxConfig(execution_timeout=2)
        sandbox = DockerSandbox(config)

        result = sandbox.execute("sleep 10")

        assert result.success is False
        assert "timeout" in result.stderr.lower() or result.error == "Timeout"

    def test_read_only_filesystem(self, request):
        """Test read-only filesystem protection."""
        if not request.config.getoption("--docker"):
            pytest.skip("Docker tests require --docker flag")

        config = SandboxConfig(read_only_root=True, execution_timeout=10)
        sandbox = DockerSandbox(config)

        result = sandbox.execute("touch /test.txt")

        assert result.success is False
        assert result.exit_code != 0

    def test_network_isolation(self, request):
        """Test network isolation."""
        if not request.config.getoption("--docker"):
            pytest.skip("Docker tests require --docker flag")

        config = SandboxConfig(network="none", execution_timeout=10)
        sandbox = DockerSandbox(config)

        # Try to access network (should fail with network=none)
        result = sandbox.execute("ping -c 1 8.8.8.8")

        assert result.success is False


class TestSandboxManager:
    """Test sandbox manager."""

    def test_singleton(self):
        """Test singleton pattern."""
        manager1 = SandboxManager.get_instance()
        manager2 = SandboxManager.get_instance()
        assert manager1 is manager2

    def test_should_use_sandbox(self):
        """Test session type sandbox decision."""
        manager = SandboxManager()

        assert manager.should_use_sandbox(SessionType.MAIN) is False
        assert manager.should_use_sandbox(SessionType.GROUP) is True
        assert manager.should_use_sandbox(SessionType.TOPIC) is True

    @pytest.mark.docker
    def test_get_sandbox(self, request):
        """Test getting sandbox instance."""
        if not request.config.getoption("--docker"):
            pytest.skip("Docker tests require --docker flag")

        manager = SandboxManager()
        config = SandboxConfig()

        sandbox1 = manager.get_sandbox("session1", config)
        sandbox2 = manager.get_sandbox("session1", config)

        # Should return same instance for same session
        assert sandbox1 is sandbox2

    @pytest.mark.docker
    def test_cleanup_session(self, request):
        """Test session cleanup."""
        if not request.config.getoption("--docker"):
            pytest.skip("Docker tests require --docker flag")

        manager = SandboxManager()
        config = SandboxConfig()

        manager.get_sandbox("session1", config)
        assert "session1" in manager._sandboxes

        manager.cleanup_session("session1")
        assert "session1" not in manager._sandboxes
