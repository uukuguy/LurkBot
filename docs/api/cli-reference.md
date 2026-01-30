# CLI Reference

Complete reference for all LurkBot CLI commands.

## Implementation

Source: `src/lurkbot/cli/main.py`

LurkBot CLI 使用 [Typer](https://typer.tiangolo.com/) 构建。

```python
app = typer.Typer(
    name="lurkbot",
    help="LurkBot - Python port of MoltBot AI assistant",
    no_args_is_help=True,
)
```

## Global Options

```bash
lurkbot [OPTIONS] COMMAND [ARGS]
```

| Option | Description |
|--------|-------------|
| `--version` | Show version and exit |
| `--help` | Show help message |

## Commands

### version

显示版本信息。

Source: `src/lurkbot/cli/main.py:20-25`

```bash
lurkbot version
```

Output:

```
LurkBot v0.1.0
```

---

### gateway

启动 Gateway 服务器。

Source: `src/lurkbot/cli/main.py:28-35`

```bash
lurkbot gateway [OPTIONS]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--host` | `0.0.0.0` | Host to bind to |
| `--port` | `8000` | Port to listen on |

**示例**:

```bash
# 默认配置启动
lurkbot gateway

# 指定端口
lurkbot gateway --port 18789

# 指定主机和端口
lurkbot gateway --host 127.0.0.1 --port 18789
```

---

### chat

启动交互式聊天会话。

Source: `src/lurkbot/cli/main.py:38-46`

```bash
lurkbot chat [OPTIONS]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--model` | `anthropic:claude-sonnet-4-20250514` | AI model to use |
| `--workspace` | `.` | Workspace directory |

**示例**:

```bash
# 默认模型启动聊天
lurkbot chat

# 指定模型
lurkbot chat --model anthropic:claude-opus-4-20250514

# 指定工作区
lurkbot chat --workspace /path/to/project
```

---

### wizard

运行交互式配置向导。

Source: `src/lurkbot/cli/main.py:49-128`

```bash
lurkbot wizard [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--mode`, `-m` | Setup mode: `local` or `remote` |
| `--flow`, `-f` | Setup flow: `quickstart` or `advanced` |
| `--workspace`, `-w` | Workspace directory |
| `--accept-risk` | Accept security risk warning without prompt |
| `--skip-channels` | Skip channel configuration |
| `--skip-skills` | Skip skill configuration |

**示例**:

```bash
# 交互式设置
lurkbot wizard

# 快速设置（使用默认值）
lurkbot wizard --flow quickstart

# 本地 Gateway 设置
lurkbot wizard --mode local

# 跳过部分配置
lurkbot wizard --skip-channels --skip-skills
```

---

### reset

重置 LurkBot 配置。

Source: `src/lurkbot/cli/main.py:131-186`

```bash
lurkbot reset [OPTIONS]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--scope`, `-s` | `config` | Reset scope |
| `--force`, `-f` | `false` | Skip confirmation prompt |

**重置范围**:

| Scope | Description |
|-------|-------------|
| `config` | Reset config files only |
| `config+creds+sessions` | Reset config, credentials, and sessions |
| `full` | Full reset (everything) |

**示例**:

```bash
# 交互式重置
lurkbot reset

# 重置配置文件
lurkbot reset --scope config

# 完全重置（无确认）
lurkbot reset --scope full --force
```

---

### security

安全相关命令子组。

Source: `src/lurkbot/cli/security.py`

```bash
lurkbot security COMMAND [ARGS]
```

详细信息请查看 `lurkbot security --help`。

---

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error / User cancelled |

---

## Environment Variables

CLI 选项可以通过环境变量设置：

```bash
# 格式: LURKBOT_<SECTION>__<OPTION>
export LURKBOT_GATEWAY__PORT=8080
export LURKBOT_AGENT__MODEL=claude-sonnet-4-20250514
```

---

## See Also

- [User Guide CLI](../user-guide/cli/index.md) - 用户指南
- [Configuration](../user-guide/configuration/index.md) - 配置选项
- [Gateway](../advanced/gateway.md) - Gateway 架构
