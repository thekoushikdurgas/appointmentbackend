"""Report generator for API testing."""

import json
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
import csv


class ReportGenerator:
    """Generates test reports in multiple formats."""
    
    def __init__(self, output_dir: Path):
        """Initialize report generator.
        
        Args:
            output_dir: Output directory for reports
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_json_report(self, results: Dict[str, Any]) -> Path:
        """Generate JSON report.
        
        Args:
            results: Complete results dictionary
        
        Returns:
            Path to generated JSON file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"test_results_{timestamp}.json"
        filepath = self.output_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        # Also create a latest.json symlink/reference
        latest_path = self.output_dir / "test_results_latest.json"
        with open(latest_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        return filepath
    
    def generate_html_report(self, results: Dict[str, Any]) -> Path:
        """Generate HTML report.
        
        Args:
            results: Complete results dictionary
        
        Returns:
            Path to generated HTML file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"test_report_{timestamp}.html"
        filepath = self.output_dir / filename
        
        summary = results["summary"]
        test_run = results["test_run"]
        
        html_content = self._generate_html_content(results, summary, test_run)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        # Also create a latest.html
        latest_path = self.output_dir / "test_report_latest.html"
        with open(latest_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return filepath
    
    def _generate_html_content(self, results: Dict[str, Any], summary: Dict[str, Any], test_run: Dict[str, Any]) -> str:
        """Generate HTML content.
        
        Args:
            results: Complete results dictionary
            summary: Summary statistics
            test_run: Test run metadata
        
        Returns:
            HTML content string
        """
        passed = summary["passed"]
        failed = summary["failed"]
        total = summary["total_tests"]
        success_rate = summary["success_rate"]
        
        # Analyze failures by category
        failure_analysis = self._analyze_failures(results.get("detailed_results", []))
        failure_analysis_html = self._generate_failure_analysis_html(failure_analysis)
        
        # Generate category breakdown
        category_rows = ""
        for category, stats in summary["category_stats"].items():
            category_rows += f"""
            <tr>
                <td>{category}</td>
                <td>{stats['total']}</td>
                <td><span class="badge badge-success">{stats['passed']}</span></td>
                <td><span class="badge badge-danger">{stats['failed']}</span></td>
                <td>{stats['success_rate']:.1f}%</td>
            </tr>
            """
        
        # Generate detailed results table
        detail_rows = ""
        for result in results["detailed_results"]:
            # Handle skipped tests
            if result.get("skipped"):
                status_class = "warning"
                status_text = "SKIP"
                status_code = "N/A"
            else:
                status_class = "success" if result["success"] else "danger"
                status_text = "PASS" if result["success"] else "FAIL"
                status_code = result.get("status_code", "N/A")
            
            error_msg = result.get("error_message", "")
            if error_msg and len(error_msg) > 100:
                error_msg = error_msg[:100] + "..."
            
            detail_rows += f"""
            <tr class="table-{status_class}">
                <td>{result['method']}</td>
                <td>{result['endpoint']}</td>
                <td>{result['test_case_name']}</td>
                <td><span class="badge badge-{status_class}">{status_text}</span></td>
                <td>{status_code}</td>
                <td>{result.get('response_time_ms', 0):.1f}ms</td>
                <td>{result['category']}</td>
                <td>{error_msg or '-'}</td>
            </tr>
            """
        
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Contact360 API Test Report</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: #f5f5f5;
            padding: 20px;
            color: #333;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            padding: 30px;
        }}
        h1 {{
            color: #2c3e50;
            margin-bottom: 10px;
        }}
        .timestamp {{
            color: #7f8c8d;
            margin-bottom: 30px;
        }}
        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .summary-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
        }}
        .summary-card.success {{
            background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        }}
        .summary-card.danger {{
            background: linear-gradient(135deg, #eb3349 0%, #f45c43 100%);
        }}
        .summary-card h3 {{
            font-size: 2.5em;
            margin-bottom: 10px;
        }}
        .summary-card p {{
            font-size: 0.9em;
            opacity: 0.9;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background: #f8f9fa;
            font-weight: 600;
            color: #2c3e50;
        }}
        tr:hover {{
            background: #f8f9fa;
        }}
        .badge {{
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.85em;
            font-weight: 600;
        }}
        .badge-success {{
            background: #28a745;
            color: white;
        }}
        .badge-danger {{
            background: #dc3545;
            color: white;
        }}
        .badge-warning {{
            background: #ffc107;
            color: #212529;
        }}
        .table-success {{
            background: #d4edda;
        }}
        .table-danger {{
            background: #f8d7da;
        }}
        .table-warning {{
            background: #fff3cd;
        }}
        .section {{
            margin-top: 40px;
        }}
        .section h2 {{
            color: #2c3e50;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #667eea;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Contact360 API Test Report</h1>
        <p class="timestamp">Generated: {test_run['timestamp']} | Duration: {test_run['duration_seconds']:.1f}s</p>
        
        <div class="summary">
            <div class="summary-card">
                <h3>{total}</h3>
                <p>Total Tests</p>
            </div>
            <div class="summary-card success">
                <h3>{passed}</h3>
                <p>Passed</p>
            </div>
            <div class="summary-card danger">
                <h3>{failed}</h3>
                <p>Failed</p>
            </div>
            <div class="summary-card">
                <h3>{success_rate:.1f}%</h3>
                <p>Success Rate</p>
            </div>
        </div>
        
        <div class="section">
            <h2>Results by Category</h2>
            <table>
                <thead>
                    <tr>
                        <th>Category</th>
                        <th>Total</th>
                        <th>Passed</th>
                        <th>Failed</th>
                        <th>Success Rate</th>
                    </tr>
                </thead>
                <tbody>
                    {category_rows}
                </tbody>
            </table>
        </div>
        
        {failure_analysis_html}
        
        <div class="section">
            <h2>Detailed Results</h2>
            <table>
                <thead>
                    <tr>
                        <th>Method</th>
                        <th>Endpoint</th>
                        <th>Test Case</th>
                        <th>Status</th>
                        <th>Status Code</th>
                        <th>Response Time</th>
                        <th>Category</th>
                        <th>Error Message</th>
                    </tr>
                </thead>
                <tbody>
                    {detail_rows}
                </tbody>
            </table>
        </div>
    </div>
</body>
</html>
"""
        return html
    
    def _analyze_failures(self, detailed_results: list) -> Dict[str, Any]:
        """Analyze failures and categorize them by root cause.
        
        Args:
            detailed_results: List of test result dictionaries
        
        Returns:
            Dictionary with failure analysis
        """
        analysis = {
            "authentication_issues": [],
            "connection_errors": [],
            "missing_parameters": [],
            "validation_errors": [],
            "other_errors": [],
        }
        
        for result in detailed_results:
            if result.get("success") or result.get("skipped"):
                continue
            
            error_msg = result.get("error_message", "")
            status_code = result.get("status_code")
            endpoint = result.get("endpoint", "")
            
            # Categorize failures
            if status_code == 401 or "Authentication credentials were not provided" in error_msg:
                analysis["authentication_issues"].append(result)
            elif "Connection error" in error_msg or "Request error" in error_msg or "Max retries exceeded" in error_msg:
                analysis["connection_errors"].append(result)
            elif status_code == 422 and ("missing" in error_msg.lower() or "Field required" in error_msg):
                analysis["missing_parameters"].append(result)
            elif status_code in [422, 400] and ("validation" in error_msg.lower() or "invalid" in error_msg.lower()):
                analysis["validation_errors"].append(result)
            else:
                analysis["other_errors"].append(result)
        
        return analysis
    
    def _generate_failure_analysis_html(self, failure_analysis: Dict[str, Any]) -> str:
        """Generate HTML for failure analysis section.
        
        Args:
            failure_analysis: Dictionary with categorized failures
        
        Returns:
            HTML string for failure analysis section
        """
        total_failures = sum(len(failures) for failures in failure_analysis.values())
        
        if total_failures == 0:
            return ""
        
        html = """
        <div class="section">
            <h2>Failure Analysis</h2>
        """
        
        # Authentication Issues
        if failure_analysis["authentication_issues"]:
            count = len(failure_analysis["authentication_issues"])
            html += f"""
            <div style="margin-bottom: 20px; padding: 15px; background: #fff3cd; border-left: 4px solid #ffc107; border-radius: 4px;">
                <h3 style="margin-top: 0; color: #856404;">Authentication Issues ({count})</h3>
                <p>These tests failed due to missing or invalid authentication tokens.</p>
                <ul style="margin: 10px 0; padding-left: 20px;">
                    <li>Ensure test user credentials are configured correctly</li>
                    <li>Check that authentication handler is working properly</li>
                    <li>For admin endpoints, ensure admin credentials are configured</li>
                </ul>
            </div>
            """
        
        # Connection Errors
        if failure_analysis["connection_errors"]:
            count = len(failure_analysis["connection_errors"])
            html += f"""
            <div style="margin-bottom: 20px; padding: 15px; background: #f8d7da; border-left: 4px solid #dc3545; border-radius: 4px;">
                <h3 style="margin-top: 0; color: #721c24;">Connection Errors ({count})</h3>
                <p>These tests failed due to connection issues, often caused by placeholder UUIDs.</p>
                <ul style="margin: 10px 0; padding-left: 20px;">
                    <li>Run setup_tests.py to create test entities with valid UUIDs</li>
                    <li>Check that the API server is running and accessible</li>
                    <li>Verify network connectivity and firewall settings</li>
                </ul>
            </div>
            """
        
        # Missing Parameters
        if failure_analysis["missing_parameters"]:
            count = len(failure_analysis["missing_parameters"])
            html += f"""
            <div style="margin-bottom: 20px; padding: 15px; background: #d1ecf1; border-left: 4px solid #0c5460; border-radius: 4px;">
                <h3 style="margin-top: 0; color: #0c5460;">Missing Parameters ({count})</h3>
                <p>These tests failed because required query parameters were not provided.</p>
                <ul style="margin: 10px 0; padding-left: 20px;">
                    <li>Update test generator to include required query parameters</li>
                    <li>Check endpoint documentation for required parameters</li>
                    <li>Verify parameter names and formats match API expectations</li>
                </ul>
            </div>
            """
        
        # Validation Errors
        if failure_analysis["validation_errors"]:
            count = len(failure_analysis["validation_errors"])
            html += f"""
            <div style="margin-bottom: 20px; padding: 15px; background: #d4edda; border-left: 4px solid #28a745; border-radius: 4px;">
                <h3 style="margin-top: 0; color: #155724;">Validation Errors ({count})</h3>
                <p>These tests failed due to data validation issues.</p>
                <ul style="margin: 10px 0; padding-left: 20px;">
                    <li>Review test data to ensure it matches API schema requirements</li>
                    <li>Check that data types and formats are correct</li>
                    <li>Verify required fields are present in request bodies</li>
                </ul>
            </div>
            """
        
        # Other Errors
        if failure_analysis["other_errors"]:
            count = len(failure_analysis["other_errors"])
            html += f"""
            <div style="margin-bottom: 20px; padding: 15px; background: #e2e3e5; border-left: 4px solid #6c757d; border-radius: 4px;">
                <h3 style="margin-top: 0; color: #383d41;">Other Errors ({count})</h3>
                <p>These tests failed for other reasons. Check detailed results for more information.</p>
            </div>
            """
        
        html += "</div>"
        return html
    
    def update_csv(self, csv_path: Path, results: Dict[str, Any]) -> bool:
        """Update CSV file with test results.
        
        Args:
            csv_path: Path to CSV file
            results: Complete results dictionary
        
        Returns:
            True if update successful, False otherwise
        """
        try:
            # Read existing CSV
            rows = []
            with open(csv_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                fieldnames = reader.fieldnames
                rows = list(reader)
            
            # Create a mapping of endpoint -> latest result
            endpoint_results = {}
            for result in results["detailed_results"]:
                endpoint_key = f"{result['method']}|{result['endpoint']}"
                # Keep the most recent result for each endpoint
                if endpoint_key not in endpoint_results:
                    endpoint_results[endpoint_key] = result
                elif result.get("response_time_ms", 0) > endpoint_results[endpoint_key].get("response_time_ms", 0):
                    endpoint_results[endpoint_key] = result
            
            # Update rows
            for row in rows:
                method = row.get("method", "")
                endpoint = row.get("endpoint", "")
                endpoint_key = f"{method}|{endpoint}"
                
                if endpoint_key in endpoint_results:
                    result = endpoint_results[endpoint_key]
                    # Only update fields that exist in fieldnames and convert None to empty string
                    status_code = result.get("status_code")
                    row["status_code"] = str(status_code) if status_code is not None else ""
                    response_time = result.get("response_time_ms", 0)
                    row["response_time_ms"] = f"{response_time:.2f}" if response_time is not None else "0.00"
                    row["success"] = "TRUE" if result.get("success", False) else "FALSE"
                    error_message = result.get("error_message")
                    row["error_message"] = str(error_message) if error_message is not None else ""
                    row["test_timestamp"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%fZ")
            
            # Filter rows to only include fields in fieldnames and convert None to empty string
            filtered_rows = []
            for row in rows:
                filtered_row = {}
                for field in fieldnames:
                    value = row.get(field)
                    # Convert None to empty string, keep other values as-is
                    filtered_row[field] = "" if value is None else str(value)
                filtered_rows.append(filtered_row)
            
            # Write updated CSV
            with open(csv_path, 'w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(filtered_rows)
            
            return True
        except Exception as e:
            print(f"Error updating CSV: {e}")
            return False

