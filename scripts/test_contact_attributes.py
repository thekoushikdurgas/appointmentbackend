#!/usr/bin/env python3
"""
Test script for Contact Attribute API endpoints.

This script systematically tests all contact attribute endpoints:
- Company, Company Domains, Title, Seniority, Industry, Department, Keywords, Technologies
- Company Address, Contact Address

It measures response times, validates responses, and generates comprehensive reports.

Usage:
    python scripts/test_contact_attributes.py --token <your_token> [--base-url <url>] [--output <dir>] [--verbose] [--timeout <seconds>]
"""

import argparse
import csv
import json
import sys
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlencode, urljoin

import requests
from requests.adapters import HTTPAdapter

try:
    from urllib3.util.retry import Retry
except ImportError:
    from requests.packages.urllib3.util.retry import Retry


# Default configuration
DEFAULT_BASE_URL = "http://127.0.0.1:8000"
DEFAULT_TIMEOUT = 300000
DEFAULT_OUTPUT_DIR = "scripts/test_results/contact_attributes"
API_PREFIX = "/api/v1"

# Test data
TEST_SEARCH_TERMS = ["tech", "software", "manager", "engineer", "sales"]
TEST_COMPANY_NAMES = ["Microsoft", "Google", "Apple", "Amazon"]

# Performance thresholds
SLOW_ENDPOINT_THRESHOLD = 2.0  # seconds


@dataclass
class ApiTestResult:
    """Container for API test results."""
    endpoint: str
    parameters: Dict[str, Any]
    status_code: Optional[int] = None
    response_time: float = 0.0
    success: bool = False
    response_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    result_count: int = 0
    validation_errors: List[str] = field(default_factory=list)


@dataclass
class EndpointTestConfig:
    """Configuration for testing an endpoint."""
    endpoint_path: str
    test_variations: List[Dict[str, Any]]
    description: str = ""


class ApiTester:
    """Main class for testing API endpoints."""
    
    def __init__(self, token: str, base_url: str = DEFAULT_BASE_URL, timeout: int = DEFAULT_TIMEOUT, verbose: bool = False):
        """
        Initialize the API tester.
        
        Args:
            token: JWT authentication token
            base_url: Base URL for the API
            timeout: Request timeout in seconds
            verbose: Enable verbose logging
        """
        self.token = token
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.verbose = verbose
        self.session = self._create_session()
        
    def _create_session(self) -> requests.Session:
        """Create a requests session with retry strategy."""
        session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Set default headers
        session.headers.update({
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "X-Request-Id": f"test-{int(time.time() * 1000)}"
        })
        
        return session
    
    def test_endpoint(self, endpoint_path: str, params: Optional[Dict[str, Any]] = None) -> ApiTestResult:
        """
        Test a single endpoint with given parameters.
        
        Args:
            endpoint_path: API endpoint path (e.g., "/api/v1/contacts/company/")
            params: Query parameters as dictionary
            
        Returns:
            ApiTestResult with test results
        """
        # Build full URL
        if endpoint_path.startswith("http"):
            url = endpoint_path
        else:
            url = urljoin(self.base_url, endpoint_path)
        
        # Build query string
        query_string = ""
        if params:
            # Filter out None values
            clean_params = {k: v for k, v in params.items() if v is not None}
            query_string = urlencode(clean_params, doseq=True)
            if query_string:
                url = f"{url}?{query_string}"
        
        result = ApiTestResult(
            endpoint=endpoint_path,
            parameters=params or {}
        )
        
        if self.verbose:
            print(f"Testing: {url}")
        
        start_time = time.perf_counter()
        
        try:
            response = self.session.get(url, timeout=self.timeout)
            result.response_time = time.perf_counter() - start_time
            result.status_code = response.status_code
            
            if response.status_code == 200:
                try:
                    result.response_data = response.json()
                    result.success = True
                    
                    # Validate response structure
                    validation_errors = self._validate_response(result.response_data, endpoint_path)
                    result.validation_errors = validation_errors
                    
                    # Count results
                    if isinstance(result.response_data, dict):
                        if "results" in result.response_data:
                            result.result_count = len(result.response_data["results"])
                        elif isinstance(result.response_data.get("data"), list):
                            result.result_count = len(result.response_data["data"])
                    elif isinstance(result.response_data, list):
                        result.result_count = len(result.response_data)
                    
                except json.JSONDecodeError as e:
                    result.success = False
                    result.error_message = f"JSON decode error: {str(e)}"
                    if self.verbose:
                        print(f"  Error: {result.error_message}")
            else:
                result.success = False
                try:
                    error_data = response.json()
                    result.error_message = error_data.get("detail", f"HTTP {response.status_code}")
                except:
                    result.error_message = f"HTTP {response.status_code}: {response.text[:200]}"
                if self.verbose:
                    print(f"  Error: {result.error_message}")
                    
        except requests.exceptions.Timeout:
            result.response_time = time.perf_counter() - start_time
            result.success = False
            result.error_message = f"Request timeout after {self.timeout}s"
            if self.verbose:
                print(f"  Error: {result.error_message}")
                
        except requests.exceptions.ConnectionError as e:
            result.response_time = time.perf_counter() - start_time
            result.success = False
            result.error_message = f"Connection error: {str(e)}"
            if self.verbose:
                print(f"  Error: {result.error_message}")
                
        except requests.exceptions.RequestException as e:
            result.response_time = time.perf_counter() - start_time
            result.success = False
            result.error_message = f"Request error: {str(e)}"
            if self.verbose:
                print(f"  Error: {result.error_message}")
        
        return result
    
    def _validate_response(self, data: Any, endpoint_path: str) -> List[str]:
        """
        Validate response structure and content.
        
        Args:
            data: Response data (dict or list)
            endpoint_path: Endpoint path for context
            
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        # Check if response is a dict (paginated) or list
        if isinstance(data, dict):
            # Check for paginated response structure
            if "results" not in data:
                errors.append("Missing 'results' key in response")
            else:
                if not isinstance(data["results"], list):
                    errors.append("'results' is not a list")
                
                # Check pagination links
                if "next" in data and data["next"] is not None:
                    if not isinstance(data["next"], str):
                        errors.append("'next' should be a string or None")
                
                if "previous" in data and data["previous"] is not None:
                    if not isinstance(data["previous"], str):
                        errors.append("'previous' should be a string or None")
        elif isinstance(data, list):
            # Direct list response
            if not all(isinstance(item, (str, dict)) for item in data):
                errors.append("List items should be strings or dicts")
        else:
            errors.append(f"Unexpected response type: {type(data)}")
        
        return errors
    
    def run_all_tests(self, endpoint_configs: List[EndpointTestConfig]) -> List[ApiTestResult]:
        """
        Run all test configurations.
        
        Args:
            endpoint_configs: List of endpoint test configurations
            
        Returns:
            List of all test results
        """
        all_results = []
        total_tests = sum(len(config.test_variations) for config in endpoint_configs)
        current_test = 0
        
        print(f"\nRunning {total_tests} test variations across {len(endpoint_configs)} endpoints...\n")
        
        for config in endpoint_configs:
            print(f"Testing {config.endpoint_path} ({len(config.test_variations)} variations)...")
            
            for variation in config.test_variations:
                current_test += 1
                result = self.test_endpoint(config.endpoint_path, variation)
                all_results.append(result)
                
                # Print progress
                status = "✓" if result.success else "✗"
                print(f"  [{current_test}/{total_tests}] {status} {result.response_time:.3f}s - {variation.get('search', variation.get('company', 'basic'))}")
        
        return all_results


def create_endpoint_configs() -> List[EndpointTestConfig]:
    """
    Create test configurations for all endpoints.
    
    Returns:
        List of EndpointTestConfig objects
    """
    configs = []
    
    # 1. Company endpoint
    company_variations = [
        {"distinct": True, "limit": 25, "offset": 0},
    ]
    for term in TEST_SEARCH_TERMS[:2]:  # Test with 2 search terms
        company_variations.append({"search": term, "distinct": True, "limit": 25, "offset": 0})
    
    configs.append(EndpointTestConfig(
        endpoint_path=f"{API_PREFIX}/contacts/company/",
        test_variations=company_variations,
        description="Company names endpoint"
    ))
    
    # 2. Company Domains endpoint
    domain_variations = [
        {"distinct": True, "limit": 25, "offset": 0},
    ]
    for term in TEST_SEARCH_TERMS[:2]:
        domain_variations.append({"search": term, "distinct": True, "limit": 25, "offset": 0})
    
    configs.append(EndpointTestConfig(
        endpoint_path=f"{API_PREFIX}/contacts/company/domain/",
        test_variations=domain_variations,
        description="Company domains endpoint"
    ))
    
    # 3. Title endpoint
    title_variations = [
        {"limit": 25, "distinct": True, "offset": 0},
    ]
    for term in TEST_SEARCH_TERMS[:2]:
        title_variations.append({"limit": 25, "search": term, "distinct": True, "offset": 0})
    for company in TEST_COMPANY_NAMES[:2]:
        for term in TEST_SEARCH_TERMS[:1]:
            title_variations.append({"company": company, "limit": 25, "search": term, "distinct": True, "offset": 0})
    
    configs.append(EndpointTestConfig(
        endpoint_path=f"{API_PREFIX}/contacts/title/",
        test_variations=title_variations,
        description="Title endpoint"
    ))
    
    # 4. Seniority endpoint
    seniority_variations = [
        {"distinct": True, "limit": 25, "offset": 0},
    ]
    for term in TEST_SEARCH_TERMS[:2]:
        seniority_variations.append({"search": term, "distinct": True, "limit": 25, "offset": 0})
    for company in TEST_COMPANY_NAMES[:2]:
        for term in TEST_SEARCH_TERMS[:1]:
            seniority_variations.append({"company": company, "search": term, "distinct": True, "limit": 25, "offset": 0})
    
    configs.append(EndpointTestConfig(
        endpoint_path=f"{API_PREFIX}/contacts/seniority/",
        test_variations=seniority_variations,
        description="Seniority endpoint"
    ))
    
    # 5. Industry endpoint
    industry_variations = [
        {"distinct": True, "limit": 25, "offset": 0},
    ]
    for term in TEST_SEARCH_TERMS[:2]:
        industry_variations.append({"search": term, "distinct": True, "limit": 25, "offset": 0})
    for company in TEST_COMPANY_NAMES[:2]:
        for term in TEST_SEARCH_TERMS[:1]:
            industry_variations.append({"company": company, "search": term, "distinct": True, "limit": 25, "offset": 0})
    
    configs.append(EndpointTestConfig(
        endpoint_path=f"{API_PREFIX}/contacts/industry/",
        test_variations=industry_variations,
        description="Industry endpoint"
    ))
    
    # 6. Department endpoint
    department_variations = [
        {"distinct": True, "limit": 25, "offset": 0},
    ]
    for term in TEST_SEARCH_TERMS[:2]:
        department_variations.append({"search": term, "distinct": True, "limit": 25, "offset": 0})
    for company in TEST_COMPANY_NAMES[:2]:
        for term in TEST_SEARCH_TERMS[:1]:
            department_variations.append({"company": company, "search": term, "distinct": True, "limit": 25, "offset": 0})
    
    configs.append(EndpointTestConfig(
        endpoint_path=f"{API_PREFIX}/contacts/department/",
        test_variations=department_variations,
        description="Department endpoint"
    ))
    
    # 7. Keywords endpoint
    keywords_variations = [
        {"distinct": True, "limit": 25, "offset": 0},
    ]
    for term in TEST_SEARCH_TERMS[:2]:
        keywords_variations.append({"search": term, "distinct": True, "limit": 25, "offset": 0})
    for company in TEST_COMPANY_NAMES[:2]:
        for term in TEST_SEARCH_TERMS[:1]:
            keywords_variations.append({"company": company, "search": term, "distinct": True, "limit": 25, "offset": 0})
    
    configs.append(EndpointTestConfig(
        endpoint_path=f"{API_PREFIX}/contacts/keywords/",
        test_variations=keywords_variations,
        description="Keywords endpoint"
    ))
    
    # 8. Technologies endpoint
    technologies_variations = [
        {"distinct": True, "limit": 25, "offset": 0},
    ]
    for term in TEST_SEARCH_TERMS[:2]:
        technologies_variations.append({"search": term, "distinct": True, "limit": 25, "offset": 0})
    for company in TEST_COMPANY_NAMES[:2]:
        for term in TEST_SEARCH_TERMS[:1]:
            technologies_variations.append({"company": company, "search": term, "distinct": True, "limit": 25, "offset": 0})
    
    configs.append(EndpointTestConfig(
        endpoint_path=f"{API_PREFIX}/contacts/technologies/",
        test_variations=technologies_variations,
        description="Technologies endpoint"
    ))
    
    # 9. Company Address endpoint
    company_address_variations = [
        {"distinct": True, "limit": 25, "offset": 0},
    ]
    for term in TEST_SEARCH_TERMS[:2]:
        company_address_variations.append({"search": term, "distinct": True, "limit": 25, "offset": 0})
    
    configs.append(EndpointTestConfig(
        endpoint_path=f"{API_PREFIX}/contacts/company_address/",
        test_variations=company_address_variations,
        description="Company address endpoint"
    ))
    
    # 10. Contact Address endpoint
    contact_address_variations = [
        {"distinct": True, "limit": 25, "offset": 0},
    ]
    for term in TEST_SEARCH_TERMS[:2]:
        contact_address_variations.append({"search": term, "distinct": True, "limit": 25, "offset": 0})
    
    configs.append(EndpointTestConfig(
        endpoint_path=f"{API_PREFIX}/contacts/contact_address/",
        test_variations=contact_address_variations,
        description="Contact address endpoint"
    ))
    
    return configs


class TestReportGenerator:
    """Generate test reports in multiple formats."""
    
    def __init__(self, output_dir: str):
        """
        Initialize report generator.
        
        Args:
            output_dir: Directory to save reports
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    def generate_all_reports(self, results: List[ApiTestResult]) -> Dict[str, str]:
        """
        Generate all report types.
        
        Args:
            results: List of test results
            
        Returns:
            Dictionary mapping report type to file path
        """
        report_paths = {}
        
        # Generate summary JSON report
        json_path = self.output_dir / f"summary_{self.timestamp}.json"
        self._generate_json_report(results, json_path)
        report_paths["json"] = str(json_path)
        
        # Generate detailed CSV report
        csv_path = self.output_dir / f"detailed_{self.timestamp}.csv"
        self._generate_csv_report(results, csv_path)
        report_paths["csv"] = str(csv_path)
        
        # Generate performance Markdown report
        md_path = self.output_dir / f"performance_{self.timestamp}.md"
        self._generate_markdown_report(results, md_path)
        report_paths["markdown"] = str(md_path)
        
        return report_paths
    
    def _generate_json_report(self, results: List[ApiTestResult], filepath: Path):
        """Generate JSON summary report."""
        # Calculate statistics
        total_tests = len(results)
        successful_tests = sum(1 for r in results if r.success)
        failed_tests = total_tests - successful_tests
        success_rate = (successful_tests / total_tests * 100) if total_tests > 0 else 0
        
        response_times = [r.response_time for r in results if r.success]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        min_response_time = min(response_times) if response_times else 0
        max_response_time = max(response_times) if response_times else 0
        
        # Group by endpoint
        endpoint_stats = {}
        for result in results:
            endpoint = result.endpoint
            if endpoint not in endpoint_stats:
                endpoint_stats[endpoint] = {
                    "total": 0,
                    "successful": 0,
                    "failed": 0,
                    "response_times": []
                }
            
            endpoint_stats[endpoint]["total"] += 1
            if result.success:
                endpoint_stats[endpoint]["successful"] += 1
                endpoint_stats[endpoint]["response_times"].append(result.response_time)
            else:
                endpoint_stats[endpoint]["failed"] += 1
        
        # Calculate per-endpoint averages
        for endpoint, stats in endpoint_stats.items():
            if stats["response_times"]:
                stats["avg_response_time"] = sum(stats["response_times"]) / len(stats["response_times"])
                stats["min_response_time"] = min(stats["response_times"])
                stats["max_response_time"] = max(stats["response_times"])
            else:
                stats["avg_response_time"] = 0
                stats["min_response_time"] = 0
                stats["max_response_time"] = 0
            del stats["response_times"]  # Remove raw list from output
        
        report = {
            "timestamp": self.timestamp,
            "summary": {
                "total_tests": total_tests,
                "successful_tests": successful_tests,
                "failed_tests": failed_tests,
                "success_rate_percent": round(success_rate, 2)
            },
            "performance": {
                "avg_response_time_seconds": round(avg_response_time, 3),
                "min_response_time_seconds": round(min_response_time, 3),
                "max_response_time_seconds": round(max_response_time, 3)
            },
            "endpoints": endpoint_stats
        }
        
        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2)
    
    def _generate_csv_report(self, results: List[ApiTestResult], filepath: Path):
        """Generate detailed CSV report."""
        with open(filepath, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                "Endpoint",
                "Parameters",
                "Status Code",
                "Response Time (s)",
                "Success",
                "Result Count",
                "Error Message",
                "Validation Errors"
            ])
            
            for result in results:
                writer.writerow([
                    result.endpoint,
                    json.dumps(result.parameters),
                    result.status_code or "",
                    round(result.response_time, 3),
                    result.success,
                    result.result_count,
                    result.error_message or "",
                    "; ".join(result.validation_errors) if result.validation_errors else ""
                ])
    
    def _generate_markdown_report(self, results: List[ApiTestResult], filepath: Path):
        """Generate performance Markdown report."""
        # Calculate statistics
        total_tests = len(results)
        successful_tests = sum(1 for r in results if r.success)
        failed_tests = total_tests - successful_tests
        success_rate = (successful_tests / total_tests * 100) if total_tests > 0 else 0
        
        response_times = [r.response_time for r in results if r.success]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        min_response_time = min(response_times) if response_times else 0
        max_response_time = max(response_times) if response_times else 0
        
        # Find slow endpoints
        slow_endpoints = [
            (r.endpoint, r.response_time, r.parameters)
            for r in results
            if r.success and r.response_time > SLOW_ENDPOINT_THRESHOLD
        ]
        slow_endpoints.sort(key=lambda x: x[1], reverse=True)
        
        # Group by endpoint for statistics
        endpoint_stats = {}
        for result in results:
            endpoint = result.endpoint
            if endpoint not in endpoint_stats:
                endpoint_stats[endpoint] = {
                    "total": 0,
                    "successful": 0,
                    "failed": 0,
                    "times": []
                }
            endpoint_stats[endpoint]["total"] += 1
            if result.success:
                endpoint_stats[endpoint]["successful"] += 1
                endpoint_stats[endpoint]["times"].append(result.response_time)
            else:
                endpoint_stats[endpoint]["failed"] += 1
        
        with open(filepath, 'w') as f:
            f.write("# Contact Attribute API Test Report\n\n")
            f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("## Summary Statistics\n\n")
            f.write(f"- **Total Tests:** {total_tests}\n")
            f.write(f"- **Successful:** {successful_tests}\n")
            f.write(f"- **Failed:** {failed_tests}\n")
            f.write(f"- **Success Rate:** {success_rate:.2f}%\n\n")
            
            f.write("## Performance Overview\n\n")
            f.write(f"- **Average Response Time:** {avg_response_time:.3f}s\n")
            f.write(f"- **Minimum Response Time:** {min_response_time:.3f}s\n")
            f.write(f"- **Maximum Response Time:** {max_response_time:.3f}s\n\n")
            
            if slow_endpoints:
                f.write(f"## Slow Endpoints (> {SLOW_ENDPOINT_THRESHOLD}s)\n\n")
                f.write("| Endpoint | Response Time | Parameters |\n")
                f.write("|----------|---------------|------------|\n")
                for endpoint, resp_time, params in slow_endpoints[:10]:  # Top 10 slowest
                    params_str = ", ".join(f"{k}={v}" for k, v in list(params.items())[:3])
                    f.write(f"| `{endpoint}` | {resp_time:.3f}s | {params_str} |\n")
                f.write("\n")
            
            f.write("## Per-Endpoint Statistics\n\n")
            f.write("| Endpoint | Total | Successful | Failed | Avg Time (s) |\n")
            f.write("|----------|-------|------------|--------|--------------|\n")
            
            for endpoint, stats in sorted(endpoint_stats.items()):
                avg_time = sum(stats["times"]) / len(stats["times"]) if stats["times"] else 0
                f.write(f"| `{endpoint}` | {stats['total']} | {stats['successful']} | {stats['failed']} | {avg_time:.3f} |\n")
            
            f.write("\n## Recommendations\n\n")
            if slow_endpoints:
                f.write(f"- {len(slow_endpoints)} endpoint(s) exceeded the {SLOW_ENDPOINT_THRESHOLD}s threshold\n")
                f.write("- Consider optimizing slow endpoints or adding caching\n")
            else:
                f.write("- All endpoints are performing within acceptable thresholds\n")
            
            if failed_tests > 0:
                f.write(f"- {failed_tests} test(s) failed - review error messages in CSV report\n")


def main():
    """Main entry point for the test script."""
    parser = argparse.ArgumentParser(
        description="Test Contact Attribute API endpoints",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/test_contact_attributes.py --token "your_token_here"
  python scripts/test_contact_attributes.py --token "your_token" --base-url "http://54.87.173.234:8000" --verbose
  python scripts/test_contact_attributes.py --token "your_token" --output "results/" --timeout 60
        """
    )
    
    parser.add_argument(
        "--token",
        required=True,
        help="JWT authentication token (required)"
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=f"Base URL for the API (default: {DEFAULT_BASE_URL})"
    )
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT_DIR,
        help=f"Output directory for reports (default: {DEFAULT_OUTPUT_DIR})"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
        help=f"Request timeout in seconds (default: {DEFAULT_TIMEOUT})"
    )
    
    args = parser.parse_args()
    
    try:
        # Create API tester
        tester = ApiTester(
            token=args.token,
            base_url=args.base_url,
            timeout=args.timeout,
            verbose=args.verbose
        )
        
        # Create endpoint configurations
        endpoint_configs = create_endpoint_configs()
        
        # Run all tests
        print("=" * 70)
        print("Contact Attribute API Test Suite")
        print("=" * 70)
        start_time = time.time()
        
        results = tester.run_all_tests(endpoint_configs)
        
        total_time = time.time() - start_time
        
        # Generate reports
        print(f"\nGenerating reports...")
        report_generator = TestReportGenerator(args.output)
        report_paths = report_generator.generate_all_reports(results)
        
        # Print summary
        print("\n" + "=" * 70)
        print("Test Summary")
        print("=" * 70)
        successful = sum(1 for r in results if r.success)
        failed = len(results) - successful
        success_rate = (successful / len(results) * 100) if results else 0
        
        print(f"Total Tests: {len(results)}")
        print(f"Successful: {successful}")
        print(f"Failed: {failed}")
        print(f"Success Rate: {success_rate:.2f}%")
        print(f"Total Execution Time: {total_time:.2f}s")
        print(f"\nReports saved to:")
        for report_type, path in report_paths.items():
            print(f"  - {report_type.upper()}: {path}")
        print("=" * 70)
        
        # Exit with error code if any tests failed
        sys.exit(1 if failed > 0 else 0)
        
    except KeyboardInterrupt:
        print("\n\nTest execution interrupted by user.")
        sys.exit(130)
    except Exception as e:
        print(f"\n\nFatal error: {str(e)}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

