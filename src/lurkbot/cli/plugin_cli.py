"""插件管理 CLI 工具

提供命令行界面管理 LurkBot 插件系统，包括：
- 插件列表和搜索
- 插件安装和卸载
- 插件启用和禁用
- 性能报告查看
- 权限管理
- 版本管理
"""

import asyncio
import json
from enum import Enum
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.tree import Tree

from lurkbot.plugins.loader import PluginState
from lurkbot.plugins.manager import get_plugin_manager
from lurkbot.plugins.permissions import PermissionType

# 创建 Typer 应用
app = typer.Typer(
    name="plugin",
    help="Manage LurkBot plugins",
    no_args_is_help=True,
)

# Rich console for beautiful output
console = Console()


# ============================================================================
# 辅助函数
# ============================================================================


def get_manager():
    """获取插件管理器实例"""
    return get_plugin_manager()


def format_plugin_status(state: PluginState) -> str:
    """格式化插件状态为彩色文本"""
    status_colors = {
        PluginState.LOADED: "[green]●[/green] Loaded",
        PluginState.ENABLED: "[bright_green]●[/bright_green] Enabled",
        PluginState.DISABLED: "[yellow]●[/yellow] Disabled",
        PluginState.ERROR: "[red]●[/red] Error",
        PluginState.UNLOADED: "[dim]○[/dim] Unloaded",
    }
    return status_colors.get(state, f"[dim]{state.value}[/dim]")


def print_error(message: str) -> None:
    """打印错误消息"""
    console.print(f"[red]✗[/red] {message}")


def print_success(message: str) -> None:
    """打印成功消息"""
    console.print(f"[green]✓[/green] {message}")


def print_warning(message: str) -> None:
    """打印警告消息"""
    console.print(f"[yellow]⚠[/yellow] {message}")


# ============================================================================
# 插件列表和搜索命令
# ============================================================================


class StatusFilter(str, Enum):
    """状态筛选枚举"""

    ALL = "all"
    ENABLED = "enabled"
    DISABLED = "disabled"
    ERROR = "error"


@app.command("list")
def list_plugins(
    status: Annotated[
        Optional[StatusFilter],
        typer.Option("--status", "-s", help="Filter by status"),
    ] = None,
    plugin_type: Annotated[
        Optional[str],
        typer.Option("--type", "-t", help="Filter by plugin type"),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output in JSON format"),
    ] = False,
) -> None:
    """List all plugins with optional filters.

    Examples:
        lurkbot plugin list
        lurkbot plugin list --status enabled
        lurkbot plugin list --type tool
        lurkbot plugin list --json
    """
    manager = get_manager()
    plugins = manager.list_plugins()

    # Apply filters
    if status and status != StatusFilter.ALL:
        if status == StatusFilter.ENABLED:
            plugins = [p for p in plugins if p.state == PluginState.ENABLED]
        elif status == StatusFilter.DISABLED:
            plugins = [p for p in plugins if p.state == PluginState.DISABLED]
        elif status == StatusFilter.ERROR:
            plugins = [p for p in plugins if p.state == PluginState.ERROR]

    if plugin_type:
        plugins = [p for p in plugins if p.manifest.type == plugin_type]

    # Output
    if json_output:
        output = [
            {
                "name": p.manifest.name,
                "version": p.manifest.version,
                "type": p.manifest.type,
                "status": p.state.value,
                "description": p.manifest.description,
            }
            for p in plugins
        ]
        console.print_json(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        if not plugins:
            print_warning("No plugins found")
            return

        table = Table(title=f"Plugins ({len(plugins)} total)")
        table.add_column("Name", style="cyan", no_wrap=True)
        table.add_column("Version", style="magenta")
        table.add_column("Type", style="blue")
        table.add_column("Status")
        table.add_column("Description", style="dim")

        for plugin in plugins:
            table.add_row(
                plugin.manifest.name,
                plugin.manifest.version,
                plugin.manifest.type,
                format_plugin_status(plugin.state),
                plugin.manifest.description or "",
            )

        console.print(table)


@app.command("search")
def search_plugins(
    query: Annotated[str, typer.Argument(help="Search query")],
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output in JSON format"),
    ] = False,
) -> None:
    """Search plugins by name, description, or tags.

    Examples:
        lurkbot plugin search "weather"
        lurkbot plugin search "api" --json
    """
    manager = get_manager()
    all_plugins = manager.list_plugins()

    # Search in name, description, and tags
    query_lower = query.lower()
    matched_plugins = [
        p
        for p in all_plugins
        if query_lower in p.manifest.name.lower()
        or (p.manifest.description and query_lower in p.manifest.description.lower())
        or any(query_lower in tag.lower() for tag in (p.manifest.tags or []))
    ]

    if not matched_plugins:
        print_warning(f"No plugins found matching '{query}'")
        return

    # Output
    if json_output:
        output = [
            {
                "name": p.manifest.name,
                "version": p.manifest.version,
                "description": p.manifest.description,
                "tags": p.manifest.tags,
            }
            for p in matched_plugins
        ]
        console.print_json(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        console.print(f"\n[bold]Found {len(matched_plugins)} plugin(s):[/bold]\n")
        for plugin in matched_plugins:
            console.print(f"[cyan]{plugin.manifest.name}[/cyan] v{plugin.manifest.version}")
            if plugin.manifest.description:
                console.print(f"  {plugin.manifest.description}")
            if plugin.manifest.tags:
                console.print(f"  Tags: {', '.join(plugin.manifest.tags)}")
            console.print()


@app.command("info")
def plugin_info(
    name: Annotated[str, typer.Argument(help="Plugin name")],
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output in JSON format"),
    ] = False,
) -> None:
    """Show detailed information about a plugin.

    Examples:
        lurkbot plugin info my-plugin
        lurkbot plugin info my-plugin --json
    """
    manager = get_plugin_manager()
    plugin = manager.get_plugin(name)

    if not plugin:
        print_error(f"Plugin '{name}' not found")
        raise typer.Exit(code=1)

    if json_output:
        output = {
            "name": plugin.manifest.name,
            "version": plugin.manifest.version,
            "type": plugin.manifest.type,
            "status": plugin.state.value,
            "description": plugin.manifest.description,
            "author": plugin.manifest.author.model_dump() if plugin.manifest.author else None,
            "tags": plugin.manifest.tags,
            "dependencies": plugin.manifest.dependencies.model_dump(),
            "permissions": plugin.manifest.permissions.model_dump(),
        }
        console.print_json(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        console.print(f"\n[bold cyan]{plugin.manifest.name}[/bold cyan] v{plugin.manifest.version}")
        console.print(f"Status: {format_plugin_status(plugin.state)}")
        console.print(f"Type: [blue]{plugin.manifest.type}[/blue]")

        if plugin.manifest.description:
            console.print(f"\n[bold]Description:[/bold]\n{plugin.manifest.description}")

        if plugin.manifest.author:
            console.print(f"\n[bold]Author:[/bold] {plugin.manifest.author}")

        if plugin.manifest.tags:
            console.print(f"\n[bold]Tags:[/bold] {', '.join(plugin.manifest.tags)}")

        if plugin.manifest.dependencies:
            console.print(f"\n[bold]Dependencies:[/bold]")
            deps = plugin.manifest.dependencies
            if deps.python:
                console.print(f"  Python: {', '.join(deps.python)}")
            if deps.system:
                console.print(f"  System: {', '.join(deps.system)}")
            if deps.env:
                console.print(f"  Environment: {', '.join(deps.env)}")

        if plugin.manifest.permissions:
            console.print(f"\n[bold]Permissions:[/bold]")
            perms = plugin.manifest.permissions
            if perms.filesystem:
                console.print(f"  • Filesystem access")
            if perms.network:
                console.print(f"  • Network access")
            if perms.exec:
                console.print(f"  • Command execution")
            if perms.channels:
                console.print(f"  • Channels: {', '.join(perms.channels)}")

        console.print()


# ============================================================================
# 插件安装和卸载命令
# ============================================================================


@app.command("install")
def install_plugin(
    path: Annotated[str, typer.Argument(help="Path to plugin directory or Git URL")],
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Force installation even if validation fails"),
    ] = False,
) -> None:
    """Install a plugin from local directory or Git repository.

    Examples:
        lurkbot plugin install ./my-plugin
        lurkbot plugin install https://github.com/user/plugin.git
        lurkbot plugin install ./my-plugin --force
    """
    console.print(f"[yellow]Installing plugin from:[/yellow] {path}")

    # TODO: Implement actual installation logic
    # This would involve:
    # 1. Validate plugin manifest
    # 2. Check dependencies
    # 3. Copy/clone plugin to plugins directory
    # 4. Load plugin

    print_warning("Plugin installation not yet implemented")
    print_warning("This feature will be available in a future release")


@app.command("uninstall")
def uninstall_plugin(
    name: Annotated[str, typer.Argument(help="Plugin name")],
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Skip confirmation prompt"),
    ] = False,
) -> None:
    """Uninstall a plugin.

    Examples:
        lurkbot plugin uninstall my-plugin
        lurkbot plugin uninstall my-plugin --force
    """
    manager = get_manager()
    plugin = manager.get_plugin(name)

    if not plugin:
        print_error(f"Plugin '{name}' not found")
        raise typer.Exit(code=1)

    # Confirmation
    if not force:
        confirm = typer.confirm(f"Are you sure you want to uninstall '{name}'?")
        if not confirm:
            print_warning("Uninstall cancelled")
            return

    # Unload plugin
    async def _uninstall():
        success = await manager.unload_plugin(name)
        if success:
            print_success(f"Plugin '{name}' uninstalled successfully")
        else:
            print_error(f"Failed to uninstall plugin '{name}'")
            raise typer.Exit(code=1)

    asyncio.run(_uninstall())


# ============================================================================
# 插件启用和禁用命令
# ============================================================================


@app.command("enable")
def enable_plugin(
    name: Annotated[str, typer.Argument(help="Plugin name")],
) -> None:
    """Enable a plugin.

    Examples:
        lurkbot plugin enable my-plugin
    """
    manager = get_manager()

    async def _enable():
        success = await manager.enable_plugin(name)
        if success:
            print_success(f"Plugin '{name}' enabled")
        else:
            print_error(f"Failed to enable plugin '{name}'")
            raise typer.Exit(code=1)

    asyncio.run(_enable())


@app.command("disable")
def disable_plugin(
    name: Annotated[str, typer.Argument(help="Plugin name")],
) -> None:
    """Disable a plugin.

    Examples:
        lurkbot plugin disable my-plugin
    """
    manager = get_manager()

    async def _disable():
        success = await manager.disable_plugin(name)
        if success:
            print_success(f"Plugin '{name}' disabled")
        else:
            print_error(f"Failed to disable plugin '{name}'")
            raise typer.Exit(code=1)

    asyncio.run(_disable())


# ============================================================================
# 性能报告命令
# ============================================================================


@app.command("perf")
def performance_report(
    name: Annotated[Optional[str], typer.Argument(help="Plugin name")] = None,
    show_all: Annotated[
        bool,
        typer.Option("--all", help="Show all plugin performance reports"),
    ] = False,
    bottlenecks: Annotated[
        bool,
        typer.Option("--bottlenecks", help="Show performance bottlenecks"),
    ] = False,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output in JSON format"),
    ] = False,
) -> None:
    """View plugin performance reports.

    Examples:
        lurkbot plugin perf my-plugin
        lurkbot plugin perf --all
        lurkbot plugin perf --bottlenecks
        lurkbot plugin perf my-plugin --json
    """
    manager = get_manager()

    if not manager.profiler:
        print_error("Performance profiling is not enabled")
        raise typer.Exit(code=1)

    if bottlenecks:
        # Show bottlenecks
        bottleneck_list = manager.get_performance_bottlenecks()
        if not bottleneck_list:
            print_success("No performance bottlenecks detected")
            return

        if json_output:
            console.print_json(json.dumps(bottleneck_list, indent=2, ensure_ascii=False))
        else:
            console.print("\n[bold red]Performance Bottlenecks:[/bold red]\n")
            for item in bottleneck_list:
                console.print(f"[yellow]●[/yellow] {item['plugin']}")
                console.print(f"  Avg time: {item['avg_time']:.3f}s")
                console.print(f"  Max time: {item['max_time']:.3f}s")
                console.print()

    elif show_all:
        # Show all reports
        reports = manager.get_all_performance_reports()
        if not reports:
            print_warning("No performance data available")
            return

        if json_output:
            output = {
                name: {
                    "total_executions": report.total_executions,
                    "successful_executions": report.successful_executions,
                    "failed_executions": report.failed_executions,
                    "avg_execution_time": report.avg_execution_time,
                    "min_execution_time": report.min_execution_time,
                    "max_execution_time": report.max_execution_time,
                }
                for name, report in reports.items()
            }
            console.print_json(json.dumps(output, indent=2, ensure_ascii=False))
        else:
            table = Table(title="Plugin Performance Reports")
            table.add_column("Plugin", style="cyan")
            table.add_column("Executions", justify="right")
            table.add_column("Avg Time", justify="right")
            table.add_column("Min Time", justify="right")
            table.add_column("Max Time", justify="right")

            for plugin_name, report in reports.items():
                table.add_row(
                    plugin_name,
                    str(report.total_executions),
                    f"{report.avg_execution_time:.3f}s",
                    f"{report.min_execution_time:.3f}s",
                    f"{report.max_execution_time:.3f}s",
                )

            console.print(table)

    elif name:
        # Show specific plugin report
        report = manager.get_performance_report(name)
        if not report:
            print_error(f"No performance data for plugin '{name}'")
            raise typer.Exit(code=1)

        if json_output:
            output = {
                "plugin": name,
                "total_executions": report.total_executions,
                "successful_executions": report.successful_executions,
                "failed_executions": report.failed_executions,
                "avg_execution_time": report.avg_execution_time,
                "min_execution_time": report.min_execution_time,
                "max_execution_time": report.max_execution_time,
            }
            console.print_json(json.dumps(output, indent=2, ensure_ascii=False))
        else:
            console.print(f"\n[bold cyan]Performance Report: {name}[/bold cyan]\n")
            console.print(f"Total Executions: {report.total_executions}")
            console.print(f"Successful: {report.successful_executions}")
            console.print(f"Failed: {report.failed_executions}")
            console.print(f"Average Time: {report.avg_execution_time:.3f}s")
            console.print(f"Min Time: {report.min_execution_time:.3f}s")
            console.print(f"Max Time: {report.max_execution_time:.3f}s")
            console.print()

    else:
        print_error("Please specify a plugin name, use --all, or --bottlenecks")
        raise typer.Exit(code=1)


# ============================================================================
# 权限管理命令
# ============================================================================


@app.command("permissions")
def show_permissions(
    name: Annotated[str, typer.Argument(help="Plugin name")],
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output in JSON format"),
    ] = False,
) -> None:
    """Show plugin permissions.

    Examples:
        lurkbot plugin permissions my-plugin
        lurkbot plugin permissions my-plugin --json
    """
    manager = get_manager()

    if not manager.permission_manager:
        print_error("Permission management is not enabled")
        raise typer.Exit(code=1)

    plugin = manager.get_plugin(name)
    if not plugin:
        print_error(f"Plugin '{name}' not found")
        raise typer.Exit(code=1)

    permissions = manager.permission_manager.get_plugin_permissions(name)

    if json_output:
        output = [
            {
                "type": perm.type.value,
                "level": perm.level.value,
            }
            for perm in permissions
        ]
        console.print_json(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        if not permissions:
            print_warning(f"No permissions granted to '{name}'")
            return

        console.print(f"\n[bold cyan]Permissions for {name}:[/bold cyan]\n")
        for perm in permissions:
            level_color = "green" if perm.level.value == "admin" else "yellow"
            console.print(
                f"[{level_color}]●[/{level_color}] {perm.type.value} "
                f"({perm.level.value})"
            )
        console.print()


@app.command("grant")
def grant_permission(
    name: Annotated[str, typer.Argument(help="Plugin name")],
    permission_type: Annotated[str, typer.Argument(help="Permission type")],
) -> None:
    """Grant permission to a plugin.

    Examples:
        lurkbot plugin grant my-plugin file_read
        lurkbot plugin grant my-plugin network_access
    """
    manager = get_manager()

    if not manager.permission_manager:
        print_error("Permission management is not enabled")
        raise typer.Exit(code=1)

    # Validate permission type
    try:
        perm_type = PermissionType(permission_type)
    except ValueError:
        print_error(f"Invalid permission type: {permission_type}")
        print_warning(f"Valid types: {', '.join(t.value for t in PermissionType)}")
        raise typer.Exit(code=1)

    async def _grant():
        success = await manager.grant_permission(name, perm_type)
        if success:
            print_success(f"Granted '{permission_type}' permission to '{name}'")
        else:
            print_error(f"Failed to grant permission to '{name}'")
            raise typer.Exit(code=1)

    asyncio.run(_grant())


@app.command("revoke")
def revoke_permission(
    name: Annotated[str, typer.Argument(help="Plugin name")],
    permission_type: Annotated[str, typer.Argument(help="Permission type")],
) -> None:
    """Revoke permission from a plugin.

    Examples:
        lurkbot plugin revoke my-plugin file_read
        lurkbot plugin revoke my-plugin network_access
    """
    manager = get_manager()

    if not manager.permission_manager:
        print_error("Permission management is not enabled")
        raise typer.Exit(code=1)

    # Validate permission type
    try:
        perm_type = PermissionType(permission_type)
    except ValueError:
        print_error(f"Invalid permission type: {permission_type}")
        print_warning(f"Valid types: {', '.join(t.value for t in PermissionType)}")
        raise typer.Exit(code=1)

    async def _revoke():
        success = await manager.revoke_permission(name, perm_type)
        if success:
            print_success(f"Revoked '{permission_type}' permission from '{name}'")
        else:
            print_error(f"Failed to revoke permission from '{name}'")
            raise typer.Exit(code=1)

    asyncio.run(_revoke())


@app.command("audit-log")
def audit_log(
    name: Annotated[Optional[str], typer.Argument(help="Plugin name")] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output in JSON format"),
    ] = False,
) -> None:
    """View permission audit log.

    Examples:
        lurkbot plugin audit-log
        lurkbot plugin audit-log my-plugin
        lurkbot plugin audit-log --json
    """
    manager = get_manager()

    if not manager.permission_manager:
        print_error("Permission management is not enabled")
        raise typer.Exit(code=1)

    async def _get_log():
        logs = await manager.get_permission_audit_log(name)
        if not logs:
            print_warning("No audit log entries found")
            return

        if json_output:
            console.print_json(json.dumps(logs, indent=2, ensure_ascii=False, default=str))
        else:
            console.print(f"\n[bold]Permission Audit Log ({len(logs)} entries):[/bold]\n")
            for entry in logs:
                console.print(f"[cyan]{entry.get('timestamp', 'N/A')}[/cyan]")
                console.print(f"  Plugin: {entry.get('plugin_name', 'N/A')}")
                console.print(f"  Action: {entry.get('action', 'N/A')}")
                console.print(f"  Permission: {entry.get('permission_type', 'N/A')}")
                console.print()

    asyncio.run(_get_log())


# ============================================================================
# 版本管理命令
# ============================================================================


@app.command("versions")
def list_versions(
    name: Annotated[str, typer.Argument(help="Plugin name")],
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output in JSON format"),
    ] = False,
) -> None:
    """List available versions of a plugin.

    Examples:
        lurkbot plugin versions my-plugin
        lurkbot plugin versions my-plugin --json
    """
    manager = get_manager()

    if not manager.version_manager:
        print_error("Version management is not enabled")
        raise typer.Exit(code=1)

    versions = manager.get_plugin_versions(name)

    if not versions:
        print_warning(f"No versions found for plugin '{name}'")
        return

    if json_output:
        console.print_json(json.dumps(versions, indent=2, ensure_ascii=False))
    else:
        console.print(f"\n[bold cyan]Versions for {name}:[/bold cyan]\n")
        for version in versions:
            console.print(f"  • {version}")
        console.print()


@app.command("switch")
def switch_version(
    name: Annotated[str, typer.Argument(help="Plugin name")],
    version: Annotated[str, typer.Argument(help="Version to switch to")],
) -> None:
    """Switch plugin to a different version.

    Examples:
        lurkbot plugin switch my-plugin 1.0.0
        lurkbot plugin switch my-plugin 2.0.0
    """
    manager = get_manager()

    if not manager.version_manager:
        print_error("Version management is not enabled")
        raise typer.Exit(code=1)

    async def _switch():
        success = await manager.switch_plugin_version(name, version)
        if success:
            print_success(f"Switched '{name}' to version {version}")
        else:
            print_error(f"Failed to switch '{name}' to version {version}")
            raise typer.Exit(code=1)

    asyncio.run(_switch())


@app.command("rollback")
def rollback_version(
    name: Annotated[str, typer.Argument(help="Plugin name")],
) -> None:
    """Rollback plugin to previous version.

    Examples:
        lurkbot plugin rollback my-plugin
    """
    manager = get_manager()

    if not manager.version_manager:
        print_error("Version management is not enabled")
        raise typer.Exit(code=1)

    async def _rollback():
        success = await manager.rollback_plugin_version(name)
        if success:
            print_success(f"Rolled back '{name}' to previous version")
        else:
            print_error(f"Failed to rollback '{name}'")
            raise typer.Exit(code=1)

    asyncio.run(_rollback())


@app.command("history")
def version_history(
    name: Annotated[str, typer.Argument(help="Plugin name")],
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output in JSON format"),
    ] = False,
) -> None:
    """View version history of a plugin.

    Examples:
        lurkbot plugin history my-plugin
        lurkbot plugin history my-plugin --json
    """
    manager = get_manager()

    if not manager.version_manager:
        print_error("Version management is not enabled")
        raise typer.Exit(code=1)

    history = manager.get_version_history(name)

    if not history:
        print_warning(f"No version history for plugin '{name}'")
        return

    if json_output:
        console.print_json(json.dumps(history, indent=2, ensure_ascii=False, default=str))
    else:
        console.print(f"\n[bold cyan]Version History for {name}:[/bold cyan]\n")
        for entry in history:
            console.print(f"[yellow]●[/yellow] {entry.get('version', 'N/A')}")
            console.print(f"  Switched at: {entry.get('timestamp', 'N/A')}")
            console.print()


# ============================================================================
# 依赖图可视化命令
# ============================================================================


@app.command("deps")
def show_dependencies(
    output_format: Annotated[
        str,
        typer.Option("--format", "-f", help="Output format: text or json"),
    ] = "text",
) -> None:
    """Visualize plugin dependency graph.

    Examples:
        lurkbot plugin deps
        lurkbot plugin deps --format json
    """
    manager = get_manager()

    if not manager.orchestrator:
        print_error("Plugin orchestration is not enabled")
        raise typer.Exit(code=1)

    graph = manager.visualize_dependency_graph(output_format=output_format)

    if output_format == "json":
        console.print_json(graph)
    else:
        console.print("\n[bold]Plugin Dependency Graph:[/bold]\n")
        console.print(graph)


if __name__ == "__main__":
    app()
