# Contact360 API Testing CLI

AI-powered command-line interface for automated API testing, monitoring, endpoint discovery, and collection management.

## Features

- **AI Agentic Learning**: Automatically learns from test results and endpoint behavior
- **Intelligent Test Execution**: Run tests with smart prioritization based on historical data
- **Continuous Monitoring**: Automated scheduled test runs with alerting
- **Endpoint Discovery**: Scan, sync, and document API endpoints
- **Postman Collection Management**: Generate, update, and manage Postman collections
- **Interactive REPL**: Manual testing and exploration mode
- **Enhanced Reporting**: Dashboards, trends, and insights
- **Configuration Profiles**: Manage multiple test environments
- **AI-Powered Analysis**: Analyze endpoints, detect anomalies, and get optimization suggestions
- **Test Case Optimization**: AI suggests improvements for test coverage

## Installation

The CLI is part of the Contact360 project. Ensure you have the required dependencies:

```bash
pip install typer rich requests python-dotenv schedule
```

## Quick Start

### Basic Usage

```bash
# Show help
python main.py

# Run all tests
python main.py test run

# Run tests for a specific category
python main.py test run-category "Authentication"

# Run tests with intelligent prioritization
python main.py test run-smart --limit 50

# Start interactive REPL
python main.py interactive repl
```

## Command Reference

### Test Commands

#### `test run`
Run all tests or filtered subset.

```bash
# Run all tests
python main.py test run

# Filter by category
python main.py test run --category "Billing"

# Filter by HTTP method
python main.py test run --method "GET"

# Specify test mode
python main.py test run --mode comprehensive

# Use specific profile
python main.py test run --profile production
```

**Options:**
- `--category, -c`: Filter by category
- `--method, -m`: Filter by HTTP method
- `--mode`: Test mode (smoke, comprehensive, hybrid)
- `--profile, -p`: Configuration profile
- `--output, -o`: Output directory
- `--verbose, -v`: Verbose output
- `--csv-dir`: CSV directory path

#### `test run-category`
Run tests for a specific category.

```bash
python main.py test run-category "Email" --mode hybrid
```

#### `test run-endpoint`
Run tests for a specific endpoint.

```bash
python main.py test run-endpoint "/api/v1/users/" --method GET
```

#### `test run-smart`
Run tests with intelligent prioritization.

```bash
# Run top 50 prioritized tests
python main.py test run-smart --limit 50

# Run with specific mode
python main.py test run-smart --limit 100 --mode comprehensive
```

### Discover Commands

#### `discover scan`
Scan API for available endpoints (requires OpenAPI spec).

```bash
python main.py discover scan --base-url http://localhost:8000
```

#### `discover sync-csv`
Sync CSV file with current API state.

```bash
python main.py discover sync-csv "csv/api_endpoints.csv"
```

#### `discover generate-docs`
Generate API documentation from CSV.

```bash
# Generate Markdown docs
python main.py discover generate-docs --format markdown

# Generate HTML docs
python main.py discover generate-docs --format html --output ./docs

# Generate JSON docs
python main.py discover generate-docs --format json
```

### Monitor Commands

#### `monitor start`
Start continuous monitoring.

```bash
# Start with default interval (300s)
python main.py monitor start

# Custom interval
python main.py monitor start --interval 600

# Monitor specific category
python main.py monitor start --category "Billing" --interval 300
```

#### `monitor stop`
Stop continuous monitoring.

```bash
python main.py monitor stop
```

#### `monitor status`
Show monitoring status.

```bash
python main.py monitor status
```

#### `monitor alerts`
Check for alerts based on recent test results.

```bash
# Check with default threshold (80% failure rate)
python main.py monitor alerts

# Custom threshold
python main.py monitor alerts --threshold 0.5
```

### Collection Commands

#### `collection generate`
Generate Postman collection from CSV.

```bash
python main.py collection generate --output collection.json
```

#### `collection update`
Update existing Postman collection.

```bash
python main.py collection update collection.json --csv endpoints.csv
```

#### `collection export`
Export Postman collection to different formats.

```bash
# Export to CSV
python main.py collection export collection.json --format csv

# Export to OpenAPI
python main.py collection export collection.json --format openapi
```

#### `collection import`
Import endpoints from various formats.

```bash
python main.py collection import endpoints.csv --output collection.json
```

### Interactive Commands

#### `interactive repl`
Start interactive REPL for manual testing.

```bash
python main.py interactive repl --profile development
```

**REPL Commands:**
- `get <endpoint>` - GET request
- `post <endpoint> [json]` - POST request
- `put <endpoint> [json]` - PUT request
- `delete <endpoint>` - DELETE request
- `auth` - Authenticate and get token
- `headers` - Show current headers
- `help` - Show help
- `exit` - Exit REPL

**Example:**
```
api> get /api/v1/users/
api> post /api/v1/auth/login/ {"email": "test@example.com", "password": "pass"}
api> auth
api> exit
```

### Config Commands

#### `config show`
Show current configuration.

```bash
# Show all profiles
python main.py config show

# Show specific profile
python main.py config show --profile production
```

#### `config add`
Add a new configuration profile.

```bash
python main.py config add production \
  --base-url https://api.example.com \
  --email admin@example.com \
  --password secret
```

#### `config set-default`
Set default profile.

```bash
python main.py config set-default production
```

#### `config remove`
Remove a configuration profile.

```bash
python main.py config remove old-profile
```

### Dashboard Commands

#### `dashboard show`
Show dashboard from latest test results.

```bash
python main.py dashboard show
```

#### `dashboard trends`
Show trend analysis over time.

```bash
# Last 7 days (default)
python main.py dashboard trends

# Last 30 days
python main.py dashboard trends --days 30
```

### AI Agentic Commands

#### `ai learn`
Learn from historical test results to build knowledge base.

```bash
# Learn from last 7 days (default)
python main.py ai learn

# Learn from last 30 days
python main.py ai learn --days 30
```

#### `ai analyze`
Analyze endpoints using AI insights.

```bash
# Analyze specific endpoint
python main.py ai analyze --endpoint "GET /api/v1/users/"

# Analyze all endpoints in category
python main.py ai analyze --category "Authentication"

# Analyze all learned endpoints
python main.py ai analyze
```

#### `ai optimize`
Get AI-powered optimization suggestions for an endpoint.

```bash
python main.py ai optimize "GET /api/v1/users/"
```

#### `ai suggest`
Get AI suggestions for test case improvements.

```bash
# Suggest for specific endpoint
python main.py ai suggest --endpoint "POST /api/v1/auth/login/"

# Suggest for all endpoints in category
python main.py ai suggest --category "Email"
```

#### `ai anomalies`
Detect anomalies in endpoint behavior.

```bash
# Check specific endpoint
python main.py ai anomalies --endpoint "GET /api/v1/users/"

# Check all endpoints (high severity only)
python main.py ai anomalies --severity high

# Check all endpoints
python main.py ai anomalies
```

#### `ai knowledge`
Manage AI knowledge base.

```bash
# Show knowledge base statistics
python main.py ai knowledge

# Export knowledge base
python main.py ai knowledge --export knowledge.json

# Import knowledge base
python main.py ai knowledge --import knowledge.json
```

## Configuration

Configuration is stored in `~/.contact360-cli/config.json`. You can manage profiles using the `config` commands or edit the file directly.

### Environment Variables

The CLI also supports environment variables:

- `API_BASE_URL` - API base URL
- `TEST_EMAIL` or `API_TEST_EMAIL` - Test user email
- `TEST_PASSWORD` or `API_TEST_PASSWORD` - Test user password
- `ACCESS_TOKEN` - Pre-configured access token
- `REFRESH_TOKEN` - Pre-configured refresh token
- `WRITE_KEY` - Write key for v1 endpoints
- `ADMIN_EMAIL` or `TEST_ADMIN_EMAIL` - Admin email
- `ADMIN_PASSWORD` or `TEST_ADMIN_PASSWORD` - Admin password

### Profile Structure

```json
{
  "default_profile": "default",
  "profiles": {
    "default": {
      "name": "default",
      "base_url": "http://127.0.0.1:8000",
      "email": "test@example.com",
      "password": "testpass123",
      "timeout": 30,
      "retry_max": 3,
      "test_mode": "hybrid"
    }
  }
}
```

## Intelligence Features

### AI Agentic Learning

The CLI automatically learns from every test execution:
- **Response Patterns**: Learns normal response structures and status codes
- **Performance Baselines**: Tracks average, median, P95 response times
- **Error Patterns**: Identifies common error messages and failure modes
- **Endpoint Behavior**: Builds knowledge base of endpoint characteristics

### Smart Test Prioritization

The `run-smart` command uses intelligent prioritization based on:
- Recent failure history
- Endpoint criticality (auth, billing get higher priority)
- Historical performance data
- Endpoint usage patterns

### AI-Powered Analysis

The AI agent provides:
- **Reliability Scoring**: Calculates endpoint reliability based on success rates
- **Anomaly Detection**: Identifies performance and status code anomalies
- **Optimization Suggestions**: Recommends improvements for endpoint operation
- **Test Case Suggestions**: Suggests missing test cases based on learned patterns

### Result Analysis

After test runs, the CLI automatically:
- Calculates health scores
- Identifies problematic endpoints
- Detects performance issues
- Generates recommendations

### Pattern Detection

The intelligence layer detects:
- Error patterns (authentication, validation, server errors)
- Performance patterns (slow endpoints, inconsistent performance)
- Category patterns (success rates by category)
- Endpoint patterns (high failure rates, slow responses)

## Examples

### Example 1: Daily Test Run

```bash
# Run comprehensive tests
python main.py test run --mode comprehensive --output ./daily-reports

# View dashboard
python main.py dashboard show

# Check for alerts
python main.py monitor alerts
```

### Example 2: Continuous Monitoring

```bash
# Start monitoring with 5-minute intervals
python main.py monitor start --interval 300

# Check status
python main.py monitor status

# View trends
python main.py dashboard trends --days 7
```

### Example 3: Development Workflow

```bash
# Quick smoke tests during development
python main.py test run --mode smoke --category "User Profile"

# Interactive testing
python main.py interactive repl

# Generate documentation
python main.py discover generate-docs --format markdown
```

### Example 4: Production Testing

```bash
# Use production profile
python main.py test run --profile production --mode comprehensive

# Generate Postman collection
python main.py collection generate --output production_collection.json

# Export for sharing
python main.py collection export production_collection.json --format openapi
```

## Output Files

### Test Reports

- `test_results_<timestamp>.json` - Detailed JSON results
- `test_results_latest.json` - Latest results (symlink)
- `test_report_<timestamp>.html` - HTML report
- `test_report_latest.html` - Latest HTML report (symlink)
- `dashboard_<timestamp>.json` - Dashboard data
- `dashboard_latest.json` - Latest dashboard (symlink)

### CSV Updates

The CLI automatically updates CSV files with test results:
- Status codes
- Response times
- Success/failure status
- Error messages
- Test timestamps

## Troubleshooting

### Authentication Issues

```bash
# Check configuration
python main.py config show

# Test authentication in REPL
python main.py interactive repl
# Then type: auth
```

### No Endpoints Found

```bash
# Check CSV directory
python main.py test run --csv-dir ./csv --verbose

# Sync CSV
python main.py discover sync-csv "csv/api_endpoints.csv"
```

### Monitoring Not Working

```bash
# Check status
python main.py monitor status

# Restart monitoring
python main.py monitor stop
python main.py monitor start
```

## Advanced Usage

### Custom Test Modes

- **smoke**: Quick tests, minimal coverage
- **comprehensive**: Full test suite with error cases
- **hybrid**: Balanced approach (default)

### Profile Management

```bash
# Create development profile
python main.py config add dev \
  --base-url http://localhost:8000 \
  --email dev@example.com

# Create production profile
python main.py config add prod \
  --base-url https://api.production.com \
  --access-token <token>

# Switch default
python main.py config set-default prod
```

### Integration with CI/CD

```bash
#!/bin/bash
# Example CI script

# Run tests
python main.py test run --mode comprehensive --output ./reports

# Check exit code
if [ $? -eq 0 ]; then
    echo "All tests passed"
else
    echo "Tests failed"
    python main.py monitor alerts
    exit 1
fi
```

## Architecture

The CLI is built with a modular architecture:

```
cli/
├── __init__.py
├── config.py              # Configuration management
├── commands/              # Command modules
│   ├── test_commands.py
│   ├── discover_commands.py
│   ├── monitor_commands.py
│   ├── collection_commands.py
│   ├── interactive_commands.py
│   ├── config_commands.py
│   └── dashboard_commands.py
└── intelligence/          # Intelligence layer
    ├── analyzer.py        # Result analysis
    ├── prioritizer.py     # Test prioritization
    ├── scheduler.py       # Smart scheduling
    ├── pattern_detector.py # Pattern detection
    └── reporting.py       # Enhanced reporting
```

## Contributing

When adding new features:

1. Add command modules in `cli/commands/`
2. Register commands in `main.py`
3. Add intelligence features in `cli/intelligence/`
4. Update this documentation

## License

Part of the Contact360 project.

