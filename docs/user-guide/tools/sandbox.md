# Sandbox

The sandbox provides isolated execution environments for untrusted sessions. It uses Docker containers to prevent malicious or accidental damage.

## Overview

When sandbox mode is enabled:

- Tools run inside Docker containers
- Filesystem access is restricted
- Network access can be disabled
- Resource limits are enforced

## When Sandbox is Used

By default, sandbox is enabled for:

| Session Type | Sandbox | Reason |
|--------------|---------|--------|
| Owner DM | No | Trusted |
| Other DM | Optional | Partially trusted |
| Group Chat | Yes | Untrusted |
| Public Channel | Yes | Untrusted |

## Configuration

### Enable/Disable Sandbox

```bash
# Global sandbox setting
LURKBOT_SANDBOX_ENABLED=true

# Per-session type
LURKBOT_SANDBOX_MAIN=false
LURKBOT_SANDBOX_DM=true
LURKBOT_SANDBOX_GROUP=true
```

### Resource Limits

```bash
# Memory limit
LURKBOT_SANDBOX_MEMORY=512m

# CPU limit (cores)
LURKBOT_SANDBOX_CPU=1

# Disk quota
LURKBOT_SANDBOX_DISK=1g

# Execution timeout (seconds)
LURKBOT_SANDBOX_TIMEOUT=60
```

### Network Access

```bash
# Disable network in sandbox
LURKBOT_SANDBOX_NETWORK=false

# Allow specific hosts
LURKBOT_SANDBOX_ALLOWED_HOSTS=api.example.com,cdn.example.com
```

### Filesystem Access

```bash
# Read-only filesystem
LURKBOT_SANDBOX_READONLY=true

# Writable directories
LURKBOT_SANDBOX_WRITABLE=/tmp,/workspace

# Mount host directories (read-only)
LURKBOT_SANDBOX_MOUNTS=/data:/data:ro
```

## Docker Configuration

### Default Image

```bash
# Sandbox base image
LURKBOT_SANDBOX_IMAGE=ubuntu:22.04

# Custom image with tools
LURKBOT_SANDBOX_IMAGE=lurkbot/sandbox:latest
```

### Custom Dockerfile

Create a custom sandbox image:

```dockerfile
# ~/.lurkbot/sandbox/Dockerfile
FROM ubuntu:22.04

# Install common tools
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    nodejs \
    npm \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create workspace
WORKDIR /workspace

# Non-root user
RUN useradd -m sandbox
USER sandbox
```

Build and use:

```bash
docker build -t lurkbot/sandbox ~/.lurkbot/sandbox/
LURKBOT_SANDBOX_IMAGE=lurkbot/sandbox
```

## Sandbox Behavior

### Tool Execution

When a tool runs in sandbox:

1. Container is created (or reused)
2. Workspace is mounted
3. Tool executes inside container
4. Output is captured
5. Container is cleaned up (or kept for reuse)

### Workspace Isolation

Each session gets its own workspace:

```
~/.lurkbot/workspaces/
├── telegram_123456789_main/    # Owner workspace (not sandboxed)
├── telegram_987654321_dm/      # DM workspace (sandboxed)
└── discord_group_123/          # Group workspace (sandboxed)
```

### Container Lifecycle

```bash
# Container reuse (faster, less isolated)
LURKBOT_SANDBOX_REUSE=true

# Fresh container per command (slower, more isolated)
LURKBOT_SANDBOX_REUSE=false

# Container cleanup timeout
LURKBOT_SANDBOX_CLEANUP_AFTER=300
```

## Security Features

### Capability Dropping

Containers run with minimal capabilities:

```bash
# Additional capabilities to drop
LURKBOT_SANDBOX_DROP_CAPS=NET_RAW,SYS_ADMIN
```

### Seccomp Profile

```bash
# Use default seccomp profile
LURKBOT_SANDBOX_SECCOMP=default

# Custom seccomp profile
LURKBOT_SANDBOX_SECCOMP=/path/to/profile.json
```

### User Namespace

```bash
# Enable user namespace remapping
LURKBOT_SANDBOX_USERNS=true
```

## Monitoring

### Container Logs

```bash
# View sandbox logs
tail -f ~/.lurkbot/logs/sandbox.log
```

### Resource Usage

```bash
# Monitor sandbox containers
docker stats --filter "label=lurkbot.sandbox=true"
```

### Audit Trail

```bash
# Enable sandbox audit
LURKBOT_SANDBOX_AUDIT=true
```

Audit log:

```json
{
  "timestamp": "2026-01-30T12:00:00Z",
  "session": "telegram:123456789:group",
  "container": "lurkbot-sandbox-abc123",
  "tool": "bash",
  "command": "ls -la",
  "exit_code": 0,
  "duration_ms": 150,
  "memory_peak": "45MB",
  "cpu_time": "0.1s"
}
```

## Troubleshooting

### "Docker not available"

Install and start Docker:

```bash
# Check Docker
docker --version
docker ps

# Start Docker daemon
sudo systemctl start docker
```

### "Container creation failed"

Check Docker permissions:

```bash
# Add user to docker group
sudo usermod -aG docker $USER

# Or use sudo
LURKBOT_SANDBOX_SUDO=true
```

### "Out of memory"

Increase memory limit:

```bash
LURKBOT_SANDBOX_MEMORY=1g
```

### "Network timeout"

Enable network or increase timeout:

```bash
LURKBOT_SANDBOX_NETWORK=true
LURKBOT_SANDBOX_TIMEOUT=120
```

### Slow sandbox startup

Enable container reuse:

```bash
LURKBOT_SANDBOX_REUSE=true
```

Or use a lighter base image:

```bash
LURKBOT_SANDBOX_IMAGE=alpine:latest
```

## Best Practices

1. **Use container reuse** for better performance
2. **Disable network** unless required
3. **Set resource limits** to prevent abuse
4. **Monitor usage** with audit logging
5. **Use custom images** with pre-installed tools
6. **Regular cleanup** of old containers

---

## See Also

- [Tool Policies](tool-policies.md) - Security configuration
- [Sessions](../agents/sessions.md) - Session types
- [Configuration](../configuration/index.md) - All settings
