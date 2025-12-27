#!/usr/bin/env python3
"""Script to monitor VQL rollout progress and metrics."""

import argparse
import json
import sys
from datetime import datetime, timedelta
from typing import Dict, Optional

import requests


def check_connectra_health(base_url: str, api_key: str) -> Dict:
    """Check Connectra service health."""
    try:
        response = requests.get(
            f"{base_url}/health",
            headers={"X-API-Key": api_key},
            timeout=5
        )
        response.raise_for_status()
        return {"status": "healthy", "response": response.json()}
    except requests.exceptions.RequestException as exc:
        return {"status": "unhealthy", "error": str(exc)}


def check_vql_health(api_base_url: str, auth_token: Optional[str] = None) -> Dict:
    """Check VQL health endpoint."""
    headers = {}
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"
    
    try:
        response = requests.get(
            f"{api_base_url}/api/v1/health/vql",
            headers=headers,
            timeout=5
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as exc:
        return {"error": str(exc)}


def format_metrics(health_data: Dict) -> str:
    """Format health metrics for display."""
    output = []
    output.append("=" * 60)
    output.append("VQL Rollout Status")
    output.append("=" * 60)
    output.append(f"Timestamp: {datetime.now().isoformat()}")
    output.append("")
    
    # Connectra Status
    output.append("Connectra Service:")
    output.append(f"  Enabled: {health_data.get('connectra_enabled', False)}")
    output.append(f"  Status: {health_data.get('connectra_status', 'unknown')}")
    output.append(f"  Base URL: {health_data.get('connectra_base_url', 'N/A')}")
    output.append("")
    
    # Feature Flags
    output.append("Feature Flags:")
    flags = health_data.get("feature_flags", {})
    for flag, enabled in flags.items():
        status = "✓ ENABLED" if enabled else "✗ DISABLED"
        output.append(f"  {flag}: {status}")
    output.append("")
    
    # Connectra Details
    if "connectra_details" in health_data:
        output.append("Connectra Details:")
        for key, value in health_data["connectra_details"].items():
            output.append(f"  {key}: {value}")
        output.append("")
    
    # Errors
    if "connectra_error" in health_data:
        output.append("⚠ WARNING:")
        output.append(f"  {health_data['connectra_error']}")
        output.append("")
    
    output.append("=" * 60)
    return "\n".join(output)


def main():
    """Main monitoring function."""
    parser = argparse.ArgumentParser(description="Monitor VQL rollout progress")
    parser.add_argument(
        "--api-url",
        default="http://localhost:8000",
        help="Backend API base URL"
    )
    parser.add_argument(
        "--connectra-url",
        help="Connectra service base URL (overrides config)"
    )
    parser.add_argument(
        "--connectra-key",
        help="Connectra API key (overrides config)"
    )
    parser.add_argument(
        "--auth-token",
        help="JWT auth token for API requests"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON"
    )
    parser.add_argument(
        "--watch",
        action="store_true",
        help="Watch mode - continuously monitor (every 30s)"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=30,
        help="Watch interval in seconds (default: 30)"
    )
    
    args = parser.parse_args()
    
    # Check VQL health
    health_data = check_vql_health(args.api_url, args.auth_token)
    
    if args.json:
        print(json.dumps(health_data, indent=2))
    else:
        print(format_metrics(health_data))
    
    # Watch mode
    if args.watch:
        import time
        try:
            while True:
                time.sleep(args.interval)
                print("\n" + "=" * 60)
                health_data = check_vql_health(args.api_url, args.auth_token)
                print(format_metrics(health_data))
        except KeyboardInterrupt:
            print("\nMonitoring stopped.")
            sys.exit(0)
    
    # Exit with error code if Connectra is unhealthy
    if health_data.get("connectra_status") == "unhealthy":
        sys.exit(1)


if __name__ == "__main__":
    main()

