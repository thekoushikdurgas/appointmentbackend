# AI Agentic Features

## Overview

The CLI now includes comprehensive AI agentic capabilities that learn from endpoint behavior, analyze patterns, and provide intelligent recommendations for operating endpoints properly.

## Core AI Components

### 1. AI Agent (`cli/intelligence/ai_agent.py`)

The core AI agent that:
- **Learns** from every test result automatically
- **Stores** knowledge in a persistent knowledge base
- **Analyzes** endpoint behavior and patterns
- **Suggests** optimizations and improvements
- **Detects** anomalies in endpoint behavior

### 2. Knowledge Base

Stored in `~/.contact360-cli/knowledge_base.json`, containing:
- Endpoint patterns (success rates, common status codes)
- Response patterns (structure, timing)
- Error patterns (common error messages)
- Performance baselines (avg, median, P95, P99)
- Learned rules and optimization suggestions

## AI Commands

### `ai learn`
Learn from historical test results to build knowledge base.

```bash
# Learn from last 7 days (default)
python main.py ai learn

# Learn from last 30 days
python main.py ai learn --days 30
```

**What it does:**
- Processes all test results from the specified time period
- Extracts response patterns, error patterns, and performance metrics
- Updates the knowledge base with learned patterns
- Builds performance baselines for each endpoint

### `ai analyze`
Analyze endpoints using AI insights.

```bash
# Analyze specific endpoint
python main.py ai analyze --endpoint "GET /api/v1/users/"

# Analyze all endpoints in category
python main.py ai analyze --category "Authentication"

# Analyze all learned endpoints
python main.py ai analyze
```

**What it provides:**
- Reliability score (based on success rate)
- Performance metrics (avg, median, P95 response times)
- Recommendations for improvement
- Detected anomalies

### `ai optimize`
Get AI-powered optimization suggestions for operating an endpoint.

```bash
python main.py ai optimize "GET /api/v1/users/"
```

**Suggestions include:**
- Authentication requirements
- Performance optimizations
- Error handling strategies
- Query parameter usage
- Retry logic recommendations

### `ai suggest`
Get AI suggestions for test case improvements.

```bash
# Suggest for specific endpoint
python main.py ai suggest --endpoint "POST /api/v1/auth/login/"

# Suggest for all endpoints in category
python main.py ai suggest --category "Email"
```

**Suggests:**
- Missing error case tests
- Missing edge case tests
- Performance test thresholds
- Tests for common error patterns

### `ai anomalies`
Detect anomalies in endpoint behavior.

```bash
# Check specific endpoint
python main.py ai anomalies --endpoint "GET /api/v1/users/"

# Check all endpoints (high severity only)
python main.py ai anomalies --severity high

# Check all endpoints
python main.py ai anomalies
```

**Detects:**
- Performance anomalies (response time spikes)
- Status code anomalies (unexpected codes)
- Response structure anomalies

### `ai knowledge`
Manage AI knowledge base.

```bash
# Show knowledge base statistics
python main.py ai knowledge

# Export knowledge base
python main.py ai knowledge --export knowledge.json

# Import knowledge base
python main.py ai knowledge --import knowledge.json
```

## Automatic Learning

The AI agent automatically learns from every test execution:

1. **During Test Execution**: Every test result is analyzed and learned from
2. **Response Analysis**: Response structure, timing, and status codes are captured
3. **Error Learning**: Error messages and patterns are recorded
4. **Performance Tracking**: Response times are tracked to build baselines
5. **Knowledge Persistence**: Learned patterns are saved to the knowledge base

## How It Works

### Learning Process

```
Test Execution → Result Analysis → Pattern Extraction → Knowledge Base Update
```

1. **Test runs** generate results
2. **AI agent** analyzes each result
3. **Patterns** are extracted (response structure, timing, errors)
4. **Knowledge base** is updated with new patterns
5. **Baselines** are recalculated (performance, reliability)

### Analysis Process

```
Knowledge Base → Pattern Matching → Anomaly Detection → Recommendations
```

1. **Knowledge base** contains learned patterns
2. **Current behavior** is compared to learned patterns
3. **Anomalies** are detected (deviations from baseline)
4. **Recommendations** are generated based on patterns

### Optimization Process

```
Endpoint Analysis → Pattern Recognition → Suggestion Generation
```

1. **Endpoint** is analyzed using knowledge base
2. **Patterns** are recognized (auth, performance, errors)
3. **Suggestions** are generated for optimal operation

## Use Cases

### 1. Learning from Production

```bash
# Run tests in production
python main.py test run --profile production

# AI automatically learns from results
# Knowledge base is updated

# Analyze what was learned
python main.py ai analyze
```

### 2. Detecting Issues Early

```bash
# Run tests
python main.py test run

# Check for anomalies
python main.py ai anomalies

# Get optimization suggestions
python main.py ai optimize "GET /api/v1/users/"
```

### 3. Improving Test Coverage

```bash
# Get suggestions for test improvements
python main.py ai suggest --category "Email"

# Review suggestions and add missing tests
```

### 4. Performance Monitoring

```bash
# Run tests regularly
python main.py test run

# AI learns performance baselines
# Check for performance anomalies
python main.py ai anomalies --severity high
```

## Knowledge Base Structure

```json
{
  "endpoint_patterns": {
    "GET /api/v1/users/": {
      "method": "GET",
      "path": "/api/v1/users/",
      "category": "User Profile",
      "success_count": 150,
      "failure_count": 5,
      "common_status_codes": {"200": 145, "404": 5},
      "avg_response_time": 234.5,
      "requires_auth": true
    }
  },
  "response_patterns": {
    "GET /api/v1/users/": [
      {
        "timestamp": "2025-01-01T10:00:00",
        "status_code": 200,
        "response_time_ms": 230,
        "response_structure": {
          "type": "dict",
          "keys": ["id", "name", "email"]
        }
      }
    ]
  },
  "error_patterns": {
    "GET /api/v1/users/": [
      "Authentication credentials were not provided"
    ]
  },
  "performance_baselines": {
    "GET /api/v1/users/": {
      "avg": 234.5,
      "median": 230.0,
      "p95": 450.0,
      "p99": 600.0,
      "min": 180.0,
      "max": 800.0,
      "sample_count": 150
    }
  }
}
```

## Benefits

1. **Automatic Learning**: No manual configuration needed - learns from every test
2. **Intelligent Insights**: Provides actionable recommendations based on learned patterns
3. **Anomaly Detection**: Identifies issues before they become problems
4. **Performance Optimization**: Suggests improvements based on actual performance data
5. **Test Coverage**: Identifies gaps in test coverage
6. **Knowledge Persistence**: Learned patterns persist across sessions

## Integration

The AI agent is automatically integrated into:
- **Test execution**: Learns from every test result
- **Test reporting**: Provides AI insights in reports
- **Dashboard**: Shows AI-generated health scores
- **Monitoring**: Uses AI patterns for alerting

## Best Practices

1. **Regular Learning**: Run `ai learn` periodically to update knowledge base
2. **Review Anomalies**: Check `ai anomalies` regularly to catch issues early
3. **Follow Suggestions**: Implement AI suggestions for better endpoint operation
4. **Export Knowledge**: Backup knowledge base with `ai knowledge --export`
5. **Category Analysis**: Use `ai analyze --category` to focus on specific areas

## Example Workflow

```bash
# 1. Run tests (AI learns automatically)
python main.py test run

# 2. Learn from historical data
python main.py ai learn --days 7

# 3. Analyze endpoints
python main.py ai analyze --category "Authentication"

# 4. Check for anomalies
python main.py ai anomalies

# 5. Get optimization suggestions
python main.py ai optimize "POST /api/v1/auth/login/"

# 6. Get test improvement suggestions
python main.py ai suggest --category "Email"

# 7. View knowledge base stats
python main.py ai knowledge
```

## Technical Details

### Learning Algorithm

- **Incremental Learning**: Updates patterns as new data arrives
- **Statistical Analysis**: Uses mean, median, percentiles for baselines
- **Pattern Recognition**: Identifies common error messages and response structures
- **Anomaly Detection**: Uses statistical thresholds (2x, 3x baseline)

### Performance

- **Efficient Storage**: Only keeps last 100 responses per endpoint
- **Fast Lookup**: Indexed by endpoint key for quick access
- **Lazy Loading**: Knowledge base loaded only when needed
- **Auto-save**: Saves periodically during learning

### Accuracy

- **Baseline Calculation**: Requires minimum 5 samples for reliable baselines
- **Anomaly Detection**: Uses conservative thresholds to reduce false positives
- **Pattern Matching**: Uses fuzzy matching for error messages

