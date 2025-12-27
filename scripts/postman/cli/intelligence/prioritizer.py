"""Test prioritization for smart test execution."""

from typing import Dict, Any, List, Optional
from collections import defaultdict
from datetime import datetime, timedelta


class TestPrioritizer:
    """Prioritizes tests based on historical data and patterns."""
    
    def __init__(self):
        """Initialize test prioritizer."""
        self.endpoint_history: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    
    def prioritize_tests(
        self, 
        endpoints: List[Dict[str, Any]], 
        historical_results: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """Prioritize endpoints for testing.
        
        Args:
            endpoints: List of endpoint dictionaries
            historical_results: Optional historical test results
        
        Returns:
            Prioritized list of endpoints
        """
        if historical_results:
            self._update_history(historical_results)
        
        prioritized = []
        
        for endpoint in endpoints:
            priority_score = self._calculate_priority_score(endpoint)
            prioritized.append({
                "endpoint": endpoint,
                "priority": priority_score,
                "reason": self._get_priority_reason(endpoint, priority_score)
            })
        
        # Sort by priority (highest first)
        prioritized.sort(key=lambda x: x["priority"], reverse=True)
        
        return prioritized
    
    def _update_history(self, results: List[Dict[str, Any]]):
        """Update endpoint history from results.
        
        Args:
            results: List of test result dictionaries
        """
        for result in results:
            endpoint_key = f"{result.get('method')} {result.get('endpoint')}"
            self.endpoint_history[endpoint_key].append({
                "timestamp": datetime.now(),
                "success": result.get("success", False),
                "response_time_ms": result.get("response_time_ms", 0),
                "status_code": result.get("status_code")
            })
    
    def _calculate_priority_score(self, endpoint: Dict[str, Any]) -> float:
        """Calculate priority score for an endpoint.
        
        Args:
            endpoint: Endpoint dictionary
        
        Returns:
            Priority score (0-100, higher = more important)
        """
        score = 50.0  # Base score
        
        endpoint_key = f"{endpoint.get('method')} {endpoint.get('endpoint')}"
        history = self.endpoint_history.get(endpoint_key, [])
        
        # Recent failures increase priority
        recent_failures = sum(
            1 for h in history[-5:] 
            if not h.get("success") and 
            (datetime.now() - h.get("timestamp", datetime.now())).days < 7
        )
        score += recent_failures * 10
        
        # Critical endpoints (auth, billing) get higher priority
        category = endpoint.get("category", "").lower()
        if "auth" in category or "billing" in category:
            score += 20
        
        # Admin endpoints get lower priority (less frequently used)
        if endpoint.get("requires_admin", "FALSE").upper() == "TRUE":
            score -= 10
        
        # GET endpoints typically more important than others
        if endpoint.get("method", "").upper() == "GET":
            score += 5
        
        # Recent changes (no history) get medium priority
        if not history:
            score += 5
        
        return min(100.0, max(0.0, score))
    
    def _get_priority_reason(self, endpoint: Dict[str, Any], score: float) -> str:
        """Get reason for priority score.
        
        Args:
            endpoint: Endpoint dictionary
            score: Priority score
        
        Returns:
            Reason string
        """
        reasons = []
        
        endpoint_key = f"{endpoint.get('method')} {endpoint.get('endpoint')}"
        history = self.endpoint_history.get(endpoint_key, [])
        
        if history:
            recent_failures = sum(1 for h in history[-5:] if not h.get("success"))
            if recent_failures > 0:
                reasons.append(f"{recent_failures} recent failure(s)")
        
        category = endpoint.get("category", "").lower()
        if "auth" in category or "billing" in category:
            reasons.append("critical category")
        
        if not reasons:
            reasons.append("standard priority")
        
        return ", ".join(reasons)

