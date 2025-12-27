"""Performance analysis script for application logs.

This script parses application logs to identify:
- Slow queries by table and operation
- Error patterns
- Endpoint response times
- Database connection pool issues
"""

import json
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


def parse_log_line(line: str) -> Optional[Dict]:
    """Parse a log line and extract relevant information."""
    # Pattern: timestamp - logger - level - message | Context: {...} | Performance: {...}
    pattern = r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) - ([^-]+) - (\w+) - (.+?)(?:\s+\| Context: (.+?))?(?:\s+\| Performance: (.+?))?$'
    match = re.match(pattern, line)
    if not match:
        return None
    
    timestamp, logger, level, message, context_str, perf_str = match.groups()
    
    # Try to parse context and performance as JSON
    context = {}
    performance = {}
    
    if context_str:
        try:
            context = json.loads(context_str)
        except (json.JSONDecodeError, ValueError):
            pass
    
    if perf_str:
        try:
            performance = json.loads(perf_str)
        except (json.JSONDecodeError, ValueError):
            pass
    
    return {
        "timestamp": timestamp,
        "logger": logger,
        "level": level,
        "message": message,
        "context": context,
        "performance": performance,
    }


def extract_slow_query_info(entry: Dict) -> Optional[Dict]:
    """Extract slow query information from log entry."""
    message = entry.get("message", "")
    context = entry.get("context", {})
    performance = entry.get("performance", {})
    
    if "Slow query" not in message and "duration_ms" not in str(performance):
        return None
    
    # Extract query information
    query_type = context.get("query_type") or context.get("operation", "unknown")
    table = context.get("table", "unknown")
    duration_ms = performance.get("duration_ms") or context.get("duration_ms")
    
    if duration_ms and float(duration_ms) > 1000:  # Only track queries > 1 second
        return {
            "timestamp": entry.get("timestamp"),
            "query_type": query_type,
            "table": table,
            "duration_ms": float(duration_ms),
            "logger": entry.get("logger"),
        }
    
    return None


def extract_endpoint_info(entry: Dict) -> Optional[Dict]:
    """Extract endpoint performance information from log entry."""
    context = entry.get("context", {})
    performance = entry.get("performance", {})
    message = entry.get("message", "")
    
    # Look for endpoint patterns in message or context
    endpoint = context.get("path") or context.get("endpoint")
    method = context.get("method")
    duration_ms = performance.get("duration_ms") or context.get("duration_ms")
    
    if endpoint and duration_ms:
        return {
            "timestamp": entry.get("timestamp"),
            "endpoint": endpoint,
            "method": method or "unknown",
            "duration_ms": float(duration_ms),
            "status_code": context.get("status_code"),
        }
    
    return None


def extract_error_info(entry: Dict) -> Optional[Dict]:
    """Extract error information from log entry."""
    level = entry.get("level", "").upper()
    if level not in ("ERROR", "WARNING", "CRITICAL"):
        return None
    
    context = entry.get("context", {})
    message = entry.get("message", "")
    
    return {
        "timestamp": entry.get("timestamp"),
        "level": level,
        "message": message,
        "endpoint": context.get("path") or context.get("endpoint"),
        "method": context.get("method"),
        "error_type": context.get("error_type"),
        "status_code": context.get("status_code"),
        "user_id": context.get("user_id"),
    }


def analyze_logs(log_file: str = "backend/logs/app.log") -> Dict:
    """Analyze performance and errors from logs.
    
    Args:
        log_file: Path to log file
        
    Returns:
        Dictionary with analysis results
    """
    log_path = Path(log_file)
    if not log_path.exists():
        return {"error": f"Log file not found: {log_file}"}
    
    slow_queries = []
    endpoint_times = []
    errors = []
    
    # Group by table/operation for slow queries
    slow_query_stats = defaultdict(list)
    
    # Group by endpoint for performance analysis
    endpoint_stats = defaultdict(list)
    
    # Error patterns
    error_patterns = defaultdict(int)
    
    print(f"Analyzing log file: {log_file}")
    
    with open(log_path, "r", encoding="utf-8") as f:
        line_count = 0
        for line in f:
            line_count += 1
            if line_count % 10000 == 0:
                print(f"Processed {line_count} lines...")
            
            entry = parse_log_line(line.strip())
            if not entry:
                continue
            
            # Extract slow query info
            query_info = extract_slow_query_info(entry)
            if query_info:
                slow_queries.append(query_info)
                key = f"{query_info['table']}:{query_info['query_type']}"
                slow_query_stats[key].append(query_info["duration_ms"])
            
            # Extract endpoint performance
            endpoint_info = extract_endpoint_info(entry)
            if endpoint_info:
                endpoint_times.append(endpoint_info)
                endpoint_key = f"{endpoint_info['method']} {endpoint_info['endpoint']}"
                endpoint_stats[endpoint_key].append(endpoint_info["duration_ms"])
            
            # Extract errors
            error_info = extract_error_info(entry)
            if error_info:
                errors.append(error_info)
                error_key = f"{error_info.get('endpoint', 'unknown')}:{error_info.get('error_type', 'unknown')}"
                error_patterns[error_key] += 1
    
    # Calculate statistics
    slow_query_summary = {}
    for key, durations in slow_query_stats.items():
        table, op = key.split(":", 1)
        slow_query_summary[key] = {
            "table": table,
            "operation": op,
            "count": len(durations),
            "avg_duration_ms": sum(durations) / len(durations),
            "max_duration_ms": max(durations),
            "min_duration_ms": min(durations),
        }
    
    endpoint_summary = {}
    for endpoint_key, durations in endpoint_stats.items():
        endpoint_summary[endpoint_key] = {
            "count": len(durations),
            "avg_duration_ms": sum(durations) / len(durations),
            "max_duration_ms": max(durations),
            "min_duration_ms": min(durations),
            "p95_duration_ms": sorted(durations)[int(len(durations) * 0.95)] if durations else 0,
        }
    
    # Sort by count for most frequent issues
    slow_query_summary_sorted = sorted(
        slow_query_summary.items(),
        key=lambda x: x[1]["count"],
        reverse=True
    )
    
    endpoint_summary_sorted = sorted(
        endpoint_summary.items(),
        key=lambda x: x[1]["avg_duration_ms"],
        reverse=True
    )
    
    return {
        "summary": {
            "total_lines_processed": line_count,
            "slow_queries_count": len(slow_queries),
            "unique_slow_query_patterns": len(slow_query_stats),
            "endpoint_calls_count": len(endpoint_times),
            "unique_endpoints": len(endpoint_stats),
            "errors_count": len(errors),
            "unique_error_patterns": len(error_patterns),
        },
        "slow_queries": {
            "top_patterns": dict(slow_query_summary_sorted[:20]),
            "all_queries": slow_queries[:100],  # Limit to first 100
        },
        "endpoint_performance": {
            "slowest_endpoints": dict(endpoint_summary_sorted[:20]),
            "all_endpoints": endpoint_times[:100],  # Limit to first 100
        },
        "errors": {
            "top_patterns": dict(sorted(error_patterns.items(), key=lambda x: x[1], reverse=True)[:20]),
            "recent_errors": errors[:50],  # Limit to first 50
        },
    }


def print_report(results: Dict) -> None:
    """Print a formatted performance report."""
    if "error" in results:
        print(f"Error: {results['error']}")
        return
    
    summary = results.get("summary", {})
    
    print("\n" + "="*80)
    print("PERFORMANCE ANALYSIS REPORT")
    print("="*80)
    
    print(f"\nSummary:")
    print(f"  Total log lines processed: {summary.get('total_lines_processed', 0):,}")
    print(f"  Slow queries found: {summary.get('slow_queries_count', 0)}")
    print(f"  Unique slow query patterns: {summary.get('unique_slow_query_patterns', 0)}")
    print(f"  Endpoint calls: {summary.get('endpoint_calls_count', 0)}")
    print(f"  Unique endpoints: {summary.get('unique_endpoints', 0)}")
    print(f"  Errors found: {summary.get('errors_count', 0)}")
    print(f"  Unique error patterns: {summary.get('unique_error_patterns', 0)}")
    
    # Slow queries section
    slow_queries = results.get("slow_queries", {}).get("top_patterns", {})
    if slow_queries:
        print("\n" + "-"*80)
        print("TOP SLOW QUERY PATTERNS")
        print("-"*80)
        print(f"{'Table:Operation':<40} {'Count':<10} {'Avg (ms)':<12} {'Max (ms)':<12}")
        print("-"*80)
        for key, stats in list(slow_queries.items())[:10]:
            table_op = f"{stats['table']}:{stats['operation']}"
            print(f"{table_op:<40} {stats['count']:<10} {stats['avg_duration_ms']:<12.2f} {stats['max_duration_ms']:<12.2f}")
    
    # Endpoint performance section
    endpoints = results.get("endpoint_performance", {}).get("slowest_endpoints", {})
    if endpoints:
        print("\n" + "-"*80)
        print("SLOWEST ENDPOINTS")
        print("-"*80)
        print(f"{'Endpoint':<50} {'Count':<10} {'Avg (ms)':<12} {'P95 (ms)':<12}")
        print("-"*80)
        for endpoint, stats in list(endpoints.items())[:10]:
            endpoint_short = endpoint[:48]
            print(f"{endpoint_short:<50} {stats['count']:<10} {stats['avg_duration_ms']:<12.2f} {stats['p95_duration_ms']:<12.2f}")
    
    # Error patterns section
    errors = results.get("errors", {}).get("top_patterns", {})
    if errors:
        print("\n" + "-"*80)
        print("TOP ERROR PATTERNS")
        print("-"*80)
        print(f"{'Pattern':<60} {'Count':<10}")
        print("-"*80)
        for pattern, count in list(errors.items())[:10]:
            pattern_short = pattern[:58]
            print(f"{pattern_short:<60} {count:<10}")
    
    print("\n" + "="*80)


def main():
    """Main entry point for the script."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Analyze application logs for performance issues")
    parser.add_argument(
        "--log-file",
        default="backend/logs/app.log",
        help="Path to log file (default: backend/logs/app.log)"
    )
    parser.add_argument(
        "--output",
        help="Output JSON file path (optional)"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress console output"
    )
    
    args = parser.parse_args()
    
    results = analyze_logs(args.log_file)
    
    if not args.quiet:
        print_report(results)
    
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\nResults saved to: {args.output}")
    
    return results


if __name__ == "__main__":
    main()

