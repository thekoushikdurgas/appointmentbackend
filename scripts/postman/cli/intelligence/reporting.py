"""Enhanced reporting with dashboards, trends, and insights."""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import statistics


class EnhancedReporter:
    """Enhanced reporting with analytics and insights."""
    
    def __init__(self, reports_dir: Path):
        """Initialize enhanced reporter.
        
        Args:
            reports_dir: Directory containing test reports
        """
        self.reports_dir = Path(reports_dir)
        self.reports_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_dashboard(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate dashboard data from results.
        
        Args:
            results: Test results dictionary
        
        Returns:
            Dashboard data dictionary
        """
        summary = results.get("summary", {})
        detailed_results = results.get("detailed_results", [])
        
        dashboard = {
            "overview": {
                "total_tests": summary.get("total_tests", 0),
                "passed": summary.get("passed", 0),
                "failed": summary.get("failed", 0),
                "skipped": summary.get("skipped", 0),
                "success_rate": summary.get("success_rate", 0),
                "duration_seconds": summary.get("duration_seconds", 0)
            },
            "trends": self._calculate_trends(detailed_results),
            "category_breakdown": summary.get("category_stats", {}),
            "performance_metrics": self._calculate_performance_metrics(detailed_results),
            "health_score": self._calculate_health_score(summary, detailed_results)
        }
        
        return dashboard
    
    def _calculate_trends(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate trends from results.
        
        Args:
            results: List of test result dictionaries
        
        Returns:
            Trends dictionary
        """
        trends = {
            "response_time_trend": [],
            "failure_rate_by_time": [],
            "endpoint_stability": {}
        }
        
        # Group by endpoint and calculate averages
        endpoint_data = defaultdict(lambda: {"times": [], "successes": 0, "failures": 0})
        
        for result in results:
            endpoint = f"{result.get('method')} {result.get('endpoint')}"
            response_time = result.get("response_time_ms", 0)
            
            if response_time > 0:
                endpoint_data[endpoint]["times"].append(response_time)
            
            if result.get("success") and not result.get("skipped"):
                endpoint_data[endpoint]["successes"] += 1
            elif not result.get("skipped"):
                endpoint_data[endpoint]["failures"] += 1
        
        # Calculate endpoint stability
        for endpoint, data in endpoint_data.items():
            total = data["successes"] + data["failures"]
            if total > 0:
                stability = (data["successes"] / total) * 100
                trends["endpoint_stability"][endpoint] = {
                    "stability_score": stability,
                    "avg_response_time": statistics.mean(data["times"]) if data["times"] else 0,
                    "total_tests": total
                }
        
        return trends
    
    def _calculate_performance_metrics(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate performance metrics.
        
        Args:
            results: List of test result dictionaries
        
        Returns:
            Performance metrics dictionary
        """
        response_times = [r.get("response_time_ms", 0) for r in results if r.get("response_time_ms", 0) > 0]
        
        if not response_times:
            return {
                "avg_response_time_ms": 0,
                "median_response_time_ms": 0,
                "p95_response_time_ms": 0,
                "p99_response_time_ms": 0,
                "slowest_endpoints": []
            }
        
        sorted_times = sorted(response_times)
        n = len(sorted_times)
        
        metrics = {
            "avg_response_time_ms": statistics.mean(response_times),
            "median_response_time_ms": statistics.median(response_times),
            "p95_response_time_ms": sorted_times[int(n * 0.95)] if n > 0 else 0,
            "p99_response_time_ms": sorted_times[int(n * 0.99)] if n > 0 else 0,
            "slowest_endpoints": self._get_slowest_endpoints(results)
        }
        
        return metrics
    
    def _get_slowest_endpoints(self, results: List[Dict[str, Any]], limit: int = 10) -> List[Dict[str, Any]]:
        """Get slowest endpoints.
        
        Args:
            results: List of test result dictionaries
            limit: Maximum number of endpoints to return
        
        Returns:
            List of slowest endpoint dictionaries
        """
        endpoint_times = defaultdict(list)
        
        for result in results:
            endpoint = f"{result.get('method')} {result.get('endpoint')}"
            response_time = result.get("response_time_ms", 0)
            if response_time > 0:
                endpoint_times[endpoint].append(response_time)
        
        slowest = []
        for endpoint, times in endpoint_times.items():
            avg_time = statistics.mean(times)
            slowest.append({
                "endpoint": endpoint,
                "avg_response_time_ms": avg_time,
                "max_response_time_ms": max(times),
                "test_count": len(times)
            })
        
        slowest.sort(key=lambda x: x["avg_response_time_ms"], reverse=True)
        return slowest[:limit]
    
    def _calculate_health_score(self, summary: Dict[str, Any], results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate overall health score.
        
        Args:
            summary: Summary statistics
            results: List of test result dictionaries
        
        Returns:
            Health score dictionary
        """
        total = summary.get("total_tests", 0)
        passed = summary.get("passed", 0)
        skipped = summary.get("skipped", 0)
        
        if total == 0:
            return {"score": 0, "status": "unknown", "factors": []}
        
        effective_total = total - skipped
        if effective_total == 0:
            return {"score": 100, "status": "no_tests", "factors": []}
        
        # Base score from pass rate
        pass_rate = (passed / effective_total) * 100
        
        # Adjust for performance issues
        performance_penalty = 0
        slow_count = sum(1 for r in results if r.get("response_time_ms", 0) > 5000)
        if slow_count > 0:
            performance_penalty = min(10, (slow_count / effective_total) * 10)
        
        # Final score
        score = max(0, pass_rate - performance_penalty)
        
        # Determine status
        if score >= 90:
            status = "excellent"
        elif score >= 75:
            status = "good"
        elif score >= 50:
            status = "fair"
        else:
            status = "poor"
        
        factors = []
        if pass_rate < 100:
            factors.append(f"Test failures: {100 - pass_rate:.1f}%")
        if performance_penalty > 0:
            factors.append(f"Performance issues: {slow_count} slow endpoints")
        
        return {
            "score": score,
            "status": status,
            "factors": factors
        }
    
    def save_dashboard(self, dashboard: Dict[str, Any], filename: Optional[str] = None) -> Path:
        """Save dashboard to file.
        
        Args:
            dashboard: Dashboard data dictionary
            filename: Optional filename (default: dashboard_<timestamp>.json)
        
        Returns:
            Path to saved file
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"dashboard_{timestamp}.json"
        
        filepath = self.reports_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(dashboard, f, indent=2, ensure_ascii=False)
        
        # Also save as latest
        latest_path = self.reports_dir / "dashboard_latest.json"
        with open(latest_path, 'w', encoding='utf-8') as f:
            json.dump(dashboard, f, indent=2, ensure_ascii=False)
        
        return filepath
    
    def generate_trend_report(self, days: int = 7) -> Dict[str, Any]:
        """Generate trend report from historical data.
        
        Args:
            days: Number of days to analyze
        
        Returns:
            Trend report dictionary
        """
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # Load all reports in the date range
        reports = []
        for report_file in self.reports_dir.glob("test_results_*.json"):
            try:
                # Extract timestamp from filename
                timestamp_str = report_file.stem.replace("test_results_", "")
                report_time = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                
                if report_time >= cutoff_date:
                    with open(report_file, 'r') as f:
                        report_data = json.load(f)
                        report_data["_timestamp"] = report_time.isoformat()
                        reports.append(report_data)
            except Exception:
                continue
        
        if not reports:
            return {"message": "No historical data available"}
        
        # Sort by timestamp
        reports.sort(key=lambda x: x.get("_timestamp", ""))
        
        # Calculate trends
        trend_data = {
            "period_days": days,
            "report_count": len(reports),
            "success_rate_trend": [],
            "test_count_trend": [],
            "performance_trend": []
        }
        
        for report in reports:
            summary = report.get("summary", {})
            trend_data["success_rate_trend"].append({
                "date": report.get("_timestamp"),
                "success_rate": summary.get("success_rate", 0)
            })
            trend_data["test_count_trend"].append({
                "date": report.get("_timestamp"),
                "total_tests": summary.get("total_tests", 0)
            })
        
        return trend_data

