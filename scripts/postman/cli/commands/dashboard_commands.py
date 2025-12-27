"""Dashboard and reporting commands."""

import sys
from pathlib import Path
from typing import Optional
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
import json

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from cli.intelligence.reporting import EnhancedReporter
from cli.config import ConfigManager

app = typer.Typer(name="dashboard", help="Dashboard and reporting commands")
console = Console()


@app.command()
def show(
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Configuration profile"),
    days: int = typer.Option(7, "--days", "-d", help="Number of days for trend analysis")
):
    """Show dashboard from latest test results."""
    config_manager = ConfigManager()
    cli_profile = config_manager.get_profile(profile)
    
    reports_dir = Path(cli_profile.output_dir) if cli_profile.output_dir else Path(__file__).parent.parent.parent / "test_reports"
    latest_json = reports_dir / "test_results_latest.json"
    
    if not latest_json.exists():
        console.print("[yellow]No test results found. Run tests first.[/yellow]")
        raise typer.Exit(1)
    
    try:
        with open(latest_json, 'r') as f:
            results = json.load(f)
        
        enhanced_reporter = EnhancedReporter(reports_dir)
        dashboard = enhanced_reporter.generate_dashboard(results)
        
        # Display dashboard
        _display_dashboard(dashboard)
        
    except Exception as e:
        console.print(f"[red]Error loading dashboard: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def trends(
    days: int = typer.Option(7, "--days", "-d", help="Number of days to analyze"),
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Configuration profile")
):
    """Show trend analysis over time."""
    config_manager = ConfigManager()
    cli_profile = config_manager.get_profile(profile)
    
    reports_dir = Path(cli_profile.output_dir) if cli_profile.output_dir else Path(__file__).parent.parent.parent / "test_reports"
    enhanced_reporter = EnhancedReporter(reports_dir)
    
    trend_report = enhanced_reporter.generate_trend_report(days=days)
    
    if "message" in trend_report:
        console.print(f"[yellow]{trend_report['message']}[/yellow]")
        return
    
    console.print(Panel.fit(
        f"[bold cyan]Trend Analysis[/bold cyan]\n"
        f"Period: [yellow]{trend_report['period_days']} days[/yellow]\n"
        f"Reports: [yellow]{trend_report['report_count']}[/yellow]",
        border_style="cyan"
    ))
    
    # Display success rate trend
    if trend_report.get("success_rate_trend"):
        table = Table(title="Success Rate Trend", show_header=True)
        table.add_column("Date")
        table.add_column("Success Rate", justify="right")
        
        for trend in trend_report["success_rate_trend"][-10:]:  # Last 10
            date_str = trend["date"][:10] if len(trend["date"]) > 10 else trend["date"]
            rate = trend["success_rate"]
            color = "green" if rate >= 80 else "yellow" if rate >= 50 else "red"
            table.add_row(date_str, f"[{color}]{rate:.1f}%[/{color}]")
        
        console.print(table)


def _display_dashboard(dashboard: dict):
    """Display dashboard data."""
    overview = dashboard.get("overview", {})
    health = dashboard.get("health_score", {})
    performance = dashboard.get("performance_metrics", {})
    
    # Overview panel
    console.print(Panel.fit(
        f"[bold cyan]Test Overview[/bold cyan]\n"
        f"Total Tests: [yellow]{overview.get('total_tests', 0)}[/yellow]\n"
        f"Passed: [green]{overview.get('passed', 0)}[/green]\n"
        f"Failed: [red]{overview.get('failed', 0)}[/red]\n"
        f"Success Rate: [yellow]{overview.get('success_rate', 0):.1f}%[/yellow]\n"
        f"Duration: [yellow]{overview.get('duration_seconds', 0):.1f}s[/yellow]",
        border_style="cyan"
    ))
    
    # Health score
    if health:
        score = health.get("score", 0)
        status = health.get("status", "unknown")
        status_color = {
            "excellent": "green",
            "good": "cyan",
            "fair": "yellow",
            "poor": "red"
        }.get(status, "white")
        
        console.print(f"\n[bold {status_color}]Health Score: {score:.1f}% ({status})[/bold {status_color}]")
    
    # Performance metrics
    if performance:
        console.print("\n[bold]Performance Metrics:[/bold]")
        console.print(f"  Avg Response Time: {performance.get('avg_response_time_ms', 0):.1f}ms")
        console.print(f"  Median Response Time: {performance.get('median_response_time_ms', 0):.1f}ms")
        console.print(f"  P95 Response Time: {performance.get('p95_response_time_ms', 0):.1f}ms")
        
        slowest = performance.get("slowest_endpoints", [])
        if slowest:
            console.print("\n[bold]Slowest Endpoints:[/bold]")
            for endpoint_data in slowest[:5]:
                console.print(f"  • {endpoint_data['endpoint']}: {endpoint_data['avg_response_time_ms']:.1f}ms")

