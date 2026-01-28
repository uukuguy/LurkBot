"""Docker sandbox implementation for secure tool execution."""

import time
from pathlib import Path
from typing import Any

import docker
from docker.errors import DockerException, ImageNotFound
from docker.types import Mount, Ulimit
from loguru import logger

from .types import SandboxConfig, SandboxResult


class DockerSandbox:
    """Docker-based sandbox for secure command execution."""

    def __init__(self, config: SandboxConfig):
        """Initialize Docker sandbox.

        Args:
            config: Sandbox configuration
        """
        self.config = config
        self.client = docker.from_env()
        self._ensure_image()

    def _ensure_image(self) -> None:
        """Ensure the Docker image exists, pull if not."""
        try:
            self.client.images.get(self.config.image)
            logger.debug(f"Image {self.config.image} found")
        except ImageNotFound:
            logger.info(f"Pulling image {self.config.image}...")
            self.client.images.pull(self.config.image)
            logger.info(f"Image {self.config.image} pulled successfully")

    def _build_mounts(self) -> list[Mount]:
        """Build Docker mounts configuration."""
        mounts = []

        if self.config.workspace_path:
            workspace_path = Path(self.config.workspace_path)
            if not workspace_path.exists():
                logger.warning(f"Workspace path {workspace_path} does not exist")
                return mounts

            mounts.append(
                Mount(
                    target=self.config.workspace_mount,
                    source=str(workspace_path.resolve()),
                    type="bind",
                    read_only=self.config.workspace_readonly,
                )
            )
            logger.debug(
                f"Mounted workspace: {workspace_path} -> {self.config.workspace_mount} "
                f"(ro={self.config.workspace_readonly})"
            )

        return mounts

    def _build_run_config(self, command: str) -> dict[str, Any]:
        """Build Docker run configuration.

        Args:
            command: Command to execute

        Returns:
            Docker run configuration dictionary
        """
        config: dict[str, Any] = {
            "image": self.config.image,
            "command": ["sh", "-c", command],
            "detach": True,
            "remove": False,  # We'll remove manually after getting logs
            # Resource limits
            "mem_limit": self.config.memory_limit,
            "cpu_quota": self.config.cpu_quota,
            "cpu_period": self.config.cpu_period,
            # Network
            "network_mode": self.config.network,
            # Security
            "user": self.config.user,
            "read_only": self.config.read_only_root,
            "security_opt": ["no-new-privileges"],
            "cap_drop": self.config.cap_drop,
            # Process limits
            "pids_limit": self.config.pids_limit,
            # Mounts
            "mounts": self._build_mounts(),
            # Tmpfs
            "tmpfs": {path.split(":")[0]: path.split(":", 1)[1] for path in self.config.tmpfs},
            # Labels
            "labels": {
                "lurkbot.sandbox": "1",
                "lurkbot.created_at": str(int(time.time())),
                **self.config.labels,
            },
            # Ulimits
            "ulimits": [
                Ulimit(name="nofile", soft=1024, hard=2048),
                Ulimit(name="nproc", soft=64),
            ],
        }

        return config

    def execute(self, command: str) -> SandboxResult:
        """Execute command in sandbox.

        Args:
            command: Shell command to execute

        Returns:
            Sandbox execution result
        """
        start_time = time.time()
        container = None

        try:
            # Create and start container
            run_config = self._build_run_config(command)
            logger.debug(f"Creating container with config: {run_config}")

            container = self.client.containers.run(**run_config)
            container_id = container.id[:12]
            logger.info(f"Container {container_id} started")

            # Wait for container to finish (with timeout)
            try:
                result = container.wait(timeout=self.config.execution_timeout)
                exit_code = result.get("StatusCode", -1)
            except Exception as e:
                logger.warning(f"Container {container_id} timed out: {e}")
                container.kill()
                execution_time = time.time() - start_time
                return SandboxResult(
                    success=False,
                    stdout="",
                    stderr=f"Execution timed out after {self.config.execution_timeout}s",
                    exit_code=-1,
                    execution_time=execution_time,
                    container_id=container_id,
                    error="Timeout",
                )

            # Get logs
            logs = container.logs(stdout=True, stderr=True)
            output = logs.decode("utf-8", errors="replace")

            # Parse stdout/stderr (Docker combines them)
            stdout = output
            stderr = ""

            execution_time = time.time() - start_time
            success = exit_code == 0

            logger.info(
                f"Container {container_id} finished: "
                f"exit_code={exit_code}, time={execution_time:.2f}s"
            )

            return SandboxResult(
                success=success,
                stdout=stdout,
                stderr=stderr,
                exit_code=exit_code,
                execution_time=execution_time,
                container_id=container_id,
            )

        except DockerException as e:
            execution_time = time.time() - start_time
            logger.error(f"Docker error: {e}")
            return SandboxResult(
                success=False,
                stdout="",
                stderr=str(e),
                exit_code=-1,
                execution_time=execution_time,
                error=f"Docker error: {e}",
            )

        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Unexpected error: {e}")
            return SandboxResult(
                success=False,
                stdout="",
                stderr=str(e),
                exit_code=-1,
                execution_time=execution_time,
                error=f"Unexpected error: {e}",
            )

        finally:
            # Clean up container
            if container:
                try:
                    container.remove(force=True)
                    logger.debug(f"Container {container.id[:12]} removed")
                except Exception as e:
                    logger.warning(f"Failed to remove container: {e}")

    def cleanup(self) -> None:
        """Clean up old sandbox containers."""
        try:
            containers = self.client.containers.list(
                all=True, filters={"label": "lurkbot.sandbox=1"}
            )

            cutoff_time = int(time.time()) - self.config.hot_container_window

            for container in containers:
                created_at = int(container.labels.get("lurkbot.created_at", "0"))
                if created_at < cutoff_time:
                    try:
                        container.remove(force=True)
                        logger.debug(f"Removed old container {container.id[:12]}")
                    except Exception as e:
                        logger.warning(f"Failed to remove container {container.id[:12]}: {e}")

        except Exception as e:
            logger.error(f"Failed to cleanup containers: {e}")
