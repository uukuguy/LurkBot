# Daemon Mode

Run LurkBot as a background service for production deployments.

## Overview

LurkBot provides cross-platform daemon service management, supporting:

- **macOS**: launchd (LaunchAgent)
- **Linux**: systemd (user service)
- **Windows**: schtasks (计划任务)

## Implementation

Source: `src/lurkbot/daemon/`

| 组件 | 源文件 | 描述 |
|------|--------|------|
| `GatewayService` | `service.py` | 服务抽象接口 |
| `ServiceRuntime` | `service.py` | 运行时状态数据模型 |
| `ServiceInstallArgs` | `service.py` | 安装参数数据模型 |
| `LaunchdService` | `launchd.py` | macOS launchd 实现 |
| `SystemdService` | `systemd.py` | Linux systemd 实现 |
| `SchtasksService` | `schtasks.py` | Windows schtasks 实现 |
| `DiagnosticResult` | `diagnostics.py` | 诊断结果数据模型 |
| Path utilities | `paths.py` | 路径解析工具 |
| Constants | `constants.py` | 常量定义 |

## Service Interface

Source: `src/lurkbot/daemon/service.py:63-159`

```python
class GatewayService(ABC):
    """
    守护进程服务抽象接口

    支持平台:
    - macOS: launchd (LaunchAgent)
    - Linux: systemd (user service)
    - Windows: schtasks (计划任务)
    """

    @property
    @abstractmethod
    def label(self) -> str:
        """服务标签/名称"""
        pass

    @abstractmethod
    async def install(self, args: ServiceInstallArgs) -> None:
        """安装服务"""
        pass

    @abstractmethod
    async def uninstall(self) -> None:
        """卸载服务"""
        pass

    @abstractmethod
    async def start(self) -> None:
        """启动服务"""
        pass

    @abstractmethod
    async def stop(self) -> None:
        """停止服务"""
        pass

    @abstractmethod
    async def restart(self) -> None:
        """重启服务"""
        pass

    @abstractmethod
    async def is_loaded(self) -> bool:
        """检查服务是否已加载"""
        pass

    @abstractmethod
    async def get_runtime(self) -> ServiceRuntime:
        """获取运行时状态"""
        pass
```

## Service Runtime

Source: `src/lurkbot/daemon/service.py:16-40`

```python
@dataclass
class ServiceRuntime:
    """服务运行时状态"""

    status: Literal["running", "stopped", "unknown"]
    """服务运行状态"""

    state: str | None = None
    """平台特定的状态字符串"""

    sub_state: str | None = None
    """平台特定的子状态字符串"""

    pid: int | None = None
    """进程 PID"""

    last_exit_status: int | None = None
    """最后退出状态码"""

    last_exit_reason: str | None = None
    """最后退出原因"""
```

## Service Install Args

Source: `src/lurkbot/daemon/service.py:43-61`

```python
@dataclass
class ServiceInstallArgs:
    """服务安装参数"""

    port: int = 18789
    """Gateway 监听端口"""

    bind: str = "loopback"
    """绑定地址类型: loopback / lan"""

    profile: str | None = None
    """Profile 名称（用于多实例）"""

    workspace: str | None = None
    """工作区路径"""
```

## Platform Resolution

Source: `src/lurkbot/daemon/service.py:162-195`

```python
def resolve_gateway_service(profile: str | None = None) -> GatewayService:
    """根据平台选择服务实现"""
    system = platform.system()

    if system == "Darwin":
        from .launchd import LaunchdService
        return LaunchdService(profile=profile)

    elif system == "Linux":
        from .systemd import SystemdService
        return SystemdService(profile=profile)

    elif system == "Windows":
        from .schtasks import SchtasksService
        return SchtasksService(profile=profile)

    else:
        raise RuntimeError(f"Unsupported platform: {system}")
```

## Service Labels

Source: `src/lurkbot/daemon/constants.py:11-18`

| 平台 | 标签格式 | 示例 |
|------|----------|------|
| macOS | Reverse Domain Notation | `bot.lurk.gateway` |
| Linux | systemd unit name | `lurkbot-gateway` |
| Windows | Task name | `lurkbot-gateway` |

多实例支持（Profile）：
- macOS: `bot.lurk.{profile}`
- Linux: `lurkbot-gateway-{profile}`
- Windows: `lurkbot-gateway-{profile}`

## CLI Commands

### Install Service

```bash
lurkbot daemon install
```

Options:
- `--port`: Gateway 监听端口（默认 18789）
- `--bind`: 绑定地址类型（loopback / lan）
- `--profile`: Profile 名称（用于多实例）
- `--workspace`: 工作区路径

### Uninstall Service

```bash
lurkbot daemon uninstall
```

### Start Service

```bash
lurkbot daemon start
```

### Stop Service

```bash
lurkbot daemon stop
```

### Restart Service

```bash
lurkbot daemon restart
```

### Check Status

```bash
lurkbot daemon status
```

## Managing the Daemon

### Check Status

```bash
lurkbot daemon status
```

Output:

```
Gateway Status: Running
  PID: 12345
  Address: ws://127.0.0.1:18789
```

## Directory Structure

Source: `src/lurkbot/daemon/paths.py`

```
~/.lurkbot/
├── logs/
│   ├── gateway.log        # Main gateway log
│   └── gateway.err.log    # Error output
└── run/
    └── gateway.pid        # Gateway PID file
```

### Path Functions

```python
from lurkbot.daemon import (
    get_lurkbot_home,        # ~/.lurkbot/
    get_logs_dir,            # ~/.lurkbot/logs/
    get_run_dir,             # ~/.lurkbot/run/
    get_gateway_pid_path,    # ~/.lurkbot/run/gateway.pid
    get_gateway_log_path,    # ~/.lurkbot/logs/gateway.log
    get_gateway_err_log_path,  # ~/.lurkbot/logs/gateway.err.log
    ensure_directories,      # 确保所有目录存在
)
```

### View Logs

```bash
# Follow main log
tail -f ~/.lurkbot/logs/gateway.log

# View errors
tail -f ~/.lurkbot/logs/gateway.err.log
```

## Platform Implementations

### macOS: Launchd

Source: `src/lurkbot/daemon/launchd.py`

使用 LaunchAgent 管理后台服务。

**配置文件位置**: `~/Library/LaunchAgents/bot.lurk.gateway.plist`

**服务标签**: `bot.lurk.gateway` (Reverse Domain Notation)

```python
class LaunchdService(GatewayService):
    """macOS Launchd 服务实现"""

    @property
    def plist_path(self) -> Path:
        """~/Library/LaunchAgents/{label}.plist"""
        return Path.home() / "Library" / "LaunchAgents" / f"{self._label}.plist"

    async def install(self, args: ServiceInstallArgs) -> None:
        """安装 LaunchAgent"""
        plist = {
            "Label": self._label,
            "RunAtLoad": True,
            "KeepAlive": True,
            "ProgramArguments": [
                "/usr/local/bin/lurkbot",
                "gateway", "run",
                "--port", str(args.port),
                "--bind", args.bind,
            ],
            "StandardOutPath": str(get_logs_dir() / "gateway.log"),
            "StandardErrorPath": str(get_logs_dir() / "gateway.err.log"),
        }
        # 写入 plist 文件并加载服务
        await self._launchctl_exec(["load", str(self.plist_path)])

    async def start(self) -> None:
        """使用 kickstart 启动服务"""
        await self._launchctl_exec(
            ["kickstart", f"gui/{self._get_uid()}/{self._label}"]
        )

    async def stop(self) -> None:
        """使用 kill 停止服务"""
        await self._launchctl_exec(
            ["kill", "TERM", f"gui/{self._get_uid()}/{self._label}"]
        )
```

### Linux: Systemd

Source: `src/lurkbot/daemon/systemd.py`

使用 systemd 用户服务管理后台进程。

**配置文件位置**: `~/.config/systemd/user/lurkbot-gateway.service`

**服务名称**: `lurkbot-gateway`

```python
class SystemdService(GatewayService):
    """Linux Systemd 服务实现"""

    @property
    def unit_path(self) -> Path:
        """~/.config/systemd/user/{name}.service"""
        return Path.home() / ".config" / "systemd" / "user" / f"{self._name}.service"

    async def install(self, args: ServiceInstallArgs) -> None:
        """安装 Systemd User Service"""
        unit_content = f"""[Unit]
Description=LurkBot Gateway Server
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart=/usr/local/bin/lurkbot gateway run --port {args.port} --bind {args.bind}
WorkingDirectory={get_lurkbot_home()}
Restart=always
RestartSec=5

[Install]
WantedBy=default.target
"""
        # 写入 unit 文件
        self.unit_path.write_text(unit_content)
        # 重新加载配置并启用服务
        await self._systemctl_exec(["--user", "daemon-reload"])
        await self._systemctl_exec(["--user", "enable", self._name])
        # 启用 linger（即使用户未登录也保持服务运行）
        await self._enable_linger()
```

**Linger 支持**: 启用 `loginctl enable-linger` 确保用户未登录时服务仍然运行。

### Windows: Schtasks

Source: `src/lurkbot/daemon/schtasks.py`

使用 Windows 计划任务管理后台进程。

**任务名称**: `lurkbot-gateway`

```python
class SchtasksService(GatewayService):
    """Windows Schtasks 服务实现"""

    async def install(self, args: ServiceInstallArgs) -> None:
        """安装 Windows 计划任务"""
        xml_content = self._build_task_xml(args)
        # 创建计划任务
        await self._schtasks_exec(
            ["/Create", "/TN", self._name, "/XML", xml_path, "/F"]
        )

    async def start(self) -> None:
        await self._schtasks_exec(["/Run", "/TN", self._name])

    async def stop(self) -> None:
        await self._schtasks_exec(["/End", "/TN", self._name])
```

**任务配置特性**:
- `BootTrigger`: 系统启动时自动运行
- `RestartOnFailure`: 失败后自动重启（间隔 1 分钟，最多 3 次）
- `ExecutionTimeLimit`: 无时间限制 (PT0S)

## Diagnostics

Source: `src/lurkbot/daemon/diagnostics.py`

LurkBot 提供服务状态诊断和常见问题检测。

### Diagnostic Result

Source: `src/lurkbot/daemon/diagnostics.py:19-31`

```python
@dataclass
class DiagnosticResult:
    """诊断结果"""

    level: Literal["ok", "warning", "error"]
    """诊断级别"""

    message: str
    """诊断消息"""

    suggestion: str | None = None
    """修复建议"""
```

### Diagnose Service

Source: `src/lurkbot/daemon/diagnostics.py:33-104`

```python
async def diagnose_service(service: GatewayService) -> list[DiagnosticResult]:
    """诊断服务状态"""
    results: list[DiagnosticResult] = []

    # 1. 检查服务是否已加载
    is_loaded = await service.is_loaded()
    if not is_loaded:
        results.append(DiagnosticResult(
            level="error",
            message="Service is not installed",
            suggestion="Run 'lurkbot daemon install' to install the service",
        ))
        return results

    # 2. 检查运行时状态
    runtime = await service.get_runtime()

    # 3. 检查最后退出状态
    # 4. 检查日志文件
    # 5. 检查端口占用（如果服务正在运行）

    return results
```

### Diagnostic Checks

诊断系统执行以下检查：

| 检查项 | 级别 | 描述 |
|--------|------|------|
| 服务未安装 | error | 服务未安装，需要运行 `lurkbot daemon install` |
| 服务已停止 | warning | 服务已停止，需要运行 `lurkbot daemon start` |
| 状态未知 | warning | 无法确定服务状态 |
| 异常退出 | error | 最后退出状态码非零 |
| 日志文件过大 | warning | 日志文件超过 10MB |
| 错误日志非空 | error | 错误日志包含内容 |
| 端口连接超时 | warning | 服务可能正在启动或无响应 |
| 端口连接拒绝 | error | 服务未监听端口 |

### Format Diagnostic Report

```python
from lurkbot.daemon import diagnose_service, format_diagnostic_report

service = resolve_gateway_service()
results = await diagnose_service(service)
report = format_diagnostic_report(results)
print(report)
```

输出示例：

```
=== Service Diagnostic Report ===

✅ Service is running (PID: 12345)
✅ Port 18789 is accessible
⚠️ Log file is large (15MB)
   💡 Consider rotating logs
```

## Usage Examples

### Basic Usage

```python
from lurkbot.daemon import resolve_gateway_service, ServiceInstallArgs

# 获取平台特定的服务实现
service = resolve_gateway_service()

# 安装服务
args = ServiceInstallArgs(port=18789, bind="loopback")
await service.install(args)

# 启动服务
await service.start()

# 获取运行时状态
runtime = await service.get_runtime()
print(f"Status: {runtime.status}, PID: {runtime.pid}")

# 停止服务
await service.stop()

# 卸载服务
await service.uninstall()
```

### Multi-Instance (Profile)

```python
from lurkbot.daemon import resolve_gateway_service, ServiceInstallArgs

# 创建多个实例
dev_service = resolve_gateway_service(profile="dev")
prod_service = resolve_gateway_service(profile="prod")

# 安装不同端口的实例
await dev_service.install(ServiceInstallArgs(port=18790))
await prod_service.install(ServiceInstallArgs(port=18791))

# 服务标签
# macOS: bot.lurk.dev, bot.lurk.prod
# Linux: lurkbot-gateway-dev, lurkbot-gateway-prod
# Windows: lurkbot-gateway-dev, lurkbot-gateway-prod
```

### With Workspace

```python
from lurkbot.daemon import resolve_gateway_service, ServiceInstallArgs

service = resolve_gateway_service()

# 指定工作区路径
args = ServiceInstallArgs(
    port=18789,
    bind="loopback",
    workspace="/path/to/my/project"
)
await service.install(args)
```

## Troubleshooting

### Service not installed

运行诊断命令：

```bash
lurkbot daemon diagnose
```

如果服务未安装：

```bash
lurkbot daemon install
```

### Service won't start

1. 检查服务是否已加载：

```bash
# macOS
launchctl list | grep bot.lurk

# Linux
systemctl --user status lurkbot-gateway

# Windows
schtasks /Query /TN lurkbot-gateway
```

2. 检查日志文件：

```bash
tail -f ~/.lurkbot/logs/gateway.err.log
```

3. 检查端口占用：

```bash
# macOS/Linux
lsof -i :18789

# Windows
netstat -ano | findstr 18789
```

### Stale PID file

如果 PID 文件存在但进程已终止：

```bash
rm ~/.lurkbot/run/gateway.pid
lurkbot daemon start
```

### Platform-specific issues

**macOS**:
- 检查 plist 文件：`cat ~/Library/LaunchAgents/bot.lurk.gateway.plist`
- 重新加载服务：`launchctl unload ~/Library/LaunchAgents/bot.lurk.gateway.plist && launchctl load ~/Library/LaunchAgents/bot.lurk.gateway.plist`

**Linux**:
- 检查 unit 文件：`cat ~/.config/systemd/user/lurkbot-gateway.service`
- 重新加载配置：`systemctl --user daemon-reload`
- 检查 linger 状态：`loginctl show-user $USER | grep Linger`

**Windows**:
- 检查任务状态：`schtasks /Query /TN lurkbot-gateway /V`
- 查看任务计划程序日志

---

## See Also

- [Gateway](gateway.md) - Gateway architecture
- [Cron Jobs](cron.md) - Scheduled tasks
- [Configuration](../user-guide/configuration/index.md) - Configuration options
