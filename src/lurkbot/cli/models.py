"""CLI commands for LLM model management."""

import typer
from rich.console import Console
from rich.table import Table

from lurkbot.config.models import (
    list_models,
    list_providers,
)

app = typer.Typer(
    name="models",
    help="Manage LLM models and providers",
    no_args_is_help=True,
)
console = Console()


@app.command("list-providers")
def list_providers_cmd(
    domestic_only: bool = typer.Option(
        False, "--domestic", "-d", help="Only show domestic Chinese providers"
    ),
):
    """List available LLM providers.

    Examples:
        lurkbot models list-providers
        lurkbot models list-providers --domestic
    """
    providers = list_providers(domestic_only=domestic_only)

    table = Table(title="Available LLM Providers", show_header=True, header_style="bold magenta")
    table.add_column("Provider", style="cyan")
    table.add_column("Display Name", style="green")
    table.add_column("Base URL", style="yellow")
    table.add_column("API Key Env", style="blue")
    table.add_column("Models", style="white")

    for provider in providers:
        table.add_row(
            provider.name,
            provider.display_name,
            provider.base_url or "N/A",
            provider.api_key_env,
            str(len(provider.models)),
        )

    console.print(table)
    console.print(f"\n[bold]Total providers:[/bold] {len(providers)}")


@app.command("list")
def list_models_cmd(
    provider: str | None = typer.Option(None, "--provider", "-p", help="Filter by provider"),
    vision: bool | None = typer.Option(None, "--vision", help="Filter by vision support"),
):
    """List available LLM models.

    Examples:
        lurkbot models list
        lurkbot models list --provider deepseek
        lurkbot models list --vision
    """
    models = list_models(provider=provider, supports_vision=vision)

    table = Table(title="Available LLM Models", show_header=True, header_style="bold magenta")
    table.add_column("Provider", style="cyan")
    table.add_column("Model ID", style="green")
    table.add_column("Display Name", style="white")
    table.add_column("Context", style="yellow", justify="right")
    table.add_column("Vision", style="blue", justify="center")
    table.add_column("Function", style="blue", justify="center")

    for model in models:
        context_str = f"{model.context_window // 1000}K"
        vision_str = "✓" if model.supports_vision else "✗"
        function_str = "✓" if model.supports_function_calling else "✗"

        table.add_row(
            model.provider,
            model.model_id,
            model.display_name,
            context_str,
            vision_str,
            function_str,
        )

    console.print(table)
    console.print(f"\n[bold]Total models:[/bold] {len(models)}")

    if provider:
        console.print(f"[dim]Filtered by provider: {provider}[/dim]")
    if vision is not None:
        console.print(f"[dim]Filtered by vision support: {vision}[/dim]")


@app.command("info")
def model_info_cmd(
    provider: str = typer.Argument(..., help="Provider name (e.g., deepseek, qwen)"),
    model_id: str = typer.Argument(..., help="Model identifier (e.g., deepseek-chat)"),
):
    """Show detailed information about a specific model.

    Examples:
        lurkbot models info deepseek deepseek-chat
        lurkbot models info qwen qwen-plus
    """
    from lurkbot.config.models import get_model

    model = get_model(provider, model_id)

    if not model:
        console.print(f"[red]Error:[/red] Unknown model {provider}:{model_id}")
        raise typer.Exit(1)

    # Create info table
    table = Table(title=f"Model Information: {model.display_name}", show_header=False)
    table.add_column("Property", style="cyan", width=25)
    table.add_column("Value", style="white")

    table.add_row("Provider", model.provider)
    table.add_row("Model ID", model.model_id)
    table.add_row("Display Name", model.display_name)
    table.add_row("Base URL", model.base_url or "N/A")
    table.add_row("API Key Environment", model.api_key_env)
    table.add_row("Context Window", f"{model.context_window:,} tokens")
    if model.max_output_tokens:
        table.add_row("Max Output Tokens", f"{model.max_output_tokens:,} tokens")
    table.add_row("Supports Vision", "Yes ✓" if model.supports_vision else "No ✗")
    table.add_row(
        "Supports Function Calling", "Yes ✓" if model.supports_function_calling else "No ✗"
    )

    if model.description:
        table.add_row("Description", model.description)

    console.print(table)

    # Show usage example
    console.print("\n[bold]Usage Example:[/bold]")
    console.print(f"  export {model.api_key_env}=your-api-key-here")
    console.print(f"  lurkbot gateway --provider {model.provider} --model {model.model_id}")
