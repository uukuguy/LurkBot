---
name: nodes
description: Discover and manage distributed nodes via mDNS/Bonjour for remote command execution.
metadata: {"moltbot":{"emoji":"🌐"}}
---

# Nodes Management

Discover nodes on the network and execute commands remotely for distributed operations.

## Available Tool

- `nodes` - Node discovery and remote execution

## Operations

### 1. Discover nodes

```bash
{
  "op": "discover",
  "timeout": 5000  # discovery timeout in ms
}
```

### 2. List known nodes

```bash
{
  "op": "list"
}
```

### 3. Get node status

```bash
{
  "op": "status",
  "nodeId": "node-123"
}
```

### 4. Execute command on node

```bash
{
  "op": "exec",
  "nodeId": "node-123",
  "command": "git status",
  "timeout": 30000
}
```

### 5. Ping a node

```bash
{
  "op": "ping",
  "nodeId": "node-123"
}
```

## Node Discovery

Uses mDNS/Bonjour for zero-configuration node discovery on local network.

**Node information includes**:
- Node ID and name
- Host and port
- Platform and architecture
- Status (online/offline/busy)
- Capabilities
- Last seen timestamp

## Use Cases

**Distributed tasks**: Run commands across multiple machines.

**Fleet management**: Monitor and control multiple agent instances.

**Load balancing**: Distribute work across available nodes.

**Network monitoring**: Check status of nodes periodically.

**Remote execution**: Run scripts or commands on remote nodes.

## Security

- Nodes must be on the same local network for mDNS discovery
- Consider authentication for production use
- Commands are executed with node's permissions
- Be cautious with exec operations

## Configuration

Node discovery requires:
- mDNS/Bonjour support on network
- Nodes must advertise their services
- Firewall rules allowing mDNS traffic

## Tips

- Use discover before executing commands to find available nodes
- Check node status before long-running operations
- Set appropriate timeouts for network operations
- Monitor node capabilities to match tasks appropriately
- Use ping to verify node availability before exec

## Related Skills

- `sessions` - Spawn subagents on different nodes
- `automation/cron` - Schedule periodic node checks
