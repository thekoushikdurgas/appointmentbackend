"""Script to analyze error patterns from application logs."""

import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


def extract_error_info(line: str) -> Optional[Dict[str, str]]:
    """Extract error information from a log line."""
    # Pattern: timestamp - logger - level - message | Context: {...} | Performance: {...}
    pattern = r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) - ([^-]+) - (\w+) - (.+?)(?:\s+\| Context: (.+?))?(?:\s+\| Performance: (.+?))?$'
    match = re.match(pattern, line)
    if not match:
        return None
    
    timestamp, logger, level, message, context_str, perf_str = match.groups()
    
    # Extract endpoint from message or context
    endpoint = None
    status_code = None
    
    # Try to extract from message
    endpoint_match = re.search(r'(\w+)\s+([/\w\-{}]+)\s+-\s+(\d+)', message)
    if endpoint_match:
        method = endpoint_match.group(1)
        endpoint = endpoint_match.group(2)
        status_code = int(endpoint_match.group(3))
    
    return {
        "timestamp": timestamp,
        "logger": logger,
        "level": level,
        "message": message,
        "endpoint": endpoint or "unknown",
        "status_code": str(status_code) if status_code else "unknown",
        "context": context_str or "",
    }


def extract_query_info(line: str) -> Optional[Dict[str, str]]:
    """Extract slow query information from a log line."""
    # Pattern: Slow query: SELECT | Context: {...} | Performance: {...}
    if "Slow query" not in line:
        return None
    
    # Extract query type and table
    query_type_match = re.search(r'Slow query: (\w+)', line)
    table_match = re.search(r'"table":\s*"([^"]+)"', line)
    duration_match = re.search(r'"duration_ms":\s*([\d.]+)', line)
    
    return {
        "query_type": query_type_match.group(1) if query_type_match else "unknown",
        "table": table_match.group(1) if table_match else "unknown",
        "duration_ms": duration_match.group(1) if duration_match else "unknown",
    }


def analyze_error_logs(log_file: str = "backend/logs/app.log") -> Dict:
    """Analyze error patterns from logs.
    
    Args:
        log_file: Path to log file
        
    Returns:
        Dictionary with error analysis results
    """
    log_path = Path(log_file)
    if not log_path.exists():
        return {"error": f"Log file not found: {log_file}"}
    
    errors = {"422": [], "404": [], "400": [], "500": []}
    slow_queries = []
    validation_errors = []
    
    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            # Parse HTTP status code errors
            if " - 422" in line:
                error_info = extract_error_info(line)
                if error_info:
                    errors["422"].append(error_info)
                    if "validation" in error_info["message"].lower():
                        validation_errors.append(error_info)
            elif " - 404" in line:
                error_info = extract_error_info(line)
                if error_info:
                    errors["404"].append(error_info)
            elif " - 400" in line:
                error_info = extract_error_info(line)
                if error_info:
                    errors["400"].append(error_info)
            elif " - 500" in line:
                error_info = extract_error_info(line)
                if error_info:
                    errors["500"].append(error_info)
            
            # Parse slow queries
            if "Slow query" in line:
                query_info = extract_query_info(line)
                if query_info:
                    slow_queries.append(query_info)
    
    # Analyze patterns
    top_422_endpoints = Counter([e["endpoint"] for e in errors["422"]]).most_common(10)
    top_404_endpoints = Counter([e["endpoint"] for e in errors["404"]]).most_common(10)
    top_400_endpoints = Counter([e["endpoint"] for e in errors["400"]]).most_common(10)
    
    top_slow_tables = Counter([q["table"] for q in slow_queries]).most_common(10)
    
    return {
        "error_summary": {
            "422": len(errors["422"]),
            "404": len(errors["404"]),
            "400": len(errors["400"]),
            "500": len(errors["500"]),
        },
        "slow_query_count": len(slow_queries),
        "top_422_errors": top_422_endpoints,
        "top_404_errors": top_404_endpoints,
        "top_400_errors": top_400_endpoints,
        "top_slow_tables": top_slow_tables,
        "validation_error_count": len(validation_errors),
        "total_errors": sum(len(v) for v in errors.values()),
    }


def print_analysis_report(analysis: Dict) -> None:
    """Print a formatted analysis report."""
    print("=" * 80)
    print("ERROR ANALYSIS REPORT")
    print("=" * 80)
    print()
    
    print("Error Summary:")
    print("-" * 80)
    for status_code, count in analysis.get("error_summary", {}).items():
        print(f"  {status_code}: {count} errors")
    print(f"  Total: {analysis.get('total_errors', 0)} errors")
    print()
    
    print("Slow Queries:")
    print("-" * 80)
    print(f"  Total slow queries: {analysis.get('slow_query_count', 0)}")
    print("  Top slow tables:")
    for table, count in analysis.get("top_slow_tables", [])[:5]:
        print(f"    - {table}: {count} slow queries")
    print()
    
    print("Top 422 Validation Errors:")
    print("-" * 80)
    for endpoint, count in analysis.get("top_422_errors", [])[:5]:
        print(f"  {endpoint}: {count} errors")
    print()
    
    print("Top 404 Not Found Errors:")
    print("-" * 80)
    for endpoint, count in analysis.get("top_404_errors", [])[:5]:
        print(f"  {endpoint}: {count} errors")
    print()
    
    print("Top 400 Bad Request Errors:")
    print("-" * 80)
    for endpoint, count in analysis.get("top_400_errors", [])[:5]:
        print(f"  {endpoint}: {count} errors")
    print()
    
    print("=" * 80)


if __name__ == "__main__":
    import sys
    
    log_file = sys.argv[1] if len(sys.argv) > 1 else "backend/logs/app.log"
    analysis = analyze_error_logs(log_file)
    
    if "error" in analysis:
        print(f"Error: {analysis['error']}")
        sys.exit(1)
    
    print_analysis_report(analysis)

