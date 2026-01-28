"""LurkBot CLI entry point."""

import typer

app = typer.Typer(
    name="lurkbot",
    help="LurkBot - Python port of MoltBot AI assistant",
    no_args_is_help=True,
)


@app.command()
def version() -> None:
    """Show version information."""
    from lurkbot import __version__

    typer.echo(f"LurkBot v{__version__}")


@app.command()
def gateway(
    host: str = typer.Option("0.0.0.0", help="Host to bind to"),
    port: int = typer.Option(8000, help="Port to bind to"),
) -> None:
    """Start the gateway server."""
    typer.echo(f"Starting gateway server on {host}:{port}...")
    # TODO: Implement gateway server


@app.command()
def chat(
    model: str = typer.Option("anthropic:claude-sonnet-4-20250514", help="Model to use"),
    workspace: str = typer.Option(".", help="Workspace directory"),
) -> None:
    """Start an interactive chat session."""
    typer.echo(f"Starting chat with model: {model}")
    typer.echo(f"Workspace: {workspace}")
    # TODO: Implement chat session


if __name__ == "__main__":
    app()
