"""Result analyzer for intelligent test insights."""

from typing import Dict, Any, List
from collections import defaultdict
from datetime import datetime, timedelta


class ResultAnalyzer:
    """Analyzes test results to provide intelligent insights."""
    
    def __init__(self):
        """Initialize result analyzer."""
        self.historical_results: List[Dict[str, Any]] = []
    
    def analyze_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze test results and provide insights.
        
        Args:
            results: Test results dictionary from ResultCollector
        
        Returns:
            Analysis dictionary with insights
        """
        summary = results.get("summary", {})
        detailed_results = results.get("detailed_results", [])
        
        analysis = {
            "overall_health": self._calculate_health_score(summary),
            "trends": self._analyze_trends(detailed_results),
            "problematic_endpoints": self._identify_problematic_endpoints(detailed_results),
            "performance_issues": self._identify_performance_issues(detailed_results),
            "recommendations": []
        }
        
        # Generate recommendations
        analysis["recommendations"] = self._generate_recommendations(analysis)
        
        return analysis
    
    def _calculate_health_score(self, summary: Dict[str, Any]) -> float:
        """Calculate overall health score (0-100).
        
        Args:
            summary: Summary statistics
        
        Returns:
            Health score (0-100)
        """
        total = summary.get("total_tests", 0)
        if total == 0:
            return 0.0
        
        passed = summary.get("passed", 0)
        skipped = summary.get("skipped", 0)
        
        # Health score based on pass rate (skipped tests don't count against)
        effective_total = total - skipped
        if effective_total == 0:
            return 100.0
        
        return (passed / effective_total) * 100.0
    
    def _analyze_trends(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze trends in test results.
        
        Args:
            results: List of test result dictionaries
        
        Returns:
            Trends dictionary
        """
        trends = {
            "failure_patterns": defaultdict(int),
            "slow_endpoints": [],
            "error_types": defaultdict(int)
        }
        
        for result in results:
            # Initialize endpoint_key for all results (used in both failure and performance analysis)
            endpoint_key = f"{result.get('method')} {result.get('endpoint')}"
            
            if not result.get("success") and not result.get("skipped"):
                # Analyze failure patterns
                trends["failure_patterns"][endpoint_key] += 1
                
                # Analyze error types
                error_msg = result.get("error_message", "")
                if "401" in error_msg or "Authentication" in error_msg:
                    trends["error_types"]["authentication"] += 1
                elif "404" in error_msg or "Not Found" in error_msg:
                    trends["error_types"]["not_found"] += 1
                elif "422" in error_msg or "validation" in error_msg.lower():
                    trends["error_types"]["validation"] += 1
                elif "500" in error_msg or "server" in error_msg.lower():
                    trends["error_types"]["server_error"] += 1
                else:
                    trends["error_types"]["other"] += 1
            
            # Identify slow endpoints (>5 seconds)
            response_time = result.get("response_time_ms", 0)
            if response_time > 5000:
                trends["slow_endpoints"].append({
                    "endpoint": endpoint_key,
                    "response_time_ms": response_time
                })
        
        # Sort slow endpoints
        trends["slow_endpoints"].sort(key=lambda x: x["response_time_ms"], reverse=True)
        
        return trends
    
    def _identify_problematic_endpoints(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify endpoints with consistent failures.
        
        Args:
            results: List of test result dictionaries
        
        Returns:
            List of problematic endpoint dictionaries
        """
        endpoint_stats = defaultdict(lambda: {"total": 0, "failed": 0, "errors": []})
        
        for result in results:
            endpoint_key = f"{result.get('method')} {result.get('endpoint')}"
            endpoint_stats[endpoint_key]["total"] += 1
            
            if not result.get("success") and not result.get("skipped"):
                endpoint_stats[endpoint_key]["failed"] += 1
                endpoint_stats[endpoint_key]["errors"].append(result.get("error_message", ""))
        
        problematic = []
        for endpoint, stats in endpoint_stats.items():
            failure_rate = stats["failed"] / stats["total"] if stats["total"] > 0 else 0
            if failure_rate > 0.5:  # More than 50% failure rate
                problematic.append({
                    "endpoint": endpoint,
                    "failure_rate": failure_rate,
                    "total_tests": stats["total"],
                    "failed_tests": stats["failed"],
                    "common_errors": self._get_common_errors(stats["errors"])
                })
        
        # Sort by failure rate
        problematic.sort(key=lambda x: x["failure_rate"], reverse=True)
        
        return problematic
    
    def _identify_performance_issues(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify performance issues.
        
        Args:
            results: List of test result dictionaries
        
        Returns:
            List of performance issue dictionaries
        """
        performance_issues = []
        
        for result in results:
            response_time = result.get("response_time_ms", 0)
            
            # Flag endpoints taking more than 3 seconds
            if response_time > 3000:
                performance_issues.append({
                    "endpoint": f"{result.get('method')} {result.get('endpoint')}",
                    "response_time_ms": response_time,
                    "severity": "high" if response_time > 10000 else "medium"
                })
        
        # Sort by response time
        performance_issues.sort(key=lambda x: x["response_time_ms"], reverse=True)
        
        return performance_issues[:10]  # Return top 10
    
    def _get_common_errors(self, errors: List[str]) -> List[str]:
        """Get most common error messages.
        
        Args:
            errors: List of error messages
        
        Returns:
            List of common error messages
        """
        error_counts = defaultdict(int)
        for error in errors:
            if error:
                # Normalize error messages
                normalized = error[:100]  # First 100 chars
                error_counts[normalized] += 1
        
        # Return top 3 most common errors
        sorted_errors = sorted(error_counts.items(), key=lambda x: x[1], reverse=True)
        return [error for error, _ in sorted_errors[:3]]
    
    def _generate_recommendations(self, analysis: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on analysis.
        
        Args:
            analysis: Analysis dictionary
        
        Returns:
            List of recommendation strings
        """
        recommendations = []
        
        health_score = analysis.get("overall_health", 100)
        if health_score < 80:
            recommendations.append(
                f"Overall health score is {health_score:.1f}%. Review failing tests and address issues."
            )
        
        problematic = analysis.get("problematic_endpoints", [])
        if problematic:
            recommendations.append(
                f"Found {len(problematic)} problematic endpoint(s). Review and fix these endpoints."
            )
        
        performance_issues = analysis.get("performance_issues", [])
        if performance_issues:
            recommendations.append(
                f"Found {len(performance_issues)} performance issue(s). Consider optimizing slow endpoints."
            )
        
        error_types = analysis.get("trends", {}).get("error_types", {})
        if error_types.get("authentication", 0) > 0:
            recommendations.append(
                "Authentication errors detected. Verify credentials and token refresh mechanism."
            )
        
        if error_types.get("server_error", 0) > 0:
            recommendations.append(
                "Server errors detected. Check server logs and infrastructure health."
            )
        
        if not recommendations:
            recommendations.append("All systems operational. No immediate action required.")
        
        return recommendations

