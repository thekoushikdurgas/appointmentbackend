"""AI agentic commands for intelligent endpoint operation."""

import sys
from pathlib import Path
from typing import Optional, Dict, Any, List
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.tree import Tree
import json

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from cli.intelligence.ai_agent import AIAgent
from cli.config import ConfigManager
from cli.commands.test_commands import load_endpoints_from_csv, filter_endpoints

app = typer.Typer(name="ai", help="AI agentic commands for intelligent endpoint operation")
console = Console()


@app.command()
def learn(
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Configuration profile"),
    days: int = typer.Option(7, "--days", "-d", help="Number of days of results to learn from")
):
    """Learn from historical test results."""
    config_manager = ConfigManager()
    cli_profile = config_manager.get_profile(profile)
    
    reports_dir = Path(cli_profile.output_dir) if cli_profile.output_dir else Path(__file__).parent.parent.parent / "test_reports"
    
    agent = AIAgent()
    
    console.print("[cyan]Learning from historical test results...[/cyan]")
    
    # Load recent test results
    from datetime import datetime, timedelta
    cutoff_date = datetime.now() - timedelta(days=days)
    
    learned_count = 0
    for report_file in reports_dir.glob("test_results_*.json"):
        try:
            timestamp_str = report_file.stem.replace("test_results_", "")
            report_time = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
            
            if report_time >= cutoff_date:
                with open(report_file, 'r') as f:
                    report_data = json.load(f)
                
                detailed_results = report_data.get("detailed_results", [])
                
                # Group results by endpoint
                endpoints_map = {}
                for result in detailed_results:
                    endpoint_key = f"{result.get('method')} {result.get('endpoint')}"
                    if endpoint_key not in endpoints_map:
                        endpoints_map[endpoint_key] = {
                            "method": result.get("method"),
                            "endpoint": result.get("endpoint"),
                            "category": result.get("category", "Unknown"),
                            "api_version": result.get("api_version", "v1"),
                            "requires_auth": "TRUE" if "Authorization" in str(result.get("request", {}).get("headers", {})) else "FALSE"
                        }
                    
                    agent.learn_from_result(result, endpoints_map[endpoint_key])
                    learned_count += 1
        except Exception as e:
            console.print(f"[yellow]Warning: Could not process {report_file.name}: {e}[/yellow]")
    
    agent.save_knowledge()
    
    console.print(f"[green]✓[/green] Learned from {learned_count} test results")
    console.print(f"[green]✓[/green] Knowledge base updated")


@app.command()
def analyze(
    endpoint: Optional[str] = typer.Option(None, "--endpoint", "-e", help="Specific endpoint to analyze (method path)"),
    category: Optional[str] = typer.Option(None, "--category", "-c", help="Analyze all endpoints in category"),
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Configuration profile")
):
    """Analyze endpoints using AI insights."""
    agent = AIAgent()
    
    if endpoint:
        # Analyze specific endpoint
        analysis = agent.analyze_endpoint(endpoint)
        _display_analysis(analysis)
    elif category:
        # Analyze all endpoints in category
        csv_directory = Path(__file__).parent.parent.parent / "csv"
        all_endpoints = []
        for csv_file in csv_directory.glob("*.csv"):
            endpoints = load_endpoints_from_csv(csv_file)
            all_endpoints.extend(endpoints)
        
        filtered = filter_endpoints(all_endpoints, category=category)
        
        console.print(f"[cyan]Analyzing {len(filtered)} endpoints in category '{category}'...[/cyan]\n")
        
        for ep in filtered:
            endpoint_key = f"{ep.get('method')} {ep.get('endpoint')}"
            analysis = agent.analyze_endpoint(endpoint_key)
            if analysis.get("patterns"):
                _display_analysis(analysis, compact=True)
    else:
        # Analyze all learned endpoints
        console.print("[cyan]Analyzing all learned endpoints...[/cyan]\n")
        
        for endpoint_key in agent.endpoint_patterns.keys():
            analysis = agent.analyze_endpoint(endpoint_key)
            _display_analysis(analysis, compact=True)


@app.command()
def optimize(
    endpoint: str = typer.Argument(..., help="Endpoint to optimize (method path)"),
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Configuration profile")
):
    """Get AI-powered optimization suggestions for an endpoint."""
    agent = AIAgent()
    
    # Load endpoint details
    csv_directory = Path(__file__).parent.parent.parent / "csv"
    all_endpoints = []
    for csv_file in csv_directory.glob("*.csv"):
        endpoints = load_endpoints_from_csv(csv_file)
        all_endpoints.extend(endpoints)
    
    # Find matching endpoint
    endpoint_parts = endpoint.split(" ", 1)
    if len(endpoint_parts) != 2:
        console.print("[red]Invalid endpoint format. Use: 'METHOD /path/to/endpoint'[/red]")
        raise typer.Exit(1)
    
    method, path = endpoint_parts
    matching_endpoint = None
    for ep in all_endpoints:
        if ep.get("method", "").upper() == method.upper() and ep.get("endpoint") == path:
            matching_endpoint = ep
            break
    
    if not matching_endpoint:
        console.print(f"[red]Endpoint not found: {endpoint}[/red]")
        raise typer.Exit(1)
    
    # Get suggestions
    endpoint_key = f"{method} {path}"
    suggestions = agent.get_operation_suggestions(endpoint_key)
    
    if not suggestions:
        console.print(f"[yellow]No optimization suggestions available for {endpoint}[/yellow]")
        console.print("[yellow]Run 'ai learn' to build knowledge base first[/yellow]")
        return
    
    console.print(Panel.fit(
        f"[bold cyan]Optimization Suggestions[/bold cyan]\n"
        f"Endpoint: [yellow]{endpoint}[/yellow]",
        border_style="cyan"
    ))
    
    # Group by priority
    by_priority = {"critical": [], "high": [], "medium": [], "low": []}
    for suggestion in suggestions:
        priority = suggestion.get("priority", "low")
        by_priority[priority].append(suggestion)
    
    for priority in ["critical", "high", "medium", "low"]:
        if by_priority[priority]:
            priority_color = {
                "critical": "red",
                "high": "yellow",
                "medium": "cyan",
                "low": "white"
            }.get(priority, "white")
            
            console.print(f"\n[bold {priority_color}]{priority.upper()} Priority:[/bold {priority_color}]")
            for suggestion in by_priority[priority]:
                console.print(f"  • [{priority_color}]{suggestion['type']}[/{priority_color}]: {suggestion['suggestion']}")
                if suggestion.get("details"):
                    console.print(f"    {suggestion['details']}")


@app.command()
def suggest(
    endpoint: Optional[str] = typer.Option(None, "--endpoint", "-e", help="Specific endpoint"),
    category: Optional[str] = typer.Option(None, "--category", "-c", help="Suggest for all endpoints in category")
):
    """Get AI suggestions for test case improvements."""
    agent = AIAgent()
    
    csv_directory = Path(__file__).parent.parent.parent / "csv"
    all_endpoints = []
    for csv_file in csv_directory.glob("*.csv"):
        endpoints = load_endpoints_from_csv(csv_file)
        all_endpoints.extend(endpoints)
    
    if endpoint:
        # Suggest for specific endpoint
        endpoint_parts = endpoint.split(" ", 1)
        if len(endpoint_parts) != 2:
            console.print("[red]Invalid endpoint format. Use: 'METHOD /path/to/endpoint'[/red]")
            raise typer.Exit(1)
        
        method, path = endpoint_parts
        matching_endpoint = None
        for ep in all_endpoints:
            if ep.get("method", "").upper() == method.upper() and ep.get("endpoint") == path:
                matching_endpoint = ep
                break
        
        if not matching_endpoint:
            console.print(f"[red]Endpoint not found: {endpoint}[/red]")
            raise typer.Exit(1)
        
        # Get existing tests (simplified - would load from test generator)
        existing_tests = []
        suggestions = agent.suggest_test_improvements(matching_endpoint, existing_tests)
        _display_suggestions(suggestions, matching_endpoint)
    
    elif category:
        # Suggest for category
        filtered = filter_endpoints(all_endpoints, category=category)
        console.print(f"[cyan]Getting suggestions for {len(filtered)} endpoints in '{category}'...[/cyan]\n")
        
        for ep in filtered:
            endpoint_key = f"{ep.get('method')} {ep.get('endpoint')}"
            existing_tests = []
            suggestions = agent.suggest_test_improvements(ep, existing_tests)
            if suggestions:
                _display_suggestions(suggestions, ep, compact=True)
    else:
        console.print("[red]Please specify --endpoint or --category[/red]")
        raise typer.Exit(1)


@app.command()
def anomalies(
    endpoint: Optional[str] = typer.Option(None, "--endpoint", "-e", help="Check specific endpoint"),
    severity: str = typer.Option("all", "--severity", help="Filter by severity: all, high, medium, low")
):
    """Detect anomalies in endpoint behavior."""
    agent = AIAgent()
    
    if endpoint:
        # Check specific endpoint
        analysis = agent.analyze_endpoint(endpoint)
        anomalies = analysis.get("anomalies", [])
        
        if severity != "all":
            anomalies = [a for a in anomalies if a.get("severity") == severity]
        
        _display_anomalies(anomalies, endpoint)
    else:
        # Check all endpoints
        console.print("[cyan]Scanning all endpoints for anomalies...[/cyan]\n")
        
        all_anomalies = []
        for endpoint_key in agent.endpoint_patterns.keys():
            analysis = agent.analyze_endpoint(endpoint_key)
            endpoint_anomalies = analysis.get("anomalies", [])
            if severity != "all":
                endpoint_anomalies = [a for a in endpoint_anomalies if a.get("severity") == severity]
            
            if endpoint_anomalies:
                all_anomalies.append({
                    "endpoint": endpoint_key,
                    "anomalies": endpoint_anomalies
                })
        
        if not all_anomalies:
            console.print("[green]✓[/green] No anomalies detected")
        else:
            for item in all_anomalies:
                _display_anomalies(item["anomalies"], item["endpoint"])


@app.command()
def knowledge(
    export: Optional[str] = typer.Option(None, "--export", help="Export knowledge base to file"),
    import_file: Optional[str] = typer.Option(None, "--import", help="Import knowledge base from file")
):
    """Manage AI knowledge base."""
    agent = AIAgent()
    
    if export:
        # Export knowledge base
        export_path = Path(export)
        with open(export_path, 'w') as f:
            json.dump(agent.knowledge_base, f, indent=2)
        console.print(f"[green]✓[/green] Knowledge base exported to {export_path}")
    
    elif import_file:
        # Import knowledge base
        import_path = Path(import_file)
        if not import_path.exists():
            console.print(f"[red]File not found: {import_path}[/red]")
            raise typer.Exit(1)
        
        with open(import_path, 'r') as f:
            imported_kb = json.load(f)
        
        # Merge with existing
        agent.knowledge_base.update(imported_kb)
        agent._save_knowledge_base()
        console.print(f"[green]✓[/green] Knowledge base imported from {import_path}")
    
    else:
        # Show knowledge base stats
        kb = agent.knowledge_base
        console.print(Panel.fit(
            "[bold cyan]Knowledge Base Statistics[/bold cyan]\n"
            f"Endpoints Learned: [yellow]{len(kb.get('endpoint_patterns', {}))}[/yellow]\n"
            f"Response Patterns: [yellow]{sum(len(v) for v in kb.get('response_patterns', {}).values())}[/yellow]\n"
            f"Error Patterns: [yellow]{sum(len(v) for v in kb.get('error_patterns', {}).values())}[/yellow]\n"
            f"Performance Baselines: [yellow]{len(kb.get('performance_baselines', {}))}[/yellow]\n"
            f"Last Updated: [yellow]{kb.get('last_updated', 'Never')}[/yellow]",
            border_style="cyan"
        ))


def _display_analysis(analysis: Dict[str, Any], compact: bool = False):
    """Display endpoint analysis."""
    endpoint = analysis.get("endpoint", "Unknown")
    patterns = analysis.get("patterns", {})
    performance = analysis.get("performance", {})
    reliability = analysis.get("reliability", {})
    recommendations = analysis.get("recommendations", [])
    anomalies = analysis.get("anomalies", [])
    
    if compact:
        reliability_score = reliability.get("score", 0)
        status = reliability.get("status", "unknown")
        status_color = {
            "excellent": "green",
            "good": "cyan",
            "fair": "yellow",
            "poor": "red"
        }.get(status, "white")
        
        console.print(f"[{status_color}]{endpoint}[/{status_color}] - Reliability: {reliability_score:.1f}% ({status})")
        if anomalies:
            console.print(f"  ⚠ {len(anomalies)} anomaly(ies) detected")
    else:
        console.print(Panel.fit(
            f"[bold cyan]Analysis: {endpoint}[/bold cyan]\n"
            f"Reliability: [yellow]{reliability.get('score', 0):.1f}%[/yellow] ({reliability.get('status', 'unknown')})\n"
            f"Total Tests: [yellow]{reliability.get('total_tests', 0)}[/yellow]\n"
            f"Avg Response Time: [yellow]{performance.get('avg', 0):.0f}ms[/yellow]",
            border_style="cyan"
        ))
        
        if recommendations:
            console.print("\n[bold]Recommendations:[/bold]")
            for rec in recommendations:
                console.print(f"  • {rec}")
        
        if anomalies:
            console.print(f"\n[bold yellow]⚠ {len(anomalies)} Anomaly(ies) Detected:[/bold yellow]")
            for anomaly in anomalies[:5]:  # Show top 5
                console.print(f"  • [{anomaly.get('severity', 'unknown')}] {anomaly.get('message', '')}")


def _display_suggestions(suggestions: List[Dict[str, Any]], endpoint: Dict[str, Any], compact: bool = False):
    """Display test improvement suggestions."""
    if not suggestions:
        return
    
    endpoint_str = f"{endpoint.get('method')} {endpoint.get('endpoint')}"
    
    if compact:
        console.print(f"[cyan]{endpoint_str}[/cyan] - {len(suggestions)} suggestion(s)")
    else:
        console.print(Panel.fit(
            f"[bold cyan]Test Suggestions: {endpoint_str}[/bold cyan]",
            border_style="cyan"
        ))
        
        for suggestion in suggestions:
            priority = suggestion.get("priority", "low")
            priority_color = {
                "high": "red",
                "medium": "yellow",
                "low": "cyan"
            }.get(priority, "white")
            
            console.print(f"\n[{priority_color}]{priority.upper()}[/{priority_color}]: {suggestion.get('suggestion', '')}")
            if suggestion.get("test_case"):
                console.print(f"  Suggested test case: {suggestion['test_case'].get('name', 'N/A')}")


def _display_anomalies(anomalies: List[Dict[str, Any]], endpoint: str):
    """Display anomalies."""
    if not anomalies:
        return
    
    console.print(f"\n[bold yellow]⚠ Anomalies for {endpoint}:[/bold yellow]")
    
    for anomaly in anomalies:
        severity = anomaly.get("severity", "unknown")
        severity_color = {
            "high": "red",
            "medium": "yellow",
            "low": "cyan"
        }.get(severity, "white")
        
        console.print(f"  • [{severity_color}]{severity.upper()}[/{severity_color}]: {anomaly.get('message', '')}")
        if anomaly.get("timestamp"):
            console.print(f"    Time: {anomaly['timestamp']}")

