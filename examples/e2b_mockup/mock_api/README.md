# Salesforce REST API Mock Server

A FastAPI-based mock server that simulates the Salesforce REST API, backed by DuckDB for data storage.

## Features

- List all available Salesforce objects
- Describe object schemas with field definitions
- Execute simplified SOQL queries
- Create new records (mock implementation)
- CORS enabled for cross-origin requests
- OpenAPI/Swagger documentation

## Prerequisites

- Python 3.8+
- DuckDB database with Salesforce data at `../test_data/salesforce.duckdb`

## Installation

1. Install dependencies:

```bash
pip install -r requirements.txt
```

## Running the Server

### Development Mode (with auto-reload)

```bash
uvicorn main:app --reload
```

### Production Mode

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

The server will start at `http://localhost:8000`

## API Documentation

Once the server is running, you can access:

- Interactive API docs (Swagger UI): http://localhost:8000/docs
- Alternative API docs (ReDoc): http://localhost:8000/redoc
- OpenAPI JSON: http://localhost:8000/openapi.json

## API Endpoints

### 1. List All SObjects

```bash
curl http://localhost:8000/sobjects
```

Returns a list of all available Salesforce objects (Lead, Opportunity, Account, etc.)

### 2. Describe an SObject

```bash
curl http://localhost:8000/sobjects/Lead/describe
```

Returns detailed metadata including all fields, their types, and properties.

### 3. Execute SOQL Query

**Simple query:**
```bash
curl "http://localhost:8000/query?q=SELECT%20*%20FROM%20Lead"
```

**With WHERE clause:**
```bash
curl "http://localhost:8000/query?q=SELECT%20Id,%20Name,%20Status%20FROM%20Lead%20WHERE%20Status='Open'"
```

**With date filter:**
```bash
curl "http://localhost:8000/query?q=SELECT%20*%20FROM%20Lead%20WHERE%20CreatedDate%20%3E%20'2024-01-01'"
```

**Multiple conditions:**
```bash
curl "http://localhost:8000/query?q=SELECT%20*%20FROM%20Lead%20WHERE%20Status='Open'%20AND%20CreatedDate%20%3E%20'2024-01-01'"
```

**With LIMIT:**
```bash
curl "http://localhost:8000/query?q=SELECT%20*%20FROM%20Lead%20LIMIT%2010"
```

### 4. Create a Record

```bash
curl -X POST http://localhost:8000/sobjects/Lead \
  -H "Content-Type: application/json" \
  -d '{
    "FirstName": "John",
    "LastName": "Doe",
    "Company": "Acme Corp",
    "Status": "Open"
  }'
```

Note: This is a mock implementation that returns a fake ID without actually inserting data.

### 5. Health Check

```bash
curl http://localhost:8000/health
```

## SOQL Query Support

The mock server supports simplified SOQL queries with the following features:

### Supported Clauses

- `SELECT` - Field selection (including `*` for all fields)
- `FROM` - Object name
- `WHERE` - Simple conditions with `=`, `>`, `<`, `>=`, `<=`
- `AND` - Multiple conditions
- `ORDER BY` - Result sorting
- `LIMIT` - Limit number of results

### Supported Objects

- Lead → `leads` table
- Opportunity → `opportunities` table
- Account → `accounts` table
- Contact → `contacts` table
- Case → `cases` table
- Task → `tasks` table
- Event → `events` table

### Query Examples

```sql
-- All records
SELECT * FROM Lead

-- Specific fields
SELECT Id, Name, Email FROM Lead

-- With filter
SELECT * FROM Lead WHERE Status = 'Open'

-- Date comparison
SELECT * FROM Lead WHERE CreatedDate > '2024-01-01'

-- Multiple conditions
SELECT * FROM Lead WHERE Status = 'Open' AND CreatedDate > '2024-01-01'

-- With sorting
SELECT * FROM Lead ORDER BY CreatedDate DESC

-- With limit
SELECT * FROM Lead LIMIT 100

-- Combined
SELECT Id, Name, Status FROM Lead
WHERE Status = 'Open'
ORDER BY CreatedDate DESC
LIMIT 50
```

## Response Format

All responses follow the Salesforce REST API format:

**Query Response:**
```json
{
  "totalSize": 42,
  "done": true,
  "records": [
    {
      "attributes": {
        "type": "Lead",
        "url": "/services/data/v58.0/sobjects/00Q..."
      },
      "Id": "00Q5e00000D8dZzEAJ",
      "FirstName": "John",
      "LastName": "Doe",
      "Status": "Open"
    }
  ]
}
```

## Error Handling

The API returns appropriate HTTP status codes:

- `200` - Success
- `400` - Bad request (invalid query syntax)
- `404` - Resource not found (unknown SObject)
- `500` - Internal server error

Error responses include a message and error code:

```json
{
  "message": "SObject 'Unknown' not found",
  "errorCode": "NOT_FOUND"
}
```

## Database Schema

The server automatically maps Salesforce objects to DuckDB tables:

| Salesforce Object | DuckDB Table |
|-------------------|--------------|
| Lead              | leads        |
| Opportunity       | opportunities|
| Account           | accounts     |
| Contact           | contacts     |
| Case              | cases        |
| Task              | tasks        |
| Event             | events       |

## Development

### Project Structure

```
mock_api/
├── main.py           # FastAPI application and endpoints
├── db.py             # DuckDB connection and query helpers
├── models.py         # Pydantic models for request/response
├── soql_parser.py    # SOQL to SQL converter
├── swagger.yaml      # OpenAPI specification
├── requirements.txt  # Python dependencies
└── README.md         # This file
```

### Adding New Objects

To add support for a new Salesforce object:

1. Add the mapping in `db.py`:
```python
OBJECT_TABLE_MAP = {
    # ...
    "CustomObject": "custom_objects",
}
```

2. Ensure the corresponding table exists in the DuckDB database

### Type Mapping

DuckDB types are automatically mapped to Salesforce field types:

| DuckDB Type | Salesforce Type |
|-------------|-----------------|
| VARCHAR     | string          |
| INTEGER     | int             |
| BIGINT      | long            |
| DOUBLE      | double          |
| DECIMAL     | currency        |
| DATE        | date            |
| TIMESTAMP   | datetime        |
| BOOLEAN     | boolean         |
| TEXT        | textarea        |

## Testing

You can test the API using the interactive docs at http://localhost:8000/docs or with curl commands shown above.

## Limitations

This is a mock implementation with the following limitations:

- SOQL parsing is simplified (doesn't support all Salesforce features)
- No authentication/authorization
- POST operations generate fake IDs without persisting data
- No support for UPDATE, DELETE operations
- No support for relationship queries (e.g., `Account.Name`)
- No support for aggregate functions (COUNT, SUM, etc.)
- Read-only database connection

## License

MIT
