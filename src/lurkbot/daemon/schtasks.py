"""
Windows Schtasks Service - Windows 守护进程实现

对标: MoltBot src/daemon/schtasks.ts

使用 Windows 计划任务实现守护进程管理。
"""

import asyncio
import re
from pathlib import Path
from typing import Literal

from .service import GatewayService, ServiceRuntime, ServiceInstallArgs
from .constants import SCHTASKS_TASK_NAME
from .paths import ensure_directories


class SchtasksService(GatewayService):
    """
    Windows Schtasks 服务实现

    对标: MoltBot SchtasksService

    使用 Windows 计划任务管理后台进程。
    """

    def __init__(self, profile: str | None = None):
        """
        初始化 Schtasks 服务

        Args:
            profile: 可选的 Profile 名称（用于多实例）
        """
        self.profile = profile
        self._name = self._resolve_name(profile)

    def _resolve_name(self, profile: str | None) -> str:
        """
        解析任务名称（支持多实例）

        Args:
            profile: Profile 名称

        Returns:
            str: 任务名称
                - 默认: lurkbot-gateway
                - Profile: lurkbot-gateway-{profile}
        """
        if profile:
            # 去除非法字符
            safe_profile = re.sub(r"[^a-zA-Z0-9-]", "-", profile)
            return f"{SCHTASKS_TASK_NAME}-{safe_profile}"
        return SCHTASKS_TASK_NAME

    @property
    def label(self) -> str:
        """任务名称"""
        return self._name

    async def install(self, args: ServiceInstallArgs) -> None:
        """
        安装 Windows 计划任务

        对标: MoltBot SchtasksService.install()

        Args:
            args: 安装参数

        Raises:
            RuntimeError: 安装失败
        """
        ensure_directories()

        # 构建 XML 配置
        xml_content = self._build_task_xml(args)

        # 保存临时 XML 文件
        import tempfile

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".xml", delete=False, encoding="utf-8"
        ) as f:
            f.write(xml_content)
            xml_path = f.name

        try:
            # 创建计划任务
            await self._schtasks_exec(
                ["/Create", "/TN", self._name, "/XML", xml_path, "/F"]
            )
        finally:
            # 删除临时文件
            Path(xml_path).unlink(missing_ok=True)

    async def uninstall(self) -> None:
        """
        卸载 Windows 计划任务

        对标: MoltBot SchtasksService.uninstall()

        Raises:
            RuntimeError: 卸载失败
        """
        # 删除任务
        try:
            await self._schtasks_exec(["/Delete", "/TN", self._name, "/F"])
        except RuntimeError:
            pass  # 忽略任务不存在的错误

    async def start(self) -> None:
        """
        启动任务

        对标: MoltBot SchtasksService.start()

        Raises:
            RuntimeError: 启动失败
        """
        await self._schtasks_exec(["/Run", "/TN", self._name])

    async def stop(self) -> None:
        """
        停止任务

        对标: MoltBot SchtasksService.stop()

        Raises:
            RuntimeError: 停止失败
        """
        await self._schtasks_exec(["/End", "/TN", self._name])

    async def restart(self) -> None:
        """
        重启任务

        对标: MoltBot SchtasksService.restart()

        Raises:
            RuntimeError: 重启失败
        """
        await self.stop()
        await asyncio.sleep(1)  # 等待任务完全停止
        await self.start()

    async def is_loaded(self) -> bool:
        """
        检查任务是否已加载

        对标: MoltBot SchtasksService.isLoaded()

        Returns:
            True 如果任务已创建
        """
        try:
            await self._schtasks_exec(["/Query", "/TN", self._name], check_returncode=False)
            return True
        except RuntimeError:
            return False

    async def get_runtime(self) -> ServiceRuntime:
        """
        获取运行时状态

        对标: MoltBot SchtasksService.getRuntime()

        Returns:
            ServiceRuntime: 当前运行时状态
        """
        if not await self.is_loaded():
            return ServiceRuntime(status="stopped")

        try:
            # 使用 schtasks /Query 获取状态
            output = await self._schtasks_exec(
                ["/Query", "/TN", self._name, "/FO", "LIST", "/V"]
            )
            return self._parse_schtasks_query(output)
        except Exception:
            return ServiceRuntime(status="unknown")

    def _parse_schtasks_query(self, output: str) -> ServiceRuntime:
        """
        解析 schtasks /Query 输出

        输出格式示例:
        HostName:                             DESKTOP-ABC
        TaskName:                             \\lurkbot-gateway
        ...
        Status:                               Running
        ...
        Last Run Time:                        1/29/2026 10:00:00 AM
        Last Result:                          0

        Args:
            output: schtasks /Query 输出

        Returns:
            ServiceRuntime: 解析后的运行时状态
        """
        lines = output.strip().split("\n")
        props = {}
        for line in lines:
            if ":" in line:
                key, value = line.split(":", 1)
                props[key.strip()] = value.strip()

        # 提取状态
        task_status = props.get("Status", "").lower()
        last_result_str = props.get("Last Result", "0")

        # 映射到统一状态
        if task_status == "running":
            status: Literal["running", "stopped", "unknown"] = "running"
        elif task_status in ["ready", "disabled"]:
            status = "stopped"
        else:
            status = "unknown"

        # 解析最后退出状态
        try:
            last_exit_status = int(last_result_str)
        except ValueError:
            last_exit_status = None

        return ServiceRuntime(
            status=status,
            state=task_status,
            last_exit_status=last_exit_status,
        )

    def _build_task_xml(self, args: ServiceInstallArgs) -> str:
        """
        构建计划任务 XML 配置

        Args:
            args: 安装参数

        Returns:
            str: XML 配置内容
        """
        # 构建命令行参数
        arguments = f"gateway run --port {args.port} --bind {args.bind}"
        if args.profile:
            arguments += f" --profile {args.profile}"

        # 环境变量
        env_vars = ""
        if args.workspace:
            env_vars = f"<EnvironmentVariables><Variable><Name>LURKBOT_WORKSPACE</Name><Value>{args.workspace}</Value></Variable></EnvironmentVariables>"

        xml = f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>LurkBot Gateway Server</Description>
  </RegistrationInfo>
  <Triggers>
    <BootTrigger>
      <Enabled>true</Enabled>
    </BootTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable>
    <IdleSettings>
      <StopOnIdleEnd>false</StopOnIdleEnd>
      <RestartOnIdle>false</RestartOnIdle>
    </IdleSettings>
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <Enabled>true</Enabled>
    <Hidden>false</Hidden>
    <RunOnlyIfIdle>false</RunOnlyIfIdle>
    <DisallowStartOnRemoteAppSession>false</DisallowStartOnRemoteAppSession>
    <UseUnifiedSchedulingEngine>true</UseUnifiedSchedulingEngine>
    <WakeToRun>false</WakeToRun>
    <ExecutionTimeLimit>PT0S</ExecutionTimeLimit>
    <Priority>7</Priority>
    <RestartOnFailure>
      <Interval>PT1M</Interval>
      <Count>3</Count>
    </RestartOnFailure>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>C:\\Program Files\\lurkbot\\lurkbot.exe</Command>
      <Arguments>{arguments}</Arguments>
      {env_vars}
    </Exec>
  </Actions>
</Task>"""
        return xml

    async def _schtasks_exec(
        self, args: list[str], check_returncode: bool = True
    ) -> str:
        """
        执行 schtasks 命令（使用 execFile 模式，防止命令注入）

        Args:
            args: 命令参数列表
            check_returncode: 是否检查返回码

        Returns:
            str: 命令输出

        Raises:
            RuntimeError: 命令执行失败（仅当 check_returncode=True）
        """
        proc = await asyncio.create_subprocess_exec(
            "schtasks",
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await proc.communicate()

        if check_returncode and proc.returncode != 0:
            raise RuntimeError(
                f"schtasks {' '.join(args)} failed: {stderr.decode().strip()}"
            )

        return stdout.decode().strip()


__all__ = ["SchtasksService"]
