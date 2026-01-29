"""
Browser Config - 浏览器配置解析

对标 MoltBot src/browser/config.ts
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from loguru import logger

from .types import BrowserConfig, ServerConfig


# ============================================================================
# Environment Variables
# ============================================================================

ENV_BROWSER_TYPE = "LURKBOT_BROWSER_TYPE"
ENV_BROWSER_HEADLESS = "LURKBOT_BROWSER_HEADLESS"
ENV_BROWSER_SLOW_MO = "LURKBOT_BROWSER_SLOW_MO"
ENV_BROWSER_VIEWPORT_WIDTH = "LURKBOT_BROWSER_VIEWPORT_WIDTH"
ENV_BROWSER_VIEWPORT_HEIGHT = "LURKBOT_BROWSER_VIEWPORT_HEIGHT"
ENV_BROWSER_USER_AGENT = "LURKBOT_BROWSER_USER_AGENT"
ENV_BROWSER_LOCALE = "LURKBOT_BROWSER_LOCALE"
ENV_BROWSER_TIMEZONE = "LURKBOT_BROWSER_TIMEZONE"
ENV_CDP_ENDPOINT = "LURKBOT_CDP_ENDPOINT"
ENV_CDP_PORT = "LURKBOT_CDP_PORT"
ENV_CHROME_PATH = "LURKBOT_CHROME_PATH"
ENV_CHROME_ARGS = "LURKBOT_CHROME_ARGS"
ENV_USER_DATA_DIR = "LURKBOT_USER_DATA_DIR"
ENV_BROWSER_SERVER_HOST = "LURKBOT_BROWSER_SERVER_HOST"
ENV_BROWSER_SERVER_PORT = "LURKBOT_BROWSER_SERVER_PORT"


# ============================================================================
# Default Values
# ============================================================================

DEFAULT_BROWSER_TYPE = "chromium"
DEFAULT_HEADLESS = True
DEFAULT_SLOW_MO = 0
DEFAULT_VIEWPORT_WIDTH = 1280
DEFAULT_VIEWPORT_HEIGHT = 720
DEFAULT_CDP_PORT = 9222
DEFAULT_SERVER_HOST = "127.0.0.1"
DEFAULT_SERVER_PORT = 9333


# ============================================================================
# Config Loading
# ============================================================================

def load_browser_config(config_path: str | Path | None = None) -> BrowserConfig:
    """
    加载浏览器配置

    优先级: 环境变量 > 配置文件 > 默认值

    Args:
        config_path: 可选的配置文件路径

    Returns:
        BrowserConfig 实例
    """
    config = BrowserConfig()

    # 从配置文件加载（如果存在）
    if config_path:
        file_config = _load_config_file(config_path)
        config = _merge_file_config(config, file_config)

    # 从环境变量覆盖
    config = _apply_env_overrides(config)

    logger.debug(
        f"Loaded browser config: type={config.browser_type}, "
        f"headless={config.headless}, viewport={config.viewport_width}x{config.viewport_height}"
    )

    return config


def load_server_config(config_path: str | Path | None = None) -> ServerConfig:
    """
    加载服务器配置

    Args:
        config_path: 可选的配置文件路径

    Returns:
        ServerConfig 实例
    """
    config = ServerConfig()

    # 从配置文件加载
    if config_path:
        file_config = _load_config_file(config_path)
        if "server" in file_config:
            server_config = file_config["server"]
            if "host" in server_config:
                config.host = server_config["host"]
            if "port" in server_config:
                config.port = int(server_config["port"])
            if "debug" in server_config:
                config.debug = bool(server_config["debug"])
            if "corsOrigins" in server_config:
                config.cors_origins = server_config["corsOrigins"]
            if "maxConcurrentSessions" in server_config:
                config.max_concurrent_sessions = int(server_config["maxConcurrentSessions"])

    # 环境变量覆盖
    if os.getenv(ENV_BROWSER_SERVER_HOST):
        config.host = os.getenv(ENV_BROWSER_SERVER_HOST)
    if os.getenv(ENV_BROWSER_SERVER_PORT):
        config.port = int(os.getenv(ENV_BROWSER_SERVER_PORT))

    logger.debug(f"Loaded server config: {config.host}:{config.port}")

    return config


def _load_config_file(config_path: str | Path) -> dict[str, Any]:
    """加载配置文件"""
    path = Path(config_path)

    if not path.exists():
        logger.warning(f"Config file not found: {path}")
        return {}

    try:
        with open(path) as f:
            if path.suffix == ".json":
                return json.load(f)
            else:
                # 支持其他格式可以在这里扩展
                logger.warning(f"Unsupported config format: {path.suffix}")
                return {}
    except Exception as e:
        logger.error(f"Failed to load config file: {e}")
        return {}


def _merge_file_config(config: BrowserConfig, file_config: dict[str, Any]) -> BrowserConfig:
    """合并文件配置"""
    browser_config = file_config.get("browser", {})

    if "type" in browser_config:
        browser_type = browser_config["type"]
        if browser_type in ("chromium", "firefox", "webkit"):
            config.browser_type = browser_type

    if "headless" in browser_config:
        config.headless = bool(browser_config["headless"])

    if "slowMo" in browser_config:
        config.slow_mo = float(browser_config["slowMo"])

    if "viewport" in browser_config:
        viewport = browser_config["viewport"]
        if "width" in viewport:
            config.viewport_width = int(viewport["width"])
        if "height" in viewport:
            config.viewport_height = int(viewport["height"])

    if "deviceScaleFactor" in browser_config:
        config.device_scale_factor = float(browser_config["deviceScaleFactor"])

    if "userAgent" in browser_config:
        config.user_agent = browser_config["userAgent"]

    if "locale" in browser_config:
        config.locale = browser_config["locale"]

    if "timezone" in browser_config:
        config.timezone = browser_config["timezone"]

    if "geolocation" in browser_config:
        config.geolocation = browser_config["geolocation"]

    if "permissions" in browser_config:
        config.permissions = browser_config["permissions"]

    if "extraHttpHeaders" in browser_config:
        config.extra_http_headers = browser_config["extraHttpHeaders"]

    # CDP 配置
    cdp_config = file_config.get("cdp", {})
    if "endpoint" in cdp_config:
        config.cdp_endpoint = cdp_config["endpoint"]
    if "port" in cdp_config:
        config.cdp_port = int(cdp_config["port"])

    # Chrome 配置
    chrome_config = file_config.get("chrome", {})
    if "path" in chrome_config:
        config.chrome_path = chrome_config["path"]
    if "args" in chrome_config:
        config.chrome_args = chrome_config["args"]
    if "userDataDir" in chrome_config:
        config.user_data_dir = chrome_config["userDataDir"]

    # 扩展配置
    if "extensions" in file_config:
        config.extensions = file_config["extensions"]

    # 超时配置
    timeout_config = file_config.get("timeout", {})
    if "navigation" in timeout_config:
        config.navigation_timeout = float(timeout_config["navigation"])
    if "default" in timeout_config:
        config.default_timeout = float(timeout_config["default"])

    return config


def _apply_env_overrides(config: BrowserConfig) -> BrowserConfig:
    """应用环境变量覆盖"""

    # 浏览器类型
    env_type = os.getenv(ENV_BROWSER_TYPE)
    if env_type and env_type in ("chromium", "firefox", "webkit"):
        config.browser_type = env_type

    # Headless 模式
    env_headless = os.getenv(ENV_BROWSER_HEADLESS)
    if env_headless is not None:
        config.headless = env_headless.lower() in ("true", "1", "yes")

    # Slow motion
    env_slow_mo = os.getenv(ENV_BROWSER_SLOW_MO)
    if env_slow_mo:
        try:
            config.slow_mo = float(env_slow_mo)
        except ValueError:
            pass

    # Viewport
    env_width = os.getenv(ENV_BROWSER_VIEWPORT_WIDTH)
    if env_width:
        try:
            config.viewport_width = int(env_width)
        except ValueError:
            pass

    env_height = os.getenv(ENV_BROWSER_VIEWPORT_HEIGHT)
    if env_height:
        try:
            config.viewport_height = int(env_height)
        except ValueError:
            pass

    # User agent
    env_user_agent = os.getenv(ENV_BROWSER_USER_AGENT)
    if env_user_agent:
        config.user_agent = env_user_agent

    # Locale
    env_locale = os.getenv(ENV_BROWSER_LOCALE)
    if env_locale:
        config.locale = env_locale

    # Timezone
    env_timezone = os.getenv(ENV_BROWSER_TIMEZONE)
    if env_timezone:
        config.timezone = env_timezone

    # CDP
    env_cdp_endpoint = os.getenv(ENV_CDP_ENDPOINT)
    if env_cdp_endpoint:
        config.cdp_endpoint = env_cdp_endpoint

    env_cdp_port = os.getenv(ENV_CDP_PORT)
    if env_cdp_port:
        try:
            config.cdp_port = int(env_cdp_port)
        except ValueError:
            pass

    # Chrome
    env_chrome_path = os.getenv(ENV_CHROME_PATH)
    if env_chrome_path:
        config.chrome_path = env_chrome_path

    env_chrome_args = os.getenv(ENV_CHROME_ARGS)
    if env_chrome_args:
        config.chrome_args = env_chrome_args.split(",")

    env_user_data_dir = os.getenv(ENV_USER_DATA_DIR)
    if env_user_data_dir:
        config.user_data_dir = env_user_data_dir

    return config


# ============================================================================
# Config Validation
# ============================================================================

def validate_browser_config(config: BrowserConfig) -> list[str]:
    """
    验证浏览器配置

    Returns:
        错误信息列表（空列表表示验证通过）
    """
    errors = []

    # 验证视口大小
    if config.viewport_width < 100:
        errors.append(f"Viewport width too small: {config.viewport_width}")
    if config.viewport_height < 100:
        errors.append(f"Viewport height too small: {config.viewport_height}")
    if config.viewport_width > 4096:
        errors.append(f"Viewport width too large: {config.viewport_width}")
    if config.viewport_height > 4096:
        errors.append(f"Viewport height too large: {config.viewport_height}")

    # 验证设备缩放因子
    if config.device_scale_factor < 0.5:
        errors.append(f"Device scale factor too small: {config.device_scale_factor}")
    if config.device_scale_factor > 4:
        errors.append(f"Device scale factor too large: {config.device_scale_factor}")

    # 验证超时设置
    if config.default_timeout < 0:
        errors.append(f"Invalid default timeout: {config.default_timeout}")
    if config.navigation_timeout < 0:
        errors.append(f"Invalid navigation timeout: {config.navigation_timeout}")

    # 验证 Chrome 路径（如果指定）
    if config.chrome_path:
        chrome_path = Path(config.chrome_path)
        if not chrome_path.exists():
            errors.append(f"Chrome path not found: {config.chrome_path}")

    # 验证用户数据目录（如果指定）
    if config.user_data_dir:
        data_dir = Path(config.user_data_dir)
        if data_dir.exists() and not data_dir.is_dir():
            errors.append(f"User data dir is not a directory: {config.user_data_dir}")

    # 验证地理位置
    if config.geolocation:
        if "latitude" not in config.geolocation or "longitude" not in config.geolocation:
            errors.append("Geolocation must have latitude and longitude")
        else:
            lat = config.geolocation.get("latitude", 0)
            lon = config.geolocation.get("longitude", 0)
            if not (-90 <= lat <= 90):
                errors.append(f"Invalid latitude: {lat}")
            if not (-180 <= lon <= 180):
                errors.append(f"Invalid longitude: {lon}")

    return errors


# ============================================================================
# Chrome Detection
# ============================================================================

def detect_chrome_path() -> str | None:
    """
    检测系统上的 Chrome 可执行文件路径

    Returns:
        Chrome 路径或 None
    """
    import platform
    import shutil

    system = platform.system()

    if system == "Darwin":  # macOS
        paths = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Chromium.app/Contents/MacOS/Chromium",
            "/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary",
        ]
    elif system == "Windows":
        paths = [
            os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
        ]
    else:  # Linux
        paths = [
            "/usr/bin/google-chrome",
            "/usr/bin/google-chrome-stable",
            "/usr/bin/chromium",
            "/usr/bin/chromium-browser",
            "/snap/bin/chromium",
        ]
        # 也尝试通过 which 查找
        which_chrome = shutil.which("google-chrome") or shutil.which("chromium")
        if which_chrome:
            paths.insert(0, which_chrome)

    for path in paths:
        if os.path.exists(path):
            logger.debug(f"Detected Chrome at: {path}")
            return path

    return None


def get_default_user_data_dir() -> str:
    """
    获取默认的用户数据目录

    Returns:
        用户数据目录路径
    """
    import platform

    system = platform.system()

    if system == "Darwin":  # macOS
        base = os.path.expanduser("~/Library/Application Support")
    elif system == "Windows":
        base = os.path.expandvars(r"%LocalAppData%")
    else:  # Linux
        base = os.path.expanduser("~/.config")

    return os.path.join(base, "lurkbot", "browser-data")


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    "load_browser_config",
    "load_server_config",
    "validate_browser_config",
    "detect_chrome_path",
    "get_default_user_data_dir",
    # Environment variable names
    "ENV_BROWSER_TYPE",
    "ENV_BROWSER_HEADLESS",
    "ENV_CDP_ENDPOINT",
    "ENV_CDP_PORT",
    "ENV_CHROME_PATH",
    "ENV_BROWSER_SERVER_HOST",
    "ENV_BROWSER_SERVER_PORT",
]
