"""Postman collection management commands."""

import sys
from pathlib import Path
from typing import Optional
import typer
from rich.console import Console
from rich.panel import Panel

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

app = typer.Typer(name="collection", help="Postman collection commands")
console = Console()


@app.command()
def generate(
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file path"),
    csv_file: Optional[str] = typer.Option(None, "--csv", help="CSV file path")
):
    """Generate Postman collection from CSV."""
    # Import the existing collection generator
    try:
        from generate_collection import main as generate_main
        import sys as sys_module
        
        # Set up arguments for the generator
        if csv_file:
            sys_module.argv = ["generate_collection.py", "--csv", csv_file]
        if output:
            if "--output" not in sys_module.argv:
                sys_module.argv.extend(["--output", output])
        
        generate_main()
        console.print("[green]✓[/green] Collection generated successfully")
    except ImportError:
        console.print("[red]Collection generator not available[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error generating collection: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def update(
    collection_file: str = typer.Argument(..., help="Postman collection JSON file path"),
    csv_file: Optional[str] = typer.Option(None, "--csv", help="CSV file path to sync from")
):
    """Update existing Postman collection."""
    collection_path = Path(collection_file)
    
    if not collection_path.exists():
        console.print(f"[red]Collection file not found: {collection_path}[/red]")
        raise typer.Exit(1)
    
    console.print(f"[cyan]Updating collection: {collection_path}[/cyan]")
    console.print("[yellow]Collection update is a placeholder - would merge CSV changes into collection[/yellow]")


@app.command()
def export(
    collection_file: str = typer.Argument(..., help="Postman collection JSON file path"),
    format: str = typer.Option("csv", "--format", help="Export format: csv, openapi, or markdown"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file path")
):
    """Export Postman collection to different formats."""
    collection_path = Path(collection_file)
    
    if not collection_path.exists():
        console.print(f"[red]Collection file not found: {collection_path}[/red]")
        raise typer.Exit(1)
    
    console.print(f"[cyan]Exporting collection to {format} format[/cyan]")
    console.print("[yellow]Collection export is a placeholder - would convert collection to requested format[/yellow]")


@app.command()
def import_cmd(
    file_path: str = typer.Argument(..., help="File to import (CSV, OpenAPI, etc.)"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output collection file path")
):
    """Import endpoints from various formats into Postman collection."""
    file_path_obj = Path(file_path)
    
    if not file_path_obj.exists():
        console.print(f"[red]File not found: {file_path_obj}[/red]")
        raise typer.Exit(1)
    
    console.print(f"[cyan]Importing from: {file_path_obj}[/cyan]")
    console.print("[yellow]Collection import is a placeholder - would parse file and create collection[/yellow]")

