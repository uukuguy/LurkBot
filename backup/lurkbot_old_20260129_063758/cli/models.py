"""Model management CLI commands."""

import typer
from rich.console import Console
from rich.table import Table

from lurkbot.config import get_settings
from lurkbot.models.registry import ModelRegistry

app = typer.Typer(help="Model management commands")
console = Console()


@app.command("list")
def list_models(
    provider: str = typer.Option(None, "--provider", "-p", help="Filter by provider"),
    api_type: str = typer.Option(None, "--api", "-a", help="Filter by API type"),
) -> None:
    """List available models."""
    settings = get_settings()
    registry = ModelRegistry(settings)

    models = registry.list_models(provider=provider, api_type=api_type)

    if not models:
        console.print("[yellow]No models found[/yellow]")
        return

    table = Table(title="Available Models")
    table.add_column("ID", style="cyan")
    table.add_column("Name", style="green")
    table.add_column("Provider", style="blue")
    table.add_column("API Type", style="magenta")
    table.add_column("Context", justify="right")
    table.add_column("Tools", justify="center")

    for model in models:
        tools_support = "✓" if model.capabilities.supports_tools else "✗"
        table.add_row(
            model.id,
            model.name,
            model.provider,
            model.api_type.value,
            f"{model.context_window:,}",
            tools_support,
        )

    console.print(table)
    console.print(f"\n[dim]Total: {len(models)} models[/dim]")


@app.command("info")
def model_info(
    model_id: str = typer.Argument(..., help="Model ID to get info for"),
) -> None:
    """Show detailed information about a model."""
    settings = get_settings()
    registry = ModelRegistry(settings)

    config = registry.get_config(model_id)
    if config is None:
        console.print(f"[red]Model not found: {model_id}[/red]")
        raise typer.Exit(1)

    console.print(f"\n[bold cyan]{config.name}[/bold cyan]")
    console.print(f"[dim]ID: {config.id}[/dim]\n")

    info_table = Table(show_header=False, box=None)
    info_table.add_column("Field", style="bold")
    info_table.add_column("Value")

    info_table.add_row("Provider", config.provider)
    info_table.add_row("API Type", config.api_type.value)
    info_table.add_row("Context Window", f"{config.context_window:,} tokens")
    info_table.add_row("Max Output", f"{config.max_tokens:,} tokens")

    console.print(info_table)

    # Capabilities
    console.print("\n[bold]Capabilities:[/bold]")
    caps = config.capabilities
    cap_items = [
        ("Tools", caps.supports_tools),
        ("Streaming", caps.supports_streaming),
        ("Vision", caps.supports_vision),
        ("Thinking", caps.supports_thinking),
    ]
    for name, supported in cap_items:
        status = "[green]✓[/green]" if supported else "[red]✗[/red]"
        console.print(f"  {status} {name}")


@app.command("default")
def set_default(
    model_id: str = typer.Argument(None, help="Model ID to set as default"),
) -> None:
    """Show or set the default model."""
    settings = get_settings()

    if model_id is None:
        # Show current default
        console.print(f"Default model: [cyan]{settings.agent.model}[/cyan]")
        return

    # Validate model exists
    registry = ModelRegistry(settings)
    config = registry.get_config(model_id)
    if config is None:
        console.print(f"[red]Model not found: {model_id}[/red]")
        raise typer.Exit(1)

    # Note: This just shows what the default would be set to
    # Actual persistence would require config file modification
    console.print("[yellow]To set default model, update your config:[/yellow]")
    console.print(f"\n  export LURKBOT_AGENT__MODEL={config.id}")
    console.print("\n  [dim]Or add to your config file:[/dim]")
    console.print(f'  {{"agent": {{"model": "{config.id}"}}}}')
