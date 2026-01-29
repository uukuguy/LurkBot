"""
macOS Launchd Service - macOS 守护进程实现

对标: MoltBot src/daemon/launchd.ts

使用 launchd 和 LaunchAgent 实现守护进程管理。
"""

import asyncio
import plistlib
import re
from pathlib import Path
from typing import Literal

from .service import GatewayService, ServiceRuntime, ServiceInstallArgs
from .constants import GATEWAY_LAUNCH_AGENT_LABEL
from .paths import get_logs_dir, ensure_directories


class LaunchdService(GatewayService):
    """
    macOS Launchd 服务实现

    对标: MoltBot LaunchdService

    使用 launchd 和 LaunchAgent 管理后台服务。
    配置文件位置: ~/Library/LaunchAgents/
    """

    def __init__(self, profile: str | None = None):
        """
        初始化 Launchd 服务

        Args:
            profile: 可选的 Profile 名称（用于多实例）
        """
        self.profile = profile
        self._label = self._resolve_label(profile)

    def _resolve_label(self, profile: str | None) -> str:
        """
        解析服务标签（支持多实例）

        Args:
            profile: Profile 名称

        Returns:
            str: 服务标签
                - 默认: bot.lurk.gateway
                - Profile: bot.lurk.{profile}
        """
        if profile:
            # 去除非法字符，确保符合 reverse domain notation
            safe_profile = re.sub(r"[^a-zA-Z0-9-]", "-", profile)
            return f"bot.lurk.{safe_profile}"
        return GATEWAY_LAUNCH_AGENT_LABEL

    @property
    def label(self) -> str:
        """服务标签"""
        return self._label

    @property
    def plist_path(self) -> Path:
        """
        plist 配置文件路径

        Returns:
            Path: ~/Library/LaunchAgents/{label}.plist
        """
        return Path.home() / "Library" / "LaunchAgents" / f"{self._label}.plist"

    async def install(self, args: ServiceInstallArgs) -> None:
        """
        安装 LaunchAgent

        对标: MoltBot LaunchdService.install()

        Args:
            args: 安装参数

        Raises:
            RuntimeError: 安装失败
        """
        ensure_directories()

        # 构建 plist 配置
        plist = {
            "Label": self._label,
            "RunAtLoad": True,
            "KeepAlive": True,
            "ProgramArguments": [
                # TODO: 应该使用实际的 lurkbot 可执行文件路径
                "/usr/local/bin/lurkbot",
                "gateway",
                "run",
                "--port",
                str(args.port),
                "--bind",
                args.bind,
            ],
            "StandardOutPath": str(get_logs_dir() / "gateway.log"),
            "StandardErrorPath": str(get_logs_dir() / "gateway.err.log"),
        }

        # 如果指定了 workspace，添加环境变量
        if args.workspace:
            plist["EnvironmentVariables"] = {"LURKBOT_WORKSPACE": args.workspace}

        # 如果指定了 profile，添加参数
        if args.profile:
            plist["ProgramArguments"].extend(["--profile", args.profile])

        # 确保 LaunchAgents 目录存在
        self.plist_path.parent.mkdir(parents=True, exist_ok=True)

        # 写入 plist 文件
        with open(self.plist_path, "wb") as f:
            plistlib.dump(plist, f)

        # 加载服务
        await self._launchctl_exec(["load", str(self.plist_path)])

    async def uninstall(self) -> None:
        """
        卸载 LaunchAgent

        对标: MoltBot LaunchdService.uninstall()

        Raises:
            RuntimeError: 卸载失败
        """
        # 卸载服务
        if self.plist_path.exists():
            await self._launchctl_exec(["unload", str(self.plist_path)])
            self.plist_path.unlink(missing_ok=True)

    async def start(self) -> None:
        """
        启动服务

        对标: MoltBot LaunchdService.start()

        Raises:
            RuntimeError: 启动失败
        """
        # launchd 使用 kickstart 命令启动服务
        await self._launchctl_exec(
            ["kickstart", f"gui/{self._get_uid()}/{self._label}"]
        )

    async def stop(self) -> None:
        """
        停止服务

        对标: MoltBot LaunchdService.stop()

        Raises:
            RuntimeError: 停止失败
        """
        # launchd 使用 kill 命令停止服务
        await self._launchctl_exec(["kill", "TERM", f"gui/{self._get_uid()}/{self._label}"])

    async def restart(self) -> None:
        """
        重启服务

        对标: MoltBot LaunchdService.restart()

        Raises:
            RuntimeError: 重启失败
        """
        await self.stop()
        await asyncio.sleep(1)  # 等待服务完全停止
        await self.start()

    async def is_loaded(self) -> bool:
        """
        检查服务是否已加载

        对标: MoltBot LaunchdService.isLoaded()

        Returns:
            True 如果服务已安装并加载
        """
        return self.plist_path.exists()

    async def get_runtime(self) -> ServiceRuntime:
        """
        获取运行时状态

        对标: MoltBot LaunchdService.getRuntime()

        Returns:
            ServiceRuntime: 当前运行时状态
        """
        if not await self.is_loaded():
            return ServiceRuntime(status="stopped")

        # 使用 launchctl list 查询状态
        try:
            result = await self._launchctl_exec(["list", self._label])
            return self._parse_launchctl_list(result)
        except Exception:
            return ServiceRuntime(status="unknown")

    def _parse_launchctl_list(self, output: str) -> ServiceRuntime:
        """
        解析 launchctl list 输出

        输出格式示例:
        {
            "Label" = "bot.lurk.gateway";
            "LimitLoadToSessionType" = "Aqua";
            "OnDemand" = false;
            "LastExitStatus" = 0;
            "PID" = 12345;
            "Program" = "/usr/local/bin/lurkbot";
            ...
        }

        Args:
            output: launchctl list 输出

        Returns:
            ServiceRuntime: 解析后的运行时状态
        """
        # 提取 PID
        pid_match = re.search(r'"PID"\s*=\s*(\d+)', output)
        pid = int(pid_match.group(1)) if pid_match else None

        # 提取 LastExitStatus
        exit_status_match = re.search(r'"LastExitStatus"\s*=\s*(-?\d+)', output)
        last_exit_status = (
            int(exit_status_match.group(1)) if exit_status_match else None
        )

        # 判断运行状态
        if pid and pid > 0:
            status: Literal["running", "stopped", "unknown"] = "running"
        else:
            status = "stopped"

        return ServiceRuntime(
            status=status,
            pid=pid,
            last_exit_status=last_exit_status,
        )

    def _get_uid(self) -> int:
        """
        获取当前用户 UID

        Returns:
            int: 用户 UID
        """
        import os

        return os.getuid()

    async def _launchctl_exec(self, args: list[str]) -> str:
        """
        执行 launchctl 命令（使用 execFile 模式，防止命令注入）

        Args:
            args: 命令参数列表

        Returns:
            str: 命令输出

        Raises:
            RuntimeError: 命令执行失败
        """
        proc = await asyncio.create_subprocess_exec(
            "launchctl",
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            raise RuntimeError(
                f"launchctl {' '.join(args)} failed: {stderr.decode().strip()}"
            )

        return stdout.decode().strip()


__all__ = ["LaunchdService"]
