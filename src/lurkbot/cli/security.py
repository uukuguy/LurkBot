"""
Security CLI Commands

对标 MoltBot src/cli/security.ts
"""

import asyncio

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(name="security", help="Security audit and management")
console = Console()


@app.command()
def audit(
    deep: bool = typer.Option(False, "--deep", help="执行深度审计（包括模型安全检查）"),
    fix: bool = typer.Option(False, "--fix", help="自动修复关键安全问题"),
    json_output: bool = typer.Option(False, "--json", help="输出 JSON 格式"),
) -> None:
    """
    执行安全审计

    用法:
    - lurkbot security audit          # 标准审计
    - lurkbot security audit --deep   # 深度审计
    - lurkbot security audit --fix    # 自动修复
    - lurkbot security audit --json   # JSON 输出

    对标: MoltBot security audit
    """
    from ..security import audit_security, apply_fixes, format_findings_table, get_severity_count

    # 执行审计
    findings = asyncio.run(audit_security(deep=deep))

    if not findings:
        if json_output:
            import json

            print(json.dumps({"status": "ok", "findings": []}))
        else:
            console.print("[green]✓[/green] No security issues found")
        return

    # JSON 输出
    if json_output:
        import json

        findings_data = [
            {"level": f.level, "message": f.message, "fix": f.fix} for f in findings
        ]
        print(json.dumps({"status": "issues_found", "findings": findings_data}))
        return

    # 显示发现
    console.print("\n[bold]Security Audit Results[/bold]\n")

    # 统计严重级别
    counts = get_severity_count(findings)
    console.print(
        f"Found {len(findings)} issues: "
        f"[red]{counts['critical']} critical[/red], "
        f"[yellow]{counts['warning']} warnings[/yellow], "
        f"[blue]{counts['info']} info[/blue]\n"
    )

    # 显示详细信息
    for i, finding in enumerate(findings, 1):
        level_colors = {
            "critical": "red",
            "warning": "yellow",
            "info": "blue",
        }
        level_icons = {
            "critical": "🔴",
            "warning": "🟡",
            "info": "🔵",
        }

        color = level_colors.get(finding.level, "white")
        icon = level_icons.get(finding.level, "⚪")

        console.print(f"{i}. {icon} [{color}]{finding.level.upper()}[/{color}]")
        console.print(f"   {finding.message}")

        if finding.fix:
            console.print(f"   [dim]Fix: {finding.fix}[/dim]")

        console.print()

    # 自动修复
    if fix:
        console.print("\n[bold]Applying fixes...[/bold]\n")
        applied = asyncio.run(apply_fixes(findings))

        if applied:
            console.print(f"[green]✓[/green] Applied {len(applied)} fixes:")
            for cmd in applied:
                console.print(f"  - {cmd}")
        else:
            console.print("[yellow]No automatic fixes available[/yellow]")


@app.command()
def check_dm_policy() -> None:
    """
    检查 DM 策略配置

    对标: MoltBot security check-dm-policy
    """
    from ..security import get_recommended_dm_scope, load_dm_policy, validate_dm_policy

    policy = load_dm_policy()

    console.print("\n[bold]DM Policy Configuration[/bold]\n")
    console.print(f"DM Scope: [cyan]{policy.dm_scope}[/cyan]")
    console.print(f"Multi-user: [cyan]{policy.is_multi_user}[/cyan]")

    is_safe = validate_dm_policy(policy)

    if is_safe:
        console.print("\n[green]✓[/green] DM policy is secure")
    else:
        console.print("\n[yellow]⚠[/yellow] DM policy may have security issues")
        recommended = get_recommended_dm_scope(policy.is_multi_user)
        console.print(f"Recommended: [cyan]{recommended}[/cyan]")
        console.print(f'\nFix: lurkbot config set session.dmScope "{recommended}"')


@app.command()
def check_gateway() -> None:
    """
    检查 Gateway 网络暴露配置

    对标: MoltBot security check-gateway
    """
    import asyncio

    from ..security.audit import _audit_gateway_exposure

    findings = asyncio.run(_audit_gateway_exposure())

    console.print("\n[bold]Gateway Security Check[/bold]\n")

    if not findings:
        console.print("[green]✓[/green] Gateway configuration is secure")
    else:
        for finding in findings:
            level_colors = {
                "critical": "red",
                "warning": "yellow",
                "info": "blue",
            }
            color = level_colors.get(finding.level, "white")

            console.print(f"[{color}]{finding.level.upper()}[/{color}]: {finding.message}")
            if finding.fix:
                console.print(f"Fix: {finding.fix}")


if __name__ == "__main__":
    app()
