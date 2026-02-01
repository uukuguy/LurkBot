# 动态配置系统指南

## 概述

LurkBot 动态配置系统提供运行时配置更新能力，支持多数据源、配置验证、版本控制和热加载功能。本文档介绍配置系统的使用方法和最佳实践。

**版本**: 1.0
**创建日期**: 2026-02-01
**状态**: 已实现

## 核心概念

### 配置来源 (ConfigSource)

| 来源 | 优先级 | 说明 | 使用场景 |
|------|--------|------|---------|
| `DEFAULT` | 1 | 默认配置 | 系统内置默认值 |
| `FILE` | 2 | 配置文件 | 本地配置文件 |
| `ENV` | 3 | 环境变量 | 容器环境配置 |
| `DATABASE` | 4 | 数据库 | 持久化配置 |
| `REMOTE` | 5 | 远程配置中心 | Nacos/Consul/etcd |
| `OVERRIDE` | 6 | 运行时覆盖 | 临时配置覆盖 |

优先级：`OVERRIDE` > `REMOTE` > `DATABASE` > `ENV` > `FILE` > `DEFAULT`

### 配置事件 (ConfigEventType)

| 事件 | 触发时机 | 处理建议 |
|------|---------|---------|
| `LOADED` | 配置加载成功 | 记录日志 |
| `UPDATED` | 配置更新 | 刷新缓存 |
| `DELETED` | 配置删除 | 回退到默认值 |
| `VALIDATED` | 配置验证通过 | 应用配置 |
| `ROLLBACK` | 配置回滚 | 通知用户 |
| `ERROR` | 配置错误 | 告警 |

## 架构设计

```
┌─────────────────────────────────────────────────────────────┐
│               动态配置系统架构                               │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │          DynamicConfigManager (配置管理器)            │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────────┐  │  │
│  │  │ 配置加载器  │  │ 配置验证器  │  │ 配置监听器    │  │  │
│  │  └────────────┘  └────────────┘  └────────────────┘  │  │
│  └──────────────────────────────────────────────────────┘  │
│           │                  │                   │          │
│  ┌────────▼──────┐  ┌────────▼──────┐  ┌────────▼───────┐ │
│  │  ConfigStore  │  │  Validators   │  │  EventBus      │ │
│  │  (配置存储)    │  │  (验证器)      │  │  (事件总线)    │ │
│  └────────┬──────┘  └───────────────┘  └────────────────┘ │
│           │                                                 │
│  ┌────────▼─────────────────────────────────────────────┐  │
│  │              ConfigProviders (配置提供者)            │  │
│  │  ┌──────┐  ┌────────┐  ┌──────┐  ┌──────┐  ┌──────┐ │  │
│  │  │ File │  │  Env   │  │Nacos │  │Consul│  │ etcd │ │  │
│  │  └──────┘  └────────┘  └──────┘  └──────┘  └──────┘ │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

## 数据模型

### 配置条目 (ConfigEntry)

```python
from lurkbot.config.dynamic import ConfigEntry, ConfigSource

entry = ConfigEntry(
    key="model.default",
    value="claude-opus-4-5",
    source=ConfigSource.FILE,
    priority=2,
    version="v1",
    created_at=datetime.now(),
    updated_at=datetime.now(),
    metadata={"author": "admin"}
)
```

### 配置快照 (ConfigSnapshot)

```python
from lurkbot.config.dynamic import ConfigSnapshot

snapshot = ConfigSnapshot(
    version="v1.2.0",
    timestamp=datetime.now(),
    entries={
        "model.default": entry1,
        "api.rate_limit": entry2
    },
    metadata={"environment": "production"}
)
```

### 配置事件 (ConfigEvent)

```python
from lurkbot.config.dynamic import ConfigEvent, ConfigEventType

event = ConfigEvent(
    type=ConfigEventType.UPDATED,
    key="model.default",
    old_value="gpt-4",
    new_value="claude-opus-4-5",
    source=ConfigSource.REMOTE,
    timestamp=datetime.now()
)
```

## 基本使用

### 初始化配置管理器

```python
from lurkbot.config.dynamic import DynamicConfigManager, ConfigSource

# 创建配置管理器
config_manager = DynamicConfigManager()

# 加载配置文件
await config_manager.load_from_file("config.yaml")

# 从环境变量加载
await config_manager.load_from_env(prefix="LURKBOT_")
```

### 获取配置

```python
# 获取单个配置
model_id = await config_manager.get("model.default")

# 获取配置（带默认值）
timeout = await config_manager.get("api.timeout", default=30)

# 获取整个配置段
model_config = await config_manager.get_section("model")
# 返回: {"default": "claude-opus-4-5", "temperature": 0.7, ...}
```

### 设置配置

```python
# 设置配置
await config_manager.set(
    key="model.default",
    value="claude-opus-4-5",
    source=ConfigSource.OVERRIDE
)

# 批量设置
await config_manager.set_many({
    "model.default": "claude-opus-4-5",
    "model.temperature": 0.7,
    "api.timeout": 60
}, source=ConfigSource.FILE)
```

### 删除配置

```python
# 删除配置
await config_manager.delete("model.deprecated_key")

# 删除配置段
await config_manager.delete_section("deprecated")
```

## 配置监听

### 监听配置变化

```python
from lurkbot.config.dynamic import ConfigEventType

# 监听所有配置变化
@config_manager.on_change
async def on_config_change(event: ConfigEvent):
    print(f"配置变化: {event.key} = {event.new_value}")

# 监听特定键
@config_manager.on_change(key="model.default")
async def on_model_change(event: ConfigEvent):
    print(f"模型变化: {event.old_value} -> {event.new_value}")

# 监听特定事件类型
@config_manager.on_event(ConfigEventType.UPDATED)
async def on_update(event: ConfigEvent):
    # 刷新缓存
    await refresh_cache(event.key)
```

### 手动监听

```python
# 注册监听器
async def my_listener(event: ConfigEvent):
    if event.type == ConfigEventType.UPDATED:
        await handle_update(event)

config_manager.add_listener(my_listener)

# 取消监听
config_manager.remove_listener(my_listener)
```

## 配置验证

### 内置验证器

```python
from lurkbot.config.validators import (
    TypeValidator,
    RangeValidator,
    PatternValidator,
    EnumValidator
)

# 类型验证
config_manager.add_validator(
    "api.timeout",
    TypeValidator(int)
)

# 范围验证
config_manager.add_validator(
    "model.temperature",
    RangeValidator(min=0.0, max=2.0)
)

# 正则验证
config_manager.add_validator(
    "model.id",
    PatternValidator(r"^[a-z0-9-]+$")
)

# 枚举验证
config_manager.add_validator(
    "model.provider",
    EnumValidator(["openai", "anthropic", "google"])
)
```

### 自定义验证器

```python
from lurkbot.config.validators import ConfigValidator

class ModelAvailabilityValidator(ConfigValidator):
    """验证模型是否可用"""

    async def validate(self, key: str, value: Any) -> bool:
        if not key.startswith("model."):
            return True

        # 检查模型是否存在
        model_id = value
        available_models = await get_available_models()
        return model_id in available_models

# 注册自定义验证器
config_manager.add_validator(
    "model.default",
    ModelAvailabilityValidator()
)
```

## 配置提供者

### 文件提供者

```python
from lurkbot.config.providers import FileProvider

# YAML 文件
file_provider = FileProvider(
    file_path="config.yaml",
    format="yaml",
    watch=True  # 监听文件变化
)

await config_manager.add_provider(file_provider)
```

### 环境变量提供者

```python
from lurkbot.config.providers import EnvProvider

# 环境变量（带前缀）
env_provider = EnvProvider(
    prefix="LURKBOT_",
    separator="__"  # LURKBOT__MODEL__DEFAULT -> model.default
)

await config_manager.add_provider(env_provider)
```

### Nacos 提供者

```python
from lurkbot.config.providers import NacosProvider

# Nacos 配置中心
nacos_provider = NacosProvider(
    server_addresses="127.0.0.1:8848",
    namespace="lurkbot",
    group="DEFAULT_GROUP",
    data_id="lurkbot-config",
    username="nacos",
    password="nacos"
)

await config_manager.add_provider(nacos_provider)

# 自动监听配置变化
await nacos_provider.start_watch()
```

### Consul 提供者

```python
from lurkbot.config.providers import ConsulProvider

# Consul KV
consul_provider = ConsulProvider(
    host="127.0.0.1",
    port=8500,
    prefix="lurkbot/config",
    token="your-token"
)

await config_manager.add_provider(consul_provider)
```

### etcd 提供者

```python
from lurkbot.config.providers import EtcdProvider

# etcd
etcd_provider = EtcdProvider(
    host="127.0.0.1",
    port=2379,
    prefix="/lurkbot/config"
)

await config_manager.add_provider(etcd_provider)
```

## 配置热加载

### 文件监控

```python
from lurkbot.config.watcher import FileWatcher

# 创建文件监控器
watcher = FileWatcher(
    path="config.yaml",
    on_change=lambda: config_manager.reload_from_file("config.yaml")
)

# 启动监控
await watcher.start()

# 停止监控
await watcher.stop()
```

### 自动重载

```python
# 配置管理器自动重载
config_manager = DynamicConfigManager(
    auto_reload=True,
    reload_interval=60  # 每 60 秒检查一次
)

await config_manager.start()
```

## 配置版本控制

### 创建快照

```python
# 创建当前配置快照
snapshot = await config_manager.create_snapshot(
    version="v1.0.0",
    metadata={"author": "admin", "reason": "pre-deploy"}
)

# 保存快照到文件
await snapshot.save_to_file("snapshots/v1.0.0.yaml")
```

### 回滚配置

```python
# 回滚到指定版本
await config_manager.rollback_to_snapshot(
    version="v1.0.0"
)

# 从文件恢复
snapshot = await ConfigSnapshot.load_from_file("snapshots/v1.0.0.yaml")
await config_manager.restore_snapshot(snapshot)
```

### 版本对比

```python
# 对比两个版本
diff = await config_manager.compare_snapshots(
    version1="v1.0.0",
    version2="v1.1.0"
)

for key, (old_val, new_val) in diff.items():
    print(f"{key}: {old_val} -> {new_val}")
```

## 租户配置

### 租户级配置

```python
from lurkbot.config.tenant_config import TenantConfigManager

# 租户配置管理器
tenant_config = TenantConfigManager(config_manager)

# 获取租户配置
config = await tenant_config.get_config("tenant-123")

# 更新租户配置
await tenant_config.update_config(
    tenant_id="tenant-123",
    updates={
        "allowed_models": ["claude-opus-4-5", "gpt-4o"],
        "rate_limit_rpm": 600
    }
)
```

### 租户配置模型

```python
from lurkbot.config.tenant_config import TenantConfig

class TenantConfig(BaseModel):
    """租户配置"""

    # 模型访问控制
    allowed_models: list[str] = []
    allowed_providers: list[str] = []
    default_model: str = "claude-opus-4-5"

    # 功能开关
    features: dict[str, bool] = {}

    # 系统提示定制
    system_prompt_prepend: str = ""
    system_prompt_append: str = ""

    # 策略配置
    policy_ids: list[str] = []

    # 速率限制
    rate_limit_rpm: int = 600
    rate_limit_tpm: int = 90000

    # 工具访问
    allowed_tools: list[str] = []
    disabled_tools: list[str] = []
```

## 最佳实践

### 1. 分层配置

```yaml
# 默认配置 (config/default.yaml)
model:
  default: claude-opus-4-5
  temperature: 0.7

# 环境配置 (config/production.yaml)
model:
  default: ${MODEL_ID}  # 从环境变量覆盖

# 租户配置 (config/tenants/tenant-123.yaml)
model:
  default: gpt-4o  # 租户特定覆盖
```

### 2. 使用配置验证

```python
# 在设置配置前验证
async def safe_set_config(key: str, value: Any):
    # 验证
    if not await config_manager.validate(key, value):
        raise ValueError(f"配置验证失败: {key}")

    # 设置
    await config_manager.set(key, value)
```

### 3. 配置变更审计

```python
# 记录所有配置变更
@config_manager.on_event(ConfigEventType.UPDATED)
async def audit_config_change(event: ConfigEvent):
    await audit_logger.log(
        action="CONFIG_UPDATE",
        details={
            "key": event.key,
            "old_value": event.old_value,
            "new_value": event.new_value,
            "source": event.source.value
        }
    )
```

### 4. 故障转移

```python
# 远程配置失败时降级到本地
try:
    await config_manager.load_from_remote()
except Exception as e:
    logger.warning(f"远程配置加载失败，使用本地配置: {e}")
    await config_manager.load_from_file("config.yaml")
```

### 5. 配置缓存

```python
from functools import lru_cache

# 缓存配置查询
@lru_cache(maxsize=1000)
def get_cached_config(key: str) -> Any:
    return config_manager.get_sync(key)

# 配置变化时清除缓存
@config_manager.on_change
async def clear_config_cache(event: ConfigEvent):
    get_cached_config.cache_clear()
```

## 性能优化

### 批量操作

```python
# 批量获取
values = await config_manager.get_many([
    "model.default",
    "model.temperature",
    "api.timeout"
])

# 批量设置（一次性触发事件）
await config_manager.set_many({
    "model.default": "claude-opus-4-5",
    "model.temperature": 0.7
})
```

### 配置预加载

```python
# 启动时预加载常用配置
await config_manager.preload([
    "model.*",
    "api.*",
    "security.*"
])
```

### 异步刷新

```python
# 后台异步刷新配置
async def refresh_config_background():
    while True:
        await asyncio.sleep(60)
        await config_manager.refresh()

asyncio.create_task(refresh_config_background())
```

## 安全考虑

### 敏感配置加密

```python
from lurkbot.security import EncryptionManager

encryption = EncryptionManager()

# 加密敏感配置
encrypted_value = await encryption.encrypt("my-secret-key")
await config_manager.set("api.secret_key", encrypted_value)

# 读取时自动解密
secret_key = await encryption.decrypt(
    await config_manager.get("api.secret_key")
)
```

### 访问控制

```python
# 限制配置访问
@require_permission("config:write")
async def update_config(key: str, value: Any):
    await config_manager.set(key, value)

@require_permission("config:read")
async def get_config(key: str):
    return await config_manager.get(key)
```

### 审计日志

```python
# 完整的配置审计
await audit_logger.log(
    action=AuditAction.CONFIG_UPDATE,
    severity=AuditSeverity.WARNING,
    actor=current_user,
    resource=f"config:{key}",
    details={
        "old_value": old_value,
        "new_value": new_value,
        "source": source.value
    }
)
```

## 集成示例

### 与多租户集成

```python
from lurkbot.tenants import TenantManager
from lurkbot.config import DynamicConfigManager

class TenantAwareConfigManager:
    """租户感知的配置管理器"""

    def __init__(
        self,
        config_manager: DynamicConfigManager,
        tenant_manager: TenantManager
    ):
        self._config = config_manager
        self._tenants = tenant_manager

    async def get_tenant_config(
        self,
        tenant_id: str,
        key: str
    ) -> Any:
        """获取租户配置（租户配置优先于全局配置）"""

        # 1. 尝试租户级配置
        tenant_key = f"tenant.{tenant_id}.{key}"
        tenant_value = await self._config.get(tenant_key)
        if tenant_value is not None:
            return tenant_value

        # 2. 尝试租户级别配置
        tenant = await self._tenants.get_tenant(tenant_id)
        tier_key = f"tier.{tenant.tier.value}.{key}"
        tier_value = await self._config.get(tier_key)
        if tier_value is not None:
            return tier_value

        # 3. 使用全局默认配置
        return await self._config.get(key)
```

### 与策略引擎集成

```python
from lurkbot.security import PolicyEngine

# 配置变化时更新策略
@config_manager.on_change(key="policies.*")
async def reload_policies(event: ConfigEvent):
    policy_config = await config_manager.get_section("policies")
    await policy_engine.reload_policies(policy_config)
```

## 故障排查

### 常见问题

| 问题 | 原因 | 解决方案 |
|------|------|---------|
| 配置不生效 | 优先级低于已有配置 | 使用更高优先级的来源 |
| 远程配置连接失败 | 网络或认证问题 | 检查网络和凭据，启用本地降级 |
| 配置热加载失败 | 文件权限或格式错误 | 检查文件权限和 YAML 格式 |
| 配置验证失败 | 值不符合验证规则 | 检查验证器和配置值 |

### 调试模式

```python
# 启用详细日志
import logging
logging.getLogger("lurkbot.config").setLevel(logging.DEBUG)

# 查看配置来源
entry = await config_manager.get_entry("model.default")
print(f"来源: {entry.source}, 优先级: {entry.priority}")

# 导出当前配置
current_config = await config_manager.export()
print(json.dumps(current_config, indent=2))
```

## 相关文档

- [多租户设计](MULTI_TENANT_DESIGN.md) - 租户系统
- [策略引擎设计](POLICY_ENGINE_DESIGN.md) - 权限策略
- [架构设计](ARCHITECTURE_DESIGN.zh.md) - 系统架构

---

**最后更新**: 2026-02-01
