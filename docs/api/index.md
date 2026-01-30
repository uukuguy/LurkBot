# API Reference

Complete API documentation for LurkBot.

## Overview

LurkBot provides multiple APIs for integration:

| API | Description | Use Case |
|-----|-------------|----------|
| [Gateway Protocol](gateway-protocol.md) | WebSocket protocol | Real-time integration |
| [RPC Methods](rpc-methods.md) | Remote procedure calls | Automation |
| [CLI Reference](cli-reference.md) | Command-line interface | Shell scripts |

## Implementation

Source: `src/lurkbot/gateway/`

| 组件 | 源文件 | 描述 |
|------|--------|------|
| `GatewayServer` | `server.py` | WebSocket 服务器 |
| `MethodRegistry` | `methods.py` | RPC 方法注册表 |
| `EventBroadcaster` | `events.py` | 事件广播器 |
| Protocol Frames | `protocol/frames.py` | 协议帧定义 |

## Gateway Protocol

### Connect to Gateway

```javascript
const ws = new WebSocket('ws://127.0.0.1:18789');

// 发送 hello 握手
ws.send(JSON.stringify({
  type: 'hello',
  minProtocol: 1,
  maxProtocol: 1,
  client: {
    id: 'my-client',
    displayName: 'My Client',
    version: '1.0.0',
    platform: 'browser',
    mode: 'web'
  }
}));
```

### Protocol Frames

Source: `src/lurkbot/gateway/protocol/frames.py`

| 帧类型 | 描述 |
|--------|------|
| `hello` | 客户端握手请求 |
| `hello-ok` | 服务器握手响应 |
| `request` | RPC 请求 |
| `response` | RPC 响应 |
| `event` | 事件推送 |

### Error Codes

Source: `src/lurkbot/gateway/protocol/frames.py:13-21`

```python
class ErrorCode(str, Enum):
    NOT_LINKED = "NOT_LINKED"        # 认证提供商未连接
    NOT_PAIRED = "NOT_PAIRED"        # 设备未配对
    AGENT_TIMEOUT = "AGENT_TIMEOUT"  # 代理操作超时
    INVALID_REQUEST = "INVALID_REQUEST"  # 无效请求
    UNAVAILABLE = "UNAVAILABLE"      # 服务暂时不可用
    METHOD_NOT_FOUND = "METHOD_NOT_FOUND"  # 方法不存在
    INTERNAL_ERROR = "INTERNAL_ERROR"  # 内部错误
```

## RPC Method System

Source: `src/lurkbot/gateway/methods.py`

### Method Registry

```python
class MethodRegistry:
    """RPC 方法注册表"""

    def register(self, method_name: str, handler: MethodHandler) -> None:
        """注册 RPC 方法"""

    def unregister(self, method_name: str) -> None:
        """取消注册 RPC 方法"""

    async def invoke(
        self,
        method_name: str,
        params: dict | None = None,
        session_key: str | None = None,
    ) -> dict | None:
        """调用 RPC 方法"""

    def list_methods(self) -> list[str]:
        """列出所有已注册的方法"""

    def has_method(self, method_name: str) -> bool:
        """检查方法是否存在"""
```

### Method Context

```python
@dataclass
class MethodContext:
    """RPC 方法上下文"""

    params: dict | None
    session_key: str | None
```

### Register Custom Method

```python
from lurkbot.gateway.methods import get_method_registry, MethodContext

registry = get_method_registry()

async def my_method(ctx: MethodContext) -> dict | None:
    # 处理请求
    return {"result": "ok"}

registry.register("my.method", my_method)
```

### Invoke Method via WebSocket

```javascript
// 发送 RPC 请求
ws.send(JSON.stringify({
  id: 'req-123',
  type: 'request',
  method: 'sessions.list',
  params: { status: 'active' },
  sessionKey: 'session-abc'
}));

// 接收响应
// {
//   "id": "req-123",
//   "type": "response",
//   "result": { "sessions": [...] }
// }
```

## CLI Reference

LurkBot CLI 使用 Typer 构建，提供以下命令：

```bash
lurkbot [OPTIONS] COMMAND [ARGS]
```

详细命令参考请查看 [CLI Reference](cli-reference.md)。

---

## See Also

- [Gateway](../advanced/gateway.md) - Gateway 架构设计
- [Architecture](../developer/architecture.md) - 系统架构
- [Configuration](../user-guide/configuration/index.md) - 配置选项
