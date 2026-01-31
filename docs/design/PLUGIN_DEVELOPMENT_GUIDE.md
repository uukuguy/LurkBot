# LurkBot 插件开发指南

## 1. 快速开始

### 1.1 创建第一个插件

**步骤 1：创建插件目录**

```bash
mkdir -p plugins/my-first-plugin
cd plugins/my-first-plugin
```

**步骤 2：创建 plugin.json**

```json
{
  "name": "my-first-plugin",
  "version": "1.0.0",
  "author": {
    "name": "Your Name",
    "email": "your.email@example.com"
  },
  "description": "我的第一个 LurkBot 插件",
  "plugin_type": "tool",
  "entry_point": "main.py",
  "enabled": true,
  "permissions": {
    "filesystem": false,
    "network": false,
    "exec": false,
    "channels": []
  },
  "dependencies": [],
  "tags": ["example", "tutorial"]
}
```

**步骤 3：创建 main.py**

```python
"""我的第一个插件"""

from lurkbot.plugins.models import PluginExecutionContext


async def execute(context: PluginExecutionContext) -> dict:
    """插件执行入口

    Args:
        context: 执行上下文

    Returns:
        执行结果（任意 JSON 可序列化的数据）
    """
    user_id = context.user_id or "unknown"
    return {
        "message": f"Hello from my-first-plugin!",
        "user_id": user_id,
        "status": "success"
    }
```

**步骤 4：测试插件**

```python
# tests/test_my_first_plugin.py
import pytest
from pathlib import Path
from lurkbot.plugins.manager import PluginManager
from lurkbot.plugins.models import PluginExecutionContext
from lurkbot.plugins.schema_validator import load_plugin_manifest


@pytest.mark.asyncio
async def test_my_first_plugin():
    # 加载插件
    plugin_dir = Path("plugins/my-first-plugin")
    manifest = load_plugin_manifest(plugin_dir)

    manager = PluginManager()
    await manager.load_plugin(plugin_dir, manifest)

    # 执行插件
    context = PluginExecutionContext(user_id="test-user")
    result = await manager.execute_plugin("my-first-plugin", context)

    # 验证结果
    assert result.success is True
    assert result.result["status"] == "success"
    assert "Hello from my-first-plugin!" in result.result["message"]
```

## 2. 插件清单（plugin.json）

### 2.1 完整字段说明

```json
{
  "name": "plugin-name",           // 插件名称（必填，唯一标识）
  "version": "1.0.0",              // 版本号（必填，语义化版本）
  "author": {                      // 作者信息（必填）
    "name": "Author Name",         // 作者姓名
    "email": "author@example.com", // 作者邮箱（可选）
    "url": "https://example.com"   // 作者网站（可选）
  },
  "description": "插件描述",        // 插件描述（必填）
  "plugin_type": "tool",           // 插件类型（必填）
  "entry_point": "main.py",        // 入口文件（必填）
  "enabled": true,                 // 是否启用（可选，默认 true）
  "permissions": {                 // 权限配置（必填）
    "filesystem": false,           // 文件系统访问
    "network": true,               // 网络访问
    "exec": false,                 // 命令执行
    "channels": ["discord"]        // 允许的频道列表
  },
  "dependencies": [                // Python 依赖（可选）
    "requests>=2.28.0",
    "pydantic>=2.0.0"
  ],
  "tags": ["utility", "api"]       // 标签（可选）
}
```

### 2.2 插件类型

```python
class PluginType(str, Enum):
    TOOL = "tool"              # 工具插件：提供独立功能
    MIDDLEWARE = "middleware"  # 中间件插件：处理数据流
    HOOK = "hook"              # 钩子插件：响应事件
    INTEGRATION = "integration"  # 集成插件：连接外部服务
```

**选择指南**：
- **TOOL**：提供独立的工具功能（如天气查询、计算器）
- **MIDDLEWARE**：在数据流中进行转换或增强（如数据清洗、格式转换）
- **HOOK**：响应系统事件（如日志记录、监控告警）
- **INTEGRATION**：集成第三方服务（如数据库、API）

### 2.3 权限配置

#### filesystem（文件系统访问）

```json
{
  "permissions": {
    "filesystem": true
  }
}
```

**用途**：读写本地文件、访问目录

**示例**：
```python
async def execute(context: PluginExecutionContext) -> dict:
    # 需要 filesystem 权限
    with open("data.txt", "r") as f:
        content = f.read()
    return {"content": content}
```

#### network（网络访问）

```json
{
  "permissions": {
    "network": true
  }
}
```

**用途**：发起 HTTP 请求、连接外部 API

**示例**：
```python
import httpx

async def execute(context: PluginExecutionContext) -> dict:
    # 需要 network 权限
    async with httpx.AsyncClient() as client:
        response = await client.get("https://api.example.com/data")
        return response.json()
```

#### exec（命令执行）

```json
{
  "permissions": {
    "exec": true
  }
}
```

**用途**：执行系统命令

**⚠️ 警告**：此权限风险较高，仅在必要时使用

**示例**：
```python
import subprocess

async def execute(context: PluginExecutionContext) -> dict:
    # 需要 exec 权限
    result = subprocess.run(["ls", "-l"], capture_output=True, text=True)
    return {"output": result.stdout}
```

#### channels（频道访问）

```json
{
  "permissions": {
    "channels": ["discord", "slack"]
  }
}
```

**用途**：限制插件可访问的频道

**示例**：
```python
async def execute(context: PluginExecutionContext) -> dict:
    # 仅在 discord 或 slack 频道中执行
    if context.channel_id not in ["discord", "slack"]:
        raise PermissionError(f"无权访问频道: {context.channel_id}")

    return {"message": "Allowed channel"}
```

## 3. 插件开发 API

### 3.1 执行入口

每个插件必须实现 `execute()` 函数：

```python
async def execute(context: PluginExecutionContext) -> Any:
    """插件执行入口

    Args:
        context: 执行上下文，包含用户信息、输入数据等

    Returns:
        执行结果（任意 JSON 可序列化的数据）

    Raises:
        Exception: 执行失败时抛出异常
    """
    pass
```

**注意事项**：
- 必须是异步函数（`async def`）
- 参数名必须是 `context`
- 返回值必须是 JSON 可序列化的数据
- 异常会被沙箱捕获并转换为错误结果

### 3.2 执行上下文

```python
class PluginExecutionContext(BaseModel):
    # 请求信息
    user_id: str | None          # 用户 ID
    channel_id: str | None       # 频道 ID
    session_id: str | None       # 会话 ID

    # 输入数据
    input_data: dict[str, Any]   # 输入数据（如用户消息）
    parameters: dict[str, Any]   # 执行参数

    # 环境信息
    environment: dict[str, Any]  # 环境变量
    config: dict[str, Any]       # 插件配置

    # 元数据
    metadata: dict[str, Any]     # 额外元数据
```

**使用示例**：

```python
async def execute(context: PluginExecutionContext) -> dict:
    # 获取用户信息
    user_id = context.user_id or "anonymous"

    # 获取输入数据
    user_message = context.input_data.get("user_message", "")

    # 获取配置
    api_key = context.config.get("api_key")

    # 获取环境变量
    debug_mode = context.environment.get("DEBUG", False)

    return {
        "user_id": user_id,
        "message_length": len(user_message),
        "debug": debug_mode
    }
```

### 3.3 执行结果

插件返回的数据会被自动封装为 `PluginExecutionResult`：

```python
class PluginExecutionResult(BaseModel):
    success: bool                # 是否成功
    result: Any                  # 执行结果
    error: str | None            # 错误信息
    execution_time: float        # 执行时间（秒）
    metadata: dict[str, Any]     # 结果元数据
```

**成功示例**：
```python
async def execute(context: PluginExecutionContext) -> dict:
    return {"temperature": 25, "condition": "sunny"}

# 自动封装为：
# PluginExecutionResult(
#     success=True,
#     result={"temperature": 25, "condition": "sunny"},
#     error=None,
#     execution_time=0.5
# )
```

**失败示例**：
```python
async def execute(context: PluginExecutionContext) -> dict:
    raise ValueError("Invalid input")

# 自动封装为：
# PluginExecutionResult(
#     success=False,
#     result=None,
#     error="插件执行失败: ValueError: Invalid input",
#     execution_time=0.1
# )
```

## 4. 高级功能

### 4.1 插件配置

插件可以通过 `context.config` 访问自定义配置：

**plugin.json**：
```json
{
  "name": "weather-plugin",
  "config": {
    "api_key": "your-api-key",
    "units": "metric",
    "cache_ttl": 300
  }
}
```

**main.py**：
```python
async def execute(context: PluginExecutionContext) -> dict:
    api_key = context.config.get("api_key")
    units = context.config.get("units", "metric")

    # 使用配置
    weather_data = await fetch_weather(api_key, units)
    return weather_data
```

### 4.2 异步操作

插件支持所有 asyncio 操作：

```python
import asyncio
import httpx

async def execute(context: PluginExecutionContext) -> dict:
    # 并发请求多个 API
    async with httpx.AsyncClient() as client:
        tasks = [
            client.get("https://api1.example.com/data"),
            client.get("https://api2.example.com/data"),
            client.get("https://api3.example.com/data"),
        ]
        responses = await asyncio.gather(*tasks)

    return {
        "results": [r.json() for r in responses]
    }
```

### 4.3 错误处理

**方式 1：抛出异常**

```python
async def execute(context: PluginExecutionContext) -> dict:
    if not context.user_id:
        raise ValueError("user_id is required")

    return {"status": "ok"}
```

**方式 2：返回错误信息**

```python
async def execute(context: PluginExecutionContext) -> dict:
    if not context.user_id:
        return {
            "error": "user_id is required",
            "status": "failed"
        }

    return {"status": "ok"}
```

**推荐**：使用方式 1（抛出异常），沙箱会自动处理并记录错误

### 4.4 日志记录

使用 Loguru 记录日志：

```python
from loguru import logger

async def execute(context: PluginExecutionContext) -> dict:
    logger.info(f"执行插件，用户: {context.user_id}")

    try:
        result = await some_operation()
        logger.debug(f"操作成功: {result}")
        return result
    except Exception as e:
        logger.error(f"操作失败: {e}")
        raise
```

### 4.5 超时控制

插件执行有默认超时限制（30 秒），可通过配置调整：

**plugin.json**：
```json
{
  "config": {
    "max_execution_time": 60.0
  }
}
```

**处理超时**：
```python
import asyncio

async def execute(context: PluginExecutionContext) -> dict:
    try:
        # 长时间操作
        result = await long_running_task()
        return result
    except asyncio.TimeoutError:
        # 超时会被沙箱捕获，这里不需要特殊处理
        raise
```

## 5. 最佳实践

### 5.1 插件结构

**推荐目录结构**：

```
plugins/my-plugin/
├── plugin.json          # 插件清单
├── main.py              # 入口文件
├── utils.py             # 工具函数
├── config.py            # 配置管理
├── README.md            # 插件文档
└── tests/               # 测试文件
    └── test_main.py
```

**模块化示例**：

```python
# main.py
from .utils import fetch_data, process_data
from .config import get_config

async def execute(context: PluginExecutionContext) -> dict:
    config = get_config(context)
    raw_data = await fetch_data(config)
    processed_data = process_data(raw_data)
    return processed_data
```

### 5.2 错误处理

**✅ 推荐**：

```python
async def execute(context: PluginExecutionContext) -> dict:
    # 验证输入
    if not context.input_data.get("city"):
        raise ValueError("city parameter is required")

    # 处理业务逻辑
    try:
        weather = await fetch_weather(context.input_data["city"])
        return weather
    except httpx.HTTPError as e:
        raise RuntimeError(f"Failed to fetch weather: {e}")
```

**❌ 不推荐**：

```python
async def execute(context: PluginExecutionContext) -> dict:
    try:
        # 捕获所有异常但不处理
        weather = await fetch_weather(context.input_data.get("city"))
        return weather
    except:
        return {}  # 静默失败，难以调试
```

### 5.3 性能优化

**使用缓存**：

```python
from functools import lru_cache
import time

# 缓存结果
_cache = {}
_cache_ttl = 300  # 5 分钟

async def execute(context: PluginExecutionContext) -> dict:
    city = context.input_data.get("city")
    cache_key = f"weather:{city}"

    # 检查缓存
    if cache_key in _cache:
        cached_data, timestamp = _cache[cache_key]
        if time.time() - timestamp < _cache_ttl:
            return cached_data

    # 获取新数据
    weather = await fetch_weather(city)
    _cache[cache_key] = (weather, time.time())

    return weather
```

**并发请求**：

```python
async def execute(context: PluginExecutionContext) -> dict:
    cities = context.input_data.get("cities", [])

    # 并发获取多个城市的天气
    tasks = [fetch_weather(city) for city in cities]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    return {
        "weather": [
            r if not isinstance(r, Exception) else {"error": str(r)}
            for r in results
        ]
    }
```

### 5.4 安全性

**验证输入**：

```python
from pydantic import BaseModel, Field

class WeatherInput(BaseModel):
    city: str = Field(..., min_length=1, max_length=100)
    units: str = Field("metric", pattern="^(metric|imperial)$")

async def execute(context: PluginExecutionContext) -> dict:
    # 使用 Pydantic 验证输入
    try:
        input_data = WeatherInput(**context.input_data)
    except ValidationError as e:
        raise ValueError(f"Invalid input: {e}")

    weather = await fetch_weather(input_data.city, input_data.units)
    return weather
```

**避免注入攻击**：

```python
# ❌ 不安全：直接拼接 SQL
async def execute(context: PluginExecutionContext) -> dict:
    user_id = context.input_data.get("user_id")
    query = f"SELECT * FROM users WHERE id = {user_id}"  # SQL 注入风险
    return await db.execute(query)

# ✅ 安全：使用参数化查询
async def execute(context: PluginExecutionContext) -> dict:
    user_id = context.input_data.get("user_id")
    query = "SELECT * FROM users WHERE id = ?"
    return await db.execute(query, (user_id,))
```

### 5.5 测试

**单元测试**：

```python
# tests/test_weather_plugin.py
import pytest
from pathlib import Path
from lurkbot.plugins.manager import PluginManager
from lurkbot.plugins.models import PluginExecutionContext
from lurkbot.plugins.schema_validator import load_plugin_manifest


@pytest.fixture
async def plugin_manager():
    manager = PluginManager()
    plugin_dir = Path("plugins/weather-plugin")
    manifest = load_plugin_manifest(plugin_dir)
    await manager.load_plugin(plugin_dir, manifest)
    return manager


@pytest.mark.asyncio
async def test_weather_plugin_success(plugin_manager):
    context = PluginExecutionContext(
        input_data={"city": "Beijing"}
    )
    result = await plugin_manager.execute_plugin("weather-plugin", context)

    assert result.success is True
    assert "temperature" in result.result
    assert "condition" in result.result


@pytest.mark.asyncio
async def test_weather_plugin_invalid_city(plugin_manager):
    context = PluginExecutionContext(
        input_data={"city": ""}
    )
    result = await plugin_manager.execute_plugin("weather-plugin", context)

    assert result.success is False
    assert "required" in result.error.lower()
```

**集成测试**：

```python
@pytest.mark.asyncio
async def test_plugin_integration_with_agent():
    from lurkbot.agents.runtime import run_embedded_agent

    result = await run_embedded_agent(
        user_message="What's the weather in Beijing?",
        enable_plugins=True
    )

    # 验证插件结果被注入到 system_prompt
    assert "weather-plugin" in result.system_prompt
    assert "temperature" in result.system_prompt
```

## 6. 示例插件

### 6.1 天气查询插件

```python
# plugins/weather-plugin/main.py
import httpx
from lurkbot.plugins.models import PluginExecutionContext

async def execute(context: PluginExecutionContext) -> dict:
    """查询天气信息"""
    city = context.input_data.get("city")
    if not city:
        raise ValueError("city parameter is required")

    api_key = context.config.get("api_key")
    if not api_key:
        raise ValueError("api_key not configured")

    # 调用天气 API
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://api.openweathermap.org/data/2.5/weather",
            params={"q": city, "appid": api_key, "units": "metric"}
        )
        response.raise_for_status()
        data = response.json()

    return {
        "city": city,
        "temperature": data["main"]["temp"],
        "condition": data["weather"][0]["description"],
        "humidity": data["main"]["humidity"]
    }
```

### 6.2 数据库查询插件

```python
# plugins/database-plugin/main.py
import asyncpg
from lurkbot.plugins.models import PluginExecutionContext

async def execute(context: PluginExecutionContext) -> dict:
    """查询数据库"""
    query = context.input_data.get("query")
    if not query:
        raise ValueError("query parameter is required")

    # 连接数据库
    db_url = context.config.get("database_url")
    conn = await asyncpg.connect(db_url)

    try:
        # 执行查询
        rows = await conn.fetch(query)
        return {
            "rows": [dict(row) for row in rows],
            "count": len(rows)
        }
    finally:
        await conn.close()
```

### 6.3 文本处理插件

```python
# plugins/text-processor/main.py
from lurkbot.plugins.models import PluginExecutionContext

async def execute(context: PluginExecutionContext) -> dict:
    """处理文本"""
    text = context.input_data.get("text", "")
    operation = context.input_data.get("operation", "uppercase")

    if operation == "uppercase":
        result = text.upper()
    elif operation == "lowercase":
        result = text.lower()
    elif operation == "reverse":
        result = text[::-1]
    elif operation == "word_count":
        result = len(text.split())
    else:
        raise ValueError(f"Unknown operation: {operation}")

    return {
        "original": text,
        "operation": operation,
        "result": result
    }
```

## 7. 故障排查

### 7.1 常见错误

**错误 1：插件未找到**

```
ERROR: 插件 my-plugin 不存在
```

**解决方案**：
1. 检查插件目录是否在 `plugins/` 下
2. 检查 `plugin.json` 是否存在且格式正确
3. 运行 `discover_all_plugins()` 确认插件被发现

**错误 2：权限不足**

```
ERROR: 权限错误: 插件无权访问频道: discord
```

**解决方案**：
1. 在 `plugin.json` 中添加所需权限
2. 重新加载插件

**错误 3：执行超时**

```
ERROR: 插件执行超时（30秒）
```

**解决方案**：
1. 优化插件代码，减少执行时间
2. 增加 `max_execution_time` 配置
3. 使用异步操作避免阻塞

### 7.2 调试技巧

**启用详细日志**：

```python
from loguru import logger

# 设置日志级别
logger.remove()
logger.add(sys.stderr, level="DEBUG")
```

**查看插件事件**：

```python
manager = get_plugin_manager()
events = manager.get_events("my-plugin")

for event in events:
    print(f"{event.timestamp}: {event.event_type} - {event.message}")
```

**手动测试插件**：

```python
import asyncio
from lurkbot.plugins.manager import get_plugin_manager
from lurkbot.plugins.models import PluginExecutionContext

async def test_plugin():
    manager = get_plugin_manager()

    context = PluginExecutionContext(
        user_id="test-user",
        input_data={"test": "data"}
    )

    result = await manager.execute_plugin("my-plugin", context)
    print(f"Success: {result.success}")
    print(f"Result: {result.result}")
    print(f"Error: {result.error}")
    print(f"Time: {result.execution_time}s")

asyncio.run(test_plugin())
```

## 8. 发布插件

### 8.1 插件打包

**创建 README.md**：

```markdown
# Weather Plugin

查询实时天气信息的 LurkBot 插件。

## 功能

- 支持全球城市天气查询
- 提供温度、湿度、天气状况等信息
- 支持摄氏度和华氏度

## 配置

在 `plugin.json` 中配置 API Key：

\`\`\`json
{
  "config": {
    "api_key": "your-openweathermap-api-key"
  }
}
\`\`\`

## 使用示例

\`\`\`python
context = PluginExecutionContext(
    input_data={"city": "Beijing"}
)
result = await manager.execute_plugin("weather-plugin", context)
\`\`\`

## 许可证

MIT License
```

**创建 LICENSE**：

```
MIT License

Copyright (c) 2026 Your Name

Permission is hereby granted...
```

### 8.2 版本管理

遵循语义化版本（Semantic Versioning）：

- **MAJOR**：不兼容的 API 变更
- **MINOR**：向后兼容的功能新增
- **PATCH**：向后兼容的问题修复

**示例**：
- `1.0.0` → 初始版本
- `1.1.0` → 新增功能
- `1.1.1` → 修复 bug
- `2.0.0` → 破坏性变更

### 8.3 发布清单

发布前检查：

- [ ] `plugin.json` 格式正确
- [ ] 所有依赖已声明
- [ ] 权限配置合理
- [ ] 单元测试通过
- [ ] 文档完整（README.md）
- [ ] 许可证文件存在
- [ ] 版本号正确

## 9. 参考资料

### 9.1 API 文档

- `PluginExecutionContext` - 执行上下文
- `PluginExecutionResult` - 执行结果
- `PluginConfig` - 插件配置
- `PluginEvent` - 插件事件

### 9.2 示例插件

- `plugins/example-plugin/` - 基础示例
- `plugins/weather-plugin/` - 天气查询
- `plugins/database-plugin/` - 数据库集成

### 9.3 相关文档

- [插件系统设计文档](./PLUGIN_SYSTEM_DESIGN.md)
- [Agent Runtime 文档](./AGENT_RUNTIME_DESIGN.md)
- [测试指南](../dev/TESTING_GUIDE.md)

## 10. 社区和支持

### 10.1 获取帮助

- GitHub Issues: https://github.com/your-org/lurkbot/issues
- 讨论区: https://github.com/your-org/lurkbot/discussions
- 文档: https://docs.lurkbot.dev

### 10.2 贡献插件

欢迎贡献插件到官方插件库！

**步骤**：
1. Fork 仓库
2. 创建插件分支
3. 开发和测试插件
4. 提交 Pull Request
5. 等待审核

**审核标准**：
- 代码质量
- 测试覆盖率
- 文档完整性
- 安全性
- 性能

---

**祝你开发愉快！** 🚀

## 11. 实际示例插件详解

### 11.1 天气查询插件（weather-plugin）

**完整实现**：

```python
# .plugins/weather-plugin/main.py
"""天气查询插件 - 使用 wttr.in API"""

import httpx
from loguru import logger
from lurkbot.plugins.models import PluginExecutionContext


async def execute(context: PluginExecutionContext) -> dict:
    """查询城市天气信息

    Args:
        context: 执行上下文，需要 input_data 包含 'city' 字段

    Returns:
        天气信息字典

    Raises:
        ValueError: 缺少必需参数
        httpx.HTTPError: API 请求失败
    """
    # 1. 验证输入
    city = context.input_data.get("city")
    if not city:
        raise ValueError("city parameter is required")

    logger.info(f"Fetching weather for city: {city}")

    # 2. 调用 wttr.in API（无需 API Key）
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"https://wttr.in/{city}",
                params={"format": "j1"}  # JSON 格式
            )
            response.raise_for_status()
            data = response.json()

    except httpx.HTTPError as e:
        logger.error(f"Failed to fetch weather: {e}")
        raise RuntimeError(f"Weather API request failed: {e}")

    # 3. 解析数据
    current = data["current_condition"][0]
    location = data["nearest_area"][0]

    # 4. 返回结构化结果
    return {
        "city": city,
        "location": {
            "name": location["areaName"][0]["value"],
            "country": location["country"][0]["value"],
        },
        "temperature": {
            "celsius": int(current["temp_C"]),
            "fahrenheit": int(current["temp_F"]),
        },
        "condition": current["weatherDesc"][0]["value"],
        "humidity": int(current["humidity"]),
        "wind_speed": f"{current['windspeedKmph']} km/h",
        "feels_like": int(current["FeelsLikeC"]),
    }
```

**plugin.json 配置**：

```json
{
  "name": "weather-plugin",
  "version": "1.0.0",
  "author": {
    "name": "LurkBot Team",
    "email": "team@lurkbot.dev"
  },
  "description": "查询实时天气信息（使用 wttr.in API）",
  "plugin_type": "tool",
  "entry_point": "main.py",
  "enabled": true,
  "permissions": {
    "filesystem": false,
    "network": true,
    "exec": false,
    "channels": []
  },
  "dependencies": [
    "httpx>=0.27.0"
  ],
  "tags": ["weather", "api", "utility"]
}
```

**关键要点**：

1. **无需 API Key**：使用免费的 wttr.in API
2. **超时控制**：设置 10 秒超时避免长时间等待
3. **错误处理**：捕获 HTTP 错误并转换为友好消息
4. **结构化输出**：返回清晰的嵌套字典结构
5. **日志记录**：使用 loguru 记录关键操作

### 11.2 时间工具插件（time-utils-plugin）

**完整实现**：

```python
# .plugins/time-utils-plugin/main.py
"""时间工具插件 - 多时区支持"""

from datetime import datetime
from zoneinfo import ZoneInfo, available_timezones
from loguru import logger
from lurkbot.plugins.models import PluginExecutionContext


async def execute(context: PluginExecutionContext) -> dict:
    """获取指定时区的当前时间

    Args:
        context: 执行上下文，可选 input_data 包含 'timezone' 字段

    Returns:
        时间信息字典
    """
    # 1. 获取时区参数（默认 UTC）
    timezone_name = context.input_data.get("timezone", "UTC")

    # 2. 验证时区
    if timezone_name not in available_timezones():
        # 提供常用时区建议
        common_timezones = [
            "UTC", "America/New_York", "Europe/London",
            "Asia/Shanghai", "Asia/Tokyo"
        ]
        raise ValueError(
            f"Invalid timezone: {timezone_name}. "
            f"Common timezones: {', '.join(common_timezones)}"
        )

    logger.info(f"Getting time for timezone: {timezone_name}")

    # 3. 获取当前时间
    tz = ZoneInfo(timezone_name)
    now = datetime.now(tz)

    # 4. 返回多种格式
    return {
        "timezone": timezone_name,
        "datetime": now.isoformat(),
        "formatted": {
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M:%S"),
            "full": now.strftime("%Y-%m-%d %H:%M:%S %Z"),
        },
        "components": {
            "year": now.year,
            "month": now.month,
            "day": now.day,
            "hour": now.hour,
            "minute": now.minute,
            "second": now.second,
            "weekday": now.strftime("%A"),
        },
        "unix_timestamp": int(now.timestamp()),
    }
```

**关键要点**：

1. **无需外部依赖**：使用 Python 标准库 `zoneinfo`
2. **时区验证**：检查时区有效性并提供建议
3. **多种格式**：返回 ISO、格式化、组件等多种时间表示
4. **默认值**：提供合理的默认时区（UTC）

### 11.3 系统信息插件（system-info-plugin）

**完整实现**：

```python
# .plugins/system-info-plugin/main.py
"""系统信息插件 - CPU/内存/磁盘监控"""

import psutil
from loguru import logger
from lurkbot.plugins.models import PluginExecutionContext


async def execute(context: PluginExecutionContext) -> dict:
    """获取系统资源使用情况

    Returns:
        系统信息字典
    """
    logger.info("Collecting system information")

    # 1. CPU 信息
    cpu_percent = psutil.cpu_percent(interval=1)
    cpu_count = psutil.cpu_count()

    # 2. 内存信息
    memory = psutil.virtual_memory()

    # 3. 磁盘信息
    disk = psutil.disk_usage("/")

    # 4. 网络信息（可选）
    net_io = psutil.net_io_counters()

    # 5. 返回结构化数据
    return {
        "cpu": {
            "percent": round(cpu_percent, 2),
            "count": cpu_count,
            "status": "high" if cpu_percent > 80 else "normal",
        },
        "memory": {
            "total_gb": round(memory.total / (1024**3), 2),
            "used_gb": round(memory.used / (1024**3), 2),
            "available_gb": round(memory.available / (1024**3), 2),
            "percent": round(memory.percent, 2),
            "status": "high" if memory.percent > 80 else "normal",
        },
        "disk": {
            "total_gb": round(disk.total / (1024**3), 2),
            "used_gb": round(disk.used / (1024**3), 2),
            "free_gb": round(disk.free / (1024**3), 2),
            "percent": round(disk.percent, 2),
            "status": "high" if disk.percent > 80 else "normal",
        },
        "network": {
            "bytes_sent_mb": round(net_io.bytes_sent / (1024**2), 2),
            "bytes_recv_mb": round(net_io.bytes_recv / (1024**2), 2),
        },
    }
```

**plugin.json 配置**：

```json
{
  "name": "system-info-plugin",
  "version": "1.0.0",
  "author": {
    "name": "LurkBot Team"
  },
  "description": "监控系统 CPU、内存、磁盘使用情况",
  "plugin_type": "tool",
  "entry_point": "main.py",
  "enabled": true,
  "permissions": {
    "filesystem": true,
    "network": false,
    "exec": false
  },
  "dependencies": [
    "psutil>=5.9.0"
  ],
  "tags": ["system", "monitoring", "utility"]
}
```

**关键要点**：

1. **需要文件系统权限**：psutil 需要读取系统文件
2. **单位转换**：将字节转换为 GB/MB 便于阅读
3. **状态判断**：提供 "high"/"normal" 状态标识
4. **精度控制**：使用 `round()` 保留 2 位小数

## 12. 调试技巧

### 12.1 启用详细日志

**方法 1：在插件中启用**

```python
from loguru import logger
import sys

# 在插件入口添加
logger.remove()
logger.add(sys.stderr, level="DEBUG")

async def execute(context: PluginExecutionContext) -> dict:
    logger.debug(f"Context: {context}")
    logger.debug(f"Input data: {context.input_data}")

    # 业务逻辑
    result = await some_operation()

    logger.debug(f"Result: {result}")
    return result
```

**方法 2：环境变量控制**

```bash
# 设置日志级别
export LOGURU_LEVEL=DEBUG

# 运行测试
pytest tests/test_my_plugin.py -v
```

### 12.2 使用断点调试

**使用 pdb**：

```python
async def execute(context: PluginExecutionContext) -> dict:
    import pdb; pdb.set_trace()  # 设置断点

    city = context.input_data.get("city")
    # ... 继续执行
```

**使用 ipdb（推荐）**：

```bash
# 安装 ipdb
pip install ipdb
```

```python
async def execute(context: PluginExecutionContext) -> dict:
    import ipdb; ipdb.set_trace()  # 更友好的调试器

    # 调试命令：
    # n - 下一行
    # s - 进入函数
    # c - 继续执行
    # p variable - 打印变量
    # l - 显示代码
```

### 12.3 手动测试脚本

创建独立的测试脚本：

```python
# tests/manual/test_my_plugin_manual.py
import asyncio
from pathlib import Path
from lurkbot.plugins.manager import PluginManager
from lurkbot.plugins.models import PluginExecutionContext
from lurkbot.plugins.schema_validator import load_plugin_manifest


async def main():
    """手动测试插件"""

    # 1. 加载插件
    plugin_dir = Path(".plugins/weather-plugin")
    manifest = load_plugin_manifest(plugin_dir)

    manager = PluginManager()
    await manager.load_plugin(plugin_dir, manifest)

    # 2. 创建测试上下文
    context = PluginExecutionContext(
        user_id="test-user",
        channel_id="test-channel",
        input_data={"city": "Beijing"}
    )

    # 3. 执行插件
    print("执行插件...")
    result = await manager.execute_plugin("weather-plugin", context)

    # 4. 打印结果
    print(f"\n成功: {result.success}")
    print(f"耗时: {result.execution_time:.3f}秒")

    if result.success:
        print(f"\n结果:")
        import json
        print(json.dumps(result.result, indent=2, ensure_ascii=False))
    else:
        print(f"\n错误: {result.error}")

    # 5. 查看事件
    print(f"\n最近事件:")
    events = manager.get_events("weather-plugin", limit=5)
    for event in events:
        print(f"  [{event.timestamp}] {event.event_type}: {event.message}")


if __name__ == "__main__":
    asyncio.run(main())
```

**运行**：

```bash
python tests/manual/test_my_plugin_manual.py
```

### 12.4 性能分析

**使用 cProfile**：

```python
import cProfile
import pstats
from io import StringIO

async def execute(context: PluginExecutionContext) -> dict:
    # 启用性能分析
    profiler = cProfile.Profile()
    profiler.enable()

    # 业务逻辑
    result = await some_operation()

    # 停止分析
    profiler.disable()

    # 打印统计
    s = StringIO()
    ps = pstats.Stats(profiler, stream=s).sort_stats("cumulative")
    ps.print_stats(10)  # 打印前 10 个最慢的函数
    logger.debug(s.getvalue())

    return result
```

**使用 time 模块**：

```python
import time

async def execute(context: PluginExecutionContext) -> dict:
    start = time.time()

    # 步骤 1
    step1_start = time.time()
    await step1()
    logger.debug(f"Step 1: {time.time() - step1_start:.3f}s")

    # 步骤 2
    step2_start = time.time()
    await step2()
    logger.debug(f"Step 2: {time.time() - step2_start:.3f}s")

    total_time = time.time() - start
    logger.debug(f"Total: {total_time:.3f}s")

    return result
```

### 12.5 Mock 外部依赖

**使用 pytest-mock**：

```python
# tests/test_weather_plugin.py
import pytest
from unittest.mock import AsyncMock

@pytest.mark.asyncio
async def test_weather_plugin_with_mock(mocker):
    # Mock httpx.AsyncClient
    mock_response = AsyncMock()
    mock_response.json.return_value = {
        "current_condition": [{
            "temp_C": "25",
            "weatherDesc": [{"value": "Sunny"}],
            "humidity": "60"
        }],
        "nearest_area": [{
            "areaName": [{"value": "Beijing"}],
            "country": [{"value": "China"}]
        }]
    }

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_response
    mock_client.__aenter__.return_value = mock_client

    mocker.patch("httpx.AsyncClient", return_value=mock_client)

    # 测试插件
    context = PluginExecutionContext(
        input_data={"city": "Beijing"}
    )
    result = await manager.execute_plugin("weather-plugin", context)

    assert result.success is True
    assert result.result["temperature"]["celsius"] == 25
```

### 12.6 常见问题排查

**问题 1：插件加载失败**

```bash
# 检查语法错误
python -m py_compile .plugins/my-plugin/main.py

# 检查 JSON 格式
python -m json.tool .plugins/my-plugin/plugin.json

# 检查导入
python -c "from lurkbot.plugins.models import PluginExecutionContext"
```

**问题 2：依赖缺失**

```bash
# 查看插件依赖
cat .plugins/my-plugin/plugin.json | grep dependencies

# 安装依赖
pip install httpx psutil

# 验证安装
python -c "import httpx; import psutil"
```

**问题 3：权限错误**

```python
# 在插件中添加权限检查日志
async def execute(context: PluginExecutionContext) -> dict:
    logger.debug(f"Channel ID: {context.channel_id}")
    logger.debug(f"Allowed channels: {manifest.permissions.channels}")

    # 检查权限
    if context.channel_id not in manifest.permissions.channels:
        raise PermissionError(f"No permission for channel: {context.channel_id}")
```

**问题 4：异步问题**

```python
# ❌ 错误：使用同步函数
def execute(context):  # 缺少 async
    result = requests.get(url)  # 同步调用
    return result

# ✅ 正确：使用异步函数
async def execute(context):
    async with httpx.AsyncClient() as client:
        result = await client.get(url)
    return result
```

## 13. 最佳实践总结

### 13.1 代码质量

**✅ 推荐**：

- 使用类型注解
- 添加文档字符串
- 验证输入参数
- 使用异步操作
- 记录关键日志
- 处理异常情况

**❌ 避免**：

- 硬编码配置
- 忽略错误
- 阻塞操作
- 过度捕获异常
- 缺少日志

### 13.2 性能优化

**✅ 推荐**：

- 使用缓存
- 并发请求
- 设置超时
- 限制数据量
- 异步 I/O

**❌ 避免**：

- 同步阻塞
- 无限循环
- 内存泄漏
- 重复计算
- 过度日志

### 13.3 安全性

**✅ 推荐**：

- 验证输入
- 参数化查询
- 最小权限
- 敏感信息加密
- 错误信息脱敏

**❌ 避免**：

- SQL 注入
- 命令注入
- 路径遍历
- 硬编码密钥
- 暴露敏感信息

### 13.4 可维护性

**✅ 推荐**：

- 模块化设计
- 单一职责
- 清晰命名
- 完整文档
- 充分测试

**❌ 避免**：

- 过度复杂
- 重复代码
- 魔法数字
- 缺少注释
- 无测试

---

**祝你开发愉快！** 🚀
