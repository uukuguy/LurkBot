"""Usage Tracker

使用量跟踪核心逻辑

对标 MoltBot:
- src/infra/provider-usage.load.ts
- src/infra/provider-usage.shared.ts
"""

import asyncio
from datetime import datetime
from typing import Any

import httpx

from .types import (
    PROVIDER_LABELS,
    ProviderUsageSnapshot,
    UsageProviderId,
    UsageSummary,
    UsageWindow,
)


# ============================================================================
# Constants (常量)
# ============================================================================

DEFAULT_TIMEOUT_MS = 5000  # 默认超时时间 (毫秒)

# 忽略的错误消息 (不显示给用户)
IGNORED_ERRORS = {
    "No credentials",
    "No token",
    "No API key",
    "Not logged in",
    "No auth",
}


# ============================================================================
# HTTP Helper (HTTP 辅助函数)
# ============================================================================

async def fetch_json_with_timeout(
    url: str,
    headers: dict[str, str] | None = None,
    timeout_ms: int = DEFAULT_TIMEOUT_MS,
) -> tuple[httpx.Response | None, str | None]:
    """获取 JSON 数据 (带超时)

    对标: fetchJson() in provider-usage.fetch.shared.ts

    Args:
        url: 请求 URL
        headers: 请求头
        timeout_ms: 超时时间 (毫秒)

    Returns:
        (响应对象, 错误消息) 元组
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers=headers or {},
                timeout=timeout_ms / 1000,  # 转换为秒
            )
            return response, None
    except httpx.TimeoutException:
        return None, "Request timeout"
    except httpx.HTTPError as e:
        return None, f"HTTP error: {str(e)}"
    except Exception as e:
        return None, f"Error: {str(e)}"


def create_error_snapshot(
    provider: UsageProviderId,
    error: str,
) -> ProviderUsageSnapshot:
    """创建错误快照

    Args:
        provider: 提供商 ID
        error: 错误消息

    Returns:
        带错误信息的提供商使用量快照
    """
    # 如果错误在忽略列表中，返回空快照
    if error in IGNORED_ERRORS:
        return ProviderUsageSnapshot(
            provider=provider,
            display_name=PROVIDER_LABELS.get(provider, provider),
            windows=[],
        )

    return ProviderUsageSnapshot(
        provider=provider,
        display_name=PROVIDER_LABELS.get(provider, provider),
        windows=[],
        error=error,
    )


# ============================================================================
# Usage Fetching (使用量获取)
# ============================================================================

async def fetch_anthropic_usage(
    api_key: str | None = None,
    timeout_ms: int = DEFAULT_TIMEOUT_MS,
) -> ProviderUsageSnapshot:
    """获取 Anthropic (Claude) 使用量

    对标: fetchAnthropicUsage() in provider-usage.fetch.claude.ts

    Args:
        api_key: Anthropic API Key 或 OAuth token
        timeout_ms: 超时时间 (毫秒)

    Returns:
        Anthropic 使用量快照
    """
    if not api_key:
        return create_error_snapshot("anthropic", "No API key")

    # OAuth endpoint (需要 oauth-2025-04-20 beta header)
    url = "https://api.anthropic.com/api/oauth/usage"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "anthropic-beta": "oauth-2025-04-20",
    }

    response, error = await fetch_json_with_timeout(url, headers, timeout_ms)

    if error:
        return create_error_snapshot("anthropic", error)

    if response is None or response.status_code != 200:
        status = response.status_code if response else "unknown"
        return create_error_snapshot("anthropic", f"HTTP {status}")

    try:
        data = response.json()
        windows = []

        # 5 小时窗口
        if "five_hour" in data:
            five_hour = data["five_hour"]
            windows.append(UsageWindow(
                label="5h",
                used_percent=five_hour.get("utilization", 0),
                reset_at=five_hour.get("reset_at"),
            ))

        # 7 天窗口
        if "seven_day" in data:
            seven_day = data["seven_day"]
            windows.append(UsageWindow(
                label="Week",
                used_percent=seven_day.get("utilization", 0),
                reset_at=seven_day.get("reset_at"),
            ))

        # 模型特定窗口 (Sonnet, Opus 等)
        if "models" in data:
            for model_name, model_data in data["models"].items():
                windows.append(UsageWindow(
                    label=model_name.capitalize(),
                    used_percent=model_data.get("utilization", 0),
                    reset_at=model_data.get("reset_at"),
                ))

        # 获取套餐信息
        plan = data.get("plan") or data.get("plan_name")

        return ProviderUsageSnapshot(
            provider="anthropic",
            display_name="Claude",
            windows=windows,
            plan=plan,
        )

    except Exception as e:
        return create_error_snapshot("anthropic", f"Parse error: {str(e)}")


async def fetch_openai_usage(
    api_key: str | None = None,
    timeout_ms: int = DEFAULT_TIMEOUT_MS,
) -> ProviderUsageSnapshot:
    """获取 OpenAI 使用量

    注意: OpenAI 不提供公开的使用量 API

    Args:
        api_key: OpenAI API Key
        timeout_ms: 超时时间 (毫秒)

    Returns:
        OpenAI 使用量快照
    """
    # OpenAI 不提供公开的使用量 API
    return create_error_snapshot("openai-codex", "API not available")


async def fetch_google_usage(
    api_key: str | None = None,
    timeout_ms: int = DEFAULT_TIMEOUT_MS,
) -> ProviderUsageSnapshot:
    """获取 Google Gemini 使用量

    注意: Google 不提供公开的使用量 API

    Args:
        api_key: Google API Key
        timeout_ms: 超时时间 (毫秒)

    Returns:
        Google 使用量快照
    """
    # Google 不提供公开的使用量 API
    return create_error_snapshot("google-gemini-cli", "API not available")


# ============================================================================
# Main Entry Point (主入口)
# ============================================================================

async def load_provider_usage_summary(
    providers: list[UsageProviderId] | None = None,
    credentials: dict[str, str] | None = None,
    timeout_ms: int = DEFAULT_TIMEOUT_MS,
) -> UsageSummary:
    """加载提供商使用量汇总

    对标: loadProviderUsageSummary() in provider-usage.load.ts

    Args:
        providers: 要查询的提供商列表 (默认查询所有)
        credentials: 提供商凭据映射 {provider: api_key}
        timeout_ms: 超时时间 (毫秒)

    Returns:
        使用量汇总
    """
    if providers is None:
        providers = ["anthropic", "openai-codex", "google-gemini-cli"]

    if credentials is None:
        credentials = {}

    # 并行获取所有提供商的使用量
    tasks = []
    for provider in providers:
        api_key = credentials.get(provider)

        if provider == "anthropic":
            tasks.append(fetch_anthropic_usage(api_key, timeout_ms))
        elif provider == "openai-codex":
            tasks.append(fetch_openai_usage(api_key, timeout_ms))
        elif provider == "google-gemini-cli":
            tasks.append(fetch_google_usage(api_key, timeout_ms))
        else:
            # 不支持的提供商
            tasks.append(asyncio.sleep(0, result=create_error_snapshot(
                provider,  # type: ignore
                "Provider not supported"
            )))

    # 等待所有任务完成
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # 过滤结果
    snapshots = []
    for result in results:
        if isinstance(result, ProviderUsageSnapshot):
            # 过滤掉空快照 (没有窗口且没有错误)
            if result.windows or result.error:
                snapshots.append(result)
        elif isinstance(result, Exception):
            # 处理异常
            pass  # 已经在 fetch 函数中处理了

    return UsageSummary(
        updated_at=int(datetime.now().timestamp() * 1000),
        providers=snapshots,
    )


# ============================================================================
# Utility Functions (工具函数)
# ============================================================================

def get_credentials_from_env() -> dict[str, str]:
    """从环境变量获取凭据

    Returns:
        提供商凭据映射
    """
    import os

    credentials = {}

    # Anthropic
    if anthropic_key := os.getenv("ANTHROPIC_API_KEY"):
        credentials["anthropic"] = anthropic_key

    # OpenAI
    if openai_key := os.getenv("OPENAI_API_KEY"):
        credentials["openai-codex"] = openai_key

    # Google
    if google_key := os.getenv("GOOGLE_API_KEY"):
        credentials["google-gemini-cli"] = google_key

    return credentials
