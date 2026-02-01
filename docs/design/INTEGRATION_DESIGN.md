# Phase 6 多租户系统集成设计

## 概述

Phase 6 将 Phase 5 实现的多租户系统和策略引擎集成到 LurkBot 核心组件中。通过集成基础设施、守卫类和中间件，实现对租户的完整支持。

## 架构设计

### 系统架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                      HTTP/WebSocket 请求                        │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│              TenantMiddleware (FastAPI)                          │
│  • 从 Header/Query 提取 tenant_id                               │
│  • 验证租户状态                                                  │
│  • 设置租户上下文                                                │
└────────────────────────┬────────────────────────────────────────┘
                         │
              ┌──────────┴──────────┐
              │                     │
              ▼                     ▼
      ┌──────────────────┐  ┌────────────────────┐
      │  Agent Runtime   │  │  Gateway Server    │
      │                  │  │                    │
      │ • 租户验证       │  │ • 租户验证         │
      │ • 配额检查       │  │ • 策略评估         │
      │ • Token 记录     │  │ • RPC 方法调用     │
      └────────┬─────────┘  └────────┬───────────┘
               │                     │
      ┌────────┴─────────────────────┴────────┐
      │                                        │
      ▼                                        ▼
┌──────────────────────────┐       ┌─────────────────────────┐
│   QuotaGuard             │       │   PolicyGuard           │
│                          │       │                         │
│ • 配额检查               │       │ • 策略评估              │
│ • 速率限制               │       │ • 权限验证              │
│ • 并发控制               │       │ • 审计追踪              │
│ • Token 使用量记录       │       │                         │
└──────────┬───────────────┘       └────────┬────────────────┘
           │                                 │
           ▼                                 ▼
    ┌────────────────────┐        ┌──────────────────────┐
    │  TenantManager     │        │  PolicyEngine        │
    │  QuotaManager      │        │                      │
    │  TenantIsolation   │        │ • 策略存储           │
    │                    │        │ • 策略评估           │
    │ • 租户 CRUD        │        │ • 缓存和优化         │
    │ • 状态管理         │        │                      │
    │ • 配额管理         │        │                      │
    └────────────────────┘        └──────────────────────┘
```

## 核心组件

### 1. 错误定义 (`errors.py`)

定义租户相关的错误类型：

- **TenantErrorCode**: 错误码枚举
  - TENANT_NOT_FOUND: 租户不存在
  - TENANT_INACTIVE: 租户不可用
  - QUOTA_EXCEEDED: 配额超限
  - RATE_LIMITED: 速率超限
  - POLICY_DENIED: 策略拒绝

- **错误类**
  - TenantError: 基类
  - QuotaExceededError: 配额超限
  - RateLimitedError: 速率限制
  - ConcurrentLimitError: 并发限制
  - PolicyDeniedError: 策略拒绝
  - TenantNotFoundError: 租户不存在
  - TenantInactiveError: 租户不可用

### 2. 守卫类 (`guards.py`)

提供配额和策略检查的上下文管理器：

#### QuotaGuard

```python
class QuotaGuard:
    async def check_and_record(
        tenant_id: str,
        quota_type: QuotaType,
        amount: float = 1,
    ) -> None
        """检查配额并记录使用量"""

    async def check_rate_limit(tenant_id: str) -> None
        """检查 API 速率限制"""

    @asynccontextmanager
    async def rate_limit_context(tenant_id: str) -> AsyncIterator
        """速率限制上下文管理器"""

    async def acquire_concurrent_slot(tenant_id: str) -> bool
        """获取并发槽位"""

    async def release_concurrent_slot(tenant_id: str) -> None
        """释放并发槽位"""

    @asynccontextmanager
    async def concurrent_slot_context(tenant_id: str) -> AsyncIterator
        """并发槽位上下文管理器"""

    async def record_token_usage(
        tenant_id: str,
        input_tokens: int,
        output_tokens: int,
    ) -> None
        """记录 Token 使用量"""
```

#### PolicyGuard

```python
class PolicyGuard:
    async def check_permission(
        principal: str,
        resource: str,
        action: str,
        tenant_id: str | None = None,
        **kwargs
    ) -> bool
        """检查权限"""

    async def require_permission(
        principal: str,
        resource: str,
        action: str,
        tenant_id: str | None = None,
        **kwargs
    ) -> None
        """要求权限（失败抛异常）"""

    async def evaluate(
        principal: str,
        resource: str,
        action: str,
        tenant_id: str | None = None,
        **kwargs
    ) -> dict
        """评估策略并返回详细结果"""
```

### 3. 中间件 (`middleware.py`)

FastAPI 中间件用于租户验证和上下文设置：

```python
class TenantMiddleware(BaseHTTPMiddleware):
    """从请求中提取 tenant_id 并设置租户上下文

    支持多种提取方式：
    1. X-Tenant-ID Header
    2. tenant_id Query 参数
    """
```

## 集成实现

### Agent Runtime 集成

**文件**: `src/lurkbot/agents/types.py`, `src/lurkbot/agents/runtime.py`, `src/lurkbot/agents/api.py`

#### 1. AgentContext 扩展

```python
@dataclass
class AgentContext:
    # ... 现有字段 ...
    tenant_id: str | None = None  # 租户 ID
```

#### 2. ChatRequest 扩展

```python
class ChatRequest(BaseModel):
    # ... 现有字段 ...
    tenant_id: str | None = Field(None, description="租户标识")
```

#### 3. 运行时流程

在 `run_embedded_agent()` 中添加租户检查：

```
Step 0: 租户验证和配额检查
  ├─ 检查速率限制
  ├─ 获取并发槽位
  └─ 失败时返回错误

Step 1-5: 正常执行流程（现有）

Step 6: 记录 Token 使用量
  └─ 调用 QuotaGuard.record_token_usage()

Finally: 释放并发槽位
  └─ 调用 QuotaGuard.release_concurrent_slot()
```

### Gateway Server 集成

**文件**: `src/lurkbot/gateway/server.py`

#### 1. 连接上下文扩展

```python
class GatewayConnection:
    tenant_id: str | None = None  # 租户标识
```

#### 2. 握手验证

在 `_handshake()` 中：

```
1. 从 auth 参数中提取 tenant_id
2. 验证租户存在且活跃
3. 保存到连接对象中
```

#### 3. RPC 方法调用

在 `_handle_request()` 中：

```
1. 如果有 tenant_id，执行策略评估
2. 检查权限：principal=tenant:{id}, resource=method:{name}, action=execute
3. 允许则执行，拒绝则返回错误
```

## 使用示例

### 1. Agent 调用示例

```python
from lurkbot.agents.api import ChatRequest, create_chat_api
from lurkbot.agents.types import SessionType

# 创建 API
app = create_chat_api()

# 发送带 tenant_id 的请求
request = ChatRequest(
    message="Hello, world!",
    session_id="session_123",
    tenant_id="tenant_abc",
    provider="anthropic",
    model="claude-sonnet-4-20250514",
)

# API 自动处理租户验证和配额检查
response = await app.chat_endpoint(request)
```

### 2. Gateway 连接示例

```javascript
// WebSocket 连接时指定 tenant_id
const message = {
    type: "hello",
    minProtocol: 1,
    maxProtocol: 1,
    client: {
        id: "client_123",
        version: "1.0.0",
        platform: "web",
        mode: "web"
    },
    auth: {
        tenant_id: "tenant_abc"  // 指定租户
    }
};

ws.send(JSON.stringify(message));
```

### 3. 配额检查示例

```python
from lurkbot.tenants import (
    TenantManager,
    MemoryTenantStorage,
    QuotaType,
    get_quota_guard,
    configure_guards,
)

# 配置全局守卫
tenant_manager = TenantManager(storage=MemoryTenantStorage())
configure_guards(tenant_manager=tenant_manager)

quota_guard = get_quota_guard()

# 检查配额
try:
    await quota_guard.check_and_record(
        tenant_id="tenant_abc",
        quota_type=QuotaType.API_CALLS_PER_DAY,
        amount=1,
    )
except QuotaExceededError as e:
    print(f"配额超限: {e.message}")

# 使用上下文管理器
async with quota_guard.concurrent_slot_context("tenant_abc"):
    # 执行需要并发控制的操作
    pass
```

### 4. 策略评估示例

```python
from lurkbot.tenants import get_policy_guard

policy_guard = get_policy_guard()

# 检查权限
allowed = await policy_guard.check_permission(
    principal="tenant:tenant_abc",
    resource="method:chat",
    action="execute",
)

# 要求权限（失败抛异常）
try:
    await policy_guard.require_permission(
        principal="tenant:tenant_abc",
        resource="method:admin.delete",
        action="execute",
    )
except PolicyDeniedError as e:
    print(f"权限拒绝: {e.message}")

# 获取详细评估结果
result = await policy_guard.evaluate(
    principal="tenant:tenant_abc",
    resource="method:chat",
    action="execute",
)
print(f"允许: {result['allowed']}")
print(f"原因: {result['reason']}")
```

### 5. FastAPI 集成示例

```python
from fastapi import FastAPI
from lurkbot.agents.api import create_chat_api
from lurkbot.tenants import (
    TenantManager,
    MemoryTenantStorage,
    TenantMiddleware,
    configure_guards,
)

# 创建应用
app = create_chat_api()

# 设置租户管理器
tenant_manager = TenantManager(storage=MemoryTenantStorage())

# 添加租户中间件
app.add_middleware(
    TenantMiddleware,
    tenant_manager=tenant_manager,
    required=True,  # 要求 tenant_id
)

# 配置全局守卫
configure_guards(tenant_manager=tenant_manager)
```

## 错误处理指南

### 常见错误和处理方式

#### 1. TenantNotFoundError

```python
try:
    await quota_guard.check_rate_limit("unknown_tenant")
except TenantNotFoundError as e:
    # 返回 404 错误
    return JSONResponse(
        status_code=404,
        content={"error": e.to_dict()}
    )
```

#### 2. QuotaExceededError

```python
try:
    await quota_guard.check_and_record(tenant_id, quota_type, amount)
except QuotaExceededError as e:
    # 返回 429 Too Many Requests
    return JSONResponse(
        status_code=429,
        content={"error": e.to_dict()},
        headers={"Retry-After": "3600"}  # 1 小时后重试
    )
```

#### 3. RateLimitedError

```python
try:
    await quota_guard.check_rate_limit(tenant_id)
except RateLimitedError as e:
    # 返回 429 Too Many Requests
    return JSONResponse(
        status_code=429,
        content={"error": e.to_dict()},
        headers={
            "Retry-After": str(e.retry_after_seconds or 60)
        }
    )
```

#### 4. PolicyDeniedError

```python
try:
    await policy_guard.require_permission(principal, resource, action)
except PolicyDeniedError as e:
    # 返回 403 Forbidden
    return JSONResponse(
        status_code=403,
        content={"error": e.to_dict()}
    )
```

## 测试覆盖

### 单元测试

- `tests/integration/test_tenant_integration.py`: 基本集成测试
- `tests/integration/test_quota_guards.py`: 配额守卫详细测试
- `tests/integration/test_policy_guards.py`: 策略守卫详细测试

### 测试运行

```bash
# 运行所有集成测试
python -m pytest tests/integration/ -xvs

# 运行特定测试
python -m pytest tests/integration/test_quota_guards.py -xvs

# 带覆盖率
python -m pytest tests/integration/ --cov=src/lurkbot/tenants --cov-report=term-missing
```

## 性能考虑

### 1. 配额检查缓存

QuotaManager 使用内存缓存存储使用量数据，支持快速查询。

### 2. 策略评估缓存

PolicyEngine 包含可配置的评估结果缓存（TTL: 5 分钟，最大 1000 条记录）。

### 3. 并发控制

通过异步锁保护共享资源，避免竞态条件。

## 安全考虑

### 1. 租户隔离

- 每个租户有独立的上下文和资源
- 租户之间不能访问彼此的数据

### 2. 权限验证

- 所有操作都经过策略评估
- 默认拒绝原则：无匹配策略时拒绝

### 3. 审计追踪

- 所有策略评估都可以记录审计日志
- PolicyEngine 支持审计处理器注册

## 向后兼容性

所有集成都是**完全向后兼容**的：

- `tenant_id` 为可选字段，不提供时系统正常运行
- 无 tenant_id 的请求绕过租户检查
- 无策略引擎时默认允许

## 下一步工作

### Phase 7: 监控和分析

- 实现租户使用统计仪表板
- 添加实时监控告警
- 支持自定义配额规则

### Phase 8: 高级功能

- 支持租户间资源共享
- 实现动态配额调整
- 添加容量规划工具

## 相关文件清单

| 文件 | 描述 |
|------|------|
| `src/lurkbot/tenants/errors.py` | 错误定义 |
| `src/lurkbot/tenants/guards.py` | 守卫类 |
| `src/lurkbot/tenants/middleware.py` | FastAPI 中间件 |
| `src/lurkbot/agents/types.py` | Agent 类型（修改） |
| `src/lurkbot/agents/runtime.py` | Agent 运行时（修改） |
| `src/lurkbot/agents/api.py` | Agent API（修改） |
| `src/lurkbot/gateway/server.py` | Gateway 服务器（修改） |
| `tests/integration/test_tenant_integration.py` | 集成测试 |
| `tests/integration/test_quota_guards.py` | 配额守卫测试 |
| `tests/integration/test_policy_guards.py` | 策略守卫测试 |
