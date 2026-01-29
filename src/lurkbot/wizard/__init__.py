"""
LurkBot Wizard 配置向导模块

对标 MoltBot wizard/ 模块

提供交互式配置向导功能：
- Onboarding 配置向导
- Gateway 配置流程
- 会话管理
"""

from .prompts import (
    WizardCancelledError,
    WizardConfirmParams,
    WizardMultiSelectParams,
    WizardProgress,
    WizardPrompter,
    WizardSelectParams,
    WizardTextParams,
    WizardValidationError,
    create_select_option,
    create_select_params,
)
from .session import WizardSession, WizardSessionPrompter, create_deferred
from .types import (
    DEFAULT_GATEWAY_PORT,
    DEFAULT_WORKSPACE,
    SECURITY_WARNING,
    GatewayAuthChoice,
    GatewayBindMode,
    GatewaySettings,
    OnboardMode,
    OnboardOptions,
    QuickstartGatewayDefaults,
    ResetScope,
    TailscaleMode,
    WizardFlow,
    WizardNextResult,
    WizardSelectOption,
    WizardSessionStatus,
    WizardStep,
    WizardStepExecutor,
    WizardStepType,
    is_valid_ipv4,
    is_valid_port,
)
from .flows import (
    configure_gateway_for_onboarding,
    run_onboarding_wizard,
    run_reset_wizard,
)
from .rich_prompter import RichPrompter, RichProgress, create_rich_prompter

__all__ = [
    # Types
    "WizardSessionStatus",
    "WizardStepType",
    "WizardStepExecutor",
    "OnboardMode",
    "WizardFlow",
    "ResetScope",
    "GatewayBindMode",
    "GatewayAuthChoice",
    "TailscaleMode",
    "WizardSelectOption",
    "WizardStep",
    "WizardNextResult",
    "OnboardOptions",
    "QuickstartGatewayDefaults",
    "GatewaySettings",
    # Prompts
    "WizardSelectParams",
    "WizardMultiSelectParams",
    "WizardTextParams",
    "WizardConfirmParams",
    "WizardProgress",
    "WizardPrompter",
    "WizardCancelledError",
    "WizardValidationError",
    "create_select_option",
    "create_select_params",
    # Session
    "WizardSession",
    "WizardSessionPrompter",
    "create_deferred",
    # Flows
    "configure_gateway_for_onboarding",
    "run_onboarding_wizard",
    "run_reset_wizard",
    # Rich Prompter
    "RichPrompter",
    "RichProgress",
    "create_rich_prompter",
    # Constants
    "DEFAULT_GATEWAY_PORT",
    "DEFAULT_WORKSPACE",
    "SECURITY_WARNING",
    # Validators
    "is_valid_ipv4",
    "is_valid_port",
]
