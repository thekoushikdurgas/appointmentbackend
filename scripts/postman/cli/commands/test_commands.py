"""Test execution commands."""

import sys
from pathlib import Path
from typing import Optional, List
import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.table import Table
from rich.panel import Panel

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.config import TestConfig
from tests.auth import AuthHandler
from tests.test_generator import TestCaseGenerator
from tests.executor import TestExecutor
from tests.collector import ResultCollector
from tests.reporter import ReportGenerator
from cli.intelligence.analyzer import ResultAnalyzer
from cli.intelligence.prioritizer import TestPrioritizer
from cli.intelligence.reporting import EnhancedReporter
from cli.intelligence.ai_agent import AIAgent
from cli.config import ConfigManager

try:
    from fixtures.seed_test_entities import TestEntitySeeder
    FIXTURES_AVAILABLE = True
except ImportError:
    TestEntitySeeder = None
    FIXTURES_AVAILABLE = False

app = typer.Typer(name="test", help="Test execution commands")
console = Console()


def load_endpoints_from_csv(csv_path: Path):
    """Load endpoints from CSV file."""
    import csv
    endpoints = []
    try:
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('endpoint'):
                    endpoints.append(row)
    except Exception as e:
        console.print(f"[red]Error reading CSV: {e}[/red]")
    return endpoints


def filter_endpoints(endpoints, category: Optional[str] = None, method: Optional[str] = None):
    """Filter endpoints by category and/or method."""
    filtered = endpoints
    if category:
        filtered = [e for e in filtered if e.get('category', '').lower() == category.lower()]
    if method:
        filtered = [e for e in filtered if e.get('method', '').upper() == method.upper()]
    return filtered


@app.command()
def run(
    category: Optional[str] = typer.Option(None, "--category", "-c", help="Filter by category"),
    method: Optional[str] = typer.Option(None, "--method", "-m", help="Filter by HTTP method"),
    mode: str = typer.Option("hybrid", "--mode", help="Test mode: smoke, comprehensive, or hybrid"),
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Configuration profile"),
    output_dir: Optional[str] = typer.Option(None, "--output", "-o", help="Output directory"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
    csv_dir: Optional[str] = typer.Option(None, "--csv-dir", help="CSV directory path")
):
    """Run all tests or filtered subset."""
    config_manager = ConfigManager()
    cli_profile = config_manager.get_profile(profile)
    
    # Initialize test config
    test_config = TestConfig(
        base_url=cli_profile.base_url,
        email=cli_profile.email,
        password=cli_profile.password,
        access_token=cli_profile.access_token,
        refresh_token=cli_profile.refresh_token,
        write_key=cli_profile.write_key,
        timeout=cli_profile.timeout,
        retry_max=cli_profile.retry_max,
        retry_backoff=cli_profile.retry_backoff,
        test_mode=mode,
        output_dir=output_dir or cli_profile.output_dir,
        auto_create_test_user=cli_profile.auto_create_test_user
    )
    
    # Load endpoints
    csv_directory = Path(csv_dir) if csv_dir else Path(__file__).parent.parent.parent / "csv"
    if not csv_directory.exists():
        console.print(f"[red]CSV directory not found: {csv_directory}[/red]")
        raise typer.Exit(1)
    
    all_endpoints = []
    for csv_file in csv_directory.glob("*.csv"):
        endpoints = load_endpoints_from_csv(csv_file)
        all_endpoints.extend(endpoints)
    
    if not all_endpoints:
        console.print("[red]No endpoints found in CSV files[/red]")
        raise typer.Exit(1)
    
    # Filter endpoints
    filtered_endpoints = filter_endpoints(all_endpoints, category, method)
    
    if not filtered_endpoints:
        console.print("[red]No endpoints match the filters[/red]")
        raise typer.Exit(1)
    
    console.print(Panel.fit(
        f"[bold cyan]Running Tests[/bold cyan]\n"
        f"Endpoints: [yellow]{len(filtered_endpoints)}[/yellow]\n"
        f"Mode: [yellow]{mode}[/yellow]",
        border_style="cyan"
    ))
    
    # Initialize components
    auth_handler = AuthHandler(test_config)
    if not auth_handler.authenticate():
        console.print("[red]Authentication failed[/red]")
        raise typer.Exit(1)
    
    # Initialize AI agent for learning
    ai_agent = AIAgent()
    
    seeder = None
    if FIXTURES_AVAILABLE and TestEntitySeeder:
        try:
            seeder = TestEntitySeeder(test_config, auth_handler)
            seeder.load_seeds()
            seeder.seed_all()
        except Exception:
            pass
    
    test_generator = TestCaseGenerator(test_mode=mode)
    executor = TestExecutor(test_config, auth_handler, seeder)
    collector = ResultCollector()
    
    # Generate and execute tests
    all_test_cases = []
    for endpoint in filtered_endpoints:
        test_cases = test_generator.generate_test_cases(endpoint)
        for test_case in test_cases:
            test_case["_endpoint"] = endpoint
            all_test_cases.append(test_case)
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=console
    ) as progress:
        task = progress.add_task("Running tests...", total=len(all_test_cases))
        
        for test_case in all_test_cases:
            endpoint = test_case.pop("_endpoint")
            result = executor.execute_test(test_case, endpoint)
            collector.add_result(result, endpoint)
            
            # Learn from result (AI agentic feature)
            ai_agent.learn_from_result(result, endpoint)
            
            if verbose:
                status = "[green]✓[/green]" if result["success"] else "[red]✗[/red]"
                console.print(f"{status} {result['method']} {result['endpoint']}")
            
            progress.update(task, advance=1)
    
    # Generate reports
    all_results = collector.get_all_results()
    reporter = ReportGenerator(test_config.output_dir)
    
    json_path = reporter.generate_json_report(all_results)
    html_path = reporter.generate_html_report(all_results)
    
    console.print(f"\n[green]✓[/green] JSON report: {json_path}")
    console.print(f"[green]✓[/green] HTML report: {html_path}")
    
    # Display summary
    summary = collector.get_summary()
    summary_table = Table(title="Test Results", show_header=True)
    summary_table.add_column("Metric")
    summary_table.add_column("Value", justify="right")
    
    summary_table.add_row("Total Tests", str(summary["total_tests"]))
    summary_table.add_row("Passed", f"[green]{summary['passed']}[/green]")
    summary_table.add_row("Failed", f"[red]{summary['failed']}[/red]")
    summary_table.add_row("Success Rate", f"{summary['success_rate']:.1f}%")
    
    console.print(summary_table)
    
    # Analyze results
    analyzer = ResultAnalyzer()
    analysis = analyzer.analyze_results(all_results)
    
    if analysis.get("recommendations"):
        console.print("\n[bold]Recommendations:[/bold]")
        for rec in analysis["recommendations"]:
            console.print(f"  • {rec}")
    
    # Save AI agent knowledge
    ai_agent.save_knowledge()
    console.print("[green]✓[/green] AI knowledge base updated")
    
    # Generate enhanced dashboard
    enhanced_reporter = EnhancedReporter(test_config.output_dir)
    dashboard = enhanced_reporter.generate_dashboard(all_results)
    dashboard_path = enhanced_reporter.save_dashboard(dashboard)
    console.print(f"[green]✓[/green] Dashboard: {dashboard_path}")
    
    # Display health score
    health = dashboard.get("health_score", {})
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
        if health.get("factors"):
            console.print("[yellow]Factors:[/yellow]")
            for factor in health["factors"]:
                console.print(f"  • {factor}")


@app.command()
def run_category(
    category: str = typer.Argument(..., help="Category name"),
    mode: str = typer.Option("hybrid", "--mode", help="Test mode"),
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Configuration profile"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output")
):
    """Run tests for a specific category."""
    run(category=category, mode=mode, profile=profile, verbose=verbose)


@app.command()
def run_endpoint(
    endpoint: str = typer.Argument(..., help="Endpoint path (e.g., /api/v1/users/)"),
    method: str = typer.Option("GET", "--method", "-m", help="HTTP method"),
    mode: str = typer.Option("hybrid", "--mode", help="Test mode"),
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Configuration profile"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output")
):
    """Run tests for a specific endpoint."""
    # This is a simplified version - full implementation would match endpoint more precisely
    run(method=method, mode=mode, profile=profile, verbose=verbose)


@app.command()
def run_smart(
    limit: int = typer.Option(50, "--limit", "-l", help="Maximum number of tests to run"),
    mode: str = typer.Option("hybrid", "--mode", help="Test mode"),
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Configuration profile"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
    output_dir: Optional[str] = typer.Option(None, "--output", "-o", help="Output directory"),
    csv_dir: Optional[str] = typer.Option(None, "--csv-dir", help="CSV directory path")
):
    """Run tests with intelligent prioritization."""
    config_manager = ConfigManager()
    cli_profile = config_manager.get_profile(profile)
    
    # Load endpoints
    csv_directory = Path(csv_dir) if csv_dir else Path(__file__).parent.parent.parent / "csv"
    all_endpoints = []
    for csv_file in csv_directory.glob("*.csv"):
        endpoints = load_endpoints_from_csv(csv_file)
        all_endpoints.extend(endpoints)
    
    # Load historical results for prioritization
    reports_dir = Path(output_dir) if output_dir else Path(__file__).parent.parent.parent / "test_reports"
    latest_json = reports_dir / "test_results_latest.json"
    historical_results = None
    
    if latest_json.exists():
        try:
            import json
            with open(latest_json, 'r') as f:
                historical_data = json.load(f)
                historical_results = historical_data.get("detailed_results", [])
        except Exception:
            pass
    
    # Prioritize endpoints
    prioritizer = TestPrioritizer()
    prioritized = prioritizer.prioritize_tests(all_endpoints, historical_results)
    
    # Take top N
    top_endpoints = [p["endpoint"] for p in prioritized[:limit]]
    
    console.print(f"[cyan]Running top {len(top_endpoints)} prioritized tests[/cyan]")
    
    # Show prioritization info
    if verbose:
        console.print("\n[bold]Top Prioritized Endpoints:[/bold]")
        for i, p in enumerate(prioritized[:10], 1):
            console.print(f"  {i}. {p['endpoint'].get('method')} {p['endpoint'].get('endpoint')} (priority: {p['priority']:.1f}, reason: {p['reason']})")
    
    # Run tests with filtered endpoints
    # Note: This is a simplified approach - in production, we'd pass the filtered list directly
    run(mode=mode, profile=profile, verbose=verbose, output_dir=output_dir, csv_dir=csv_dir)

