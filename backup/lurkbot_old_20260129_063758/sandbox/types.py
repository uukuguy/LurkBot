"""Type definitions for Docker sandbox."""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class SandboxConfig:
    """Configuration for Docker sandbox."""

    # Image settings
    image: str = "debian:bookworm-slim"

    # Resource limits
    memory_limit: str = "512m"  # e.g., "512m", "1g"
    cpu_quota: int = 50000  # 50% of CPU (out of 100000)
    cpu_period: int = 100000

    # Security settings
    read_only_root: bool = True
    network: str = "none"  # "none", "bridge", "host"
    user: str = "nobody"

    # Filesystem
    tmpfs: list[str] = field(
        default_factory=lambda: [
            "/tmp:rw,noexec,nosuid,size=100m",
            "/var/tmp:rw,noexec,nosuid,size=50m",
        ]
    )
    workspace_path: Path | None = None  # Host workspace path to mount
    workspace_mount: str = "/workspace"  # Container mount point
    workspace_readonly: bool = True

    # Process limits
    pids_limit: int = 64

    # Capabilities to drop
    cap_drop: list[str] = field(
        default_factory=lambda: [
            "ALL",  # Drop all capabilities first
        ]
    )

    # Timeout
    execution_timeout: int = 30  # seconds

    # Container reuse
    hot_container_window: int = 300  # seconds (5 minutes)

    # Labels
    labels: dict[str, str] = field(default_factory=dict)


@dataclass
class SandboxResult:
    """Result from sandbox execution."""

    success: bool
    stdout: str
    stderr: str
    exit_code: int
    execution_time: float  # seconds
    container_id: str | None = None
    error: str | None = None
