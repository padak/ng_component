# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repository implements an **Agent-Based Integration System** - a proof-of-concept demonstrating how AI agents can dynamically generate and execute integration scripts for external systems (like Salesforce) without hardcoded schemas.

**Core Vision**: "10% is the technical logic itself, 90% is productization — and the agent handles those 90%."

See `docs/prd.md` for complete product requirements.

## Repository Structure

```
ng_component/
├── docs/
│   ├── prd.md           # Product Requirements Document
│   └── idea.md          # Original concept notes
│
└── examples/e2b_mockup/  # Working proof-of-concept
    ├── agent_executor.py      # Main orchestrator (uploads & starts everything in E2B)
    ├── script_templates.py    # Pre-built templates for generating scripts
    ├── example_usage.py       # Usage examples
    ├── test_executor.py       # Main test suite
    ├── mock_api/              # FastAPI mock Salesforce (uploaded to sandbox)
    ├── salesforce_driver/     # Python client for agents (uploaded to sandbox)
    ├── test_data/             # DuckDB with 180 test records (uploaded to sandbox)
    └── test_scenarios/        # Integration test scenarios
```

## Key Architecture Concepts

### Discovery-First Pattern

Agents don't need pre-existing knowledge of system schemas:

```python
# 1. Discover objects
objects = client.list_objects()  # ["Lead", "Campaign", ...]

# 2. Discover fields
fields = client.get_fields("Lead")  # {schema with types}

# 3. Generate query dynamically
query = f"SELECT {', '.join(fields.keys())} FROM Lead"
```

### E2B Sandbox Execution

All agent-generated code runs in isolated E2B cloud sandboxes (VMs):

**Architecture:**
- Mock API, DuckDB, and driver all run INSIDE the sandbox
- Scripts call `localhost:8000` (same machine, inside sandbox)
- No network translation needed - everything is local to the sandbox
- AgentExecutor uploads: API code, database file, driver code

**API:**
- Use `Sandbox.create(api_key=...)` not `Sandbox()`
- Cleanup: Use `sandbox.kill()` not `sandbox.close()`

### Driver Contract

Every driver must implement:
- `list_objects() -> List[str]` - Discover available objects
- `get_fields(object_name: str) -> Dict[str, Any]` - Get field schema
- `query(soql: str) -> List[Dict]` - Execute queries

## Common Development Commands

### Setup

```bash
# Install dependencies (use project venv)
source .venv/bin/activate
pip install -r examples/e2b_mockup/requirements.txt

# Initialize test database
cd examples/e2b_mockup/test_data
python setup.py
```

### Running Components

```bash
# Run E2B integration tests (AgentExecutor handles Mock API automatically)
cd examples/e2b_mockup
python test_executor.py

# Run test scenarios
cd examples/e2b_mockup/test_scenarios
python run_all_scenarios.py

# Test driver locally (without E2B, requires manually starting Mock API)
cd examples/e2b_mockup/mock_api
python main.py  # Start in separate terminal

# Then in another terminal:
cd examples/e2b_mockup
PYTHONPATH=. SF_API_URL=http://localhost:8000 SF_API_KEY=test_key \
  python salesforce_driver/examples/list_objects.py
```

### Testing SOQL Parser

```bash
cd examples/e2b_mockup/mock_api
python test_soql_parser.py
```

## Environment Variables

Required in `examples/e2b_mockup/.env`:

```bash
E2B_API_KEY=your_e2b_api_key      # Required for E2B sandboxes
SF_API_URL=http://localhost:8000   # Used inside sandbox (always localhost:8000)
SF_API_KEY=test_key_12345          # Mock API key
```

**Note:** `SF_API_URL` should always be `http://localhost:8000` because this URL is used by scripts running inside the E2B sandbox to connect to the Mock API also running inside the same sandbox.

## Architecture Flow

```
User Request ("Get leads from last 30 days")
    ↓
AgentExecutor (on host)
    ↓
1. Create E2B Sandbox (cloud VM)
2. Upload mock_api/ code to sandbox
3. Upload test_data/salesforce.duckdb to sandbox
4. Upload salesforce_driver/ to sandbox
5. Start Mock API inside sandbox (localhost:8000)
6. Run discovery (optional): list_objects(), get_fields()
7. Generate script from template
8. Execute script in sandbox
    ↓
    [Inside E2B Sandbox]
    Python Script → Salesforce Driver → Mock API (localhost:8000) → DuckDB
                   ←                   ←                           ←
    ↓
Results → AgentExecutor → User
```

**Key Points:**
- All components (API, DB, driver, scripts) run inside the same E2B sandbox
- No network communication between host and sandbox needed
- Scripts use `localhost:8000` to connect to API on same machine

## Known Limitations (By Design)

This is a proof-of-concept mockup:

1. **SOQL Parser**: Basic only (SELECT, WHERE, AND, dates). Date comparisons need quotes: `'2024-01-01'` not `2024-01-01`
2. **Templates**: Pre-built scripts. Production would use Claude Sonnet 4.5 to generate dynamically
3. **Single Driver**: Only Salesforce mock. Production supports multiple systems
4. **Mock API**: Simulated data. Production connects to real APIs

## Important Implementation Notes

### E2B SDK API

The E2B code-interpreter SDK uses:
- `Sandbox.create(api_key=...)` to create sandboxes
- `sandbox.sandbox_id` for ID (not `.id`)
- `sandbox.kill()` to cleanup (not `.close()`)
- `sandbox.run_code(code, envs={...})` for execution
- `sandbox.files.write(path, content)` to upload files (text or binary)

**Output Handling:**
- `result.text` - Last expression value (not print statements!)
- `result.logs.stdout` - List of stdout lines from print()
- `result.logs.stderr` - List of stderr lines
- `result.error` - Exception if code failed

Example:
```python
# This returns None in result.text
result = sandbox.run_code("print('Hello')")
print(result.logs.stdout)  # ['Hello\n']

# This returns 8 in result.text
result = sandbox.run_code("x = 5 + 3\nx")
print(result.text)  # 8
```

### PYTHONPATH for Driver

When testing driver examples locally:
```bash
PYTHONPATH=. python salesforce_driver/examples/script.py
```

### Network Access in Sandbox

All services run INSIDE the E2B sandbox:
- Mock API is uploaded and started inside the sandbox on `localhost:8000`
- DuckDB database file is uploaded to the sandbox filesystem
- Scripts execute inside the sandbox and call `localhost:8000`
- No network translation needed - everything is local to the sandbox VM

### Using AgentExecutor

The `AgentExecutor` class handles all E2B setup automatically:

```python
from agent_executor import AgentExecutor

# Create executor (automatically uploads everything to E2B and starts Mock API)
executor = AgentExecutor()

# Execute a request (generates script, runs in E2B sandbox, returns results)
result = executor.execute("Get all leads from last 30 days")

# Result contains:
# - result['success']: True/False
# - result['data']: List of records
# - result['script']: Generated Python code
# - result['output']: Execution output

# Cleanup
executor.close()  # Kills sandbox and Mock API
```

**What AgentExecutor does automatically:**
1. Creates E2B sandbox (cloud VM)
2. Uploads `mock_api/` folder to `/home/user/mock_api/`
3. Uploads `test_data/salesforce.duckdb` to `/home/user/test_data/`
4. Uploads `salesforce_driver/` to `/home/user/salesforce_driver/`
5. Installs dependencies (fastapi, uvicorn, duckdb, pydantic)
6. Starts uvicorn on background port 8000
7. Waits for API to be ready
8. Executes your script with `PYTHONPATH=/home/user`

## Testing Strategy

1. **Unit tests**: `mock_api/test_soql_parser.py` (SOQL parsing)
2. **Integration tests**: `test_executor.py` (E2B + driver)
3. **Scenario tests**: `test_scenarios/*.py` (end-to-end capabilities)

Expected results:
- SOQL parser: 12/12 tests pass
- E2B integration: All core tests pass (upload, API startup, driver integration)
- Scenarios: 5/5 pass (needs E2B_API_KEY)

**Verified Working (2025-11-10):**
```
✓ Files uploaded to E2B sandbox (mock_api, test_data, salesforce_driver)
✓ Mock API starts inside sandbox on localhost:8000
✓ Driver queries API successfully from within sandbox
✓ Complete flow: Upload → Start API → Query → Return results
```

## What Success Looks Like

✅ Core architecture validated:
- Mock API serves realistic Salesforce responses
- Driver provides discovery capabilities
- E2B sandboxes execute generated code
- Agent can build queries dynamically from discovered schemas

The mockup proves the "discovery → generate → execute" pattern works.

## Common Pitfalls

### ❌ Don't: Try to run Mock API on host machine
```python
# WRONG - This won't work with E2B sandboxes
# Start API locally: cd mock_api && python main.py
# Sandbox tries to reach host localhost - FAILS!
```

### ✅ Do: Let AgentExecutor handle everything
```python
# CORRECT - AgentExecutor uploads and starts API in sandbox
executor = AgentExecutor()  # Everything automatic!
```

### ❌ Don't: Use host.docker.internal
```python
# WRONG - E2B is NOT Docker, this doesn't exist
api_url = "http://host.docker.internal:8000"
```

### ✅ Do: Use localhost in sandbox
```python
# CORRECT - Everything runs in same E2B VM
api_url = "http://localhost:8000"
```

### ❌ Don't: Expect print() in result.text
```python
# WRONG - result.text will be None!
result = sandbox.run_code("print('Hello')")
print(result.text)  # None
```

### ✅ Do: Use result.logs.stdout for print output
```python
# CORRECT - print() goes to logs.stdout
result = sandbox.run_code("print('Hello')")
print(result.logs.stdout)  # ['Hello\n']

# Or return a value for result.text
result = sandbox.run_code("'Hello'")  # Last expression
print(result.text)  # 'Hello'
```

## Next Steps for Production

1. Replace script templates with Claude Sonnet 4.5 API for dynamic generation
2. Add more drivers (PostgreSQL, HubSpot, REST APIs)
3. Implement MCP server registration for drivers
4. Enhance SOQL parser (OR, IN, NOT, subqueries)
5. Add caching layer for discovery results
6. Implement proper error handling and retry logic
7. Add monitoring and logging for production use
