#!/usr/bin/env python3
"""Dedicated test runner for LinkedIn API endpoints."""

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
from fixtures.linkedin_test_scenarios import LinkedInTestScenarios


def main():
    """Main entry point for LinkedIn API testing."""
    parser = argparse.ArgumentParser(
        description="Test LinkedIn API endpoints comprehensively",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic test run
  python test_linkedin_api.py
  
  # Test specific category
  python test_linkedin_api.py --category search
  
  # Custom output directory
  python test_linkedin_api.py --output-dir ./linkedin_test_reports
  
  # Comprehensive mode
  python test_linkedin_api.py --mode comprehensive
  
  # Note: LinkedIn endpoints require authentication (all roles can access)
        """
    )
    
    parser.add_argument(
        "--base-url",
        type=str,
        default=None,
        help="API base URL (default: from env or http://127.0.0.1:8000)"
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=["smoke", "comprehensive", "hybrid"],
        default="comprehensive",
        help="Test mode (default: comprehensive)"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Output directory for reports (default: ./test_reports/linkedin_api)"
    )
    parser.add_argument(
        "--category",
        type=str,
        choices=["search", "search_errors"],
        default=None,
        help="Test specific category only"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed progress"
    )
    
    args = parser.parse_args()
    
    console = Console()
    
    # Display header
    console.print(Panel.fit(
        "[bold cyan]LinkedIn API Test Suite[/bold cyan]\n"
        f"Base URL: [yellow]{args.base_url or 'http://127.0.0.1:8000'}[/yellow]\n"
        f"Mode: [yellow]{args.mode}[/yellow]\n"
        "[dim]Note: LinkedIn endpoints require authentication (all roles can access)[/dim]",
        border_style="cyan"
    ))
    
    # Initialize configuration
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        output_dir = Path(__file__).parent / "test_reports" / "linkedin_api"
    
    config = TestConfig(
        base_url=args.base_url,
        test_mode=args.mode,
        output_dir=str(output_dir)
    )
    
    # Initialize authentication handler
    auth_handler = AuthHandler(config)
    if not auth_handler.authenticate():
        console.print("[red]Error: Authentication failed.[/red]")
        sys.exit(1)
    
    console.print("[green]✓[/green] Authentication successful")
    
    # Filter scenarios by category if specified
    scenarios = LinkedInTestScenarios.get_all_scenarios()
    if args.category:
        scenarios = {args.category: scenarios.get(args.category, [])}
        console.print(f"[yellow]Testing category: {args.category}[/yellow]")
    
    # Initialize components
    executor = TestExecutor(config, auth_handler, seeder=None)
    collector = ResultCollector()
    
    # Convert scenarios to test cases
    all_test_cases = []
    for category, category_scenarios in scenarios.items():
        for scenario in category_scenarios:
            # Create endpoint dictionary
            endpoint = {
                "method": scenario.get("method", "POST"),
                "endpoint": scenario.get("endpoint", "/api/v3/linkedin/"),
                "api_version": "v3",
                "category": category.replace("_", " ").title(),
                "description": scenario.get("description", ""),
                "requires_auth": True,  # LinkedIn endpoints require auth
                "requires_admin": False  # All authenticated users can access
            }
            
            # Create test case
            test_case = {
                "name": scenario.get("name", "unknown"),
                "description": scenario.get("description", ""),
                "method": endpoint["method"],
                "endpoint": endpoint["endpoint"],
                "body": scenario.get("body"),
                "query_params": scenario.get("query_params", {}),
                "expected_status": scenario.get("expected_status", [200]),
                "headers": scenario.get("headers"),  # For unauthorized tests
                "_endpoint": endpoint
            }
            
            all_test_cases.append((test_case, endpoint))
    
    console.print(f"[green]✓[/green] Generated {len(all_test_cases)} test cases")
    
    # Execute tests
    console.print("\n[bold]Testing LinkedIn API endpoints...[/bold]")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=console
    ) as progress:
        task = progress.add_task("Running tests...", total=len(all_test_cases))
        
        for test_case, endpoint in all_test_cases:
            # Show current progress
            category = endpoint.get("category", "Unknown")
            endpoint_path = endpoint.get("endpoint", "Unknown")
            progress.update(
                task,
                description=f"Testing [{category}] {endpoint_path}",
                advance=0
            )
            
            # Extract endpoint reference
            endpoint_ref = test_case.pop("_endpoint")
            
            result = executor.execute_test(test_case, endpoint_ref)
            collector.add_result(result, endpoint_ref)
            
            if args.verbose:
                status = "[green]✓[/green]" if result["success"] else "[red]✗[/red]"
                console.print(
                    f"{status} [{category}] {result['method']} {result['endpoint']} - {result['test_case_name']}"
                )
            
            progress.update(task, advance=1)
    
    # Generate reports
    console.print("\n[bold]Generating reports...[/bold]")
    
    all_results = collector.get_all_results()
    summary = collector.get_summary()
    
    reporter = ReportGenerator(config.output_dir)
    
    json_path = reporter.generate_json_report(all_results)
    html_path = reporter.generate_html_report(all_results)
    
    console.print(f"[green]✓[/green] JSON report: {json_path}")
    console.print(f"[green]✓[/green] HTML report: {html_path}")
    
    # Display summary
    console.print("\n[bold]Test Summary[/bold]")
    
    summary_table = Table(show_header=True, header_style="bold magenta")
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("Value", style="green")
    
    summary_table.add_row("Total Tests", str(summary["total"]))
    summary_table.add_row("Passed", f"[green]{summary['passed']}[/green]")
    summary_table.add_row("Failed", f"[red]{summary['failed']}[/red]")
    summary_table.add_row("Skipped", f"[yellow]{summary['skipped']}[/yellow]")
    summary_table.add_row("Success Rate", f"{summary['success_rate']:.1f}%")
    
    console.print(summary_table)
    
    # Display category breakdown
    if len(scenarios) > 1:
        console.print("\n[bold]Category Breakdown[/bold]")
        
        category_table = Table(show_header=True, header_style="bold magenta")
        category_table.add_column("Category", style="cyan")
        category_table.add_column("Total", style="white")
        category_table.add_column("Passed", style="green")
        category_table.add_column("Failed", style="red")
        category_table.add_column("Success Rate", style="yellow")
        
        for category, category_scenarios in scenarios.items():
            category_results = [
                r for r in all_results
                if r.get("_endpoint", {}).get("category", "").lower() == category.replace("_", " ").lower()
            ]
            
            if category_results:
                category_passed = sum(1 for r in category_results if r["success"])
                category_total = len(category_results)
                category_failed = category_total - category_passed
                category_rate = (category_passed / category_total * 100) if category_total > 0 else 0
                
                category_table.add_row(
                    category.replace("_", " ").title(),
                    str(category_total),
                    f"[green]{category_passed}[/green]",
                    f"[red]{category_failed}[/red]",
                    f"{category_rate:.1f}%"
                )
        
        console.print(category_table)
    
    # Exit with appropriate code
    if summary["failed"] > 0:
        console.print(f"\n[red]Tests completed with {summary['failed']} failure(s)[/red]")
        sys.exit(1)
    else:
        console.print("\n[green]All tests passed![/green]")
        sys.exit(0)


if __name__ == "__main__":
    main()
