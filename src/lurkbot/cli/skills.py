"""Skills CLI commands for ClawHub integration."""

import asyncio
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from lurkbot.skills.clawhub import ClawHubClient
from lurkbot.skills.registry import get_skill_manager
from lurkbot.skills.workspace import SkillSource

app = typer.Typer(
    name="skills",
    help="Manage skills from ClawHub and local sources",
    no_args_is_help=True,
)

console = Console()


@app.command()
def search(
    query: str = typer.Argument(..., help="Search query"),
    limit: int = typer.Option(20, "--limit", "-l", help="Maximum results"),
    tags: list[str] | None = typer.Option(None, "--tag", "-t", help="Filter by tags"),
) -> None:
    """Search for skills on ClawHub.

    Examples:
        lurkbot skills search weather
        lurkbot skills search "github" --tag productivity
        lurkbot skills search notion --limit 10
    """
    console.print(f"[bold]Searching ClawHub for:[/bold] {query}")

    async def _search() -> None:
        async with ClawHubClient() as client:
            skills = await client.search(query, limit=limit, tags=tags or [])

            if not skills:
                console.print("[yellow]No skills found[/yellow]")
                return

            # Create results table
            table = Table(title=f"Found {len(skills)} skills")
            table.add_column("Slug", style="cyan")
            table.add_column("Description", style="white")
            table.add_column("Version", style="green")
            table.add_column("Downloads", style="magenta", justify="right")

            for skill in skills:
                table.add_row(
                    skill.slug,
                    skill.description[:60] + ("..." if len(skill.description) > 60 else ""),
                    skill.version,
                    str(skill.downloads),
                )

            console.print(table)

    asyncio.run(_search())


@app.command()
def info(
    slug: str = typer.Argument(..., help="Skill slug (e.g., 'openclaw/weather')"),
) -> None:
    """Get detailed information about a skill.

    Examples:
        lurkbot skills info openclaw/weather
        lurkbot skills info openclaw/github
    """
    console.print(f"[bold]Fetching info for:[/bold] {slug}")

    async def _info() -> None:
        async with ClawHubClient() as client:
            skill = await client.info(slug)

            # Display skill info
            console.print("\n[bold cyan]Skill Information[/bold cyan]")
            console.print(f"[bold]Name:[/bold] {skill.name}")
            console.print(f"[bold]Slug:[/bold] {skill.slug}")
            console.print(f"[bold]Version:[/bold] {skill.version}")
            console.print(f"[bold]Author:[/bold] {skill.author}")
            console.print(f"[bold]Description:[/bold] {skill.description}")
            console.print(f"[bold]Downloads:[/bold] {skill.downloads}")
            if skill.rating:
                console.print(f"[bold]Rating:[/bold] {skill.rating:.1f}/5.0")
            if skill.tags:
                console.print(f"[bold]Tags:[/bold] {', '.join(skill.tags)}")
            if skill.license:
                console.print(f"[bold]License:[/bold] {skill.license}")
            if skill.homepage:
                console.print(f"[bold]Homepage:[/bold] {skill.homepage}")
            if skill.repository:
                console.print(f"[bold]Repository:[/bold] {skill.repository}")

            # Get versions
            versions = await client.list_versions(slug)
            if versions:
                console.print(f"\n[bold]Available versions:[/bold] {len(versions)}")
                for v in versions[:5]:  # Show latest 5 versions
                    console.print(f"  • {v.version} ({v.released_at})")

    asyncio.run(_info())


@app.command()
def install(
    slug: str = typer.Argument(..., help="Skill slug (e.g., 'openclaw/weather')"),
    version: str | None = typer.Option(None, "--version", "-v", help="Specific version"),
    workspace: str | None = typer.Option(None, "--workspace", "-w", help="Workspace directory"),
    force: bool = typer.Option(False, "--force", "-f", help="Force reinstall"),
) -> None:
    """Install a skill from ClawHub.

    Examples:
        lurkbot skills install openclaw/weather
        lurkbot skills install openclaw/github --version 1.2.0
        lurkbot skills install openclaw/notion --force
    """
    workspace_path = Path(workspace) if workspace else Path.cwd()
    version_str = f"@{version}" if version else ""
    console.print(f"[bold]Installing:[/bold] {slug}{version_str}")

    async def _install() -> None:
        skill_manager = get_skill_manager()

        # Load existing skills
        if not len(skill_manager.registry):
            skill_manager.load_skills(workspace_root=workspace_path)

        try:
            skill_entry = await skill_manager.install_from_clawhub(
                slug=slug,
                version=version,
                workspace_root=workspace_path,
                force=force,
            )

            console.print(f"\n[green]✓ Successfully installed:[/green] {skill_entry.key}")
            console.print(f"[dim]Location:[/dim] {skill_entry.file_path}")

        except ValueError as e:
            console.print(f"[red]✗ Installation failed:[/red] {e}")
            raise typer.Exit(code=1)
        except Exception as e:
            console.print(f"[red]✗ Unexpected error:[/red] {e}")
            raise typer.Exit(code=1)

    asyncio.run(_install())


@app.command()
def list(
    source: str | None = typer.Option(
        None, "--source", "-s", help="Filter by source (workspace/managed/bundled/extra)"
    ),
    workspace: str | None = typer.Option(None, "--workspace", "-w", help="Workspace directory"),
) -> None:
    """List installed skills.

    Examples:
        lurkbot skills list
        lurkbot skills list --source managed
        lurkbot skills list --source bundled
    """
    workspace_path = Path(workspace) if workspace else Path.cwd()

    skill_manager = get_skill_manager()
    skill_manager.load_skills(workspace_root=workspace_path)

    skills = skill_manager.list_skills()

    if source:
        try:
            source_filter = SkillSource(source)
            skills = [s for s in skills if s.source == source_filter]
        except ValueError:
            console.print(
                f"[red]Invalid source:[/red] {source}. "
                f"Valid options: workspace, managed, bundled, extra"
            )
            raise typer.Exit(code=1)

    if not skills:
        console.print("[yellow]No skills installed[/yellow]")
        return

    # Create table
    table = Table(title=f"Installed Skills ({len(skills)})")
    table.add_column("Key", style="cyan")
    table.add_column("Source", style="magenta")
    table.add_column("Version", style="green")
    table.add_column("User Invocable", style="yellow", justify="center")
    table.add_column("Tools", style="white")

    for skill in skills:
        tools_str = ", ".join(skill.frontmatter.tools) if skill.frontmatter.tools else "—"
        if len(tools_str) > 40:
            tools_str = tools_str[:37] + "..."

        table.add_row(
            skill.key,
            skill.source.value,
            skill.frontmatter.version or "—",
            "✅" if skill.frontmatter.user_invocable else "❌",
            tools_str,
        )

    console.print(table)


@app.command()
def update(
    workspace: str | None = typer.Option(None, "--workspace", "-w", help="Workspace directory"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Check for updates without installing"),
) -> None:
    """Check for and install skill updates from ClawHub.

    Examples:
        lurkbot skills update --dry-run
        lurkbot skills update
    """
    workspace_path = Path(workspace) if workspace else Path.cwd()

    async def _update() -> None:
        skill_manager = get_skill_manager()
        skill_manager.load_skills(workspace_root=workspace_path)

        console.print("[bold]Checking for updates...[/bold]")

        try:
            updates = await skill_manager.check_updates()

            if not updates:
                console.print("[green]All skills are up to date[/green]")
                return

            # Display available updates
            table = Table(title=f"Available Updates ({len(updates)})")
            table.add_column("Skill", style="cyan")
            table.add_column("Current", style="yellow")
            table.add_column("Latest", style="green")

            for skill_key, current_ver, latest_ver in updates:
                table.add_row(skill_key, current_ver, latest_ver)

            console.print(table)

            if dry_run:
                console.print("\n[dim]Run without --dry-run to install updates[/dim]")
                return

            # TODO: Implement actual update installation
            console.print("\n[yellow]Update installation not yet implemented[/yellow]")

        except Exception as e:
            console.print(f"[red]✗ Update check failed:[/red] {e}")
            raise typer.Exit(code=1)

    asyncio.run(_update())


@app.command()
def remove(
    key: str = typer.Argument(..., help="Skill key to remove"),
    workspace: str | None = typer.Option(None, "--workspace", "-w", help="Workspace directory"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
) -> None:
    """Remove an installed skill.

    Examples:
        lurkbot skills remove weather
        lurkbot skills remove github --force
    """
    workspace_path = Path(workspace) if workspace else Path.cwd()

    skill_manager = get_skill_manager()
    skill_manager.load_skills(workspace_root=workspace_path)

    skill = skill_manager.get_skill(key)
    if not skill:
        console.print(f"[red]✗ Skill not found:[/red] {key}")
        raise typer.Exit(code=1)

    if not force:
        confirm = typer.confirm(f"Remove skill '{key}' ({skill.source.value})?")
        if not confirm:
            console.print("[yellow]Cancelled[/yellow]")
            return

    # Remove skill file/directory
    if skill.file_path.name == "SKILL.md":
        # Remove parent directory
        import shutil

        shutil.rmtree(skill.file_path.parent)
        console.print(f"[green]✓ Removed directory:[/green] {skill.file_path.parent}")
    else:
        # Remove file
        skill.file_path.unlink()
        console.print(f"[green]✓ Removed file:[/green] {skill.file_path}")

    # Unregister from manager
    skill_manager.registry.unregister(key)
    console.print(f"[green]✓ Skill removed:[/green] {key}")
