# LurkBot 示例插件

本目录包含 LurkBot 插件系统的示例插件，展示如何开发和使用插件。

## 📦 示例插件列表

### 1. Weather Plugin (天气查询插件)

**目录**: `weather/`

**功能**: 查询城市天气信息

**权限**: 需要网络访问

**使用示例**:
```python
from lurkbot.plugins import get_plugin_manager, PluginExecutionContext

manager = get_plugin_manager()
await manager.load_plugin(Path("examples/plugins/weather"), manifest)

context = PluginExecutionContext(
    input_data={"city": "Beijing"},
    parameters={"units": "metric"}
)

result = await manager.execute_plugin("weather-plugin", context)
print(result.result)  # {'city': 'Beijing', 'temperature': 25, ...}
```

### 2. Translator Plugin (翻译插件)

**目录**: `translator/`

**功能**: 文本翻译

**权限**: 需要网络访问

**使用示例**:
```python
context = PluginExecutionContext(
    input_data={"text": "Hello"},
    parameters={"source_lang": "en", "target_lang": "zh"}
)

result = await manager.execute_plugin("translator-plugin", context)
print(result.result)  # {'translated_text': '你好', ...}
```

### 3. Skill Exporter Plugin (技能导出插件)

**目录**: `skill-exporter/`

**功能**: 将 Phase 3-C 学习的技能导出为独立插件

**权限**: 需要文件系统访问

**使用示例**:
```python
context = PluginExecutionContext(
    input_data={"skill_name": "my-skill"},
    parameters={"plugin_name": "skill-my-skill"}
)

result = await manager.execute_plugin("skill-exporter", context)
print(result.result)  # {'success': True, 'plugin_dir': '...', ...}
```

## 🚀 快速开始

### 1. 加载所有示例插件

```python
from pathlib import Path
from lurkbot.plugins import get_plugin_manager

manager = get_plugin_manager()

# 自动发现并加载所有插件
count = await manager.discover_and_load_all(workspace_root=Path.cwd())
print(f"加载了 {count} 个插件")

# 列出所有已启用的插件
enabled_plugins = manager.list_enabled_plugins()
for plugin in enabled_plugins:
    print(f"- {plugin.name} v{plugin.manifest.version}")
```

### 2. 执行插件

```python
from lurkbot.plugins import PluginExecutionContext

# 创建执行上下文
context = PluginExecutionContext(
    user_id="user123",
    channel_id="discord-general",
    input_data={"city": "Shanghai"},
    parameters={"units": "metric"}
)

# 执行单个插件
result = await manager.execute_plugin("weather-plugin", context)
if result.success:
    print(f"结果: {result.result}")
    print(f"执行时间: {result.execution_time}秒")
else:
    print(f"错误: {result.error}")
```

### 3. 并发执行多个插件

```python
# 执行所有已启用的插件
results = await manager.execute_plugins(context)

for plugin_name, result in results.items():
    if result.success:
        print(f"{plugin_name}: {result.result}")
    else:
        print(f"{plugin_name} 失败: {result.error}")
```

## 📝 插件开发指南

### 插件结构

```
my-plugin/
├── plugin.json          # 插件清单
├── main.py              # 插件入口文件
└── README.md            # 插件说明（可选）
```

### 插件清单 (plugin.json)

```json
{
  "name": "my-plugin",
  "version": "1.0.0",
  "description": "My awesome plugin",
  "type": "tool",
  "language": "python",
  "entry": "main.py",
  "main_class": "MyPlugin",
  "permissions": {
    "filesystem": false,
    "network": true,
    "exec": false
  },
  "tags": ["example"],
  "enabled": true
}
```

### 插件类实现

```python
from typing import Any

class MyPlugin:
    """My plugin implementation"""

    def __init__(self):
        self.enabled = False

    async def initialize(self, config: dict[str, Any]) -> None:
        """初始化插件"""
        pass

    async def execute(self, context: dict[str, Any]) -> Any:
        """执行插件功能"""
        # 从 context 获取输入
        input_data = context.get("input_data", {})
        parameters = context.get("parameters", {})

        # 执行业务逻辑
        result = {"status": "success"}

        return result

    async def cleanup(self) -> None:
        """清理资源"""
        pass

    async def on_enable(self) -> None:
        """插件启用时的回调"""
        self.enabled = True

    async def on_disable(self) -> None:
        """插件禁用时的回调"""
        self.enabled = False
```

## 🔒 权限说明

插件可以请求以下权限：

- **filesystem**: 文件系统访问
- **network**: 网络访问
- **exec**: 命令执行
- **channels**: 特定频道访问

权限在 `plugin.json` 的 `permissions` 字段中声明。

## 📚 更多资源

- [插件系统设计文档](../../docs/design/PLUGIN_SYSTEM_DESIGN.md)
- [插件开发指南](../../docs/design/PLUGIN_DEVELOPMENT_GUIDE.md)
- [LurkBot 架构文档](../../docs/design/ARCHITECTURE_DESIGN.md)

## 🤝 贡献

欢迎贡献更多示例插件！请参考现有插件的结构和实现。
