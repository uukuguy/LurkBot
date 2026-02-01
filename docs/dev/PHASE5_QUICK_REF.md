# Phase 5 快速参考

## 模块导入

```python
# 多租户
from lurkbot.tenants import (
    # 模型
    Tenant, TenantStatus, TenantTier,
    TenantQuota, TenantConfig, TenantUsage, TenantEvent,

    # 管理器
    TenantManager, QuotaManager, TenantIsolation,

    # 上下文
    TenantContext, get_current_tenant_id, set_current_tenant,

    # 装饰器
    require_tenant_context, inject_tenant_id,

    # 枚举
    QuotaType, QuotaCheckResult
)

# 策略引擎
from lurkbot.security import (
    # 策略引擎
    PolicyEngine, PolicyStore, PolicyCache,

    # 策略 DSL
    Policy, PolicyEffect, PolicyConditions,
    TimeCondition, IPCondition, AttributeCondition,
    EvaluationContext, PolicyDecision,

    # 权限继承
    InheritanceManager, InheritanceNode, ResolvedPermissions
)
```

## 常用操作

### 租户管理

```python
# 创建租户
manager = TenantManager()
tenant = await manager.create_tenant(
    name="example-corp",
    display_name="Example Corp",
    tier=TenantTier.PROFESSIONAL
)

# 检查配额
result = await manager.check_quota(
    tenant_id=tenant.id,
    quota_type=QuotaType.API_CALLS_PER_MINUTE
)
if not result.allowed:
    raise QuotaExceededError(result.reason)

# 使用上下文
async with manager.context(tenant.id):
    # 此作用域内所有操作自动使用租户上下文
    await do_work()
```

### 策略评估

```python
# 创建策略引擎
engine = PolicyEngine()

# 添加策略
policy = Policy(
    name="work-hours-access",
    effect=PolicyEffect.ALLOW,
    principals=["role:developer"],
    resources=["tool:*"],
    actions=["execute"],
    conditions=PolicyConditions(
        time=TimeCondition(
            weekdays=[1,2,3,4,5],
            after="09:00",
            before="18:00"
        )
    )
)
await engine.add_policy(policy)

# 评估
decision = await engine.evaluate(
    EvaluationContext(
        principal="user:alice",
        resource="tool:code-interpreter",
        action="execute"
    )
)

if not decision.allowed:
    raise AccessDeniedError(decision.reason)
```

### 权限继承

```python
# 创建继承管理器
manager = InheritanceManager()

# 构建继承层次
await manager.add_node(InheritanceNode(
    id="tenant:company-a",
    node_type="tenant",
    granted_permissions={"access_data"}
))

await manager.add_node(InheritanceNode(
    id="user:alice",
    node_type="user",
    parent_ids=["tenant:company-a"],
    granted_permissions={"edit_profile"}
))

# 解析权限
resolved = await manager.resolve_permissions("user:alice")
assert "access_data" in resolved.granted
assert "edit_profile" in resolved.granted
```

## 配额类型

| 类型 | 说明 |
|------|------|
| `AGENTS` | 代理数量 |
| `SESSIONS` | 会话数量 |
| `PLUGINS` | 插件数量 |
| `TOOLS` | 工具数量 |
| `TOKENS_PER_DAY` | 每日 token |
| `API_CALLS_PER_MINUTE` | API 速率 |
| `CONCURRENT_REQUESTS` | 并发请求 |
| `STORAGE_MB` | 存储空间 |
| `MESSAGES_PER_SESSION` | 会话消息数 |
| `CONTEXT_LENGTH` | 上下文长度 |

## 租户级别默认配额

| 级别 | 代理 | 会话 | API/分钟 | Token/天 |
|------|------|------|---------|---------|
| FREE | 3 | 10 | 100 | 10,000 |
| BASIC | 10 | 50 | 500 | 100,000 |
| PROFESSIONAL | 50 | 200 | 2,000 | 1,000,000 |
| ENTERPRISE | 无限 | 无限 | 10,000 | 10,000,000 |

## 策略条件

### 时间条件

```python
TimeCondition(
    weekdays=[1,2,3,4,5],  # 周一到周五
    after="09:00",
    before="18:00"
)
```

### IP 条件

```python
IPCondition(
    allowed_cidrs=["10.0.0.0/8"],
    allowed_ips=["1.2.3.4"]
)
```

### 属性条件

```python
AttributeCondition(
    key="tier",
    operator="in",
    value=["professional", "enterprise"]
)
```

操作符: `eq`, `ne`, `in`, `not_in`, `gt`, `lt`, `gte`, `lte`, `contains`

## 事件类型

### 租户事件

- `TENANT_CREATED` - 租户创建
- `TENANT_ACTIVATED` - 租户激活
- `TENANT_SUSPENDED` - 租户暂停
- `TENANT_EXPIRED` - 租户过期
- `TENANT_DELETED` - 租户删除
- `QUOTA_EXCEEDED` - 配额超限
- `TIER_UPGRADED` - 级别升级
- `CONFIG_UPDATED` - 配置更新

### 事件处理

```python
@manager.on_event(TenantEventType.QUOTA_EXCEEDED)
async def handle_quota_exceeded(event):
    await notify_admin(
        f"租户 {event.tenant_id} 配额超限"
    )
```

## 集成模式

### Agent Runtime

```python
async def run_agent_with_tenant(context, tenant_id):
    # 1. 检查配额
    await quota_manager.check_quota(
        tenant_id, QuotaType.API_CALLS
    )

    # 2. 评估策略
    decision = await policy_engine.evaluate(
        principal=tenant_id,
        resource=f"model:{context.model_id}",
        action="execute"
    )
    if not decision.allowed:
        raise AccessDeniedError()

    # 3. 执行
    async with tenant_manager.context(tenant_id):
        result = await run_agent(context)

    # 4. 记录使用
    await quota_manager.record_usage(
        tenant_id, QuotaType.API_CALLS, 1
    )

    return result
```

### Gateway Server

```python
async def handshake_with_tenant(connection, params):
    # 1. 验证租户
    tenant_id = params.get("tenant_id")
    tenant = await tenant_manager.get_tenant(tenant_id)

    if tenant.status != TenantStatus.ACTIVE:
        raise ValueError(f"租户未激活: {tenant_id}")

    # 2. 存储上下文
    connection.tenant_id = tenant_id

    # 3. 返回确认
    return {
        "type": "hello-ok",
        "tenant_id": tenant_id,
        "tier": tenant.tier.value
    }
```

## 测试统计

- **Total Tests**: 221
- **Pass Rate**: 100%
- **Modules**: 8
- **Code Lines**: ~2,300

## 相关文档

- [多租户设计](../design/MULTI_TENANT_DESIGN.md)
- [动态配置指南](../design/DYNAMIC_CONFIG_GUIDE.md)
- [策略引擎设计](../design/POLICY_ENGINE_DESIGN.md)
- [Phase 5 完成总结](PHASE5_COMPLETION_SUMMARY.md)

---

**更新日期**: 2026-02-01
