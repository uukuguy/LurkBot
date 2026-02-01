# 多租户系统设计文档

## 概述

LurkBot 多租户系统提供企业级的租户隔离、资源管理和权限控制功能。本文档描述多租户架构的设计决策、核心组件和集成方式。

**版本**: 1.0
**创建日期**: 2026-02-01
**状态**: 已实现

## 架构设计

### 核心组件

```
┌─────────────────────────────────────────────────────────────────┐
│                     多租户系统架构                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─────────────────┐    ┌─────────────────┐    ┌──────────────┐ │
│  │  TenantManager  │────│  QuotaManager   │────│  Isolation   │ │
│  │  (生命周期管理)  │    │  (配额管理)      │    │  (隔离上下文) │ │
│  └────────┬────────┘    └────────┬────────┘    └──────┬───────┘ │
│           │                      │                     │         │
│  ┌────────▼──────────────────────▼─────────────────────▼───────┐│
│  │                      TenantStorage                           ││
│  │                   (存储抽象层)                                ││
│  │    ┌─────────────┐    ┌─────────────┐    ┌────────────────┐ ││
│  │    │MemoryStorage│    │ FileStorage │    │DatabaseStorage │ ││
│  │    └─────────────┘    └─────────────┘    └────────────────┘ ││
│  └──────────────────────────────────────────────────────────────┘│
│                                                                   │
└───────────────────────────────────────────────────────────────────┘
              │                    │                     │
    ┌─────────▼───────┐  ┌─────────▼───────┐  ┌─────────▼───────┐
    │  Agent Runtime  │  │ Gateway Server  │  │  Policy Engine  │
    │  (代理运行时)    │  │  (网关服务器)    │  │  (策略引擎)     │
    └─────────────────┘  └─────────────────┘  └─────────────────┘
```

### 数据模型

#### 租户实体 (Tenant)

```python
class Tenant(BaseModel):
    """租户实体"""
    id: str                      # 唯一标识 (UUID)
    name: str                    # 租户名称（唯一）
    display_name: str            # 显示名称
    status: TenantStatus         # 状态
    tier: TenantTier            # 套餐级别
    trial_ends_at: datetime | None  # 试用结束时间
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, Any]     # 扩展元数据
```

#### 租户状态 (TenantStatus)

| 状态 | 说明 | 允许操作 |
|------|------|---------|
| `ACTIVE` | 正常激活 | 所有操作 |
| `TRIAL` | 试用期 | 有限操作 |
| `SUSPENDED` | 暂停 | 只读操作 |
| `EXPIRED` | 过期 | 无操作 |

#### 租户级别 (TenantTier)

| 级别 | 说明 | 预设配额 |
|------|------|---------|
| `FREE` | 免费版 | 代理: 3, 会话: 10, API: 100/分钟 |
| `BASIC` | 基础版 | 代理: 10, 会话: 50, API: 500/分钟 |
| `PROFESSIONAL` | 专业版 | 代理: 50, 会话: 200, API: 2000/分钟 |
| `ENTERPRISE` | 企业版 | 无限制 |

#### 配额模型 (TenantQuota)

```python
class TenantQuota(BaseModel):
    """租户配额"""
    tenant_id: str
    max_agents: int              # 最大代理数
    max_sessions: int            # 最大会话数
    max_plugins: int             # 最大插件数
    max_tools: int               # 最大工具数
    max_tokens_per_day: int      # 每日 token 限制
    max_api_calls_per_minute: int  # API 速率限制
    max_concurrent_requests: int   # 最大并发请求
    storage_quota_mb: int        # 存储配额 (MB)
```

## 配额管理

### 配额类型

系统支持 10 种配额类型：

| 配额类型 | 说明 | 检查时机 |
|----------|------|---------|
| `AGENTS` | 代理数量 | 创建代理时 |
| `SESSIONS` | 会话数量 | 创建会话时 |
| `PLUGINS` | 插件数量 | 安装插件时 |
| `TOOLS` | 工具数量 | 注册工具时 |
| `TOKENS_PER_DAY` | 每日 token | 代理执行时 |
| `API_CALLS_PER_MINUTE` | API 速率 | 每次请求时 |
| `CONCURRENT_REQUESTS` | 并发请求 | 请求开始时 |
| `STORAGE_MB` | 存储空间 | 存储操作时 |
| `MESSAGES_PER_SESSION` | 会话消息数 | 发送消息时 |
| `CONTEXT_LENGTH` | 上下文长度 | 构建提示时 |

### 配额检查结果

| 结果 | 说明 | 处理方式 |
|------|------|---------|
| `OK` | 配额充足 | 允许操作 |
| `WARNING` | 接近限制 (>80%) | 允许但警告 |
| `EXCEEDED` | 超出限制 | 软拒绝，返回错误 |
| `BLOCKED` | 硬限制 | 强制拒绝 |

### 使用示例

```python
from lurkbot.tenants import TenantManager, QuotaType

# 初始化
manager = TenantManager()

# 检查配额
result = await manager.check_quota(
    tenant_id="tenant-123",
    quota_type=QuotaType.API_CALLS_PER_MINUTE
)

if not result.allowed:
    raise QuotaExceededError(result.reason)

# 记录使用
await manager.record_usage(
    tenant_id="tenant-123",
    quota_type=QuotaType.API_CALLS_PER_MINUTE,
    amount=1
)
```

## 租户隔离

### 上下文隔离

使用 Python `contextvars` 实现异步上下文隔离：

```python
from lurkbot.tenants import TenantContext, set_current_tenant

# 设置当前租户上下文
tenant_ctx = TenantContext(
    tenant_id="tenant-123",
    tenant_name="Example Corp",
    tier=TenantTier.PROFESSIONAL
)
set_current_tenant(tenant_ctx)

# 在任何地方获取当前租户
from lurkbot.tenants import get_current_tenant_id
current_tenant = get_current_tenant_id()
```

### 上下文管理器

```python
from lurkbot.tenants import TenantManager

manager = TenantManager()

# 使用 async with 自动管理上下文
async with manager.context("tenant-123") as ctx:
    # 此作用域内所有操作自动使用租户上下文
    await do_something()
    # 自动检查配额、记录使用等
```

### 资源隔离

租户资源通过 `TenantIsolation` 类进行隔离：

```python
from lurkbot.tenants import TenantIsolation

isolation = TenantIsolation()

# 添加租户资源
await isolation.add_resource(
    tenant_id="tenant-123",
    resource_type="session",
    resource_id="session-abc",
    metadata={"created_by": "user-1"}
)

# 检查资源访问权限
has_access = await isolation.check_access(
    tenant_id="tenant-123",
    resource_type="session",
    resource_id="session-abc"
)
```

### 装饰器

```python
from lurkbot.tenants import require_tenant_context, inject_tenant_id

@require_tenant_context
async def protected_operation():
    """需要租户上下文的操作"""
    tenant_id = get_current_tenant_id()
    # ...

@inject_tenant_id
async def auto_inject_operation(tenant_id: str = None):
    """自动注入 tenant_id 参数"""
    # tenant_id 自动从上下文获取
    # ...
```

## 事件系统

### 事件类型

| 事件类型 | 触发时机 | 数据 |
|----------|---------|------|
| `TENANT_CREATED` | 租户创建 | tenant_id, tier |
| `TENANT_ACTIVATED` | 租户激活 | tenant_id |
| `TENANT_SUSPENDED` | 租户暂停 | tenant_id, reason |
| `TENANT_EXPIRED` | 租户过期 | tenant_id |
| `TENANT_DELETED` | 租户删除 | tenant_id |
| `QUOTA_EXCEEDED` | 配额超限 | tenant_id, quota_type, current, limit |
| `TIER_UPGRADED` | 级别升级 | tenant_id, old_tier, new_tier |
| `CONFIG_UPDATED` | 配置更新 | tenant_id, keys |

### 事件处理

```python
from lurkbot.tenants import TenantManager, TenantEventType

manager = TenantManager()

# 注册事件处理器
@manager.on_event(TenantEventType.QUOTA_EXCEEDED)
async def handle_quota_exceeded(event):
    # 发送告警
    await notify_admin(
        f"租户 {event.tenant_id} 配额超限: {event.data['quota_type']}"
    )

# 也可以使用方法注册
manager.on_event(TenantEventType.TENANT_CREATED, handler_func)
```

## 存储层

### 存储接口

```python
class TenantStorage(ABC):
    """租户存储抽象接口"""

    @abstractmethod
    async def create_tenant(self, tenant: Tenant) -> Tenant: ...

    @abstractmethod
    async def get_tenant(self, tenant_id: str) -> Tenant | None: ...

    @abstractmethod
    async def update_tenant(self, tenant: Tenant) -> Tenant | None: ...

    @abstractmethod
    async def delete_tenant(self, tenant_id: str) -> bool: ...

    # ... 配额、配置、使用记录等方法
```

### 存储实现

| 实现 | 特点 | 适用场景 |
|------|------|---------|
| `MemoryTenantStorage` | 内存存储，快速 | 开发、测试 |
| `FileTenantStorage` | 文件持久化 | 单机部署 |
| `DatabaseTenantStorage` | 数据库存储 | 生产环境 |

### 配置示例

```python
from lurkbot.tenants import TenantManager, FileTenantStorage

# 使用文件存储
storage = FileTenantStorage(data_dir="/var/lib/lurkbot/tenants")
manager = TenantManager(storage=storage)
```

## 集成指南

### Agent Runtime 集成

在 `src/lurkbot/agents/runtime.py` 中集成多租户：

```python
async def run_embedded_agent(
    context: AgentContext,
    tenant_id: str | None = None,
    ...
) -> AgentRunResult:
    # 1. 获取租户上下文
    tenant_id = tenant_id or get_current_tenant_id()
    if not tenant_id:
        raise ValueError("缺少租户上下文")

    # 2. 检查租户状态
    tenant = await tenant_manager.get_tenant(tenant_id)
    if tenant.status != TenantStatus.ACTIVE:
        raise TenantInactiveError(tenant_id)

    # 3. 检查配额
    quota_check = await tenant_manager.check_quota(
        tenant_id, QuotaType.API_CALLS_PER_MINUTE
    )
    if not quota_check.allowed:
        raise QuotaExceededError(quota_check.reason)

    # 4. 执行代理（在租户上下文中）
    async with tenant_manager.context(tenant_id):
        result = await _run_agent_internal(context, ...)

    # 5. 记录使用
    await tenant_manager.record_usage(
        tenant_id, QuotaType.API_CALLS_PER_MINUTE, 1
    )

    return result
```

### Gateway Server 集成

在 `src/lurkbot/gateway/server.py` 中集成多租户：

```python
async def _handshake(self, connection: GatewayConnection) -> None:
    hello_msg = await connection.receive_json()

    # 1. 提取租户 ID
    tenant_id = hello_msg.get("params", {}).get("tenant_id")

    # 2. 验证租户
    tenant = await self._tenant_manager.get_tenant(tenant_id)
    if not tenant or tenant.status != TenantStatus.ACTIVE:
        raise ValueError(f"无效租户: {tenant_id}")

    # 3. 存储到连接
    connection.tenant_id = tenant_id
    connection.tenant_tier = tenant.tier

    # 4. 发送确认
    await connection.send_json({
        "type": "hello-ok",
        "tenant_id": tenant_id,
        "tier": tenant.tier.value
    })
```

### 策略引擎集成

与权限策略引擎集成：

```python
from lurkbot.security import PolicyEngine, EvaluationContext

# 创建策略引擎
policy_engine = PolicyEngine()

# 评估租户权限
decision = await policy_engine.evaluate(
    EvaluationContext(
        principal=f"tenant:{tenant_id}",
        resource=f"model:{model_id}",
        action="execute",
        tenant_id=tenant_id
    )
)

if not decision.allowed:
    raise AccessDeniedError(decision.reason)
```

## 最佳实践

### 1. 始终使用上下文管理器

```python
# 推荐
async with manager.context(tenant_id):
    await operation()

# 不推荐（手动管理容易遗漏）
set_current_tenant(tenant_ctx)
try:
    await operation()
finally:
    set_current_tenant(None)
```

### 2. 配额检查在操作前

```python
# 在资源消耗前检查配额
if not await manager.can_proceed(tenant_id, QuotaType.API_CALLS):
    raise QuotaExceededError()

# 执行操作
await expensive_operation()

# 记录使用
await manager.record_usage(tenant_id, QuotaType.API_CALLS, 1)
```

### 3. 事件驱动的监控

```python
# 注册事件处理器进行监控
@manager.on_event(TenantEventType.QUOTA_EXCEEDED)
async def monitor_quota(event):
    metrics.increment("quota_exceeded", tags={
        "tenant_id": event.tenant_id,
        "quota_type": event.data["quota_type"]
    })
```

### 4. 优雅降级

```python
# 配额接近限制时降级
result = await manager.check_quota(tenant_id, QuotaType.TOKENS)
if result.status == QuotaCheckResult.WARNING:
    # 切换到更简洁的模式
    context.max_tokens = context.max_tokens // 2
```

## 性能考虑

### 缓存策略

- 租户信息缓存 TTL: 5 分钟
- 配额信息缓存 TTL: 1 分钟
- 使用 LRU 缓存避免内存膨胀

### 批量操作

```python
# 批量检查多个配额
results = await manager.check_all_quotas(tenant_id)
for quota_type, result in results.items():
    if not result.allowed:
        raise QuotaExceededError(quota_type)
```

### 异步处理

- 使用异步锁保证并发安全
- 事件处理异步执行，不阻塞主流程
- 使用统计批量更新减少 I/O

## 安全考虑

### 数据隔离

1. 所有资源操作必须验证租户 ID
2. 跨租户访问默认拒绝
3. 管理员操作需要特殊权限

### 审计日志

```python
# 所有租户操作记录审计
await audit_logger.log(
    action=AuditAction.TENANT_UPDATE,
    tenant_id=tenant_id,
    actor=current_user,
    details={"field": "tier", "old": "free", "new": "basic"}
)
```

### 密钥隔离

- 租户 API 密钥独立管理
- 加密存储敏感配置
- 定期轮换密钥

## 测试覆盖

| 模块 | 测试数量 | 覆盖率 |
|------|---------|-------|
| models | 28 | 100% |
| storage | 42 | 100% |
| quota | 21 | 100% |
| isolation | 27 | 100% |
| manager | 37 | 100% |
| **总计** | **155** | **100%** |

## 相关文档

- [动态配置指南](DYNAMIC_CONFIG_GUIDE.md) - 配置管理
- [策略引擎设计](POLICY_ENGINE_DESIGN.md) - 权限策略
- [架构设计](ARCHITECTURE_DESIGN.zh.md) - 系统架构

---

**最后更新**: 2026-02-01
