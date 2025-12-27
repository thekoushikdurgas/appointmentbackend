#!/usr/bin/env python3
"""Dedicated test runner for Email API endpoints."""

import sys
import argparse
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from tests.config import TestConfig
from tests.auth import AuthHandler
from tests.executor import TestExecutor
from tests.collector import ResultCollector
from tests.reporter import ReportGenerator
from fixtures.email_test_scenarios import EmailTestScenarios


def main():
    """Main entry point for Email API testing."""
    parser = argparse.ArgumentParser(
        description="Test Email API endpoints comprehensively",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic test run
  python test_email_api.py
  
  # Test specific category
  python test_email_api.py --category finder
  
  # Custom output directory
  python test_email_api.py --output-dir ./email_test_reports
  
  # Comprehensive mode
  python test_email_api.py --mode comprehensive
  
  # Note: Email endpoints require authentication (all roles can access)
        """
    )
    
    parser.add_argument(
        "--base-url",
        type=str,
        default=None,
        help="API base URL (default: from env or http://34.229.94.175)"
    )
    parser.add_argument(
        "--category",
        type=str,
        default=None,
        help="Test specific category (finder, export, single, bulk_verifier, single_verifier, verifier, verifier_single, bulk_download, or their _errors variants)"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="./email_test_reports",
        help="Output directory for test reports (default: ./email_test_reports)"
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=["smoke", "comprehensive"],
        default="comprehensive",
        help="Test mode: smoke (quick tests) or comprehensive (all tests, default)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    
    args = parser.parse_args()
    
    # Initialize console
    console = Console()
    
    # Print header
    console.print(Panel.fit(
        "[bold cyan]Email API Test Runner[/bold cyan]\n"
        "Comprehensive testing for all Email API endpoints",
        border_style="cyan"
    ))
    
    # Load configuration
    config = TestConfig(base_url=args.base_url)
    console.print(f"[dim]Base URL: {config.base_url}[/dim]")
    
    # Initialize components
    auth_handler = AuthHandler(config)
    executor = TestExecutor(config, auth_handler)
    collector = ResultCollector()
    
    # Get all scenarios
    all_scenarios = EmailTestScenarios.get_all_scenarios()
    
    # Filter by category if specified
    if args.category:
        filtered_scenarios = [
            s for s in all_scenarios
            if s.get("category") == args.category or s.get("category", "").startswith(args.category)
        ]
        if not filtered_scenarios:
            console.print(f"[red]No scenarios found for category: {args.category}[/red]")
            console.print(f"[yellow]Available categories:[/yellow]")
            categories = set(s.get("category", "unknown") for s in all_scenarios)
            for cat in sorted(categories):
                console.print(f"  - {cat}")
            return 1
        scenarios = filtered_scenarios
        console.print(f"[green]Testing category: {args.category}[/green] ({len(scenarios)} scenarios)")
    else:
        scenarios = all_scenarios
        console.print(f"[green]Testing all categories[/green] ({len(scenarios)} scenarios)")
    
    # Filter by mode
    if args.mode == "smoke":
        # For smoke tests, only run scenarios without "_error" in category
        scenarios = [s for s in scenarios if "_error" not in s.get("category", "")]
        console.print(f"[yellow]Smoke mode: {len(scenarios)} scenarios[/yellow]")
    
    # Authenticate
    console.print("\n[bold]Authentication[/bold]")
    try:
        auth_success = auth_handler.authenticate()
        if not auth_success:
            console.print("[red]Authentication failed. Some tests may fail.[/red]")
    except Exception as e:
        console.print(f"[red]Authentication error: {e}[/red]")
        console.print("[yellow]Continuing without authentication...[/yellow]")
    
    # Run tests
    console.print(f"\n[bold]Running {len(scenarios)} test scenarios...[/bold]\n")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=console
    ) as progress:
        task = progress.add_task("[cyan]Testing...", total=len(scenarios))
        
        for scenario in scenarios:
            scenario_name = scenario.get("name", "unknown")
            category = scenario.get("category", "unknown")
            
            if args.verbose:
                console.print(f"\n[dim]Running: {category}/{scenario_name}[/dim]")
            
            # Check if authentication is required
            requires_auth = scenario.get("requires_auth", True)
            if not requires_auth:
                # Skip auth for this test
                test_auth = None
            else:
                test_auth = auth_handler
            
            # Execute test
            try:
                result = executor.execute_scenario(scenario, auth_handler=test_auth)
                collector.add_result(result)
                
                if args.verbose:
                    status_icon = "✅" if result["success"] else "❌"
                    console.print(f"  {status_icon} {scenario_name}: {result.get('status_code', 'N/A')}")
            except Exception as e:
                collector.add_error(scenario, str(e))
                if args.verbose:
                    console.print(f"  ❌ {scenario_name}: Error - {e}")
            
            progress.update(task, advance=1)
    
    # Generate report
    console.print("\n[bold]Generating Report[/bold]")
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    reporter = ReportGenerator(collector)
    report_path = reporter.generate_html_report(
        output_dir / "email_api_test_report.html",
        title="Email API Test Report"
    )
    
    # Print summary
    console.print("\n[bold]Test Summary[/bold]")
    summary = collector.get_summary()
    
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Metric", style="cyan")
    table.add_column("Count", style="green")
    
    table.add_row("Total Tests", str(summary["total"]))
    table.add_row("Passed", f"[green]{summary['passed']}[/green]")
    table.add_row("Failed", f"[red]{summary['failed']}[/red]")
    table.add_row("Errors", f"[yellow]{summary['errors']}[/yellow]")
    
    # Category breakdown
    if not args.category:
        table.add_row("", "")
        table.add_row("[bold]By Category[/bold]", "")
        category_stats = collector.get_category_stats()
        for category, stats in sorted(category_stats.items()):
            table.add_row(
                f"  {category}",
                f"[green]{stats['passed']}[/green]/[red]{stats['failed']}[/red]"
            )
    
    console.print(table)
    
    # Print report location
    console.print(f"\n[green]Report saved to: {report_path}[/green]")
    
    # Return exit code
    return 0 if summary["failed"] == 0 and summary["errors"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

