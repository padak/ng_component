# Driver Contract for Agent-Based Integration System

**Date:** 2025-11-11
**Purpose:** Define the interface that all drivers must implement for the Agent-Based Integration System

---

## Overview

A **driver** is a Python module that provides a standardized interface for agents to interact with external data sources (Salesforce, PostgreSQL, HubSpot, REST APIs, etc.). The driver handles:

1. **Discovery** - What data is available?
2. **Schema Introspection** - What fields/columns exist?
3. **Query Execution** - How to fetch data?

---

## Core Contract

Every driver MUST implement these three methods:

### 1. `list_objects() -> List[str]`

**Purpose:** Discover all available objects/tables/entities in the data source.

**Returns:** List of object names (e.g., `["Lead", "Campaign", "Account"]`)

**Example:**
```python
from salesforce_driver import SalesforceClient

client = SalesforceClient(api_url="...", api_key="...")
objects = client.list_objects()
# Returns: ["Lead", "Opportunity", "Account", "Campaign"]
```

**Agent Usage:**
```
Agent: "What data do you have?"
→ calls list_objects()
→ Agent: "I can help you with: Lead, Opportunity, Account, Campaign"
```

---

### 2. `get_fields(object_name: str) -> Dict[str, Any]`

**Purpose:** Get complete field schema for a specific object.

**Parameters:**
- `object_name` (str): Name of object (e.g., "Lead")

**Returns:** Dictionary with field definitions:
```python
{
    "Id": {
        "type": "string",
        "label": "ID",
        "required": True
    },
    "FirstName": {
        "type": "string",
        "label": "First Name",
        "required": False
    },
    "Status": {
        "type": "string",
        "label": "Status",
        "required": False
    }
}
```

**Example:**
```python
fields = client.get_fields("Lead")
# Returns: {"Id": {...}, "FirstName": {...}, "Status": {...}, ...}
```

**Agent Usage:**
```
Agent: "What fields does Lead have?"
→ calls get_fields("Lead")
→ Agent: "Lead has: Id, FirstName, LastName, Status, Email, Company..."
```

---

### 3. `query(query_string: str) -> List[Dict[str, Any]]`

**Purpose:** Execute a query and return results.

**Parameters:**
- `query_string` (str): Query in the driver's native query language (SOQL, SQL, etc.)

**Returns:** List of dictionaries (one per record):
```python
[
    {
        "Id": "00Q...",
        "FirstName": "John",
        "LastName": "Doe",
        "Status": "Qualified"
    },
    {
        "Id": "00Q...",
        "FirstName": "Jane",
        "LastName": "Smith",
        "Status": "New"
    }
]
```

**Example:**
```python
results = client.query(
    "SELECT Id, FirstName, LastName, Status FROM Lead WHERE Status = 'Qualified'"
)
# Returns: [{"Id": "...", "FirstName": "John", ...}, ...]
```

**Agent Usage:**
```
User: "Get all qualified leads"
→ Agent calls get_fields("Lead") to discover schema
→ Agent generates: "SELECT Id, FirstName, LastName, Status FROM Lead WHERE Status = 'Qualified'"
→ Agent calls query(...)
→ Agent returns results to user
```

---

## Optional Methods

Drivers MAY implement these for enhanced functionality:

### 4. `count(object_name: str) -> int`

**Purpose:** Get total record count for an object (faster than full query).

**Example:**
```python
count = client.count("Lead")
# Returns: 180
```

---

### 5. `get_relationships(object_name: str) -> Dict[str, Any]`

**Purpose:** Discover relationships between objects (foreign keys, lookups).

**Example:**
```python
relationships = client.get_relationships("Lead")
# Returns: {
#   "CampaignId": {
#     "type": "lookup",
#     "references": "Campaign",
#     "field": "Id"
#   }
# }
```

---

### 6. `execute_raw(command: str) -> Any`

**Purpose:** Execute driver-specific commands that don't fit query() pattern.

**Example:**
```python
# For SQL databases
client.execute_raw("CREATE INDEX idx_status ON leads(status)")

# For REST APIs
client.execute_raw("POST /contacts", body={...})
```

---

## Driver Initialization

Drivers should accept configuration via constructor:

```python
class DataSourceClient:
    def __init__(self, api_url: str, api_key: str, **kwargs):
        """
        Initialize client with connection details.

        Args:
            api_url: Base URL for API/database connection
            api_key: Authentication key/token
            **kwargs: Driver-specific options (timeout, retries, etc.)
        """
        self.api_url = api_url
        self.api_key = api_key
        # Initialize connection...
```

**Common kwargs:**
- `timeout` (int): Request timeout in seconds
- `max_retries` (int): Number of retry attempts
- `verify_ssl` (bool): SSL certificate verification

---

## Error Handling

Drivers should raise descriptive exceptions:

```python
class DriverError(Exception):
    """Base exception for driver errors"""
    pass

class AuthenticationError(DriverError):
    """Invalid credentials or API key"""
    pass

class ObjectNotFoundError(DriverError):
    """Requested object doesn't exist"""
    pass

class QueryError(DriverError):
    """Query syntax error or execution failure"""
    pass
```

---

## Query Language

Each driver uses its native query language:

| Driver Type | Query Language | Example |
|------------|----------------|---------|
| Salesforce | SOQL | `SELECT Id, Name FROM Lead WHERE Status = 'New'` |
| PostgreSQL | SQL | `SELECT id, name FROM leads WHERE status = 'New'` |
| MongoDB | MongoDB Query | `{"status": "New"}` |
| REST API | JSON Filter | `{"filter": {"status": {"eq": "New"}}}` |

The agent will learn the query language by:
1. Reading driver documentation (provided in system prompt)
2. Seeing examples in tool descriptions
3. Trial and error with feedback

---

## Agent Integration

The agent receives driver instructions via system prompt:

```python
SYSTEM_PROMPT = f"""
You have access to a {driver_type} driver with these capabilities:

**Available Methods:**
1. list_objects() - Discover available objects
2. get_fields(object_name) - Get field schema
3. query(soql) - Execute SOQL query

**Query Language:** SOQL (Salesforce Object Query Language)

**Example Workflow:**
User: "Get leads from last 30 days"
1. Call get_fields("Lead") to see available fields
2. Generate query: "SELECT Id, FirstName, LastName, CreatedDate FROM Lead WHERE CreatedDate >= LAST_N_DAYS:30"
3. Call query(...) with generated SOQL
4. Return results to user

**Important:**
- ALWAYS call get_fields() before generating queries (don't guess field names!)
- Field names are case-sensitive
- Use proper SOQL syntax (WHERE, ORDER BY, LIMIT, etc.)
"""
```

---

## Testing Your Driver

Create a test script to verify driver contract:

```python
# test_driver.py
from my_driver import MyClient

def test_driver():
    client = MyClient(api_url="...", api_key="...")

    # Test 1: Discovery
    objects = client.list_objects()
    assert isinstance(objects, list)
    assert len(objects) > 0
    print(f"✓ Found {len(objects)} objects")

    # Test 2: Schema
    if objects:
        fields = client.get_fields(objects[0])
        assert isinstance(fields, dict)
        assert len(fields) > 0
        print(f"✓ Object '{objects[0]}' has {len(fields)} fields")

    # Test 3: Query
    results = client.query(f"SELECT * FROM {objects[0]} LIMIT 10")
    assert isinstance(results, list)
    print(f"✓ Query returned {len(results)} records")

    print("\n✅ Driver contract verified!")

if __name__ == "__main__":
    test_driver()
```

---

## Example: Salesforce Driver

See `examples/e2b_mockup/salesforce_driver/` for a complete reference implementation:

```
salesforce_driver/
├── __init__.py
├── client.py              # SalesforceClient class
├── soql_builder.py        # SOQL query builder helpers
├── README.md              # Driver documentation
└── examples/
    ├── list_objects.py    # Discovery example
    ├── get_fields.py      # Schema introspection
    └── query_leads.py     # Query execution
```

**Key Features:**
- ✅ Implements all 3 required methods
- ✅ Raises descriptive exceptions
- ✅ Includes comprehensive documentation
- ✅ Provides usage examples
- ✅ Works with E2B sandboxes

---

## Next Steps

1. **Create your driver** implementing the 3 required methods
2. **Write tests** to verify the contract
3. **Document** query language and usage examples
4. **Integrate** with AgentExecutor (it already supports any driver!)
5. **Test with agent** - let Claude use your driver conversationally

---

## Questions?

- See `examples/e2b_mockup/salesforce_driver/` for reference
- Check `web_ui/app.py` for how agents use drivers
- Read `CLAUDE.md` for system architecture

Happy driver development! 🚀
