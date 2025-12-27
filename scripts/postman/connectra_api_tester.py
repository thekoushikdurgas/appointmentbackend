#!/usr/bin/env python3
"""Main API testing script for Connectra endpoints."""

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
from tests.executor import TestExecutor
from tests.collector import ResultCollector
from tests.reporter import ReportGenerator


class ConnectraAuthHandler:
    """Handles authentication for Connectra API testing using X-API-Key."""
    
    def __init__(self, config: 'ConnectraTestConfig'):
        """Initialize Connectra authentication handler.
        
        Args:
            config: Connectra test configuration
        """
        self.config = config
        self.base_url = config.base_url
        self.api_key: Optional[str] = config.api_key
        self._authenticated = False
    
    def authenticate(self) -> bool:
        """Authenticate using API key.
        
        Returns:
            True if API key is available, False otherwise
        """
        if self.api_key:
            self._authenticated = True
            return True
        return False
    
    def get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers for Connectra API.
        
        Returns:
            Dictionary with X-API-Key header
        """
        headers = {}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        return headers
    
    def handle_401(self) -> bool:
        """Handle 401 Unauthorized response.
        
        For Connectra, 401 usually means invalid API key.
        We can't refresh it automatically, so return False.
        
        Returns:
            False (cannot auto-refresh API key)
        """
        return False


class ConnectraTestConfig:
    """Configuration for Connectra API testing."""
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: int = 30,
        retry_max: int = 3,
        retry_backoff: float = 1.5,
        test_mode: str = "hybrid",
        output_dir: Optional[str] = None,
    ):
        """Initialize Connectra test configuration.
        
        Args:
            base_url: Connectra API base URL (default: from env or http://127.0.0.1:8000)
            api_key: Connectra API key for X-API-Key header
            timeout: Request timeout in seconds
            retry_max: Maximum retry attempts
            retry_backoff: Exponential backoff multiplier
            test_mode: Test mode (smoke/comprehensive/hybrid)
            output_dir: Output directory for reports
        """
        import os
        from dotenv import load_dotenv
        
        # Load environment variables
        env_path = Path(__file__).parent / ".env"
        if env_path.exists():
            load_dotenv(env_path)
        
        self.base_url = base_url or os.getenv("CONNECTRA_BASE_URL", "http://127.0.0.1:8000")
        self.api_key = api_key or os.getenv("CONNECTRA_API_KEY", "3e6b8811-40c2-46e7-8d7c-e7e038e86071")
        
        self.timeout = timeout
        self.retry_max = retry_max
        self.retry_backoff = retry_backoff
        
        if test_mode not in ["smoke", "comprehensive", "hybrid"]:
            raise ValueError(f"Invalid test_mode: {test_mode}. Must be one of: smoke, comprehensive, hybrid")
        self.test_mode = test_mode
        
        # Set output directory
        if output_dir:
            self.output_dir = Path(output_dir)
        else:
            self.output_dir = Path(__file__).parent / "test_reports" / "connectra"
        
        # Create output directory if it doesn't exist
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def has_api_key(self) -> bool:
        """Check if API key is available."""
        return bool(self.api_key)


class ConnectraTestExecutor:
    """Executes HTTP requests for Connectra API testing."""
    
    def __init__(self, config: ConnectraTestConfig, auth_handler: ConnectraAuthHandler):
        """Initialize test executor.
        
        Args:
            config: Test configuration
            auth_handler: Authentication handler
        """
        self.config = config
        self.auth_handler = auth_handler
        import requests
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
        
        self.requests = requests
        self.session = self._create_session()
        # Track UUIDs from created resources for use in PUT/DELETE endpoints
        self.company_uuids = []
        self.contact_uuids = []
    
    def _create_session(self):
        """Create a requests session with retry logic.
        
        Returns:
            Configured requests session
        """
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
        
        session = self.requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=self.config.retry_max,
            backoff_factor=self.config.retry_backoff,
            status_forcelist=[500, 502, 503, 504],  # Retry on server errors
            allowed_methods=["GET", "POST", "PUT", "PATCH", "DELETE"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
    def execute_test(self, test_case: Dict[str, Any], endpoint: Dict[str, Any], retry_count: int = 0) -> Dict[str, Any]:
        """Execute a test case.
        
        Args:
            test_case: Test case dictionary
            endpoint: Endpoint dictionary from CSV
            retry_count: Current retry attempt number
        
        Returns:
            Test result dictionary
        """
        method = test_case.get("method", "GET")
        endpoint_path = endpoint.get("endpoint", "")
        body = test_case.get("body")
        expected_status = test_case.get("expected_status", [200])
        
        # Replace {uuid} placeholder with actual UUID
        if "{uuid}" in endpoint_path:
            if "/companies/" in endpoint_path:
                # Use a company UUID if available, otherwise create one first
                if not self.company_uuids:
                    # Create a company first to get a UUID
                    create_url = f"{self.config.base_url}/companies/create"
                    create_body = {"name": "Test Company for UUID", "employees_count": 100}
                    headers = {"Accept": "application/json", "Content-Type": "application/json"}
                    headers.update(self.auth_handler.get_auth_headers())
                    try:
                        create_response = self.session.post(create_url, json=create_body, headers=headers, timeout=self.config.timeout)
                        if create_response.status_code in [200, 201]:
                            create_data = create_response.json()
                            if isinstance(create_data, dict) and "data" in create_data:
                                uuid_value = create_data["data"].get("uuid")
                            elif isinstance(create_data, dict) and "uuid" in create_data:
                                uuid_value = create_data["uuid"]
                            else:
                                uuid_value = None
                            if uuid_value:
                                self.company_uuids.append(uuid_value)
                    except:
                        pass
                if self.company_uuids:
                    endpoint_path = endpoint_path.replace("{uuid}", self.company_uuids[0])
                else:
                    # Fallback: use a test UUID format (will likely fail but at least won't be literal {uuid})
                    import uuid as uuid_lib
                    endpoint_path = endpoint_path.replace("{uuid}", str(uuid_lib.uuid4()))
            elif "/contacts/" in endpoint_path:
                # Use a contact UUID if available, otherwise create one first
                if not self.contact_uuids:
                    # Create a contact first to get a UUID
                    create_url = f"{self.config.base_url}/contacts/create"
                    create_body = {"first_name": "Test", "last_name": "User", "email": "test@example.com"}
                    headers = {"Accept": "application/json", "Content-Type": "application/json"}
                    headers.update(self.auth_handler.get_auth_headers())
                    try:
                        create_response = self.session.post(create_url, json=create_body, headers=headers, timeout=self.config.timeout)
                        if create_response.status_code in [200, 201]:
                            create_data = create_response.json()
                            if isinstance(create_data, dict) and "data" in create_data:
                                uuid_value = create_data["data"].get("uuid")
                            elif isinstance(create_data, dict) and "uuid" in create_data:
                                uuid_value = create_data["uuid"]
                            else:
                                uuid_value = None
                            if uuid_value:
                                self.contact_uuids.append(uuid_value)
                    except:
                        pass
                if self.contact_uuids:
                    endpoint_path = endpoint_path.replace("{uuid}", self.contact_uuids[0])
                else:
                    # Fallback: use a test UUID format
                    import uuid as uuid_lib
                    endpoint_path = endpoint_path.replace("{uuid}", str(uuid_lib.uuid4()))
        
        # Build full URL
        if endpoint_path.startswith("/"):
            url = f"{self.config.base_url}{endpoint_path}"
        else:
            url = f"{self.config.base_url}/{endpoint_path}"
        
        # Prepare headers
        headers = {
            "Accept": "application/json",
        }
        
        # Add Content-Type for requests with body
        if method in ["POST", "PUT", "PATCH"]:
            headers["Content-Type"] = "application/json"
        
        # Add authentication headers
        auth_headers = self.auth_handler.get_auth_headers()
        headers.update(auth_headers)
        
        # Execute request
        try:
            if method == "GET":
                response = self.session.get(url, headers=headers, timeout=self.config.timeout)
            elif method == "POST":
                response = self.session.post(url, json=body, headers=headers, timeout=self.config.timeout)
            elif method == "PUT":
                response = self.session.put(url, json=body, headers=headers, timeout=self.config.timeout)
            elif method == "DELETE":
                response = self.session.delete(url, headers=headers, timeout=self.config.timeout)
            else:
                return {
                    "success": False,
                    "method": method,
                    "endpoint": endpoint_path,
                    "test_case_name": test_case.get("name", "unknown"),
                    "status_code": None,
                    "response_time_ms": 0,
                    "error_message": f"Unsupported method: {method}"
                }
            
            # Check if status code matches expected
            success = response.status_code in expected_status if isinstance(expected_status, list) else response.status_code == expected_status
            
            # Handle 401 - invalid API key
            if response.status_code == 401:
                if retry_count < 3:
                    if self.auth_handler.handle_401():
                        return self.execute_test(test_case, endpoint, retry_count + 1)
                return {
                    "success": False,
                    "method": method,
                    "endpoint": endpoint_path,
                    "test_case_name": test_case.get("name", "unknown"),
                    "status_code": response.status_code,
                    "response_time_ms": response.elapsed.total_seconds() * 1000,
                    "error_message": "Unauthorized - Invalid API key"
                }
            
            # Extract UUIDs from successful create responses
            if success and response.status_code in [200, 201] and method == "POST":
                try:
                    response_data = response.json()
                    if isinstance(response_data, dict):
                        if "data" in response_data and isinstance(response_data["data"], dict):
                            uuid_value = response_data["data"].get("uuid")
                            if uuid_value:
                                if "/companies/create" in endpoint_path or "/companies/upsert" in endpoint_path:
                                    if uuid_value not in self.company_uuids:
                                        self.company_uuids.append(uuid_value)
                                elif "/contacts/create" in endpoint_path or "/contacts/upsert" in endpoint_path:
                                    if uuid_value not in self.contact_uuids:
                                        self.contact_uuids.append(uuid_value)
                        elif "uuid" in response_data:
                            uuid_value = response_data["uuid"]
                            if uuid_value:
                                if "/companies" in endpoint_path:
                                    if uuid_value not in self.company_uuids:
                                        self.company_uuids.append(uuid_value)
                                elif "/contacts" in endpoint_path:
                                    if uuid_value not in self.contact_uuids:
                                        self.contact_uuids.append(uuid_value)
                except:
                    pass
            
            return {
                "success": success,
                "method": method,
                "endpoint": endpoint_path,
                "test_case_name": test_case.get("name", "unknown"),
                "status_code": response.status_code,
                "response_time_ms": response.elapsed.total_seconds() * 1000,
                "error_message": None if success else f"Expected status {expected_status}, got {response.status_code}",
                "response_body": response.text[:500] if not success else None  # Store error response
            }
        
        except Exception as e:
            return {
                "success": False,
                "method": method,
                "endpoint": endpoint_path,
                "test_case_name": test_case.get("name", "unknown"),
                "status_code": None,
                "response_time_ms": 0,
                "error_message": str(e)
            }


def load_endpoints_from_csv(csv_path: Path) -> List[Dict[str, Any]]:
    """Load endpoints from a CSV file.
    
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


def generate_simple_test_cases(endpoint: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Generate simple test cases for a Connectra endpoint.
    
    Args:
        endpoint: Endpoint dictionary from CSV
    
    Returns:
        List of test case dictionaries
    """
    method = endpoint.get("method", "GET")
    endpoint_path = endpoint.get("endpoint", "")
    
    test_cases = []
    
    if method == "GET":
        # Simple GET test
        test_cases.append({
            "name": "simple_get",
            "description": f"Simple {method} request",
            "method": method,
            "endpoint": endpoint_path,
            "body": None,
            "expected_status": [200, 201, 202, 204]
        })
    elif method in ["POST", "PUT", "PATCH"]:
        # Generate basic body for POST/PUT
        body = {}
        
        # Add endpoint-specific bodies
        if "/companies/create" in endpoint_path or "/companies/upsert" in endpoint_path:
            body = {
                "name": "Test Company",
                "employees_count": 100
            }
        elif "/contacts/create" in endpoint_path or "/contacts/upsert" in endpoint_path:
            body = {
                "first_name": "Test",
                "last_name": "User",
                "email": "test@example.com"
            }
        elif "/companies/bulk" in endpoint_path:
            body = {
                "companies": [
                    {
                        "name": "Test Company 1",
                        "employees_count": 100
                    }
                ]
            }
        elif "/contacts/bulk" in endpoint_path:
            body = {
                "contacts": [
                    {
                        "first_name": "Test",
                        "last_name": "User",
                        "email": "test@example.com"
                    }
                ]
            }
        elif "/companies/filters/data" in endpoint_path:
            # Filter data endpoint requires filter_key
            body = {
                "filter_key": "name",  # Use a common filter key
                "page": 1,
                "limit": 10
            }
        elif "/contacts/filters/data" in endpoint_path:
            # Filter data endpoint requires filter_key
            body = {
                "filter_key": "first_name",  # Use a common filter key
                "page": 1,
                "limit": 10
            }
        elif "/companies" in endpoint_path and method == "POST":
            # Query endpoint
            body = {
                "where": {},
                "page": 1,
                "limit": 10
            }
        elif "/contacts" in endpoint_path and method == "POST":
            # Query endpoint
            body = {
                "where": {},
                "page": 1,
                "limit": 10
            }
        
        test_cases.append({
            "name": "simple_request",
            "description": f"Simple {method} request with body",
            "method": method,
            "endpoint": endpoint_path,
            "body": body,
            "expected_status": [200, 201, 202, 204]
        })
    elif method == "DELETE":
        test_cases.append({
            "name": "simple_delete",
            "description": f"Simple {method} request",
            "method": method,
            "endpoint": endpoint_path,
            "body": None,
            "expected_status": [200, 201, 202, 204]
        })
    
    return test_cases


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
        description="Test Connectra API endpoints",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic test run (uses API key from env or config)
  python connectra_api_tester.py
  
  # Test specific category
  python connectra_api_tester.py --filter-category Companies --verbose
  
  # Custom output directory
  python connectra_api_tester.py --output-dir ./reports
  
  # Comprehensive mode
  python connectra_api_tester.py --mode comprehensive
  
  # Custom API key
  python connectra_api_tester.py --api-key your-api-key-here
        """
    )
    
    parser.add_argument(
        "--base-url",
        type=str,
        default=None,
        help="Connectra API base URL (default: from env or http://127.0.0.1:8000)"
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default=None,
        help="Connectra API key for X-API-Key header (default: from env)"
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
        help="Output directory for reports (default: ./test_reports/connectra)"
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
        "--csv-dir",
        type=str,
        default=None,
        help="Directory containing CSV files (default: ./csv)"
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
        "[bold cyan]Connectra API Test Suite[/bold cyan]\n"
        f"Base URL: [yellow]{args.base_url or 'http://127.0.0.1:8000'}[/yellow]\n"
        f"Mode: [yellow]{args.mode}[/yellow]",
        border_style="cyan"
    ))
    
    # Initialize configuration
    config = ConnectraTestConfig(
        base_url=args.base_url,
        api_key=args.api_key,
        test_mode=args.mode,
        output_dir=args.output_dir
    )
    
    # Initialize authentication handler
    auth_handler = ConnectraAuthHandler(config)
    if not auth_handler.authenticate():
        console.print("[red]Error: API key not configured. Set CONNECTRA_API_KEY env var or use --api-key flag.[/red]")
        sys.exit(1)
    
    console.print("[green]✓[/green] API key configured")
    
    # Load endpoints from CSV files
    if args.csv_dir:
        csv_dir = Path(args.csv_dir)
    else:
        csv_dir = Path(__file__).parent / "csv" / "connectra"
    
    endpoints_by_file = load_all_endpoints(csv_dir)
    
    if not endpoints_by_file:
        console.print(f"[yellow]Warning: No endpoints loaded from CSV files in {csv_dir}[/yellow]")
        console.print("[yellow]Note: Connectra API tester expects CSV files in csv/connectra/ directory[/yellow]")
        # Continue anyway - might test from collection directly
    
    total_endpoints = sum(len(eps) for eps in endpoints_by_file.values())
    if total_endpoints > 0:
        console.print(f"[green]✓[/green] Loaded {total_endpoints} endpoints from {len(endpoints_by_file)} CSV file(s)")
    
    # Initialize components
    executor = ConnectraTestExecutor(config, auth_handler)
    collector = ResultCollector()
    
    # Track which CSV file each endpoint came from
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
        console.print("[yellow]Tip: Create CSV files in csv/connectra/ directory with Connectra endpoints[/yellow]")
        sys.exit(1)
    
    # Group endpoints by category for sequential processing
    categories = group_endpoints_by_category(all_endpoints)
    sorted_categories = sorted(categories.keys())
    
    console.print(f"[green]✓[/green] Organized into {len(sorted_categories)} categories")
    
    # Generate all test cases first
    all_test_cases = []
    for endpoint in all_endpoints:
        test_cases = generate_simple_test_cases(endpoint)
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
                # Find all test cases for this endpoint
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

