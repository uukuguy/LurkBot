"""
Security Audit System

对标 MoltBot src/security/audit.ts
"""

from dataclasses import dataclass
from typing import Literal


@dataclass
class SecurityFinding:
    """
    安全发现项

    对标: MoltBot SecurityFinding
    """

    level: Literal["critical", "warning", "info"]
    message: str
    fix: str | None = None


async def audit_security(deep: bool = False) -> list[SecurityFinding]:
    """
    执行安全审计

    Args:
        deep: 是否执行深度审计（包括模型安全检查）

    Returns:
        发现的安全问题列表

    对标: MoltBot auditSecurity()
    """
    findings: list[SecurityFinding] = []

    # A. Gateway 网络暴露检查
    findings.extend(await _audit_gateway_exposure())

    # B. DM 策略检查
    findings.extend(await _audit_dm_policy())

    # C. 模型安全检查（仅深度模式）
    if deep:
        findings.extend(await _audit_model_safety())

    return findings


async def _audit_gateway_exposure() -> list[SecurityFinding]:
    """
    Gateway 网络暴露检查

    绑定配置:
    - bind = "loopback" (127.0.0.1) → ✅ 安全
    - bind = "lan" (192.168.x.x) → ⚠️ 需认证
    - bind = "auto" (0.0.0.0) → ⚠️ 危险

    Returns:
        发现的安全问题列表

    对标: MoltBot _auditGatewayExposure()
    """
    findings: list[SecurityFinding] = []

    try:
        from ..config import load_config

        config = load_config()

        # 获取 Gateway 配置
        gateway_config = config.get("gateway", {})
        bind = gateway_config.get("bind", "loopback")
        auth_config = gateway_config.get("auth", {})
        auth_mode = auth_config.get("mode")

        # 检查是否暴露到网络
        is_exposed = bind in ("lan", "auto", "0.0.0.0")
        has_auth = auth_mode in ("token", "password")

        if is_exposed and not has_auth:
            findings.append(
                SecurityFinding(
                    level="critical",
                    message=(
                        "Gateway bound to network without authentication. "
                        "Anyone on your network can fully control your agent."
                    ),
                    fix="lurkbot config set gateway.bind loopback",
                )
            )
        elif is_exposed and has_auth:
            findings.append(
                SecurityFinding(
                    level="warning",
                    message=(
                        f"Gateway bound to {bind} with {auth_mode} authentication. "
                        "Ensure credentials are strong."
                    ),
                    fix=None,
                )
            )

    except Exception:
        # 如果配置加载失败，跳过检查
        pass

    return findings


async def _audit_dm_policy() -> list[SecurityFinding]:
    """
    DM 策略检查

    检查项:
    - 多发件人共享 main session → 建议隔离

    Returns:
        发现的安全问题列表

    对标: MoltBot _auditDMPolicy()
    """
    findings: list[SecurityFinding] = []

    try:
        from .dm_policy import load_dm_policy

        policy = load_dm_policy()

        # 检查是否多用户共享 main session
        if policy.dm_scope == "main" and policy.is_multi_user:
            findings.append(
                SecurityFinding(
                    level="warning",
                    message=(
                        "Multiple senders share the main session. "
                        "Consider isolating sessions for privacy."
                    ),
                    fix='lurkbot config set session.dmScope "per-channel-peer"',
                )
            )

    except Exception:
        # 如果配置加载失败，跳过检查
        pass

    return findings


async def _audit_model_safety() -> list[SecurityFinding]:
    """
    模型安全检查（深度模式）

    检查项:
    - 危险工具权限
    - 模型权限配置

    Returns:
        发现的安全问题列表

    对标: MoltBot _auditModelSafety()
    """
    findings: list[SecurityFinding] = []

    try:
        from .model_check import check_model_safety

        model_findings = await check_model_safety()
        findings.extend(model_findings)

    except Exception:
        # 如果检查失败，跳过
        pass

    return findings


async def apply_fixes(findings: list[SecurityFinding]) -> list[str]:
    """
    自动应用安全修复

    Args:
        findings: 安全发现项列表

    Returns:
        已应用的修复命令列表

    对标: MoltBot applyFixes()
    """
    applied_fixes: list[str] = []

    for finding in findings:
        if finding.fix and finding.level == "critical":
            try:
                # 解析修复命令
                # 格式: "lurkbot config set key value"
                if finding.fix.startswith("lurkbot config set "):
                    cmd_parts = finding.fix.split(" ")
                    if len(cmd_parts) >= 4:
                        key = cmd_parts[3]
                        value = " ".join(cmd_parts[4:]).strip('"')

                        # 应用配置修改
                        from ..config import set_config

                        set_config(key, value)
                        applied_fixes.append(finding.fix)

            except Exception:
                # 如果修复失败，跳过
                pass

    return applied_fixes
