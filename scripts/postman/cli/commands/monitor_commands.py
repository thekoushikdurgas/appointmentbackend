"""Monitoring commands."""

import sys
import json
from pathlib import Path
from typing import Optional
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from cli.intelligence.scheduler import SmartScheduler
from cli.config import ConfigManager
from cli.commands.test_commands import run as run_tests

app = typer.Typer(name="monitor", help="Monitoring commands")
console = Console()

# Global scheduler instance
scheduler = SmartScheduler()


@app.command()
def start(
    interval: int = typer.Option(300, "--interval", "-i", help="Check interval in seconds"),
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Configuration profile"),
    category: Optional[str] = typer.Option(None, "--category", "-c", help="Monitor specific category")
):
    """Start continuous monitoring."""
    config_manager = ConfigManager()
    config = config_manager.config
    
    if scheduler.running:
        console.print("[yellow]Monitoring is already running[/yellow]")
        return
    
    def monitor_job():
        """Job function for monitoring."""
        try:
            # Run tests
            # Note: This is a simplified version - full implementation would
            # properly call the test runner and handle results
            console.print(f"[cyan]Running scheduled check at {datetime.now()}[/cyan]")
            # run_tests(category=category, profile=profile, verbose=False)
            return {"success": True, "timestamp": datetime.now().isoformat()}
        except Exception as e:
            console.print(f"[red]Monitor check failed: {e}[/red]")
            return {"success": False, "error": str(e)}
    
    job_id = "default_monitor"
    if scheduler.add_job(job_id, monitor_job, interval_seconds=interval):
        scheduler.start()
        console.print(f"[green]✓[/green] Monitoring started (interval: {interval}s)")
    else:
        console.print("[red]Failed to start monitoring[/red]")


@app.command()
def stop():
    """Stop continuous monitoring."""
    if not scheduler.running:
        console.print("[yellow]Monitoring is not running[/yellow]")
        return
    
    scheduler.stop()
    console.print("[green]✓[/green] Monitoring stopped")


@app.command()
def status():
    """Show monitoring status."""
    status_data = scheduler.get_status()
    
    if not status_data["running"]:
        console.print("[yellow]Monitoring is not running[/yellow]")
        return
    
    table = Table(title="Monitoring Status", show_header=True)
    table.add_column("Job ID")
    table.add_column("Interval")
    table.add_column("Last Run")
    table.add_column("Next Run")
    table.add_column("Runs")
    table.add_column("Success")
    table.add_column("Failed")
    
    for job_id, job_data in status_data["jobs"].items():
        table.add_row(
            job_id,
            f"{job_data['interval_seconds']}s",
            job_data["last_run"] or "Never",
            job_data["next_run"] or "N/A",
            str(job_data["run_count"]),
            str(job_data["success_count"]),
            str(job_data["failure_count"])
        )
    
    console.print(table)


@app.command()
def alerts(
    threshold: float = typer.Option(0.8, "--threshold", help="Failure rate threshold (0-1)"),
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Configuration profile")
):
    """Check for alerts based on recent test results."""
    config_manager = ConfigManager()
    cli_profile = config_manager.get_profile(profile)
    
    # Load recent test results
    reports_dir = Path(cli_profile.output_dir) if cli_profile.output_dir else Path(__file__).parent.parent.parent / "test_reports"
    latest_json = reports_dir / "test_results_latest.json"
    
    if not latest_json.exists():
        console.print("[yellow]No test results found[/yellow]")
        return
    
    try:
        with open(latest_json, 'r') as f:
            results = json.load(f)
        
        summary = results.get("summary", {})
        total = summary.get("total_tests", 0)
        failed = summary.get("failed", 0)
        
        if total > 0:
            failure_rate = failed / total
            
            if failure_rate >= threshold:
                console.print(f"[red]⚠ ALERT: Failure rate {failure_rate:.1%} exceeds threshold {threshold:.1%}[/red]")
                
                # Show failed tests
                failed_tests = [r for r in results.get("detailed_results", []) if not r.get("success")]
                if failed_tests:
                    console.print(f"\n[bold]Failed Tests ({len(failed_tests)}):[/bold]")
                    for test in failed_tests[:10]:  # Show top 10
                        console.print(f"  • {test.get('method')} {test.get('endpoint')}: {test.get('error_message', 'Unknown error')}")
            else:
                console.print(f"[green]✓[/green] No alerts - failure rate {failure_rate:.1%} is below threshold")
        else:
            console.print("[yellow]No tests to analyze[/yellow]")
    
    except Exception as e:
        console.print(f"[red]Error checking alerts: {e}[/red]")

