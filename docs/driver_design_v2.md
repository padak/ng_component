# Driver Design v2.0 - Production Architecture

**Version:** 2.0
**Date:** 2025-11-11
**Status:** Design Specification

---

## Executive Summary

The **Driver** is the bridge between the **Agent** (Claude Code generating Python scripts) and **External Systems** (Salesforce, PostgreSQL, Weather APIs, etc.).

### Key Relationship

```
User (Business Request)
    ↓
Agent (Generates Python Code)
    ↓
Driver (Provides API + Documentation)
    ↓
External System (Salesforce, APIs, DBs)
```

### Core Principle

> **Driver documents HOW to write Python code. Agent generates the code. Python runtime executes it.**

The driver is NOT a runtime orchestrator - it's a **well-documented Python library** that agents use to generate correct integration scripts.

### What Driver Provides

1. **API Interface** - Methods for discovery, read, write operations
2. **Documentation** - README, docstrings, examples for agent to learn from
3. **Error Handling** - Structured exceptions the agent can understand
4. **Capabilities Discovery** - Agent learns what the driver can do
5. **Best Practices** - Automatic retry, rate limiting, connection pooling

---

## Driver API Contract v2.0

Every driver MUST implement this contract to be usable by agents.

### Core Interface

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Iterator
from enum import Enum

class PaginationStyle(Enum):
    """How the driver handles pagination"""
    NONE = "none"              # No pagination support
    OFFSET = "offset"          # LIMIT/OFFSET style (SQL)
    CURSOR = "cursor"          # Cursor-based (Salesforce, GraphQL)
    PAGE_NUMBER = "page"       # Page-based (REST APIs)

@dataclass
class DriverCapabilities:
    """What the driver can do"""
    read: bool = True
    write: bool = False
    update: bool = False
    delete: bool = False
    batch_operations: bool = False
    streaming: bool = False
    pagination: PaginationStyle = PaginationStyle.NONE
    query_language: Optional[str] = None  # "SOQL", "SQL", "MongoDB Query", None
    max_page_size: Optional[int] = None
    supports_transactions: bool = False
    supports_relationships: bool = False

class BaseDriver(ABC):
    """
    Base class for all drivers.
    Every driver should inherit from this and implement required methods.
    """

    def __init__(
        self,
        api_url: str,
        api_key: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 3,
        debug: bool = False,
        **kwargs
    ):
        """
        Initialize the driver.

        Args:
            api_url: Base URL for API/database connection
            api_key: Authentication key/token (optional, can be loaded from env)
            timeout: Request timeout in seconds
            max_retries: Number of retry attempts for rate limiting
            debug: Enable debug logging (logs all API calls)
            **kwargs: Driver-specific options
        """
        self.api_url = api_url
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        self.debug = debug

        # Validate credentials at init time (fail fast!)
        self._validate_connection()

    @classmethod
    def from_env(cls, **kwargs) -> 'BaseDriver':
        """
        Create driver instance from environment variables.

        Example:
            # Reads SF_API_URL and SF_API_KEY from os.environ
            client = SalesforceDriver.from_env()

        Raises:
            AuthenticationError: If required env vars are missing
        """
        pass  # Implementation in subclass

    @abstractmethod
    def get_capabilities(self) -> DriverCapabilities:
        """
        Return driver capabilities so agent knows what it can do.

        Returns:
            DriverCapabilities with boolean flags for features

        Example:
            capabilities = client.get_capabilities()
            if capabilities.write:
                # Agent can generate create() calls
        """
        pass

    # Discovery Methods (REQUIRED)

    @abstractmethod
    def list_objects(self) -> List[str]:
        """
        Discover all available objects/tables/entities.

        Returns:
            List of object names (e.g., ["Lead", "Campaign", "Account"])

        Example:
            objects = client.list_objects()
            # Salesforce: ["Lead", "Opportunity", "Account"]
            # PostgreSQL: ["users", "posts", "comments"]
            # Weather API: ["forecast", "historical", "air_quality"]
        """
        pass

    @abstractmethod
    def get_fields(self, object_name: str) -> Dict[str, Any]:
        """
        Get complete field schema for an object.

        Args:
            object_name: Name of object (case-sensitive!)

        Returns:
            Dictionary with field definitions:
            {
                "field_name": {
                    "type": "string|integer|float|boolean|datetime|...",
                    "label": "Human-readable name",
                    "required": bool,
                    "nullable": bool,
                    "max_length": int (for strings),
                    "references": str (for foreign keys)
                }
            }

        Raises:
            ObjectNotFoundError: If object doesn't exist

        Example:
            fields = client.get_fields("Lead")
            # Returns: {
            #   "Id": {"type": "string", "required": True, "label": "ID"},
            #   "FirstName": {"type": "string", "required": False, "label": "First Name"},
            #   ...
            # }
        """
        pass

    # Read Operations (REQUIRED)

    @abstractmethod
    def read(
        self,
        query: str,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute a read query and return results.

        Args:
            query: Query in driver's native language (SOQL, SQL, etc.)
            limit: Maximum number of records to return
            offset: Number of records to skip (for pagination)

        Returns:
            List of dictionaries (one per record)

        Raises:
            QuerySyntaxError: Invalid query syntax
            RateLimitError: API rate limit exceeded (after retries)

        Example (Salesforce):
            results = client.read(
                "SELECT Id, FirstName, LastName FROM Lead WHERE Status = 'Qualified'",
                limit=100
            )
            # Returns: [{"Id": "00Q...", "FirstName": "John", ...}, ...]

        Example (REST API - query is ignored):
            results = client.read("", limit=10)  # Uses default endpoint
        """
        pass

    # Write Operations (OPTIONAL - depends on capabilities)

    def create(self, object_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new record.

        Args:
            object_name: Name of object to create
            data: Field values as dictionary

        Returns:
            Created record with ID

        Raises:
            NotImplementedError: If driver doesn't support write operations
            ValidationError: If data is invalid

        Example:
            record = client.create("Lead", {
                "FirstName": "John",
                "LastName": "Doe",
                "Company": "Acme Corp",
                "Status": "New"
            })
            # Returns: {"Id": "00Q...", "FirstName": "John", ...}
        """
        raise NotImplementedError("Write operations not supported by this driver")

    def update(self, object_name: str, record_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update an existing record.

        Args:
            object_name: Name of object
            record_id: ID of record to update
            data: Field values to update

        Returns:
            Updated record

        Raises:
            NotImplementedError: If driver doesn't support updates
            ObjectNotFoundError: If record doesn't exist
        """
        raise NotImplementedError("Update operations not supported by this driver")

    def delete(self, object_name: str, record_id: str) -> bool:
        """
        Delete a record.

        Args:
            object_name: Name of object
            record_id: ID of record to delete

        Returns:
            True if successful

        Raises:
            NotImplementedError: If driver doesn't support delete

        Note:
            Agents should RARELY generate delete operations!
            Always require explicit user approval for deletes.
        """
        raise NotImplementedError("Delete operations not supported by this driver")

    # Pagination / Streaming (OPTIONAL)

    def read_batched(
        self,
        query: str,
        batch_size: int = 1000
    ) -> Iterator[List[Dict[str, Any]]]:
        """
        Execute query and yield results in batches (memory-efficient).

        Args:
            query: Query in driver's native language
            batch_size: Number of records per batch

        Yields:
            Batches of records as lists of dictionaries

        Example:
            for batch in client.read_batched("SELECT * FROM huge_table", batch_size=1000):
                process_batch(batch)  # Process 1000 records at a time

        Note:
            Agent generates code with this pattern.
            Python runtime handles iteration (not the agent!).
        """
        raise NotImplementedError("Batched reading not supported by this driver")

    # Low-Level API (OPTIONAL - for REST APIs)

    def call_endpoint(
        self,
        endpoint: str,
        method: str = "GET",
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Call a REST API endpoint directly (low-level access).

        Args:
            endpoint: API endpoint path (e.g., "/v1/forecast")
            method: HTTP method ("GET", "POST", "PUT", "DELETE")
            params: URL query parameters
            data: Request body (for POST/PUT)
            **kwargs: Additional request options

        Returns:
            Response data as dictionary

        Example:
            result = client.call_endpoint(
                endpoint="/v1/forecast",
                method="GET",
                params={
                    "latitude": 37.7749,
                    "longitude": -122.4194,
                    "hourly": ["temperature_2m", "precipitation"],
                    "forecast_days": 5
                }
            )
        """
        raise NotImplementedError("Low-level endpoint calls not supported by this driver")

    # Utility Methods

    def get_rate_limit_status(self) -> Dict[str, Any]:
        """
        Get current rate limit status (if supported by API).

        Returns:
            {
                "remaining": int,     # Requests remaining
                "limit": int,         # Total limit
                "reset_at": str,      # ISO timestamp when limit resets
                "retry_after": int    # Seconds to wait (if rate limited)
            }

        Example:
            status = client.get_rate_limit_status()
            if status["remaining"] < 10:
                print("Warning: Only 10 API calls left!")
        """
        return {"remaining": None, "limit": None, "reset_at": None, "retry_after": None}

    def close(self):
        """
        Close connections and cleanup resources.

        Example:
            client = Driver.from_env()
            try:
                results = client.read("SELECT * FROM table")
            finally:
                client.close()
        """
        pass

    # Internal Methods

    def _validate_connection(self):
        """
        Validate connection at __init__ time (fail fast!).

        Raises:
            AuthenticationError: Invalid credentials
            ConnectionError: Cannot reach API
        """
        pass
```

---

## Exception Hierarchy

Drivers MUST raise structured exceptions that agents can understand and react to.

```python
class DriverError(Exception):
    """Base exception for all driver errors"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def __str__(self):
        """Return descriptive error message for agent"""
        return f"{self.__class__.__name__}: {self.message}"

class AuthenticationError(DriverError):
    """
    Invalid credentials or API key.

    Agent should:
    - Inform user to check credentials
    - Check .env file exists and has correct keys
    """
    pass

class ConnectionError(DriverError):
    """
    Cannot reach API (network issue, API down).

    Agent should:
    - Inform user API is unreachable
    - Suggest checking api_url configuration
    - Wait and retry later
    """
    pass

class ObjectNotFoundError(DriverError):
    """
    Requested object/table doesn't exist.

    Agent should:
    - Call list_objects() to see what's available
    - Suggest similar object names (fuzzy match)

    Example:
        ObjectNotFoundError(
            "Object 'Leads' not found. Did you mean 'Lead'?",
            details={"suggestions": ["Lead", "Campaign"]}
        )
    """
    pass

class FieldNotFoundError(DriverError):
    """
    Requested field doesn't exist on object.

    Agent should:
    - Call get_fields(object_name) to see available fields
    - Suggest similar field names

    Example:
        FieldNotFoundError(
            "Field 'Email' not found on Lead. Did you mean 'EmailAddress'?",
            details={"object": "Lead", "suggestions": ["EmailAddress", "Email__c"]}
        )
    """
    pass

class QuerySyntaxError(DriverError):
    """
    Invalid query syntax.

    Agent should:
    - Fix query syntax based on error message
    - Consult driver README for query language rules
    - Regenerate query

    Example:
        QuerySyntaxError(
            "SOQL syntax error: Expected field name after SELECT",
            details={"query": "SELECT FROM Lead", "position": 7}
        )
    """
    pass

class RateLimitError(DriverError):
    """
    API rate limit exceeded (after automatic retries).

    Driver automatically retries with exponential backoff.
    This exception is only raised after max_retries exhausted.

    Agent should:
    - Inform user of rate limit
    - Suggest reducing batch size or adding delays
    - Show retry_after seconds

    Example:
        RateLimitError(
            "API rate limit exceeded. Retry after 60 seconds.",
            details={"retry_after": 60, "limit": 1000, "reset_at": "2025-11-11T15:30:00Z"}
        )
    """
    pass

class ValidationError(DriverError):
    """
    Data validation failed (for write operations).

    Note: Driver does NOT validate input by default.
    This is only raised when API returns validation errors.

    Agent should:
    - Check required fields are present
    - Fix data types
    - Regenerate create/update call

    Example:
        ValidationError(
            "Required field 'LastName' is missing",
            details={"object": "Lead", "missing_fields": ["LastName"]}
        )
    """
    pass

class TimeoutError(DriverError):
    """
    Request timed out.

    Agent should:
    - Inform user
    - Suggest increasing timeout parameter
    - Retry with smaller dataset
    """
    pass
```

### Error Message Best Practices

Every error MUST include:
1. **Clear message** - What went wrong (for agent to understand)
2. **Actionable suggestion** - What to do to fix it
3. **Details dict** - Structured data for programmatic handling

Example of GOOD error:
```python
raise ObjectNotFoundError(
    "Object 'Leads' not found. Did you mean 'Lead'? Available objects: Lead, Campaign, Account",
    details={
        "requested": "Leads",
        "suggestions": ["Lead"],
        "available": ["Lead", "Campaign", "Account"]
    }
)
```

Example of BAD error:
```python
raise Exception("Object not found")  # ❌ Not helpful!
```

---

## Documentation Requirements

For the agent to use the driver effectively, documentation is CRITICAL.

### 1. README.md (REQUIRED)

Every driver MUST have a comprehensive README with these sections:

```markdown
# [System Name] Driver

## Overview
Brief description of the system (Salesforce, PostgreSQL, Weather API, etc.).

## Installation
\`\`\`bash
pip install salesforce-driver
\`\`\`

## Quick Start
\`\`\`python
from salesforce_driver import SalesforceDriver

# Option 1: Load from environment
client = SalesforceDriver.from_env()

# Option 2: Explicit credentials
client = SalesforceDriver(
    api_url="https://yourinstance.salesforce.com",
    api_key="your_api_key_here"
)

# Discovery
objects = client.list_objects()
fields = client.get_fields("Lead")

# Query data
results = client.read("SELECT Id, Name FROM Lead WHERE Status = 'Qualified'")

# Cleanup
client.close()
\`\`\`

## Authentication
How to get credentials, where to put them (.env), what permissions are needed.

## Query Language
- **Language**: SOQL (Salesforce Object Query Language)
- **Syntax**: `SELECT fields FROM object WHERE condition`
- **Examples**:
  - `SELECT Id, Name FROM Lead`
  - `SELECT Id, Name FROM Lead WHERE Status = 'Qualified'`
  - `SELECT Id, Name FROM Lead WHERE CreatedDate >= LAST_N_DAYS:30`

## Capabilities
- ✅ Read operations (SOQL queries)
- ✅ Write operations (create, update)
- ❌ Delete operations (not supported)
- ✅ Batch operations (up to 1000 records)
- ✅ Pagination (cursor-based)

## Common Patterns

### Pagination for large datasets
\`\`\`python
for batch in client.read_batched("SELECT * FROM Lead", batch_size=1000):
    process_batch(batch)
\`\`\`

### Error handling
\`\`\`python
from salesforce_driver.exceptions import ObjectNotFoundError, RateLimitError

try:
    results = client.read("SELECT * FROM NonExistentObject")
except ObjectNotFoundError as e:
    print(f"Error: {e.message}")
    print(f"Available objects: {e.details['available']}")
except RateLimitError as e:
    print(f"Rate limited. Retry after {e.details['retry_after']} seconds")
\`\`\`

## API Reference
Link to full API documentation or docstrings.

## Rate Limits
- 1000 requests per hour
- Driver automatically retries with exponential backoff
- Check remaining requests: `client.get_rate_limit_status()`

## Troubleshooting
Common issues and solutions.
```

### 2. Docstrings (REQUIRED)

Every public method MUST have a docstring with:
- Description
- Type hints
- Args with descriptions
- Returns description
- Raises documentation
- Example usage

Example:
```python
def get_fields(self, object_name: str) -> Dict[str, Any]:
    """
    Get complete field schema for an object.

    This method calls the API to retrieve all fields, their types,
    and metadata for the specified object.

    Args:
        object_name: Name of the object (case-sensitive!)
                     Use list_objects() to see available objects.

    Returns:
        Dictionary mapping field names to field metadata:
        {
            "field_name": {
                "type": "string|integer|float|...",
                "label": "Human Readable Name",
                "required": bool,
                "nullable": bool
            }
        }

    Raises:
        ObjectNotFoundError: If object doesn't exist
        AuthenticationError: If credentials are invalid
        RateLimitError: If API rate limit exceeded

    Example:
        >>> client = SalesforceDriver.from_env()
        >>> fields = client.get_fields("Lead")
        >>> print(fields.keys())
        dict_keys(['Id', 'FirstName', 'LastName', 'Email', ...])

        >>> # Check if field exists
        >>> if "Email" in fields:
        ...     print(f"Email type: {fields['Email']['type']}")
        Email type: string
    """
    pass
```

### 3. OpenAPI Spec (OPTIONAL - for REST APIs)

For REST API drivers, provide an OpenAPI/Swagger spec:

```yaml
# openapi.yaml
openapi: 3.0.0
info:
  title: Weather API Driver
  version: 1.0.0
paths:
  /v1/forecast:
    get:
      summary: Get weather forecast
      parameters:
        - name: latitude
          in: query
          required: true
          schema:
            type: number
        - name: longitude
          in: query
          required: true
          schema:
            type: number
        - name: forecast_days
          in: query
          schema:
            type: integer
            default: 7
      responses:
        200:
          description: Forecast data
          content:
            application/json:
              schema:
                type: object
                properties:
                  hourly:
                    type: object
```

Agents can read this to understand REST API structure.

### 4. Example Scripts (REQUIRED)

Provide 3-5 certified example scripts in `examples/` folder:

```python
# examples/list_all_leads.py
"""
Example: List all leads from Salesforce
"""
from salesforce_driver import SalesforceDriver

def main():
    # Initialize client from environment
    client = SalesforceDriver.from_env()

    try:
        # Query all leads
        results = client.read("SELECT Id, FirstName, LastName, Email FROM Lead")

        print(f"Found {len(results)} leads:")
        for lead in results:
            print(f"  - {lead['FirstName']} {lead['LastName']} ({lead['Email']})")

    finally:
        client.close()

if __name__ == "__main__":
    main()
```

```python
# examples/recent_qualified_leads.py
"""
Example: Get leads from last 30 days with 'Qualified' status
"""
from salesforce_driver import SalesforceDriver

def main():
    client = SalesforceDriver.from_env()

    try:
        # Query with filters
        query = """
            SELECT Id, FirstName, LastName, Company, Status, CreatedDate
            FROM Lead
            WHERE Status = 'Qualified'
            AND CreatedDate >= LAST_N_DAYS:30
            ORDER BY CreatedDate DESC
        """

        results = client.read(query)

        print(f"Found {len(results)} qualified leads from last 30 days:")
        for lead in results:
            print(f"  - {lead['Company']}: {lead['FirstName']} {lead['LastName']}")

    finally:
        client.close()

if __name__ == "__main__":
    main()
```

```python
# examples/pagination_large_dataset.py
"""
Example: Process large dataset with pagination
"""
from salesforce_driver import SalesforceDriver

def main():
    client = SalesforceDriver.from_env()

    try:
        total_processed = 0

        # Use batched reading for memory efficiency
        for batch in client.read_batched("SELECT * FROM Lead", batch_size=1000):
            # Process each batch
            process_batch(batch)
            total_processed += len(batch)
            print(f"Processed {total_processed} records...")

        print(f"Done! Total: {total_processed} records")

    finally:
        client.close()

def process_batch(records):
    """Process a batch of records"""
    # Your processing logic here
    pass

if __name__ == "__main__":
    main()
```

These examples serve as **few-shot learning** for the agent.

---

## System-Specific Examples

Different types of systems require different driver designs.

### Example 1: Salesforce Driver (Query Language + High-Level API)

```python
from typing import List, Dict, Any, Optional, Iterator
from .base import BaseDriver, DriverCapabilities, PaginationStyle
from .exceptions import *
import requests
import os

class SalesforceDriver(BaseDriver):
    """
    Salesforce driver using SOQL query language.

    Features:
    - SOQL query execution
    - High-level CRUD operations
    - Automatic retry on rate limits
    - Cursor-based pagination

    Example:
        client = SalesforceDriver.from_env()
        leads = client.read("SELECT Id, Name FROM Lead WHERE Status = 'Qualified'")

        # Or use high-level API
        lead = client.create_lead(first_name="John", last_name="Doe", company="Acme")
    """

    @classmethod
    def from_env(cls, **kwargs):
        """Load credentials from SF_API_URL and SF_API_KEY environment variables"""
        api_url = os.environ.get("SF_API_URL")
        api_key = os.environ.get("SF_API_KEY")

        if not api_url or not api_key:
            raise AuthenticationError(
                "Missing Salesforce credentials. Set SF_API_URL and SF_API_KEY environment variables.",
                details={"env_vars": ["SF_API_URL", "SF_API_KEY"]}
            )

        return cls(api_url=api_url, api_key=api_key, **kwargs)

    def get_capabilities(self) -> DriverCapabilities:
        return DriverCapabilities(
            read=True,
            write=True,
            update=True,
            delete=False,  # Delete not allowed!
            batch_operations=True,
            streaming=False,
            pagination=PaginationStyle.CURSOR,
            query_language="SOQL",
            max_page_size=2000,
            supports_transactions=False,
            supports_relationships=True
        )

    def list_objects(self) -> List[str]:
        """List all Salesforce objects"""
        response = self._api_call("/sobjects")
        return [obj["name"] for obj in response["sobjects"]]

    def get_fields(self, object_name: str) -> Dict[str, Any]:
        """Get field schema for a Salesforce object"""
        try:
            response = self._api_call(f"/sobjects/{object_name}/describe")
        except requests.HTTPError as e:
            if e.response.status_code == 404:
                available = self.list_objects()
                raise ObjectNotFoundError(
                    f"Object '{object_name}' not found. Available objects: {', '.join(available[:5])}...",
                    details={"requested": object_name, "available": available}
                )
            raise

        fields = {}
        for field in response["fields"]:
            fields[field["name"]] = {
                "type": field["type"],
                "label": field["label"],
                "required": not field["nillable"],
                "nullable": field["nillable"],
                "max_length": field.get("length"),
                "references": field.get("referenceTo")
            }

        return fields

    def read(self, query: str, limit: Optional[int] = None, offset: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Execute SOQL query.

        Example:
            results = client.read("SELECT Id, Name FROM Lead WHERE Status = 'Qualified'")
        """
        # Add limit/offset if provided
        if limit:
            query += f" LIMIT {limit}"
        if offset:
            query += f" OFFSET {offset}"

        try:
            response = self._api_call("/query", params={"q": query})
        except requests.HTTPError as e:
            if e.response.status_code == 400:
                raise QuerySyntaxError(
                    f"SOQL syntax error: {e.response.json().get('message', 'Unknown error')}",
                    details={"query": query}
                )
            raise

        return response["records"]

    def read_batched(self, query: str, batch_size: int = 1000) -> Iterator[List[Dict[str, Any]]]:
        """
        Execute SOQL query and yield results in batches (cursor-based pagination).

        Example:
            for batch in client.read_batched("SELECT * FROM Lead", batch_size=1000):
                process_batch(batch)
        """
        query_locator = None

        while True:
            if query_locator:
                # Continue from cursor
                response = self._api_call(f"/query/{query_locator}")
            else:
                # Initial query
                response = self._api_call("/query", params={"q": f"{query} LIMIT {batch_size}"})

            records = response["records"]
            if records:
                yield records

            # Check if more records
            if not response.get("done"):
                query_locator = response["nextRecordsUrl"].split("/")[-1]
            else:
                break

    def create(self, object_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a Salesforce record.

        Example:
            lead = client.create("Lead", {
                "FirstName": "John",
                "LastName": "Doe",
                "Company": "Acme Corp"
            })
        """
        try:
            response = self._api_call(f"/sobjects/{object_name}", method="POST", json=data)
            return {"Id": response["id"], **data}
        except requests.HTTPError as e:
            if e.response.status_code == 400:
                error_data = e.response.json()
                raise ValidationError(
                    f"Validation failed: {error_data[0]['message']}",
                    details={"object": object_name, "errors": error_data}
                )
            raise

    # High-level API (convenience methods)

    def create_lead(
        self,
        first_name: str,
        last_name: str,
        company: str,
        email: Optional[str] = None,
        status: str = "New",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Create a Lead (high-level convenience method).

        Example:
            lead = client.create_lead(
                first_name="John",
                last_name="Doe",
                company="Acme Corp",
                email="john@acme.com"
            )
        """
        data = {
            "FirstName": first_name,
            "LastName": last_name,
            "Company": company,
            "Status": status,
            **kwargs
        }
        if email:
            data["Email"] = email

        return self.create("Lead", data)

    # Internal helpers

    def _api_call(self, endpoint: str, method: str = "GET", **kwargs):
        """Make API call with automatic retry on rate limits"""
        url = f"{self.api_url}{endpoint}"
        headers = {"Authorization": f"Bearer {self.api_key}"}

        for attempt in range(self.max_retries):
            try:
                if self.debug:
                    print(f"[DEBUG] {method} {url}")

                response = requests.request(
                    method,
                    url,
                    headers=headers,
                    timeout=self.timeout,
                    **kwargs
                )
                response.raise_for_status()
                return response.json()

            except requests.HTTPError as e:
                if e.response.status_code == 429:
                    # Rate limited - retry with exponential backoff
                    retry_after = int(e.response.headers.get("Retry-After", 2 ** attempt))
                    if attempt < self.max_retries - 1:
                        if self.debug:
                            print(f"[DEBUG] Rate limited. Retrying in {retry_after}s...")
                        time.sleep(retry_after)
                        continue
                    else:
                        raise RateLimitError(
                            f"API rate limit exceeded. Retry after {retry_after} seconds.",
                            details={"retry_after": retry_after}
                        )
                raise

    def _validate_connection(self):
        """Validate connection at init"""
        try:
            self._api_call("/sobjects")
        except requests.HTTPError as e:
            if e.response.status_code == 401:
                raise AuthenticationError(
                    "Invalid Salesforce credentials. Check your API key.",
                    details={"api_url": self.api_url}
                )
            raise ConnectionError(f"Cannot connect to Salesforce: {e}")
```

### Example 2: Weather API Driver (REST API, No Query Language)

```python
class WeatherAPIDriver(BaseDriver):
    """
    Open-Meteo Weather API driver.

    This is a REST API with no query language - just endpoints with parameters.

    Example:
        client = WeatherAPIDriver(api_url="https://api.open-meteo.com")
        forecast = client.get_forecast(latitude=37.77, longitude=-122.41, days=5)
    """

    @classmethod
    def from_env(cls, **kwargs):
        """Weather API doesn't require authentication"""
        api_url = os.environ.get("WEATHER_API_URL", "https://api.open-meteo.com")
        return cls(api_url=api_url, api_key=None, **kwargs)

    def get_capabilities(self) -> DriverCapabilities:
        return DriverCapabilities(
            read=True,
            write=False,
            update=False,
            delete=False,
            batch_operations=False,
            streaming=False,
            pagination=PaginationStyle.NONE,
            query_language=None,  # No query language!
            max_page_size=None,
            supports_transactions=False,
            supports_relationships=False
        )

    def list_objects(self) -> List[str]:
        """List available endpoints (treated as 'objects')"""
        return ["forecast", "historical", "air_quality", "geocoding"]

    def get_fields(self, object_name: str) -> Dict[str, Any]:
        """Get parameters for an endpoint"""
        if object_name == "forecast":
            return {
                "name": "forecast",
                "endpoint": "/v1/forecast",
                "methods": ["GET"],
                "parameters": {
                    "latitude": {
                        "type": "float",
                        "required": True,
                        "description": "Latitude (degrees)"
                    },
                    "longitude": {
                        "type": "float",
                        "required": True,
                        "description": "Longitude (degrees)"
                    },
                    "hourly": {
                        "type": "array",
                        "required": False,
                        "items": ["temperature_2m", "precipitation", "wind_speed_10m"],
                        "description": "Hourly weather variables"
                    },
                    "forecast_days": {
                        "type": "integer",
                        "required": False,
                        "default": 7,
                        "description": "Number of forecast days (1-16)"
                    }
                },
                "response": {
                    "hourly": {
                        "time": "ISO8601 timestamps",
                        "temperature_2m": "float array",
                        "precipitation": "float array"
                    }
                }
            }
        else:
            raise ObjectNotFoundError(f"Endpoint '{object_name}' not found")

    def read(self, query: str, limit: Optional[int] = None, offset: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Not applicable for REST APIs without query language.
        Use call_endpoint() or high-level methods instead.
        """
        raise NotImplementedError(
            "Weather API doesn't have a query language. Use call_endpoint() or get_forecast() instead."
        )

    def call_endpoint(
        self,
        endpoint: str,
        method: str = "GET",
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Call REST API endpoint.

        Example:
            result = client.call_endpoint(
                endpoint="/v1/forecast",
                params={
                    "latitude": 37.7749,
                    "longitude": -122.4194,
                    "hourly": ["temperature_2m"],
                    "forecast_days": 5
                }
            )
        """
        url = f"{self.api_url}{endpoint}"

        if self.debug:
            print(f"[DEBUG] {method} {url} params={params}")

        response = requests.request(
            method,
            url,
            params=params,
            json=data,
            timeout=self.timeout
        )
        response.raise_for_status()
        return response.json()

    # High-level API (convenience)

    def get_forecast(
        self,
        latitude: float,
        longitude: float,
        days: int = 7,
        hourly: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Get weather forecast (high-level convenience method).

        Args:
            latitude: Latitude in degrees
            longitude: Longitude in degrees
            days: Number of forecast days (1-16)
            hourly: List of hourly variables (e.g., ["temperature_2m", "precipitation"])

        Returns:
            Forecast data with hourly arrays

        Example:
            forecast = client.get_forecast(
                latitude=37.7749,
                longitude=-122.4194,
                days=5,
                hourly=["temperature_2m", "precipitation"]
            )

            # Access data
            temps = forecast["hourly"]["temperature_2m"]
            print(f"First hour temp: {temps[0]}°C")
        """
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "forecast_days": days
        }

        if hourly:
            params["hourly"] = ",".join(hourly)

        return self.call_endpoint("/v1/forecast", params=params)
```

### Example 3: PostgreSQL Driver (SQL Query Language)

```python
class PostgreSQLDriver(BaseDriver):
    """
    PostgreSQL database driver.

    Features:
    - SQL query execution
    - Transaction support
    - Batch operations
    - Offset-based pagination

    Example:
        client = PostgreSQLDriver.from_env()
        users = client.read("SELECT * FROM users WHERE created_at > '2025-01-01'")
    """

    def __init__(self, api_url: str, api_key: Optional[str] = None, **kwargs):
        # For PostgreSQL, api_url is connection string
        # api_key is password (or part of connection string)
        super().__init__(api_url, api_key, **kwargs)

        import psycopg2
        self.conn = psycopg2.connect(api_url)

    @classmethod
    def from_env(cls, **kwargs):
        """Load from PG_CONNECTION_STRING environment variable"""
        connection_string = os.environ.get("PG_CONNECTION_STRING")
        if not connection_string:
            raise AuthenticationError(
                "Missing PostgreSQL connection string. Set PG_CONNECTION_STRING environment variable.",
                details={"format": "postgresql://user:password@host:port/database"}
            )
        return cls(api_url=connection_string, **kwargs)

    def get_capabilities(self) -> DriverCapabilities:
        return DriverCapabilities(
            read=True,
            write=True,
            update=True,
            delete=True,  # PostgreSQL supports delete
            batch_operations=True,
            streaming=False,
            pagination=PaginationStyle.OFFSET,
            query_language="SQL",
            max_page_size=None,
            supports_transactions=True,
            supports_relationships=True
        )

    def list_objects(self) -> List[str]:
        """List all tables in database"""
        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
            """)
            return [row[0] for row in cur.fetchall()]

    def get_fields(self, object_name: str) -> Dict[str, Any]:
        """Get column schema for a table"""
        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_name = %s
            """, (object_name,))

            fields = {}
            for row in cur.fetchall():
                fields[row[0]] = {
                    "type": row[1],
                    "nullable": row[2] == "YES",
                    "default": row[3]
                }

            if not fields:
                available = self.list_objects()
                raise ObjectNotFoundError(
                    f"Table '{object_name}' not found. Available tables: {', '.join(available)}",
                    details={"requested": object_name, "available": available}
                )

            return fields

    def read(self, query: str, limit: Optional[int] = None, offset: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Execute SQL query.

        Example:
            results = client.read("SELECT * FROM users WHERE active = true")
        """
        # Add limit/offset
        if limit:
            query += f" LIMIT {limit}"
        if offset:
            query += f" OFFSET {offset}"

        with self.conn.cursor() as cur:
            try:
                cur.execute(query)
            except Exception as e:
                raise QuerySyntaxError(f"SQL syntax error: {e}", details={"query": query})

            columns = [desc[0] for desc in cur.description]
            return [dict(zip(columns, row)) for row in cur.fetchall()]

    def create(self, object_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Insert a row"""
        columns = ", ".join(data.keys())
        placeholders = ", ".join(["%s"] * len(data))
        query = f"INSERT INTO {object_name} ({columns}) VALUES ({placeholders}) RETURNING *"

        with self.conn.cursor() as cur:
            cur.execute(query, list(data.values()))
            self.conn.commit()

            columns = [desc[0] for desc in cur.description]
            row = cur.fetchone()
            return dict(zip(columns, row))

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
```

---

## Agent Integration Guidelines

How agents should use drivers to generate correct Python scripts.

### 1. Discovery Flow

**When to discover:**
- **Start of session** - First time user mentions a system
- **On-demand** - When agent encounters unknown object/field
- **Never** - When agent already has schema cached in conversation

**Agent decision logic:**
```python
# Agent's internal logic (conceptual, not actual code)
if "Salesforce" mentioned and not schema_cached:
    # Load driver
    driver = load_driver("salesforce")

    # Read capabilities
    capabilities = driver.get_capabilities()

    # Discover available objects
    objects = driver.list_objects()

    # Cache for this session
    cache_schema(objects)

# Later, when user asks "Get all leads":
if "Lead" not in schema_cache:
    # Discover Lead fields
    fields = driver.get_fields("Lead")
    cache_schema("Lead", fields)

# Generate query using cached schema
query = generate_soql_query(fields, user_request)
```

### 2. Code Generation Patterns

**Pattern 1: Simple Query**
```python
# Agent generates:
from salesforce_driver import SalesforceDriver

client = SalesforceDriver.from_env()

try:
    results = client.read("SELECT Id, FirstName, LastName FROM Lead WHERE Status = 'Qualified'")

    print(f"Found {len(results)} qualified leads:")
    for lead in results:
        print(f"  - {lead['FirstName']} {lead['LastName']}")

finally:
    client.close()
```

**Pattern 2: Pagination for Large Datasets**
```python
# Agent generates:
from salesforce_driver import SalesforceDriver

client = SalesforceDriver.from_env()

try:
    total = 0

    # Python runtime handles iteration (not the agent!)
    for batch in client.read_batched("SELECT * FROM Lead", batch_size=1000):
        # Process each batch
        for lead in batch:
            # ... do something with lead ...
            pass

        total += len(batch)
        print(f"Processed {total} records...")

    print(f"Done! Total: {total} records")

finally:
    client.close()
```

**Pattern 3: Error Handling**
```python
# Agent generates:
from salesforce_driver import SalesforceDriver
from salesforce_driver.exceptions import ObjectNotFoundError, RateLimitError

client = SalesforceDriver.from_env()

try:
    # Try to query
    results = client.read("SELECT * FROM CustomObject__c")

except ObjectNotFoundError as e:
    # Handle missing object
    print(f"Error: {e.message}")
    print(f"Available objects: {', '.join(e.details['available'][:10])}")

except RateLimitError as e:
    # Handle rate limit
    print(f"Rate limited! Retry after {e.details['retry_after']} seconds")

finally:
    client.close()
```

**Pattern 4: Multi-System Integration**
```python
# Agent generates:
from salesforce_driver import SalesforceDriver
from postgresql_driver import PostgreSQLDriver

# Initialize both drivers
sf_client = SalesforceDriver.from_env()
pg_client = PostgreSQLDriver.from_env()

try:
    # Get data from Salesforce
    leads = sf_client.read("SELECT Id, FirstName, LastName, Email FROM Lead WHERE Status = 'Qualified'")

    print(f"Fetched {len(leads)} leads from Salesforce")

    # Insert into PostgreSQL
    for lead in leads:
        pg_client.create("leads", {
            "salesforce_id": lead["Id"],
            "first_name": lead["FirstName"],
            "last_name": lead["LastName"],
            "email": lead["Email"]
        })

    print(f"Inserted {len(leads)} leads into PostgreSQL")

finally:
    sf_client.close()
    pg_client.close()
```

### 3. README-Driven Learning

Agents should read driver READMEs to learn:
- Query language syntax
- Common patterns
- Example scripts
- Error handling
- Rate limits

**Agent's learning flow:**
1. Load driver's README.md
2. Parse "Query Language" section → Learn syntax
3. Read "Common Patterns" section → Learn best practices
4. Look at `examples/` scripts → Few-shot learning

---

## Production Considerations

### 1. Rate Limiting Strategy

**Driver implementation:**
```python
def _api_call_with_retry(self, url, method="GET", **kwargs):
    """Make API call with exponential backoff on rate limits"""
    for attempt in range(self.max_retries):
        try:
            response = requests.request(method, url, **kwargs)
            response.raise_for_status()
            return response.json()

        except requests.HTTPError as e:
            if e.response.status_code == 429:
                # Rate limited - calculate backoff
                retry_after = int(e.response.headers.get("Retry-After", 2 ** attempt))

                if attempt < self.max_retries - 1:
                    # Retry
                    if self.debug:
                        print(f"[DEBUG] Rate limited. Retrying in {retry_after}s (attempt {attempt+1}/{self.max_retries})")
                    time.sleep(retry_after)
                    continue
                else:
                    # Exhausted retries
                    raise RateLimitError(
                        f"API rate limit exceeded after {self.max_retries} attempts. Retry after {retry_after} seconds.",
                        details={
                            "retry_after": retry_after,
                            "attempts": self.max_retries
                        }
                    )

            # Other HTTP errors - don't retry
            raise
```

**Configuration:**
```python
# Default: 3 retries with exponential backoff
client = SalesforceDriver.from_env(max_retries=3)

# For high-volume scripts: increase retries
client = SalesforceDriver.from_env(max_retries=10)

# For testing: no retries
client = SalesforceDriver.from_env(max_retries=0)
```

### 2. Connection Pooling

For database drivers, use connection pooling:

```python
class PostgreSQLDriver(BaseDriver):
    """PostgreSQL driver with connection pooling"""

    _connection_pool = None

    def __init__(self, api_url: str, **kwargs):
        super().__init__(api_url, **kwargs)

        # Create connection pool (shared across instances)
        if not PostgreSQLDriver._connection_pool:
            from psycopg2 import pool
            PostgreSQLDriver._connection_pool = pool.SimpleConnectionPool(
                minconn=1,
                maxconn=10,
                dsn=api_url
            )

        self.conn = self._connection_pool.getconn()

    def close(self):
        """Return connection to pool"""
        if self.conn:
            self._connection_pool.putconn(self.conn)
```

### 3. Debug Mode

Enable debug logging for troubleshooting:

```python
# Enable debug mode
client = SalesforceDriver.from_env(debug=True)

# Now all API calls are logged:
# [DEBUG] GET https://api.salesforce.com/sobjects
# [DEBUG] Rate limited. Retrying in 2s...
# [DEBUG] GET https://api.salesforce.com/query?q=SELECT...

results = client.read("SELECT * FROM Lead")
```

### 4. Testing Guidelines

**Mock API responses for testing:**

```python
# tests/test_salesforce_driver.py
import pytest
from unittest.mock import Mock, patch
from salesforce_driver import SalesforceDriver

@patch('salesforce_driver.requests.request')
def test_list_objects(mock_request):
    """Test list_objects() with mocked API"""
    # Mock API response
    mock_response = Mock()
    mock_response.json.return_value = {
        "sobjects": [
            {"name": "Lead"},
            {"name": "Campaign"},
            {"name": "Account"}
        ]
    }
    mock_request.return_value = mock_response

    # Test
    client = SalesforceDriver(api_url="https://test.salesforce.com", api_key="test_key")
    objects = client.list_objects()

    assert objects == ["Lead", "Campaign", "Account"]
    mock_request.assert_called_once()

@patch('salesforce_driver.requests.request')
def test_rate_limit_retry(mock_request):
    """Test automatic retry on rate limit"""
    # First call: rate limited
    rate_limit_response = Mock()
    rate_limit_response.status_code = 429
    rate_limit_response.headers = {"Retry-After": "1"}
    rate_limit_response.raise_for_status.side_effect = requests.HTTPError(response=rate_limit_response)

    # Second call: success
    success_response = Mock()
    success_response.json.return_value = {"sobjects": []}

    mock_request.side_effect = [rate_limit_response, success_response]

    # Test
    client = SalesforceDriver(api_url="https://test.salesforce.com", api_key="test_key", max_retries=2)
    objects = client.list_objects()

    assert mock_request.call_count == 2  # Retried once
```

**Integration tests with E2B:**

```python
# tests/test_integration.py
from e2b_code_interpreter import Sandbox

def test_salesforce_driver_in_e2b():
    """Test driver works in E2B sandbox"""

    # Create sandbox
    sandbox = Sandbox.create()

    try:
        # Install driver
        sandbox.run_code("!pip install salesforce-driver")

        # Upload test script
        script = """
from salesforce_driver import SalesforceDriver

client = SalesforceDriver(
    api_url="https://test.salesforce.com",
    api_key="test_key"
)

objects = client.list_objects()
print(f"Found {len(objects)} objects")
"""

        result = sandbox.run_code(script)

        # Verify
        assert "Found" in result.logs.stdout[0]
        assert result.error is None

    finally:
        sandbox.kill()
```

### 5. Versioning

Drivers should declare their version:

```python
# salesforce_driver/__init__.py
__version__ = "1.0.0"

from .client import SalesforceDriver
from .exceptions import *

__all__ = ["SalesforceDriver", "DriverCapabilities", ...]
```

Agents can check version compatibility:

```python
import salesforce_driver

if salesforce_driver.__version__ < "1.0.0":
    raise Exception("Driver version too old. Please upgrade: pip install --upgrade salesforce-driver")
```

---

## Comparison with MCP Code Execution

Our driver design aligns with Anthropic's [Code Execution with MCP](https://www.anthropic.com/engineering/code-execution-with-mcp) paradigm while providing specialized value for data integration use cases.

### Shared Foundation

Both approaches recognize that **agents should generate code rather than make direct tool calls**:

✅ **Code execution** - Agent generates code, sandbox executes it
✅ **Context efficiency** - Only final results pass through agent context
✅ **Progressive disclosure** - Tools/capabilities loaded on-demand
✅ **Local data processing** - Filter/transform data in execution environment
✅ **Privacy benefits** - Sensitive data stays in execution environment

**Key insight from Anthropic article:**
> "LLMs are adept at writing code and developers should take advantage of this strength."

**Our driver principle:**
> "Driver documents HOW to write Python code. Agent generates the code. Python runtime executes it."

**These are fundamentally the same paradigm!** ✅

### Our Specialized Advantages

While Anthropic provides a **generic approach** for any MCP server, our driver design offers **specialized value** for data integration:

#### 1. Data Integration Focus

**Anthropic MCP + Code Execution:**
- Generic approach (any MCP server, any domain)
- Filesystem-based discovery (`./servers/google-drive/tools.ts`)
- No domain-specific patterns

**Our Driver Design:**
```python
# Standardized discovery pattern for data sources:
objects = client.list_objects()           # What data is available?
fields = client.get_fields("Lead")        # What's the structure?
results = client.read("SELECT ...")       # Query the data
```

**Benefits:**
- 🎯 **Standardized discovery flow** across all data sources
- 🎯 **Schema introspection** as first-class citizen
- 🎯 **CRUD operations** explicitly designed
- 🎯 **Pagination patterns** (offset, cursor, page-based)

#### 2. The "10% vs 90%" Problem

From our original concept:
> "10% is the actual technical logic, 90% is productization - making it work for people's unique installations"

**Anthropic article:**
- Doesn't address this specific pain point
- Generic code execution framework

**Our design:**
- ✅ **Agent handles the 90%** (adaptation to custom installations)
- ✅ **Driver provides the 10%** (technical implementation)
- ✅ **Eliminates customization overhead**

**Real-world impact:**
```
Traditional connector:
- Hardcoded fields
- Breaks when customer adds custom fields
- Requires developer intervention

Our approach:
- Agent discovers custom fields at runtime
- Generates code that adapts automatically
- No developer needed!
```

#### 3. Business User Workflow

**Anthropic article:**
- Developer/technical user perspective
- Focus on code efficiency

**Our design:**
- 🎯 **Business users** (non-programmers) as primary audience
- 🎯 **Natural language → Python script** pipeline
- 🎯 **Approval workflow** for non-technical validation
- 🎯 **Agent as intermediary** between business requirements and technical implementation

**Example workflow:**
```
Business user: "I want leads from last 30 days with email and company"

Agent: [Discovers schema, generates script, shows preview]
       "This will fetch 150 leads. Should I proceed?"

Business user: "Yes" [Non-technical approval]

Agent: [Runs in E2B, returns results]
```

#### 4. LLM-Optimized Documentation

**Our driver structure:**
```
driver/
├── README.md          # System overview + query language syntax
├── examples/          # 3-5 certified scripts (few-shot learning!)
│   ├── simple_query.py
│   ├── pagination.py
│   └── error_handling.py
└── docstrings         # Type hints + examples in every method
```

**Learning flow:**
1. Agent reads **README.md** → "This is how SOQL works"
2. Agent studies **examples/query_with_filters.py** → "Aha, this is how to filter"
3. Agent examines **examples/pagination.py** → "This is how to handle large datasets"
4. Agent generates own script using learned patterns

**Anthropic approach:**
- Filesystem exploration (agent must "discover" what exists)
- No structured learning process
- No few-shot examples

**Our advantage:**
- 🎯 **Few-shot learning** from certified examples
- 🎯 **Query language documentation** (SOQL syntax, SQL patterns)
- 🎯 **Common patterns** section (agent learns best practices)
- 🎯 **Guaranteed-to-work examples**

#### 5. Both Abstraction Layers

**Our design supports two levels:**
```python
# Low-level (flexibility):
client.read("SELECT Id, Name FROM Lead WHERE Status = 'Qualified'")
client.call_endpoint("/v1/forecast", params={...})

# High-level (convenience):
client.create_lead(first_name="John", last_name="Doe", company="Acme")
client.get_forecast(latitude=37.77, longitude=-122.41, days=5)
```

**Benefits:**
- 🎯 Agent chooses appropriate abstraction (simple → high-level, complex → low-level)
- 🎯 **Learning progression** (start with high-level, gradually use low-level)
- 🎯 Supports both **query languages** (SOQL, SQL) and **REST APIs** (no query language)

**Anthropic:**
- Only low-level (direct API calls)

#### 6. Query Language Agnostic

**Our design supports:**

| System | Query Language | Implementation |
|--------|---------------|----------------|
| Salesforce | SOQL | `read("SELECT Id FROM Lead")` |
| PostgreSQL | SQL | `read("SELECT id FROM leads")` |
| MongoDB | MongoDB Query | `read('{"status": "New"}')` |
| Weather API | None (REST) | `call_endpoint("/forecast", params={...})` |

**How it works:**
- ✅ Driver documents its query language in README
- ✅ Agent learns syntax from examples/
- ✅ REST APIs without query language supported via `call_endpoint()`

**Anthropic:**
- Assumes filesystem/module-based APIs
- Doesn't address query language learning

#### 7. Production-Ready Features

**Our design includes:**

```python
# Automatic retry (exponential backoff)
client = SalesforceDriver(max_retries=3)
# Driver handles 429 errors transparently!

# Connection pooling (databases)
client = PostgreSQLDriver()  # Reuses connections

# Debug mode
client = Driver(debug=True)  # Logs all API calls

# Fail-fast validation
client = Driver(api_key="invalid")  # Fails at __init__, not during execution!
```

**Anthropic article:**
- Doesn't mention rate limiting
- Doesn't mention connection pooling
- Doesn't address production concerns

**Why this matters:**
- 🎯 Agent doesn't handle retry logic (driver does it)
- 🎯 Production scripts are reliable out-of-the-box
- 🎯 Debugging is easy (debug=True)

#### 8. Structured Exception Hierarchy

**Our approach:**

```python
try:
    results = client.read("SELECT * FROM NonExistent")
except ObjectNotFoundError as e:
    # e.message: "Object 'NonExistent' not found. Did you mean 'Lead'?"
    # e.details: {"suggestions": ["Lead", "Campaign"]}

except RateLimitError as e:
    # e.details: {"retry_after": 60, "reset_at": "2025-11-11T15:30:00Z"}

except QuerySyntaxError as e:
    # e.details: {"query": "SELECT FROM Lead", "position": 7}
```

**Benefits:**
- 🎯 Agent **understands errors** (structured, not raw API errors)
- 🎯 **Actionable suggestions** ("Did you mean 'Lead'?")
- 🎯 **Programmatic error handling** (agent can parse `details`)

**Anthropic:**
- Doesn't address error handling for data integration
- Raw exceptions only

#### 9. Capabilities Discovery

**Our standardized approach:**

```python
capabilities = client.get_capabilities()

# Returns:
DriverCapabilities(
    read=True,
    write=True,
    delete=False,           # Salesforce: delete not allowed!
    pagination=PaginationStyle.CURSOR,
    query_language="SOQL",
    max_page_size=2000
)

# Agent now knows:
# - Can write → generates create() calls
# - Cannot delete → won't offer delete operations
# - Uses cursor pagination → generates read_batched() code
# - Query language is SOQL → learns syntax from README
```

**Benefits:**
- 🎯 **Self-documenting** - agent discovers what driver supports
- 🎯 **Safety** - agent won't propose unsupported operations
- 🎯 **Optimization** - agent uses correct pagination style

**Anthropic:**
- No standardized capabilities discovery

#### 10. Multi-System Orchestration

**Our explicit pattern:**

```python
# Agent generates:
from salesforce_driver import SalesforceDriver
from postgresql_driver import PostgreSQLDriver

sf = SalesforceDriver.from_env()
pg = PostgreSQLDriver.from_env()

try:
    # Multi-system integration!
    leads = sf.read("SELECT * FROM Lead WHERE Status = 'Qualified'")

    for lead in leads:
        pg.create("leads", {
            "salesforce_id": lead["Id"],
            "first_name": lead["FirstName"],
            ...
        })
finally:
    sf.close()
    pg.close()
```

**Our design includes:**
- ✅ Multi-driver patterns in examples/
- ✅ Error handling across systems
- ✅ Proper cleanup (close() on both drivers)

**Anthropic:**
- Single system focus
- Doesn't address multi-system orchestration

### Comparison Summary

| Feature | Anthropic MCP + Code Exec | Our Driver Design |
|---------|---------------------------|-------------------|
| **Paradigm** | ✅ Code execution | ✅ Code execution |
| **Context efficiency** | ✅ High (98.7% reduction) | ✅ High (same pattern) |
| **Data integration focus** | ❌ Generic | ✅ Specialized |
| **Discovery pattern** | Filesystem exploration | ✅ `list_objects()`, `get_fields()` |
| **10% vs 90% problem** | ❌ Not addressed | ✅ Core design principle |
| **Business user focus** | ❌ Developer-focused | ✅ Non-technical users |
| **LLM-optimized docs** | Filesystem | ✅ README + examples + docstrings |
| **Abstraction layers** | Low-level only | ✅ Low + High level |
| **Query language support** | ❌ | ✅ SOQL, SQL, MongoDB, REST |
| **Production features** | ❌ | ✅ Retry, pooling, debug mode |
| **Error handling** | Raw exceptions | ✅ Structured hierarchy + suggestions |
| **Capabilities discovery** | ❌ | ✅ `get_capabilities()` |
| **Multi-system patterns** | ❌ | ✅ Explicit examples |
| **Pagination support** | ❌ | ✅ 3 styles (offset, cursor, page) |
| **MCP compatible** | ✅ Native | ✅ Can wrap as MCP server |

### Positioning

**Anthropic solves:**
> "How to efficiently use MCP servers through code execution"

**We solve:**
> "How business users can write data integration scripts for customized systems without programming"

**Our relationship to MCP:**
- Drivers **can be wrapped as MCP servers**
- We implement the **Code Execution paradigm** from Anthropic's article
- We provide **specialized value** for data integration use cases
- We're **MCP-compatible** but not MCP-dependent

**In practice:**
```
MCP Protocol (universal standard)
    ↓
MCP + Code Execution (Anthropic best practice)
    ↓
Our Driver Design (specialized implementation for data integration)
```

### Conclusion

Our driver design **validates Anthropic's Code Execution paradigm** while adding specialized value for data integration:

1. ✅ We use the **same core approach** (code execution over direct tool calls)
2. ✅ We achieve the **same benefits** (context efficiency, progressive disclosure, local processing)
3. ✅ We add **data-specific patterns** (discovery, schema introspection, CRUD operations)
4. ✅ We optimize for **business users** (non-technical audience)
5. ✅ We solve **real-world problems** (the 10% vs 90% customization overhead)

**Our unique value proposition:**

> "While Anthropic provides a generic code execution framework for MCP servers, we deliver a specialized solution for data integration that eliminates 90% of customization overhead through agent-driven discovery and LLM-optimized documentation, enabling business users to write integration scripts without programming."

---

## Summary Checklist

When building a new driver, ensure:

### Required Implementation
- [ ] Inherit from `BaseDriver`
- [ ] Implement `__init__()` and `from_env()`
- [ ] Implement `get_capabilities()`
- [ ] Implement `list_objects()`
- [ ] Implement `get_fields(object_name)`
- [ ] Implement `read(query, limit, offset)`
- [ ] Implement structured exception hierarchy
- [ ] Validate credentials at `__init__` (fail fast!)
- [ ] Automatic retry on rate limits (exponential backoff)

### Optional (Based on Capabilities)
- [ ] Implement `create()`, `update()`, `delete()` if supported
- [ ] Implement `read_batched()` for large datasets
- [ ] Implement `call_endpoint()` for REST APIs
- [ ] Implement high-level convenience methods
- [ ] Implement `get_rate_limit_status()`
- [ ] Implement connection pooling for databases

### Documentation
- [ ] README.md with overview, quick start, authentication, query language
- [ ] Docstrings for all public methods (with type hints!)
- [ ] 3-5 example scripts in `examples/` folder
- [ ] OpenAPI spec (if REST API)
- [ ] Troubleshooting section in README

### Testing
- [ ] Unit tests with mocked API responses
- [ ] Integration tests with E2B sandboxes
- [ ] Test error handling (rate limits, auth errors, missing objects)
- [ ] Test pagination for large datasets

### Production Readiness
- [ ] Debug mode support
- [ ] Timeout configuration
- [ ] Max retries configuration
- [ ] Descriptive error messages with suggestions
- [ ] Version declaration in `__init__.py`

---

## Next Steps

1. **Review existing Salesforce driver** (`examples/e2b_mockup/salesforce_driver/`) against this spec
2. **Update PRD** (`docs/prd.md`) Section 4.1 to reference this design
3. **Build second driver** (PostgreSQL or Weather API) to validate contract
4. **Create driver template** (cookiecutter or scaffold script)
5. **Write agent integration guide** (how agents consume drivers)

---

**Questions? Feedback?**
- See current implementation: `examples/e2b_mockup/salesforce_driver/`
- Discuss in PRD: `docs/prd.md`
- Architecture overview: `CLAUDE.md`

**Happy driver development! 🚀**
