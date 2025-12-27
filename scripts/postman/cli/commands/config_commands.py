"""Configuration management commands."""

import sys
from pathlib import Path
from typing import Optional
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from cli.config import ConfigManager, CLIProfile

app = typer.Typer(name="config", help="Configuration management")
console = Console()


@app.command()
def show(
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile name")
):
    """Show current configuration."""
    config_manager = ConfigManager()
    
    if profile:
        try:
            cli_profile = config_manager.get_profile(profile)
            _display_profile(cli_profile)
        except ValueError as e:
            console.print(f"[red]{e}[/red]")
    else:
        # Show all profiles
        profiles = config_manager.list_profiles()
        default_profile = config_manager.config.default_profile
        
        table = Table(title="Configuration Profiles", show_header=True)
        table.add_column("Name")
        table.add_column("Base URL")
        table.add_column("Email")
        table.add_column("Default")
        
        for name, prof in profiles.items():
            is_default = "✓" if name == default_profile else ""
            table.add_row(
                name,
                prof.base_url,
                prof.email or "-",
                is_default
            )
        
        console.print(table)


@app.command()
def set_default(
    profile: str = typer.Argument(..., help="Profile name to set as default")
):
    """Set default profile."""
    config_manager = ConfigManager()
    
    try:
        config_manager.set_default_profile(profile)
        console.print(f"[green]✓[/green] Default profile set to: {profile}")
    except ValueError as e:
        console.print(f"[red]{e}[/red]")


@app.command()
def add(
    name: str = typer.Argument(..., help="Profile name"),
    base_url: str = typer.Option(..., "--base-url", help="API base URL"),
    email: Optional[str] = typer.Option(None, "--email", help="Login email"),
    password: Optional[str] = typer.Option(None, "--password", help="Login password"),
    access_token: Optional[str] = typer.Option(None, "--access-token", help="Access token"),
    refresh_token: Optional[str] = typer.Option(None, "--refresh-token", help="Refresh token"),
    admin_email: Optional[str] = typer.Option(None, "--admin-email", help="Admin email"),
    admin_password: Optional[str] = typer.Option(None, "--admin-password", help="Admin password")
):
    """Add a new configuration profile."""
    config_manager = ConfigManager()
    
    profile = CLIProfile(
        name=name,
        base_url=base_url,
        email=email,
        password=password,
        access_token=access_token,
        refresh_token=refresh_token,
        admin_email=admin_email,
        admin_password=admin_password
    )
    
    config_manager.add_profile(profile)
    console.print(f"[green]✓[/green] Profile '{name}' added")


@app.command()
def remove(
    name: str = typer.Argument(..., help="Profile name to remove")
):
    """Remove a configuration profile."""
    config_manager = ConfigManager()
    
    try:
        config_manager.remove_profile(name)
        console.print(f"[green]✓[/green] Profile '{name}' removed")
    except ValueError as e:
        console.print(f"[red]{e}[/red]")


def _display_profile(profile: CLIProfile):
    """Display a profile's details."""
    console.print(Panel.fit(
        f"[bold cyan]Profile: {profile.name}[/bold cyan]\n"
        f"Base URL: [yellow]{profile.base_url}[/yellow]\n"
        f"Email: [yellow]{profile.email or 'Not set'}[/yellow]\n"
        f"Test Mode: [yellow]{profile.test_mode}[/yellow]\n"
        f"Timeout: [yellow]{profile.timeout}s[/yellow]",
        border_style="cyan"
    ))

