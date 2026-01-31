# Phase 8 快速参考

## 当前状态

**Phase 8: 插件系统实际应用集成** - 60% 完成

## 已创建的示例插件

### 1. weather-plugin (天气查询)
- **位置**: `.plugins/weather-plugin/`
- **功能**: 使用 wttr.in API 查询天气
- **依赖**: httpx>=0.24.0
- **权限**: network

### 2. time-utils-plugin (时间工具)
- **位置**: `.plugins/time-utils-plugin/`
- **功能**: 多时区时间查询
- **依赖**: 无
- **权限**: 无

### 3. system-info-plugin (系统信息)
- **位置**: `.plugins/system-info-plugin/`
- **功能**: CPU/内存/磁盘监控
- **依赖**: psutil>=5.9.0
- **权限**: filesystem

## 待修复的问题

### 优先级 1: PluginExecutionResult 字段

**问题**: 插件返回的结果缺少 `execution_time` 字段

**解决方案**: 检查 `src/lurkbot/plugins/models.py` 确认该字段是否由沙箱自动添加

### 优先级 2: 安装依赖

```bash
pip install httpx>=0.24.0 psutil>=5.9.0
```

## 测试命令

```bash
# 手动测试
python tests/manual/test_example_plugins_manual.py

# CLI 测试
lurkbot plugin list
lurkbot plugin info weather-plugin
```

## 重要发现

1. **插件目录**: `.plugins/` (不是 `plugins/`)
2. **Manifest 格式**:
   - `type` (不是 `plugin_type`)
   - `entry` + `main_class` (不是 `entry_point`)
   - `dependencies` 是字典 (不是列表)

## 下一步

1. 修复插件代码
2. 完成端到端测试
3. 完善文档
