"""Endpoint discovery commands."""

import sys
from pathlib import Path
from typing import Optional
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
import csv

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

app = typer.Typer(name="discover", help="Endpoint discovery commands")
console = Console()


@app.command()
def scan(
    base_url: str = typer.Option("http://34.229.94.175/", "--base-url", help="API base URL"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output CSV file path")
):
    """Scan API for available endpoints (placeholder - would need OpenAPI spec or similar)."""
    console.print("[yellow]Endpoint scanning requires OpenAPI specification or API introspection[/yellow]")
    console.print("[yellow]This feature is a placeholder for future implementation[/yellow]")
    
    # In a real implementation, this would:
    # 1. Fetch OpenAPI spec from /docs or /openapi.json
    # 2. Parse endpoints from the spec
    # 3. Generate CSV format
    # 4. Save to output file


@app.command()
def sync_csv(
    csv_file: str = typer.Argument(..., help="CSV file path to sync"),
    base_url: str = typer.Option("http://34.229.94.175", "--base-url", help="API base URL")
):
    """Sync CSV file with current API state."""
    csv_path = Path(csv_file)
    
    if not csv_path.exists():
        console.print(f"[red]CSV file not found: {csv_path}[/red]")
        raise typer.Exit(1)
    
    # Load existing endpoints
    endpoints = []
    try:
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            endpoints = list(reader)
    except Exception as e:
        console.print(f"[red]Error reading CSV: {e}[/red]")
        raise typer.Exit(1)
    
    console.print(f"[green]Loaded {len(endpoints)} endpoints from CSV[/green]")
    
    # In a real implementation, this would:
    # 1. Check each endpoint against the API
    # 2. Update status codes, response times, etc.
    # 3. Add new endpoints if discovered
    # 4. Mark deprecated endpoints
    
    console.print("[yellow]CSV sync is a placeholder - would verify endpoints against API[/yellow]")


@app.command()
def generate_docs(
    csv_file: Optional[str] = typer.Option(None, "--csv", help="CSV file path"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output directory"),
    format: str = typer.Option("markdown", "--format", help="Documentation format: markdown, html, or json")
):
    """Generate API documentation from CSV."""
    csv_directory = Path(__file__).parent.parent.parent / "csv"
    
    if csv_file:
        csv_files = [Path(csv_file)]
    else:
        csv_files = list(csv_directory.glob("*.csv"))
    
    if not csv_files:
        console.print("[red]No CSV files found[/red]")
        raise typer.Exit(1)
    
    output_dir = Path(output) if output else Path(__file__).parent.parent.parent / "docs"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    all_endpoints = []
    for csv_path in csv_files:
        try:
            with open(csv_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get('endpoint'):
                        all_endpoints.append(row)
        except Exception as e:
            console.print(f"[yellow]Warning: Could not read {csv_path}: {e}[/yellow]")
    
    if format == "markdown":
        _generate_markdown_docs(all_endpoints, output_dir)
    elif format == "html":
        _generate_html_docs(all_endpoints, output_dir)
    elif format == "json":
        _generate_json_docs(all_endpoints, output_dir)
    
    console.print(f"[green]✓[/green] Documentation generated in {output_dir}")


def _generate_markdown_docs(endpoints, output_dir: Path):
    """Generate Markdown documentation."""
    output_file = output_dir / "api_documentation.md"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# API Documentation\n\n")
        f.write(f"Generated from {len(endpoints)} endpoints\n\n")
        
        # Group by category
        categories = {}
        for endpoint in endpoints:
            category = endpoint.get('category', 'Other')
            if category not in categories:
                categories[category] = []
            categories[category].append(endpoint)
        
        for category, category_endpoints in sorted(categories.items()):
            f.write(f"## {category}\n\n")
            
            for endpoint in category_endpoints:
                method = endpoint.get('method', 'GET')
                path = endpoint.get('endpoint', '')
                description = endpoint.get('description', '')
                
                f.write(f"### {method} {path}\n\n")
                if description:
                    f.write(f"{description}\n\n")
                
                f.write(f"- **Requires Auth**: {endpoint.get('requires_auth', 'FALSE')}\n")
                f.write(f"- **Requires Admin**: {endpoint.get('requires_admin', 'FALSE')}\n")
                f.write(f"- **API Version**: {endpoint.get('api_version', 'v1')}\n\n")


def _generate_html_docs(endpoints, output_dir: Path):
    """Generate HTML documentation."""
    output_file = output_dir / "api_documentation.html"
    
    html = """<!DOCTYPE html>
<html>
<head>
    <title>API Documentation</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        h1 { color: #333; }
        h2 { color: #666; border-bottom: 2px solid #eee; padding-bottom: 10px; }
        h3 { color: #888; }
        .endpoint { margin: 20px 0; padding: 15px; background: #f9f9f9; border-radius: 5px; }
        .method { display: inline-block; padding: 5px 10px; border-radius: 3px; font-weight: bold; }
        .GET { background: #61affe; color: white; }
        .POST { background: #49cc90; color: white; }
        .PUT { background: #fca130; color: white; }
        .DELETE { background: #f93e3e; color: white; }
    </style>
</head>
<body>
    <h1>API Documentation</h1>
    <p>Generated from {count} endpoints</p>
"""
    
    # Group by category
    categories = {}
    for endpoint in endpoints:
        category = endpoint.get('category', 'Other')
        if category not in categories:
            categories[category] = []
        categories[category].append(endpoint)
    
    for category, category_endpoints in sorted(categories.items()):
        html += f"<h2>{category}</h2>\n"
        
        for endpoint in category_endpoints:
            method = endpoint.get('method', 'GET')
            path = endpoint.get('endpoint', '')
            description = endpoint.get('description', '')
            
            html += f"""
            <div class="endpoint">
                <h3><span class="method {method}">{method}</span> {path}</h3>
                <p>{description}</p>
                <ul>
                    <li><strong>Requires Auth:</strong> {endpoint.get('requires_auth', 'FALSE')}</li>
                    <li><strong>Requires Admin:</strong> {endpoint.get('requires_admin', 'FALSE')}</li>
                    <li><strong>API Version:</strong> {endpoint.get('api_version', 'v1')}</li>
                </ul>
            </div>
            """
    
    html += "</body></html>"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html.format(count=len(endpoints)))


def _generate_json_docs(endpoints, output_dir: Path):
    """Generate JSON documentation."""
    import json
    output_file = output_dir / "api_documentation.json"
    
    docs = {
        "version": "1.0",
        "endpoint_count": len(endpoints),
        "endpoints": endpoints
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(docs, f, indent=2, ensure_ascii=False)

