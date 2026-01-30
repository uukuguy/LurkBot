"""Interactive chat CLI commands."""

import asyncio
import uuid
from typing import NoReturn

import typer
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt

from lurkbot.agents.base import AgentContext
from lurkbot.agents.runtime import AgentRuntime
from lurkbot.config import get_settings
from lurkbot.tools.base import SessionType

app = typer.Typer(help="Chat commands")
console = Console()


def _get_runtime() -> AgentRuntime:
    """Get configured agent runtime."""
    settings = get_settings()
    return AgentRuntime(settings)


@app.command("start")
def start_chat(
    model: str = typer.Option(None, "--model", "-m", help="Model to use for chat"),
    session_id: str = typer.Option(None, "--session", "-s", help="Resume existing session"),
    no_stream: bool = typer.Option(False, "--no-stream", help="Disable streaming output"),
) -> None:
    """Start an interactive chat session."""

    async def _chat() -> NoReturn:
        runtime = _get_runtime()
        settings = get_settings()

        # Determine session ID
        sid = session_id or f"cli-{uuid.uuid4().hex[:8]}"
        channel = "cli"

        # Determine model
        model_id = model or settings.agent.model

        # Get or create session
        try:
            await runtime.get_session(sid)
            console.print(f"[dim]Resuming session: {sid}[/dim]")
        except KeyError:
            await runtime.get_or_create_session(
                session_id=sid,
                channel=channel,
                session_type=SessionType.MAIN,
            )
            console.print(f"[dim]Created session: {sid}[/dim]")

        # Show welcome message
        console.print(
            Panel(
                f"[bold cyan]LurkBot Chat[/bold cyan]\n"
                f"Model: [green]{model_id}[/green]\n"
                f"Session: [dim]{sid}[/dim]\n\n"
                f"[dim]Type 'exit' or 'quit' to end the session[/dim]\n"
                f"[dim]Type '/help' for available commands[/dim]",
                title="Welcome",
                border_style="cyan",
            )
        )

        agent = runtime.get_agent(model_id)

        while True:
            try:
                # Get user input
                user_input = Prompt.ask("\n[bold green]You[/bold green]")

                if not user_input.strip():
                    continue

                # Handle special commands
                if user_input.lower() in ("exit", "quit", "/exit", "/quit"):
                    console.print("\n[dim]Goodbye![/dim]")
                    break

                if user_input.lower() == "/help":
                    _show_help()
                    continue

                if user_input.lower() == "/clear":
                    await runtime.clear_session(sid)
                    console.print("[yellow]Session cleared[/yellow]")
                    continue

                if user_input.lower() == "/history":
                    await _show_history(runtime, sid)
                    continue

                if user_input.lower().startswith("/model "):
                    new_model = user_input[7:].strip()
                    try:
                        agent = runtime.get_agent(new_model)
                        model_id = new_model
                        console.print(f"[green]Switched to model: {model_id}[/green]")
                    except Exception as e:
                        console.print(f"[red]Failed to switch model: {e}[/red]")
                    continue

                # Create context
                context = AgentContext(
                    session_id=sid,
                    channel=channel,
                    session_type=SessionType.MAIN,
                    user_id="cli-user",
                    workspace=str(settings.data_dir),
                )

                # Get response
                console.print("\n[bold blue]Assistant[/bold blue]")

                if no_stream:
                    # Non-streaming mode
                    response = await agent.chat(user_input, context)
                    console.print(Markdown(response))
                else:
                    # Streaming mode
                    full_response = ""
                    with Live(console=console, refresh_per_second=10) as live:
                        async for chunk in agent.chat_stream(user_input, context):
                            if chunk.text:
                                full_response += chunk.text
                                live.update(Markdown(full_response))

            except KeyboardInterrupt:
                console.print("\n[dim]Use 'exit' to quit[/dim]")
                continue
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")

    asyncio.run(_chat())


def _show_help() -> None:
    """Show help message."""
    console.print(
        Panel(
            "[bold]Available Commands:[/bold]\n\n"
            "  [cyan]/help[/cyan]     - Show this help message\n"
            "  [cyan]/clear[/cyan]    - Clear the current session\n"
            "  [cyan]/history[/cyan]  - Show conversation history\n"
            "  [cyan]/model <id>[/cyan] - Switch to a different model\n"
            "  [cyan]exit[/cyan]      - End the chat session",
            title="Help",
            border_style="blue",
        )
    )


async def _show_history(runtime: AgentRuntime, session_id: str) -> None:
    """Show conversation history."""
    messages = await runtime.get_messages(session_id)

    if not messages:
        console.print("[dim]No messages in this session[/dim]")
        return

    console.print(f"\n[bold]Conversation History[/bold] ({len(messages)} messages):\n")
    for msg in messages:
        role_color = "green" if msg.role == "user" else "blue"
        role_name = "You" if msg.role == "user" else "Assistant"
        console.print(f"[bold {role_color}]{role_name}[/bold {role_color}]")

        content = msg.content
        if len(content) > 500:
            content = content[:500] + "..."
        console.print(Markdown(content))
        console.print()


@app.command("send")
def send_message(
    message: str = typer.Argument(..., help="Message to send"),
    model: str = typer.Option(None, "--model", "-m", help="Model to use"),
    session_id: str = typer.Option(None, "--session", "-s", help="Session ID"),
) -> None:
    """Send a single message and get a response."""

    async def _send() -> None:
        runtime = _get_runtime()
        settings = get_settings()

        # Determine session ID
        sid = session_id or f"cli-oneshot-{uuid.uuid4().hex[:8]}"
        channel = "cli"

        # Determine model
        model_id = model or settings.agent.model

        # Get or create session
        await runtime.get_or_create_session(
            session_id=sid,
            channel=channel,
            session_type=SessionType.MAIN,
        )

        # Create context
        context = AgentContext(
            session_id=sid,
            channel=channel,
            session_type=SessionType.MAIN,
            user_id="cli-user",
            workspace=str(settings.data_dir),
        )

        agent = runtime.get_agent(model_id)

        console.print(f"[dim]Using model: {model_id}[/dim]\n")

        # Get response
        response = await agent.chat(message, context)
        console.print(Markdown(response))

    asyncio.run(_send())
