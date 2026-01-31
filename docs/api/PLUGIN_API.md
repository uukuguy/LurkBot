# LurkBot 插件 API 文档

## 目录

- [1. 核心接口](#1-核心接口)
- [2. 数据模型](#2-数据模型)
- [3. 插件管理器 API](#3-插件管理器-api)
- [4. 权限系统](#4-权限系统)
- [5. 事件系统](#5-事件系统)
- [6. 错误处理](#6-错误处理)

## 1. 核心接口

### 1.1 插件执行入口

每个插件必须实现 `execute()` 函数作为执行入口。

**函数签名**：

```python
async def execute(context: PluginExecutionContext) -> Any:
    """插件执行入口

    Args:
        context: 执行上下文，包含用户信息、输入数据、配置等

    Returns:
        执行结果（任意 JSON 可序列化的数据）

    Raises:
        Exception: 执行失败时抛出异常
    """
    pass
```

**参数说明**：

- `context`: `PluginExecutionContext` 类型，包含执行所需的所有上下文信息

**返回值**：

- 任意 JSON 可序列化的数据（dict, list, str, int, float, bool, None）
- 返回值会被自动封装为 `PluginExecutionResult`

**异常处理**：

- 插件抛出的异常会被沙箱捕获
- 异常信息会记录到 `PluginExecutionResult.error`
- 不会影响主程序运行

**示例**：

```python
async def execute(context: PluginExecutionContext) -> dict:
    # 获取输入参数
    city = context.input_data.get("city")
    if not city:
        raise ValueError("city parameter is required")

    # 执行业务逻辑
    weather_data = await fetch_weather(city)

    # 返回结果
    return {
        "city": city,
        "temperature": weather_data["temp"],
        "condition": weather_data["condition"]
    }
```

### 1.2 插件清单（plugin.json）

插件清单定义插件的元数据和配置。

**完整结构**：

```json
{
  "name": "plugin-name",
  "version": "1.0.0",
  "author": {
    "name": "Author Name",
    "email": "author@example.com",
    "url": "https://example.com"
  },
  "description": "插件描述",
  "plugin_type": "tool",
  "entry_point": "main.py",
  "enabled": true,
  "permissions": {
    "filesystem": false,
    "network": true,
    "exec": false,
    "channels": ["discord", "slack"]
  },
  "dependencies": [
    "httpx>=0.27.0",
    "pydantic>=2.0.0"
  ],
  "config": {
    "api_key": "your-api-key",
    "timeout": 30
  },
  "tags": ["utility", "api"]
}
```

**字段说明**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `name` | string | ✅ | 插件唯一标识符 |
| `version` | string | ✅ | 语义化版本号 |
| `author` | object | ✅ | 作者信息 |
| `description` | string | ✅ | 插件描述 |
| `plugin_type` | enum | ✅ | 插件类型（tool/middleware/hook/integration） |
| `entry_point` | string | ✅ | 入口文件路径 |
| `enabled` | boolean | ❌ | 是否启用（默认 true） |
| `permissions` | object | ✅ | 权限配置 |
| `dependencies` | array | ❌ | Python 依赖列表 |
| `config` | object | ❌ | 插件配置 |
| `tags` | array | ❌ | 标签列表 |

## 2. 数据模型

### 2.1 PluginExecutionContext

执行上下文，包含插件执行所需的所有信息。

**定义**：

```python
class PluginExecutionContext(BaseModel):
    """插件执行上下文"""

    # 请求信息
    user_id: str | None = None
    channel_id: str | None = None
    session_id: str | None = None

    # 输入数据
    input_data: dict[str, Any] = Field(default_factory=dict)
    parameters: dict[str, Any] = Field(default_factory=dict)

    # 环境信息
    environment: dict[str, Any] = Field(default_factory=dict)
    config: dict[str, Any] = Field(default_factory=dict)

    # 元数据
    metadata: dict[str, Any] = Field(default_factory=dict)
```

**字段说明**：

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `user_id` | str \| None | 用户 ID | "user-123" |
| `channel_id` | str \| None | 频道 ID | "discord" |
| `session_id` | str \| None | 会话 ID | "session-456" |
| `input_data` | dict | 输入数据 | {"city": "Beijing"} |
| `parameters` | dict | 执行参数 | {"format": "json"} |
| `environment` | dict | 环境变量 | {"DEBUG": true} |
| `config` | dict | 插件配置 | {"api_key": "xxx"} |
| `metadata` | dict | 额外元数据 | {"source": "cli"} |

**使用示例**：

```python
async def execute(context: PluginExecutionContext) -> dict:
    # 获取用户信息
    user_id = context.user_id or "anonymous"

    # 获取输入数据
    city = context.input_data.get("city", "Beijing")

    # 获取配置
    api_key = context.config.get("api_key")
    if not api_key:
        raise ValueError("api_key not configured")

    # 获取环境变量
    debug = context.environment.get("DEBUG", False)
    if debug:
        logger.debug(f"Fetching weather for {city}")

    # 执行业务逻辑
    weather = await fetch_weather(city, api_key)

    return {
        "user_id": user_id,
        "city": city,
        "weather": weather
    }
```

### 2.2 PluginExecutionResult

插件执行结果，由系统自动生成。

**定义**：

```python
class PluginExecutionResult(BaseModel):
    """插件执行结果"""

    success: bool
    result: Any | None = None
    error: str | None = None
    execution_time: float
    metadata: dict[str, Any] = Field(default_factory=dict)
```

**字段说明**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `success` | bool | 是否执行成功 |
| `result` | Any | 执行结果（插件返回值） |
| `error` | str \| None | 错误信息（失败时） |
| `execution_time` | float | 执行时间（秒） |
| `metadata` | dict | 结果元数据 |

**成功示例**：

```python
PluginExecutionResult(
    success=True,
    result={"temperature": 25, "condition": "sunny"},
    error=None,
    execution_time=0.523,
    metadata={}
)
```

**失败示例**：

```python
PluginExecutionResult(
    success=False,
    result=None,
    error="插件执行失败: ValueError: city parameter is required",
    execution_time=0.012,
    metadata={}
)
```

### 2.3 PluginConfig

插件配置模型。

**定义**：

```python
class PluginConfig(BaseModel):
    """插件配置"""

    name: str
    version: str
    author: dict[str, str]
    description: str
    plugin_type: PluginType
    entry_point: str
    enabled: bool = True
    permissions: PluginPermissions
    dependencies: list[str] = Field(default_factory=list)
    config: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
```

**字段说明**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `name` | str | 插件名称 |
| `version` | str | 版本号 |
| `author` | dict | 作者信息 |
| `description` | str | 插件描述 |
| `plugin_type` | PluginType | 插件类型 |
| `entry_point` | str | 入口文件 |
| `enabled` | bool | 是否启用 |
| `permissions` | PluginPermissions | 权限配置 |
| `dependencies` | list[str] | 依赖列表 |
| `config` | dict | 配置字典 |
| `tags` | list[str] | 标签列表 |

### 2.4 PluginType

插件类型枚举。

**定义**：

```python
class PluginType(str, Enum):
    """插件类型"""

    TOOL = "tool"              # 工具插件
    MIDDLEWARE = "middleware"  # 中间件插件
    HOOK = "hook"              # 钩子插件
    INTEGRATION = "integration"  # 集成插件
```

**类型说明**：

| 类型 | 说明 | 使用场景 |
|------|------|----------|
| `TOOL` | 提供独立工具功能 | 天气查询、计算器、翻译 |
| `MIDDLEWARE` | 处理数据流转换 | 数据清洗、格式转换、加密 |
| `HOOK` | 响应系统事件 | 日志记录、监控告警、审计 |
| `INTEGRATION` | 集成外部服务 | 数据库、API、云服务 |

### 2.5 PluginPermissions

权限配置模型。

**定义**：

```python
class PluginPermissions(BaseModel):
    """插件权限配置"""

    filesystem: bool = False
    network: bool = False
    exec: bool = False
    channels: list[str] = Field(default_factory=list)
```

**字段说明**：

| 字段 | 类型 | 说明 | 风险等级 |
|------|------|------|----------|
| `filesystem` | bool | 文件系统访问权限 | 中 |
| `network` | bool | 网络访问权限 | 中 |
| `exec` | bool | 命令执行权限 | 高 |
| `channels` | list[str] | 允许访问的频道列表 | 低 |

**示例**：

```python
# 只需要网络权限
permissions = PluginPermissions(
    network=True
)

# 需要文件系统和网络权限
permissions = PluginPermissions(
    filesystem=True,
    network=True
)

# 限制频道访问
permissions = PluginPermissions(
    network=True,
    channels=["discord", "slack"]
)
```

### 2.6 PluginEvent

插件事件模型。

**定义**：

```python
class PluginEvent(BaseModel):
    """插件事件"""

    plugin_name: str
    event_type: str
    timestamp: datetime
    message: str
    metadata: dict[str, Any] = Field(default_factory=dict)
```

**事件类型**：

| 事件类型 | 说明 | 触发时机 |
|---------|------|----------|
| `loaded` | 插件加载 | 插件成功加载时 |
| `unloaded` | 插件卸载 | 插件卸载时 |
| `enabled` | 插件启用 | 插件被启用时 |
| `disabled` | 插件禁用 | 插件被禁用时 |
| `executed` | 插件执行 | 插件执行完成时 |
| `error` | 执行错误 | 插件执行失败时 |

**示例**：

```python
PluginEvent(
    plugin_name="weather-plugin",
    event_type="executed",
    timestamp=datetime.now(),
    message="插件执行成功",
    metadata={
        "execution_time": 0.523,
        "user_id": "user-123"
    }
)
```

## 3. 插件管理器 API

### 3.1 PluginManager

插件管理器，负责插件的加载、执行和管理。

**初始化**：

```python
from lurkbot.plugins.manager import PluginManager

# 创建插件管理器
manager = PluginManager()

# 或使用全局单例
from lurkbot.plugins.manager import get_plugin_manager
manager = get_plugin_manager()
```

### 3.2 加载插件

**方法签名**：

```python
async def load_plugin(
    self,
    plugin_dir: Path,
    manifest: PluginConfig
) -> None:
    """加载单个插件

    Args:
        plugin_dir: 插件目录路径
        manifest: 插件配置

    Raises:
        PluginLoadError: 加载失败
    """
```

**使用示例**：

```python
from pathlib import Path
from lurkbot.plugins.schema_validator import load_plugin_manifest

# 加载插件清单
plugin_dir = Path(".plugins/weather-plugin")
manifest = load_plugin_manifest(plugin_dir)

# 加载插件
await manager.load_plugin(plugin_dir, manifest)
```

### 3.3 发现并加载所有插件

**方法签名**：

```python
async def discover_and_load_all(
    self,
    workspace_root: Path | None = None
) -> int:
    """发现并加载所有插件

    Args:
        workspace_root: 工作空间根目录（默认当前目录）

    Returns:
        成功加载的插件数量
    """
```

**使用示例**：

```python
from pathlib import Path

# 加载所有插件
workspace_root = Path.cwd()
loaded_count = await manager.discover_and_load_all(workspace_root)

print(f"成功加载 {loaded_count} 个插件")
```

### 3.4 执行插件

**方法签名**：

```python
async def execute_plugin(
    self,
    plugin_name: str,
    context: PluginExecutionContext
) -> PluginExecutionResult:
    """执行插件

    Args:
        plugin_name: 插件名称
        context: 执行上下文

    Returns:
        执行结果

    Raises:
        PluginNotFoundError: 插件不存在
        PluginDisabledError: 插件已禁用
    """
```

**使用示例**：

```python
# 创建执行上下文
context = PluginExecutionContext(
    user_id="user-123",
    channel_id="discord",
    input_data={"city": "Beijing"}
)

# 执行插件
result = await manager.execute_plugin("weather-plugin", context)

# 检查结果
if result.success:
    print(f"结果: {result.result}")
    print(f"耗时: {result.execution_time}秒")
else:
    print(f"错误: {result.error}")
```

### 3.5 启用/禁用插件

**方法签名**：

```python
async def enable_plugin(self, plugin_name: str) -> None:
    """启用插件"""

async def disable_plugin(self, plugin_name: str) -> None:
    """禁用插件"""
```

**使用示例**：

```python
# 启用插件
await manager.enable_plugin("weather-plugin")

# 禁用插件
await manager.disable_plugin("weather-plugin")
```

### 3.6 获取插件信息

**方法签名**：

```python
def get_plugin(self, plugin_name: str) -> PluginConfig | None:
    """获取插件配置"""

def list_plugins(self) -> list[PluginConfig]:
    """列出所有插件"""

def get_enabled_plugins(self) -> list[PluginConfig]:
    """获取已启用的插件"""
```

**使用示例**：

```python
# 获取单个插件
plugin = manager.get_plugin("weather-plugin")
if plugin:
    print(f"插件: {plugin.name} v{plugin.version}")

# 列出所有插件
all_plugins = manager.list_plugins()
for plugin in all_plugins:
    status = "启用" if plugin.enabled else "禁用"
    print(f"{plugin.name}: {status}")

# 获取已启用的插件
enabled_plugins = manager.get_enabled_plugins()
print(f"已启用 {len(enabled_plugins)} 个插件")
```

### 3.7 获取插件事件

**方法签名**：

```python
def get_events(
    self,
    plugin_name: str | None = None,
    limit: int = 100
) -> list[PluginEvent]:
    """获取插件事件

    Args:
        plugin_name: 插件名称（None 表示所有插件）
        limit: 返回事件数量限制

    Returns:
        事件列表（按时间倒序）
    """
```

**使用示例**：

```python
# 获取特定插件的事件
events = manager.get_events("weather-plugin", limit=10)
for event in events:
    print(f"{event.timestamp}: {event.event_type} - {event.message}")

# 获取所有插件的事件
all_events = manager.get_events(limit=50)
```

### 3.8 获取性能统计

**方法签名**：

```python
def get_performance_stats(
    self,
    plugin_name: str
) -> dict[str, Any]:
    """获取插件性能统计

    Returns:
        {
            "total_executions": int,
            "successful_executions": int,
            "failed_executions": int,
            "avg_execution_time": float,
            "min_execution_time": float,
            "max_execution_time": float
        }
    """
```

**使用示例**：

```python
stats = manager.get_performance_stats("weather-plugin")

print(f"总执行次数: {stats['total_executions']}")
print(f"成功次数: {stats['successful_executions']}")
print(f"失败次数: {stats['failed_executions']}")
print(f"平均耗时: {stats['avg_execution_time']:.3f}秒")
```

## 4. 权限系统

### 4.1 权限检查

插件执行前会自动检查权限。

**检查逻辑**：

```python
def check_permissions(
    plugin: PluginConfig,
    context: PluginExecutionContext
) -> None:
    """检查插件权限

    Raises:
        PermissionError: 权限不足
    """
    # 检查频道权限
    if plugin.permissions.channels:
        if context.channel_id not in plugin.permissions.channels:
            raise PermissionError(
                f"插件无权访问频道: {context.channel_id}"
            )
```

### 4.2 权限配置示例

**只读插件**（无特殊权限）：

```json
{
  "permissions": {
    "filesystem": false,
    "network": false,
    "exec": false
  }
}
```

**网络插件**（需要网络访问）：

```json
{
  "permissions": {
    "network": true
  }
}
```

**系统监控插件**（需要文件系统访问）：

```json
{
  "permissions": {
    "filesystem": true
  }
}
```

**高权限插件**（需要命令执行）：

```json
{
  "permissions": {
    "filesystem": true,
    "network": true,
    "exec": true
  }
}
```

**频道限制插件**：

```json
{
  "permissions": {
    "network": true,
    "channels": ["discord", "slack"]
  }
}
```

## 5. 事件系统

### 5.1 事件类型

| 事件类型 | 触发时机 | 元数据 |
|---------|----------|--------|
| `loaded` | 插件加载成功 | `{"plugin_dir": str}` |
| `unloaded` | 插件卸载 | `{}` |
| `enabled` | 插件启用 | `{}` |
| `disabled` | 插件禁用 | `{}` |
| `executed` | 插件执行成功 | `{"execution_time": float, "user_id": str}` |
| `error` | 插件执行失败 | `{"error": str, "user_id": str}` |

### 5.2 事件监听

**获取事件**：

```python
# 获取最近 10 个事件
events = manager.get_events("weather-plugin", limit=10)

for event in events:
    print(f"[{event.timestamp}] {event.event_type}: {event.message}")
    if event.metadata:
        print(f"  元数据: {event.metadata}")
```

**过滤事件**：

```python
# 只获取错误事件
error_events = [
    e for e in manager.get_events("weather-plugin")
    if e.event_type == "error"
]

# 统计执行次数
execution_count = len([
    e for e in manager.get_events("weather-plugin")
    if e.event_type == "executed"
])
```

## 6. 错误处理

### 6.1 异常类型

**PluginLoadError**：

```python
class PluginLoadError(Exception):
    """插件加载失败"""
    pass
```

**PluginNotFoundError**：

```python
class PluginNotFoundError(Exception):
    """插件不存在"""
    pass
```

**PluginDisabledError**：

```python
class PluginDisabledError(Exception):
    """插件已禁用"""
    pass
```

**PermissionError**：

```python
class PermissionError(Exception):
    """权限不足"""
    pass
```

### 6.2 错误处理示例

**捕获加载错误**：

```python
try:
    await manager.load_plugin(plugin_dir, manifest)
except PluginLoadError as e:
    logger.error(f"插件加载失败: {e}")
```

**捕获执行错误**：

```python
try:
    result = await manager.execute_plugin("weather-plugin", context)
except PluginNotFoundError:
    logger.error("插件不存在")
except PluginDisabledError:
    logger.error("插件已禁用")
except PermissionError as e:
    logger.error(f"权限不足: {e}")
```

**处理执行结果**：

```python
result = await manager.execute_plugin("weather-plugin", context)

if result.success:
    # 处理成功结果
    data = result.result
    logger.info(f"插件执行成功，耗时 {result.execution_time}秒")
else:
    # 处理失败结果
    logger.error(f"插件执行失败: {result.error}")
```

### 6.3 超时处理

插件执行有默认超时限制（30 秒）：

```python
# 在 plugin.json 中配置超时时间
{
  "config": {
    "max_execution_time": 60.0
  }
}
```

超时会被自动捕获并转换为错误结果：

```python
PluginExecutionResult(
    success=False,
    error="插件执行超时（30秒）",
    execution_time=30.0
)
```

---

## 附录

### A. 完整示例

**插件代码**（main.py）：

```python
from lurkbot.plugins.models import PluginExecutionContext
import httpx

async def execute(context: PluginExecutionContext) -> dict:
    """天气查询插件"""

    # 验证输入
    city = context.input_data.get("city")
    if not city:
        raise ValueError("city parameter is required")

    # 获取配置
    api_key = context.config.get("api_key")
    if not api_key:
        raise ValueError("api_key not configured")

    # 调用 API
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.openweathermap.org/data/2.5/weather",
            params={"q": city, "appid": api_key, "units": "metric"}
        )
        response.raise_for_status()
        data = response.json()

    # 返回结果
    return {
        "city": city,
        "temperature": data["main"]["temp"],
        "condition": data["weather"][0]["description"],
        "humidity": data["main"]["humidity"]
    }
```

**使用代码**：

```python
from lurkbot.plugins.manager import get_plugin_manager
from lurkbot.plugins.models import PluginExecutionContext

# 获取管理器
manager = get_plugin_manager()

# 加载所有插件
await manager.discover_and_load_all()

# 创建上下文
context = PluginExecutionContext(
    user_id="user-123",
    channel_id="discord",
    input_data={"city": "Beijing"}
)

# 执行插件
result = await manager.execute_plugin("weather-plugin", context)

# 处理结果
if result.success:
    print(f"温度: {result.result['temperature']}°C")
    print(f"天气: {result.result['condition']}")
else:
    print(f"错误: {result.error}")
```

### B. 类型定义

完整的类型定义可在以下文件中找到：

- `src/lurkbot/plugins/models.py` - 数据模型
- `src/lurkbot/plugins/manager.py` - 插件管理器
- `src/lurkbot/plugins/sandbox.py` - 沙箱执行器

### C. 相关文档

- [插件开发指南](../design/PLUGIN_DEVELOPMENT_GUIDE.md)
- [插件用户指南](../design/PLUGIN_USER_GUIDE.md)
- [插件系统设计](../design/PLUGIN_SYSTEM_DESIGN.md)

---

**文档版本**: v1.0.0
**最后更新**: 2026-02-01
