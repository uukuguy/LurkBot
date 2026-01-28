"""Main CLI entry point."""

import asyncio

import typer
from rich.console import Console

from lurkbot import __version__
from lurkbot.config import get_settings
from lurkbot.utils import setup_logging

app = typer.Typer(
    name="lurkbot",
    help="LurkBot - Multi-channel AI Assistant Platform",
    no_args_is_help=True,
)
console = Console()

# Sub-command groups
gateway_app = typer.Typer(help="Gateway server commands")
channels_app = typer.Typer(help="Channel management commands")
config_app = typer.Typer(help="Configuration commands")

app.add_typer(gateway_app, name="gateway")
app.add_typer(channels_app, name="channels")
app.add_typer(config_app, name="config")


@app.callback()
def main(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output"),
) -> None:
    """LurkBot CLI."""
    log_level = "DEBUG" if verbose else "INFO"
    setup_logging(level=log_level)


@app.command()
def version() -> None:
    """Show version information."""
    console.print(f"LurkBot v{__version__}")


# Gateway commands
@gateway_app.command("start")
def gateway_start(
    host: str = typer.Option(None, "--host", "-h", help="Host to bind to"),
    port: int = typer.Option(None, "--port", "-p", help="Port to listen on"),
) -> None:
    """Start the gateway server."""
    from lurkbot.gateway import GatewayServer

    settings = get_settings()
    if host:
        settings.gateway.host = host
    if port:
        settings.gateway.port = port

    console.print(f"Starting gateway on {settings.gateway.host}:{settings.gateway.port}")

    server = GatewayServer(settings)
    asyncio.run(server.run())


@gateway_app.command("status")
def gateway_status() -> None:
    """Check gateway server status."""
    import httpx

    settings = get_settings()
    url = f"http://{settings.gateway.host}:{settings.gateway.port}/health"

    try:
        response = httpx.get(url, timeout=5)
        if response.status_code == 200:
            console.print("[green]Gateway is running[/green]")
        else:
            console.print(f"[yellow]Gateway returned status {response.status_code}[/yellow]")
    except httpx.ConnectError:
        console.print("[red]Gateway is not running[/red]")


# Channel commands
@channels_app.command("list")
def channels_list() -> None:
    """List configured channels."""
    settings = get_settings()

    console.print("\n[bold]Configured Channels:[/bold]\n")

    channels = [
        ("Telegram", settings.telegram.enabled, bool(settings.telegram.bot_token)),
        ("Discord", settings.discord.enabled, bool(settings.discord.bot_token)),
        ("Slack", settings.slack.enabled, bool(settings.slack.bot_token)),
    ]

    for name, enabled, configured in channels:
        status = "[green]enabled[/green]" if enabled else "[dim]disabled[/dim]"
        config_status = "[green]configured[/green]" if configured else "[red]not configured[/red]"
        console.print(f"  {name}: {status} ({config_status})")


# Config commands
@config_app.command("show")
def config_show() -> None:
    """Show current configuration."""
    settings = get_settings()
    console.print("\n[bold]Current Configuration:[/bold]\n")
    console.print(f"  Data directory: {settings.data_dir}")
    console.print(f"  Log level: {settings.log_level}")
    console.print(f"  Gateway: {settings.gateway.host}:{settings.gateway.port}")
    console.print(f"  Default model: {settings.agent.model}")


@config_app.command("init")
def config_init() -> None:
    """Initialize configuration file."""
    from pathlib import Path

    settings = get_settings()
    config_dir = settings.data_dir
    config_file = config_dir / "config.json"

    if config_file.exists():
        console.print(f"[yellow]Config file already exists: {config_file}[/yellow]")
        return

    config_dir.mkdir(parents=True, exist_ok=True)

    import json

    default_config = {
        "gateway": {"host": "127.0.0.1", "port": 18789},
        "agent": {"model": "anthropic/claude-sonnet-4-20250514"},
        "telegram": {"enabled": False},
        "discord": {"enabled": False},
        "slack": {"enabled": False},
    }

    config_file.write_text(json.dumps(default_config, indent=2))
    console.print(f"[green]Created config file: {config_file}[/green]")


if __name__ == "__main__":
    app()
