"""
Gateway 配置流程

对标 MoltBot wizard/flows/gateway-config.ts
"""

import secrets
from typing import Any

from ..prompts import (
    WizardConfirmParams,
    WizardPrompter,
    WizardSelectParams,
    WizardTextParams,
    create_select_option,
)
from ..types import (
    DEFAULT_GATEWAY_PORT,
    GatewayAuthChoice,
    GatewayBindMode,
    GatewaySettings,
    QuickstartGatewayDefaults,
    TailscaleMode,
    WizardFlow,
    is_valid_ipv4,
    is_valid_port,
)


def generate_token(length: int = 32) -> str:
    """生成安全令牌"""
    return secrets.token_urlsafe(length)


async def configure_gateway_for_onboarding(
    prompter: WizardPrompter,
    flow: WizardFlow,
    defaults: QuickstartGatewayDefaults | None = None,
) -> GatewaySettings:
    """
    配置 Gateway

    对标 MoltBot configureGatewayForOnboarding()

    Args:
        prompter: 向导提示器
        flow: 向导流程类型 (quickstart/advanced)
        defaults: QuickStart 模式下的默认配置

    Returns:
        GatewaySettings: Gateway 配置设置
    """
    if defaults is None:
        defaults = QuickstartGatewayDefaults()

    settings = GatewaySettings(
        port=defaults.port,
        bind=defaults.bind,
        auth_mode=defaults.auth_mode,
        token=defaults.token,
        password=defaults.password,
        tailscale_mode=defaults.tailscale_mode,
        tailscale_reset_on_exit=defaults.tailscale_reset_on_exit,
    )

    # QuickStart 模式使用默认配置
    if flow == "quickstart":
        # 生成令牌（如果需要）
        if settings.auth_mode == "token" and not settings.token:
            settings.token = generate_token()
        return settings

    # Advanced 模式：交互式配置
    await prompter.note(
        "Let's configure the Gateway server.\n"
        "The Gateway handles API requests and manages bot connections.",
        title="Gateway Configuration",
    )

    # 1. 端口配置
    settings.port = await _configure_port(prompter, defaults.port)

    # 2. 绑定模式配置
    settings.bind, settings.custom_bind_host = await _configure_bind_mode(
        prompter, defaults.bind
    )

    # 3. 认证方式配置
    settings.auth_mode, settings.token, settings.password = await _configure_auth(
        prompter, defaults.auth_mode
    )

    # 4. Tailscale 配置（可选）
    settings.tailscale_mode, settings.tailscale_reset_on_exit = (
        await _configure_tailscale(prompter, defaults.tailscale_mode)
    )

    return settings


async def _configure_port(prompter: WizardPrompter, default_port: int) -> int:
    """配置端口"""

    def validate_port(value: str) -> str | None:
        try:
            port = int(value)
            if not is_valid_port(port):
                return "Port must be between 1 and 65535"
            return None
        except ValueError:
            return "Please enter a valid port number"

    port_str = await prompter.text(
        WizardTextParams(
            message="Gateway port:",
            initial_value=str(default_port),
            placeholder=str(DEFAULT_GATEWAY_PORT),
            validate=validate_port,
        )
    )

    return int(port_str) if port_str else default_port


async def _configure_bind_mode(
    prompter: WizardPrompter,
    default_bind: GatewayBindMode,
) -> tuple[GatewayBindMode, str | None]:
    """配置绑定模式"""
    bind_options = [
        create_select_option(
            "loopback",
            "Loopback only (127.0.0.1)",
            "Most secure - only local connections",
        ),
        create_select_option(
            "lan",
            "LAN (0.0.0.0)",
            "Allow connections from local network",
        ),
        create_select_option(
            "auto",
            "Auto-detect",
            "Automatically choose based on environment",
        ),
        create_select_option(
            "tailnet",
            "Tailscale network",
            "Bind to Tailscale IP only",
        ),
        create_select_option(
            "custom",
            "Custom IP",
            "Specify a custom bind address",
        ),
    ]

    bind_mode: GatewayBindMode = await prompter.select(
        WizardSelectParams(
            message="How should the Gateway bind?",
            options=bind_options,
            initial_value=default_bind,
        )
    )

    custom_host: str | None = None

    if bind_mode == "custom":
        def validate_ip(value: str) -> str | None:
            if not value:
                return "IP address is required"
            if not is_valid_ipv4(value):
                return "Please enter a valid IPv4 address"
            return None

        custom_host = await prompter.text(
            WizardTextParams(
                message="Custom bind IP address:",
                placeholder="192.168.1.100",
                validate=validate_ip,
            )
        )

    return bind_mode, custom_host


async def _configure_auth(
    prompter: WizardPrompter,
    default_auth: GatewayAuthChoice,
) -> tuple[GatewayAuthChoice, str | None, str | None]:
    """配置认证方式"""
    auth_options = [
        create_select_option(
            "token",
            "Token authentication",
            "Generate a secure random token (recommended)",
        ),
        create_select_option(
            "password",
            "Password authentication",
            "Set a custom password",
        ),
    ]

    auth_mode: GatewayAuthChoice = await prompter.select(
        WizardSelectParams(
            message="Authentication method:",
            options=auth_options,
            initial_value=default_auth,
        )
    )

    token: str | None = None
    password: str | None = None

    if auth_mode == "token":
        # 生成令牌
        token = generate_token()
        await prompter.note(
            f"Generated token: {token}\n\n"
            "Save this token securely - you'll need it to connect clients.",
            title="Authentication Token",
        )
    else:
        # 密码输入
        def validate_password(value: str) -> str | None:
            if len(value) < 8:
                return "Password must be at least 8 characters"
            return None

        password = await prompter.text(
            WizardTextParams(
                message="Enter password (min 8 characters):",
                validate=validate_password,
            )
        )

    return auth_mode, token, password


async def _configure_tailscale(
    prompter: WizardPrompter,
    default_mode: TailscaleMode,
) -> tuple[TailscaleMode, bool]:
    """配置 Tailscale"""
    use_tailscale = await prompter.confirm(
        WizardConfirmParams(
            message="Do you want to expose the Gateway via Tailscale?",
            initial_value=default_mode != "off",
        )
    )

    if not use_tailscale:
        return "off", False

    tailscale_options = [
        create_select_option(
            "serve",
            "Tailscale Serve",
            "Expose to your Tailnet only",
        ),
        create_select_option(
            "funnel",
            "Tailscale Funnel",
            "Expose to the public internet via Tailscale",
        ),
    ]

    tailscale_mode: TailscaleMode = await prompter.select(
        WizardSelectParams(
            message="Tailscale exposure mode:",
            options=tailscale_options,
            initial_value="serve" if default_mode == "off" else default_mode,
        )
    )

    reset_on_exit = await prompter.confirm(
        WizardConfirmParams(
            message="Reset Tailscale exposure when Gateway exits?",
            initial_value=False,
        )
    )

    return tailscale_mode, reset_on_exit
