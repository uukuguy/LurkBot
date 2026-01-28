"""Session management CLI commands."""

import asyncio

import typer
from rich.console import Console
from rich.table import Table

from lurkbot.config import get_settings
from lurkbot.storage.jsonl import SessionStore

app = typer.Typer(help="Session management commands")
console = Console()


async def _get_session_store() -> SessionStore:
    """Get configured session store."""
    settings = get_settings()
    sessions_dir = settings.data_dir / "sessions"
    store = SessionStore(sessions_dir=sessions_dir)
    await store.initialize()
    return store


@app.command("list")
def list_sessions() -> None:
    """List all sessions."""

    async def _list() -> None:
        store = await _get_session_store()
        session_ids = await store.list_sessions()

        if not session_ids:
            console.print("[yellow]No sessions found[/yellow]")
            return

        table = Table(title="Sessions")
        table.add_column("Session ID", style="cyan")
        table.add_column("Channel", style="blue")
        table.add_column("Type", style="magenta")
        table.add_column("Messages", justify="right")
        table.add_column("Last Activity", style="dim")

        for session_id in session_ids:
            try:
                metadata = await store.load_metadata(session_id)
                msg_count = await store.get_message_count(session_id)

                last_activity = "-"
                if metadata.updated_at:
                    last_activity = metadata.updated_at.strftime("%Y-%m-%d %H:%M")

                table.add_row(
                    session_id,
                    metadata.channel,
                    metadata.session_type,
                    str(msg_count),
                    last_activity,
                )
            except Exception:
                table.add_row(session_id, "-", "-", "-", "[red]error[/red]")

        console.print(table)
        console.print(f"\n[dim]Total: {len(session_ids)} sessions[/dim]")

    asyncio.run(_list())


@app.command("show")
def show_session(
    session_id: str = typer.Argument(..., help="Session ID to show"),
    limit: int = typer.Option(10, "--limit", "-n", help="Number of messages to show"),
) -> None:
    """Show session details and recent messages."""

    async def _show() -> None:
        store = await _get_session_store()

        if not await store.session_exists(session_id):
            console.print(f"[red]Session not found: {session_id}[/red]")
            raise typer.Exit(1)

        metadata = await store.load_metadata(session_id)

        console.print(f"\n[bold cyan]Session: {session_id}[/bold cyan]\n")

        info_table = Table(show_header=False, box=None)
        info_table.add_column("Field", style="bold")
        info_table.add_column("Value")

        info_table.add_row("Channel", metadata.channel)
        info_table.add_row("Type", metadata.session_type)
        info_table.add_row("User ID", metadata.user_id)
        info_table.add_row("Created", metadata.created_at.strftime("%Y-%m-%d %H:%M:%S"))
        if metadata.updated_at:
            info_table.add_row("Last Updated", metadata.updated_at.strftime("%Y-%m-%d %H:%M:%S"))

        console.print(info_table)

        # Show recent messages
        messages = await store.load_messages(session_id, limit=limit)
        if messages:
            console.print(f"\n[bold]Recent Messages[/bold] ({len(messages)} shown):\n")
            for msg in messages:
                role_color = "green" if msg.role == "user" else "blue"
                content = msg.content
                content_preview = content[:100] + "..." if len(content) > 100 else content
                console.print(f"  [{role_color}]{msg.role}[/{role_color}]: {content_preview}")
        else:
            console.print("\n[dim]No messages in this session[/dim]")

    asyncio.run(_show())


@app.command("clear")
def clear_session(
    session_id: str = typer.Argument(..., help="Session ID to clear"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
) -> None:
    """Clear all messages from a session."""

    async def _clear() -> None:
        store = await _get_session_store()

        if not await store.session_exists(session_id):
            console.print(f"[red]Session not found: {session_id}[/red]")
            raise typer.Exit(1)

        if not force:
            confirm = typer.confirm(f"Clear all messages from session {session_id}?")
            if not confirm:
                console.print("[yellow]Cancelled[/yellow]")
                raise typer.Exit(0)

        await store.clear_messages(session_id)
        console.print(f"[green]Cleared session: {session_id}[/green]")

    asyncio.run(_clear())


@app.command("delete")
def delete_session(
    session_id: str = typer.Argument(..., help="Session ID to delete"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
) -> None:
    """Delete a session completely."""

    async def _delete() -> None:
        store = await _get_session_store()

        if not await store.session_exists(session_id):
            console.print(f"[red]Session not found: {session_id}[/red]")
            raise typer.Exit(1)

        if not force:
            confirm = typer.confirm(f"Delete session {session_id}? This cannot be undone.")
            if not confirm:
                console.print("[yellow]Cancelled[/yellow]")
                raise typer.Exit(0)

        result = await store.delete_session(session_id)
        if result:
            console.print(f"[green]Deleted session: {session_id}[/green]")
        else:
            console.print(f"[red]Failed to delete session: {session_id}[/red]")
            raise typer.Exit(1)

    asyncio.run(_delete())
