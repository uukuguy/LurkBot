# Gateway

The Gateway is LurkBot's central control plane. It coordinates all communication between channels, agents, and tools.

## Implementation

Source: `src/lurkbot/gateway/`

| 组件 | 源文件 | 描述 |
|------|--------|------|
| `GatewayServer` | `server.py` | WebSocket 服务器核心 |
| `GatewayConnection` | `server.py` | 单个 WebSocket 连接 |
| Protocol Frames | `protocol/frames.py` | 协议帧定义 |
| Event Broadcaster | `events.py` | 事件广播器 |
| Method Registry | `methods.py` | RPC 方法注册表 |

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      GatewayServer                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │  WebSocket  │  │   Method    │  │       Event         │  │
│  │   Handler   │  │  Registry   │  │    Broadcaster      │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
         ↑                   ↑                    ↑
         │                   │                    │
    ┌────┴────┐        ┌────┴────┐         ┌────┴────┐
    │  Hooks  │        │  Cron   │         │  Skills │
    │ Registry│        │  Tool   │         │ Manager │
    └─────────┘        └─────────┘         └─────────┘
```

## GatewayServer

Source: `src/lurkbot/gateway/server.py:49-62`

```python
class GatewayServer:
    """Gateway WebSocket 服务器"""

    VERSION = "0.1.0"
    PROTOCOL_VERSION = 1

    def __init__(self):
        self._connections: Set[GatewayConnection] = set()
        self._event_broadcaster = get_event_broadcaster()
        self._method_registry = get_method_registry()
```

## Protocol Frames

Source: `src/lurkbot/gateway/protocol/frames.py`

LurkBot Gateway 使用 JSON 帧协议进行通信。

### Error Codes

```python
class ErrorCode(str, Enum):
    """错误码枚举"""

    NOT_LINKED = "NOT_LINKED"        # 认证提供商未连接
    NOT_PAIRED = "NOT_PAIRED"        # 设备未配对
    AGENT_TIMEOUT = "AGENT_TIMEOUT"  # 代理操作超时
    INVALID_REQUEST = "INVALID_REQUEST"  # 无效请求
    UNAVAILABLE = "UNAVAILABLE"      # 服务暂时不可用
    METHOD_NOT_FOUND = "METHOD_NOT_FOUND"  # 方法不存在
    INTERNAL_ERROR = "INTERNAL_ERROR"  # 内部错误
```

### Client Info

```python
class ClientInfo(BaseModel):
    """客户端信息"""

    id: str
    display_name: str | None
    version: str
    platform: str
    mode: Literal["app", "web", "cli"]
```

### Connect Parameters (Hello Handshake)

Source: `src/lurkbot/gateway/protocol/frames.py:45-56`

```python
class ConnectParams(BaseModel):
    """连接参数 (hello 握手)"""

    min_protocol: int      # 最低支持的协议版本
    max_protocol: int      # 最高支持的协议版本
    client: ClientInfo     # 客户端信息
    caps: list[str] | None # 客户端能力
    auth: dict[str, str] | None  # 认证信息 (token, password)
```

### Server Info

```python
class ServerInfo(BaseModel):
    """服务器信息"""

    version: str           # 服务器版本
    host: str | None       # 主机名
    conn_id: str           # 连接 ID
```

### Features

```python
class Features(BaseModel):
    """服务器功能列表"""

    methods: list[str]     # 支持的 RPC 方法
    events: list[str]      # 支持的事件类型
```

### Frame Types

#### HelloOk Response

```python
class HelloOk(BaseModel):
    """Hello OK 响应帧"""

    type: Literal["hello-ok"] = "hello-ok"
    protocol: int          # 协议版本
    server: ServerInfo     # 服务器信息
    features: Features     # 功能列表
    snapshot: Snapshot     # 初始快照数据
```

#### Event Frame

```python
class EventFrame(BaseModel):
    """事件帧"""

    id: str
    type: Literal["event"] = "event"
    at: int                # 时间戳 (毫秒)
    event: str             # 事件名称
    payload: dict | None   # 事件数据
    session_key: str | None
```

#### Request Frame

```python
class RequestFrame(BaseModel):
    """请求帧"""

    id: str
    type: Literal["request"] = "request"
    method: str            # RPC 方法名
    params: dict | None    # 方法参数
    session_key: str | None
```

#### Response Frame

```python
class ResponseFrame(BaseModel):
    """响应帧"""

    id: str
    type: Literal["response"] = "response"
    result: dict | None    # 成功结果
    error: ErrorShape | None  # 错误信息
```

## Connection Handling

Source: `src/lurkbot/gateway/server.py:64-92`

```python
async def handle_connection(self, websocket: WebSocket) -> None:
    """处理 WebSocket 连接"""
    conn_id = str(uuid.uuid4())[:8]
    connection = GatewayConnection(websocket, conn_id)

    await websocket.accept()

    try:
        # 握手
        await self._handshake(connection)
        self._connections.add(connection)

        # 订阅事件
        subscriber = self._event_broadcaster.subscribe(
            lambda event: self._send_event(connection, event)
        )

        # 消息循环
        await self._message_loop(connection)

    except WebSocketDisconnect:
        logger.info(f"Gateway connection closed: {conn_id}")
    finally:
        self._connections.discard(connection)
```

## Handshake Process

Source: `src/lurkbot/gateway/server.py:94-122`

1. 客户端发送 `hello` 消息
2. 服务器解析连接参数
3. 服务器发送 `hello-ok` 响应，包含：
   - 协议版本
   - 服务器信息
   - 功能列表（支持的方法和事件）
   - 初始快照数据

```python
hello_ok = HelloOk(
    protocol=self.PROTOCOL_VERSION,
    server=ServerInfo(
        version=self.VERSION,
        host=None,
        conn_id=connection.conn_id,
    ),
    features=Features(
        methods=self._method_registry.list_methods(),
        events=["agent.*", "session.*", "cron.*", "config.*"],
    ),
    snapshot=Snapshot(),
)
```

## RPC Request Handling

Source: `src/lurkbot/gateway/server.py:135-169`

```python
async def _handle_request(self, connection: GatewayConnection, message: dict) -> None:
    """处理 RPC 请求"""
    request = RequestFrame(**message)

    try:
        result = await self._method_registry.invoke(
            request.method,
            params=request.params,
            session_key=request.session_key,
        )

        response = ResponseFrame(
            id=request.id,
            result=result,
        )

    except ValueError as e:
        response = ResponseFrame(
            id=request.id,
            error=ErrorShape(
                code=ErrorCode.METHOD_NOT_FOUND,
                message=str(e),
            ),
        )
```

## Starting the Gateway

### Foreground Mode

```bash
lurkbot gateway start
```

### Daemon Mode

```bash
lurkbot gateway start --daemon
```

### Custom Configuration

```bash
lurkbot gateway start \
  --host 0.0.0.0 \
  --port 8080 \
  --log-level debug
```

## WebSocket Protocol

### Connect to the Gateway

```javascript
const ws = new WebSocket('ws://127.0.0.1:18789');

ws.onopen = () => {
  // Send hello handshake
  ws.send(JSON.stringify({
    type: 'hello',
    minProtocol: 1,
    maxProtocol: 1,
    client: {
      id: 'my-client',
      version: '1.0.0',
      platform: 'web',
      mode: 'web'
    }
  }));
};

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  if (message.type === 'hello-ok') {
    console.log('Connected:', message.server);
    console.log('Features:', message.features);
  }
};
```

### Send RPC Request

```javascript
// Send request
ws.send(JSON.stringify({
  id: 'req-123',
  type: 'request',
  method: 'sessions.list',
  params: {}
}));

// Handle response
ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  if (message.type === 'response' && message.id === 'req-123') {
    if (message.error) {
      console.error('Error:', message.error);
    } else {
      console.log('Result:', message.result);
    }
  }
};
```

### Message Types

#### Request

```json
{
  "id": "req-123",
  "type": "request",
  "method": "sessions.list",
  "params": {},
  "sessionKey": "telegram:123456789:main"
}
```

#### Response

```json
{
  "id": "req-123",
  "type": "response",
  "result": { "sessions": [...] }
}
```

#### Event

```json
{
  "id": "evt-456",
  "type": "event",
  "at": 1706700000000,
  "event": "session.message",
  "payload": {
    "content": "Hello!",
    "role": "user"
  },
  "sessionKey": "telegram:123456789:main"
}
```

## Security

### Authentication

Enable token-based authentication:

```bash
LURKBOT_GATEWAY__AUTH_ENABLED=true
LURKBOT_GATEWAY__AUTH_TOKENS=token1,token2
```

### TLS/SSL

For production, use TLS:

```bash
LURKBOT_GATEWAY__TLS_ENABLED=true
LURKBOT_GATEWAY__TLS_CERT=/path/to/cert.pem
LURKBOT_GATEWAY__TLS_KEY=/path/to/key.pem
```

### Network Binding

For local-only access:

```bash
LURKBOT_GATEWAY__HOST=127.0.0.1
```

For network access (use with caution):

```bash
LURKBOT_GATEWAY__HOST=0.0.0.0
```

## Monitoring

### Health Check

```bash
curl http://127.0.0.1:18789/health
```

### Metrics

```bash
curl http://127.0.0.1:18789/metrics
```

### Logs

```bash
tail -f ~/.lurkbot/logs/gateway.log
```

## Troubleshooting

### "Address already in use"

Another process is using the port:

```bash
# Find the process
lsof -i :18789

# Use a different port
lurkbot gateway start --port 8080
```

### "Connection refused"

Gateway is not running:

```bash
lurkbot gateway status
lurkbot gateway start
```

### "Authentication failed"

Check your token:

```bash
echo $LURKBOT_GATEWAY__AUTH_TOKENS
```

---

## See Also

- [Daemon Mode](daemon.md) - Background operation
- [API Reference](../api/index.md) - Complete API documentation
- [Architecture](../developer/architecture.md) - Technical details
