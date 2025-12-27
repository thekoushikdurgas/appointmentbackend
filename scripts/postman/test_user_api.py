#!/usr/bin/env python3
"""Dedicated test runner for user API endpoints."""

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
from tests.test_generator import TestCaseGenerator
from tests.executor import TestExecutor
from tests.collector import ResultCollector
from tests.reporter import ReportGenerator
from fixtures.user_test_scenarios import UserTestScenarios


def main():
    """Main entry point for user API testing."""
    parser = argparse.ArgumentParser(
        description="Test User API endpoints comprehensively",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic test run
  python test_user_api.py
  
  # Test specific category
  python test_user_api.py --category registration
  
  # Custom output directory
  python test_user_api.py --output-dir ./user_test_reports
  
  # Comprehensive mode
  python test_user_api.py --mode comprehensive
        """
    )
    
    parser.add_argument(
        "--base-url",
        type=str,
        default=None,
        help="API base URL (default: from env or http://34.229.94.175)"
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
        help="Output directory for reports (default: ./test_reports/user_api)"
    )
    parser.add_argument(
        "--category",
        type=str,
        choices=["registration", "login", "token_management", "profile_management", "role_management", "super_admin"],
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
        "[bold cyan]User API Test Suite[/bold cyan]\n"
        f"Base URL: [yellow]{args.base_url or 'http://34.229.94.175'}[/yellow]\n"
        f"Mode: [yellow]{args.mode}[/yellow]",
        border_style="cyan"
    ))
    
    # Initialize configuration
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        output_dir = Path(__file__).parent / "test_reports" / "user_api"
    
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
    
    # Check if super admin authentication is needed
    scenarios = UserTestScenarios.get_all_scenarios()
    needs_super_admin = any(
        scenario.get("requires_super_admin", False)
        for category_scenarios in scenarios.values()
        for scenario in category_scenarios
    )
    
    if needs_super_admin:
        if config.has_admin_credentials():
            if auth_handler.authenticate_admin():
                console.print("[green]✓[/green] Admin authentication successful")
            else:
                console.print("[yellow]⚠[/yellow] Admin authentication failed - super admin tests will be skipped")
        else:
            console.print("[yellow]⚠[/yellow] Admin credentials not configured - super admin tests will be skipped")
    
    # Filter scenarios by category if specified
    if args.category:
        scenarios = {args.category: scenarios.get(args.category, [])}
        console.print(f"[yellow]Testing category: {args.category}[/yellow]")
    
    # Initialize components
    test_generator = TestCaseGenerator(test_mode=config.test_mode)
    executor = TestExecutor(config, auth_handler, seeder=None)
    collector = ResultCollector()
    
    # Convert scenarios to test cases
    all_test_cases = []
    for category, category_scenarios in scenarios.items():
        for scenario in category_scenarios:
            # Create endpoint dictionary
            endpoint = {
                "method": scenario.get("method", "GET"),
                "endpoint": scenario.get("endpoint", "/api/v1/users/profile/"),
                "api_version": "v1",
                "category": category.replace("_", " ").title(),
                "description": scenario.get("description", ""),
                "requires_auth": True,
                "requires_admin": scenario.get("requires_super_admin", False)
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
                "_endpoint": endpoint
            }
            
            all_test_cases.append((test_case, endpoint))
    
    console.print(f"[green]✓[/green] Generated {len(all_test_cases)} test cases")
    
    # Execute tests
    console.print("\n[bold]Testing user API endpoints...[/bold]")
    
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
    console.print("\n")
    summary_table = Table(title="User API Test Results Summary", show_header=True, header_style="bold cyan")
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("Value", style="white", justify="right")
    
    summary_table.add_row("Total Tests", str(summary["total_tests"]))
    summary_table.add_row("Passed", f"[green]{summary['passed']}[/green] ({summary['success_rate']:.1f}%)")
    summary_table.add_row("Failed", f"[red]{summary['failed']}[/red]")
    summary_table.add_row("Unique Endpoints", str(summary["unique_endpoints"]))
    summary_table.add_row("Duration", f"{summary['duration_seconds']:.1f}s")
    
    console.print(summary_table)
    
    # Display category breakdown
    if len(summary["category_stats"]) > 0:
        console.print("\n")
        category_table = Table(title="Results by Category", show_header=True, header_style="bold cyan")
        category_table.add_column("Category", style="cyan")
        category_table.add_column("Total", justify="right")
        category_table.add_column("Passed", justify="right", style="green")
        category_table.add_column("Failed", justify="right", style="red")
        category_table.add_column("Success Rate", justify="right")
        
        for category, stats in sorted(summary["category_stats"].items()):
            category_table.add_row(
                category,
                str(stats["total"]),
                str(stats["passed"]),
                str(stats["failed"]),
                f"{stats['success_rate']:.1f}%"
            )
        
        console.print(category_table)
    
    # Exit with appropriate code
    if summary["failed"] > 0:
        console.print(f"\n[red]Tests completed with {summary['failed']} failures.[/red]")
        sys.exit(1)
    else:
        console.print("\n[green]All tests passed![/green]")
        sys.exit(0)


if __name__ == "__main__":
    main()

