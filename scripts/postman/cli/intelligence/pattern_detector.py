"""Pattern detection for intelligent test insights."""

from typing import Dict, Any, List
from collections import defaultdict
import re


class PatternDetector:
    """Detects patterns in test results and endpoint behavior."""
    
    def __init__(self):
        """Initialize pattern detector."""
        self.patterns: Dict[str, Any] = defaultdict(list)
    
    def detect_patterns(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Detect patterns in test results.
        
        Args:
            results: List of test result dictionaries
        
        Returns:
            Dictionary of detected patterns
        """
        patterns = {
            "error_patterns": self._detect_error_patterns(results),
            "performance_patterns": self._detect_performance_patterns(results),
            "category_patterns": self._detect_category_patterns(results),
            "endpoint_patterns": self._detect_endpoint_patterns(results)
        }
        
        return patterns
    
    def _detect_error_patterns(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Detect error patterns.
        
        Args:
            results: List of test result dictionaries
        
        Returns:
            List of error pattern dictionaries
        """
        error_patterns = defaultdict(lambda: {"count": 0, "endpoints": set()})
        
        for result in results:
            if not result.get("success") and not result.get("skipped"):
                error_msg = result.get("error_message", "")
                status_code = result.get("status_code")
                endpoint = f"{result.get('method')} {result.get('endpoint')}"
                
                # Categorize errors
                if status_code == 401:
                    pattern_key = "authentication_required"
                elif status_code == 404:
                    pattern_key = "resource_not_found"
                elif status_code == 422:
                    pattern_key = "validation_error"
                elif status_code == 500:
                    pattern_key = "server_error"
                elif "timeout" in error_msg.lower():
                    pattern_key = "timeout"
                elif "connection" in error_msg.lower():
                    pattern_key = "connection_error"
                else:
                    pattern_key = "other_error"
                
                error_patterns[pattern_key]["count"] += 1
                error_patterns[pattern_key]["endpoints"].add(endpoint)
        
        return [
            {
                "pattern": pattern,
                "count": data["count"],
                "affected_endpoints": len(data["endpoints"]),
                "endpoint_list": list(data["endpoints"])[:5]  # Top 5
            }
            for pattern, data in error_patterns.items()
        ]
    
    def _detect_performance_patterns(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Detect performance patterns.
        
        Args:
            results: List of test result dictionaries
        
        Returns:
            List of performance pattern dictionaries
        """
        endpoint_times = defaultdict(list)
        
        for result in results:
            if result.get("success"):
                endpoint = f"{result.get('method')} {result.get('endpoint')}"
                response_time = result.get("response_time_ms", 0)
                endpoint_times[endpoint].append(response_time)
        
        performance_patterns = []
        
        for endpoint, times in endpoint_times.items():
            if times:
                avg_time = sum(times) / len(times)
                max_time = max(times)
                min_time = min(times)
                
                # Detect slow endpoints
                if avg_time > 3000:
                    performance_patterns.append({
                        "pattern": "slow_endpoint",
                        "endpoint": endpoint,
                        "avg_response_time_ms": avg_time,
                        "max_response_time_ms": max_time,
                        "min_response_time_ms": min_time
                    })
                
                # Detect inconsistent performance
                if max_time > avg_time * 2:
                    performance_patterns.append({
                        "pattern": "inconsistent_performance",
                        "endpoint": endpoint,
                        "avg_response_time_ms": avg_time,
                        "max_response_time_ms": max_time,
                        "variance": max_time - avg_time
                    })
        
        return performance_patterns
    
    def _detect_category_patterns(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Detect patterns by category.
        
        Args:
            results: List of test result dictionaries
        
        Returns:
            Category pattern dictionary
        """
        category_stats = defaultdict(lambda: {"total": 0, "passed": 0, "failed": 0})
        
        for result in results:
            category = result.get("category", "Unknown")
            category_stats[category]["total"] += 1
            
            if result.get("success") and not result.get("skipped"):
                category_stats[category]["passed"] += 1
            elif not result.get("skipped"):
                category_stats[category]["failed"] += 1
        
        patterns = {}
        for category, stats in category_stats.items():
            if stats["total"] > 0:
                success_rate = (stats["passed"] / stats["total"]) * 100
                patterns[category] = {
                    "total": stats["total"],
                    "passed": stats["passed"],
                    "failed": stats["failed"],
                    "success_rate": success_rate,
                    "health": "good" if success_rate > 80 else "warning" if success_rate > 50 else "critical"
                }
        
        return patterns
    
    def _detect_endpoint_patterns(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Detect patterns specific to endpoints.
        
        Args:
            results: List of test result dictionaries
        
        Returns:
            List of endpoint pattern dictionaries
        """
        endpoint_stats = defaultdict(lambda: {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "response_times": [],
            "status_codes": []
        })
        
        for result in results:
            endpoint = f"{result.get('method')} {result.get('endpoint')}"
            endpoint_stats[endpoint]["total"] += 1
            
            if result.get("success") and not result.get("skipped"):
                endpoint_stats[endpoint]["passed"] += 1
            elif not result.get("skipped"):
                endpoint_stats[endpoint]["failed"] += 1
            
            response_time = result.get("response_time_ms", 0)
            if response_time > 0:
                endpoint_stats[endpoint]["response_times"].append(response_time)
            
            status_code = result.get("status_code")
            if status_code:
                endpoint_stats[endpoint]["status_codes"].append(status_code)
        
        patterns = []
        for endpoint, stats in endpoint_stats.items():
            if stats["total"] > 0:
                failure_rate = (stats["failed"] / stats["total"]) * 100
                avg_response_time = (
                    sum(stats["response_times"]) / len(stats["response_times"])
                    if stats["response_times"] else 0
                )
                
                # Detect problematic endpoints
                if failure_rate > 50:
                    patterns.append({
                        "pattern": "high_failure_rate",
                        "endpoint": endpoint,
                        "failure_rate": failure_rate,
                        "total_tests": stats["total"]
                    })
                
                # Detect slow endpoints
                if avg_response_time > 5000:
                    patterns.append({
                        "pattern": "slow_response",
                        "endpoint": endpoint,
                        "avg_response_time_ms": avg_response_time
                    })
        
        return patterns

