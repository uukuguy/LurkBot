---
name: gateway
description: Bridge to Gateway WebSocket API for RPC calls to gateway server for session, cron, and channel operations.
metadata: {"moltbot":{"emoji":"🌉"}}
---

# Gateway RPC

Communicate with the Gateway WebSocket server for advanced operations and cross-session messaging.

## Available Tool

- `gateway` - Make RPC calls to the Gateway server

## Gateway Methods

The gateway tool supports various RPC methods for interacting with the Gateway server:

### Session Management
- Agent operations
- Session queries
- Cross-session communication

### Cron Control
- Job management
- Schedule operations
- Run history

### Channel Operations
- Channel configuration
- Message routing
- Event handling

### System Information
- Server status
- Configuration queries
- Health checks

## Quick Examples

### Make an RPC call

```bash
{
  "method": "agent",
  "params": {
    "sessionKey": "channel:default:abc123",
    "message": "Task completed",
    "deliver": true
  },
  "timeoutMs": 30000
}
```

### Query server status

```bash
{
  "method": "ping",
  "params": {}
}
```

## Parameters

- `method` (required) - Gateway RPC method name
- `params` (optional) - Method-specific parameters
- `timeoutMs` (optional) - Request timeout in milliseconds (default: 30000)

## Gateway Server

The Gateway server must be running for this tool to work:

```bash
# Start Gateway server
lurkbot gateway start
```

Gateway provides:
- WebSocket connections for agents
- Cross-session messaging
- Cron service coordination
- Channel multiplexing

## Use Cases

**Cross-session messaging**: Send messages between different agent sessions via Gateway.

**Remote operations**: Trigger actions on agents running in Gateway sessions.

**Service coordination**: Access centralized services like cron scheduler.

**Real-time communication**: Use WebSocket for low-latency operations.

## Configuration

Gateway connection is configured in agent settings:

```python
{
  "gateway_url": "ws://localhost:18789",
  "session_key": "channel:agent:session-id"
}
```

## Tips

- Ensure Gateway server is running before using this tool
- Use appropriate timeouts for long-running operations
- Check Gateway server logs for debugging
- Gateway handles session lifecycle automatically
- Methods are Gateway-version specific

## Related Skills

- `sessions` - Use sessions_send which relies on Gateway
- `automation/cron` - Access cron service via Gateway
- `messaging` - Route messages through Gateway channels
