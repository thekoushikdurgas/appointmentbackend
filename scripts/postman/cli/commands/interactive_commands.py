"""Interactive REPL mode for manual testing."""

import sys
from pathlib import Path
from typing import Optional
import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
import requests

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from cli.config import ConfigManager

app = typer.Typer(name="interactive", help="Interactive REPL mode")
console = Console()


@app.command()
def repl(
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Configuration profile")
):
    """Start interactive REPL for manual API testing."""
    config_manager = ConfigManager()
    cli_profile = config_manager.get_profile(profile)
    
    console.print(Panel.fit(
        "[bold cyan]Contact360 API Interactive REPL[/bold cyan]\n"
        f"Base URL: [yellow]{cli_profile.base_url}[/yellow]\n"
        "Type 'help' for commands, 'exit' to quit",
        border_style="cyan"
    ))
    
    # Initialize session
    session = requests.Session()
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Origin": "localhost:3000"
    }
    
    # Add auth if available
    if cli_profile.access_token:
        headers["Authorization"] = f"Bearer {cli_profile.access_token}"
    
    while True:
        try:
            command = Prompt.ask("\n[cyan]api>[/cyan]").strip()
            
            if not command:
                continue
            
            if command.lower() == "exit" or command.lower() == "quit":
                console.print("[yellow]Goodbye![/yellow]")
                break
            
            if command.lower() == "help":
                _show_help()
                continue
            
            if command.lower().startswith("get "):
                _handle_get(command, cli_profile.base_url, session, headers)
            elif command.lower().startswith("post "):
                _handle_post(command, cli_profile.base_url, session, headers)
            elif command.lower().startswith("put "):
                _handle_put(command, cli_profile.base_url, session, headers)
            elif command.lower().startswith("delete "):
                _handle_delete(command, cli_profile.base_url, session, headers)
            elif command.lower() == "auth":
                _handle_auth(cli_profile, headers)
            elif command.lower() == "headers":
                _show_headers(headers)
            else:
                console.print(f"[red]Unknown command: {command}[/red]")
                console.print("Type 'help' for available commands")
        
        except KeyboardInterrupt:
            console.print("\n[yellow]Interrupted. Type 'exit' to quit.[/yellow]")
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")


def _show_help():
    """Show help message."""
    help_text = """
Available Commands:
  get <endpoint>              - GET request (e.g., get /api/v1/users/)
  post <endpoint> [json]      - POST request with optional JSON body
  put <endpoint> [json]       - PUT request with optional JSON body
  delete <endpoint>            - DELETE request
  auth                        - Authenticate and get token
  headers                     - Show current headers
  help                        - Show this help
  exit                        - Exit REPL
"""
    console.print(help_text)


def _handle_get(command: str, base_url: str, session: requests.Session, headers: dict):
    """Handle GET request."""
    parts = command.split(" ", 1)
    if len(parts) < 2:
        console.print("[red]Usage: get <endpoint>[/red]")
        return
    
    endpoint = parts[1].strip()
    # Normalize base_url (remove trailing slash) and ensure endpoint starts with /
    base_url = base_url.rstrip('/')
    if not endpoint.startswith('/'):
        endpoint = '/' + endpoint
    url = f"{base_url}{endpoint}"
    
    try:
        response = session.get(url, headers=headers, timeout=30)
        _display_response(response)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


def _handle_post(command: str, base_url: str, session: requests.Session, headers: dict):
    """Handle POST request."""
    parts = command.split(" ", 1)
    if len(parts) < 2:
        console.print("[red]Usage: post <endpoint> [json_body][/red]")
        return
    
    endpoint = parts[1].strip()
    # Normalize base_url (remove trailing slash)
    base_url = base_url.rstrip('/')
    
    # Try to parse JSON body if provided
    json_data = None
    if "{" in endpoint:
        # Extract JSON from command
        json_start = endpoint.find("{")
        endpoint_path = endpoint[:json_start].strip()
        json_str = endpoint[json_start:].strip()
        if not endpoint_path.startswith('/'):
            endpoint_path = '/' + endpoint_path
        url = f"{base_url}{endpoint_path}"
    else:
        if not endpoint.startswith('/'):
            endpoint = '/' + endpoint
        url = f"{base_url}{endpoint}"
        
        try:
            import json
            json_data = json.loads(json_str)
        except:
            console.print("[yellow]Warning: Could not parse JSON, sending as-is[/yellow]")
    
    try:
        response = session.post(url, headers=headers, json=json_data, timeout=30)
        _display_response(response)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


def _handle_put(command: str, base_url: str, session: requests.Session, headers: dict):
    """Handle PUT request."""
    parts = command.split(" ", 1)
    if len(parts) < 2:
        console.print("[red]Usage: put <endpoint> [json_body][/red]")
        return
    
    endpoint = parts[1].strip()
    # Normalize base_url (remove trailing slash)
    base_url = base_url.rstrip('/')
    
    # Similar JSON parsing as POST
    json_data = None
    if "{" in endpoint:
        json_start = endpoint.find("{")
        endpoint_path = endpoint[:json_start].strip()
        json_str = endpoint[json_start:].strip()
        if not endpoint_path.startswith('/'):
            endpoint_path = '/' + endpoint_path
        url = f"{base_url}{endpoint_path}"
    else:
        if not endpoint.startswith('/'):
            endpoint = '/' + endpoint
        url = f"{base_url}{endpoint}"
        
        try:
            import json
            json_data = json.loads(json_str)
        except:
            pass
    
    try:
        response = session.put(url, headers=headers, json=json_data, timeout=30)
        _display_response(response)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


def _handle_delete(command: str, base_url: str, session: requests.Session, headers: dict):
    """Handle DELETE request."""
    parts = command.split(" ", 1)
    if len(parts) < 2:
        console.print("[red]Usage: delete <endpoint>[/red]")
        return
    
    endpoint = parts[1].strip()
    # Normalize base_url (remove trailing slash) and ensure endpoint starts with /
    base_url = base_url.rstrip('/')
    if not endpoint.startswith('/'):
        endpoint = '/' + endpoint
    url = f"{base_url}{endpoint}"
    
    try:
        response = session.delete(url, headers=headers, timeout=30)
        _display_response(response)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


def _handle_auth(profile, headers: dict):
    """Handle authentication."""
    if not profile.email or not profile.password:
        console.print("[red]Email and password not configured[/red]")
        return
    
    try:
        import requests
        # Normalize base_url (remove trailing slash if present)
        base_url = profile.base_url.rstrip('/')
        url = f"{base_url}/api/v1/auth/login/"
        payload = {
            "email": profile.email,
            "password": profile.password,
            "geolocation": None
        }
        
        response = requests.post(url, json=payload, timeout=30)
        if response.status_code == 200:
            data = response.json()
            token = data.get("access_token")
            if token:
                headers["Authorization"] = f"Bearer {token}"
                console.print("[green]✓[/green] Authentication successful")
            else:
                console.print("[red]No access token in response[/red]")
        else:
            console.print(f"[red]Authentication failed: {response.status_code}[/red]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


def _show_headers(headers: dict):
    """Show current headers."""
    console.print("\n[bold]Current Headers:[/bold]")
    for key, value in headers.items():
        if "token" in key.lower() or "key" in key.lower():
            console.print(f"  {key}: ***")
        else:
            console.print(f"  {key}: {value}")


def _display_response(response: requests.Response):
    """Display HTTP response."""
    status_color = "green" if 200 <= response.status_code < 300 else "yellow" if 300 <= response.status_code < 400 else "red"
    console.print(f"\n[bold {status_color}]Status: {response.status_code}[/bold {status_color}]")
    
    # Try to parse JSON
    try:
        data = response.json()
        import json
        console.print(f"[cyan]Response:[/cyan]\n{json.dumps(data, indent=2)}")
    except:
        console.print(f"[cyan]Response:[/cyan]\n{response.text[:500]}")

