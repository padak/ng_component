# Salesforce Driver - Mock Implementation

> **For AI Agents**: This is a Python driver that connects to a mock Salesforce API. It helps you discover, explore, and query Salesforce-like data without needing real Salesforce credentials. Perfect for testing, development, and learning Salesforce integration patterns.

This driver provides a Python interface to interact with a mock Salesforce API, allowing you to perform queries, discover objects, and retrieve field schemas without connecting to a real Salesforce instance.

## What is Salesforce?

**Salesforce** is a Customer Relationship Management (CRM) platform used by businesses to manage customer data, sales pipelines, marketing campaigns, and service operations. It stores data in **objects** (like database tables) such as:

- **Lead**: Potential customers who haven't been qualified yet
- **Campaign**: Marketing campaigns that generate leads
- **Opportunity**: Qualified sales opportunities with revenue potential
- **Account**: Companies or organizations (customers/prospects)

These objects have **fields** (like database columns) and can be **related** to each other (like foreign keys).

## What This Driver Does

This driver is a lightweight Python client that communicates with a mock Salesforce API over HTTP. It simulates real Salesforce behavior while being completely isolated from production systems.

**Key capabilities:**
- **Discovery**: List available objects and inspect their field schemas
- **Querying**: Execute SOQL (Salesforce Object Query Language) queries
- **Relationships**: Query related objects using joins
- **Error Handling**: Clear, specific exceptions for different error scenarios

**Use cases:**
- Testing integrations without affecting real data
- Development environments where Salesforce access is limited
- Learning how to interact with Salesforce APIs
- Prototyping data workflows
- AI agent integration with CRM systems

**Important**: This is a MOCK driver. It does not connect to real Salesforce. All data is simulated.

## Authentication & Setup

### Required Environment Variables

The driver requires two environment variables:

1. **SF_API_KEY** (required): Your API key for authentication
2. **SF_API_URL** (optional): The API endpoint URL (defaults to `http://localhost:8000`)

### Setup Instructions

**Step 1: Install dependencies**
```bash
pip install -r requirements.txt
```

**Step 2: Set environment variables**

Option A - Export in your shell:
```bash
export SF_API_KEY="your-api-key"
export SF_API_URL="http://localhost:8000"  # optional
```

Option B - Set in Python code:
```python
import os
os.environ['SF_API_KEY'] = 'your-api-key'
os.environ['SF_API_URL'] = 'http://localhost:8000'
```

Option C - Create a `.env` file:
```env
SF_API_KEY=your-api-key
SF_API_URL=http://localhost:8000
```

**Step 3: Verify connection**
```bash
python examples/list_objects.py
```

### For AI Agents

As an AI agent, you should:
1. Check that `SF_API_KEY` and `SF_API_URL` are set before making requests
2. Use discovery methods (`list_objects()`, `get_fields()`) to understand available data
3. Build queries based on discovered schema rather than assumptions
4. Handle exceptions gracefully and provide clear error messages to users

## Quick Start

### Basic Authentication

The driver authenticates using an API key. You can provide it in two ways:

**Method 1: Environment variable (recommended)**
```python
import os
os.environ['SF_API_KEY'] = 'your-api-key'

from salesforce_driver import SalesforceClient

client = SalesforceClient()
```

**Method 2: Direct parameter**
```python
from salesforce_driver import SalesforceClient

client = SalesforceClient(
    api_url="http://localhost:8000",
    api_key="your-api-key"
)
```

### Basic Operations

#### 1. List Available Objects

Before querying, discover what objects are available:

```python
from salesforce_driver import SalesforceClient

client = SalesforceClient()

# Get all available Salesforce objects
objects = client.list_objects()
print(f"Available objects: {objects}")
# Output: Available objects: ['Lead', 'Campaign', 'Opportunity', 'Account']
```

#### 2. Get Field Schema

Understand the structure of an object before querying:

```python
# Get all fields for the Lead object
fields = client.get_fields('Lead')

for field_name, field_info in fields.items():
    field_type = field_info.get('type', 'unknown')
    print(f"{field_name}: {field_type}")

# Output:
# Id: string
# Name: string
# Email: string
# Status: string
# Company: string
# CreatedDate: datetime
```

#### 3. Execute SOQL Queries

Query data using SOQL (Salesforce Object Query Language):

```python
# Simple query
leads = client.query("SELECT Id, Name, Email FROM Lead LIMIT 5")

for lead in leads:
    print(f"Lead: {lead['Name']} - {lead['Email']}")

# Query with WHERE clause
recent_leads = client.query("""
    SELECT Id, Name, Email, CreatedDate
    FROM Lead
    WHERE CreatedDate > 2024-01-01
    ORDER BY CreatedDate DESC
""")

# Query with relationships (joins)
leads_with_campaigns = client.query("""
    SELECT
        Lead.Id,
        Lead.Name,
        Lead.Email,
        Campaign.Name AS CampaignName
    FROM Lead
    WHERE Campaign.Id != null
""")
```

## Discovery Capabilities

> **For AI Agents**: Discovery is CRITICAL. Always use these methods before writing queries to understand what data is available. Never guess field names or object structures.

The driver provides two main discovery methods to help you explore the data model:

### 1. `list_objects()` - Object Discovery

Retrieves a list of all available Salesforce objects in the system.

```python
objects = client.list_objects()
# Returns: ['Lead', 'Campaign', 'Opportunity', 'Account']
```

**When to use:**
- **ALWAYS** at the start of any integration or query task
- When exploring an unfamiliar Salesforce instance
- To validate that a specific object exists before querying
- When the user asks "what data is available?"

**For AI Agents:**
- Call this FIRST before attempting any queries
- Use the results to validate user requests (e.g., if user asks for "Contacts" but only "Leads" exist, inform them)
- Cache results as objects rarely change during a session

### 2. `get_fields(object_name)` - Schema Discovery

Retrieves the complete field schema for a specific object, including field names, types, and metadata.

```python
schema = client.get_fields('Lead')

# Response structure:
# {
#   'name': 'Lead',
#   'label': 'Lead',
#   'fields': [
#     {
#       'name': 'Id',
#       'type': 'string',
#       'label': 'Lead ID',
#       'nullable': False,
#       'createable': False,
#       'updateable': False
#     },
#     {
#       'name': 'Email',
#       'type': 'string',
#       'label': 'Email',
#       'nullable': True,
#       'createable': True,
#       'updateable': True
#     },
#     # ... more fields
#   ]
# }

# Working with the schema
for field in schema['fields']:
    print(f"{field['name']}: {field['type']}")
```

**When to use:**
- Before writing ANY query against an object
- To understand data types for proper query construction
- To validate field names before using them in WHERE clauses
- When building dynamic queries based on available fields
- When the user asks "what fields does X have?"

**For AI Agents:**
- Call this BEFORE constructing queries to ensure field names are correct
- Use the type information to properly format query values (strings need quotes, numbers don't)
- Check `nullable` to understand which fields might have missing data
- Build your SELECT clause from actual field names, not assumptions
- If a user asks for a field that doesn't exist, suggest similar fields from the schema

## Best Practices for AI Agents

> **This section is specifically for AI agents integrating with Salesforce data.**

### The Discovery-First Workflow

As an AI agent, ALWAYS follow this workflow:

1. **Discover objects** → `list_objects()`
2. **Validate object exists** → Check if requested object is in the list
3. **Discover fields** → `get_fields(object_name)`
4. **Build query from actual fields** → Use field names from schema
5. **Execute query** → `query(soql)`
6. **Handle results** → Process and present data to user

### Handling User Requests

When a user asks for data:

**❌ Bad approach:**
```python
# DON'T assume field names or object structure
leads = client.query("SELECT Id, FullName, EmailAddress FROM Contacts LIMIT 10")
# This will fail if fields are named differently!
```

**✅ Good approach:**
```python
# 1. Discover what's available
objects = client.list_objects()

# 2. Validate object
if 'Lead' not in objects:
    print(f"Lead object not found. Available: {', '.join(objects)}")
    return

# 3. Get schema
schema = client.get_fields('Lead')
field_names = [f['name'] for f in schema['fields']]

# 4. Build query from actual fields
common_fields = ['Id', 'Name', 'Email', 'Company']
available_fields = [f for f in common_fields if f in field_names]

# 5. Query
query = f"SELECT {', '.join(available_fields)} FROM Lead LIMIT 10"
leads = client.query(query)
```

### When Schema Discovery Fails

If you can't find a field the user requested:

```python
schema = client.get_fields('Lead')
field_names = [f['name'] for f in schema['fields']]

requested_field = 'EmailAddress'
if requested_field not in field_names:
    # Suggest alternatives
    similar = [f for f in field_names if 'email' in f.lower()]
    print(f"Field '{requested_field}' not found.")
    if similar:
        print(f"Did you mean: {', '.join(similar)}?")
    else:
        print(f"Available fields: {', '.join(field_names[:10])}...")
```

### Exception Handling for Agents

Always wrap API calls in appropriate exception handlers:

```python
from salesforce_driver import (
    ConnectionError,
    AuthError,
    ObjectNotFoundError,
    QueryError
)

try:
    leads = client.query("SELECT Id, Name FROM Lead")
except ConnectionError:
    print("Cannot connect to Salesforce API. Is the server running?")
except AuthError:
    print("Authentication failed. Check SF_API_KEY environment variable.")
except ObjectNotFoundError as e:
    print(f"Object not found: {e}")
    print("Run list_objects() to see what's available.")
except QueryError as e:
    print(f"Query failed: {e}")
    print("Check SOQL syntax and field names.")
```

### Query Construction Tips for Agents

**Date filtering:**
```python
from datetime import datetime, timedelta

# Format dates as YYYY-MM-DD for SOQL
date_30_days_ago = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
query = f"SELECT Id, Name FROM Lead WHERE CreatedDate > '{date_30_days_ago}'"
```

**String values in WHERE clauses:**
```python
# Always use single quotes for string literals in SOQL
query = "SELECT Id, Name FROM Lead WHERE Status = 'Open'"  # Correct
# NOT: WHERE Status = "Open"  # Wrong
```

**Null checks:**
```python
# Check for presence of data
query = "SELECT Id, Name FROM Lead WHERE Email != null"

# Check for missing data
query = "SELECT Id, Name FROM Lead WHERE Email = null"
```

**Relationships:**
```python
# To query related data, use dot notation
query = """
    SELECT Lead.Name, Campaign.Name
    FROM Lead
    WHERE Campaign.Id != null
"""
```

### Presenting Results to Users

When showing query results to users:

```python
leads = client.query("SELECT Id, Name, Email, Status FROM Lead LIMIT 10")

if not leads:
    print("No leads found matching your criteria.")
else:
    print(f"Found {len(leads)} leads:\n")
    for i, lead in enumerate(leads, 1):
        print(f"{i}. {lead.get('Name', 'N/A')}")
        print(f"   Email: {lead.get('Email', 'N/A')}")
        print(f"   Status: {lead.get('Status', 'N/A')}\n")
```

## Best Practices for Querying

### 1. Always Use Discovery First

Don't guess field names or object structures. Use discovery methods:

```python
# BAD: Guessing field names
try:
    leads = client.query("SELECT Id, FullName, EmailAddress FROM Lead")
except Exception as e:
    print(f"Failed: {e}")

# GOOD: Using discovery to find correct field names
fields = client.get_fields('Lead')
available_fields = list(fields.keys())
print(f"Available fields: {available_fields}")

# Now query with correct field names
leads = client.query(f"SELECT {', '.join(available_fields[:5])} FROM Lead")
```

### 2. Handle Errors Gracefully

The driver provides specific exception types for different error scenarios:

```python
from salesforce_driver import (
    SalesforceClient,
    ConnectionError,
    AuthError,
    ObjectNotFoundError,
    QueryError
)

client = SalesforceClient()

try:
    leads = client.query("SELECT Id, Name FROM Lead")
except ConnectionError as e:
    print(f"Cannot connect to API. Is the server running? Error: {e}")
except AuthError as e:
    print(f"Authentication failed. Check your API key. Error: {e}")
except ObjectNotFoundError as e:
    print(f"Object not found. Check object name. Error: {e}")
except QueryError as e:
    print(f"Query failed. Check SOQL syntax. Error: {e}")
```

### 3. Use LIMIT for Exploration

When exploring data, always use LIMIT to avoid overwhelming results:

```python
# Get a sample of records first
sample = client.query("SELECT Id, Name, Email FROM Lead LIMIT 10")

# Inspect the structure
if sample:
    print("Sample record structure:")
    print(sample[0].keys())

# Once you understand the data, fetch more if needed
all_leads = client.query("SELECT Id, Name, Email FROM Lead")
```

### 4. Validate Objects Before Querying

Always check if an object exists before querying:

```python
def safe_query(client, object_name, fields, where_clause=""):
    """Safely query an object with validation"""
    # Check if object exists
    available_objects = client.list_objects()
    if object_name not in available_objects:
        print(f"Object '{object_name}' not found")
        print(f"Available objects: {available_objects}")
        return []

    # Build query
    query = f"SELECT {fields} FROM {object_name}"
    if where_clause:
        query += f" WHERE {where_clause}"

    # Execute
    try:
        return client.query(query)
    except QueryError as e:
        print(f"Query failed: {e}")
        return []

# Usage
leads = safe_query(client, "Lead", "Id, Name, Email", "Status = 'Open'")
```

### 5. Use Context Manager for Resource Cleanup

The client supports context managers for automatic cleanup:

```python
# Automatically closes connection when done
with SalesforceClient() as client:
    leads = client.query("SELECT Id, Name FROM Lead")
    # Process leads...
# Connection automatically closed here
```

## Common Query Patterns

### Filter by Date Range

```python
from datetime import datetime, timedelta

# Leads from the last 30 days
thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
query = f"""
    SELECT Id, Name, Email, CreatedDate
    FROM Lead
    WHERE CreatedDate > {thirty_days_ago}
    ORDER BY CreatedDate DESC
"""
leads = client.query(query)
```

### Join Related Objects

```python
# Get leads with their associated campaign information
query = """
    SELECT
        Lead.Id,
        Lead.Name,
        Lead.Email,
        Lead.Status,
        Campaign.Name AS CampaignName,
        Campaign.Status AS CampaignStatus
    FROM Lead
    WHERE Campaign.Id != null
"""
leads_with_campaigns = client.query(query)

for lead in leads_with_campaigns:
    print(f"{lead['Name']} is in campaign: {lead['CampaignName']}")
```

### Aggregate Data

```python
# Count leads by status
count = client.get_object_count('Lead')
print(f"Total leads: {count}")

# For more complex aggregations, use COUNT() in queries
# (Note: Support depends on mock API implementation)
```

### Null Checks

```python
# Find leads with email addresses
query = "SELECT Id, Name, Email FROM Lead WHERE Email != null"
leads_with_email = client.query(query)

# Find leads without campaigns
query = "SELECT Id, Name FROM Lead WHERE Campaign.Id = null"
leads_without_campaigns = client.query(query)
```

## Rate Limiting

**Good news!** This is a mock API with no rate limiting. You can make as many requests as you need without worrying about:

- API call limits
- Rate throttling
- Governor limits
- Concurrent request restrictions

However, it's still good practice to:
- Use LIMIT clauses to reduce data transfer
- Cache discovery results (objects and fields rarely change)
- Batch similar queries together when possible

## Example Workflows

### Workflow 1: Exploring a New Object

```python
from salesforce_driver import SalesforceClient

client = SalesforceClient()

# Step 1: See what's available
objects = client.list_objects()
print(f"Available objects: {objects}")

# Step 2: Pick an object and explore its structure
object_name = "Lead"
fields = client.get_fields(object_name)

print(f"\nFields in {object_name}:")
for field_name, field_def in fields.items():
    print(f"  {field_name} ({field_def['type']})")

# Step 3: Get a sample of data
sample = client.query(f"SELECT * FROM {object_name} LIMIT 5")
print(f"\nSample records: {len(sample)}")
if sample:
    print(f"First record: {sample[0]}")
```

### Workflow 2: Building a Report

```python
from salesforce_driver import SalesforceClient

client = SalesforceClient()

# Get all leads with their campaign data
leads = client.query("""
    SELECT
        Lead.Id,
        Lead.Name,
        Lead.Email,
        Lead.Status,
        Lead.CreatedDate,
        Campaign.Name AS CampaignName
    FROM Lead
    WHERE Campaign.Id != null
    ORDER BY Lead.CreatedDate DESC
""")

# Generate report
print("Lead Campaign Report")
print("=" * 80)
for lead in leads:
    print(f"{lead['Name']:30} | {lead['Status']:15} | {lead['CampaignName']}")
```

### Workflow 3: Data Validation

```python
from salesforce_driver import SalesforceClient, QueryError

def validate_lead_data(client):
    """Validate lead data quality"""
    issues = []

    # Check for leads without email
    no_email = client.query(
        "SELECT Id, Name FROM Lead WHERE Email = null"
    )
    if no_email:
        issues.append(f"{len(no_email)} leads missing email addresses")

    # Check for leads without companies
    no_company = client.query(
        "SELECT Id, Name FROM Lead WHERE Company = null"
    )
    if no_company:
        issues.append(f"{len(no_company)} leads missing company names")

    # Report findings
    if issues:
        print("Data Quality Issues Found:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("All leads have complete data!")

    return issues

client = SalesforceClient()
validate_lead_data(client)
```

## Troubleshooting

### Issue: ConnectionError

**Problem**: Cannot connect to the API

**Solution**:
1. Verify the mock API server is running
2. Check the API URL is correct: `echo $SF_API_URL`
3. Test connectivity: `curl http://localhost:8000/objects`

### Issue: AuthError

**Problem**: Authentication failed

**Solution**:
1. Verify your API key is set: `echo $SF_API_KEY`
2. Check the API key is correct for the mock server
3. Ensure the key is being passed correctly to the client

### Issue: ObjectNotFoundError

**Problem**: Salesforce object not found

**Solution**:
1. Use `list_objects()` to see available objects
2. Check spelling and capitalization (Salesforce is case-sensitive)
3. Verify the mock API supports that object type

### Issue: QueryError

**Problem**: SOQL query failed

**Solution**:
1. Use `get_fields(object_name)` to verify field names
2. Check SOQL syntax (must start with SELECT)
3. Verify field names are spelled correctly
4. Check that relationship fields exist (e.g., Campaign.Name)

## Additional Resources

- See `examples/` directory for complete working examples
- Read `docs/SALESFORCE_OVERVIEW.md` for deeper Salesforce concepts
- Check the mock API documentation for supported features

## Support

This is a mock driver for testing purposes. For questions about real Salesforce APIs, refer to the official Salesforce documentation.

For issues with this driver:
1. Check the troubleshooting section above
2. Review the example code in `examples/`
3. Verify the mock API server is running correctly
