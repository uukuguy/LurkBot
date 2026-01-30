"""
Security Warning Formatting and Display

对标 MoltBot src/security/warnings.ts
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .audit import SecurityFinding


def format_security_warning(finding: "SecurityFinding") -> str:
    """
    格式化安全警告

    Args:
        finding: 安全发现项

    Returns:
        格式化的警告文本

    对标: MoltBot formatSecurityWarning()
    """
    level_icons = {
        "critical": "🔴",
        "warning": "🟡",
        "info": "🔵",
    }

    icon = level_icons.get(finding.level, "⚪")
    level_text = finding.level.upper()

    lines = [f"{icon} {level_text}: {finding.message}"]

    if finding.fix:
        lines.append(f"   Fix: {finding.fix}")

    return "\n".join(lines)


def generate_fix_command(finding: "SecurityFinding") -> str | None:
    """
    生成修复命令

    Args:
        finding: 安全发现项

    Returns:
        修复命令，如果没有则返回 None

    对标: MoltBot generateFixCommand()
    """
    return finding.fix


def warning_to_console(finding: "SecurityFinding") -> None:
    """
    输出警告到控制台

    Args:
        finding: 安全发现项

    对标: MoltBot warningToConsole()
    """
    from loguru import logger

    formatted = format_security_warning(finding)

    if finding.level == "critical":
        logger.error(formatted)
    elif finding.level == "warning":
        logger.warning(formatted)
    else:
        logger.info(formatted)


def format_findings_table(findings: list["SecurityFinding"]) -> str:
    """
    格式化发现项为表格

    Args:
        findings: 安全发现项列表

    Returns:
        表格文本

    对标: MoltBot formatFindingsTable()
    """
    if not findings:
        return "✓ No security issues found"

    lines = ["Security Audit Results", "=" * 60]

    for i, finding in enumerate(findings, 1):
        level_icons = {
            "critical": "🔴",
            "warning": "🟡",
            "info": "🔵",
        }
        icon = level_icons.get(finding.level, "⚪")

        lines.append(f"\n{i}. {icon} {finding.level.upper()}")
        lines.append(f"   {finding.message}")

        if finding.fix:
            lines.append(f"   Fix: {finding.fix}")

    return "\n".join(lines)


def get_severity_count(findings: list["SecurityFinding"]) -> dict[str, int]:
    """
    统计各严重级别的数量

    Args:
        findings: 安全发现项列表

    Returns:
        严重级别计数字典

    对标: MoltBot getSeverityCount()
    """
    counts = {"critical": 0, "warning": 0, "info": 0}

    for finding in findings:
        counts[finding.level] += 1

    return counts
