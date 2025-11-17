#!/usr/bin/env python3
"""
Test script for Apollo API endpoints: /apollo/contacts and /apollo/contacts/count

This script:
1. Reads Apollo URLs from a CSV file
2. Tests both /apollo/contacts and /apollo/contacts/count endpoints
3. Compares the results and identifies discrepancies
4. Generates a detailed report

Usage:
    python scripts/test_apollo_apis.py --token <your_token> --csv <path_to_csv>
"""

import argparse
import csv
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests
from requests.adapters import HTTPAdapter

try:
    from urllib3.util.retry import Retry
except ImportError:
    # Fallback for older requests versions
    from requests.packages.urllib3.util.retry import Retry


# Configuration
BASE_URL = "http://127.0.0.1:8000"
API_VERSION = "v2"
CONTACTS_ENDPOINT = f"/api/{API_VERSION}/apollo/contacts?limit=50&offset=0"
COUNT_ENDPOINT = f"/api/{API_VERSION}/apollo/contacts/count"

# Request settings
REQUEST_TIMEOUT = 600000  # 10 minutes
MAX_RETRIES = 3
RETRY_BACKOFF_FACTOR = 1


@dataclass
class ApiResult:
    """Container for API call results."""
    url: str
    request_id: Optional[str] = None
    success: bool = False
    status_code: Optional[int] = None
    response_data: Optional[Dict] = None
    error_message: Optional[str] = None
    response_time: float = 0.0
    contacts_count: Optional[int] = None  # For /contacts endpoint
    total_count: Optional[int] = None  # For /count endpoint


@dataclass
class ComparisonResult:
    """Container for comparison results between two APIs."""
    request_id: Optional[str]
    apollo_url: str
    contacts_api_count: Optional[int]
    count_api_count: Optional[int]
    match: bool
    difference: Optional[int] = None
    contacts_api_success: bool = False
    count_api_success: bool = False
    contacts_api_error: Optional[str] = None
    count_api_error: Optional[str] = None
    contacts_response_time: float = 0.0
    count_response_time: float = 0.0


class ApolloApiTester:
    """Main class for testing Apollo API endpoints."""
    
    def __init__(self, token: str, base_url: str = BASE_URL):
        """
        Initialize the tester.
        
        Args:
            token: JWT authentication token
            base_url: Base URL for the API
        """
        self.token = token
        self.base_url = base_url.rstrip('/')
        self.session = self._create_session()
        
    def _create_session(self) -> requests.Session:
        """Create a requests session with retry strategy."""
        session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=MAX_RETRIES,
            backoff_factor=RETRY_BACKOFF_FACTOR,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["POST"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Set default headers
        session.headers.update({
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        })
        
        return session
    
    def test_contacts_endpoint(self, apollo_url: str, limit: Optional[int] = None) -> ApiResult:
        """
        Test the /apollo/contacts endpoint.
        
        Args:
            apollo_url: Apollo.io URL to test
            limit: Optional limit for pagination (if None, gets all results)
            
        Returns:
            ApiResult with response data
        """
        result = ApiResult(url=apollo_url)
        endpoint_url = f"{self.base_url}{CONTACTS_ENDPOINT}"
        
        payload = {"url": apollo_url}
        params = {}
        if limit is not None:
            params["limit"] = limit
        
        start_time = time.time()
        try:
            response = self.session.post(
                endpoint_url,
                json=payload,
                params=params,
                timeout=REQUEST_TIMEOUT
            )
            result.response_time = time.time() - start_time
            result.status_code = response.status_code
            
            if response.status_code == 200:
                result.success = True
                result.response_data = response.json()
                
                # Extract count from results
                if "results" in result.response_data:
                    result.contacts_count = len(result.response_data["results"])
                else:
                    result.contacts_count = 0
            else:
                result.success = False
                try:
                    error_data = response.json()
                    result.error_message = error_data.get("detail", f"HTTP {response.status_code}")
                except:
                    result.error_message = f"HTTP {response.status_code}: {response.text[:200]}"
                    
        except requests.exceptions.Timeout:
            result.error_message = "Request timeout"
        except requests.exceptions.ConnectionError:
            result.error_message = "Connection error"
        except requests.exceptions.RequestException as e:
            result.error_message = f"Request error: {str(e)}"
        except Exception as e:
            result.error_message = f"Unexpected error: {str(e)}"
        
        return result
    
    def test_count_endpoint(self, apollo_url: str) -> ApiResult:
        """
        Test the /apollo/contacts/count endpoint.
        
        Args:
            apollo_url: Apollo.io URL to test
            
        Returns:
            ApiResult with response data
        """
        result = ApiResult(url=apollo_url)
        endpoint_url = f"{self.base_url}{COUNT_ENDPOINT}"
        
        payload = {"url": apollo_url}
        
        start_time = time.time()
        try:
            response = self.session.post(
                endpoint_url,
                json=payload,
                timeout=REQUEST_TIMEOUT
            )
            result.response_time = time.time() - start_time
            result.status_code = response.status_code
            
            if response.status_code == 200:
                result.success = True
                result.response_data = response.json()
                
                # Extract count
                if "count" in result.response_data:
                    result.total_count = result.response_data["count"]
                else:
                    result.total_count = 0
            else:
                result.success = False
                try:
                    error_data = response.json()
                    result.error_message = error_data.get("detail", f"HTTP {response.status_code}")
                except:
                    result.error_message = f"HTTP {response.status_code}: {response.text[:200]}"
                    
        except requests.exceptions.Timeout:
            result.error_message = "Request timeout"
        except requests.exceptions.ConnectionError:
            result.error_message = "Connection error"
        except requests.exceptions.RequestException as e:
            result.error_message = f"Request error: {str(e)}"
        except Exception as e:
            result.error_message = f"Unexpected error: {str(e)}"
        
        return result
    
    def compare_results(
        self,
        contacts_result: ApiResult,
        count_result: ApiResult,
        request_id: Optional[str] = None
    ) -> ComparisonResult:
        """
        Compare results from both API endpoints.
        
        Args:
            contacts_result: Result from /apollo/contacts endpoint
            count_result: Result from /apollo/contacts/count endpoint
            request_id: Optional request ID from CSV
            
        Returns:
            ComparisonResult with comparison data
        """
        comparison = ComparisonResult(
            request_id=request_id,
            apollo_url=contacts_result.url,
            contacts_api_count=contacts_result.contacts_count,
            count_api_count=count_result.total_count,
            contacts_api_success=contacts_result.success,
            count_api_success=count_result.success,
            contacts_api_error=contacts_result.error_message,
            count_api_error=count_result.error_message,
            contacts_response_time=contacts_result.response_time,
            count_response_time=count_result.response_time,
        )
        
        # Only compare if both succeeded
        if contacts_result.success and count_result.success:
            if contacts_result.contacts_count is not None and count_result.total_count is not None:
                comparison.difference = abs(contacts_result.contacts_count - count_result.total_count)
                # Note: contacts_count might be limited by pagination, so we check if it matches or is less
                # If contacts_count equals count_api_count, they match perfectly
                # If contacts_count < count_api_count, it might be due to pagination limits
                comparison.match = (contacts_result.contacts_count == count_result.total_count)
        
        return comparison


def read_csv_urls(csv_path: Path) -> List[Tuple[Optional[str], str]]:
    """
    Read Apollo URLs from CSV file.
    
    Args:
        csv_path: Path to CSV file
        
    Returns:
        List of tuples (request_id, apollo_url)
    """
    urls = []
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row_num, row in enumerate(reader, start=2):  # Start at 2 (row 1 is header)
                apollo_url = row.get('apollo_url', '').strip()
                request_id = row.get('request_id', '').strip() or None
                
                if not apollo_url:
                    print(f"Warning: Row {row_num} has no apollo_url, skipping")
                    continue
                
                if not apollo_url.startswith('http'):
                    print(f"Warning: Row {row_num} has invalid URL format: {apollo_url[:50]}...")
                    continue
                
                urls.append((request_id, apollo_url))
        
        print(f"Successfully read {len(urls)} URLs from CSV")
        return urls
        
    except FileNotFoundError:
        print(f"Error: CSV file not found: {csv_path}")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        sys.exit(1)


def generate_report(
    comparisons: List[ComparisonResult],
    output_file: Optional[Path] = None
) -> None:
    """
    Generate a detailed report of the test results.
    
    Args:
        comparisons: List of comparison results
        output_file: Optional path to save report
    """
    report_lines = []
    report_lines.append("=" * 80)
    report_lines.append("APOLLO API TEST REPORT")
    report_lines.append("=" * 80)
    report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append(f"Total URLs Tested: {len(comparisons)}")
    report_lines.append("")
    
    # Statistics
    successful_contacts = sum(1 for c in comparisons if c.contacts_api_success)
    successful_count = sum(1 for c in comparisons if c.count_api_success)
    both_successful = sum(1 for c in comparisons if c.contacts_api_success and c.count_api_success)
    matches = sum(1 for c in comparisons if c.match)
    
    # Response time statistics
    successful_contacts_times = [c.contacts_response_time for c in comparisons if c.contacts_api_success and c.contacts_response_time > 0]
    successful_count_times = [c.count_response_time for c in comparisons if c.count_api_success and c.count_response_time > 0]
    
    report_lines.append("SUMMARY STATISTICS")
    report_lines.append("-" * 80)
    report_lines.append(f"Successful /contacts calls: {successful_contacts}/{len(comparisons)}")
    report_lines.append(f"Successful /count calls: {successful_count}/{len(comparisons)}")
    report_lines.append(f"Both successful: {both_successful}/{len(comparisons)}")
    report_lines.append(f"Counts match: {matches}/{both_successful}" if both_successful > 0 else "Counts match: N/A")
    
    if successful_contacts_times:
        avg_contacts_time = sum(successful_contacts_times) / len(successful_contacts_times)
        min_contacts_time = min(successful_contacts_times)
        max_contacts_time = max(successful_contacts_times)
        report_lines.append("")
        report_lines.append("RESPONSE TIME STATISTICS - /contacts")
        report_lines.append(f"  Average: {avg_contacts_time:.3f}s")
        report_lines.append(f"  Min: {min_contacts_time:.3f}s")
        report_lines.append(f"  Max: {max_contacts_time:.3f}s")
    
    if successful_count_times:
        avg_count_time = sum(successful_count_times) / len(successful_count_times)
        min_count_time = min(successful_count_times)
        max_count_time = max(successful_count_times)
        report_lines.append("")
        report_lines.append("RESPONSE TIME STATISTICS - /count")
        report_lines.append(f"  Average: {avg_count_time:.3f}s")
        report_lines.append(f"  Min: {min_count_time:.3f}s")
        report_lines.append(f"  Max: {max_count_time:.3f}s")
    
    report_lines.append("")
    
    # Detailed results
    report_lines.append("DETAILED RESULTS")
    report_lines.append("-" * 80)
    
    for idx, comp in enumerate(comparisons, 1):
        report_lines.append(f"\n[{idx}] Request ID: {comp.request_id or 'N/A'}")
        report_lines.append(f"    Apollo URL: {comp.apollo_url[:100]}...")
        report_lines.append(f"    /contacts API: {'✓' if comp.contacts_api_success else '✗'}")
        if comp.contacts_api_success:
            report_lines.append(f"      - Count: {comp.contacts_api_count}")
            report_lines.append(f"      - Response Time: {comp.contacts_response_time:.3f}s")
        else:
            report_lines.append(f"      - Error: {comp.contacts_api_error}")
            if comp.contacts_response_time > 0:
                report_lines.append(f"      - Response Time: {comp.contacts_response_time:.3f}s (failed)")
        
        report_lines.append(f"    /count API: {'✓' if comp.count_api_success else '✗'}")
        if comp.count_api_success:
            report_lines.append(f"      - Count: {comp.count_api_count}")
            report_lines.append(f"      - Response Time: {comp.count_response_time:.3f}s")
        else:
            report_lines.append(f"      - Error: {comp.count_api_error}")
            if comp.count_response_time > 0:
                report_lines.append(f"      - Response Time: {comp.count_response_time:.3f}s (failed)")
        
        if comp.contacts_api_success and comp.count_api_success:
            if comp.match:
                report_lines.append(f"    Comparison: ✓ MATCH ({comp.contacts_api_count} == {comp.count_api_count})")
            else:
                report_lines.append(f"    Comparison: ✗ MISMATCH ({comp.contacts_api_count} vs {comp.count_api_count}, diff: {comp.difference})")
    
    # Print to console
    report_text = "\n".join(report_lines)
    print("\n" + report_text)
    
    # Save to file if specified
    if output_file:
        try:
            output_file.parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(report_text)
            print(f"\nReport saved to: {output_file}")
        except Exception as e:
            print(f"\nWarning: Could not save report to file: {e}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Test Apollo API endpoints and compare results",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/test_apollo_apis.py --token "ey..." --csv "scripts/lead360data/file.csv"
  python scripts/test_apollo_apis.py --token "ey..." --csv "scripts/lead360data/file.csv" --limit 100 --output report.txt
        """
    )
    
    parser.add_argument(
        "--token",
        required=True,
        help="JWT authentication token (starts with 'ey...')"
    )
    
    parser.add_argument(
        "--csv",
        required=True,
        type=Path,
        help="Path to CSV file containing Apollo URLs"
    )
    
    parser.add_argument(
        "--base-url",
        default=BASE_URL,
        help=f"Base URL for API (default: {BASE_URL})"
    )
    
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of results from /contacts endpoint (for testing pagination)"
    )
    
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Path to save detailed report (default: print to console only)"
    )
    
    parser.add_argument(
        "--max-urls",
        type=int,
        default=None,
        help="Maximum number of URLs to test (for quick testing)"
    )
    
    args = parser.parse_args()
    
    # Validate token
    if not args.token.startswith("ey"):
        print("Warning: Token doesn't start with 'ey...', but continuing anyway...")
    
    # Validate CSV file
    if not args.csv.exists():
        print(f"Error: CSV file not found: {args.csv}")
        sys.exit(1)
    
    print("=" * 80)
    print("APOLLO API TESTER")
    print("=" * 80)
    print(f"CSV File: {args.csv}")
    print(f"Base URL: {args.base_url}")
    print(f"Limit: {args.limit if args.limit else 'None (all results)'}")
    print(f"Max URLs: {args.max_urls if args.max_urls else 'All'}")
    print("=" * 80)
    print()
    
    # Read URLs from CSV
    urls = read_csv_urls(args.csv)
    
    if not urls:
        print("Error: No valid URLs found in CSV file")
        sys.exit(1)
    
    # Limit URLs if specified
    if args.max_urls and args.max_urls < len(urls):
        urls = urls[:args.max_urls]
        print(f"Limited to first {args.max_urls} URLs for testing")
    
    # Initialize tester
    tester = ApolloApiTester(token=args.token, base_url=args.base_url)
    
    # Test each URL
    comparisons = []
    total = len(urls)
    
    print(f"\nTesting {total} URLs...\n")
    
    for idx, (request_id, apollo_url) in enumerate(urls, 1):
        print(f"[{idx}/{total}] Testing URL: {apollo_url[:80]}...")
        
        # Test /contacts endpoint
        print("  → Testing /apollo/contacts...", end=" ", flush=True)
        contacts_result = tester.test_contacts_endpoint(apollo_url, limit=args.limit)
        if contacts_result.success:
            print(f"✓ ({contacts_result.contacts_count} results, {contacts_result.response_time:.3f}s)")
        else:
            print(f"✗ ({contacts_result.error_message}, {contacts_result.response_time:.3f}s)")
        
        # Test /count endpoint
        print("  → Testing /apollo/contacts/count...", end=" ", flush=True)
        count_result = tester.test_count_endpoint(apollo_url)
        if count_result.success:
            print(f"✓ ({count_result.total_count} count, {count_result.response_time:.3f}s)")
        else:
            print(f"✗ ({count_result.error_message}, {count_result.response_time:.3f}s)")
        
        # Compare results
        comparison = tester.compare_results(contacts_result, count_result, request_id)
        comparisons.append(comparison)
        
        if comparison.contacts_api_success and comparison.count_api_success:
            if comparison.match:
                print(f"  → Comparison: ✓ MATCH")
            else:
                print(f"  → Comparison: ✗ MISMATCH (diff: {comparison.difference})")
        
        print()
    
    # Generate report
    output_file = args.output or Path("apollo_api_test_report.txt")
    generate_report(comparisons, output_file)
    
    # Exit code based on results
    if all(c.contacts_api_success and c.count_api_success and c.match for c in comparisons):
        print("\n✓ All tests passed!")
        sys.exit(0)
    else:
        print("\n✗ Some tests failed or mismatches found. Check report for details.")
        sys.exit(1)


if __name__ == "__main__":
    main()

