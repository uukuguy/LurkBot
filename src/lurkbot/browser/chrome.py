"""
Chrome Manager - Chrome 浏览器启动和管理

对标 MoltBot src/browser/chrome.ts
"""

from __future__ import annotations

import asyncio
import os
import platform
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from loguru import logger

from .config import detect_chrome_path, get_default_user_data_dir
from .types import BrowserConfig, BrowserError


# ============================================================================
# Chrome Launch Options
# ============================================================================

@dataclass
class ChromeLaunchOptions:
    """Chrome 启动选项"""
    headless: bool = True
    debug_port: int = 9222
    user_data_dir: str | None = None
    disable_gpu: bool = True
    no_sandbox: bool = False
    disable_dev_shm_usage: bool = True
    disable_extensions: bool = False
    disable_background_networking: bool = True
    disable_sync: bool = True
    disable_translate: bool = True
    disable_features: list[str] = field(default_factory=list)
    enable_features: list[str] = field(default_factory=list)
    window_size: tuple[int, int] | None = None
    start_maximized: bool = False
    proxy_server: str | None = None
    extra_args: list[str] = field(default_factory=list)


# ============================================================================
# Chrome Process Manager
# ============================================================================

class ChromeManager:
    """
    Chrome 进程管理器

    负责启动、监控和关闭 Chrome 进程。
    支持通过 CDP 端口连接。
    """

    def __init__(
        self,
        chrome_path: str | None = None,
        config: BrowserConfig | None = None,
    ):
        """
        初始化 Chrome 管理器

        Args:
            chrome_path: Chrome 可执行文件路径
            config: 浏览器配置
        """
        self._chrome_path = chrome_path or detect_chrome_path()
        self._config = config or BrowserConfig()
        self._process: subprocess.Popen | None = None
        self._temp_dir: str | None = None
        self._debug_port: int = self._config.cdp_port
        self._ws_endpoint: str | None = None

    @property
    def is_running(self) -> bool:
        """检查 Chrome 是否正在运行"""
        return self._process is not None and self._process.poll() is None

    @property
    def debug_port(self) -> int:
        """获取调试端口"""
        return self._debug_port

    @property
    def ws_endpoint(self) -> str | None:
        """获取 WebSocket 端点"""
        return self._ws_endpoint

    async def launch(self, options: ChromeLaunchOptions | None = None) -> str:
        """
        启动 Chrome

        Args:
            options: 启动选项

        Returns:
            WebSocket 端点 URL

        Raises:
            BrowserError: 如果启动失败
        """
        if self.is_running:
            logger.warning("Chrome is already running")
            return self._ws_endpoint or f"ws://127.0.0.1:{self._debug_port}"

        if not self._chrome_path:
            raise BrowserError("Chrome executable not found", "CHROME_NOT_FOUND")

        opts = options or ChromeLaunchOptions()
        opts.debug_port = self._debug_port

        # 准备用户数据目录
        user_data_dir = self._prepare_user_data_dir(opts)

        # 构建启动参数
        args = self._build_launch_args(opts, user_data_dir)

        logger.info(f"Launching Chrome: {self._chrome_path}")
        logger.debug(f"Chrome args: {' '.join(args)}")

        try:
            # 启动进程
            self._process = subprocess.Popen(
                [self._chrome_path] + args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=self._get_chrome_env(),
            )

            # 等待 Chrome 启动并获取 WebSocket 端点
            self._ws_endpoint = await self._wait_for_ws_endpoint(opts.debug_port)

            logger.info(f"Chrome started, CDP endpoint: {self._ws_endpoint}")

            return self._ws_endpoint

        except Exception as e:
            logger.error(f"Failed to launch Chrome: {e}")
            await self.close()
            raise BrowserError(f"Failed to launch Chrome: {e}", "LAUNCH_FAILED")

    async def close(self) -> None:
        """关闭 Chrome"""
        if self._process:
            logger.info("Closing Chrome...")

            try:
                # 先尝试优雅关闭
                self._process.terminate()

                # 等待进程结束
                try:
                    await asyncio.wait_for(
                        asyncio.get_event_loop().run_in_executor(
                            None, self._process.wait
                        ),
                        timeout=5.0,
                    )
                except asyncio.TimeoutError:
                    # 强制关闭
                    logger.warning("Chrome did not terminate gracefully, killing...")
                    self._process.kill()
                    self._process.wait()

            except Exception as e:
                logger.error(f"Error closing Chrome: {e}")

            finally:
                self._process = None
                self._ws_endpoint = None

        # 清理临时目录
        if self._temp_dir and os.path.exists(self._temp_dir):
            try:
                shutil.rmtree(self._temp_dir)
                self._temp_dir = None
            except Exception as e:
                logger.warning(f"Failed to clean up temp dir: {e}")

    def _prepare_user_data_dir(self, options: ChromeLaunchOptions) -> str:
        """准备用户数据目录"""
        if options.user_data_dir:
            user_data_dir = options.user_data_dir
        elif self._config.user_data_dir:
            user_data_dir = self._config.user_data_dir
        else:
            # 创建临时目录
            self._temp_dir = tempfile.mkdtemp(prefix="lurkbot-chrome-")
            user_data_dir = self._temp_dir

        # 确保目录存在
        Path(user_data_dir).mkdir(parents=True, exist_ok=True)

        return user_data_dir

    def _build_launch_args(
        self,
        options: ChromeLaunchOptions,
        user_data_dir: str,
    ) -> list[str]:
        """构建启动参数"""
        args = [
            f"--remote-debugging-port={options.debug_port}",
            f"--user-data-dir={user_data_dir}",
        ]

        # Headless 模式
        if options.headless:
            # 使用新版 headless 模式
            args.append("--headless=new")

        # GPU 设置
        if options.disable_gpu:
            args.append("--disable-gpu")

        # 沙箱设置
        if options.no_sandbox:
            args.append("--no-sandbox")

        # /dev/shm 设置（Docker 环境常需要）
        if options.disable_dev_shm_usage:
            args.append("--disable-dev-shm-usage")

        # 扩展设置
        if options.disable_extensions:
            args.append("--disable-extensions")

        # 网络设置
        if options.disable_background_networking:
            args.append("--disable-background-networking")

        if options.disable_sync:
            args.append("--disable-sync")

        if options.disable_translate:
            args.append("--disable-translate")

        # 特性开关
        if options.disable_features:
            args.append(f"--disable-features={','.join(options.disable_features)}")

        if options.enable_features:
            args.append(f"--enable-features={','.join(options.enable_features)}")

        # 窗口大小
        if options.window_size:
            args.append(f"--window-size={options.window_size[0]},{options.window_size[1]}")
        elif self._config.viewport_width and self._config.viewport_height:
            args.append(
                f"--window-size={self._config.viewport_width},{self._config.viewport_height}"
            )

        if options.start_maximized:
            args.append("--start-maximized")

        # 代理设置
        if options.proxy_server:
            args.append(f"--proxy-server={options.proxy_server}")

        # 默认禁用的功能（提高稳定性）
        default_disabled = [
            "--disable-background-timer-throttling",
            "--disable-backgrounding-occluded-windows",
            "--disable-renderer-backgrounding",
            "--disable-hang-monitor",
            "--disable-ipc-flooding-protection",
            "--disable-popup-blocking",
            "--disable-prompt-on-repost",
            "--disable-default-apps",
            "--disable-component-extensions-with-background-pages",
            "--no-first-run",
            "--no-default-browser-check",
            "--metrics-recording-only",
        ]
        args.extend(default_disabled)

        # 额外参数
        args.extend(options.extra_args)

        # 从配置添加参数
        args.extend(self._config.chrome_args)

        return args

    def _get_chrome_env(self) -> dict[str, str]:
        """获取 Chrome 环境变量"""
        env = os.environ.copy()

        # 禁用某些干扰性功能
        env["CHROME_HEADLESS"] = "1"

        return env

    async def _wait_for_ws_endpoint(
        self,
        port: int,
        timeout: float = 30.0,
    ) -> str:
        """
        等待 WebSocket 端点可用

        Args:
            port: 调试端口
            timeout: 超时时间（秒）

        Returns:
            WebSocket 端点 URL

        Raises:
            BrowserError: 如果超时
        """
        import aiohttp

        url = f"http://127.0.0.1:{port}/json/version"
        start_time = asyncio.get_event_loop().time()

        while True:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=2)) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            ws_url = data.get("webSocketDebuggerUrl")
                            if ws_url:
                                return ws_url
            except Exception:
                pass

            # 检查超时
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > timeout:
                raise BrowserError(
                    f"Timeout waiting for Chrome to start (port {port})",
                    "TIMEOUT",
                )

            # 检查进程是否还在运行
            if self._process and self._process.poll() is not None:
                stderr = self._process.stderr.read().decode() if self._process.stderr else ""
                raise BrowserError(
                    f"Chrome process exited unexpectedly: {stderr}",
                    "PROCESS_EXITED",
                )

            await asyncio.sleep(0.1)


# ============================================================================
# Chrome Version Detection
# ============================================================================

async def get_chrome_version(chrome_path: str | None = None) -> str | None:
    """
    获取 Chrome 版本

    Args:
        chrome_path: Chrome 可执行文件路径

    Returns:
        版本字符串或 None
    """
    path = chrome_path or detect_chrome_path()
    if not path:
        return None

    try:
        result = subprocess.run(
            [path, "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            # 输出格式: "Google Chrome 120.0.6099.109"
            output = result.stdout.strip()
            parts = output.split()
            if parts:
                return parts[-1]  # 返回版本号部分
    except Exception as e:
        logger.debug(f"Failed to get Chrome version: {e}")

    return None


def is_chrome_installed() -> bool:
    """检查 Chrome 是否已安装"""
    return detect_chrome_path() is not None


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    "ChromeLaunchOptions",
    "ChromeManager",
    "get_chrome_version",
    "is_chrome_installed",
]
