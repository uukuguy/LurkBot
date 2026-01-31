# LurkBot 示例插件

本目录包含 LurkBot 插件系统的示例插件，展示了插件开发的最佳实践。

## 示例插件列表

### 1. weather-plugin（天气查询插件）

**功能**: 查询指定城市的天气信息

**特点**:
- 使用 wttr.in API 获取实时天气数据
- 支持从用户查询中自动提取城市名称
- 提供详细的天气信息（温度、湿度、风速等）
- 需要网络权限

**使用示例**:
```bash
# 启用插件
lurkbot plugin enable weather-plugin

# 查看插件信息
lurkbot plugin info weather-plugin
```

**参数**:
- `city`: 城市名称（可选，默认从查询中提取或使用 Beijing）

### 2. time-utils-plugin（时间工具插件）

**功能**: 提供时间相关的工具函数

**特点**:
- 多时区时间查询
- 时间格式转换
- 支持常用城市时区映射
- 无需任何权限

**使用示例**:
```bash
# 启用插件
lurkbot plugin enable time-utils-plugin

# 查看插件信息
lurkbot plugin info time-utils-plugin
```

**参数**:
- `timezone`: 时区字符串（可选，默认 Asia/Shanghai）

### 3. system-info-plugin（系统信息插件）

**功能**: 查询系统资源使用情况

**特点**:
- CPU 使用率监控
- 内存使用情况
- 磁盘使用情况
- 网络统计信息
- 需要文件系统权限

**使用示例**:
```bash
# 启用插件
lurkbot plugin enable system-info-plugin

# 查看插件信息
lurkbot plugin info system-info-plugin
```

## 插件开发指南

### 基本结构

每个插件目录包含以下文件：

```
plugin-name/
├── plugin.json      # 插件清单（必需）
├── __init__.py      # Python 包初始化（必需）
└── main.py          # 插件实现（必需）
```

### plugin.json 格式

```json
{
  "name": "plugin-name",
  "version": "1.0.0",
  "author": {
    "name": "Your Name",
    "email": "your@email.com"
  },
  "description": "插件描述",
  "plugin_type": "tool",
  "entry_point": "main:PluginClass",
  "enabled": true,
  "permissions": {
    "filesystem": false,
    "network": false,
    "exec": false,
    "channels": []
  },
  "dependencies": [],
  "tags": ["tag1", "tag2"]
}
```

### 插件实现

```python
from lurkbot.plugins.models import (
    PluginExecutionContext,
    PluginExecutionResult,
)

class MyPlugin:
    """插件类"""

    async def execute(
        self, context: PluginExecutionContext
    ) -> PluginExecutionResult:
        """执行插件逻辑"""
        try:
            # 插件逻辑
            result_data = {"key": "value"}

            return PluginExecutionResult(
                success=True,
                data=result_data,
                result="格式化的结果文本",
                message="执行成功",
            )
        except Exception as e:
            return PluginExecutionResult(
                success=False,
                error=str(e),
                message="执行失败",
            )
```

## 测试插件

### 单元测试

```python
import pytest
from lurkbot.plugins.models import PluginExecutionContext
from your_plugin import YourPlugin

@pytest.mark.asyncio
async def test_plugin_execution():
    plugin = YourPlugin()
    context = PluginExecutionContext(
        user_id="test-user",
        channel_id="test-channel",
        session_id="test-session",
        input_data={"query": "test query"},
        parameters={},
    )

    result = await plugin.execute(context)
    assert result.success is True
```

### 集成测试

```bash
# 加载插件
lurkbot plugin load ./plugins/your-plugin

# 启用插件
lurkbot plugin enable your-plugin

# 测试执行（通过 Agent Runtime）
# 发送包含触发词的消息，观察插件是否执行
```

## 最佳实践

### 1. 错误处理

- 始终使用 try-except 捕获异常
- 返回清晰的错误消息
- 记录详细的错误日志

### 2. 性能优化

- 避免阻塞操作
- 使用异步 I/O
- 设置合理的超时时间
- 缓存频繁访问的数据

### 3. 安全性

- 最小权限原则
- 验证用户输入
- 避免执行不可信代码
- 保护敏感信息

### 4. 可维护性

- 清晰的代码注释
- 完整的文档字符串
- 遵循 PEP 8 规范
- 编写单元测试

## 更多资源

- [插件系统设计文档](../../docs/design/PLUGIN_SYSTEM_DESIGN.md)
- [插件开发指南](../../docs/design/PLUGIN_DEVELOPMENT_GUIDE.md)
- [插件 API 文档](../../docs/api/PLUGIN_API.md)

## 贡献

欢迎贡献更多示例插件！请参考现有插件的实现，并确保：

1. 代码质量高，注释完整
2. 包含完整的测试
3. 更新本 README 文档
4. 遵循插件开发规范

## 许可证

MIT License
