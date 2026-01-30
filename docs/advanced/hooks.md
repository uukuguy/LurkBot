# Hooks

Hooks are event-driven automation triggers that execute actions when specific events occur in LurkBot.

## Overview

Hooks allow you to:

- Execute code when messages are received
- Run actions before/after tool execution
- Automate responses to specific patterns
- Integrate with external systems

## Implementation

Source: `src/lurkbot/hooks/`

LurkBot 的 Hooks 系统基于 PydanticAI 实现，包含以下核心组件：

| 组件 | 源文件 | 描述 |
|------|--------|------|
| `HookRegistry` | `registry.py` | 钩子注册表，管理钩子的注册、查询和触发 |
| `InternalHookEvent` | `types.py` | 钩子事件结构定义 |
| `HookPackage` | `types.py` | 钩子包，包含元数据和处理器 |

## Hook Event Types

LurkBot 定义了四种内部钩子事件类型：

```python
# Source: src/lurkbot/hooks/types.py:13
InternalHookEventType = Literal["command", "session", "agent", "gateway"]
```

| 事件类型 | 描述 | 示例 Action |
|----------|------|-------------|
| `command` | 命令相关事件 | `new`, `execute`, `complete` |
| `session` | 会话相关事件 | `created`, `ended`, `message` |
| `agent` | 代理相关事件 | `bootstrap`, `turn`, `complete` |
| `gateway` | 网关相关事件 | `connected`, `disconnected` |

## Event Structure

Source: `src/lurkbot/hooks/types.py:16-26`

```python
class InternalHookEvent(BaseModel):
    """钩子事件结构"""

    type: InternalHookEventType      # 事件类型: command, session, agent, gateway
    action: str                       # 具体动作
    session_key: str                  # 会话标识
    context: dict[str, object] = {}   # 上下文数据
    timestamp: datetime               # 事件时间戳
    messages: list[str] = []          # 消息列表
```

## Hook Package

Source: `src/lurkbot/hooks/types.py:43-64`

每个钩子由 `HookPackage` 封装，包含元数据和处理器：

```python
class HookMetadata(BaseModel):
    """钩子元数据"""

    name: str                         # 钩子名称
    emoji: str = "🔌"                 # 图标
    events: list[str] = []            # 监听的事件模式
    description: str = ""             # 描述
    requires: HookRequirements        # 依赖要求
    enabled: bool = True              # 是否启用
    priority: int = 100               # 优先级 (越小越优先)

class HookPackage(BaseModel):
    """钩子包"""

    metadata: HookMetadata            # 元数据
    handler: HookHandler              # 处理器函数
    source_path: str                  # 源文件路径
```

## Creating Hooks

### Programmatic Hooks

Source: `src/lurkbot/hooks/registry.py:168-186`

使用全局注册表注册钩子：

```python
from lurkbot.hooks.types import InternalHookEvent, HookMetadata, HookPackage
from lurkbot.hooks.registry import register_internal_hook, trigger_internal_hook

# 定义处理器
async def my_handler(event: InternalHookEvent) -> None:
    """处理钩子事件"""
    print(f"Event: {event.type}:{event.action}")
    print(f"Session: {event.session_key}")

# 创建钩子包
package = HookPackage(
    metadata=HookMetadata(
        name="my-hook",
        emoji="🔔",
        events=["session:*"],
        description="My custom hook",
        priority=50,
    ),
    handler=my_handler,
    source_path="my_hooks.py",
)

# 注册到全局注册表
register_internal_hook("session:*", package)
```

### Configuration File

Add hooks to `~/.lurkbot/hooks.yaml`:

```yaml
hooks:
  - name: log-messages
    event: session:message
    action: log
    config:
      file: ~/.lurkbot/logs/messages.log

  - name: notify-errors
    event: agent:complete
    condition: "result.success == false"
    action: webhook
    config:
      url: https://hooks.slack.com/...
      template: "Agent failed: {{result.error}}"

  - name: auto-greet
    event: session:created
    action: message
    config:
      content: "Hello! How can I help you today?"
```

## Event Patterns

Source: `src/lurkbot/hooks/registry.py:98-114`

钩子注册表支持通配符模式匹配：

```python
def _match_event_pattern(self, event_key: str, pattern: str) -> bool:
    """
    匹配事件模式

    支持通配符:
    - "command:*" 匹配所有 command 事件
    - "session:*" 匹配所有 session 事件
    - "command:new" 精确匹配
    """
    return fnmatch.fnmatch(event_key, pattern)
```

示例：

```python
# 匹配所有 session 事件
register_internal_hook("session:*", package)

# 匹配特定事件
register_internal_hook("command:execute", package)

# 匹配 agent 的 bootstrap 和 turn 事件
register_internal_hook("agent:bootstrap", package)
register_internal_hook("agent:turn", package)
```

## Hook Priority

Source: `src/lurkbot/hooks/registry.py:20-48`

钩子按优先级执行，**priority 数值越小，优先级越高**：

```python
def register(self, event_pattern: str, package: HookPackage) -> None:
    """注册钩子到事件模式"""
    # 按优先级插入 (priority 越小越靠前)
    packages = self._hooks[event_pattern]
    insert_pos = 0
    for i, pkg in enumerate(packages):
        if package.metadata.priority < pkg.metadata.priority:
            insert_pos = i
            break
        insert_pos = i + 1

    packages.insert(insert_pos, package)
```

示例：

```python
# 高优先级钩子 (优先执行)
security_hook = HookPackage(
    metadata=HookMetadata(
        name="security-check",
        priority=10,  # 低数值 = 高优先级
        events=["command:*"],
    ),
    handler=security_handler,
    source_path="security.py",
)

# 普通优先级钩子
logging_hook = HookPackage(
    metadata=HookMetadata(
        name="logging",
        priority=100,  # 默认优先级
        events=["command:*"],
    ),
    handler=logging_handler,
    source_path="logging.py",
)
```

## Triggering Hooks

Source: `src/lurkbot/hooks/registry.py:116-142`

触发钩子事件：

```python
from lurkbot.hooks.registry import trigger_internal_hook
from lurkbot.hooks.types import InternalHookEvent

# 创建事件
event = InternalHookEvent(
    type="session",
    action="created",
    session_key="telegram:123456789:main",
    context={"user_id": "123456789"},
)

# 触发所有匹配的钩子
await trigger_internal_hook(event)
```

执行流程：

1. 根据事件类型和 action 构建 event key (例如：`"session:created"`)
2. 查找所有匹配的钩子处理器
3. 按优先级排序
4. 依次执行每个处理器
5. 捕获并记录异常（不中断后续钩子）

## Hook Requirements

Source: `src/lurkbot/hooks/types.py:33-41`

钩子可以声明依赖要求：

```python
class HookRequirements(BaseModel):
    """钩子依赖要求"""

    bins: list[str] = []           # 必需的二进制命令
    env: list[str] = []            # 必需的环境变量
    python_packages: list[str] = [] # 必需的 Python 包
```

示例：

```python
package = HookPackage(
    metadata=HookMetadata(
        name="docker-watcher",
        events=["command:*"],
        requires=HookRequirements(
            bins=["docker"],
            env=["DOCKER_HOST"],
        ),
    ),
    handler=docker_handler,
    source_path="docker_hooks.py",
)
```

## Examples

### Session Event Hook

```python
from lurkbot.hooks.types import InternalHookEvent, HookMetadata, HookPackage
from lurkbot.hooks.registry import register_internal_hook

async def on_session_created(event: InternalHookEvent) -> None:
    """Handle new session creation."""
    print(f"New session: {event.session_key}")
    event.messages.append("Welcome to LurkBot!")

package = HookPackage(
    metadata=HookMetadata(
        name="session-greeter",
        emoji="👋",
        events=["session:created"],
        description="Greet users on new sessions",
        priority=50,
    ),
    handler=on_session_created,
    source_path="greeting_hook.py",
)

register_internal_hook("session:created", package)
```

### Command Event Hook

```python
async def on_command_execute(event: InternalHookEvent) -> None:
    """Log command executions."""
    command = event.context.get("command", "unknown")
    print(f"Executing command: {command}")

package = HookPackage(
    metadata=HookMetadata(
        name="command-logger",
        events=["command:execute"],
        priority=100,
    ),
    handler=on_command_execute,
    source_path="logger_hook.py",
)

register_internal_hook("command:execute", package)
```

### Security Hook

```python
async def security_check(event: InternalHookEvent) -> None:
    """Block dangerous commands."""
    command = event.context.get("command", "")
    if "rm -rf" in command or "sudo" in command:
        raise ValueError("Dangerous command blocked by security hook")

package = HookPackage(
    metadata=HookMetadata(
        name="security-block",
        emoji="🛡️",
        events=["command:*"],
        description="Block dangerous commands",
        priority=1,  # 最高优先级
    ),
    handler=security_check,
    source_path="security_hook.py",
)

register_internal_hook("command:*", package)
```

## Hook Registry API

Source: `src/lurkbot/hooks/registry.py`

### 核心方法

```python
class HookRegistry:
    def register(self, event_pattern: str, package: HookPackage) -> None:
        """注册钩子到事件模式"""

    def unregister(self, event_pattern: str, hook_name: str) -> bool:
        """取消注册钩子"""

    def get_handlers_for_event(self, event: InternalHookEvent) -> list[HookPackage]:
        """获取匹配事件的所有钩子处理器"""

    async def trigger(self, event: InternalHookEvent) -> None:
        """触发事件，执行所有匹配的钩子处理器"""

    def list_hooks(self, event_pattern: str | None = None) -> list[HookPackage]:
        """列出所有注册的钩子"""
```

### 全局辅助函数

```python
# 注册钩子到全局注册表
register_internal_hook(event_pattern: str, package: HookPackage) -> None

# 触发钩子事件
await trigger_internal_hook(event: InternalHookEvent) -> None

# 获取全局注册表
get_global_registry() -> HookRegistry
```

## Troubleshooting

### Hook not triggering

1. 检查事件模式是否正确
   - 使用 `list_hooks()` 查看已注册的钩子
   - 确认事件类型和 action 匹配

2. 检查钩子是否启用
   - 确保 `metadata.enabled = True`

3. 检查依赖要求
   - 确保所需的二进制命令和环境变量存在

4. 查看日志
   ```bash
   tail -f ~/.lurkbot/logs/hooks.log
   ```

### Hook errors

钩子执行错误会被捕获并记录，不会中断后续钩子：

Source: `src/lurkbot/hooks/registry.py:133-142`

```python
for pkg in packages:
    try:
        await pkg.handler(event)
    except Exception as e:
        logger.error(f"Hook '{pkg.metadata.name}' failed: {e}")
        event.messages.append(f"❌ Hook '{pkg.metadata.name}' failed: {e}")
```

### Debugging hooks

启用 debug 日志：

```python
from loguru import logger
logger.add("hooks_debug.log", level="DEBUG")
```

查看钩子注册信息：

```python
from lurkbot.hooks.registry import get_global_registry

registry = get_global_registry()
hooks = registry.list_hooks()

for hook in hooks:
    print(f"Hook: {hook.metadata.name}")
    print(f"  Events: {hook.metadata.events}")
    print(f"  Priority: {hook.metadata.priority}")
    print(f"  Enabled: {hook.metadata.enabled}")
```

---

## See Also

- [Skills](skills.md) - Extensible plugins
- [Gateway](gateway.md) - Gateway architecture
- [Configuration](../user-guide/configuration/index.md) - Configuration options
