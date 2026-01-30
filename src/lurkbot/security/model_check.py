"""
Model Safety Checks

对标 MoltBot src/security/model_check.ts
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .audit import SecurityFinding


async def check_model_safety() -> list["SecurityFinding"]:
    """
    检查模型安全配置

    检查项:
    - 危险工具权限
    - 模型权限配置

    Returns:
        发现的安全问题列表

    对标: MoltBot checkModelSafety()
    """
    from .audit import SecurityFinding

    findings: list[SecurityFinding] = []

    # A. 检查危险工具访问
    findings.extend(await _check_dangerous_tools())

    # B. 检查模型权限
    findings.extend(await _validate_model_permissions())

    return findings


async def _check_dangerous_tools() -> list["SecurityFinding"]:
    """
    检查危险工具访问权限

    危险工具包括:
    - Shell 执行工具
    - 文件系统写入工具
    - 网络访问工具

    Returns:
        发现的安全问题列表

    对标: MoltBot _checkDangerousTools()
    """
    from .audit import SecurityFinding

    findings: list[SecurityFinding] = []

    try:
        from ..config import load_config

        config = load_config()

        # 获取工具配置
        tools_config = config.get("tools", {})
        enabled_tools = tools_config.get("enabled", [])

        # 检查是否启用了危险工具
        dangerous_tools = {
            "shell": "Shell execution tool allows arbitrary command execution",
            "file_write": "File write tool can modify system files",
            "network": "Network tool can access external services",
        }

        for tool_name, warning in dangerous_tools.items():
            if tool_name in enabled_tools:
                findings.append(
                    SecurityFinding(
                        level="warning",
                        message=f"Dangerous tool enabled: {tool_name}. {warning}",
                        fix=f'lurkbot config remove tools.enabled "{tool_name}"',
                    )
                )

    except Exception:
        # 如果配置加载失败，跳过检查
        pass

    return findings


async def _validate_model_permissions() -> list["SecurityFinding"]:
    """
    验证模型权限配置

    检查项:
    - 模型是否有文件系统访问权限
    - 模型是否有网络访问权限

    Returns:
        发现的安全问题列表

    对标: MoltBot _validateModelPermissions()
    """
    from .audit import SecurityFinding

    findings: list[SecurityFinding] = []

    try:
        from ..config import load_config

        config = load_config()

        # 获取模型配置
        model_config = config.get("model", {})
        permissions = model_config.get("permissions", {})

        # 检查文件系统权限
        fs_access = permissions.get("filesystem", "read-only")
        if fs_access == "full":
            findings.append(
                SecurityFinding(
                    level="warning",
                    message=(
                        "Model has full filesystem access. "
                        "Consider restricting to read-only."
                    ),
                    fix='lurkbot config set model.permissions.filesystem "read-only"',
                )
            )

        # 检查网络权限
        network_access = permissions.get("network", False)
        if network_access:
            findings.append(
                SecurityFinding(
                    level="info",
                    message="Model has network access enabled.",
                    fix=None,
                )
            )

    except Exception:
        # 如果配置加载失败，跳过检查
        pass

    return findings
