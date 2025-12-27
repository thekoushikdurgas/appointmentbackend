"""Result collector for API testing."""

import time
from typing import Dict, Any, List
from collections import defaultdict


class ResultCollector:
    """Collects and organizes test results."""
    
    def __init__(self):
        """Initialize result collector."""
        self.start_time = time.time()
        self.results: List[Dict[str, Any]] = []
        self.results_by_category: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.results_by_endpoint: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    
    def add_result(self, result: Dict[str, Any], endpoint: Dict[str, Any]):
        """Add a test result.
        
        Args:
            result: Test result dictionary
            endpoint: Endpoint dictionary from CSV
        """
        # Add endpoint metadata
        result["api_version"] = endpoint.get("api_version", "v1")
        result["category"] = endpoint.get("category", "Other")
        result["endpoint_description"] = endpoint.get("description", "")
        
        # Store result
        self.results.append(result)
        
        # Organize by category
        category = result["category"]
        self.results_by_category[category].append(result)
        
        # Organize by endpoint
        endpoint_key = f"{result['method']} {result['endpoint']}"
        self.results_by_endpoint[endpoint_key].append(result)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics.
        
        Returns:
            Summary dictionary
        """
        total_tests = len(self.results)
        passed = sum(1 for r in self.results if r["success"] and not r.get("skipped", False))
        skipped = sum(1 for r in self.results if r.get("skipped", False))
        failed = total_tests - passed - skipped
        duration = time.time() - self.start_time
        
        # Count by category
        category_stats = {}
        for category, results in self.results_by_category.items():
            category_total = len(results)
            category_passed = sum(1 for r in results if r["success"] and not r.get("skipped", False))
            category_skipped = sum(1 for r in results if r.get("skipped", False))
            category_stats[category] = {
                "total": category_total,
                "passed": category_passed,
                "failed": category_total - category_passed - category_skipped,
                "skipped": category_skipped,
                "success_rate": (category_passed / category_total * 100) if category_total > 0 else 0
            }
        
        # Count by endpoint
        endpoint_stats = {}
        for endpoint_key, results in self.results_by_endpoint.items():
            endpoint_total = len(results)
            endpoint_passed = sum(1 for r in results if r["success"])
            endpoint_stats[endpoint_key] = {
                "total": endpoint_total,
                "passed": endpoint_passed,
                "failed": endpoint_total - endpoint_passed,
                "success_rate": (endpoint_passed / endpoint_total * 100) if endpoint_total > 0 else 0
            }
        
        # Count unique endpoints tested
        unique_endpoints = len(self.results_by_endpoint)
        
        return {
            "total_tests": total_tests,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "success_rate": (passed / total_tests * 100) if total_tests > 0 else 0,
            "duration_seconds": duration,
            "unique_endpoints": unique_endpoints,
            "category_stats": category_stats,
            "endpoint_stats": endpoint_stats
        }
    
    def get_all_results(self) -> Dict[str, Any]:
        """Get all results in structured format.
        
        Returns:
            Complete results dictionary
        """
        summary = self.get_summary()
        
        return {
            "test_run": {
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(self.start_time)),
                "total_endpoints": summary["unique_endpoints"],
                "total_tests": summary["total_tests"],
                "passed": summary["passed"],
                "failed": summary["failed"],
                "success_rate": summary["success_rate"],
                "duration_seconds": summary["duration_seconds"]
            },
            "summary": summary,
            "results_by_category": dict(self.results_by_category),
            "detailed_results": self.results
        }
    
    def get_failed_tests(self) -> List[Dict[str, Any]]:
        """Get all failed test results.
        
        Returns:
            List of failed test results
        """
        return [r for r in self.results if not r["success"]]
    
    def get_passed_tests(self) -> List[Dict[str, Any]]:
        """Get all passed test results.
        
        Returns:
            List of passed test results
        """
        return [r for r in self.results if r["success"]]

