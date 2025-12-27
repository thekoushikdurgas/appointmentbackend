#!/usr/bin/env python3
"""Main API testing script for Contact360 endpoints."""

import csv
import sys
import argparse
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.table import Table
from rich.panel import Panel

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from tests.config import TestConfig
from tests.auth import AuthHandler
from tests.test_generator import TestCaseGenerator
from tests.executor import TestExecutor
from tests.collector import ResultCollector
from tests.reporter import ReportGenerator

# Import fixtures (handle import error gracefully)
try:
    from fixtures.seed_test_entities import TestEntitySeeder
    FIXTURES_AVAILABLE = True
except ImportError:
    TestEntitySeeder = None
    FIXTURES_AVAILABLE = False


def load_endpoints_from_csv(csv_path: Path) -> List[Dict[str, Any]]:
    """Load endpoints from a single CSV file.
    
    Args:
        csv_path: Path to CSV file
    
    Returns:
        List of endpoint dictionaries
    """
    endpoints = []
    try:
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('endpoint'):  # Skip empty rows
                    endpoints.append(row)
    except FileNotFoundError:
        print(f"Error: CSV file not found: {csv_path}")
        return []
    except Exception as e:
        print(f"Error reading CSV file {csv_path}: {e}")
        return []
    
    return endpoints


def load_all_endpoints(csv_dir: Path) -> Dict[Path, List[Dict[str, Any]]]:
    """Load endpoints from all CSV files in a directory.
    
    Args:
        csv_dir: Path to directory containing CSV files
    
    Returns:
        Dictionary mapping CSV file path to list of endpoint dictionaries
    """
    endpoints_by_file = {}
    
    if not csv_dir.exists():
        print(f"Error: CSV directory not found: {csv_dir}")
        return endpoints_by_file
    
    # Find all CSV files in the directory
    csv_files = list(csv_dir.glob("*.csv"))
    
    if not csv_files:
        print(f"Warning: No CSV files found in {csv_dir}")
        return endpoints_by_file
    
    for csv_path in csv_files:
        endpoints = load_endpoints_from_csv(csv_path)
        if endpoints:
            endpoints_by_file[csv_path] = endpoints
            print(f"Loaded {len(endpoints)} endpoints from {csv_path.name}")
    
    return endpoints_by_file


def group_endpoints_by_category(endpoints: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Group endpoints by category.
    
    Args:
        endpoints: List of endpoint dictionaries
    
    Returns:
        Dictionary mapping category name to list of endpoints
    """
    categories = {}
    for endpoint in endpoints:
        category = endpoint.get('category', 'Other')
        if category not in categories:
            categories[category] = []
        categories[category].append(endpoint)
    
    return categories


def filter_endpoints(
    endpoints: List[Dict[str, Any]],
    category: Optional[str] = None,
    method: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Filter endpoints by category and/or method.
    
    Args:
        endpoints: List of endpoint dictionaries
        category: Category filter (optional)
        method: Method filter (optional)
    
    Returns:
        Filtered list of endpoints
    """
    filtered = endpoints
    
    if category:
        filtered = [e for e in filtered if e.get('category', '').lower() == category.lower()]
    
    if method:
        filtered = [e for e in filtered if e.get('method', '').upper() == method.upper()]
    
    return filtered


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Test Contact360 API endpoints",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic test run (uses hardcoded credentials, always updates CSV)
  python api_tester.py
  
  # Test specific category
  python api_tester.py --filter-category Auth --verbose
  
  # Custom output directory
  python api_tester.py --output-dir ./reports
  
  # Comprehensive mode
  python api_tester.py --mode comprehensive
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
        default="hybrid",
        help="Test mode (default: hybrid)"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Output directory for reports (default: ./test_reports)"
    )
    parser.add_argument(
        "--filter-category",
        type=str,
        default=None,
        help="Only test endpoints in this category"
    )
    parser.add_argument(
        "--filter-method",
        type=str,
        default=None,
        help="Only test endpoints with this method"
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
        "[bold cyan]Contact360 API Test Suite[/bold cyan]\n"
        f"Base URL: [yellow]{args.base_url or 'http://127.0.0.1:8000'}[/yellow]\n"
        f"Mode: [yellow]{args.mode}[/yellow]",
        border_style="cyan"
    ))
    
    # Initialize configuration (uses hardcoded credentials by default)
    config = TestConfig(
        base_url=args.base_url,
        test_mode=args.mode,
        output_dir=args.output_dir
    )
    
    # Initialize authentication handler
    auth_handler = AuthHandler(config)
    if not auth_handler.authenticate():
        console.print("[red]Error: Authentication failed.[/red]")
        sys.exit(1)
    
    console.print("[green]✓[/green] Authentication successful")
    
    # Load endpoints from all CSV files in the csv directory
    csv_dir = Path(__file__).parent / "csv"
    endpoints_by_file = load_all_endpoints(csv_dir)
    
    if not endpoints_by_file:
        console.print("[red]Error: No endpoints loaded from CSV files.[/red]")
        sys.exit(1)
    
    total_endpoints = sum(len(eps) for eps in endpoints_by_file.values())
    console.print(f"[green]✓[/green] Loaded {total_endpoints} endpoints from {len(endpoints_by_file)} CSV file(s)")
    
    # Check if any endpoints require admin and authenticate admin if needed
    all_endpoints_flat = []
    for endpoints in endpoints_by_file.values():
        all_endpoints_flat.extend(endpoints)
    
    has_admin_endpoints = any(
        str(endpoint.get("requires_admin", "FALSE")).upper() in ["TRUE", "1", "YES", "Y", "ON"]
        for endpoint in all_endpoints_flat
    )
    
    if has_admin_endpoints:
        if config.has_admin_credentials():
            if auth_handler.authenticate_admin():
                console.print("[green]✓[/green] Admin authentication successful")
            else:
                console.print("[yellow]⚠[/yellow] Admin authentication failed - admin endpoints will be skipped")
        else:
            console.print("[yellow]⚠[/yellow] Admin credentials not configured - admin endpoints will be skipped")
    
    # Initialize test entity seeder (if available)
    seeder = None
    if FIXTURES_AVAILABLE and TestEntitySeeder:
        try:
            seeder = TestEntitySeeder(config, auth_handler)
            seeder.load_seeds()
            # Try to seed entities (non-blocking if it fails)
            try:
                seeder.seed_all()
                console.print("[green]✓[/green] Test entities seeded")
            except Exception as e:
                console.print(f"[yellow]⚠[/yellow] Could not seed all test entities: {e}")
        except Exception as e:
            console.print(f"[yellow]⚠[/yellow] Could not initialize test seeder: {e}")
    
    # Initialize components
    test_generator = TestCaseGenerator(test_mode=config.test_mode)
    executor = TestExecutor(config, auth_handler, seeder)
    collector = ResultCollector()
    
    # Track which CSV file each endpoint came from
    # Use a tuple key (method, endpoint) to uniquely identify endpoints
    endpoint_to_csv = {}
    all_endpoints = []
    for csv_path, endpoints in endpoints_by_file.items():
        # Filter endpoints if filters are specified
        filtered = filter_endpoints(endpoints, args.filter_category, args.filter_method)
        for endpoint in filtered:
            endpoint_key = (endpoint.get('method', ''), endpoint.get('endpoint', ''))
            endpoint_to_csv[endpoint_key] = csv_path
            all_endpoints.append(endpoint)
    
    if not all_endpoints:
        console.print("[red]Error: No endpoints to test after filtering.[/red]")
        sys.exit(1)
    
    # Group endpoints by category for sequential processing
    categories = group_endpoints_by_category(all_endpoints)
    sorted_categories = sorted(categories.keys())
    
    console.print(f"[green]✓[/green] Organized into {len(sorted_categories)} categories")
    
    # Generate all test cases first
    all_test_cases = []
    for endpoint in all_endpoints:
        test_cases = test_generator.generate_test_cases(endpoint)
        endpoint_key = (endpoint.get('method', ''), endpoint.get('endpoint', ''))
        for test_case in test_cases:
            test_case["_endpoint"] = endpoint  # Store endpoint reference
            test_case["_csv_file"] = endpoint_to_csv.get(endpoint_key)  # Store CSV file reference
            all_test_cases.append(test_case)
    
    console.print(f"[green]✓[/green] Generated {len(all_test_cases)} test cases")
    
    # Execute tests category by category, endpoint by endpoint
    console.print("\n[bold]Testing endpoints...[/bold]")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=console
    ) as progress:
        task = progress.add_task("Running tests...", total=len(all_test_cases))
        
        # Process categories one by one
        for category in sorted_categories:
            category_endpoints = categories[category]
            
            # Process each endpoint in the category
            for endpoint in category_endpoints:
                # Find all test cases for this endpoint using method and endpoint path
                endpoint_method = endpoint.get('method', '')
                endpoint_path = endpoint.get('endpoint', '')
                endpoint_test_cases = [
                    tc for tc in all_test_cases 
                    if tc.get("_endpoint", {}).get('method') == endpoint_method 
                    and tc.get("_endpoint", {}).get('endpoint') == endpoint_path
                ]
                
                # Execute each test case for this endpoint
                for test_case in endpoint_test_cases:
                    endpoint_ref = test_case.pop("_endpoint")
                    csv_file_ref = test_case.pop("_csv_file", None)
                    
                    # Show current progress
                    current_category = endpoint_ref.get('category', 'Unknown')
                    current_endpoint = endpoint_ref.get('endpoint', 'Unknown')
                    progress.update(
                        task, 
                        description=f"Testing [{current_category}] {current_endpoint}",
                        advance=0
                    )
                    
                    result = executor.execute_test(test_case, endpoint_ref)
                    collector.add_result(result, endpoint_ref)
                    
                    # Store CSV file reference in result for later CSV updates
                    result["_csv_file"] = csv_file_ref
                    
                    if args.verbose:
                        status = "[green]✓[/green]" if result["success"] else "[red]✗[/red]"
                        console.print(
                            f"{status} [{current_category}] {result['method']} {result['endpoint']} - {result['test_case_name']}"
                        )
                    
                    progress.update(task, advance=1)
    
    # Generate reports
    console.print("\n[bold]Generating reports...[/bold]")
    
    all_results = collector.get_all_results()
    summary = collector.get_summary()
    
    # Convert Path objects to strings for JSON serialization
    def convert_paths(obj):
        """Recursively convert Path objects to strings."""
        if isinstance(obj, Path):
            return str(obj)
        elif isinstance(obj, dict):
            return {k: convert_paths(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_paths(item) for item in obj]
        return obj
    
    # Create a copy for reports (with Path objects converted to strings)
    report_results = convert_paths(all_results)
    
    reporter = ReportGenerator(config.output_dir)
    
    json_path = reporter.generate_json_report(report_results)
    html_path = reporter.generate_html_report(report_results)
    
    console.print(f"[green]✓[/green] JSON report: {json_path}")
    console.print(f"[green]✓[/green] HTML report: {html_path}")
    
    # Update each CSV file with its results
    console.print("\n[bold]Updating CSV files...[/bold]")
    
    # Group results by CSV file
    results_by_csv = {}
    for result in all_results["detailed_results"]:
        csv_file = result.get("_csv_file")
        if csv_file:
            if csv_file not in results_by_csv:
                results_by_csv[csv_file] = []
            results_by_csv[csv_file].append(result)
    
    # Update each CSV file
    updated_count = 0
    for csv_path, csv_results in results_by_csv.items():
        # Create a results dict structure for this CSV file
        csv_results_dict = {
            "test_run": all_results["test_run"],
            "summary": {
                "total_tests": len(csv_results),
                "passed": sum(1 for r in csv_results if r["success"]),
                "failed": sum(1 for r in csv_results if not r["success"]),
                "success_rate": (sum(1 for r in csv_results if r["success"]) / len(csv_results) * 100) if csv_results else 0,
                "duration_seconds": all_results["test_run"]["duration_seconds"],
                "unique_endpoints": len(set(f"{r['method']}|{r['endpoint']}" for r in csv_results)),
                "category_stats": {},
                "endpoint_stats": {}
            },
            "results_by_category": {},
            "detailed_results": csv_results
        }
        
        if reporter.update_csv(csv_path, csv_results_dict):
            console.print(f"[green]✓[/green] Updated: {csv_path.name}")
            updated_count += 1
        else:
            console.print(f"[red]✗[/red] Failed to update: {csv_path.name}")
    
    console.print(f"[green]✓[/green] Updated {updated_count} of {len(results_by_csv)} CSV file(s)")
    
    # Display summary
    console.print("\n")
    summary_table = Table(title="Test Results Summary", show_header=True, header_style="bold cyan")
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

