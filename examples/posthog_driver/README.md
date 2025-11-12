# PostHog Driver for ng_component

A production-ready driver for PostHog analytics platform following the ng_component BaseDriver contract.

## Table of Contents

- [Overview](#overview)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Authentication](#authentication)
- [HogQL Query Language](#hogql-query-language)
- [Driver Capabilities](#driver-capabilities)
- [Common Patterns](#common-patterns)
- [API Reference](#api-reference)
- [Rate Limits](#rate-limits)
- [Error Handling](#error-handling)
- [Troubleshooting](#troubleshooting)

## Overview

PostHog is an open-source product analytics platform that tracks user events, sessions, and behavior. This driver provides:

- **Discovery-first pattern**: Agents can explore available resources without prior knowledge
- **HogQL support**: SQL-like query language optimized for analytics
- **Automatic pagination**: Handle large result sets with built-in batching
- **Rate limiting**: Exponential backoff retry for 429 errors
- **Regional support**: US Cloud and EU Cloud instances

### What PostHog Tracks

- **Events**: User interactions (clicks, page views, custom events)
- **Persons**: User profiles with properties
- **Cohorts**: User segments based on behavior
- **Insights**: Pre-defined analytics queries
- **Event Definitions**: Event types and their properties
- **Property Definitions**: Custom property metadata

## Installation

```bash
# From project root
cd examples/posthog_driver
pip install -e .

# Or install dependencies directly
pip install requests python-dotenv
```

## Quick Start

```python
from posthog_driver import PostHogDriver

# Option 1: Load from environment variables
driver = PostHogDriver.from_env()

# Option 2: Explicit configuration
driver = PostHogDriver(
    api_url="https://us.posthog.com",
    api_key="phx_YourAPIKey123",
    project_id="12345"
)

# Discover available resources
objects = driver.list_objects()
print(objects)  # ["events", "persons", "cohorts", ...]

# Get schema for events
fields = driver.get_fields("events")
print(fields.keys())  # uuid, event, timestamp, distinct_id, properties, ...

# Query events using HogQL
results = driver.read("""
    SELECT event, timestamp, distinct_id, properties
    FROM events
    WHERE timestamp > now() - INTERVAL 7 DAY
    LIMIT 10
""")

for event in results:
    print(f"{event['timestamp']}: {event['event']} by {event['distinct_id']}")
```

## Authentication

PostHog requires three pieces of information:

### API Key

Personal API key (starts with `phx_` for US, `pheu_` for EU):

1. Go to **Settings** → **Project** → **API Keys**
2. Create a new Personal API Key
3. Copy the key (format: `phx_...` or `pheu_...`)

### Project ID

Numeric project identifier:

1. Go to **Settings** → **Project** → **General**
2. Find "Project ID" (numeric value)
3. Copy the number (e.g., `12345`)

### Region

PostHog offers two cloud regions:

- **US Cloud**: `https://us.posthog.com` (default)
- **EU Cloud**: `https://eu.posthog.com`

Self-hosted instances use their own URL (e.g., `https://posthog.yourcompany.com`)

### Environment Variables

Create `.env` file:

```bash
# Required
POSTHOG_API_KEY=phx_YourAPIKey123
POSTHOG_PROJECT_ID=12345

# Optional (defaults to US)
POSTHOG_REGION=us  # or "eu"
# Or specify full URL for self-hosted
POSTHOG_API_URL=https://us.posthog.com
```

Then use:

```python
from posthog_driver import PostHogDriver

# Automatically loads from .env
driver = PostHogDriver.from_env()
```

## HogQL Query Language

HogQL is PostHog's SQL-like query language for analytics. It's similar to ClickHouse SQL.

### Basic Syntax

```sql
SELECT column1, column2, ...
FROM table_name
WHERE condition
GROUP BY column
ORDER BY column [ASC|DESC]
LIMIT number
OFFSET number
```

### Available Tables

| Table | Description |
|-------|-------------|
| `events` | User events and interactions |
| `persons` | User profiles and properties |
| `person_distinct_ids` | Mapping between anonymous and identified users |
| `cohorts` | User segments |
| `groups` | Group analytics data |

### Common Columns

**events table:**
- `uuid`: Unique event identifier (UUID)
- `event`: Event name (e.g., "$pageview", "button_clicked")
- `timestamp`: Event time (DateTime)
- `distinct_id`: User identifier (String)
- `properties`: Event properties (JSON)
- `person_id`: Person UUID
- `person_properties`: Person properties at event time (JSON)

**persons table:**
- `id`: Person UUID
- `created_at`: First seen timestamp
- `properties`: Person properties (JSON)
- `is_identified`: Boolean indicating if user is identified

### Property Access

Access nested JSON properties using dot notation:

```sql
-- Access event property
SELECT properties.browser, properties.$current_url
FROM events
WHERE properties.plan_type = 'premium'

-- Access person property
SELECT person_properties.email, person_properties.name
FROM events
WHERE person_properties.plan = 'enterprise'
```

### Time Functions

```sql
-- Current time
SELECT now()

-- Time intervals
SELECT timestamp > now() - INTERVAL 7 DAY  -- Last 7 days
SELECT timestamp > now() - INTERVAL 1 HOUR  -- Last hour
SELECT timestamp > now() - INTERVAL 30 MINUTE  -- Last 30 minutes

-- Date formatting
SELECT toDate(timestamp) as date
SELECT toStartOfHour(timestamp) as hour
SELECT toStartOfDay(timestamp) as day
```

Supported intervals: `SECOND`, `MINUTE`, `HOUR`, `DAY`, `WEEK`, `MONTH`, `YEAR`

### Aggregation Functions

```sql
-- Count events
SELECT count() FROM events

-- Count distinct users
SELECT count(DISTINCT distinct_id) FROM events

-- Average, sum, min, max
SELECT avg(properties.session_duration) FROM events
SELECT sum(properties.revenue) FROM events
SELECT min(timestamp), max(timestamp) FROM events

-- Group by
SELECT event, count() as event_count
FROM events
WHERE timestamp > now() - INTERVAL 7 DAY
GROUP BY event
ORDER BY event_count DESC
```

### String Functions

```sql
-- Case conversion
SELECT lower(event), upper(distinct_id) FROM events

-- Substring
SELECT substring(distinct_id, 1, 8) FROM events

-- Concatenation
SELECT concat(event, ' - ', distinct_id) FROM events

-- Pattern matching
SELECT * FROM events WHERE event LIKE '%click%'
SELECT * FROM events WHERE properties.page ILIKE '%product%'  -- Case insensitive
```

### Conditional Logic

```sql
-- IF statement
SELECT
    event,
    if(properties.price > 100, 'expensive', 'cheap') as price_tier
FROM events

-- CASE statement
SELECT
    event,
    CASE
        WHEN properties.plan = 'enterprise' THEN 'Enterprise'
        WHEN properties.plan = 'pro' THEN 'Professional'
        ELSE 'Free'
    END as plan_name
FROM events
```

### Array Functions

```sql
-- Check if value in array
SELECT * FROM events
WHERE has(properties.features, 'advanced_analytics')

-- Array length
SELECT arrayCount(properties.tags) FROM events

-- Array join
SELECT arrayJoin(properties.features) as feature FROM events
```

### Complete Examples

**1. Recent Events by Type**

```sql
SELECT
    event,
    count() as count,
    count(DISTINCT distinct_id) as unique_users
FROM events
WHERE timestamp > now() - INTERVAL 24 HOUR
GROUP BY event
ORDER BY count DESC
LIMIT 20
```

**2. User Activity Timeline**

```sql
SELECT
    distinct_id,
    event,
    timestamp,
    properties.$current_url as url,
    properties.browser
FROM events
WHERE distinct_id = 'user_12345'
ORDER BY timestamp DESC
LIMIT 100
```

**3. Conversion Funnel**

```sql
SELECT
    toDate(timestamp) as date,
    countIf(event = 'pageview') as page_views,
    countIf(event = 'signup_clicked') as signups_started,
    countIf(event = 'signup_completed') as signups_completed
FROM events
WHERE timestamp > now() - INTERVAL 30 DAY
GROUP BY date
ORDER BY date
```

**4. Active Users by Day**

```sql
SELECT
    toDate(timestamp) as date,
    count(DISTINCT distinct_id) as daily_active_users
FROM events
WHERE timestamp > now() - INTERVAL 30 DAY
GROUP BY date
ORDER BY date
```

**5. Feature Adoption**

```sql
SELECT
    properties.feature_name as feature,
    count() as usage_count,
    count(DISTINCT distinct_id) as unique_users,
    round(avg(properties.session_duration), 2) as avg_duration
FROM events
WHERE event = 'feature_used'
    AND timestamp > now() - INTERVAL 7 DAY
GROUP BY feature
ORDER BY usage_count DESC
```

**6. Revenue by Plan Type**

```sql
SELECT
    person_properties.plan_type as plan,
    count(DISTINCT distinct_id) as users,
    sum(properties.amount) as total_revenue,
    round(sum(properties.amount) / count(DISTINCT distinct_id), 2) as avg_revenue_per_user
FROM events
WHERE event = 'purchase_completed'
    AND timestamp > now() - INTERVAL 30 DAY
GROUP BY plan
ORDER BY total_revenue DESC
```

### HogQL Limitations

- No `JOIN` between tables (use property embedding instead)
- No `UPDATE` or `DELETE` (read-only queries)
- No subqueries in `FROM` clause (use CTEs with `WITH`)
- Complex aggregations may have performance limits
- Maximum query execution time: 60 seconds

## Driver Capabilities

The driver exposes its capabilities through `get_capabilities()`:

```python
capabilities = driver.get_capabilities()

print(capabilities.read)                # True
print(capabilities.write)               # False (read-only)
print(capabilities.query_language)      # "HogQL"
print(capabilities.pagination_style)    # "OFFSET"
print(capabilities.max_page_size)       # 10000
print(capabilities.supports_relationships)  # True
```

This information helps agents understand what operations are supported.

## Common Patterns

### Pagination with Batching

For large result sets, use `read_batched()` to process data in chunks:

```python
# Process 100,000 events in batches of 1000
query = """
    SELECT event, timestamp, distinct_id
    FROM events
    WHERE timestamp > now() - INTERVAL 7 DAY
"""

total_processed = 0
for batch in driver.read_batched(query, batch_size=1000):
    # Process each batch
    print(f"Processing {len(batch)} events...")
    for event in batch:
        # Do something with event
        pass
    total_processed += len(batch)

print(f"Total processed: {total_processed}")
```

### Time-Range Queries

Always include time filters for better performance:

```python
# Good - Limited time range
results = driver.read("""
    SELECT * FROM events
    WHERE timestamp > now() - INTERVAL 7 DAY
    LIMIT 1000
""")

# Better - Specific time window
results = driver.read("""
    SELECT * FROM events
    WHERE timestamp >= '2024-01-01 00:00:00'
      AND timestamp < '2024-01-08 00:00:00'
    LIMIT 1000
""")
```

### Working with Properties

PostHog stores event and person properties as JSON:

```python
# Filter by event property
results = driver.read("""
    SELECT event, properties
    FROM events
    WHERE properties.button_id = 'signup_btn'
      AND timestamp > now() - INTERVAL 1 DAY
""")

# Access nested properties
results = driver.read("""
    SELECT
        distinct_id,
        properties.user.email as email,
        properties.user.plan as plan
    FROM events
    WHERE event = 'subscription_upgraded'
""")
```

### Aggregation Queries

Group and aggregate data efficiently:

```python
# Daily event counts
results = driver.read("""
    SELECT
        toDate(timestamp) as date,
        event,
        count() as count
    FROM events
    WHERE timestamp > now() - INTERVAL 30 DAY
    GROUP BY date, event
    ORDER BY date DESC, count DESC
""")

# User engagement metrics
results = driver.read("""
    SELECT
        distinct_id,
        count() as event_count,
        count(DISTINCT event) as unique_events,
        min(timestamp) as first_seen,
        max(timestamp) as last_seen
    FROM events
    WHERE timestamp > now() - INTERVAL 30 DAY
    GROUP BY distinct_id
    HAVING event_count > 10
    ORDER BY event_count DESC
""")
```

### Dynamic Schema Discovery

Agents can discover available resources and fields:

```python
# Step 1: Discover objects
objects = driver.list_objects()
print(f"Available objects: {objects}")

# Step 2: Get schema for specific object
for obj in objects:
    fields = driver.get_fields(obj)
    print(f"\n{obj} fields:")
    for field_name, field_info in fields.items():
        print(f"  {field_name}: {field_info['type']} - {field_info['description']}")

# Step 3: Generate query dynamically
# Agent now knows what fields exist and can construct valid queries
```

### Rate Limit Handling

The driver automatically retries on rate limits, but you can check status:

```python
# Check current rate limit status
status = driver.get_rate_limit_status()
print(f"Remaining requests: {status['remaining']}")
print(f"Limit: {status['limit']}")
print(f"Reset at: {status['reset_at']}")

# If you need to be cautious
if status['remaining'] < 10:
    print("Approaching rate limit, slowing down...")
    time.sleep(60)
```

## API Reference

### PostHogDriver

Main driver class implementing the BaseDriver contract.

#### Constructor

```python
PostHogDriver(
    api_url: str,
    api_key: str,
    project_id: str,
    timeout: int = 30,
    max_retries: int = 3,
    debug: bool = False,
    **kwargs
)
```

**Parameters:**
- `api_url`: PostHog API URL (e.g., "https://us.posthog.com")
- `api_key`: Personal API key (starts with phx_ or pheu_)
- `project_id`: Numeric project ID
- `timeout`: Request timeout in seconds (default: 30)
- `max_retries`: Maximum retry attempts for rate limits (default: 3)
- `debug`: Enable debug logging (default: False)

**Raises:**
- `AuthenticationError`: Invalid API key or project ID
- `ConnectionError`: Cannot reach PostHog API

#### from_env

```python
@classmethod
PostHogDriver.from_env(**kwargs) -> PostHogDriver
```

Create driver from environment variables.

**Environment Variables:**
- `POSTHOG_API_KEY` (required): API key
- `POSTHOG_PROJECT_ID` (required): Project ID
- `POSTHOG_REGION` (optional): "us" or "eu" (default: "us")
- `POSTHOG_API_URL` (optional): Full API URL (overrides region)
- `POSTHOG_TIMEOUT` (optional): Request timeout
- `POSTHOG_MAX_RETRIES` (optional): Max retries

**Example:**
```python
driver = PostHogDriver.from_env(debug=True)
```

#### list_objects

```python
driver.list_objects() -> List[str]
```

Discover available resource types.

**Returns:** List of object names:
- `"events"`: User events and interactions
- `"persons"`: User profiles
- `"cohorts"`: User segments
- `"insights"`: Pre-defined analytics queries
- `"event_definitions"`: Event type metadata
- `"property_definitions"`: Property metadata

#### get_fields

```python
driver.get_fields(object_name: str) -> Dict[str, Any]
```

Get schema for specific resource type.

**Parameters:**
- `object_name`: One of the objects from list_objects()

**Returns:** Dictionary mapping field names to field info:
```python
{
    "field_name": {
        "type": "string",           # Field data type
        "label": "Field Label",     # Human-readable name
        "description": "...",       # Field description
        "required": False,          # Is field required
        "nullable": True            # Can field be null
    }
}
```

**Raises:**
- `ObjectNotFoundError`: Unknown object name

#### read

```python
driver.read(
    query: str,
    limit: Optional[int] = None,
    offset: Optional[int] = None
) -> List[Dict[str, Any]]
```

Execute HogQL query and return results.

**Parameters:**
- `query`: HogQL query string
- `limit`: Maximum results to return (optional, overrides query LIMIT)
- `offset`: Number of results to skip (optional, overrides query OFFSET)

**Returns:** List of dictionaries, one per result row

**Raises:**
- `QuerySyntaxError`: Invalid HogQL syntax
- `RateLimitError`: Rate limit exceeded (after retries)
- `TimeoutError`: Query execution timeout
- `ConnectionError`: API communication error

**Example:**
```python
results = driver.read("""
    SELECT event, count() as count
    FROM events
    WHERE timestamp > now() - INTERVAL 7 DAY
    GROUP BY event
""", limit=10)
```

#### read_batched

```python
driver.read_batched(
    query: str,
    batch_size: int = 1000
) -> Iterator[List[Dict[str, Any]]]
```

Execute query and yield results in batches.

**Parameters:**
- `query`: HogQL query string (do not include LIMIT/OFFSET)
- `batch_size`: Results per batch (default: 1000, max: 10000)

**Yields:** Batches of results (each batch is a list of dicts)

**Example:**
```python
for batch in driver.read_batched("SELECT * FROM events", batch_size=500):
    print(f"Processing {len(batch)} events")
    for event in batch:
        process_event(event)
```

#### get_capabilities

```python
driver.get_capabilities() -> DriverCapabilities
```

Get driver capability information.

**Returns:** DriverCapabilities object with:
- `read`: True
- `write`: False
- `query_language`: "HogQL"
- `pagination_style`: "OFFSET"
- `max_page_size`: 10000
- `supports_relationships`: True

#### get_rate_limit_status

```python
driver.get_rate_limit_status() -> Dict[str, Any]
```

Get current rate limit status.

**Returns:**
```python
{
    "limit": 240,              # Requests per minute
    "remaining": 180,          # Remaining requests
    "reset_at": "1699876543"   # Unix timestamp when limit resets
}
```

## Rate Limits

PostHog enforces different rate limits based on endpoint type:

| Endpoint Type | Requests/Minute | Requests/Hour |
|---------------|-----------------|---------------|
| Analytics queries (HogQL) | 240 | 1,200 |
| CRUD operations | 480 | 4,800 |

### Automatic Retry

The driver automatically retries on 429 (rate limit) errors with exponential backoff:

- **1st retry**: Wait 1 second
- **2nd retry**: Wait 2 seconds
- **3rd retry**: Wait 4 seconds
- **After max_retries**: Raise `RateLimitError`

### Best Practices

1. **Include time filters**: Limit query scope with `WHERE timestamp > ...`
2. **Use LIMIT**: Always specify reasonable LIMIT values
3. **Batch processing**: Use `read_batched()` for large datasets
4. **Monitor remaining**: Check `get_rate_limit_status()` before heavy operations
5. **Increase timeout**: Set higher timeout for complex queries

```python
# Good query pattern
driver = PostHogDriver.from_env(timeout=60, max_retries=5)

query = """
    SELECT * FROM events
    WHERE timestamp > now() - INTERVAL 1 DAY
    LIMIT 10000
"""

for batch in driver.read_batched(query, batch_size=1000):
    process_batch(batch)
    time.sleep(0.5)  # Optional: Add delay between batches
```

## Error Handling

The driver uses structured exceptions for clear error handling:

### Exception Hierarchy

```python
PostHogError (base)
├── AuthenticationError      # Invalid credentials
├── ConnectionError          # Network/API unavailable
├── ObjectNotFoundError      # Unknown resource type
├── QuerySyntaxError         # Invalid HogQL
├── RateLimitError           # Rate limit exceeded
└── TimeoutError             # Query timeout
```

### Exception Details

All exceptions include:
- `message`: Human-readable error description
- `details`: Dictionary with additional context

### Handling Examples

**Basic try-catch:**

```python
from posthog_driver import PostHogDriver, QuerySyntaxError, RateLimitError

try:
    driver = PostHogDriver.from_env()
    results = driver.read("SELECT * FROM events LIMIT 10")
except QuerySyntaxError as e:
    print(f"Invalid query: {e.message}")
    print(f"Query: {e.details.get('query')}")
except RateLimitError as e:
    print(f"Rate limited: {e.message}")
    retry_after = e.details.get('retry_after', 60)
    print(f"Retry after {retry_after} seconds")
except Exception as e:
    print(f"Unexpected error: {e}")
```

**Comprehensive error handling:**

```python
from posthog_driver import (
    PostHogDriver,
    AuthenticationError,
    ConnectionError,
    ObjectNotFoundError,
    QuerySyntaxError,
    RateLimitError,
    TimeoutError
)

try:
    driver = PostHogDriver.from_env()
    results = driver.read("""
        SELECT event, count() as count
        FROM events
        WHERE timestamp > now() - INTERVAL 7 DAY
        GROUP BY event
    """)

except AuthenticationError as e:
    print("Authentication failed. Check your API key and project ID.")
    print(f"Details: {e.details}")

except ConnectionError as e:
    print("Cannot reach PostHog API. Check your network and API URL.")
    print(f"URL attempted: {e.details.get('url')}")

except ObjectNotFoundError as e:
    print(f"Unknown object: {e.message}")
    suggestions = e.details.get('suggestions', [])
    if suggestions:
        print(f"Did you mean: {', '.join(suggestions)}?")

except QuerySyntaxError as e:
    print(f"Invalid HogQL syntax: {e.message}")
    print(f"Query: {e.details.get('query')}")
    print(f"Error position: {e.details.get('position')}")

except RateLimitError as e:
    print(f"Rate limit exceeded: {e.message}")
    retry_after = e.details.get('retry_after', 60)
    print(f"Retry after {retry_after} seconds")
    print(f"Limit: {e.details.get('limit')} requests/minute")

except TimeoutError as e:
    print(f"Query timeout: {e.message}")
    print("Try reducing the time range or adding more filters")

except Exception as e:
    print(f"Unexpected error: {e}")
```

## Troubleshooting

### Authentication Issues

**Problem:** `AuthenticationError: Invalid API key`

**Solutions:**
1. Verify API key format (starts with `phx_` or `pheu_`)
2. Check key hasn't been revoked in PostHog settings
3. Ensure project ID is numeric
4. Try regenerating API key

```python
# Test authentication
from posthog_driver import PostHogDriver, AuthenticationError

try:
    driver = PostHogDriver.from_env(debug=True)
    print("Authentication successful")
except AuthenticationError as e:
    print(f"Auth failed: {e.details}")
```

### Connection Issues

**Problem:** `ConnectionError: Cannot reach PostHog API`

**Solutions:**
1. Check `POSTHOG_REGION` or `POSTHOG_API_URL` is correct
2. Verify network connectivity: `ping us.posthog.com`
3. Check firewall rules allow HTTPS (443)
4. Try increasing timeout: `PostHogDriver.from_env(timeout=60)`

```python
# Test connection
import requests

api_url = "https://us.posthog.com"
try:
    response = requests.get(f"{api_url}/api/projects/", timeout=10)
    print(f"Connection OK: {response.status_code}")
except Exception as e:
    print(f"Connection failed: {e}")
```

### Query Syntax Errors

**Problem:** `QuerySyntaxError: Invalid HogQL syntax`

**Solutions:**
1. Check table names: `events`, `persons` (not `event`, `person`)
2. Verify column names: Use `get_fields()` to see available columns
3. Use proper property syntax: `properties.field_name`
4. Check function names: `count()`, `toDate()`, etc.

```python
# Debug query
driver = PostHogDriver.from_env(debug=True)

# First, check available fields
fields = driver.get_fields("events")
print("Available fields:", list(fields.keys()))

# Then construct query
query = f"SELECT {', '.join(list(fields.keys())[:5])} FROM events LIMIT 10"
results = driver.read(query)
```

### Rate Limiting

**Problem:** `RateLimitError: API rate limit exceeded`

**Solutions:**
1. Add delays between requests: `time.sleep(1)`
2. Increase `max_retries`: `PostHogDriver(max_retries=5)`
3. Reduce query frequency
4. Use smaller `batch_size` in `read_batched()`
5. Check current status: `get_rate_limit_status()`

```python
# Rate-limit-aware processing
driver = PostHogDriver.from_env(max_retries=5)

for batch in driver.read_batched(query, batch_size=500):
    process_batch(batch)

    # Check if approaching limit
    status = driver.get_rate_limit_status()
    if status['remaining'] < 50:
        print("Approaching rate limit, waiting 60s...")
        time.sleep(60)
```

### Query Timeouts

**Problem:** `TimeoutError: Request timed out`

**Solutions:**
1. Increase timeout: `PostHogDriver(timeout=60)`
2. Reduce time range: `WHERE timestamp > now() - INTERVAL 1 DAY`
3. Add more filters to reduce result set
4. Use `LIMIT` to cap results: `LIMIT 10000`
5. Break query into smaller time windows

```python
# Process large time range in chunks
from datetime import datetime, timedelta

driver = PostHogDriver.from_env(timeout=60)
start_date = datetime(2024, 1, 1)
end_date = datetime(2024, 1, 31)

current = start_date
while current < end_date:
    next_date = current + timedelta(days=1)

    query = f"""
        SELECT * FROM events
        WHERE timestamp >= '{current.isoformat()}'
          AND timestamp < '{next_date.isoformat()}'
        LIMIT 10000
    """

    results = driver.read(query)
    print(f"{current.date()}: {len(results)} events")

    current = next_date
```

### Empty Results

**Problem:** Query returns no results unexpectedly

**Solutions:**
1. Verify project has data: `SELECT count() FROM events`
2. Check time range: `WHERE timestamp > now() - INTERVAL 30 DAY`
3. Test simpler query first: `SELECT * FROM events LIMIT 10`
4. Verify filters aren't too restrictive
5. Check property names are correct

```python
# Debug empty results
driver = PostHogDriver.from_env()

# Step 1: Check if any data exists
total = driver.read("SELECT count() as total FROM events")
print(f"Total events: {total[0]['total']}")

# Step 2: Get recent events
recent = driver.read("""
    SELECT * FROM events
    ORDER BY timestamp DESC
    LIMIT 10
""")
print(f"Recent events: {len(recent)}")

# Step 3: Check time range
with_time = driver.read("""
    SELECT
        min(timestamp) as first_event,
        max(timestamp) as last_event,
        count() as total
    FROM events
""")
print(f"Time range: {with_time[0]}")
```

### Debug Mode

Enable debug logging to see all API requests and responses:

```python
driver = PostHogDriver.from_env(debug=True)

# This will print:
# - API URLs
# - Request parameters
# - Response status codes
# - Rate limit headers
# - Error details

results = driver.read("SELECT * FROM events LIMIT 10")
```

## Examples

See the `examples/` directory for complete working examples:

- `basic_query.py` - Simple event queries
- `user_activity.py` - Track user behavior
- `aggregation.py` - Event counts and metrics
- `pagination.py` - Handle large result sets
- `error_handling.py` - Comprehensive error handling

## Support

- **PostHog Documentation**: https://posthog.com/docs
- **HogQL Reference**: https://posthog.com/docs/hogql
- **API Reference**: https://posthog.com/docs/api
- **ng_component**: https://github.com/padak/ng_component

## License

This driver follows the license of the ng_component project.
