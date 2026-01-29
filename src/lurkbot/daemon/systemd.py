"""
Linux Systemd Service - Linux 守护进程实现

对标: MoltBot src/daemon/systemd.ts

使用 systemd 用户服务实现守护进程管理。
"""

import asyncio
import re
from pathlib import Path
from typing import Literal

from .service import GatewayService, ServiceRuntime, ServiceInstallArgs
from .constants import SYSTEMD_SERVICE_NAME
from .paths import get_lurkbot_home, ensure_directories


class SystemdService(GatewayService):
    """
    Linux Systemd 服务实现

    对标: MoltBot SystemdService

    使用 systemd 用户服务管理后台进程。
    配置文件位置: ~/.config/systemd/user/
    """

    def __init__(self, profile: str | None = None):
        """
        初始化 Systemd 服务

        Args:
            profile: 可选的 Profile 名称（用于多实例）
        """
        self.profile = profile
        self._name = self._resolve_name(profile)

    def _resolve_name(self, profile: str | None) -> str:
        """
        解析服务名称（支持多实例）

        Args:
            profile: Profile 名称

        Returns:
            str: 服务名称
                - 默认: lurkbot-gateway
                - Profile: lurkbot-gateway-{profile}
        """
        if profile:
            # 去除非法字符，确保符合 systemd unit name 规范
            safe_profile = re.sub(r"[^a-zA-Z0-9-]", "-", profile)
            return f"{SYSTEMD_SERVICE_NAME}-{safe_profile}"
        return SYSTEMD_SERVICE_NAME

    @property
    def label(self) -> str:
        """服务名称"""
        return self._name

    @property
    def unit_path(self) -> Path:
        """
        Systemd Unit 文件路径

        Returns:
            Path: ~/.config/systemd/user/{name}.service
        """
        return Path.home() / ".config" / "systemd" / "user" / f"{self._name}.service"

    async def install(self, args: ServiceInstallArgs) -> None:
        """
        安装 Systemd User Service

        对标: MoltBot SystemdService.install()

        Args:
            args: 安装参数

        Raises:
            RuntimeError: 安装失败
        """
        ensure_directories()

        # 构建 unit 文件内容
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
KillMode=process
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=default.target
"""

        # 如果指定了 workspace，添加环境变量
        if args.workspace:
            env_line = f"Environment=LURKBOT_WORKSPACE={args.workspace}"
            # 插入到 [Service] 段
            unit_content = unit_content.replace(
                "[Service]\n", f"[Service]\n{env_line}\n"
            )

        # 如果指定了 profile，修改 ExecStart
        if args.profile:
            unit_content = unit_content.replace(
                f"--bind {args.bind}",
                f"--bind {args.bind} --profile {args.profile}",
            )

        # 确保目录存在
        self.unit_path.parent.mkdir(parents=True, exist_ok=True)

        # 写入 unit 文件
        self.unit_path.write_text(unit_content)

        # 重新加载 systemd 配置
        await self._systemctl_exec(["--user", "daemon-reload"])

        # 启用服务（开机自启）
        await self._systemctl_exec(["--user", "enable", self._name])

        # 启用 linger（即使用户未登录也保持服务运行）
        await self._enable_linger()

    async def uninstall(self) -> None:
        """
        卸载 Systemd User Service

        对标: MoltBot SystemdService.uninstall()

        Raises:
            RuntimeError: 卸载失败
        """
        # 停止服务
        try:
            await self.stop()
        except Exception:
            pass  # 忽略停止失败

        # 禁用服务
        try:
            await self._systemctl_exec(["--user", "disable", self._name])
        except Exception:
            pass  # 忽略禁用失败

        # 删除 unit 文件
        self.unit_path.unlink(missing_ok=True)

        # 重新加载配置
        await self._systemctl_exec(["--user", "daemon-reload"])

    async def start(self) -> None:
        """
        启动服务

        对标: MoltBot SystemdService.start()

        Raises:
            RuntimeError: 启动失败
        """
        await self._systemctl_exec(["--user", "start", self._name])

    async def stop(self) -> None:
        """
        停止服务

        对标: MoltBot SystemdService.stop()

        Raises:
            RuntimeError: 停止失败
        """
        await self._systemctl_exec(["--user", "stop", self._name])

    async def restart(self) -> None:
        """
        重启服务

        对标: MoltBot SystemdService.restart()

        Raises:
            RuntimeError: 重启失败
        """
        await self._systemctl_exec(["--user", "restart", self._name])

    async def is_loaded(self) -> bool:
        """
        检查服务是否已加载

        对标: MoltBot SystemdService.isLoaded()

        Returns:
            True 如果服务已安装并加载
        """
        if not self.unit_path.exists():
            return False

        try:
            output = await self._systemctl_exec(
                ["--user", "is-enabled", self._name], check_returncode=False
            )
            # is-enabled 返回 enabled, disabled, masked 等状态
            return output.strip() in ["enabled", "enabled-runtime", "static"]
        except Exception:
            return False

    async def get_runtime(self) -> ServiceRuntime:
        """
        获取运行时状态

        对标: MoltBot SystemdService.getRuntime()

        Returns:
            ServiceRuntime: 当前运行时状态
        """
        if not await self.is_loaded():
            return ServiceRuntime(status="stopped")

        try:
            # 使用 systemctl show 获取详细状态
            output = await self._systemctl_exec(
                ["--user", "show", self._name, "--no-pager"]
            )
            return self._parse_systemctl_show(output)
        except Exception:
            return ServiceRuntime(status="unknown")

    def _parse_systemctl_show(self, output: str) -> ServiceRuntime:
        """
        解析 systemctl show 输出

        输出格式示例:
        ActiveState=active
        SubState=running
        MainPID=12345
        ExecMainStatus=0
        ...

        Args:
            output: systemctl show 输出

        Returns:
            ServiceRuntime: 解析后的运行时状态
        """
        lines = output.strip().split("\n")
        props = {}
        for line in lines:
            if "=" in line:
                key, value = line.split("=", 1)
                props[key] = value

        # 提取状态信息
        active_state = props.get("ActiveState", "unknown")
        sub_state = props.get("SubState", "")
        main_pid_str = props.get("MainPID", "0")
        exec_status_str = props.get("ExecMainStatus", "0")

        # 解析 PID
        try:
            main_pid = int(main_pid_str)
            pid = main_pid if main_pid > 0 else None
        except ValueError:
            pid = None

        # 解析退出状态
        try:
            last_exit_status = int(exec_status_str)
        except ValueError:
            last_exit_status = None

        # 映射到统一状态
        if active_state == "active" and sub_state == "running":
            status: Literal["running", "stopped", "unknown"] = "running"
        elif active_state in ["inactive", "failed"]:
            status = "stopped"
        else:
            status = "unknown"

        return ServiceRuntime(
            status=status,
            state=active_state,
            sub_state=sub_state,
            pid=pid,
            last_exit_status=last_exit_status,
        )

    async def _enable_linger(self) -> None:
        """
        启用 loginctl linger（持久化用户服务）

        即使用户未登录，服务也会运行。

        Raises:
            RuntimeError: 启用失败
        """
        import getpass

        username = getpass.getuser()

        try:
            await self._loginctl_exec(["enable-linger", username])
        except RuntimeError:
            # linger 启用失败不影响服务安装，只是服务可能在用户登出后停止
            pass

    async def _systemctl_exec(
        self, args: list[str], check_returncode: bool = True
    ) -> str:
        """
        执行 systemctl 命令（使用 execFile 模式，防止命令注入）

        Args:
            args: 命令参数列表
            check_returncode: 是否检查返回码

        Returns:
            str: 命令输出

        Raises:
            RuntimeError: 命令执行失败（仅当 check_returncode=True）
        """
        proc = await asyncio.create_subprocess_exec(
            "systemctl",
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await proc.communicate()

        if check_returncode and proc.returncode != 0:
            raise RuntimeError(
                f"systemctl {' '.join(args)} failed: {stderr.decode().strip()}"
            )

        return stdout.decode().strip()

    async def _loginctl_exec(self, args: list[str]) -> str:
        """
        执行 loginctl 命令（使用 execFile 模式，防止命令注入）

        Args:
            args: 命令参数列表

        Returns:
            str: 命令输出

        Raises:
            RuntimeError: 命令执行失败
        """
        proc = await asyncio.create_subprocess_exec(
            "loginctl",
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            raise RuntimeError(
                f"loginctl {' '.join(args)} failed: {stderr.decode().strip()}"
            )

        return stdout.decode().strip()


__all__ = ["SystemdService"]
