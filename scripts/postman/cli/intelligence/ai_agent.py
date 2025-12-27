"""Core AI agent for intelligent endpoint operation and learning."""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from collections import defaultdict
import statistics


class AIAgent:
    """Core AI agent for learning and intelligent endpoint operation."""
    
    def __init__(self, knowledge_base_path: Optional[Path] = None):
        """Initialize AI agent.
        
        Args:
            knowledge_base_path: Path to knowledge base storage
        """
        if knowledge_base_path is None:
            knowledge_base_path = Path.home() / ".contact360-cli" / "knowledge_base.json"
        
        self.knowledge_base_path = Path(knowledge_base_path)
        self.knowledge_base_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.knowledge_base = self._load_knowledge_base()
        
        # Learning data structures
        self.endpoint_patterns: Dict[str, Dict[str, Any]] = defaultdict(dict)
        self.response_patterns: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.error_patterns: Dict[str, List[str]] = defaultdict(list)
        self.performance_baselines: Dict[str, Dict[str, float]] = defaultdict(dict)
    
    def _load_knowledge_base(self) -> Dict[str, Any]:
        """Load knowledge base from storage.
        
        Returns:
            Knowledge base dictionary
        """
        if not self.knowledge_base_path.exists():
            return {
                "endpoint_patterns": {},
                "response_patterns": {},
                "error_patterns": {},
                "performance_baselines": {},
                "learned_rules": [],
                "optimization_suggestions": [],
                "last_updated": None
            }
        
        try:
            with open(self.knowledge_base_path, 'r') as f:
                return json.load(f)
        except Exception:
            return {
                "endpoint_patterns": {},
                "response_patterns": {},
                "error_patterns": {},
                "performance_baselines": {},
                "learned_rules": [],
                "optimization_suggestions": [],
                "last_updated": None
            }
    
    def _save_knowledge_base(self):
        """Save knowledge base to storage."""
        self.knowledge_base["endpoint_patterns"] = dict(self.endpoint_patterns)
        self.knowledge_base["response_patterns"] = {
            k: v[-100:] for k, v in self.response_patterns.items()  # Keep last 100
        }
        self.knowledge_base["error_patterns"] = dict(self.error_patterns)
        self.knowledge_base["performance_baselines"] = dict(self.performance_baselines)
        self.knowledge_base["last_updated"] = datetime.now().isoformat()
        
        try:
            with open(self.knowledge_base_path, 'w') as f:
                json.dump(self.knowledge_base, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save knowledge base: {e}")
    
    def learn_from_result(self, result: Dict[str, Any], endpoint: Dict[str, Any]):
        """Learn from a test result.
        
        Args:
            result: Test result dictionary
            endpoint: Endpoint dictionary
        """
        # Ensure we have valid method and endpoint
        method = result.get('method') or endpoint.get('method', 'UNKNOWN')
        endpoint_path = result.get('endpoint') or endpoint.get('endpoint', 'UNKNOWN')
        endpoint_key = f"{method} {endpoint_path}"
        
        # Learn response patterns
        if result.get("success"):
            response_data = {
                "timestamp": datetime.now().isoformat(),
                "status_code": result.get("status_code"),
                "response_time_ms": result.get("response_time_ms", 0),
                "response_structure": self._extract_response_structure(result)
            }
            self.response_patterns[endpoint_key].append(response_data)
            
            # Update performance baseline
            response_times = [r["response_time_ms"] for r in self.response_patterns[endpoint_key] if r.get("response_time_ms", 0) > 0]
            if response_times:
                self.performance_baselines[endpoint_key] = {
                    "avg": statistics.mean(response_times),
                    "median": statistics.median(response_times),
                    "p95": sorted(response_times)[int(len(response_times) * 0.95)] if len(response_times) > 0 else 0,
                    "min": min(response_times),
                    "max": max(response_times),
                    "sample_count": len(response_times)
                }
        else:
            # Learn error patterns
            error_msg = result.get("error_message", "")
            if error_msg:
                self.error_patterns[endpoint_key].append(error_msg)
        
        # Update endpoint patterns
        self._update_endpoint_patterns(endpoint_key, result, endpoint)
        
        # Auto-save periodically (every 10 learnings)
        # Use get() to safely access the list even if key doesn't exist yet
        response_count = len(self.response_patterns.get(endpoint_key, []))
        if response_count > 0 and response_count % 10 == 0:
            self._save_knowledge_base()
    
    def _extract_response_structure(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Extract response structure for learning.
        
        Args:
            result: Test result dictionary
        
        Returns:
            Response structure dictionary
        """
        response_body = result.get("response", {}).get("body")
        
        if not response_body:
            return {}
        
        structure = {
            "type": type(response_body).__name__,
            "keys": [],
            "array_length": None
        }
        
        if isinstance(response_body, dict):
            structure["keys"] = list(response_body.keys())[:20]  # Limit to 20 keys
        elif isinstance(response_body, list):
            structure["array_length"] = len(response_body)
            if response_body and isinstance(response_body[0], dict):
                structure["keys"] = list(response_body[0].keys())[:20]
        
        return structure
    
    def _update_endpoint_patterns(self, endpoint_key: str, result: Dict[str, Any], endpoint: Dict[str, Any]):
        """Update endpoint patterns based on result.
        
        Args:
            endpoint_key: Endpoint identifier
            result: Test result dictionary
            endpoint: Endpoint dictionary
        """
        if endpoint_key not in self.endpoint_patterns:
            self.endpoint_patterns[endpoint_key] = {
                "method": result.get("method"),
                "path": result.get("endpoint"),
                "category": endpoint.get("category"),
                "api_version": endpoint.get("api_version"),
                "success_count": 0,
                "failure_count": 0,
                "common_status_codes": defaultdict(int),
                "avg_response_time": 0,
                "requires_auth": endpoint.get("requires_auth", "FALSE").upper() == "TRUE",
                "requires_admin": endpoint.get("requires_admin", "FALSE").upper() == "TRUE"
            }
        
        pattern = self.endpoint_patterns[endpoint_key]
        
        if result.get("success"):
            pattern["success_count"] += 1
        else:
            pattern["failure_count"] += 1
        
        status_code = result.get("status_code")
        if status_code:
            pattern["common_status_codes"][status_code] += 1
        
        # Update average response time
        response_times = [r["response_time_ms"] for r in self.response_patterns[endpoint_key] if r.get("response_time_ms", 0) > 0]
        if response_times:
            pattern["avg_response_time"] = statistics.mean(response_times)
    
    def analyze_endpoint(self, endpoint_key: str) -> Dict[str, Any]:
        """Analyze an endpoint and provide insights.
        
        Args:
            endpoint_key: Endpoint identifier
        
        Returns:
            Analysis dictionary
        """
        analysis = {
            "endpoint": endpoint_key,
            "patterns": self.endpoint_patterns.get(endpoint_key, {}),
            "performance": self.performance_baselines.get(endpoint_key, {}),
            "reliability": self._calculate_reliability(endpoint_key),
            "recommendations": self._generate_recommendations(endpoint_key),
            "anomalies": self._detect_anomalies(endpoint_key)
        }
        
        return analysis
    
    def _calculate_reliability(self, endpoint_key: str) -> Dict[str, Any]:
        """Calculate endpoint reliability metrics.
        
        Args:
            endpoint_key: Endpoint identifier
        
        Returns:
            Reliability metrics dictionary
        """
        pattern = self.endpoint_patterns.get(endpoint_key, {})
        total = pattern.get("success_count", 0) + pattern.get("failure_count", 0)
        
        if total == 0:
            return {"score": 0, "status": "unknown", "total_tests": 0}
        
        success_rate = (pattern.get("success_count", 0) / total) * 100
        
        if success_rate >= 95:
            status = "excellent"
        elif success_rate >= 80:
            status = "good"
        elif success_rate >= 50:
            status = "fair"
        else:
            status = "poor"
        
        return {
            "score": success_rate,
            "status": status,
            "total_tests": total,
            "success_count": pattern.get("success_count", 0),
            "failure_count": pattern.get("failure_count", 0)
        }
    
    def _generate_recommendations(self, endpoint_key: str) -> List[str]:
        """Generate recommendations for an endpoint.
        
        Args:
            endpoint_key: Endpoint identifier
        
        Returns:
            List of recommendation strings
        """
        recommendations = []
        pattern = self.endpoint_patterns.get(endpoint_key, {})
        performance = self.performance_baselines.get(endpoint_key, {})
        reliability = self._calculate_reliability(endpoint_key)
        
        # Reliability recommendations
        if reliability["score"] < 80:
            recommendations.append(
                f"Endpoint has {reliability['failure_count']} failures. Review error patterns and fix issues."
            )
        
        # Performance recommendations
        avg_time = performance.get("avg", 0)
        if avg_time > 5000:
            recommendations.append(
                f"Average response time is {avg_time:.0f}ms. Consider optimizing endpoint performance."
            )
        
        # Status code recommendations
        status_codes = pattern.get("common_status_codes", {})
        if 500 in status_codes:
            recommendations.append(
                "Server errors (500) detected. Check server logs and infrastructure."
            )
        
        if 401 in status_codes and not pattern.get("requires_auth"):
            recommendations.append(
                "Unexpected authentication errors. Verify endpoint authentication requirements."
            )
        
        # Error pattern recommendations
        errors = self.error_patterns.get(endpoint_key, [])
        if len(errors) > 5:
            unique_errors = set(errors[-20:])  # Last 20 errors
            if len(unique_errors) == 1:
                recommendations.append(
                    f"Consistent error pattern detected: {list(unique_errors)[0][:100]}"
                )
        
        return recommendations
    
    def _detect_anomalies(self, endpoint_key: str) -> List[Dict[str, Any]]:
        """Detect anomalies in endpoint behavior.
        
        Args:
            endpoint_key: Endpoint identifier
        
        Returns:
            List of anomaly dictionaries
        """
        anomalies = []
        performance = self.performance_baselines.get(endpoint_key, {})
        recent_responses = self.response_patterns.get(endpoint_key, [])[-10:]  # Last 10
        
        if not recent_responses:
            return anomalies
        
        # Detect performance anomalies
        baseline_avg = performance.get("avg", 0)
        baseline_p95 = performance.get("p95", 0)
        
        for response in recent_responses:
            response_time = response.get("response_time_ms", 0)
            
            # Anomaly: response time > 2x p95
            if baseline_p95 > 0 and response_time > baseline_p95 * 2:
                anomalies.append({
                    "type": "performance",
                    "severity": "high",
                    "message": f"Response time {response_time:.0f}ms exceeds baseline p95 ({baseline_p95:.0f}ms) by 2x",
                    "timestamp": response.get("timestamp")
                })
            
            # Anomaly: response time > 3x average
            if baseline_avg > 0 and response_time > baseline_avg * 3:
                anomalies.append({
                    "type": "performance",
                    "severity": "medium",
                    "message": f"Response time {response_time:.0f}ms exceeds average ({baseline_avg:.0f}ms) by 3x",
                    "timestamp": response.get("timestamp")
                })
        
        # Detect status code anomalies
        pattern = self.endpoint_patterns.get(endpoint_key, {})
        common_codes = pattern.get("common_status_codes", {})
        
        if common_codes:
            most_common = max(common_codes.items(), key=lambda x: x[1])
            expected_code = most_common[0]
            
            for response in recent_responses:
                status_code = response.get("status_code")
                if status_code and status_code != expected_code and status_code >= 400:
                    anomalies.append({
                        "type": "status_code",
                        "severity": "high" if status_code >= 500 else "medium",
                        "message": f"Unexpected status code {status_code} (expected {expected_code})",
                        "timestamp": response.get("timestamp")
                    })
        
        return anomalies
    
    def suggest_test_improvements(self, endpoint: Dict[str, Any], existing_tests: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Suggest test case improvements based on learned patterns.
        
        Args:
            endpoint: Endpoint dictionary
            existing_tests: List of existing test cases
        
        Returns:
            List of suggested test improvements
        """
        suggestions = []
        endpoint_key = f"{endpoint.get('method')} {endpoint.get('endpoint')}"
        
        # Analyze existing tests
        test_coverage = self._analyze_test_coverage(endpoint, existing_tests)
        
        # Suggest missing test cases
        if not test_coverage.get("error_cases"):
            suggestions.append({
                "type": "missing_test",
                "priority": "high",
                "suggestion": "Add error case tests (400, 401, 422, 500)",
                "test_case": self._generate_error_test_case(endpoint)
            })
        
        if not test_coverage.get("edge_cases"):
            suggestions.append({
                "type": "missing_test",
                "priority": "medium",
                "suggestion": "Add edge case tests (empty inputs, boundary values)",
                "test_case": self._generate_edge_case_test(endpoint)
            })
        
        # Suggest performance tests
        performance = self.performance_baselines.get(endpoint_key, {})
        if performance and not test_coverage.get("performance_tests"):
            suggestions.append({
                "type": "performance_test",
                "priority": "medium",
                "suggestion": f"Add performance test (baseline: {performance.get('avg', 0):.0f}ms)",
                "test_case": self._generate_performance_test(endpoint, performance)
            })
        
        # Suggest based on learned error patterns
        errors = self.error_patterns.get(endpoint_key, [])
        if errors:
            common_error = max(set(errors), key=errors.count)
            suggestions.append({
                "type": "error_pattern",
                "priority": "high",
                "suggestion": f"Add test for common error: {common_error[:100]}",
                "test_case": self._generate_error_pattern_test(endpoint, common_error)
            })
        
        return suggestions
    
    def _analyze_test_coverage(self, endpoint: Dict[str, Any], tests: List[Dict[str, Any]]) -> Dict[str, bool]:
        """Analyze test coverage.
        
        Args:
            endpoint: Endpoint dictionary
            tests: List of test cases
        
        Returns:
            Coverage analysis dictionary
        """
        coverage = {
            "error_cases": False,
            "edge_cases": False,
            "performance_tests": False,
            "auth_tests": False
        }
        
        for test in tests:
            expected_status = test.get("expected_status", [])
            
            # Check for error case tests
            if any(code >= 400 for code in expected_status if isinstance(code, int)):
                coverage["error_cases"] = True
            
            # Check for edge cases (empty, null, boundary values)
            body = test.get("body", {})
            if any(v in [None, "", []] for v in body.values() if isinstance(v, (str, list))):
                coverage["edge_cases"] = True
            
            # Check for performance tests
            if "response_time" in test.get("description", "").lower():
                coverage["performance_tests"] = True
            
            # Check for auth tests
            headers = test.get("headers", {})
            if "Authorization" not in headers or headers.get("Authorization") is None:
                coverage["auth_tests"] = True
        
        return coverage
    
    def _generate_error_test_case(self, endpoint: Dict[str, Any]) -> Dict[str, Any]:
        """Generate error test case.
        
        Args:
            endpoint: Endpoint dictionary
        
        Returns:
            Test case dictionary
        """
        return {
            "name": "ai_suggested_error_case",
            "description": "AI-suggested error case test",
            "method": endpoint.get("method", "GET"),
            "endpoint": endpoint.get("endpoint", ""),
            "expected_status": [400, 401, 422, 500],
            "body": {} if endpoint.get("method") in ["POST", "PUT", "PATCH"] else None
        }
    
    def _generate_edge_case_test(self, endpoint: Dict[str, Any]) -> Dict[str, Any]:
        """Generate edge case test.
        
        Args:
            endpoint: Endpoint dictionary
        
        Returns:
            Test case dictionary
        """
        return {
            "name": "ai_suggested_edge_case",
            "description": "AI-suggested edge case test",
            "method": endpoint.get("method", "GET"),
            "endpoint": endpoint.get("endpoint", ""),
            "body": {"empty_string": "", "null_value": None, "empty_array": []} if endpoint.get("method") in ["POST", "PUT", "PATCH"] else None,
            "expected_status": [200, 400, 422]
        }
    
    def _generate_performance_test(self, endpoint: Dict[str, Any], performance: Dict[str, float]) -> Dict[str, Any]:
        """Generate performance test.
        
        Args:
            endpoint: Endpoint dictionary
            performance: Performance baseline dictionary
        
        Returns:
            Test case dictionary
        """
        threshold = performance.get("p95", performance.get("avg", 0)) * 1.5
        
        return {
            "name": "ai_suggested_performance_test",
            "description": f"AI-suggested performance test (threshold: {threshold:.0f}ms)",
            "method": endpoint.get("method", "GET"),
            "endpoint": endpoint.get("endpoint", ""),
            "expected_status": [200],
            "performance_threshold_ms": threshold
        }
    
    def _generate_error_pattern_test(self, endpoint: Dict[str, Any], error_pattern: str) -> Dict[str, Any]:
        """Generate test for specific error pattern.
        
        Args:
            endpoint: Endpoint dictionary
            error_pattern: Error message pattern
        
        Returns:
            Test case dictionary
        """
        return {
            "name": "ai_suggested_error_pattern_test",
            "description": f"AI-suggested test for error pattern: {error_pattern[:50]}",
            "method": endpoint.get("method", "GET"),
            "endpoint": endpoint.get("endpoint", ""),
            "expected_status": [400, 401, 422, 500],
            "body": {} if endpoint.get("method") in ["POST", "PUT", "PATCH"] else None
        }
    
    def get_operation_suggestions(self, endpoint_key: str) -> List[Dict[str, Any]]:
        """Get intelligent suggestions for operating an endpoint.
        
        Args:
            endpoint_key: Endpoint identifier
        
        Returns:
            List of operation suggestions
        """
        suggestions = []
        pattern = self.endpoint_patterns.get(endpoint_key, {})
        performance = self.performance_baselines.get(endpoint_key, {})
        
        # Authentication suggestions
        if pattern.get("requires_auth"):
            suggestions.append({
                "type": "authentication",
                "priority": "critical",
                "suggestion": "Ensure valid authentication token is provided",
                "details": "Endpoint requires authentication. Use 'auth' command in REPL or configure access_token in profile."
            })
        
        # Performance optimization suggestions
        avg_time = performance.get("avg", 0)
        if avg_time > 3000:
            suggestions.append({
                "type": "performance",
                "priority": "high",
                "suggestion": "Consider caching or optimizing endpoint",
                "details": f"Average response time is {avg_time:.0f}ms, which may impact user experience."
            })
        
        # Error handling suggestions
        errors = self.error_patterns.get(endpoint_key, [])
        if errors:
            unique_errors = set(errors[-10:])
            if len(unique_errors) > 0:
                suggestions.append({
                    "type": "error_handling",
                    "priority": "medium",
                    "suggestion": "Implement retry logic for transient errors",
                    "details": f"Endpoint has {len(errors)} recent errors. Consider exponential backoff retry strategy."
                })
        
        # Query parameter suggestions
        if pattern.get("method") == "GET":
            suggestions.append({
                "type": "usage",
                "priority": "low",
                "suggestion": "Use pagination parameters (limit, offset) for large datasets",
                "details": "GET endpoints typically support pagination to improve performance."
            })
        
        return suggestions
    
    def save_knowledge(self):
        """Save all learned knowledge to storage."""
        self._save_knowledge_base()

