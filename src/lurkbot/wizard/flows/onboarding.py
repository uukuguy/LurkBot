"""
Onboarding 配置向导主流程

对标 MoltBot wizard/flows/onboarding.ts
"""

from typing import Any

from ..prompts import (
    WizardConfirmParams,
    WizardPrompter,
    WizardSelectParams,
    WizardTextParams,
    create_select_option,
)
from ..types import (
    DEFAULT_WORKSPACE,
    SECURITY_WARNING,
    GatewaySettings,
    OnboardMode,
    OnboardOptions,
    QuickstartGatewayDefaults,
    ResetScope,
    WizardFlow,
)
from .gateway_config import configure_gateway_for_onboarding


async def run_onboarding_wizard(
    prompter: WizardPrompter,
    options: OnboardOptions | None = None,
) -> dict[str, Any]:
    """
    运行 Onboarding 配置向导

    对标 MoltBot runOnboardingWizard()

    Args:
        prompter: 向导提示器
        options: 预设选项

    Returns:
        配置结果字典
    """
    if options is None:
        options = OnboardOptions()

    result: dict[str, Any] = {
        "mode": None,
        "flow": None,
        "workspace": None,
        "gateway": None,
        "accepted_risk": False,
        "skip_channels": False,
        "skip_providers": False,
        "skip_skills": False,
    }

    # 1. 显示欢迎信息
    await prompter.intro("🤖 LurkBot Setup Wizard")

    # 2. 安全警告
    if not options.accept_risk:
        await prompter.note(SECURITY_WARNING, title="⚠️ Security Warning")

        accepted = await prompter.confirm(
            WizardConfirmParams(
                message="I understand the risks and want to continue",
                initial_value=False,
            )
        )

        if not accepted:
            await prompter.outro("Setup cancelled. Stay safe! 👋")
            return result

        result["accepted_risk"] = True
    else:
        result["accepted_risk"] = True

    # 3. 选择模式
    mode = options.mode
    if not mode:
        mode = await _select_mode(prompter)
    result["mode"] = mode

    # 4. 选择流程类型
    flow = options.flow
    if not flow:
        flow = await _select_flow(prompter)
    result["flow"] = flow

    # 5. 配置工作区
    workspace = options.workspace
    if not workspace:
        workspace = await _configure_workspace(prompter, flow)
    result["workspace"] = workspace

    # 6. 配置 Gateway（仅 local 模式）
    if mode == "local":
        gateway_defaults = QuickstartGatewayDefaults()
        gateway_settings = await configure_gateway_for_onboarding(
            prompter, flow, gateway_defaults
        )
        result["gateway"] = gateway_settings

    # 7. 配置跳过选项（仅 advanced 模式）
    if flow == "advanced":
        result["skip_channels"] = await prompter.confirm(
            WizardConfirmParams(
                message="Skip channel configuration for now?",
                initial_value=False,
            )
        )

        result["skip_providers"] = await prompter.confirm(
            WizardConfirmParams(
                message="Skip provider configuration for now?",
                initial_value=False,
            )
        )

        result["skip_skills"] = await prompter.confirm(
            WizardConfirmParams(
                message="Skip skill configuration for now?",
                initial_value=False,
            )
        )

    # 8. 显示完成信息
    await _show_completion(prompter, result)

    return result


async def _select_mode(prompter: WizardPrompter) -> OnboardMode:
    """选择运行模式"""
    mode_options = [
        create_select_option(
            "local",
            "Local mode",
            "Run Gateway and bots on this machine",
        ),
        create_select_option(
            "remote",
            "Remote mode",
            "Connect to an existing Gateway server",
        ),
    ]

    mode: OnboardMode = await prompter.select(
        WizardSelectParams(
            message="How do you want to run LurkBot?",
            options=mode_options,
            initial_value="local",
        )
    )

    return mode


async def _select_flow(prompter: WizardPrompter) -> WizardFlow:
    """选择配置流程"""
    flow_options = [
        create_select_option(
            "quickstart",
            "QuickStart",
            "Get running fast with sensible defaults",
        ),
        create_select_option(
            "advanced",
            "Advanced",
            "Full control over all settings",
        ),
    ]

    flow: WizardFlow = await prompter.select(
        WizardSelectParams(
            message="Which setup flow do you prefer?",
            options=flow_options,
            initial_value="quickstart",
        )
    )

    return flow


async def _configure_workspace(
    prompter: WizardPrompter,
    flow: WizardFlow,
) -> str:
    """配置工作区目录"""
    if flow == "quickstart":
        return DEFAULT_WORKSPACE

    workspace = await prompter.text(
        WizardTextParams(
            message="Workspace directory:",
            initial_value=DEFAULT_WORKSPACE,
            placeholder=DEFAULT_WORKSPACE,
        )
    )

    return workspace or DEFAULT_WORKSPACE


async def _show_completion(
    prompter: WizardPrompter,
    result: dict[str, Any],
) -> None:
    """显示完成信息"""
    mode = result.get("mode", "local")
    flow = result.get("flow", "quickstart")
    workspace = result.get("workspace", DEFAULT_WORKSPACE)

    summary_lines = [
        f"Mode: {mode}",
        f"Flow: {flow}",
        f"Workspace: {workspace}",
    ]

    gateway: GatewaySettings | None = result.get("gateway")
    if gateway:
        summary_lines.append(f"Gateway port: {gateway.port}")
        summary_lines.append(f"Gateway bind: {gateway.bind}")
        summary_lines.append(f"Auth mode: {gateway.auth_mode}")

    summary = "\n".join(summary_lines)

    await prompter.note(
        f"Configuration complete!\n\n{summary}\n\n"
        "Run `lurkbot start` to launch your bot.",
        title="✅ Setup Complete",
    )

    await prompter.outro("Happy botting! 🚀")


# ============================================================================
# 重置向导
# ============================================================================


async def run_reset_wizard(
    prompter: WizardPrompter,
) -> ResetScope | None:
    """
    运行重置向导

    对标 MoltBot runResetWizard()

    Args:
        prompter: 向导提示器

    Returns:
        重置范围，如果取消则返回 None
    """
    await prompter.intro("🔄 LurkBot Reset Wizard")

    await prompter.note(
        "This wizard will help you reset LurkBot configuration.\n"
        "Choose what you want to reset:",
        title="Reset Options",
    )

    scope_options = [
        create_select_option(
            "config",
            "Configuration only",
            "Reset config files, keep credentials and sessions",
        ),
        create_select_option(
            "config+creds+sessions",
            "Config + Credentials + Sessions",
            "Reset config, credentials, and active sessions",
        ),
        create_select_option(
            "full",
            "Full reset",
            "Remove everything and start fresh",
        ),
    ]

    scope: ResetScope = await prompter.select(
        WizardSelectParams(
            message="What do you want to reset?",
            options=scope_options,
            initial_value="config",
        )
    )

    # 确认
    confirmed = await prompter.confirm(
        WizardConfirmParams(
            message=f"Are you sure you want to perform a '{scope}' reset?",
            initial_value=False,
        )
    )

    if not confirmed:
        await prompter.outro("Reset cancelled.")
        return None

    await prompter.outro(f"Reset ({scope}) will be performed.")
    return scope
