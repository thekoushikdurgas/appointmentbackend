#!/usr/bin/env python3
"""AI Agentic CLI for Contact360 API Testing."""

import sys
from pathlib import Path
import typer
from rich.console import Console
from rich.panel import Panel

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Import command modules
from cli.commands import test_commands
from cli.commands import discover_commands
from cli.commands import monitor_commands
from cli.commands import collection_commands
from cli.commands import interactive_commands
from cli.commands import config_commands
from cli.commands import dashboard_commands
from cli.commands import ai_commands

# Create main app
app = typer.Typer(
    name="contact360-cli",
    help="AI Agentic CLI for Contact360 API Testing",
    add_completion=False
)

# Add command groups
app.add_typer(test_commands.app, name="test")
app.add_typer(discover_commands.app, name="discover")
app.add_typer(monitor_commands.app, name="monitor")
app.add_typer(collection_commands.app, name="collection")
app.add_typer(interactive_commands.app, name="interactive")
app.add_typer(config_commands.app, name="config")
app.add_typer(dashboard_commands.app, name="dashboard")
app.add_typer(ai_commands.app, name="ai")

console = Console()


@app.command()
def version():
    """Show CLI version."""
    from cli import __version__
    console.print(f"Contact360 CLI v{__version__}")


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """Contact360 API Testing CLI - AI-powered automation for API testing."""
    if ctx.invoked_subcommand is None:
        console.print(Panel.fit(
            "[bold cyan]Contact360 API Testing CLI[/bold cyan]\n\n"
            "AI-powered automation for API testing, monitoring, and management.\n\n"
            "[yellow]Available Commands:[/yellow]\n"
            "  test          - Run API tests\n"
            "  discover      - Discover and sync endpoints\n"
            "  monitor       - Continuous monitoring\n"
            "  collection    - Postman collection management\n"
            "  interactive   - Interactive REPL mode\n"
            "  config        - Configuration management\n"
            "  dashboard     - View dashboards and trends\n"
            "  ai            - AI agentic features (learn, analyze, optimize)\n\n"
            "Use '[cyan]python main.py <command> --help[/cyan]' for more information.\n"
            "Example: [cyan]python main.py test run[/cyan]",
            border_style="cyan"
        ))
        raise typer.Exit()


if __name__ == "__main__":
    app()

