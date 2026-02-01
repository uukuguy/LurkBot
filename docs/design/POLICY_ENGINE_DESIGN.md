# 策略引擎设计文档

## 概述

LurkBot 策略引擎提供基于策略的访问控制 (PBAC)，支持条件策略、权限继承和审计追踪。本文档描述策略引擎的架构设计、DSL 语法和使用指南。

**版本**: 1.0
**创建日期**: 2026-02-01
**状态**: 已实现

## 架构设计

### 核心组件

```
┌─────────────────────────────────────────────────────────────────┐
│                     策略引擎架构                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                   PolicyEngine (策略引擎)                 │   │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────────────┐  │   │
│  │  │ 策略评估   │  │ 冲突解决   │  │ 缓存管理          │  │   │
│  │  └────────────┘  └────────────┘  └────────────────────┘  │   │
│  └──────────────────────────────────────────────────────────┘   │
│           │                  │                     │             │
│  ┌────────▼───────┐  ┌───────▼───────┐  ┌─────────▼─────────┐  │
│  │  PolicyStore   │  │  PolicyCache  │  │  InheritanceManager│  │
│  │  (策略存储)    │  │  (评估缓存)   │  │  (权限继承)        │  │
│  └────────────────┘  └───────────────┘  └───────────────────┘  │
│           │                                        │             │
│  ┌────────▼────────────────────────────────────────▼───────────┐│
│  │                     Policy DSL (策略语言)                   ││
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  ││
│  │  │TimeCondition │  │ IPCondition  │  │AttributeCondition│  ││
│  │  └──────────────┘  └──────────────┘  └──────────────────┘  ││
│  └──────────────────────────────────────────────────────────────┘│
│                                                                   │
└───────────────────────────────────────────────────────────────────┘
```

### 评估流程

```
请求 → 上下文构建 → 缓存检查 → 策略匹配 → 条件评估 → 冲突解决 → 决策 → 审计
```

## 策略 DSL

### 策略定义

```python
from lurkbot.security import Policy, PolicyEffect, PolicyConditions

policy = Policy(
    name="工作时间访问策略",
    description="仅在工作时间允许访问",
    effect=PolicyEffect.ALLOW,
    principals=["role:developer", "group:engineering"],
    resources=["tool:*", "session:*"],
    actions=["read", "execute"],
    priority=100,
    enabled=True,
    conditions=PolicyConditions(
        time=TimeCondition(
            weekdays=[1, 2, 3, 4, 5],  # 周一到周五
            after="09:00",
            before="18:00"
        ),
        ip=IPCondition(
            allowed_cidrs=["10.0.0.0/8"]
        )
    ),
    tags=["security", "time-based"]
)
```

### 策略效果

| 效果 | 说明 | 使用场景 |
|------|------|---------|
| `ALLOW` | 允许操作 | 授权访问 |
| `DENY` | 拒绝操作 | 明确禁止 |

### 主体匹配

```python
# 通配符匹配
principals=["*"]                    # 所有主体
principals=["role:*"]              # 所有角色
principals=["user:alice"]           # 特定用户
principals=["tenant:tenant-123"]    # 特定租户
principals=["group:admin"]          # 特定组
```

### 资源匹配

```python
# 通配符匹配
resources=["*"]                     # 所有资源
resources=["tool:*"]               # 所有工具
resources=["model:claude-*"]       # Claude 系列模型
resources=["session:tenant-123/*"] # 租户所有会话
```

### 操作匹配

```python
# 操作列表
actions=["*"]                       # 所有操作
actions=["read", "write"]          # 读写操作
actions=["execute"]                # 执行操作
actions=["delete"]                 # 删除操作
```

## 条件系统

### 时间条件

```python
from lurkbot.security import TimeCondition

# 工作日工作时间
time_condition = TimeCondition(
    weekdays=[1, 2, 3, 4, 5],  # 周一(1)到周五(5)
    after="09:00",
    before="18:00"
)

# 仅周末
weekend_condition = TimeCondition(
    weekdays=[6, 7]  # 周六(6)和周日(7)
)

# 夜间维护窗口
maintenance_condition = TimeCondition(
    after="02:00",
    before="06:00"
)
```

### IP 条件

```python
from lurkbot.security import IPCondition

# CIDR 匹配
ip_condition = IPCondition(
    allowed_cidrs=["10.0.0.0/8", "192.168.0.0/16"]
)

# IP 白名单
ip_whitelist = IPCondition(
    allowed_ips=["1.2.3.4", "5.6.7.8"]
)

# 组合
ip_combined = IPCondition(
    allowed_cidrs=["10.0.0.0/8"],
    allowed_ips=["8.8.8.8"]  # 额外允许的 IP
)
```

### 属性条件

```python
from lurkbot.security import AttributeCondition

# 等于
eq_condition = AttributeCondition(
    key="tier",
    operator="eq",
    value="enterprise"
)

# 不等于
ne_condition = AttributeCondition(
    key="status",
    operator="ne",
    value="suspended"
)

# 包含于
in_condition = AttributeCondition(
    key="role",
    operator="in",
    value=["admin", "superuser"]
)

# 大于
gt_condition = AttributeCondition(
    key="quota_remaining",
    operator="gt",
    value=0
)

# 包含
contains_condition = AttributeCondition(
    key="features",
    operator="contains",
    value="advanced_ai"
)
```

### 条件组合

```python
from lurkbot.security import PolicyConditions

# 多条件组合（AND 逻辑）
conditions = PolicyConditions(
    time=TimeCondition(
        weekdays=[1, 2, 3, 4, 5],
        after="09:00",
        before="18:00"
    ),
    ip=IPCondition(
        allowed_cidrs=["10.0.0.0/8"]
    ),
    attributes=[
        AttributeCondition(
            key="tier",
            operator="in",
            value=["professional", "enterprise"]
        ),
        AttributeCondition(
            key="status",
            operator="eq",
            value="active"
        )
    ]
)
```

## 权限继承

### 继承节点

```python
from lurkbot.security import InheritanceManager, InheritanceNode

manager = InheritanceManager()

# 创建层次结构
await manager.add_node(InheritanceNode(
    id="tenant:company-a",
    node_type="tenant",
    granted_permissions={"access_company_data"}
))

await manager.add_node(InheritanceNode(
    id="group:engineering",
    node_type="group",
    parent_ids=["tenant:company-a"],
    granted_permissions={"deploy_code"}
))

await manager.add_node(InheritanceNode(
    id="user:alice",
    node_type="user",
    parent_ids=["group:engineering"],
    granted_permissions={"edit_profile"},
    denied_permissions={"delete_user"}  # 明确拒绝
))
```

### 权限解析

```python
# 解析用户有效权限
resolved = await manager.resolve_permissions("user:alice")

# 结果
print(resolved.granted)  # {"access_company_data", "deploy_code", "edit_profile"}
print(resolved.denied)   # {"delete_user"}

# 检查特定权限
has_access = resolved.has_permission("deploy_code")  # True
has_delete = resolved.has_permission("delete_user")  # False (被拒绝)
```

### 拒绝优先

拒绝权限始终优先于授予权限：

```python
# 角色授予 read/write/delete
await manager.add_node(InheritanceNode(
    id="role:user",
    node_type="role",
    granted_permissions={"read", "write", "delete"}
))

# 用户拒绝 delete
await manager.add_node(InheritanceNode(
    id="user:alice",
    node_type="user",
    parent_ids=["role:user"],
    denied_permissions={"delete"}
))

# 解析结果
resolved = await manager.resolve_permissions("user:alice")
print(resolved.has_permission("read"))    # True
print(resolved.has_permission("write"))   # True
print(resolved.has_permission("delete"))  # False (拒绝优先)
```

### 菱形继承

系统正确处理菱形继承（多路径继承）：

```
       A (perm_a)
      / \
     B   C
     (b) (c)
      \ /
       D
```

```python
# D 继承自 B 和 C，B 和 C 都继承自 A
resolved = await manager.resolve_permissions("role:d")
# perm_a 只计算一次，避免重复
assert "perm_a" in resolved.granted
assert "perm_b" in resolved.granted
assert "perm_c" in resolved.granted
```

### 循环检测

系统自动检测并阻止循环继承：

```python
await manager.add_node(InheritanceNode(id="role:a", node_type="role"))
await manager.add_node(InheritanceNode(id="role:b", node_type="role"))

await manager.set_parents("role:a", ["role:b"])

# 尝试创建循环
try:
    await manager.set_parents("role:b", ["role:a"])
except ValueError as e:
    print(e)  # "设置继承关系会产生循环: role:b -> role:a"
```

## 策略评估

### 评估上下文

```python
from lurkbot.security import EvaluationContext

context = EvaluationContext(
    principal="user:alice",
    resource="model:claude-opus-4-5",
    action="execute",
    tenant_id="tenant-123",
    principal_roles=["developer", "team-lead"],
    principal_groups=["engineering", "ai-team"],
    ip_address="10.0.1.100",
    environment={"tier": "professional"},
    request_time=datetime.now()
)
```

### 执行评估

```python
from lurkbot.security import PolicyEngine

engine = PolicyEngine()

# 添加策略
await engine.add_policy(policy1)
await engine.add_policy(policy2)

# 评估
decision = await engine.evaluate(context)

print(decision.effect)          # PolicyEffect.ALLOW
print(decision.matched_policy)  # "工作时间访问策略"
print(decision.conditions_met)  # True
print(decision.evaluation_time_ms)  # 0.5
```

### 快捷方法

```python
# 简化检查
allowed = await engine.is_allowed(
    principal="user:alice",
    resource="model:claude-opus-4-5",
    action="execute"
)

if not allowed:
    raise AccessDeniedError()
```

## 冲突解决

### 解决规则

1. **优先级规则**: 高优先级策略覆盖低优先级
2. **拒绝优先**: 同优先级下，DENY 优先于 ALLOW
3. **默认拒绝**: 无匹配策略时，默认拒绝

### 优先级示例

```python
# 低优先级：拒绝所有
policy_deny_all = Policy(
    name="deny-all",
    effect=PolicyEffect.DENY,
    principals=["*"],
    resources=["*"],
    actions=["*"],
    priority=10  # 低优先级
)

# 高优先级：管理员覆盖
policy_admin_override = Policy(
    name="admin-override",
    effect=PolicyEffect.ALLOW,
    principals=["role:admin"],
    resources=["*"],
    actions=["*"],
    priority=100  # 高优先级
)

# 管理员可以访问（高优先级覆盖低优先级）
```

### 同优先级示例

```python
# 同优先级：允许工具使用
policy_allow_tools = Policy(
    name="allow-tools",
    effect=PolicyEffect.ALLOW,
    principals=["*"],
    resources=["tool:*"],
    actions=["execute"],
    priority=50
)

# 同优先级：禁止危险工具
policy_deny_dangerous = Policy(
    name="deny-dangerous",
    effect=PolicyEffect.DENY,
    principals=["*"],
    resources=["tool:dangerous-*"],
    actions=["execute"],
    priority=50
)

# 危险工具被拒绝（同优先级下 DENY 优先）
```

## 缓存机制

### 缓存配置

```python
from lurkbot.security import PolicyEngine, PolicyCache

# 自定义缓存配置
cache = PolicyCache(
    max_size=1000,       # 最大缓存条目
    ttl_seconds=300      # 缓存过期时间（秒）
)

engine = PolicyEngine(cache=cache, enable_cache=True)
```

### 缓存失效

```python
# 添加/移除策略自动失效缓存
await engine.add_policy(new_policy)     # 自动失效
await engine.remove_policy("old-policy") # 自动失效

# 手动失效
engine._cache.invalidate()              # 全部失效
engine._cache.invalidate(cache_key)     # 单个失效
```

### 缓存统计

```python
stats = await engine.get_stats()
print(stats["cache"])
# {
#     "size": 150,
#     "max_size": 1000,
#     "hits": 8500,
#     "misses": 1500,
#     "hit_rate": 0.85
# }
```

## 审计追踪

### 注册审计处理器

```python
async def audit_handler(context: EvaluationContext, decision: PolicyDecision):
    await audit_logger.log(
        action="POLICY_EVALUATION",
        principal=context.principal,
        resource=context.resource,
        result="ALLOWED" if decision.allowed else "DENIED",
        policy=decision.matched_policy,
        details={
            "action": context.action,
            "tenant_id": context.tenant_id,
            "evaluation_time_ms": decision.evaluation_time_ms
        }
    )

engine.on_audit(audit_handler)
```

### 审计日志示例

```json
{
    "timestamp": "2026-02-01T10:30:00Z",
    "action": "POLICY_EVALUATION",
    "principal": "user:alice",
    "resource": "model:claude-opus-4-5",
    "result": "ALLOWED",
    "policy": "工作时间访问策略",
    "details": {
        "action": "execute",
        "tenant_id": "tenant-123",
        "evaluation_time_ms": 0.5
    }
}
```

## 集成指南

### 与 Agent Runtime 集成

```python
from lurkbot.security import PolicyEngine, EvaluationContext

async def run_agent_with_policy_check(
    context: AgentContext,
    policy_engine: PolicyEngine
) -> AgentRunResult:
    # 构建评估上下文
    eval_ctx = EvaluationContext(
        principal=f"user:{context.user_id}",
        resource=f"model:{context.model_id}",
        action="execute",
        tenant_id=context.tenant_id,
        principal_roles=context.user_roles,
        environment={
            "tier": context.tenant_tier,
            "session_id": context.session_id
        }
    )

    # 评估策略
    decision = await policy_engine.evaluate(eval_ctx)

    if not decision.allowed:
        return AgentRunResult(
            prompt_error=AccessDeniedError(decision.reason)
        )

    # 继续执行代理
    return await run_agent_internal(context)
```

### 与 Gateway 集成

```python
async def handle_request_with_policy(
    connection: GatewayConnection,
    method: str,
    params: dict
) -> Any:
    # 构建评估上下文
    eval_ctx = EvaluationContext(
        principal=f"tenant:{connection.tenant_id}",
        resource=f"method:{method}",
        action="invoke",
        tenant_id=connection.tenant_id,
        ip_address=connection.remote_ip
    )

    # 评估策略
    decision = await policy_engine.evaluate(eval_ctx)

    if not decision.allowed:
        return {"error": "ACCESS_DENIED", "reason": decision.reason}

    # 继续处理请求
    return await process_request(method, params)
```

### 与多租户集成

```python
async def create_tenant_policies(tenant: Tenant) -> list[Policy]:
    """为租户创建默认策略"""

    policies = []

    # 租户级别基础策略
    policies.append(Policy(
        name=f"tenant-{tenant.id}-base",
        effect=PolicyEffect.ALLOW,
        principals=[f"tenant:{tenant.id}"],
        resources=["*"],
        actions=["read"],
        priority=50
    ))

    # 根据级别添加策略
    if tenant.tier in [TenantTier.PROFESSIONAL, TenantTier.ENTERPRISE]:
        policies.append(Policy(
            name=f"tenant-{tenant.id}-advanced",
            effect=PolicyEffect.ALLOW,
            principals=[f"tenant:{tenant.id}"],
            resources=["tool:advanced-*", "model:*"],
            actions=["*"],
            priority=60
        ))

    return policies
```

## 最佳实践

### 1. 最小权限原则

```python
# 推荐：精确授权
Policy(
    principals=["role:data-analyst"],
    resources=["report:*"],
    actions=["read"]
)

# 不推荐：过度授权
Policy(
    principals=["role:data-analyst"],
    resources=["*"],
    actions=["*"]
)
```

### 2. 使用标签组织策略

```python
Policy(
    name="compliance-audit-policy",
    tags=["compliance", "audit", "gdpr"],
    # ...
)

# 按标签查询
audit_policies = await engine.list_policies(tag="audit")
```

### 3. 分层策略设计

```python
# 系统级：默认拒绝
Policy(name="system-deny-all", priority=1, effect=PolicyEffect.DENY)

# 租户级：基础权限
Policy(name="tenant-base", priority=50, effect=PolicyEffect.ALLOW)

# 用户级：特定权限
Policy(name="user-specific", priority=100, effect=PolicyEffect.ALLOW)

# 管理员：紧急覆盖
Policy(name="admin-override", priority=1000, effect=PolicyEffect.ALLOW)
```

### 4. 条件策略用于动态控制

```python
# 按时间控制
Policy(
    conditions=PolicyConditions(
        time=TimeCondition(weekdays=[1,2,3,4,5], after="09:00", before="18:00")
    )
)

# 按网络控制
Policy(
    conditions=PolicyConditions(
        ip=IPCondition(allowed_cidrs=["10.0.0.0/8"])
    )
)
```

### 5. 审计所有决策

```python
# 注册审计处理器
engine.on_audit(lambda ctx, dec: audit_logger.log(
    action="POLICY_DECISION",
    principal=ctx.principal,
    resource=ctx.resource,
    decision=dec.effect.value,
    policy=dec.matched_policy
))
```

## 性能优化

### 预热缓存

```python
# 启动时预热常见评估
common_contexts = [
    EvaluationContext(principal="tenant:default", resource="model:*", action="execute"),
    # ...
]

for ctx in common_contexts:
    await engine.evaluate(ctx)
```

### 批量评估

```python
# 批量评估多个操作
results = await engine.evaluate_batch([ctx1, ctx2, ctx3])
```

### 策略预编译

```python
# 策略添加时预编译匹配规则
await engine.add_policy(policy, precompile=True)
```

## 测试覆盖

| 模块 | 测试数量 | 覆盖率 |
|------|---------|-------|
| policy_dsl | 18 | 100% |
| policy_engine | 22 | 100% |
| inheritance | 24 | 100% |
| **总计** | **64** | **100%** |

## 相关文档

- [多租户设计](MULTI_TENANT_DESIGN.md) - 租户系统
- [动态配置指南](DYNAMIC_CONFIG_GUIDE.md) - 配置管理
- [架构设计](ARCHITECTURE_DESIGN.zh.md) - 系统架构

---

**最后更新**: 2026-02-01
