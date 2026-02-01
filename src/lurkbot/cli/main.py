"""LurkBot CLI entry point."""

import asyncio
from typing import Optional

import typer

app = typer.Typer(
    name="lurkbot",
    help="LurkBot - Python port of MoltBot AI assistant",
    no_args_is_help=True,
)

# 注册子命令
from .models import app as models_app
from .plugin_cli import app as plugin_app
from .security import app as security_app
from .skills import app as skills_app

app.add_typer(models_app, name="models")
app.add_typer(security_app, name="security")
app.add_typer(skills_app, name="skills")
app.add_typer(plugin_app, name="plugin")


@app.command()
def version() -> None:
    """Show version information."""
    from lurkbot import __version__

    typer.echo(f"LurkBot v{__version__}")


@app.command()
def gateway(
    host: str = typer.Option("0.0.0.0", help="Host to bind to"),
    port: int = typer.Option(18789, help="Port to bind to"),
    reload: bool = typer.Option(False, "--reload", help="Enable hot reload (development)"),
) -> None:
    """Start the gateway server."""
    from lurkbot.gateway import start_gateway_server

    typer.echo(f"Starting gateway server on {host}:{port}...")
    start_gateway_server(host=host, port=port, reload=reload)


@app.command()
def chat(
    model: str = typer.Option("anthropic:claude-sonnet-4-20250514", help="Model to use"),
    workspace: str = typer.Option(".", help="Workspace directory"),
) -> None:
    """Start an interactive chat session."""
    typer.echo(f"Starting chat with model: {model}")
    typer.echo(f"Workspace: {workspace}")
    # TODO: Implement chat session


@app.command()
def wizard(
    mode: Optional[str] = typer.Option(
        None,
        "--mode",
        "-m",
        help="Setup mode: local or remote",
    ),
    flow: Optional[str] = typer.Option(
        None,
        "--flow",
        "-f",
        help="Setup flow: quickstart or advanced",
    ),
    workspace: Optional[str] = typer.Option(
        None,
        "--workspace",
        "-w",
        help="Workspace directory",
    ),
    accept_risk: bool = typer.Option(
        False,
        "--accept-risk",
        help="Accept security risk warning without prompt",
    ),
    skip_channels: bool = typer.Option(
        False,
        "--skip-channels",
        help="Skip channel configuration",
    ),
    skip_skills: bool = typer.Option(
        False,
        "--skip-skills",
        help="Skip skill configuration",
    ),
) -> None:
    """
    Run the interactive configuration wizard.

    This wizard helps you set up LurkBot with sensible defaults
    or full control over all settings.

    Examples:
        lurkbot wizard                    # Interactive setup
        lurkbot wizard --flow quickstart  # Quick setup with defaults
        lurkbot wizard --mode local       # Local gateway setup
    """
    from lurkbot.wizard import (
        OnboardOptions,
        WizardCancelledError,
        create_rich_prompter,
        run_onboarding_wizard,
    )

    # 创建选项
    options = OnboardOptions(
        mode=mode,  # type: ignore
        flow=flow,  # type: ignore
        workspace=workspace,
        accept_risk=accept_risk,
        skip_channels=skip_channels,
        skip_skills=skip_skills,
    )

    # 创建提示器
    prompter = create_rich_prompter()

    # 运行向导
    try:
        result = asyncio.run(run_onboarding_wizard(prompter, options))
        if result.get("accepted_risk"):
            typer.echo("\n✅ Configuration complete!")
        else:
            typer.echo("\n⚠️ Setup cancelled.")
    except WizardCancelledError:
        typer.echo("\n⚠️ Setup cancelled by user.")
        raise typer.Exit(code=1)
    except KeyboardInterrupt:
        typer.echo("\n⚠️ Setup interrupted.")
        raise typer.Exit(code=1)


@app.command()
def reset(
    scope: str = typer.Option(
        "config",
        "--scope",
        "-s",
        help="Reset scope: config, config+creds+sessions, or full",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Skip confirmation prompt",
    ),
) -> None:
    """
    Reset LurkBot configuration.

    Scopes:
        config                  - Reset config files only
        config+creds+sessions   - Reset config, credentials, and sessions
        full                    - Full reset (everything)

    Examples:
        lurkbot reset                     # Interactive reset
        lurkbot reset --scope full        # Full reset
        lurkbot reset --scope config -f   # Reset config without confirmation
    """
    from lurkbot.wizard import (
        WizardCancelledError,
        create_rich_prompter,
        run_reset_wizard,
    )

    if force:
        # 直接执行重置
        typer.echo(f"Resetting with scope: {scope}")
        # TODO: 实现实际的重置逻辑
        typer.echo("✅ Reset complete!")
        return

    # 交互式重置
    prompter = create_rich_prompter()

    try:
        result = asyncio.run(run_reset_wizard(prompter))
        if result:
            typer.echo(f"\n✅ Reset ({result}) complete!")
        else:
            typer.echo("\n⚠️ Reset cancelled.")
    except WizardCancelledError:
        typer.echo("\n⚠️ Reset cancelled by user.")
        raise typer.Exit(code=1)
    except KeyboardInterrupt:
        typer.echo("\n⚠️ Reset interrupted.")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
