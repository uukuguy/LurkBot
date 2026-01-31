# LurkBot 插件系统用户指南

## 目录

- [1. 简介](#1-简介)
- [2. 快速开始](#2-快速开始)
- [3. 插件管理](#3-插件管理)
- [4. 插件配置](#4-插件配置)
- [5. 使用示例](#5-使用示例)
- [6. 常见问题](#6-常见问题)
- [7. 故障排除](#7-故障排除)

## 1. 简介

### 1.1 什么是插件系统？

LurkBot 插件系统允许你通过安装插件来扩展 AI 助手的功能。插件可以：

- 🌤️ **查询外部数据**：天气、新闻、股票等
- 🔧 **执行系统操作**：文件处理、系统监控等
- 🔌 **集成第三方服务**：数据库、API、云服务等
- 🎨 **自定义功能**：根据你的需求开发专属功能

### 1.2 插件类型

| 类型 | 说明 | 示例 |
|------|------|------|
| **Tool** | 提供独立工具功能 | 天气查询、计算器 |
| **Middleware** | 处理数据流转换 | 数据清洗、格式转换 |
| **Hook** | 响应系统事件 | 日志记录、监控告警 |
| **Integration** | 集成外部服务 | 数据库连接、API 集成 |

### 1.3 系统要求

- Python 3.12+
- LurkBot v0.1.0+
- 网络连接（部分插件需要）

## 2. 快速开始

### 2.1 安装 LurkBot

```bash
# 克隆仓库
git clone https://github.com/your-org/lurkbot.git
cd lurkbot

# 安装依赖
uv sync

# 验证安装
lurkbot --version
```

### 2.2 查看可用插件

```bash
# 列出所有插件
lurkbot plugin list

# 输出示例：
# ┌──────────────────────┬─────────┬──────────┬─────────────────────────┐
# │ Name                 │ Version │ Status   │ Description             │
# ├──────────────────────┼─────────┼──────────┼─────────────────────────┤
# │ weather-plugin       │ 1.0.0   │ enabled  │ 天气查询插件            │
# │ time-utils-plugin    │ 1.0.0   │ enabled  │ 时间工具插件            │
# │ system-info-plugin   │ 1.0.0   │ enabled  │ 系统信息插件            │
# └──────────────────────┴─────────┴──────────┴─────────────────────────┘
```

### 2.3 查看插件详情

```bash
# 查看插件信息
lurkbot plugin info weather-plugin

# 输出示例：
# Plugin: weather-plugin
# Version: 1.0.0
# Type: tool
# Status: enabled
# Description: 查询实时天气信息
#
# Permissions:
#   - network: true
#   - filesystem: false
#
# Dependencies:
#   - httpx>=0.27.0
```

### 2.4 启用/禁用插件

```bash
# 启用插件
lurkbot plugin enable weather-plugin

# 禁用插件
lurkbot plugin disable weather-plugin
```

## 3. 插件管理

### 3.1 插件目录结构

插件默认存放在 `.plugins/` 目录：

```
.plugins/
├── weather-plugin/
│   ├── plugin.json       # 插件配置
│   ├── main.py           # 插件代码
│   ├── requirements.txt  # 依赖列表
│   └── README.md         # 插件文档
├── time-utils-plugin/
└── system-info-plugin/
```

### 3.2 安装插件

**方式 1：从本地目录安装**

```bash
# 将插件复制到 .plugins/ 目录
cp -r my-plugin .plugins/

# 重新加载插件
lurkbot plugin reload
```

**方式 2：从 Git 仓库安装**（计划中）

```bash
# 从 GitHub 安装
lurkbot plugin install github:username/plugin-name

# 从本地 Git 仓库安装
lurkbot plugin install git:///path/to/plugin
```

### 3.3 卸载插件

```bash
# 禁用插件
lurkbot plugin disable my-plugin

# 删除插件目录
rm -rf .plugins/my-plugin

# 重新加载
lurkbot plugin reload
```

### 3.4 更新插件

```bash
# 查看插件版本
lurkbot plugin info my-plugin

# 手动更新：替换插件目录
cp -r my-plugin-v2.0.0 .plugins/my-plugin

# 重新加载
lurkbot plugin reload
```

## 4. 插件配置

### 4.1 配置文件位置

插件配置存储在 `plugin.json` 文件中：

```json
{
  "name": "weather-plugin",
  "version": "1.0.0",
  "enabled": true,
  "config": {
    "api_key": "your-api-key-here",
    "units": "metric",
    "cache_ttl": 300
  }
}
```

### 4.2 修改配置

**方式 1：直接编辑 plugin.json**

```bash
# 编辑配置文件
vim .plugins/weather-plugin/plugin.json

# 重新加载插件
lurkbot plugin reload
```

**方式 2：使用 CLI 命令**（计划中）

```bash
# 设置配置项
lurkbot plugin config weather-plugin api_key "your-api-key"

# 查看配置
lurkbot plugin config weather-plugin
```

### 4.3 环境变量

部分插件支持通过环境变量配置：

```bash
# 设置环境变量
export WEATHER_API_KEY="your-api-key"
export WEATHER_UNITS="metric"

# 启动 LurkBot
lurkbot agent run
```

### 4.4 权限配置

插件权限在 `plugin.json` 中定义：

```json
{
  "permissions": {
    "filesystem": false,  // 文件系统访问
    "network": true,      // 网络访问
    "exec": false,        // 命令执行
    "channels": ["discord", "slack"]  // 允许的频道
  }
}
```

**权限说明**：

- `filesystem`: 允许读写本地文件
- `network`: 允许发起网络请求
- `exec`: 允许执行系统命令（⚠️ 高风险）
- `channels`: 限制插件可访问的频道

## 5. 使用示例

### 5.1 天气查询插件

**功能**：查询全球城市的实时天气信息

**配置**：

```json
{
  "config": {
    "default_city": "Beijing"
  }
}
```

**使用**：

```python
from lurkbot.plugins.manager import get_plugin_manager
from lurkbot.plugins.models import PluginExecutionContext

# 获取插件管理器
manager = get_plugin_manager()

# 创建执行上下文
context = PluginExecutionContext(
    user_id="user-123",
    input_data={"city": "Shanghai"}
)

# 执行插件
result = await manager.execute_plugin("weather-plugin", context)

# 查看结果
print(result.result)
# 输出: {'city': 'Shanghai', 'temperature': 25, 'condition': 'sunny'}
```

**在 Agent 中使用**：

```python
from lurkbot.agents.runtime import run_embedded_agent

# 启用插件的 Agent
result = await run_embedded_agent(
    user_message="What's the weather in Shanghai?",
    enable_plugins=True
)

# 插件结果会自动注入到 system_prompt
print(result.system_prompt)
# 包含: "weather-plugin result: {'city': 'Shanghai', ...}"
```

### 5.2 时间工具插件

**功能**：多时区时间转换和格式化

**使用**：

```python
context = PluginExecutionContext(
    input_data={
        "timezone": "America/New_York"
    }
)

result = await manager.execute_plugin("time-utils-plugin", context)

print(result.result)
# 输出: {'timezone': 'America/New_York', 'time': '2026-01-31 10:30:00', ...}
```

### 5.3 系统信息插件

**功能**：监控系统 CPU、内存、磁盘使用情况

**使用**：

```python
context = PluginExecutionContext(
    user_id="admin-user"
)

result = await manager.execute_plugin("system-info-plugin", context)

print(result.result)
# 输出: {'cpu_percent': 45.2, 'memory_percent': 62.8, 'disk_usage': {...}}
```

### 5.4 批量执行插件

```python
# 并发执行多个插件
plugins = ["weather-plugin", "time-utils-plugin", "system-info-plugin"]

tasks = [
    manager.execute_plugin(plugin, context)
    for plugin in plugins
]

results = await asyncio.gather(*tasks)

for plugin, result in zip(plugins, results):
    print(f"{plugin}: {result.success}")
```

## 6. 常见问题

### 6.1 插件相关

**Q: 如何知道插件是否正常工作？**

A: 使用以下命令检查：

```bash
# 查看插件状态
lurkbot plugin info my-plugin

# 查看插件事件日志
lurkbot plugin events my-plugin

# 手动测试插件
python tests/manual/test_example_plugins_manual.py
```

**Q: 插件执行失败怎么办？**

A: 检查以下几点：

1. 插件是否已启用：`lurkbot plugin list`
2. 依赖是否已安装：`pip list | grep <dependency>`
3. 配置是否正确：检查 `plugin.json`
4. 权限是否足够：检查 `permissions` 配置
5. 查看错误日志：`lurkbot plugin events my-plugin`

**Q: 如何查看插件执行时间？**

A: 执行结果中包含 `execution_time` 字段：

```python
result = await manager.execute_plugin("my-plugin", context)
print(f"执行时间: {result.execution_time}秒")
```

### 6.2 配置相关

**Q: 如何保护敏感配置（如 API Key）？**

A: 推荐使用环境变量：

```bash
# 设置环境变量
export MY_PLUGIN_API_KEY="secret-key"

# 在插件中读取
api_key = os.getenv("MY_PLUGIN_API_KEY")
```

**Q: 配置修改后需要重启吗？**

A: 需要重新加载插件：

```bash
lurkbot plugin reload
```

### 6.3 性能相关

**Q: 插件执行太慢怎么办？**

A: 优化建议：

1. 使用缓存减少重复请求
2. 使用异步操作避免阻塞
3. 增加超时时间配置
4. 优化插件代码逻辑

**Q: 如何限制插件执行时间？**

A: 在 `plugin.json` 中配置：

```json
{
  "config": {
    "max_execution_time": 60.0
  }
}
```

### 6.4 安全相关

**Q: 插件是否安全？**

A: LurkBot 插件系统提供以下安全机制：

1. **权限控制**：插件需要明确声明所需权限
2. **沙箱隔离**：插件在隔离环境中执行
3. **超时保护**：防止插件无限执行
4. **错误捕获**：插件错误不会影响主程序

**Q: 如何审查插件安全性？**

A: 安装前检查：

1. 查看 `plugin.json` 中的权限配置
2. 阅读插件源代码（`main.py`）
3. 检查依赖列表（`requirements.txt`）
4. 查看插件文档和评价

## 7. 故障排除

### 7.1 插件加载失败

**症状**：

```
ERROR: 无法加载插件 my-plugin
```

**排查步骤**：

1. **检查插件目录结构**：

```bash
ls -la .plugins/my-plugin/
# 应包含: plugin.json, main.py
```

2. **验证 plugin.json 格式**：

```bash
cat .plugins/my-plugin/plugin.json | python -m json.tool
```

3. **检查 Python 语法**：

```bash
python -m py_compile .plugins/my-plugin/main.py
```

4. **查看详细错误**：

```bash
lurkbot plugin load my-plugin --verbose
```

### 7.2 权限错误

**症状**：

```
ERROR: 权限错误: 插件无权访问网络
```

**解决方案**：

在 `plugin.json` 中添加所需权限：

```json
{
  "permissions": {
    "network": true
  }
}
```

然后重新加载：

```bash
lurkbot plugin reload
```

### 7.3 依赖缺失

**症状**：

```
ModuleNotFoundError: No module named 'httpx'
```

**解决方案**：

1. **检查依赖声明**：

```bash
cat .plugins/my-plugin/plugin.json | grep dependencies
```

2. **手动安装依赖**：

```bash
pip install httpx
```

3. **或使用插件安装命令**（自动安装依赖）：

```bash
lurkbot plugin install .plugins/my-plugin
```

### 7.4 执行超时

**症状**：

```
ERROR: 插件执行超时（30秒）
```

**解决方案**：

**方式 1：增加超时时间**

```json
{
  "config": {
    "max_execution_time": 120.0
  }
}
```

**方式 2：优化插件代码**

```python
# 使用异步操作
async def execute(context):
    # ❌ 同步阻塞
    # result = requests.get(url)

    # ✅ 异步非阻塞
    async with httpx.AsyncClient() as client:
        result = await client.get(url)

    return result
```

### 7.5 配置错误

**症状**：

```
ERROR: 配置项 api_key 未设置
```

**解决方案**：

1. **检查配置文件**：

```bash
cat .plugins/my-plugin/plugin.json
```

2. **添加缺失配置**：

```json
{
  "config": {
    "api_key": "your-api-key-here"
  }
}
```

3. **或使用环境变量**：

```bash
export MY_PLUGIN_API_KEY="your-api-key"
```

### 7.6 获取帮助

如果以上方法无法解决问题：

1. **查看日志**：

```bash
tail -f logs/lurkbot.log
```

2. **运行诊断**：

```bash
lurkbot plugin diagnose my-plugin
```

3. **提交 Issue**：

访问 [GitHub Issues](https://github.com/your-org/lurkbot/issues) 并提供：
- 插件名称和版本
- 错误信息
- 配置文件内容
- 系统环境信息

4. **社区支持**：

- 讨论区: https://github.com/your-org/lurkbot/discussions
- 文档: https://docs.lurkbot.dev

---

## 附录

### A. 内置插件列表

| 插件名称 | 功能 | 权限 |
|---------|------|------|
| weather-plugin | 天气查询 | network |
| time-utils-plugin | 时间工具 | - |
| system-info-plugin | 系统监控 | filesystem |

### B. 插件开发资源

- [插件开发指南](./PLUGIN_DEVELOPMENT_GUIDE.md)
- [插件 API 文档](../api/PLUGIN_API.md)
- [插件系统设计](./PLUGIN_SYSTEM_DESIGN.md)

### C. 版本历史

- **v0.1.0** (2026-01-31): 初始版本，支持基础插件功能
- **v0.2.0** (计划中): 插件市场、自动更新

---

**祝你使用愉快！** 🚀

如有问题，欢迎通过 [GitHub Issues](https://github.com/your-org/lurkbot/issues) 反馈。
