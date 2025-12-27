#!/usr/bin/env python3
"""Dedicated test runner for Company API endpoints."""

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
from fixtures.company_test_scenarios import CompanyTestScenarios


def main():
    """Main entry point for Company API testing."""
    parser = argparse.ArgumentParser(
        description="Test Company API endpoints comprehensively",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic test run
  python test_company_api.py
  
  # Test specific category
  python test_company_api.py --category query
  
  # Custom output directory
  python test_company_api.py --output-dir ./company_test_reports
  
  # Comprehensive mode
  python test_company_api.py --mode comprehensive
  
  # Note: All Company endpoints require authentication (all roles can access)
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
        help="Test specific category (query, count, filters, filter_data, detail, company_contacts, or their _errors variants)"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="./company_test_reports",
        help="Output directory for test reports (default: ./company_test_reports)"
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
        "[bold cyan]Company API Test Runner[/bold cyan]\n"
        "Comprehensive testing for all Company API endpoints",
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
    all_scenarios = CompanyTestScenarios.get_all_scenarios()
    
    # Filter by category if specified
    if args.category:
        all_scenarios = [s for s in all_scenarios if s.get("category") == args.category]
        if not all_scenarios:
            console.print(f"[red]No scenarios found for category: {args.category}[/red]")
            return 1
    
    # Filter by mode
    if args.mode == "smoke":
        all_scenarios = [s for s in all_scenarios if "errors" not in s.get("category", "")]
    
    console.print(f"[dim]Total scenarios: {len(all_scenarios)}[/dim]")
    
    # Run tests
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=console
    ) as progress:
        task = progress.add_task("[cyan]Running tests...", total=len(all_scenarios))
        
        for scenario in all_scenarios:
            progress.update(task, description=f"[cyan]Testing {scenario.get('name', 'unknown')}...")
            
            # Create endpoint dict
            endpoint = {
                "method": scenario.get("method", "GET"),
                "endpoint": scenario.get("endpoint", ""),
                "api_version": scenario.get("endpoint", "").split("/")[2] if len(scenario.get("endpoint", "").split("/")) > 2 else "v3",
                "category": scenario.get("category", ""),
                "description": scenario.get("description", "")
            }
            
            # Handle path params in endpoint URL
            endpoint_path = scenario.get("endpoint", "")
            if scenario.get("path_params"):
                for key, value in scenario.get("path_params", {}).items():
                    endpoint_path = endpoint_path.replace(f"{{{key}}}", str(value))
            
            # Create test case
            test_case = {
                "name": scenario.get("name", ""),
                "description": scenario.get("description", ""),
                "method": scenario.get("method", "GET"),
                "url": endpoint_path,
                "query_params": scenario.get("query_params", {}),
                "body": scenario.get("body", {}),
                "headers": {},
                "expected_status": scenario.get("expected_status", [200]),
                "validate_response": scenario.get("validate_response", {}),
                "requires_auth": scenario.get("requires_auth", True)
            }
            
            # Execute test
            try:
                result = executor.execute_test(test_case, endpoint)
                collector.collect(result, endpoint, test_case)
                
                if args.verbose:
                    status_icon = "[green]✓[/green]" if result.get("success") else "[red]✗[/red]"
                    console.print(f"{status_icon} {scenario.get('name')}")
            except Exception as e:
                console.print(f"[red]Error testing {scenario.get('name')}: {e}[/red]")
                result = {
                    "success": False,
                    "error_message": str(e),
                    "status_code": None
                }
                collector.collect(result, endpoint, test_case)
            
            progress.advance(task)
    
    # Generate report
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    reporter = ReportGenerator()
    report_path = reporter.generate_report(
        collector.get_results(),
        output_dir=output_dir,
        test_name="Company API Tests"
    )
    
    # Print summary
    console.print("\n")
    results = collector.get_results()
    total = len(results)
    passed = sum(1 for r in results if r.get("success"))
    failed = total - passed
    
    summary_table = Table(title="Test Summary", show_header=True, header_style="bold magenta")
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("Count", style="green")
    
    summary_table.add_row("Total Tests", str(total))
    summary_table.add_row("Passed", f"[green]{passed}[/green]")
    summary_table.add_row("Failed", f"[red]{failed}[/red]")
    summary_table.add_row("Success Rate", f"{passed/total*100:.1f}%" if total > 0 else "0%")
    
    console.print(summary_table)
    console.print(f"\n[dim]Detailed report saved to: {report_path}[/dim]")
    
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

