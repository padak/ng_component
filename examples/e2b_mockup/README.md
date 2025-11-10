# E2B Mockup - Agent-Based Salesforce Integration

Complete implementation of an AI agent executor that uses the Salesforce driver in E2B sandboxes. This demonstrates how AI agents (like Claude) can safely execute Salesforce operations in isolated environments.

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Edit .env and add your E2B_API_KEY

# 3. Start mock API (in separate terminal)
cd mock_api
python main.py

# 4. Run tests
python test_executor.py

# 5. Try examples
python example_usage.py
```

**See [QUICKSTART.md](QUICKSTART.md) for detailed setup instructions.**

## What is This?

This project demonstrates a complete agent-based integration system for Salesforce:

1. **AI Agent** receives natural language request (e.g., "Get all leads from last 30 days")
2. **Agent Executor** orchestrates the execution:
   - Creates isolated E2B sandbox
   - Loads Salesforce driver
   - Discovers schema
   - Generates Python script
   - Executes safely in sandbox
3. **Salesforce Driver** communicates with API
4. **Mock API** provides test data
5. **Results** returned to user

### Why E2B Sandboxes?

E2B provides isolated, secure execution environments:
- Code runs in separate Docker containers
- No access to host filesystem
- Limited network access
- Resource and time limits
- Perfect for AI-generated code

## Directory Structure

```
examples/e2b_mockup/
│
├── agent_executor.py           # Main orchestrator (AgentExecutor class)
├── script_templates.py         # Pre-built operation templates
├── test_executor.py           # Comprehensive test suite
├── example_usage.py           # Usage examples
│
├── QUICKSTART.md              # 5-minute setup guide
├── README_AGENT.md            # Detailed agent executor docs
├── ARCHITECTURE.md            # System architecture & data flow
├── requirements.txt           # Python dependencies
├── .env.example               # Environment variable template
│
├── salesforce_driver/         # Salesforce Python client
│   ├── client.py             # Main SalesforceClient class
│   ├── exceptions.py         # Custom exceptions
│   ├── README.md             # Driver documentation
│   └── examples/             # Usage examples
│
├── mock_api/                  # FastAPI mock Salesforce API
│   ├── main.py               # API server
│   ├── db.py                 # DuckDB database
│   ├── soql_parser.py        # SOQL to SQL converter
│   └── README.md             # API documentation
│
├── test_data/                 # Test data generation
│   └── setup.py              # Populate database
│
└── test_scenarios/            # Integration test scenarios
    └── scenario_*.py         # Various test scenarios
```

## Core Components

### 1. Agent Executor (`agent_executor.py`)

Main orchestrator that manages the entire execution flow.

```python
from agent_executor import AgentExecutor

# Create executor
executor = AgentExecutor()

# Execute natural language request
result = executor.execute("Get all leads from last 30 days")

# Check results
if result['success']:
    print(f"Found {result['data']['count']} leads")

# Clean up
executor.close()
```

**Features:**
- Automatic sandbox creation and management
- Driver upload and configuration
- Schema discovery and caching
- Template-based script generation
- Error handling and cleanup

**See [README_AGENT.md](README_AGENT.md) for complete documentation.**

### 2. Script Templates (`script_templates.py`)

Pre-built templates for common Salesforce operations:

- `get_recent_leads(days)` - Get leads from last N days
- `get_campaign_with_leads(name)` - Get campaign with leads
- `get_leads_by_status(status)` - Filter by status
- `get_all_leads(limit)` - Get all leads
- `custom_query(soql)` - Execute custom SOQL
- `discover_schema(object)` - Schema discovery

```python
from script_templates import ScriptTemplates

script = ScriptTemplates.get_recent_leads(
    api_url='http://host.docker.internal:8000',
    api_key='test_key',
    days=30
)
```

### 3. Salesforce Driver (`salesforce_driver/`)

Python client library for Salesforce API:

```python
from salesforce_driver import SalesforceClient

client = SalesforceClient(
    api_url='http://localhost:8000',
    api_key='test_key'
)

# List objects
objects = client.list_objects()

# Get schema
schema = client.get_fields('Lead')

# Query data
leads = client.query("SELECT Id, Name FROM Lead")
```

**See [salesforce_driver/README.md](salesforce_driver/README.md)**

### 4. Mock API (`mock_api/`)

FastAPI-based mock Salesforce API:

- Object listing (`/sobjects`)
- Schema description (`/sobjects/{object}/describe`)
- SOQL queries (`/query?q=...`)
- DuckDB backend
- Realistic test data

```bash
cd mock_api
python main.py

# API runs on http://localhost:8000
```

**See [mock_api/README.md](mock_api/README.md)**

## Example User Requests

The agent executor handles natural language requests:

```python
executor = AgentExecutor()

# Recent leads
executor.execute("Get all leads from last 30 days")
executor.execute("Show me leads from the last week")

# Filtered leads
executor.execute("Get leads with status New")
executor.execute("Show me qualified leads")

# Campaign queries
executor.execute("Get leads for Summer Campaign")

# General queries
executor.execute("Get all leads")
```

## How It Works

```
User Request
    ↓
Agent Executor
    ↓ Create E2B Sandbox
    ↓ Upload Driver Files
    ↓ Run Discovery
    ↓ Generate Script
    ↓ Execute in Sandbox
    ↓   ↓
    ↓   → Salesforce Driver → Mock API → DuckDB
    ↓   ←                   ←          ←
    ↓ Parse Results
    ↓
Return to User
```

**See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed flow diagrams.**

## Testing

### Run All Tests

```bash
python test_executor.py
```

This tests:
1. Environment variables
2. Mock API connectivity
3. E2B sandbox creation
4. Driver loading
5. Discovery operations
6. Query execution
7. Full integration flow

### Run Specific Tests

```bash
python test_executor.py --test e2b        # E2B connection
python test_executor.py --test driver     # Driver loading
python test_executor.py --test discovery  # Discovery
python test_executor.py --test full       # Full flow
```

### Expected Output

```
================================================================================
AGENT EXECUTOR TEST SUITE
================================================================================

Test 1: Environment Variables
✓ E2B_API_KEY: e2b_sk_...
✓ SF_API_URL: http://localhost:8000
✓ SF_API_KEY: test_key...

Test 2: Mock API Connectivity
✓ Mock API is running

Test 3: E2B Connection
✓ Sandbox created: sandbox-abc123
✓ Code executed successfully

...

Total: 8/8 tests passed
🎉 All tests passed!
```

## Usage Examples

### Basic Usage

```python
from agent_executor import AgentExecutor

with AgentExecutor() as executor:
    result = executor.execute("Get all leads")

    if result['success']:
        for lead in result['data']['leads']:
            print(f"{lead['Name']} - {lead['Company']}")
```

### Multiple Requests (Reuse Sandbox)

```python
executor = AgentExecutor()

# All requests use same sandbox (faster)
result1 = executor.execute("Get leads from last 30 days")
result2 = executor.execute("Get leads with status New")
result3 = executor.execute("Get leads for Summer Campaign")

executor.close()
```

### Discovery

```python
with AgentExecutor() as executor:
    # Run discovery
    discovery = executor.run_discovery()

    print(f"Available objects: {discovery['objects']}")

    for obj_name, schema in discovery['schemas'].items():
        fields = schema.get('fields', [])
        print(f"{obj_name}: {len(fields)} fields")
```

### Custom Script

```python
from agent_executor import AgentExecutor
from script_templates import ScriptTemplates

with AgentExecutor() as executor:
    script = ScriptTemplates.custom_query(
        api_url=executor.sandbox_sf_api_url,
        api_key=executor.sf_api_key,
        soql_query="SELECT Id, Name FROM Lead WHERE Email != null"
    )

    result = executor.execute_script(script, "Custom query")
```

**See [example_usage.py](example_usage.py) for more examples.**

## Configuration

### Environment Variables

Required variables (set in `.env`):

```bash
# E2B API key (get from https://e2b.dev/)
E2B_API_KEY=e2b_sk_your_key_here

# Mock API URL (default: http://localhost:8000)
SF_API_URL=http://localhost:8000

# Mock API key (any value for testing)
SF_API_KEY=test_key_12345
```

### Network Configuration

The executor automatically handles network addressing:

- **On Host:** `http://localhost:8000`
- **In E2B Sandbox:** `http://host.docker.internal:8000`

This conversion happens automatically in the executor.

## Architecture Highlights

### Security & Isolation

- **Sandboxed Execution** - Code runs in isolated Docker containers
- **No Host Access** - Scripts cannot access host filesystem
- **Limited Network** - Only specified API endpoints accessible
- **Resource Limits** - CPU, memory, and time limits enforced
- **Disposable** - Sandboxes are created and destroyed per session

### Performance Optimization

- **Sandbox Reuse** - One sandbox handles multiple requests
- **Discovery Caching** - Schema cached for session
- **Parallel Execution** - Multiple sandboxes for concurrent requests
- **Pre-built Templates** - Fast script generation

### Error Handling

Comprehensive error handling at every level:

- Environment validation
- Sandbox creation errors
- Driver loading errors
- Script execution errors
- API communication errors

All errors are captured and returned in structured format.

## Development

### Adding New Templates

1. Add method to `ScriptTemplates` class:

```python
@staticmethod
def your_new_operation(api_url, api_key, param):
    script = f'''
    from salesforce_driver import SalesforceClient
    client = SalesforceClient('{api_url}', '{api_key}')
    result = client.query("YOUR SOQL")
    print(json.dumps(result))
    '''
    return script
```

2. Add pattern matching in `AgentExecutor._generate_from_template()`:

```python
if 'your pattern' in prompt_lower:
    script = ScriptTemplates.your_new_operation(...)
    return script, "Description"
```

### Testing New Templates

```python
from agent_executor import AgentExecutor
from script_templates import ScriptTemplates

with AgentExecutor() as executor:
    script = ScriptTemplates.your_new_operation(
        api_url=executor.sandbox_sf_api_url,
        api_key=executor.sf_api_key,
        param='value'
    )
    result = executor.execute_script(script, "Test new operation")
    print(result)
```

## API Reference

### AgentExecutor

```python
class AgentExecutor:
    def __init__(
        e2b_api_key: str = None,
        sf_api_url: str = None,
        sf_api_key: str = None,
        auto_load_driver: bool = True
    )

    def create_sandbox() -> Sandbox
        # Creates E2B sandbox

    def load_driver() -> bool
        # Uploads driver to sandbox

    def run_discovery() -> Dict[str, Any]
        # Discovers Salesforce schema

    def execute_script(script: str, description: str) -> Dict[str, Any]
        # Executes Python script

    def execute(user_prompt: str, use_template: bool = True) -> Dict[str, Any]
        # Main execution method

    def close()
        # Cleanup resources
```

### Response Format

```python
{
    'success': bool,              # Whether execution succeeded
    'user_prompt': str,           # Original user request
    'description': str,           # What was executed
    'output': str,                # Raw output from sandbox
    'error': str | None,          # Error message if failed
    'data': dict | None,          # Parsed JSON data if available
    'sandbox_id': str | None,     # E2B sandbox ID
    'discovered_objects': list    # Available Salesforce objects
}
```

## Documentation

- **[QUICKSTART.md](QUICKSTART.md)** - Get started in 5 minutes
- **[README_AGENT.md](README_AGENT.md)** - Detailed agent executor docs
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - System architecture & data flow
- **[salesforce_driver/README.md](salesforce_driver/README.md)** - Driver documentation
- **[mock_api/README.md](mock_api/README.md)** - API documentation

## Troubleshooting

### Common Issues

**"E2B_API_KEY not set"**
- Copy `.env.example` to `.env`
- Add your E2B API key

**"Cannot connect to Mock API"**
- Start the mock API: `cd mock_api && python main.py`
- Verify with: `curl http://localhost:8000/health`

**"Failed to create sandbox"**
- Check E2B API key is valid
- Verify E2B account has quota
- Check network connectivity

**"Driver import failed"**
- Ensure `salesforce_driver/` directory exists
- Check all `.py` files are present

See [QUICKSTART.md](QUICKSTART.md) for more troubleshooting tips.

## Roadmap

Future enhancements:

- [ ] LLM-based script generation (replace templates)
- [ ] More Salesforce objects (Account, Opportunity, etc.)
- [ ] Real Salesforce API integration
- [ ] Streaming results for large queries
- [ ] Result caching
- [ ] Parallel query execution
- [ ] Web UI for testing

## Resources

- [E2B Documentation](https://e2b.dev/docs)
- [E2B Code Interpreter](https://github.com/e2b-dev/code-interpreter)
- [Salesforce SOQL Reference](https://developer.salesforce.com/docs/atlas.en-us.soql_sosl.meta/soql_sosl/)

## Contributing

This is example/demo code. To extend:

1. Add new templates in `script_templates.py`
2. Add new test scenarios in `test_scenarios/`
3. Extend the mock API with more objects
4. Improve error handling
5. Add more documentation

## License

This is example code for demonstration purposes.

## Support

For issues or questions:

1. Check the documentation files
2. Run the test suite: `python test_executor.py`
3. Review example usage: `python example_usage.py`
4. Check the architecture docs: [ARCHITECTURE.md](ARCHITECTURE.md)

---

**Quick Links:**
- [5-Minute Setup Guide](QUICKSTART.md)
- [Agent Executor Docs](README_AGENT.md)
- [System Architecture](ARCHITECTURE.md)
- [Driver Documentation](salesforce_driver/README.md)
- [API Documentation](mock_api/README.md)
