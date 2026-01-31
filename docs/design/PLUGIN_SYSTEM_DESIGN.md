# LurkBot 插件系统设计文档

## 1. 概述

### 1.1 设计目标

LurkBot 插件系统旨在提供一个安全、灵活、可扩展的插件架构，允许开发者通过插件扩展 AI Agent 的功能，而无需修改核心代码。

**核心目标**：
- **安全性**：通过沙箱机制隔离插件执行，防止恶意代码影响系统
- **可扩展性**：支持动态加载/卸载插件，无需重启服务
- **易用性**：提供简洁的插件开发 API 和清晰的生命周期管理
- **高性能**：支持并发执行多个插件，最小化性能开销
- **可观测性**：完整的事件系统和日志记录，便于调试和监控

### 1.2 适用场景

- **功能增强**：为 AI Agent 添加新的工具和能力（如天气查询、数据库访问）
- **数据处理**：在 LLM 调用前后对数据进行预处理或后处理
- **集成外部服务**：连接第三方 API 和服务
- **自定义行为**：根据特定业务需求定制 Agent 行为
- **A/B 测试**：通过插件快速验证新功能

### 1.3 技术栈

- **语言**：Python 3.12+
- **异步框架**：asyncio
- **数据验证**：Pydantic v2
- **日志**：Loguru
- **测试**：pytest + pytest-asyncio

## 2. 系统架构

### 2.1 整体架构图

```
┌─────────────────────────────────────────────────────────────┐
│                      Agent Runtime                          │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  Step 0.5: Plugin Execution (Before LLM Call)         │  │
│  │  - 获取 PluginManager                                  │  │
│  │  - 构造 PluginExecutionContext                        │  │
│  │  - 并发执行所有已启用插件                              │  │
│  │  - 格式化结果并注入 system_prompt                      │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    Plugin Manager                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ 生命周期管理  │  │  状态跟踪    │  │  事件分发    │      │
│  │ - load       │  │ - configs    │  │ - events     │      │
│  │ - unload     │  │ - sandboxes  │  │ - handlers   │      │
│  │ - enable     │  │              │  │              │      │
│  │ - disable    │  │              │  │              │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
         ↓                    ↓                    ↓
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ Plugin Loader│    │Plugin Registry│    │Plugin Sandbox│
│              │    │              │    │              │
│ - 动态加载    │    │ - CRUD 操作  │    │ - 超时控制   │
│ - 模块管理    │    │ - 查询过滤   │    │ - 权限检查   │
│ - 状态控制    │    │ - 持久化     │    │ - 异常隔离   │
└──────────────┘    └──────────────┘    └──────────────┘
         ↓                    ↓
┌──────────────┐    ┌──────────────┐
│Plugin Manifest│   │ Plugin Models│
│              │    │              │
│ - 元数据定义  │    │ - 数据模型   │
│ - 权限声明    │    │ - 状态枚举   │
│ - 依赖管理    │    │ - 事件类型   │
└──────────────┘    └──────────────┘
```

### 2.2 核心组件

#### 2.2.1 Plugin Manager（插件管理器）

**职责**：
- 插件生命周期管理（加载、卸载、启用、禁用）
- 插件执行调度（单个执行、并发执行）
- 配置管理和沙箱初始化
- 事件发布和处理

**关键方法**：
```python
class PluginManager:
    async def discover_and_load_all(workspace_root) -> int
    async def load_plugin(plugin_dir, manifest) -> PluginInstance
    async def unload_plugin(name) -> bool
    async def enable_plugin(name) -> bool
    async def disable_plugin(name) -> bool
    async def execute_plugin(name, context) -> PluginExecutionResult
    async def execute_plugins(context, plugin_names) -> dict[str, PluginExecutionResult]
```

**文件位置**：`src/lurkbot/plugins/manager.py`

#### 2.2.2 Plugin Loader（插件加载器）

**职责**：
- 动态加载 Python 模块
- 插件实例化和初始化
- 模块卸载和清理
- 状态管理（UNLOADED/LOADED/ENABLED/DISABLED/ERROR）

**关键方法**：
```python
class PluginLoader:
    def load(plugin_dir, manifest) -> PluginInstance
    def unload(name) -> bool
    def enable(name) -> bool
    def disable(name) -> bool
    def get(name) -> PluginInstance | None
```

**文件位置**：`src/lurkbot/plugins/loader.py`

#### 2.2.3 Plugin Registry（插件注册表）

**职责**：
- 插件实例的 CRUD 操作
- 按状态、类型、标签查询插件
- 插件元数据持久化（JSON）
- 关键字搜索

**关键方法**：
```python
class PluginRegistry:
    def register(plugin) -> None
    def unregister(name) -> bool
    def get(name) -> PluginInstance | None
    def list_by_state(state) -> list[PluginInstance]
    def list_by_type(plugin_type) -> list[PluginInstance]
    def find_by_tag(tag) -> list[PluginInstance]
    def find_by_keyword(keyword) -> list[PluginInstance]
```

**文件位置**：`src/lurkbot/plugins/registry.py`

#### 2.2.4 Plugin Sandbox（插件沙箱）

**职责**：
- 超时控制（asyncio.wait_for）
- 权限检查（文件系统、网络、命令执行、频道访问）
- 异常隔离和错误处理
- 资源限制（内存、CPU）

**关键方法**：
```python
class PluginSandbox:
    async def execute(plugin_func, context, *args, **kwargs) -> PluginExecutionResult
    def _check_permissions(context) -> None
    def _apply_resource_limits() -> None
```

**文件位置**：`src/lurkbot/plugins/sandbox.py`

#### 2.2.5 Plugin Manifest（插件清单）

**职责**：
- 定义插件元数据（名称、版本、作者、描述）
- 声明插件权限（文件系统、网络、命令执行、频道）
- 管理插件依赖
- 配置插件类型和标签

**数据结构**：
```python
class PluginManifest(BaseModel):
    name: str
    version: str
    author: PluginAuthor
    description: str
    plugin_type: PluginType
    entry_point: str
    enabled: bool = True
    permissions: PluginPermissions
    dependencies: list[str] = []
    tags: list[str] = []
```

**文件位置**：`src/lurkbot/plugins/manifest.py`

#### 2.2.6 Plugin Models（数据模型）

**职责**：
- 定义插件配置（PluginConfig）
- 定义执行上下文（PluginExecutionContext）
- 定义执行结果（PluginExecutionResult）
- 定义事件模型（PluginEvent）
- 定义状态枚举（PluginStatus、PluginEventType）

**文件位置**：`src/lurkbot/plugins/models.py`

## 3. 数据流

### 3.1 插件加载流程

```
1. discover_all_plugins(workspace_root)
   ↓
2. 遍历 plugins/ 目录，查找 plugin.json
   ↓
3. 验证 plugin.json 格式（schema_validator）
   ↓
4. PluginManager.load_plugin(plugin_dir, manifest)
   ↓
5. PluginLoader.load() - 动态导入模块
   ↓
6. PluginRegistry.register() - 注册到注册表
   ↓
7. 创建 PluginConfig 和 PluginSandbox
   ↓
8. 发布 LOAD 事件
   ↓
9. 如果 auto_load=True，自动调用 enable_plugin()
```

### 3.2 插件执行流程

```
1. Agent Runtime 构造 PluginExecutionContext
   ↓
2. PluginManager.execute_plugins(context)
   ↓
3. 获取所有 ENABLED 状态的插件
   ↓
4. 并发执行（asyncio.gather）
   ↓
5. 对每个插件：
   a. 检查插件状态（ENABLED）
   b. 获取 PluginSandbox
   c. Sandbox.execute(plugin.execute, context)
      - 权限检查
      - 超时控制（asyncio.wait_for）
      - 异常捕获
   d. 返回 PluginExecutionResult
   ↓
6. 收集所有结果，构造 dict[str, PluginExecutionResult]
   ↓
7. 格式化结果并注入到 system_prompt
   ↓
8. 发布 EXECUTE 事件
```

### 3.3 插件卸载流程

```
1. PluginManager.unload_plugin(name)
   ↓
2. 如果插件已启用，先调用 disable_plugin()
   ↓
3. PluginLoader.unload(name)
   - 从 sys.modules 删除模块
   - 清理插件实例
   ↓
4. PluginRegistry.unregister(name)
   ↓
5. 清理 _configs 和 _sandboxes
   ↓
6. 发布 UNLOAD 事件
```

## 4. 安全机制

### 4.1 沙箱隔离

**超时控制**：
- 使用 `asyncio.wait_for()` 限制插件执行时间
- 默认超时：30 秒（可配置）
- 超时后自动终止执行，返回错误结果

**权限检查**：
- **文件系统访问**：`allow_filesystem`（默认 False）
- **网络访问**：`allow_network`（默认 False）
- **命令执行**：`allow_exec`（默认 False）
- **频道访问**：`allowed_channels`（白名单）

**异常隔离**：
- 所有插件异常被捕获并封装到 `PluginExecutionResult`
- 单个插件失败不影响其他插件执行
- 异常信息记录到日志和事件系统

### 4.2 资源限制

**内存限制**：
- 默认：512 MB
- 通过 `resource.setrlimit(RLIMIT_AS)` 实现（Linux/macOS）

**CPU 限制**：
- 默认：80%
- 通过 `resource.setrlimit(RLIMIT_CPU)` 实现（Linux/macOS）

**并发控制**：
- 使用 `asyncio.gather()` 并发执行插件
- 每个插件在独立的沙箱中运行
- 避免插件间相互干扰

### 4.3 权限声明

插件必须在 `plugin.json` 中显式声明所需权限：

```json
{
  "permissions": {
    "filesystem": false,
    "network": true,
    "exec": false,
    "channels": ["discord", "slack"]
  }
}
```

**权限验证时机**：
1. 插件加载时：验证 manifest 格式
2. 插件执行前：检查上下文是否符合权限要求
3. 运行时：沙箱动态检查权限

## 5. 事件系统

### 5.1 事件类型

```python
class PluginEventType(str, Enum):
    LOAD = "load"          # 插件加载
    UNLOAD = "unload"      # 插件卸载
    ENABLE = "enable"      # 插件启用
    DISABLE = "disable"    # 插件禁用
    EXECUTE = "execute"    # 插件执行
    ERROR = "error"        # 错误事件
```

### 5.2 事件模型

```python
class PluginEvent(BaseModel):
    plugin_name: str              # 插件名称
    event_type: PluginEventType   # 事件类型
    timestamp: datetime           # 事件时间
    success: bool                 # 是否成功
    message: str | None           # 事件消息
    error: str | None             # 错误信息
    metadata: dict[str, Any]      # 事件元数据
```

### 5.3 事件处理

**注册事件处理器**：
```python
manager = get_plugin_manager()

async def on_plugin_event(event: PluginEvent):
    if event.event_type == PluginEventType.ERROR:
        logger.error(f"插件错误: {event.plugin_name} - {event.error}")

manager.add_event_handler(on_plugin_event)
```

**事件发布流程**：
1. 插件生命周期操作触发事件
2. `PluginManager._emit_event()` 发布事件
3. 事件记录到 `_events` 列表
4. 调用所有注册的事件处理器
5. 支持同步和异步处理器

## 6. 性能考虑

### 6.1 并发执行

- 使用 `asyncio.gather()` 并发执行多个插件
- 避免串行执行导致的延迟累加
- 单个插件超时不阻塞其他插件

**性能指标**：
- 10 个插件并发执行：总耗时 ≈ max(单个插件耗时)
- 串行执行：总耗时 = sum(所有插件耗时)

### 6.2 懒加载

- 插件在首次使用时加载，而非启动时全部加载
- 支持按需加载和卸载
- 减少内存占用和启动时间

### 6.3 缓存机制

- `PluginLoader` 缓存已加载的模块和实例
- `PluginRegistry` 提供快速查询接口
- 避免重复加载和解析

### 6.4 资源清理

- 插件卸载时清理 `sys.modules`
- 释放沙箱和配置对象
- 避免内存泄漏

## 7. 可扩展性

### 7.1 插件类型

```python
class PluginType(str, Enum):
    TOOL = "tool"              # 工具插件（提供功能）
    MIDDLEWARE = "middleware"  # 中间件插件（数据处理）
    HOOK = "hook"              # 钩子插件（事件响应）
    INTEGRATION = "integration"  # 集成插件（外部服务）
```

### 7.2 插件发现

- 自动扫描 `plugins/` 目录
- 支持自定义插件目录（通过 `workspace_root` 参数）
- 验证 `plugin.json` 格式

### 7.3 依赖管理

- 插件可声明依赖的 Python 包
- 未来可扩展为插件间依赖

```json
{
  "dependencies": [
    "requests>=2.28.0",
    "pydantic>=2.0.0"
  ]
}
```

### 7.4 版本兼容性

- 插件清单包含版本号
- 支持语义化版本（Semantic Versioning）
- 未来可实现版本兼容性检查

## 8. 监控和调试

### 8.1 日志记录

使用 Loguru 记录关键操作：
- 插件加载/卸载：INFO 级别
- 插件执行：DEBUG 级别
- 错误和异常：ERROR 级别

### 8.2 事件追踪

- 所有事件记录到 `PluginManager._events`
- 支持按插件名称过滤事件
- 事件包含时间戳和元数据

### 8.3 性能指标

`PluginExecutionResult` 包含：
- `execution_time`：执行耗时（秒）
- `metadata`：自定义性能指标

### 8.4 错误处理

- 所有异常被捕获并转换为 `PluginExecutionResult`
- 错误信息包含异常类型和堆栈信息
- 发布 ERROR 事件通知监控系统

## 9. 与 Agent Runtime 集成

### 9.1 集成点

在 `src/lurkbot/agents/runtime.py` 的 `run_embedded_agent()` 函数中：

```python
async def run_embedded_agent(
    ...,
    enable_plugins: bool = True,
) -> AgentRunResult:
    # Step 0.5: Execute plugins (if enabled)
    if enable_plugins:
        plugin_manager = get_plugin_manager()
        plugin_context = PluginExecutionContext(
            user_id=user_id,
            channel_id=channel_id,
            session_id=session_id,
            input_data={"user_message": user_message},
            parameters={},
            environment={},
            config={},
        )
        plugin_results = await plugin_manager.execute_plugins(plugin_context)

        # Format and inject into system_prompt
        if plugin_results:
            plugin_results_text = _format_plugin_results(plugin_results)
            system_prompt = system_prompt + "\n\n" + plugin_results_text
```

### 9.2 结果注入

插件执行结果格式化为文本并注入到 `system_prompt`：

```
=== Plugin Execution Results ===

[weather-plugin]
Status: Success
Result: {"temperature": 25, "condition": "sunny"}
Execution Time: 0.5s

[database-plugin]
Status: Success
Result: {"user_count": 1234}
Execution Time: 0.3s
```

### 9.3 错误处理

- 插件执行失败不影响 Agent 运行
- 错误信息记录到日志
- 可选择是否将错误信息注入到 system_prompt

## 10. Phase 5-B: 高级功能实现

### 10.1 插件热重载（已实现）

**功能描述**：支持不重启服务更新插件，通过文件监控自动检测插件变化并重新加载。

**核心组件**：
- `PluginReloadHandler`：文件系统事件处理器，监控插件目录变化
- `HotReloadManager`：热重载管理器，协调文件监控和插件重载流程

**关键特性**：
- 使用 watchdog 库监控文件系统变化
- 防抖机制避免频繁重载（默认 1 秒）
- 保持插件状态（启用/禁用状态）
- 支持动态添加/移除监控路径

**使用示例**：
```python
from lurkbot.plugins.hot_reload import HotReloadManager
from lurkbot.plugins.manager import PluginManager

manager = PluginManager()
hot_reload = HotReloadManager(
    manager,
    watch_paths=[Path("plugins")],
    debounce_seconds=1.0
)

# 启动热重载
hot_reload.start()

# 停止热重载
hot_reload.stop()
```

**相关文件**：
- `src/lurkbot/plugins/hot_reload.py`
- `tests/test_plugin_hot_reload.py`

### 10.2 插件市场（已实现）

**功能描述**：提供插件发现、下载、安装和版本管理功能。

**核心组件**：
- `PluginMarketplace`：插件市场管理器
- `PluginIndex`：插件索引数据结构
- `PluginPackageInfo`：插件包信息模型

**关键特性**：
- 从远程索引刷新插件列表
- 按关键词和标签搜索插件
- 下载并验证插件包（支持 SHA256 校验）
- 自动解析和安装依赖
- 本地缓存机制
- 插件更新检测

**使用示例**：
```python
from lurkbot.plugins.marketplace import PluginMarketplace
from lurkbot.plugins.manager import PluginManager

manager = PluginManager()
marketplace = PluginMarketplace(
    manager,
    index_url="https://plugins.lurkbot.io/index.json"
)

# 刷新索引
await marketplace.refresh_index()

# 搜索插件
results = await marketplace.search(query="weather", tags=["utility"])

# 安装插件
await marketplace.install_plugin("weather-plugin", version="1.0.0")

# 更新插件
await marketplace.update_plugin("weather-plugin")
```

**相关文件**：
- `src/lurkbot/plugins/marketplace.py`
- `tests/test_plugin_marketplace.py`

### 10.3 容器沙箱（已实现）

**功能描述**：使用 Docker 容器技术实现更严格的插件隔离。

**核心组件**：
- `ContainerSandbox`：容器沙箱管理器
- Docker SDK for Python

**关键特性**：
- 完全隔离的执行环境
- 资源配额管理（CPU、内存）
- 网络隔离（支持 none、bridge、host 模式）
- 文件系统隔离（只读模式）
- 安全选项（no-new-privileges、cap-drop）
- 超时控制

**使用示例**：
```python
from lurkbot.plugins.container_sandbox import ContainerSandbox
from lurkbot.plugins.models import PluginConfig, PluginExecutionContext

config = PluginConfig(
    allow_network=False,
    max_memory_mb=128,
    max_cpu_percent=50.0
)

sandbox = ContainerSandbox(config, image="python:3.12-slim")

context = PluginExecutionContext(
    channel_id="test-channel",
    user_id="test-user"
)

result = await sandbox.execute(
    plugin_name="test-plugin",
    plugin_code=plugin_code,
    context=context,
    timeout=30.0
)
```

**相关文件**：
- `src/lurkbot/plugins/container_sandbox.py`
- `tests/test_container_sandbox.py`

### 10.4 插件间通信（已实现）

**功能描述**：支持插件之间的数据共享和通信。

**核心组件**：
- `MessageBus`：消息总线，实现发布-订阅模式
- `SharedState`：共享状态管理器
- `PluginCommunication`：通信管理器

**关键特性**：
- 发布-订阅消息模式
- 主题订阅和取消订阅
- 异步消息分发
- 命名空间隔离的共享状态
- 线程安全的状态访问
- 支持同步和异步回调

**使用示例**：
```python
from lurkbot.plugins.communication import get_communication, Message

comm = get_communication()
comm.start()

# 订阅消息
async def on_message(message: Message):
    print(f"收到消息: {message.data}")

comm.message_bus.subscribe("my-topic", on_message)

# 发布消息
msg = Message(
    id="msg-1",
    sender="plugin-a",
    topic="my-topic",
    data={"key": "value"}
)
await comm.message_bus.publish(msg)

# 共享状态
await comm.shared_state.set("plugin-a", "key1", "value1")
value = await comm.shared_state.get("plugin-a", "key1")
```

**相关文件**：
- `src/lurkbot/plugins/communication.py`
- `tests/test_plugin_communication.py`

## 11. 未来优化方向

### 11.1 短期优化（Phase 6）

1. **插件编排**：支持插件依赖和执行顺序
2. **插件版本管理**：支持多版本共存和回滚
3. **插件性能分析**：提供详细的性能分析工具
4. **插件权限细化**：更细粒度的权限控制

### 11.2 长期优化（Phase 7+）

1. **分布式插件执行**：支持远程插件服务
2. **插件 WebAssembly 支持**：支持 WASM 插件
3. **插件 AI 辅助开发**：AI 辅助插件开发和调试
4. **插件生态系统**：建立完整的插件生态

## 12. 参考资料

### 12.1 相关文件

**核心模块**：
- `src/lurkbot/plugins/manager.py` - 插件管理器
- `src/lurkbot/plugins/loader.py` - 插件加载器
- `src/lurkbot/plugins/registry.py` - 插件注册表
- `src/lurkbot/plugins/sandbox.py` - 插件沙箱
- `src/lurkbot/plugins/manifest.py` - 插件清单
- `src/lurkbot/plugins/models.py` - 数据模型
- `src/lurkbot/agents/runtime.py` - Agent 运行时

**Phase 5-B 新增模块**：
- `src/lurkbot/plugins/hot_reload.py` - 插件热重载
- `src/lurkbot/plugins/marketplace.py` - 插件市场
- `src/lurkbot/plugins/container_sandbox.py` - 容器沙箱
- `src/lurkbot/plugins/communication.py` - 插件间通信

**测试文件**：
- `tests/test_plugin_*.py` - 所有插件系统测试

### 12.2 设计模式

- **单例模式**：PluginManager、PluginLoader、PluginRegistry、HotReloadManager、PluginMarketplace、PluginCommunication 使用全局单例
- **工厂模式**：PluginLoader 负责创建插件实例
- **观察者模式**：事件系统实现插件生命周期监控；MessageBus 实现发布-订阅模式
- **策略模式**：PluginSandbox 和 ContainerSandbox 根据配置应用不同的安全策略

### 12.3 技术参考

- [Pydantic Documentation](https://docs.pydantic.dev/)
- [asyncio Documentation](https://docs.python.org/3/library/asyncio.html)
- [Python Import System](https://docs.python.org/3/reference/import.html)
- [Watchdog Documentation](https://python-watchdog.readthedocs.io/)
- [Docker SDK for Python](https://docker-py.readthedocs.io/)
- [httpx Documentation](https://www.python-httpx.org/)
- [Resource Limits (Linux)](https://man7.org/linux/man-pages/man2/setrlimit.2.html)
