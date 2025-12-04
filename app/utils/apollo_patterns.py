"""Utility for detecting common Apollo filter patterns and optimizing query paths."""

from typing import Dict, List, Set

from app.core.logging import get_logger

logger = get_logger(__name__)


class ApolloPatternDetector:
    """Detects common Apollo filter patterns for optimization."""
    
    # Common filter patterns based on usage statistics
    COMMON_PATTERNS = {
        "high_frequency_location": {
            "params": ["personLocations[]"],
            "usage": 0.85,  # 85% of queries
            "description": "Person location filters (most common)",
        },
        "high_frequency_employees": {
            "params": ["organizationNumEmployeesRanges[]"],
            "usage": 0.82,  # 82% of queries
            "description": "Company employee range filters",
        },
        "high_frequency_titles": {
            "params": ["personTitles[]"],
            "usage": 0.77,  # 77% of queries
            "description": "Job title filters",
        },
        "email_verification": {
            "params": ["contactEmailStatusV2[]"],
            "usage": 0.57,  # 57% of queries
            "description": "Email verification status filters",
        },
        "combined_location_employees": {
            "params": ["personLocations[]", "organizationNumEmployeesRanges[]"],
            "usage": 0.70,  # Estimated 70% when both present
            "description": "Combined location and employee filters",
        },
        "executive_search": {
            "params": ["personTitles[]", "personSeniorities[]", "contactEmailStatusV2[]"],
            "usage": 0.30,  # Estimated
            "description": "Executive-level search with verified emails",
        },
    }
    
    @staticmethod
    def detect_patterns(raw_parameters: Dict[str, List[str]]) -> Set[str]:
        """
        Detect common Apollo filter patterns in the given parameters.
        
        Args:
            raw_parameters: Dictionary of Apollo URL parameters
            
        Returns:
            Set of detected pattern names
        """
        detected_patterns = set()
        param_keys = set(raw_parameters.keys())
        
        for pattern_name, pattern_info in ApolloPatternDetector.COMMON_PATTERNS.items():
            pattern_params = set(pattern_info["params"])
            # Check if all pattern parameters are present
            if pattern_params.issubset(param_keys):
                detected_patterns.add(pattern_name)
                logger.debug(
                    "Detected Apollo pattern '%s': %s",
                    pattern_name,
                    pattern_info["description"],
                )
        
        return detected_patterns
    
    @staticmethod
    def get_pattern_info(pattern_name: str) -> Dict:
        """
        Get information about a specific pattern.
        
        Args:
            pattern_name: Name of the pattern
            
        Returns:
            Pattern information dictionary or None if not found
        """
        return ApolloPatternDetector.COMMON_PATTERNS.get(pattern_name)
    
    @staticmethod
    def should_use_optimized_path(raw_parameters: Dict[str, List[str]]) -> bool:
        """
        Determine if an optimized query path should be used based on detected patterns.
        
        Currently, all queries use optimized paths (EXISTS subqueries, conditional joins),
        but this can be used for future optimizations or logging.
        
        Args:
            raw_parameters: Dictionary of Apollo URL parameters
            
        Returns:
            True if optimized path should be used (always True currently)
        """
        patterns = ApolloPatternDetector.detect_patterns(raw_parameters)
        
        # Log detected patterns for monitoring
        if patterns:
            logger.debug(
                "Detected %d Apollo patterns: %s",
                len(patterns),
                ", ".join(sorted(patterns)),
            )
        
        # All queries use optimized paths, but we can track patterns
        return True

